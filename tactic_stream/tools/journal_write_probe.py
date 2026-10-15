"""Run the identical journal server script on temporary fixtures only."""
from pathlib import Path
import sys


def run_journal_write_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import journal_write_contract
        return journal_write_contract.run(case)
    finally:
        sys.path.remove(scripts)
