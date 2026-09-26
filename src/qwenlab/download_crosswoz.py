"""Download original held-out archive via GitHub's blob API and verify Git hash."""
import base64
import hashlib
import json
import urllib.request
from qwenlab.common import ROOT, load_json

def main():
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    source=load_json(ROOT/'configs/data_sources.json')['crosswoz']
    with op.open(source['url'],timeout=120) as response: blob=json.load(response)
    content=base64.b64decode(blob['content'])
    actual=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    if actual!=source['git_blob_sha'] or hashlib.sha256(content).hexdigest()!=source['sha256']:
        raise ValueError('Archive digest mismatch')
    target=ROOT/'data/raw'; target.mkdir(parents=True,exist_ok=True)
    (target/'crosswoz-test.json.zip').write_bytes(content)
    (target/'crosswoz-source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    print('CrossWOZ archive verified:',len(content),'bytes')

if __name__=='__main__': main()
