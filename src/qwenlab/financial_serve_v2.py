"""Versioned eight-action transport; no model/API/database is started implicitly.

create_app accepts a protocol-bound engine. The CLI deliberately supports only
an explicit fixture for integration checks until a new-policy model is qualified.
"""
import argparse
from copy import deepcopy
import hashlib
import hmac
import json
import math
import os
import threading
import time

from qwenlab.common import ROOT

SPEC_PATH = ROOT / 'configs/support-financial-v2.json'


def protocol():
    raw = SPEC_PATH.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), hashlib.sha256(raw).hexdigest()


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('Invalid object fields')


def validate_input(value, spec):
    exact_keys(value, ['message', 'history', 'state', 'service_scope', 'capability_profile', 'capabilities', 'available_tools', 'images'])
    if not isinstance(value['message'], str) or not value['message'].strip() or len(value['message']) > 2000:
        raise ValueError('Invalid message')
    history = value['history']
    if not isinstance(history, list) or len(history) > 4:
        raise ValueError('Invalid history')
    for item in history:
        exact_keys(item, ['role', 'content'])
        if item['role'] not in ('user', 'assistant') or not isinstance(item['content'], str) or len(item['content']) > 800:
            raise ValueError('Invalid history item')
    state = value['state']
    exact_keys(state, ['authenticated'], ['application_id', 'status_code', 'pending', 'handoff_status'])
    if type(state['authenticated']) is not bool:
        raise ValueError('Invalid authentication')
    if 'application_id' in state and (type(state['application_id']) is not int or not 0 < state['application_id'] <= 2147483647):
        raise ValueError('Invalid application id')
    if 'status_code' in state and (type(state['status_code']) is not int or state['status_code'] not in (0, 1, 2)):
        raise ValueError('Invalid status code')
    if 'pending' in state and state['pending'] not in ('applicationId', 'statusCode'):
        raise ValueError('Invalid pending state')
    if 'handoff_status' in state and state['handoff_status'] not in ('none', 'requested', 'queued', 'connected', 'failed'):
        raise ValueError('Invalid handoff status')
    if value['service_scope'] != 'loan_platform' or value['capability_profile'] not in ('current-node-no-kb', 'planned-kb'):
        raise ValueError('Invalid capability profile')
    capabilities = value['capabilities']
    exact_keys(capabilities, ['knowledge_collections', 'handoff_available'])
    collections = capabilities['knowledge_collections']
    if not isinstance(collections, list) or any(c not in ('loan_service_docs', 'privacy_policy') for c in collections):
        raise ValueError('Invalid collections')
    if len(collections) != len(set(collections)) or type(capabilities['handoff_available']) is not bool:
        raise ValueError('Invalid capabilities')
    if value['capability_profile'] == 'current-node-no-kb' and (collections or capabilities['handoff_available']):
        raise ValueError('Current profile cannot advertise unimplemented capabilities')
    available = value['available_tools']
    if not isinstance(available, list) or any(not isinstance(t, str) or t not in spec['tools'] for t in available):
        raise ValueError('Invalid tool allowlist')
    if len(available) != len(set(available)) or value['images'] != []:
        raise ValueError('Invalid tools or unsupported images')
    return deepcopy(value)


def validate_prediction(result, task, spec, value):
    exact_keys(result, ['choice', 'probabilities'])
    keys = spec['actions'] if task == 'action' else spec['tools']
    probs = result['probabilities']
    if result['choice'] not in keys or not isinstance(probs, dict) or set(probs) != set(keys):
        raise ValueError('Invalid prediction labels')
    if any(type(p) not in (float, int) or not math.isfinite(p) or not 0 <= p <= 1 for p in probs.values()):
        raise ValueError('Invalid probabilities')
    if abs(sum(probs.values()) - 1) > 1e-5 or probs[result['choice']] != max(probs.values()):
        raise ValueError('Invalid probability distribution')
    if task == 'tool' and result['choice'] not in value['available_tools']:
        raise ValueError('Unavailable tool prediction')
    return result


