import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from qwenlab import financial_jev_session_recovery_v2 as recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.auth = dict(retryable_http=[408, 429, 500, 502, 503, 504],
                         retryable_transport=['URLError', 'TimeoutError'])

    def test_only_transient_or_uncertain_failures_retry(self):
        for error, status in [('URLError', None), ('HTTPError', 429), ('HTTPError', 503)]:
            self.assertTrue(recovery.retryable(dict(state='failed_or_uncertain', error=error,
                                                    http_status=status), self.auth))
        for status in (400, 401, 402, 403, 451):
            self.assertFalse(recovery.retryable(dict(state='failed_or_uncertain', error='HTTPError',
                                                     http_status=status), self.auth))
        self.assertTrue(recovery.retryable(dict(state='pending'), self.auth))

    def test_successful_requests_are_never_retryable(self):
        self.assertFalse(recovery.retryable(dict(state='returned', error='URLError'), self.auth))

    def test_per_request_limit_checked_before_mutation(self):
        record = dict(state='failed_or_uncertain', error='URLError', request_sha256='same')
        with patch.object(recovery, 'archives', return_value=[Path('a')] * recovery.PER_REQUEST), \
                patch.object(recovery.io, 'read', return_value=record):
            with self.assertRaisesRegex(RuntimeError, 'limit'):
                recovery.archive_for_retry(Path('unused'), record, self.auth)

    def test_global_limit_checked_before_mutation(self):
        record = dict(state='failed_or_uncertain', error='URLError', request_sha256='same')
        with patch.object(recovery, 'archives', return_value=[Path('a')] * recovery.MAX_EXTRA), \
                patch.object(recovery.io, 'read', return_value={'request_sha256': 'other'}):
            with self.assertRaisesRegex(RuntimeError, 'limit'):
                recovery.archive_for_retry(Path('unused'), record, self.auth)


if __name__ == '__main__':
    unittest.main()
