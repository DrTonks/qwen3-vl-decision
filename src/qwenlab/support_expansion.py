"""Versioned training expansion and human-review import. No model/API calls."""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import json
from pathlib import Path
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from qwenlab.common import ROOT
from qwenlab import support_curriculum as base
from qwenlab.support_expansion_catalog import build_rows
from qwenlab.support_review import parse_json, validate_case

VERSION = 'support-curriculum-v2'
HEADERS = ['样本ID', '场景组', '复核状态', '当前问题', '历史对话', '业务动作', '意图', '工具',
           '参数JSON', '待补字段', '已选申请ID', '标注依据', '复核备注', '历史修改JSON']
STATUS = {'未复核': 'ai_preannotated', '通过': 'accepted', '已修改': 'revised', '待定': 'needs_discussion', '排除': 'excluded'}
SOURCE_FILES = ['src/qwenlab/support_expansion.py', 'src/qwenlab/support_expansion_catalog.py',
                'src/qwenlab/support_curriculum.py', 'configs/decision-v5.json']
EVAL_FILES = ['development-cases.jsonl', 'calibration-cases.jsonl', 'challenge-cases.jsonl',
              'development-candidates.jsonl', 'calibration-candidates.jsonl', 'challenge-model-candidates.jsonl']


def history_text(history):
    return '\n'.join(('用户：' if t['role'] == 'user' else '客服：') + t['content'] for t in history)


def review_row(row):
    e, s = row['expected'], row['state']
    return dict(zip(HEADERS, [row['id'], row['group'], next(k for k, v in STATUS.items() if v == row['review']['status']),
        row['message'], history_text(row['history']), e['action'], e['intent'] or '', e['tool'] or '',
        json.dumps(e['arguments'], ensure_ascii=False), s['pending'] or '', s['selectedApplicationId'] or '',
        row['rationale'], row['review']['notes'], '']))


def clean_key(row):
    # Exact observable-context de-duplication, not a semantic novelty claim.
    return json.dumps({'message': base.normalize(row['message']), 'history': row['history'], 'state': row['state']},
                      ensure_ascii=False, sort_keys=True)


def unique_rows(rows):
    seen, output, excluded = {}, [], []
    for row in rows:
        key = clean_key(row)
        if key in seen:
            if seen[key]['expected'] != row['expected']:
                raise ValueError('Conflicting labels for duplicate input: ' + row['id'])
            excluded.append({'id': row['id'], 'duplicate_of': seen[key]['id']})
        else:
            seen[key] = row
            output.append(row)
    return output, excluded


def heldout_rows(v1):
    return [r for filename in EVAL_FILES[:3] for r in base.read_rows(v1 / filename)]


def regression_sources(v1):
    paths = [v1 / name for name in EVAL_FILES[:3]] + [ROOT / 'data/support-runtime-v1/cases.jsonl']
    paths += [ROOT / f'data/processed/v5/business-{s}.jsonl' for s in ('dev', 'calibration', 'test')]
    sources = {}
    for i, path in enumerate(paths):
        if not path.is_file():
            raise FileNotFoundError('Required heldout corpus: ' + path.name)
        sources[f'{i + 1}:{path.name}'] = base.read_rows(path)
    return sources, {f'{i + 1}:{p.name}': {'sha256': base.digest(p), 'count': len(sources[f'{i + 1}:{p.name}'])}
                     for i, p in enumerate(paths)}


