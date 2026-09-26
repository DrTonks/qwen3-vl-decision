import unittest
import torch
from torch import nn
from qwenlab.candidate_benchmark import CandidateHead, temporary_head


class CandidateHeadTests(unittest.TestCase):
    def test_projection_matches_selected_vocabulary_in_requested_order(self):
        torch.manual_seed(42)
        for bias in (False, True):
            head = nn.Linear(12, 19, bias=bias).double()
            hidden = torch.randn(2, 1, 12, dtype=torch.float64)
            ids = [9, 0, 18, 3]
            torch.testing.assert_close(CandidateHead(head, ids)(hidden), head(hidden)[..., ids], atol=1e-12, rtol=1e-12)

    def test_head_restores_even_on_failure(self):
        base = nn.Module(); original = nn.Linear(3, 4); base.lm_head = original
        with self.assertRaises(RuntimeError):
            with temporary_head(base, CandidateHead(original, [2, 0])):
                raise RuntimeError('simulated forward failure')
        self.assertIs(base.lm_head, original)

    def test_invalid_candidates_fail(self):
        for ids in ([], [1, 1], [-1], [4]):
            with self.assertRaises(ValueError):
                CandidateHead(nn.Linear(3, 4), ids)


if __name__ == '__main__':
    unittest.main()
