"""Synthetic CPU-only sampling invariants; no evaluation or model fixtures."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch
import uuid

from qwenlab import financial_sampling_plan as sampling
from qwenlab.financial_sampling_plan import CapacityError, QUOTAS, layer_of, main, plan


def sample(layer, number, group=None):
    cohort, input_layer = {
        'current-node': ('current-service', 'node-projection'),
        'current-component': ('current-service', 'component-message-only'),
        'planned': ('planned-retrieval', 'planned-capability-component'),
        'preauth': ('preauth-robustness', 'preauth-component'),
    }[layer]
    return dict(id=f'{layer}-{number:04d}', scene_family_id=group or f'{layer}-g{number:04d}',
                split='train', training_eligible=False, cohort=cohort, input_layer=input_layer,
                annotation=dict(action='tool' if number % 3 == 0 else 'answer',
                                tool_name='queryMyApplications' if number % 3 == 0 else None))


def pool(size=300):
    return [sample(layer, index) for layer in QUOTAS for index in range(size)]


def flatten(result):
    return [rid for step in result['step_rows'] for rid in step]


class SamplingPlanTests(unittest.TestCase):
    def test_default_budget_steps_and_counts_are_reproducible_without_mutation(self):
        rows = pool(400)
        before = deepcopy(rows)
        result = plan(rows, 'stratified', 41)
        self.assertEqual(result, plan(list(reversed(rows)), 'stratified', 41))
        self.assertEqual(rows, before)
        self.assertEqual(len(result['step_rows']), 400)
        self.assertTrue(all(len(step) == 8 for step in result['step_rows']))
        self.assertEqual(result['total_exposures'], 3200)
        self.assertEqual(sum(result['counts']['row'].values()), 3200)
        self.assertEqual(sum(result['counts']['group'].values()), 3200)
        self.assertEqual(sum(result['counts']['tool'].values()), result['counts']['action']['tool'])
        self.assertLessEqual(result['coverage']['row']['max_exposure'], 4)
        self.assertLessEqual(result['coverage']['group']['max_exposure'], 16)
        self.assertEqual(result['training_started'], False)

    def test_every_consecutive_quota_block_has_exact_layers_and_cohorts(self):
        rows = pool(30)
        by_id = {r['id']: r for r in rows}
        sequence = flatten(plan(rows, 'stratified', 12, steps=10))
        for offset in range(0, len(sequence), 20):
            selected = [by_id[rid] for rid in sequence[offset:offset + 20]]
            self.assertEqual(Counter(layer_of(r) for r in selected), QUOTAS)
            self.assertEqual(Counter(r['cohort'] for r in selected),
                             {'current-service': 12, 'planned-retrieval': 5, 'preauth-robustness': 3})

    def test_uniform_is_full_pool_shuffle_without_quota_or_rejection_sampling(self):
        rows = [sample('current-component', i) for i in range(60)]
        result = plan(rows, 'uniform', 19, steps=5)
        expected = sorted(r['id'] for r in rows)
        random.Random(19).shuffle(expected)
        self.assertEqual(flatten(result), expected[:40])
        self.assertEqual(result['counts']['cohort']['current-service'], 40)
        self.assertIsNone(result['layer_quotas_per_block'])

    def test_uniform_restarts_with_independently_shuffled_complete_round(self):
        rows = [sample('current-component', i) for i in range(20)]
        result = plan(rows, 'uniform', 91, steps=5)
        rng = random.Random(91)
        first = sorted(r['id'] for r in rows)
        second = first.copy()
        rng.shuffle(first)
        rng.shuffle(second)
        self.assertEqual(flatten(result), first + second)
        self.assertEqual(set(result['counts']['row'].values()), {2})

    def test_uniform_fails_on_capped_draw_instead_of_skipping_or_resampling(self):
        rows = [sample('current-component', i, 'shared-large-group') for i in range(30)]
        rows += [sample('planned', i) for i in range(50)]
        with self.assertRaises(CapacityError) as caught:
            plan(rows, 'uniform', 5, steps=10, max_group_exposure=1)
        self.assertEqual(caught.exception.diagnostic['reason'], 'insufficient_total_capacity')
        with self.assertRaises(CapacityError) as caught:
            plan(rows, 'uniform', 5, steps=5, max_group_exposure=1)
        self.assertEqual(caught.exception.diagnostic['reason'], 'uniform_draw_exceeds_hard_cap')

    def test_different_seeds_change_order_but_not_frozen_stratified_counts(self):
        rows = pool(30)
        a, b = plan(rows, 'stratified', 4, steps=10), plan(rows, 'stratified', 5, steps=10)
        self.assertNotEqual(flatten(a), flatten(b))
        self.assertEqual(a['counts']['layer'], b['counts']['layer'])
        self.assertEqual(a['pool_sha256'], b['pool_sha256'])
        self.assertEqual(a['pool_sha256'], plan(rows, 'uniform', 4, steps=10)['pool_sha256'])

    def test_old_current_rows_are_component_without_node_claim(self):
        rows = pool(30)
        old = sample('current-component', 900)
        del old['input_layer']
        self.assertEqual(layer_of(old), 'current-component')
        rows.append(old)
        result = plan(rows, 'stratified', 3, steps=10)
        self.assertEqual(result['counts']['layer']['current-node'], 36)

    def test_source_groups_rotate_so_a_large_group_does_not_dominate(self):
        rows = [sample('current-node', 0, 'small')]
        rows += [sample('current-node', i + 1, 'large') for i in range(12)]
        rows += [sample('current-node', 30, 'third')]
        rows += [sample(layer, i) for layer in ('current-component', 'planned', 'preauth')
                 for i in range(10)]
        result = plan(rows, 'stratified', 4, steps=5, batch=4, max_row_exposure=5)
        self.assertEqual({g: result['counts']['group'][g] for g in ('small', 'large', 'third')},
                         {'small': 3, 'large': 3, 'third': 3})
        large_counts = [result['counts']['row'][r['id']] for r in rows
                        if r['scene_family_id'] == 'large']
        self.assertEqual(max(large_counts), 1)

    def test_shared_group_cap_across_layers_cannot_be_counted_once_per_layer(self):
        # Each layer independently appears sufficient, but 17 required slots all
        # draw on the same group whose total cap is only 16.
        rows = [sample(layer, i, 'cross-layer')
                for layer in ('current-node', 'planned', 'preauth') for i in range(9)]
        rows += [sample('current-component', i) for i in range(8)]
        with self.assertRaises(CapacityError) as caught:
            plan(rows, 'stratified', 2, steps=5, batch=4)
        self.assertEqual(caught.exception.diagnostic['reason'], 'hard_cap_exhausted_during_rotation')
        self.assertIn('cross-layer', caught.exception.diagnostic['exhausted_groups'])

    def test_successful_cross_layer_group_still_obeys_one_total_cap(self):
        rows = pool(20)
        rows[0]['scene_family_id'] = 'cross-layer'
        rows[40]['scene_family_id'] = 'cross-layer'
        result = plan(rows, 'stratified', 12, steps=10, max_group_exposure=2)
        self.assertLessEqual(result['counts']['group']['cross-layer'], 2)

    def test_insufficient_layer_or_global_capacity_fails_without_relaxing_caps(self):
        with self.assertRaises(CapacityError) as caught:
            plan(pool(1), 'uniform', 2, steps=5, batch=4)
        self.assertEqual(caught.exception.diagnostic['reason'], 'insufficient_total_capacity')
        rows = pool(20)
        rows = [r for r in rows if layer_of(r) != 'current-node']
        rows += [sample('current-node', 0)]
        with self.assertRaises(CapacityError) as caught:
            plan(rows, 'stratified', 2, steps=5, batch=4)
        self.assertEqual(caught.exception.diagnostic['layer'], 'current-node')

    def test_coverage_and_counts_include_zero_exposure_rows_groups_and_tools(self):
        rows = pool(40)
        result = plan(rows, 'stratified', 9, steps=5, batch=4)
        selected = set(flatten(result))
        self.assertEqual(set(result['counts']['row']), {r['id'] for r in rows})
        self.assertEqual(set(result['coverage']['row']['unseen']), {r['id'] for r in rows} - selected)
        self.assertEqual(result['coverage']['row']['seen'], len(selected))
        self.assertEqual(result['counts']['tool']['queryApplicationDetail'], 0)

    def test_first_200_step_accounting_is_frozen_from_the_same_full_sequence(self):
        result = plan(pool(400), 'stratified', 82)
        prefix = result['prefix_200_steps']
        self.assertEqual(prefix['steps'], 200)
        self.assertEqual(prefix['exposures'], 1600)
        expected = Counter(flatten(result)[:1600])
        self.assertEqual({k: v for k, v in prefix['counts']['row'].items() if v}, expected)
        self.assertEqual(prefix['counts']['layer'],
                         {'current-node': 720, 'current-component': 240, 'planned': 400, 'preauth': 240})

    def test_invalid_inputs_and_nontraining_rows_are_rejected(self):
        rows = pool(20)
        missing_split = deepcopy(rows)
        del missing_split[0]['split']
        with self.assertRaises(ValueError):
            plan(missing_split, 'uniform', 1, steps=5)
        for split in ('dev', 'calibration', 'final', 'candidate'):
            bad = deepcopy(rows)
            bad[0]['split'] = split
            with self.subTest(split=split), self.assertRaises(ValueError):
                plan(bad, 'uniform', 1, steps=5)
        for kwargs in ({'steps': 1}, {'steps': True}, {'batch': 0},
                       {'max_row_exposure': 0}, {'max_group_exposure': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                plan(rows, 'stratified', 1, **kwargs)
        for key, value in (('id', rows[1]['id']), ('scene_family_id', ''),
                           ('input_layer', 'invented-node-projection')):
            bad = deepcopy(rows)
            bad[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan(bad, 'uniform', 1, steps=5)

    def test_cli_reads_only_explicit_input_and_never_overwrites_output(self):
        root = Path(__file__).resolve().parents[1] / '.local' / f'sampling-test-{uuid.uuid4().hex}'
        root.mkdir(parents=True)
        source, output = root / 'train.json', root / 'plan.json'
        try:
            source.write_text(json.dumps(pool(20)), encoding='utf-8')
            arguments = ['--input', str(source), '--output', str(output), '--mode', 'stratified',
                         '--seed', '4', '--steps', '5', '--batch', '4']
            with patch('builtins.print'), patch.object(sampling, 'ROOT', root):
                main(arguments)
            original = output.read_bytes()
            with patch.object(sampling, 'ROOT', root):
                with self.assertRaises(FileExistsError):
                    main(arguments)
            self.assertEqual(output.read_bytes(), original)
            saved = json.loads(original)
            self.assertEqual(saved['source']['path'], 'train.json')
            self.assertFalse(Path(saved['source']['path']).is_absolute())
            self.assertEqual(saved['total_exposures'], 20)
            self.assertEqual(saved['model_api_requests'], 0)
        finally:
            for file in (source, output):
                if file.exists():
                    file.unlink()
            root.rmdir()

    def test_cli_rejects_outside_input_and_output_before_any_read(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'synthetic-path-scope'
        outside = root.parent / 'outside.json'
        for source, output in ((outside, root / 'plan.json'), (root / 'train.json', outside)):
            with self.subTest(source=source, output=output):
                with patch.object(sampling, 'ROOT', root), patch.object(Path, 'read_bytes') as read:
                    with self.assertRaisesRegex(ValueError, 'repository root'):
                        main(['--input', str(source), '--output', str(output),
                              '--mode', 'uniform', '--seed', '4'])
                    read.assert_not_called()

    def test_cli_snapshot_drift_is_rejected_without_creating_output(self):
        root = Path(__file__).resolve().parents[1] / '.local' / f'sampling-drift-{uuid.uuid4().hex}'
        root.mkdir(parents=True)
        source, output = root / 'train.json', root / 'plan.json'
        try:
            raw = json.dumps(pool(20)).encode('utf-8')
            changed = raw + b'\n'
            source.write_bytes(raw)
            with patch.object(sampling, 'ROOT', root), \
                 patch.object(Path, 'read_bytes', side_effect=[raw, changed]) as read:
                with self.assertRaisesRegex(ValueError, 'changed during planning'):
                    main(['--input', str(source), '--output', str(output),
                          '--mode', 'stratified', '--seed', '4', '--steps', '5', '--batch', '4'])
                self.assertEqual(read.call_count, 2)
            self.assertFalse(output.exists())
        finally:
            source.unlink()
            root.rmdir()


if __name__ == '__main__':
    unittest.main()
