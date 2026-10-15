"""Run the same access-rule server script in original and new private kernels."""
from pathlib import Path
import sys


def run_access_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import access_contract
        return access_contract.run(case)
    finally:
        sys.path.remove(scripts)
