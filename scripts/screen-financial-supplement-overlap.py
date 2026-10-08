"""Blind lexical screening: emit candidate IDs only, never held-out text/labels.

Authoring must be frozen before this runs. Hits are quarantined as whole groups;
do not rewrite them to evade a match. This is not a semantic leakage guarantee.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def normalized(text):
    return re.sub(r'[^\w\u4e00-\u9fff]', '', re.sub(r'\d+', 'NUM', text).lower())


def grams(text):
    return {text[i:i+2] for i in range(len(text)-1)}


def screen(candidates, corpus):
    index = defaultdict(set)
    for row in corpus:
        value = normalized(row['input']['message'])
        index[value].add(row['input'].get('capability_profile', 'unknown'))
    prepared = [(value, grams(value)) for value in index]
    hits = []
    for row in candidates:
        text = normalized(row['input']['message']); tokens = grams(text)
        best = 0.0; exact = text in index
        if not exact and len(text) >= 12:
            for other, other_tokens in prepared:
                if len(other) < 12: continue
                if min(len(text),len(other))/max(len(text),len(other)) < .75: continue
                score = len(tokens & other_tokens)/max(1,len(tokens | other_tokens))
                best = max(best, score)
        if exact or best >= .85:
            hits.append(dict(candidate_id=row['id'], kind='numeric_normalized_exact' if exact else 'bigram_jaccard',
                             similarity=1.0 if exact else round(best,4)))
    return hits


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--build',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Do not overwrite screening evidence')
    candidate_path=args.build/'candidates.json'
    rows=json.loads(candidate_path.read_text(encoding='utf-8')); groups={r['id']:r['scene_family_id'] for r in rows}
    result=dict(version='financial-supplement-blind-lexical-v1', candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                policy='Flag whole candidate groups; never reveal held-out text or use hits as rewrite prompts.',
                scope='financial-service-v2 train/development/calibration/final only; no model predictions',
                lexical_threshold=.85, semantic_overlap_guarantee=False, corpora={}, quarantine_groups=[], training_eligible=False)
    flagged=set()
    for split in ['train','development','calibration','final']:
        path=ROOT/'data/financial-service-v2'/f'{split}.json'
        old=json.loads(path.read_text(encoding='utf-8'))
        hits=screen(rows,old)
        result['corpora'][split]=dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(old),hits=hits)
        for hit in hits:
            if split != 'train': flagged.add(groups[hit['candidate_id']])
    result['quarantine_groups']=sorted(flagged)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(hits={s:len(v['hits']) for s,v in result['corpora'].items()}, quarantine_groups=sorted(flagged)),ensure_ascii=False))


if __name__=='__main__': main()
