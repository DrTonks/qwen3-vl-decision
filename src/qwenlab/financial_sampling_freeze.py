"""Freeze CPU-only exposure schedules and tokenizer accounting; never train.

Only the verified training pool is read as examples. No model class, adapter,
optimizer, evaluation corpus, training permission, or remote API is opened.
The manifest is the publication commit marker and is written last.
"""
import argparse
from collections import Counter
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform

from qwenlab.common import ROOT, sha
from qwenlab import financial_sampling_data as data
from qwenlab import financial_sampling_plan as sampler
from qwenlab import financial_prompt_v2 as prompt


CONFIG = ROOT / 'configs/financial-sampling-study-v1.json'
TOKENIZER = ROOT / 'models/Qwen3.5-0.8B'
OUT = ROOT / 'data/financial-sampling-study-v1/schedule-v1'
ARMS = ('uniform', 'stratified')
FILES = frozenset({'uniform-plan.json', 'stratified-plan.json',
                   'exposure-ledger.json', 'token-lengths.json', 'summary.json'})
MANIFEST_KEYS = {'version', 'status', 'training_enabled', 'training_eligible',
                 'deployment_enabled', 'model_weights_loaded', 'model_api_requests',
                 'sources', 'files', 'tokenizer', 'row_hash_format'}
ROW_HASH_FORMAT = 'sha256 of UTF-8 JSON, ensure_ascii=False, sort_keys=True, separators=(comma,colon)'
SOURCE_CODE = ('financial_sampling_data.py', 'financial_sampling_plan.py',
               'financial_sampling_freeze.py', 'common.py', 'financial_prompt_v2.py',
               'financial_serve_v2.py')
TOKENIZER_REQUIRED = frozenset({'config.json', 'tokenizer.json',
                               'tokenizer_config.json', 'chat_template.jinja'})
TOKENIZER_OPTIONAL = frozenset({'added_tokens.json', 'special_tokens_map.json',
                               'vocab.json', 'merges.txt', 'tokenizer.model'})


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def row_sha(row):
    raw = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def relative(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError('Dependency must remain inside repository')
    return resolved.relative_to(ROOT.resolve()).as_posix()


def check_config(config):
    """Version one has a fixed design; edits require a new reviewed version."""
    fixed = dict(version='financial-sampling-study-v1', status='design_cpu_preflight_only',
                 training_enabled=False, deployment_enabled=False, model_api_requests=0,
                 model='Qwen/Qwen3.5-0.8B', initial_adapter=None, seed=20261004,
                 sampling_seed=20261004, steps_per_arm=400, effective_batch=8,
                 micro_batch=2, gradient_accumulation=4, max_input_tokens=2048,
                 truncate=False, padding_side='left', arms=list(ARMS),
                 diagnostic_steps=[200], selection_steps=[400])
    for key, value in fixed.items():
        if config.get(key) != value or type(config.get(key)) is not type(value):
            raise ValueError(f'Unsupported frozen design field: {key}')
    if config.get('pool') != relative(data.OUT) or config.get('schedule_directory') != relative(OUT):
        raise ValueError('Study pool/schedule path differs from configured version')
    sampling = config.get('sampling', {})
    if (sampling.get('quotas_per_20') != sampler.QUOTAS
            or type(sampling.get('max_row_exposure')) is not int
            or sampling['max_row_exposure'] != 4
            or type(sampling.get('max_group_exposure')) is not int
            or sampling['max_group_exposure'] != 16):
        raise ValueError('Sampling quotas or hard exposure caps changed')
    loss = config.get('loss', {})
    if loss.get('action_weight') != 1.0 or loss.get('tool_weight') != 0.75:
        raise ValueError('Supervision weights changed')
    return config


def tokenizer_files():
    paths = []
    for name in sorted(TOKENIZER_REQUIRED | TOKENIZER_OPTIONAL):
        path = TOKENIZER / name
        if name in TOKENIZER_REQUIRED and not path.is_file():
            raise ValueError(f'Missing local tokenizer dependency: {name}')
        if path.is_file():
            relative(path)
            paths.append(path)
    extra = TOKENIZER / 'chat_templates'
    if extra.exists():
        paths.extend(sorted(extra.glob('*.jinja')))
    for path in paths:
        relative(path)
    return paths


def source_bindings():
    paths = [CONFIG, data.OUT / 'manifest.json', data.OUT / 'train.json',
             ROOT / 'configs/support-financial-v2.json', ROOT / 'requirements-qwen35.txt']
    if sha(ROOT / 'configs/support-financial-v2.json') != prompt.POLICY_HASH:
        raise ValueError('Imported prompt policy no longer matches on-disk policy')
    paths += [ROOT / 'src/qwenlab' / name for name in SOURCE_CODE]
    paths += tokenizer_files()
    # The pool verifier independently checks its full transitive closure. Bind
    # that manifest and each listed dependency hash here as well; hashing does
    # not parse or expose any protected evaluation text.
    pool_manifest = read(data.OUT / 'manifest.json')
    paths += [ROOT / name for name in pool_manifest['sources']]
    return {relative(path): sha(path) for path in sorted(set(paths), key=str)}


def runtime_versions():
    return dict(python=platform.python_version(), python_implementation=platform.python_implementation(),
                **{name: metadata.version(name) for name in
                   ('transformers', 'tokenizers', 'jinja2', 'huggingface-hub')})


def local_tokenizer():
    from transformers import AutoTokenizer
    result = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True,
                                           trust_remote_code=False)
    result.padding_side = 'left'
    return result


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Expected nonempty verified training pool')
    ids = set()
    for row in rows:
        if row.get('split') != 'train' or row.get('training_eligible') is not False:
            raise ValueError('Only design-only training-pool rows are accepted')
        rid = row.get('id')
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError('Pool IDs must be unique nonempty strings')
        ids.add(rid)
        if not isinstance(row.get('scene_family_id'), str) or not row['scene_family_id']:
            raise ValueError('Pool source group missing')
        sampler.layer_of(row)
    return {r['id']: r for r in rows}


