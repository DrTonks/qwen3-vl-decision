import copy
import unittest
from qwenlab.support_train import balanced_sample, gate


class SupportTrainingTests(unittest.TestCase):
    def test_replay_selection_is_reproducible_balanced_and_without_replacement(self):
        rows=[{'id':str(i),'labels':{'intent':str(i%3)}} for i in range(60)]
        first=balanced_sample(rows,12,123)
        self.assertEqual(first,balanced_sample(rows,12,123))
        self.assertEqual(len({r['id'] for r in first}),12)
        self.assertEqual([sum(r['labels']['intent']==str(i) for r in first) for i in range(3)],[4,4,4])

    def reference(self):
        metric={'accuracy':.8,'macro_f1_gold_supported_classes':.8,'correct':80}
        data={name:{'tasks':{'intent':copy.deepcopy(metric)}} for name in ('business','legacy','massive','crosswoz')}
        for name in ('business','legacy'):
            data[name]['tasks']['route']=copy.deepcopy(metric)
            data[name]['tasks']['tool']=copy.deepcopy(metric)
            data[name]['human_missed']=0
        config={'gate':{'max_regression':.03,'min_route_f1_gain':.01,'min_route_correct_gain':1,'max_extra_human_misses':0}}
        return data,config

    def test_unchanged_metrics_cannot_trigger_long_training(self):
        ref,cfg=self.reference()
        self.assertFalse(gate(ref,copy.deepcopy(ref),cfg)['continue_training'])

    def test_route_gain_with_regression_or_human_miss_cannot_continue(self):
        ref,cfg=self.reference(); now=copy.deepcopy(ref)
        now['business']['tasks']['route']['correct']=81
        self.assertTrue(gate(ref,now,cfg)['continue_training'])
        now['massive']['tasks']['intent']['accuracy']=.7
        self.assertFalse(gate(ref,now,cfg)['continue_training'])
        now=copy.deepcopy(ref); now['business']['tasks']['route']['correct']=81
        now['legacy']['human_missed']=1
        self.assertFalse(gate(ref,now,cfg)['continue_training'])

    def test_route_macro_f1_gain_can_continue_without_accuracy_gain(self):
        ref,cfg=self.reference(); now=copy.deepcopy(ref)
        now['business']['tasks']['route']['macro_f1_gold_supported_classes']=.82
        self.assertTrue(gate(ref,now,cfg)['continue_training'])


if __name__=='__main__':
    unittest.main()
