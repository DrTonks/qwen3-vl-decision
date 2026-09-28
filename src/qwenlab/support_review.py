"""Import human CSV edits into a new, hashed support evaluation version.

No models, APIs, databases or credentials are read. Original versions are immutable.
"""
import argparse
from collections import Counter
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


FIELDS = ['id', 'group', 'source_ids_json', 'message', 'history_json', 'state_json',
          'expected_action', 'expected_tool', 'expected_arguments_json', 'expected_route',
          'expected_intent', 'rationale', 'review_status', 'reviewer', 'notes', 'taxonomy_approved']
ACTIVE = {'ai_preannotated', 'accepted', 'revised'}
HELD = {'needs_discussion', 'excluded'}
TOOLS = {'queryLoanProducts', 'queryMyApplications', 'queryApplicationDetail',
         'queryMyCreditScore', 'explainApplicationStatus'}
INTENTS = {'products', 'applications', 'application_detail', 'credit', 'status_code',
           'ui_issue', 'repayment', 'payment_dispute', 'security', 'handoff', 'general'}
ACTIONS = {'tool', 'clarify', 'answer', 'human', 'refuse', 'close'}
IDENTIFIER = re.compile(r'^[A-Za-z0-9_-]{1,100}$')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'duplicate JSON key: {key}')
        value[key] = item
    return value


def _constant(value):
    raise ValueError(f'non-finite JSON value: {value}')


def parse_json(text, label):
    try:
        return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, TypeError) as error:
        raise ValueError(f'{label}: invalid JSON ({error})') from error


def load_jsonl(path):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            raise ValueError(f'{Path(path).name}:{number}: blank JSONL row')
        rows.append(parse_json(line, f'{Path(path).name}:{number}'))
    return rows


