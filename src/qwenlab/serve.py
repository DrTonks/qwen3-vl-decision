"""Persistent, loopback-only text classifier. No database, tools or vendor calls."""
import argparse
from contextlib import ExitStack
import hashlib
import hmac
import json
import os
from pathlib import Path
import threading
import time

from qwenlab.common import ROOT, load_json

PROTOCOL = 'support-classifier-v1'
SPEC = load_json(ROOT / 'configs/decision-v5.json')
POLICY_HASH = hashlib.sha256(json.dumps(SPEC, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
TASKS = ('intent', 'route', 'tool')


def validate_input(value):
    if not isinstance(value, dict) or set(value) - {'message', 'history', 'state', 'available_tools'}:
        raise ValueError('Invalid input fields; text only')
    message = value.get('message')
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
        raise ValueError('message must contain 1-2000 characters')
    history = value.get('history', [])
    if not isinstance(history, list) or len(history) > 4:
        raise ValueError('At most four recent messages')
    for item in history:
        if not isinstance(item, dict) or set(item) != {'role', 'content'} or item['role'] not in ('user', 'assistant'):
            raise ValueError('Invalid history')
        if not isinstance(item['content'], str) or len(item['content']) > 800:
            raise ValueError('History message too long')
    state = value.get('state', {})
    if not isinstance(state, dict) or set(state) - {'authenticated', 'application_id', 'status_code', 'pending'} or state.get('authenticated') is not True:
        raise ValueError('Invalid server-owned state')
    if 'application_id' in state and (type(state['application_id']) is not int or not 0 < state['application_id'] <= 2147483647):
        raise ValueError('Invalid application_id')
    if 'pending' in state and state['pending'] != 'applicationId':
        raise ValueError('Invalid pending field')
    if 'status_code' in state and (type(state['status_code']) is not int or not 0 <= state['status_code'] <= 2147483647):
        raise ValueError('Invalid status_code')
    available = value.get('available_tools', [])
    tools = set(SPEC['questions']['tool']['criteria']) - {'none'}
    if not isinstance(available, list) or any(not isinstance(x, str) or x not in tools for x in available) or len(set(available)) != len(available):
        raise ValueError('Invalid tools')
    return {'message': message, 'history': history, 'state': state, 'available_tools': available}


class QwenEngine:
    def __init__(self, adapter, projection):
        from qwenlab.modeling import load_model
        from qwenlab.candidate_inference import CandidateScorer
        from qwenlab.joint_v5 import encode
        self.encode = encode
        self.adapter = Path(adapter).name
        self.tok, self.model = load_model('nf4', adapter)
        self.tok.padding_side = 'left'
        self.model.eval()
        self.scorer = CandidateScorer(self.model, projection)
        self.predict({'message': '查询我的信用分', 'history': [], 'state': {'authenticated': True},
                      'available_tools': list(SPEC['questions']['tool']['criteria'])[1:]})

    def metadata(self):
        return {'model': 'Qwen3-VL-2B-Instruct', 'adapter': self.adapter, 'projection': self.scorer.projection,
                'projectionFallback': self.scorer.fallback_reason, 'policyVersion': SPEC['version'], 'textOnly': True}

    def predict(self, value):
        import torch
        row = dict(value, id='support-inference', dataset='business',
                   labels={'intent': 'general', 'route': 'clarify', 'tool': 'none'})
        # Encode all tasks before any forward. Never silently truncate an overlong request.
        examples = [self.encode(self.tok, row, task) for task in TASKS]
        torch.cuda.synchronize()
        start = time.perf_counter()
        result = {}
        with torch.inference_mode():
            for task, example in zip(TASKS, examples):
                inputs = self.tok.pad([example['tokens']], padding=True, return_tensors='pt').to('cuda')
                probs = self.scorer.scores(inputs, example['ids'])[0].softmax(-1).cpu().tolist()
                result[task] = {'choice': example['keys'][max(range(len(probs)), key=probs.__getitem__)],
                                'probabilities': dict(zip(example['keys'], probs))}
        torch.cuda.synchronize()
        return {'predictions': result, 'inferenceMs': round((time.perf_counter() - start) * 1000, 3),
                'inputTokens': [len(e['tokens']['input_ids']) for e in examples]}


def create_app(engine, token=''):
    from flask import Flask, jsonify, request
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 32768
    gate = threading.BoundedSemaphore(1)

    @app.before_request
    def authorize():
        if token and not hmac.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + token):
            return jsonify(error='UNAUTHORIZED'), 401

    @app.get('/health')
    @app.get('/ready')
    def health():
        return jsonify(ready=True, protocolVersion=PROTOCOL, policyHash=POLICY_HASH, **engine.metadata())

    @app.post('/decide')
    def decide():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'protocolVersion', 'policyHash', 'input'}:
            return jsonify(error='INVALID_REQUEST'), 400
        if body['protocolVersion'] != PROTOCOL or body['policyHash'] != POLICY_HASH:
            return jsonify(error='PROTOCOL_MISMATCH'), 409
        try:
            value = validate_input(body['input'])
        except ValueError:
            return jsonify(error='INVALID_INPUT'), 400
        # Reject overload immediately instead of creating an unbounded GPU queue.
        if not gate.acquire(blocking=False):
            return jsonify(error='BUSY'), 503
        try:
            result = engine.predict(value)
            return jsonify(protocolVersion=PROTOCOL, policyHash=POLICY_HASH, **engine.metadata(), **result)
        except ValueError:
            return jsonify(error='INPUT_TOO_LONG'), 422
        except Exception:
            # Avoid logging user text, input tensors, credentials or machine paths.
            return jsonify(error='INFERENCE_FAILED'), 503
        finally:
            gate.release()

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=['support-v1'], default='support-v1')
    parser.add_argument('--port', type=int)
    parser.add_argument('--adapter')
    parser.add_argument('--projection', choices=['candidate', 'full'])
    args = parser.parse_args()
    cfg = load_json(ROOT / f'configs/serve-{args.profile}.json')
    adapter = args.adapter or cfg['adapter']
    if not (ROOT / adapter / 'adapter_config.json').is_file():
        raise SystemExit('Adapter not found; configure --adapter or the profile')
    from qwenlab.joint_v5 import exclusive_lock
    from waitress import serve
    # Same locks as the experimental worker: training and serving cannot contend.
    with ExitStack() as stack:
        stack.enter_context(exclusive_lock('joint-v5-pipeline.lock'))
        stack.enter_context(exclusive_lock('joint-v5-gpu.lock'))
        print('Loading Qwen and warming candidate projection...', flush=True)
        engine = QwenEngine(adapter, args.projection or cfg['projection'])
        app = create_app(engine, os.environ.get('QWEN_DECISION_KEY', ''))
        port = args.port or cfg['port']
        print(json.dumps({'ready': True, 'port': port, 'policyHash': POLICY_HASH, **engine.metadata()}), flush=True)
        serve(app, host='127.0.0.1', port=port, threads=4, connection_limit=32, channel_timeout=30)


if __name__ == '__main__':
    main()
