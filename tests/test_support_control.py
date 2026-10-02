import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qwenlab import support_control as control
from qwenlab.common import sha
from qwenlab.joint_v5 import atomic_json


class PauseControlTests(unittest.TestCase):
    def test_only_exact_run_modules_are_selected(self):
        self.assertEqual(control.module_role(['python','-m','qwenlab.support_train_v8','run']),'train')
        self.assertEqual(control.module_role(['python','-m','qwenlab.support_v8_cycle','--resume']),'cycle')
        self.assertEqual(control.module_role(['python','-m','qwenlab.support_v8_finalize']),'finalize')
        self.assertIsNone(control.module_role(['python','-m','qwenlab.support_train_v8','progress']))
        self.assertIsNone(control.module_role(['python','-m','unrelated']))

    def test_truncated_final_log_does_not_prevent_safe_pause(self):
        self.assertEqual(control.last_logged_step(['{"step":301}','{"ste'],300),301)
        self.assertEqual(control.last_logged_step([],300),300)

    def test_resume_rejects_duplicate_worker_before_mutation(self):
        with patch.object(control,'discover',return_value=[{'pid':1}]),patch.object(control,'write_state') as write:
            with self.assertRaisesRegex(RuntimeError,'already running'): control.resume_check()
            write.assert_not_called()

    def test_failed_resume_start_can_retry_without_live_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); marker=root/'pause.json'; checkpoint=root/'step-300'; checkpoint.mkdir()
            atomic_json(marker,{'state':'resuming','checkpoint':'step-300','step':300})
            with patch.object(control,'ROOT',root),patch.object(control,'CONTROL',marker),patch.object(control,'discover',return_value=[]),patch.object(control,'verify_checkpoint',return_value={'step':300}),patch.object(control,'latest',return_value=checkpoint),patch.object(control,'write_state') as write:
                control.resume_check()
                self.assertEqual(write.call_args.args[0],'resuming')

    def test_old_pause_record_cannot_hide_live_finalizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'pause.json'
            atomic_json(marker,{'state':'paused','checkpoint':'step-300'})
            with patch.object(control,'CONTROL',marker),patch.object(control,'discover',return_value=[{'pid':456,'role':'finalize'}]),patch.object(control,'verify_checkpoint') as verify:
                with self.assertRaisesRegex(RuntimeError,'No active V8 training'): control.pause()
                verify.assert_not_called()

    def test_new_finalizer_prevents_shutdown_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); checkpoint=root/'step-300'; checkpoint.mkdir()
            record={'pid':123,'role':'train'}
            live=iter([True,True,False,False])
            with patch.object(control,'discover',side_effect=[[record],[{'pid':456,'role':'finalize'}]]),patch.object(control,'latest',return_value=checkpoint),patch.object(control,'verify_checkpoint',return_value={'step':300}),patch.object(control,'write_state') as write,patch.object(control,'same_process',side_effect=lambda r:next(live)),patch.object(control.psutil,'Process'):
                with self.assertRaisesRegex(RuntimeError,'shutdown is NOT confirmed'): control.pause(immediate=True)
                self.assertNotIn('paused',[c.args[0] for c in write.call_args_list])

    def test_checkpoint_and_teacher_integrity_and_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/'results'; out.mkdir()
            ckpt=root/'checkpoints'; path=ckpt/'step-300'; path.mkdir(parents=True)
            atomic_json(out/'protocol.json',{'protocol':'frozen'})
            names=('adapter_model.safetensors','adapter_config.json','training-state.pt')
            for n in names: (path/n).write_bytes(b'test')
            atomic_json(path/'checkpoint.json',{'step':300,'protocol_sha256':sha(out/'protocol.json'),'files':{n:sha(path/n) for n in names}})
            teacher=root/'.local/cache/support-v8-teacher'; teacher.mkdir(parents=True)
            (teacher/'logits.jsonl').write_bytes(b'{}\n')
            atomic_json(teacher/'identity.json',{})
            atomic_json(teacher/'manifest.json',{'protocol_sha256':sha(out/'protocol.json'),'logits_sha256':sha(teacher/'logits.jsonl')})
            with patch.object(control,'ROOT',root),patch.object(control,'OUT',out),patch.object(control,'CKPT',ckpt),patch.object(control.os,'fsync') as sync:
                self.assertEqual(control.verify_checkpoint(path,True)['step'],300)
                self.assertEqual(sync.call_count,8)
                with self.assertRaisesRegex(ValueError,'outside'): control.verify_checkpoint(root/'other')
                (path/'training-state.pt').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'integrity'): control.verify_checkpoint(path)


if __name__=='__main__': unittest.main()
