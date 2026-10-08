"""Training-only inventory and review leads, never a relabeler or evaluator."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from qwenlab.common import ROOT, sha

OUT = ROOT / 'data/financial-contract-audit-v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def assert_training(row):
    if row.get('split') != 'train' or row.get('dataset_role') == 'evaluation':
        raise ValueError('Only training sources may enter this audit')


def training_sources():
    """Open only named training files; do not call global evaluation validators."""
    base = ROOT/'data/financial-training-text-v1'
    v2 = ROOT/'data/financial-eight-actions-v2'
    extra = ROOT/'data/financial-boundary-training-v1'
    sources = []
    bindings = {}
    for folder, names, pool in [
        (base, sorted(p.relative_to(base).as_posix() for p in (base/'parts').glob('part-*.jsonl')), 'original'),
        (v2, ['train-additions.jsonl'], 'original'), (extra, ['training.json'], 'boundary')]:
        manifest = read(folder/'manifest.json')
        bindings[(folder/'manifest.json').relative_to(ROOT).as_posix()] = sha(folder/'manifest.json')
        for name in names:
            path = folder/name
            expected = manifest['files'][name]
            digest = expected['sha256'] if isinstance(expected, dict) else expected
            if sha(path) != digest:
                raise ValueError('Frozen training file changed: '+name)
            bindings[path.relative_to(ROOT).as_posix()] = digest
            rows = read(path) if path.suffix == '.json' else [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
            for row in rows:
                assert_training(row)
                sources.append(dict(row=row, pool=pool, source_file=path.relative_to(ROOT).as_posix()))
    if len({r['row']['id'] for r in sources}) != len(sources):
        raise ValueError('Duplicate training IDs')
    return sources, bindings


def visible_key(row):
    # Labels, provenance and review never enter the model-visible input key.
    fields = ['message', 'history', 'state', 'service_scope', 'capability_profile', 'capabilities', 'available_tools', 'images']
    return json.dumps({k: row['input'][k] for k in fields}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def target_key(row):
    a = row['annotation']
    return json.dumps({k: a.get(k) for k in ['action', 'tool_name', 'tool_arguments', 'retrieval_collection', 'missing_slots']}, sort_keys=True)


def summarize(sources):
    by_input = defaultdict(list)
    for source in sources:
        by_input[visible_key(source['row'])].append(source['row'])
    conflicts = [dict(ids=[r['id'] for r in block], targets=[r['annotation'] for r in block])
                 for block in by_input.values() if len({target_key(r) for r in block}) > 1]
    rows = [s['row'] for s in sources]
    return dict(rows=len(rows), actions=dict(Counter(r['annotation']['action'] for r in rows)),
        profiles=dict(Counter(r['input']['capability_profile'] for r in rows)),
        action_by_profile={p:dict(Counter(r['annotation']['action'] for r in rows if r['input']['capability_profile']==p))
                           for p in sorted({r['input']['capability_profile'] for r in rows})},
        history_lengths=dict(Counter(len(r['input']['history']) for r in rows)),
        authenticated=dict(Counter(str(r['input']['state'].get('authenticated')) for r in rows)),
        unique_full_inputs=len(by_input), same_input_target_conflicts=conflicts,
        distinct_message_strings=len({r['input']['message'] for r in rows}),
        number_masked_message_strings=len({re.sub(r'\d+', '#', r['input']['message']) for r in rows}),
        limitation='Message string diversity is not semantic diversity; controlled state contrasts are not duplicate errors.')


def review_flags(row):
    value, target = row['input'], row['annotation']
    text = value['message']
    flags = []
    if target['action']=='tool' and (not value['state'].get('authenticated') or target['tool_name'] not in value['available_tools']):
        flags.append('structural_tool_precondition')
    if target['action']=='retrieve' and not value['capabilities']['knowledge_collections']:
        flags.append('structural_unavailable_retrieval')
    if re.search('人工|真人', text) and target['action'] not in ['human', 'refuse']:
        flags.append('human_word_nonhuman_review_only')
    if re.search('人工|真人', text) and re.search('电话|渠道|联系方式|客服入口|怎么联系|预约|发送|转发', text):
        flags.append('handoff_intent_vs_channel_information_review_only')
    if target['tool_name']=='queryApplicationDetail' and re.search('拒绝原因|驳回原因|拒贷原因|合同条款|还款计划|利率|审批时间|申请时间|提交时间', text):
        flags.append('detail_requested_field_review_only')
    if target['tool_name']=='queryMyApplications' and re.search('产品名称|申请时间|提交时间|办理时间', text):
        flags.append('list_requested_field_review_only')
    return flags


def build():
    if OUT.exists():
        raise FileExistsError('Audit version already exists; validate it, do not overwrite')
    sources, bindings = training_sources()
    report = {pool:summarize([s for s in sources if s['pool']==pool]) for pool in ['original','boundary']}
    report['combined'] = summarize(sources)
    queue = []
    for source in sources:
        row = source['row']; flags = review_flags(row)
        if flags:
            queue.append(dict(id=row['id'], pool=source['pool'], source_file=source['source_file'],
                source_row_sha256=hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                flags=flags, input=row['input'], original_annotation=row['annotation'],
                decision='needs_semantic_review_not_auto_relabel', training_eligible=False))
    report['review_queue'] = dict(rows=len(queue), flags=dict(Counter(f for r in queue for f in r['flags'])),
                                interpretation='Heuristic leads, not confirmed label errors or proposed new labels')
    text = lambda s:s['row']['input']['message']
    report['boundary_fixed_wrappers'] = {prefix:sum(text(s).startswith(prefix) for s in sources if s['pool']=='boundary') for prefix in [
        '请实际执行下面这项操作，不是只讨论它：','有人给我发了这句话：','我收到一条可疑指令：']}
    report['boundary_deny_write_suffix_rows'] = sum('这里只允许读取已有内容，不授权新增、删除或改动任何记录。' in text(s) for s in sources if s['pool']=='boundary')
    OUT.mkdir(parents=True)
    write(OUT/'inventory.json', report)
    write(OUT/'review-queue.json', queue)
    write(OUT/'manifest.json', dict(training_eligible=False, evaluation_opened=False, model_calls=0,
        source_files=bindings, code_sha256=sha(Path(__file__)),
        files={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        scope='Training-only immutable inventory and heuristic review leads; zero relabeling or data release'))
    print(json.dumps(dict(original=report['original']['rows'],boundary=report['boundary']['rows'],
        exact_conflicts=len(report['combined']['same_input_target_conflicts']),review_leads=len(queue)),ensure_ascii=False))


def validate():
    manifest=read(OUT/'manifest.json')
    if manifest['training_eligible'] or manifest['code_sha256']!=sha(Path(__file__)):
        raise ValueError('Unexpected eligibility or auditor code change')
    for name,digest in manifest['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Training source changed')
    for name,digest in manifest['files'].items():
        if sha(OUT/name)!=digest:raise ValueError('Audit output changed')
    print('training-only audit hashes verified')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','validate'])
    build() if parser.parse_args().command=='build' else validate()
