"""Release unchanged training candidates only after a bound independent AI review."""
import argparse
import copy
import json
from collections import Counter, defaultdict

from qwenlab.common import ROOT, sha
from qwenlab import financial_boundary_candidates as candidates
from qwenlab.financial_train import read, durable_json

OUT = ROOT / 'data/financial-boundary-training-v1'
REVIEW = ROOT / 'docs/evidence/financial-boundary-label-review.json'


def select_reviewed(rows, review, candidate_sha256):
    if review.get('candidate_sha256') != candidate_sha256:
        raise ValueError('Review does not bind exact candidate content')
    if review.get('reviewer_type') != 'independent_ai_agent' or not review.get('reviewer'):
        raise ValueError('Independent review identity missing')
    if review.get('human_reviewed') is not False:
        raise ValueError('AI review must not claim human review')
    records = review['records']
    ids = [r['id'] for r in records]
    if len(set(ids)) != len(ids) or set(ids) != {r['id'] for r in rows}:
        raise ValueError('Review must cover every candidate exactly once')
    if any(r['verdict'] not in {'accept', 'reject', 'needs_discussion'} or not r.get('reason') for r in records):
        raise ValueError('Invalid or unreasoned review verdict')
    by_id = {r['id']: r for r in records}
    groups = defaultdict(list)
    for row in rows:
        groups[row['scene_family_id']].append(row)
    excluded = {g: [r['id'] for r in block if by_id[r['id']]['verdict'] != 'accept']
                for g, block in groups.items() if any(by_id[r['id']]['verdict'] != 'accept' for r in block)}
    selected = [r for r in rows if r['scene_family_id'] not in excluded]
    if not selected:
        raise ValueError('No independently accepted complete groups')
    released = []
    for row in selected:
        result = copy.deepcopy(row)
        result['split'] = 'train'
        result['review'] = dict(status='independent_ai_review_accepted', human_reviewed_current_version=False,
                                independently_reviewed=True, reviewer=review['reviewer'],
                                review_file=REVIEW.relative_to(ROOT).as_posix(),
                                candidate_sha256=candidate_sha256)
        result['usage'] = 'training_only_never_evaluation'
        released.append(result)
    return released, excluded


def expected_release():
    candidates.validate()
    source = candidates.OUT / 'candidates.json'
    rows, excluded = select_reviewed(read(source), read(REVIEW), sha(source))
    return rows, excluded


def build():
    if OUT.exists():
        raise FileExistsError('Release already exists; never silently regenerate')
    rows, excluded = expected_release()
    OUT.mkdir(parents=True)
    durable_json(OUT / 'training.json', rows)
    durable_json(OUT / 'excluded-groups.json', excluded)
    sources = [candidates.OUT / 'manifest.json', candidates.OUT / 'candidates.json', REVIEW,
               ROOT / 'src/qwenlab/financial_boundary_release.py']
    manifest = dict(version=OUT.name, training_eligible=True, human_reviewed=False,
                    review_type='independent_ai_review', accepted_rows=len(rows),
                    accepted_source_groups=len({r['scene_family_id'] for r in rows}),
                    excluded_source_groups=len(excluded), actions=dict(Counter(r['annotation']['action'] for r in rows)),
                    source_files={p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
                    files={p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
                    limitation='Controlled synthetic contrasts, not new independent scenarios or human labels; whole ambiguous groups excluded.')
    durable_json(OUT / 'manifest.json', manifest)
    return validate()


def validate():
    manifest = read(OUT / 'manifest.json')
    if manifest.get('training_eligible') is not True or manifest.get('human_reviewed') is not False:
        raise ValueError('Invalid release eligibility or human review claim')
    for path, digest in manifest['source_files'].items():
        if sha(ROOT / path) != digest:
            raise ValueError('Release dependency changed: ' + path)
    for name, digest in manifest['files'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Released content changed: ' + name)
    rows, excluded = expected_release()
    if read(OUT / 'training.json') != rows or read(OUT / 'excluded-groups.json') != excluded:
        raise ValueError('Release is not unchanged accepted groups from reviewed candidates')
    if manifest['accepted_rows'] != len(rows) or manifest['accepted_source_groups'] != len({r['scene_family_id'] for r in rows}):
        raise ValueError('Release count mismatch')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['build', 'validate'])
    args = parser.parse_args()
    print(json.dumps(build() if args.command == 'build' else validate(), ensure_ascii=False, indent=2))
