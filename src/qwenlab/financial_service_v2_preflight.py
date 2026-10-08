"""CPU-only, no-truncation tokenizer audit for the frozen v2 datasets."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

from qwenlab.common import ROOT
from qwenlab.financial_prompt_v2 import POLICY_HASH, encode
from qwenlab.financial_service_v2_data import OUT, validate, validate_train


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    ordered = sorted(values)
    return dict(count=len(values), minimum=min(values), maximum=max(values),
                p50=ordered[math.ceil(.5*len(values))-1],
                p95=ordered[math.ceil(.95*len(values))-1])


def run(train_only=False):
    from transformers import AutoTokenizer
    train = validate_train()
    if not train_only:
        validate()
    model_path = ROOT/'models/Qwen3.5-0.8B'
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    report = dict(status='pass', scope='train_only' if train_only else 'all_frozen_splits',
                  policy_sha256=POLICY_HASH, model='Qwen/Qwen3.5-0.8B',
                  model_weights_loaded=False, model_api_requests=0, max_input_tokens=2048,
                  truncation=False, splits={},
                  source_files={'src/qwenlab/financial_prompt_v2.py':sha(ROOT/'src/qwenlab/financial_prompt_v2.py'),
                                'src/qwenlab/financial_service_v2_preflight.py':sha(Path(__file__))},
                  tokenizer_files={p.name:sha(p) for p in model_path.iterdir()
                                   if p.is_file() and (p.name.startswith('tokenizer') or p.name.startswith('chat_template') or p.name in ('vocab.json','merges.txt','added_tokens.json','special_tokens_map.json'))},
                  packages={p:importlib.metadata.version(p) for p in ['transformers','tokenizers']})
    splits = ['train'] if train_only else ['train','development','calibration','final']
    for split in splits:
        path = OUT/(split+'.json')
        rows = train if split == 'train' else json.loads(path.read_text(encoding='utf-8'))
        lengths = {'action':[], 'tool':[]}
        labels = {'action':Counter(), 'tool':Counter()}
        for row in rows:
            for task in ['action'] + (['tool'] if row['annotation']['action']=='tool' else []):
                target = row['annotation']['action' if task == 'action' else 'tool_name']
                encoded = encode(tokenizer,row,task,target=target,max_tokens=2048)
                lengths[task].append(len(encoded['tokens']['input_ids']))
                labels[task][target] += 1
                report.setdefault('candidate_token_ids', {})[task] = dict(zip(encoded['keys'],encoded['ids']))
        report['splits'][split] = dict(rows=len(rows), tokens={k:stats(v) for k,v in lengths.items()},
                                      targets={k:dict(v) for k,v in labels.items()})
        report['source_files'][path.relative_to(ROOT).as_posix()] = sha(path)
        print(json.dumps({split:report['splits'][split]['tokens']},ensure_ascii=False),flush=True)
    target = ROOT/'docs/evidence'/('financial-service-v2-tokenizer-train.json' if train_only else 'financial-service-v2-tokenizer.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(target.relative_to(ROOT).as_posix())


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--train-only',action='store_true')
    run(parser.parse_args().train_only)
