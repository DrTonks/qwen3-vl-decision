"""Isolated export recovery tests; never finalize the real rewrite corpus."""
from contextlib import ExitStack,contextmanager,redirect_stdout
import io
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

import qwenlab.financial_completion as completion
from qwenlab.common import ROOT,sha
from qwenlab.prepare_v2 import write_rows
from qwenlab.joint_v5 import atomic_json


@contextmanager
def workspace():
    # Retain these small, ignored fixtures for failure diagnosis. No recursive
    # removal or writes outside the explicitly named workspace are performed.
    root=ROOT/'.local/test-financial-completion-export'/uuid.uuid4().hex
    base=root/'.local/financial-rewrite-completion';job=base/'jobs/0001';job.mkdir(parents=True)
    old=root/'.local/financial-public-rewrite-v1';old.mkdir(parents=True)
    source={'source_id':'massive-train-unit','source_path':'data/raw/massive-1.1-zh-CN.jsonl',
        'source_split':'train','source_group':'unit','source_message':'查看原服务列表',
        'source_history':[],'source_labels':{'intent':'lists_query'},'dataset':'massive',
        'source_dialog_id':None,'source_turn_index':None,'already_processed':False,
        'processing_status':'pending_financial_adaptation_review'}
    proposal={'source_id':source['source_id'],'message':'请查一下我的借款申请列表。','history':[],
        'state':{'authenticated':True},'action':'tool','tool_name':'queryMyApplications',
        'tool_arguments':{},'retrieval_collection':None,'missing_slots':[],
        'reason':'已登录，查询本人已有申请列表。','rewrite_rationale':'将原列表查询合成为个人借款列表查询。'}
    for name in ['pending.jsonl','inventory.jsonl']:write_rows(old/name,[source])
    write_rows(job/'source.jsonl',[source]);write_rows(job/'drafts.jsonl',[proposal])
    entry={'job':'0001','source_count':1,'source_sha256':sha(job/'source.jsonl'),
           'status':'drafting','worker':'author'}
    atomic_json(job/'status.json',entry)
    atomic_json(base/'queue.json',{'source_count':1,'pending_sha256':sha(old/'pending.jsonl'),'jobs':[entry]})
    for directory in ['financial-actions-text-v2','financial-public-rewrite-v1']:
        folder=root/'data'/directory;folder.mkdir(parents=True);write_rows(folder/'cases.jsonl',[])
    atomic_json(root/'data/financial-public-rewrite-v1/manifest.json',{
        'full_inventory_status':{'pending_financial_adaptation_review':1},'ledger_sha256':sha(old/'inventory.jsonl')})
    with ExitStack() as stack:
        for name,value in [('ROOT',root),('BASE',base),('SOURCE',old/'pending.jsonl')]:
            stack.enter_context(patch.object(completion,name,value))
        stack.enter_context(patch.object(completion,'completion_protection',return_value=set()))
        stack.enter_context(patch('qwenlab.financial_public_rewrite.validate',return_value={}))
        stack.enter_context(redirect_stdout(io.StringIO()))
        completion.audit_job('0001')
        report={'decision':'pass','reviewer':'independent','mode':'full_independent_agent_review',
                'human_review':False,'reviewed_source_ids':[source['source_id']],
                'validated_sha256':sha(job/'validated.jsonl'),'unresolved_findings':[]}
        atomic_json(job/'review-findings.json',report)
        report.update(findings_sha256=sha(job/'review-findings.json'),source_sha256=sha(job/'source.jsonl'),
                      audit_sha256=sha(job/'structural-audit.json'))
        atomic_json(job/'review.json',report);completion.accept_job('0001')
        yield root,base,job


