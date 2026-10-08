"""Versioned training overlay and independently authored evaluation arrays.

No training, inference, APIs or mutation of V1/legacy protection snapshots.
Evaluation is ordinary JSON, protected explicitly here. This preserves the
legacy reader's frozen JSONL inventory without hiding evaluation from V2.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import difflib
import json
from pathlib import Path
import uuid

from qwenlab.common import ROOT, sha
from qwenlab.prepare_v2 import read_rows
from qwenlab.financial_completion import completion_protection, identity, BASE as OLD_JOBS
from qwenlab.financial_expansion import check
from qwenlab.financial_pilot import ACTIONS, TOOLS, serialize_input
from qwenlab import financial_release as v1

LOCAL = ROOT/'.local/financial-eight-actions-v2'
OUT = ROOT/'data/financial-eight-actions-v2'
BASE = ROOT/'data/financial-training-text-v1'
CONFIG = ROOT/'configs/financial-eight-actions-pilot-v2.json'
CATALOG = LOCAL/'candidates/evaluation-catalog-v2.json'
SPLITS = ['development', 'calibration', 'final']
COUNTS = {
    'development': dict(clarify=64, tool=64, human=64, answer=48, retrieve=48, refuse=48, redirect=24, close=24),
    'calibration': {a: 32 for a in ACTIONS},
    'final': dict(clarify=80, tool=80, human=96, answer=64, retrieve=64, refuse=64, redirect=32, close=32),
}


def review_content_digest(row):
    return v1.digest({key:row.get(key) for key in v1.CONTENT_FIELDS+['evaluation_split']})


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.part')
    temporary.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    temporary.replace(path)


def candidate(row):
    r = deepcopy(row)
    r.update(split='train_candidate', usage='candidate_only_not_training_release')
    r['review'].update(status='assistant_draft', human_reviewed_current_version=False)
    return r


def base_rows():
    v1.validate(BASE)
    return [candidate(r) for p in sorted((BASE/'parts').glob('part-*.jsonl')) for r in read_rows(p)]


def reviewed_rows(stem, require_review=True):
    path = LOCAL/'candidates'/(stem+'.jsonl')
    rows = read_rows(path)
    if require_review:
        report_path = LOCAL/'review'/(stem+'-review.json')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        ids = [r['id'] for r in rows]
        if (report.get('decision') != 'pass' or report.get('unresolved_findings') != []
                or report.get('human_review') is not False or report.get('data_sha256') != sha(path)
                or len(ids) != len(set(ids)) or set(report.get('reviewed_ids', [])) != set(ids)):
            raise ValueError('Full independent review missing or stale: '+stem)
        for row in rows:
            if identity(report['reviewer']) == identity(row['provenance']['producer']):
                raise ValueError('Author cannot approve own data')
        if report.get('reviewed_content_sha256')!={r['id']:review_content_digest(r) for r in rows}:
            raise ValueError('Independent review content binding missing/stale')
    for row in rows:
        if row['provenance'].get('origin') != 'synthetic' or row['review']['human_reviewed_current_version'] is not False:
            raise ValueError('Preserve synthetic provenance and non-human-review status')
        if stem == 'evaluation':
            split = row.get('evaluation_split')
            if split not in SPLITS or row['split'] != split:
                raise ValueError('Evaluation must be stored under its real partition')
        elif row['split'] != 'train_candidate' or row.get('evaluation_split'):
            raise ValueError('Evaluation cannot enter training overlay')
    return rows


def joined_groups(train, evaluation, catalog):
    rows = train+evaluation
    for r in rows:
        r.setdefault('curation', {})
    v1.attach_groups(rows)
    # Shared background/history makes subproblems correlated. Conservatively
    # unite macro stories too, not just the more numerous subfamily labels.
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    macro = {}
    for r in evaluation:
        family = r['scene_family_id']
        if family not in catalog or catalog[family]['split'] != r['evaluation_split']:
            raise ValueError('Unknown or wrongly partitioned evaluation family: '+family)
        key = catalog[family]['macro_scene']
        group = r['curation']['partition_group']
        if key in macro:
            union(group, macro[key])
        macro[key] = group
    groups, partitions = {}, defaultdict(set)
    for r in rows:
        split = r.get('evaluation_split', 'train')
        group = find(r['curation']['partition_group'])
        r['curation']['partition_group'] = group
        partitions[group].add(split)
        groups[r['id']] = dict(split=split, family=r['scene_family_id'], group=group)
    if len(groups) != len(rows):
        raise ValueError('Duplicate record IDs')
    crossed = {g: sorted(p) for g,p in partitions.items() if len(p)>1}
    if crossed:
        raise ValueError('Related wording/story spans partitions: '+json.dumps(crossed, ensure_ascii=False))
    return groups


def near_pairs(references, queries, cutoff=.92):
    """Limited lexical candidate retrieval; not a semantic independence proof."""
    texts = [v1.pattern_text(r['input']['message']) for r in references]
    def grams(text):
        return {text[n:n+3] for n in range(max(0,len(text)-2))}
    index = defaultdict(list)
    for i,text in enumerate(texts):
        for gram in grams(text):
            index[gram].append(i)
    result = {}
    for q in queries:
        text = v1.pattern_text(q['input']['message'])
        rare = sorted(grams(text), key=lambda g:(len(index[g]),g))[:12]
        counts = Counter(i for gram in rare for i in index[gram][:250])
        for i,_ in counts.most_common(30):
            ref = references[i]
            if q['id'] == ref['id'] or q.get('evaluation_split') == ref.get('evaluation_split'):
                continue
            old = texts[i]
            if min(len(text),len(old))/max(1,len(text),len(old)) < .85:
                continue
            ratio = difflib.SequenceMatcher(None, text, old, autojunk=False).ratio()
            if ratio >= cutoff:
                pair = tuple(sorted([q['id'],ref['id']]))
                result[pair] = dict(ids=list(pair), ratio=round(ratio,6))
    return sorted(result.values(), key=lambda p:(-p['ratio'],p['ids']))


def reference_pool():
    rows = []
    for folder in sorted((OLD_JOBS/'jobs').iterdir()):
        path = folder/'validated.jsonl'
        if (folder/'status.json').exists() and path.exists():
            status = json.loads((folder/'status.json').read_text(encoding='utf-8'))
            if status.get('status') == 'reviewed':
                rows.extend(read_rows(path))
    for name in ['financial-actions-text-v2','financial-public-rewrite-v1']:
        rows.extend(read_rows(ROOT/'data'/name/'cases.jsonl'))
    return rows


def summarize(base, additions, evaluation, catalog):
    return {
        'base_train': len(base), 'new_train': len(additions), 'train_total': len(base)+len(additions),
        'new_train_actions': dict(Counter(r['annotation']['action'] for r in additions)),
        'new_train_status_tools': sum(r['annotation']['tool_name']=='explainApplicationStatus' for r in additions),
        'new_train_no_kb': sum(r['input']['capability_profile']=='current-no-kb-v1' for r in additions),
        'evaluation': {s:dict(rows=sum(r['evaluation_split']==s for r in evaluation),
            actions=dict(Counter(r['annotation']['action'] for r in evaluation if r['evaluation_split']==s)),
            families=len({r['scene_family_id'] for r in evaluation if r['evaluation_split']==s}),
            macro_stories=len({catalog[r['scene_family_id']]['macro_scene'] for r in evaluation if r['evaluation_split']==s}),
            no_kb=sum(r['input']['capability_profile']=='current-no-kb-v1' for r in evaluation if r['evaluation_split']==s)) for s in SPLITS},
    }


def assemble(require_review):
    blocked = completion_protection()
    base = base_rows()
    additions = reviewed_rows('train-additions', require_review)
    evaluation = reviewed_rows('evaluation', require_review)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    check([candidate(r) for r in additions+evaluation], blocked)
    check(base+[candidate(r) for r in additions], blocked)
    # Exact full inputs and masked wording/history must not cross the new splits.
    groups = joined_groups(base+additions, evaluation, catalog)
    old_inputs = {serialize_input(r):r['id'] for r in reference_pool()}
    collisions = [dict(evaluation_id=r['id'], old_id=old_inputs[serialize_input(r)])
                  for r in evaluation if serialize_input(r) in old_inputs]
    if collisions:
        raise ValueError('New evaluation repeats old candidate input: '+json.dumps(collisions))
    stats = summarize(base, additions, evaluation, catalog)
    pairs = near_pairs(reference_pool()+additions+evaluation, evaluation)
    return base, additions, evaluation, catalog, groups, stats, pairs


def audit():
    *_, stats, pairs = assemble(False)
    write_json(LOCAL/'audit.json', dict(stats=stats, near_pairs=pairs,
        screen='Masked current-message lexical candidate screen only; labels/contexts need independent adjudication.'))
    print(json.dumps(dict(stats=stats, near_pairs=len(pairs)), ensure_ascii=False, indent=2))


def check_budget(stats, evaluation):
    if stats['new_train_status_tools'] < 240 or stats['new_train_no_kb'] < 500:
        raise ValueError('Training coverage floor not met')
    if any(stats['new_train_actions'].get(a,0)<20 for a in ACTIONS):
        raise ValueError('Missing action contrast in new training')
    for split in SPLITS:
        if stats['evaluation'][split]['actions'] != COUNTS[split]:
            raise ValueError('Evaluation quota differs from frozen plan: '+split)
        rows = [r for r in evaluation if r['evaluation_split']==split]
        counts = Counter(r['annotation']['tool_name'] for r in rows if r['annotation']['action']=='tool')
        if any(counts[t]<4 for t in TOOLS):
            raise ValueError('Every split needs all five tools')
        if stats['evaluation'][split]['families']<32 or stats['evaluation'][split]['no_kb']<24:
            raise ValueError('Evaluation context coverage floor not met')


def verify_overlap_review(pairs):
    path = LOCAL/'review/overlap-review.json'
    review = json.loads(path.read_text(encoding='utf-8'))
    if (review.get('decision')!='pass' or review.get('human_review') is not False
            or review.get('unresolved_findings')!=[] or review.get('pairs_sha256')!=v1.digest(pairs)):
        raise ValueError('Cross-partition lexical overlap review missing/stale')
    expected = {tuple(p['ids']) for p in pairs}
    if {tuple(p) for p in review.get('reviewed_pairs',[])} != expected:
        raise ValueError('Every reported near pair needs actual independent context review')
    return path


def publish(row, split, groups):
    r = deepcopy(row)
    r.update(split=split, dataset_role='evaluation' if split in SPLITS else 'training_addition',
             usage='evaluation_agent_reviewed_synthetic' if split in SPLITS else 'training_release_agent_reviewed')
    r['review'].update(status='independent_agent_review_pass', semantic_review='individually_read',
                       human_reviewed_current_version=False)
    r['curation'] = dict(independently_read=True, human_review=False, original_id=r['id'],
                         partition_group=groups[r['id']]['group'])
    return r


def build():
    if OUT.exists():
        raise FileExistsError('V2 release exists; never overwrite frozen data')
    v1.validate(BASE, verify_local=True)
    base, additions, evaluation, catalog, groups, stats, pairs = assemble(True)
    check_budget(stats, evaluation)
    overlap = verify_overlap_review(pairs)
    stage = OUT.with_name(OUT.name+'.staging-'+uuid.uuid4().hex[:10])
    stage.mkdir(parents=True)
    files, bindings = {}, {}
    def record(name, source=None):
        if source:
            dest = stage/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(source.read_bytes())
            bindings[source.relative_to(ROOT).as_posix()] = sha(source)
        files[name] = dict(sha256=sha(stage/name))
    v1.write_lf(stage/'train-additions.jsonl', [publish(r,'train',groups) for r in additions])
    record('train-additions.jsonl')
    for split in SPLITS:
        write_json(stage/f'evaluation/{split}.json', [publish(r,split,groups) for r in evaluation if r['evaluation_split']==split])
        record(f'evaluation/{split}.json')
    write_json(stage/'groups.json', groups)
    record('groups.json')
    write_json(stage/'overlap-audit.json', dict(pairs=pairs, method='limited lexical screen, not complete semantic dedup'))
    record('overlap-audit.json')
    record('evaluation/catalog.json', CATALOG)
    record('protocol.json', CONFIG)
    record('reviews/overlap-review.json', overlap)
    for stem in ['train-additions','evaluation']:
        path = LOCAL/'candidates'/(stem+'.jsonl')
        bindings[path.relative_to(ROOT).as_posix()] = sha(path)
        record('reviews/'+stem+'-review.json', LOCAL/'review'/(stem+'-review.json'))
    for name in ['src/qwenlab/financial_ready.py','src/qwenlab/financial_actions_prompt.py',
                 'src/qwenlab/financial_actions_metrics.py']:
        bindings[name] = sha(ROOT/name)
    protection = OLD_JOBS/'protection.json'
    bindings[protection.relative_to(ROOT).as_posix()] = sha(protection)
    write_json(stage/'manifest.json', dict(version='financial-eight-actions-v2', purpose='train_and_evaluation',
        human_review=False, synthetic=True, independent_authoring=True, true_user_generalization_proven=False,
        base_release=BASE.relative_to(ROOT).as_posix(), base_manifest_sha256=sha(BASE/'manifest.json'),
        files=files, source_bindings=bindings, stats=stats, action_tokens=v1.LETTERS,
        evaluations_are_standard_json_arrays=True, final_selection_usage='never train or select with final',
        note='Macro stories are correlated clusters; authored dataset counts do not establish real-world accuracy.'))
    validate(stage, verify_local=True)
    stage.rename(OUT)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def artifacts(folder):
    train = read_rows(folder/'train-additions.jsonl')
    evaluation = {s:json.loads((folder/f'evaluation/{s}.json').read_text(encoding='utf-8')) for s in SPLITS}
    return train, evaluation


def validate(folder=None, verify_local=False):
    folder = Path(folder) if folder is not None else OUT
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('purpose')!='train_and_evaluation' or manifest.get('human_review') is not False
            or manifest.get('action_tokens')!=v1.LETTERS or manifest.get('synthetic') is not True):
        raise ValueError('Unsupported release contract')
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(manifest['files'])|{'manifest.json'}:
        raise ValueError('Unexpected/missing artifact')
    for name,meta in manifest['files'].items():
        path = folder/name
        if folder.resolve() not in path.resolve().parents or sha(path)!=meta['sha256']:
            raise ValueError('Artifact changed or escapes directory: '+name)
    parent = ROOT/manifest['base_release']
    if ROOT.resolve() not in parent.resolve().parents or sha(parent/'manifest.json')!=manifest['base_manifest_sha256']:
        raise ValueError('Base training release changed')
    v1.validate(parent)
    train, evaluation = artifacts(folder)
    catalog = json.loads((folder/'evaluation/catalog.json').read_text(encoding='utf-8'))
    for split,rows in [('train',train)]+list(evaluation.items()):
        if not isinstance(rows,list):
            raise ValueError('Evaluation must be a standard JSON array')
        for r in rows:
            if (r['split']!=split or r['dataset_role']!=('training_addition' if split=='train' else 'evaluation')
                    or r['usage']!=('training_release_agent_reviewed' if split=='train' else 'evaluation_agent_reviewed_synthetic')
                    or r['review']['status']!='independent_agent_review_pass'
                    or r['review']['human_reviewed_current_version'] is not False
                    or r['review'].get('semantic_review')!='individually_read'
                    or r['curation'].get('independently_read') is not True
                    or r['curation'].get('human_review') is not False
                    or r['provenance'].get('origin')!='synthetic'):
                raise ValueError('Dataset role/partition/review mismatch')
            if split!='train' and (r['evaluation_split']!=split or catalog[r['scene_family_id']]['split']!=split):
                raise ValueError('Wrong evaluation partition')
        check([candidate(r) for r in rows], set())
    for stem, rows in [('train-additions',train),('evaluation',[r for s in SPLITS for r in evaluation[s]])]:
        report = json.loads((folder/f'reviews/{stem}-review.json').read_text(encoding='utf-8'))
        source_path = f'.local/financial-eight-actions-v2/candidates/{stem}.jsonl'
        if (report.get('decision')!='pass' or report.get('human_review') is not False or report.get('unresolved_findings')!=[]
                or report.get('data_sha256')!=manifest['source_bindings'][source_path]
                or set(report.get('reviewed_ids',[]))!={r['id'] for r in rows}):
            raise ValueError('Independent review coverage/binding mismatch')
        if report.get('reviewed_content_sha256')!={r['id']:review_content_digest(r) for r in rows}:
            raise ValueError('Published content differs from reviewed content')
        report_key = f'.local/financial-eight-actions-v2/review/{stem}-review.json'
        if manifest['source_bindings'].get(report_key)!=manifest['files'][f'reviews/{stem}-review.json']['sha256']:
            raise ValueError('Published review packet differs from its source binding')
        if any(identity(report['reviewer'])==identity(r['provenance']['producer']) for r in rows):
            raise ValueError('Self-approved data')
    groups = json.loads((folder/'groups.json').read_text(encoding='utf-8'))
    assignments = defaultdict(set)
    for item in groups.values():
        assignments[item['group']].add(item['split'])
    if any(len(v)!=1 for v in assignments.values()):
        raise ValueError('Group crosses partitions')
    for r in train+[r for s in SPLITS for r in evaluation[s]]:
        if groups[r['id']]!=dict(split=r['split'],family=r['scene_family_id'],group=r['curation']['partition_group']):
            raise ValueError('Group evidence differs from row')
    eval_rows = [r for s in SPLITS for r in evaluation[s]]
    parent_rows = [candidate(r) for p in sorted((parent/'parts').glob('part-*.jsonl')) for r in read_rows(p)]
    if summarize(parent_rows,train,eval_rows,catalog)!=manifest['stats']:
        raise ValueError('Row statistics mismatch')
    rebuilt_groups = joined_groups(deepcopy(parent_rows+train),deepcopy(eval_rows),catalog)
    if rebuilt_groups!=groups:
        raise ValueError('Group reconstruction differs from visible artifacts')
    overlap_pairs = json.loads((folder/'overlap-audit.json').read_text(encoding='utf-8'))['pairs']
    overlap_report = json.loads((folder/'reviews/overlap-review.json').read_text(encoding='utf-8'))
    if (overlap_report.get('decision')!='pass' or overlap_report.get('human_review') is not False
            or overlap_report.get('unresolved_findings')!=[]
            or overlap_report.get('pairs_sha256')!=v1.digest(overlap_pairs)
            or {tuple(p) for p in overlap_report.get('reviewed_pairs',[])}!={tuple(p['ids']) for p in overlap_pairs}):
        raise ValueError('Overlap evidence mismatch')
    check_budget(manifest['stats'], eval_rows)
    if verify_local:
        for name,value in manifest['source_bindings'].items():
            path = ROOT/name
            if ROOT.resolve() not in path.resolve().parents or sha(path)!=value:
                raise ValueError('Source/review/protocol changed: '+name)
        v1.validate(parent, verify_local=True)
        _, additions, original_evaluation, _, expected_groups, stats, pairs = assemble(True)
        if groups!=expected_groups or stats!=manifest['stats']:
            raise ValueError('Source reconstruction differs')
        original = {r['id']:r for r in additions+original_evaluation}
        for r in train+[r for s in SPLITS for r in evaluation[s]]:
            if any(r[k]!=original[r['id']][k] for k in v1.CONTENT_FIELDS):
                raise ValueError('Published row differs from independently reviewed source')
        verify_overlap_review(pairs)
    return manifest['stats']


def training_rows(folder=None):
    folder = Path(folder) if folder is not None else OUT
    validate(folder)
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    parent = ROOT/manifest['base_release']
    groups = json.loads((folder/'groups.json').read_text(encoding='utf-8'))
    rows = [r for p in sorted((parent/'parts').glob('part-*.jsonl')) for r in read_rows(p)]
    rows += read_rows(folder/'train-additions.jsonl')
    for r in rows:
        if r['split']!='train' or groups[r['id']]['split']!='train' or r.get('dataset_role')=='evaluation':
            raise ValueError('Evaluation cannot enter training adapter')
        yield dict(id=r['id'],group=groups[r['id']]['group'],input=serialize_input(r),
                   action=r['annotation']['action'], action_token=v1.LETTERS[r['annotation']['action']],
                   tool_name=r['annotation']['tool_name'], tool_arguments=r['annotation']['tool_arguments'],
                   retrieval_collection=r['annotation']['retrieval_collection'], missing_slots=r['annotation']['missing_slots'])


def evaluation_rows(split, folder=None, allow_final=False):
    if split not in SPLITS or (split=='final' and not allow_final):
        raise ValueError('Final requires explicit fixed-candidate evaluation access')
    folder = Path(folder) if folder is not None else OUT
    validate(folder)
    return json.loads((folder/f'evaluation/{split}.json').read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit','build','validate','export-training'])
    parser.add_argument('--verify-local', action='store_true')
    args = parser.parse_args()
    if args.command=='audit':
        audit()
    elif args.command=='build':
        build()
    elif args.command=='validate':
        print(json.dumps(validate(verify_local=args.verify_local), ensure_ascii=False, indent=2))
    else:
        v1.write_lf(LOCAL/'train-input-target.jsonl',training_rows())
        print('Saved .local/financial-eight-actions-v2/train-input-target.jsonl')


if __name__=='__main__':
    main()
