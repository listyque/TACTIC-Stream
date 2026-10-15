"""Run the identical server script in original/new private fixtures."""
from pathlib import Path
import sys


def run_security_lifecycle_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import security_lifecycle_contract
        return security_lifecycle_contract.run(case)
    finally:
        sys.path.remove(scripts)
