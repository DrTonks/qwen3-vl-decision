"""Independent complete-coverage experiment: two epochs, actual partial batch.

Old frozen experiments are unchanged. CPU verification is explicitly self
verification, not an independent review. Real probe pause/resume is required.
"""
import argparse
from collections import Counter
import copy
import gc
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import time

from qwenlab.common import ROOT, sha
from qwenlab import financial_train as ft, qwen35_model as qm
from qwenlab import financial_sampling_freeze as parent_schedule
from qwenlab import financial_full_coverage_schedule as schedule
from qwenlab import financial_preauth_cycle as parent_cycle
from qwenlab import financial_sampling_cycle as numerical_parent
from qwenlab import financial_sampling_data as pool
from qwenlab import financial_service_v2_cycle as v2
from qwenlab import financial_service_v2_data as evaluation_data
from qwenlab import financial_service_v2_metrics as metrics
from qwenlab import financial_prompt_v2 as prompt


DEFAULT = 'financial-full-coverage-v1'
PROBE = 'financial-full-coverage-probe-v1'
CONFIG = ROOT / 'configs/financial-full-coverage-execution-v1.json'
DESIGN = ROOT / 'configs/financial-sampling-study-v1.json'
SCHEDULE_REVIEW = ROOT / 'docs/evidence/financial-state-pair-schedule-review.json'
REFERENCE = ROOT / 'results/financial-preauth-v1'
REVIEW = ROOT / 'docs/evidence/financial-full-coverage-executor-review.json'
LOCK = 'financial-eight-actions-gpu.lock'
ARMS = ('fullcover',)
REVIEW_FILES = [
    'src/qwenlab/financial_full_coverage_cycle.py',
    'tests/test_financial_full_coverage_cycle.py',
    'scripts/start-financial-full-coverage.ps1',
    'scripts/pause-financial-full-coverage.ps1',
    'scripts/resume-financial-full-coverage.ps1',
]
SOURCES = sorted(set(ft.SOURCES + REVIEW_FILES + ['src/qwenlab/financial_state_pair_cycle.py', 'src/qwenlab/financial_full_coverage_schedule.py'] + [
    'src/qwenlab/qwen35_model.py', 'src/qwenlab/financial_service_v2_cycle.py',
    'src/qwenlab/financial_service_v2_metrics.py', 'src/qwenlab/financial_service_v2_data.py',
    'src/qwenlab/financial_prompt_v2.py', 'src/qwenlab/financial_serve_v2.py',
    'src/qwenlab/financial_sampling_plan.py', 'src/qwenlab/financial_sampling_freeze.py',
    'src/qwenlab/financial_sampling_data.py', 'requirements-qwen35.txt',
    'configs/support-financial-v2.json', 'configs/financial-full-coverage-execution-v1.json', 'configs/financial-sampling-study-v1.json',
    'src/qwenlab/financial_sampling_cycle.py', 'src/qwenlab/financial_preauth_cycle.py', 'src/qwenlab/financial_full_coverage_schedule.py',
    'configs/qwen35-model-source.json',
]))
TERMINAL = {'complete', 'failed', 'paused'}
EVALUATION_STEPS = (500, 1000, 1500, 1673, 2000, 2500, 3000, 3346)
TOTAL_STEPS = 3346
read = v2.read
durable_json = v2.durable_json


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def relative(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Artifact path outside repository')
    return path.relative_to(ROOT.resolve()).as_posix()


def immutable_json(path, value):
    canonical = json.loads(json.dumps(value))
    if Path(path).exists():
        if read(path) != canonical:
            raise ValueError('Frozen result differs: ' + relative(path))
    else:
        durable_json(path, canonical)


class Run:
    def __init__(self, name=DEFAULT):
        if name not in (DEFAULT, PROBE):
            raise ValueError('Fixed independent sampling namespaces required')
        self.name = name
        self.probe = name == PROBE
        self.out = ROOT / 'results' / name
        self.control = ROOT / '.local/financial-full-coverage-v1' / (name + '-control.json')
        self.checkpoints = ROOT / '.local/checkpoints' / name
        self.cache = ROOT / '.local/cache' / name

    def protocol_hash(self):
        return sha(self.out / 'protocol.json')

    def status(self, stage, **values):
        import psutil
        durable_json(self.out / 'status.json', dict(
            stage=stage, run_name=self.name, probe=self.probe, updated_at=ft.now(),
            pid=os.getpid(), process_created=psutil.Process().create_time(),
            safe_to_shutdown=False, **values))


class ArmRun:
    """Explicit context for immutable v2 checkpoint helpers; no global patching."""
    def __init__(self, cycle, arm):
        if arm not in ARMS:
            raise ValueError('Unknown arm')
        self.cycle, self.arm = cycle, arm
        self.name = cycle.name + '-' + arm
        self.out = cycle.out / 'arms' / arm
        self.checkpoints = cycle.checkpoints / arm
        self.cache = cycle.cache / arm
        self.control = cycle.control

    def protocol_hash(self):
        return self.cycle.protocol_hash()

    def status(self, stage, **values):
        self.cycle.status(stage, arm=self.arm, **values)


def verify_review():
    value = read(REVIEW)
    if value.get('status') != 'pass' or value.get('independent') is not False or value.get('open_findings') != []:
        raise ValueError('Passing documented CPU verification required')
    expected = set(REVIEW_FILES + ['src/qwenlab/financial_full_coverage_schedule.py'])
    if set(value.get('files', {})) != expected:
        raise ValueError('Verification inventory differs')
    for name, expected_hash in value['files'].items():
        if sha(ROOT / name) != expected_hash:
            raise ValueError('CPU verification stale: ' + name)
    if value['config_sha256'] != sha(CONFIG) or value['schedule_manifest_sha256'] != sha(schedule.OUT / 'manifest.json'):
        raise ValueError('Config or schedule verification stale')
    return value


def runtime_binding():
    import torch
    names = sorted(set(ft.PACKAGES + ['tokenizers', 'huggingface-hub', 'safetensors', 'jinja2']))
    return dict(python=platform.python_version(), packages={n: metadata.version(n) for n in names},
                torch_cuda=torch.version.cuda, cudnn=torch.backends.cudnn.version(),
                gpu_name=torch.cuda.get_device_name(0),
                matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,
                cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
                cudnn_benchmark=torch.backends.cudnn.benchmark,
                deterministic_algorithms=torch.are_deterministic_algorithms_enabled())


def source_bindings():
    values = {name: sha(ROOT / name) for name in SOURCES}
    frozen = read(schedule.OUT / 'manifest.json')
    values.update(schedule.source_bindings())
    values[relative(SCHEDULE_REVIEW)] = sha(SCHEDULE_REVIEW)
    values[relative(REVIEW)] = sha(REVIEW)
    if frozen['sources'] != schedule.source_bindings(): raise ValueError('Schedule sources changed')
    for name in frozen['files']:
        values[relative(schedule.OUT / name)] = sha(schedule.OUT / name)
    values[relative(schedule.OUT / 'manifest.json')] = sha(schedule.OUT / 'manifest.json')
    # Verify rather than merely inherit the transitive schedule source claims.
    if any(sha(ROOT / name) != expected for name, expected in values.items()):
        raise ValueError('Frozen schedule/source closure changed')
    return values


def verify_model():
    source = read(ROOT / 'configs/qwen35-model-source.json')
    if source.get('repo_id') != 'Qwen/Qwen3.5-0.8B':
        raise ValueError('Wrong official base model')
    values = {}
    for entry in source['files']:
        path = (qm.MODEL / entry['Path']).resolve()
        if not path.is_relative_to(qm.MODEL.resolve()) or sha(path) != entry['Sha256']:
            raise ValueError('Official model bytes changed')
        values[relative(path)] = entry['Sha256']
    if not any(name.endswith('.safetensors') for name in values):
        raise ValueError('Missing official model weight inventory')
    return values


def evaluation_bindings():
    """Hash frozen evaluation bytes; never parse holdout examples before selection."""
    path = evaluation_data.OUT / 'evaluation-manifest.json'
    value = read(path)
    if (value['policy_sha256'] != prompt.POLICY_HASH
            or value['code_sha256'] != sha(Path(evaluation_data.__file__))
            or value['training_eligible'] is not False):
        raise ValueError('Evaluation manifest is stale')
    for name, expected in value['files'].items():
        if sha(evaluation_data.OUT / name) != expected:
            raise ValueError('Frozen evaluation bytes changed')
    return dict(manifest_sha256=sha(path), files=value['files'])


def check_design(cfg):
    if (cfg['version'] != 'financial-full-coverage-execution-v1' or cfg['epochs'] != 2
            or cfg['rows'] != 13378 or cfg['batch'] != 8 or cfg['steps_per_epoch'] != 1673
            or cfg['steps_per_arm'] != TOTAL_STEPS or tuple(cfg['evaluation_steps']) != EVALUATION_STEPS
            or cfg['model_api_requests'] != 0 or cfg['deployment_enabled'] is not False):
        raise ValueError('Fixed complete coverage design required')
    inherited = numerical_parent.check_design(read(DESIGN))
    inherited.update(arms=list(ARMS), execution_order=list(ARMS), steps_per_arm=TOTAL_STEPS,
        warmup_steps=cfg['warmup_steps'], learning_rate=cfg['learning_rate'],
        scheduler=dict(type='linear_warmup_then_linear_decay', total_steps=TOTAL_STEPS,
                       formula='lr(s)=5e-5*min(s/100,(3346-s+1)/3246)'),
        schedule_directory=relative(schedule.OUT), sampling=cfg,
        diagnostic_steps=list(EVALUATION_STEPS), selection_steps=list(EVALUATION_STEPS),
        selection_order=['original gates; macro_f1; joint_tool_accuracy; earlier_step'],
        stop_policy='maximum2 complete epochs; early stop only three persistent joint deteriorations after epoch1',
        executor_status='complete-coverage execution; CPU self verification explicitly recorded',
        probe=dict(required_before_main=True, steps_per_arm=25, total_steps=25,
                   train_only=True, discard_adapters=True, schedule='first25; full3346-stepLR'))
    return inherited


def reference_bindings():
    names = ['protocol.json', 'completion.json', 'arms/preauth/initialization.json']
    for variant in ('base', 'preauth-step-400'):
        names += ['development/' + variant + '/' + n for n in ('binding.json','metrics.json','timing.json','predictions.jsonl')]
    values = {relative(REFERENCE / n): sha(REFERENCE / n) for n in names}
    checkpoint = parent_cycle.ArmRun(parent_cycle.Run(), 'preauth').checkpoints / 'step-400/checkpoint.json'
    values[relative(checkpoint)] = sha(checkpoint)
    return values


def check_reference(common, evaluation, cfg):
    old = read(REFERENCE / 'protocol.json')
    completion = read(REFERENCE / 'completion.json')
    if (completion.get('status') != 'complete' or completion.get('protocol_sha256') != sha(REFERENCE / 'protocol.json')
            or old.get('prompt_sha256') != sha(Path(prompt.__file__)) or old.get('policy_sha256') != prompt.POLICY_HASH
            or old.get('evaluation') != evaluation or old.get('probe') is not False
            or old.get('arms') != ['preauth'] or old.get('steps_per_arm') != 400
            or completion.get('arm_steps') != {'preauth':400}):
        raise ValueError('Historical comparison protocol or evaluation mismatch')
    for key in ('model_files', 'runtime'):
        if old['common_binding'][key] != common[key]:
            raise ValueError('Historical model/runtime differs: ' + key)
    keys = ('model', 'initial_adapter', 'seed', 'effective_batch', 'micro_batch',
            'gradient_accumulation', 'learning_rate', 'warmup_steps', 'optimizer',
            'gradient_clipping', 'precision', 'lora', 'attention', 'gradient_checkpointing',
            'model_use_cache', 'torch_cpu_threads', 'loss', 'max_input_tokens', 'truncate',
            'padding_side', 'development_gate', 'current_service_additional_gate',
            'preauth_additional_gate', 'capability_additional_gate', 'calibration')
    if any(digest(old['config'][key]) != digest(cfg[key]) for key in keys):
        raise ValueError('Historical numerical design or gates differ')
    if common['historical_reference_sha256'] != reference_bindings():
        raise ValueError('Historical comparison artifacts changed')
    for variant in ('base', 'preauth-step-400'):
        binding = read(REFERENCE / 'development' / variant / 'binding.json')
        if binding != parent_cycle.eval_binding(parent_cycle.Run(), old, variant, 'development'):
            raise ValueError('Historical binding/checkpoint mismatch before GPU training')
    return old


def freeze(run, resume=False, pause_at_step=None):
    verify_review()
    schedule.verify()
    cfg = check_design(read(CONFIG))
    if pause_at_step is not None and (not run.probe or type(pause_at_step) is not int
                                     or pause_at_step != 12):
        raise ValueError('--pause-at-step must be12 for the frozen probe')
    existing = run.out / 'protocol.json'
    if existing.exists() != bool(resume):
        raise ValueError('Existing run requires --resume; fresh run must not use --resume')
    old = read(existing) if existing.exists() else None
    if old:
        if pause_at_step not in (None, old['probe_pause_at_step']):
            raise ValueError('Cannot change the frozen probe pause trigger')
        pause_at_step = old['probe_pause_at_step']
    if run.probe and pause_at_step != 12:
        raise ValueError('This protocol requires a real step12 pause and step13 resume')
    if run.probe and pause_at_step is None:
        raise ValueError('Probe requires an explicit real pause/resume step, e.g.12')
    sources = source_bindings()
    runtime = runtime_binding()
    models = verify_model()
    common = dict(source_sha256=sources, runtime=runtime, model_files=models,
                  review_sha256=sha(REVIEW), config_sha256=sha(CONFIG),
                  schedule_manifest_sha256=sha(schedule.OUT / 'manifest.json'),
                  historical_reference_sha256=reference_bindings())
    common_hash = digest(common)
    evaluation = evaluation_bindings()
    check_reference(common, evaluation, cfg)
    probe_summary_sha = None
    if not run.probe:
        probe_summary_sha = verify_probe(common_hash)
    protocol = dict(version='financial-full-coverage-execution-v1', run_name=run.name,
                    config=cfg, probe=run.probe, probe_pause_at_step=pause_at_step,
                    steps_per_arm=25 if run.probe else TOTAL_STEPS, arms=list(ARMS),
                    execution_permission=dict(training_enabled=True,
                        authorization='explicit_user_request_for_reviewed_sampling_training',
                        deployment_enabled=False, model_api_requests=0),
                    common_binding=common, common_binding_sha256=common_hash,
                    probe_summary_sha256=probe_summary_sha,
                    evaluation=None if run.probe else evaluation,
                    prompt_sha256=sha(Path(prompt.__file__)), policy_sha256=prompt.POLICY_HASH,
                    selection='predeclared development checkpoints; original gates; passing macroF1 then joint tool then earlier step; historical not eligible',
                    inference='predicted action then conditional predicted tool; no gold tool routing',
                    resume='exact frozen row-ID cursor; optimizer and Python/NumPy/torch/CUDA RNG restored',
                    probe_adapters_used_for_main=False)
    if sources != source_bindings() or runtime != runtime_binding():
        raise ValueError('Execution dependencies changed during freeze')
    if old is not None and old != protocol:
        raise ValueError('Execution protocol/source/runtime differs; resume refused')
    immutable_json(existing, protocol)
    return protocol


def learning_rate(step, cfg):
    total = cfg['steps_per_arm']
    if type(step) is not int or not 1 <= step <= total:
        raise ValueError('Step outside frozen complete coverage budget')
    return cfg['learning_rate'] * min(step / cfg['warmup_steps'], (total-step+1)/(total-cfg['warmup_steps']))


def validate_schedule(plan, rows, arm, cfg):
    if arm != 'fullcover' or rows != execution_rows():
        raise ValueError('Wrong complete coverage arm or input payload')
    return schedule.validate_plan(plan, rows, read(CONFIG))


def checkpoint_summary_binding(summary, protocol, arm, step):
    if (summary.get('step') != step or summary.get('arm') != arm
            or summary.get('schedule_manifest_sha256') != protocol['common_binding']['schedule_manifest_sha256']
            or summary.get('cursor') != dict(arm=arm, completed_steps=step, next_step=step + 1)
            or not isinstance(summary.get('initial_parameter_sha256'), str)
            or len(summary['initial_parameter_sha256']) != 64
            or summary.get('sample_positions') != sum(len(b) for b in read(schedule.OUT / 'plan.json')['step_rows'][:step])):
        raise ValueError('Checkpoint cursor/arm/schedule binding mismatch')
    return True


def nested_digest(value):
    """Value hash for tensor/NumPy RNG and optimizer states, not pickle identities."""
    h = hashlib.sha256()
    def walk(item):
        if isinstance(item, dict):
            h.update(b'dict')
            for key in sorted(item, key=lambda v: (type(v).__name__, str(v))):
                walk(key); walk(item[key])
        elif isinstance(item, (list, tuple)):
            h.update(type(item).__name__.encode()); h.update(str(len(item)).encode())
            for child in item: walk(child)
        elif hasattr(item, 'detach'):
            tensor = item.detach().cpu().contiguous()
            h.update(str(tensor.dtype).encode()); h.update(str(tuple(tensor.shape)).encode())
            # Adapter/optimizer tensors are FP32; use uint8 view for BF16 RNG-independent compatibility.
            import torch
            h.update(tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif hasattr(item, 'dtype') and hasattr(item, 'tobytes'):
            h.update(str(item.dtype).encode()); h.update(str(item.shape).encode()); h.update(item.tobytes())
        else:
            h.update((type(item).__name__ + ':' + repr(item)).encode())
    walk(value)
    return h.hexdigest()


def parameter_hash(model):
    import torch
    values = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
    if not values or any('lora_' not in n or '.language_model.' not in n or p.dtype != torch.float32
                         for n, p in values.items()):
        raise ValueError('Only FP32 language LoRA parameters may train')
    return nested_digest(values)


def reset_seed(seed):
    import numpy as np
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


def optimizer_for(model, cfg):
    import torch
    op = cfg['optimizer']
    return torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
        lr=cfg['learning_rate'], betas=tuple(op['betas']), eps=op['eps'], weight_decay=op['weight_decay'],
        amsgrad=op['amsgrad'], foreach=op['foreach'], fused=op['fused'], maximize=op['maximize'],
        capturable=op['capturable'], differentiable=op['differentiable'])


def execution_rows():
    from qwenlab import financial_state_pair_cycle as original
    return original.execution_rows()


def training_lengths():
    lengths = {r['row_id']: r for r in read(parent_schedule.OUT / 'token-lengths.json')['rows']}
    for r in read(schedule.CANDIDATES / 'checks/input-accounting.json')['rows']:
        if r['id'] in lengths: raise ValueError('Duplicate candidate length ID')
        lengths[r['id']] = dict(action_input_tokens=r['action'], tool_input_tokens=r.get('tool'))
    return lengths


def train_rows():
    return [dict(r, action=r['annotation']['action'], tool_name=r['annotation']['tool_name'])
            for r in execution_rows()]


def encoded_training(run, tok, rows):
    """Local JSON cache plus immutable per-row and exact token payload bindings."""
    path, meta_path = run.cache / 'encoded.json', run.cache / 'encoded-meta.json'
    binding = dict(protocol_sha256=run.protocol_hash(), ordered_row_ids=[r['id'] for r in rows],
                   row_sha256={r['id']: parent_schedule.row_sha(r) for r in rows},
                   prompt_sha256=sha(Path(prompt.__file__)),
                   schedule_manifest_sha256=sha(schedule.OUT / 'manifest.json'))
    if path.exists() != meta_path.exists():
        # A crash between the two cache commits is recoverable: retain the
        # incomplete derived cache and rebuild, never reset optimizer state.
        for partial in (path, meta_path):
            if partial.exists():
                orphan = partial.with_name(partial.name + f'.orphan-{time.time_ns()}')
                if orphan.resolve().parent != run.cache.resolve():
                    raise ValueError('Unsafe cache recovery path')
                partial.rename(orphan)
    if path.exists() or meta_path.exists():
        meta = read(meta_path)
        if meta['binding'] != binding or meta['file_sha256'] != sha(path):
            raise ValueError('Encoded cache binding changed')
        encoded = read(path)
        v2.check_encoded(encoded, rows)
        if meta['encoded_payload_sha256'] != digest(encoded):
            raise ValueError('Cached token payload changed')
        # A cache/meta pair is not a trust root. Re-encode the actual prompt so
        # same-length token/candidate-ID tampering cannot be self-re-signed.
        for row, item in zip(rows, encoded):
            for task in ('action', 'tool'):
                expected_item = (prompt.encode(tok, row, task,
                    row['action'] if task == 'action' else row['tool_name'])
                    if task == 'action' or row['action'] == 'tool' else None)
                if item[task] != expected_item:
                    raise ValueError('Cached tokens differ from actual immutable prompt encoding')
    else:
        encoded = []
        for i, row in enumerate(rows):
            pause_check(run, 'encoding_training')
            encoded.append(dict(action=prompt.encode(tok, row, 'action', row['action']),
                                tool=prompt.encode(tok, row, 'tool', row['tool_name'])
                                if row['action'] == 'tool' else None))
            if (i + 1) % 500 == 0:
                run.status('encoding_training', done=i + 1, total=len(rows))
        v2.check_encoded(encoded, rows)
        durable_json(path, encoded)
        durable_json(meta_path, dict(binding=binding, file_sha256=sha(path),
                                    encoded_payload_sha256=digest(encoded)))
    expected = training_lengths()
    for row, item in zip(rows, encoded):
        for task in ('action', 'tool'):
            if item[task]:
                tokens = item[task]['tokens']
                if (not isinstance(tokens.get('input_ids'), list)
                        or not isinstance(tokens.get('attention_mask'), list)
                        or len(tokens['input_ids']) != len(tokens['attention_mask'])
                        or any(type(x) is not int or x < 0 for x in tokens['input_ids'])
                        or any(type(x) is not int or x != 1 for x in tokens['attention_mask'])):
                    raise ValueError('Invalid unpadded token IDs/attention mask')
            actual = len(item[task]['tokens']['input_ids']) if item[task] else None
            if actual != expected[row['id']][task + '_input_tokens']:
                raise ValueError('Cached length differs from actual frozen tokenizer preflight')
    return {r['id']: item for r, item in zip(rows, encoded)}


def ensure_finite_training(loss, norm):
    if not math.isfinite(float(loss)) or not math.isfinite(float(norm)):
        raise FloatingPointError('Nonfinite gradient/loss; stop without automatic extension')


def save_checkpoint(armrun, protocol, model, optimizer, summary):
    import torch
    from qwenlab.joint_v5 import rng_state
    step = summary['step']
    checkpoint_summary_binding(summary, protocol, armrun.arm, step)
    summary.update(checkpoint_parameter_sha256=parameter_hash(model),
                   optimizer_state_sha256=nested_digest(optimizer.state_dict()),
                   rng_state_sha256=nested_digest(rng_state()))
    path = v2.checkpoint(armrun, model, optimizer, step, summary)
    state = torch.load(path / 'training-state.pt', map_location='cpu', weights_only=False)
    if (state['summary'] != summary or state['step'] != step
            or nested_digest(state['optimizer']) != summary['optimizer_state_sha256']
            or nested_digest(state['rng']) != summary['rng_state_sha256']):
        raise ValueError('Durable checkpoint does not match completed optimizer state')
    durable_json(armrun.out / 'training-summary.json', summary)
    return path


def process_identity():
    import psutil
    return dict(pid=os.getpid(), process_created=psutil.Process().create_time())


def identity_alive(identity):
    import psutil
    try:
        return abs(psutil.Process(identity['pid']).create_time() - identity['process_created']) < .001
    except (KeyError, psutil.NoSuchProcess):
        return False
    except psutil.AccessDenied:
        # Uninspectable is not proof of exit. Never claim a safe shutdown.
        return True


def alive(status):
    return identity_alive(status)


def pause_check(context, stage, model=None, optimizer=None, summary=None, protocol=None, automatic=False):
    run = context.cycle if isinstance(context, ArmRun) else context
    if not automatic and not ft.pause_requested(run):
        return
    checkpoint = None
    if model is not None:
        checkpoint = save_checkpoint(context, protocol, model, optimizer, summary)
    if automatic:
        evidence = dict(version='financial-full-coverage-pause-resume-v1', state='paused',
                        protocol_sha256=run.protocol_hash(), arm=context.arm,
                        completed_step=summary['step'], next_step=summary['step'] + 1,
                        prior_worker=process_identity(), checkpoint=relative(checkpoint),
                        checkpoint_sha256=sha(checkpoint / 'checkpoint.json'),
                        saved_parameter_sha256=summary['checkpoint_parameter_sha256'],
                        saved_optimizer_sha256=summary['optimizer_state_sha256'],
                        saved_rng_sha256=summary['rng_state_sha256'], at=ft.now())
        immutable_json(run.out / 'pause-resume-evidence.json', evidence)
    record = dict(state='paused', safe_to_shutdown=False, interrupted_stage=stage,
                  checkpoint=relative(checkpoint) if checkpoint else None,
                  protocol_sha256=run.protocol_hash(), worker=process_identity(), at=ft.now())
    durable_json(run.control, record)
    run.status('paused', interrupted_stage=stage, arm=getattr(context, 'arm', None),
               step=summary['step'] if summary else None, checkpoint=record['checkpoint'])
    raise ft.Paused()


def record_restoration(armrun, saved, state, optimizer, model):
    from qwenlab.joint_v5 import rng_state
    summary = state['summary']
    actual = dict(parameter_sha256=parameter_hash(model),
                  optimizer_sha256=nested_digest(optimizer.state_dict()),
                  rng_sha256=nested_digest(rng_state()))
    if (actual['parameter_sha256'] != summary['checkpoint_parameter_sha256']
            or actual['optimizer_sha256'] != summary['optimizer_state_sha256']
            or actual['rng_sha256'] != summary['rng_state_sha256']):
        raise ValueError('Restored adapter/optimizer/RNG differs from saved checkpoint')
    record = dict(protocol_sha256=armrun.protocol_hash(), checkpoint=relative(saved),
                  checkpoint_sha256=sha(saved / 'checkpoint.json'), arm=armrun.arm,
                  completed_step=state['step'], next_step=state['step'] + 1,
                  restored=actual, worker=process_identity(), at=ft.now())
    ft.append(armrun.out / 'resume-history.jsonl', record)
    proof = armrun.cycle.out / 'pause-resume-evidence.json'
    if proof.exists():
        evidence = read(proof)
        if evidence['state'] == 'paused' and evidence['arm'] == armrun.arm:
            if (identity_alive(evidence['prior_worker']) or evidence['checkpoint'] != relative(saved)
                    or evidence['checkpoint_sha256'] != record['checkpoint_sha256']
                    or evidence['completed_step'] != state['step']
                    or evidence['protocol_sha256'] != armrun.protocol_hash()):
                raise ValueError('Probe pause was not followed by a real independent-process checkpoint resume')
            evidence.update(state='resumed', prior_worker_exited=True, restore_record=record,
                            resumed_next_step=state['step'] + 1)
            durable_json(proof, evidence)


def initial_record(armrun, model, protocol):
    value = dict(initial_parameter_sha256=parameter_hash(model), seed=protocol['config']['seed'],
                 protocol_sha256=armrun.protocol_hash(), common_binding_sha256=protocol['common_binding_sha256'],
                 fresh_official_base=True, probe_adapter_loaded=False,
                 dtypes=ft.dtype_summary(model), arm=armrun.arm)
    immutable_json(armrun.out / 'initialization.json', value)
    other = read(REFERENCE / 'arms/preauth/initialization.json')
    if (other['initial_parameter_sha256'] != value['initial_parameter_sha256']
            or other['seed'] != value['seed']):
        raise ValueError('New initialization differs from archived same-seed fresh preauth arm')
    if not armrun.cycle.probe:
        probe = read(ROOT / 'results' / PROBE / 'arms' / armrun.arm / 'initialization.json')
        if probe['initial_parameter_sha256'] != value['initial_parameter_sha256']:
            raise ValueError('Main initialization differs from same-seed probe fresh initialization')
    return value


def recover_logs(armrun, step, step_rows):
    path = armrun.out / 'train.jsonl'
    raw = path.read_text(encoding='utf-8') if path.exists() else ''
    lines = raw.splitlines()
    incomplete = bool(raw and not raw.endswith('\n'))
    if incomplete:
        lines = lines[:-1]
    records = [json.loads(line) for line in lines if line]
    kept = [r for r in records if r['step'] <= step]
    if [r['step'] for r in kept] != list(range(1, step + 1)):
        raise ValueError('Committed training log has missing or duplicate steps')
    if any(record['row_ids'] != step_rows[record['step'] - 1] for record in kept):
        raise ValueError('Committed log differs from the immutable row-ID schedule')
    if incomplete or len(kept) != len(records):
        # Preserve any interrupted suffix before restoring the checkpoint cursor.
        durable_json(armrun.out / f'interrupted-log-{time.time_ns()}.json', dict(raw=raw, checkpoint_step=step))
        with path.open('wb') as stream:
            stream.write(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in kept).encode())
            stream.flush(); os.fsync(stream.fileno())
    return kept


