import unittest
from qwenlab.post_training import state_pairs, slices


class PostTrainingTests(unittest.TestCase):
    def test_state_pairs_require_both_routes_correct(self):
        rows = [{'group': 'a', 'labels': {'route': gold}, 'predictions': {'route': {'choice': pred}}}
                for gold, pred in [('tool', 'tool'), ('clarify', 'clarify'), ('human', 'tool')]]
        result = state_pairs(rows)
        self.assertEqual(result['pairs'], 3)
        self.assertEqual(result['both_routes_correct'], 1)
        self.assertIsNone(state_pairs([])['accuracy'])

    def test_join_refuses_partial_or_duplicate_predictions(self):
        raw = [{'id': 'a'}, {'id': 'b'}]
        with self.assertRaises(ValueError):
            slices(raw, [{'id': 'a'}], 'condition')
        with self.assertRaises(ValueError):
            slices(raw, [{'id': 'a'}, {'id': 'a'}], 'condition')


if __name__ == '__main__':
    unittest.main()
