from pathlib import Path
import sys


def run_workflow_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import workflow_contract
        return workflow_contract.run(case)
    finally:
        sys.path.remove(scripts)
