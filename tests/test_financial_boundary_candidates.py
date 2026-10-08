import copy
import unittest
from qwenlab import financial_boundary_candidates as b


def source():
    return dict(id='training-source',split='train',_source_file='data/train.jsonl',_source_group='train-group',
        provenance={'license':'project_authored'},
        input={'message':'核对申请702的信息。','state':{'authenticated':True,'application_id':702},'history':[],
               'images':[],'available_tools':['queryApplicationDetail','queryMyApplications'],
               'capabilities':{'knowledge_collections':[],'handoff_connected':False}},
        annotation={'action':'tool','tool_name':'queryApplicationDetail','tool_arguments':{'applicationId':702}})


class CandidateIsolationTests(unittest.TestCase):
    def test_non_training_sources_cannot_be_relabelled_as_training(self):
        for split in ['development','calibration','final','train_candidate']:
            row=source();row['split']=split
            with self.assertRaisesRegex(ValueError,'training sources'):b.derive(row,'query',0)

    def test_derivation_never_mutates_shared_source_or_other_variants(self):
        row=source();before=copy.deepcopy(row)
        out=[b.derive(row,'query',i) for i in range(3)]
        self.assertEqual(row,before)
        out[0]['input']['state']['application_id']=1
        out[0]['input']['available_tools'].clear()
        self.assertEqual(out[2]['input']['state']['application_id'],702)
        self.assertEqual(row,before)

    def test_candidate_validator_rejects_impossible_tool_and_false_review_claim(self):
        row=b.derive(source(),'query',2);b.validate_row(row)
        row['input']['available_tools']=[]
        with self.assertRaisesRegex(ValueError,'Impossible tool'):b.validate_row(row)
        row=b.derive(source(),'query',2);row['review']['human_reviewed_current_version']=True
        with self.assertRaisesRegex(ValueError,'review claim'):b.validate_row(row)


if __name__=='__main__':unittest.main()