def build_plans(rows, config):
    validate_rows(rows)
    if len(rows) < config['steps_per_arm'] * config['effective_batch']:
        raise ValueError('Uniform arm must draw without replacement from at least 3200 rows')
    plans = {arm: sampler.plan(rows, arm, config['sampling_seed'],
                              config['steps_per_arm'], config['effective_batch'],
                              max_row_exposure=config['sampling']['max_row_exposure'],
                              max_group_exposure=config['sampling']['max_group_exposure'])
             for arm in ARMS}
    if plans['uniform']['coverage']['row']['max_exposure'] != 1:
        raise ValueError('Uniform arm unexpectedly repeats a row')
    return plans


def build_ledger(rows, plans, micro_batch):
    indexed = validate_rows(rows)
    ledger = {}
    hashes = {rid: row_sha(row) for rid, row in indexed.items()}
    for arm in ARMS:
        counts = Counter()
        records = []
        for step, members in enumerate(plans[arm]['step_rows'], 1):
            if len(members) % micro_batch:
                raise ValueError('Partial microbatch in fixed schedule')
            for offset, rid in enumerate(members):
                row = indexed[rid]
                counts[rid] += 1
                records.append(dict(exposure_index=len(records) + 1, step=step,
                                    microbatch=offset // micro_batch + 1,
                                    position=offset % micro_batch + 1,
                                    effective_batch_position=offset + 1,
                                    row_id=rid, row_sha256=hashes[rid],
                                    group=row['scene_family_id'], layer=sampler.layer_of(row),
                                    occurrence=counts[rid]))
        ledger[arm] = records
    return dict(version='financial-exposure-ledger-v1', index_base=1,
                occurrence_scope='within_arm_in_exposure_order',
                microbatch_scope='within_optimizer_step', arms=ledger)


def token_lengths(rows, tokenizer, max_tokens=2048):
    """Encode every action and every supervised true-tool prompt, without truncation."""
    validate_rows(rows)
    records = []
    for row in sorted(rows, key=lambda r: r['id']):
        lengths = {}
        for task in ('action', 'tool'):
            if task == 'tool' and row['annotation']['action'] != 'tool':
                lengths['tool_input_tokens'] = None
                continue
            encoded = prompt.encode(tokenizer, row, task=task, max_tokens=max_tokens)
            size = len(encoded['tokens']['input_ids'])
            if type(size) is not int or not 0 < size <= max_tokens:
                raise ValueError('Invalid tokenizer length; truncation is forbidden')
            lengths[task + '_input_tokens'] = size
        records.append(dict(row_id=row['id'], row_sha256=row_sha(row), **lengths))
    return dict(version='financial-pool-token-lengths-v1', max_input_tokens=max_tokens,
                truncated=False, scope='all_action_and_true_tool_prompts',
                tool_supervision='true_tool_rows_only', rows=records)


