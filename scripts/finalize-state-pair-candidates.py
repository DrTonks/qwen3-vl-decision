"""Archive reviewed candidates for sampling design; never approve training."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from qwenlab.common import ROOT, sha
from qwenlab.financial_state_pair_candidates import DATA, DEFAULT_BACKEND, encoded, read, verify


def review_rows(rows, review, screen):
    if review['scope']['human_reviewed'] is not False or review['scope']['training_eligible'] is not False or review['failures']:
        raise ValueError('Invalid independent review provenance/failures')
    by_group={r['source_group']:r for r in review['reviews']}
    if len(by_group)!=len(review['reviews']) or set(by_group)!={r['scene_family_id'] for r in rows}:
        raise ValueError('Review does not exactly cover candidate groups')
    variants={v['id']:v for g in review['reviews'] for v in g['variants']}
    if len(variants)!=sum(len(g['variants']) for g in review['reviews']) or set(variants)!={r['id'] for r in rows}:
        raise ValueError('Review does not exactly cover candidate rows')
    blocked=set(screen['quarantine_groups'])
    if not blocked<=set(by_group):raise ValueError('Unknown quarantined group')
    # Require group verdicts to agree with the row-level judgments.
    for group in by_group.values():
        expected_ids={r['id'] for r in rows if r['scene_family_id']==group['source_group']}
        if {v['id'] for v in group['variants']}!=expected_ids:
            raise ValueError('Review variant assigned to wrong story group')
        if group['verdict'] not in ('keep','quarantine'):raise ValueError('Unknown review verdict')
        if group['verdict']=='quarantine':blocked.add(group['source_group'])
        if any(v['verdict']!='keep' or v['failures'] for v in group['variants']):blocked.add(group['source_group'])
    accepted=[]; quarantine=[]
    for source in rows:
        row=deepcopy(source); reviewed=variants[row['id']]
        if any(reviewed[k]!=row['annotation'][k] for k in ('action','tool_name','tool_arguments','missing_slots')):
            raise ValueError('Independent labels disagree with source')
        if reviewed['human_reviewed'] is not False or reviewed['training_eligible'] is not False:
            raise ValueError('Independent review cannot approve training or claim human provenance')
        row['review_status']='quarantined' if row['scene_family_id'] in blocked else 'independent_ai_reviewed_candidate'
        row['training_eligible']=False;row['human_reviewed']=False
        (quarantine if row['scene_family_id'] in blocked else accepted).append(row)
    return accepted,quarantine


def resolve_review_reference(name):
    # Review paths are logical workspace identities, never machine absolute paths.
    if name.startswith('qwen/'):
        target=ROOT/name.removeprefix('qwen/')
        base=ROOT
    elif name.startswith('uestc_Integrated_Design/'):
        base=ROOT.parent/'uestc_Integrated_Design';target=base/name.removeprefix('uestc_Integrated_Design/')
    elif name=='.local/state-pair-label-review.json':
        target=DATA/'checks/semantic-initial.json';base=DATA
    else:raise ValueError('Unknown review reference namespace')
    if not target.resolve().is_relative_to(base.resolve()):raise ValueError('Escaping review reference')
    return target


def check_evidence():
    verify(DATA/'build',DEFAULT_BACKEND)
    review=read(DATA/'checks/semantic-review.json');screen=read(DATA/'checks/blind-overlap.json')
    for ref in review['source_sha_binding']:
        if sha(resolve_review_reference(ref['path']))!=ref['sha256']:raise ValueError('Stale semantic source')
    if screen['candidate_sha256']!=sha(DATA/'build/candidates.json') or screen['index_sha256']!=sha(DATA/'checks/coverage-index.json'):
        raise ValueError('Stale blind screen input')
    if screen['script_sha256']!=sha(ROOT/'scripts/screen-financial-expansion-overlap.py'):
        raise ValueError('Stale blind screening engine')
    accounting=read(DATA/'checks/input-accounting.json')
    if accounting['candidate_sha256']!=sha(DATA/'build/candidates.json') or accounting['truncated'] is not False:
        raise ValueError('Stale or truncated tokenizer check')
    for field,name in [('script_sha256','scripts/check-state-pair-inputs.py'),('prompt_sha256','src/qwenlab/financial_prompt_v2.py')]:
        if accounting[field]!=sha(ROOT/name):raise ValueError('Stale tokenizer accounting source')
    for ref,digest in accounting['tokenizer_sha256'].items():
        if sha(ROOT/ref)!=digest:raise ValueError('Changed tokenizer')
    code=read(DATA/'checks/code-review.json')
    if code['blocking_findings']:raise ValueError('Unresolved blocking code review')
    expected={'src/qwenlab/financial_state_pair_candidates.py','scripts/replay-state-pair-decisions.cjs',
              'scripts/screen-state-pair-candidates.py','tests/test_financial_state_pair_candidates.py'}
    if set(code['source_sha256'])!=expected:raise ValueError('Incomplete code review source bindings')
    for name,digest in code['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Stale code review')
    # AI review prose is advisory; source bindings prevent an old review from
    # silently appearing to cover a changed implementation.
    return review,screen,accounting,code


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['finalize','verify']);args=parser.parse_args()
    destination=DATA/'readiness-manifest.json'
    if args.command=='finalize':
        if destination.exists():raise FileExistsError('No finalized evidence overwrite')
        for source,name in [('state-pair-label-review.json','semantic-initial.json'),('state-pair-label-review-final.json','semantic-review.json')]:
            payload=(ROOT.parent/'.local'/source).read_bytes(); target=DATA/'checks'/name
            if target.exists():
                if target.read_bytes()!=payload:raise ValueError('Existing semantic evidence differs; do not overwrite')
            else:
                with target.open('xb') as f:f.write(payload)
    review,screen,accounting,code=check_evidence()
    accepted,quarantine=review_rows(read(DATA/'build/candidates.json'),review,screen)
    summary=dict(version='financial-state-pair-candidate-readiness-v1',accepted_candidates=len(accepted),
                 accepted_groups=len({r['scene_family_id'] for r in accepted}),quarantine_candidates=len(quarantine),
                 status='ready_for_sampling_design_only',training_eligible=False,human_reviewed=False,
                 training_executed=False,model_api_requests=0,weights_loaded=False)
    if args.command=='finalize':
        for name,value in [('reviewed-candidates.json',accepted),('quarantine.json',quarantine),('readiness-summary.json',summary)]:
            with (DATA/name).open('xb') as f:f.write(encoded(value))
        evidence=sorted([p for sub in ('build','checks') for p in (DATA/sub).iterdir() if p.is_file()]+[DATA/'stories.json',DATA/'reviewed-candidates.json',DATA/'quarantine.json',DATA/'readiness-summary.json'])
        sources=['scripts/finalize-state-pair-candidates.py','scripts/check-state-pair-inputs.py','scripts/screen-state-pair-candidates.py',
                 'tests/test_financial_state_pair_candidates.py','tests/test_state_pair_readiness.py','src/qwenlab/financial_service_v2_data.py',
                 'src/qwenlab/financial_serve_v2.py','src/qwenlab/financial_prompt_v2.py','src/qwenlab/common.py']
        manifest=dict(**summary,files={p.relative_to(DATA).as_posix():sha(p) for p in evidence},
                      sources={p:sha(ROOT/p) for p in sources})
        with destination.open('xb') as f:f.write(encoded(manifest))
    else:
        manifest=read(destination)
        for name,digest in manifest['files'].items():
            if sha(DATA/name)!=digest:raise ValueError('Readiness evidence changed: '+name)
        for name,digest in manifest['sources'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Readiness source changed: '+name)
        for name,value in [('reviewed-candidates.json',accepted),('quarantine.json',quarantine),('readiness-summary.json',summary)]:
            if (DATA/name).read_bytes()!=encoded(value):raise ValueError('Readiness replay changed')
        if any(manifest[k]!=v for k,v in summary.items()):raise ValueError('Readiness status changed')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
