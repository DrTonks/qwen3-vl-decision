"""Synthetic-only CPU schedule/accounting tests; no real pool, tokenizer or weights."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid
import unittest
from unittest.mock import patch, Mock

from qwenlab import financial_sampling_freeze as freeze


@contextmanager
def synthetic_directory():
    parent = Path(__file__).resolve().parents[1] / '.local'
    folder = parent / ('sampling-freeze-test-' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        assert folder.resolve().is_relative_to(parent.resolve())
        for path in sorted(folder.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if path.is_file(): path.unlink()
            elif path.is_dir(): path.rmdir()
        folder.rmdir()


def sample(layer, number):
    cohort, boundary = {
        'current-node': ('current-service', 'node-projection'),
        'current-component': ('current-service', 'component-message-only'),
        'planned': ('planned-retrieval', 'planned-capability-component'),
        'preauth': ('preauth-robustness', 'preauth-component'),
    }[layer]
    tool = number % 3 == 0 and layer != 'preauth'
    return dict(id=f'{layer}-{number:04d}', scene_family_id=f'{layer}-g{number // 2:04d}',
                split='train', training_eligible=False, cohort=cohort, input_layer=boundary,
                input={'message': f'synthetic-only-{number}'},
                annotation=dict(action='tool' if tool else 'answer',
                                tool_name='queryMyApplications' if tool else None))


def pool():
    return [sample(layer, i) for layer in freeze.sampler.LAYERS for i in range(900)]


def config():
    return dict(version='financial-sampling-study-v1', status='design_cpu_preflight_only',
                training_enabled=False, deployment_enabled=False, model_api_requests=0,
                model='Qwen/Qwen3.5-0.8B', initial_adapter=None, seed=20261004,
                sampling_seed=20261004, steps_per_arm=400, effective_batch=8,
                micro_batch=2, gradient_accumulation=4, max_input_tokens=2048,
                truncate=False, padding_side='left', arms=['uniform', 'stratified'],
                diagnostic_steps=[200], selection_steps=[400],
                pool='data/pool', schedule_directory='data/schedule',
                sampling=dict(quotas_per_20=freeze.sampler.QUOTAS.copy(),
                              max_row_exposure=4, max_group_exposure=16),
                loss=dict(action_weight=1.0, tool_weight=0.75))


def fake_encode(tokenizer, row, task='action', max_tokens=2048):
    size = 20 + int(row['id'].rsplit('-', 1)[1]) % 7 + (10 if task == 'tool' else 0)
    return {'tokens': {'input_ids': list(range(size))}}


class AccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = pool()
        cls.config = config()
        with patch.object(freeze.prompt, 'encode', side_effect=fake_encode):
            cls.values = freeze.calculate(cls.rows, cls.config, object())

    def test_fixed_two_arm_budget_ledger_binding_and_occurrences(self):
        values = self.values
        self.assertEqual(set(values), freeze.FILES)
        by_id = {r['id']: r for r in self.rows}
        for arm in freeze.ARMS:
            records = values['exposure-ledger.json']['arms'][arm]
            self.assertEqual(len(records), 3200)
            counts = {}
            for i, record in enumerate(records):
                counts[record['row_id']] = counts.get(record['row_id'], 0) + 1
                self.assertEqual(record['exposure_index'], i + 1)
                self.assertEqual(record['step'], i // 8 + 1)
                self.assertEqual(record['microbatch'], i % 8 // 2 + 1)
                self.assertEqual(record['position'], i % 2 + 1)
                self.assertEqual(record['effective_batch_position'], i % 8 + 1)
                self.assertEqual(record['occurrence'], counts[record['row_id']])
                self.assertEqual(record['row_sha256'], freeze.row_sha(by_id[record['row_id']]))
            self.assertLessEqual(max(counts.values()), 4)
        self.assertEqual(values['uniform-plan.json']['coverage']['row']['max_exposure'], 1)
        self.assertEqual(values['stratified-plan.json']['counts']['layer'],
                         {'current-node':1440,'current-component':480,'planned':800,'preauth':480})

    def test_prefix_is_same_schedule_and_weighting_uses_original_rows(self):
        summary = self.values['summary.json']
        for arm in freeze.ARMS:
            for scope, expected_n in [('prefix_200', 1600), ('full_400', 3200)]:
                value = summary['arms'][arm][scope]
                t = value['true_tool_exposures']
                self.assertEqual(value['original_row_exposures'], expected_n)
                self.assertEqual(value['supervised_tasks'], expected_n + t)
                self.assertEqual(value['supervised_weight'], expected_n + .75 * t)
                self.assertEqual(value['repeated_row_exposures'], expected_n - value['unique_rows'])
                self.assertEqual(value['raw_input_tokens']['total'],
                                 value['raw_input_tokens']['action'] + value['raw_input_tokens']['tool'])
                self.assertGreaterEqual(value['padded_input_tokens']['total'], value['raw_input_tokens']['total'])
        self.assertEqual(summary['arms']['stratified']['prefix_200']['layer_counts'],
                         {'current-node':720,'current-component':240,'planned':400,'preauth':240})

    def test_separate_padding_uses_original_microbatch_not_global_tool_repacking(self):
        rows = [sample('current-node', i) for i in range(4)]
        # First microbatch: one tool; second microbatch: one tool. Tool lengths
        # differ greatly and must not be re-padded as a combined two-tool batch.
        rows[1]['annotation'] = {'action':'answer','tool_name':None}
        rows[2]['annotation'] = {'action':'answer','tool_name':None}
        plans = {arm: {'step_rows':[[r['id'] for r in rows]]} for arm in freeze.ARMS}
        records = freeze.build_ledger(rows, plans, 2)['arms']['uniform']
        lengths = {r['id']: {'action_input_tokens':a, 'tool_input_tokens':t}
                   for r, a, t in zip(rows, [3,7,9,5], [11,None,None,21])}
        result = freeze.arm_summary(records, {r['id']:r for r in rows}, lengths, 2)
        self.assertEqual(result['raw_input_tokens'], {'action':24,'tool':32,'total':56})
        self.assertEqual(result['padded_input_tokens'], {'action':32,'tool':32,'total':64})
        self.assertEqual(result['supervised_tasks'], 6)
        self.assertEqual(result['supervised_weight'], 5.5)

    def test_all_pool_actions_and_only_true_tools_are_encoded(self):
        rows = self.rows[:4]
        with patch.object(freeze.prompt, 'encode', side_effect=fake_encode) as encode:
            result = freeze.token_lengths(rows, object())
        self.assertEqual(encode.call_count, len(rows) + sum(r['annotation']['action']=='tool' for r in rows))
        self.assertEqual(len(result['rows']), len(rows))
        self.assertIsNone(result['rows'][1]['tool_input_tokens'])
        self.assertFalse(result['truncated'])
        self.assertTrue(all(c.kwargs['max_tokens']==2048 for c in encode.call_args_list))

    def test_overlength_fails_instead_of_truncating_and_metadata_tamper_rejected(self):
        with patch.object(freeze.prompt, 'encode', return_value={'tokens':{'input_ids':[0]*2049}}):
            with self.assertRaises(ValueError):
                freeze.token_lengths(self.rows[:1], object())
        original = self.values['token-lengths.json']
        for mutate in (lambda v: v['rows'].pop(),
                       lambda v: v['rows'][0].update(row_sha256='0'*64),
                       lambda v: v['rows'][0].update(action_input_tokens=True),
                       lambda v: v['rows'][0].update(action_input_tokens=2049),
                       lambda v: v.update(truncated=True)):
            altered = deepcopy(original); mutate(altered)
            with self.assertRaises(ValueError):
                freeze.validate_lengths(self.rows, altered, 2048)

    def test_uniform_does_not_cycle_when_pool_too_small(self):
        with self.assertRaisesRegex(ValueError, 'without replacement'):
            freeze.build_plans(self.rows[:3199], self.config)

    def test_nontrain_or_enabled_pool_rejected(self):
        for field, value in [('split','final'), ('training_eligible',True)]:
            rows = deepcopy(self.rows[:1]); rows[0][field] = value
            with self.assertRaises(ValueError):
                freeze.validate_rows(rows)


class SyntheticPublicationTests(unittest.TestCase):
    def setUp(self):
        # These fixtures never read a real training or evaluation example.
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = self.stack.enter_context(synthetic_directory())
        self.out = self.root / 'data/schedule'
        self.config_path = self.root / 'configs/study.json'
        self.config_path.parent.mkdir(parents=True)
        self.config_path.write_bytes(freeze.json_bytes(config()))
        self.dependency = self.root / 'dependency.txt'
        self.dependency.write_text('synthetic-v1', encoding='utf-8')
        for name, value in [('ROOT',self.root),('OUT',self.out),('CONFIG',self.config_path),
                            ('TOKENIZER',self.root/'models/synthetic-tokenizer')]:
            self.stack.enter_context(patch.object(freeze,name,value))
        self.stack.enter_context(patch.object(freeze.data,'OUT',self.root/'data/pool'))
        self.stack.enter_context(patch.object(freeze.data,'verify',return_value=pool()))
        self.stack.enter_context(patch.object(freeze,'runtime_versions',return_value={'transformers':'synthetic','tokenizers':'synthetic'}))
        self.loader = self.stack.enter_context(patch.object(freeze,'local_tokenizer',return_value=object()))
        self.encoder = self.stack.enter_context(patch.object(freeze.prompt,'encode',side_effect=fake_encode))
        self.stack.enter_context(patch.object(freeze,'source_bindings',side_effect=self.bindings))

    def bindings(self):
        return {'configs/study.json':freeze.sha(self.config_path), 'dependency.txt':freeze.sha(self.dependency)}

    def rewrite_manifest_hash(self, filename):
        manifest = freeze.read(self.out/'manifest.json')
        manifest['files'][filename] = freeze.sha(self.out/filename)
        (self.out/'manifest.json').write_bytes(freeze.json_bytes(manifest))

    def test_prepare_verify_and_tokenizer_replay_are_reproducible_and_design_only(self):
        result = freeze.prepare()
        self.assertFalse(result['training_enabled'])
        self.assertEqual({p.name for p in self.out.iterdir()}, freeze.FILES | {'manifest.json'})
        self.loader.reset_mock(); self.encoder.reset_mock()
        self.assertFalse(freeze.verify()['tokenizer_replayed'])
        self.loader.assert_not_called(); self.encoder.assert_not_called()
        self.assertTrue(freeze.verify(tokenize=True)['tokenizer_replayed'])
        self.loader.assert_called_once()
        manifest = freeze.read(self.out/'manifest.json')
        self.assertFalse(manifest['training_eligible'])
        self.assertFalse(manifest['model_weights_loaded'])
        self.assertEqual(manifest['model_api_requests'], 0)
        self.assertTrue(all(not Path(p).is_absolute() for p in manifest['sources']))

    def test_existing_output_never_overwritten(self):
        self.out.mkdir(parents=True)
        marker = self.out/'keep.txt'; marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            freeze.prepare()
        self.assertEqual(marker.read_text(), 'keep')
        self.loader.assert_not_called()

    def test_changed_sources_during_compute_publish_nothing(self):
        first = True
        def mutate(*args, **kwargs):
            nonlocal first
            if first:
                self.dependency.write_text('changed'); first = False
            return fake_encode(*args, **kwargs)
        self.encoder.side_effect = mutate
        with self.assertRaisesRegex(ValueError, 'Sources changed'):
            freeze.prepare()
        self.assertFalse(self.out.exists())

    def test_hash_valid_ledger_and_summary_forgery_still_fails_replay(self):
        freeze.prepare()
        path = self.out/'exposure-ledger.json'
        altered = freeze.read(path); altered['arms']['uniform'][0]['occurrence'] = 2
        path.write_bytes(freeze.json_bytes(altered)); self.rewrite_manifest_hash(path.name)
        with self.assertRaisesRegex(ValueError, 'ledger replay'):
            freeze.verify()

    def test_changed_dependency_and_extra_output_rejected(self):
        freeze.prepare()
        self.dependency.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'dependency closure'):
            freeze.verify()
        self.dependency.write_text('synthetic-v1')
        (self.out/'extra.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            freeze.verify()

    def test_actual_token_replay_catches_rehashed_length_forgery(self):
        freeze.prepare()
        path = self.out/'token-lengths.json'
        value = freeze.read(path); value['rows'][0]['action_input_tokens'] += 1
        path.write_bytes(freeze.json_bytes(value)); self.rewrite_manifest_hash(path.name)
        # Even a recomputed summary cannot conceal a different actual tokenizer.
        rows = freeze.data.verify()
        summary = freeze.build_summary(rows,freeze.read(self.out/'exposure-ledger.json'),value,config())
        (self.out/'summary.json').write_bytes(freeze.json_bytes(summary)); self.rewrite_manifest_hash('summary.json')
        self.assertEqual(freeze.verify()['status'], 'verified')
        with self.assertRaisesRegex(ValueError, 'tokenizer replay'):
            freeze.verify(tokenize=True)

    def test_config_cannot_enable_training_or_change_fixed_design(self):
        for key, value in [('training_enabled',True),('deployment_enabled',True),
                           ('sampling_seed',1),('truncate',True),('micro_batch',4)]:
            bad = config(); bad[key] = value
            with self.assertRaises(ValueError):
                freeze.check_config(bad)


class LocalLoaderAndClosureTests(unittest.TestCase):
    def test_local_loader_never_requests_weights_or_remote_code(self):
        tokenizer = Mock()
        auto = Mock(); auto.from_pretrained.return_value = tokenizer
        with patch.dict('sys.modules',{'transformers':Mock(AutoTokenizer=auto)}):
            self.assertIs(freeze.local_tokenizer(),tokenizer)
        auto.from_pretrained.assert_called_once_with(freeze.TOKENIZER,local_files_only=True,trust_remote_code=False)
        self.assertEqual(tokenizer.padding_side,'left')

    def test_tokenizer_inventory_binds_fallback_files_and_detects_new_optional_file(self):
        with synthetic_directory() as folder:
            root = Path(folder); model = root/'model'; model.mkdir()
            for name in freeze.TOKENIZER_REQUIRED:
                (model/name).write_text('synthetic')
            with patch.object(freeze,'ROOT',root), patch.object(freeze,'TOKENIZER',model):
                initial = {p.name for p in freeze.tokenizer_files()}
                self.assertEqual(initial,freeze.TOKENIZER_REQUIRED)
                for name in ('vocab.json','merges.txt'):
                    (model/name).write_text('synthetic-fallback')
                after = {p.name for p in freeze.tokenizer_files()}
                self.assertEqual(after,initial|{'vocab.json','merges.txt'})
                (model/'tokenizer.json').unlink()
                with self.assertRaises(ValueError):
                    freeze.tokenizer_files()


if __name__ == '__main__':
    unittest.main()
