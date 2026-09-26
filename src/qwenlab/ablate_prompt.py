"""Exploratory development-only prompt ablation; never updates the v2 test results."""
import json
import re
import string
import time
from qwenlab.common import ROOT, append_json, sha
from qwenlab.modeling import load_model, dataset, specification, prompt, score
from qwenlab.train import business_split
from qwenlab.summarize import metric

def main():
    import torch
    out=ROOT/'results/phase2/development-ablation'
    if out.exists(): raise FileExistsError('Ablation exists')
    out.mkdir(parents=True)
    tokenizer,model=load_model('nf4','.local/checkpoints/qlora-v2/best');model.eval()
    data={'business':business_split()[1],'massive':dataset('massive','dev')}
    summary={}
    for name,rows in data.items():
        task='route' if name=='business' else 'intent'
        summary[name]={}
        for variant in ('frozen','identifiers','symbol','identifiers_symbol'):
            results=[]
            for row in rows:
                inputs,keys,ids=prompt(tokenizer,row,task)
                if variant!='frozen':
                    text=tokenizer.decode(inputs.input_ids[0],skip_special_tokens=False)
                    check=tokenizer(text,return_tensors='pt')
                    if not torch.equal(inputs.input_ids,check.input_ids): raise AssertionError('Tokenizer roundtrip changed')
                    if 'identifiers' in variant:
                        q=specification(name)['questions'][task]
                        for symbol,key in zip(string.ascii_uppercase+string.ascii_lowercase+string.digits,keys):
                            pattern=r'(?m)^'+re.escape(symbol+' '+q['criteria'][key])
                            text,n=re.subn(pattern,lambda m:m.group(0)+' ('+key+')',text)
                            if n!=1: raise ValueError('Candidate line not uniquely matched')
                    if 'symbol' in variant: text=text.replace('只输出一个候选字母。','只输出一个候选符号。')
                    inputs=tokenizer(text,return_tensors='pt')
                with torch.inference_mode():
                    logits=score(model,inputs.to('cuda'),ids);probs=logits.softmax(-1).cpu().tolist()
                pred={'choice':keys[max(range(len(keys)),key=probs.__getitem__)],'probabilities':dict(zip(keys,probs))}
                result={'id':row['id'],'group':row['group'],'labels':{task:row['labels'][task]},'predictions':{task:pred}}
                results.append(result);append_json(out/(name+'-'+variant+'.jsonl'),result)
            summary[name][variant]=metric(results,task)
            print(name,variant,summary[name][variant]['accuracy'],flush=True)
    metadata={'split':'development only; no new test scoring',
        'model':'same NF4 + selected QLoRA v2 adapter, no further training',
        'purpose':'exploratory after v2 failure; not a new held-out performance claim',
        'data_manifest_sha256':sha(ROOT/'data/processed/v2/manifest.json'),'metrics':summary}
    (out/'summary.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
