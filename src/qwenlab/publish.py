"""Explicit publication allowlist; fail closed on local paths or credentials."""
import argparse
import hashlib
import json
import re
import zipfile
from qwenlab.common import ROOT

def publication_files(root=ROOT):
    names=['README.md','pyproject.toml','.gitignore','requirements.txt','requirements-lock.txt','requirements-train.txt','requirements-serve.txt','LICENSE','NOTICE.md']
    files=[root/name for name in names if (root/name).is_file()]
    for directory in ('src','tests','scripts','configs','docs','data/support-design-v1','data/support-runtime-v1','results/support-runtime-v1','results/baseline-v1','results/phase2','results/route-v3','results/joint-v4','results/joint-v5'):
        for path in (root/directory).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.log'): continue
            if path.name=='verification.json' or path.name.endswith('console.txt'): continue
            files.append(path)
    for pattern in ('*.json','*.jsonl','*.csv','*.md'):
        files.extend((root/'data').glob(pattern))
    template = root/'data/review/support-actions-v1-template.csv'
    if template.is_file(): files.append(template)
    return sorted(set(files))

def audit(files):
    keyfile=ROOT/'.local/secrets/jev-api-key.txt'
    secret=keyfile.read_text(encoding='utf-8-sig').strip().encode() if keyfile.exists() else b''
    errors=[]
    for path in files:
        rel=path.relative_to(ROOT).as_posix(); content=path.read_bytes()
        if any(part in ('.local','.venv','.cache','models','.planning') for part in path.relative_to(ROOT).parts): errors.append((rel,'private directory'))
        if len(content)>20*1024**2: errors.append((rel,'oversize file'))
        if secret and secret in content: errors.append((rel,'credential exact match'))
        try: text=content.decode('utf-8-sig')
        except UnicodeDecodeError: errors.append((rel,'unexpected binary')); continue
        if re.search(r'(?<![\w])(?:[A-Za-z]:[\\/]|/(?:Users|home|mnt)/)',text): errors.append((rel,'absolute personal path'))
    return errors

def main():
    p=argparse.ArgumentParser(); p.add_argument('--export',action='store_true'); args=p.parse_args()
    files=publication_files(); errors=audit(files)
    if errors:
        print(json.dumps(errors,ensure_ascii=False,indent=2)); raise SystemExit('Publication audit failed')
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    local=ROOT/'.local'; local.mkdir(exist_ok=True)
    (local/'publication-audit.json').write_text(json.dumps({'files':manifest,'status':'passed','private_learning_excluded':True},ensure_ascii=False,indent=2),encoding='utf-8')
    if args.export:
        target=ROOT/'dist'; target.mkdir(exist_ok=True)
        with zipfile.ZipFile(target/'qwen-decision-lab-source-results.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
            for path in files: z.write(path,path.relative_to(ROOT).as_posix())
            z.writestr('PUBLICATION_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Publication audit passed:',len(files),'files; private learning, credentials, local weights and paths excluded')

if __name__=='__main__': main()
