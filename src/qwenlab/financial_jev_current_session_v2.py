"""Bounded current-protocol Jev development evaluation; never retries a request."""
import argparse
import json
import os
import time
import urllib.request
from copy import deepcopy
from pathlib import Path

from qwenlab import financial_jev_reference as io
from qwenlab import financial_service_v2_metrics as metrics
from qwenlab.financial_prompt_v2 import SPEC, POLICY_HASH
from qwenlab.financial_serve_v2 import validate_input

ROOT = io.ROOT
OUT = ROOT / 'results/financial-jev-current-session-v2'
PUBLIC = ROOT / 'docs/evidence/financial-jev-current-session-v2'
DATA = ROOT / 'data/financial-service-v2/development.json'
PROXY = "http://127.0.0.1:7890"
MAX_REQUESTS = 256
MAX_TOKENS = 500000
SOURCES = ['src/qwenlab/financial_jev_current_session_v2.py', 'src/qwenlab/financial_jev_reference.py',
           'src/qwenlab/financial_service_v2_metrics.py', 'src/qwenlab/financial_actions_metrics.py',
           'src/qwenlab/financial_prompt_v2.py', 'src/qwenlab/financial_serve_v2.py',
           'src/qwenlab/financial_pilot.py', 'configs/support-financial-v2.json']


def payload(row, task):
    if task not in ('action', 'tool'):
        raise ValueError('Unknown task')
    value = validate_input(deepcopy(row['input']), SPEC)
    if value['images']:
        raise ValueError('Text-only evaluation')
    value['available_tools'] = sorted(value['available_tools'])
    value['capabilities']['knowledge_collections'] = sorted(value['capabilities']['knowledge_collections'])
    return dict(model='jev-latest', state=dict(policy=SPEC['policy'], input=value),
                questions={task: dict(type='choice', **SPEC['questions'][task])})


def source_rows():
    rows = io.read(DATA)
    if len(rows) != 128 or len({r['id'] for r in rows}) != 128 or any(r['split'] != 'development' for r in rows):
        raise ValueError('Only the frozen 128-row development split is allowed')
    for row in rows:
        for task in ('action', 'tool'):
            payload(row, task)
    return rows


def freeze():
    rows = source_rows()
    protocol = dict(version='financial-jev-current-session-v2', endpoint=io.ENDPOINT,
                    transport=dict(proxy=PROXY, client="requests.Session with connection pooling", automatic_transport_retries=0, direct_fallback=False, tls_verification=True,
                                   authorization='User explicitly requested port 7890 after direct HTTP451 failures; preserve old ledger'),
                    model='jev-latest', model_policy='pin first disclosed resolved model; stop on drift',
                    specification=SPEC, policy_sha256=POLICY_HASH,
                    dataset_sha256=io.file_sha(DATA), rows=128,
                    requests={r['id']: {t: io.digest(payload(r, t)) for t in ('action', 'tool')} for r in rows},
                    source_sha256={p: io.file_sha(ROOT / p) for p in SOURCES},
                    max_requests=MAX_REQUESTS, max_reported_input_tokens=MAX_TOKENS, retries=0,
                    call_strategy='action, then tool only when predicted action is tool; no gold routing or backend guards',
                    timing='sum of serial HTTP request durations per sample, including network; no backend/load/answer generation',
                    response_policy='Preserve provider choice; flag non-argmax responses and report strict-failure metrics separately; never retry a returned answer for quality',
                    official_response_reference='https://docs.typesafe.ai/primitives/choice',
                    evaluation_only=True, training_allowed=False, calibration_or_final_read=False)
    path = OUT / 'protocol.json'
    if path.exists() and io.read(path) != protocol:
        raise ValueError('Frozen protocol changed; do not reuse paid cache')
    if not path.exists():
        io.write(path, protocol)
    return rows, protocol


def normalized_answer(body, task, pinned):
    if body.get('model') != pinned:
        raise ValueError('Resolved model changed')
    keys = SPEC['actions' if task == 'action' else 'tools']
    answer = io.validate_answer(body['answers'][task], keys)
    answer['choice_probability_consistent'] = answer['probabilities'][answer['choice']] >= max(answer['probabilities'].values()) - 1e-6
    # Preserve vendor choice; report contract violations separately, never redraw an answer.
    return answer


