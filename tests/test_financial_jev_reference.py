import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from qwenlab import financial_jev_reference as j


def row():
    return dict(id='sample-1',split='development',annotation={'action':'human'},
        input=dict(message='查一下我的申请',history=[],state={'authenticated':True},
            capabilities={'knowledge_collections':[],'handoff_connected':False},
            available_tools=j.prompt.TOOLS,images=[]))


def body(action='answer',model='jev-test-1'):
    def answer(keys,choice):
        return dict(choice=choice,probabilities={k:float(k==choice) for k in keys},confidence=.8)
    return dict(model=model,answers=dict(action=answer(j.prompt.ACTIONS,action),
        tool=answer(j.prompt.TOOLS,j.prompt.TOOLS[0])),usage={'input_tokens':100,'output_tokens':20})


class ReferenceTests(unittest.TestCase):
    def test_payload_never_contains_labels_or_provenance(self):
        r=row();p=j.payload(r);r['annotation']={'action':'refuse'};r['id']='different'
        r['provenance']={'private':'not visible'}
        self.assertEqual(p,j.payload(r))
        self.assertEqual(set(p['questions']),{'action','tool'})

    def test_tool_only_counts_after_predicted_tool(self):
        out=j.normalize('1','development',body(),.1,'hash','jev-test-1')
        self.assertIsNone(out['tool_name'])
        self.assertIn('raw_tool_prediction',out)
        out=j.normalize('1','development',body('tool'),.1,'hash','jev-test-1')
        self.assertEqual(out['tool_name'],j.prompt.TOOLS[0])

    def test_nan_and_model_drift_fail(self):
        b=body();b['answers']['action']['probabilities']['answer']=float('nan')
        with self.assertRaises(ValueError):j.normalize('1','development',b,.1,'hash','jev-test-1')
        with self.assertRaises(ValueError):j.normalize('1','development',body(),.1,'hash','other')

    def test_pending_and_failed_are_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'request.json'
            for state in ['pending','failed_or_uncertain']:
                j.write(p,dict(state=state,request_sha256='one'))
                with self.assertRaises(RuntimeError):j.use_cached(p,'one')
            with self.assertRaises(ValueError):j.use_cached(p,'changed')

    def test_complete_run_is_idempotent_and_uses_two_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'results';key=root/'.local/secrets/jev-api-key.txt'
            key.parent.mkdir(parents=True);key.write_text('unit-test-token',encoding='utf-8')
            samples=[row(),dict(row(),id='sample-2')]
            op=Mock();op.open.side_effect=[io.StringIO(json.dumps(body())),io.StringIO(json.dumps(body('tool')))]
            with patch.object(j,'ROOT',root),patch.object(j,'OUT',out),patch.object(j,'SPLITS',{'development':2}), \
                 patch.object(j,'MAX_REQUESTS',2),patch.object(j,'freeze',return_value={'test':True}), \
                 patch.object(j,'source_rows',return_value=samples),patch.object(j,'exclusive_lock',return_value=contextlib.nullcontext()), \
                 patch.object(j.urllib.request,'build_opener',return_value=op):
                j.run();j.run()
                self.assertEqual(op.open.call_count,2)
                self.assertEqual(j.read(out/'completion.json')['input_tokens'],200)
                self.assertEqual(len(j.read(out/'development-predictions.json')),2)
                self.assertFalse(j.read(out/'completion.json')['final_scored'])

    def test_failed_api_writes_ledger_and_resume_never_reissues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'results';key=root/'.local/secrets/jev-api-key.txt'
            key.parent.mkdir(parents=True);key.write_text('unit-test-token',encoding='utf-8')
            op=Mock();op.open.side_effect=TimeoutError('Never serialize this exception message')
            with patch.object(j,'ROOT',root),patch.object(j,'OUT',out),patch.object(j,'SPLITS',{'development':1}), \
                 patch.object(j,'MAX_REQUESTS',1),patch.object(j,'freeze',return_value={'test':True}), \
                 patch.object(j,'source_rows',return_value=[row()]),patch.object(j,'exclusive_lock',return_value=contextlib.nullcontext()), \
                 patch.object(j.urllib.request,'build_opener',return_value=op):
                with self.assertRaises(RuntimeError):j.run()
                with self.assertRaises(RuntimeError):j.run()
                self.assertEqual(op.open.call_count,1)
                text=(out/'requests/development/sample-1.json').read_text(encoding='utf-8')
                self.assertNotIn('Never serialize',text)
                self.assertNotIn('unit-test-token',text)


if __name__=='__main__':unittest.main()
