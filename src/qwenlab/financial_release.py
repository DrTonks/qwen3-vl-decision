"""Curate a versioned, agent-reviewed, training-only financial text release.

This command does not resume the rewrite queue, run a model, or create evaluation
data. Original accepted artifacts remain immutable. A batch-level pass alone is
insufficient: only IDs actually read by an independent reviewer are eligible.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import uuid

from qwenlab.common import ROOT, sha
from qwenlab.financial_completion import (
    BASE as COMPLETION, completion_protection, identity, verify_job_sources, verify_review,
)
from qwenlab.financial_expansion import check
from qwenlab.financial_pilot import ACTIONS, serialize_input, normalize
from qwenlab.financial_pilot import review_markdown
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows

LOCAL = ROOT / '.local/financial-training-release-v1'
OUT = ROOT / 'data/financial-training-text-v1'
TARGETS = dict(retrieve=2500, answer=2000, tool=2200, clarify=1600,
               human=1500, close=600, refuse=900, redirect=550)
PART_SIZE = 1000
LETTERS = {action: chr(65 + n) for n, action in enumerate(ACTIONS)}
PRODUCTS = '极速贷|工薪贷|优享贷|微企贷|精英贷|房抵贷|尊享贷|教育贷|医疗贷'
CONTENT_FIELDS = ['id', 'scene_family_id', 'input', 'annotation', 'provenance']


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def write_lf(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')


def pattern_text(text):
    """A lexical structural screen, not a claim of semantic equivalence."""
    return re.sub(r'\d+(?:\.\d+)?', '<number>',
                  re.sub(PRODUCTS, '<product>', normalize(text)))


def pattern_key(row):
    v = deepcopy(row['input'])
    v['message'] = pattern_text(v['message'])
    v['history'] = [dict(role=h['role'], content=pattern_text(h['content']))
                    for h in v['history']]
    if 'application_id' in v['state']:
        v['state']['application_id'] = '<application>'
    a = row['annotation']
    # Keep authentication, status, capability and action distinctions. We do
    # not collapse contrary decisions just because the wording is similar.
    return digest([v, a['action'], a['tool_name'], a['retrieval_collection'], a['missing_slots']])


def grouping_key(row):
    """Same wording with different state/capabilities must stay together later."""
    v = row['input']
    return digest([pattern_text(v['message']),
                   [(h['role'], pattern_text(h['content'])) for h in v['history']]])


def load_baseline():
    blocked = completion_protection()
    rows, actually_read, bindings = [], set(), {}
    for folder in sorted((COMPLETION / 'jobs').iterdir()):
        if not (folder / 'status.json').exists():
            continue
        status = json.loads((folder / 'status.json').read_text(encoding='utf-8'))
        if status.get('status') != 'reviewed':
            continue
        verify_job_sources(folder.name)
        verify_review(folder, status)
        review = json.loads((folder / 'review.json').read_text(encoding='utf-8'))
        batch = read_rows(folder / 'validated.jsonl')
        rows.extend(batch)
        actually_read.update(review['reviewed_source_ids'])
        for name in ['source.jsonl', 'drafts.jsonl', 'validated.jsonl',
                     'structural-audit.json', 'review.json', 'review-findings.json']:
            p = folder / name
            bindings[p.relative_to(ROOT).as_posix()] = sha(p)
    finding_path = COMPLETION / 'legacy-score-scale-findings.json'
    findings = json.loads(finding_path.read_text(encoding='utf-8'))
    suspects = {item['source_id'] for item in findings['items']}
    by_source = {r['provenance']['parent_id']: r for r in rows}
    if not suspects <= by_source.keys():
        raise ValueError('Unknown legacy suspect source')
    for item in findings['items']:
        expected = bindings[f'.local/financial-rewrite-completion/jobs/{item["job"]}/validated.jsonl']
        if item['validated_sha256'] != expected:
            raise ValueError('Stale legacy finding binding')
    bindings[finding_path.relative_to(ROOT).as_posix()] = sha(finding_path)
    bad_groups = {by_source[s]['scene_family_id'] for s in suspects}
    eligible, ledger = [], []
    for row in rows:
        sid = row['provenance']['parent_id']
        reason = ('legacy_scale_suspect_group' if row['scene_family_id'] in bad_groups
                  else 'not_individually_independently_read' if sid not in actually_read
                  else None)
        if reason:
            ledger.append(dict(id=row['id'], disposition='quarantined', reason=reason,
                               source_id=sid, family=row['scene_family_id'],
                               direct_lexical_suspect=sid in suspects))
        else:
            r = deepcopy(row)
            r['curation'] = dict(origin='accepted_completion', original_id=row['id'],
                                  independently_read=True, human_review=False)
            eligible.append(r)
    return eligible, ledger, bindings, blocked, len(rows)


def addition_review(path):
    review_path = LOCAL / 'review' / (path.stem + '-review.json')
    if not review_path.exists():
        raise ValueError('Independent addition review missing: ' + path.stem)
    review = json.loads(review_path.read_text(encoding='utf-8'))
    if review.get('decision') != 'pass' or review.get('unresolved_findings') != []:
        raise ValueError('Addition review not passed')
    if review.get('human_review') is not False or review.get('data_sha256') != sha(path):
        raise ValueError('Addition review/hash mismatch')
    rows = read_rows(path)
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)) or set(review.get('reviewed_ids', [])) != set(ids):
        raise ValueError('Additions require full independent ID coverage')
    reviewer = identity(review['reviewer'])
    for row in rows:
        if reviewer == identity(row['provenance']['producer']):
            raise ValueError('Author cannot approve own addition')
    return rows, review_path


def load_additions(blocked, require_reviews):
    rows, bindings = [], {}
    paths = sorted((LOCAL / 'additions').glob('*.jsonl'))
    if require_reviews and {p.stem for p in paths} != {'scope', 'safety', 'core'}:
        raise ValueError('Expected complete scope, safety and core additions')
    for path in paths:
        batch = read_rows(path)
        check(batch, blocked)
        if require_reviews:
            batch, review_path = addition_review(path)
            bindings[review_path.relative_to(ROOT).as_posix()] = sha(review_path)
        bindings[path.relative_to(ROOT).as_posix()] = sha(path)
        for row in batch:
            if row['provenance'].get('origin') != 'synthetic':
                raise ValueError('New authored data must retain synthetic origin')
            if row['review'].get('status') != 'assistant_draft':
                raise ValueError('Unresolved addition cannot enter release')
            r = deepcopy(row)
            r['curation'] = dict(origin='new_authored_boundary', original_id=row['id'],
                                  independently_read=require_reviews, human_review=False)
            rows.append(r)
    return rows, bindings


def curate(rows, ledger, targets=TARGETS):
    """Deterministic quotas with round-robin context strata and family caps."""
    canonical, patterns, unique = {}, {}, []
    for row in sorted(rows, key=lambda r: (r['curation']['origin'] != 'new_authored_boundary', r['id'])):
        key, pattern = serialize_input(row), pattern_key(row)
        if key in canonical:
            prior = canonical[key]
            target_fields = ['action', 'tool_name', 'tool_arguments', 'retrieval_collection', 'missing_slots']
            if any(prior['annotation'][field] != row['annotation'][field] for field in target_fields):
                raise ValueError('Conflicting identical input')
            ledger.append(dict(id=row['id'], disposition='duplicate', reason='canonical_input',
                               retained_id=prior['id']))
            continue
        canonical[key] = row
        if pattern in patterns:
            ledger.append(dict(id=row['id'], disposition='not_selected', reason='lexical_variable_pattern',
                               retained_id=patterns[pattern]['id']))
            continue
        patterns[pattern] = row
        unique.append(row)
    selected, family_counts = [], Counter()
    for action in ACTIONS:
        strata = defaultdict(list)
        for row in unique:
            if row['annotation']['action'] == action:
                v, a = row['input'], row['annotation']
                key = (v['state']['authenticated'], len(v['history']), v['capability_profile'],
                       a['tool_name'] or a['retrieval_collection'] or '', tuple(a['missing_slots']))
                strata[key].append(row)
        for values in strata.values():
            values.sort(key=lambda r: digest(r['id']))
        taken, offset = 0, 0
        while taken < targets[action] and any(offset < len(v) for v in strata.values()):
            for key in sorted(strata, key=repr):
                values = strata[key]
                if offset >= len(values) or taken >= targets[action]:
                    continue
                row = values[offset]
                family = row['scene_family_id']
                if family_counts[action, family] >= 20:
                    continue
                selected.append(row)
                family_counts[action, family] += 1
                taken += 1
            offset += 1
    selected_ids = {r['id'] for r in selected}
    for row in unique:
        if row['id'] not in selected_ids:
            ledger.append(dict(id=row['id'], disposition='not_selected', reason='quota_or_family_cap'))
    return sorted(selected, key=lambda r: digest(r['id'])), unique


def attach_groups(rows):
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    keys = {}
    for row in rows:
        family, wording = row['scene_family_id'], grouping_key(row)
        if wording in keys:
            union(family, keys[wording])
        keys[wording] = family
    for row in rows:
        row['curation']['partition_group'] = 'FT-G-' + digest(find(row['scene_family_id']))[:20]


def summarize(rows):
    return dict(rows=len(rows), actions=dict(Counter(r['annotation']['action'] for r in rows)),
                original_families=len({r['scene_family_id'] for r in rows}),
                partition_groups=len({r.get('curation', {}).get('partition_group', r['scene_family_id']) for r in rows}),
                with_history=sum(bool(r['input']['history']) for r in rows),
                authentication_by_action={a: dict(Counter(str(r['input']['state']['authenticated']).lower()
                    for r in rows if r['annotation']['action'] == a)) for a in ACTIONS})


def prepare():
    rows, ledger, bindings, blocked, total = load_baseline()
    LOCAL.mkdir(parents=True, exist_ok=True)
    check(rows, blocked)
    write_lf(LOCAL / 'baseline-eligible.jsonl', rows)
    write_lf(LOCAL / 'baseline-ledger.jsonl', ledger)
    atomic_json(LOCAL / 'baseline-manifest.json', dict(total_accepted=total,
        eligible=summarize(rows), quarantined=len(ledger), source_bindings=bindings,
        note='Eligibility is not a training release. Legacy lexical suspicion is not a confirmed defect.'))
    print(json.dumps(dict(total_accepted=total, eligible=summarize(rows), quarantined=len(ledger)),
                     ensure_ascii=False, indent=2))


def export_review_evidence(stage, selected, files, bindings):
    """Ship original independent review packets, not a new self-approval."""
    old_index, new_index = {}, {}
    for folder in sorted((COMPLETION / 'jobs').iterdir()):
        path = folder / 'review.json'
        if not path.exists() or path.relative_to(ROOT).as_posix() not in bindings:
            continue
        review = json.loads(path.read_text(encoding='utf-8'))
        for source_id in review['reviewed_source_ids']:
            old_index[source_id] = (path, f'reviews/legacy-{folder.name}.json', review)
    for path in sorted((LOCAL/'additions').glob('*.jsonl')):
        review_path = LOCAL/'review'/(path.stem+'-review.json')
        review = json.loads(review_path.read_text(encoding='utf-8'))
        for row_id in review['reviewed_ids']:
            new_index[row_id] = (review_path, 'reviews/'+review_path.name, review)
    evidence = []
    for row in selected:
        legacy = row['curation']['origin'] == 'accepted_completion'
        source_id = row['provenance']['parent_id'] if legacy else row['id']
        path, target, review = (old_index if legacy else new_index)[source_id]
        if target not in files:
            dest = stage/target
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            files[target] = dict(sha256=sha(dest))
        evidence.append(dict(id=row['id'], source_id=source_id,
            review_kind='legacy' if legacy else 'addition', reviewer=review['reviewer'],
            review_file=target, source_review_path=path.relative_to(ROOT).as_posix(),
            content_sha256=digest({key: row[key] for key in CONTENT_FIELDS}), human_review=False))
    write_lf(stage/'review-evidence.jsonl', evidence)
    files['review-evidence.jsonl'] = dict(rows=len(evidence), sha256=sha(stage/'review-evidence.jsonl'))


def validate_review_evidence(folder, rows, manifest):
    evidence = read_rows(folder/'review-evidence.jsonl')
    index = {e['id']: e for e in evidence}
    if len(index) != len(rows) or len(evidence) != len(index) or set(index) != {r['id'] for r in rows}:
        raise ValueError('Independent review evidence coverage mismatch')
    packets = {}
    for row in rows:
        e = index[row['id']]
        if e.get('review_kind') not in ['legacy', 'addition']:
            raise ValueError('Unknown review evidence kind')
        name = e['review_file']
        if not name.startswith('reviews/') or name not in manifest['files']:
            raise ValueError('Review packet missing from manifest')
        if manifest['source_bindings'].get(e['source_review_path']) != manifest['files'][name]['sha256']:
            raise ValueError('Review packet/source binding mismatch')
        if name not in packets:
            packets[name] = json.loads((folder/name).read_text(encoding='utf-8'))
        review = packets[name]
        field = 'reviewed_source_ids' if e['review_kind'] == 'legacy' else 'reviewed_ids'
        expected_id = row['provenance'].get('parent_id') if e['review_kind'] == 'legacy' else row['id']
        if (review.get('decision') != 'pass' or review.get('human_review') is not False
                or review.get('unresolved_findings') != []
                or e['human_review'] is not False or e['source_id'] != expected_id
                or expected_id not in review[field] or e['reviewer'] != review['reviewer']
                or identity(review['reviewer']) == identity(row['provenance']['producer'])):
            raise ValueError('Invalid independent review evidence')
        if e['content_sha256'] != digest({key: row[key] for key in CONTENT_FIELDS}):
            raise ValueError('Review evidence content mismatch')


def build():
    if OUT.exists():
        raise FileExistsError('Release exists: validate it or build a new version')
    rows, ledger, bindings, blocked, total = load_baseline()
    added, added_bindings = load_additions(blocked, require_reviews=True)
    bindings.update(added_bindings)
    check(rows + added, blocked)
    all_candidates = rows + added
    # Deduplicated-away sources can still connect other retained siblings.
    attach_groups(all_candidates)
    selected, unique = curate(all_candidates, ledger)
    selected_ids = {r['id'] for r in selected}
    if len(selected) < 10000 or len(selected) > 15000:
        raise ValueError(f'Expected 10000–15000 usable rows, got {len(selected)}')
    counts = Counter(r['annotation']['action'] for r in selected)
    for action, floor in dict(refuse=800, redirect=500, close=500, human=1300, clarify=1200).items():
        if counts[action] < floor:
            raise ValueError(f'Insufficient independently reviewed coverage: {action}={counts[action]} < {floor}')
    stage = OUT.with_name(OUT.name + '.staging-' + uuid.uuid4().hex[:10])
    stage.mkdir(parents=True)
    try:
        files = {}
        for n, start in enumerate(range(0, len(selected), PART_SIZE), 1):
            name = f'parts/part-{n:04d}.jsonl'
            batch = []
            for candidate in selected[start:start+PART_SIZE]:
                row = deepcopy(candidate)
                row.update(split='train', usage='training_release_agent_reviewed')
                row['review'].update(status='independent_agent_review_pass',
                                     semantic_review='individually_read', human_reviewed_current_version=False)
                batch.append(row)
            write_lf(stage / name, batch)
            files[name] = dict(rows=len(batch), sha256=sha(stage / name))
        write_lf(stage / 'selection-ledger.jsonl', ledger)
        files['selection-ledger.jsonl'] = dict(rows=len(ledger), sha256=sha(stage / 'selection-ledger.jsonl'))
        groups = {r['id']: dict(source_family=r['scene_family_id'],
                                 partition_group=r['curation']['partition_group'],
                                 selected=r['id'] in selected_ids) for r in all_candidates}
        atomic_json(stage / 'groups.json', groups)
        files['groups.json'] = dict(sha256=sha(stage / 'groups.json'))
        export_review_evidence(stage, selected, files, bindings)
        notice = ROOT/'data/financial-public-rewrite-v1/NOTICE.md'
        license_path = notice.parent/'licenses/CrossWOZ-LICENSE.txt'
        for source, name in [(notice, 'NOTICE.md'), (license_path, 'licenses/CrossWOZ-LICENSE.txt')]:
            dest = stage/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = source.read_bytes()
            if name == 'NOTICE.md':
                text = content.decode('utf-8').replace(
                    '所有候选未进行当前版本人工确认、未作训练发布；授权归属不等于数据质量或模型效果背书。',
                    '本版用于训练，保留AI合成来源并已逐条独立agent复核；未进行当前版本人工确认。授权归属不等于数据质量或模型效果背书。')
                content = text.encode('utf-8')
            dest.write_bytes(content)
            files[name] = dict(sha256=sha(dest))
            bindings[source.relative_to(ROOT).as_posix()] = sha(source)
        for name in ['src/qwenlab/financial_release.py', 'src/qwenlab/financial_release_core.py']:
            bindings[name] = sha(ROOT/name)
        atomic_json(stage / 'manifest.json', dict(version='financial-training-text-v1',
            purpose='training_only', independent_evaluation_ready=False,
            human_review=False, synthetic=True, source_total_accepted=total,
            policy_version='loan-eight-actions-pilot-1', targets=TARGETS,
            stats=summarize(selected), addition_stats=summarize(added),
            source_bindings=bindings, files=files, action_tokens=LETTERS,
            release_note='All selected IDs independently read. Lexical dedup is not complete semantic dedup. '
                         'Planned knowledge retrieval is simulated. New eight-action evaluation must be frozen separately.'))
        validate(stage, verify_local=True)
        stage.rename(OUT)
    except BaseException:
        # Keep failed staging for diagnosis; do not destroy an existing release.
        raise
    print(json.dumps(summarize(selected), ensure_ascii=False, indent=2))


def validate(folder=OUT, verify_local=False):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('purpose') != 'training_only' or manifest.get('human_review') is not False
            or manifest.get('independent_evaluation_ready') is not False
            or manifest.get('action_tokens') != LETTERS):
        raise ValueError('Unsupported release purpose/review claim')
    expected = manifest['files']
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(expected) | {'manifest.json'}:
        raise ValueError('Unexpected or missing release files')
    rows = []
    for name, meta in expected.items():
        p = folder / name
        if p.resolve().parent != folder.resolve() and folder.resolve() not in p.resolve().parents:
            raise ValueError('File escapes release directory')
        if sha(p) != meta['sha256']:
            raise ValueError('Artifact changed: ' + name)
        if p.suffix == '.jsonl':
            batch = read_rows(p)
            if len(batch) != meta['rows']:
                raise ValueError('Artifact count mismatch')
            if name.startswith('parts/'):
                rows.extend(batch)
    candidates = []
    for r in rows:
        if r['split'] != 'train' or r['usage'] != 'training_release_agent_reviewed':
            raise ValueError('Invalid training release row')
        if r['review']['status'] != 'independent_agent_review_pass' or r['curation']['independently_read'] is not True:
            raise ValueError('Row not individually independently read')
        if r['review']['human_reviewed_current_version'] is not False:
            raise ValueError('False human-review claim')
        c = deepcopy(r)
        c.update(split='train_candidate', usage='candidate_only_not_training_release')
        c['review']['status'] = 'assistant_draft'
        candidates.append(c)
    check(candidates, set())
    if summarize(rows) != manifest['stats']:
        raise ValueError('Summary disagrees with artifacts')
    validate_review_evidence(folder, rows, manifest)
    group_map = json.loads((folder / 'groups.json').read_text(encoding='utf-8'))
    for row in rows:
        if group_map[row['id']] != dict(source_family=row['scene_family_id'],
                   partition_group=row['curation']['partition_group'], selected=True):
            raise ValueError('Grouping evidence mismatch')
    if verify_local:
        for name, value in manifest['source_bindings'].items():
            p = ROOT / name
            if ROOT.resolve() not in p.resolve().parents or sha(p) != value:
                raise ValueError('Original source/review changed: ' + name)
        original, original_ledger, _, blocked, _ = load_baseline()
        additions, _ = load_additions(blocked, require_reviews=True)
        all_candidates = original + additions
        attach_groups(all_candidates)
        chosen, _ = curate(all_candidates, original_ledger)
        originals = {r['id']: r for r in chosen}
        if set(originals) != {r['id'] for r in rows}:
            raise ValueError('Release selection differs from bound reviewed sources')
        for row in rows:
            source = originals[row['id']]
            for field in ['id', 'scene_family_id', 'input', 'annotation', 'provenance', 'curation']:
                if row[field] != source[field]:
                    raise ValueError('Release row differs from reviewed original: ' + row['id'] + '/' + field)
        expected_groups = {r['id']: dict(source_family=r['scene_family_id'],
                              partition_group=r['curation']['partition_group'],
                              selected=r['id'] in originals) for r in all_candidates}
        if group_map != expected_groups or read_rows(folder / 'selection-ledger.jsonl') != original_ledger:
            raise ValueError('Selection/group evidence differs from source reconstruction')
        check(candidates, blocked)
    return manifest['stats']


def training_rows(folder=OUT):
    """Only visible input and compact targets are exposed to training code."""
    validate(folder)
    for p in sorted((folder / 'parts').glob('part-*.jsonl')):
        for row in read_rows(p):
            a = row['annotation']
            yield dict(id=row['id'], group=row['curation']['partition_group'],
                       input=serialize_input(row), action=a['action'], action_token=LETTERS[a['action']],
                       tool_name=a['tool_name'], tool_arguments=a['tool_arguments'],
                       retrieval_collection=a['retrieval_collection'], missing_slots=a['missing_slots'])


def review_candidate(row):
    r = deepcopy(row)
    r.update(split='train_candidate', usage='candidate_only_not_training_release')
    r['review'].update(status='assistant_draft', semantic_review='editing_copy_not_approved',
                       human_reviewed_current_version=False)
    r['curation']['independently_read'] = False
    return r


def review_copy():
    """An editable candidate copy; changes cannot silently replace the release."""
    validate(OUT)
    path = LOCAL/'human-review/cases.jsonl'
    if path.parent.exists():
        raise FileExistsError('Human review copy exists; keep existing edits')
    candidates = [review_candidate(r) for p in sorted((OUT/'parts').glob('part-*.jsonl'))
                  for r in read_rows(p)]
    write_lf(path, candidates)
    atomic_json(path.parent/'base.json', dict(release_manifest_sha256=sha(OUT/'manifest.json')))
    for action in ACTIONS:
        dest = path.parent/'by-action'/(action+'.md')
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(review_markdown([r for r in candidates if r['annotation']['action'] == action]),
                        encoding='utf-8')
    print('Saved .local/financial-training-release-v1/human-review/cases.jsonl and by-action/*.md')


def check_review_copy():
    validate(OUT)
    folder = LOCAL/'human-review'
    base = json.loads((folder/'base.json').read_text(encoding='utf-8'))
    if base['release_manifest_sha256'] != sha(OUT/'manifest.json'):
        raise ValueError('Review copy belongs to a different release')
    edited = read_rows(folder/'cases.jsonl')
    originals = {r['id']: review_candidate(r) for p in sorted((OUT/'parts').glob('part-*.jsonl'))
                 for r in read_rows(p)}
    if len(edited) != len(originals) or {r['id'] for r in edited} != set(originals):
        raise ValueError('Review copy must retain original IDs/count')
    changes = []
    for row in edited:
        original = originals[row['id']]
        if {k: v for k, v in row.items() if k not in ['input', 'annotation']} != {
                k: v for k, v in original.items() if k not in ['input', 'annotation']}:
            raise ValueError('Edit only input and annotation: ' + row['id'])
        fields = [k for k in ['input', 'annotation'] if row[k] != original[k]]
        if fields:
            changes.append(dict(id=row['id'], changed_fields=fields))
    result = check(edited, completion_protection())
    report = dict(rows=result['rows'], changed=len(changes), changes=changes,
                  human_review=False, status='candidate_edits_need_independent_review')
    atomic_json(folder/'changes.json', report)
    print(json.dumps(dict(rows=result['rows'], changed=len(changes),
                         status=report['status']), ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'build', 'validate', 'export-training',
                                           'review-copy', 'check-review-copy'])
    parser.add_argument('--verify-local', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    elif args.command == 'build':
        build()
    elif args.command == 'validate':
        print(json.dumps(validate(verify_local=args.verify_local), ensure_ascii=False, indent=2))
    elif args.command == 'review-copy':
        review_copy()
    elif args.command == 'check-review-copy':
        check_review_copy()
    else:
        write_lf(LOCAL / 'train-input-target.jsonl', training_rows())
        print('Saved .local/financial-training-release-v1/train-input-target.jsonl')


if __name__ == '__main__':
    main()
