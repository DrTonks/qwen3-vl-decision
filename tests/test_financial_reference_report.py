import unittest
from qwenlab.financial_reference_report import probability_metrics


class ProbabilityAuditTests(unittest.TestCase):
    def test_perfect_and_confidently_wrong_probabilities(self):
        rows=[{'id':'one','annotation':{'action':'answer'}}]
        p={'id':'one','action':'answer','action_prediction':{'probabilities':{'answer':1.,'human':0.}}}
        m=probability_metrics(rows,[p])
        self.assertEqual((m['nll'],m['ece10'],m['brier_sum_over_classes']),(0.,0.,0.))
        p['action']='human';p['action_prediction']['probabilities']={'answer':0.,'human':1.}
        m=probability_metrics(rows,[p])
        self.assertEqual(m['errors_confidence_ge_09'],1)
        self.assertEqual(m['ece10'],1)
        self.assertEqual(m['brier_sum_over_classes'],2)
        self.assertGreater(m['nll'],20)


if __name__=='__main__':unittest.main()