def scan_ledger(rows):
    allowed = {f'{r["id"]}-{t}.json': io.digest(payload(r, t)) for r in rows for t in ('action', 'tool')}
    tokens = 0
    paths = list((OUT / 'requests').glob('*.json'))
    if len(paths) > MAX_REQUESTS:
        raise ValueError('Request count exceeded')
    for path in paths:
        if path.name not in allowed:
            raise ValueError('Unknown cached request')
        record = io.use_cached(path, allowed[path.name])
        n = (record['body'].get('usage') or {}).get('input_tokens')
        if type(n) is not int or n < 0:
            raise ValueError('Missing usage; stop without retry')
        tokens += n
    return len(paths), tokens


def evaluate_offline(rows, protocol):
    count, tokens = scan_ledger(rows)
    pinned = io.read(OUT / 'resolved-model.json')['model']
    predictions = []
    for row in rows:
        calls = []
        for task in ('action', 'tool'):
            if task == 'tool' and action['choice'] != 'tool':
                break
            request = payload(row, task)
            record = io.use_cached(OUT / 'requests' / f'{row["id"]}-{task}.json', io.digest(request))
            if record is None:
                raise ValueError('Incomplete development cache')
            answer = normalized_answer(record['body'], task, pinned)
            if task == 'action': action = answer
            else: tool = answer
            calls.append(record)
        predictions.append(dict(id=row['id'], split='development', action=action['choice'],
            tool_name=tool['choice'] if action['choice'] == 'tool' else None,
            action_prediction=action, tool_prediction=tool if action['choice'] == 'tool' else None,
            argument_source=None, model=pinned, elapsed_s=sum(r['elapsed_s'] for r in calls),
            input_tokens=sum(r['body']['usage']['input_tokens'] for r in calls),
            request_sha256=[r['request_sha256'] for r in calls]))
    if count != 128 + sum(p['action'] == 'tool' for p in predictions):
        raise ValueError('Unexpected calls outside conditional-tool path')
    # Vendor provides probabilities, not native logits. Do not fabricate logits.
    report = metrics.basic(rows, predictions, POLICY_HASH, io.digest(protocol))
    report['cohorts'] = {}
    for cohort in sorted({r['cohort'] for r in rows}):
        subset = [r for r in rows if r['cohort'] == cohort]; ids = {r['id'] for r in subset}
        report['cohorts'][cohort] = metrics.basic(subset, [p for p in predictions if p['id'] in ids], POLICY_HASH, io.digest(protocol))
    completion = dict(status='complete', model=pinned, rows=128, requests=count,
                      input_tokens=tokens, protocol_sha256=io.digest(protocol), retries=0,
                      calibration_or_final_read=False, training_allowed=False)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    artifacts = {'protocol.json': protocol, 'predictions.json': predictions,
                 'metrics.json': report, 'completion.json': completion}
    for name, value in artifacts.items():
        path = PUBLIC / name
        if path.exists() and io.read(path) != value:
            raise ValueError('Published cache changed: ' + name)
        io.write(path, value)
    io.write(PUBLIC / 'manifest.json', dict(files={n: io.file_sha(PUBLIC / n) for n in artifacts},
        training_allowed=False, scope='current development only; raw credential-free vendor responses kept locally'))
    io.write(OUT / 'completion.json', completion)
    io.write(OUT / 'status.json', dict(stage='complete', done=128, requests=count, updated_at=io.now()))
    return report, completion


class SessionOpener:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {'http': PROXY, 'https': PROXY}
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    def open(self, request, timeout):
        from io import BytesIO
        import urllib.error
        if request.full_url != io.ENDPOINT or request.get_method() != 'POST':
            raise ValueError('Only the fixed Jev endpoint is permitted')
        response = self.session.post(io.ENDPOINT, data=request.data,
            headers=dict(request.header_items()), timeout=(15, timeout), allow_redirects=False)
        if response.status_code != 200:
            raise urllib.error.HTTPError(io.ENDPOINT, response.status_code,
                'Non-success Jev HTTP status', response.headers, BytesIO(response.content))
        return BytesIO(response.content)


