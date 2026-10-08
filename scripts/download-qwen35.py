"""Download official ModelScope weights with per-file pinned revision/hash."""
from datetime import datetime,timezone
import hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
state=root/'.local/qwen35-download.json'
manifest=root/'configs/qwen35-model-source.json'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
repo='Qwen/Qwen3.5-0.8B'
if not manifest.exists():
    endpoint=f'https://modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true'
    listing=json.load(opener.open(endpoint,timeout=30))
    files=[f for f in listing['Data']['Files'] if f['Type']=='blob' and
        f['Path'] not in ['README.md','configuration.json','.gitattributes']]
    manifest.write_text(json.dumps(dict(repo_id=repo,source='Qwen official ModelScope',files=files),indent=2)+'\n',encoding='utf-8')
source=json.loads(manifest.read_text(encoding='utf-8'))
record=dict(repo_id=repo,status='downloading',source='modelscope',model_path='models/Qwen3.5-0.8B',
    started_at=datetime.now(timezone.utc).isoformat(),verified_files=[])
state.parent.mkdir(exist_ok=True)
folder=root/record['model_path'];folder.mkdir(parents=True,exist_ok=True)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save():
    temp=state.with_suffix('.part');temp.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');temp.replace(state)
for item in source['files']:
    name=item['Path']
    if '/' in name or '\\' in name or name.startswith('.'):
        raise ValueError('Unexpected model filename')
    target=folder/name
    if not (target.exists() and target.stat().st_size==item['Size'] and digest(target)==item['Sha256']):
        url=f'https://modelscope.cn/api/v1/models/{repo}/repo?'+urllib.parse.urlencode({'Revision':item['Revision'],'FilePath':name})
        partial=target.with_suffix(target.suffix+'.part')
        record.update(file=name,total_bytes=item['Size'],downloaded_bytes=0);save()
        with opener.open(url,timeout=90) as response,partial.open('wb') as stream:
            last=time.monotonic()
            while block:=response.read(4*1024*1024):
                stream.write(block);record['downloaded_bytes']+=len(block)
                if time.monotonic()-last>10:
                    save();print(json.dumps(dict(file=name,MB=round(record['downloaded_bytes']/1e6))),flush=True);last=time.monotonic()
        if partial.stat().st_size!=item['Size'] or digest(partial)!=item['Sha256']:
            raise ValueError('Downloaded checksum/size mismatch: '+name)
        partial.replace(target)
    record['verified_files'].append(name);save();print('verified '+name,flush=True)
record.update(status='download_complete',completed_at=datetime.now(timezone.utc).isoformat());save()
print(json.dumps(record),flush=True)