def evaluate_rows(project, rows, heldouts, regressions):
    for row in rows:
        validate_case(row)
    approved_ids = {r['id'] for r in rows if r['review']['status'] not in {'needs_discussion', 'excluded'}}
    active = [r for r in rows if r['id'] in approved_ids]
    base.validate_structure(active + heldouts)
    observations = base.normalize_with_backend(project, rows + heldouts)
    # Train filtering uses old evaluation wording; unchanged heldouts are added
    # only for normalized-input collision checks, never for train supervision.
    by_observation = {r['id']: r for r in observations}
    audit, candidates = base.audit_candidates(active + heldouts,
        [by_observation[r['id']] for r in active + heldouts], regressions)
    # Retain diagnostics for held rows without letting excluded labels block
    # conflict checks over the actual training population.
    for row in rows:
        if row['id'] not in approved_ids:
            records, _ = base.audit_candidates([row], [by_observation[row['id']]], regressions)
            audit.extend(records)
    row_by_id = {r['id']: r for r in rows}
    audit = [r for r in audit if r['id'] in row_by_id]
    candidates = [r for r in candidates if r['id'] in row_by_id and r['split'] == 'train']
    incomplete = {r['id'] for r in rows if r['expected']['route'] and r['expected']['intent'] is None}
    candidates = [r for r in candidates if r['id'] in approved_ids and r['id'] not in incomplete]
    for c in candidates:
        status = row_by_id[c['id']]['review']['status']
        c['label_status'] = 'human_reviewed' if status in {'accepted', 'revised'} else 'pending_review'
    for record in audit:
        if record['id'] in incomplete:
            record['held_reasons'].append('missing_intent_label')
            record['eligible_for_draft_experiment'] = False
        if record['id'] not in approved_ids:
            record['held_reasons'].append('review:' + row_by_id[record['id']]['review']['status'])
            record['eligible_for_draft_experiment'] = False
    return audit, candidates, [r for r in observations if r['id'] in row_by_id]


def check_frozen(source):
    source = Path(source)
    manifest = parse_json((source / 'manifest.json').read_text(encoding='utf-8-sig'), 'manifest')
    required = {'cases.jsonl', 'train-candidates.jsonl', 'review.json', 'regression-fingerprints.json',
                'source-snapshot.json', 'eligibility.jsonl', 'runtime-inputs.jsonl', 'train-reviewed-only.jsonl', *EVAL_FILES}
    hashes = manifest.get('files_sha256', {})
    if not required <= hashes.keys():
        raise ValueError('Incomplete manifest')
    for name, digest in hashes.items():
        if Path(name).name != name or not (source / name).is_file() or base.digest(source / name) != digest:
            raise ValueError('Frozen file missing or changed: ' + name)
    return manifest


def fingerprint(text):
    import hashlib
    return hashlib.sha256(base.normalize(text).encode('utf-8')).hexdigest()


def fingerprints(regressions):
    return {name: sorted({fingerprint(row['message']) for row in values}) for name, values in regressions.items()}


def apply_fingerprints(rows, mapping):
    """Create minimum exclusion inputs without publishing old heldout text again."""
    result = {}
    for name, hashes in mapping.items():
        blocked = set(hashes)
        result[name] = [{'message': r['message']} for r in rows if fingerprint(r['message']) in blocked]
    return result