def validate_lengths(rows, lengths, max_tokens):
    if (set(lengths) != {'version', 'max_input_tokens', 'truncated', 'scope', 'tool_supervision', 'rows'}
            or lengths['version'] != 'financial-pool-token-lengths-v1'
            or lengths['max_input_tokens'] != max_tokens or lengths['truncated'] is not False
            or lengths['scope'] != 'all_action_and_true_tool_prompts'
            or lengths['tool_supervision'] != 'true_tool_rows_only'):
        raise ValueError('Invalid token-length inventory')
    indexed = validate_rows(rows)
    records = lengths['rows']
    if not isinstance(records, list) or [r.get('row_id') for r in records] != sorted(indexed):
        raise ValueError('Token lengths must cover the entire pool exactly once in ID order')
    for record in records:
        if set(record) != {'row_id', 'row_sha256', 'action_input_tokens', 'tool_input_tokens'}:
            raise ValueError('Invalid token row keys')
        if record['row_sha256'] != row_sha(indexed[record['row_id']]):
            raise ValueError('Token row SHA is stale')
        for key in ('action_input_tokens', 'tool_input_tokens'):
            if key == 'tool_input_tokens' and indexed[record['row_id']]['annotation']['action'] != 'tool':
                if record[key] is not None:
                    raise ValueError('Non-tool rows must not have tool-token supervision')
                continue
            if type(record[key]) is not int or not 0 < record[key] <= max_tokens:
                raise ValueError('Invalid/overlength untruncated input')
    return {r['row_id']: r for r in records}


def arm_summary(records, indexed, lengths, micro_batch):
    row_counts = Counter(r['row_id'] for r in records)
    group_counts = Counter(r['group'] for r in records)
    actions = Counter(indexed[r['row_id']]['annotation']['action'] for r in records)
    tools = Counter(indexed[r['row_id']]['annotation']['tool_name'] for r in records
                    if indexed[r['row_id']]['annotation']['action'] == 'tool')
    action_raw = tool_raw = action_padded = tool_padded = 0
    maximum = dict(action=0, tool=0)
    tool_microbatches = 0
    for start in range(0, len(records), micro_batch):
        block = records[start:start + micro_batch]
        if len(block) != micro_batch or len({(r['step'], r['microbatch']) for r in block}) != 1:
            raise ValueError('Ledger microbatch boundaries are inconsistent')
        action_sizes = [lengths[r['row_id']]['action_input_tokens'] for r in block]
        tool_sizes = [lengths[r['row_id']]['tool_input_tokens'] for r in block
                      if indexed[r['row_id']]['annotation']['action'] == 'tool']
        action_raw += sum(action_sizes)
        action_padded += len(action_sizes) * max(action_sizes)
        maximum['action'] = max(maximum['action'], max(action_sizes))
        if tool_sizes:
            tool_microbatches += 1
            tool_raw += sum(tool_sizes)
            tool_padded += len(tool_sizes) * max(tool_sizes)
            maximum['tool'] = max(maximum['tool'], max(tool_sizes))
    n, t = len(records), sum(tools.values())
    return dict(steps=max((r['step'] for r in records), default=0), original_row_exposures=n,
                true_tool_exposures=t, supervised_tasks=n + t,
                supervised_weight=n + 0.75 * t,
                unique_rows=len(row_counts), unique_groups=len(group_counts),
                repeated_row_exposures=n - len(row_counts),
                rows_seen_more_than_once=sum(c > 1 for c in row_counts.values()),
                max_row_exposure=max(row_counts.values(), default=0),
                max_group_exposure=max(group_counts.values(), default=0),
                layer_counts=dict(sorted(Counter(r['layer'] for r in records).items())),
                action_counts=dict(sorted(actions.items())), tool_counts=dict(sorted(tools.items())),
                action_microbatches=n // micro_batch, nonempty_tool_microbatches=tool_microbatches,
                raw_input_tokens=dict(action=action_raw, tool=tool_raw, total=action_raw + tool_raw),
                padded_input_tokens=dict(action=action_padded, tool=tool_padded,
                                         total=action_padded + tool_padded),
                max_input_tokens=maximum)


def build_summary(rows, ledger, lengths, config):
    indexed = validate_rows(rows)
    sizes = validate_lengths(rows, lengths, config['max_input_tokens'])
    arms = {}
    for arm in ARMS:
        records = ledger['arms'][arm]
        arms[arm] = {
            'prefix_200': arm_summary([r for r in records if r['step'] <= 200], indexed, sizes, config['micro_batch']),
            'full_400': arm_summary(records, indexed, sizes, config['micro_batch']),
        }
    return dict(version='financial-sampling-accounting-v1', training_enabled=False,
                training_eligible=False, model_weights_loaded=False, model_api_requests=0,
                pool_rows=len(rows), pool_groups=len({r['scene_family_id'] for r in rows}),
                pool_max_input_tokens={task: max((r[task + '_input_tokens'] for r in sizes.values()
                                                 if r[task + '_input_tokens'] is not None), default=0)
                                       for task in ('action', 'tool')},
                token_accounting='input tokens only; action and true-tool prompts padded separately to their maximum within each original two-row microbatch; no cross-microbatch tool repacking',
                supervision_formula='N + T tasks; N + 0.75*T weight; N original row exposures, T true-tool exposures',
                interpretation='joint layer allocation, source-group weighting and repetition; not equal FLOPs or isolated quota effect',
                arms=arms)


