"""Isolation, prompt leakage, executable-target metrics and review tests."""
from copy import deepcopy
import json
import unittest
import uuid
from unittest.mock import patch

from qwenlab.common import ROOT, sha
from qwenlab.financial_release_core import rows as core_rows
from qwenlab.financial_pilot import ACTIONS, TOOLS
from qwenlab import financial_ready as ready
from qwenlab import financial_actions_prompt as prompts
from qwenlab import financial_actions_metrics as metrics


def row(number=0, split=None):
    r = deepcopy(core_rows()[number])
    if split:
        r.update(split=split, evaluation_split=split)
    return r


def workspace():
    folder = ROOT/'.local/test-financial-ready'/uuid.uuid4().hex
    folder.mkdir(parents=True)
    return folder


def small_release():
    folder = workspace()
    parent = folder.parent/(folder.name+'-base')
    ready.write_json(parent/'manifest.json',{})
    ready.v1.write_lf(parent/'parts/part-0001.jsonl',[])
    source_train = [row()]
    source_eval = [row(2,'development'),row(4,'calibration'),row(6,'final')]
    catalog = {r['scene_family_id']:dict(split=r['evaluation_split'],macro_scene=r['id']) for r in source_eval}
    groups = ready.joined_groups(source_train,source_eval,catalog)
    train = [ready.publish(r,'train',groups) for r in source_train]
    evaluation = [ready.publish(r,r['evaluation_split'],groups) for r in source_eval]
    ready.v1.write_lf(folder/'train-additions.jsonl',train)
    ready.write_json(folder/'groups.json',groups)
    ready.write_json(folder/'evaluation/catalog.json',catalog)
    for split in ready.SPLITS:
        ready.write_json(folder/f'evaluation/{split}.json',[r for r in evaluation if r['evaluation_split']==split])
    bindings = {}
    for stem,items in [('train-additions',source_train),('evaluation',source_eval)]:
        digest = '0'*64
        ready.write_json(folder/f'reviews/{stem}-review.json',dict(decision='pass',human_review=False,
            reviewer='independent',unresolved_findings=[],data_sha256=digest,
            reviewed_ids=[r['id'] for r in items],
            reviewed_content_sha256={r['id']:ready.review_content_digest(r) for r in items}))
        bindings[f'.local/financial-eight-actions-v2/candidates/{stem}.jsonl'] = digest
        bindings[f'.local/financial-eight-actions-v2/review/{stem}-review.json'] = sha(folder/f'reviews/{stem}-review.json')
    ready.write_json(folder/'overlap-audit.json',dict(pairs=[]))
    ready.write_json(folder/'reviews/overlap-review.json',dict(decision='pass',human_review=False,
        unresolved_findings=[],pairs_sha256=ready.v1.digest([]),reviewed_pairs=[]))
    files = {p.relative_to(folder).as_posix():dict(sha256=sha(p)) for p in folder.rglob('*')
             if p.is_file() and parent not in p.parents}
    manifest = dict(purpose='train_and_evaluation',human_review=False,synthetic=True,action_tokens=ready.v1.LETTERS,
        files=files,source_bindings=bindings,base_release=parent.relative_to(ROOT).as_posix(),
        base_manifest_sha256=sha(parent/'manifest.json'),stats=ready.summarize([],train,evaluation,catalog))
    ready.write_json(folder/'manifest.json',manifest)
    return folder,manifest


