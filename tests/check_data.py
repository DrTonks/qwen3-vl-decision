import json
import unittest
from collections import defaultdict
from qwenlab.common import ROOT,load_rows,specification,input_state

class DataContract(unittest.TestCase):
    def test_no_group_leak_and_no_label_leak(self):
        seen={}; texts={}; count=0
        spec=specification('business')
        for split in ('dev','calibration','test'):
            rows,_=load_rows('business',split)
            for r in rows:
                count+=1
                self.assertEqual(seen.setdefault(r['group'],split),split)
                signature=json.dumps(input_state(r),sort_keys=True,ensure_ascii=False)
                self.assertEqual(texts.setdefault(signature,split),split)
                self.assertNotIn('labels',input_state(r))
                for task,answer in r['labels'].items(): self.assertIn(answer,spec['questions'][task]['criteria'])
                self.assertEqual(r['labels']['needs_human']=='yes',r['labels']['route']=='human')
                if r['labels']['route']=='tool':
                    self.assertIn(r['labels']['tool'],r['available_tools'])
                    self.assertTrue(r['state']['authenticated'])
                    if r['labels']['tool']=='queryApplicationDetail': self.assertIsNotNone(r['state'].get('application_id'))
                else: self.assertEqual(r['labels']['tool'],'none')
        self.assertEqual(count,192)

    def test_public_candidates(self):
        if not (ROOT/'data/massive_zh_test.jsonl').exists(): self.skipTest('Public download still in progress')
        rows,_=load_rows('massive'); spec=specification('massive')
        self.assertEqual(len({r['id'] for r in rows}),len(rows))
        for r in rows: self.assertIn(r['labels']['intent'],spec['questions']['intent']['criteria'])

if __name__=='__main__': unittest.main()