def train_arm(run, protocol, arm, raw_rows):
    import torch
    from qwenlab.joint_v5 import rng_state, restore_rng
    context = ArmRun(run, arm)
    context.out.mkdir(parents=True, exist_ok=True)
    cfg = protocol['config']
    plan = read(schedule.OUT / 'plan.json')
    step_rows = validate_schedule(plan, raw_rows, arm, cfg)
    bound = protocol['steps_per_arm']
    saved = ft.latest_checkpoint(context)
    if saved:
        meta = ft.validate_checkpoint(context, saved)
        if not 0 <= meta['step'] <= bound:
            raise ValueError('Checkpoint exceeds this arm budget')
        if (context.out / 'arm-complete.json').exists():
            completion = read(context.out / 'arm-complete.json')
            if completion['steps'] != meta['step'] or completion['checkpoint_sha256'] != sha(saved / 'checkpoint.json') or completion['protocol_sha256'] != run.protocol_hash():
                raise ValueError('Arm completion is stale')
            recover_logs(context, meta['step'], step_rows)
            return
    elif (context.out / 'train.jsonl').exists():
        raise ValueError('Uncheckpointed arm log exists; refuse silent reset')
    context.status('loading_training', step=int(saved.name[5:]) if saved else 0, total_steps=bound)
    reset_seed(cfg['seed'])
    tok, model = qm.load(training=True, checkpoint=saved)
    optimizer = optimizer_for(model, cfg)
    records = [dict(r, action=r['annotation']['action'], tool_name=r['annotation']['tool_name']) for r in raw_rows]
    lookup = {r['id']: r for r in records}
    try:
        if saved is None:
            initial = initial_record(context, model, protocol)
            summary = dict(step=0, arm=arm, cursor=dict(arm=arm, completed_steps=0, next_step=1),
                           initial_parameter_sha256=initial['initial_parameter_sha256'],
                           schedule_manifest_sha256=protocol['common_binding']['schedule_manifest_sha256'],
                           sampled_by_id={}, sampled_tools={}, sample_positions=0, unique_rows=0,
                           training_elapsed_s=0., peak_allocated_gib=0.)
        else:
            state = torch.load(saved / 'training-state.pt', map_location='cpu', weights_only=False)
            if state['protocol_sha256'] != run.protocol_hash() or state['step'] != int(saved.name[5:]):
                raise ValueError('Checkpoint protocol/step changed')
            summary = state['summary']
            checkpoint_summary_binding(summary, protocol, arm, state['step'])
            initial = read(context.out / 'initialization.json')
            if initial['initial_parameter_sha256'] != summary['initial_parameter_sha256']:
                raise ValueError('Checkpoint initial adapter identity changed')
        encoded = encoded_training(context, tok, records)
        if saved is None:
            ft.preflight(context, tok, model, list(encoded.values()), dict(pilot=dict(
                micro_batch=2, gradient_accumulation=4, action_loss_weight=1., tool_loss_weight=.75)))
            save_checkpoint(context, protocol, model, optimizer, summary)
        else:
            optimizer.load_state_dict(state['optimizer'])
            restore_rng(state['rng'])
            record_restoration(context, saved, state, optimizer, model)
        recover_logs(context, summary['step'], step_rows)
        expected_counts = Counter(rid for batch in step_rows[:summary['step']] for rid in batch)
        if dict(expected_counts) != summary['sampled_by_id']:
            raise ValueError('Checkpoint exposure counters differ from schedule prefix')
        if not run.probe and summary['step'] in EVALUATION_STEPS:
            rng = rng_state()
            try: evaluate(run, tok, model, f'{arm}-step-{summary["step"]}', protocol)
            finally: restore_rng(rng)
        counts, tools = Counter(summary['sampled_by_id']), Counter(summary['sampled_tools'])
        params = [p for p in model.parameters() if p.requires_grad]
        torch.cuda.reset_peak_memory_stats()
        stop_already = not run.probe and summary['step'] in EVALUATION_STEPS and persistent_deterioration(run,protocol)
        for step in range(summary['step'] + 1, bound + 1) if not stop_already else ():
            pause_check(context, 'training', model, optimizer, summary, protocol)
            ids = step_rows[step - 1]
            context.status('training', step=step - 1, total_steps=bound)
            model.train(); optimizer.zero_grad(set_to_none=cfg['optimizer']['zero_grad_set_to_none'])
            rate = learning_rate(step, cfg)
            for group in optimizer.param_groups: group['lr'] = rate
            torch.cuda.synchronize(); started = time.perf_counter(); loss = 0.; tool_count = 0
            for pos in range(0, len(ids), 2):
                block = [encoded[rid] for rid in ids[pos:pos + 2]]
                a, t, c = ft.micro_backward(tok, model, block, dict(pilot=dict(
                    action_loss_weight=1., tool_loss_weight=.75, gradient_accumulation=1/micro_weight(len(block),len(ids)))))
                loss += (a + .75 * t) * micro_weight(len(block),len(ids)); tool_count += c
            norm = torch.nn.utils.clip_grad_norm_(params, max_norm=1., norm_type=2., error_if_nonfinite=True)
            ensure_finite_training(loss, norm)
            optimizer.step(); optimizer.zero_grad(set_to_none=True); torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            counts.update(ids)
            tools.update(lookup[rid]['tool_name'] for rid in ids if lookup[rid]['action'] == 'tool')
            summary.update(step=step, cursor=dict(arm=arm, completed_steps=step, next_step=step + 1),
                           sampled_by_id=dict(counts), sampled_tools=dict(tools), sample_positions=sum(counts.values()),
                           unique_rows=len(counts), training_elapsed_s=summary['training_elapsed_s'] + elapsed,
                           peak_allocated_gib=max(summary['peak_allocated_gib'], torch.cuda.max_memory_allocated() / 2**30))
            ft.append(context.out / 'train.jsonl', dict(step=step, arm=arm, row_ids=ids,
                row_ids_sha256=digest(ids), loss=loss, lr=rate, true_tools=tool_count,
                elapsed_s=elapsed, gradient_norm=float(norm), sample_positions=sum(counts.values()),
                unique_rows=len(counts), protocol_sha256=run.protocol_hash()))
            durable_json(context.out / 'training-summary.json', summary)
            automatic = (run.probe and arm == 'fullcover' and step == protocol['probe_pause_at_step']
                         and not (run.out / 'pause-resume-evidence.json').exists())
            if automatic:
                pause_check(context, 'probe_pause_resume_smoke', model, optimizer, summary, protocol, automatic=True)
            if step % cfg['checkpoint_save_interval'] == 0 or step == bound or step in EVALUATION_STEPS or ft.pause_requested(run):
                context.status('saving', step=step, total_steps=bound)
                save_checkpoint(context, protocol, model, optimizer, summary)
            pause_check(context, 'training', model, optimizer, summary, protocol)
            if not run.probe and step in EVALUATION_STEPS:
                rng = rng_state()
                try: evaluate(run, tok, model, f'{arm}-step-{step}', protocol)
                finally: restore_rng(rng)
                if persistent_deterioration(run, protocol):
                    immutable_json(context.out / 'early-stop.json', dict(step=step, reason='three persistent joint deteriorations after full epoch1', protocol_sha256=run.protocol_hash()))
                    break
        if run.probe:
            rng = rng_state()
            try:
                with ft.inference_scorer(model) as scorer:
                    for task in ('action', 'tool'):
                        v2.task_prediction(tok, scorer, lookup[step_rows[0][0]], task)
                    immutable_json(context.out / 'projection-check.json', dict(
                        projection=scorer.projection, fallback_reason=scorer.fallback_reason,
                        verified_layouts=len(scorer.verified), scope='training-only input; no evaluation rows'))
            finally: restore_rng(rng)
        completed = summary['step']
        final_path = context.checkpoints / f'step-{completed}'
        ft.validate_checkpoint(context, final_path)
        immutable_json(context.out / 'arm-complete.json', dict(arm=arm, steps=completed,
            checkpoint_sha256=sha(final_path / 'checkpoint.json'), protocol_sha256=run.protocol_hash(),
            initial_parameter_sha256=summary['initial_parameter_sha256'], sample_positions=summary['sample_positions']))
    finally:
        del model, optimizer
        gc.collect(); torch.cuda.empty_cache()


