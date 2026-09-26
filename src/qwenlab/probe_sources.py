"""Read-only public endpoint diagnostics; never reads the API key."""
import concurrent.futures
import urllib.request
import json
from pathlib import Path
from qwenlab.common import ROOT

URLS = {
    'huggingface_model': 'https://huggingface.co/api/models/Qwen/Qwen3-VL-2B-Instruct',
    'modelscope_model': 'https://modelscope.cn/api/v1/models/Qwen/Qwen3-VL-2B-Instruct/repo/files?Revision=master&Recursive=true',
    'massive': 'https://datasets-server.huggingface.co/rows?dataset=AmazonScience/massive&config=zh-CN&split=test&offset=0&length=2',
    'massive_github': 'https://raw.githubusercontent.com/alexa/massive/main/README.md',
    'jev_schema': 'https://api.typesafe.ai/openapi.json',
}
def probe(item):
    name,url=item
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url,timeout=25) as r: body=r.read()
        folder=ROOT/'data'/'raw'; folder.mkdir(parents=True,exist_ok=True)
        (folder/(name+'.txt')).write_bytes(body)
        return name, {'ok':True,'bytes':len(body)}
    except Exception as e: return name, {'ok':False,'error':type(e).__name__}
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for name,result in pool.map(probe,URLS.items()): print(name,json.dumps(result),flush=True)