def write_version(output, rows, candidates, audit, observations, source, provenance, fingerprint_map, min_count=0, review_ids=None):
    output, source = Path(output).resolve(), Path(source).resolve()
    if output.exists() or output == source or source in output.parents:
        raise FileExistsError('Choose a new sibling output directory; frozen files and review edits are never overwritten')
    if len(candidates) < min_count:
        raise ValueError(f'Only {len(candidates)} eligible rows, below target {min_count}')
    output.mkdir(parents=True)
    for name in EVAL_FILES:
        shutil.copyfile(source / name, output / name)
    if (source / 'source-snapshot.json').is_file():
        shutil.copyfile(source / 'source-snapshot.json', output / 'source-snapshot.json')
    base.write_rows(output / 'cases.jsonl', rows)
    base.write_rows(output / 'train-candidates.jsonl', candidates)
    reviewed = {r['id'] for r in rows if r['review']['status'] in {'accepted', 'revised'}}
    base.write_rows(output / 'train-reviewed-only.jsonl', [r for r in candidates if r['id'] in reviewed])
    base.write_rows(output / 'eligibility.jsonl', audit)
    base.write_rows(output / 'runtime-inputs.jsonl', observations)
    eligible_ids = {r['id'] for r in candidates}
    # The initial review covers eligible candidates. Subsequent imports preserve
    # that scope so held/excluded rows can be corrected and reinstated later.
    review_ids = eligible_ids if review_ids is None else review_ids
    review = [review_row(r) for r in rows if r['id'] in review_ids]
    base.write_json(output / 'review.json', {'headers': HEADERS, 'rows': review})
    base.write_json(output / 'regression-fingerprints.json', fingerprint_map)
    reviewed_candidate_count = sum(r['id'] in reviewed for r in candidates)
    all_candidates_reviewed = bool(candidates) and reviewed_candidate_count == len(candidates)
    manifest = {
        'version': VERSION, 'hash_algorithm': 'sha256_after_CRLF_to_LF',
        'status': 'reviewed_candidates_awaiting_training_authorization' if all_candidates_reviewed else 'ready_for_review',
        'training_started': False, 'training_authorized': False,
        'count': len(rows), 'eligible_train_count': len(candidates),
        'scenario_groups': len({r['group'] for r in candidates}),
        'unique_messages': len({base.normalize(r['message']) for r in candidates}),
        'routes': dict(Counter(r['labels']['route'] for r in candidates)),
        'intents': dict(Counter(r['labels']['intent'] for r in candidates)),
        'tools': dict(Counter(r['labels']['tool'] for r in candidates)),
        'runtime_paths': dict(Counter(r['runtime_path'] for r in candidates)),
        'contexts': dict(Counter(r.get('augmentation', 'legacy') for r in rows if r['id'] in eligible_ids)),
        'review_counts': dict(Counter(r['review']['status'] for r in rows if r['id'] in eligible_ids)),
        'all_row_review_counts': dict(Counter(r['review']['status'] for r in rows)),
        'reviewed_eligible_count': reviewed_candidate_count,
        'held_reasons': dict(Counter(reason for r in audit for reason in r['held_reasons'])),
        'provenance': provenance,
        'generator_hashes': {p: base.digest(ROOT / p) for p in SOURCE_FILES},
        'limitations': ['Rows are scenario/expression/context combinations, not independent users',
                       'Exact normalized de-duplication does not establish semantic independence',
                       'Model and full component metrics must attribute backend guards separately',
                       'Authorship provenance is preserved after review; human review does not imply real user data',
                       'Only recorded accepted/revised rows count as reviewed; held rows remain outside training',
                       'Training requires separate explicit user authorization'],
        'files_sha256': {p.name: base.digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    base.write_json(output / 'manifest.json', manifest)
    return manifest


def build(project, output, v1=None):
    v1 = Path(v1 or ROOT / 'data/support-curriculum-v1')
    base.check(v1, project)
    eligible_ids = {r['id'] for r in base.read_rows(v1 / 'train-candidates.jsonl')}
    legacy = [r for r in base.read_rows(v1 / 'train-cases.jsonl') if r['id'] in eligible_ids]
    proposed, duplicates = unique_rows(legacy + build_rows())
    regressions, regression_meta = regression_sources(v1)
    heldouts = heldout_rows(v1)
    audit, candidates, observations = evaluate_rows(project, proposed, heldouts, regressions)
    # Keep every new holdout byte unchanged; train-only expansion cannot reshuffle it.
    report = write_version(output, proposed, candidates, audit, observations, v1,
        {'source_manifest_sha256': base.digest(v1 / 'manifest.json'),
         'origin': 'Assistant-authored training scenarios, programmatic expression/context composition; human review recorded per row',
         'legacy_train_rows': len(legacy), 'new_proposed_rows': len(proposed) - len(legacy),
         'duplicate_rows_removed': duplicates, 'heldout_sources': regression_meta,
         'human_review_completed': False}, fingerprints(regressions), min_count=3000)
    return report


def read_xlsx(path):
    """Read flat, value-only review rows using stdlib; no Excel dependency.

    Formula cells on the review sheet are rejected (no cached-value guessing).
    Other sheets, including instructions/formulas, are not imported.
    """
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rel_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    with zipfile.ZipFile(path) as z:
        if sum(info.file_size for info in z.infolist()) > 80 * 1024 * 1024:
            raise ValueError('Review workbook is unexpectedly large')
        book = ET.fromstring(z.read('xl/workbook.xml'))
        sheet = next((s for s in book.findall('m:sheets/m:sheet', ns) if s.get('name') == '训练复核'), None)
        if sheet is None:
            raise ValueError('Missing worksheet 训练复核')
        relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rel = next(r for r in relationships if r.get('Id') == sheet.get(rel_ns))
        target = rel.get('Target', '')
        if rel.get('TargetMode') == 'External' or '..' in Path(target).parts:
            raise ValueError('Invalid worksheet relationship')
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(t.text or '' for t in si.findall('.//m:t', ns))
                       for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        grid = []
        for row in ET.fromstring(z.read(target)).findall('m:sheetData/m:row', ns):
            record = {}
            for cell in row.findall('m:c', ns):
                if cell.find('m:f', ns) is not None:
                    raise ValueError('Review cells must contain values, not formulas: ' + cell.get('r', ''))
                col = re.match(r'[A-Z]+', cell.get('r', ''))
                if not col:
                    raise ValueError('Cell address is missing')
                index = 0
                for char in col.group():
                    index = index * 26 + ord(char) - 64
                v = cell.find('m:v', ns)
                text = v.text if v is not None and v.text is not None else ''
                if cell.get('t') == 's':
                    text = strings[int(text)]
                elif cell.get('t') == 'inlineStr':
                    inline = cell.find('m:is', ns)
                    text = ''.join(inline.itertext()) if inline is not None else ''
                record[index - 1] = text
            values = [record.get(i, '') for i in range(max(len(HEADERS), max(record, default=-1) + 1))]
            if any(values):
                grid.append(values)
    if not grid or grid[0] != HEADERS:
        raise ValueError('Review headers changed; keep the original table headers')
    if any(len(r) != len(HEADERS) for r in grid[1:]):
        raise ValueError('Unexpected extra review columns')
    return [dict(zip(HEADERS, r)) for r in grid[1:]]


def read_edits(path):
    path = Path(path)
    if path.suffix.lower() == '.xlsx':
        return read_xlsx(path)
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != HEADERS:
                raise ValueError('CSV headers changed')
            return list(reader)
    raise ValueError('Review file must be .xlsx or UTF-8 CSV')


def apply_edits(original_rows, review_rows, expected_ids, reviewer):
    if len(review_rows) != len(expected_ids) or {r.get('样本ID') for r in review_rows} != expected_ids:
        raise ValueError('Review ID set changed: do not delete, duplicate or add rows; mark 排除 instead')
    indexed = {r['样本ID']: r for r in review_rows}
    output, changes = [], []
    for original in original_rows:
        row = deepcopy(original)
        if row['id'] not in expected_ids:
            output.append(row)
            continue
        values = indexed[row['id']]
        if values['场景组'] != row['group'] or values['历史对话'] != history_text(row['history']):
            raise ValueError('Read-only group/history changed: ' + row['id'] + '; use 历史修改JSON for advanced edits')
        status = STATUS.get(values['复核状态'])
        if status is None:
            raise ValueError('Unknown review status: ' + row['id'])
        row['message'], row['rationale'] = values['当前问题'], values['标注依据']
        action = values['业务动作']
        row['expected'] = {'action': action, 'route': {'tool': 'tool', 'answer': 'llm', 'clarify': 'clarify', 'human': 'human'}.get(action),
                           'intent': values['意图'] or None, 'tool': values['工具'] or None,
                           'arguments': parse_json(values['参数JSON'], row['id'] + ' 参数JSON')}
        raw_id = str(values['已选申请ID']).strip()
        if raw_id and not re.fullmatch(r'[1-9][0-9]*', raw_id):
            raise ValueError('Selected application ID must be a positive integer: ' + row['id'])
        row['state'] = {'pending': values['待补字段'] or None, 'selectedApplicationId': int(raw_id) if raw_id else None}
        if values['历史修改JSON'].strip():
            row['history'] = parse_json(values['历史修改JSON'], row['id'] + ' 历史修改JSON')
        changed = any(row[k] != original[k] for k in ('message', 'history', 'state', 'expected', 'rationale'))
        if changed and status in {'ai_preannotated', 'accepted'}:
            raise ValueError('Edited rows must be marked 已修改/待定/排除: ' + row['id'])
        review_changed = changed or status != original['review']['status'] or values['复核备注'] != original['review']['notes']
        if review_changed and status in {'accepted', 'revised'} and not reviewer.strip():
            raise ValueError('Use --reviewer to attribute completed review')
        if review_changed:
            row['review'] = {'status': status, 'reviewer': reviewer.strip() if status != 'ai_preannotated' else '',
                             'notes': values['复核备注'], 'taxonomy_approved': False}
        validate_case(row)
        if changed or row['review'] != original['review']:
            changes.append({'id': row['id'], 'content_changed': changed, 'review_status': status,
                            'previous_review': original['review'], 'new_review': row['review']})
        output.append(row)
    return output, changes


def import_review(project, source, review_file, output, reviewer):
    source = Path(source)
    source_manifest = check_frozen(source)
    if base.source_snapshot(project) != json.loads((source / 'source-snapshot.json').read_text(encoding='utf-8')):
        raise ValueError('Project capability snapshot changed; revalidate as a new dataset before importing review')
    old = base.read_rows(source / 'cases.jsonl')
    expected_ids = {r['样本ID'] for r in json.loads((source / 'review.json').read_text(encoding='utf-8'))['rows']}
    rows, changes = apply_edits(old, read_edits(review_file), expected_ids, reviewer)
    mapping = json.loads((source / 'regression-fingerprints.json').read_text(encoding='utf-8'))
    audit, candidates, observations = evaluate_rows(project, rows, heldout_rows(source), apply_fingerprints(rows, mapping))
    accepted = {r['id'] for r in rows if r['review']['status'] in {'accepted', 'revised'}}
    # Do not silently discard newly reviewed labels that the pipeline cannot use.
    bad = [r for r in audit if r['id'] in accepted and r['held_reasons']]
    if bad:
        raise ValueError('Reviewed rows fail validation; mark 待定 or fix them: ' + json.dumps(bad[:5], ensure_ascii=False))
    completed = {r['id'] for r in rows if r['review']['status'] in {'accepted', 'revised', 'excluded'}} & expected_ids
    return write_version(output, rows, candidates, audit, observations, source,
        {'origin': source_manifest['provenance']['origin'], 'parent_manifest_sha256': base.digest(source / 'manifest.json'),
         'review_file_sha256': base.digest(review_file), 'changes': changes,
         'human_review_completed': bool(expected_ids) and completed == expected_ids,
         'reviewed_row_count': len(accepted), 'completed_review_row_count': len(completed),
         'reviewer': reviewer}, mapping, review_ids=expected_ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check', 'import-review'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--reviewer', default='')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        if not args.project or not args.output:
            parser.error('build requires --project and --output')
        result = build(args.project, args.output)
    elif args.command == 'import-review':
        if not all((args.project, args.source, args.review, args.output)):
            parser.error('import-review requires --project, --source, --review and --output')
        result = import_review(args.project, args.source, args.review, args.output, args.reviewer)
    else:
        if not args.source:
            parser.error('check requires --source')
        result = check_frozen(args.source)
    print(json.dumps({k: result[k] for k in ('status', 'eligible_train_count', 'scenario_groups', 'unique_messages', 'routes', 'reviewed_eligible_count')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
