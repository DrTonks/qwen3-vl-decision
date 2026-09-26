"""Freeze public run evidence after successful training and calibration."""
import json
import shutil
import random
from collections import Counter
from importlib.metadata import version
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows

def main():
    out=ROOT/'results/phase2'; out.mkdir(parents=True,exist_ok=True)
    training=ROOT/'.local/checkpoints/qlora-v2'
    state=load_json(training/'training-state.json')
    if state['status']!='complete': raise ValueError('Training is not complete')
    target=out/'training'; target.mkdir(exist_ok=True)
    for filename in ('training-state.json','train.jsonl','validation.jsonl'):
        public_name='training-summary.json' if filename=='training-state.json' else filename
        shutil.copy2(training/filename,target/public_name)
    adapter=training/'best'
    (target/'adapter-manifest.json').write_text(json.dumps({p.name:{'sha256':sha(p),'bytes':p.stat().st_size}
        for p in sorted(adapter.glob('*')) if p.is_file()},indent=2),encoding='utf-8')
    shutil.copy2(adapter/'adapter_config.json',target/'adapter_config.json')
    from qwenlab.train import business_split, examples
    from qwenlab.modeling import dataset
    public=examples(dataset('massive','train')); business=examples(business_split()[0])
    cfg=state['config']; rng=random.Random(cfg['seed']); unique_rows={'massive':set(),'business':set()}; unique_questions={'massive':set(),'business':set()}
    for _ in range(cfg['steps']*cfg['gradient_accumulation']):
        pool=business if rng.random()<cfg['business_sampling_probability'] else public
        row,task=rng.choice(pool); rng.randrange(2**31)
        unique_rows[row['dataset']].add(row['id']); unique_questions[row['dataset']].add((row['id'],task))
    sampling={'provenance':'Reconstructed from recorded seed and the unchanged training sampler; not an online trace',
        'unique_rows':{k:len(v) for k,v in unique_rows.items()},'unique_questions':{k:len(v) for k,v in unique_questions.items()}}
    (target/'sampling-summary.json').write_text(json.dumps(sampling,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'data/processed/v2/manifest.json',out/'data-manifest.json')
    for name in ('massive-spec.json','crosswoz-spec.json'):
        shutil.copy2(ROOT/'data/processed/v2'/name,out/name)
    source_paths=[*sorted((ROOT/'src/qwenlab').glob('*.py')),*sorted((ROOT/'configs').glob('*.json'))]
    (out/'source-sha256.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},indent=2),encoding='utf-8')
    packages={p:version(p) for p in ('torch','transformers','peft','bitsandbytes','accelerate','numpy')}
    (out/'software.json').write_text(json.dumps(packages,indent=2),encoding='utf-8')
    # Count actual new calls, excluding the copied unchanged business/CrossWOZ files.
    archived=list((ROOT/'.local/archive/invalid-61-candidates/jev-v2').glob('*-test.jsonl'))
    if archived:
        sources={'discarded_61_candidate_run':archived,
            'corrected_massive':[ROOT/'results/runs/jev-v2/massive-test.jsonl']}
    else:
        sources={'current_run':list((ROOT/'results/runs/jev-v2').glob('*-test.jsonl'))}
    usage={}
    for name,paths in sources.items():
        rows=[r for p in paths for r in read_rows(p)]
        good=[r for r in rows if not r.get('error')]
        usage[name]={'requests_recorded':len(rows),'successful':len(good),'failed':len(rows)-len(good),
            'failures':dict(Counter(str(r.get('status'))+':'+r.get('error','') for r in rows if r.get('error'))),
            'input_tokens_reported':sum((r.get('usage') or {}).get('input_tokens',0) for r in good),
            'output_tokens_reported':sum((r.get('usage') or {}).get('output_tokens',0) for r in good)}
    usage['note']='This phase only. Available invalid-vocabulary archives are included; reused files are not counted twice when those archives are available. Failed-call billing is unknown; token totals are not a bill.'
    (out/'api-usage.json').write_text(json.dumps(usage,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Public training, adapter hashes, dataset, software and API usage records saved')

if __name__=='__main__': main()
