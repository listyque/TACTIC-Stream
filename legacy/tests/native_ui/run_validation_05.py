"""Repeat native UI tests with a FRESH synthetic CherryPy backend per suite.

Run from the source fork with its supported Python environment. Playwright and
Chromium are developer-only dependencies. The default browser transport is
native; --bridge is explicit and records its cookie/navigation/CSP limitation.
This is not the production launcher and never connects to a user database.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / 'tests/native_ui'


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def execute(command: list[str], log: Path, timeout: int = 240) -> dict:
    start = time.monotonic()
    with log.open('w', encoding='utf-8') as stream:
        stream.write('COMMAND: ' + json.dumps(command, ensure_ascii=False) + '\n')
        stream.flush()
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write('\nVALIDATION TIMEOUT\n')
            code = 124
    result = {'return_code': code, 'seconds': round(time.monotonic()-start, 3),
              'log': str(log.relative_to(ROOT)) if log.is_relative_to(ROOT) else str(log)}
    if 'unittest' in command:
        matches = re.findall(r'^Ran (\d+) tests? in ', log.read_text(encoding='utf-8'), re.M)
        result['tests'] = int(matches[-1]) if matches else None
    return result


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def fixture_suite(name: str, output: Path, args: argparse.Namespace) -> dict:
    port = free_port()
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ, TACTIC_FIXTURE_PORT=str(port),
               TACTIC_FIXTURE_ERROR_LOG=str(output / f'{name}-server-error.log'))
    # TEST-only mount configuration is made inside serve_fixture.py. Do not
    # inherit external native UI routing or real server configuration flags.
    env.pop('TACTIC_UI', None)
    env.pop('TACTIC_CONFIG_PATH', None)
    report = output / (name + ('/browser-results.json' if 'browser' in name else '.json'))
    command = [sys.executable, str(TESTS / (name + '.py')), '--url', url,
               '--output', str(report.parent if 'browser' in name else report)]
    if 'browser' in name:
        command += ['--chromium', args.chromium]
        if args.bridge:
            command += ['--bridge']
    with (output / f'{name}-server.log').open('w', encoding='utf-8') as server_log:
        process = subprocess.Popen([sys.executable, str(TESTS / 'serve_fixture.py')],
                                   cwd=ROOT, env=env, stdout=server_log,
                                   stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 25
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f'{name}: fixture exited ({process.returncode})')
                try:
                    with urlopen(url + '/api/ui/v2/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError, OSError):
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError(f'{name}: fixture did not become ready')
                time.sleep(0.1)
            result = execute(command, output / (name + '.log'), timeout=240)
            if report.exists():
                data = json.loads(report.read_text())
                scenarios = data.get('scenarios', data.get('results', []))
                result['scenarios'] = len(scenarios)
                result['passed_scenarios'] = sum(item.get('passed') is True for item in scenarios)
                result['js_errors'] = data.get('js_errors', [])
            result['fresh_fixture'] = True
            result['report'] = str(report.relative_to(ROOT)) if report.is_relative_to(ROOT) else str(report)
            return result
        finally:
            stop(process)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/native-ui/0.5/validation')
    parser.add_argument('--bridge', action='store_true')
    parser.add_argument('--chromium', default=shutil.which('chromium') or 'chromium')
    parser.add_argument('--skip-browser', action='store_true')
    parser.add_argument('--only', choices=('unit', 'http', 'browser'))
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'python': sys.version, 'platform': platform.platform(),
              'browser_transport': 'explicit Python HTTP bridge; no native cookies/CSP/navigation proof' if args.bridge else 'native HTTP',
              'backend': 'test-only synthetic persistence; original TACTIC Select and new services; not a full TACTIC database',
              'suites': {}}
    result_code = 0
    try:
        build = execute(['node', 'tools/native_ui/build.cjs'], args.output / 'build.log')
        report['suites']['build'] = build
        if build['return_code']:
            return 1
        if args.only in (None, 'unit'):
            report['suites']['unit'] = execute(
                [sys.executable, '-W', 'ignore', '-m', 'unittest', 'discover', '-s', 'tests/native_ui', '-v'],
                args.output / 'unit.log')
            print('Unit:', report['suites']['unit']['return_code'], flush=True)
        suites = []
        if args.only in (None, 'http'):
            suites += ['run_http', 'run_http_03', 'run_http_04', 'run_http_05']
        if args.only in (None, 'browser') and not args.skip_browser:
            suites += ['run_browser_03', 'run_browser_04', 'run_browser_05']
        for name in suites:
            try:
                report['suites'][name] = fixture_suite(name, args.output, args)
            except Exception as exc:
                report['suites'][name] = {'return_code': 1, 'error': str(exc)}
            print(name, json.dumps(report['suites'][name], ensure_ascii=False), flush=True)
        result_code = int(any(suite['return_code'] != 0 for suite in report['suites'].values()))
        return result_code
    finally:
        report['passed'] = bool(report['suites']) and all(x['return_code'] == 0 for x in report['suites'].values())
        (args.output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
