import math
import unittest
from qwenlab.summarize import metric,paired_ci
from qwenlab.calibrate import probabilities
from qwenlab.apply_route_gate import gate

class Metrics(unittest.TestCase):
    def row(self,i,y,p):return {'id':str(i),'group':str(i),'labels':{'intent':y},'predictions':{'intent':{'choice':max(p,key=p.get),'probabilities':p}}}
    def test_known_probabilities(self):
        rows=[self.row(0,'a',{'a':.8,'b':.2}),self.row(1,'b',{'a':.6,'b':.4})]
        m=metric(rows,'intent')
        self.assertAlmostEqual(m['accuracy'],.5)
        self.assertAlmostEqual(m['brier_multiclass_sum'],.4)
        self.assertAlmostEqual(m['nll'],(-math.log(.8)-math.log(.4))/2)
        self.assertAlmostEqual(m['ece_10_equal_width'],.4)
        self.assertEqual(paired_ci(rows,rows,'intent')['group_bootstrap_95'],[0,0])
    def test_temperature_preserves_choice(self):
        for t in (.1,1,10):
            p=probabilities([1,5,2],t)
            self.assertEqual(max(range(3),key=p.__getitem__),1)
            self.assertAlmostEqual(sum(p),1)
    def test_route_gate_is_independent_and_non_mutating(self):
        pred={'route':{'choice':'human'},'tool':{'choice':'queryMyApplications'}}
        self.assertEqual(gate(pred)['tool']['choice'],'none')
        self.assertEqual(pred['tool']['choice'],'queryMyApplications')
        pred['route']['choice']='tool'
        self.assertEqual(gate(pred)['tool']['choice'],'queryMyApplications')
if __name__=='__main__':unittest.main()
