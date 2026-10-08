"""Exercise real Flask <-> Node HTTP using explicit fixtures, no GPU/DB/API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading

from qwenlab.common import ROOT
from qwenlab.financial_serve_v2 import FixtureEngine, create_app, protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root', type=Path, default=ROOT.parent / 'uestc_Integrated_Design' / '后端')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/financial-v2-http-smoke.json')
    args = parser.parse_args()
    verifier = args.backend_root / 'scripts/verify-financial-v2-http.cjs'
    backend_spec = args.backend_root / 'services/customerSupport/policies/support-financial-v2.json'
    spec, digest = protocol()
    if hashlib.sha256(backend_spec.read_bytes()).hexdigest() != digest:
        raise SystemExit('Backend and Flask policy bytes differ')
    node = shutil.which('node')
    if not node or not verifier.is_file():
        raise SystemExit('Node runtime or backend verification script missing')
    key = secrets.token_urlsafe(32)
    calls = []

    class ExplicitFixture(FixtureEngine):
        def predict(self, value, task):
            action = value['message'].removeprefix('fixture:')
            if value['message'] != 'fixture:' + action or action not in spec['actions']:
                raise ValueError('Only exact integration-fixture messages are accepted')
            calls.append(task)
            keys = spec['actions'] if task == 'action' else spec['tools']
            choice = action if task == 'action' else 'queryMyCreditScore'
            return dict(choice=choice, probabilities={k: float(k == choice) for k in keys})

    from werkzeug.serving import make_server, WSGIRequestHandler
    class QuietHandler(WSGIRequestHandler):
        def log(self, *args, **kwargs):
            pass

    app = create_app(ExplicitFixture(spec, digest, 'answer', 'queryMyCreditScore'), key)
    server = make_server('127.0.0.1', 0, app, request_handler=QuietHandler, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = {**os.environ, 'FINANCIAL_VERIFY_URL': f'http://127.0.0.1:{server.server_port}/decide', 'FINANCIAL_VERIFY_KEY': key}
        result = subprocess.run([node, str(verifier)], cwd=args.backend_root, env=env,
                                encoding='utf-8', capture_output=True, timeout=45)
        if result.returncode:
            raise RuntimeError('Node integration check failed: ' + result.stderr[-2000:])
        report = json.loads(result.stdout)
        report.update(policy_sha256=digest, fixture_only=True, model_calls=0, database_calls=0,
                      external_api_calls=0, observed_http_inference_calls=dict(action=calls.count('action'), tool=calls.count('tool')))
        report['source_sha256'] = {
            'qwen/scripts/verify-financial-v2-http.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'qwen/src/qwenlab/financial_serve_v2.py': hashlib.sha256((ROOT / 'src/qwenlab/financial_serve_v2.py').read_bytes()).hexdigest(),
            'backend/scripts/verify-financial-v2-http.cjs': hashlib.sha256(verifier.read_bytes()).hexdigest()
        }
        for name in ['financialContract.js', 'financialProvider.js', 'financialOrchestrator.js', 'tools.js', 'parameters.js', 'contract.js', 'responses.js']:
            report['source_sha256']['backend/services/customerSupport/' + name] = hashlib.sha256(
                (args.backend_root / 'services/customerSupport' / name).read_bytes()).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


if __name__ == '__main__':
    main()
