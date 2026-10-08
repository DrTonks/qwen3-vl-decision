"""Blind, offline lexical screen. Never emit protected rows, IDs, or labels.

Freeze candidate authoring before screening. Quarantine complete new source
groups on either heldout risk or training-pool duplication; do not rewrite hits
to evade this screen. Lexical non-matches are not proof of semantic independence.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = 'configs/financial-supplement-heldout-index-v1.json'
ROLES = ('heldout', 'training_pool')
THRESHOLD_PERCENT = 85
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')


class ScreeningError(ValueError):
    """Messages deliberately contain no corpus payloads or identifiers."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized(text):
    if not isinstance(text, str):
        raise ScreeningError('Message/history content must be strings')
    text = re.sub(r'\d+', '#', unicodedata.normalize('NFKC', text).casefold())
    return ''.join(c for c in text if c.isalnum() or c == '#')


def grams(text):
    return frozenset(text[i:i + 2] for i in range(len(text) - 1))


def at_path(row, path, missing=None):
    value = row
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return missing
        value = value[key]
    return value


def input_keys(row, reader):
    message = normalized(at_path(row, reader['message_path']))
    history = at_path(row, reader['history_path'], [])
    if not isinstance(history, list):
        raise ScreeningError('History must be a list')
    turns = []
    for turn in history:
        if not isinstance(turn, dict) or not isinstance(turn.get('role'), str) or not isinstance(turn.get('content'), str):
            raise ScreeningError('History turns require role/content strings')
        turns.append((turn['role'], normalized(turn['content'])))
    # Tuple boundaries prevent role/order/turn-boundary collisions in exact keys.
    context = (message, tuple(turns))
    context_text = '\x1e'.join(role + '\x1f' + content for role, content in turns) + '\x1d' + message
    return message, context, context_text


class LexicalIndex:
    def __init__(self):
        self.messages = set()
        self.contexts = set()
        self._texts = [set(), set()]
        self._sizes = [[], []]
        self._postings = [defaultdict(list), defaultdict(list)]

    def add(self, keys):
        message, context, context_text = keys
        if message:
            self.messages.add(message)
        self.contexts.add(context)
        for channel, text in enumerate((message, context_text)):
            if text in self._texts[channel]:
                continue
            self._texts[channel].add(text)
            token_set = grams(text)
            number = len(self._sizes[channel])
            self._sizes[channel].append(len(token_set))
            for gram in token_set:
                self._postings[channel][gram].append(number)

    def near(self, text, channel):
        token_set = grams(text)
        size = len(token_set)
        if not size:
            return False
        overlaps = Counter()
        sizes = self._sizes[channel]
        for gram in token_set:
            for number in self._postings[channel].get(gram, ()):
                other_size = sizes[number]
                # Necessary bound on set sizes; does not discard >= .85 pairs.
                if 100 * min(size, other_size) >= THRESHOLD_PERCENT * max(size, other_size):
                    overlaps[number] += 1
        return any(100 * overlap >= THRESHOLD_PERCENT * (size + sizes[number] - overlap)
                   for number, overlap in overlaps.items())

    def match(self, keys):
        message, context, context_text = keys
        kinds = []
        if message and message in self.messages:
            kinds.append('numeric_normalized_message_exact')
        elif self.near(message, 0):
            kinds.append('message_bigram_jaccard_ge_0.85')
        if context in self.contexts:
            kinds.append('numeric_normalized_message_history_exact')
        elif self.near(context_text, 1):
            kinds.append('message_history_bigram_jaccard_ge_0.85')
        return kinds


def safe_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ScreeningError('Index paths must be repository-relative POSIX paths')
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ScreeningError('Index path escapes repository')
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ScreeningError('Index path escapes repository')
    return resolved


def json_data(data):
    try:
        return json.loads(data.decode('utf-8-sig'))
    except (UnicodeError, ValueError):
        raise ScreeningError('Invalid JSON; payload suppressed') from None


