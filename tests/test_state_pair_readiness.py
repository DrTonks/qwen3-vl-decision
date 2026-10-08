from copy import deepcopy
import importlib.util
import unittest
from qwenlab.common import ROOT
from qwenlab.financial_state_pair_candidates import DATA, read

spec=importlib.util.spec_from_file_location('finalize_pairs',ROOT/'scripts/finalize-state-pair-candidates.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.rows=read(DATA/'build/candidates.json')
        self.review=read(DATA/'checks/semantic-review.json')
        self.screen=read(DATA/'checks/blind-overlap.json')

    def run_check(self):
        return module.review_rows(self.rows,self.review,self.screen)

    def test_remains_training_disabled(self):
        accepted,blocked=self.run_check()
        self.assertEqual((len(accepted),len(blocked)),(136,0))
        self.assertTrue(all(r['training_eligible'] is False and r['human_reviewed'] is False and r['split']=='candidate' for r in accepted))

    def test_lexical_hit_quarantines_whole_story(self):
        self.screen['quarantine_groups']=['FIN-SP1-D01']
        accepted,blocked=self.run_check()
        self.assertEqual((len(accepted),len(blocked)),(132,4))
        self.assertEqual({r['scene_family_id'] for r in blocked},{'FIN-SP1-D01'})

    def test_one_bad_variant_blocks_whole_story(self):
        self.review['reviews'][0]['variants'][0]['verdict']='quarantine'
        accepted,blocked=self.run_check()
        self.assertEqual((len(accepted),len(blocked)),(133,3))

    def test_missing_or_duplicate_review_fails(self):
        self.review['reviews'].pop()
        with self.assertRaises(ValueError):self.run_check()

    def test_mismatched_label_fails(self):
        self.review['reviews'][0]['variants'][0]['action']='refuse'
        with self.assertRaisesRegex(ValueError,'disagree'):self.run_check()

    def test_human_provenance_cannot_be_promoted(self):
        self.review['reviews'][0]['variants'][0]['human_reviewed']=True
        with self.assertRaisesRegex(ValueError,'provenance'):self.run_check()

    def test_reference_path_escape_fails(self):
        with self.assertRaises(ValueError):module.resolve_review_reference('qwen/../dbroot.txt')

    def test_swapped_group_members_cannot_quarantine_wrong_story(self):
        first,second=self.review['reviews'][:2]
        first['variants'][0],second['variants'][0]=second['variants'][0],first['variants'][0]
        second['variants'][0]['verdict']='quarantine'
        with self.assertRaisesRegex(ValueError,'wrong story group'):self.run_check()


if __name__=='__main__':unittest.main()