class ReadyTests(unittest.TestCase):
    def test_evaluation_is_not_accepted_as_training_addition(self):
        folder = workspace()
        ready.v1.write_lf(folder/'candidates/train-additions.jsonl',[row(split='development')])
        with patch.object(ready,'LOCAL',folder):
            with self.assertRaisesRegex(ValueError,'cannot enter training overlay'):
                ready.reviewed_rows('train-additions',False)

    def test_evaluation_split_must_be_real_and_valid(self):
        folder = workspace()
        r = row()
        r['evaluation_split'] = 'development'
        ready.v1.write_lf(folder/'candidates/evaluation.jsonl',[r])
        with patch.object(ready,'LOCAL',folder):
            with self.assertRaisesRegex(ValueError,'real partition'):
                ready.reviewed_rows('evaluation',False)

    def test_independent_review_requires_exact_ids_and_data_hash(self):
        folder = workspace()
        path = folder/'candidates/train-additions.jsonl'
        r = row()
        ready.v1.write_lf(path,[r])
        report = dict(decision='pass', human_review=False, unresolved_findings=[],
                      data_sha256=sha(path), reviewer='independent', reviewed_ids=[r['id']],
                      reviewed_content_sha256={r['id']:ready.review_content_digest(r)})
        ready.write_json(folder/'review/train-additions-review.json',report)
        with patch.object(ready,'LOCAL',folder):
            self.assertEqual(len(ready.reviewed_rows('train-additions')),1)
            report['reviewer'] = 'root'
            ready.write_json(folder/'review/train-additions-review.json',report)
            with self.assertRaisesRegex(ValueError,'own data'):
                ready.reviewed_rows('train-additions')
            report.update(reviewer='independent',reviewed_ids=[])
            ready.write_json(folder/'review/train-additions-review.json',report)
            with self.assertRaisesRegex(ValueError,'missing or stale'):
                ready.reviewed_rows('train-additions')

    def test_state_contrasts_cannot_cross_partitions(self):
        training, evaluation = row(),row(split='development')
        evaluation['id'] += '-eval'
        evaluation['scene_family_id'] = 'new-eval-family'
        evaluation['input']['state']['authenticated'] = not training['input']['state']['authenticated']
        catalog = {'new-eval-family':dict(split='development',macro_scene='story-a')}
        with self.assertRaisesRegex(ValueError,'spans partitions'):
            ready.joined_groups([training],[evaluation],catalog)

    def test_shared_macro_background_is_a_correlated_group(self):
        a,b = row(split='development'),row(2,split='development')
        catalog = {r['scene_family_id']:dict(split='development',macro_scene='same-story') for r in [a,b]}
        groups = ready.joined_groups([],[a,b],catalog)
        self.assertEqual(groups[a['id']]['group'],groups[b['id']]['group'])
        b.update(split='final',evaluation_split='final')
        catalog[b['scene_family_id']]['split'] = 'final'
        with self.assertRaisesRegex(ValueError,'spans partitions'):
            ready.joined_groups([],[a,b],catalog)

    def test_numeric_template_overlap_is_reported_without_automatic_relabel(self):
        a,b = row(),row(split='final')
        a['input']['message'] = '请解释编号78211申请页面显示的数字状态，不要猜审核原因。'
        b['input']['message'] = '请解释编号96345申请页面显示的数字状态，不要猜审核原因。'
        a['id'],b['id'] = 'a','b'
        pairs = ready.near_pairs([a],[b])
        self.assertEqual(pairs,[dict(ids=['a','b'],ratio=1.0)])
        self.assertEqual(b['annotation']['action'],'clarify')

    def test_training_adapter_reads_only_explicit_train_files(self):
        folder = workspace()
        parent = folder/'base'
        r = row()
        r['split'] = 'train'
        ready.v1.write_lf(parent/'parts/part-0001.jsonl',[r])
        ready.v1.write_lf(folder/'train-additions.jsonl',[])
        # No evaluation files are created. An accidental glob would fail.
        ready.write_json(folder/'manifest.json',dict(base_release=parent.relative_to(ROOT).as_posix()))
        ready.write_json(folder/'groups.json',{r['id']:dict(split='train',group='g')})
        with patch.object(ready,'validate',return_value={}):
            result = list(ready.training_rows(folder))
            self.assertEqual(len(result),1)
            self.assertNotIn('annotation',json.loads(result[0]['input']))
            self.assertNotIn('evaluation_split',json.loads(result[0]['input']))
            r['dataset_role'] = 'evaluation'
            ready.v1.write_lf(parent/'parts/part-0001.jsonl',[r])
            with self.assertRaisesRegex(ValueError,'cannot enter training adapter'):
                list(ready.training_rows(folder))

    def test_final_access_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'explicit fixed-candidate'):
            ready.evaluation_rows('final')

    def test_prompt_never_encodes_gold_or_partition_metadata(self):
        r = row(split='final')
        r['annotation']['reason'] = 'unique-secret-label-explanation'
        content,keys = prompts.messages(r)
        text = '\n'.join(m['content'] for m in content)
        self.assertNotIn('unique-secret-label-explanation',text)
        self.assertNotIn(r['id'],text)
        self.assertNotIn('evaluation_split',text)
        self.assertEqual(keys,ACTIONS)
        self.assertEqual(prompts.messages(r,'tool')[1],TOOLS)
        self.assertNotIn('0未通过',str(prompts.messages(r,'tool')))

    def test_content_proof_covers_semantics_and_partition(self):
        a,b = row(split='development'),row(split='development')
        before = ready.review_content_digest(a)
        b['input']['message'] += ' 不要猜测。'
        self.assertNotEqual(before,ready.review_content_digest(b))
        a['evaluation_split'] = 'final'
        self.assertNotEqual(before,ready.review_content_digest(a))

    def test_portable_package_rejects_data_resigning_without_independent_review(self):
        folder, manifest = small_release()
        # The synthetic parent is outside the immutable artifact inventory.
        with patch.object(ready.v1,'validate',return_value={}),patch.object(ready,'check_budget',return_value=None):
            self.assertEqual(ready.validate(folder)['new_train'],1)
            path = folder/'evaluation/final.json'
            changed = json.loads(path.read_text(encoding='utf-8'))
            changed[0]['input']['message'] += ' 帮我看看。'
            ready.write_json(path,changed)
            manifest['files']['evaluation/final.json']['sha256'] = sha(path)
            ready.write_json(folder/'manifest.json',manifest)
            with self.assertRaisesRegex(ValueError,'differs from reviewed content'):
                ready.validate(folder)


