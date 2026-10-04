from copy import deepcopy
import unittest
import json
import uuid
from contextlib import contextmanager
from pathlib import Path
from qwenlab.common import ROOT,sha
from qwenlab.prepare_v2 import write_rows
from qwenlab.financial_completion import proposal_to_row,verify_review,review_selection,verify_pending_coverage


@contextmanager
def review_fixture():
    # Python's 0700 temporary-directory ACL is incompatible with this Windows
    # sandbox identity; ordinary workspace directories inherit the correct ACL.
    folder=ROOT/'.local'/'test-financial-completion'/str(uuid.uuid4())
    folder.mkdir(parents=True)
    try:yield folder
    finally:
        for name in ['validated.jsonl','source.jsonl','drafts.jsonl','structural-audit.json','review.json','review-findings.json']:
            (folder/name).unlink(missing_ok=True)
        folder.rmdir()


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.source={'source_id':'massive-train-unit','source_path':'data/raw/massive-1.1-zh-CN.jsonl',
            'source_split':'train','source_group':'unit','source_message':'查看原服务列表',
            'source_history':[],'source_labels':{'intent':'lists_query'},'dataset':'massive',
            'source_dialog_id':None,'source_turn_index':None,'already_processed':False}
        self.p={'source_id':'massive-train-unit','message':'查一下我提交过的借款申请。','history':[],
            'state':{'authenticated':True},'action':'tool','tool_name':'queryMyApplications','tool_arguments':{},
            'retrieval_collection':None,'missing_slots':[],'reason':'查询本人已有申请列表。',
            'rewrite_rationale':'原列表查询改成贷款申请列表，新金融背景为合成。'}

    def test_provenance_separated_and_synthetic_declared(self):
        r=proposal_to_row(self.p,self.source,'test_author')
        self.assertNotIn('source_message',r['input'])
        self.assertEqual(r['provenance']['parent_message'],self.source['source_message'])
        self.assertFalse(r['review']['human_reviewed_current_version'])

    def test_no_silent_empty_state_default(self):
        self.p['state']={}
        with self.assertRaises(ValueError):proposal_to_row(self.p,self.source,'test_author')

    def test_unsupported_retrieval_collection(self):
        self.p.update(action='retrieve',tool_name=None,retrieval_collection='invented_bank_records')
        with self.assertRaises(ValueError):proposal_to_row(self.p,self.source,'test_author')

    def test_wrong_parent_and_extra_fields_rejected(self):
        for change in ({'source_id':'another'},{'label_hint':'hidden_label'}):
            p={**deepcopy(self.p),**change}
            with self.assertRaises(ValueError):proposal_to_row(p,self.source,'test_author')

    def test_number_grounding_enforced(self):
        self.p.update(tool_name='queryApplicationDetail',tool_arguments={'applicationId':81234},state={'authenticated':True,'application_id':81234})
        with self.assertRaises(ValueError):proposal_to_row(self.p,self.source,'test_author')

    def test_short_natural_clarification_allowed(self):
        self.p.update(message='还款。',action='clarify',tool_name=None,missing_slots=['request_details'])
        self.assertEqual(proposal_to_row(self.p,self.source,'test_author')['annotation']['action'],'clarify')

    def test_review_artifact_hash_and_independence(self):
        with review_fixture() as folder:
            row=proposal_to_row(self.p,self.source,'author')
            write_rows(folder/'validated.jsonl',[row]);write_rows(folder/'source.jsonl',[self.source])
            write_rows(folder/'drafts.jsonl',[self.p])
            audit={'errors':[],'missing':[],'validated_sha256':sha(folder/'validated.jsonl'),
                   'draft_file':'drafts.jsonl','draft_sha256':sha(folder/'drafts.jsonl'),
                   'author_id':'author','source_sha256':sha(folder/'source.jsonl')}
            (folder/'structural-audit.json').write_text(json.dumps(audit),encoding='utf-8')
            review={'decision':'pass','reviewer':'independent','human_review':False,
                    'mode':'full_independent_agent_review','validated_sha256':audit['validated_sha256'],
                    'reviewed_source_ids':[self.source['source_id']],'unresolved_findings':[]}
            (folder/'review-findings.json').write_text(json.dumps(review),encoding='utf-8')
            review.update(findings_sha256=sha(folder/'review-findings.json'),source_sha256=audit['source_sha256'],
                          audit_sha256=sha(folder/'structural-audit.json'))
            (folder/'review.json').write_text(json.dumps(review),encoding='utf-8')
            self.assertEqual(verify_review(folder,{'worker':'author'}),(1,1))
            original_findings=(folder/'review-findings.json').read_bytes()
            failed=json.loads(original_findings);failed['decision']='fail'
            (folder/'review-findings.json').write_text(json.dumps(failed),encoding='utf-8')
            rebound={**review,'findings_sha256':sha(folder/'review-findings.json')}
            (folder/'review.json').write_text(json.dumps(rebound),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Findings do not pass'):verify_review(folder,{'worker':'author'})
            (folder/'review-findings.json').write_bytes(original_findings)
            (folder/'review.json').write_text(json.dumps(review),encoding='utf-8')
            original_source=(folder/'source.jsonl').read_bytes()
            write_rows(folder/'source.jsonl',[{**self.source,'source_message':'changed but same ID'}])
            with self.assertRaisesRegex(ValueError,'source changed'):verify_review(folder,{'worker':'author'})
            (folder/'source.jsonl').write_bytes(original_source)
            unclosed={k:v for k,v in review.items() if k!='unresolved_findings'}
            (folder/'review.json').write_text(json.dumps(unclosed),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'explicit closure'):verify_review(folder,{'worker':'author'})
            bad={**review,'reviewer':'/root/author'}
            (folder/'review.json').write_text(json.dumps(bad),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'own draft'):verify_review(folder,{'worker':'author'})
            (folder/'review.json').write_text(json.dumps(review),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Missing author'):verify_review(folder,{})
            (folder/'drafts.jsonl').write_text('{}\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Draft changed'):verify_review(folder,{'worker':'author'})

    def test_pending_cannot_omit_or_rewrite_authoritative_source(self):
        a={'source_id':'a','source_message':'a','processing_status':'pending_financial_adaptation_review'}
        b={**a,'source_id':'b','source_message':'b'}
        with self.assertRaisesRegex(ValueError,'authoritative'):verify_pending_coverage([a,b],[a],2)
        with self.assertRaisesRegex(ValueError,'authoritative'):verify_pending_coverage([a,b],[a,{**b,'source_message':'changed'}],2)
        self.assertEqual(verify_pending_coverage([a,b],[b,a],2),{'pending_financial_adaptation_review':2})

    def test_review_selection_includes_every_safety_boundary(self):
        rows=[]
        for i in range(20):
            source={**self.source,'source_id':f'massive-train-unit-{i}'}
            p={**self.p,'source_id':source['source_id'],'message':f'第{i}个示例：查询本人贷款申请列表。'}
            rows.append(proposal_to_row(p,source,'author'))
        rows[-1]['annotation'].update(action='human',tool_name=None)
        selection=review_selection(rows)
        self.assertIn(rows[-1]['provenance']['parent_id'],selection['required_source_ids'])
        self.assertEqual(selection,review_selection(list(reversed(rows))))


if __name__=='__main__':unittest.main()
