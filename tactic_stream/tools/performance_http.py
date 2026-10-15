"""Measure owned server startup and complete JSON/XML-RPC client scenarios."""
import argparse
import ast
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from xmlrpc.client import ServerProxy
from concurrent.futures import ThreadPoolExecutor

from performance_probe import ROOT, Api, Store, rss_kib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT / 'src')
    parser.add_argument('--repeats', type=int, default=15)
    parser.add_argument('--starts', type=int, default=5)
    parser.add_argument('--io-batches', type=int, default=0, help='Compare 16 HTTP reads serially and with 4 threads')
    parser.add_argument('--json-keepalive', action='store_true', help='Reuse JSON HTTP connection like a browser')
    args = parser.parse_args()
    if not (args.data_dir / 'performance-probe.json').is_file():
        parser.error('Require the owned performance fixture')
    args.output.mkdir(parents=True, exist_ok=True)
    ticket = {'ticket': Api(Store(args.data_dir)).get_ticket('admin', 'private-performance-password'), 'project': 'one'}
    cases = {'query_10': [ticket, 'contract/entity', [], None, ['id asc'], False, 10, 0],
             'query_1000': [ticket, 'contract/entity', [], None, ['id asc'], False, 1000, 0],
             'query_all': [ticket, 'contract/entity', [], None, ['id asc'], True]}
    startup, report, io_report = [], {}, {}
    child_code = """
import json, os, socket, sys, threading
from pathlib import Path
from types import SimpleNamespace
values = json.loads(sys.argv[1])
sys.path.insert(0, values['source'])
from tactic_stream.server.startup import read_server_config, start_server
settings = read_server_config(Path(values['data']), host='127.0.0.1', port=values['port'])
settings['log_dir'] = values['log']
Path(values['log']).mkdir(parents=True, exist_ok=True)
(Path(values['log']) / 'pid.txt').write_text(str(os.getpid()))
listener = socket.socket()
listener.bind(('127.0.0.1', values['port']))
listener.listen(2048)
listener.setblocking(False)
stop = SimpleNamespace(value=False)
def shutdown():
    sys.stdin.readline()
    stop.value = True
threading.Thread(target=shutdown, daemon=True).start()
start_server(settings, sockets=[listener], stop=stop, slot='http-benchmark')
listener.close()
"""
    for start_index in range(args.starts):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        base = 'http://127.0.0.1:%s' % port
        settings = dict(source=str(args.source.resolve()), data=str(args.data_dir.resolve()),
                        port=port, log=str((args.output / ('worker-%s' % start_index)).resolve()))
        with (args.output / ('server-%s.log' % start_index)).open('w', encoding='utf-8') as output:
            started = time.perf_counter()
            child = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', '-c', child_code, json.dumps(settings)],
                                     stdin=subprocess.PIPE, stdout=output, stderr=output, text=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            proxy = json_connection = None
            try:
                for _ in range(500):
                    if child.poll() is not None:
                        raise RuntimeError('Owned HTTP server failed; inspect its log')
                    try:
                        with urlopen(base + '/health', timeout=1) as response:
                            assert json.load(response)['database_initialized']
                        break
                    except OSError:
                        time.sleep(.01)
                else:
                    raise TimeoutError('Owned HTTP server did not start')
                startup.append((time.perf_counter() - started) * 1000)
                worker_pid = int((Path(settings['log']) / 'pid.txt').read_text())
                if start_index:
                    continue
                proxy = ServerProxy(base + '/tactic/default/Api/', allow_none=True)
                if args.json_keepalive:
                    json_connection = HTTPConnection('127.0.0.1', port, timeout=15)
                for name, call_args in cases.items():
                    for transport in ('xmlrpc', 'json'):
                        if transport == 'json' and args.json_keepalive:
                            # Each scenario reuses its connection; the previous
                            # one can have expired during a long XML-RPC batch.
                            json_connection.close()
                            json_connection = HTTPConnection('127.0.0.1', port, timeout=15)
                        samples, network, decoding = [], [], []
                        expected = None
                        for index in range(args.repeats + 1):
                            started = time.perf_counter()
                            if transport == 'xmlrpc':
                                raw = proxy.query(*call_args)
                                received = time.perf_counter()
                                value = ast.literal_eval(raw)
                            else:
                                body = json.dumps({'method': 'query', 'args': call_args}).encode()
                                if json_connection:
                                    json_connection.request('POST', '/admin/rpc', body,
                                                            headers={'Content-Type': 'application/json'})
                                    response = json_connection.getresponse()
                                    assert response.status == 200
                                    raw = response.read()
                                else:
                                    request = Request(base + '/admin/rpc', body, headers={'Content-Type': 'application/json'})
                                    with urlopen(request, timeout=15) as response:
                                        raw = response.read()
                                received = time.perf_counter()
                                value = json.loads(raw)['result']
                            finished = time.perf_counter()
                            digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                            if expected is None:
                                expected = digest
                                cold = (finished - started) * 1000
                            else:
                                assert expected == digest
                                samples.append((finished - started) * 1000)
                                network.append((received - started) * 1000)
                                decoding.append((finished - received) * 1000)
                        report[name + '_' + transport] = dict(cold_ms=cold,
                            median_ms=statistics.median(samples), min_ms=min(samples), max_ms=max(samples),
                            network_median_ms=statistics.median(network),
                            decode_median_ms=statistics.median(decoding), result_count=len(value), sha256=expected,
                            server_memory=rss_kib(worker_pid) if sys.platform == 'win32' else None)
                if args.io_batches:
                    body = json.dumps({'method': 'query', 'args': cases['query_10']}).encode()
                    def http_read(_):
                        request = Request(base + '/admin/rpc', body, headers={'Content-Type': 'application/json'})
                        with urlopen(request, timeout=15) as response:
                            return json.load(response)['result']
                    for workers in (1, 4):
                        samples = []
                        with ThreadPoolExecutor(max_workers=workers) as executor:
                            for index in range(args.io_batches + 1):
                                started = time.perf_counter()
                                values = list(executor.map(http_read, range(16)))
                                elapsed = (time.perf_counter() - started) * 1000
                                assert all(value == values[0] for value in values)
                                if index:
                                    samples.append(elapsed)
                                else:
                                    cold = elapsed
                        io_report[str(workers)] = dict(cold_batch_ms=cold, median_batch_ms=statistics.median(samples),
                                                      min_ms=min(samples), max_ms=max(samples), tasks=16)
            finally:
                if proxy:
                    proxy.__exit__(None, None, None)
                if json_connection:
                    json_connection.close()
                child.communicate('\n', timeout=15)
                assert child.returncode == 0
    result = dict(source=str(args.source.resolve()), repeats=args.repeats, json_keepalive=args.json_keepalive,
                  startup=dict(samples_ms=startup, median_ms=statistics.median(startup),
                               min_ms=min(startup), max_ms=max(startup), polling_ms=10), scenarios=report,
                  io_batches=io_report)
    (args.output / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
