"""Partition safety, coverage/resume semantics and confidence policy checks."""
import math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from qwenlab import qwen35_cycle as cycle


class Qwen35Tests(unittest.TestCase):
    def test_two_epochs_cover_every_row_exactly_twice_including_tail(self):
        n=11899;batch=8;steps=math.ceil(n/batch)
        all_batches=[]
        for epoch in range(2):
            order=cycle.epoch_order(n,20261002,epoch)
            self.assertEqual(set(order),set(range(n)))
            all_batches.extend(order[i:i+batch] for i in range(0,n,batch))
        self.assertEqual(len(all_batches),2976)
        self.assertEqual(len(all_batches[steps-1]),3)
        self.assertEqual(set(Counter(i for b in all_batches for i in b).values()),{2})
        orders=[cycle.epoch_order(n,20261002,e) for e in range(2)]
        for resumed_step in [0,57,200,1487,1488,1489,2975]:
            recovered=[]
            for step in range(resumed_step+1,2977):
                epoch=(step-1)//steps;offset=((step-1)%steps)*batch
                recovered.append(orders[epoch][offset:offset+batch])
            self.assertEqual(recovered,all_batches[resumed_step:])

    def test_tail_microbatch_weight_equals_actual_full_batch_mean(self):
        import torch
        for n in [1,3,8]:
            p=torch.tensor(.7,dtype=torch.float64,requires_grad=True)
            values=torch.arange(1,n+1,dtype=torch.float64)
            expected=((p*values-2)**2).mean();expected.backward();full=p.grad.clone();p.grad=None
            for offset in range(0,n,2):
                block=values[offset:offset+2]
                (((p*block-2)**2).mean()/(n/len(block))).backward()
            self.assertTrue(torch.allclose(p.grad,full,atol=1e-12))

    def test_holdout_requires_selected_candidate_before_access(self):
        with tempfile.TemporaryDirectory() as temp:
            run=cycle.Run();run.out=Path(temp)
            cycle.ft.durable_json(run.out/'selection.json',dict(passed=False))
            with patch.object(cycle.ft.data,'evaluation_rows') as read:
                with self.assertRaises(ValueError):cycle.evaluate(run,None,None,'step-200',{},'final')
                read.assert_not_called()

    def test_final_requires_frozen_calibration_before_access(self):
        with tempfile.TemporaryDirectory() as temp:
            run=cycle.Run();run.out=Path(temp)
            cycle.ft.durable_json(run.out/'protocol.json',{})
            cycle.ft.durable_json(run.out/'selection.json',dict(passed=True,selected='step-200',protocol_sha256=run.protocol_hash()))
            with patch.object(cycle.ft.data,'evaluation_rows') as read:
                with self.assertRaises(ValueError):cycle.evaluate(run,None,None,'step-200',{},'final')
                with self.assertRaises(ValueError):cycle.evaluate(run,None,None,'step-744',{},'calibration')
                read.assert_not_called()

    def test_temperature_preserves_argmax_and_normalizes_stably(self):
        for t in [.25,.5,1,4]:
            probabilities=cycle.temperature_probs([10000,10001,9990],t)
            self.assertAlmostEqual(sum(probabilities),1)
            self.assertEqual(max(range(3),key=probabilities.__getitem__),1)

    def test_dedicated_paths_reject_traversal_and_old_run(self):
        for name in ['../escape','financial-eight-actions-pilot-v2','financial-qwen35-../../x']:
            with self.assertRaises(ValueError):cycle.Run(name)


if __name__=='__main__':unittest.main()
