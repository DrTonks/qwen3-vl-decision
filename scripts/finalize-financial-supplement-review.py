"""Package reviewed candidates, preserving group quarantine and training=false."""
import argparse
from copy import deepcopy
from pathlib import Path

from qwenlab import financial_supplement_pilot as p


def classify(rows, label_review, blind_review, candidate_hash):
    if label_review.get('candidate_file_sha256') != candidate_hash or blind_review.get('candidate_sha256') != candidate_hash:
        raise ValueError('Review does not bind these candidates')
    if label_review.get('policy_sha256') != p.protocol()[1]: raise ValueError('Wrong label policy')
    for field in ['human_reviewed','heldout_read','evaluation_data_read','screen_results_read','training_or_api_run']:
        if label_review.get(field) is not False: raise ValueError('Independent review scope not confirmed')
    decisions=label_review.get('rows',[])
    by_id={r['id']:r for r in decisions}
    if len(decisions)!=len(rows) or len(by_id)!=len(rows) or set(by_id)!={r['id'] for r in rows}:
        raise ValueError('Independent review must cover every candidate exactly once')
    valid_groups={r['scene_family_id'] for r in rows}
    blocked=set(blind_review['quarantine_groups'])
    if not blocked <= valid_groups: raise ValueError('Unknown quarantine group')
    for row in rows:
        review=by_id[row['id']]
        if review['source_row_sha256']!=row['provenance']['source_row_sha256'] or review['reviewed_action']!=row['annotation']['action']:
            raise ValueError('Stale per-row annotation review')
        if review['decision'] not in ['accept','quarantine','revise'] or not review['reason']:
            raise ValueError('Invalid review decision')
        if review['decision']!='accept': blocked.add(row['scene_family_id'])
    accepted=[];quarantined=[]
    for original in rows:
        row=deepcopy(original);r=by_id[row['id']]
        row['review_status']='quarantined_by_source_group' if row['scene_family_id'] in blocked else 'independent_ai_review_accepted'
        row['review']=dict(type='independent_ai',decision=r['decision'],reason=r['reason'],human_reviewed=False)
        row['training_eligible']=False
        (quarantined if row['scene_family_id'] in blocked else accepted).append(row)
    return accepted,quarantined


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--backend',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists(): raise FileExistsError('Keep prior reviewed package; use a new output directory')
    if not out.is_relative_to(p.DATA): raise ValueError('Output must stay in this dataset directory')
    rows=p.verify(args.build,args.backend);candidate_hash=p.sha(args.build/'candidates.json')
    labels=p.ROOT/'docs/evidence/financial-supplement-pilot-label-review-v2.json'
    code=p.ROOT/'docs/evidence/financial-supplement-pilot-code-review-v2.json'
    code_review=p.read(code)
    if code_review.get('status')!='pass_with_scope_limits' or code_review.get('open_findings'):
        raise ValueError('Code review has open findings')
    if code_review['code_sha256']!=p.sha(Path(p.__file__)) or code_review['candidate_sha256']!=candidate_hash:
        raise ValueError('Code review is stale')
    audit=p.read(args.build/'audit.json');blind=p.read(args.build/'blind-overlap.json')
    if audit['candidate_sha256']!=candidate_hash or audit['status']!='pass' or audit.get('no_truncation') is not True:
        raise ValueError('Token/schema audit not complete')
    if blind['script_sha256']!=p.sha(p.ROOT/'scripts/screen-financial-supplement-overlap.py'):
        raise ValueError('Blind screening implementation changed')
    for split, record in blind['corpora'].items():
        if split not in ['train','development','calibration','final'] or record['source_sha256']!=p.sha(p.ROOT/'data/financial-service-v2'/f'{split}.json'):
            raise ValueError('Blind screening corpus changed')
    if set(blind['corpora']) != {'train','development','calibration','final'}: raise ValueError('Incomplete overlap coverage')
    accepted,quarantined=classify(rows,p.read(labels),blind,candidate_hash)
    out.mkdir()
    p.write(out/'accepted.json',accepted);p.write(out/'quarantine.json',quarantined)
    dependencies=[args.build/'manifest.json',args.build/'candidates.json',args.build/'audit.json',args.build/'blind-overlap.json',labels,code,Path(__file__)]
    p.write(out/'manifest.json',dict(version='financial-supplement-pilot-reviewed-v1',training_eligible=False,human_reviewed=False,
            status='independent_ai_review_complete_not_a_training_release',accepted=p.summary(accepted),
            quarantined_ids=[r['id'] for r in quarantined],quarantined_groups=sorted({r['scene_family_id'] for r in quarantined}),
            sources={f.resolve().relative_to(p.ROOT).as_posix():p.sha(f) for f in dependencies},
            files={name:p.sha(out/name) for name in ['accepted.json','quarantine.json']}))
    print(f'Reviewed candidates: {len(accepted)} accepted; {len(quarantined)} quarantined; 0 training eligible.')


if __name__=='__main__':main()
