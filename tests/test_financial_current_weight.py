"""Numerical CPU checks, including a separate-process optimizer/RNG resume.

The tiny classifier is not Qwen; these tests do not replace the real GPU probe.
"""
import copy
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

import torch

from qwenlab import financial_current_weight as cw


@contextmanager
def local_test_folder():
    # Windows sandbox accounts cannot reopen the owner-only ACL used by mkdtemp.
    root = (cw.ROOT / 'tmp').resolve()
    path = root / ('weight-test-' + uuid.uuid4().hex)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        if path.resolve().parent != root or path.is_symlink():
            raise ValueError('Unexpected cleanup target')
        for name in ('state.pt', 'resumed.pt'):
            (path / name).unlink(missing_ok=True)
        path.rmdir()


def toy_rows():
    return [dict(id=str(i), split='train', cohort=cohort, input_layer=layer)
            for i, (cohort, layer) in enumerate([
                ('current-service', 'node-projection'),
                ('current-service', 'component-message-only'),
                ('planned-retrieval', 'planned-capability-component'),
                ('preauth-robustness', 'preauth-component'),
            ])]


def fixture(count=8):
    return [dict(action=dict(x=[i / 10, .5, -.2], target=i % 3),
                 tool=dict(x=[-.3, i / 7, .1], target=(i + 1) % 3) if i % 3 == 0 else None)
            for i in range(count)]


def model(dropout=0.):
    return torch.nn.Sequential(torch.nn.Linear(3, 5), torch.nn.Tanh(),
                               torch.nn.Dropout(dropout), torch.nn.Linear(5, 3)).double()


def scorer(tokenizer, net, items):
    return list(net(torch.tensor([item['x'] for item in items], dtype=torch.float64)).unbind())


def run_update(net, opt, block, weights):
    opt.zero_grad(set_to_none=True)
    for start in range(0, len(block), 2):
        cw.weighted_micro_backward(None, net, block[start:start + 2], weights[start:start + 2],
                                   len(block), scorer=scorer)
    opt.step()


def resume_worker(folder):
    folder = Path(folder)
    saved = torch.load(folder / 'state.pt', weights_only=False)
    cw.validate_resume(saved['binding'], saved['preparation'], 1)
    net = model(.2)
    net.load_state_dict(saved['model'])
    opt = torch.optim.AdamW(net.parameters(), lr=.003)
    opt.load_state_dict(saved['optimizer'])
    torch.set_rng_state(saved['rng'])
    for _ in range(2):
        run_update(net, opt, fixture(6), [1.5, 1.5, .5, .5, 1.5, .5])
    torch.save(dict(model=net.state_dict(), optimizer=opt.state_dict(), rng=torch.get_rng_state()),
               folder / 'resumed.pt')


class WeightTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(12)

    def test_pool_mean_and_two_epoch_membership(self):
        weights, summary = cw.weight_plan(toy_rows(), [['0', '1', '2', '3']] * 2, cw.RAW_WEIGHTS)
        self.assertEqual(list(weights.values()), [1.5, 1.5, .5, .5])
        self.assertEqual(sum(weights.values()) / 4, 1)
        self.assertEqual(summary['objective_mass_share']['current-node'], .375)

    def test_wrong_split_duplicate_id_or_unknown_layer_rejected(self):
        for field, value in [('split', 'development'), ('id', '1'), ('cohort', 'unknown')]:
            rows = toy_rows(); rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                cw.weight_plan(rows, [['0', '1', '2', '3']] * 2, cw.RAW_WEIGHTS)

    def test_total_exposure_does_not_replace_per_epoch_check(self):
        with self.assertRaises(ValueError):
            cw.weight_plan(toy_rows(), [['0', '0', '1', '1'], ['2', '2', '3', '3']], cw.RAW_WEIGHTS)

    def test_weight_sweep_not_accepted(self):
        weights = dict(cw.RAW_WEIGHTS, planned=2)
        with self.assertRaises(ValueError):
            cw.weight_plan(toy_rows(), [['0', '1', '2', '3']] * 2, weights)

    def compare_to_reference(self, n, chunks, weights, with_tools=True):
        block = fixture(n)
        if not with_tools:
            for row in block: row['tool'] = None
        net = model(); ref = copy.deepcopy(net)
        loss = 0.; count = 0; start = 0
        for size in chunks:
            out = cw.weighted_micro_backward(None, net, block[start:start + size],
                    weights[start:start + size], n, scorer=scorer)
            loss += out['loss']; count += out['true_tools']; start += size
        self.assertEqual(start, n)
        terms = []
        for row, weight in zip(block, weights):
            a = scorer(None, ref, [row['action']])[0]
            term = torch.nn.functional.cross_entropy(a[None, :], torch.tensor([row['action']['target']]))
            if row['tool'] is not None:
                t = scorer(None, ref, [row['tool']])[0]
                term = term + .75 * torch.nn.functional.cross_entropy(t[None, :], torch.tensor([row['tool']['target']]))
            terms.append(term * weight)
        expected = sum(terms) / n
        expected.backward()
        self.assertAlmostEqual(loss, expected.item(), places=12)
        self.assertEqual(count, sum(row['tool'] is not None for row in block))
        for a, b in zip(net.parameters(), ref.parameters()):
            torch.testing.assert_close(a.grad, b.grad, rtol=1e-12, atol=1e-12)
        return loss

    def test_weighted_microbatch_matches_whole_batch_gradient(self):
        self.compare_to_reference(8, [2, 2, 2, 2], [1.5, .5] * 4)

    def test_final_six_rows_use_six_denominator(self):
        self.compare_to_reference(6, [2, 2, 2], [1.5, .5] * 3)

    def test_unequal_microbatches_match_reference(self):
        self.compare_to_reference(6, [1, 2, 3], [1.5, .5] * 3)

    def test_no_tool_rows(self):
        self.compare_to_reference(6, [2, 2, 2], [1.5, .5] * 3, with_tools=False)

    def test_all_unit_weights_match_old_row_loss_formula(self):
        self.compare_to_reference(8, [2, 2, 2, 2], [1.] * 8)

    def test_single_row_weight_is_not_normalized_away(self):
        a = self.compare_to_reference(1, [1], [2.])
        torch.manual_seed(12)
        b = self.compare_to_reference(1, [1], [1.])
        self.assertAlmostEqual(a, 2 * b, places=12)

    def test_invalid_weights_and_batch_sizes(self):
        for weights, batch in [([0.], 1), ([float('nan')], 1), ([float('inf')], 1),
                               ([True], 1), ([], 1), ([1.], 0), ([1.], 9), ([1.], True)]:
            with self.subTest(weights=weights, batch=batch), self.assertRaises(ValueError):
                cw.weighted_micro_backward(None, model(), fixture(1), weights, batch, scorer=scorer)

    def test_nonfinite_and_missing_scores_stop(self):
        def nonfinite(_, net, items):
            return [net(torch.ones(3, dtype=torch.float64)) * float('nan') for _ in items]
        with self.assertRaises(FloatingPointError):
            cw.weighted_micro_backward(None, model(), fixture(1), [1.], 1, scorer=nonfinite)
        with self.assertRaises(ValueError):
            cw.weighted_micro_backward(None, model(), fixture(1), [1.], 1, scorer=lambda *args: [])

    def test_resume_rejects_changed_weight_schedule_or_cursor(self):
        prep = dict(weighting=dict(steps=3, weighted_rows_sha256='weights', step_rows_sha256='schedule'))
        saved = cw.checkpoint_binding(prep, 1)
        cw.validate_resume(saved, prep, 1)
        for key in ('weighted_rows_sha256', 'step_rows_sha256'):
            changed = copy.deepcopy(prep); changed['weighting'][key] = 'other'
            with self.assertRaises(ValueError): cw.validate_resume(saved, changed, 1)
        with self.assertRaises(ValueError): cw.validate_resume(saved, prep, 2)

    def test_cpu_cross_process_optimizer_and_rng_resume(self):
        prep = dict(weighting=dict(steps=3, weighted_rows_sha256='weights', step_rows_sha256='schedule'))
        net = model(.2); opt = torch.optim.AdamW(net.parameters(), lr=.003)
        block, weights = fixture(6), [1.5, 1.5, .5, .5, 1.5, .5]
        run_update(net, opt, block, weights)
        with local_test_folder() as temp:
            path = Path(temp)
            torch.save(dict(model=net.state_dict(), optimizer=opt.state_dict(), rng=torch.get_rng_state(),
                            preparation=prep, binding=cw.checkpoint_binding(prep, 1)), path / 'state.pt')
            for _ in range(2): run_update(net, opt, block, weights)
            expected_rng = torch.get_rng_state()
            result_process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), '--resume-worker', str(temp)],
                capture_output=True, timeout=120)
            self.assertEqual(result_process.returncode, 0, result_process.stderr.decode(errors='replace'))
            result = torch.load(path / 'resumed.pt', weights_only=False)
            for key, value in net.state_dict().items():
                torch.testing.assert_close(value, result['model'][key], rtol=0, atol=0)
            for key, state in opt.state_dict()['state'].items():
                for name, value in state.items():
                    torch.testing.assert_close(value, result['optimizer']['state'][key][name], rtol=0, atol=0)
            torch.testing.assert_close(expected_rng, result['rng'], rtol=0, atol=0)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--resume-worker':
        torch.set_num_threads(1)
        resume_worker(sys.argv[2])
    else:
        unittest.main()