def checkpoint_for_variant(run, variant):
    if variant == 'base': return None
    match = re.fullmatch(r'fullcover-step-(\d+)', variant)
    if not match or int(match[1]) not in EVALUATION_STEPS:
        raise ValueError('Invalid predeclared checkpoint variant')
    context = ArmRun(run, 'fullcover')
    path = context.checkpoints / f'step-{int(match[1])}'
    ft.validate_checkpoint(context, path)
    return path


def evaluation_rows(run, protocol, split, variant):
    if run.probe or split not in ('development', 'calibration', 'final'):
        raise ValueError('Probe cannot consume evaluation examples')
    if split != 'development':
        selected = read(run.out / 'selection.json')
        if (not selected['passed'] or selected['protocol_sha256'] != run.protocol_hash()
                or selected.get('selected') not in tuple(f'fullcover-step-{s}' for s in EVALUATION_STEPS)
                or variant not in ('base', selected['selected'])
                or (split == 'calibration' and variant == 'base')):
            raise ValueError('Only the selected passing declared candidate may use calibration')
        if split == 'final':
            policy = read(run.out / 'calibration-policy.json')
            if (not policy['passed'] or policy['protocol_sha256'] != run.protocol_hash()
                    or policy['variant'] != selected['selected']):
                raise ValueError('Final requires a frozen passing calibration policy')
    manifest = protocol['evaluation']
    if manifest['manifest_sha256'] != sha(evaluation_data.OUT / 'evaluation-manifest.json'):
        raise ValueError('Evaluation manifest changed')
    path = evaluation_data.OUT / (split + '.json')
    if sha(path) != manifest['files'][path.name]:
        raise ValueError('Evaluation split bytes changed')
    rows = read(path)
    if len(rows) != {'development':128, 'calibration':96, 'final':160}[split]:
        raise ValueError('Unexpected evaluation denominator')
    for row in rows:
        if row['split'] != split or row['training_eligible'] is not False:
            raise ValueError('Evaluation role changed')
        evaluation_data.check_row(row, prompt.SPEC)
    return rows


