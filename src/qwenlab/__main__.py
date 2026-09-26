"""Small CLI dispatcher; all commands resolve paths from the project root."""
import importlib
import sys

COMMANDS = {
    "download-model": "download_model", "download-public": "download_public", "download-crosswoz": "download_crosswoz",
    "build-business": "build_dataset", "local": "run_local", "jev": "run_jev",
    "summarize": "summarize", "calibrate-v1": "calibrate", "route-gate": "apply_route_gate",
    "prepare": "prepare_v2", "evaluate": "evaluate", "train": "train",
    "calibrate": "calibrate_v2", "report": "report_v2", "audit": "publish",
}

def main():
    if len(sys.argv)<2 or sys.argv[1] in ("-h","--help"):
        print("qwen-lab <command> [options]\nCommands: " + ", ".join(COMMANDS))
        return
    command=sys.argv.pop(1)
    if command not in COMMANDS: raise SystemExit("Unknown command: " + command)
    importlib.import_module("qwenlab."+COMMANDS[command]).main()

if __name__=="__main__": main()
