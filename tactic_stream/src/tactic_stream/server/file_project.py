"""Binary transport only; file authorization and mutations use the native command."""
from pathlib import Path, PurePosixPath
import tarfile

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from pyasm.biz.file_project import COMMAND, blob_file_path
from pyasm.common.errors import AuthenticationError, SecurityException
from tactic.command.file_project_cmd import TRANSFER_LIMIT


_ATTACHMENT_SUFFIXES = {
    '.html', '.htm', '.xhtml', '.svg', '.svgz', '.xml', '.xsl',
    '.js', '.mjs', '.cjs', '.swf', '.mhtml',
}


class FileProjectStaticFiles(StaticFiles):
    def __init__(self, *args, private_jobs=None, api=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.private_jobs=Path(private_jobs).resolve() if private_jobs else None
        self.api = api

    async def get_response(self, path, scope):
        absolute = (Path(self.directory) / path).resolve()
        if self.private_jobs and absolute.is_relative_to(self.private_jobs):
            raise HTTPException(404)
        if any(part.casefold() == 'file-projects' or part.casefold().endswith('.file-projects') for part in absolute.parts):
            raise HTTPException(404)
        if self.api is not None:
            def check_auth():
                from pyasm.common import Config
                from pyasm.search.search import RequestContext, request_context
                with request_context(RequestContext(self.api.store, 'admin')):
                    if Config.get_value('security', 'require_asset_auth') != 'true':
                        return True
                request = Request(scope)
                ticket = (
                    request.headers.get('X-Tactic-Ticket')
                    or request.query_params.get('ticket')
                    or request.query_params.get('login_ticket')
                    or request.cookies.get('login_ticket')
                    or ''
                )
                auth_header = request.headers.get('Authorization', '')
                if not ticket and auth_header.lower().startswith('bearer '):
                    ticket = auth_header[7:].strip()
                if not ticket:
                    return False
                try:
                    self.api.auth.validate(ticket)
                    return True
                except Exception:
                    return False
            if not await run_in_threadpool(check_auth):
                raise HTTPException(403)
        response = await super().get_response(path, scope)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'none'; img-src 'self' data:; media-src 'self'; style-src 'unsafe-inline'; sandbox",
        )
        if absolute.suffix.lower() in _ATTACHMENT_SUFFIXES:
            response.headers.setdefault('Content-Disposition', 'attachment')
        return response


def install_routes(app, api):
    from .file_transfers import install_routes as install_transfers
    install_transfers(app, api)
    def archive(project, items):
        for item in items:
            if item.get('deleted') or item['size'] > TRANSFER_LIMIT:
                continue
            header = tarfile.TarInfo(item.get('local_path', item['path']))
            header.size, header.mode = item['size'], 0o644
            yield header.tobuf(format=tarfile.PAX_FORMAT, encoding='utf-8')
            with blob_file_path(project, item['blob'], api.store.data_dir, item.get('_storage_root')).open('rb') as stream:
                remaining = item['size']
                while remaining:
                    part = stream.read(min(TRANSFER_LIMIT, remaining))
                    if not part:
                        raise OSError('Committed blob is shorter than its catalog entry')
                    remaining -= len(part)
                    yield part
            if item['size'] % 512:
                yield bytes(512 - item['size'] % 512)
        yield bytes(1024)

    def invoke(request, arguments):
        ticket = request.headers.get('X-Tactic-Ticket', '')
        project = request.query_params.get('project', '')
        try:
            if not ticket or not project:
                raise AuthenticationError('Ticket and project required')
            result = api.dispatch('execute_cmd', ({'ticket': ticket, 'project': project}, COMMAND, arguments))['info']
            if arguments['action'] == 'sync_next':
                if 'download_paths' in arguments:
                    paths = arguments['download_paths']
                    if not isinstance(paths, list) or len(paths) > 1000 or any(not isinstance(path, str) for path in paths):
                        raise ValueError('Download subset requires a bounded path list')
                    selected = set(paths)
                    if result['ack_revision'] != arguments.get('ack_revision') or selected - {item['path'] for item in result['items']}:
                        raise ValueError('Download subset differs from pinned plan')
                    result['items'] = [item for item in result['items'] if item['path'] in selected]
                return StreamingResponse(archive(project, result['items']), media_type='application/x-tar',
                    headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                             'X-Tactic-Ack-Revision': str(result['ack_revision'])})
            if arguments['action'] == 'transfer':
                return FileResponse(blob_file_path(project, result['blob'], api.store.data_dir, result.get('_storage_root')),
                    filename=PurePosixPath(result['path']).name, media_type='application/octet-stream',
                    headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
            return JSONResponse(result, headers={'Cache-Control': 'no-store'})
        except (AuthenticationError, SecurityException) as exc:
            return JSONResponse({'error': str(exc)}, status_code=403)
        except FileNotFoundError:
            return JSONResponse({'error': 'File not found'}, status_code=404)
        except (ValueError, TypeError) as exc:
            return JSONResponse({'error': str(exc)}, status_code=400)

    @app.get('/file-project/download', include_in_schema=False)
    async def download(request: Request):
        args = {key: request.query_params[key] for key in
                ('stream', 'path', 'published_change', 'change', 'shelf', 'integration', 'conflict_side', 'sync', 'source_path', 'workspace')
                if key in request.query_params}
        if 'ack_revision' in request.query_params:
            try:args['ack_revision']=int(request.query_params['ack_revision'])
            except ValueError:return JSONResponse({'error':'Invalid sync revision'},status_code=400)
        if 'edit_revision' in request.query_params:
            try:
                args['edit_revision'] = int(request.query_params['edit_revision'])
            except ValueError:
                return JSONResponse({'error': 'Invalid edit revision'}, status_code=400)
        if 'have' in request.query_params:
            have=request.query_params['have'].lower()
            if have not in ('true','false','1','0'):
                return JSONResponse({'error':'Invalid Have selector'},status_code=400)
            args['have']=have in ('true','1')
        return await run_in_threadpool(invoke, request, {'action': 'transfer', **args})

    @app.get('/file-project/sync-download', include_in_schema=False)
    async def sync_download(request: Request):
        return await run_in_threadpool(invoke, request, {'action': 'sync_next', 'sync': request.query_params.get('sync')})

    @app.post('/file-project/sync-download', include_in_schema=False)
    async def sync_download_subset(request: Request):
        try:
            import json
            body = bytearray()
            async for part in request.stream():
                if len(body) + len(part) > 3 * 1024 * 1024:
                    return JSONResponse({'error': 'Download subset exceeds 3 MiB'}, status_code=413)
                body.extend(part)
            data = json.loads(body)
            return await run_in_threadpool(invoke, request, {'action': 'sync_next', 'sync': data['sync'],
                'ack_revision': data['ack_revision'], 'download_paths': data['paths']})
        except (ValueError, TypeError, KeyError) as exc:
            return JSONResponse({'error': str(exc)}, status_code=400)

    @app.put('/file-project/upload', include_in_schema=False)
    async def upload(request: Request):
        body = bytearray()
        async for part in request.stream():
            if len(body) + len(part) > TRANSFER_LIMIT:
                return JSONResponse({'error': 'Transfer chunk exceeds limit'}, status_code=413)
            body.extend(part)
        try:
            offset = int(request.query_params.get('offset', '0'))
        except ValueError:
            return JSONResponse({'error': 'Invalid upload offset'}, status_code=400)
        args = {key: request.query_params.get(key) for key in ('change', 'blob')}
        return await run_in_threadpool(invoke, request,
            {'action': 'upload_chunk', **args, 'offset': offset, 'data': bytes(body)})