def eval_binding(run, protocol, variant, split):
    checkpoint = checkpoint_for_variant(run, variant)
    return dict(protocol_sha256=run.protocol_hash(), variant=variant, split=split,
                checkpoint_sha256=sha(checkpoint / 'checkpoint.json') if checkpoint else None,
                split_sha256=protocol['evaluation']['files'][split + '.json'])


def prediction_prefix(path):
    path = Path(path)
    if not path.exists():
        return []
    raw = path.read_text(encoding='utf-8')
    if raw and not raw.endswith('\n'):
        durable_json(path.parent / f'incomplete-tail-{time.time_ns()}.json', dict(raw=raw))
        raw = raw[:raw.rfind('\n') + 1]
        with path.open('wb') as stream:
            stream.write(raw.encode()); stream.flush(); os.fsync(stream.fileno())
    return [json.loads(line) for line in raw.splitlines() if line]


def evaluate(run, tok, model, variant, protocol, split='development'):
    rows = evaluation_rows(run, protocol, split, variant)
    folder = run.out / split / variant
    immutable_json(folder / 'binding.json', eval_binding(run, protocol, variant, split))
    done = prediction_prefix(folder / 'predictions.jsonl')
    ft.evaluation_prefix(rows, done)
    if len(done) < len(rows):
        run.status('evaluation', variant=variant, split=split, done=len(done), total=len(rows))
        with ft.inference_scorer(model) as scorer:
            for task in ('action', 'tool'):
                v2.task_prediction(tok, scorer, rows[0], task)
            for row in rows[:10]:
                ft.predict_request(tok, scorer, row, v2.task_prediction)
            for row in rows[len(done):]:
                pause_check(run, 'evaluation')
                prediction = ft.predict_request(tok, scorer, row, v2.task_prediction)
                prediction.update(projection=scorer.projection, projection_fallback=scorer.fallback_reason,
                                  measured_at=ft.now())
                ft.append(folder / 'predictions.jsonl', prediction); done.append(prediction)
                if len(done) % 16 == 0:
                    run.status('evaluation', variant=variant, split=split, done=len(done), total=len(rows))
    report = metrics.evaluate(rows, done, protocol['prompt_sha256'], run.protocol_hash())
    timing = dict(action_p50_s=ft.metrics.percentile([p['action_elapsed_s'] for p in done], .5),
                  request_p50_s=ft.metrics.percentile([p['elapsed_s'] for p in done], .5),
                  request_p95_s=ft.metrics.percentile([p['elapsed_s'] for p in done], .95),
                  total_measured_s=sum(p['elapsed_s'] for p in done),
                  conditional_tool_requests=sum(p['action'] == 'tool' for p in done),
                  scope='same local serial action+predicted-tool path including tokenization/transfers; excludes load/warmup; no backend')
    immutable_json(folder / 'metrics.json', report)
    immutable_json(folder / 'timing.json', timing)
    return report


