"""Streaming HTTP transport; authorization, progress and offsets remain native commands."""
import asyncio
from hashlib import sha256
from pathlib import Path
from time import monotonic
import os

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request, ClientDisconnect
from starlette.responses import JSONResponse, StreamingResponse

from pyasm.biz.file_project import COMMAND
from pyasm.biz.file_bytes import byte_lock
from pyasm.common.errors import AuthenticationError, SecurityException
from tactic.command.file_transfer import BLOCK_BYTES, TRANSFER_ACTIONS
from tactic.command.file_project_cmd import FILE_ACTIONS
from tactic.command.file_reads import READ_ACTIONS
from tactic.command.file_storage import STORAGE_ACTIONS, FileProjectBusy
from tactic.command.file_bulk import BULK_ACTIONS


def install_routes(app, api):
    slots = asyncio.Semaphore(4)

    def call(request, action, **kwargs):
        ticket = request.headers.get('X-Tactic-Ticket')
        project = request.query_params.get('project')
        if not ticket or not project:
            raise AuthenticationError('Ticket and project required')
        return api.dispatch('execute_cmd', ({'ticket': ticket, 'project': project}, COMMAND,
                             {'action': action, **kwargs}))['info']

    def busy_response(exc):
        return JSONResponse({'error': str(exc), 'error_code': 'file_project_busy'}, status_code=503,
                            headers={'Retry-After': '1', 'X-Tactic-Error': 'file_project_busy'})

    @app.post('/file-project/command', include_in_schema=False)
    async def command(request: Request):
        action = 'command'
        try:
            import json
            body = bytearray()
            async for part in request.stream():
                if len(body) + len(part) > 3 * 1024 * 1024:
                    return JSONResponse({'error': 'Metadata request exceeds 3 MiB'}, status_code=413)
                body.extend(part)
            arguments = json.loads(body)
            action = arguments.pop('action')
            public_bulk = BULK_ACTIONS - {'bulk_claim','bulk_run','bulk_fail','bulk_block'}
            if action not in TRANSFER_ACTIONS | FILE_ACTIONS | STORAGE_ACTIONS | READ_ACTIONS | public_bulk | {'gc_begin', 'gc_status', 'gc_cancel'}:
                raise ValueError('File-project action required')
            return JSONResponse(await run_in_threadpool(call, request, action, **arguments), headers={'Cache-Control': 'no-store'})
        except FileProjectBusy as exc:
            return busy_response(exc)
        except (AuthenticationError, SecurityException) as exc:
            return JSONResponse({'error': str(exc)}, status_code=403)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            details={'error':str(exc)}
            if getattr(exc,'file_error',None):details['file_error']={**exc.file_error,'operation':action}
            return JSONResponse(details, status_code=400)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception('File-project command failed: %s', action)
            details = {'error': 'File operation failed. See the server log for details.'}
            if getattr(exc, 'file_error', None):
                details['file_error'] = {**exc.file_error, 'operation': action}
            return JSONResponse(details, status_code=500)

    @app.put('/file-project/transfer-upload', include_in_schema=False)
    async def upload(request: Request):
        lease = None
        completed = False
        args = {key: request.query_params.get(key) for key in ('task', 'blob')}
        batch = request.query_params.get('batch') == '1'
        try:
            size = int(request.headers.get('Content-Length', '0'))
            offset = int(request.query_params.get('offset', '0'))
            if not 1 <= size <= BLOCK_BYTES:
                raise ValueError('Streaming block requires Content-Length within 64 MiB')
            async with slots:
                lease = await run_in_threadpool(call, request, 'transfer_write_begin', **args, batch=batch, size=size, offset=offset)
                path = Path(lease['_path'])
                digest, received, touched = sha256(), 0, monotonic()
                with byte_lock(path):
                    await run_in_threadpool(call, request, 'transfer_write_touch', **args, token=lease['token'])
                    with path.open('w+b' if batch or not path.exists() else 'r+b') as output:
                        output.truncate(offset)
                        output.seek(offset)
                        buf = bytearray()
                        async for block in request.stream():
                            received += len(block)
                            if received > size:
                                raise ValueError('Upload exceeded declared block size')
                            digest.update(block)
                            buf.extend(block)
                            if len(buf) >= 1024 * 1024:
                                await run_in_threadpool(output.write, bytes(buf))
                                buf.clear()
                            if monotonic() - touched > 10:
                                await run_in_threadpool(call, request, 'transfer_write_touch', **args, token=lease['token'])
                                touched = monotonic()
                        if buf:
                            await run_in_threadpool(output.write, bytes(buf))
                            buf.clear()
                        if received != size:
                            raise ValueError('Truncated upload block')
                        if request.headers.get('X-Chunk-SHA256') and digest.hexdigest() != request.headers['X-Chunk-SHA256']:
                            raise ValueError('Upload block checksum mismatch')
                        await run_in_threadpool(output.flush)
                        await run_in_threadpool(os.fsync, output.fileno())
                    result = await run_in_threadpool(call, request,
                        'transfer_batch_commit' if batch else 'transfer_write_commit', **args, token=lease['token'])
                    completed = True
                return JSONResponse(result, headers={'Cache-Control': 'no-store'})
        except FileProjectBusy as exc:
            return busy_response(exc)
        except (AuthenticationError, SecurityException) as exc:
            return JSONResponse({'error': str(exc)}, status_code=403)
        except (ValueError, TypeError, OSError, ClientDisconnect) as exc:
            return JSONResponse({'error': str(exc)}, status_code=400)
        finally:
            if lease:
                if not completed:
                    deadline = monotonic() + 120
                    while True:
                        try:
                            await run_in_threadpool(call, request, 'transfer_write_abort', **args, token=lease['token'])
                            break
                        except FileProjectBusy:
                            if monotonic() >= deadline:
                                break
                            await asyncio.sleep(1)
                        except Exception:
                            # Expiry permits recovery when the database or owner permissions are unavailable.
                            break
                if batch:
                    Path(lease['_path']).unlink(missing_ok=True)

    @app.get('/file-project/manifest', include_in_schema=False)
    async def manifest(request: Request):
        try:
            args = {key: request.query_params[key] for key in ('task', 'after') if key in request.query_params}
            result = await run_in_threadpool(call, request, 'transfer_next', **args)
            import json
            def lines():
                yield json.dumps({key: value for key, value in result.items() if key != 'items'}).encode() + b'\n'
                for entry in result['items']:
                    yield json.dumps(entry, ensure_ascii=False).encode('utf-8') + b'\n'
            return StreamingResponse(lines(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})
        except (AuthenticationError, SecurityException) as exc:
            return JSONResponse({'error': str(exc)}, status_code=403)
        except (ValueError, TypeError) as exc:
            return JSONResponse({'error': str(exc)}, status_code=400)
