"""Explicit owner-managed MCP grants; no native session ticket in client output."""
import hashlib
import json
import secrets
import time
from uuid import uuid4

from pyasm.biz import Project
from pyasm.common import Environment,Container,Config
from pyasm.common.config import config_file_lock
from pyasm.search import Search
from pyasm.security.security import _require_admin
from tactic_stream.provider_credentials import seal,unseal
from tactic_stream.server import mcp_access
from .agent_request_cmd import AgentRequestCmd,context_document,text,identity
from .page_cmd import digest


class AgentMcpCmd(AgentRequestCmd):
    @classmethod
    def is_undoable(cls):
        return False

    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code')!=Project.get_project_code():
            raise ValueError('MCP connection project mismatch')
        self.owner=Environment.get_user_name()
        self.sql=Search('config/trigger').get_sql()
        root=mcp_access.directory();root.mkdir(parents=True,exist_ok=True)
        action=self.kwargs.get('action')
        enabled=(Container.get('Api:environ') or {}).get('MCP_ENABLED',Config.get_value('security','agent_mcp_enabled')=='true')
        if action not in ('state','create','revoke','reveal'):
            raise ValueError('Unknown MCP connection action')
        request_id=self.kwargs.get('request_id')
        if request_id:
            row=self.load('spt_agent_request',identity(request_id))
            if row.get('transport')=='mcp':
                raise ValueError('MCP connections cannot delegate their access')
            if action not in ('state',) and (row['status']!='running' or not row['document']['allow_changes']):
                raise ValueError('This request does not allow configuration changes')
            if action=='reveal':
                raise ValueError('Collect the connection token in the MCP window')
        with config_file_lock(root/'collection.lock'):
            if action in ('revoke','reveal'):
                grant=mcp_access.read_grant(self.kwargs.get('id'))
                if not grant or grant['owner']!=self.owner or grant['project']!=Project.get_project_code():
                    raise ValueError('MCP connection is unavailable')
                if action=='reveal':
                    self.load('spt_agent_request',grant['id'])
                    if grant['revoked'] or grant['expires']<=time.time() or not grant.get('pending_token'):
                        raise ValueError('This connection token is no longer available')
                    token=unseal(grant.pop('pending_token'))
                    self.write_grant(root,grant)
                    return dict(mcp_access.public(grant),token=token,path='/mcp/'+grant['id'])
                grant['revoked']=True
                grant.pop('pending_token',None)
                self.write_grant(root,grant)
            if action=='create':
                if not enabled:
                    raise ValueError('Enable external MCP connections in Server configuration and restart first')
                catalog=mcp_access.tool_catalog()
                tools=self.kwargs.get('tools')
                if (not isinstance(tools,list) or not tools or any(not isinstance(tool,str) for tool in tools)
                        or len(set(tools))!=len(tools) or not set(tools)<={tool['name'] for tool in catalog}):
                    raise ValueError('Choose tools from this server catalogue')
                minutes=self.kwargs.get('minutes',60)
                if type(minutes) is not int or not 5<=minutes<=480:
                    raise ValueError('MCP access lifetime must be between 5 and 480 minutes')
                title=text(self.kwargs.get('title'),256)
                instructions=text(self.kwargs.get('instructions',''),16384,empty=True)
                context=context_document(row['document']['context'] if request_id else self.kwargs.get('context'))
                deferred=bool(request_id)
                code=identity(self.kwargs.get('operation_id')) if deferred else str(uuid4())
                fingerprint=digest([title,instructions,tools,minutes,context])
                existing=mcp_access.read_grant(code)
                if existing:
                    if existing['owner']!=self.owner or existing['project']!=Project.get_project_code() or existing.get('request_hash')!=fingerprint:
                        raise ValueError('Operation ID belongs to another MCP connection')
                    if not self.load('spt_agent_request',code,missing=True):
                        raise ValueError('Previous connection publication was incomplete. Revoke it and create a new connection.')
                    return dict(mcp_access.public(existing),path='/mcp/'+code,collect_in='MCP connections')
                token=secrets.token_urlsafe(32)
                now=int(time.time())
                writable=any(not tool['readonly'] for tool in catalog if tool['name'] in tools)
                grant=dict(id=code,title=title,project=Project.get_project_code(),owner=self.owner,
                    created=now,expires=now+minutes*60,revoked=False,tools=tools,allow_changes=writable,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    credential=seal(Environment.get_security().get_ticket_key()),request_hash=fingerprint)
                if deferred:
                    grant['pending_token']=seal(token)
                row=dict(request_id=code,transport='mcp',created=now,seen=now,status='completed',outcome='completed',
                    document=dict(prompt=instructions or title,context=context,allow_changes=writable,allow_web=False,
                        attachments=[],provider='external_mcp',model='',effort=''),
                    messages=[],events=[],operations={},answer='',error='',output='',host_id='')
                self.save('spt_agent_request',code,row)
                self.write_grant(root,grant)
                self.info=dict(mcp_access.public(grant),path='/mcp/'+code)
                if deferred:
                    self.info['collect_in']='MCP connections'
                else:
                    self.info['token']=token
                return self.info
            grants=[]
            for path in sorted(root.glob('*.json')):
                grant=json.loads(path.read_text(encoding='utf-8'))
                if grant['owner']==self.owner and grant['project']==Project.get_project_code():
                    grants.append(mcp_access.public(grant))
            self.info=dict(connections=grants,tools=mcp_access.tool_catalog(),enabled=enabled)
            return self.info

    @staticmethod
    def write_grant(root,grant):
        temporary=root/(grant['id']+'.tmp')
        temporary.write_text(json.dumps(grant,ensure_ascii=False),encoding='utf-8')
        temporary.replace(root/(grant['id']+'.json'))
