from contextvars import copy_context
from types import SimpleNamespace
import unittest
import torch
from torch import nn
from qwenlab.candidate_inference import CandidateLinear, CandidateScorer
from qwenlab.progress import estimate


class ToyLM(nn.Module):
    def __init__(self):
        super().__init__(); self.embedding = nn.Embedding(19, 8); self.lm_head = nn.Linear(8, 19, bias=True)
        self.lm_head.weight = self.embedding.weight

    def forward(self, input_ids, attention_mask=None, logits_to_keep=1, use_cache=False):
        return SimpleNamespace(logits=self.lm_head(self.embedding(input_ids)[:, -logits_to_keep:]))


class CandidateInferenceTests(unittest.TestCase):
    def test_selected_logits_order_and_full_forward_unchanged(self):
        torch.manual_seed(1); model = ToyLM().eval(); inputs = {'input_ids': torch.tensor([[1, 3, 5]])}
        original_weight = model.lm_head.weight; original_keys = list(model.state_dict())
        reference = model(**inputs).logits.detach(); scorer = CandidateScorer(model)
        for ids in ([5, 0, 18, 7], [0, 1], [5, 0, 18, 7]):
            torch.testing.assert_close(scorer.scores(inputs, ids), reference[:, -1, ids])
        self.assertEqual(scorer.projection, 'candidate'); self.assertEqual(len(scorer.verified), 2)
        self.assertIs(model.embedding.weight, original_weight); self.assertIs(model.lm_head.weight, original_weight)
        self.assertEqual(list(model.state_dict()), original_keys)
        torch.testing.assert_close(model(**inputs).logits, reference)

    def test_exception_and_other_context_restore_full_head(self):
        head = CandidateLinear(nn.Linear(8, 19).eval()); hidden = torch.randn(1, 1, 8)
        context = copy_context()
        with torch.inference_mode():
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                with head.select([1, 4]):
                    self.assertEqual(head(hidden).shape[-1], 2)
                    self.assertEqual(context.run(head, hidden).shape[-1], 19)
                    raise RuntimeError('injected')
            self.assertEqual(head(hidden).shape[-1], 19)

    def test_cache_invalidates_for_updated_weight_and_bias(self):
        head = CandidateLinear(nn.Linear(4, 7).eval()); x = torch.randn(2, 1, 4)
        with torch.inference_mode():
            with head.select([1, 3]): head(x)
            head.weight.add_(2); head.bias.add_(1)
            expected = nn.functional.linear(x, head.weight, head.bias)[..., [1, 3]]
            with head.select([1, 3]): torch.testing.assert_close(head(x), expected)

    def test_inference_only_and_invalid_inputs(self):
        head = CandidateLinear(nn.Linear(4, 7).eval())
        with self.assertRaises(RuntimeError):
            with head.select([1, 2]): pass
        with torch.inference_mode():
            for ids in ([], [1, 1], [-1], [7], [1.2]):
                with self.assertRaises(ValueError):
                    with head.select(ids): pass
        scorer = CandidateScorer(ToyLM().eval())
        with self.assertRaises(ValueError): scorer.scores({'labels': torch.tensor([1])}, [1, 2])
        scorer.model.train()
        with self.assertRaises(RuntimeError): scorer.scores({'input_ids': torch.tensor([[1]])}, [1, 2])

    def test_startup_mismatch_falls_back(self):
        model = ToyLM().eval(); scorer = CandidateScorer(model); ids = [1, 2]
        original = scorer.head.forward
        def corrupt(hidden):
            value = original(hidden)
            if scorer.head._selection.get() is not None:
                value = value.clone(); value[..., 0] += 1000
            return value
        scorer.head.forward = corrupt
        x = {'input_ids': torch.tensor([[1, 2]])}
        actual = scorer.scores(x, ids)
        self.assertEqual(scorer.projection, 'full'); self.assertEqual(scorer.fallback_reason, 'startup_candidate_mismatch')
        torch.testing.assert_close(actual, model(**x).logits[:, -1, ids])

    def test_actual_tiny_qwen_text_forward_on_cpu(self):
        from transformers import Qwen3VLConfig, Qwen3VLForConditionalGeneration
        config = Qwen3VLConfig(text_config={'vocab_size': 32, 'hidden_size': 16, 'intermediate_size': 32,
            'num_hidden_layers': 1, 'num_attention_heads': 2, 'num_key_value_heads': 1, 'head_dim': 8,
            'rope_scaling': {'rope_type': 'default', 'mrope_section': [1, 1, 2], 'mrope_interleaved': True}},
            vision_config={'depth': 1, 'hidden_size': 16, 'intermediate_size': 32, 'out_hidden_size': 16,
                           'num_heads': 2, 'deepstack_visual_indexes': []})
        model = Qwen3VLForConditionalGeneration(config).eval()
        x = {'input_ids': torch.tensor([[1, 2, 3, 4]]), 'attention_mask': torch.ones(1, 4, dtype=torch.long)}
        with torch.inference_mode(): ref = model(**x, logits_to_keep=1, use_cache=False).logits[:, -1, [3, 9, 17]]
        scorer = CandidateScorer(model)
        torch.testing.assert_close(scorer.scores(x, [3, 9, 17]), ref)
        self.assertEqual(scorer.projection, 'candidate')

    def test_recent_step_eta(self):
        result = estimate([{'step': 10, 'elapsed_s': 51}, {'step': 30, 'elapsed_s': 151}], 100)
        self.assertEqual(result['seconds_per_step'], 5)
        self.assertEqual(result['remaining_training_s'], 350)
        self.assertEqual(result['progress_percent'], 30)
        self.assertIsNone(estimate([], 100))


if __name__ == '__main__': unittest.main()