def _text(value, maximum, label, allow_empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise ValueError(f'{label}: expected {"0" if allow_empty else "1"}..{maximum} characters')


def validate_case(row):
    if not isinstance(row, dict):
        raise ValueError('case must be an object')
    case_id = row.get('id')
    if not isinstance(case_id, str) or not IDENTIFIER.fullmatch(case_id):
        raise ValueError('case ID must be a stable ASCII identifier')
    label = f'case {case_id}'
    if not isinstance(row.get('group'), str) or not IDENTIFIER.fullmatch(row['group']):
        raise ValueError(f'{label}: invalid group')
    if not isinstance(row.get('source_ids'), list) or any(not isinstance(s, str) or not IDENTIFIER.fullmatch(s) for s in row['source_ids']):
        raise ValueError(f'{label}: source_ids must contain identifiers')
    _text(row.get('message'), 2000, f'{label}.message')
    _text(row.get('rationale'), 4000, f'{label}.rationale')
    history = row.get('history')
    if not isinstance(history, list) or len(history) > 4:
        raise ValueError(f'{label}: history must contain at most four turns')
    for index, turn in enumerate(history):
        if not isinstance(turn, dict) or set(turn) != {'role', 'content'} or turn.get('role') not in ('user', 'assistant'):
            raise ValueError(f'{label}: history turn {index} must have user/assistant role and content only')
        _text(turn['content'], 800, f'{label}.history[{index}].content')
    state = row.get('state')
    if not isinstance(state, dict) or set(state) != {'pending', 'selectedApplicationId'}:
        raise ValueError(f'{label}: state only accepts pending and selectedApplicationId')
    if state['pending'] not in (None, 'applicationId', 'statusCode'):
        raise ValueError(f'{label}: invalid pending slot')
    selected = state['selectedApplicationId']
    if selected is not None and (type(selected) is not int or not 0 < selected <= 2147483647):
        raise ValueError(f'{label}: selectedApplicationId must be a positive integer or null')
    if (state['pending'] or selected is not None) and not history:
        raise ValueError(f'{label}: non-empty workflow state requires explanatory history')
    if selected is not None and not any(re.search(rf'(?<!\d){selected}(?!\d)', t['content']) for t in history):
        raise ValueError(f'{label}: selectedApplicationId must occur in the supplied history')
    expected = row.get('expected')
    if not isinstance(expected, dict) or set(expected) != {'action', 'tool', 'arguments', 'route', 'intent'}:
        raise ValueError(f'{label}: expected must contain action/tool/arguments/route/intent')
    action = expected['action']
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError(f'{label}: unsupported current action')
    route = expected['route']
    valid_routes = {'tool': ('tool',), 'clarify': ('clarify',), 'answer': ('llm',),
                    'human': (None, 'human'), 'refuse': (None,), 'close': (None,)}
    if route not in valid_routes[action]:
        raise ValueError(f'{label}: route is inconsistent with action {action}')
    intent = expected['intent']
    if intent is not None and (not isinstance(intent, str) or intent not in INTENTS):
        raise ValueError(f'{label}: invalid intent')
    arguments, tool = expected['arguments'], expected['tool']
    if not isinstance(arguments, dict):
        raise ValueError(f'{label}: arguments must be an object')
    if action == 'tool':
        if not isinstance(tool, str) or tool not in TOOLS:
            raise ValueError(f'{label}: invalid tool')
        key = 'applicationId' if tool == 'queryApplicationDetail' else 'status' if tool == 'explainApplicationStatus' else None
        if set(arguments) != ({key} if key else set()):
            raise ValueError(f'{label}: tool arguments do not match {tool}')
        if key and type(arguments[key]) is not int:
            raise ValueError(f'{label}: {key} must be an integer (not boolean/string)')
        if key == 'applicationId' and not 0 < arguments[key] <= 2147483647:
            raise ValueError(f'{label}: invalid applicationId')
        if key == 'status' and arguments[key] not in (0, 1, 2):
            raise ValueError(f'{label}: supported status codes are 0/1/2')
    elif tool is not None or arguments:
        raise ValueError(f'{label}: non-tool action must have null tool and empty arguments')
    review = row.get('review')
    if not isinstance(review, dict) or set(review) != {'status', 'reviewer', 'notes', 'taxonomy_approved'}:
        raise ValueError(f'{label}: invalid review fields')
    if not isinstance(review['status'], str) or review['status'] not in ACTIVE | HELD:
        raise ValueError(f'{label}: invalid review status')
    _text(review['reviewer'], 100, f'{label}.reviewer', True)
    _text(review['notes'], 8000, f'{label}.notes', True)
    if type(review['taxonomy_approved']) is not bool:
        raise ValueError(f'{label}: taxonomy_approved must be boolean')
    if review['status'] == 'ai_preannotated' and review['taxonomy_approved']:
        raise ValueError(f'{label}: AI-only row cannot claim human taxonomy approval')
    return row


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def csv_row(row):
    expected, review = row['expected'], row['review']
    return {'id': row['id'], 'group': row['group'], 'source_ids_json': json.dumps(row['source_ids'], ensure_ascii=False),
            'message': row['message'], 'history_json': json.dumps(row['history'], ensure_ascii=False),
            'state_json': json.dumps(row['state'], ensure_ascii=False),
            **{f'expected_{k}': expected[k] for k in ['action', 'tool', 'route', 'intent']},
            'expected_arguments_json': json.dumps(expected['arguments'], ensure_ascii=False),
            'rationale': row['rationale'], 'review_status': review['status'], 'reviewer': review['reviewer'],
            'notes': review['notes'], 'taxonomy_approved': str(review['taxonomy_approved']).lower()}


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(row) for row in rows)