class MetricTests(unittest.TestCase):
    def test_tool_action_accuracy_is_not_tool_selection_accuracy(self):
        r = row(111)
        prediction = dict(id=r['id'],action='tool',tool_name='queryMyApplications')
        result = metrics.evaluate([r],[prediction])
        self.assertEqual(result['action_accuracy'],1)
        self.assertEqual(result['action_tool_joint_accuracy'],0)

    def test_backend_arguments_are_reported_separately(self):
        r = row(71)
        prediction = dict(id=r['id'],action='tool',tool_name=r['annotation']['tool_name'],
            tool_arguments=r['annotation']['tool_arguments'],argument_source='trusted_state_parser')
        result = metrics.evaluate([r],[prediction])
        self.assertEqual(result['parameter_results']['trusted_state_parser']['accuracy'],1)
        self.assertIsNone(result['parameter_results']['model']['accuracy'])

    def test_gold_tool_cannot_be_hidden_after_wrong_action(self):
        r = row(71)
        with self.assertRaisesRegex(ValueError,'gold/oracle'):
            metrics.evaluate([r],[dict(id=r['id'],action='answer',tool_name=r['annotation']['tool_name'])])

    def test_missing_prediction_does_not_shrink_denominator(self):
        with self.assertRaisesRegex(ValueError,'exact split IDs'):
            metrics.evaluate([row()],[])

    def test_human_miss_and_unavailable_retrieval_are_visible(self):
        r = row(181)
        r['input']['capabilities']['knowledge_collections'] = []
        result = metrics.evaluate([r],[dict(id=r['id'],action='retrieve')])
        self.assertEqual(result['human_misses'],[r['id']])
        self.assertEqual(result['unavailable_knowledge_retrievals'],[r['id']])

    def test_nonfinite_speed_measurement_is_rejected(self):
        r = row()
        with self.assertRaisesRegex(ValueError,'elapsed'):
            metrics.evaluate([r],[dict(id=r['id'],action='clarify',elapsed_s=float('nan'))])

    def test_gate_rejects_final_prompt_changes_and_nan(self):
        from qwenlab.financial_pilot import base_input,label
        examples = []
        for action in ACTIONS:
            examples.append(dict(id=action,split='development',input=base_input('贷款客服指标测试'+action),
                annotation=label(action,'测试计数',tool='explainApplicationStatus' if action=='tool' else None,
                                 arguments={'status':1} if action=='tool' else None)))
        good = [dict(id=r['id'],action=r['annotation']['action'],tool_name=r['annotation']['tool_name']) for r in examples]
        old = deepcopy(good)
        old[4]['action'] = 'answer'
        base = metrics.evaluate(examples,old,prompt_sha256='a'*64,protocol_sha256='b'*64)
        current = metrics.evaluate(examples,good,prompt_sha256='a'*64,protocol_sha256='b'*64)
        policy = json.loads((ROOT/'configs/financial-eight-actions-pilot-v2.json').read_text(encoding='utf-8'))['development_gate']
        self.assertTrue(metrics.development_gate(base,current,policy)['passed'])
        final = deepcopy(current)
        final['partition'] = 'final'
        with self.assertRaisesRegex(ValueError,'Only development'):
            metrics.development_gate(base,final,policy)
        altered = deepcopy(current)
        altered['prompt_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError,'same frozen prompt'):
            metrics.development_gate(base,altered,policy)
        bad = deepcopy(current)
        bad['macro_f1'] = float('nan')
        with self.assertRaisesRegex(ValueError,'finite probabilities'):
            metrics.development_gate(base,bad,policy)


if __name__=='__main__':
    unittest.main()
