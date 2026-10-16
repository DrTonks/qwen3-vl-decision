"""User-authorized bounded recovery around the frozen proxy evaluator.

Successful requests are never repeated. Every uncertain attempt is archived
before reissuing. This supplements, rather than rewrites, the original protocol.
"""
import argparse
from collections import Counter
import time

from qwenlab import financial_jev_current_proxy as current

io = current.io
RETRIES = current.OUT / 'authorized-retries'
AUTH = current.OUT / 'retry-authorization.json'
MAX_EXTRA = 64
PER_REQUEST = 3


def authorization():
    value = dict(version='financial-jev-proxy-recovery-v1',
        user_instruction='允许多次重试和测试，最终目的是要拿出能够写在readme上的测评结果',
        scope='same frozen 128-row development; no prompt changes; successful cache reused',
        max_extra_requests=MAX_EXTRA, max_retries_per_request=PER_REQUEST,
        maximum_attempts=current.MAX_REQUESTS + MAX_EXTRA,
        backoff_seconds=[2, 4, 8],
        retryable_http=[408, 429, 500, 502, 503, 504],
        retryable_transport=['URLError', 'TimeoutError', 'ConnectionError', 'ConnectionResetError'],
        unknown_prior_cost='Failed/uncertain requests may have been billed; usage cannot be assumed zero',
        original_protocol_sha256=io.file_sha(current.OUT / 'protocol.json'),
        recovery_source_sha256=io.file_sha(__file__))
    if AUTH.exists() and io.read(AUTH) != value:
        raise ValueError('Recovery authorization changed')
    if not AUTH.exists(): io.write(AUTH, value)
    return value


def retryable(record, auth):
    if record.get('state') not in ('failed_or_uncertain', 'pending'):
        return False
    if record.get('state') == 'pending': return True
    return (record.get('http_status') in auth['retryable_http'] or
            record.get('error') in auth['retryable_transport'])


def archives():
    return sorted(RETRIES.glob('attempt-*/failed.json'))


def pending_failure(rows):
    allowed = {f'{r["id"]}-{task}.json': io.digest(current.payload(r, task))
               for r in rows for task in ('action', 'tool')}
    failed = []
    for path in (current.OUT / 'requests').glob('*.json'):
        record = io.read(path)
        if record.get('request_sha256') != allowed.get(path.name):
            raise ValueError('Unexpected request fingerprint')
        if record.get('state') != 'returned': failed.append((path, record))
    if len(failed) > 1: raise ValueError('Multiple unresolved requests need inspection')
    return failed[0] if failed else None


def archive_for_retry(path, record, auth):
    old = [io.read(p) for p in archives()]
    count = sum(r['request_sha256'] == record['request_sha256'] for r in old)
    if len(old) >= MAX_EXTRA or count >= PER_REQUEST:
        raise RuntimeError('Authorized retry limit reached')
    if not retryable(record, auth):
        raise RuntimeError('Non-transient failure; do not keep retrying')
    folder = RETRIES / f'attempt-{len(old) + 1:03d}'
    if folder.exists(): raise ValueError('Partial archive exists; inspect instead of overwriting')
    delay = auth['backoff_seconds'][count]
    io.write(folder / 'authorization.json', dict(request_sha256=record['request_sha256'],
        original_path=path.relative_to(current.OUT).as_posix(),
        original_sha256=io.file_sha(path), retry_ordinal=count + 1,
        backoff_s=delay, authorized_by=AUTH.name, at=io.now()))
    # Both paths are fixed descendants of the same experiment; never move a tree.
    if not path.resolve().is_relative_to(current.OUT.resolve()):
        raise ValueError('Unexpected source path')
    if not folder.resolve().is_relative_to(current.OUT.resolve()):
        raise ValueError('Unexpected archive path')
    path.replace(folder / 'failed.json')
    print(f'Retry {count + 1}/{PER_REQUEST}: {record["id"]}/{record["task"]}; '
          f'archived failures {len(old) + 1}/{MAX_EXTRA}; wait {delay}s', flush=True)
    time.sleep(delay)


def accounting():
    successful = [io.read(p) for p in (current.OUT / 'requests').glob('*.json')]
    failed = [io.read(p) for p in archives()]
    notes = [io.read(p.parent / 'authorization.json') for p in archives()]
    if any(r['state'] != 'returned' for r in successful):
        raise ValueError('Accounting requires a complete successful cache')
    elapsed = Counter()
    for record in successful + failed:
        elapsed[record['id']] += record.get('elapsed_s', 0)
    for record, note in zip(failed, notes):
        elapsed[record['id']] += note['backoff_s']
    from qwenlab.financial_actions_metrics import percentile
    values = list(elapsed.values())
    result = dict(status='complete', successful_requests=len(successful),
        failed_attempts=len(failed), total_attempts=len(successful) + len(failed),
        automatic_retries_authorized_by_user=len(failed),
        input_tokens_success=sum(r['body']['usage']['input_tokens'] for r in successful),
        failed_usage_and_cost='unknown',
        retry_inclusive_latency=dict(p50_s=percentile(values, .5), p95_s=percentile(values, .95),
             per_sample_s=dict(elapsed),
             scope='sum successful and failed HTTP durations plus scheduled retry backoff; excludes manual authorization downtime, process startup and backend'),
        authorization=io.read(AUTH),
        failed_attempts_summary=[dict(id=r['id'], task=r['task'], error=r.get('error'),
             http_status=r.get('http_status'), elapsed_s=r.get('elapsed_s'),
             request_sha256=r['request_sha256']) for r in failed])
    io.write(current.PUBLIC / 'retry-accounting.json', result)
    io.write(current.PUBLIC / 'retry-authorization.json', io.read(AUTH))
    return result


def run():
    with io.exclusive_lock('financial-jev-current-proxy-recovery-v1.lock'):
        rows, _ = current.freeze()
        auth = authorization()
        while True:
            with io.exclusive_lock('financial-jev-current-proxy-v1.lock'):
                failure = pending_failure(rows)
                if failure: archive_for_retry(*failure, auth)
            try:
                current.run()
                break
            except RuntimeError:
                if pending_failure(rows) is None: raise
                # Next iteration archives this exact failure before any resend.
        result = accounting()
        print(f'Complete: {result["total_attempts"]} attempts, '
              f'{result["failed_attempts"]} authorized retries.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'accounting'))
    args = parser.parse_args()
    if args.command == 'run': run()
    else: accounting()
