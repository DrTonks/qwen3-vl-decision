"""Fetch pinned public CrossWOZ archives; never read credentials."""
import urllib.request
from qwenlab.common import ROOT, load_json, sha


def main():
    manifest = load_json(ROOT / 'data/crosswoz-training-source.json')
    folder = ROOT / 'data/raw'; folder.mkdir(parents=True, exist_ok=True)
    for name, record in manifest['files'].items():
        path = folder / name
        if path.exists():
            if sha(path) != record['sha256']: raise ValueError('Existing source hash mismatch: ' + name)
            print('Verified existing', name); continue
        pending = path.with_suffix(path.suffix + '.part')
        with urllib.request.urlopen(record['url'], timeout=120) as response, pending.open('wb') as output:
            while block := response.read(1024 * 1024): output.write(block)
        if sha(pending) != record['sha256']: raise ValueError('Downloaded source hash mismatch: ' + name)
        pending.replace(path); print('Downloaded and verified', name)


if __name__ == '__main__': main()
