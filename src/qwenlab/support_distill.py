"""Train-only V5 logit replay. Cached logits are bound to exact encoded candidates."""
from collections import Counter
import hashlib
import json
import math
import time

from qwenlab.common import append_json, load_json, sha
from qwenlab.joint_v4 import batch_logits
from qwenlab.joint_v5 import atomic_json, read_resumable_rows


def encoded_hash(example):
    payload = {key: example[key] for key in ('id', 'task', 'dataset', 'tokens', 'keys', 'ids')}
    # HuggingFace returns BatchEncoding (a Mapping), not a JSON-native dict.
    payload['tokens'] = dict(example['tokens'])
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def validate_record(record, example):
    if (record['id'], record['task'], record['encoded_sha256']) != (example['id'], example['task'], encoded_hash(example)):
        raise ValueError('Teacher input or candidate order changed')
    logits = record['logits']
    if len(logits) != len(example['keys']) or not all(math.isfinite(v) for v in logits):
        raise ValueError('Invalid teacher logits')


def distillation_loss(student, teacher, temperature):
    import torch
    if temperature <= 0:
        raise ValueError('Temperature must be positive')
    teacher = torch.as_tensor(teacher, device=student.device, dtype=torch.float32).detach()
    if student.shape != teacher.shape or not torch.isfinite(teacher).all():
        raise ValueError('Invalid teacher tensor')
    return torch.nn.functional.kl_div(
        torch.log_softmax(student.float() / temperature, dim=-1),
        torch.softmax(teacher / temperature, dim=-1), reduction='sum') * temperature**2


def cache_identity(targets, protocol_hash):
    return {'protocol_sha256': protocol_hash,
            'encoded_population_sha256': hashlib.sha256(''.join(encoded_hash(x) for x in targets).encode()).hexdigest(),
            'items': len(targets)}


def attach_teacher(tok, model, pools, cfg, folder, protocol_hash, status, checkpoint_exists=False):
    """Only called with the initial V5 model when building a new cache."""
    import torch
    targets = [x for name, pool in sorted(pools.items()) for x in pool if x.get('teacher_eligible')]
    spec = cfg['distillation']
    if len(targets) != spec['cache_expected_items']:
        raise ValueError('Unexpected teacher population')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/'logits.jsonl'
    manifest_path = folder/'manifest.json'
    identity = cache_identity(targets, protocol_hash)
    meta = load_json(manifest_path) if manifest_path.exists() else None
    if checkpoint_exists and meta is None:
        raise ValueError('A trained checkpoint must have an intact V5 teacher cache')
    identity_path = folder/'identity.json'
    if identity_path.exists():
        if load_json(identity_path) != identity:
            raise ValueError('Partial teacher cache protocol changed')
    elif path.exists() or meta:
        raise ValueError('Teacher cache lacks identity')
    else:
        atomic_json(identity_path, identity)
    if meta and (any(meta.get(k) != v for k,v in identity.items()) or sha(path) != meta['logits_sha256']):
        raise ValueError('Teacher cache integrity failed')
    done = read_resumable_rows(path)
    if len(done) > len(targets):
        raise ValueError('Teacher cache has extra rows')
    for record, example in zip(done, targets):
        validate_record(record, example)
    if meta and len(done) != len(targets):
        raise ValueError('Complete teacher cache is truncated')
    start = time.perf_counter()
    initial_count = len(done)
    model.eval()
    with torch.no_grad():
        for offset in range(initial_count, len(targets), spec['batch_size']):
            batch = targets[offset:offset+spec['batch_size']]
            scores = batch_logits(tok, model, batch)
            for example, score in zip(batch, scores):
                record = {'id': example['id'], 'task': example['task'],
                          'encoded_sha256': encoded_hash(example), 'logits': score.float().cpu().tolist()}
                validate_record(record, example)
                append_json(path, record)
                done.append(record)
            elapsed = time.perf_counter()-start
            status('teacher_cache', done=len(done), total=len(targets),
                   remaining_teacher_minutes=round(elapsed/(len(done)-initial_count)*(len(targets)-len(done))/60, 1),
                   eta_excludes_training_and_evaluation=True)
    if not meta:
        meta = dict(identity, logits_sha256=sha(path), tasks=dict(Counter(x['task'] for x in targets)),
                    teacher_gold_agreement={task: sum(max(range(len(r['logits'])), key=r['logits'].__getitem__)==x['target']
                        for r,x in zip(done,targets) if x['task']==task) for task in spec['tasks']},
                    training_inputs_only=True, includes_heldout=False)
        atomic_json(manifest_path, meta)
    for record, example in zip(done, targets):
        example['teacher_logits'] = record['logits']
    return meta


def training_coverage(rows):
    result = {}
    for origin in sorted({r['training_origin'] for r in rows}):
        part = [r for r in rows if r['training_origin']==origin]
        if any(r['split'] != 'train' for r in part):
            raise ValueError('Coverage accepts training rows only')
        result[origin] = {'rows':len(part), 'with_history':sum(bool(r.get('history')) for r in part),
                         'conditions':dict(Counter(r.get('condition','unspecified') for r in part)),
                         'history_by_condition':dict(Counter(r.get('condition','unspecified') for r in part if r.get('history'))),
                         'routes':dict(Counter(r['labels']['route'] for r in part))}
    return result
