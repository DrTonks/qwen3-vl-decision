import unittest
from qwenlab.integrated_report import accuracy_all, business_counts, aligned_latency, paired_speed


class IntegratedReportTests(unittest.TestCase):
    def test_failed_requests_stay_in_denominator_and_risk_counts(self):
        rows = [{'id': 'a', 'error': 'unavailable', 'labels': {'route': 'human'}},
                {'id': 'b', 'error': 'unavailable', 'labels': {'route': 'tool'}},
                {'id': 'c', 'labels': {'route': 'tool', 'tool': 'lookup', 'intent': 'record'},
                 'predictions': {k: {'choice': v} for k, v in {'route': 'tool', 'tool': 'lookup', 'intent': 'record'}.items()}}]
        self.assertAlmostEqual(accuracy_all(rows, 'route'), 1/3)
        counts = business_counts(rows)
        self.assertEqual((counts['human_missed'], counts['human_required']), (1, 1))
        self.assertEqual((counts['joint_tool_correct'], counts['tool_required']), (1, 2))
        self.assertEqual(counts['all_fields_correct'], 1)

    def test_latency_matches_ids_not_file_order_and_reports_errors(self):
        rows = [{'id': 'a', 'elapsed_s': 1}, {'id': 'b', 'elapsed_s': 100},
                {'id': 'c', 'error': 'timeout'}]
        result = aligned_latency(rows, ['c', 'a'])
        self.assertEqual(result['p50_s'], 1)
        self.assertEqual(result['errors'], 1)
        with self.assertRaises(ValueError):
            aligned_latency(rows, ['missing'])

    def test_speed_pairs_group_repeats_and_reject_missing_mate(self):
        rows = [{'id': 'a', 'repeat': i, 'mode': mode, 'elapsed_s': t}
                for i in range(3) for mode, t in [('full', 2), ('candidate', 1)]]
        result = paired_speed(rows)
        self.assertEqual(result['request_groups'], 1)
        self.assertEqual(result['mean_saved_s'], 1)
        self.assertEqual(result['group_bootstrap_95_s'], [1, 1])
        with self.assertRaises(ValueError):
            paired_speed(rows[:-1])


if __name__ == '__main__':
    unittest.main()
