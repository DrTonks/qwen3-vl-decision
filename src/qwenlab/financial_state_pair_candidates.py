"""Versioned, training-disabled state contrasts projected by the actual Node adapter.

Build only from original story fixtures. No evaluation questions or predictions
are loaded here. Independent review and blind screening are separate evidence.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from uuid import uuid4

from qwenlab.common import ROOT, sha
from qwenlab.financial_serve_v2 import protocol
from qwenlab.financial_service_v2_data import check_row

DATA = ROOT / 'data/financial-state-pair-candidates-v1'
STORIES = DATA / 'stories.json'
DEFAULT_BACKEND = ROOT.parent / 'uestc_Integrated_Design/后端'
TOOLS = ['queryLoanProducts', 'queryMyApplications', 'queryApplicationDetail',
         'queryMyCreditScore', 'explainApplicationStatus']
ARTIFACTS = ['authoring.json', 'node-contexts.jsonl', 'node-projections.jsonl',
             'candidates.json', 'grounding.json', 'pairs.json', 'summary.json', 'REVIEW.md']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def differences(a, b, prefix=''):
    if isinstance(a, dict) and isinstance(b, dict):
        output = []
        for key in sorted(a.keys() | b.keys()):
            p = prefix + '.' + key if prefix else key
            output.extend([p] if key not in a or key not in b else differences(a[key], b[key], p))
        return output
    return [] if canonical(a) == canonical(b) else [prefix]


def author(stories):
    if len(stories) != 40 or len({s['id'] for s in stories}) != 40:
        raise ValueError('Expected 40 unique independent story fixtures')
    if Counter(s['tool'] for s in stories) != Counter({t: 8 for t in TOOLS}):
        raise ValueError('Expected eight stories for each supported tool')
    rows = []
    for story in stories:
        tool = story['tool']; group = 'FIN-SP1-' + story['id']
        detail = tool == 'queryApplicationDetail'; status = tool == 'explainApplicationStatus'
        if not isinstance(story['message'], str) or not story['message'].strip():
            raise ValueError('Nonempty message required')
        if detail and (type(story.get('application_id')) is not int or not 0 < story['application_id'] <= 2147483647):
            raise ValueError('Explicit valid synthetic application ID required')
        if status and (type(story.get('status')) is not int or story['status'] not in (0, 1, 2)
                       or not isinstance(story.get('missing_message'), str) or not story['missing_message'].strip()):
            raise ValueError('Status story requires code and missing-code text')
        base = dict(message=story['message'], history=[], authenticated=True,
                    state={'selectedApplicationId': story['application_id']} if detail else {}, availableTools=TOOLS.copy())
        for variant in ['ready', 'unauthenticated', 'unavailable'] + (['missing'] if detail or status else []):
            context = deepcopy(base)
            action, args, missing = 'tool', {}, []
            reason = '明确请求读取工具实际提供的信息；已认证且目标工具可用。'
            if detail: args = {'applicationId': story['application_id']}
            if status: args = {'status': story['status']}
            if variant == 'unauthenticated':
                context['authenticated'] = False
                action, args, missing = 'clarify', {}, ['authentication']
                reason = '冻结契约要求全部工具均须认证；先要求完成认证，不能凭用户文字声称已登录。'
            elif variant == 'unavailable':
                context['availableTools'].remove(tool)
                action, args = ('answer' if tool in ('queryLoanProducts', 'explainApplicationStatus') else 'human'), {}
                reason = ('公开目录或静态术语查询不涉及待处理的个人业务；目标工具和知识库均不可用，应如实说明限制，不编造查询结果。'
                          if action == 'answer' else '当前个人业务查询能力不可用且没有知识库；按契约选人工处理需求，不能声称转接已受理。')
            elif variant == 'missing':
                action, args = 'clarify', {}
                if detail:
                    context['state'] = {}; missing = ['application_id']
                    reason = '仅说这笔或那笔，当前消息没有编号且服务端没有所选对象，先补充申请编号。'
                else:
                    context['message'] = story['missing_message']; missing = ['status_code']
                    reason = '明确要查单个状态码定义但没有给出代码，先补充具体状态码。此样本改变文字，不是纯状态字段对。'
            rows.append(dict(id=group+'-'+variant, source_group=group, target_tool=tool, variant=variant,
                             context=context, expected_action=action, expected_tool=tool if action == 'tool' else None,
                             tool_arguments=args, missing_slots=missing, label_reason=reason))
    return rows


def materialize(authored, projected, spec):
    if len(authored) != len(projected): raise ValueError('Projection count changed')
    rows = []
    for source, actual in zip(authored, projected):
        if source['id'] != actual['id']: raise ValueError('Projection identity changed')
        annotation = dict(action=source['expected_action'], tool_name=source['expected_tool'],
                          tool_arguments=source['tool_arguments'], missing_slots=source['missing_slots'],
                          retrieval_collection=None, reason=source['label_reason'], policy_version=spec['version'],
                          evidence_paths=['input.message', 'input.state', 'input.available_tools'])
        row = dict(id=source['id'], scene_family_id=source['source_group'], split='candidate',
                   cohort='current-service' if actual['input']['state']['authenticated'] else 'preauth',
                   input_layer='node-projection', evaluation_layer=actual['evaluation_layer'],
                   target_tool=source['target_tool'], variant=source['variant'], input=actual['input'], annotation=annotation,
                   provenance=dict(origin='ai_synthetic', source_group=source['source_group'],
                       source_document='data/financial-state-pair-candidates-v1/stories.json',
                       source_row_sha256=hashlib.sha256(canonical(source).encode('utf-8')).hexdigest(),
                       basis=['configs/support-financial-v2.json', 'repo:uestc_Integrated_Design/后端/services/customerSupport/tools.js'],
                       licence_or_permission='Original synthetic text; no third-party dialogue copied.'),
                   projection=dict(input_adapter_version=actual['inputAdapterVersion'], node_input_sha256=actual['inputSha256'], transformations=[]),
                   review_status='author_annotated_pending_independent_review', human_reviewed=False, training_eligible=False)
        check_row(row, spec)
        # Generic schema permits message-only arguments; this package requires
        # every tool argument to survive the real adapter as trusted state.
        for arg, field in [('applicationId', 'application_id'), ('status', 'status_code')]:
            if arg in annotation['tool_arguments'] and row['input']['state'].get(field) != annotation['tool_arguments'][arg]:
                raise ValueError('Ungrounded parameter')
        rows.append(row)
    return rows


def pair_report(rows):
    groups = defaultdict(dict)
    for row in rows:
        if row['variant'] in groups[row['scene_family_id']]: raise ValueError('Duplicate variant')
        groups[row['scene_family_id']][row['variant']] = row
    pairs = []
    for group, variants in groups.items():
        ready = variants['ready']
        for kind, row in variants.items():
            if kind == 'ready': continue
            expected = {'unauthenticated': ['state.authenticated'], 'unavailable': ['available_tools'],
                        'missing': ['message', 'state.status_code'] if row['target_tool'] == 'explainApplicationStatus' else ['state.application_id']}[kind]
            changed = differences(ready['input'], row['input'])
            if changed != expected: raise ValueError('Unexpected contrast fields: ' + row['id'])
            negative = ('answer' if row['target_tool'] in ('queryLoanProducts', 'explainApplicationStatus') else 'human') if kind == 'unavailable' else 'clarify'
            if ready['annotation']['action'] != 'tool' or row['annotation']['action'] != negative:
                raise ValueError('Unexpected action direction')
            pairs.append(dict(scene_family_id=group, target_tool=row['target_tool'], variant=kind,
                              ids=[ready['id'], row['id']], changed_fields=changed, strict_single_field=len(changed) == 1))
    return pairs


def run_node(backend, output, authored):
    fixtures = output / 'node-contexts.jsonl'; projections = output / 'node-projections.jsonl'
    fixtures.write_text(''.join(json.dumps(dict(id=r['id'], context=r['context']), ensure_ascii=False)+'\n' for r in authored), encoding='utf-8')
    subprocess.run(['node', str(backend/'scripts/export-financial-input.cjs'), str(fixtures), str(projections)],
                   cwd=backend, capture_output=True, encoding='utf-8', check=True, timeout=60)
    return [json.loads(line) for line in projections.read_text(encoding='utf-8').splitlines()]


def render(rows, pairs):
    lines = ['# 可信状态对照候选复查表', '', 'AI原创合成，未经人工复核，未批准训练。同行仅共享故事，所有变体须整组留在训练侧。',
             '', '实际Node离线投影 ≠ 真实登录/数据库/端到端执行；未登录样本属于决策组件层。',
             '', '先查screening/review证据再选择候选；本文件仅是冻结作者稿。修改请复制为v2，不覆盖旧稿。', '']
    pair_by_group = defaultdict(list)
    for pair in pairs: pair_by_group[pair['scene_family_id']].append(pair)
    for row in rows:
        if row['variant'] == 'ready':
            lines += ['## '+row['scene_family_id'], '', '目标工具：`'+row['target_tool']+'`', '',
                      '对照变化：'+canonical(pair_by_group[row['scene_family_id']]), '']
        lines += ['### '+row['id'], '', '```json', json.dumps(row['input'], ensure_ascii=False, indent=2), '```', '',
                  '预标注：`'+row['annotation']['action']+'`；参数：`'+canonical(row['annotation']['tool_arguments'])+'`；缺项：`'+canonical(row['annotation']['missing_slots'])+'`',
                  '', row['annotation']['reason'], '']
    return '\n'.join(lines)


def generate(output, backend):
    authored = author(read(STORIES)); spec, policy_hash = protocol()
    if sha(backend/'services/customerSupport/policies/support-financial-v2.json') != policy_hash:
        raise ValueError('Backend/Python policy mismatch')
    output.mkdir(parents=True, exist_ok=False)
    (output/'authoring.json').write_bytes(encoded(authored))
    projected = run_node(backend, output, authored)
    rows = materialize(authored, projected, spec); pairs = pair_report(rows)
    (output/'candidates.json').write_bytes(encoded(rows))
    replay = subprocess.run(['node', str(ROOT/'scripts/replay-state-pair-decisions.cjs'), str(backend),
                              str(output/'authoring.json'), str(output/'candidates.json')], cwd=ROOT,
                             capture_output=True, encoding='utf-8', timeout=60, check=True)
    grounding = json.loads(replay.stdout)
    summary = dict(rows=len(rows), groups=len({r['scene_family_id'] for r in rows}),
                   actions=dict(Counter(r['annotation']['action'] for r in rows)),
                   strict_pairs=sum(p['strict_single_field'] for p in pairs),
                   supplemental_text_pairs=sum(not p['strict_single_field'] for p in pairs),
                   strict_by_variant=dict(Counter(p['variant'] for p in pairs if p['strict_single_field'])),
                   tool_rows=dict(Counter(r['target_tool'] for r in rows)),
                   actual_node_projected=len(projected), actual_query_guard_replayed=len(grounding),
                   history_turns=0, model_api_requests=0, training_eligible=False, human_reviewed=False,
                   independent_semantic_review='pending', blind_screen='pending')
    for name, value in [('pairs.json', pairs), ('grounding.json', grounding), ('summary.json', summary)]:
        (output/name).write_bytes(encoded(value))
    (output/'REVIEW.md').write_text(render(rows, pairs), encoding='utf-8')
    manifest = dict(version='financial-state-pair-candidates-v1', status='frozen_author_draft',
                    stories_sha256=sha(STORIES), policy_sha256=policy_hash,
                    source_sha256={p: sha(ROOT/p) for p in ['src/qwenlab/financial_state_pair_candidates.py', 'scripts/replay-state-pair-decisions.cjs']},
                    backend_source_sha256=projected[0]['sourceSha256'],
                    files={name: sha(output/name) for name in ARTIFACTS}, training_eligible=False, human_reviewed=False,
                    model_weights_loaded=False, model_api_requests=0, evaluation_text_used_for_authoring=False)
    (output/'manifest.json').write_bytes(encoded(manifest))
    return summary


def verify(output, backend):
    manifest = read(output/'manifest.json')
    if manifest['stories_sha256'] != sha(STORIES) or set(manifest['files']) != set(ARTIFACTS):
        raise ValueError('Stale story source or wrong evidence set')
    for name, digest in manifest['files'].items():
        if sha(output/name) != digest: raise ValueError('Evidence hash mismatch: '+name)
    scratch = ROOT/'.local'; scratch.mkdir(exist_ok=True)
    # Use normal inherited Windows ACLs; tempfile's private-directory mode can
    # make its own contents inaccessible under the desktop sandbox identity.
    regenerated = scratch/('state-pair-replay-'+uuid4().hex)
    generate(regenerated, backend)
    for name in ARTIFACTS + ['manifest.json']:
        if (output/name).read_bytes() != (regenerated/name).read_bytes():
            raise ValueError('Replay differs: '+name)
    return dict(status='pass', replay_files=len(ARTIFACTS)+1, training_eligible=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'verify'])
    parser.add_argument('--output', type=Path, default=DATA/'build')
    parser.add_argument('--backend', type=Path, default=DEFAULT_BACKEND)
    args = parser.parse_args(); output = args.output.resolve(); backend = args.backend.resolve()
    if not output.is_relative_to(ROOT.resolve()): raise ValueError('Output must be within repository')
    result = generate(output, backend) if args.command == 'build' else verify(output, backend)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
