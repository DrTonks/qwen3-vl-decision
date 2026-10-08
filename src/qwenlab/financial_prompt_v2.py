"""New protocol encoder, independent of all frozen pilot/V5 encoders."""
from copy import deepcopy
import json

from qwenlab.financial_serve_v2 import protocol, validate_input

SPEC, POLICY_HASH = protocol()


def messages(row, task='action'):
    if task not in ('action', 'tool'):
        raise ValueError('Unknown task')
    value = validate_input(row['input'], SPEC)
    value['available_tools'] = sorted(value['available_tools'])
    value['capabilities']['knowledge_collections'] = sorted(value['capabilities']['knowledge_collections'])
    keys = SPEC['actions'] if task == 'action' else SPEC['tools']
    question = SPEC['questions'][task]
    choices = '\n'.join(f"{chr(65+i)} {key}：{question['criteria'][key]}" for i, key in enumerate(keys))
    return [dict(role='system', content=SPEC['policy'] + '只输出一个候选字母。'),
            dict(role='user', content=json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                 + '\n' + question['instructions'] + '\n' + choices)], list(keys)


def encode(tokenizer, row, task='action', target=None, max_tokens=2048):
    content, keys = messages(row, task)
    ids = [tokenizer.encode(chr(65+i), add_special_tokens=False) for i in range(len(keys))]
    if any(len(tokens) != 1 for tokens in ids):
        raise ValueError('Every candidate must be one token')
    text = tokenizer.apply_chat_template(content, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    if not text.endswith('<think>\n\n</think>\n\n'):
        raise ValueError('Expected explicitly closed Qwen3.5 non-thinking prefix')
    tokens = tokenizer(text)
    if len(tokens['input_ids']) > max_tokens:
        raise ValueError('Input exceeds protocol context budget; no truncation')
    result = dict(id=row['id'], task=task, tokens=dict(tokens), keys=keys, ids=[v[0] for v in ids])
    if target is not None:
        result['target'] = keys.index(target)
    return result
