"""Offline-only consumer of the pinned vendor reference; never makes API calls."""
import argparse
import json
from pathlib import Path

from qwenlab.common import ROOT
from qwenlab import financial_jev_reference as jev
from qwenlab import financial_actions_metrics as metrics

PUBLIC=ROOT/'docs/evidence/financial-jev-reference-v1'


def load_cached(split):
    if split not in jev.SPLITS:raise ValueError('Unknown split')
    manifest=jev.read(PUBLIC/'manifest.json')
    for name,h in manifest['files'].items():
        if Path(name).name!=name or jev.file_sha(PUBLIC/name)!=h:
            raise ValueError('Cache integrity failure')
    protocol=jev.read(PUBLIC/'protocol.json');done=jev.read(PUBLIC/'completion.json')
    if protocol['specification']!=jev.specification():raise ValueError('Business/prompt policy changed; cache not interchangeable')
    if protocol['split_sha256'][split]!=jev.file_sha(jev.DATA/f'evaluation/{split}.json'):
        raise ValueError('Evaluation inputs/labels changed; do not reuse as same benchmark')
    if done['protocol_sha256']!=jev.digest(protocol):raise ValueError('Protocol binding changed')
    source=jev.source_rows(split);pred=jev.read(PUBLIC/(split+'-predictions.json'))
    if [p['id'] for p in pred]!=[r['id'] for r in source]:raise ValueError('Population/order mismatch')
    for row,p in zip(source,pred):
        if p['request_sha256']!=jev.digest(jev.payload(row)) or p['model']!=done['model']:
            raise ValueError('Request/model binding changed')
    return source,pred,protocol


def compare_development(path):
    rows,reference,protocol=load_cached('development')
    path=Path(path)
    if path.suffix=='.jsonl':candidate=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    else:candidate=jev.read(path)
    if not isinstance(candidate,list):raise ValueError('Expected prediction list or JSONL')
    jm=metrics.evaluate(rows,reference);cm=metrics.evaluate(rows,candidate)
    fields=['rows','action_accuracy','macro_f1','action_tool_joint_accuracy','human_misses','false_refusals','latency']
    compact=lambda m:{k:len(m[k]) if isinstance(m[k],list) else m[k] for k in fields}
    return dict(split='development',api_calls=0,reference_model=reference[0]['model'],
        jev=compact(jm),candidate=compact(cm),
        limitation='Component development comparison only; no candidate selection, final scoring, or deployment approval.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--predictions',required=True)
    args=p.parse_args();print(json.dumps(compare_development(args.predictions),ensure_ascii=False,indent=2))