def choose_candidate(reports, cfg, protocol_sha256):
    gates = {k:metrics.development_gate(reports['base'], v, cfg) for k,v in reports.items() if k != 'base'}
    passing = [k for k,g in gates.items() if g['passed']]
    selected = max(passing, key=lambda k:(reports[k]['macro_f1'], reports[k]['action_tool_joint_accuracy'], -int(k.rsplit('-',1)[1]))) if passing else None
    return dict(passed=bool(passing), selected=selected, selected_arm='fullcover' if selected else None,
        gates=gates, protocol_sha256=protocol_sha256, selection_steps=list(EVALUATION_STEPS),
        automatic_extension=False, usage='development selection only; original gates unchanged; repeated synthetic dev limitation')


def select(run, protocol):
    completion = read(ArmRun(run,'fullcover').out / 'arm-complete.json')
    variants = ['base'] + [f'fullcover-step-{s}' for s in EVALUATION_STEPS if s <= completion['steps']]
    reports = {}
    rows = evaluation_rows(run, protocol, 'development', 'base')
    for variant in variants:
        folder = run.out / 'development' / variant
        if read(folder / 'binding.json') != eval_binding(run, protocol, variant, 'development'):
            raise ValueError('Selection binding changed')
        predictions = ft.rows_file(folder / 'predictions.jsonl')
        ft.evaluation_prefix(rows, predictions)
        if len(predictions) != len(rows): raise ValueError('Incomplete checkpoint evaluation')
        computed = metrics.evaluate(rows,predictions,protocol['prompt_sha256'],run.protocol_hash())
        if computed != read(folder / 'metrics.json'): raise ValueError('Metrics differ from saved logits')
        reports[variant] = computed
    decision = choose_candidate(reports,protocol['config'],run.protocol_hash())
    immutable_json(run.out / 'selection.json',decision)
    return decision,reports


