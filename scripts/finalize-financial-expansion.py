"""Review-bound, group-preserving candidate release; never permits training."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import uuid

from qwenlab import financial_supplement_expansion as e

ROOT=e.ROOT
INDEX=ROOT/'configs/financial-supplement-heldout-index-v1.json'
SCREENER=ROOT/'scripts/screen-financial-expansion-overlap.py'


def verify_screen(build,saved):
    """Replay in an isolated script; no protected corpus text enters this module."""
    scratch=ROOT/'.local/expansion-screen-replay'/uuid.uuid4().hex
    scratch.mkdir(parents=True);fresh=scratch/'report.json'
    try:
        run=subprocess.run([sys.executable,'-B',str(SCREENER),'--candidates',str((build/'candidates.json').resolve()),'--output',str(fresh)],
                           cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=600)
        if run.returncode:raise ValueError('Independent blind screening replay failed')
        if e.pilot.read(fresh)!=saved:raise ValueError('Blind report is incomplete or differs from actual replay')
    finally:
        if fresh.exists():fresh.unlink()
        scratch.rmdir()


def verify_tokens(rows,audit,candidate):
    if audit.get('candidate_sha256')!=candidate or audit.get('status')!='structural_and_token_pass' or audit.get('no_truncation') is not True:
        raise ValueError('Missing token/structure audit')
    if audit.get('tokens')!=e.token_stats(rows):raise ValueError('Full action/tool token audit differs from replay')


def reviewed_rows(rows,reviews,candidate_hash):
    new={r['id']:r for r in rows if not r['id'].startswith('FSP1-')};decisions={}
    for review in reviews:
        if review.get('candidate_sha256')!=candidate_hash or review.get('policy_sha256')!=e.pilot.protocol()[1]:raise ValueError('Review candidate/policy binding differs')
        if review.get('independent') is not True or any(review.get(k) is not False for k in ['human_reviewed','evaluation_data_read']):raise ValueError('Review independence not confirmed')
        for record in review.get('rows',[]):
            rid=record['id']
            if rid not in new or rid in decisions:raise ValueError('Unexpected or repeated reviewed ID')
            source=new[rid]
            if record.get('source_row_sha256')!=source['provenance']['source_row_sha256'] or record.get('reviewed_action')!=source['annotation']['action']:raise ValueError('Per-row review is stale')
            if record.get('decision') not in ['accept','quarantine','revise'] or not isinstance(record.get('reason'),str) or not record['reason'].strip():raise ValueError('Invalid row review')
            decisions[rid]=record
    if set(decisions)!=set(new):raise ValueError('Every new row requires exactly one independent review')
    return decisions


def split_groups(rows,decisions,screen):
    groups={r['scene_family_id'] for r in rows}
    reasons=screen['quarantine_groups_by_reason']
    if set(reasons)!={'heldout','training_pool'}:raise ValueError('Unknown/missing blind-screen roles')
    blind=set(reasons['heldout'])|set(reasons['training_pool'])
    if set(screen['quarantine_groups'])!=blind or not blind<=groups:raise ValueError('Screening group union differs')
    expected_ids={r['id'] for r in rows if r['scene_family_id'] in blind}
    if set(screen['quarantine_candidate_ids'])!=expected_ids:raise ValueError('Incomplete group quarantine IDs')
    semantic={r['scene_family_id'] for r in rows if r['id'] in decisions and decisions[r['id']]['decision']!='accept'}
    # Same full visible input is one example, not independent training evidence.
    # Keep the earliest group (inherited rows first), remove later duplicate groups.
    seen={};duplicates=set()
    for r in rows:
        key=json.dumps(r['input'],ensure_ascii=False,sort_keys=True)
        if key in seen and seen[key]!=r['scene_family_id']:duplicates.add(r['scene_family_id'])
        else:seen[key]=r['scene_family_id']
    blocked=blind|semantic|duplicates;accepted=[];quarantined=[]
    for original in rows:
        row=deepcopy(original);group=row['scene_family_id']
        tags=[]
        for reason,subset in [('heldout_lexical_match',set(reasons['heldout'])),('training_pool_duplicate',set(reasons['training_pool'])),
                              ('independent_label_review',semantic),('internal_exact_input_duplicate',duplicates)]:
            if group in subset:tags.append(reason)
        if row['id'] in decisions:row['review']=dict(type='independent_ai',**decisions[row['id']])
        row['training_eligible']=False;row['human_reviewed']=False
        row['review_status']='quarantined_by_source_group' if group in blocked else 'independent_ai_review_accepted'
        row['quarantine_reasons']=tags
        (quarantined if group in blocked else accepted).append(row)
    return accepted,quarantined


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--backend',required=True)
    parser.add_argument('--reviews',type=Path,nargs='+',required=True);parser.add_argument('--code-review',type=Path,required=True)
    parser.add_argument('--screen',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if out.exists():raise FileExistsError('Choose a new immutable reviewed output')
    if out.parent!=e.DATA:raise ValueError('Output must be inside expansion dataset')
    rows=e.verify(args.build,args.backend);candidate=e.pilot.sha(args.build/'candidates.json')
    code=e.pilot.read(args.code_review)
    if code.get('status') not in ['pass','pass_with_scope_limits'] or code.get('open_findings') or code.get('candidate_sha256')!=candidate:raise ValueError('Code review is missing/stale')
    required=[ROOT/'src/qwenlab/financial_supplement_expansion.py',Path(__file__).resolve(),SCREENER]
    if not {e.relative(p) for p in required}<=set(code.get('source_sha256',{})):raise ValueError('Incomplete code review source closure')
    for name,digest in code['source_sha256'].items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or e.pilot.sha(path)!=digest:raise ValueError('Reviewed code changed')
    audit=e.pilot.read(args.build/'audit.json')
    verify_tokens(rows,audit,candidate)
    screen=e.pilot.read(args.screen)
    if screen['candidate_sha256']!=candidate or screen['index_sha256']!=e.pilot.sha(INDEX) or screen['script_sha256']!=e.pilot.sha(SCREENER):raise ValueError('Screening dependencies changed')
    verify_screen(args.build,screen)
    for corpus in screen['corpora']:
        path=(ROOT/corpus['path']).resolve()
        if not path.is_relative_to(ROOT) or e.pilot.sha(path)!=corpus['sha256']:raise ValueError('Screening corpus changed')
    decisions=reviewed_rows(rows,[e.pilot.read(p) for p in args.reviews],candidate)
    accepted,quarantined=split_groups(rows,decisions,screen)
    out.mkdir();e.pilot.write(out/'accepted.json',accepted);e.pilot.write(out/'quarantine.json',quarantined)
    sources=[args.build/'manifest.json',args.build/'candidates.json',args.build/'audit.json',args.screen,INDEX,SCREENER,
             args.code_review,*args.reviews,Path(__file__).resolve()]
    e.pilot.write(out/'manifest.json',dict(version='financial-supplement-expansion-reviewed-v1',training_eligible=False,human_reviewed=False,
        status='independent_ai_review_complete_not_training_release',accepted=e.pilot.summary(accepted),quarantined=e.pilot.summary(quarantined),
        quarantined_groups=sorted({r['scene_family_id'] for r in quarantined}),
        files={f:e.pilot.sha(out/f) for f in ['accepted.json','quarantine.json']},sources={e.relative(p):e.pilot.sha(p) for p in sources}))
    print(json.dumps(dict(accepted=len(accepted),quarantined=len(quarantined),training_eligible=0),ensure_ascii=False))


if __name__=='__main__':main()
