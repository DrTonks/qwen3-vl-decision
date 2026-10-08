"""Blind screen using all prior protected corpora plus the latest training pool.

Only match flags for NEW candidate IDs are printed, never old texts or labels.
The old index stays frozen. Extra coverage is persisted in a separate index.
"""
import importlib.util
import json
from pathlib import Path

from qwenlab.common import ROOT, sha
from qwenlab.financial_state_pair_candidates import DATA, encoded, read, verify, DEFAULT_BACKEND


def main():
    verify(DATA/'build', DEFAULT_BACKEND)
    evidence = DATA/'checks'
    evidence.mkdir(exist_ok=True)
    base = ROOT/'configs/financial-supplement-heldout-index-v1.json'
    index = read(base)
    index['evidence'].append(dict(path=base.relative_to(ROOT).as_posix(), sha256=sha(base)))
    pool = ROOT/'data/financial-sampling-study-v1/pool-v1/train.json'
    pool_manifest = pool.parent/'manifest.json'
    # Training rows only; protected examples remain inside the blind screen.
    rows = read(pool)
    if len(rows) != 13242 or any(r['split'] != 'train' for r in rows):
        raise ValueError('Unexpected current training pool')
    entry = dict(path=pool.relative_to(ROOT).as_posix(), format='json_array', role='training_pool',
                 reader=dict(message_path=['input','message'], history_path=['input','history'],
                             missing_history='empty', split_field='split', include_splits=['train']),
                 sha256=sha(pool), file_rows=len(rows), selected_rows=len(rows),
                 evidence=dict(path=pool_manifest.relative_to(ROOT).as_posix(), sha256=sha(pool_manifest)))
    if any(r['path'] == entry['path'] for r in index['corpora']): raise ValueError('Duplicate pool coverage')
    index['corpora'].append(entry)
    index['counts'] = {role: dict(entries=sum(r['role']==role for r in index['corpora']),
        selected_rows_with_snapshot_repetition=sum(r['selected_rows'] for r in index['corpora'] if r['role']==role),
        unique_file_sha256=len({r['sha256'] for r in index['corpora'] if r['role']==role})) for role in ('heldout','training_pool')}
    index_path = evidence/'coverage-index.json'
    with index_path.open('xb') as f: f.write(encoded(index))
    source = ROOT/'scripts/screen-financial-expansion-overlap.py'
    spec = importlib.util.spec_from_file_location('blind_screen_state_pairs', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    report = module.run_screen(DATA/'build/candidates.json', evidence/'blind-overlap.json', index_path)
    print(json.dumps({k:report[k] for k in ['candidate_count','hit_candidate_counts','quarantine_groups','quarantine_candidate_ids']},ensure_ascii=False))


if __name__=='__main__': main()
