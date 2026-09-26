"""Shared first-token classifier used by training and inference."""
import json
import random
import string
from qwenlab.common import ROOT, input_state, load_json
from qwenlab.prepare_v2 import read_rows

def dataset(name, split):
    return read_rows(ROOT/f'data/processed/v2/{name}-{split}.jsonl')

def specification(name):
    return load_json(ROOT/'configs/decision_spec.json') if name=='business' else load_json(ROOT/f'data/processed/v2/{name}-spec.json')

def load_model(precision='bf16', adapter=None, training=False):
    import torch
    from transformers import AutoTokenizer, Qwen3VLForConditionalGeneration, BitsAndBytesConfig
    torch.set_num_threads(6)
    checkpoint=ROOT/'models/Qwen3-VL-2B-Instruct'
    tokenizer=AutoTokenizer.from_pretrained(checkpoint,local_files_only=True)
    options=dict(dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='sdpa',local_files_only=True)
    if precision=='nf4':
        options['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_skip_modules=['visual','lm_head'])
    model=Qwen3VLForConditionalGeneration.from_pretrained(checkpoint,**options)
    if adapter:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,ROOT/adapter,is_trainable=training)
    return tokenizer,model

def prompt(tokenizer, row, task, shuffle_seed=None):
    if row.get('images'):
        raise NotImplementedError('Text-only experiment; images require a processor and separate validation')
    spec=specification(row['dataset']); q=spec['questions'][task]; keys=list(q['criteria'])
    if shuffle_seed is not None: random.Random(shuffle_seed).shuffle(keys)
    symbols=string.ascii_uppercase+string.ascii_lowercase+string.digits
    token_ids=[tokenizer.encode(c,add_special_tokens=False) for c in symbols[:len(keys)]]
    if any(len(ids)!=1 for ids in token_ids): raise ValueError('Candidate symbols must each tokenize to one token')
    # No English label IDs or empty state containers in the compact prompt.
    state={k:v for k,v in input_state(row).items() if v not in ([],{},None)}
    options='\n'.join(f'{c} {q["criteria"][k]}' for c,k in zip(symbols,keys))
    messages=[{'role':'system','content':spec['policy']+'\n只输出一个候选字母。'},
        {'role':'user','content':json.dumps(state,ensure_ascii=False,separators=(',',':'))+'\n'+q['instructions']+'\n'+options}]
    text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    inputs=tokenizer(text,return_tensors='pt')
    if inputs.input_ids.shape[1]>2048: raise ValueError('Input exceeds 2048; no silent truncation')
    return inputs, keys, [ids[0] for ids in token_ids]

def score(model, inputs, token_ids):
    # Selecting only the final position avoids materializing sequence x vocabulary logits.
    return model(**inputs,logits_to_keep=1,use_cache=False).logits[0,-1,token_ids].float()

def predict(tokenizer, model, row, task):
    import torch
    import time
    torch.cuda.synchronize(); start=time.perf_counter()
    inputs,keys,ids=prompt(tokenizer,row,task)
    inputs=inputs.to('cuda')
    with torch.inference_mode(): logits=score(model,inputs,ids); probs=logits.softmax(-1).cpu().tolist()
    torch.cuda.synchronize()
    return {'choice':keys[max(range(len(keys)),key=probs.__getitem__)],
        'probabilities':dict(zip(keys,probs)),'candidate_logits':logits.cpu().tolist(),'ordered_keys':keys,
        'input_tokens':inputs.input_ids.shape[1],'elapsed_s':time.perf_counter()-start}
