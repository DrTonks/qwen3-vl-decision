"""Same frozen business messages, Qwen3-VL native non-thinking chat wrapper."""
from qwenlab.financial_prompt_v2 import SPEC, POLICY_HASH, messages


def encode(tokenizer,row,task='action',target=None,max_tokens=2048):
    content,keys=messages(row,task)
    ids=[tokenizer.encode(chr(65+i),add_special_tokens=False) for i in range(len(keys))]
    if any(len(v)!=1 for v in ids): raise ValueError('Each candidate must be one token')
    text=tokenizer.apply_chat_template(content,tokenize=False,add_generation_prompt=True)
    if not text.endswith('<|im_start|>assistant\n'):
        raise ValueError('Unexpected official Qwen3-VL assistant prefix')
    tokens=tokenizer(text,add_special_tokens=False)
    if len(tokens['input_ids'])>max_tokens: raise ValueError('No silent input truncation')
    result=dict(id=row['id'],task=task,tokens=dict(tokens),keys=keys,ids=[v[0] for v in ids])
    if target is not None: result['target']=keys.index(target)
    return result
