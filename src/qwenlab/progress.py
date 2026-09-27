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


def count_complete(path):
    return path.read_bytes().count(b'\n') if path.exists() else 0


def evaluation_progress(folder, status):
    manifest_path = folder / 'data-manifest.json'
    if not manifest_path.exists(): return None
    manifest = load_json(manifest_path)['files']; stage = status.get('stage')
    variant = status.get('variant'); tasks = []
    if variant and stage in ('reference-dev', 'checkpoint-dev', 'frozen-evaluation'):
        splits = ['calibration', 'test'] if stage == 'frozen-evaluation' else ['dev']
        for split in splits:
            for name in ('business', 'massive', 'crosswoz'):
                filename = f'{name}-{split}.jsonl'; path = folder / variant / filename
                total = manifest[filename]['rows']; done = min(total, count_complete(path))
                tasks.append({'name': filename, 'done': done, 'total': total,
                              'forwards_per_row': 3 if name == 'business' else 1,
                              'metrics_saved': (folder / variant / f'{name}-{split}-metrics.json').exists()})
    elif stage == 'action-probe':
        total = manifest['business-dev.jsonl']['rows']
        tasks.append({'name': 'action-probe/predictions.jsonl',
                      'done': min(total, count_complete(folder / 'action-probe/predictions.jsonl')),
                      'total': total, 'forwards_per_row': 2,
                      'metrics_saved': (folder / 'action-probe/metrics.json').exists()})
    if not tasks: return None
    return {'key': f'{stage}/{variant}', 'files': tasks,
            'done': sum(t['done'] for t in tasks), 'total': sum(t['total'] for t in tasks),
            'forward_units_done': sum(t['done'] * t['forwards_per_row'] for t in tasks),
            'forward_units_total': sum(t['total'] * t['forwards_per_row'] for t in tasks)}


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
            if summary['status'] != 'complete':
                result['training']['rough_finish_local'] = (datetime.now().astimezone() + timedelta(seconds=result['training']['remaining_training_s'])).isoformat(timespec='minutes')
        result['training_elapsed_minutes'] = round(summary.get('elapsed_s', 0) / 60, 1)
        result['log_age_s'] = round(time.time() - path.stat().st_mtime, 1) if path.exists() else None
        result['possibly_stale'] = status.get('stage') == 'training' and (result['log_age_s'] is None or result['log_age_s'] > 180)
        if result['possibly_stale'] and result.get('training'):
            result['training'].pop('rough_finish_local', None)
    checkpoint = folder / 'latest-checkpoint.json'
    result['latest_checkpoint'] = load_json(checkpoint)['step'] if checkpoint.exists() else None
    result['evaluation'] = evaluation_progress(folder, status)
    projection = folder / 'projection-inference/status.json'
    result['projection_validation'] = load_json(projection) if projection.exists() else {'status': 'not_scheduled'}
    comparison = {}
    for name in ('jev', 'local'):
        path = folder / 'comparison' / f'{name}-status.json'
        if path.exists():
            value = load_json(path)
            if value.get('status') == 'running' and value.get('completed', 0):
                if name == 'jev': elapsed = value.get('elapsed_s', 0)
                else:
                    elapsed = 0
                    timing = folder / 'comparison/local-latency.jsonl'
                    if timing.exists():
                        for line in timing.read_text(encoding='utf-8').splitlines():
                            try: elapsed += json.loads(line)['elapsed_s']
                            except json.JSONDecodeError: break
                value['remaining_minutes_estimate'] = max(0, value['total'] - value['completed']) * elapsed / value['completed'] / 60
            comparison[name] = value
    result['comparison'] = comparison
    length_path = folder / 'length-benchmark/status.json'
    if length_path.exists():
        length = load_json(length_path)
        if length.get('status') == 'running' and length.get('completed', 0) >= 24:
            length['remaining_minutes_estimate'] = (length['total'] - length['completed']) * length.get('elapsed_s', 0) / length['completed'] / 60
        result['length_benchmark'] = length
    result['eta_scope'] = 'Training ETA or current evaluation stage only; excludes subsequent stages and loading. Watch estimates evaluation speed from new completed rows. Projection worker currently writes agreement results at end, so no invented live percentage.'
    return result


