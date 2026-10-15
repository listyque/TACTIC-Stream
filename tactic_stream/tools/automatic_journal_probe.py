"""Run an unchanged server script in either kernel's private fixture."""
from pathlib import Path
import sys


def run_automatic_journal_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        import automatic_journal_contract
        return automatic_journal_contract.run(case)
    finally:
        sys.path.remove(scripts)