def calculate(rows, config, tokenizer):
    plans = build_plans(rows, config)
    ledger = build_ledger(rows, plans, config['micro_batch'])
    lengths = token_lengths(rows, tokenizer, config['max_input_tokens'])
    return {'uniform-plan.json': plans['uniform'], 'stratified-plan.json': plans['stratified'],
            'exposure-ledger.json': ledger, 'token-lengths.json': lengths,
            'summary.json': build_summary(rows, ledger, lengths, config)}


def prepare():
    if OUT.exists():
        raise FileExistsError('Preserve existing immutable schedule directory')
    config = check_config(read(CONFIG))
    before = source_bindings()
    rows = data.verify()
    versions = runtime_versions()
    values = calculate(rows, config, local_tokenizer())
    if before != source_bindings():
        raise ValueError('Sources changed while computing schedules; no publication')
    payloads = {name: json_bytes(values[name]) for name in sorted(FILES)}
    manifest = dict(version='financial-sampling-freeze-v1', status='design_cpu_preflight_only',
                    training_enabled=False, training_eligible=False, deployment_enabled=False,
                    model_weights_loaded=False, model_api_requests=0, sources=before,
                    files={name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()},
                    tokenizer=dict(path=relative(TOKENIZER), local_files_only=True,
                                   trust_remote_code=False, padding_side='left', runtime=versions),
                    row_hash_format=ROW_HASH_FORMAT)
    # All calculations have completed. Directory creation is exclusive, and
    # every file is also opened exclusively; a partial I/O failure has no valid
    # manifest and can never be mistaken for a frozen schedule.
    OUT.mkdir(parents=True, exist_ok=False)
    for name, raw in payloads.items():
        with (OUT / name).open('xb') as stream:
            stream.write(raw)
    if before != source_bindings():
        raise ValueError('Sources changed during publication; manifest withheld')
    with (OUT / 'manifest.json').open('xb') as stream:
        stream.write(json_bytes(manifest))
    return values['summary.json']


def verify(tokenize=False):
    manifest = read(OUT / 'manifest.json')
    if set(manifest) != MANIFEST_KEYS or manifest['version'] != 'financial-sampling-freeze-v1':
        raise ValueError('Incomplete schedule manifest')
    if (manifest['status'] != 'design_cpu_preflight_only'
            or any(manifest[k] is not False for k in ('training_enabled', 'training_eligible',
                                                     'deployment_enabled', 'model_weights_loaded'))
            or type(manifest['model_api_requests']) is not int or manifest['model_api_requests'] != 0
            or manifest['row_hash_format'] != ROW_HASH_FORMAT):
        raise ValueError('Frozen schedules cannot enable execution')
    if set(manifest['files']) != FILES or {p.name for p in OUT.iterdir()} != FILES | {'manifest.json'}:
        raise ValueError('Schedule output inventory differs')
    before = source_bindings()
    if manifest['sources'] != before:
        raise ValueError('Source dependency closure changed')
    for name in FILES:
        if sha(OUT / name) != manifest['files'][name]:
            raise ValueError(f'Schedule output changed: {name}')
    expected_tokenizer = dict(path=relative(TOKENIZER), local_files_only=True,
                              trust_remote_code=False, padding_side='left', runtime=runtime_versions())
    if manifest['tokenizer'] != expected_tokenizer:
        raise ValueError('Tokenizer runtime or preparation changed')
    config = check_config(read(CONFIG))
    rows = data.verify()
    plans = build_plans(rows, config)
    ledger = build_ledger(rows, plans, config['micro_batch'])
    for arm in ARMS:
        if plans[arm] != read(OUT / f'{arm}-plan.json'):
            raise ValueError('Schedule replay differs')
    if ledger != read(OUT / 'exposure-ledger.json'):
        raise ValueError('Exposure ledger replay differs')
    lengths = read(OUT / 'token-lengths.json')
    validate_lengths(rows, lengths, config['max_input_tokens'])
    if tokenize and lengths != token_lengths(rows, local_tokenizer(), config['max_input_tokens']):
        raise ValueError('Actual tokenizer replay differs')
    summary = build_summary(rows, ledger, lengths, config)
    if summary != read(OUT / 'summary.json'):
        raise ValueError('Exposure/token summary replay differs')
    if before != source_bindings():
        raise ValueError('Sources changed during verification')
    return dict(status='verified', tokenizer_replayed=bool(tokenize), rows=len(rows),
                arms=list(ARMS), exposures_per_arm=3200, training_enabled=False,
                model_weights_loaded=False, model_api_requests=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('--tokenize', action='store_true', help='Replay actual local tokenization when verifying')
    args = parser.parse_args(argv)
    if args.command == 'prepare' and args.tokenize:
        parser.error('prepare always tokenizes; --tokenize is for verify')
    result = prepare() if args.command == 'prepare' else verify(args.tokenize)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
