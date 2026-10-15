"""Read-only live checks using the unchanged TACTIC Handler client and procedures."""
import argparse
import getpass
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler', type=Path, default=Path('D:/code/th_codex'))
    parser.add_argument('--server', default='http://127.0.0.1:8081')
    parser.add_argument('--project', default='admin')
    parser.add_argument('--login', default='admin')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.handler))
    from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
    spec = importlib.util.spec_from_file_location('handler_query', args.handler / 'thlib/tactic_query.py')
    query = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(query)
    client = TacticServerStub(setup=False, protocol='xmlrpc')
    client.set_server(args.server)
    client.set_project(args.project)
    client.set_ticket(client.get_ticket(args.login, os.environ.get('TACTIC_PASSWORD') or getpass.getpass()))
    results = {}

    def procedure(name, kwargs):
        code = query.prepare_serverside_script(getattr(query, name), kwargs, shrink=False, catch_traceback=False)
        code['_debug_args'] = False
        result = client.execute_python_script('', kwargs=code)['info']
        if isinstance(result, dict) and 'spt_ret_val' in result:
            result = result['spt_ret_val']
        if isinstance(result, str) and result.lstrip().startswith('Traceback'):
            raise RuntimeError(result)
        return json.loads(result) if isinstance(result, str) and result.startswith(('{', '[', '"')) else result

    checks = {
        'ping': client.ping,
        'projects': lambda: client.query('sthpw/project', order_bys=['code asc']),
        'search_objects_10': lambda: client.query('sthpw/search_object', order_bys=['id asc'], limit=10),
        'columns': lambda: client.get_column_info('sthpw/search_object'),
        'eval': lambda: client.eval('6*7'),
        'base_dirs': client.get_base_dirs,
        'handler_projects_and_logins': lambda: procedure('get_projects_and_logins', {'current_login': args.login}),
        'handler_search_types': lambda: procedure('query_search_types_extended', {'project_code': args.project}),
        'handler_sobjects_10': lambda: procedure('query_sobjects', {
            'search_type': 'sthpw/search_object', 'project_code': args.project,
            'order_bys': ['id asc'], 'limit': 10, 'include_snapshots': False, 'compressed_return': False}),
        'handler_milestones': lambda: procedure('query_sobjects', {
            'search_type': 'sthpw/milestone', 'project_code': args.project,
            'filters': [('project_code', args.project)], 'order_bys': ['due_date', 'description'],
            'include_snapshots': False, 'include_info': True, 'include_status_log': False,
            'compressed_return': False}),
    }
    try:
        for name, check in checks.items():
            started = time.perf_counter()
            try:
                value = check()
                results[name] = {'ok': True, 'type': type(value).__name__}
                if isinstance(value, (list, dict)):
                    results[name]['count'] = len(value)
                if name == 'projects':
                    results[name]['project_codes'] = [item['code'] for item in value]
                if name == 'eval':
                    assert value == 42
            except Exception as error:
                secrets = client.ticket.values() if isinstance(client.ticket, dict) else [client.ticket]
                message = str(error)
                for secret in secrets:
                    if isinstance(secret, str) and secret:
                        message = message.replace(secret, '[ticket]')
                results[name] = {'ok': False, 'error': message}
            results[name]['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
            print(name, 'OK' if results[name]['ok'] else 'FAILED', flush=True)
    finally:
        client.server.__exit__(None, None, None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'server': args.server, 'project': args.project, 'checks': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    return int(any(not item['ok'] for item in results.values()))


if __name__ == '__main__':
    sys.exit(main())
