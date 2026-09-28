import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qwenlab import support_v8_finalize as final
from qwenlab.common import append_json, load_json, sha
from qwenlab.joint_v5 import atomic_json


class FinalizeTests(unittest.TestCase):
    def fixture(self, root):
        (root/'.local/secrets').mkdir(parents=True)
        (root/'.local/secrets/jev-api-key.txt').write_text('test-placeholder',encoding='utf-8')
        (root/'configs').mkdir()
        criteria={'intent':{'products':'products'},'route':{'tool':'tool'},'tool':{'queryLoanProducts':'products'}}
        spec={'policy':'test','questions':{k:{'instructions':'test','criteria':v} for k,v in criteria.items()}}
        atomic_json(root/'configs/decision-v5.json',spec)
        out=root/'final'; out.mkdir()
        row={'id':'one','group':'g','labels':{'intent':'products','route':'tool','tool':'queryLoanProducts'},'message':'test'}
        body={'model':'test-version','answers':{k:{'choice':next(iter(v)),'probabilities':{next(iter(v)):1.}} for k,v in criteria.items()}}
        return out,row,body

    def test_api_budget_and_uncertain_request_never_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out,row,body=self.fixture(root)
            with patch.object(final,'ROOT',root),patch.object(final,'FINAL',out),patch.object(final,'state'),patch.object(final.urllib.request,'build_opener') as opener:
                with self.assertRaisesRegex(ValueError,'budget'):
                    final.vendor([row],[],{'final_evaluation':{'jev_max_requests':0}})
                opener.assert_not_called()
                append_json(out/'jev/attempts.jsonl',{'sequence':0,'kind':'challenge','id':'one'})
                with self.assertRaisesRegex(ValueError,'Uncertain'):
                    final.vendor([row],[],{'final_evaluation':{'jev_max_requests':1}})
                opener.assert_not_called()

    def test_vendor_success_reused_and_version_mismatch_stops(self):
        from io import StringIO
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out,row,body=self.fixture(root)
            with patch.object(final,'ROOT',root),patch.object(final,'FINAL',out),patch.object(final,'state'),patch.object(final.urllib.request,'build_opener') as opener:
                opener.return_value.open.return_value=StringIO(json.dumps(body))
                cfg={'final_evaluation':{'jev_max_requests':2}}
                result=final.vendor([row],[],cfg)
                self.assertEqual(result['challenge'][0]['model'],'test-version')
                final.vendor([row],[],cfg)
                self.assertEqual(opener.return_value.open.call_count,1)
                changed={**body,'model':'changed-version'}
                opener.return_value.open.return_value=StringIO(json.dumps(changed))
                with self.assertRaisesRegex(RuntimeError,'Vendor stopped'):
                    final.vendor([row],[row],cfg)
                before=opener.return_value.open.call_count
                with self.assertRaisesRegex(ValueError,'Previous vendor error'):
                    final.vendor([row],[row],cfg)
                self.assertEqual(opener.return_value.open.call_count,before)

    def test_no_candidate_does_not_load_models_or_call_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            atomic_json(out/'selection.json',{'selected':'v5-reference'})
            with patch('qwenlab.support_train_v8.prepare',return_value={}),patch.object(final,'OUT',out),patch.object(final,'FINAL',out/'final'),patch.object(final,'failed_report') as report,patch.object(final,'load_model') as model,patch.object(final,'vendor') as api:
                final.run()
                report.assert_called_once()
                model.assert_not_called()
                api.assert_not_called()

    def test_changed_selected_adapter_is_rejected_before_final_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/'results'; out.mkdir()
            atomic_json(out/'protocol.json',{'frozen':True})
            ck=root/'.local/checkpoints/support-v8/step-200'; ck.mkdir(parents=True)
            (ck/'adapter_model.safetensors').write_bytes(b'original')
            atomic_json(ck/'checkpoint.json',{'step':200,'protocol_sha256':sha(out/'protocol.json'),
                        'files':{'adapter_model.safetensors':sha(ck/'adapter_model.safetensors')}})
            (ck/'adapter_model.safetensors').write_bytes(b'changed')
            with patch.object(final,'ROOT',root),patch.object(final,'OUT',out),patch('qwenlab.support_train_v8.latest_checkpoint'):
                with self.assertRaisesRegex(ValueError,'corrupt'):
                    final.verify_candidate('step-200',{})

    def test_attempt_is_synced_before_return(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(final.os,'fsync') as sync:
            p=Path(tmp)/'attempts.jsonl'
            final.record_attempt(p,{'sequence':0})
            sync.assert_called_once()
            self.assertEqual(json.loads(p.read_text(encoding='utf-8'))['sequence'],0)


if __name__=='__main__': unittest.main()
