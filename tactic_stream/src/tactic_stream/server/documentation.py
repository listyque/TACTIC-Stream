"""Public API reference; no project data, credentials or execution on GET."""
import inspect
import json
from importlib.resources import files

from tactic_stream.server.api import Api, SUPPORTED_METHODS, WRITE_METHODS


EXAMPLES = {
    'query': [
        {'label': 'First 10 SearchTypes', 'description': 'List the first 10 registered object types. Each result includes its search key.',
         'args': ['sthpw/search_object', [], None, ['id asc'], False, 10, 0]},
        {'label': 'Projects', 'description': 'List project codes and names. Use a project code in the connection settings.',
         'args': ['sthpw/project'], 'kwargs': {'limit': 10}},
        {'label': 'Users', 'description': 'Read user records visible to your account. No passwords are returned.',
         'args': ['sthpw/login'], 'kwargs': {'columns': ['login', 'display_name', 'email'], 'limit': 10}},
        {'label': 'Tasks', 'description': 'Read the first 10 tasks. An empty list means no matching tasks are available.',
         'args': ['sthpw/task'], 'kwargs': {'limit': 10}},
        {'label': 'Filter by code', 'description': 'Find the administration project by code. Change admin to another project code.',
         'args': ['sthpw/project'], 'kwargs': {'filters': [['code', 'admin']], 'limit': 10}},
        {'label': 'Filter by namespace', 'description': 'Find SearchTypes in the sthpw namespace. Each filter is a column/value pair.',
         'args': ['sthpw/search_object'], 'kwargs': {'filters': [['namespace', 'sthpw']], 'limit': 10}},
        {'label': 'Choose columns', 'description': 'Return only search_type, title and namespace instead of every database column.',
         'args': ['sthpw/search_object'], 'kwargs': {'columns': ['search_type', 'title', 'namespace'], 'limit': 10}},
        {'label': 'Next page', 'description': 'Skip the first 10 records and read the next 10. Keep the same ordering between pages.',
         'args': ['sthpw/search_object'], 'kwargs': {'order_bys': ['id asc'], 'limit': 10, 'offset': 10}},
    ],
    'ping': [{'label': 'Check connection', 'description': 'Check that the API responds with your current ticket.', 'args': []}],
    'fast_ping': [{'label': 'Check availability', 'description': 'Check that the server responds without signing in.', 'args': []}],
    'get_base_dirs': [{'label': 'Repository paths', 'description': 'Read the repository and sandbox paths configured on the server.', 'args': []}],
    'get_column_info': [{'label': 'SearchType fields', 'description': 'Read field names and database types for a SearchType.', 'args': ['sthpw/search_object']}],
    'get_column_names': [{'label': 'Column names', 'description': 'Get the list of columns for a SearchType.', 'args': ['sthpw/search_object']}],
    'get_by_code': [{'label': 'One project', 'description': 'Read a single project by its code.', 'args': ['sthpw/project', 'admin']}],
    'get_by_search_key': [{'label': 'Object by search key', 'description': 'Read a record using the search key returned by query.', 'args': ['sthpw/project?code=admin']}],
    'execute_python_script': [{'label': 'Server-side Python', 'description': 'Run Python on the server and return five projects. Script execution requires the corresponding account permissions.',
                               'args': ['', {'code': "return server.query('sthpw/project', limit=5)"}]}],
    'get_ticket': [{'label': 'Request a ticket', 'description': 'Sign in and obtain an API ticket. Enter your own password.', 'args': ['admin', '']}],
    'get_ticket_data': [{'label': 'Sign-in details', 'description': 'Sign in and read ticket details. Enter your own password.', 'args': ['admin', '']}],
}


def api_documentation():
    manifest = json.loads((files('tactic_stream') / 'compatibility/api_manifest.json').read_text(encoding='utf-8'))
    help_catalog = json.loads((files('tactic_stream') / 'compatibility/api_help.json').read_text(encoding='utf-8'))
    methods = []
    for name, original in sorted(manifest['methods'].items()):
        available = name in SUPPORTED_METHODS
        signature = inspect.signature(getattr(Api, name)) if available else None
        examples = EXAMPLES.get(name, [])
        parameters = []
        if signature:
            for parameter in signature.parameters.values():
                if parameter.name == 'self':
                    continue
                required = parameter.default is inspect.Parameter.empty
                parameters.append({'name': parameter.name, 'required': required,
                                   'default': None if required else repr(parameter.default),
                                   'default_value': None if required else parameter.default,
                                   'kind': parameter.kind.name})
        methods.append({
            'name': name,
            'status': 'available' if available else original['status'],
            'writes': name in WRITE_METHODS or name in ('eval', 'get_preallocated_path', 'get_virtual_snapshot_path', 'get_ticket', 'get_ticket_data'),
            'requires_ticket': any(item['name'] == 'ticket' for item in parameters) and name != 'fast_ping',
            'parameters': parameters,
            'signature': str(signature).replace('(self, ', '(', 1) if signature else '(' + original['signature'].removeprefix('self, ') + ')',
            'original_signature': '(' + original['signature'].removeprefix('self, ') + ')',
            'reference': original.get('client_documentation') or original.get('documentation', ''),
            'help': help_catalog[name],
            'reason': original.get('reason', ''),
            'example': examples[0] if examples else {'args': []},
            'examples': examples,
        })
    return {'methods': methods, 'full_api_parity_verified': manifest['full_api_parity_verified'],
            'xmlrpc_route': '/tactic/{project}/Api/', 'json_route': '/admin/rpc',
            'baseline': manifest['baseline'],
            'xmlrpc_errors': {'400': 'Invalid arguments or missing object', '403': 'Invalid credentials / expired ticket / unavailable project / permission denied (distinct messages)',
                              '501': 'Operation not migrated or excluded', '503': 'Database unavailable',
                              '500': 'Internal error or partial database commit'},
            'json_errors': {'400': 'invalid_request / validation_failed', '403': 'authentication_failed / origin_forbidden',
                            '413': 'request_too_large', '415': 'json_required',
                            '501': 'unsupported_operation', '503': 'database_unavailable',
                            '500': 'request_failed / partial_commit'}}
