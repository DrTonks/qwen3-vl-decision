from collections import Counter
from copy import deepcopy
import random
import unittest
from unittest.mock import patch
from qwenlab import financial_preauth_schedule as m


def fixture():
    rows=[];steps=[];fixed=[]
    def add(rid,auth,kb,action='answer',missing=()):
        row=dict(id=rid,scene_family_id='group-'+rid,split='train',training_eligible=False,
            cohort='current-service' if auth else 'preauth-robustness',
            input_layer='node-projection' if auth else 'preauth-component',
            input=dict(state=dict(authenticated=auth),capabilities=dict(knowledge_collections=['docs'] if kb else [])),
            annotation=dict(action=action,tool_name=None,missing_slots=list(missing)))
        rows.append(row);return rid
    for i in range(2720):fixed.append(add(f'a{i:04}',True,False))
    no=[add(f'n{i:03}',False,False,'clarify' if i%3==0 else 'answer',('authentication',) if i%3==0 else ()) for i in range(344)]
    kb=[add(f'k{i:03}',False,True,'retrieve' if i%3==0 else 'answer') for i in range(500)]
    old_pre=no[:19]+kb[:461];flat=[]
    for i in range(160):flat.extend(fixed[i*17:(i+1)*17]+old_pre[i*3:(i+1)*3])
    return rows,[flat[i:i+8] for i in range(0,3200,8)],m.read(m.CONFIG)


class PreauthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,cls.old,cls.cfg=fixture();cls.plan=m.make_plan(cls.rows,cls.old,cls.cfg)

    def test_preserves_2720_exact_positions_and_unique_preauth(self):
        idx={r['id']:r for r in self.rows};old=sum(self.old,[]);new=sum(self.plan['step_rows'],[])
        fixed=[i for i,r in enumerate(old) if idx[r]['input']['state']['authenticated']]
        self.assertEqual(len(fixed),2720)
        self.assertTrue(all(old[i]==new[i] for i in fixed))
        pre=[r for r in new if not idx[r]['input']['state']['authenticated']]
        self.assertEqual(len(set(pre)),480)
        self.assertEqual(sum(r.startswith('n') for r in pre),320)

    def test_order_independent_and_does_not_consume_global_rng(self):
        before=random.getstate()
        self.assertEqual(m.make_plan(list(reversed(self.rows)),self.old,self.cfg),self.plan)
        self.assertEqual(before,random.getstate())

    def test_prefix_is_not_resampled(self):
        self.assertEqual(self.plan['prefix_200_steps'],self.plan['step_rows'][:200])
        flat=sum(self.plan['prefix_200_steps'],[])
        self.assertEqual((sum(x.startswith('n') for x in flat),sum(x.startswith('k') for x in flat)),(160,80))

    def test_fixed_position_swap_is_rejected(self):
        bad=deepcopy(self.plan);bad['step_rows'][0][:2]=reversed(bad['step_rows'][0][:2])
        with self.assertRaises(ValueError):m.validate_plan(self.rows,self.old,bad,self.cfg)

    def test_preauth_duplicate_is_rejected(self):
        bad=deepcopy(self.plan);flat=sum(bad['step_rows'],[]);pos=[i for i,x in enumerate(flat) if x.startswith('n')]
        flat[pos[1]]=flat[pos[0]];bad['step_rows']=[flat[i:i+8] for i in range(0,3200,8)]
        with self.assertRaises(ValueError):m.validate_plan(self.rows,self.old,bad,self.cfg)

    def test_global_group_cap_counts_fixed_authenticated_exposure(self):
        rs=deepcopy(self.rows)
        for r in rs[:17]:r['scene_family_id']='one-group'
        with self.assertRaises(ValueError):m.make_plan(rs,self.old,self.cfg)

    def test_eval_role_and_truthy_authentication_rejected(self):
        for field,value in [('split','development'),('training_eligible',True)]:
            rs=deepcopy(self.rows);rs[0][field]=value
            with self.assertRaises(ValueError):m.make_plan(rs,self.old,self.cfg)
        rs=deepcopy(self.rows);rs[0]['input']['state']['authenticated']='false'
        with self.assertRaises(ValueError):m.make_plan(rs,self.old,self.cfg)

    def test_largest_remainder_preserves_nonempty_buckets_and_ties(self):
        self.assertEqual(m.allocate({'c':3,'b':3,'a':3},5),{'a':2,'b':2,'c':1})
        self.assertEqual(m.allocate({'a':1,'b':8},2),{'a':1,'b':1})
        for total in (1,10):
            with self.assertRaises(ValueError):m.allocate({'a':1,'b':8},total)

    def test_capacity_failure_does_not_relax_or_skip_bucket(self):
        rows=deepcopy(self.rows[-5:])
        for r in rows:r['scene_family_id']='full'
        with self.assertRaises(ValueError):m.choose(rows,2,Counter(full=16),1)
        with self.assertRaises(ValueError):m.choose(rows,3,Counter(full=14),1)

    def test_missing_slot_normalization_does_not_mutate_source(self):
        row=deepcopy(self.rows[2720]);row['annotation']['missing_slots']=['applicationId','application_id','authentication']
        before=deepcopy(row)
        self.assertEqual(m.bucket(row),'clarify|application_id+authentication')
        self.assertEqual(row,before)

    def test_kb_exclusion_uses_all_no_kb_groups_before_selection(self):
        rs=deepcopy(self.rows);idx={r['id']:r for r in rs}
        idx['k000']['scene_family_id']=idx['n343']['scene_family_id']
        p=m.make_plan(rs,self.old,self.cfg)
        self.assertNotIn('k000',sum(p['step_rows'],[]))

    def test_block_ratio_and_coverage_tampering_rejected(self):
        bad=deepcopy(self.plan);bad['bucket_quotas']['no_kb']['answer|none_declared']+=1
        with self.assertRaises(ValueError):m.validate_plan(self.rows,self.old,bad,self.cfg)
        bad=deepcopy(self.plan);bad['prefix_200_steps']=bad['step_rows'][1:201]
        with self.assertRaises(ValueError):m.validate_plan(self.rows,self.old,bad,self.cfg)

    def test_no_partial_pool_can_silently_bypass_required_count(self):
        rs=[r for r in self.rows if not r['id'].startswith('n') or int(r['id'][1:])<200]
        with self.assertRaises(ValueError):m.make_plan(rs,self.old,self.cfg)

    def test_new_training_permission_or_budget_rejected(self):
        for key,value in [('training_enabled',True),('steps',401),('seed',7)]:
            cfg=deepcopy(self.cfg);cfg[key]=value
            with self.assertRaises(ValueError):m.make_plan(self.rows,self.old,cfg)

    def test_existing_publication_never_overwritten(self):
        with patch.object(type(m.OUT),'exists',return_value=True):
            with self.assertRaises(FileExistsError):m.prepare()


if __name__=='__main__':unittest.main()