def load_rows(data, format_name):
    if format_name == 'json_array':
        rows = json_data(data)
    elif format_name == 'jsonl':
        try:
            rows = [json.loads(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
        except (UnicodeError, ValueError):
            raise ScreeningError('Invalid JSONL; payload suppressed') from None
    else:
        raise ScreeningError('Unsupported corpus format')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ScreeningError('Corpus must contain object rows')
    return rows


def validate_reader(reader, role):
    fields = {'message_path', 'history_path', 'missing_history', 'split_field', 'include_splits'}
    if not isinstance(reader, dict) or set(reader) != fields:
        raise ScreeningError('Invalid corpus reader fields')
    if (reader['message_path'], reader['history_path']) not in [(['message'], ['history']), (['input', 'message'], ['input', 'history'])]:
        raise ScreeningError('Unsupported message/history paths')
    if reader['missing_history'] != 'empty':
        raise ScreeningError('Unsupported missing history rule')
    splits = reader['include_splits']
    if not isinstance(splits, list) or any(not isinstance(s, str) for s in splits) or len(set(splits)) != len(splits):
        raise ScreeningError('Invalid split filter')
    if reader['split_field'] is None:
        if splits:
            raise ScreeningError('Split filter lacks a split field')
    elif reader['split_field'] != 'split' or not splits:
        raise ScreeningError('Invalid split field')
    allowed = {'train'} if role == 'training_pool' else {'development', 'dev', 'calibration', 'final', 'test', 'challenge', 'fresh_evaluation'}
    if not set(splits) <= allowed:
        raise ScreeningError('Role and split rules disagree')


def checked_bytes(root, reference):
    if set(reference) != {'path', 'sha256'}:
        raise ScreeningError('Invalid evidence reference')
    data = safe_path(root, reference['path']).read_bytes()
    if digest(data) != reference['sha256']:
        raise ScreeningError('Indexed evidence hash changed')
    return data


def load_corpora(root, index):
    if not isinstance(index, dict) or set(index) != {'version', 'corpora', 'evidence', 'counts'} or index['version'] != 'financial-supplement-heldout-index-v1':
        raise ScreeningError('Invalid coverage index')
    if not isinstance(index['corpora'], list) or not index['corpora']:
        raise ScreeningError('Empty coverage index')
    for evidence in index['evidence']:
        checked_bytes(root, evidence)
    indexes = {role: LexicalIndex() for role in ROLES}
    records = []
    seen = set()
    evidence_seen = set()
    for entry in index['corpora']:
        if set(entry) != {'path', 'format', 'role', 'reader', 'sha256', 'file_rows', 'selected_rows', 'evidence'} or entry['role'] not in ROLES:
            raise ScreeningError('Invalid corpus index entry')
        if entry['path'] in seen:
            raise ScreeningError('Duplicate corpus path in index')
        seen.add(entry['path'])
        evidence_key = (entry['evidence']['path'], entry['evidence']['sha256'])
        if evidence_key not in evidence_seen:
            checked_bytes(root, entry['evidence'])
            evidence_seen.add(evidence_key)
        reader = entry['reader']
        validate_reader(reader, entry['role'])
        data = safe_path(root, entry['path']).read_bytes()
        if digest(data) != entry['sha256']:
            raise ScreeningError('Indexed corpus hash changed')
        rows = load_rows(data, entry['format'])
        if type(entry['file_rows']) is not int or type(entry['selected_rows']) is not int or len(rows) != entry['file_rows']:
            raise ScreeningError('Indexed corpus row count changed')
        selected = rows if reader['split_field'] is None else [r for r in rows if r.get('split') in reader['include_splits']]
        if len(selected) != entry['selected_rows']:
            raise ScreeningError('Indexed split row count changed')
        for row in selected:
            indexes[entry['role']].add(input_keys(row, reader))
        records.append({k: entry[k] for k in ('path', 'role', 'sha256', 'file_rows', 'selected_rows')})
    counts = {role: {'entries': sum(r['role'] == role for r in records),
                     'selected_rows_with_snapshot_repetition': sum(r['selected_rows'] for r in records if r['role'] == role),
                     'unique_file_sha256': len({r['sha256'] for r in records if r['role'] == role})} for role in ROLES}
    if counts != index['counts'] or any(not counts[role]['entries'] for role in ROLES):
        raise ScreeningError('Coverage totals do not match index')
    return indexes, records, counts


def screen_candidates(candidates, indexes):
    if not isinstance(candidates, list) or not candidates:
        raise ScreeningError('Candidates must be a nonempty JSON array')
    identities = set()
    groups = {}
    prepared = []
    reader = {'message_path': ['input', 'message'], 'history_path': ['input', 'history']}
    for row in candidates:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not SAFE_ID.fullmatch(row[k]) for k in ('id', 'scene_family_id')):
            raise ScreeningError('Candidates require safe IDs and source groups')
        if row['id'] in identities:
            raise ScreeningError('Duplicate candidate ID')
        identities.add(row['id'])
        groups[row['id']] = row['scene_family_id']
        prepared.append((row['id'], input_keys(row, reader)))
    hits = {role: [] for role in ROLES}
    blocked = {role: set() for role in ROLES}
    for candidate_id, keys in prepared:
        for role in ROLES:
            kinds = indexes[role].match(keys)
            if kinds:
                hits[role].append({'candidate_id': candidate_id, 'source_group': groups[candidate_id], 'match_kinds': kinds})
                blocked[role].add(groups[candidate_id])
    all_blocked = set.union(*blocked.values())
    return {'hits': hits,
            'hit_candidate_counts': {role: len(hits[role]) for role in ROLES},
            'quarantine_groups_by_reason': {role: sorted(blocked[role]) for role in ROLES},
            'quarantine_groups': sorted(all_blocked),
            'quarantine_candidate_ids': sorted(i for i, group in groups.items() if group in all_blocked),
            'candidate_count': len(candidates), 'candidate_group_count': len(set(groups.values()))}


def run_screen(candidate_path, output_path, index_path=None, root=ROOT):
    root = root.resolve()
    candidate_path, output_path = Path(candidate_path).resolve(), Path(output_path).resolve()
    index_path = Path(index_path or root / DEFAULT_INDEX).resolve()
    if not all(p.is_relative_to(root) for p in (candidate_path, output_path, index_path)):
        raise ScreeningError('Inputs and output must stay inside repository')
    if output_path.exists():
        raise ScreeningError('Do not overwrite existing evidence')
    candidate_bytes, index_bytes = candidate_path.read_bytes(), index_path.read_bytes()
    indexes, records, counts = load_corpora(root, json_data(index_bytes))
    result = screen_candidates(load_rows(candidate_bytes, 'json_array'), indexes)
    result.update(version='financial-expansion-blind-lexical-v1',
                  candidate_path=candidate_path.relative_to(root).as_posix(), candidate_sha256=digest(candidate_bytes),
                  index_path=index_path.relative_to(root).as_posix(), index_sha256=digest(index_bytes),
                  script_sha256=digest(Path(__file__).read_bytes()), corpora=records, coverage_counts=counts,
                  unique_normalized_messages={role: len(indexes[role].messages) for role in ROLES},
                  unique_normalized_message_histories={role: len(indexes[role].contexts) for role in ROLES},
                  lexical_threshold=0.85, semantic_overlap_guarantee=False, training_eligible=False,
                  human_reviewed=False, model_weights_loaded=False, model_api_requests=0,
                  policy='Quarantine whole groups on either heldout leakage risk or training-pool duplicate; do not rewrite to evade matches.',
                  scope='Message and ordered role/content history only. No labels, predictions, state, or capability semantics in matching. Non-match is not proof of semantic independence.')
    # Pin input snapshots throughout a possibly long screen; never publish stale inputs.
    if digest(candidate_path.read_bytes()) != result['candidate_sha256'] or digest(index_path.read_bytes()) != result['index_sha256']:
        raise ScreeningError('Inputs changed while screening')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--index', type=Path)
    args = parser.parse_args()
    try:
        result = run_screen(args.candidates, args.output, args.index)
    except (ScreeningError, OSError, KeyError, TypeError):
        # Suppress exception payloads: malformed old files must not become logs.
        parser.exit(1, 'Screening failed: invalid schema, stale index/input, unsafe path, or output already exists. No corpus contents disclosed.\n')
    print(json.dumps({'candidate_count': result['candidate_count'],
                      'hit_candidate_counts': result['hit_candidate_counts'],
                      'quarantine_group_count': len(result['quarantine_groups']),
                      'quarantine_candidate_count': len(result['quarantine_candidate_ids']),
                      'training_eligible': False}))


if __name__ == '__main__':
    main()
