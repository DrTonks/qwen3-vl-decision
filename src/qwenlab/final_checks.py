"""Audit completeness/provenance and export a human-review worksheet."""
import csv
import json
import hashlib
from pathlib import Path
from qwenlab.common import ROOT,load_rows,sha

def main():
    folder=ROOT/'results/baseline-v1'
    counts={}
    for filename,expected in {
        'jev-business-test.jsonl':72,'jev-business-dev.jsonl':64,'jev-massive-test.jsonl':117,
        'qwen-first-business-test.jsonl':72,'qwen-generate-business-test.jsonl':72,
        'qwen-first-business-dev.jsonl':64,'qwen-generate-business-dev.jsonl':64,
        'qwen-first-business-calibration.jsonl':56,'qwen-first-massive-test.jsonl':117,
        'qwen-generate-massive-test.jsonl':117,'qwen-first-business-test-perm17.jsonl':72,
        'qwen-calibrated-business-test.jsonl':72,'qwen-gated-business-test.jsonl':72,
        'jev-gated-business-test.jsonl':72}.items():
        rows=[json.loads(x) for x in (folder/filename).read_text(encoding='utf-8').splitlines()]
        assert len(rows)==expected,filename
        assert len({r['id'] for r in rows})==expected,filename
        assert all(not r.get('error') for r in rows),filename
        counts[filename]=expected
    for meta in folder.glob('*-meta.json'):
        d=json.loads(meta.read_text(encoding='utf-8'))
        dataset='massive' if 'massive' in meta.name else 'business'
        assert d['dataset_sha256']==load_rows(dataset)[1],meta.name
    review=ROOT/'data/business_review.csv'
    with review.open('w',encoding='utf-8-sig',newline='') as f:
        fields=['id','group','split','message','history','state','available_tools','intent','route','tool','needs_human','reviewer_1','reviewer_2','agreed_labels','notes']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for split in ('dev','calibration','test'):
            for r in load_rows('business',split)[0]:
                out={k:r[k] for k in ('id','group','split','message')}
                out.update({k:json.dumps(r[k],ensure_ascii=False) for k in ('history','state','available_tools')})
                out.update(r['labels']);writer.writerow(out)
    # Read only for exact-match exclusion check. Never serialize the key or its hash.
    secret=(ROOT/'.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip().encode()
    checked=0
    for top in [*ROOT.glob('*.py'),*ROOT.glob('*.md'),*ROOT.glob('*.json'),*ROOT.glob('*.ps1'),*ROOT.glob('*.txt'),*ROOT.glob('data/*.json*'),*ROOT.glob('data/*.csv'),*ROOT.glob('results/**/*')]:
        if not top.is_file() or top.name=='jev-api-key.txt':continue
        assert secret not in top.read_bytes(),'Credential found in output: '+top.name
        checked+=1
    manifest={str(p.relative_to(ROOT)):sha(p) for p in [*ROOT.glob('*.py'),*ROOT.glob('*.ps1'),ROOT/'configs/decision_spec.json',ROOT/'requirements-lock.txt',ROOT/'configs/model_source.json',*ROOT.glob('data/*.json*')]}
    result={'complete_result_files':counts,'dataset_hashes_match':True,'secret_absent_from_checked_outputs':True,'checked_files':checked,
        'source_and_data_sha256':manifest,'human_review_pending':True,'production_integration':False,'training_performed':False}
    (folder/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Verified',len(counts),'result files;',checked,'files checked; no credential in generated outputs.')
if __name__=='__main__':main()
