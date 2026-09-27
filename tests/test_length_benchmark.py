import unittest
from qwenlab.length_benchmark import add_background, stats


class LengthBenchmarkTests(unittest.TestCase):
    def test_padding_preserves_current_business_and_original_row(self):
        row = {'message': '查我的申请', 'state': {'authenticated': True}, 'history': [{'role': 'user', 'content': '申请编号是1'}], 'labels': {'route': 'tool'}}
        padded = add_background(row, ['一本书有封面。'])
        for key in ('message', 'state', 'labels'): self.assertEqual(padded[key], row[key])
        self.assertEqual(padded['history'][1:], row['history'])
        self.assertEqual(len(row['history']), 1)
        self.assertEqual(add_background(row, []), row)

    def test_failures_count_for_accuracy_but_not_success_latency(self):
        labels = {'intent': 'credit', 'route': 'tool', 'tool': 'queryMyCreditScore'}
        rows = [{'labels': labels, 'predictions': labels, 'elapsed_s': .4},
                {'labels': labels, 'predictions': {}, 'elapsed_s': 30, 'error': 'TimeoutError'}]
        result = stats(rows)
        self.assertEqual(result['accuracy_all_requests']['route'], .5)
        self.assertEqual(result['p50_s'], .4)
        self.assertEqual(result['errors'], 1)


if __name__ == '__main__': unittest.main()
