"""Build auditable project scenario drafts without models, DB access or API calls.

The Node bridge uses the production input normalizer, guards and argument
grounding. Code checks feasibility, not the semantic truth of AI labels.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from qwenlab.common import ROOT
from qwenlab.support_review import validate_case, write_csv
from qwenlab.support_scenario_catalog import cards
from qwenlab.support_challenge_catalog import cards as challenge_cards

VERSION = 'support-curriculum-v1'
DEV = {'F01', 'F08', 'F10', 'F14', 'F25', 'F30'}
CALIBRATION = {'F02', 'F04', 'F05', 'F11', 'F17', 'F26'}
DEFERRED_POLICIES = {'P04', 'P05', 'P06'}
SOURCES = {
    'tools': '后端/services/customerSupport/tools.js',
    'policy': '后端/services/customerSupport/policies/decision-v5.json',
    'adapter': '后端/services/customerSupport/modelDecision.js',
    'parameters': '后端/services/customerSupport/parameters.js',
    'guards': '后端/services/customerSupport/decisions.js',
    'contract': '后端/services/customerSupport/contract.js',
    'orchestrator': '后端/services/customerSupport/orchestrator.js',
    'seed': '后端/db/seedLoanProduct.js',
    'apply': 'Uni-ui/pages/apply/index.vue',
    'orders': 'Uni-ui/pages/myorder/index.vue',
    'detail': 'Uni-ui/pages/myorder/detail.vue',
    'materials': 'Uni-ui/pages/myorder/supplement-material.vue',
    'credit': 'Uni-ui/pages/profile/credit.vue',
}
NEUTRAL_HISTORY = [
    {'role': 'user', 'content': '稍等，我先看一下页面。'},
    {'role': 'assistant', 'content': '好的，你可以继续描述问题。'},
]

BRIDGE = r"""
const fs = require('fs'), path = require('path');
const root = process.argv[1];
const {modelInput, toDecision} = require(path.join(root, '后端/services/customerSupport/modelDecision'));
const {definitions} = require(path.join(root, '后端/services/customerSupport/tools'));
const {groundDecision, validateDecision} = require(path.join(root, '后端/services/customerSupport/contract'));
const {safetyDecision} = require(path.join(root, '后端/services/customerSupport/decisions'));
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
const outputs = rows.map(row => {
  const context = {message: row.message, history: row.history, state: row.state, tools: definitions};
  let mapped = null;
  if (row.expected.route) {
    const e = row.expected;
    mapped = groundDecision(validateDecision(toDecision({route: {choice: e.route},
      intent: {choice: e.intent}, tool: {choice: e.tool || 'none'}}, context)), context);
  }
  return {id: row.id, input: modelInput(context), guard: safetyDecision(row.message), mapped};
});
process.stdout.write(JSON.stringify(outputs));
"""


def digest(path):
    # These inputs are text. Git on Windows may convert LF to CRLF; hash their
    # LF-normalized bytes so a clean checkout does not invalidate the manifest.
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def read_rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def write_rows(path, rows):
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).lower()
                   if unicodedata.category(c)[0] not in {'P', 'Z', 'C'})


def split_for(family):
    if family.startswith('X'):
        return 'challenge'
    return 'development' if family in DEV else 'calibration' if family in CALIBRATION else 'train'


def build_rows(catalog=None, augment=True):
    catalog = cards() if catalog is None else catalog
    rows = []
    for card in catalog:
        if len(card['messages']) != 5 or len(card['history']) > 2:
            raise ValueError(f'Card must have five authored messages and at most two history turns: {card["id"]}')
        for index, message in enumerate(card['messages'], 1):
            for context_variant in (('base', 'neutral_history') if augment else ('base',)):
                row = {
                    'id': f'{card["id"]}-{index:02d}-{context_variant}',
                    'group': card['family'], 'card_id': card['id'], 'title': card['title'],
                    'split': split_for(card['family']), 'source_ids': card['sources'],
                    'message': message,
                    'history': deepcopy((NEUTRAL_HISTORY if context_variant == 'neutral_history' else []) + card['history']),
                    'state': deepcopy(card['state']), 'expected': deepcopy(card['expected']),
                    'rationale': card['rationale'], 'discussion': card['discussion'],
                    'authored_utterance_id': f'{card["id"]}-{index:02d}',
                    'augmentation': context_variant,
                    'review': {'status': 'ai_preannotated', 'reviewer': '', 'notes': '', 'taxonomy_approved': False},
                }
                validate_case(row)
                rows.append(row)
    validate_structure(rows)
    return rows


def validate_structure(rows):
    ids, families, messages, inputs = set(), {}, {}, {}
    for row in rows:
        validate_case(row)
        if row['id'] in ids:
            raise ValueError('Duplicate ID: ' + row['id'])
        ids.add(row['id'])
        family, split = row['group'], row['split']
        if split not in {'train', 'development', 'calibration', 'challenge'} or split != split_for(family):
            raise ValueError('Family split changed: ' + family)
        if families.setdefault(family, split) != split:
            raise ValueError('Family crosses split: ' + family)
        message = normalize(row['message'])
        if messages.setdefault(message, split) != split:
            raise ValueError('Normalized utterance crosses split: ' + row['id'])
        key = json.dumps({k: row[k] for k in ('message', 'history', 'state')}, sort_keys=True, ensure_ascii=False)
        label = row['expected']
        if key in inputs and inputs[key] != label:
            raise ValueError('Identical observable context has conflicting labels: ' + row['id'])
        inputs[key] = label
    return True


def normalize_with_backend(project, rows):
    result = subprocess.run(['node', '-e', BRIDGE, str(Path(project).resolve())],
                            input=json.dumps(rows, ensure_ascii=False), text=True,
                            encoding='utf-8', capture_output=True, check=True, timeout=45)
    outputs = json.loads(result.stdout)
    if [r['id'] for r in outputs] != [r['id'] for r in rows]:
        raise ValueError('Backend bridge changed row order/IDs')
    return outputs


def same_decision(expected, actual):
    return bool(actual) and all((expected.get(k) or default) == (actual.get(k) or default)
                                for k, default in (('action', None), ('tool', None), ('arguments', {})))


def audit_candidates(rows, observations, regression_rows):
    old_texts = {}
    for name, old in regression_rows.items():
        for row in old:
            old_texts.setdefault(normalize(row['message']), set()).add(name)
    report, candidates, observable_inputs = [], [], {}
    for row, observation in zip(rows, observations, strict=True):
        if row['id'] != observation['id']:
            raise ValueError('Observation ID mismatch')
        observable = json.dumps(observation['input'], ensure_ascii=False, sort_keys=True)
        supervision = {key: row['expected'][key] for key in ('route', 'intent', 'tool')}
        previous = observable_inputs.setdefault(observable, (row['split'], supervision))
        if previous[0] != row['split']:
            raise ValueError('Normalized model input crosses splits: ' + row['id'])
        if previous[1] != supervision:
            raise ValueError('Normalized model input has conflicting labels: ' + row['id'])
        held = []
        if row['expected']['route'] is None:
            held.append('outside_current_four_routes')
        if row['discussion'] in DEFERRED_POLICIES:
            held.append('policy_discussion:' + row['discussion'])
        if observation['guard'] and not same_decision(row['expected'], observation['guard']):
            held.append('guard_conflicts_with_proposed_action')
        if row['expected']['route'] and not same_decision(row['expected'], observation['mapped']):
            held.append('unrepresentable_by_current_adapter')
        overlaps = sorted(old_texts.get(normalize(row['message']), []))
        if overlaps:
            held.append('seen_regression_utterance')
        report.append({'id': row['id'], 'split': row['split'], 'held_reasons': held,
                       'regression_overlaps': overlaps, 'guard': observation['guard'],
                       'runtime_path': 'guard' if observation['guard'] else 'model',
                       'mapped_with_proposed_label': observation['mapped'],
                       'eligible_for_draft_experiment': not held})
        if not held:
            e = row['expected']
            candidates.append({'id': row['id'], 'group': row['group'], 'dataset': 'business',
                               'split': row['split'], **observation['input'],
                               'labels': {'intent': e['intent'], 'route': e['route'],
                                          'tool': e['tool'] or 'none',
                                          'needs_human': 'yes' if e['route'] == 'human' else 'no'},
                               'label_status': 'ai_preannotated_offline_experiment',
                               'runtime_path': 'guard' if observation['guard'] else 'model',
                               'usage': 'evaluation_only' if row['split'] == 'challenge' else 'offline_experiment_only'})
    return report, candidates


def coverage(candidates):
    routes = {'tool', 'clarify', 'llm', 'human'}
    tools = {'queryLoanProducts', 'queryMyApplications', 'queryApplicationDetail',
             'queryMyCreditScore', 'explainApplicationStatus'}
    report = {}
    for split in ('train', 'development', 'calibration'):
        subset = [r for r in candidates if r['split'] == split]
        missing_routes = routes - {r['labels']['route'] for r in subset}
        missing_tools = tools - {r['labels']['tool'] for r in subset if r['labels']['route'] == 'tool'}
        report[split] = {'missing_routes': sorted(missing_routes), 'missing_tools': sorted(missing_tools)}
        if missing_routes or missing_tools:
            raise ValueError('Filtered candidates lack route/tool coverage: ' + split)
    return report


def source_snapshot(project):
    project = Path(project)
    return {key: {'path': path, 'sha256': digest(project / path)} for key, path in SOURCES.items()}


def render_cards(catalog):
    lines = ['# 客服场景卡：全AI生成的离线实验材料', '',
             '60张卡、30个场景族。每卡5条起草问法，另加一组无关前置历史形成上下文对照；不是600个独立场景。', '',
             '先阅读 docs/18 的实验政策；不需要组员试玩或人工标注，不将AI标签声称为人工金标。', '']
    for card in catalog:
        e = card['expected']
        lines += [f'## {card["id"]} {card["title"]}', '',
                  f'- 集合：`{split_for(card["family"])}`；场景族：`{card["family"]}`。',
                  f'- 业务依据：{", ".join(card["sources"])}（路径和哈希见 source-snapshot.json）。',
                  f'- 服务端状态：`{json.dumps(card["state"], ensure_ascii=False)}`。',
                  f'- 前置对话：`{json.dumps(card["history"], ensure_ascii=False)}`。',
                  f'- 建议：`{e["action"]}` / `{e["tool"] or "无工具"}` / `{json.dumps(e["arguments"], ensure_ascii=False)}`。',
                  f'- 理由：{card["rationale"]}',
                  f'- 政策备注：{card["discussion"] or "沿用当前能力边界的AI实验标签"}。', '',
                  *[f'{i}. {message}' for i, message in enumerate(card['messages'], 1)], '']
    return '\n'.join(lines)


def build(project, output, regression_paths=None):
    project, output = Path(project).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing draft or human edits; choose a new output directory')
    if output == project or project in output.parents:
        raise ValueError('Curriculum outputs belong in the experiment repository, not the application repository')
    catalog = cards()
    rows = build_rows(catalog)
    challenge = build_rows(challenge_cards(), augment=False)
    validate_structure(rows + challenge)
    sources = source_snapshot(project)
    local_policy = ROOT / 'configs/decision-v5.json'
    if json.loads(local_policy.read_text(encoding='utf-8')) != json.loads((project / SOURCES['policy']).read_text(encoding='utf-8')):
        raise ValueError('Runtime and experiment policies differ; settle the contract before creating training candidates')
    paths = regression_paths if regression_paths is not None else [
        ROOT / 'data/support-runtime-v1/cases.jsonl',
        ROOT / 'data/processed/v5/business-test.jsonl',
    ]
    regression, regression_meta = {}, {}
    for index, path in enumerate(paths):
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError('Required regression corpus missing: ' + path.name)
        key = f'regression-{index + 1}:{path.name}'
        regression[key] = read_rows(path)
        regression_meta[key] = {'sha256': digest(path), 'count': len(regression[key])}
    observations = normalize_with_backend(project, rows + challenge)
    audit, candidates = audit_candidates(rows + challenge, observations, regression)
    coverage_report = coverage(candidates)
    output.mkdir(parents=True)
    write_rows(output / 'cards.jsonl', catalog)
    write_rows(output / 'cases.jsonl', rows)
    write_rows(output / 'challenge-cards.jsonl', challenge_cards())
    write_rows(output / 'challenge-cases.jsonl', challenge)
    write_rows(output / 'challenge-model-candidates.jsonl', [r for r in candidates if r['split'] == 'challenge'])
    write_rows(output / 'runtime-inputs.jsonl', observations)
    write_rows(output / 'eligibility.jsonl', audit)
    for split in ('train', 'development', 'calibration'):
        write_rows(output / f'{split}-cases.jsonl', [r for r in rows if r['split'] == split])
        write_rows(output / f'{split}-candidates.jsonl', [r for r in candidates if r['split'] == split])
    write_csv(output / 'review.csv', rows)
    write_json(output / 'source-snapshot.json', sources)
    (output / '场景卡.md').write_text(render_cards(catalog), encoding='utf-8')
    manifest = {
        'version': VERSION, 'status': 'ai_preannotated_offline_experiment',
        'hash_algorithm': 'sha256_after_CRLF_to_LF',
        'training_started': False, 'public_data_downloaded': False,
        'card_count': len(catalog), 'family_count': len({r['group'] for r in rows}),
        'authored_slots': len({r['authored_utterance_id'] for r in rows}),
        'unique_normalized_messages': len({normalize(r['message']) for r in rows}),
        'case_count': len(rows), 'split_counts': dict(Counter(r['split'] for r in rows)),
        'challenge_count': len(challenge), 'challenge_families': len(challenge_cards()),
        'actions': dict(Counter(r['expected']['action'] for r in rows)),
        'draft_candidate_counts': dict(Counter(r['split'] for r in candidates)),
        'draft_candidate_routes': {s: dict(Counter(r['labels']['route'] for r in candidates if r['split'] == s))
                                   for s in ('train', 'development', 'calibration')},
        'draft_candidate_intents': {s: dict(Counter(r['labels']['intent'] for r in candidates if r['split'] == s))
                                    for s in ('train', 'development', 'calibration')},
        'draft_candidate_tools': {s: dict(Counter(r['labels']['tool'] for r in candidates if r['split'] == s))
                                  for s in ('train', 'development', 'calibration')},
        'runtime_paths': dict(Counter(r['runtime_path'] for r in audit)),
        'coverage': coverage_report,
        'held_reason_counts': dict(Counter(reason for r in audit for reason in r['held_reasons'])),
        'regression_corpora': regression_meta,
        'source_hashes': {name: digest(ROOT / name) for name in
                          ('src/qwenlab/support_curriculum.py', 'src/qwenlab/support_scenario_catalog.py',
                           'src/qwenlab/support_challenge_catalog.py',
                           'configs/decision-v5.json')},
        'limitations': ['AI labels, not human gold', 'No independent acceptance collected',
                       'No GPU inference, training or API calls', 'Source hashes describe working files, not remote HEAD',
                       'Argument validation is feasibility only, not label truth',
                       'Exact normalized overlap checks are not semantic decontamination',
                       'Neutral-history pairs and punctuation variants are dependent',
                       'Guard-handled human examples may supervise the classifier; live guarded results are not model accuracy',
                       'No public dataset content imported; no database or personal records accessed'],
        'files_sha256': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    write_json(output / 'manifest.json', manifest)
    return manifest


def check(output, project=None):
    output = Path(output)
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or digest(output / name) != expected:
            raise ValueError('Draft file changed or missing: ' + name)
    for name, expected in manifest['source_hashes'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('Generator or policy changed: ' + name)
    rows = read_rows(output / 'cases.jsonl')
    challenge = read_rows(output / 'challenge-cases.jsonl')
    validate_structure(rows + challenge)
    if len(rows) != manifest['case_count']:
        raise ValueError('Case count mismatch')
    if project is not None:
        snapshot = json.loads((output / 'source-snapshot.json').read_text(encoding='utf-8'))
        if snapshot != source_snapshot(project):
            raise ValueError('Project source changed since this draft was built')
    return {'status': 'passed', 'cases': len(rows), 'human_gold': False, 'training_started': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        if args.project is None:
            parser.error('--project is required for build')
        result = build(args.project, args.output)
        result = {k: result[k] for k in ('status', 'card_count', 'case_count', 'split_counts', 'draft_candidate_counts', 'held_reason_counts')}
    else:
        result = check(args.output, args.project)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
