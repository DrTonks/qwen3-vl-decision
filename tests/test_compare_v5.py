import unittest
from qwenlab.compare_v5 import accuracy


class ComparisonTests(unittest.TestCase):
    def test_failed_request_counts_as_incorrect_even_with_partial_answer(self):
        good = {'labels': {'route': 'tool'}, 'predictions': {'route': {'choice': 'tool'}}}
        error = {**good, 'error': 'HTTPError'}
        self.assertEqual(accuracy([good, error], 'route'), .5)

    def test_missing_prediction_counts_as_incorrect(self):
        self.assertEqual(accuracy([{'labels': {'intent': 'general'}, 'predictions': {}}], 'intent'), 0)


if __name__ == '__main__': unittest.main()
