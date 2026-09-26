"""Read-only analysis of frozen predictions; never selects a model on test."""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows
from qwenlab.joint_v4 import OUT, DATA, dump, metrics


def slices(raw, predictions, field):
    source = {r['id']: r for r in raw}
    if len(source) != len(raw) or len({r['id'] for r in predictions}) != len(predictions):
        raise ValueError('Duplicate row IDs')
    if set(source) != {r['id'] for r in predictions}:
        raise ValueError('Predictions and source must match exactly')
    groups = defaultdict(list)
    for row in predictions:
        if row['labels'] != source[row['id']]['labels']:
            raise ValueError('Label mismatch')
        groups[source[row['id']][field]].append(row)
    return {name: metrics(rows) for name, rows in sorted(groups.items())}


def state_pairs(predictions):
    """Count pairs within wording groups whose gold route changes with state."""
    groups = defaultdict(list)
    for r in predictions:
        groups[r['group']].append(r)
    total = correct = 0
    for rows in groups.values():
        for a, b in combinations(rows, 2):
            if a['labels']['route'] == b['labels']['route']:
                continue
            total += 1
            correct += all(r['predictions']['route']['choice'] == r['labels']['route'] for r in (a, b))
    return {'pairs': total, 'both_routes_correct': correct,
            'accuracy': correct / total if total else None,
            'note': 'Pairs overlap and are dependent; descriptive only, not independent trials.'}


def errors(raw, predictions):
    source = {r['id']: r for r in raw}
    result = []
    for row in predictions:
        wrong = {t: {'gold': row['labels'][t], 'predicted': row['predictions'][t]['choice']}
                 for t in ('intent', 'route', 'tool')
                 if row['labels'][t] != row['predictions'][t]['choice']}
        if not wrong:
            continue
        origin = source[row['id']]
        result.append({**{k: origin[k] for k in ('id', 'group', 'semantic_family', 'condition', 'message', 'state')},
                       'errors': wrong, 'label_review': 'pending',
                       'priority': 'human_missed' if row['labels']['route'] == 'human' and 'route' in wrong
                       else 'tool_chain' if row['labels']['route'] == 'tool' else 'other'})
    return sorted(result, key=lambda r: ({'human_missed': 0, 'tool_chain': 1, 'other': 2}[r['priority']], r['id']))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--include-test', action='store_true', help='Only after the frozen v4 pipeline completes')
    args = p.parse_args()
    if args.include_test and load_json(OUT / 'completion.json')['status'] != 'complete':
        raise RuntimeError('Full evaluation has not completed')
    selection = load_json(OUT / 'selection.json'); selected = selection['selected']
    target = OUT / 'diagnostics'; target.mkdir(exist_ok=True)
    curve = []
    for variant, datasets in selection['development'].items():
        b, public = datasets['business'], datasets['massive']
        curve.append({'variant': variant, 'step': 0 if variant == 'base' else int(variant.split('-')[1]),
                      'public_intent_accuracy': public['tasks']['intent']['accuracy'],
                      'business_intent_accuracy': b['tasks']['intent']['accuracy'],
                      'route_accuracy': b['tasks']['route']['accuracy'],
                      'route_macro_f1': b['tasks']['route']['macro_f1_gold_supported_classes'],
                      'joint_tool_correct': b['joint_tool_correct'], 'tool_required': b['tool_required'],
                      'human_missed': b['human_missed'], 'human_required': b['human_required'],
                      'route_nll': b['tasks']['route']['nll']})
    result = {'selected_by_frozen_dev_protocol': selected, 'development_curve': curve,
              'source_sha256': {'selection.json': sha(OUT / 'selection.json')}, 'slices': {},
              'limits': ['Unreviewed synthetic labels', 'Shared author and policy across splits',
                         'Checkpoints are not data-size experiments', 'Test errors are audit evidence, not training data']}
    for split in (['dev', 'test'] if args.include_test else ['dev']):
        raw = read_rows(DATA / f'business-{split}.jsonl')
        variants = ['base', selected] + (['jev'] if split == 'test' else [])
        for variant in dict.fromkeys(variants):
            path = OUT / variant / f'business-{split}.jsonl'; predictions = read_rows(path)
            result['source_sha256'][path.relative_to(OUT).as_posix()] = sha(path)
            result['source_sha256'][f'business-{split}-source'] = sha(DATA / f'business-{split}.jsonl')
            result['slices'][f'{variant}/{split}'] = {
                'condition': slices(raw, predictions, 'condition'),
                'semantic_family': slices(raw, predictions, 'semantic_family'),
                'state_pairs': state_pairs(predictions)}
            if variant == selected:
                dump(target / f'{split}-review.json', errors(raw, predictions))
            elif variant == 'jev':
                dump(target / 'jev-test-review.json', errors(raw, predictions))
    dump(target / 'analysis.json', result)
    lines = ['# 训练后诊断', '', f'冻结开发协议选择：`{selected}`。本报告不重新选择检查点。', '',
             '|检查点|公共意图|业务意图|业务路由|路由宏 F1|工具联合正确|人工漏转|路由 NLL|',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for c in curve:
        lines.append(f'|{c["variant"]}|{c["public_intent_accuracy"]:.2%}|{c["business_intent_accuracy"]:.2%}'
                     f'|{c["route_accuracy"]:.2%}|{c["route_macro_f1"]:.3f}'
                     f'|{c["joint_tool_correct"]}/{c["tool_required"]}|{c["human_missed"]}/{c["human_required"]}|{c["route_nll"]:.3f}|')
    for split in (['dev', 'test'] if args.include_test else ['dev']):
        lines += ['', f'## 所选模型：{split} 状态分层', '',
                  '|状态|数量|路由准确率|工具联合正确|人工漏转|', '|---|---:|---:|---:|---:|']
        for condition, m in result['slices'][f'{selected}/{split}']['condition'].items():
            lines.append(f'|{condition}|{m["n"]}|{m["tasks"]["route"]["accuracy"]:.2%}'
                         f'|{m["joint_tool_correct"]}/{m["tool_required"]}|{m["human_missed"]}/{m["human_required"]}|')
        pairs = result['slices'][f'{selected}/{split}']['state_pairs']
        lines += ['', f'同表达、不同应答路由的状态对：两端均正确 {pairs["both_routes_correct"]}/{pairs["pairs"]}。这些配对相互重叠，不能当作独立样本。']
    lines += ['', '开发错例用于复核政策和设计新训练场景；测试错例仅用于描述本轮局限。',
              '如使用测试错例指导下一轮，当前测试集必须降级为回归集，下一轮另建独立验收集。',
              '未人工复核的标签可能有歧义；先审标签再归因模型。不能把文件写入复核队列视为已复核。']
    (target / 'analysis.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Diagnostics saved; selected={selected}; include_test={args.include_test}')


if __name__ == '__main__':
    main()
