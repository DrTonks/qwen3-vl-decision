from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from qwenlab import financial_sampling_data as data


def row(rid, group, message='same', action='answer'):
    return dict(id=rid, scene_family_id=group, input={'message': message},
                annotation=dict(action=action, tool_name=None, tool_arguments={},
                                retrieval_collection=None, missing_slots=[]))


class PoolTests(unittest.TestCase):
    def test_conflict_quarantines_both_groups_and_siblings(self):
        rows = [row('a', 'g1'), row('b', 'g2', action='human'),
                row('c', 'g1', 'different'), row('d', 'safe', 'unrelated')]
        snapshot = deepcopy(rows)
        keep, quarantine = data.partition(rows, [])
        self.assertEqual([r['id'] for r in keep], ['d'])
        self.assertEqual({r['id'] for r in quarantine}, {'a', 'b', 'c'})
        self.assertEqual(rows, snapshot)

    def test_missing_slot_disagreement_is_a_label_conflict(self):
        rows = [row('a', 'g1', action='clarify'), row('b', 'g2', action='clarify')]
        rows[0]['annotation']['missing_slots'] = ['authentication']
        self.assertEqual(len(data.partition(rows, [])[1]), 2)

    def test_same_label_or_different_visible_state_not_conflict(self):
        rows = [row('a', 'g1'), row('b', 'g2')]
        self.assertEqual(len(data.partition(rows, [])[0]), 2)
        rows[1]['annotation']['action'] = 'human'
        rows[1]['input']['state'] = {'authenticated': False}
        self.assertEqual(len(data.partition(rows, [])[0]), 2)

    def test_heldout_whole_group_and_unknown_group(self):
        rows = [row('a', 'g1'), row('b', 'g1', 'other'), row('c', 'g2')]
        keep, quarantine = data.partition(rows, ['g1'])
        self.assertEqual([r['id'] for r in keep], ['c'])
        self.assertEqual(len(quarantine), 2)
        with self.assertRaises(ValueError):
            data.partition(rows, ['unknown'])

    def test_legacy_content_is_fixed_before_loader(self):
        with patch.object(data, 'sha', return_value='different'), patch.object(data.old, 'validate_train') as loader:
            with self.assertRaisesRegex(ValueError, 'frozen'):
                data.load_training_only()
            loader.assert_not_called()

    def test_manifest_cannot_skip_file_validation_or_grant_training(self):
        m = dict(version='financial-sampling-pool-v1', training_eligible=False,
                 status='design_only', sources={}, files={f: 'hash' for f in data.FILES})
        for broken in [dict(m, files={}), dict(m, training_eligible=True), dict(m, status='ready')]:
            with patch.object(data, 'read', return_value=broken):
                with self.assertRaises(ValueError):
                    data.verify()

    def test_output_refuses_overwrite_before_compute(self):
        with patch.object(data, 'OUT', Path(__file__).resolve().parent), patch.object(data, 'compute') as compute:
            with self.assertRaises(FileExistsError):
                data.build()
            compute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
