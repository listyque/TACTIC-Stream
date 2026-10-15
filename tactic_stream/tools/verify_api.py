"""Run the existing suite and record transport evidence without request data."""
import json
import argparse
from pathlib import Path
import sys
from threading import Lock
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.screenshots/api-block6-runtime.json')
    parser.add_argument('tests', nargs='*', help='Unittest names; omit for the full suite')
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]
    from tactic_stream.server.api import Api, SUPPORTED_METHODS
    counts = {}
    lock = Lock()
    dispatch = Api.dispatch

    def measured(self, method, *args, **kwargs):
        outcome = 'success'
        try:
            return dispatch(self, method, *args, **kwargs)
        except Exception as error:
            outcome = type(error).__name__
            raise
        finally:
            with lock:
                outcomes = counts.setdefault(method, {})
                outcomes[outcome] = outcomes.get(outcome, 0) + 1

    suite = (unittest.defaultTestLoader.loadTestsFromNames(args.tests) if args.tests
             else unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    if unittest.defaultTestLoader.errors:
        raise RuntimeError('\n'.join(unittest.defaultTestLoader.errors))
    with patch.object(Api, 'dispatch', measured):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {
        'version': __import__('tactic_stream').__version__,
        'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'successful': result.wasSuccessful(),
        'limits': 'Private fixture calls through Api.dispatch only. Counts prove exercised entry points, not full behavior parity. Native direct calls and child processes are not counted. No arguments, credentials, paths or project data are recorded.',
        'methods': {name: counts.get(name, {}) for name in sorted(SUPPORTED_METHODS)},
        'unexpected_methods': {name: value for name, value in sorted(counts.items()) if name not in SUPPORTED_METHODS},
    }
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print('Transport evidence:', output)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
