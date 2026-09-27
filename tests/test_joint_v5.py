import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from qwenlab.common import input_state, ROOT
from qwenlab.curriculum_v5 import action_label, business, variants, DATA
from qwenlab.joint_data import business_rows
from qwenlab.joint_v5 import epoch_blocks, lr_scale, rng_state, restore_rng, read_resumable_rows, encode
from qwenlab.prepare_v2 import read_rows, normalize


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows = business()

    def test_group_isolation_and_input_dedup(self):
        groups = {}; inputs = {}
        for row in self.rows:
            self.assertEqual(groups.setdefault(row['group'], row['split']), row['split'])
            digest = json.dumps(input_state(row), ensure_ascii=False, sort_keys=True)
            self.assertEqual(inputs.setdefault(digest, row['split']), row['split'])
            self.assertEqual(action_label(row['labels']['route'], row['labels']['tool']), row['labels']['action'])

    def test_no_v4_heldout_wording_in_train(self):
        heldout = {normalize(r['message']) for r in business_rows() if r['split'] != 'train'}
        for row in self.rows:
            if row['split'] == 'train':
                for text in [row['message']] + [h['content'] for h in row.get('history', []) if h['role'] == 'user']:
                    self.assertNotIn(normalize(text), heldout)

    def test_success_empty_not_timeout(self):
        cases = {x[0]: x for x in variants('applications')}
        self.assertEqual(cases['empty_success'][3:], ('llm', 'none'))
        self.assertEqual(cases['timeout_once'][3:], ('tool', 'queryMyApplications'))
        self.assertEqual(cases['timeout_twice'][3:], ('human', 'none'))
        self.assertEqual(cases['partial'][3:], ('tool', 'queryMyApplications'))
        self.assertEqual(cases['complete'][3:], ('llm', 'none'))
        self.assertEqual(cases['stale'][3:], ('tool', 'queryMyApplications'))

    def test_public_dialogue_and_split_isolation(self):
        groups = {}; train_texts = set(); heldout_texts = set()
        for split in ('train', 'dev', 'calibration', 'test'):
            for r in read_rows(DATA / f'crosswoz-{split}.jsonl'):
                self.assertEqual(groups.setdefault(r['group'], split), split)
                self.assertNotIn('dialog_act', input_state(r)); self.assertNotIn('goal', input_state(r))
                (train_texts if split == 'train' else heldout_texts).add(normalize(r['message']))
        self.assertFalse(train_texts & heldout_texts)

    def test_metadata_not_in_prompt(self):
        class Tokenizer:
            def encode(self, text, **kwargs): return [ord(text)]
            def apply_chat_template(self, messages, **kwargs):
                self.rendered = json.dumps(messages, ensure_ascii=False); return self.rendered
            def __call__(self, text, **kwargs): return {'input_ids': [1, 2], 'attention_mask': [1, 1]}
        tok = Tokenizer(); row = copy.deepcopy(self.rows[0])
        row['condition'] = 'SECRET_CONDITION'; row['group'] = 'SECRET_GROUP'; row['source'] = 'SECRET_SOURCE'
        encode(tok, row, 'route')
        for marker in ('SECRET_CONDITION', 'SECRET_GROUP', 'SECRET_SOURCE', 'label_status', 'labels'):
            self.assertNotIn(marker, tok.rendered)


class ResumeTests(unittest.TestCase):
    def test_coverage_deterministic_plan_and_lr(self):
        pools = {'a': list(range(9)), 'b': list(range(6))}; cfg = {'seed': 17, 'micro_batch': 2}
        blocks = epoch_blocks(pools, cfg, 0)
        self.assertEqual(blocks, epoch_blocks(pools, cfg, 0))
        self.assertNotEqual(blocks, epoch_blocks(pools, cfg, 1))
        for name, values in pools.items():
            self.assertEqual(sorted(i for k, ids in blocks if k == name for i in ids), list(range(len(values))))
        self.assertGreater(lr_scale(1, 100, .05), 0)
        self.assertEqual(lr_scale(5, 100, .05), 1)
        self.assertGreater(lr_scale(100, 100, .05), 0)

    def test_optimizer_and_rng_resume_matches_uninterrupted(self):
        import numpy as np
        import torch
        torch.manual_seed(42); random.seed(42); np.random.seed(42)
        model = torch.nn.Sequential(torch.nn.Linear(4, 4), torch.nn.Dropout(.3), torch.nn.Linear(4, 2))
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
        def step(m, opt):
            x = torch.randn(3, 4) * (random.random() + np.random.random())
            opt.zero_grad(); m(x).square().mean().backward(); opt.step()
        step(model, optimizer)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.pt'
            torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'rng': rng_state()}, path)
            step(model, optimizer); expected = copy.deepcopy(model.state_dict())
            resumed = torch.nn.Sequential(torch.nn.Linear(4, 4), torch.nn.Dropout(.3), torch.nn.Linear(4, 2))
            resumed_optimizer = torch.optim.AdamW(resumed.parameters(), lr=.001)
            state = torch.load(path, weights_only=False, map_location='cpu')
            resumed.load_state_dict(state['model']); resumed_optimizer.load_state_dict(state['optimizer']); restore_rng(state['rng'])
            step(resumed, resumed_optimizer)
            for k, value in resumed.state_dict().items(): self.assertTrue(torch.equal(value, expected[k]), k)

    def test_only_truncated_last_append_can_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.jsonl'
            path.write_text('{"id":1}\n{"id":', encoding='utf-8')
            self.assertEqual(read_resumable_rows(path), [{'id': 1}])
            self.assertTrue(path.read_text().endswith('\n'))
            path.write_text('{bad}\n{"id":2}\n', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError): read_resumable_rows(path)


if __name__ == '__main__': unittest.main()
