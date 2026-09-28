"""Read completed development predictions; never turn errors into training rows."""
import argparse
from collections import Counter
from qwenlab.common import ROOT, load_json
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run', choices=('support-v6','support-v7'), default='support-v6')
    args=parser.parse_args()
    run=ROOT/'results'/args.run
    source={r['id']:r for r in read_rows(ROOT/'data/processed'/args.run/'legacy-dev.jsonl')}
    reference={r['id']:r for r in read_rows(run/'v5-reference/legacy-dev.jsonl')}
    after=read_rows(run/'step-200/legacy-dev.jsonl')
    regressions=[]; improvements=[]; human_misses=[]
    for row in after:
        item=source[row['id']]
        old=reference[row['id']]['predictions']['route']['choice']
        new=row['predictions']['route']['choice']; gold=row['labels']['route']
        record={'id':row['id'],'group':item['group'],'condition':item['condition'],
                'message':item['message'],'history':item.get('history',[]),'state':item.get('state',{}),
                'available_tools':item['available_tools'],'gold':gold,'reference':old,'step_200':new}
        if old==gold and new!=gold: regressions.append(record)
        if old!=gold and new==gold: improvements.append(record)
        if gold=='human' and new!='human': human_misses.append(record)
    result={'development_diagnostics_not_training_data':True,
        'route_regressions':len(regressions),'route_improvements':len(improvements),
        'human_misses':len(human_misses),'human_miss_groups':len({r['group'] for r in human_misses}),
        'human_miss_conditions':dict(Counter(r['condition'] for r in human_misses)),
        'regressions':regressions,'improvements':improvements,'human_miss_records':human_misses,
        'metrics':{name:{variant:load_json(run/variant/f'{name}-dev-metrics.json') for variant in ('v5-reference','step-200')}
                   for name in ('business','legacy','massive','crosswoz')}}
    target=ROOT/'results'/f'{args.run}-diagnostics'/'analysis.json'
    if target.exists():
        if load_json(target)!=result: raise ValueError('Diagnostic source changed')
    else:
        atomic_json(target,result)
    print({k:result[k] for k in ('route_regressions','route_improvements','human_misses','human_miss_groups','human_miss_conditions')})


if __name__=='__main__': main()
