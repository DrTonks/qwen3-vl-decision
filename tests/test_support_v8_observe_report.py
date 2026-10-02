import unittest
from qwenlab.support_v8_observe_report import paired, route_classes


def row(i,gold,pred,group='group'):
    return {'id':str(i),'group':group,'labels':{'route':gold},'predictions':{'route':{'choice':pred}}}


class ReportTests(unittest.TestCase):
    def test_paired_counts_and_perfect_improvement_interval(self):
        old=[row(1,'human','tool'),row(2,'tool','human')]
        new=[row(1,'human','human'),row(2,'tool','tool')]
        result=paired(old,new,repeats=100)
        self.assertEqual(result['fixed'],2)
        self.assertEqual(result['accuracy_delta'],1)
        self.assertEqual(result['group_bootstrap_95_descriptive'],[1,1])

    def test_mixed_changes_and_identity_guard(self):
        old=[row(1,'human','human'),row(2,'tool','human')]
        new=[row(1,'human','tool'),row(2,'tool','tool')]
        result=paired(old,new,repeats=100)
        self.assertEqual(result['regressed'],1)
        self.assertEqual(result['fixed'],1)
        with self.assertRaises(ValueError): paired(old,list(reversed(new)),repeats=1)
        changed=[dict(r,group='changed') for r in new]
        with self.assertRaises(ValueError): paired(old,changed,repeats=1)

    def test_class_recall_and_precision(self):
        result=route_classes([row(1,'human','human'),row(2,'tool','human')])
        self.assertEqual(result['human']['recall'],1)
        self.assertEqual(result['human']['precision'],.5)
        self.assertEqual(result['tool']['recall'],0)


if __name__=='__main__': unittest.main()
