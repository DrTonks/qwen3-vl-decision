"""Read-only progress and rough training ETA; never starts a training job."""
import argparse
from datetime import datetime, timedelta
import json
import time
from qwenlab.common import ROOT, load_json


def estimate(logs, total):
    if not logs: return None
    recent = logs[-101:]
    if len(recent) < 2: return None
    delta_steps = recent[-1]['step'] - recent[0]['step']
    if delta_steps <= 0: return None
    seconds = (recent[-1]['elapsed_s'] - recent[0]['elapsed_s']) / delta_steps
    if seconds <= 0: return None
    return {'step': recent[-1]['step'], 'total': total, 'progress_percent': 100 * recent[-1]['step'] / total,
            'seconds_per_step': seconds, 'remaining_training_s': max(0, total - recent[-1]['step']) * seconds,
            'observed_steps': delta_steps}


def snapshot():
    folder = ROOT / 'results/joint-v5'; status_path = folder / 'status.json'
    status = load_json(status_path) if status_path.exists() else {'status': 'not_started'}
    summary_path = folder / 'training-summary.json'
    result = {'checked_at': datetime.now().astimezone().isoformat(timespec='seconds'), **status}
    if summary_path.exists():
        summary = load_json(summary_path); logs = []; path = folder / 'train.jsonl'
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                try: logs.append(json.loads(line))
                except json.JSONDecodeError: break  # A live append may be partial; never edit it.
        result['training_status'] = summary['status']
        result['training'] = estimate(logs, summary['total_steps'])
        if result['training']:
            result['epoch_fraction'] = result['training']['step'] / summary['steps_per_epoch']
            result['training']['rough_finish_local'] = (datetime.now().astimezone() + timedelta(seconds=result['training']['remaining_training_s'])).isoformat(timespec='minutes')
        result['log_age_s'] = round(time.time() - path.stat().st_mtime, 1) if path.exists() else None
        result['possibly_stale'] = status.get('stage') == 'training' and (result['log_age_s'] is None or result['log_age_s'] > 180)
        if result['possibly_stale'] and result.get('training'):
            result['training'].pop('rough_finish_local', None)
    checkpoint = folder / 'latest-checkpoint.json'
    result['latest_checkpoint'] = load_json(checkpoint)['step'] if checkpoint.exists() else None
    result['eta_scope'] = 'Training only; excludes checkpoint evaluation, calibration/test inference and action probe. Recent speed, not a promise; stale logs do not prove process alive.'
    return result


def display(result):
    print(f"[{result['checked_at']}] 流程：{result.get('status')} / {result.get('stage', '-')}")
    train = result.get('training')
    if train:
        print(f"训练 {train['step']}/{train['total']} 步（{train['progress_percent']:.2f}%），已完成 {result['epoch_fraction']:.3f} 轮")
        print(f"最近 {train['observed_steps']} 步平均 {train['seconds_per_step']:.2f} 秒/步；训练预计剩余 {train['remaining_training_s']/3600:.2f} 小时")
        print('训练预计结束：', train.get('rough_finish_local', '日志可能停滞，暂不显示结束时间'))
        print(f"最近日志距今 {result['log_age_s']} 秒；已保存检查点 {result['latest_checkpoint']}")
    if result.get('possibly_stale'): print('注意：训练日志超过3分钟未更新，请结合进程和错误日志检查。')
    print('估时不含训练后的评测；受输入长度、温度和其他GPU任务影响。\n', flush=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--watch', action='store_true'); p.add_argument('--json', action='store_true'); args = p.parse_args()
    try:
        while True:
            result = snapshot()
            if args.json: print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            else: display(result)
            if not args.watch or result.get('status') in ('complete', 'failed', 'not_started'): break
            time.sleep(15)
    except KeyboardInterrupt: print('已停止查看；后台训练不受影响。')


if __name__ == '__main__': main()
