"""Materialize explicitly authored and independently reviewed label proposals.

This is a review packet, not a trainable release or a relabeler. The old input
schema remains intact until a separately reviewed migration is designed.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from qwenlab.common import ROOT, sha
from qwenlab.financial_contract_audit import training_sources

OUT = ROOT / 'data/financial-contract-revision-v2'
QUEUE = ROOT / 'data/financial-contract-audit-v1/review-queue.json'
DRAFT = ROOT / 'configs/financial-support-contract-draft-v2.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def row_sha(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def check_proposals(queue, proposals):
    source = {r['id']: r for r in queue}
    if len(proposals) != len(source) or len({r['id'] for r in proposals}) != len(source) or {r['id'] for r in proposals} != set(source):
        raise ValueError('Every queued row must have exactly one proposal')
    for p in proposals:
        old = source[p['id']]
        if p['source_row_sha256'] != old['source_row_sha256'] or p['decision'] not in ('retain', 'revise', 'quarantine'):
            raise ValueError('Invalid source binding or decision')
        if p.get('human_reviewed') is not False or p.get('reviewer_type') != 'ai_author' or p.get('training_eligible') is not False:
            raise ValueError('Review provenance and nontraining status must be explicit')
        if not isinstance(p['reason'], str) or len(p['reason']) < 8 or not p.get('evidence_paths'):
            raise ValueError('Missing specific review evidence')
        a = p['proposed_annotation']
        if p['decision'] == 'quarantine':
            if not isinstance(a, dict) or a.get('action') is not None or a.get('tool_name') is not None or a.get('tool_arguments') or a.get('retrieval_collection') is not None or a.get('missing_slots'):
                raise ValueError('Quarantined rows must not publish a new target')
            continue
        if set(a) != set(old['original_annotation']) or a['policy_version'] != 'financial-support-contract-draft-v2':
            raise ValueError('Incomplete or unversioned proposed annotation')
        if a['action'] not in ('clarify', 'retrieve', 'tool', 'answer', 'human', 'redirect', 'refuse', 'close'):
            raise ValueError('Invalid action')
        if a['action'] == 'tool':
            if not old['input']['state']['authenticated'] or a['tool_name'] not in old['input']['available_tools']:
                raise ValueError('Impossible tool target')
        elif a['tool_name'] is not None or a['tool_arguments']:
            raise ValueError('Non-tool action cannot carry a tool')
        if a['action'] == 'retrieve':
            if a['retrieval_collection'] not in old['input']['capabilities']['knowledge_collections']:
                raise ValueError('Unavailable retrieval collection')
        elif a['retrieval_collection'] is not None:
            raise ValueError('Non-retrieval action cannot carry a collection')
        if a['action'] != 'clarify' and a['missing_slots']:
            raise ValueError('Non-clarification action cannot carry missing slots')
        fields = ['action', 'tool_name', 'tool_arguments', 'retrieval_collection', 'missing_slots']
        changed = any(a[k] != old['original_annotation'][k] for k in fields)
        if changed != (p['decision'] == 'revise'):
            raise ValueError('Decision disagrees with actual target change')


def build():
    if (OUT / 'manifest.json').exists():
        raise FileExistsError('Version already built; validate or create a new version')
    queue, proposals, review = read(QUEUE), read(OUT / 'proposals.json'), read(OUT / 'independent-review.json')
    check_proposals(queue, proposals)
    if review.get('proposals_sha256') != sha(OUT / 'proposals.json') or review.get('draft_sha256') != sha(DRAFT):
        raise ValueError('Independent review must bind exact proposal and policy bytes')
    if review.get('reviewer_type') != 'independent_ai_reviewer' or review.get('human_reviewed') is not False:
        raise ValueError('Independent review provenance missing')
    if review.get('status') != 'pass' or review.get('approved_ids') != [p['id'] for p in proposals]:
        raise ValueError('Independent review must cover every proposal')
    sources, bindings = training_sources()
    source_map = {s['row']['id']: s['row'] for s in sources}
    ledger, candidates = [], []
    for p in proposals:
        original = source_map[p['id']]
        if row_sha(original) != p['source_row_sha256']:
            raise ValueError('Original row changed')
        ledger.append(dict(id=p['id'], source_scene_family_id=original.get('scene_family_id'),
                           original=deepcopy(original), proposal=deepcopy(p), training_eligible=False))
        if p['decision'] != 'quarantine':
            candidate = deepcopy(original)
            candidate['annotation'] = deepcopy(p['proposed_annotation'])
            candidate['split'] = 'train_candidate'
            candidate['usage'] = 'reviewed_label_proposal_only_requires_input_migration_and_full_release_review'
            candidate['training_eligible'] = False
            candidate['review'] = dict(status='independent_ai_reviewed_label_proposal',
                                      human_reviewed_current_version=False, source_row_sha256=p['source_row_sha256'])
            candidates.append(candidate)
    quarantine_groups = sorted({str(x['source_scene_family_id']) for x in ledger if x['proposal']['decision'] == 'quarantine'})
    related = [dict(id=s['row']['id'], scene_family_id=s['row'].get('scene_family_id')) for s in sources
               if str(s['row'].get('scene_family_id')) in quarantine_groups]
    write(OUT / 'ledger.json', ledger)
    write(OUT / 'reviewed-candidates.json', candidates)
    write(OUT / 'quarantine-groups.json', dict(groups=quarantine_groups, related_training_rows=related,
        note='Do not release a related group without resolving or isolating it as a whole; this packet is not a full training release.'))
    summary = dict(queue_rows=len(queue), decisions=dict(Counter(p['decision'] for p in proposals)),
                   candidate_rows=len(candidates), actions=dict(Counter(r['annotation']['action'] for r in candidates)),
                   quarantined_groups=len(quarantine_groups), related_rows=len(related), training_eligible=False,
                   input_migrated=False, evaluation_opened=False, model_calls=0)
    write(OUT / 'summary.json', summary)
    lines = ['# 逐条修订复核册', '', 'AI起草与独立AI复核；保留旧输入，只是新标签候选，不能直接训练。', '']
    for item in ledger:
        p, old = item['proposal'], item['original']
        new = p['proposed_annotation']
        lines += [f"## {old['id']}", '', f"处理：{p['decision']}；旧动作：{old['annotation']['action']}；建议：{new['action'] if new else '隔离'}。", '',
                  '```json', json.dumps(old['input'], ensure_ascii=False, indent=2), '```', '', p['reason'], '']
    (OUT / 'review.md').write_text('\n'.join(lines), encoding='utf-8')
    bindings[QUEUE.relative_to(ROOT).as_posix()] = sha(QUEUE)
    bindings[DRAFT.relative_to(ROOT).as_posix()] = sha(DRAFT)
    write(OUT / 'manifest.json', dict(training_eligible=False, source_files=bindings, code_sha256=sha(Path(__file__)),
        files={p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'manifest.json'}, summary=summary))
    print(json.dumps(summary, ensure_ascii=False))


def validate():
    m = read(OUT / 'manifest.json')
    if m['training_eligible'] or m['code_sha256'] != sha(Path(__file__)):
        raise ValueError('Unexpected eligibility or code drift')
    for name, digest in m['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Source changed: ' + name)
    for name, digest in m['files'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Review artifact changed: ' + name)
    check_proposals(read(QUEUE), read(OUT / 'proposals.json'))
    print('Review packet hashes and proposal structure verified; not a training release')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['build', 'validate'])
    build() if parser.parse_args().command == 'build' else validate()
