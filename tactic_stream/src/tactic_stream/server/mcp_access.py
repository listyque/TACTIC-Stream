"""Revocable project MCP access; native credentials never leave the server vault."""
import asyncio
import hashlib
import hmac
import json
import secrets
from pathlib import Path
import time
from uuid import UUID

from pyasm.biz import Project
from pyasm.common import Environment


def directory():
    return Path(Environment.get_data_dir())/'agent_mcp'


def read_grant(code, root=None):
    if not isinstance(code,str) or str(UUID(code))!=code:
        raise ValueError('Invalid MCP connection identity')
    path=(root or directory())/(code+'.json')
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def expired(grant):
    return grant['expires'] is not None and time.time() >= grant['expires']


def credential(grant, unlimited):
    from pyasm.security import Ticket
    from tactic_stream.provider_credentials import seal
    if unlimited:
        if grant.get('credential_owned'):
            return grant['credential'], True
        key=secrets.token_urlsafe(32)
        Ticket.create(key,grant['owner'],expiry=-1,category='mcp:'+grant['id'])
        return seal(key), True
    return seal(Environment.get_security().get_ticket_key()), False


def retire_credential(grant):
    if not grant.get('credential_owned'):
        return
    from pyasm.security import Ticket
    from tactic_stream.provider_credentials import unseal
    ticket=Ticket.get_by_key(unseal(grant['credential']))
    if ticket:
        if ticket.get_value('login')!=grant['owner'] or ticket.get_value('category')!='mcp:'+grant['id']:
            raise ValueError('MCP connection credential ownership mismatch')
        ticket.delete(triggers=False)


def current_grant(row):
    if row.get('transport')!='mcp':
        return None
    grant=read_grant(row['request_id'])
    if (grant and grant['owner']==Environment.get_user_name() and grant['project']==Project.get_project_code()
            and not grant['revoked'] and not expired(grant) and grant['allow_changes']):
        return grant
    return None


def public(grant):
    from tactic.ui.panel.page_cmd import digest
    return dict({key:grant[key] for key in ('id','title','project','created','expires','revoked','tools')},
                pending=bool(grant.get('pending_token')),
                revision=digest([grant['tools'],grant['expires'],grant['revoked'],grant.get('request_hash')]))


def project_context(api, grant, ticket):
    result=api.dispatch('execute_cmd',(dict(ticket=ticket,project=grant['project']),
        'tactic.ui.panel.agent_request_cmd.AgentRequestCmd',
        dict(action='read',project_code=grant['project'],request_id=grant['id'])))
    document=result['info']['document']
    return dict(context=document['context'],instructions=document['prompt'])


def permitted_tool(name):
    # No cross-project history, project creation/template access or provider administration.
    return not name.startswith(('ts_project_','ts_mcp_','agent_conversation','agent_provider'))


def tool_catalog():
    from tactic_stream.admin_agent import StreamConnection,create_server
    root=Path(__file__).resolve().parents[3]
    server=create_server(StreamConnection('http://tactic.internal',Project.get_project_code(),'private-server-credential'),root,
        allow_naming_save=True,allow_page_save=True,allow_automation_draft=True,
        allow_project_edit=True,request_id='00000000-0000-4000-8000-000000000000')
    tools=asyncio.run(server.list_tools())
    return [dict(name=tool.name,title=tool.title or tool.name.replace('_',' '),
        description=(tool.description or '').split('\n')[0],readonly=bool(tool.annotations and tool.annotations.read_only_hint))
        for tool in tools if permitted_tool(tool.name)]


def authorize(api, code, token):
    from pyasm.search.search import RequestContext,request_context
    from pyasm.search import Search
    from tactic_stream.provider_credentials import unseal
    from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
    from .navigation_links import check_project
    grant=read_grant(code,api.store.data_dir/'agent_mcp')
    if (not grant or grant['revoked'] or expired(grant) or not token or len(token)>512
            or not hmac.compare_digest(grant['token_hash'],hashlib.sha256(token.encode()).hexdigest())):
        raise ValueError('MCP connection is unavailable')
    ticket=unseal(grant['credential'])
    owner=api.auth.validate(ticket)
    if owner!=grant['owner']:
        raise ValueError('MCP connection is unavailable')
    with request_context(RequestContext(api.store,owner,grant['project'])):
        api.auth.bind_security(owner,ticket)
        check_project(grant['project'])
        if not Environment.get_security().is_admin():
            raise ValueError('MCP connection owner no longer has administrator access')
        reader=AgentRequestCmd();reader.owner=owner;reader.sql=Search('config/trigger').get_sql()
        row=reader.load('spt_agent_request',code)
        if row.get('transport')!='mcp' or row['document']['context']['project']!=grant['project']:
            raise ValueError('MCP connection is unavailable')
    return grant,ticket
