"""Opt-in inference projection, preserving the normal full-vocabulary path.

The replacement Linear shares the original Parameter objects and state-dict
keys. A context-local selector changes only the vocabulary rows for one call.
Training and old frozen experiments never import this module.
"""
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock

import torch
from torch import nn


class CandidateLinear(nn.Linear):
    def __init__(self, original, cache_size=16):
        if type(original) is not nn.Linear:
            raise TypeError('Requires an ordinary, unquantized nn.Linear output head')
        nn.Module.__init__(self)
        self.in_features = original.in_features; self.out_features = original.out_features
        self.weight = original.weight; self.bias = original.bias
        self.train(original.training)
        self._selection = ContextVar('candidate_token_ids', default=None)
        self._cache = OrderedDict(); self._cache_size = cache_size; self._lock = RLock()
        self._signature = None

    @contextmanager
    def select(self, ids):
        if self.training or torch.is_grad_enabled():
            raise RuntimeError('Candidate projection is inference-only; use eval and inference_mode')
        ids = tuple(ids)
        if not ids or any(type(i) is not int for i in ids) or len(ids) != len(set(ids)) or min(ids) < 0 or max(ids) >= self.out_features:
            raise ValueError('Candidates must be unique valid token IDs')
        token = self._selection.set(ids)
        try: yield
        finally: self._selection.reset(token)

    def forward(self, hidden):
        ids = self._selection.get()
        if ids is None: return nn.functional.linear(hidden, self.weight, self.bias)
        if self.training or torch.is_grad_enabled(): raise RuntimeError('Selected projection cannot train')
        def signature(p):
            return None if p is None else (p.data_ptr(), p._version, str(p.device), p.dtype)
        with self._lock:
            sig = (signature(self.weight), signature(self.bias))
            if sig != self._signature: self._cache.clear(); self._signature = sig
            if ids not in self._cache:
                index = torch.tensor(ids, device=self.weight.device)
                self._cache[ids] = (self.weight.detach().index_select(0, index),
                                    None if self.bias is None else self.bias.detach().index_select(0, index))
                if len(self._cache) > self._cache_size: self._cache.popitem(last=False)
            self._cache.move_to_end(ids); weight, bias = self._cache[ids]
        return nn.functional.linear(hidden, weight, bias)


class CandidateScorer:
    """Own a loaded eval model. Serialize calls and verify each candidate layout.

    On first use of each layout, compare against the full head on that input.
    A mismatch switches this scorer to full projection. This is a startup
    compatibility check, not proof of equivalence on every possible input.
    """
    def __init__(self, model, projection='candidate', probability_tolerance=1e-4):
        if model.training: raise ValueError('Call model.eval() before creating a scorer')
        if projection not in ('candidate', 'full'): raise ValueError(projection)
        self.model = model; self.projection = projection; self.tolerance = probability_tolerance
        self._lock = RLock(); self.verified = set(); self.fallback_reason = None
        self.base = model.get_base_model() if hasattr(model, 'get_base_model') else model
        if not hasattr(self.base, 'lm_head'): raise TypeError('Missing lm_head')
        self.head = None
        if projection == 'candidate':
            if isinstance(self.base.lm_head, CandidateLinear): self.head = self.base.lm_head
            else:
                try: self.head = CandidateLinear(self.base.lm_head)
                except TypeError:
                    self.projection = 'full'; self.fallback_reason = 'unsupported_output_head'
                else: self.base.lm_head = self.head

    @torch.inference_mode()
    def scores(self, inputs, ids):
        if self.model.training: raise RuntimeError('Model switched to train mode')
        if set(inputs) - {'input_ids', 'attention_mask', 'position_ids'}:
            raise ValueError('Validated text-only, cache-free interface; unsupported input fields')
        ids = tuple(ids)
        if not ids or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Invalid candidate IDs')
        with self._lock:
            def full():
                return self.model(**inputs, logits_to_keep=1, use_cache=False).logits[:, -1, list(ids)].float()
            if self.projection == 'full': return full()
            with self.head.select(ids):
                selected = self.model(**inputs, logits_to_keep=1, use_cache=False).logits[:, -1].float()
            if ids not in self.verified:
                reference = full()
                matches = torch.equal(selected.argmax(-1), reference.argmax(-1))
                delta = (selected.softmax(-1) - reference.softmax(-1)).abs().max().item()
                if not torch.isfinite(selected).all() or not matches or delta > self.tolerance:
                    self.projection = 'full'; self.fallback_reason = 'startup_candidate_mismatch'
                    return reference
                self.verified.add(ids)
            return selected
