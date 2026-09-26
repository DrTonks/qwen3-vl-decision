"""Download Qwen official ModelScope files with pinned revisions and SHA256 checks."""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'models'/'Qwen3-VL-2B-Instruct'
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def main():
    manifest=json.loads((ROOT/'configs/model_source.json').read_text(encoding='utf-8'))
    MODEL.mkdir(parents=True,exist_ok=True)
    saved=[]
    for item in manifest['Data']['Files']:
        name=item['Path']
        if item['Type']!='blob' or name.startswith('.') or name=='configuration.json': continue
        if '/' in name or '\\' in name: raise ValueError('Unexpected nested filename')
        target=MODEL/name
        def digest(p):
            h=hashlib.sha256()
            with p.open('rb') as f:
                for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
            return h.hexdigest()
        if target.exists() and target.stat().st_size==item['Size'] and digest(target)==item['Sha256']:
            print('verified',name,flush=True); saved.append(item); continue
        url='https://modelscope.cn/api/v1/models/Qwen/Qwen3-VL-2B-Instruct/repo?'+urllib.parse.urlencode({'Revision':item['Revision'],'FilePath':name})
        partial=target.with_suffix(target.suffix+'.part')
        for attempt in range(3):
            try:
                print('download',name,item['Size'],flush=True)
                last=time.monotonic(); count=0
                with OPENER.open(url,timeout=90) as response, partial.open('wb') as f:
                    while block:=response.read(4*1024*1024):
                        f.write(block); count+=len(block)
                        if time.monotonic()-last>20:
                            print(name,round(count/1e6),'MB',flush=True); last=time.monotonic()
                if partial.stat().st_size!=item['Size'] or digest(partial)!=item['Sha256']: raise ValueError('Checksum mismatch')
                partial.replace(target); saved.append(item); break
            except Exception as e:
                print('retry',name,attempt+1,type(e).__name__,flush=True)
                if attempt==2: raise
        print('verified',name,flush=True)
    (MODEL/'download_manifest.json').write_text(json.dumps({'source':'Qwen official ModelScope','files':saved},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
