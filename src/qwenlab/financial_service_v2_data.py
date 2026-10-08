"""Versioned schema migration and independently authored evaluation packaging.

No training or model calls. Original sources are read-only. Dataset eligibility
remains false until a new executor and experiment protocol are reviewed.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
import re

from qwenlab.common import ROOT, sha
from qwenlab.financial_contract_audit import training_sources
from qwenlab.financial_contract_revision import validate as validate_revision, row_sha
from qwenlab.financial_serve_v2 import protocol, validate_input

OUT = ROOT / 'data/financial-service-v2'
LOCAL = ROOT / '.local/financial-service-v2'
SEMANTIC = ROOT / 'docs/evidence/financial-v2-migration-semantic-review.json'
REVISION = ROOT / 'data/financial-contract-revision-v2'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def groups(rows):
    parent = {r['id']: r['id'] for r in rows}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    tags = {}
    for r in rows:
        provenance = r.get('provenance', {})
        for kind, value in [('scene', r['scene_family_id']), ('partition', r.get('curation', {}).get('partition_group')),
                            ('partition', provenance.get('source_group') if provenance.get('source_group', '').startswith('FT-G-') else None)]:
            if value:
                tag = (kind, value)
                if tag in tags: union(r['id'], tags[tag])
                else: tags[tag] = r['id']
        for key in ['source_id', 'parent_id']:
            if provenance.get(key) in parent: union(r['id'], provenance[key])
    blocks = defaultdict(list)
    for r in rows: blocks[find(r['id'])].append(r['id'])
    return {rid: 'FSV2-G-' + hashlib.sha256('|'.join(sorted(ids)).encode()).hexdigest()[:20]
            for ids in blocks.values() for rid in ids}


def migrate_input(old):
    value = deepcopy(old)
    if value['capabilities']['handoff_connected'] is not False:
        raise ValueError('Ambiguous old connected=true cannot be migrated')
    value['capability_profile'] = {'planned-kb-v1': 'planned-kb', 'current-no-kb-v1': 'current-node-no-kb'}[value['capability_profile']]
    value['capabilities'] = dict(knowledge_collections=list(value['capabilities']['knowledge_collections']), handoff_available=False)
    value['state']['handoff_status'] = 'none'
    # This is a new deployment scenario assumption, not a semantic equivalence
    # between old connected and new availability. Keep the old row hash/ledger.
    return value


def check_row(row, spec):
    value = validate_input(row['input'], spec)
    a = row['annotation']
    if not isinstance(a['tool_arguments'],dict) or not isinstance(a['missing_slots'],list):
        raise ValueError('Tool arguments must be an object and missing slots a list')
    if a['policy_version'] != spec['version'] or a['action'] not in spec['actions']:
        raise ValueError('Wrong policy or action: ' + row['id'])
    if a['action'] == 'tool':
        tool = a['tool_name']; args = a['tool_arguments']
        if not value['state']['authenticated'] or tool not in value['available_tools']:
            raise ValueError('Impossible tool: ' + row['id'])
        required = {'applicationId'} if tool == 'queryApplicationDetail' else {'status'} if tool == 'explainApplicationStatus' else set()
        if not isinstance(args, dict) or set(args) != required:
            raise ValueError('Invalid tool arguments')
        if required == {'applicationId'} and (type(args['applicationId']) is not int or not 0 < args['applicationId'] <= 2147483647):
            raise ValueError('Invalid application id')
        if required == {'status'} and (type(args['status']) is not int or args['status'] not in (0, 1, 2)):
            raise ValueError('Invalid status code')
        for arg, field in [('applicationId', 'application_id'), ('status', 'status_code')]:
            if arg in args and field in value['state'] and args[arg] != value['state'][field]:
                raise ValueError('Tool target contradicts explicit trusted state: ' + row['id'])
    elif a['tool_name'] is not None or a['tool_arguments']:
        raise ValueError('Unexpected tool target')
    if a['action'] == 'retrieve':
        if a['retrieval_collection'] not in value['capabilities']['knowledge_collections']:
            raise ValueError('Unavailable knowledge')
    elif a['retrieval_collection'] is not None:
        raise ValueError('Unexpected retrieval target')
    if a['action'] != 'clarify' and a['missing_slots']:
        raise ValueError('Unexpected missing slots')


def summarize(rows):
    return dict(rows=len(rows), groups=len({r['scene_family_id'] for r in rows}),
                actions=dict(Counter(r['annotation']['action'] for r in rows)),
                cohorts=dict(Counter(r['cohort'] for r in rows)),
                cohort_actions={c: dict(Counter(r['annotation']['action'] for r in rows if r['cohort'] == c)) for c in sorted({r['cohort'] for r in rows})},
                profiles=dict(Counter(r['input']['capability_profile'] for r in rows)))


def build_train():
    if (OUT / 'train-manifest.json').exists(): raise FileExistsError('Train migration already frozen')
    validate_revision()
    sources, bindings = training_sources(); rows = [s['row'] for s in sources]; by_id = {r['id']: r for r in rows}
    spec, policy_hash = protocol()
    proposals = {r['id']: r for r in read(REVISION / 'proposals.json')}
    semantic = read(SEMANTIC)
    for name, digest in semantic['source_files'].items():
        if sha(ROOT/name) != digest: raise ValueError('Stale semantic review source: '+name)
    decisions = semantic['records']
    if semantic['evaluation_data_read'] is not False or semantic['human_reviewed'] is not False:
        raise ValueError('Review scope/provenance must be explicit')
    if len({r['id'] for r in decisions}) != len(decisions): raise ValueError('Duplicate semantic review id')
    for r in decisions:
        if r['source_row_sha256'] != row_sha(by_id[r['id']]) or r['decision'] not in ('keep', 'quarantine'):
            raise ValueError('Invalid semantic review binding')
    reviewed = {r['id']: r for r in decisions}
    membership = groups(rows)
    seeds = defaultdict(list)
    for r in rows:
        rid = r['id']
        if r['input']['capabilities']['handoff_connected']:
            seeds[membership[rid]].append(dict(id=rid, reason='ambiguous_legacy_handoff_connected_true'))
        if proposals.get(rid, {}).get('decision') == 'quarantine':
            seeds[membership[rid]].append(dict(id=rid, reason='reviewed_channel_intent_ambiguity'))
        if reviewed.get(rid, {}).get('decision') == 'quarantine':
            seeds[membership[rid]].append(dict(id=rid, reason='targeted_policy_audit_quarantine'))
    migrated, ledger = [], []
    for source in sources:
        old = source['row']; rid = old['id']; group = membership[rid]
        entry = dict(id=rid, source_file=source['source_file'], source_row_sha256=row_sha(old), source_scene_family_id=old['scene_family_id'],
                     scene_family_id=group, decision='exclude_group' if group in seeds else 'migrate', reasons=seeds.get(group, []))
        ledger.append(entry)
        if group in seeds: continue
        row = deepcopy(old)
        row['input'] = migrate_input(old['input']); row['scene_family_id'] = group
        if rid in proposals: row['annotation'] = deepcopy(proposals[rid]['proposed_annotation'])
        row['annotation']['policy_version'] = spec['version']
        row['cohort'] = ('preauth-robustness' if not row['input']['state']['authenticated'] else
                         'current-service' if row['input']['capability_profile'] == 'current-node-no-kb' else 'planned-retrieval')
        row['review'] = dict(status='schema_migrated_with_inherited_semantic_review', human_reviewed_current_version=False,
                             source_review=deepcopy(old['review']), explicit_label_revision=rid in proposals,
                             targeted_new_policy_review=rid in reviewed)
        row['migration'] = dict(source_row_sha256=entry['source_row_sha256'], source_id=rid, policy_sha256=policy_hash,
                                handoff_assumption='No connector and no in-session handoff in this version; legacy true groups excluded')
        row['training_eligible'] = False
        row['usage'] = 'versioned_training_candidate_requires_executor_and_experiment_review'
        check_row(row, spec); migrated.append(row)
    prior_excluded = {r['id'] for r in read(REVISION/'quarantine-groups.json')['related_training_rows']}
    if prior_excluded & {r['id'] for r in migrated}: raise ValueError('Prior quarantined group was accidentally released')
    write(OUT / 'train.json', migrated); write(OUT / 'migration-ledger.json', ledger)
    write(OUT / 'excluded-groups.json', dict(groups=dict(seeds), excluded_rows=sum(e['decision'] == 'exclude_group' for e in ledger)))
    summary = summarize(migrated)
    summary.update(source_rows=len(rows), excluded_rows=len(rows)-len(migrated), excluded_groups=len(seeds),
                   explicit_revisions_applied=sum(r['id'] in proposals and proposals[r['id']]['decision'] == 'revise' for r in migrated),
                   full_new_policy_semantic_review=False, training_eligible=False)
    write(OUT / 'train-summary.json', summary)
    for p in [SEMANTIC, REVISION/'manifest.json', REVISION/'proposals.json', ROOT/'configs/support-financial-v2.json',
              ROOT/'src/qwenlab/financial_prompt_v2.py', ROOT/'src/qwenlab/financial_serve_v2.py',
              ROOT/'src/qwenlab/financial_contract_audit.py', ROOT/'src/qwenlab/financial_contract_revision.py']:
        bindings[p.relative_to(ROOT).as_posix()] = sha(p)
    write(OUT / 'train-manifest.json', dict(policy_sha256=policy_hash, training_eligible=False, source_files=bindings,
          code_sha256=sha(Path(__file__)), files={p.name:sha(p) for p in OUT.iterdir() if p.name in ['train.json','migration-ledger.json','excluded-groups.json','train-summary.json']}))
    print(json.dumps(summary, ensure_ascii=False))


def normalized(text):
    return re.sub(r'\s+', '', re.sub(r'\d+', '#', text)).lower()


def text_key(row):
    return normalized(json.dumps([row['input']['message'], row['input']['history']], ensure_ascii=False, sort_keys=True))


def overlap_audit(train, evaluation):
    train_keys = defaultdict(list); train_messages = defaultdict(list)
    for r in train:
        train_keys[text_key(r)].append(r['id']); train_messages[normalized(r['input']['message'])].append(r['id'])
    exact, message_equal, near = [], [], []
    # Approximate screening: retrieve top20 by character trigram overlap, then
    # SequenceMatcher on message. It is not exhaustive semantic deduplication.
    index = defaultdict(set); texts = {}
    for r in train:
        t = normalized(r['input']['message']); texts[r['id']] = t
        for g in {t[i:i+3] for i in range(max(0, len(t)-2))}: index[g].add(r['id'])
    for r in evaluation:
        if text_key(r) in train_keys: exact.append(dict(evaluation_id=r['id'], training_ids=train_keys[text_key(r)]))
        t = normalized(r['input']['message'])
        if t in train_messages: message_equal.append(dict(evaluation_id=r['id'], training_ids=train_messages[t]))
        counts = Counter()
        for g in {t[i:i+3] for i in range(max(0, len(t)-2))}: counts.update(index.get(g, ()))
        for rid, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:20]:
            candidate = texts[rid]
            if candidate == t: continue
            score = difflib.SequenceMatcher(None, t, candidate, autojunk=False).ratio()
            if score >= .86: near.append(dict(evaluation_id=r['id'], training_id=rid, score=round(score,6)))
    cross = []
    for i, a in enumerate(evaluation):
        for b in evaluation[i+1:]:
            if a['split'] == b['split']: continue
            if text_key(a) == text_key(b): cross.append(dict(left=a['id'],right=b['id'],reason='exact_context'))
            elif normalized(a['input']['message']) == normalized(b['input']['message']):
                cross.append(dict(left=a['id'],right=b['id'],reason='same_message_different_history'))
    return dict(exact_context=exact, identical_message=message_equal, near_message=near, cross_split=cross,
                method='All exact normalized message/context checks; top20 trigram candidates per eval message for0.86 SequenceMatcher. Not semantic independence proof.')


def validate_train():
    spec,digest=protocol();m=read(OUT/'train-manifest.json')
    if m['code_sha256']!=sha(Path(__file__)) or m['policy_sha256']!=digest or m['training_eligible'] is not False:
        raise ValueError('Training code/policy/eligibility changed')
    for p,h in m['source_files'].items():
        if sha(ROOT/p)!=h:raise ValueError('Training source changed: '+p)
    for p,h in m['files'].items():
        if sha(OUT/p)!=h:raise ValueError('Training artifact changed: '+p)
    rows=read(OUT/'train.json')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate training id')
    for r in rows:
        if r['split']!='train' or r['training_eligible'] is not False:raise ValueError('Invalid migrated role')
        check_row(r,spec)
    return rows


def validate_evaluation_shape(evaluation):
    spec,_=protocol()
    if len(evaluation)!=384 or len({r['id'] for r in evaluation}) !=384: raise ValueError('Expected384 unique evaluation ids')
    groups_seen = defaultdict(set)
    for r in evaluation:
        check_row(r,spec)
        if r.get('dataset_role')!='evaluation' or r['training_eligible'] is not False or r['review']['human_reviewed_current_version'] is not False:
            raise ValueError('Evaluation role/provenance missing')
        groups_seen[r['scene_family_id']].add(r['split'])
        cohort=r['cohort'];value=r['input']
        if cohort=='preauth-robustness':
            if value['state']['authenticated']:raise ValueError('Preauth cohort is authenticated')
        elif cohort in ['current-service','planned-retrieval']:
            expected='current-node-no-kb' if cohort=='current-service' else 'planned-kb'
            if not value['state']['authenticated'] or value['capability_profile']!=expected:raise ValueError('Wrong evaluation capability cohort')
        else:raise ValueError('Unknown cohort')
    if any(len(s)!=1 for s in groups_seen.values()):raise ValueError('Evaluation family crosses splits')
    if Counter(r['split'] for r in evaluation)!=dict(development=128,calibration=96,final=160):raise ValueError('Unexpected split sizes')
    if any(n!=4 for n in Counter(r['scene_family_id'] for r in evaluation).values()):raise ValueError('Every independent story must contain4 cases')
    for split,size in [('development',128),('calibration',96),('final',160)]:
        block=[r for r in evaluation if r['split']==split];actions=Counter(r['annotation']['action'] for r in block)
        if set(actions)!=set(spec['actions']) or any(actions[a]<12 for a in ['human','refuse','tool']):raise ValueError('Insufficient action coverage')
        if {r['annotation']['tool_name'] for r in block if r['annotation']['action']=='tool'}!=set(spec['tools']):raise ValueError('Missing tool coverage')
        if Counter(r['cohort'] for r in block)!=dict(zip(['current-service','planned-retrieval','preauth-robustness'],[size//2,size//4,size//4])):raise ValueError('Wrong evaluation cohort sizes')


def prepare_evaluation():
    train = validate_train(); evaluation=read(LOCAL/'evaluation-author.json')
    validate_evaluation_shape(evaluation)
    report=overlap_audit(train,evaluation)
    report.update(train_sha256=sha(OUT/'train.json'),evaluation_sha256=sha(LOCAL/'evaluation-author.json'))
    write(LOCAL/'overlap-audit.json',report)
    print(json.dumps({k:len(report[k]) for k in ['exact_context','identical_message','near_message','cross_split']}))


def freeze_evaluation():
    if (OUT/'evaluation-manifest.json').exists():raise FileExistsError('Evaluation already frozen')
    train=validate_train()
    evaluation=read(LOCAL/'evaluation-author.json'); review=read(LOCAL/'evaluation-review.json'); overlap=read(LOCAL/'overlap-audit.json')
    validate_evaluation_shape(evaluation)
    if {r['id'] for r in train}&{r['id'] for r in evaluation} or {r['scene_family_id'] for r in train}&{r['scene_family_id'] for r in evaluation}:
        raise ValueError('Train and evaluation ids/groups intersect')
    if review.get('status')!='pass' or review.get('evaluation_sha256')!=sha(LOCAL/'evaluation-author.json') or review.get('human_reviewed') is not False:
        raise ValueError('Independent evaluation review missing/stale')
    if set(review.get('reviewed_ids',[]))!={r['id'] for r in evaluation} or not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip() or review['reviewer']=='/root/financial_v2_eval_author':
        raise ValueError('Independent reviewer must cover every row')
    if overlap['train_sha256']!=sha(OUT/'train.json') or overlap['evaluation_sha256']!=review['evaluation_sha256']:
        raise ValueError('Stale overlap audit')
    if overlap['exact_context'] or overlap['cross_split']:
        raise ValueError('Exact context or cross-split text collision unresolved')
    if overlap['identical_message'] or overlap['near_message']:
        resolution=read(LOCAL/'overlap-review.json')
        if resolution.get('status')!='pass' or resolution.get('audit_sha256')!=sha(LOCAL/'overlap-audit.json'):
            raise ValueError('Lexical similarity needs explicit independent resolution')
    spec,policy_hash=protocol()
    for r in evaluation:check_row(r,spec)
    for split in ['development','calibration','final']:
        write(OUT/(split+'.json'),[r for r in evaluation if r['split']==split])
    write(OUT/'evaluation-review.json',review);write(OUT/'overlap-audit.json',overlap)
    if (LOCAL/'overlap-review.json').exists():write(OUT/'overlap-review.json',read(LOCAL/'overlap-review.json'))
    write(OUT/'evaluation-author-evidence.json',read(LOCAL/'evaluation-author-evidence.json'))
    summary={s:summarize([r for r in evaluation if r['split']==s]) for s in ['development','calibration','final']}
    write(OUT/'evaluation-summary.json',summary)
    names=['development.json','calibration.json','final.json','evaluation-review.json','overlap-audit.json','overlap-review.json','evaluation-author-evidence.json','evaluation-summary.json']
    write(OUT/'evaluation-manifest.json',dict(policy_sha256=policy_hash,train_sha256=sha(OUT/'train.json'),training_eligible=False,
          code_sha256=sha(Path(__file__)),files={n:sha(OUT/n) for n in names if (OUT/n).exists()},
          limitation='Independently authored synthetic evaluation, not real traffic; no model outputs used for authoring/review.'))
    print(json.dumps(summary,ensure_ascii=False))


def validate():
    spec,digest=protocol()
    validate_train()
    for name in ['train-manifest.json','evaluation-manifest.json']:
        m=read(OUT/name)
        if m['code_sha256']!=sha(Path(__file__)) or m['policy_sha256']!=digest or m['training_eligible'] is not False:raise ValueError('Code/policy/eligibility changed')
        if name=='evaluation-manifest.json' and m['train_sha256']!=sha(OUT/'train.json'):raise ValueError('Evaluation no longer bound to training version')
        for p,h in m.get('source_files',{}).items():
            if sha(ROOT/p)!=h:raise ValueError('Source changed: '+p)
        for p,h in m['files'].items():
            if sha(OUT/p)!=h:raise ValueError('Artifact changed: '+p)
    for name in ['train','development','calibration','final']:
        for row in read(OUT/(name+'.json')):check_row(row,spec)
    validate_evaluation_shape([r for name in ['development','calibration','final'] for r in read(OUT/(name+'.json'))])
    print('V2 migrated data and independent evaluation bindings verified; training remains disabled')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build-train','prepare-evaluation','freeze-evaluation','validate'])
    {'build-train':build_train,'prepare-evaluation':prepare_evaluation,'freeze-evaluation':freeze_evaluation,'validate':validate}[parser.parse_args().command]()
