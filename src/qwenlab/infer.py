"""Standalone text inference; candidate projection on by default, full fallback."""
import argparse
import json
from qwenlab.common import ROOT, load_json
from qwenlab.joint_v5 import encode, exclusive_lock
from qwenlab.modeling import load_model


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Project-relative JSON request, no labels needed')
    p.add_argument('--adapter', default='.local/checkpoints/joint-v4/step-1582')
    p.add_argument('--projection', choices=['candidate', 'full'], default='candidate')
    args = p.parse_args()
    path = (ROOT / args.input).resolve(); request = load_json(path)
    if not isinstance(request.get('message'), str): raise ValueError('message must be text')
    if request.get('images'): raise NotImplementedError('Image inference has not been validated')
    # Label placeholders satisfy the frozen encoder's target bookkeeping only;
    # labels are excluded by input_state and cannot influence the prompt.
    row = {k: request[k] for k in ('message', 'history', 'state', 'available_tools', 'images') if k in request}
    row.update(id='inference', dataset='business', labels={'intent': 'general', 'route': 'clarify', 'tool': 'none'})
    # Do not contend with the running v5 GPU worker.
    with exclusive_lock('joint-v5-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'):
        from qwenlab.candidate_inference import CandidateScorer
        tok, model = load_model('nf4', None if args.adapter == 'base' else args.adapter)
        tok.padding_side = 'left'; model.eval(); scorer = CandidateScorer(model, args.projection)
        results = {}
        for task in ('intent', 'route', 'tool'):
            example = encode(tok, row, task)
            inputs = tok.pad([example['tokens']], padding=True, return_tensors='pt').to('cuda')
            probabilities = scorer.scores(inputs, example['ids'])[0].softmax(-1).cpu().tolist()
            results[task] = {'choice': example['keys'][max(range(len(probabilities)), key=probabilities.__getitem__)],
                             'probabilities': dict(zip(example['keys'], probabilities))}
        if results['route']['choice'] != 'tool': results['tool'] = {'choice': 'none', 'derived': True}
        print(json.dumps({'predictions': results, 'projection': scorer.projection,
                          'fallback_reason': scorer.fallback_reason, 'policy': 'decision-v5; three-task experiment',
                          'real_tools_executed': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
