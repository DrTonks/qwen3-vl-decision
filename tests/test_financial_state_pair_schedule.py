from collections import Counter
from copy import deepcopy
import unittest

from qwenlab import financial_state_pair_schedule as s


class PairScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old,cls.new,cls.steps,cls.pairs=s.load_sources()
        cls.cfg=s.read(s.CONFIG)
        cls.plan,cls.changes=s.make_plan(cls.old,cls.new,cls.steps,cls.pairs,cls.cfg)
        cls.idx={r['id']:r for r in cls.old+cls.new}
        cls.flat=[i for step in cls.plan['step_rows'] for i in step]

    def validate(self,plan):
        s.validate_plan(self.old,self.new,self.steps,self.pairs,plan,self.cfg)

    def test_every_new_row_once_each_half(self):
        for part in (self.flat[:1600],self.flat[1600:]):
            counts=Counter(part)
            self.assertTrue(all(counts[r['id']]==1 for r in self.new))

    def test_input_and_annotation_unchanged_in_metadata_migration(self):
        candidates=s.read(s.CANDIDATES/'reviewed-candidates.json')
        for before,after in zip(candidates,self.new):
            self.assertEqual(before['input'],after['input']);self.assertEqual(before['annotation'],after['annotation'])
            self.assertEqual(after['split'],'train');self.assertIs(after['training_eligible'],False)

    def test_exact_position_cells_and_old_anchors(self):
        old=[i for step in self.steps for i in step]
        anchors={i for p in self.pairs for i in p['row_ids']}
        self.assertTrue(anchors<=set(self.flat[:1600]))
        for before,after in zip(old,self.flat):
            self.assertEqual(s.cell(self.idx[before]),s.cell(self.idx[after]))
            if before in anchors:self.assertEqual(before,after)

    def test_candidate_lost_from_first_half_fails(self):
        value=deepcopy(self.plan);target=self.new[0]['id']
        p=self.flat.index(target);value['step_rows'][p//8][p%8]=self.steps[p//8][p%8]
        value['prefix_200_steps']=deepcopy(value['step_rows'][:200])
        with self.assertRaises(ValueError):self.validate(value)

    def test_cell_shift_fails(self):
        value=deepcopy(self.plan)
        first=value['step_rows'][0][0]
        other=next(i for i in self.flat if s.cell(self.idx[i])!=s.cell(self.idx[first]))
        value['step_rows'][0][0]=other;value['prefix_200_steps']=deepcopy(value['step_rows'][:200])
        with self.assertRaisesRegex(ValueError,'cell'):self.validate(value)

    def test_unknown_row_fails(self):
        value=deepcopy(self.plan);value['step_rows'][0][0]='NONEXISTENT'
        with self.assertRaisesRegex(ValueError,'row IDs'):self.validate(value)

    def test_inconsistent_prefix_fails(self):
        value=deepcopy(self.plan);value['prefix_200_steps']=[]
        with self.assertRaisesRegex(ValueError,'Prefix'):self.validate(value)

    def test_training_enable_cannot_be_smuggled(self):
        value=deepcopy(self.plan);value['training_enabled']=True
        with self.assertRaisesRegex(ValueError,'enable'):self.validate(value)
        cfg=deepcopy(self.cfg);cfg['training_enabled']=True
        with self.assertRaises(ValueError):s.check_config(cfg)

    def test_input_order_does_not_change_schedule(self):
        plan,changes=s.make_plan(list(reversed(self.old)),list(reversed(self.new)),self.steps,self.pairs,self.cfg)
        self.assertEqual(plan,self.plan);self.assertEqual(changes,self.changes)

    def test_no_donor_fails_without_changing_budget(self):
        altered=deepcopy(self.new)
        row=altered[0];row['annotation']['action']='retrieve';row['annotation']['tool_name']=None
        with self.assertRaisesRegex(ValueError,'No same-cell donor'):s.make_plan(self.old,altered,self.steps,self.pairs,self.cfg)

    def test_maximum_exposure_caps_hold(self):
        self.assertLessEqual(max(Counter(self.flat).values()),4)
        self.assertLessEqual(max(Counter(self.idx[i]['scene_family_id'] for i in self.flat).values()),16)
        self.assertEqual(len(self.changes),281)


if __name__=='__main__':unittest.main()