def holdout(run, protocol, decision):
    import torch
    variant = decision['selected']
    path = checkpoint_for_variant(run, variant)
    tok, model = qm.load(checkpoint=path)
    try:
        evaluate(run, tok, model, variant, protocol, 'calibration')
        # This pure run-aware routine uses this run.out, protocol and explicitly
        # supplied variant. It does not inherit any old experiment namespace.
        policy = v2.calibrate(run, protocol, variant)
        if not policy['passed']:
            return False
        evaluate(run, tok, model, variant, protocol, 'final')
    finally:
        del model; gc.collect(); torch.cuda.empty_cache()
    tok, model = qm.load()
    try:
        evaluate(run, tok, model, 'base', protocol, 'final')
    finally:
        del model; gc.collect(); torch.cuda.empty_cache()
    rows = evaluation_rows(run, protocol, 'final', variant)
    predictions = ft.rows_file(run.out / 'final' / variant / 'predictions.jsonl')
    kept = {p['id'] for p in predictions if max(v2.temperature_probs(
        p['action_prediction']['logits'], policy['temperature'])) >= policy['threshold']}
    immutable_json(run.out / 'final/selective-summary.json', dict(
        coverage=len(kept) / len(rows), accepted=len(kept), deferred=len(rows) - len(kept),
        accepted_metrics=metrics.evaluate([r for r in rows if r['id'] in kept],
            [p for p in predictions if p['id'] in kept], protocol['prompt_sha256'], run.protocol_hash()) if kept else None,
        policy_sha256=sha(run.out / 'calibration-policy.json'),
        note='Subset denominator differs; defer is not a correct answer; no fallback API executed.'))
    return True


def paired_bootstrap(rows, base, candidate, seed, repeats=1000):
    """Paired source-group resampling of action correctness differences."""
    groups = {}
    for row in rows:
        groups.setdefault(row['scene_family_id'], []).append(row)
    a, b = {p['id']: p for p in base}, {p['id']: p for p in candidate}
    if set(a) != {r['id'] for r in rows} or set(a) != set(b):
        raise ValueError('Paired bootstrap requires aligned full predictions')
    rng = random.Random(seed); names = sorted(groups); changes = []
    for _ in range(repeats):
        sample = [r for _ in names for r in groups[rng.choice(names)]]
        changes.append(sum(int(b[r['id']]['action'] == r['annotation']['action'])
                           - int(a[r['id']]['action'] == r['annotation']['action']) for r in sample) / len(sample))
    return dict(groups=len(names), rows=len(rows), repeats=repeats, seed=seed,
                action_accuracy_delta_ci95=[ft.metrics.percentile(changes, .025), ft.metrics.percentile(changes, .975)],
                scope='paired synthetic story-group bootstrap, one training seed; not production generalization')


def historical_comparison(run, protocol, reports):
    old = check_reference(protocol['common_binding'],protocol['evaluation'],protocol['config'])
    rows = evaluation_rows(run,protocol,'development','base')
    previous_run = parent_cycle.Run()
    folder = REFERENCE / 'development/preauth-step-400'
    preds = ft.rows_file(folder/'predictions.jsonl')
    ft.evaluation_prefix(rows,preds)
    previous = metrics.evaluate(rows,preds,old['prompt_sha256'],previous_run.protocol_hash())
    if previous != read(folder/'metrics.json'): raise ValueError('Historical metrics changed')
    comparisons = {variant:paired_bootstrap(rows,preds,ft.rows_file(run.out/'development'/variant/'predictions.jsonl'),protocol['config']['seed']) for variant in reports if variant!='base'}
    result = dict(historical_preauth400=previous, complete_coverage_development=reports,
        paired_bootstrap=comparisons, limitation='different exposure distribution, training length and LR trajectory; not isolated causal comparison; one seed repeated synthetic dev')
    immutable_json(run.out/'historical-comparison.json',result)
    return result