def proxy_opener():
    return SessionOpener()


def run():
    with io.exclusive_lock('financial-jev-current-session-v2.lock'):
        rows, protocol = freeze()
        if (OUT / 'completion.json').exists():
            evaluate_offline(rows, protocol)
            print('Already complete; zero API requests.', flush=True)
            return
        count, tokens = scan_ledger(rows)
        pin_path = OUT / 'resolved-model.json'
        pinned = io.read(pin_path)['model'] if pin_path.exists() else None
        key = (ROOT / '.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
        if not key or any(c.isspace() for c in key):
            raise ValueError('Invalid credential format')
        opener = proxy_opener()
        for index, row in enumerate(rows):
            for task in ('action', 'tool'):
                if task == 'tool' and action['choice'] != 'tool':
                    break
                request = payload(row, task); fingerprint = io.digest(request)
                path = OUT / 'requests' / f'{row["id"]}-{task}.json'
                record = io.use_cached(path, fingerprint)
                if record is None:
                    if count >= MAX_REQUESTS or tokens >= MAX_TOKENS:
                        raise RuntimeError('Fixed budget reached; no further requests')
                    record = dict(state='pending', id=row['id'], task=task,
                                  request_sha256=fingerprint, started_at=io.now(), attempts=1)
                    io.write(path, record)  # Commit before any possibly billable send.
                    req = urllib.request.Request(io.ENDPOINT, data=json.dumps(request, ensure_ascii=False).encode(),
                        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
                    start = time.perf_counter()
                    try:
                        with opener.open(req, timeout=45) as response:
                            body = json.load(response)
                        record.update(state='returned', body=body, elapsed_s=time.perf_counter() - start)
                        io.write(path, record)
                    except Exception as exc:
                        record.update(state='failed_or_uncertain', error=type(exc).__name__,
                                      http_status=getattr(exc, 'code', None), elapsed_s=time.perf_counter() - start)
                        io.write(path, record)
                        io.write(OUT / 'status.json', dict(stage='stopped_on_error', done=index,
                            id=row['id'], task=task, error=type(exc).__name__,
                            http_status=getattr(exc, 'code', None), retries=0, updated_at=io.now()))
                        raise RuntimeError('Stopped; request ledger preserved; no automatic retry') from None
                    count += 1
                    n = (body.get('usage') or {}).get('input_tokens')
                    if type(n) is not int or n < 0:
                        raise ValueError('Missing usage; stop without retry')
                    tokens += n
                if pinned is None:
                    pinned = record['body'].get('model')
                    if not isinstance(pinned, str) or not pinned.startswith('jev-') or pinned in ('jev-latest', 'jev-preview'):
                        raise ValueError('Concrete vendor model version required')
                    io.write(pin_path, dict(model=pinned, first_request_sha256=fingerprint))
                answer = normalized_answer(record['body'], task, pinned)
                if task == 'action': action = answer
            if (index + 1) % 16 == 0 or index == 127:
                io.write(OUT / 'status.json', dict(stage='running', done=index + 1, total=128,
                    requests=count, input_tokens=tokens, model=pinned, updated_at=io.now()))
                print(f'{index + 1}/128 samples; {count} requests; {tokens} input tokens', flush=True)
        report, completion = evaluate_offline(rows, protocol)
        print(json.dumps(dict(completion=completion, accuracy=report['action_accuracy'],
                              joint_tool=report['action_tool_joint_accuracy'], latency=report['latency']), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'audit', 'progress'))
    args = parser.parse_args()
    if args.command == 'prepare':
        freeze(); print('Prepared development-only reference; maximum 256 requests; zero requests made.')
    elif args.command == 'run': run()
    elif args.command == 'audit':
        report, completion = evaluate_offline(*freeze())
        print(json.dumps(dict(completion=completion, accuracy=report['action_accuracy']), indent=2))
    else:
        print(json.dumps(io.read(OUT / 'status.json') if (OUT / 'status.json').exists() else {'stage': 'not_started'}, indent=2))


if __name__ == '__main__':
    main()
