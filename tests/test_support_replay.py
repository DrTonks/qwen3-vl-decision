import copy
import unittest
from qwenlab.support_replay import filter_replay, stratified_replay
from qwenlab.support_expansion import fingerprint


def row(i, condition='live', route='tool'):
    return {'id':str(i),'group':'g'+str(i),'split':'train','dataset':'business',
        'message':'训练问题'+str(i),'condition':condition,'state':{'authenticated':True},
        'labels':{'intent':'products','route':route,'tool':'queryLoanProducts' if route=='tool' else 'none'}}


class SupportReplayTests(unittest.TestCase):
    def test_sampling_covers_all_conditions_and_routes_without_replacement(self):
        rows=[row(i,'condition'+str(i%4),['tool','human','clarify','llm'][i%4]) for i in range(80)]
        picked=stratified_replay(rows,20,2026)
        self.assertEqual(picked,stratified_replay(rows,20,2026))
        self.assertEqual(len({r['id'] for r in picked}),20)
        self.assertEqual(len({r['condition'] for r in picked}),4)
        self.assertEqual(len({r['labels']['route'] for r in picked}),4)

    def test_all_heldout_checks_and_reviewed_duplicate_filter(self):
        rows=[row(i) for i in range(5)]
        held=copy.deepcopy(rows[0]); held['message']='不同问题但同组'
        picked,rejected=filter_replay(rows,[held],{fingerprint(rows[1]['message'])},[rows[2]])
        self.assertEqual([r['id'] for r in picked],['3','4'])
        self.assertEqual(rejected,{'heldout_overlap':2,'reviewed_train_duplicate':1})

    def test_dev_row_cannot_be_inserted_into_replay(self):
        bad=row(1); bad['split']='dev'
        with self.assertRaisesRegex(ValueError,'Only original training'):
            filter_replay([bad],[],set(),[])

    def test_conflicting_duplicate_supervision_fails(self):
        a=row(1); b=copy.deepcopy(a); b['id']='different'; b['labels']['route']='llm'; b['labels']['tool']='none'
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            filter_replay([a,b],[],set(),[])

    def test_anchor_is_zero_at_initial_weights_and_penalizes_drift(self):
        import torch
        from qwenlab.support_train_v7 import anchor_penalty
        a=torch.tensor([1.,2.]); p=a.clone().requires_grad_()
        zero=anchor_penalty([p],[a],.5)
        self.assertEqual(zero.item(),0.)
        with torch.no_grad(): p.add_(.1)
        loss=anchor_penalty([p],[a],.5)
        self.assertGreater(loss.item(),0.)
        loss.backward()
        self.assertTrue(torch.isfinite(p.grad).all())
        self.assertTrue((p.grad>0).all())
        self.assertIsNone(a.grad)


if __name__=='__main__':
    unittest.main()
