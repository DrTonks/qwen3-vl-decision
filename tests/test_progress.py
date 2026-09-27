from contextlib import redirect_stdout
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from qwenlab.progress import evaluation_progress, display


class ProgressTests(unittest.TestCase):
    def test_evaluation_counts_task_forwards_without_retraining(self):
        manifest = {'files': {f'{name}-{split}.jsonl': {'rows': 10}
                    for name in ('business', 'massive', 'crosswoz') for split in ('calibration', 'test')}}
        with patch('qwenlab.progress.load_json', return_value=manifest), patch.object(Path, 'exists', return_value=True), \
             patch('qwenlab.progress.count_complete', side_effect=lambda p: 4 if p.name == 'business-calibration.jsonl' else 0):
            result = evaluation_progress(Path('results'), {'stage': 'frozen-evaluation', 'variant': 'step-7110'})
        self.assertEqual(result['done'], 4); self.assertEqual(result['total'], 60)
        self.assertEqual(result['forward_units_done'], 12); self.assertEqual(result['forward_units_total'], 100)

    def test_completed_training_does_not_claim_whole_workflow_done(self):
        output = io.StringIO()
        with redirect_stdout(output):
            display({'checked_at': 'now', 'status': 'running', 'stage': 'frozen-evaluation',
                'training_status': 'complete', 'training': {'step': 7110, 'total': 7110},
                'training_elapsed_minutes': 579.3, 'projection_validation': {'status': 'waiting'},
                'evaluation': {'key': 'test', 'done': 10, 'total': 100, 'files': []}})
        text = output.getvalue()
        self.assertIn('训练已完成', text); self.assertIn('当前评测 10/100', text)
        self.assertNotIn('训练预计结束', text)


if __name__ == '__main__': unittest.main()
