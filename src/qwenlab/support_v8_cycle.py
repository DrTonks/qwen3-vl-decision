"""One supervised V8 cycle; subprocess boundary releases training GPU memory."""
import argparse
import subprocess
import sys
from qwenlab.common import ROOT, load_json
from qwenlab.joint_v5 import exclusive_lock


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    with exclusive_lock('support-v8-cycle.lock'):
        state_path=ROOT/'results/support-v8/status.json'
        state=load_json(state_path) if state_path.exists() else {}
        if state.get('stage') not in ('complete','stopped_at_gate'):
            command=[sys.executable,'-u','-m','qwenlab.support_train_v8','run']
            if args.resume: command.append('--resume')
            subprocess.run(command,cwd=ROOT,check=True)
        subprocess.run([sys.executable,'-u','-m','qwenlab.support_v8_finalize'],cwd=ROOT,check=True)


if __name__=='__main__': main()
