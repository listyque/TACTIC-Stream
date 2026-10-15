"""Execute the same business script in both kernels."""
from pathlib import Path
import sys


def run_business_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import business_contract
        return business_contract.run(case)
    finally:
        sys.path.remove(scripts)
