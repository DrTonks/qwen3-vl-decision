"""Train-only business-state replay for a separately frozen support-v7 run."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
import random
import shutil
from qwenlab.common import ROOT, input_state, load_json, sha
from qwenlab import support_expansion as exp
from qwenlab.joint_v5 import atomic_json
from qwenlab.joint_v4 import metrics
from qwenlab.prepare_v2 import read_rows, write_rows


def stratified_replay(rows, count, seed):
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row['labels']['route'], row['labels']['intent'], row['condition'])].append(row)
    rng = random.Random(seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    chosen = []
    while len(chosen) < count and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(chosen) < count:
                chosen.append(buckets[key].pop())
    if len(chosen) != count:
        raise ValueError('Insufficient train-only state replay')
    return chosen


def input_key(row):
    return json.dumps(input_state(row), ensure_ascii=False, sort_keys=True)


def filter_replay(pool, heldouts, blocked_fingerprints, reviewed_train):
    held_groups = {r['group'] for r in heldouts}
    held_inputs = {input_key(r) for r in heldouts}
    reviewed_inputs = {input_key(r) for r in reviewed_train}
    seen = {}
    kept = []
    rejected = Counter()
    for row in pool:
        key = input_key(row)
        if row.get('split') != 'train':
            raise ValueError('Only original training rows may enter replay')
        if row['group'] in held_groups or key in held_inputs or exp.fingerprint(row['message']) in blocked_fingerprints:
            rejected['heldout_overlap'] += 1
            continue
        if key in reviewed_inputs:
            rejected['reviewed_train_duplicate'] += 1
            continue
        labels = {t: row['labels'][t] for t in ('intent','route','tool')}
        if key in seen:
            if seen[key] != labels:
                raise ValueError('Conflicting train-only replay labels')
            rejected['duplicate_replay_input'] += 1
            continue
        seen[key] = labels
        kept.append(row)
    return kept, dict(rejected)


def prepare_dataset(config_path, data_dir, out_dir, source_files):
    cfg = load_json(config_path)
    if not cfg['training_authorization']['confirmed']:
        raise PermissionError('Training is not authorized')
    reviewed = ROOT/cfg['reviewed_source']
    exp.check_frozen(reviewed)
    previous = ROOT/'data/processed/support-v6'
    previous_manifest = load_json(previous/'manifest.json')
    for name, item in previous_manifest['files'].items():
        if exp.base.digest(previous/name) != item['sha256']:
            raise ValueError('Frozen v6 prepared data changed: '+name)
    if not (data_dir/'manifest.json').exists():
        if data_dir.exists():
            raise FileExistsError('Incomplete prepared run; inspect before rebuilding')
        primary = read_rows(reviewed/'train-reviewed-only.jsonl')
        if len(primary) != 3901 or any(r['label_status'] != 'human_reviewed' for r in primary):
            raise ValueError('Human-reviewed source changed')
        train_path = ROOT/'data/processed/v5/business-train.jsonl'
        hashes = {cfg['reviewed_source']+'/manifest.json': exp.base.digest(reviewed/'manifest.json'),
                  'data/processed/support-v6/manifest.json': exp.base.digest(previous/'manifest.json'),
                  'data/processed/v5/business-train.jsonl': exp.base.digest(train_path)}
        fingerprints = set()
        for values in load_json(reviewed/'regression-fingerprints.json').values():
            fingerprints.update(values)
        heldouts = []
        for name in ('business','massive','crosswoz'):
            for split in ('dev','calibration','test'):
                path = ROOT/f'data/processed/v5/{name}-{split}.jsonl'
                values = read_rows(path)
                heldouts.extend(values)
                fingerprints.update(exp.fingerprint(r['message']) for r in values)
                hashes[path.relative_to(ROOT).as_posix()] = exp.base.digest(path)
        for name in exp.EVAL_FILES[3:]:
            values = read_rows(reviewed/name)
            heldouts.extend(values)
            fingerprints.update(exp.fingerprint(r['message']) for r in values)
        pool, rejected = filter_replay(read_rows(train_path), heldouts, fingerprints, primary)
        replay = stratified_replay(pool, cfg['legacy_replay_rows'], cfg['seed'])
        for row in primary:
            row['training_origin'] = 'reviewed_project'
        replay = deepcopy(replay)
        for row in replay:
            row['source_group'] = row['group']
            row['group'] = 'legacy-' + row['group']
            row['training_origin'] = 'legacy_state_replay'
            row['label_status'] = 'legacy_synthetic_replay_not_new_human_review'
        datasets = {'business-train.jsonl': primary+replay}
        for name in previous_manifest['files']:
            if name != 'business-train.jsonl':
                datasets[name] = read_rows(previous/name)
        if not {r['condition'] for r in pool} <= {r['condition'] for r in replay}:
            raise ValueError('Replay dropped an available condition')
        data_dir.mkdir(parents=True)
        for name, rows in datasets.items():
            write_rows(data_dir/name, rows)
        atomic_json(data_dir/'manifest.json', {
            'source_hashes': hashes,
            'files': {name:{'rows':len(rows),'sha256':exp.base.digest(data_dir/name)} for name,rows in datasets.items()},
            'reviewed_project_count': len(primary), 'legacy_replay_count':len(replay),
            'legacy_replay_condition_counts':dict(Counter(r['condition'] for r in replay)),
            'legacy_replay_route_counts':dict(Counter(r['labels']['route'] for r in replay)),
            'legacy_replay_intent_counts':dict(Counter(r['labels']['intent'] for r in replay)),
            'legacy_replay_group_count':len({r['group'] for r in replay}),
            'eligible_replay_pool_count':len(pool), 'replay_exclusions':rejected,
            'human_review_does_not_extend_to_replay':True,
            'selection_uses_development_only':True,
            'known_limitation':'Development errors informed broad condition coverage; exact de-duplication is not semantic independence'})
    manifest = load_json(data_dir/'manifest.json')
    for name, item in manifest['files'].items():
        if exp.base.digest(data_dir/name) != item['sha256']:
            raise ValueError('Frozen v7 data changed: '+name)
    for name, digest in manifest['source_hashes'].items():
        if exp.base.digest(ROOT/name) != digest:
            raise ValueError('Frozen replay source changed: '+name)
    adapter = ROOT/cfg['initial_adapter']
    cache = reference_cache(cfg, data_dir)
    protocol = {'config':cfg, 'prepared_manifest_sha256':exp.base.digest(data_dir/'manifest.json'),
        'source_hashes':{name:exp.base.digest(ROOT/name) for name in source_files},
        'initial_adapter_hashes':{name:sha(adapter/name) for name in ('adapter_model.safetensors','adapter_config.json')},
        'evaluation_batch':1, 'reviewed_project_rows':3901, 'legacy_replay_is_separately_attributed':True,
        'development_informed_adaptation':True, 'no_heldout_rows_used_as_training_supervision':True,
        'reference_reuse':cache}
    out_dir.mkdir(parents=True,exist_ok=True)
    if (out_dir/'protocol.json').exists() and load_json(out_dir/'protocol.json') != protocol:
        raise ValueError('Frozen v7 protocol changed; start a new experiment version')
    if not (out_dir/'protocol.json').exists():
        atomic_json(out_dir/'protocol.json',protocol)
        atomic_json(out_dir/'data-manifest.json',manifest)
    target = out_dir/'v5-reference'
    target.mkdir(exist_ok=True)
    for name, digest in cache['files_sha256'].items():
        if (target/name).exists():
            if exp.base.digest(target/name) != digest:
                raise ValueError('Reused reference prediction changed: '+name)
        else:
            shutil.copyfile(ROOT/'results/support-v6/v5-reference'/name, target/name)
    return cfg


def reference_cache(cfg, data_dir):
    """Reuse only identical-adapter, identical-input, identical-inference baselines."""
    previous = ROOT/'results/support-v6'
    protocol = load_json(previous/'protocol.json')
    for name, digest in protocol['initial_adapter_hashes'].items():
        if sha(ROOT/cfg['initial_adapter']/name) != digest:
            raise ValueError('Reference adapter changed')
    inference_sources = ['src/qwenlab/joint_v5.py','src/qwenlab/joint_v4.py',
        'src/qwenlab/modeling.py','src/qwenlab/common.py','configs/decision-v5.json',
        'data/processed/v2/massive-spec.json','data/processed/v2/crosswoz-spec.json']
    for name in inference_sources:
        if exp.base.digest(ROOT/name) != protocol['source_hashes'][name]:
            raise ValueError('Reference inference code/spec changed: '+name)
    hashes = {}
    for name in ('business','massive','crosswoz','legacy'):
        filename = name+'-dev.jsonl'
        if exp.base.digest(data_dir/filename) != exp.base.digest(ROOT/'data/processed/support-v6'/filename):
            raise ValueError('Reference development input changed')
        expected = read_rows(data_dir/filename)
        predictions = read_rows(previous/'v5-reference'/filename)
        if [(r['id'],r['labels']) for r in predictions] != [(r['id'],r['labels']) for r in expected]:
            raise ValueError('Reference prediction population mismatch')
        metric_file = name+'-dev-metrics.json'
        if metrics(predictions) != load_json(previous/'v5-reference'/metric_file):
            raise ValueError('Reference metric reconstruction mismatch')
        for file in (filename,metric_file):
            hashes[file] = exp.base.digest(previous/'v5-reference'/file)
    return {'source':'results/support-v6/v5-reference','batch':1,
            'source_protocol_sha256':exp.base.digest(previous/'protocol.json'),'files_sha256':hashes}
