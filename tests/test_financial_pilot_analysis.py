"""Offline diagnostics must preserve joint denominators and group dependence."""
from copy import deepcopy
from collections import Counter
import unittest

from qwenlab import financial_pilot_analysis as analysis


class AnalysisTests(unittest.TestCase):
    def selection_fixture(self):
        protocol=analysis.ft.read(analysis.ROOT/'configs/financial-eight-actions-pilot-v2.json')
        binding='a'*64
        base=dict(partition='development',rows=8,data_sha256=binding,prompt_sha256=binding,
            protocol_sha256=binding,macro_f1=.5,action_tool_joint_accuracy=1.,status_tool_accuracy=1.,
            human_misses=[],false_refusals=[],unavailable_knowledge_retrievals=[],
            per_action={a:dict(support=1,precision=1.,recall=1.,f1=1.) for a in analysis.ft.prompts.ACTIONS})
        candidate=deepcopy(base);candidate['macro_f1']=.9
        reports={'base':base,'step-100':deepcopy(candidate),'step-200':deepcopy(candidate)}
        gates={v:analysis.ft.metrics.development_gate(base,reports[v],protocol['development_gate'])
            for v in ['step-100','step-200']}
        selection=dict(selected='step-100',gates=gates,passed=True,usage='development_candidate_only',
            default_provider_changed=False,calibration_evaluated=False,final_evaluated=False,protocol_sha256=binding)
        completion=dict(status='pilot_complete',selection=deepcopy(selection),protocol_sha256=binding,
            model_api_requests=0,deployed=False)
        return completion,selection,reports,{'config':protocol},binding

    def test_selection_recomputes_winner_and_complete_binding(self):
        args=self.selection_fixture()
        self.assertEqual(analysis.validate_selection(*args)['selected'],'step-100')
        for field,value in [('selected','step-999'),('passed',False),('usage','deployed'),
                ('protocol_sha256','b'*64),('default_provider_changed',True)]:
            changed=deepcopy(args);changed[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                analysis.validate_selection(*changed)

    def test_completion_protocol_and_embedded_selection_must_match(self):
        for field,value in [('protocol_sha256','b'*64),('model_api_requests',1),('deployed',True),
                ('selection',{}),('status','training')]:
            changed=deepcopy(self.selection_fixture());changed[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                analysis.validate_selection(*changed)

    def test_tool_failure_separates_routing_from_tool_selection(self):
        rows=[dict(id=str(i),annotation=dict(tool_name='explainApplicationStatus')) for i in range(4)]
        predictions={'0':dict(action='answer',tool_name=None),
            '1':dict(action='tool',tool_name='queryMyApplications'),
            '2':dict(action='tool',tool_name='explainApplicationStatus'),
            '3':dict(action='tool',tool_name='explainApplicationStatus')}
        m=analysis.tool_results(rows,predictions)['explainApplicationStatus']
        self.assertEqual(m['support'],4)
        self.assertEqual(m['routed_tool'],3)
        self.assertEqual(m['joint_accuracy'],.5)
        self.assertEqual(m['selected_correct_given_routed'],2/3)
        self.assertEqual(m['wrong_action_counts'],{'answer':1})

    def test_group_bootstrap_not_artificially_narrowed_by_same_story_replicas(self):
        rows=[dict(id='a',annotation=dict(action='answer'),curation=dict(partition_group='story-one')),
            dict(id='b',annotation=dict(action='answer'),curation=dict(partition_group='story-two'))]
        reference={'a':dict(action='clarify'),'b':dict(action='answer')}
        candidate={'a':dict(action='answer'),'b':dict(action='clarify')}
        original=analysis.cluster_interval(rows,reference,candidate,repeats=200)
        copies=[];old={};new={}
        for r in rows:
            for n in range(100):
                c=deepcopy(r);c['id']=r['id']+str(n);copies.append(c)
                old[c['id']]=reference[r['id']];new[c['id']]=candidate[r['id']]
        duplicated=analysis.cluster_interval(copies,old,new,repeats=200)
        self.assertEqual(original['interval95'],duplicated['interval95'])
        self.assertEqual(duplicated['cluster_count'],2)

    def test_paired_counts_net_equals_accuracy_correct_delta(self):
        rows=[dict(id=str(i),annotation=dict(action='answer')) for i in range(4)]
        old={str(i):dict(action='answer' if i<2 else 'clarify') for i in range(4)}
        new={str(i):dict(action='answer' if i>0 else 'clarify') for i in range(4)}
        result=analysis.changes(rows,old,new)
        self.assertEqual((result['improved'],result['regressed'],result['net']),(2,1,1))
        self.assertIn('do not append',result['usage'])


if __name__=='__main__':unittest.main()
