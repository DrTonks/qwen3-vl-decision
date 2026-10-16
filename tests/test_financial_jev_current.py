import copy
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from qwenlab import financial_jev_current as current
from qwenlab import financial_prompt_v2 as prompt


class CurrentReferenceTests(unittest.TestCase):
    def test_inputs_and_choices_match_current_qwen_contract(self):
        import json
        for row in current.source_rows():
            for task in ('action', 'tool'):
                payload = current.payload(row, task)
                messages, keys = prompt.messages(row, task)
                self.assertEqual(json.loads(messages[1]['content'].split('\n')[0]), payload['state']['input'])
                self.assertEqual(set(keys), set(payload['questions'][task]['criteria']))
                self.assertEqual(payload['state']['policy'], prompt.SPEC['policy'])

    def test_labels_never_enter_request(self):
        row = current.source_rows()[0]
        other = copy.deepcopy(row); other['annotation'] = {'action': 'arbitrary secret gold'}
        self.assertEqual(current.payload(row, 'action'), current.payload(other, 'action'))
        self.assertEqual(current.payload(row, 'tool'), current.payload(other, 'tool'))

    def test_model_drift_and_invalid_answer_rejected(self):
        keys = current.SPEC['actions']
        body = dict(model='jev-test', answers=dict(action=dict(choice=keys[0], probabilities={k: int(k == keys[0]) for k in keys})))
        self.assertEqual(current.normalized_answer(body, 'action', 'jev-test')['choice'], keys[0])
        with self.assertRaises(ValueError): current.normalized_answer(body, 'action', 'jev-other')
        body['answers']['action']['choice'] = keys[1]
        with self.assertRaises(ValueError): current.normalized_answer(body, 'action', 'jev-test')

    def test_pending_failed_or_changed_requests_cannot_retry(self):
        folder = current.ROOT / 'tmp' / ('jev-cache-test-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        path = folder / 'request.json'
        try:
            for state in ('pending', 'failed_or_uncertain'):
                current.io.write(path, dict(state=state, request_sha256='bound'))
                with self.assertRaises(RuntimeError): current.io.use_cached(path, 'bound')
            with self.assertRaises(ValueError): current.io.use_cached(path, 'changed')
        finally:
            path.unlink(); folder.rmdir()

    def test_no_non_development_population(self):
        rows = current.source_rows()
        rows[0]['split'] = 'final'
        with patch.object(current.io, 'read', return_value=rows):
            with self.assertRaises(ValueError): current.source_rows()


if __name__ == '__main__':
    unittest.main()
