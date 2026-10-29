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
from tactic_stream.server.agent_security import allowed_catalog
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
        if action not in ('state','create','configure','revoke','reveal'):
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
            if action=='configure':
                grant=mcp_access.read_grant(self.kwargs.get('id'))
                if not grant or grant['owner']!=self.owner or grant['project']!=Project.get_project_code() or grant['revoked']:
                    raise ValueError('MCP connection is unavailable')
                ledger=self.load('spt_agent_request',grant['id'])
                catalog=allowed_catalog('mcp')
                tools=self.kwargs.get('tools')
                if (not isinstance(tools,list) or not tools or not all(isinstance(tool,str) for tool in tools) or len(set(tools))!=len(tools)
                        or not all(isinstance(tool,str) and tool in {item['name'] for item in catalog} for tool in tools)):
                    raise ValueError('Choose tools from this server catalogue')
                minutes=self.kwargs.get('minutes',60)
                if type(minutes) is not int or (minutes != 0 and not 5<=minutes<=480):
                    raise ValueError('MCP access lifetime must be zero or between 5 and 480 minutes')
                instructions=text(self.kwargs.get('instructions'),16384)
                operation=identity(self.kwargs.get('operation_id'))
                fingerprint=digest([tools,minutes,instructions,self.kwargs.get('expected_revision')])
                previous=grant.get('last_update',{})
                if previous.get('operation_id')==operation:
                    if previous['digest']!=fingerprint:
                        raise ValueError('Operation ID belongs to another MCP update')
                    return mcp_access.public(grant)
                if self.kwargs.get('expected_revision')!=mcp_access.public(grant)['revision']:
                    raise ValueError('MCP connection changed. Reload before updating access.')
                writable=any(not item['readonly'] for item in catalog if item['name'] in tools)
                previous_grant=dict(grant)
                credential,owned=mcp_access.credential(grant,minutes==0)
                grant.update(tools=tools,expires=None if minutes == 0 else int(time.time())+minutes*60,allow_changes=writable,
                    request_hash=fingerprint,credential=credential,credential_owned=owned,
                    last_update=dict(operation_id=operation,digest=fingerprint))
                ledger['document'].update(prompt=instructions,allow_changes=writable)
                self.save('spt_agent_request',grant['id'],ledger)
                self.write_grant(root,grant)
                if not owned:
                    mcp_access.retire_credential(previous_grant)
                return mcp_access.public(grant)
            if action in ('revoke','reveal'):
                grant=mcp_access.read_grant(self.kwargs.get('id'))
                if not grant or grant['owner']!=self.owner or grant['project']!=Project.get_project_code():
                    raise ValueError('MCP connection is unavailable')
                if action=='reveal':
                    self.load('spt_agent_request',grant['id'])
                    if grant['revoked'] or mcp_access.expired(grant) or not grant.get('pending_token'):
                        raise ValueError('This connection token is no longer available')
                    token=unseal(grant.pop('pending_token'))
                    self.write_grant(root,grant)
                    return dict(mcp_access.public(grant),token=token,path='/mcp/'+grant['id'])
                grant['revoked']=True
                grant.pop('pending_token',None)
                self.write_grant(root,grant)
                mcp_access.retire_credential(grant)
            if action=='create':
                if not enabled:
                    raise ValueError('Enable external MCP connections in Server configuration and restart first')
                catalog=allowed_catalog('mcp')
                tools=self.kwargs.get('tools')
                if (not isinstance(tools,list) or not tools or any(not isinstance(tool,str) for tool in tools)
                        or len(set(tools))!=len(tools) or not set(tools)<={tool['name'] for tool in catalog}):
                    raise ValueError('Choose tools from this server catalogue')
                minutes=self.kwargs.get('minutes',60)
                if type(minutes) is not int or (minutes != 0 and not 5<=minutes<=480):
                    raise ValueError('MCP access lifetime must be zero or between 5 and 480 minutes')
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
                    created=now,expires=None if minutes == 0 else now+minutes*60,revoked=False,tools=tools,allow_changes=writable,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    request_hash=fingerprint)
                grant['credential'],grant['credential_owned']=mcp_access.credential(grant,minutes==0)
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
            self.info=dict(connections=grants,tools=allowed_catalog('mcp'),enabled=enabled,unlimited_lifetime=True)
            return self.info

    @staticmethod
    def write_grant(root,grant):
        temporary=root/(grant['id']+'.tmp')
        temporary.write_text(json.dumps(grant,ensure_ascii=False),encoding='utf-8')
        temporary.replace(root/(grant['id']+'.json'))
