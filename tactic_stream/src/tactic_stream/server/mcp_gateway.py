"""Opt-in authenticated MCP HTTP; tools reuse the existing native API in process."""
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from .mcp_access import authorize,permitted_tool


def build_server(app, base, api, grant, ticket, token):
    import anyio
    import httpx2 as httpx
    from tactic_stream.admin_agent import StreamConnection,create_server

    class LocalConnection(StreamConnection):
        def request(self, path, payload=None):
            async def send_request():
                await run_in_threadpool(authorize,api,grant['id'],token)
                # ASGITransport never follows a Host header to a network destination.
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=base) as client:
                    response=await client.request('GET' if payload is None else 'POST',path,json=payload)
                result=self._decode(response.content)
                if response.status_code!=200:
                    from mcp.server.mcpserver.exceptions import ToolError
                    raise ToolError(str(result.get('error','TACTIC request failed')))
                return result
            return anyio.from_thread.run(send_request)

    root=Path(__file__).resolve().parents[3]
    handler=root.parent.parent/'TH'
    connection=LocalConnection(base,grant['project'],ticket)
    return create_server(connection,root,handler if handler.is_dir() else None,
        allow_naming_save=True,allow_page_save=True,allow_automation_draft=True,
        allow_project_edit=True,request_id=grant['id'])


class McpGateway:
    def __init__(self, app, api):
        self.app,self.api=app,api

    async def __call__(self, scope, receive, send):
        if scope['type']!='http':
            return
        from pyasm.common.errors import AuthenticationError,SecurityException
        request=Request(scope,receive)
        authorization=request.headers.get('authorization','')
        token=authorization[7:] if authorization.startswith('Bearer ') else ''
        code=scope['path'].removeprefix(scope.get('root_path','')).strip('/')
        headers={'Cache-Control':'no-store','WWW-Authenticate':'Bearer','X-Content-Type-Options':'nosniff'}
        try:
            grant,ticket=await run_in_threadpool(authorize,self.api,code,token)
        except (ValueError,LookupError,PermissionError,AuthenticationError,SecurityException):
            await JSONResponse({'error':'MCP connection is unavailable.'},status_code=401,headers=headers)(scope,receive,send)
            return
        try:
            server=await run_in_threadpool(build_server,self.app,str(request.base_url).rstrip('/'),self.api,grant,ticket,token)
            for tool in await server.list_tools():
                if tool.name not in grant['tools'] or not permitted_tool(tool.name):
                    server.remove_tool(tool.name)
            from mcp.server.transport_security import TransportSecuritySettings
            from pyasm.common import Config
            host=Config.get_value('install','hostname') or 'localhost'
            hosts=list(dict.fromkeys([host,'127.0.0.1','localhost','[::1]']))
            security=TransportSecuritySettings(allowed_hosts=[name+':*' for name in hosts],
                allowed_origins=[scheme+'://'+name+':*' for scheme in ('http','https') for name in hosts])
            endpoint=server.streamable_http_app(streamable_http_path='/',json_response=True,stateless_http=True,
                max_request_body_size=1024*1024,transport_security=security)
            forwarded=dict(scope,path='/',raw_path=b'/',root_path='')
            async with server.session_manager.run():
                await endpoint(forwarded,receive,send)
        except ImportError:
            await JSONResponse({'error':'Install tactic-stream[agent] to enable MCP.'},status_code=503,headers=headers)(scope,receive,send)