class FixtureEngine:
    """A constant response, visibly marked as fixture; never a classifier score."""
    def __init__(self, spec, policy_hash, action, tool):
        if action not in spec['actions'] or tool not in spec['tools']:
            raise ValueError('Invalid fixture choice')
        self.spec, self.policy_hash, self.action, self.tool = spec, policy_hash, action, tool

    def metadata(self):
        return dict(protocolVersion=self.spec['protocolVersion'], policyHash=self.policy_hash,
                    fixture=True, model='constant-fixture-no-model', experimental=True)

    def predict(self, value, task):
        keys = self.spec['actions'] if task == 'action' else self.spec['tools']
        choice = self.action if task == 'action' else self.tool
        return dict(choice=choice, probabilities={key: float(key == choice) for key in keys})


def create_app(engine, token):
    from flask import Flask, jsonify, request
    if not isinstance(token, str) or not token or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('A nonempty local service token is required')
    spec, policy_hash = protocol()
    metadata = engine.metadata()
    if metadata.get('protocolVersion') != spec['protocolVersion'] or metadata.get('policyHash') != policy_hash:
        raise ValueError('Engine must explicitly bind the new protocol and policy')
    if type(metadata.get('fixture')) is not bool:
        raise ValueError('Engine must declare fixture status')
    # Fixed at startup; engine output may not overwrite the transport contract.
    metadata = {k: metadata.get(k) for k in ['fixture', 'model']}
    envelope = dict(protocolVersion=spec['protocolVersion'], policyHash=policy_hash, experimental=True, **metadata)
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 32768
    gate = threading.BoundedSemaphore(1)

    @app.before_request
    def authorize():
        supplied = request.headers.get('Authorization', '')
        if not supplied.isascii() or not hmac.compare_digest(supplied, 'Bearer ' + token):
            return jsonify(error='UNAUTHORIZED'), 401

    @app.get('/ready')
    @app.get('/health')
    def ready():
        return jsonify(ready=True, **envelope)

    @app.post('/decide')
    def decide():
        body = request.get_json(silent=True)
        try:
            exact_keys(body, ['protocolVersion', 'policyHash', 'task', 'input'])
        except ValueError:
            return jsonify(error='INVALID_REQUEST'), 400
        if body['protocolVersion'] != spec['protocolVersion'] or body['policyHash'] != policy_hash:
            return jsonify(error='PROTOCOL_MISMATCH'), 409
        if body['task'] not in ('action', 'tool'):
            return jsonify(error='INVALID_TASK'), 400
        try:
            value = validate_input(body['input'], spec)
            if body['task'] == 'tool' and (not value['state']['authenticated'] or not value['available_tools']):
                raise ValueError('No authenticated tool capability')
        except (ValueError, TypeError):
            return jsonify(error='INVALID_INPUT'), 400
        if not gate.acquire(blocking=False):
            return jsonify(error='BUSY'), 503
        try:
            started = time.perf_counter()
            prediction = engine.predict(value, body['task'])
            validate_prediction(prediction, body['task'], spec, value)
            return jsonify(**envelope, task=body['task'], prediction=prediction,
                           inferenceMs=round((time.perf_counter() - started) * 1000, 3))
        except Exception:
            return jsonify(error='INFERENCE_FAILED'), 503
        finally:
            gate.release()

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-action', required=True)
    parser.add_argument('--fixture-tool', default='queryMyApplications')
    parser.add_argument('--port', type=int, default=18766)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged valid port')
    token = os.environ.get('QWEN_DECISION_KEY', '')
    spec, policy_hash = protocol()
    engine = FixtureEngine(spec, policy_hash, args.fixture_action, args.fixture_tool)
    app = create_app(engine, token)
    from waitress import serve
    print(json.dumps(dict(ready=True, port=args.port, **engine.metadata())), flush=True)
    serve(app, host='127.0.0.1', port=args.port, threads=4, connection_limit=32, channel_timeout=30)


if __name__ == '__main__':
    main()