def display(result):
    print(f"[{result['checked_at']}] 流程：{result.get('status')} / {result.get('stage', '-')}")
    train = result.get('training')
    if train and result.get('training_status') == 'complete':
        print(f"训练已完成：{train['step']}/{train['total']}步，用时 {result['training_elapsed_minutes']:.1f} 分钟；各项评测状态见下方。")
    elif train:
        print(f"训练 {train['step']}/{train['total']} 步（{train['progress_percent']:.2f}%），已完成 {result['epoch_fraction']:.3f} 轮")
        print(f"最近 {train['observed_steps']} 步平均 {train['seconds_per_step']:.2f} 秒/步；训练预计剩余 {train['remaining_training_s']/3600:.2f} 小时")
        print('训练预计结束：', train.get('rough_finish_local', '日志可能停滞，暂不显示结束时间'))
        print(f"最近日志距今 {result['log_age_s']} 秒；已保存检查点 {result['latest_checkpoint']}")
    if result.get('possibly_stale'): print('注意：训练日志超过3分钟未更新，请结合进程和错误日志检查。')
    evaluation = result.get('evaluation')
    if evaluation:
        print(f"当前评测 {evaluation['done']}/{evaluation['total']} 条（{100*evaluation['done']/evaluation['total']:.1f}%），范围：{evaluation['key']}")
        for task in evaluation['files']:
            label = '完成' if task['metrics_saved'] else ('预测已写完，等待统计/计时' if task['done'] == task['total'] else '待完成')
            print(f"  {task['name']}: {task['done']}/{task['total']} [{label}]")
        if 'remaining_stage_minutes' in evaluation:
            print(f"按近期吞吐粗估当前预测阶段剩余 {evaluation['remaining_stage_minutes']:.1f} 分钟（不含后续阶段/加载）。")
        elif evaluation['done'] < evaluation['total']: print('持续查看约30秒后显示当前阶段的分钟估算。')
    print('输出层裁剪验证：', result['projection_validation']['status'])
    if result['projection_validation']['status'] == 'running': print('完整裁剪验证正在运行；逐条进度暂不落盘，不显示虚构百分比。')
    for name, status in result.get('comparison', {}).items():
        print(f"新增同输入对照 {name}: {status['status']}，{status.get('completed', 0)}/{status.get('total', '?')}")
        if 'remaining_minutes_estimate' in status: print(f"  此部分粗估剩余 {status['remaining_minutes_estimate']:.1f} 分钟；不含加载。")
    length = result.get('length_benchmark')
    if length:
        print(f"输入长度对照：{length['status']}，{length.get('completed', 0)}/{length.get('total', '?')}，API失败 {length.get('api_errors', 0)}")
        if 'remaining_minutes_estimate' in length: print(f"  粗估剩余 {length['remaining_minutes_estimate']:.1f} 分钟；包含已发生等待，网络波动会影响估计。")
    print('预测写完不等于整个流程结束；速度受输入长度、温度和其他GPU任务影响。\n', flush=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--watch', action='store_true'); p.add_argument('--json', action='store_true'); args = p.parse_args()
    observations = []
    try:
        while True:
            result = snapshot()
            current = result.get('evaluation'); now = time.monotonic()
            if current:
                if observations and observations[-1][1] != current['key']: observations.clear()
                observations.append((now, current['key'], current['forward_units_done']))
                observations = observations[-9:]
                elapsed = now - observations[0][0]; delta = current['forward_units_done'] - observations[0][2]
                if elapsed >= 25 and delta > 0 and current['forward_units_done'] < current['forward_units_total']:
                    current['remaining_stage_minutes'] = (current['forward_units_total'] - current['forward_units_done']) / (delta / elapsed) / 60
            if args.json: print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            else: display(result)
            comparison_active = any(v.get('status') in ('starting', 'loading', 'running') for v in result.get('comparison', {}).values())
            comparison_active = comparison_active or result.get('length_benchmark', {}).get('status') in ('loading', 'running')
            all_done = result.get('status') == 'complete' and result['projection_validation']['status'] in ('complete', 'failed', 'not_scheduled') and not comparison_active
            if not args.watch or all_done or result.get('status') in ('failed', 'not_started'): break
            time.sleep(15)
    except KeyboardInterrupt: print('已停止查看；后台训练不受影响。')


if __name__ == '__main__': main()
