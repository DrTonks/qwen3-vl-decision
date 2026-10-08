from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import importlib.util
from unittest.mock import patch

from qwenlab import financial_supplement_pilot as p


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.source = p.read(p.DATA/'authoring.json')

    def test_budget_groups_and_ids(self):
        p.validate_source(self.source)
        for mutate in [lambda rows: rows.pop(), lambda rows: rows[0].update(id=rows[1]['id']),
                       lambda rows: rows[0].update(source_group='FSP1-G-C99'),
                       lambda rows: rows[0]['context'].update(authenticated=False),
                       lambda rows: rows[0].update(input_layer='node-projection')]:
            value=deepcopy(self.source); mutate(value)
            with self.assertRaises(ValueError): p.validate_source(value)

    def projected(self, source):
        spec, _ = p.protocol()
        value=dict(message=source['context']['message'],history=[],state={'authenticated':True,'handoff_status':'none'},
                   service_scope='loan_platform',capability_profile='current-node-no-kb',
                   capabilities={'knowledge_collections':[],'handoff_available':False},available_tools=spec['tools'],images=[])
        return dict(id=source['id'],input=value,inputAdapterVersion='test',inputSha256='test')

    def test_tool_parameter_must_agree_with_real_node_projection(self):
        row=next(r for r in self.source if r['expected_tool']=='queryApplicationDetail')
        projected=self.projected(row)
        with self.assertRaisesRegex(ValueError,'actual Node'):p.materialize(row,projected,p.protocol()[0])
        projected['input']['state']['application_id']=row['tool_arguments']['applicationId']
        result=p.materialize(row,projected,p.protocol()[0])
        self.assertNotIn('application_id',result['input']['state'])
        self.assertFalse(result['training_eligible']);self.assertFalse(result['human_reviewed'])
        self.assertEqual(result['provenance']['origin'],'ai_synthetic')

    def test_component_cannot_remove_only_source_of_target(self):
        row=deepcopy(next(r for r in self.source if r['expected_tool']=='queryApplicationDetail'))
        row['context']['message']='这笔的期数是多少'
        projected=self.projected(row);projected['input']['state']['application_id']=row['tool_arguments']['applicationId']
        with self.assertRaisesRegex(ValueError,'not visible'):p.materialize(row,projected,p.protocol()[0])

    def test_knowledge_requires_planned_profile(self):
        row=deepcopy(next(r for r in self.source if r['expected_action']=='retrieve'))
        result=p.materialize(row,self.projected(row),p.protocol()[0])
        self.assertEqual(result['input']['capability_profile'],'planned-kb')
        row['cohort']='current-service';row['input_layer']='node-projection'
        with self.assertRaises(ValueError):p.materialize(row,self.projected(row),p.protocol()[0])

    def test_empty_manifest_cannot_skip_candidate_hash(self):
        for manifest in [{}, dict.fromkeys(p.MANIFEST_FIELDS,None)]:
            manifest['files']={}
            with patch.object(p,'read',return_value=manifest):
                with self.assertRaisesRegex(ValueError,'exact known'):p.verify(Path('unused'),'unused')

    def test_old_build_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError): p.build('unused',p.DATA)

    def test_blind_screen_emits_only_candidate_identifiers(self):
        spec=importlib.util.spec_from_file_location('blind_screen',p.ROOT/'scripts/screen-financial-supplement-overlap.py')
        screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)
        candidate=[dict(id='NEW-1',input={'message':'请查询本人申请123的借款期数'})]
        heldout=[dict(id='SECRET-ID',input={'message':'请查询本人申请456的借款期数'},annotation={'action':'secret-label'})]
        result=screen.screen(candidate,heldout)
        self.assertEqual(result,[dict(candidate_id='NEW-1',kind='numeric_normalized_exact',similarity=1.0)])
        self.assertNotIn('456',str(result));self.assertNotIn('SECRET',str(result));self.assertNotIn('secret-label',str(result))
        self.assertEqual(screen.screen(candidate,[dict(input={'message':'我要了解宠物护理的步骤'})]),[])

    def finalizer(self):
        spec=importlib.util.spec_from_file_location('review_package',p.ROOT/'scripts/finalize-financial-supplement-review.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_review_quarantine_propagates_without_enabling_training(self):
        rows=p.read(p.DATA/'build-v2/candidates.json')
        labels=p.read(p.ROOT/'docs/evidence/financial-supplement-pilot-label-review-v2.json')
        digest=p.sha(p.DATA/'build-v2/candidates.json')
        labels=deepcopy(labels);labels['rows'][0]['decision']='quarantine'
        keep,blocked=self.finalizer().classify(rows,labels,dict(candidate_sha256=digest,quarantine_groups=[]),digest)
        self.assertIn(rows[1]['id'],{r['id'] for r in blocked})
        self.assertTrue(all(not r['training_eligible'] and not r['human_reviewed'] for r in keep+blocked))
        self.assertEqual(len(keep)+len(blocked),160)

    def test_review_requires_exact_coverage_and_row_binding(self):
        rows=p.read(p.DATA/'build-v2/candidates.json')
        labels=p.read(p.ROOT/'docs/evidence/financial-supplement-pilot-label-review-v2.json')
        digest=p.sha(p.DATA/'build-v2/candidates.json');blind=dict(candidate_sha256=digest,quarantine_groups=[])
        for mutate in [lambda d:d['rows'].pop(),lambda d:d['rows'][0].update(source_row_sha256='stale'),
                       lambda d:d.update(human_reviewed=True),lambda d:d.update(candidate_file_sha256='stale')]:
            changed=deepcopy(labels);mutate(changed)
            with self.assertRaises(ValueError):self.finalizer().classify(rows,changed,blind,digest)


if __name__=='__main__':unittest.main()