def import_review(source, csv_path, output):
    source, csv_path, output = Path(source).resolve(), Path(csv_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; choose a new version directory. No files were overwritten.')
    if output == source or source in output.parents:
        raise ValueError('Output must not be inside the frozen source directory.')
    manifest_path = source / 'manifest.json'
    manifest = parse_json(manifest_path.read_text(encoding='utf-8-sig'), 'source manifest')
    hashes = manifest.get('files_sha256', {})
    for name in ('cases.jsonl', 'review-holdouts.jsonl', 'deferred-cases.jsonl'):
        file = source / name
        if name == 'cases.jsonl' or name in hashes or file.exists():
            if not file.is_file():
                raise ValueError(f'Source {name} is missing; refusing to drop records from the frozen version')
            if hashes.get(name) != digest(file):
                raise ValueError(f'Source {name} differs from its frozen hash')
    original = load_jsonl(source / 'cases.jsonl')
    if (source / 'review-holdouts.jsonl').exists():
        original += load_jsonl(source / 'review-holdouts.jsonl')
    by_id = {}
    for row in original:
        validate_case(row)
        if row['id'] in by_id:
            raise ValueError(f'Duplicate source ID: {row["id"]}')
        by_id[row['id']] = row
    if not by_id:
        raise ValueError('Source contains no cases')
    edited = {}
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != set(FIELDS):
            raise ValueError('CSV columns must match the original review.csv exactly (order may change)')
        for line, cells in enumerate(reader, 2):
            if None in cells or any(value is None for value in cells.values()):
                raise ValueError(f'CSV record {line}: incorrect number of columns; check JSON quoting')
            case_id = cells['id']
            if case_id in edited:
                raise ValueError(f'Duplicate CSV ID: {case_id}')
            if case_id not in by_id:
                raise ValueError(f'Unknown CSV ID: {case_id}; adding cases requires a separate authored version')
            old = by_id[case_id]
            sources = parse_json(cells['source_ids_json'], f'{case_id}.source_ids_json')
            if cells['group'] != old['group'] or sources != old['source_ids']:
                raise ValueError(f'{case_id}: group/source IDs are immutable during review import')
            approved = cells['taxonomy_approved'].strip().lower()
            if approved not in ('true', 'false'):
                raise ValueError(f'{case_id}: taxonomy_approved must be true or false')
            row = copy.deepcopy(old)
            row.update(message=cells['message'], history=parse_json(cells['history_json'], f'{case_id}.history_json'),
                       state=parse_json(cells['state_json'], f'{case_id}.state_json'), rationale=cells['rationale'])
            row['expected'] = {'action': cells['expected_action'].strip(), 'tool': cells['expected_tool'].strip() or None,
                               'arguments': parse_json(cells['expected_arguments_json'], f'{case_id}.expected_arguments_json'),
                               'route': cells['expected_route'].strip() or None, 'intent': cells['expected_intent'].strip() or None}
            row['review'] = {'status': cells['review_status'].strip(), 'reviewer': cells['reviewer'], 'notes': cells['notes'],
                             'taxonomy_approved': approved == 'true'}
            edited[case_id] = validate_case(row)
    missing = set(by_id) - set(edited)
    if missing:
        raise ValueError('CSV is missing IDs: ' + ', '.join(sorted(missing)))
    # Keep original order, not the arbitrary order from an Excel sort.
    rows = [edited[row['id']] for row in original]
    active = [row for row in rows if row['review']['status'] in ACTIVE]
    held = [row for row in rows if row['review']['status'] in HELD]
    changes = []
    for row in rows:
        before = by_id[row['id']]
        fields = [key for key in ('message', 'history', 'state', 'expected', 'rationale', 'review') if before[key] != row[key]]
        if fields:
            changes.append({'id': row['id'], 'changed_fields': fields})
    # All validation is completed before the destination is created.
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / 'cases.jsonl', active)
    write_jsonl(output / 'review-holdouts.jsonl', held)
    write_jsonl(output / 'review-changes.jsonl', changes)
    write_csv(output / 'review.csv', rows)
    if (source / 'deferred-cases.jsonl').exists():
        (output / 'deferred-cases.jsonl').write_bytes((source / 'deferred-cases.jsonl').read_bytes())
    review_counts = dict(Counter(row['review']['status'] for row in rows))
    next_manifest = {'version': output.name, 'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'review_imported_not_automatically_gold', 'scope': manifest.get('scope'),
        'origin': 'Imported from a paired review CSV; edited labels are not automatically independent human gold',
        'parent_version': manifest.get('version'), 'source_cases_sha256': hashes['cases.jsonl'],
        'source_manifest_sha256': digest(manifest_path), 'source_review_csv_sha256': digest(csv_path),
        'source_holdouts_sha256': hashes.get('review-holdouts.jsonl'),
        'source_total_count': len(original), 'count': len(active), 'held_count': len(held), 'review_status_counts': review_counts,
        'groups': len({row['group'] for row in active}), 'actions': dict(Counter(row['expected']['action'] for row in active)),
        'fixtures': manifest.get('fixtures'), 'split': manifest.get('split', 'evaluation_not_for_training'),
        'deferred_count': manifest.get('deferred_count', 0), 'changed_count': len(changes),
        'limitations': manifest.get('limitations', []),
        'files_sha256': {file.name: digest(file) for file in sorted(output.iterdir()) if file.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(next_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return next_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('import', help='Import a paired CSV into a new immutable dataset version')
    command.add_argument('--source', type=Path, required=True)
    command.add_argument('--csv', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = import_review(args.source, args.csv, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Review import rejected: {error}\n')
    print(json.dumps({'version': manifest['version'], 'active_count': manifest['count'],
                      'held_count': manifest['held_count'], 'review_status_counts': manifest['review_status_counts'],
                      'cases_sha256': manifest['files_sha256']['cases.jsonl']}, ensure_ascii=False, indent=2))
    if manifest['held_count']:
        print('needs_discussion/excluded rows are preserved in review-holdouts.jsonl and review.csv; excluded from active evaluation.')
    if manifest['count'] == 0:
        print('No active cases remain. This version cannot produce an evaluation accuracy score.')


if __name__ == '__main__':
    main()
