"""Authenticated page resolution from original project config/url definitions."""
import re
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType
from .interface import _require_table_access
from .navigation_links import check_project, navigation_link_request


def read_custom_url(path, parameters=None):
    project = Project.get_project_code()
    check_project(project)
    if (not isinstance(path, str) or not path.startswith('/') or len(path) > 16384
            or any(character in path for character in '\r\n\x00?#')
            or any(part in ('.', '..') for part in path.split('/'))):
        raise ValueError('Invalid custom URL path')
    if parameters is None:
        parameters = {}
    if (not isinstance(parameters, dict) or len(parameters) > 100
            or any(not isinstance(key, str) or not isinstance(value, str)
                   or len(key) > 256 or len(value) > 16384 for key, value in parameters.items())):
        raise ValueError('Custom URL parameters must be bounded text values')
    matches = []
    for row in Search('config/url').get_sobjects():
        if row.get_value('s_status', no_exception=True) == 'retired':
            continue
        pattern = row.get_value('url') or ''
        parts = re.split(r'(\{[A-Za-z_]\w*\})', pattern)
        names = [part[1:-1] for part in parts if re.fullmatch(r'\{[A-Za-z_]\w*\}', part)]
        if len(names) != len(set(names)):
            continue
        expression = ''.join('([^/]+)' if re.fullmatch(r'\{[A-Za-z_]\w*\}', part) else re.escape(part) for part in parts)
        match = re.fullmatch(expression, path)
        if match:
            literal_length = sum(len(part) for part in parts if not re.fullmatch(r'\{[A-Za-z_]\w*\}', part))
            matches.append((len(names), -literal_length, row, dict(zip(names, match.groups()))))
    if not matches:
        raise LookupError('Custom URL is not configured: ' + path)
    matches.sort(key=lambda match: match[:2])
    if len(matches) > 1 and matches[0][:2] == matches[1][:2]:
        raise ValueError('Custom URL matches multiple definitions: ' + path)
    _, _, row, captured = matches[0]
    if not Environment.get_security().check_access('url', ['/tactic/' + project + path, path], 'view'):
        raise SecurityException('Custom URL access denied')
    source = row.get_value('widget') or ''
    if len(source) > 1024 * 1024 or '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('Invalid custom URL definition')
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise ValueError('Invalid custom URL XML') from error
    display = root.find('display')
    if root.tag != 'element' or display is None:
        raise ValueError('Custom URL requires an element/display definition')
    options = {}
    for node in display:
        if list(node):
            raise ValueError('Custom URL display options must be text')
        value = node.text or ''
        for name, replacement in captured.items():
            value = value.replace('{' + name + '}', replacement)
        options[node.tag] = value
    handler = display.get('class') or 'tactic.ui.panel.ViewPanelWdg'
    return dict(project=project, path=path, title=row.get_value('description') or path,
                handler=handler, options=options, parameters=dict(parameters, **captured))


def resolve_custom_url(path, parameters=None):
    definition = read_custom_url(path, parameters)
    project, handler, options = definition['project'], definition['handler'], definition['options']
    # Resolve declarations only. Never import/call a class or a script named by a URL.
    if handler not in ('tactic.ui.panel.ViewPanelWdg', 'tactic.ui.panel.TableLayoutWdg',
                       'tactic.ui.panel.CustomLayoutWdg'):
        raise UnsupportedContract('Custom URL handler is not implemented: ' + handler)
    key = options.get('search_key')
    record = navigation_link_request(dict(link=key if key.startswith('skey://') else 'skey://' + key))['object'] if key else None
    search_type = options.get('search_type') or (record['__search_type__'].split('?')[0] if record else '')
    layout = handler == 'tactic.ui.panel.CustomLayoutWdg'
    if layout and not options.get('view'):
        raise ValueError('Custom URL layout requires a view')
    if not search_type and layout:
        search_type = 'sthpw/project'
    if not search_type:
        raise ValueError('Custom URL must specify a search_type or search_key')
    scoped = SearchType.breakup_search_type(search_type)
    if scoped.get('project') and scoped['project'] != project:
        raise ValueError('Custom URL must stay in its project')
    search_type = search_type.split('?')[0]
    SearchType.get(search_type)
    _require_table_access(search_type)
    if record and record['__search_type__'].split('?')[0] != search_type.split('?')[0]:
        raise ValueError('Custom URL search_key does not match search_type')
    options = dict(definition['parameters'], **options)
    return dict(project=project, path=path, title=definition['title'],
                search_type=search_type, view='table' if layout else options.get('view') or 'table',
                layoutView=options.get('view') if layout else '', options=options,
                filterField='code' if record and record.get('code') else 'id' if record else '',
                filterValue=str(record.get('code') or record['id']) if record else '')


def install_rest_routes(app, invoke_json, workspace_index, request_environ):
    import json
    from urllib.parse import parse_qsl
    from fastapi import Request
    from starlette.concurrency import run_in_threadpool
    from starlette.responses import Response, JSONResponse

    @app.api_route('/projects/{project}/{custom_path:path}', methods=['GET', 'POST', 'PUT', 'DELETE'], include_in_schema=False)
    @app.api_route('/tactic/{project}/{custom_path:path}', methods=['GET', 'POST', 'PUT', 'DELETE'], include_in_schema=False)
    async def custom_endpoint(request: Request, project: str, custom_path: str):
        authorization = request.headers.get('authorization', '')
        if request.method == 'GET' and 'text/html' in request.headers.get('accept', '') and not authorization:
            return workspace_index()
        headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
        if request.headers.get('origin') not in (None, str(request.base_url).rstrip('/')):
            return JSONResponse({'error': 'Cross-site requests are not allowed.'}, status_code=403, headers=headers)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 1024 * 1024:
                return Response(status_code=413, headers=headers)
            body.extend(chunk)
        content_type = request.headers.get('content-type', '').split(';')[0].strip()
        parameters, data = dict(request.query_params), None
        try:
            if 'ticket' in parameters or 'login_ticket' in parameters:
                raise ValueError('Credentials do not belong in a URL')
            if body:
                if content_type == 'application/json':
                    from tactic_stream.server.app import reject_json_constant
                    data = json.loads(body, parse_constant=reject_json_constant)
                elif content_type == 'application/x-www-form-urlencoded':
                    parameters.update(parse_qsl(body.decode('utf-8'), max_num_fields=100))
                else:
                    return Response(status_code=415, headers=headers)
            token = authorization[7:] if authorization.startswith('Bearer ') else ''
            token = token or parameters.pop('login_ticket', '')
            if isinstance(data, dict):
                token = token or data.pop('login_ticket', '')
            payload = dict(method='execute_cmd', args=[dict(ticket=token, project=project),
                'tactic.ui.panel.custom_url_cmd.CustomUrlCmd', dict(path='/' + custom_path,
                    parameters=parameters, method=request.method, body=data,
                    accept=request.headers.get('accept', 'application/json'))], kwargs={})
        except (ValueError, UnicodeError):
            return JSONResponse({'error': 'Invalid custom URL request.'}, status_code=400, headers=headers)
        response = await run_in_threadpool(invoke_json, json.dumps(payload).encode(), request_environ(request))
        if response.status_code != 200:
            return response
        return JSONResponse(json.loads(response.body)['result']['info'], headers=headers)
