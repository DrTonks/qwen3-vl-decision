"""Prepare a versioned sampling-study pool; never enables or executes training."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

from qwenlab import financial_service_v2_data as old
from qwenlab import financial_supplement_expansion as expansion
from qwenlab.common import ROOT, sha

OUT = ROOT / 'data/financial-sampling-study-v1/pool-v1'
SUPPLEMENT = ROOT / 'data/financial-supplement-expansion-v1/reviewed-v1'
SUPPLEMENT_DIGEST = 'd587d892b9267aae594328de1b34e5a654803e56bad0dba9abfc764489ee513e'
LEGACY_DIGEST = 'e12e359809ccb162ac242b2661b3f995b0e7bc44b5e8595c94e982c68bd5f021'
INDEX = ROOT / 'configs/financial-supplement-heldout-index-v1.json'
SCREEN = ROOT / 'scripts/screen-financial-expansion-overlap.py'
FILES = {'train.json', 'quarantine.json', 'summary.json', 'blind-heldout.json'}


def read(p):
    return old.read(p)


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def sources():
    manifest = read(SUPPLEMENT / 'manifest.json')
    paths = [old.OUT / 'train-manifest.json', old.OUT / 'train.json',
             SUPPLEMENT / 'manifest.json', SUPPLEMENT / 'accepted.json',
             INDEX, SCREEN, Path(__file__).resolve()]
    paths += [ROOT / p for p in manifest['sources']]
    paths += [ROOT / p for p in read(old.OUT / 'train-manifest.json')['source_files']]
    paths += [ROOT / 'src/qwenlab/financial_service_v2_data.py',
              ROOT / 'src/qwenlab/financial_supplement_expansion.py',
              ROOT / 'src/qwenlab/financial_supplement_pilot.py', ROOT / 'src/qwenlab/common.py']
    # Index dependencies are part of the replay closure, including heldout bytes.
    index = read(INDEX)
    paths += [ROOT / e['path'] for e in index['corpora']]
    paths += [ROOT / e['evidence']['path'] for e in index['corpora']]
    paths += [ROOT / e['path'] for e in index['evidence']]
    return {rel(p): sha(p) for p in paths}


def load_training_only():
    if sha(old.OUT / 'train.json') != LEGACY_DIGEST:
        raise ValueError('Expected the frozen 11756-row legacy training pool')
    rows = old.validate_train()
    manifest = read(SUPPLEMENT / 'manifest.json')
    if manifest['training_eligible'] is not False or manifest['human_reviewed'] is not False:
        raise ValueError('Reviewed candidate eligibility changed')
    if sha(SUPPLEMENT / 'accepted.json') != SUPPLEMENT_DIGEST:
        raise ValueError('Expected the frozen 1486-row reviewed supplement')
    for name, digest in manifest['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Supplement review source changed')
    for name, digest in manifest['files'].items():
        if sha(SUPPLEMENT / name) != digest:
            raise ValueError('Supplement package changed')
    spec, _ = old.protocol()
    result = []
    for origin, batch in [('legacy', rows), ('supplement', read(SUPPLEMENT / 'accepted.json'))]:
        for original in batch:
            row = deepcopy(original)
            if origin == 'supplement' and (row['review_status'] != 'independent_ai_review_accepted' or row['quarantine_reasons']):
                raise ValueError('Unaccepted supplement')
            if row['split'] != ('train' if origin == 'legacy' else 'candidate') or row['training_eligible'] is not False:
                raise ValueError('Training source role mismatch')
            old.check_row(row, spec)
            row.update(split='train', training_eligible=False,
                       usage='sampling_design_only_executor_review_required',
                       sampling_source=origin)
            if origin == 'legacy':
                # Legacy hand-authored input is not a production Node replay.
                row['input_layer'] = {'current-service': 'component-message-only',
                                      'planned-retrieval': 'planned-capability-component',
                                      'preauth-robustness': 'preauth-component'}[row['cohort']]
            result.append(row)
    if len(result) != 13242 or len({r['id'] for r in result}) != len(result):
        raise ValueError('Unexpected combined training source inventory')
    return result


def partition(rows, heldout_groups):
    """Quarantine whole groups on heldout match or contradictory visible input."""
    known = {r['scene_family_id'] for r in rows}
    if not set(heldout_groups) <= known:
        raise ValueError('Unknown heldout group')
    by_input = defaultdict(list)
    for row in rows:
        by_input[json.dumps(row['input'], ensure_ascii=False, sort_keys=True)].append(row)
    conflicts = set()
    for block in by_input.values():
        labels = {json.dumps({k: r['annotation'][k] for k in
                    ['action', 'tool_name', 'tool_arguments', 'retrieval_collection', 'missing_slots']},
                    sort_keys=True) for r in block}
        if len(labels) > 1:
            conflicts.update(r['scene_family_id'] for r in block)
    blocked = set(heldout_groups) | conflicts
    accepted, rejected = [], []
    for original in rows:
        row = deepcopy(original)
        row['sampling_exclusion_reasons'] = [label for label, groups in
            [('historical_heldout_lexical_match', set(heldout_groups)),
             ('conflicting_full_visible_input', conflicts)] if row['scene_family_id'] in groups]
        (rejected if row['scene_family_id'] in blocked else accepted).append(row)
    return accepted, rejected


def compute():
    initial_sources = sources()
    rows = load_training_only()
    spec = importlib.util.spec_from_file_location('sampling_blind_screen', SCREEN)
    screen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(screen)
    indexes, records, counts = screen.load_corpora(ROOT, read(INDEX))
    # Old training rows would trivially match their own training pool. Screen
    # against heldout only; retain and disclose all original index validation.
    indexes['training_pool'] = screen.LexicalIndex()
    report = screen.screen_candidates(rows, indexes)
    report.update(scope='heldout_only_for_combined_training_pool',
                  index_sha256=sha(INDEX), screener_sha256=sha(SCREEN),
                  validated_corpus_counts=counts,
                  compared_corpora=[r for r in records if r['role'] == 'heldout'],
                  training_pool_match_disabled=True, threshold=0.85,
                  semantic_independence_proven=False, training_eligible=False)
    accepted, rejected = partition(rows, report['quarantine_groups'])
    summary = dict(input_rows=len(rows), accepted=expansion.pilot.summary(accepted),
                   quarantined=expansion.pilot.summary(rejected),
                   accepted_origins=dict(Counter(r['sampling_source'] for r in accepted)),
                   exclusion_reasons=dict(Counter(t for r in rejected for t in r['sampling_exclusion_reasons'])),
                   training_eligible=False, model_weights_loaded=False, model_api_requests=0)
    if initial_sources != sources():
        raise ValueError('Sources changed during preparation')
    return dict(zip(['train.json', 'quarantine.json', 'summary.json', 'blind-heldout.json'],
                    [accepted, rejected, summary, report])), initial_sources


def build():
    if OUT.exists():
        raise FileExistsError('Preserve frozen study pool')
    values, bindings = compute()
    OUT.mkdir(parents=True)
    for name, value in values.items():
        old.write(OUT / name, value)
    old.write(OUT / 'manifest.json', dict(version='financial-sampling-pool-v1',
              training_eligible=False, status='design_only', sources=bindings,
              files={name: sha(OUT / name) for name in sorted(FILES)}))
    print(json.dumps(values['summary.json'], ensure_ascii=False))


def verify(replay=False):
    manifest = read(OUT / 'manifest.json')
    if set(manifest) != {'version', 'training_eligible', 'status', 'sources', 'files'} or set(manifest['files']) != FILES:
        raise ValueError('Incomplete pool manifest')
    if manifest['version'] != 'financial-sampling-pool-v1' or manifest['status'] != 'design_only' or manifest['training_eligible'] is not False:
        raise ValueError('Pool cannot enable training')
    if manifest['sources'] != sources():
        raise ValueError('Source dependency inventory changed')
    for name, digest in manifest['files'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Pool output changed')
    if replay:
        values, _ = compute()
        if any(read(OUT / name) != value for name, value in values.items()):
            raise ValueError('Full blind replay differs')
    return read(OUT / 'train.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['build', 'verify'])
    p.add_argument('--replay', action='store_true')
    args = p.parse_args()
    if args.command == 'build':
        build()
    else:
        print(json.dumps(dict(rows=len(verify(args.replay)), training_enabled=False)))


if __name__ == '__main__':
    main()
