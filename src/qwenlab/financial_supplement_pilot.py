"""Offline authored candidate packaging. Never trains or promotes eligibility."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

from qwenlab.common import ROOT
from qwenlab.financial_serve_v2 import protocol
from qwenlab.financial_service_v2_data import check_row

DATA = ROOT / 'data/financial-supplement-pilot-v1'
COHORTS = {'current-service': 120, 'planned-retrieval': 24, 'preauth-robustness': 16}
FIELDS = {'id', 'source_group', 'cohort', 'input_layer', 'context', 'expected_action', 'expected_tool',
          'tool_arguments', 'missing_slots', 'retrieval_collection', 'label_reason'}
BUILD_FILES = ['node-contexts.jsonl', 'node-projections.jsonl', 'candidates.json', 'REVIEW.md', 'summary.json']
MANIFEST_FIELDS = {'version', 'status', 'source_sha256', 'policy_sha256', 'files', 'code_sha256', 'training_eligible',
                   'human_reviewed', 'model_weights_loaded', 'model_api_requests', 'evaluation_text_used_for_authoring'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def validate_source(rows):
    if not isinstance(rows, list) or len(rows) != 160:
        raise ValueError('Pilot must contain 160 authored rows')
    if len({r['id'] for r in rows}) != 160:
        raise ValueError('Duplicate authored ID')
    if Counter(r['cohort'] for r in rows) != COHORTS:
        raise ValueError('Unexpected cohort counts')
    groups = Counter(r['source_group'] for r in rows)
    if len(groups) < 40 or max(groups.values()) > 4:
        raise ValueError('Source groups must not be oversized')
    for row in rows:
        if set(row) != FIELDS or not re.fullmatch(r'FSP1-[A-Z]\d{2}-[12]', row['id']):
            raise ValueError('Invalid authored fields or ID')
        if not re.fullmatch(r'FSP1-G-[A-Z]\d{2}', row['source_group']) or row['source_group'] != 'FSP1-G-' + row['id'].split('-')[1]:
            raise ValueError('Invalid source group')
        layers = {'current-service': ['node-projection', 'component-message-only'],
                  'planned-retrieval': ['planned-capability-component'], 'preauth-robustness': ['preauth-component']}
        if row['input_layer'] not in layers[row['cohort']]:
            raise ValueError('Incorrect input layer')
        if row['context']['authenticated'] is not (row['cohort'] != 'preauth-robustness'):
            raise ValueError('Incorrect authentication cohort')
        if not isinstance(row['label_reason'], str) or len(row['label_reason'].strip()) < 10:
            raise ValueError('Missing annotation rationale')
        if not isinstance(row['missing_slots'], list) or any(not isinstance(x, str) for x in row['missing_slots']):
            raise ValueError('Invalid missing slots')
    current = [r for r in rows if r['cohort'] == 'current-service']
    if Counter(r['input_layer'] for r in current) != {'node-projection': 90, 'component-message-only': 30}:
        raise ValueError('Current-service input-layer budget differs from 90/30')


def materialize(source, projected, spec):
    if projected['id'] != source['id']:
        raise ValueError('Projection identity mismatch')
    value = deepcopy(projected['input'])
    transformations = []
    if source['input_layer'] == 'component-message-only':
        for field in ['application_id', 'status_code']:
            if field in value['state']:
                transformations.append('remove_state.' + field)
                del value['state'][field]
        # Removing a referential slot must not remove the only source of the target.
        for arg in source['tool_arguments'].values():
            if not re.search(r'(?<!\d)' + re.escape(str(arg)) + r'(?!\d)', value['message']):
                raise ValueError('Component target not visible in message')
    if source['cohort'] == 'planned-retrieval':
        value['capability_profile'] = 'planned-kb'
        value['capabilities']['knowledge_collections'] = [source['retrieval_collection'] or 'loan_service_docs']
        transformations.append('declare_planned_knowledge_collection')
    action, tool = source['expected_action'], source['expected_tool']
    if action == 'tool':
        for arg, field in [('applicationId', 'application_id'), ('status', 'status_code')]:
            if arg in source['tool_arguments'] and projected['input']['state'].get(field) != source['tool_arguments'][arg]:
                raise ValueError('Expected tool parameter disagrees with actual Node projection: ' + source['id'])
    row = dict(id=source['id'], scene_family_id=source['source_group'], split='candidate', cohort=source['cohort'],
               input_layer=source['input_layer'], input=value,
               annotation=dict(action=action, tool_name=tool, tool_arguments=source['tool_arguments'],
                               missing_slots=source['missing_slots'], retrieval_collection=source['retrieval_collection'],
                               reason=source['label_reason'], evidence_paths=['input.message', 'input.state', 'input.capabilities', 'input.history'],
                               policy_version=spec['version']),
               provenance=dict(origin='ai_synthetic', source_id=source['id'], source_group=source['source_group'],
                               source_document='authoring.json', licence_or_permission='Original synthetic text authored for this user-requested project; no third-party dataset copied.',
                               basis=['configs/support-financial-v2.json', 'repo:uestc_Integrated_Design/后端/services/customerSupport/tools.js'],
                               source_row_sha256=hashlib.sha256(json.dumps(source, ensure_ascii=False, sort_keys=True).encode()).hexdigest()),
               projection=dict(input_adapter_version=projected['inputAdapterVersion'], node_input_sha256=projected['inputSha256'],
                               transformations=transformations),
               review_status='author_annotated_pending_independent_review', human_reviewed=False, training_eligible=False)
    check_row(row, spec)
    return row


def summary(rows):
    return dict(rows=len(rows), groups=len({r['scene_family_id'] for r in rows}),
                cohorts=dict(Counter(r['cohort'] for r in rows)), actions=dict(Counter(r['annotation']['action'] for r in rows)),
                cohort_actions={c: dict(Counter(r['annotation']['action'] for r in rows if r['cohort'] == c)) for c in COHORTS},
                layers=dict(Counter(r['input_layer'] for r in rows)),
                tools=dict(Counter(r['annotation']['tool_name'] for r in rows if r['annotation']['action'] == 'tool')),
                training_eligible_rows=sum(r['training_eligible'] for r in rows))


def render_review(rows, authoring):
    by_id = {r['id']: r for r in authoring}
    lines = ['# 首批160条金融客服候选复查', '', '来源：AI原创合成；当前仅作者标注，尚非独立复核或人工复核。全部不可直接训练。',
             '', '修改上一级 `authoring.json`，不要仅修改本Markdown。重建必须使用新输出目录。相同source_group不得跨训练/评估拆分。', '']
    for row in rows:
        a = row['annotation']; context = by_id[row['id']]['context']
        lines += [f"## {row['id']} · {a['action']}" , '',
                  f"场景：{row['cohort']}；输入层：{row['input_layer']}；来源组：{row['scene_family_id']}", '',
                  f"当前消息：{row['input']['message']}", '',
                  '```json', json.dumps(dict(history=row['input']['history'], server_state=context['state'], model_state=row['input']['state'],
                                             capabilities=row['input']['capabilities'], available_tools=row['input']['available_tools']), ensure_ascii=False, indent=2), '```', '',
                  f"标注：工具={a['tool_name']}；参数={json.dumps(a['tool_arguments'],ensure_ascii=False)}；知识集合={a['retrieval_collection']}；缺槽={json.dumps(a['missing_slots'],ensure_ascii=False)}", '',
                  '理由：' + a['reason'], '', '- [ ] 动作符合完整语义、认证和能力', '- [ ] 工具/参数/知识集合可成立',
                  '- [ ] 与配对场景一致，无歧义或需隔离项', '']
    return '\n'.join(lines) + '\n'


def build(backend, output):
    backend, output = Path(backend).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Use a new build directory; old evidence is immutable')
    source = DATA / 'authoring.json'; authored = read(source); validate_source(authored)
    exporter = backend / 'scripts/export-financial-input.cjs'
    if not exporter.is_file(): raise FileNotFoundError('Missing actual Node exporter')
    spec, policy_hash = protocol()
    if sha(backend / 'services/customerSupport/policies/support-financial-v2.json') != policy_hash:
        raise ValueError('Node and Python policies differ')
    output.mkdir(parents=True)
    fixtures = output / 'node-contexts.jsonl'; projection = output / 'node-projections.jsonl'
    fixtures.write_text(''.join(json.dumps(dict(id=r['id'],context=r['context']),ensure_ascii=False)+'\n' for r in authored),encoding='utf-8')
    result = subprocess.run(['node', str(exporter), str(fixtures), str(projection)], cwd=backend,
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    if result.returncode:
        raise RuntimeError('Node projection failed; no candidates published: ' + result.stderr[:400])
    projected = [json.loads(line) for line in projection.read_text(encoding='utf-8').splitlines()]
    if len(projected) != len(authored): raise ValueError('Projection row count mismatch')
    rows = [materialize(a, p, spec) for a, p in zip(authored, projected)]
    write(output / 'candidates.json', rows)
    (output / 'REVIEW.md').write_text(render_review(rows, authored), encoding='utf-8')
    write(output / 'summary.json', summary(rows))
    write(output / 'manifest.json', dict(version='financial-supplement-pilot-v1', status='draft_pending_review',
          source_sha256=sha(source), policy_sha256=policy_hash, files={f: sha(output/f) for f in BUILD_FILES},
          code_sha256=sha(Path(__file__)), training_eligible=False, human_reviewed=False,
          model_weights_loaded=False, model_api_requests=0, evaluation_text_used_for_authoring=False))
    print(json.dumps(summary(rows), ensure_ascii=False))


def verify(output, backend):
    output = Path(output); manifest = read(output / 'manifest.json')
    if set(manifest) != MANIFEST_FIELDS or set(manifest['files']) != set(BUILD_FILES):
        raise ValueError('Manifest requires the exact known fields and file set')
    if manifest['version'] != 'financial-supplement-pilot-v1' or manifest['status'] != 'draft_pending_review':
        raise ValueError('Unknown manifest version/status')
    if any(manifest[k] is not False for k in ['training_eligible','human_reviewed','model_weights_loaded','evaluation_text_used_for_authoring']) or type(manifest['model_api_requests']) is not int or manifest['model_api_requests'] != 0:
        raise ValueError('Draft cannot claim eligibility/review or model work')
    if manifest['source_sha256'] != sha(DATA / 'authoring.json'):
        raise ValueError('Editable source changed: rebuild into a new directory')
    if manifest['code_sha256'] != sha(Path(__file__)) or manifest['policy_sha256'] != protocol()[1]:
        raise ValueError('Code/policy differs from this build')
    for name, digest in manifest['files'].items():
        if sha(output / name) != digest: raise ValueError('Build output edited: ' + name)
    authored = read(DATA/'authoring.json'); validate_source(authored)
    contexts = [json.loads(line) for line in (output/'node-contexts.jsonl').read_text(encoding='utf-8').splitlines()]
    if contexts != [dict(id=r['id'], context=r['context']) for r in authored]:
        raise ValueError('Contexts differ from the editable authored source')
    backend = Path(backend).resolve()
    if sha(backend/'services/customerSupport/policies/support-financial-v2.json') != protocol()[1]:
        raise ValueError('Actual Node policy changed')
    # Recompute with the actual backend rather than trusting saved projection hashes.
    scratch = ROOT/'.local/supplement-verification'/uuid.uuid4().hex
    scratch.mkdir(parents=True)
    fresh = scratch/'node.jsonl'
    try:
        run = subprocess.run(['node',str(backend/'scripts/export-financial-input.cjs'),str((output/'node-contexts.jsonl').resolve()),str(fresh)],
                             cwd=backend,capture_output=True,text=True,encoding='utf-8',timeout=60)
        if run.returncode: raise ValueError('Actual Node projection replay failed')
        projected = [json.loads(line) for line in fresh.read_text(encoding='utf-8').splitlines()]
    finally:
        if fresh.exists(): fresh.unlink()
        scratch.rmdir()
    saved = [json.loads(line) for line in (output/'node-projections.jsonl').read_text(encoding='utf-8').splitlines()]
    if projected != saved or len(projected) != len(authored):
        raise ValueError('Node source hashes or projected inputs changed; use a new build')
    expected = [materialize(a,p,protocol()[0]) for a,p in zip(authored,projected)]
    rows = read(output/'candidates.json')
    if rows != expected: raise ValueError('Candidates do not reproduce from authored source and actual Node')
    if read(output/'summary.json') != summary(rows) or (output/'REVIEW.md').read_text(encoding='utf-8') != render_review(rows,authored):
        raise ValueError('Summary/review does not reproduce')
    return rows


def audit(output, backend, tokenize=False):
    """No held-out corpus read: lexical audit within candidates only."""
    output = Path(output); rows = verify(output, backend)
    if (output/'audit.json').exists(): raise FileExistsError('Audit exists; preserve it')
    normalized = {}; duplicates = []
    for r in rows:
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', re.sub(r'\d+', '#', r['input']['message']).lower())
        key = (text, json.dumps(r['input']['history'], ensure_ascii=False, sort_keys=True))
        if key in normalized: duplicates.append([normalized[key], r['id']])
        normalized[key] = r['id']
    report = dict(status='pass' if not duplicates else 'needs_review', scope='structure_and_internal_lexical_duplicates',
                  independent_semantic_review=False, external_overlap_review='pending', candidate_sha256=sha(output/'candidates.json'),
                  numeric_normalized_duplicates=duplicates, model_weights_loaded=False, model_api_requests=0,
                  heldout_files_read=False, training_eligible=False)
    if tokenize:
        from transformers import AutoTokenizer
        from qwenlab.financial_prompt_v2 import encode
        tokenizer = AutoTokenizer.from_pretrained(ROOT/'models/Qwen3.5-0.8B', local_files_only=True)
        lengths = {'action': [], 'tool': []}
        for row in rows:
            for task in ['action'] + (['tool'] if row['annotation']['action'] == 'tool' else []):
                encoded = encode(tokenizer, row, task, max_tokens=2048)
                lengths[task].append(len(encoded['tokens']['input_ids']))
        report['tokens'] = {k: dict(count=len(v), maximum=max(v), minimum=min(v), mean=round(sum(v)/len(v),2)) for k,v in lengths.items()}
        report['no_truncation'] = True
    write(output/'audit.json', report)
    print(json.dumps(report, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['build','verify','audit'])
    p.add_argument('--backend', required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--tokenize',action='store_true')
    args = p.parse_args()
    if args.command == 'build':
        build(args.backend,args.output)
    elif args.command == 'verify': print(json.dumps(summary(verify(args.output,args.backend)),ensure_ascii=False))
    else: audit(args.output,args.backend,args.tokenize)


if __name__ == '__main__': main()
