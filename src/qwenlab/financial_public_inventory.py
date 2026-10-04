"""Read-only inventory of public TRAIN sources, not eight-action gold labels.

Raw sources are canonical: processed subsets are flags, never extra rows.
No validation/test partitions or future system reply enters source_history.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

from qwenlab.common import ROOT

MASSIVE = 'data/raw/massive-1.1-zh-CN.jsonl'
CROSSWOZ = 'data/raw/crosswoz-train.json.zip'
PROCESSED = ('data/processed/v5/massive-train.jsonl',
             'data/processed/v5/crosswoz-train.jsonl')
INTEGRATED = 'data/financial-actions-text-v2/cases.jsonl'
CROSSWOZ_METADATA = 'data/crosswoz-training-source.json'
CROSSWOZ_LICENSE_URL = 'https://raw.githubusercontent.com/thu-coai/CrossWOZ/df82c9fdff91b9b130f2d6b89110d3870ba6260e/LICENSE'


def _rows(path):
    with path.open(encoding='utf-8-sig') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def classify(message, labels, dataset):
    """Conservative source triage; suggestions are explicitly not action labels."""
    compact = re.sub(r'[\s，。！？、,.!?~～]', '', message)
    # These are a review queue, never automatic refusal gold labels.
    if re.search(r'(伪造|造假|冒充|绕过.{0,8}(验证|认证)|盗取|窃取|偷.{0,5}(密码|账号)|破解.{0,5}(密码|账号))', message):
        return 'suspected_improper_review', '含疑似越权/欺骗词；须区分防骗咨询、受害求助与实际不当请求，不能自动标拒绝。'
    if re.search(r'(借款|贷款|还款|逾期|征信|借贷)', message):
        return 'loan_related_review', '出现贷款相关词，需核实是否真是贷款诉求及上下文，非直接沿用标签。'
    if labels.get('intent') in {'qa_currency', 'qa_stock'} or re.search(r'(股票|汇率|外汇|证券|基金|理财|保险|信用卡)', message):
        return 'finance_other_review', '涉及金融但不一定属于贷款平台服务；可少量留作范围边界，其余改写时需改变业务对象。'
    if re.fullmatch(r'(好|好的|好吧|行|嗯|恩|哦|知道了|明白了|谢谢|谢谢你|多谢|谢谢您|感谢|再见|拜拜|不用了|没事了|没有了|你好|您好|嗨|哈喽|早上好|晚上好|谢谢再见|好的谢谢|好的谢谢你|谢谢拜拜)+', compact):
        return 'social_close_or_ambiguous_review', '简短礼貌/确认/结束语；结合前文判断 answer/close/clarify，不能按原领域一概引导。'
    if labels.get('intent') == 'general_greet':
        return 'social_close_or_ambiguous_review', '原始意图为问候，需核实是否混有其他请求；客服也需要礼貌互动。'
    acts = labels.get('dialog_acts', [])
    if dataset == 'crosswoz' and acts and all(a[0] == 'General' for a in acts):
        return 'social_close_or_ambiguous_review', '当前轮只有 General 对话行为；旧旅游上下文不能直接作为金融场景金标。'
    if len(compact) <= 5 or labels.get('intent') == 'general_quirky':
        return 'ambiguous_or_general_review', '短句或通用闲谈标签，需人工式逐条审查；不能从来源标签推断是否越界。'
    return 'out_of_scope_rewrite_pool', '原任务以生活助理/旅游服务为主；少量保留清晰域外请求作 redirect，其余改写为贷款客服并重审。'


def inventory(root=None):
    """Return canonical raw-train user rows with provenance and reuse flags.

    source_history contains at most four preceding user/assistant messages.
    source_history_total_turns records how much context was truncated.
    source_group must stay together if variants are later split for evaluation.
    `already_integrated` means direct parent reused in v2, NOT semantic novelty.
    """
    root = Path(root) if root is not None else ROOT
    processed_ids = {row['id'] for p in PROCESSED for row in _rows(root / p)}
    integrated_ids = set()
    known_sources = set(PROCESSED) | {MASSIVE, CROSSWOZ}
    for row in _rows(root / INTEGRATED):
        provenance = row.get('provenance', {})
        if provenance.get('source') in known_sources and provenance.get('parent_id'):
            integrated_ids.add(str(provenance['parent_id']))
    result = []

    def add(dataset, source_id, source_group, message, history, labels, **extra):
        disposition, reason = classify(message, labels, dataset)
        result.append({
            'dataset': dataset,
            'source_path': MASSIVE if dataset == 'massive' else CROSSWOZ,
            'source_id': source_id, 'source_group': source_group,
            'source_split': 'train', 'source_message': message,
            'source_history': history, 'source_labels': labels,
            'already_processed': source_id in processed_ids,
            'already_integrated': source_id in integrated_ids,
            'disposition_suggestion': disposition, 'reason': reason,
            'triage_status': 'assistant_rule_screen_not_gold',
            'license_status': 'CC-BY-4.0_attribution_required' if dataset == 'massive' else 'Apache-2.0 (repository-level; release notice required)',
            **extra,
        })

    for row in _rows(root / MASSIVE):
        if row['partition'] != 'train':
            continue
        sid = f"massive-train-{row['id']}"
        # Equal utterances are kept in the same source group, as in v5.
        add('massive', sid, 'massive-' + row['utt'], row['utt'], [],
            {'intent': row['intent'], 'scenario': row['scenario']},
            source_dialog_id=None, source_turn_index=None,
            source_history_total_turns=0, source_raw_id=str(row['id']))

    metadata = json.loads((root / CROSSWOZ_METADATA).read_text(encoding='utf-8-sig'))
    actual_sha = hashlib.sha256((root / CROSSWOZ).read_bytes()).hexdigest()
    if actual_sha != metadata['files']['crosswoz-train.json.zip']['sha256']:
        raise ValueError('CrossWOZ train archive does not match recorded source metadata')
    with zipfile.ZipFile(root / CROSSWOZ) as archive:
        names = [n for n in archive.namelist() if n == 'train.json' or n.endswith('/train.json')]
        if len(names) != 1:
            raise ValueError('Expected exactly one CrossWOZ train.json member')
        dialogs = json.loads(archive.read(names[0]))
    for did, dialog in dialogs.items():
        history = []
        for index, message in enumerate(dialog['messages']):
            role = {'usr': 'user', 'sys': 'assistant'}.get(message['role'])
            if role is None:
                raise ValueError('Unknown CrossWOZ message role')
            if role == 'user':
                acts = message.get('dialog_act', [])
                domains = sorted({a[1] for a in acts if len(a) > 1 and a[0] != 'General'})
                add('crosswoz', f'crosswoz-train-{did}-{index}', f'crosswoz-train-{did}',
                    message['content'], [dict(x) for x in history[-4:]],
                    {'domains': domains, 'dialog_acts': acts}, source_dialog_id=str(did),
                    source_turn_index=index, source_history_total_turns=len(history),
                    source_raw_id=f'{did}:{index}')
            history.append({'role': role, 'content': message['content']})
    if len({r['source_id'] for r in result}) != len(result):
        raise ValueError('Duplicate canonical source IDs')
    return result


def summary(rows, root=None):
    root = Path(root) if root is not None else ROOT
    remaining = [r for r in rows if not r['already_integrated']]
    return {
        'raw_train_rows': len(rows), 'remaining_rows': len(remaining),
        'integrated_unique_parents': sum(r['already_integrated'] for r in rows),
        'already_processed_rows': sum(r['already_processed'] for r in rows),
        'by_source': {name: {
            'rows': len(part := [r for r in rows if r['dataset'] == name]),
            'processed': sum(r['already_processed'] for r in part),
            'integrated': sum(r['already_integrated'] for r in part),
            'remaining': sum(not r['already_integrated'] for r in part),
            'groups': len({r['source_group'] for r in part}),
            'history_length_counts': dict(Counter(len(r['source_history']) for r in part)),
        } for name in ['massive', 'crosswoz']},
        'remaining_triage_counts': dict(Counter(r['disposition_suggestion'] for r in remaining)),
        'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                          for p in [MASSIVE, CROSSWOZ, CROSSWOZ_METADATA, *PROCESSED, INTEGRATED]},
        'crosswoz_license_evidence': CROSSWOZ_LICENSE_URL,
        'triage_is_gold': False,
    }


if __name__ == '__main__':
    print(json.dumps(summary(inventory()), ensure_ascii=False, indent=2))
