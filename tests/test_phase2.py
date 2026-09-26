import copy
import unittest
from qwenlab.common import ROOT, input_state, load_json, sha
from qwenlab.modeling import dataset, specification
from qwenlab.prepare_v2 import normalize
from qwenlab.calibrate_v2 import probabilities, apply
from qwenlab.train import business_split
from qwenlab.publish import publication_files

@unittest.skipUnless((ROOT/'data/processed/v2/manifest.json').exists(),'Run prepare first')
class Phase2(unittest.TestCase):
    def test_frozen_data_and_specs(self):
        folder=ROOT/'data/processed/v2'; manifest=load_json(folder/'manifest.json')
        for name,record in manifest['files'].items(): self.assertEqual(sha(folder/name),record['sha256'])
        for name,digest in manifest['spec_sha256'].items():
            path=ROOT/'configs/decision_spec.json' if name=='business-spec.json' else folder/name
            self.assertEqual(sha(path),digest)
    def test_public_splits_are_disjoint(self):
        sets={split:{normalize(r['message']) for r in dataset('massive',split)} for split in ('train','dev','calibration','test')}
        names=list(sets)
        for i,a in enumerate(names):
            for b in names[i+1:]: self.assertFalse(sets[a]&sets[b],(a,b))
        self.assertEqual(len(dataset('massive','test')),2974)
        self.assertEqual(len(specification('massive')['questions']['intent']['criteria']),60)

    def test_business_training_is_group_disjoint(self):
        train,dev=business_split(); sets=[{r['group'] for r in rows} for rows in (train,dev,dataset('business','calibration'),dataset('business','test'))]
        for i,a in enumerate(sets):
            for b in sets[i+1:]: self.assertFalse(a&b)

    def test_crosswoz_no_annotation_leak(self):
        for row in dataset('crosswoz','test'):
            self.assertEqual(set(input_state(row)),{'message','history'})
            self.assertLessEqual(len(row['history']),6)
            for turn in row['history']: self.assertEqual(set(turn),{'role','content'})

    def test_no_private_files_in_publication(self):
        for path in publication_files():
            self.assertFalse(set(path.relative_to(ROOT).parts)&{'.local','.cache','.venv','models','.planning'})

class Calibration(unittest.TestCase):
    def test_temperature_changes_confidence_not_decision(self):
        row={'labels':{'route':'human'},'predictions':{'route':{'candidate_logits':[1.,3.],
             'ordered_keys':['tool','human'],'choice':'human'}}}
        saved=copy.deepcopy(row); out=apply([row],{'route':{'temperature':2}})
        self.assertEqual(row,saved)
        self.assertEqual(out[0]['predictions']['route']['choice'],'human')
        self.assertAlmostEqual(sum(out[0]['predictions']['route']['probabilities'].values()),1)
        self.assertLess(probabilities([1.,3.],2).max(),probabilities([1.,3.],1).max())

if __name__=='__main__': unittest.main()
