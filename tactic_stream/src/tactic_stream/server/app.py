"""ASGI transport. Blocking database/RPC work stays outside the event loop."""
import logging
import asyncio
import gzip
import time
from hashlib import sha256
from email import policy
from email.parser import BytesParser
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from importlib.resources import files
import json
from pathlib import Path
from pathlib import PurePosixPath
import sqlite3
from urllib.parse import urlsplit
from xml.parsers import expat
from xmlrpc.client import Fault, dumps, loads

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response, FileResponse, StreamingResponse
from starlette.staticfiles import StaticFiles

from tactic_stream import __version__
from tactic_stream.server.api import Api, compatibility_manifest
from tactic_stream.server.xmlrpc_response import encode_response
from pyasm.common.errors import AuthenticationError, SecurityException, TacticException, UnsupportedContract
from pyasm.common import UserException
from pyasm.search.storage import Store
from pyasm.search.transaction import PartialCommitException

LOG = logging.getLogger(__name__)
MAX_BODY = 1024 * 1024
MAX_UPLOAD_BODY = 64 * 1024 * 1024
EVENT_HEARTBEAT = 20


class ServerClockHeaders:
    """Timestamp response headers without buffering or changing stream lifetime."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        started = datetime.now(timezone.utc).isoformat().encode('ascii')

        async def send_with_clock(message):
            if message['type'] == 'http.response.start':
                ended = datetime.now(timezone.utc).isoformat().encode('ascii')
                message = dict(message, headers=list(message.get('headers', [])) + [
                    (b'x-tactic-utc-started', started),
                    (b'x-tactic-utc-ended', ended),
                ])
            await send(message)

        await self.app(scope, receive, send_with_clock)


def json_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError('Response value is not JSON serializable: ' + type(value).__name__)


def upload_parts(content_type, body, *, max_field_bytes=4096):
    """Decode the original client's multipart envelope and browser file parts."""
    if '\r' in content_type or '\n' in content_type:
        raise ValueError('Invalid multipart content type')
    message = BytesParser(policy=policy.default).parsebytes(
        ('Content-Type: ' + content_type + '\r\nMIME-Version: 1.0\r\n\r\n').encode('ascii') + body)
    if message.get_content_type() != 'multipart/form-data' or not message.is_multipart() or message.defects:
        raise ValueError('Multipart form data is required')
    fields, uploads = {}, []
    parts = list(message.iter_parts())
    if len(parts) > 64:
        raise ValueError('Too many upload fields')
    for part in parts:
        if part.defects or part.is_multipart() or part.get_content_disposition() != 'form-data':
            raise ValueError('Invalid multipart part')
        name = part.get_param('name', header='content-disposition')
        payload = part.get_payload(decode=True)
        if not isinstance(name, str) or payload is None:
            raise ValueError('Invalid upload field')
        if part.get_filename() is not None:
            if name not in ('file', 'Filedata') and not (name.startswith('file') and name[4:].isdigit()):
                raise ValueError('Invalid file field')
            uploads.append((name, part.get_filename(), payload))
        else:
            if name in fields or len(payload) > max_field_bytes:
                raise ValueError('Invalid or duplicate upload field')
            fields[name] = payload.decode('utf-8')
    if fields.get('num_files') and int(fields['num_files']) != len(uploads):
        raise ValueError('Upload file count does not match')
    result = []
    for index, (field, filename, payload) in enumerate(uploads):
        suffix = field[4:] if field.startswith('file') and field[4:].isdigit() else str(index)
        filename = fields.get('file_name' + suffix) or fields.get('Filename') or filename
        if fields.get('action') and 'file_name' + suffix in fields:
            # UploadMultipart sends JSON-escaped Unicode; browser names are already UTF-8.
            filename = json.loads('"' + filename + '"')
        result.append((filename, payload))
    return fields, result


def reject_json_constant(value):
    raise ValueError("Invalid JSON number")


def repository_web_paths(roots, web_dirs):
    """Check repository routes before startup or publishing configuration."""
    mounts = []
    for alias, address in web_dirs.items():
        url = urlsplit(address)
        if url.scheme or url.netloc:
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
                raise ValueError('Invalid external repository web URL')
            url.port
            continue  # An external repository web server owns this URL.
        path = url.path.rstrip('/')
        if (not path.startswith('/') or path.split('/')[1] in ('', 'admin', 'projects', 'ui', 'tactic', 'api', 'health', 'test', 'docs', 'redoc', 'openapi.json')
                or any(part in ('.', '..') for part in path.split('/')) or '\\' in path or url.query or url.fragment):
            raise ValueError('Repository web path overlaps application routes or is invalid: ' + address)
        if alias not in roots:
            raise ValueError('Repository web alias has no asset directory: ' + alias)
        if any(path == saved or path.startswith(saved + '/') or saved.startswith(path + '/') for saved, _ in mounts):
            raise ValueError('Repository web paths overlap')
        mounts.append((path, alias))
    return mounts


