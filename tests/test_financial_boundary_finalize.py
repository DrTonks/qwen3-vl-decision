"""Read-only integration checks for the study/arm evaluation binding regression."""
import copy
import unittest
from unittest.mock import patch
from qwenlab import financial_boundary_finalize as final


class FinalizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = final.s.Study()
        cls.arm = final.s.Arm(cls.study, 'replay')
        needed = [cls.study.out/'protocol.json', cls.arm.out/'protocol.json',
            final.ROOT/'results/financial-qwen35-v1/development/base/predictions.jsonl',
            cls.arm.out/'development/step-384/predictions.jsonl']
        if any(not p.exists() for p in needed):
            raise unittest.SkipTest('Requires archived local experiment artifacts; not distributed in fresh clones')
        cls.protocol = final.ft.read(cls.study.out/'protocol.json')
        cls.arm_protocol = final.ft.read(cls.arm.out/'protocol.json')
        cls.rows = final.ft.data.evaluation_rows('development')
        cls.raw = final.ft.rows_file(final.ROOT/'results/financial-qwen35-v1/development/base/predictions.jsonl')
        cls.pred = final.ft.rows_file(cls.arm.out/'development/step-384/predictions.jsonl')

    def test_original_mixed_protocol_error_is_reproduced(self):
        base = final.ft.metrics.evaluate(self.rows, self.raw, self.protocol['prompt_sha256'], self.study.protocol_hash())
        candidate = final.ft.metrics.evaluate(self.rows, self.pred, self.protocol['prompt_sha256'], self.arm.protocol_hash())
        with self.assertRaisesRegex(ValueError, 'same frozen prompt and protocol'):
            final.ft.metrics.development_gate(base, candidate, self.protocol['config']['development_gate'])

    def test_verified_context_uses_same_predictions_and_unchanged_gate(self):
        original = copy.deepcopy((self.raw, self.pred))
        gate = final.compare_in_arm_context(self.protocol, self.arm_protocol, 'replay',
            self.study.protocol_hash(), self.arm.protocol_hash(), self.rows, self.raw, self.pred)
        self.assertEqual(gate['failures'], ['human_recall'])
        self.assertFalse(gate['passed'])
        self.assertEqual((self.raw, self.pred), original)

    def test_changed_arm_policy_rejected_before_metric_rebinding(self):
        arm = copy.deepcopy(self.arm_protocol)
        arm['config']['development_gate']['minimum_human_recall'] = 0
        with patch.object(final.ft.metrics, 'evaluate') as evaluate:
            with self.assertRaises(ValueError):
                final.compare_in_arm_context(self.protocol, arm, 'replay', self.study.protocol_hash(),
                    self.arm.protocol_hash(), self.rows, self.raw, self.pred)
            evaluate.assert_not_called()

    def test_any_passing_candidate_stops_offline_failure_finalizer(self):
        final.require_no_passing({'a': {'passed': False}})
        with self.assertRaises(RuntimeError):
            final.require_no_passing({'a': {'passed': True}})


if __name__ == '__main__':
    unittest.main()
