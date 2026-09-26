import unittest
from qwenlab.route_v3 import prompt, route_metrics, selection_key


class TokenizerStub:
    def encode(self, value, **kwargs): return [ord(value)]
    def apply_chat_template(self, messages, **kwargs):
        self.messages = messages
        return str(messages)
    def __call__(self, text, **kwargs):
        class Inputs:
            class Shape:
                shape = (1, 100)
            input_ids = Shape()
        return Inputs()


class RouteTests(unittest.TestCase):
    def test_prompt_no_gold_leakage_and_original_format(self):
        tok = TokenizerStub()
        row = {'message': '查询申请', 'state': {}, 'labels': {'route': 'GOLD_SECRET'}, 'group': 'GROUP_SECRET'}
        _, keys, ids = prompt(tok, row)
        content = str(tok.messages)
        self.assertNotIn('GOLD_SECRET', content)
        self.assertNotIn('GROUP_SECRET', content)
        self.assertIn('A: ', content)
        self.assertIn('(tool)', content)
        self.assertIn('"state": {}', content)
        self.assertEqual(len(set(ids)), 4)
        self.assertEqual(set(keys), {'tool', 'clarify', 'human', 'llm'})

    def test_selection_does_not_reward_all_human(self):
        rows = [{'labels': {'route': k}, 'predictions': {'route': {'choice': 'human',
            'probabilities': {'human': .7, 'tool': .1, 'clarify': .1, 'llm': .1}}}} for k in ['human', 'tool', 'clarify', 'llm']]
        result = route_metrics(rows)
        self.assertEqual(result['human_missed'], 0)
        self.assertEqual(result['human_false_positive'], 3)
        self.assertAlmostEqual(result['macro_f1_gold_supported_classes'], .1)
        better = dict(result, macro_f1_gold_supported_classes=.5, human_missed=1)
        self.assertGreater(selection_key(better), selection_key(result))

    def test_image_rejected(self):
        with self.assertRaises(NotImplementedError): prompt(TokenizerStub(), {'images': ['image']})


if __name__ == '__main__': unittest.main()
