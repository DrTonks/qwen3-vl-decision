import copy
import unittest
from qwenlab.support_v8_observe_eval import validate_rows, latency
from qwenlab.support_v8_observe_eval import verify_cached_file, ROOT
from unittest.mock import patch


class EvalTests(unittest.TestCase):
    def test_reuse_rejects_changed_labels_ids_or_incomplete_population(self):
        source=[{'id':'a','labels':{'route':'human'}},{'id':'b','labels':{'route':'tool'}}]
        validate_rows(copy.deepcopy(source),source,complete=True)
        for rows in [source[:1],list(reversed(source)),[{'id':'a','labels':{'route':'llm'}},source[1]]]:
            with self.assertRaises(ValueError): validate_rows(rows,source,complete=True)

    def test_prefix_resume_and_errors(self):
        source=[{'id':'a','labels':{}}]
        validate_rows([],source)
        with self.assertRaises(ValueError): validate_rows([dict(source[0],error='failed')],source)

    def test_latency_seconds_and_count(self):
        m=latency([{'elapsed_s':.5},{'elapsed_s':.7},{'elapsed_s':.9}])
        self.assertEqual(m['requests'],3)
        self.assertAlmostEqual(m['mean_s'],.7)
        self.assertAlmostEqual(m['p50_s'],.7)

    def test_pre_continuation_snapshot_rejects_modified_or_unrecorded_cache(self):
        p=ROOT/'results/example.jsonl'
        with patch('qwenlab.support_v8_observe_eval.sha',return_value='actual'):
            verify_cached_file(p,{str(p.relative_to(ROOT)):'actual'})
            with self.assertRaises(ValueError): verify_cached_file(p,{})
            with self.assertRaises(ValueError): verify_cached_file(p,{str(p.relative_to(ROOT)):'old'})


if __name__=='__main__': unittest.main()
