"""Synthetic CPU safety invariants; never load model weights or evaluation rows."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from qwenlab import financial_sampling_cycle as cycle


def protocol():
    return {'common_binding': {'schedule_manifest_sha256': 'schedule-hash'}}


def checkpoint(step=12):
    return dict(step=step, arm='uniform', schedule_manifest_sha256='schedule-hash',
                cursor=dict(arm='uniform', completed_steps=step, next_step=step + 1),
                initial_parameter_sha256='a' * 64, sample_positions=step * 8)


class CheckpointAndScheduleTests(unittest.TestCase):
    def test_probe_and_main_have_separate_artifact_namespaces(self):
        main, probe = cycle.Run(), cycle.Run(cycle.PROBE)
        self.assertFalse(main.probe)
        self.assertTrue(probe.probe)
        for attribute in ('out', 'control', 'checkpoints', 'cache'):
            self.assertNotEqual(getattr(main, attribute), getattr(probe, attribute))
        with self.assertRaises(ValueError):
            cycle.Run('financial-service-v2-main')
        self.assertNotEqual(cycle.ArmRun(main, 'uniform').cache,
                            cycle.ArmRun(main, 'stratified').cache)

    def test_resume_cursor_is_the_next_unconsumed_business_batch(self):
        value = checkpoint()
        self.assertTrue(cycle.checkpoint_summary_binding(value, protocol(), 'uniform', 12))
        for key, altered in (
            ('step', 11), ('arm', 'stratified'), ('sample_positions', 95),
            ('schedule_manifest_sha256', 'stale'), ('initial_parameter_sha256', 'short'),
            ('cursor', dict(arm='uniform', completed_steps=12, next_step=12)),
            ('cursor', dict(arm='stratified', completed_steps=12, next_step=13)),
        ):
            bad = deepcopy(value)
            bad[key] = altered
            with self.subTest(key=key, altered=altered), self.assertRaises(ValueError):
                cycle.checkpoint_summary_binding(bad, protocol(), 'uniform', 12)
        for key in value:
            bad = deepcopy(value)
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                cycle.checkpoint_summary_binding(bad, protocol(), 'uniform', 12)

    def test_frozen_schedule_rejects_cursor_order_or_accounting_tampering(self):
        expected = {'step_rows': [['synthetic-a', 'synthetic-b']],
                    'counts': {'row': {'synthetic-a': 1, 'synthetic-b': 1}}}
        rows = [{'id': 'synthetic-a'}, {'id': 'synthetic-b'}]
        with patch.object(cycle.schedule.sampler, 'plan', return_value=expected) as replay:
            self.assertEqual(cycle.validate_schedule(deepcopy(expected), rows, 'uniform',
                                                    {'sampling_seed': 123}), expected['step_rows'])
            replay.assert_called_once_with(rows, 'uniform', 123, 400, 8,
                                           max_row_exposure=4, max_group_exposure=16)
        mutations = [dict(step_rows=[['synthetic-b', 'synthetic-a']]),
                     dict(counts={'row': {'synthetic-a': 2, 'synthetic-b': 0}})]
        for mutation in mutations:
            bad = deepcopy(expected)
            bad.update(mutation)
            with patch.object(cycle.schedule.sampler, 'plan', return_value=expected):
                with self.assertRaises(ValueError):
                    cycle.validate_schedule(bad, rows, 'uniform', {'sampling_seed': 123})

    def test_probe_uses_frozen_400_step_learning_rate_not_25_step_decay(self):
        cfg = {'learning_rate': 5e-5, 'warmup_steps': 100}
        for step, expected in ((1, 5e-7), (12, 6e-6), (25, 1.25e-5),
                               (100, 5e-5), (200, 3.35e-5), (400, 5e-5 / 300)):
            with self.subTest(step=step):
                self.assertAlmostEqual(cycle.learning_rate(step, cfg), expected)
        for step in (0, 401, 1.5, True):
            with self.subTest(step=step), self.assertRaises(ValueError):
                cycle.learning_rate(step, cfg)

    def test_resume_rejects_missing_duplicate_or_reordered_committed_business_rows(self):
        arm = SimpleNamespace(out=Path('synthetic/arm'))
        schedule = [['row-a', 'row-b'], ['row-c', 'row-d']]
        valid = [dict(step=1, row_ids=schedule[0]), dict(step=2, row_ids=schedule[1])]
        for records in (valid[:1], [valid[0], valid[0]],
                        [dict(step=1, row_ids=list(reversed(schedule[0]))), valid[1]]):
            raw = ''.join(json.dumps(r) + '\n' for r in records)
            with self.subTest(records=records), patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'read_text', return_value=raw):
                with self.assertRaises(ValueError):
                    cycle.recover_logs(arm, 2, schedule)

    def test_resume_discards_only_uncommitted_suffix_and_preserves_evidence(self):
        arm = SimpleNamespace(out=Path('synthetic/arm'))
        schedule = [['row-a'], ['row-b']]
        committed = dict(step=1, row_ids=['row-a'])
        raw = json.dumps(committed) + '\n' + '{"step":2,"row_ids":'
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'read_text', return_value=raw), patch.object(Path, 'open') as opened, \
             patch.object(cycle, 'durable_json') as evidence, patch.object(cycle.os, 'fsync'):
            kept = cycle.recover_logs(arm, 1, schedule)
            self.assertEqual(kept, [committed])
            self.assertEqual(evidence.call_args.args[1], {'raw': raw, 'checkpoint_step': 1})
            written = opened.return_value.__enter__.return_value.write.call_args.args[0].decode('utf-8')
            self.assertEqual(json.loads(written), committed)


class ReviewBindingTests(unittest.TestCase):
    def setUp(self):
        self.review = dict(version='financial-sampling-executor-review-v1', status='pass',
                           independent=True, reviewer='/synthetic-independent-reviewer',
                           human_reviewed=False, evaluation_examples_read=False,
                           predictions_read=False, gpu_used=False, model_api_requests=0,
                           open_findings=[], files={name: 'hash' for name in cycle.REVIEW_FILES},
                           config_sha256='hash', schedule_manifest_sha256='hash')

    def verify(self, review):
        with patch.object(cycle, 'read', return_value=review), patch.object(cycle, 'sha', return_value='hash'):
            return cycle.verify_review()

    def test_only_complete_independent_bound_review_authorizes_executor(self):
        self.assertEqual(self.verify(self.review), self.review)
        mutations = [('status', 'pending'), ('independent', False), ('human_reviewed', True),
                     ('evaluation_examples_read', True), ('predictions_read', True),
                     ('gpu_used', True), ('model_api_requests', 1), ('open_findings', ['unresolved']),
                     ('reviewer', '/root'), ('reviewer', '/root/supplement_expand_b'),
                     ('config_sha256', 'old'), ('schedule_manifest_sha256', 'old')]
        for key, value in mutations:
            bad = deepcopy(self.review)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(bad)
        for name in cycle.REVIEW_FILES:
            bad = deepcopy(self.review)
            del bad['files'][name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                self.verify(bad)

    def test_review_rejects_changed_source_bytes(self):
        for name in cycle.REVIEW_FILES:
            bad = deepcopy(self.review)
            bad['files'][name] = 'old-source-hash'
            with self.subTest(source=name), self.assertRaises(ValueError):
                self.verify(bad)

    def test_source_closure_does_not_blindly_trust_inherited_hash_claims(self):
        frozen = {'sources': {'synthetic/transitive.py': 'stale'}, 'files': {}}
        with patch.object(cycle, 'read', return_value=frozen), \
             patch.object(cycle, 'sha', return_value='current'), patch.object(cycle, 'SOURCES', []):
            with self.assertRaises(ValueError):
                cycle.source_bindings()


class EncodedCacheTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='synthetic-1', action='answer', tool_name=None)]
        self.run = SimpleNamespace(cache=Path('synthetic/cache'), protocol_hash=lambda: 'protocol-hash')
        keys = list(cycle.prompt.SPEC['actions'])
        self.encoded = [dict(action=dict(id='synthetic-1', task='action', keys=keys,
                                        target=keys.index('answer'),
                                        tokens={'input_ids': [101, 102], 'attention_mask': [1, 1]}),
                             tool=None)]
        self.binding = dict(protocol_sha256='protocol-hash', ordered_row_ids=['synthetic-1'],
                            row_sha256={'synthetic-1': 'row-hash'}, prompt_sha256='hash',
                            schedule_manifest_sha256='hash')
        self.meta = dict(binding=self.binding, file_sha256='hash',
                         encoded_payload_sha256=cycle.digest(self.encoded))

    def load_cache(self, encoded, meta, length=2):
        def read(path):
            if Path(path).name == 'encoded-meta.json':
                return meta
            if Path(path).name == 'encoded.json':
                return encoded
            if Path(path).name == 'token-lengths.json':
                return {'rows': [{'row_id': 'synthetic-1', 'action_input_tokens': length,
                                  'tool_input_tokens': None}]}
            raise AssertionError('Unexpected read outside synthetic fixtures: ' + str(path))
        with patch.object(Path, 'exists', return_value=True), patch.object(cycle, 'read', side_effect=read), \
             patch.object(cycle, 'sha', return_value='hash'), \
             patch.object(cycle.prompt, 'encode', return_value=deepcopy(self.encoded[0]['action'])), \
             patch.object(cycle.schedule, 'row_sha', return_value='row-hash'):
            return cycle.encoded_training(self.run, None, self.rows)

    def test_complete_cache_replays_only_when_source_and_token_bindings_match(self):
        self.assertEqual(self.load_cache(self.encoded, self.meta), {'synthetic-1': self.encoded[0]})
        for key in self.meta:
            bad = deepcopy(self.meta)
            del bad[key]
            with self.subTest(missing=key), self.assertRaises((ValueError, KeyError)):
                self.load_cache(self.encoded, bad)
        bad = deepcopy(self.meta)
        bad['binding']['row_sha256']['synthetic-1'] = 'stale-source'
        with self.assertRaises(ValueError):
            self.load_cache(self.encoded, bad)

    def test_cache_rejects_missing_task_fields_and_token_payload_changes(self):
        for key in ('id', 'task', 'target', 'keys', 'tokens'):
            bad = deepcopy(self.encoded)
            del bad[0]['action'][key]
            with self.subTest(missing=key), self.assertRaises((ValueError, KeyError)):
                self.load_cache(bad, self.meta)
        bad = deepcopy(self.encoded)
        bad[0]['action']['tokens']['input_ids'][0] = 999
        with self.assertRaises(ValueError):
            self.load_cache(bad, self.meta)
        with self.assertRaises(ValueError):
            self.load_cache(self.encoded, self.meta, length=3)

    def test_resigned_same_length_cache_cannot_override_actual_prompt_encoding(self):
        for changed_tokens in ({'input_ids': [999, 102], 'attention_mask': [1, 1]},
                               {'input_ids': [101, 102]},
                               {'input_ids': [101, 102], 'attention_mask': [1]}):
            bad = deepcopy(self.encoded)
            bad[0]['action']['tokens'] = changed_tokens
            resigned = deepcopy(self.meta)
            resigned['encoded_payload_sha256'] = cycle.digest(bad)
            with self.subTest(tokens=changed_tokens), self.assertRaises(ValueError):
                self.load_cache(bad, resigned)


class FiniteAndSafeExitTests(unittest.TestCase):
    def test_nonfinite_loss_or_gradient_stops_instead_of_continuing(self):
        cycle.ensure_finite_training(0.8, 1.5)
        for value in (float('nan'), float('inf'), float('-inf')):
            for loss, norm in ((value, .5), (.5, value)):
                with self.subTest(loss=loss, norm=norm), self.assertRaises(FloatingPointError):
                    cycle.ensure_finite_training(loss, norm)

    def test_shutdown_requires_terminal_saved_state_dead_worker_and_released_lock(self):
        for stage in ('paused', 'complete'):
            self.assertTrue(cycle.safe_exit_status({'stage': stage}, False, True, True))
            self.assertFalse(cycle.safe_exit_status({'stage': stage}, True, True, True))
            self.assertFalse(cycle.safe_exit_status({'stage': stage}, False, False, True))
            self.assertFalse(cycle.safe_exit_status({'stage': stage}, False, True, False))
        for stage in ('training', 'saving', 'loading_training', 'failed'):
            self.assertFalse(cycle.safe_exit_status({'stage': stage}, False, True, True))


def gate_config():
    return dict(development_gate={
        'minimum_macro_f1_gain_over_same_prompt_base': .01,
        'minimum_per_action_recall': .8, 'minimum_human_recall': .95,
        'maximum_extra_human_misses_over_base': 0,
        'maximum_extra_false_refusals_on_non_refuse_over_base': 0,
        'maximum_unavailable_knowledge_retrievals': 0,
        'minimum_joint_action_tool_accuracy_on_true_tool': .9,
        'minimum_status_tool_accuracy': .9,
    }, current_service_additional_gate={
        'minimum_human_recall': .95, 'maximum_extra_human_misses_over_base': 0,
        'maximum_extra_false_refusals_on_non_refuse_over_base': 0,
        'maximum_unavailable_knowledge_retrievals': 0,
        'minimum_joint_action_tool_accuracy_on_true_tool': .9,
    }, preauth_additional_gate={'maximum_tool_actions': 0},
        capability_additional_gate={'maximum_unavailable_tool_choices': 0})


def metric_report(macro=.9, joint=.96):
    current = dict(data_sha256='d' * 64, per_action={'human': {'support': 4, 'recall': 1.}},
                   human_misses=[], false_refusals=[], unavailable_knowledge_retrievals=[],
                   action_tool_joint_accuracy=joint)
    return dict(partition='development', rows=16, data_sha256='d' * 64,
                prompt_sha256='e' * 64, protocol_sha256='f' * 64,
                per_action={a: dict(support=2, precision=1., recall=1., f1=1.)
                            for a in cycle.prompt.SPEC['actions']},
                macro_f1=macro, action_tool_joint_accuracy=joint, status_tool_accuracy=1.,
                human_misses=[], false_refusals=[], unavailable_knowledge_retrievals=[],
                unauthenticated_tool_actions=[], unavailable_tool_choices=[],
                cohorts={'current-service': current})


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = gate_config()
        self.reports = dict(base=metric_report(.7), uniform=metric_report(.9), stratified=metric_report(.9))

    def choose(self, reports=None):
        return cycle.choose_candidate(reports or self.reports, self.cfg, 'f' * 64)

    def test_selection_uses_macro_then_joint_then_uniform_only_among_passing_arms(self):
        self.assertEqual(self.choose()['selected'], 'uniform-step-400')
        self.reports['stratified']['action_tool_joint_accuracy'] = .98
        self.assertEqual(self.choose()['selected_arm'], 'stratified')
        self.reports['uniform']['macro_f1'] = .92
        self.assertEqual(self.choose()['selected_arm'], 'uniform')
        self.reports['uniform']['human_misses'] = ['synthetic-human-miss']
        self.assertEqual(self.choose()['selected_arm'], 'stratified')
        self.reports['stratified']['human_misses'] = ['synthetic-human-miss']
        decision = self.choose()
        self.assertFalse(decision['passed'])
        self.assertIsNone(decision['selected'])
        self.assertFalse(decision['automatic_extension'])

    def test_each_safety_gate_prevents_high_macro_candidate_from_winning(self):
        mutations = [
            lambda r: r['per_action']['human'].update(recall=.9),
            lambda r: r['per_action']['clarify'].update(recall=.7),
            lambda r: r.update(false_refusals=['synthetic-false-refusal']),
            lambda r: r.update(unavailable_knowledge_retrievals=['synthetic-unavailable-kb']),
            lambda r: r.update(action_tool_joint_accuracy=.8),
            lambda r: r.update(status_tool_accuracy=.8),
            lambda r: r.update(unauthenticated_tool_actions=['synthetic-preauth-tool']),
            lambda r: r.update(unavailable_tool_choices=['synthetic-unavailable-tool']),
            lambda r: r['cohorts']['current-service']['per_action']['human'].update(recall=.9),
            lambda r: r['cohorts']['current-service'].update(human_misses=['synthetic-current-miss']),
            lambda r: r['cohorts']['current-service'].update(false_refusals=['synthetic-current-refusal']),
            lambda r: r['cohorts']['current-service'].update(unavailable_knowledge_retrievals=['synthetic-current-kb']),
            lambda r: r['cohorts']['current-service'].update(action_tool_joint_accuracy=.8),
        ]
        for index, mutate in enumerate(mutations):
            reports = deepcopy(self.reports)
            reports['stratified']['macro_f1'] = .99
            mutate(reports['stratified'])
            with self.subTest(gate=index):
                self.assertEqual(self.choose(reports)['selected_arm'], 'uniform')

    def test_selection_rejects_diagnostic_holdout_nonfinite_or_stale_reports(self):
        for mutation in (lambda r: r.update(partition='final'), lambda r: r.update(partition='calibration'),
                         lambda r: r.update(macro_f1=float('nan')),
                         lambda r: r.update(action_tool_joint_accuracy=float('inf')),
                         lambda r: r.update(data_sha256='a' * 64),
                         lambda r: r.update(prompt_sha256='b' * 64),
                         lambda r: r.update(protocol_sha256='c' * 64)):
            reports = deepcopy(self.reports)
            mutation(reports['uniform'])
            with self.assertRaises(ValueError):
                self.choose(reports)
        reports = deepcopy(self.reports)
        reports['uniform-step-200'] = reports.pop('uniform')
        with self.assertRaises(ValueError):
            self.choose(reports)


class ProbePrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.summary = dict(status='complete', steps_per_arm=25, total_optimizer_steps=50,
                            evaluation_rows_used=0, probe_adapter_used_for_main=False,
                            adapters_discarded_from_training_use=True, real_pause_resume_verified=True,
                            common_binding_sha256='common', protocol_sha256='hash',
                            artifacts={'synthetic-proof': 'hash'})

    def verify(self, summary, alive=False):
        def read(path):
            values = {'probe-summary.json': summary, 'protocol.json': {'common_binding_sha256': 'common'},
                      'completion.json': {'probe_summary_sha256': 'hash'}, 'status.json': {'pid': 123}}
            return values[Path(path).name]
        with patch.object(cycle, 'read', side_effect=read), patch.object(cycle, 'sha', return_value='hash'), \
             patch.object(cycle, 'probe_artifacts', return_value={'synthetic-proof': 'hash'}), \
             patch.object(cycle, 'validate_probe_evidence'), patch.object(cycle, 'identity_alive', return_value=alive):
            return cycle.verify_probe('common')

    def test_main_requires_successful_matching_probe_with_exited_worker(self):
        self.assertEqual(self.verify(self.summary), 'hash')
        for key, value in (('status', 'paused'), ('steps_per_arm', 24), ('total_optimizer_steps', 49),
                           ('evaluation_rows_used', 1), ('probe_adapter_used_for_main', True),
                           ('adapters_discarded_from_training_use', False), ('real_pause_resume_verified', False),
                           ('common_binding_sha256', 'stale'), ('protocol_sha256', 'stale'),
                           ('artifacts', {})):
            bad = deepcopy(self.summary)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(bad)
        with self.assertRaises(ValueError):
            self.verify(self.summary, alive=True)
        with patch.object(cycle, 'read', side_effect=FileNotFoundError('synthetic absent probe')):
            with self.assertRaises(FileNotFoundError):
                cycle.verify_probe('common')

    def test_pause_evidence_requires_real_new_worker_and_exact_restored_states(self):
        run = cycle.Run(cycle.PROBE)
        evidence = dict(state='resumed', prior_worker_exited=True, protocol_sha256='hash',
                        arm='uniform', completed_step=12, resumed_next_step=13,
                        checkpoint_sha256='hash', checkpoint='synthetic/checkpoint',
                        prior_worker={'pid': 1}, saved_parameter_sha256='params',
                        saved_optimizer_sha256='optimizer', saved_rng_sha256='rng',
                        restore_record=dict(next_step=13, checkpoint_sha256='hash', worker={'pid': 2},
                            restored=dict(parameter_sha256='params', optimizer_sha256='optimizer', rng_sha256='rng')))
        def verify(value, logs=None):
            with patch.object(cycle, 'read', return_value=value), patch.object(cycle, 'sha', return_value='hash'), \
                 patch.object(cycle.ft, 'validate_checkpoint'), \
                 patch.object(cycle.ft, 'rows_file', return_value=[{'step': 13}] if logs is None else logs):
                return cycle.validate_probe_evidence(run, {'probe_pause_at_step': 12})
        self.assertEqual(verify(evidence), evidence)
        for key in ('parameter_sha256', 'optimizer_sha256', 'rng_sha256'):
            bad = deepcopy(evidence)
            bad['restore_record']['restored'][key] = 'not-restored'
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify(bad)
        bad = deepcopy(evidence)
        bad['restore_record']['worker'] = bad['prior_worker']
        with self.assertRaises(ValueError):
            verify(bad)
        with self.assertRaises(ValueError):
            verify(evidence, logs=[])


class PreprotocolRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = (Path(__file__).resolve().parents[1] / '.local'
                     / f'synthetic-preprotocol-{uuid.uuid4().hex}')
        self.root.mkdir(parents=True)
        self.root_patch = patch.object(cycle, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.cleanup)
        self.run = cycle.Run(cycle.PROBE)
        self.run.out.mkdir(parents=True)
        self.status = dict(stage='failed', run_name=self.run.name, interrupted_stage='checking_protocol',
                           requested_pause_at_step=12, pid=123, process_created=1.)
        (self.run.out / 'status.json').write_text(json.dumps(self.status), encoding='utf-8')

    def cleanup(self):
        # Only this uniquely owned synthetic fixture is traversed and removed.
        owned = self.root.resolve()
        for item in sorted(self.root.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if not item.resolve().is_relative_to(owned):
                raise AssertionError('Refuse cleanup outside synthetic fixture')
            if item.is_dir():
                item.rmdir()
            else:
                item.unlink()
        self.root.rmdir()

    def recover(self, resume=True, live=False):
        with patch.object(cycle, 'alive', return_value=live), \
             patch.object(cycle, 'identity_alive', return_value=live):
            return cycle.recover_preprotocol(self.run, resume, self.status)

    def test_explicit_resume_can_retry_only_preprotocol_failure_and_preserves_status_evidence(self):
        self.assertTrue(self.recover())
        evidence = list(self.run.out.glob('preprotocol-failure-*.json'))
        self.assertEqual(len(evidence), 1)
        self.assertIn('failed', evidence[0].read_text(encoding='utf-8'))
        self.assertFalse((self.run.out / 'protocol.json').exists())
        self.assertFalse(self.run.checkpoints.exists())

    def test_no_silent_fresh_restart_or_live_worker_recovery(self):
        for resume, live in ((False, False), (True, True)):
            with self.subTest(resume=resume, live=live), self.assertRaises(ValueError):
                self.recover(resume=resume, live=live)

    def test_recovery_requires_matching_run_status_and_original_probe_trigger(self):
        original = deepcopy(self.status)
        for key, value in (('run_name', cycle.DEFAULT), ('stage', 'training'),
                           ('requested_pause_at_step', None), ('requested_pause_at_step', 25)):
            self.status = deepcopy(original)
            self.status[key] = value
            (self.run.out / 'status.json').write_text(json.dumps(self.status), encoding='utf-8')
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.recover()
        self.status = deepcopy(original)
        changed = dict(original, error='changed after status read')
        (self.run.out / 'status.json').write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.recover()

    def test_training_evaluation_checkpoint_cache_or_unknown_residue_blocks_retry(self):
        markers = [self.run.out / 'arms/uniform/train.jsonl',
                   self.run.out / 'development/base/predictions.jsonl',
                   self.run.out / 'unexpected.json',
                   self.run.checkpoints / 'uniform/step-12/checkpoint.json',
                   self.run.cache / 'uniform/encoded.json']
        for marker in markers:
            with self.subTest(marker=marker.relative_to(self.root)):
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text('synthetic residual evidence', encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.recover()
                self.assertEqual(marker.read_text(encoding='utf-8'), 'synthetic residual evidence')
                marker.unlink()
                # Remove only the directories just introduced by this subtest.
                directory = marker.parent
                while directory not in (self.run.out, self.root) and directory.exists():
                    if any(directory.iterdir()):
                        break
                    directory.rmdir()
                    directory = directory.parent


if __name__ == '__main__':
    unittest.main()