def finish_main(run, protocol, decision, reports, final_done):
    historical_comparison(run,protocol,reports)
    arm_completion = read(ArmRun(run,'fullcover').out/'arm-complete.json')
    immutable_json(run.out/'comparison.json',dict(selection=decision,development=reports,one_training_seed=True))
    immutable_json(run.out/'completion.json',dict(status='complete',protocol_sha256=run.protocol_hash(),selection=decision,
        calibration_evaluated=decision['passed'],final_evaluated=bool(final_done),model_api_requests=0,deployed=False,
        auto_extended=False,arm_steps={'fullcover':arm_completion['steps']},maximum_steps=TOTAL_STEPS,
        complete_epochs=arm_completion['steps']//1673))


def validate_probe_evidence(run, protocol):
    evidence = read(run.out / 'pause-resume-evidence.json')
    restore = evidence.get('restore_record', {})
    if (evidence.get('state') != 'resumed' or evidence.get('prior_worker_exited') is not True
            or evidence.get('protocol_sha256') != run.protocol_hash() or evidence.get('arm') != 'fullcover'
            or evidence.get('completed_step') != protocol['probe_pause_at_step']
            or evidence.get('resumed_next_step') != protocol['probe_pause_at_step'] + 1
            or restore.get('next_step') != evidence['resumed_next_step']
            or restore.get('checkpoint_sha256') != evidence['checkpoint_sha256']
            or restore.get('worker') == evidence.get('prior_worker')):
        raise ValueError('Matching real pause/resume evidence is required')
    expected = dict(parameter_sha256=evidence['saved_parameter_sha256'],
                    optimizer_sha256=evidence['saved_optimizer_sha256'], rng_sha256=evidence['saved_rng_sha256'])
    if restore.get('restored') != expected:
        raise ValueError('Probe did not restore the exact adapter, optimizer and RNG')
    checkpoint = ROOT / evidence['checkpoint']
    context = ArmRun(run, 'fullcover'); ft.validate_checkpoint(context, checkpoint)
    if sha(checkpoint / 'checkpoint.json') != evidence['checkpoint_sha256']:
        raise ValueError('Probe pause checkpoint changed')
    logs = ft.rows_file(context.out / 'train.jsonl')
    if not any(log['step'] == evidence['resumed_next_step'] for log in logs):
        raise ValueError('Probe did not execute the next step after restoration')
    return evidence


def probe_artifacts(run):
    paths = [run.out / 'protocol.json', run.out / 'pause-resume-evidence.json']
    for arm in ARMS:
        context = ArmRun(run, arm)
        paths += [context.out / name for name in ('initialization.json', 'train.jsonl',
                  'training-summary.json', 'arm-complete.json', 'projection-check.json')]
        for checkpoint in context.checkpoints.glob('step-*'):
            if checkpoint.is_dir():
                ft.validate_checkpoint(context, checkpoint)
                paths.append(checkpoint / 'checkpoint.json')
    return {relative(path): sha(path) for path in paths}


def finish_probe(run, protocol):
    validate_probe_evidence(run, protocol)
    all_logs, initial = [], []
    for arm in ARMS:
        context = ArmRun(run, arm)
        logs = ft.rows_file(context.out / 'train.jsonl')
        if [r['step'] for r in logs] != list(range(1, 26)):
            raise ValueError('Probe requires exactly25 updates per arm')
        plan = read(schedule.OUT / 'plan.json')['step_rows']
        if any(log['row_ids'] != plan[log['step'] - 1] for log in logs):
            raise ValueError('Probe did not follow frozen schedule prefix')
        ft.validate_checkpoint(context, context.checkpoints / 'step-25')
        initial.append(read(context.out / 'initialization.json')['initial_parameter_sha256'])
        all_logs += logs
    if len(set(initial)) != 1:
        raise ValueError('Probe arms have different initial adapters')
    seconds = ft.metrics.percentile([r['elapsed_s'] for r in all_logs if r['step'] > 5], .5)
    result = dict(status='complete', steps_per_arm=25, total_optimizer_steps=25,
                  common_binding_sha256=protocol['common_binding_sha256'], protocol_sha256=run.protocol_hash(),
                  initial_parameter_sha256=initial[0], median_step_s=seconds,
                  main_training_minutes_estimate=TOTAL_STEPS * seconds / 60,
                  evaluation_rows_used=0, probe_adapter_used_for_main=False,
                  adapters_discarded_from_training_use=True, artifacts_retained_for_audit=True,
                  real_pause_resume_verified=True, model_api_requests=0, artifacts=probe_artifacts(run),
                  estimate_scope='training only; excludes loading, evaluation, saving and hardware changes')
    immutable_json(run.out / 'probe-summary.json', result)
    immutable_json(run.out / 'completion.json', dict(status='complete', probe=True,
                   protocol_sha256=run.protocol_hash(), probe_summary_sha256=sha(run.out / 'probe-summary.json')))


def verify_probe(common_hash):
    run = Run(PROBE)
    result = read(run.out / 'probe-summary.json')
    protocol = read(run.out / 'protocol.json')
    completion = read(run.out / 'completion.json')
    if (result.get('status') != 'complete' or result.get('steps_per_arm') != 25
            or result.get('total_optimizer_steps') != 25 or result.get('evaluation_rows_used') != 0
            or result.get('probe_adapter_used_for_main') is not False
            or result.get('adapters_discarded_from_training_use') is not True
            or result.get('real_pause_resume_verified') is not True
            or result.get('common_binding_sha256') != common_hash
            or protocol['common_binding_sha256'] != common_hash
            or result['protocol_sha256'] != run.protocol_hash()
            or completion.get('probe_summary_sha256') != sha(run.out / 'probe-summary.json')):
        raise ValueError('Main requires a matching successful probe and real pause/resume smoke')
    if result['artifacts'] != probe_artifacts(run):
        raise ValueError('Probe artifacts changed')
    validate_probe_evidence(run, protocol)
    if identity_alive(read(run.out / 'status.json')):
        raise ValueError('Probe worker must exit before main starts')
    return sha(run.out / 'probe-summary.json')


def verify_execution_sources(protocol):
    if (protocol['common_binding']['source_sha256'] != source_bindings()
            or protocol['common_binding']['review_sha256'] != sha(REVIEW)
            or protocol['common_binding']['runtime'] != runtime_binding()
            or protocol['common_binding']['historical_reference_sha256'] != reference_bindings()):
        raise ValueError('Execution code/review/runtime changed during the cycle')


def recover_preprotocol(run, resume, previous_status):
    """Preserve failed initialization evidence; never discard training artifacts.

    The launcher uses --resume for an existing result directory. Before a
    protocol has committed there is no optimizer cursor to resume, so an
    explicit retry is allowed only for a verified status-only initialization.
    """
    if (run.out / 'protocol.json').exists():
        return False
    if not resume:
        if previous_status or (run.out.exists() and any(run.out.iterdir())):
            raise ValueError('Existing preprotocol state requires explicit --resume')
        return False
    if (not previous_status or previous_status.get('stage') not in ('failed', 'checking_protocol')
            or previous_status.get('run_name') != run.name or identity_alive(previous_status)):
        raise ValueError('Only an exited preprotocol initialization failure may restart')
    if not (run.out / 'status.json').is_file() or read(run.out / 'status.json') != previous_status:
        raise ValueError('Preprotocol status changed or was not preserved')
    for child in run.out.iterdir():
        if child.name == 'status.json' and child.is_file() and not child.is_symlink():
            continue
        if (re.fullmatch(r'preprotocol-failure-\d+\.json', child.name)
                and child.is_file() and not child.is_symlink()):
            record = read(child)
            if (record.get('version') == 'financial-full-coverage-preprotocol-failure-v1'
                    and record.get('run_name') == run.name
                    and isinstance(record.get('prior_status'), dict)):
                continue
        raise ValueError('Uncommitted protocol has other artifacts; refuse a fresh reset')
    for namespace in (run.checkpoints, run.cache):
        if namespace.exists() and (not namespace.is_dir() or any(namespace.iterdir())):
            raise ValueError('Checkpoint/cache artifacts forbid preprotocol fresh recovery')
    trigger = previous_status.get('requested_pause_at_step')
    if run.probe and (type(trigger) is not int or trigger != 12):
        raise ValueError('Probe retry lacks the original recorded pause trigger')
    immutable_json(run.out / f'preprotocol-failure-{time.time_ns()}.json', dict(
        version='financial-full-coverage-preprotocol-failure-v1', run_name=run.name,
        prior_status=previous_status, recovery='explicit_resume_before_protocol_commit',
        training_artifacts_found=False, recorded_at=ft.now()))
    return True


def worker(run, resume=False, pause_at_step=None):
    from qwenlab.joint_v5 import exclusive_lock
    with exclusive_lock(LOCK):
        if (run.out / 'completion.json').exists():
            raise FileExistsError('Completed experiment is immutable')
        previous = read(run.out / 'status.json') if (run.out / 'status.json').exists() else {}
        if previous and identity_alive(previous):
            raise RuntimeError('A previous sampling worker is still alive')
        fresh_recovery = recover_preprotocol(run, resume, previous)
        if fresh_recovery and run.probe:
            trigger = previous['requested_pause_at_step']
            if pause_at_step not in (None, trigger):
                raise ValueError('Cannot change the recorded probe pause trigger during recovery')
            pause_at_step = trigger
        control = read(run.control) if run.control.exists() else {}
        if control.get('state') in ('pause_requested', 'paused') and not resume:
            raise RuntimeError('Explicit resume required after a pause request')
        if resume:
            durable_json(run.control, dict(state='resuming', safe_to_shutdown=False, at=ft.now()))
        run.status('checking_protocol', requested_pause_at_step=pause_at_step)
        protocol = freeze(run, resume and not fresh_recovery, pause_at_step)
        pause_check(run, 'checking_protocol')
        import torch
        immutable_json(run.out / 'hardware.json', dict(gpu=torch.cuda.get_device_name(0),
                       torch=str(torch.__version__), cuda=torch.version.cuda,
                       total_memory_bytes=torch.cuda.get_device_properties(0).total_memory))
        raw_rows = execution_rows()
        if not run.probe:
            # Always replay cached metrics from saved logits; evaluate() does not
            # repeat already committed inference requests on resume.
            run.status('loading_baseline')
            tok, model = qm.load()
            try:
                immutable_json(run.out / 'base-parameter-dtypes.json', ft.dtype_summary(model))
                evaluate(run, tok, model, 'base', protocol)
            finally:
                del model; gc.collect(); torch.cuda.empty_cache()
        for arm in ARMS:
            verify_execution_sources(protocol)
            train_arm(run, protocol, arm, raw_rows)
        verify_execution_sources(protocol)
        if run.probe:
            finish_probe(run, protocol)
        else:
            decision, reports = select(run, protocol)
            final_done = holdout(run, protocol, decision) if decision['passed'] else False
            verify_execution_sources(protocol)
            finish_main(run, protocol, decision, reports, final_done)
        run.status('complete', probe_summary=run.probe, selected=None if run.probe else decision['selected'])


def safe_exit_status(status, worker_alive, checkpoint_valid, lock_released=True):
    return (status.get('stage') in ('paused', 'complete') and not worker_alive
            and bool(checkpoint_valid) and bool(lock_released))


def checkpoints_safe(run, status):
    try:
        if not (run.out / 'protocol.json').exists():
            return False
        protocol = read(run.out / 'protocol.json')
        for arm in ARMS:
            context = ArmRun(run, arm)
            latest = ft.latest_checkpoint(context)
            logs = ft.rows_file(context.out / 'train.jsonl')
            step = int(latest.name[5:]) if latest else 0
            if logs and logs[-1]['step'] > step:
                return False
            expected = read(run.out / 'completion.json').get('arm_steps', {}).get(arm, protocol['steps_per_arm']) if status.get('stage') == 'complete' else None
            if status.get('stage') == 'complete' and step != expected:
                return False
        if status.get('stage') == 'complete':
            completion = read(run.out / 'completion.json')
            if completion.get('protocol_sha256') != run.protocol_hash():
                return False
        return True
    except (OSError, KeyError, ValueError):
        return False


def gpu_lock_released():
    from qwenlab.joint_v5 import exclusive_lock
    try:
        with exclusive_lock(LOCK):
            pass
        return True
    except RuntimeError:
        return False


def progress(run):
    path = run.out / 'status.json'
    if not path.exists():
        return dict(stage='not_started', run_name=run.name, run_exists=run.out.exists(),
                    protocol_exists=(run.out / 'protocol.json').exists(), worker_alive=False, safe_to_shutdown=False)
    value = read(path)
    live = identity_alive(value)
    value.update(run_exists=True, protocol_exists=(run.out / 'protocol.json').exists(),
                 worker_alive=live, safe_to_shutdown=False)
    logs = {}
    for arm in ARMS:
        source = ArmRun(run, arm).out / 'train.jsonl'
        raw = source.read_text(encoding='utf-8') if source.exists() else ''
        lines = raw.splitlines()
        if raw and not raw.endswith('\n'): lines = lines[:-1]
        logs[arm] = [json.loads(line) for line in lines if line]
    per_arm = 25 if run.probe else TOTAL_STEPS
    steps = {arm: logs[arm][-1]['step'] if logs[arm] else 0 for arm in ARMS}
    recent = [record['elapsed_s'] for arm in ARMS for record in logs[arm][-30:]]
    value.update(arm_steps=steps, cycle_step=sum(steps.values()), total_steps=len(ARMS) * per_arm,
                 percent=round(sum(steps.values()) / (len(ARMS) * per_arm) * 100, 2))
    if recent:
        seconds = ft.metrics.percentile(recent, .5)
        value.update(recent_step_median_s=round(seconds, 3),
                     remaining_train_minutes_estimate=round((len(ARMS) * per_arm - sum(steps.values())) * seconds / 60, 1),
                     estimate_scope='remaining optimizer updates only; current arm/stage shown separately; excludes evaluation/load/save')
    if not live and value.get('stage') in ('paused', 'complete'):
        value['safe_to_shutdown'] = safe_exit_status(value, live, checkpoints_safe(run, value), gpu_lock_released())
    return value


def pause(run):
    value = progress(run)
    if value.get('worker_alive'):
        original = read(run.out / 'status.json')
        durable_json(run.control, dict(state='pause_requested', safe_to_shutdown=False, at=ft.now()))
        print('等待当前优化器步骤提交、检查点保存和工作进程真实退出。', flush=True)
        while identity_alive(original):
            time.sleep(2)
        value = progress(run)
    if not value.get('safe_to_shutdown'):
        raise RuntimeError('Worker exit, checkpoint integrity and GPU lock release are not all confirmed')
    durable_json(run.control, dict(state=value['stage'], safe_to_shutdown=True,
                 confirmed_worker_exited=True, confirmed_gpu_lock_released=True,
                 protocol_sha256=run.protocol_hash(), at=ft.now()))
    print('已确认工作进程退出、检查点完整且GPU锁释放；可以正常关机。', flush=True)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'progress', 'pause'))
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--pause-at-step', type=int)
    args = parser.parse_args(argv)
    if args.command != 'run' and (args.resume or args.pause_at_step is not None):
        parser.error('--resume and --pause-at-step belong to run only')
    if args.pause_at_step is not None and not args.probe:
        parser.error('--pause-at-step is a probe-only process interruption smoke')
    run = Run(PROBE if args.probe else DEFAULT)
    if args.command == 'progress':
        while True:
            value = progress(run)
            print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)
            if not args.watch or not value.get('worker_alive'):
                break
            time.sleep(20)
    elif args.command == 'pause':
        pause(run)
    else:
        try:
            worker(run, args.resume, args.pause_at_step)
        except ft.Paused:
            print('检查点已保存；本进程正在退出。progress/pause必须确认真实退出后才能宣告可关机。', flush=True)
        except Exception as exc:
            status = read(run.out / 'status.json') if (run.out / 'status.json').exists() else {}
            if status.get('pid') == os.getpid():
                run.status('failed', error_type=type(exc).__name__, error=str(exc),
                           requested_pause_at_step=status.get('requested_pause_at_step'))
            raise