def create_app(data_dir: Path, thread_count=None, *, event_collector=True) -> FastAPI:
    # Construction does not initialize a database or touch legacy/local_data.
    @asynccontextmanager
    async def lifespan(app):
        if thread_count is not None:
            from anyio import to_thread
            to_thread.current_default_thread_limiter().total_tokens = thread_count
        if api.store.is_initialized():
            def initialize_core():
                from tactic.core.bootstrap import CoreInit
                from pyasm.search.search import RequestContext, request_context
                with request_context(RequestContext(api.store, 'admin', 'admin')):
                    CoreInit().execute()
                    from pyasm.search.file_recovery import recover_files
                    try:
                        recover_files(api.store)
                    except Exception:
                        LOG.exception('File recovery unresolved; repository writes remain blocked until recovery succeeds')
            await run_in_threadpool(initialize_core)
        process = stop = file_process = file_stop = None
        from tactic_stream.server.startup import read_server_config
        settings = await run_in_threadpool(read_server_config, api.store.data_dir)
        update_interval = settings['update_interval']
        events.interval = update_interval
        if event_collector:
            import multiprocessing
            from tactic_stream.server.update_collector import UpdateCollector, start_updates
            # Standalone ASGI/test hosts own their producer; TacticMonitor supplies its own.
            await run_in_threadpool(UpdateCollector(api.store.data_dir).tick)
            spawn = multiprocessing.get_context('spawn')
            stop = spawn.Value('b', 0, lock=False)
            process = spawn.Process(target=start_updates, args=({'data_dir': str(api.store.data_dir), 'update_interval': update_interval}, None, stop), name='TACTIC-updates')
            process.start()
        try:
            if event_collector and settings.get('files_enabled'):
                from .file_tasks import start_files
                file_stop = spawn.Value('b', 0, lock=False)
                candidate = spawn.Process(target=start_files, args=(settings, None, file_stop), name='TACTIC-files')
                try:
                    candidate.start()
                except BaseException:
                    candidate.close()
                    raise
                file_process = candidate
            yield
        finally:
            try:
                await events.close()
            finally:
                if file_process is not None:
                    file_stop.value = True
                    await run_in_threadpool(file_process.join, 3)
                    if file_process.is_alive():
                        file_process.kill()
                        await run_in_threadpool(file_process.join, 3)
                    file_process.close()
                if process is not None:
                    stop.value = True
                    await run_in_threadpool(process.join, 3)
                    if process.is_alive():
                        process.kill()
                        await run_in_threadpool(process.join, 3)
                    process.close()
    app = FastAPI(title="TACTIC Stream", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(ServerClockHeaders)
    api = Api(Store(data_dir))
    from tactic_stream.server.server_events import ServerEvents, matching_changes, advance_cursors, presence_state, event_frame
    events = ServerEvents(api.store.data_dir)
    json_api = Api(api.store)
    json_api.protocol = 'json'

    # Handler downloads repository files directly, as with TACTIC's Apache asset alias.
    from pyasm.common import Config, Environment
    from pyasm.search.search import RequestContext, request_context
    with request_context(RequestContext(api.store, 'admin')):
        roots = Environment.get_asset_dirs()
        roots.setdefault('default', Environment.get_asset_dir())
        web_dirs = Config.get_dict_value('checkin', 'web_base_dir')
        mcp_enabled = Config.get_value('security','agent_mcp_enabled') == 'true'
    from tactic_stream.server.file_project import FileProjectStaticFiles
    for path, alias in repository_web_paths(roots, web_dirs):
        app.mount(path, FileProjectStaticFiles(directory=roots[alias], check_dir=False,
            private_jobs=api.store.data_dir / 'temp/file-jobs'), name='repository-' + alias)

    @app.get("/", include_in_schema=False)
    @app.get("/projects/{project}/", include_in_schema=False)
    @app.get('/docs', include_in_schema=False)
    @app.get('/docs/', include_in_schema=False)
    def workspace_index():
        content = (files("tactic_stream") / "web/index.html").read_bytes()
        return Response(content, media_type="text/html", headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' blob:; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; frame-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        })

    @app.get("/health")
    def health():
        return {"service": "tactic_stream", "version": __version__,
                "database_initialized": api.store.is_initialized()}

    @app.get('/test', include_in_schema=False)
    def test():
        return Response('OK', media_type='text/plain')

    @app.get("/api/compatibility")
    def compatibility():
        return compatibility_manifest()

    @app.get('/api/documentation', summary='TACTIC method reference', tags=['API reference'])
    def documentation():
        from tactic_stream.server.documentation import api_documentation
        return JSONResponse(api_documentation(), headers={'Cache-Control': 'no-store'})

    def request_environ(request):
        return dict(MCP_ENABLED=mcp_enabled, SERVER_PORT=str(request.scope['server'][1]) if request.scope.get('server') else None,
                    REMOTE_ADDR=request.client.host if request.client else None,
                    REQUEST_METHOD=request.method, PATH_INFO=request.url.path, BASE_URL=str(request.base_url).rstrip('/'))

    def invoke_json(body, environ=None):
        headers = {"Cache-Control": "no-store"}
        method, script_error = None, None
        sdk = False
        try:
            payload = json.loads(body.decode("utf-8"), parse_constant=reject_json_constant)
            if not isinstance(payload, dict) or set(payload) - {"method", "args", "kwargs", "codec"}:
                raise ValueError("Invalid JSON request")
            from tactic_stream.rpc_json import CODEC, decode, encode
            if 'codec' in payload:
                if payload['codec'] != CODEC:
                    raise ValueError('Unsupported RPC codec')
                sdk = True
            method, args, kwargs = payload.get("method"), payload.get("args", []), payload.get("kwargs", {})
            if not isinstance(method, str) or not isinstance(args, list) or not isinstance(kwargs, dict):
                raise ValueError("Invalid JSON request")
            if sdk:
                args, kwargs = decode(args, True), decode(kwargs, True)
            transport_api = json_api if method in ('query', 'eval') else api
            result = transport_api.dispatch(method, args, kwargs, environ=environ)
            try:
                response = {'result': encode(result), 'codec': CODEC} if sdk else {'result': result}
                content = json.dumps(response, default=json_date, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':'))
            except (TypeError, ValueError) as error:
                if sdk:
                    # The command may have committed; this is not a rejected input.
                    raise RuntimeError('SDK response could not be serialized') from error
                raise
            return Response(content, media_type='application/json', headers=headers)
        except AuthenticationError as error:
            status, code, message = 403, "authentication_failed", "Invalid credentials or expired session."
            if sdk:
                message = {'Project unavailable': 'No project available',
                           'Login/Password combination incorrect': 'Login/Password combination incorrect'}.get(
                               str(error), 'Invalid or expired ticket. Session may have expired.')
        except SecurityException as error:
            status, code, message = 403, 'permission_denied', 'Permission denied'
            script_error = error
        except UnsupportedContract as error:
            status, code, message = 501, "unsupported_operation", "This operation or object type is not available yet."
            if sdk:
                message = str(error)
        except PartialCommitException as error:
            LOG.exception('Partial database commit')
            status, code, message = 500, 'partial_commit', str(error)
        except UserException as error:
            status, code, message = 400, 'invalid_request', 'Check the project, object type and search parameters.'
            if method == 'execute_cmd':
                code, message = 'validation_failed', str(error)
            script_error = error
        except (ValueError, TypeError, LookupError, TacticException) as error:
            status, code, message = 400, "invalid_request", "Check the project, object type and search parameters."
            if sdk or (method == 'execute_cmd' and isinstance(args, list) and len(args) > 1 and args[1] in (
                    'tactic.ui.panel.agent_actions_cmd.AgentActionsCmd',
                    'tactic.ui.panel.agent_request_cmd.AgentRequestCmd',
                    'tactic.ui.panel.custom_url_cmd.CustomUrlCmd',
                    'tactic.ui.panel.agent_attachment_cmd.AgentAttachmentCmd')):
                message = str(error)
            script_error = error
        except sqlite3.OperationalError:
            status, code, message = 503, "database_unavailable", "Database unavailable. Check initialization and the selected project."
        except Exception as error:
            LOG.exception("Admin request failed")
            status, code, message = 500, "request_failed", "Request failed."
            script_error = error
        if method == 'execute_python_script' and getattr(script_error, 'tactic_script_sources', None):
            from tactic.command.python_cmd import format_script_traceback
            message = format_script_traceback(script_error)
        elif method == 'execute_js_script' and getattr(script_error, 'tactic_js_source', None):
            message = script_error.tactic_js_source + '\n' + str(script_error)
        return JSONResponse({"error": message, "error_code": code}, status_code=status, headers=headers)

    async def admin_body(request):
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
            return JSONResponse({"error": "JSON content is required.", "error_code": "json_required"}, status_code=415,
                                headers={"Cache-Control": "no-store"})
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"error": "Cross-site requests are not allowed.", "error_code": "origin_forbidden"}, status_code=403,
                                headers={"Cache-Control": "no-store"})
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                return JSONResponse({"error": "The request is too large.", "error_code": "request_too_large"}, status_code=413,
                                    headers={"Cache-Control": "no-store"})
            body.extend(chunk)
        return bytes(body)

    @app.post('/admin/rpc', include_in_schema=False)
    async def admin_rpc(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(invoke_json, body, request_environ(request))

    def interface_request(body, form=False, configuration=None, deletion=None, status=False, relations=False, navigation=False, project_creation=False, sidebar=None, search_configuration=None, groups=None, rules=None, project_catalog=False, users=None, columns=None, cells=False, workspace_layout=None, result_items=False, script_shelf=None, script_editor=None, activity=False, navigation_link=False, journal=False, server_updates=False, messages=None, uploads=None, user_profile=None, knowledge=None, checkin_queue=None, invalidations=(), raw_database=None, project_agent=None, custom_url=False):
        from tactic_stream.server.widget_configuration import WidgetConfigConflict
        from pyasm.common.config import ConfigConflict
        object_status = status
        try:
            payload = json.loads(body.decode('utf-8'), parse_constant=reject_json_constant)
            fields = {'ticket', 'project', 'search_type', 'view'}
            if custom_url:
                fields = {'ticket', 'project', 'path', 'parameters'}
            if project_agent:
                fields = {'ticket', 'project', 'target', 'document', 'expected_revision', 'operation_id', 'template_id', 'title'}
            if raw_database:
                fields = {'ticket', 'project', 'identity', 'document', 'expected_revision', 'item_offset', 'confirmation'}
            if navigation or project_creation or sidebar or groups or rules or project_catalog or users or user_profile or columns or workspace_layout or script_shelf or script_editor or activity or navigation_link:
                fields = {'ticket', 'project'}
            if navigation_link:
                fields.update(('link', 'keys'))
            if journal:
                fields = {'ticket', 'project', 'search_key'}
            if server_updates:
                fields = {'ticket', 'project', 'message_after', 'activity_after', 'reaction_after', 'cache_after', 'presence_ttl', 'channels', 'search_types', 'invalidated_types', 'heartbeat'}
            if checkin_queue:
                from tactic_stream.server.checkin_queue import FIELDS
                fields = {'ticket', 'project'} | FIELDS
            if messages:
                from tactic_stream.server.messages import FIELDS
                fields = {'ticket', 'project'} | FIELDS[messages]
            if knowledge:
                from tactic_stream.server.knowledge import FIELDS
                fields = {'ticket', 'project'} | FIELDS
            if activity:
                fields.update(('filter', 'offset', 'users', 'day', 'counts_only', 'exclude_own', 'time_zone'))
            if script_editor:
                fields.update(('code', 'folder', 'title', 'language', 'source', 'revision', 'revision_id', 'cursor', 'manual'))
            if script_shelf:
                fields.update(('code', 'title', 'configuration', 'revision', 'mode', 'entry_key', 'path'))
            if workspace_layout:
                fields.update(('code', 'title', 'configuration', 'revision'))
            if columns:
                fields.update(('source_id', 'xml', 'revision'))
            if cells:
                fields.add('search_keys')
            if result_items:
                fields.update(('search_keys', 'branch', 'offset', 'limit', 'query'))
            if user_profile:
                fields.update(('login', 'document', 'revision', 'token'))
            if users:
                fields.update(('identity', 'document', 'expected_revision'))
            if rules:
                fields.update(('document', 'expected_revision'))
                if rules == 'effective':
                    fields.add('login')
            if groups:
                fields.update(('group_code', 'login_group', 'description', 'add_members', 'remove_members', 'expected_revision'))
            if sidebar:
                fields.update(('state', 'revision', 'operation', 'field', 'value', 'xml'))
            if search_configuration:
                fields.update(('scope', 'revision', 'code', 'title', 'records', 'configuration', 'filters', 'selections', 'limit', 'offset', 'order_bys', 'show_retired', 'keyword', 'include_total', 'columns', 'tags', 'tag_column'))
                if search_configuration == 'suggestions':
                    fields.update(('column', 'nested_scope'))
            if form:
                fields.update(('search_key', 'default', 'source_key', 'search_keys', 'parent_key', 'connect_key'))
            if relations:
                fields.add('search_key')
            if deletion:
                fields.update(('search_key', 'search_keys', 'related_types'))
            if status:
                fields.update(('search_keys', 'operation'))
            if configuration in ('check', 'preview', 'save'):
                fields.update(('source_id', 'xml', 'revision'))
            if not isinstance(payload, dict) or set(payload) - fields:
                raise ValueError('Invalid interface request')
            # Global communication/profile reads do not require a selected project.
            if (messages or server_updates or user_profile or navigation_link) and payload.get('project') == '':
                payload = dict(payload, project='sthpw')
            if not all(isinstance(payload.get(name), str) and payload[name] for name in (('ticket', 'project') if configuration == 'catalog' or custom_url or project_agent or raw_database or navigation or project_creation or sidebar or groups or rules or project_catalog or users or user_profile or columns or workspace_layout or script_shelf or script_editor or activity or navigation_link or journal or server_updates or messages or knowledge or checkin_queue else ('ticket', 'project', 'search_type'))):
                raise ValueError('Invalid interface request')
            login = api.auth.validate(payload['ticket'])
            with request_context(RequestContext(api.store, login, payload['project'])):
                api.auth.bind_security(login, payload['ticket'])
                from tactic_stream.server.interface import read_interface, read_form
                if custom_url:
                    from tactic_stream.server.custom_urls import resolve_custom_url
                    result = resolve_custom_url(payload.get('path'), payload.get('parameters'))
                elif project_agent:
                    from tactic_stream.server.project_agent import project_agent_request
                    result = project_agent_request(project_agent, payload)
                elif raw_database:
                    from tactic_stream.server.raw_database import raw_database_operation
                    result = raw_database_operation(raw_database, payload)
                elif checkin_queue:
                    from tactic_stream.server.checkin_queue import checkin_queue_request
                    result = checkin_queue_request(checkin_queue, payload, uploads)
                elif knowledge:
                    from tactic_stream.server.knowledge import knowledge_request
                    result = knowledge_request(knowledge, payload, uploads)
                elif user_profile:
                    from tactic_stream.server.user_profile import user_profile_request
                    result = user_profile_request(user_profile, payload, uploads)
                elif messages:
                    from tactic_stream.server.messages import messages_request
                    result = messages_request(messages, payload, uploads)
                elif server_updates:
                    from tactic_stream.server.server_updates import server_updates_request
                    result = server_updates_request(payload, heartbeat=server_updates != 'stream',
                        presence_only=server_updates == 'presence', invalidations=invalidations)
                elif journal:
                    from tactic_stream.server.transaction_journal import details
                    result = details(payload)
                elif navigation_link:
                    from tactic_stream.server.navigation_links import navigation_link_request
                    if 'keys' in payload:
                        from tactic_stream.server.skey_previews import preview_links_request
                        if 'link' in payload:
                            raise ValueError('Choose one link operation')
                        result = preview_links_request(payload['keys'])
                    else:
                        result = navigation_link_request(payload)
                elif activity:
                    from tactic_stream.server.activity_feed import activity_feed_request
                    result = activity_feed_request(payload)
                elif result_items:
                    from tactic_stream.server.result_items import read_result_items
                    result = read_result_items(payload['search_type'], payload.get('search_keys'), payload.get('branch'), payload.get('offset', 0), payload.get('limit', 50), payload.get('query', ''))
                elif script_editor:
                    from tactic_stream.server.script_editor import script_editor_request
                    result = script_editor_request(script_editor, payload)
                elif script_shelf:
                    from tactic_stream.server.script_shelf import script_shelf_request
                    result = script_shelf_request(script_shelf, payload)
                elif workspace_layout:
                    from tactic_stream.server.workspace_layout import workspace_layout_request
                    result = workspace_layout_request(workspace_layout, payload)
                elif cells:
                    from tactic_stream.server.table_cells import read_table_cells
                    result = read_table_cells(payload['search_type'], payload.get('view', 'table'), payload.get('search_keys'))
                elif project_catalog:
                    from tactic_stream.server.project_creation import get_project_catalog
                    result = get_project_catalog()
                elif columns:
                    from tactic_stream.server.columns_editor import columns_editor_request
                    result = columns_editor_request(columns, payload)
                elif users:
                    from tactic_stream.server.security_users import security_users_request
                    result = security_users_request(users, payload)
                elif rules:
                    from tactic_stream.server.security_rules import security_rules_request
                    result = security_rules_request(rules, payload)
                elif groups:
                    from tactic_stream.server.security_groups import security_groups_request
                    result = security_groups_request(groups, payload)
                elif search_configuration:
                    from tactic_stream.server.search_configuration import search_configuration_request
                    result = search_configuration_request(search_configuration, payload)
                elif sidebar:
                    from tactic_stream.server.sidebar_editor import sidebar_request
                    result = sidebar_request(sidebar, payload)
                elif project_creation:
                    from tactic_stream.server.project_creation import get_project_creation_catalog
                    result = get_project_creation_catalog()
                elif navigation:
                    from tactic_stream.server.navigation import read_navigation
                    result = read_navigation()
                elif relations:
                    from tactic_stream.server.object_operations import read_relations
                    result = read_relations(payload['search_type'], payload.get('search_key'))
                elif status:
                    from pyasm.command import Command
                    from tactic_stream.server.object_operations import ObjectStatusCmd
                    command = ObjectStatusCmd(search_type=payload['search_type'], search_keys=payload.get('search_keys'),
                                              operation=payload.get('operation'), view=payload.get('view', 'table'))
                    command.get_transaction().set_sync(False)
                    result = Command.execute_cmd(command)
                elif deletion:
                    from tactic_stream.server.object_operations import read_deletion, delete_object
                    if payload.get('search_key') is not None and payload.get('search_keys') is not None:
                        raise ValueError('Choose one search key selection')
                    arguments = (payload['search_type'], payload.get('search_keys', payload.get('search_key')))
                    if deletion == 'read':
                        result = read_deletion(*arguments, view=payload.get('view', 'table'))
                    else:
                        result = delete_object(*arguments, payload.get('related_types'), view=payload.get('view', 'table'))
                elif configuration:
                    from tactic_stream.server.widget_configuration import read_layout_catalog, read_widget_configuration, check_widget_configuration, preview_widget_configuration, save_widget_configuration
                    if configuration == 'catalog':
                        result = read_layout_catalog()
                    elif configuration == 'read':
                        result = read_widget_configuration(payload['search_type'], payload.get('view', 'table'))
                    else:
                        operation = {'save': save_widget_configuration, 'check': check_widget_configuration,
                                     'preview': preview_widget_configuration}[configuration]
                        result = operation(payload['search_type'], payload.get('view', 'table'), payload.get('source_id'),
                                           payload.get('xml'), payload.get('revision'))
                elif form:
                    if payload.get('search_key') is not None and not isinstance(payload['search_key'], str):
                        raise ValueError('Invalid search key')
                    if payload.get('source_key') is not None and not isinstance(payload['source_key'], str):
                        raise ValueError('Invalid source key')
                    if payload.get('default') is not None and not isinstance(payload['default'], dict):
                        raise ValueError('Invalid default data')
                    result = read_form(payload['search_type'], payload.get('view', 'edit'),
                                       payload.get('search_key'), payload.get('default'), payload.get('source_key'), payload.get('search_keys'),
                                       payload.get('parent_key'), payload.get('connect_key'), ignore=payload.get('ignore'))
                else:
                    result = read_interface(payload['search_type'], payload.get('view', 'table'))
            if messages == 'file':
                return FileResponse(**result, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
            return JSONResponse({'result': result}, headers={'Cache-Control': 'no-store'})
        except AuthenticationError:
            status, code, message = 403, 'authentication_failed', 'Invalid credentials or expired session.'
        except SecurityException as error:
            status, code, message = 403, 'access_denied', str(error)
            if user_profile:
                message = 'You do not have permission for this user profile operation.'
            elif messages:
                message = 'You do not have permission for this Messages operation.'
            elif knowledge:
                message = 'You do not have permission for this Knowledge Base operation.'
            elif navigation_link:
                message = 'You do not have permission to open this TACTIC link.'
            elif activity:
                message = 'You do not have permission to read this activity journal.'
            elif server_updates:
                message = 'You do not have permission to read these server updates.'
            elif script_shelf or script_editor:
                message = 'You do not have permission for this script operation.'
        except UnsupportedContract as error:
            status, code, message = 501, 'unsupported_operation', 'This operation or object type is not available yet.'
            if custom_url or script_shelf or script_editor:
                message = str(error)
        except ConfigConflict:
            status, code, message = 409, 'writer_busy', 'Another configuration writer is busy. Inspect the operation UUID before retrying.'
        except WidgetConfigConflict as error:
            status, code, message = 409, 'widget_config_conflict', 'Interface configuration changed. Reload before saving.'
            if groups or rules or users or user_profile or columns or script_editor:
                message = str(error)
        except PartialCommitException as error:
            LOG.exception('Partial interface operation commit')
            status, code, message = 500, 'partial_commit', str(error)
        except (ValueError, TypeError, LookupError, TacticException) as error:
            status, code, message = 400, 'invalid_request', 'Check the project, object type and search parameters.'
            if custom_url or project_agent or raw_database or search_configuration or groups or rules or users or user_profile or columns or cells or workspace_layout or result_items or script_shelf or script_editor or navigation_link or journal or messages or knowledge or checkin_queue:
                message = str(error)
            if configuration:
                message = str(error)
                code = 'invalid_widget_config'
            elif deletion:
                message = str(error)
                code = 'invalid_deletion'
            elif object_status:
                message = str(error)
                code = 'invalid_object_operation'
            elif navigation:
                message = str(error)
                code = 'invalid_navigation'
            elif sidebar:
                message = str(error)
                code = 'invalid_sidebar'
        except Exception:
            LOG.exception('Interface operation failed')
            status, code, message = 500, 'request_failed', 'Request failed.'
        return JSONResponse({'error': message, 'error_code': code}, status_code=status, headers={'Cache-Control': 'no-store'})

    @app.post('/admin/table-cells', include_in_schema=False)
    async def table_cells(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, cells=True)

    @app.post('/admin/user-profile/avatar', include_in_schema=False)
    async def user_avatar(request: Request):
        body = await multipart_body(request)
        if isinstance(body, Response): return body
        def invoke_avatar():
            try: fields, uploads = upload_parts(*body)
            except (ValueError, TypeError):
                return JSONResponse({'error': 'Invalid avatar upload.', 'error_code': 'invalid_request'}, status_code=400, headers={'Cache-Control':'no-store'})
            return interface_request(json.dumps(fields).encode(), user_profile='avatar', uploads=uploads)
        return await run_in_threadpool(invoke_avatar)

    @app.post('/admin/user-profile/{action}', include_in_schema=False)
    async def user_profile_operation(action: str, request: Request):
        body = await admin_body(request)
        if isinstance(body, Response): return body
        return await run_in_threadpool(interface_request, body, user_profile=action)

    @app.post('/admin/messages/upload', include_in_schema=False)
    async def messages_upload(request: Request):
        body = await multipart_body(request)
        if isinstance(body, Response):
            return body
        def invoke_message_upload():
            try:
                fields, uploads = upload_parts(*body)
            except (ValueError, TypeError):
                return JSONResponse({'error': 'Invalid attachment upload.', 'error_code': 'invalid_request'}, status_code=400, headers={'Cache-Control': 'no-store'})
            return interface_request(json.dumps(fields).encode(), messages='upload', uploads=uploads)
        return await run_in_threadpool(invoke_message_upload)

    @app.post('/admin/messages/{action}', include_in_schema=False)
    async def messages_operation(action: str, request: Request):
        from tactic_stream.server.messages import OPERATIONS
        if action not in OPERATIONS:
            return JSONResponse({'error': {'code': 'invalid_request', 'message': 'Unknown Messages operation.'}},
                                status_code=400, headers={'Cache-Control': 'no-store'})
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, messages=action)

    @app.post('/admin/knowledge/upload', include_in_schema=False)
    async def knowledge_upload(request: Request):
        body = await multipart_body(request)
        if isinstance(body, Response):
            return body
        def invoke():
            try:
                fields, uploads = upload_parts(*body)
            except (ValueError, TypeError):
                return JSONResponse({'error': 'Invalid attachment upload.', 'error_code': 'invalid_request'}, status_code=400)
            return interface_request(json.dumps(fields).encode(), knowledge='upload', uploads=uploads)
        return await run_in_threadpool(invoke)

    @app.post('/admin/knowledge/{action}', include_in_schema=False)
    async def knowledge_operation(action: str, request: Request):
        from tactic_stream.server.knowledge import OPERATIONS
        if action not in OPERATIONS or action == 'upload':
            return JSONResponse({'error': 'Unknown Knowledge Base operation.', 'error_code': 'invalid_request'}, status_code=400)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, knowledge=action)

    @app.post('/admin/server-updates', include_in_schema=False)
    async def server_updates(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, server_updates=True)

    @app.post('/admin/server-events', include_in_schema=False)
    async def server_events(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        # POST keeps login tickets out of URLs, browser history and proxy access logs.
        initial = await run_in_threadpool(interface_request, body, server_updates='presence')
        if initial.status_code != 200:
            return initial
        payload = json.loads(body)
        subscription = json.loads(initial.body)['result']['subscription']
        try:
            subscriber = await events.subscribe(payload['project'], subscription, dict(
                application={'TACTIC Handler':'TACTIC Handler', 'TACTIC Stream':'Web browser'}.get(request.headers.get('x-tactic-client'), 'Unknown client'),
                address=request.client.host if request.client else ''))
        except (OSError, ValueError):
            LOG.exception('Server event watcher could not start')
            return JSONResponse({'error': 'Update notifications are unavailable.', 'error_code': 'request_failed'}, status_code=503)
        try:
            # A fresh stream must invalidate retained client caches even without a journal cursor.
            stream_body = json.dumps(dict(payload, invalidated_types=subscription['search_types'] if 'cache' in subscription['channels'] else [])).encode()
            initial = await run_in_threadpool(interface_request, stream_body, server_updates='stream')
            if initial.status_code != 200:
                events.unsubscribe(subscriber)
                return initial
        except BaseException:
            events.unsubscribe(subscriber)
            raise

        async def stream():
            result = json.loads(initial.body)['result']
            previous_presence = presence_state(result)
            advance_cursors(payload, result)
            heartbeat_at = time.monotonic() + EVENT_HEARTBEAT
            try:
                yield event_frame('updates', result)
                while True:
                    try:
                        await asyncio.wait_for(subscriber['event'].wait(), max(0, heartbeat_at - time.monotonic()))
                    except TimeoutError:
                        pass
                    if subscriber.get('error'):
                        yield event_frame('error', {'error': 'Update notifications are unavailable.', 'error_code': 'request_failed', 'status': 503})
                        return
                    changes = set(subscriber['changes'])
                    subscriber['changes'].clear()
                    subscriber['event'].clear()
                    if time.monotonic() >= heartbeat_at:
                        response = await run_in_threadpool(interface_request, json.dumps(payload).encode(), server_updates='presence')
                        data = json.loads(response.body)
                        if response.status_code != 200:
                            yield event_frame('error', dict(data, status=response.status_code))
                            return
                        result = data['result']
                        subscriber['subscription'] = result['subscription']
                        presence_changed = presence_state(result) != previous_presence
                        previous_presence = presence_state(result)
                        heartbeat_at = time.monotonic() + EVENT_HEARTBEAT
                        if presence_changed:
                            result['presenceOnly'] = True
                            yield event_frame('updates', result)
                        yield ': keepalive\n\n'
                    if changes:
                        notification = matching_changes(subscriber, changes)
                        if notification['channels']:
                            yield event_frame('changes', notification)
            finally:
                events.unsubscribe(subscriber)

        class ServerEventResponse(StreamingResponse):
            async def __call__(self, scope, receive, send):
                try:
                    await super().__call__(scope, receive, send)
                finally:
                    # Headers can fail before the generator's finally is entered.
                    events.unsubscribe(subscriber)

        return ServerEventResponse(stream(), media_type='text/event-stream', headers={
            'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no', 'X-Content-Type-Options': 'nosniff'})

    @app.post('/admin/activity-feed', include_in_schema=False)
    async def activity_feed(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, activity=True)

    @app.post('/admin/navigation-link', include_in_schema=False)
    async def navigation_link(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, navigation_link=True)

    @app.post('/admin/transaction-log/details', include_in_schema=False)
    async def transaction_details(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, journal=True)

    @app.post('/admin/result-items', include_in_schema=False)
    async def result_items(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, result_items=True)

    @app.post('/admin/project-catalog', include_in_schema=False)
    async def project_catalog(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, project_catalog=True)

    @app.post('/admin/object-status', include_in_schema=False)
    async def object_status(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, status=True)

    @app.post('/admin/object-deletion/{action}', include_in_schema=False)
    async def object_deletion(action: str, request: Request):
        if action not in ('read', 'apply'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, deletion=action)

    @app.post('/admin/object-relations', include_in_schema=False)
    async def object_relations(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, relations=True)

    @app.post('/admin/interface', include_in_schema=False)
    async def admin_interface(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body)

    @app.post('/admin/navigation', include_in_schema=False)
    async def admin_navigation(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, navigation=True)

    @app.post('/admin/script-editor/{action}', include_in_schema=False)
    async def script_editor(action: str, request: Request):
        if action not in ('read', 'save', 'delete', 'history', 'revision', 'analyse'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, script_editor=action)

    @app.post('/admin/script-shelf/{action}', include_in_schema=False)
    async def script_shelf(action: str, request: Request):
        if action not in ('read', 'save', 'delete', 'assign', 'script'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, script_shelf=action)

    @app.post('/admin/workspace-layout/{action}', include_in_schema=False)
    async def workspace_layout(action: str, request: Request):
        if action not in ('read', 'save', 'delete'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, workspace_layout=action)

    @app.post('/admin/agent-project/{action}', include_in_schema=False)
    async def agent_project(action: str, request: Request):
        if action not in ('preview', 'create', 'read', 'export', 'install', 'operation'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, project_agent=action)

    @app.post('/admin/project-creation', include_in_schema=False)
    async def project_creation(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, project_creation=True)

    @app.post('/admin/form', include_in_schema=False)
    async def admin_form(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, True)

    @app.post('/admin/sidebar/{action}', include_in_schema=False)
    async def admin_sidebar(request: Request, action: str):
        if action not in ('read', 'edit', 'save'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, sidebar=action)

    @app.post('/admin/search-configuration/{action}', include_in_schema=False)
    async def search_configuration(request: Request, action: str):
        if action not in ('read', 'settings', 'save', 'delete', 'quick-save', 'query', 'tags', 'suggestions', 'visibility'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, search_configuration=action)

    @app.post('/admin/security-rules/{action}', include_in_schema=False)
    async def admin_security_rules(request: Request, action: str):
        if action not in ('read', 'save', 'effective'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, rules=action)

    @app.post('/admin/columns-editor/{action}', include_in_schema=False)
    async def admin_columns_editor(request: Request, action: str):
        if action not in ('read', 'save'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, columns=action)

    @app.post('/admin/security-users/{action}', include_in_schema=False)
    async def security_users(request: Request, action: str):
        if action not in ('read', 'save'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, users=action)

    @app.post('/admin/security-groups/{action}', include_in_schema=False)
    async def security_groups(request: Request, action: str):
        if action not in ('read', 'save'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, groups=action)

    @app.post('/admin/widget-configuration/{action}', include_in_schema=False)
    async def admin_widget_configuration(request: Request, action: str):
        if action not in ('catalog', 'read', 'check', 'preview', 'save'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, False, action)

    def session_action(body, action):
        try:
            payload = json.loads(body.decode('utf-8'), parse_constant=reject_json_constant)
            if not isinstance(payload, dict) or set(payload) != {'ticket'}:
                raise ValueError('Invalid session request')
            result = True
            if action == 'identity':
                login = api.auth.validate(payload['ticket'])
                with request_context(RequestContext(api.store, login, 'admin')):
                    security = api.auth.bind_security(login, payload['ticket'])
                    from tactic_stream.server.security_groups import user_identities
                    result = user_identities([security.get_login()])[0]
                    result['administration'] = security.is_admin()
            else:
                getattr(api.auth, action)(payload['ticket'])
            return JSONResponse({'result': result}, headers={'Cache-Control': 'no-store'})
        except (AuthenticationError, SecurityException):
            status, code, message = 403, 'authentication_failed', 'Invalid credentials or expired session.'
        except (ValueError, TypeError):
            status, code, message = 400, 'invalid_request', 'Check the project, object type and search parameters.'
        except UnsupportedContract:
            status, code, message = 501, 'unsupported_operation', 'This operation or object type is not available yet.'
        except Exception:
            LOG.exception('Session request failed')
            status, code, message = 500, 'request_failed', 'Request failed.'
        return JSONResponse({'error': message, 'error_code': code}, status_code=status, headers={'Cache-Control': 'no-store'})

    @app.post('/admin/session/{action}', include_in_schema=False)
    async def admin_session(request: Request, action: str):
        if action not in ('logout', 'renew', 'identity'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(session_action, body, action)

    def configuration_request(body, save=False, lifecycle=None):
        from pyasm.common.config import ConfigException, ConfigConflict
        try:
            payload = json.loads(body.decode('utf-8'), parse_constant=reject_json_constant)
            fields = {'ticket', 'revision', 'instance_id', 'request_id'} if lifecycle == 'restart' else {'ticket', 'changes', 'revision'} if save else {'ticket'}
            if not isinstance(payload, dict) or set(payload) != fields:
                raise ValueError('Invalid configuration request')
            login = api.auth.validate(payload['ticket'])
            with request_context(RequestContext(api.store, login, 'admin')):
                api.auth.bind_security(login, payload['ticket'])
                from tactic_stream.server.configuration import read_configuration, save_configuration
                if lifecycle:
                    from tactic_stream.server.lifecycle import read_runtime, request_restart
                    result = request_restart(payload['revision'], payload['instance_id'], payload['request_id']) if lifecycle == 'restart' else read_runtime()
                else:
                    result = save_configuration(payload['changes'], payload['revision']) if save else read_configuration()
            return JSONResponse({'result': result}, headers={'Cache-Control': 'no-store'})
        except AuthenticationError:
            status, code, message = 403, 'authentication_failed', 'Invalid credentials or expired session.'
        except SecurityException:
            status, code, message = 403, 'access_denied', 'Server configuration requires administrator access.'
        except ConfigConflict:
            return JSONResponse({'error': 'Configuration changed or another save is in progress. Reload before saving.',
                                 'error_code': 'configuration_conflict'}, status_code=409, headers={'Cache-Control': 'no-store'})
        except ConfigException as error:
            return JSONResponse({'error': error.hint or 'Check the service values and worker settings.',
                                 'error_code': 'invalid_configuration', 'error_field': error.field},
                                status_code=400, headers={'Cache-Control': 'no-store'})
        except UnsupportedContract:
            status, code, message = 501, 'unsupported_operation', 'This operation or object type is not available yet.'
        except OSError:
            LOG.exception('Configuration file is unavailable')
            status, code, message = 503, 'configuration_unavailable', 'The configuration file could not be saved. Check file permissions and disk space.'
        except (ValueError, TypeError):
            status, code, message = 400, 'invalid_request', 'Check the project, object type and search parameters.'
        except Exception:
            LOG.exception('Configuration read failed')
            status, code, message = 500, 'request_failed', 'Request failed.'
        return JSONResponse({'error': message, 'error_code': code}, status_code=status, headers={'Cache-Control': 'no-store'})

    @app.post('/admin/raw-database/{action}', include_in_schema=False)
    async def admin_raw_database(request: Request, action: str):
        if action not in ('list', 'load', 'save', 'drop', 'export'):
            return JSONResponse({'error': 'Unknown raw database operation.'}, status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, raw_database=action)

    @app.post('/admin/configuration/restart', include_in_schema=False)
    @app.post('/admin/configuration/runtime', include_in_schema=False)
    async def admin_configuration_lifecycle(request: Request):
        action = request.url.path.rsplit('/', 1)[-1]
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(configuration_request, body, lifecycle=action)

    @app.post('/admin/configuration', include_in_schema=False)
    async def admin_configuration(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(configuration_request, body)

    @app.post('/admin/configuration/save', include_in_schema=False)
    async def admin_configuration_save(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(configuration_request, body, True)

    @app.get("/ui/{asset:path}", include_in_schema=False)
    def ui_asset(asset: str, request: Request):
        path = PurePosixPath(asset)
        if '\\' in asset or any(part in (".", "..") for part in asset.split('/')) or path.is_absolute():
            return Response(status_code=404)
        content_type = {".js": "text/javascript", ".css": "text/css", ".ttf": "font/ttf", ".png": "image/png"}.get(path.suffix) if path.parts and path.parts[0] == 'assets' else None
        if path.parts and path.parts[0] == 'assets' and path.name.endswith(('.js.map', '.css.map')):
            content_type = 'application/json'
        if path.parts[:2] == ('licenses', 'icon-fonts') and path.suffix in ('.txt', '.md'):
            content_type = 'text/plain'
        help_asset = path.parts and path.parts[0] == 'help'
        if help_asset and len(path.parts) == 2:
            if asset == 'help/index.json':
                content_type = 'application/json'
            elif path.suffix == '.md':
                content_type = 'text/plain'
        if help_asset and path.parts[:2] == ('help', 'media') and len(path.parts) == 3:
            content_type = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(path.suffix)
        if not content_type:
            return Response(status_code=404)
        resource = files("tactic_stream") / "web" / asset
        if not resource.is_file():
            return Response(status_code=404)
        content = resource.read_bytes()
        headers = {
            "Cache-Control": "no-store" if help_asset else "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff",
        }
        compress = False
        if len(content) >= 1024 and content_type in ('text/javascript', 'text/css', 'text/plain', 'application/json', 'font/ttf'):
            headers['Vary'] = 'Accept-Encoding'
            encodings = {}
            for encoding in request.headers.get('accept-encoding', '').lower().split(','):
                name, _, parameter = encoding.strip().partition(';')
                try:
                    quality = float(parameter.strip().removeprefix('q=')) if parameter else 1.0
                except ValueError:
                    quality = 0.0
                encodings[name.strip()] = quality
            compress = 0 < encodings.get('gzip', encodings.get('*', 0)) <= 1
            if compress:
                headers['Content-Encoding'] = 'gzip'
        if path.parts[0] == 'assets' and (path.suffix in ('.js', '.css') or path.name.endswith(('.js.map', '.css.map'))):
            headers['Cache-Control'] = 'public, no-cache'
            headers['ETag'] = '"' + sha256(content).hexdigest() + ('-gzip' if compress else '') + '"'
            if any(tag.strip().removeprefix('W/') in ('*', headers['ETag']) for tag in request.headers.get('if-none-match', '').split(',')):
                return Response(status_code=304, headers=headers)
        if compress:
            content = gzip.compress(content, compresslevel=6, mtime=0)
        return Response(content, media_type=content_type, headers=headers)

    def invoke(body, environ=None):
        method, script_error = None, None
        try:
            # No DTD/entity support; XML-RPC clients do not require either.
            def reject_declaration(*args):
                raise ValueError("DTD/entity declarations are not accepted")
            parser = expat.ParserCreate()
            parser.StartDoctypeDeclHandler = reject_declaration
            parser.EntityDeclHandler = reject_declaration
            parser.Parse(body, True)
            args, method = loads(body, use_builtin_types=True)
            result = api.dispatch(method, args, environ=environ)
            return encode_response(result)
        except AuthenticationError as error:
            message = {
                'Project unavailable': 'No project available',
                'Login/Password combination incorrect': 'Login/Password combination incorrect',
            }.get(str(error), 'Invalid or expired ticket. Session may have expired.')
            fault = Fault(403, message)
        except SecurityException as error:
            fault = Fault(403, "Permission denied")
            script_error = error
        except UnsupportedContract as exc:
            fault = Fault(501, str(exc))
        except PartialCommitException as error:
            LOG.exception('Partial database commit')
            fault = Fault(500, str(error))
        except (ValueError, TypeError, LookupError, TacticException, expat.ExpatError) as error:
            fault = Fault(400, "Invalid XML-RPC arguments or missing object")
            script_error = error
        except sqlite3.OperationalError:
            fault = Fault(503, "Database unavailable; initialize a new owned data directory first")
        except Exception as error:
            # Ordinary transport failures stay private. Script diagnostics below
            # are only reachable after PythonCmd's trusted-execution check.
            LOG.exception("XML-RPC request failed")
            fault = Fault(500, "Internal server error")
            script_error = error
        if method == 'execute_python_script' and getattr(script_error, 'tactic_script_sources', None):
            from tactic.command.python_cmd import format_script_traceback
            fault.faultString = format_script_traceback(script_error)
        elif method == 'execute_js_script' and getattr(script_error, 'tactic_js_source', None):
            fault.faultString = script_error.tactic_js_source + '\n' + str(script_error)
        return dumps(fault, allow_none=True).encode("utf-8")

    @app.post("/tactic/{route_project}/Api/")
    async def xmlrpc(request: Request, route_project: str):
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                return Response(status_code=413)
            body.extend(chunk)
        result = await run_in_threadpool(invoke, bytes(body), request_environ(request))
        return Response(result, media_type="text/xml", headers={"Cache-Control": "no-store"})

    def invoke_upload(content_type, body):
        try:
            fields, uploads = upload_parts(content_type, body)
            return JSONResponse(api.http_upload(fields, uploads), headers={'Cache-Control': 'no-store'})
        except (AuthenticationError, SecurityException):
            status, message = 403, 'Invalid credentials or expired session.'
        except UnsupportedContract:
            status, message = 501, 'This upload operation is not available yet.'
        except PartialCommitException as error:
            LOG.exception('Partial upload commit')
            status, message = 500, str(error)
        except (ValueError, TypeError, LookupError, TacticException):
            status, message = 400, 'Invalid upload request.'
        except Exception:
            LOG.exception('HTTP upload failed')
            status, message = 500, 'Upload failed.'
        return JSONResponse({'error': message}, status_code=status, headers={'Cache-Control': 'no-store'})

    async def multipart_body(request):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return Response(status_code=403)
        content_type = request.headers.get('content-type', '')
        if content_type.split(';', 1)[0].strip().lower() != 'multipart/form-data':
            return Response(status_code=415)
        # ponytail: multipart parsing holds one bounded chunk in memory; streaming parser
        # only needed for clients that cannot split requests below 64 MiB.
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_UPLOAD_BODY:
                return Response(status_code=413)
            body.extend(chunk)
        return content_type, bytes(body)

    @app.post('/admin/checkin-queue/submit', include_in_schema=False)
    async def checkin_queue_submit(request: Request):
        body = await multipart_body(request)
        if isinstance(body, Response):
            return body
        def invoke():
            try:
                fields, uploads = upload_parts(*body, max_field_bytes=1024 * 1024)
            except (ValueError, TypeError, UnicodeError):
                return JSONResponse({'error': 'Invalid check-in chunk.', 'error_code': 'invalid_request'}, status_code=400)
            return interface_request(json.dumps(fields).encode(), checkin_queue='submit', uploads=uploads)
        return await run_in_threadpool(invoke)

    @app.post('/admin/checkin-queue/{action}', include_in_schema=False)
    async def checkin_queue_action(request: Request, action: str):
        if action not in ('updates', 'cancel'):
            return Response(status_code=404)
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, checkin_queue=action)

    @app.post('/tactic/{route_project}/UploadServer/', include_in_schema=False)
    async def upload_server(request: Request, route_project: str):
        body = await multipart_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(invoke_upload, *body)

    from tactic_stream.server.file_project import install_routes
    install_routes(app, api)

    @app.post('/admin/custom-url', include_in_schema=False)
    async def custom_url(request: Request):
        body = await admin_body(request)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(interface_request, body, custom_url=True)

    from tactic_stream.server.custom_urls import install_rest_routes
    install_rest_routes(app, invoke_json, workspace_index, request_environ)

    if mcp_enabled:
        from tactic_stream.server.mcp_gateway import McpGateway
        app.mount('/mcp',McpGateway(app,api),name='project-mcp')

    return app
