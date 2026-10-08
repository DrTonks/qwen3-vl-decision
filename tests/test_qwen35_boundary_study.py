"""CPU checks for matched budgets, resume ordering and whole-study holdout guards."""
from collections import Counter
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from qwenlab import qwen35_boundary_study as study


class BoundaryStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=study.ROOT/'.local/boundary-test-temp'
        cls.tmp.mkdir(parents=True,exist_ok=True)

    def test_exact_equal_budget_and_complete_overlay_coverage(self):
        replay=study.schedule(11899,12235,20261002)
        overlay=study.schedule(12235,12235,20261002)
        self.assertEqual(len(replay),len(overlay))
        self.assertEqual(set(replay),set(range(11899)))
        self.assertEqual(set(Counter(overlay).values()),{1})
        self.assertEqual(sum(v==2 for v in Counter(replay).values()),336)
        self.assertEqual(len(overlay[-3:]),3)
        batches=[overlay[i:i+8] for i in range(0,len(overlay),8)]
        self.assertEqual(len(batches),1530)
        self.assertEqual(len(batches[-1]),3)
        for saved in [0,1,383,384,768,1529,1530]:
            resumed=[overlay[(step-1)*8:step*8] for step in range(saved+1,1531)]
            self.assertEqual(resumed,batches[saved:])

    def test_invalid_budget_does_not_drop_old_data(self):
        with self.assertRaises(ValueError): study.schedule(100,99,1)
        with self.assertRaises(ValueError): study.schedule(0,10,1)

    def test_arm_control_is_shared_and_status_propagates(self):
        root=study.Study()
        for name in study.ARMS:
            arm=study.Arm(root,name)
            self.assertEqual(arm.control,root.control)
            with patch.object(study.cycle.Run,'status') as status:
                arm.status('paused',step=1)
                self.assertEqual(status.call_count,2)
                self.assertEqual(status.call_args.kwargs['arm'],name)

    def test_failed_global_selection_never_reads_holdout(self):
        with patch.object(study.cycle,'holdout') as holdout:
            with self.assertRaises(ValueError): study.run_holdout(study.Study(),dict(passed=False))
            holdout.assert_not_called()

    def test_incomplete_second_arm_blocks_selection_before_evaluation(self):
        root=study.Study()
        def read(path):
            if 'replay' in str(path): return dict(protocol_sha256='checked',steps=1530)
            raise FileNotFoundError('second arm not finished')
        with patch.object(study.ft,'read',side_effect=read), patch.object(study.Arm,'protocol_hash',return_value='checked'), patch.object(study.ft.data,'evaluation_rows') as evaluation:
            with self.assertRaises(FileNotFoundError): study.select(root,dict(config=dict(initial_run=study.cycle.DEFAULT,max_steps=1530)))
            evaluation.assert_not_called()

    def test_code_review_missing_or_changed_hash_is_rejected(self):
        with patch.object(study.ft,'read',return_value={'status':'pass','files':{}}):
            with self.assertRaises(ValueError): study.validate_code_review()
        review=dict(status='pass',files={name:'old' for name in study.REVIEW_FILES})
        with patch.object(study.ft,'read',return_value=review),patch.object(study,'sha',return_value='changed'):
            with self.assertRaises(ValueError): study.validate_code_review()

    def test_immutable_artifact_rejects_changed_contents(self):
        with tempfile.TemporaryDirectory(dir=self.tmp) as temp:
            path=Path(temp)/'selection.json'
            study.immutable_json(path,{'winner':'replay'})
            study.immutable_json(path,{'winner':'replay'})
            with self.assertRaises(ValueError): study.immutable_json(path,{'winner':'overlay'})

    def test_pause_request_between_arms_stops_entire_worker(self):
        root=study.Study()
        with tempfile.TemporaryDirectory(dir=self.tmp) as temp:
            root.out=Path(temp)/'results'; root.control=Path(temp)/'control.json'
            study.ft.durable_json(root.out/'protocol.json',{})
            study.ft.durable_json(root.control,dict(state='pause_requested'))
            with self.assertRaises(study.ft.Paused): study.cycle.pause_check(root,'between_arms')
            self.assertEqual(study.ft.read(root.out/'status.json')['stage'],'paused')
            self.assertEqual(study.ft.read(root.control)['state'],'paused')


if __name__=='__main__': unittest.main()