class ExportRecoveryTests(unittest.TestCase):
    def test_multiple_parts_preserve_exact_order_and_content(self):
        with workspace() as (root,base,job):
            out=root/'partition-test';out.mkdir()
            rows=[{'id':f'case-{i}','message':'分片测试'} for i in range(5)]
            completion.write_export_rows(out/'cases.jsonl',rows)
            parts=completion.write_parts(out,rows,part_size=2)
            self.assertEqual([p['rows'] for p in parts],[2,2,1])
            manifest={'parts':parts,'candidate_rows':5,'cases_sha256':sha(out/'cases.jsonl')}
            self.assertEqual(completion.verify_parts(out,manifest),5)
            for part in parts:
                self.assertNotIn(b'\r',(out/part['path']).read_bytes())
            self.assertEqual((out/'cases.jsonl').read_bytes(),
                             b''.join((out/part['path']).read_bytes() for part in parts))
            changed=[dict(p) for p in parts]
            changed[0]['sha256'],changed[1]['sha256']=changed[1]['sha256'],changed[0]['sha256']
            with self.assertRaisesRegex(ValueError,'part changed'):
                completion.verify_parts(out,{**manifest,'parts':changed})

    def test_parts_portable_verification_and_changed_parts(self):
        with workspace() as (root,base,job):
            manifest=completion.finalize();out=root/'data/financial-public-rewrite-completion-v1'
            self.assertEqual(completion.verify_parts(out,manifest),1)
            combined=(out/'cases.jsonl').read_bytes()
            (out/'cases.jsonl').unlink()
            self.assertEqual(completion.verify_parts(out,manifest),1)
            part=out/manifest['parts'][0]['path']
            part.write_bytes(combined+b'{}\n')
            with self.assertRaisesRegex(ValueError,'part changed'):completion.verify_parts(out,manifest)

    def test_export_bytes_are_lf_and_crlf_conversion_is_rejected(self):
        with workspace() as (root,base,job):
            manifest=completion.finalize();out=root/'data/financial-public-rewrite-completion-v1'
            self.assertEqual(manifest['jsonl_newline'],'LF')
            for name in ['cases.jsonl','source-ledger.jsonl',manifest['parts'][0]['path']]:
                self.assertNotIn(b'\r',(out/name).read_bytes())
            part=out/manifest['parts'][0]['path']
            part.write_bytes(part.read_bytes().replace(b'\n',b'\r\n'))
            with self.assertRaisesRegex(ValueError,'part changed'):
                completion.verify_parts(out,manifest)

    def test_parts_reject_omission_order_and_extra_files(self):
        with workspace() as (root,base,job):
            manifest=completion.finalize();out=root/'data/financial-public-rewrite-completion-v1'
            with self.assertRaisesRegex(ValueError,'Missing export parts'):
                completion.verify_parts(out,{**manifest,'parts':[]})
            bad={**manifest,'parts':[{**manifest['parts'][0],'path':'../cases.jsonl'}]}
            with self.assertRaisesRegex(ValueError,'order/path'):
                completion.verify_parts(out,bad)
            (out/'parts/part-0002.jsonl').write_text('{}\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Unexpected export part'):
                completion.verify_parts(out,manifest)

    def test_retained_message_is_not_counted_as_rewrite_or_full_original_input(self):
        # A domain redirect may retain source wording with only punctuation
        # changes, while the surrounding state/history remains synthetic.
        row={'id':'retained','scene_family_id':'family',
             'input':{'message':'多说一点关于郑和的事。','history':[{'role':'user','content':'新合成上下文'}]},
             'provenance':{'parent_id':'source','parent_message':'多说一点关于郑和的事'}}
        self.assertEqual(completion.source_ledger([row])[0]['status'],'source_message_retained')
        row['input']['message']='多说一点关于贷款申请的事。'
        self.assertEqual(completion.source_ledger([row])[0]['status'],'rewritten')

    def test_export_rejects_inflated_rewritten_count(self):
        with workspace() as (root,base,job):
            manifest=completion.finalize();out=root/'data/financial-public-rewrite-completion-v1'
            self.assertEqual(manifest['source_message_status'],{'rewritten':1})
            manifest['source_message_status']={'rewritten':2}
            atomic_json(out/'manifest.json',manifest)
            with self.assertRaisesRegex(ValueError,'source message counts'):
                completion.verify_export(out)

    def test_partial_export_retry_is_idempotent_and_progress_validates(self):
        with workspace() as (root,base,job):
            original=completion.write_export_rows
            def interrupted(path,rows):
                if path.name=='source-ledger.jsonl':raise OSError('simulated disk interruption')
                return original(path,rows)
            out=root/'data/financial-public-rewrite-completion-v1'
            with patch.object(completion,'write_export_rows',side_effect=interrupted):
                with self.assertRaisesRegex(OSError,'interruption'):completion.finalize()
            self.assertFalse(out.exists())
            self.assertFalse((base/'completion.json').exists())
            manifest=completion.finalize()
            self.assertTrue(completion.progress()['whole_goal_complete'])
            first=(out/'cases.jsonl').stat().st_mtime_ns
            (base/'completion.json').unlink()
            self.assertEqual(completion.finalize(),manifest)
            self.assertEqual(first,(out/'cases.jsonl').stat().st_mtime_ns)
            self.assertTrue(completion.progress()['whole_goal_complete'])
            with patch.object(completion,'completion_protection',side_effect=ValueError('Protected change')):
                with self.assertRaisesRegex(ValueError,'Protected change'):completion.progress()

    def test_manifest_coverage_and_ledger_tampering_fail(self):
        with workspace() as (root,base,job):
            manifest=completion.finalize();out=root/'data/financial-public-rewrite-completion-v1'
            bad={**manifest,'candidate_rows':0}
            atomic_json(out/'manifest.json',bad);atomic_json(base/'completion.json',bad)
            with self.assertRaisesRegex(ValueError,'coverage/counts'):completion.progress()
            atomic_json(out/'manifest.json',manifest)
            ledger=json.loads((out/'source-ledger.jsonl').read_text(encoding='utf-8'))
            ledger['candidate_id']='wrong';write_rows(out/'source-ledger.jsonl',[ledger])
            bad={**manifest,'source_ledger_sha256':sha(out/'source-ledger.jsonl')}
            atomic_json(out/'manifest.json',bad)
            with self.assertRaisesRegex(ValueError,'ledger does not match'):completion.verify_export(out)

    def test_accept_rejects_source_change_with_same_ids(self):
        with workspace() as (root,base,job):
            source=json.loads((job/'source.jsonl').read_text(encoding='utf-8'))
            source['source_message']='changed';write_rows(job/'source.jsonl',[source])
            with self.assertRaisesRegex(ValueError,'Frozen job source changed'):completion.accept_job('0001')


if __name__=='__main__':unittest.main()