def micro_weight(micro_size, actual_batch):
    if type(micro_size) is not int or type(actual_batch) is not int or not 0 < micro_size <= actual_batch <= 8:
        raise ValueError('Invalid actual batch denominator')
    return micro_size/actual_batch


def development_nll(rows,predictions):
    ft.evaluation_prefix(rows,predictions)
    if not rows or len(rows)!=len(predictions): raise ValueError('Incomplete development prediction set')
    return -sum(math.log(max(p['action_prediction']['probabilities'][r['annotation']['action']],1e-12)) for r,p in zip(rows,predictions))/len(rows)


def deterioration_history(history, policy):
    eligible = [h for h in history if h['step'] >= 1673]
    if len(eligible) < policy['consecutive_evaluations']: return False
    recent = eligible[-policy['consecutive_evaluations']:]
    prior = [h for h in history if h['step'] < recent[0]['step']]
    if not prior: return False
    best = max(prior,key=lambda h:h['macro_f1'])
    return all(h['macro_f1'] <= best['macro_f1']-policy['macro_f1_drop']
        and h['nll'] >= best['nll']+policy['nll_increase']
        and h['human_misses'] >= best['human_misses'] and h['preauth_tool_actions'] >= best['preauth_tool_actions']
        for h in recent)


def persistent_deterioration(run,protocol):
    history=[]
    for step in EVALUATION_STEPS:
        folder=run.out/'development'/f'fullcover-step-{step}'
        if not (folder/'metrics.json').exists(): continue
        report=read(folder/'metrics.json')
        predictions=ft.rows_file(folder/'predictions.jsonl')
        # Annotation targets come from frozen development rows, never from predictions.
        rows=evaluation_rows(run,protocol,'development','base')
        nll=development_nll(rows,predictions)
        history.append(dict(step=step,macro_f1=report['macro_f1'],nll=nll,
            human_misses=len(report['human_misses']),preauth_tool_actions=len(report['unauthenticated_tool_actions'])))
    return deterioration_history(history,protocol['config']['sampling']['early_stop'])


if __name__ == '__main__':
    main()
