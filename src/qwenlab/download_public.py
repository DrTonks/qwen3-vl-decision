"""Stream official MASSIVE 1.1 archive and retain only zh-CN, with provenance."""
import urllib.request
import tarfile
import json
import hashlib
import random
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
URL='https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz'
def main():
    raw=ROOT/'data/raw'; raw.mkdir(parents=True,exist_ok=True)
    path=raw/'massive-1.1-zh-CN.jsonl'
    if not path.exists():
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL,timeout=90) as response, tarfile.open(fileobj=response,mode='r|gz') as archive:
            for member in archive:
                if member.name.endswith('/zh-CN.jsonl') or member.name=='zh-CN.jsonl':
                    with archive.extractfile(member) as f: path.write_bytes(f.read())
                    print('downloaded zh-CN',path.stat().st_size,flush=True); break
            else: raise RuntimeError('zh-CN not found')
    data=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    source=json.loads((ROOT/'configs/data_sources.json').read_text(encoding='utf-8'))['massive']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=source['member_sha256']:
        raise ValueError('MASSIVE source digest mismatch; retain file for inspection')
    by=defaultdict(list)
    for r in data:
        if r['partition']=='test': by[r['intent']].append(r)
    rng=random.Random(20260926); out=[]
    for intent,items in sorted(by.items()):
        rng.shuffle(items)
        for r in items[:2]:
            out.append({'id':'massive-'+str(r['id']),'group':str(r['id']),'split':'test','source':'MASSIVE-1.1-zh-CN',
                'label_status':'public_original','message':r['utt'],'history':[],'state':{},'images':[],
                'labels':{'intent':intent}})
    target=ROOT/'data/massive_zh_test.jsonl'
    target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in out),encoding='utf-8')
    (ROOT/'data/massive_manifest.json').write_text(json.dumps({'url':URL,'license':'CC-BY-4.0',
        'citation':'FitzGerald et al., MASSIVE (2022/2023), Amazon Science',
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'subset_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'seed':20260926,'selection':'2 per intent from official test split, sorted intent then seeded shuffle',
        'rows':len(out),'intents':sorted(by),'scope':'General assistant intents; not loan routing, no platform tool labels'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('public subset',len(out),'intents',len(by),flush=True)
if __name__=='__main__': main()
