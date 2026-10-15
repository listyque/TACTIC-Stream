"""Execute unchanged account/Security code on private old and new fixtures."""
from pathlib import Path
import sys


def run_security_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import security_contract
        return security_contract.run(case)
    finally:
        sys.path.remove(scripts)
