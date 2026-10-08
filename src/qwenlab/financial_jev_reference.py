"""One bounded, durable vendor reference. Never imported by training.

One call per evaluation input, two independent questions, tool ignored unless
predicted action is tool. An uncertain/failed request is NEVER auto-retried.
Final labels are not scored here. No caller-supplied endpoint or credentials log.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.request

from qwenlab.common import ROOT
from qwenlab.financial_pilot import visible_input
from qwenlab import financial_actions_prompt as prompt
from qwenlab.joint_v5 import exclusive_lock

OUT = ROOT / 'results/financial-jev-reference-v1'
DATA = ROOT / 'data/financial-eight-actions-v2'
SPLITS = {'development': 384, 'calibration': 256, 'final': 512}
ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
SOURCES = ['src/qwenlab/financial_jev_reference.py', 'src/qwenlab/financial_actions_prompt.py',
           'src/qwenlab/financial_pilot.py']
MAX_REQUESTS = 1152
MAX_REPORTED_INPUT_TOKENS = 2_000_000


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    """Durable replace: a pending record is persisted BEFORE a billable call."""
    import os
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.pending-write')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)


def specification():
    return {'policy': prompt.POLICY, 'questions': {
        'action': {'type': 'choice', 'instructions': '选择下一步业务动作。',
                   'criteria': prompt.ACTION_DESCRIPTIONS},
        'tool': {'type': 'choice',
                 'instructions': '假设下一步动作是查询，选择所需的一个可用工具；仍由后端校验身份和参数。此问题独立作答，非查询动作时此输出会被程序丢弃。',
                 'criteria': prompt.TOOL_DESCRIPTIONS}}}


def payload(row):
    value = visible_input(row)
    if value['images']:
        raise ValueError('Text-only reference')
    spec = specification()
    return {'model': 'jev-latest', 'state': {'policy': spec['policy'], 'input': value},
            'questions': spec['questions']}


def source_rows(split):
    if split not in SPLITS:
        raise ValueError('Unknown evaluation split')
    rows = read(DATA / f'evaluation/{split}.json')
    if len(rows) != SPLITS[split] or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Frozen split population mismatch')
    if any(r['split'] != split for r in rows):
        raise ValueError('Mixed evaluation partitions')
    return rows


def freeze():
    sources = {p: hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
               for p in SOURCES}
    protocol = dict(version='financial-jev-reference-v1', endpoint=ENDPOINT,
        requested_model='jev-latest', resolved_model_policy='pin first successful response; reject drift',
        specification=specification(), source_hashes=sources,
        dataset_manifest_sha256=file_sha(DATA/'manifest.json'),
        split_sha256={s:file_sha(DATA/f'evaluation/{s}.json') for s in SPLITS},
        split_rows=SPLITS, max_requests=MAX_REQUESTS,
        max_reported_input_tokens=MAX_REPORTED_INPUT_TOKENS, retries=0,
        evaluation_only=True, training_allowed=False,
        final_scoring='cached predictions only until an independently qualified fixed candidate',
        timing='one serial HTTPS request, two parallel questions; includes network, excludes backend',
        price_estimate=dict(input_usd_per_million=0.042, output_usd_per_million=0,
            source='https://typesafe.ai/blog/introducing-system-one-models-and-jev', checked='2026-10-02'))
    path = OUT/'protocol.json'
    if path.exists() and read(path) != protocol:
        raise ValueError('Reference protocol changed; do not overwrite/reuse cache')
    if not path.exists():
        write(path, protocol)
    return protocol


def validate_answer(answer, keys):
    probs = answer['probabilities']
    if set(probs) != set(keys) or answer['choice'] not in probs:
        raise ValueError('Invalid choice keys')
    if any(isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x)
           or not 0 <= x <= 1 for x in probs.values()) or abs(sum(probs.values())-1) > .03:
        raise ValueError('Invalid probability distribution')
    return dict(choice=answer['choice'], probabilities=probs, provider_confidence=answer.get('confidence'))


def normalize(row_id, split, body, elapsed, request_hash, model):
    if not isinstance(body.get('model'), str) or body['model'] != model:
        raise ValueError('Resolved vendor model changed')
    a = validate_answer(body['answers']['action'], prompt.ACTIONS)
    t = validate_answer(body['answers']['tool'], prompt.TOOLS)
    return dict(id=row_id, split=split, request_sha256=request_hash, model=model,
        action=a['choice'], tool_name=t['choice'] if a['choice']=='tool' else None,
        action_prediction=a, raw_tool_prediction=t, argument_source=None,
        elapsed_s=elapsed, usage=body.get('usage'), measured_at=now())


def use_cached(path, request_hash):
    if not path.exists():
        return None
    record = read(path)
    if record.get('request_sha256') != request_hash:
        raise ValueError('Request fingerprint changed')
    if record.get('state') != 'returned':
        raise RuntimeError('Uncertain/failed request exists; NO automatic API retry')
    return record


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def run():
    with exclusive_lock('financial-jev-reference-v1.lock'):
        protocol = freeze()
        if (OUT/'completion.json').exists():
            print('Reference already complete; zero API calls.', flush=True)
            return
        # Validate every split and request BEFORE credentials or paid calls.
        work = [(split,row,payload(row)) for split in SPLITS for row in source_rows(split)]
        if len(work) != MAX_REQUESTS:
            raise ValueError('Unexpected API budget')
        for split,row,request in work:
            use_cached(OUT/'requests'/split/(row['id']+'.json'),digest(request))
        key = (ROOT/'.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
        if not key or any(c.isspace() for c in key):
            raise ValueError('Invalid credential format')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        pin_path = OUT/'resolved-model.json'
        pinned = read(pin_path)['model'] if pin_path.exists() else None
        count = total_tokens = 0
        for split,row,request in work:
            path = OUT/'requests'/split/(row['id']+'.json')
            request_hash = digest(request)
            record = use_cached(path,request_hash)
            if record is None:
                if total_tokens >= MAX_REPORTED_INPUT_TOKENS:
                    raise RuntimeError('Reported token budget reached')
                record = dict(state='pending', id=row['id'], split=split,
                    request_sha256=request_hash, started_at=now(), attempts=1)
                write(path,record)
                req = urllib.request.Request(ENDPOINT, data=json.dumps(request,ensure_ascii=False).encode(),
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
                start = time.perf_counter()
                try:
                    with opener.open(req,timeout=45) as response:
                        body = json.load(response)
                    record.update(state='returned', body=body, elapsed_s=time.perf_counter()-start, returned_at=now())
                    write(path,record)  # Preserve billable response even if subsequent validation fails.
                except Exception as exc:
                    record.update(state='failed_or_uncertain',error=type(exc).__name__,
                                  http_status=getattr(exc,'code',None),elapsed_s=time.perf_counter()-start)
                    write(path,record)
                    write(OUT/'status.json',dict(stage='stopped_on_error',done=count,total=MAX_REQUESTS,
                        id=row['id'],error=type(exc).__name__,http_status=getattr(exc,'code',None),updated_at=now(),retries=0))
                    raise RuntimeError('API stopped; sanitized request ledger saved; no retry') from None
            model = record['body'].get('model')
            if pinned is None:
                if not isinstance(model,str) or not model.startswith('jev-') or model in ['jev-latest','jev-preview']:
                    raise ValueError('Server did not disclose a concrete model version')
                pinned = model
                write(pin_path,dict(model=pinned,first_request_sha256=request_hash))
            result = normalize(row['id'],split,record['body'],record['elapsed_s'],request_hash,pinned)
            prediction_path = OUT/split/(row['id']+'.json')
            if not prediction_path.exists():
                write(prediction_path,result)
            else:
                stored=read(prediction_path)
                # Original timestamp is immutable; reconstructing never restamps it.
                result['measured_at']=stored['measured_at']
                if stored != result:raise ValueError('Cached normalized prediction changed')
            usage=result['usage'] or {}
            n=usage.get('input_tokens')
            if type(n) is not int or n<0:raise ValueError('Missing measured usage; stop to protect budget')
            total_tokens += n;count += 1
            if count%16==0 or count==MAX_REQUESTS:
                write(OUT/'status.json',dict(stage='running',done=count,total=MAX_REQUESTS,split=split,
                    input_tokens=total_tokens,updated_at=now(),resolved_model=pinned,retries=0))
                print(count,'/',MAX_REQUESTS,split,'tokens',total_tokens,flush=True)
        # Do not expose final scores; export provider predictions without gold labels.
        for split in SPLITS:
            predictions=[read(OUT/split/(row['id']+'.json')) for row in source_rows(split)]
            write(OUT/(split+'-predictions.json'),predictions)
        write(OUT/'completion.json',dict(status='complete',at=now(),requests=count,
            model=pinned,input_tokens=total_tokens,estimated_input_cost_usd=total_tokens*.042/1e6,
            protocol_sha256=digest(protocol),retries=0,final_scored=False,training_allowed=False))
        write(OUT/'status.json',dict(stage='complete',done=count,total=MAX_REQUESTS,updated_at=now()))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run','progress'])
    args=parser.parse_args()
    if args.command=='prepare':
        freeze();print('Frozen bounded reference:',MAX_REQUESTS,'maximum paid calls')
    elif args.command=='run':run()
    else:print(json.dumps(read(OUT/'status.json') if (OUT/'status.json').exists() else {'stage':'not_started'},indent=2))


if __name__=='__main__':
    main()
