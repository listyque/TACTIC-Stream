"""User-owned external-agent requests; this command never runs a model or script."""
import json
import time
from uuid import UUID, uuid4

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin

ACTIVE = ('queued', 'running', 'cancelling')
HOST_TTL = 45
REQUEST_TTL = 90


def identity(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('Expected a canonical UUID')
    return value


def text(value, limit, *, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()) or '\x00' in value:
        raise ValueError('Invalid agent request text')
    return value


def selected_object(key):
    item = Search.get_by_search_key(key)
    if item is None:
        raise ValueError('Selected object is unavailable in this project')
    project = item.get_value('project_code', no_exception=True) or item.get_project_code()
    if project != Project.get_project_code():
        raise ValueError('Selected object is unavailable in this project')
    return item


def context_document(value):
    fields = {'client', 'project', 'page', 'title', 'search_type', 'view', 'search_keys'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Invalid agent context')
    if value['client'] not in ('TH', 'TS') or value['project'] != Project.get_project_code():
        raise ValueError('Agent context project mismatch')
    for name in ('page', 'title', 'search_type', 'view'):
        text(value[name], 512, empty=True)
    if value['search_type']:
        selected_type = SearchType.get(value['search_type'])
        if selected_type.get_database() not in ('sthpw', Project.get_project_code()):
            raise ValueError('Search Type belongs to another project')
    keys = value['search_keys']
    if not isinstance(keys, list) or len(keys) > 200 or len(set(keys)) != len(keys):
        raise ValueError('Select at most 200 distinct objects')
    for key in keys:
        text(key, 2048)
        selected_object(key)
    return value


class AgentRequestCmd(Command):
    """One authenticated user's inbox and explicitly connected external host."""

    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Agent request project mismatch')
        self.sql = Search('config/trigger').get_sql()
        if not all(self.sql.table_exists(name) for name in ('spt_agent_request', 'spt_agent_host')):
            raise ValueError('Upgrade the project schema before connecting an agent')
        action = self.kwargs.get('action')
        if action not in ('state', 'submit', 'read', 'selection', 'cancel', 'heartbeat', 'disconnect', 'claim', 'update', 'message', 'ack', 'undo', 'download'):
            raise ValueError('Unknown agent request action')
        self.owner = Environment.get_user_name()
        self.now = int(time.time())
        # Consistent lock order also makes claims and repeated submissions atomic.
        for table in ('spt_agent_host', 'spt_agent_request'):
            self.sql.get_database_impl().lock_collection_table(self.sql, table)
        if action == 'disconnect':
            host_id = identity(self.kwargs.get('host_id'))
            host = self.load('spt_agent_host', host_id)
            host['seen'] = 0
            self.save('spt_agent_host', host_id, host)
            for row in self.records('spt_agent_request'):
                if row['host_id'] == host_id and row['status'] in ACTIVE:
                    row.update(status='interrupted', error='External agent disconnected. Inspect changes before sending a new request.')
                    self.save('spt_agent_request', row['request_id'], row)
            self.info = dict(status='disconnected')
            return
        if action == 'heartbeat':
            host_id = identity(self.kwargs.get('host_id'))
            capabilities = self.kwargs.get('capabilities')
            if (not isinstance(capabilities, dict) or set(capabilities) - {'changes', 'trials', 'models', 'steering', 'attachments', 'web_search'}
                    or any(type(capabilities.get(key)) is not bool for key in ('changes', 'trials'))
                    or type(capabilities.get('web_search', False)) is not bool):
                raise ValueError('Invalid host capabilities')
            models = capabilities.get('models', [])
            if (not isinstance(models, list) or len(models) > 100 or any(
                    not isinstance(model, dict) or not isinstance(model.get('id'), str)
                    or not isinstance(model.get('label'), str)
                    or not isinstance(model.get('efforts', []), list)
                    or len(model.get('efforts', [])) > 20
                    or any(not isinstance(value, str) or not value or len(value) > 32 for value in model.get('efforts', []))
                    or type(model.get('is_default', False)) is not bool for model in models)):
                raise ValueError('Invalid model catalogue')
            host = dict(host_id=host_id, label=text(self.kwargs.get('label'), 120),
                        capabilities=capabilities, seen=self.now)
            self.save('spt_agent_host', host_id, host)
            self.info = host
            return
        if action == 'state':
            hosts = [row for row in self.records('spt_agent_host') if self.now - row['seen'] <= HOST_TTL]
            requests = sorted(self.records('spt_agent_request'), key=lambda row: (row['created'], row['request_id']), reverse=True)
            for row in requests:
                self.expire(row)
            self.info = dict(hosts=hosts, requests=[dict(request_id=row['request_id'],
                prompt=(row['document']['prompt'] or 'Attachments')[:120], status=row['status']) for row in requests[:30]])
            return
        if action == 'submit':
            request_id = identity(self.kwargs.get('request_id'))
            document = self.kwargs.get('document')
            if (not isinstance(document, dict) or set(document) - {'prompt', 'context', 'allow_changes', 'attachments', 'model', 'effort', 'allow_web'}
                    or not {'prompt', 'context', 'allow_changes'} <= set(document)):
                raise ValueError('Invalid agent request document')
            text(document['prompt'], 12000, empty=True)
            if type(document.get('allow_web', False)) is not bool:
                raise ValueError('Invalid web search permission')
            if type(document['allow_changes']) is not bool:
                raise ValueError('Invalid change permission')
            old = self.load('spt_agent_request', request_id, missing=True)
            if old:
                if old['document'] != document:
                    raise ValueError('Request ID was used with a different document')
                self.info = old
                return
            context_document(document['context'])
            host = self.load('spt_agent_host', identity(self.kwargs.get('host_id')))
            if self.now - host['seen'] > HOST_TTL:
                raise ValueError('External agent is offline')
            if document['allow_changes'] and not host['capabilities']['changes']:
                raise ValueError('This host only allows reading and previews')
            if document.get('allow_web') and not host['capabilities'].get('web_search'):
                raise ValueError('This agent does not support web search')
            self.check_model(host, document.get('model', ''), document.get('effort', ''))
            attachments = self.check_attachments(document.get('attachments', []))
            if not document['prompt'].strip() and not attachments:
                raise ValueError('Write a message or attach a file')
            if sum(row['status'] in ACTIVE for row in self.records('spt_agent_request')) >= 5:
                raise ValueError('Wait for an existing agent request to finish')
            row = dict(request_id=request_id, document=document, host_id=host['host_id'],
                       status='queued', created=self.now, seen=self.now, events=[], answer='', error='',
                       messages=[dict(id=request_id, role='user', text=document['prompt'], attachments=attachments, delivered=True)],
                       model=document.get('model', ''), effort=document.get('effort', ''), turn=1)
        elif action == 'claim':
            host_id = identity(self.kwargs.get('host_id'))
            host = self.load('spt_agent_host', host_id)
            if self.now - host['seen'] > HOST_TTL:
                raise ValueError('Refresh the external host connection')
            rows = self.records('spt_agent_request')
            for row in rows:
                self.expire(row)
            if any(row['host_id'] == host_id and row['status'] in ('running', 'cancelling') for row in rows):
                self.info = dict(request=None)
                return
            pending = sorted((row for row in rows if row['host_id'] == host_id and row['status'] == 'queued'),
                             key=lambda row: (row['created'], row['request_id']))
            if not pending:
                self.info = dict(request=None)
                return
            row = pending[0]
            row.update(status='running', seen=self.now)
            self.save('spt_agent_request', row['request_id'], row)
            self.info = dict(request=row)
            return
        else:
            row = self.load('spt_agent_request', identity(self.kwargs.get('request_id')))
            self.expire(row)
            if action == 'read':
                self.info = row
                return
            if action == 'download':
                if not row['document'].get('allow_web') or row['status'] != 'running':
                    raise ValueError('Web downloads require an active conversation with internet access')
                code = identity(self.kwargs.get('operation_id'))
                source_url = text(self.kwargs.get('source_url'), 4096)
                if not source_url.startswith('https://'):
                    raise ValueError('Use a public HTTPS file URL')
                files = self.check_attachments([code])
                old = next((message for message in row.get('messages', []) if message['id'] == code), None)
                if old:
                    if old.get('source_url') != source_url:
                        raise ValueError('Download operation ID already has another URL')
                    self.info = old['attachments'][0]
                    return
                if len(row.get('messages', [])) >= 100 or sum(bool(message.get('source_url')) for message in row.get('messages', [])) >= 20:
                    raise ValueError('Start a new conversation for more downloads')
                files[0]['source_url'] = source_url
                row.setdefault('messages', []).append(dict(id=code, role='assistant',
                    text='Downloaded reference\n\n' + source_url, source_url=source_url, attachments=files, delivered=True))
                self.save('spt_agent_request', row['request_id'], row)
                self.info = files[0]
                return
            if action == 'selection':
                from tactic_stream.server.api import Api
                items = []
                fields = ['code', 'name', 'title', 'description', 'process', 'search_code', 'pipeline_code', 'project_code', 'timestamp']
                for key in row['document']['context']['search_keys']:
                    items.append(selected_object(key))
                self.info = dict(objects=Api._get_sobjects_dict(items, columns=fields))
                return
            if action == 'undo':
                code = identity(self.kwargs.get('operation_id'))
                receipt = row.get('operations', {}).get(code)
                if receipt and receipt.get('undone'):
                    self.info = row
                    return
                if row['status'] in ACTIVE or row.get('undo_operation') != code or not receipt or not receipt.get('undo'):
                    raise ValueError('Only the last reversible field change in a finished request can be undone')
                undo = receipt['undo']
                item = selected_object(undo['key'])
                if any(item.get_data().get(field) != value for field, value in undo['after'].items()):
                    raise ValueError('The fields changed after the agent operation. Undo refused.')
                for field, value in undo['before'].items():
                    item.set_value(field, value, allow_none=True)
                item.commit()
                receipt['undone'] = True
                row['undo_operation'] = ''
                row.setdefault('events', []).append('Last agent field change undone')
            elif action == 'message':
                if row['status'] == 'cancelling':
                    raise ValueError('Wait until the current turn stops before continuing')
                message_id = identity(self.kwargs.get('message_id'))
                message = dict(id=message_id, role='user', text=text(self.kwargs.get('text'), 12000, empty=True),
                               attachments=self.check_attachments(self.kwargs.get('attachments', [])), delivered=False)
                if not message['text'].strip() and not message['attachments']:
                    raise ValueError('Write a message or attach a file')
                if 'messages' not in row:
                    row['messages'] = [dict(id=row['request_id'], role='user', text=row['document']['prompt'], attachments=[], delivered=True)]
                    if row.get('answer'):
                        row['messages'].append(dict(id=str(uuid4()), role='assistant', text=row['answer'], attachments=[]))
                messages = row['messages']
                if row['status'] in ('cancelled', 'interrupted'):
                    for previous in messages:
                        if not previous.get('delivered', True):
                            previous.update(delivered=True, cancelled=True)
                old = next((item for item in messages if item['id'] == message_id), None)
                if old:
                    if any(old[key] != message[key] for key in ('text', 'attachments')):
                        raise ValueError('Message ID was used with different contents')
                    self.info = row
                    return
                if len(messages) >= 100:
                    raise ValueError('Start a new conversation after 100 messages')
                host_id = self.kwargs.get('host_id', row['host_id'])
                if row['status'] == 'running' and host_id != row['host_id']:
                    raise ValueError('Cannot change the host while a turn is running')
                host = self.load('spt_agent_host', identity(host_id))
                if row['document']['allow_changes'] and not host['capabilities']['changes']:
                    raise ValueError('This host only allows reading and previews')
                if row['document'].get('allow_web') and not host['capabilities'].get('web_search'):
                    raise ValueError('This agent does not support web search')
                if self.now - host['seen'] > HOST_TTL:
                    raise ValueError('External agent is offline')
                if row['status'] == 'running' and not host['capabilities'].get('steering'):
                    raise ValueError('This agent does not support corrections while working')
                model = self.kwargs.get('model', row.get('model', ''))
                effort = self.kwargs.get('effort', row.get('effort', ''))
                self.check_model(host, model, effort)
                if row['status'] != 'running':
                    row.update(status='queued', seen=self.now, created=self.now, host_id=host_id, model=model, effort=effort, turn=row.get('turn', 1) + 1, output='', error='')
                elif model != row.get('model', '') or effort != row.get('effort', ''):
                    raise ValueError('Change the model or reasoning effort after the current turn finishes')
                messages.append(message)
            elif action == 'ack':
                if identity(self.kwargs.get('host_id')) != row['host_id']:
                    raise ValueError('Request belongs to another external host')
                codes = self.kwargs.get('message_ids')
                if not isinstance(codes, list):
                    raise ValueError('Invalid message acknowledgements')
                for message in row.get('messages', []):
                    if message['id'] in codes and message['role'] == 'user':
                        message['delivered'] = True
            elif action == 'cancel':
                if row['status'] == 'queued':
                    row['status'] = 'cancelled'
                    row['outcome'] = 'cancelled'
                elif row['status'] == 'running':
                    row['status'] = 'cancelling'
            elif action == 'update':
                if identity(self.kwargs.get('host_id')) != row['host_id']:
                    raise ValueError('Request belongs to another external host')
                if row['status'] not in ('running', 'cancelling'):
                    raise ValueError('Request is already closed; execution must not be repeated')
                status = self.kwargs.get('status', 'running')
                if status not in ('running', 'completed', 'failed', 'cancelled'):
                    raise ValueError('Invalid request status')
                if row['status'] == 'cancelling' and status == 'completed':
                    status = 'cancelled'
                row['seen'] = self.now
                if status != 'running':
                    answer = text(self.kwargs.get('answer', ''), 64000, empty=True)
                    if answer:
                        row.setdefault('messages', []).append(dict(id=str(uuid4()), role='assistant', text=answer, attachments=[]))
                    if status == 'completed' and any(not message.get('delivered', True) for message in row.get('messages', [])):
                        status = 'queued'
                    row.update(status=status, answer=answer,
                               error=text(self.kwargs.get('error', ''), 4000, empty=True))
                    outcome = self.kwargs.get('outcome', 'completed') if status in ('completed', 'queued') else status
                    if outcome not in ('completed', 'needs_input', 'blocked', 'failed', 'cancelled'):
                        raise ValueError('Invalid task outcome')
                    row['outcome'] = outcome
                elif 'output' in self.kwargs:
                    row['output'] = text(self.kwargs['output'], 64000, empty=True)
                event = self.kwargs.get('event', '')
                if event:
                    text(event, 3000)
                    row['events'] = (row['events'] + [event])[-100:]
        self.save('spt_agent_request', row['request_id'], row)
        self.info = row

    def check_model(self, host, model, effort=''):
        text(model, 128, empty=True)
        text(effort, 32, empty=True)
        selected = next((item for item in host['capabilities'].get('models', [])
                         if item['id'] == model or (not model and item.get('is_default'))), None)
        if model and selected is None:
            raise ValueError('Choose a model offered by the connected agent')
        if effort and (selected is None or effort not in selected.get('efforts', [])):
            raise ValueError('Choose a reasoning effort offered for this model')

    def check_attachments(self, codes):
        from .agent_attachment_cmd import attachment
        if (not isinstance(codes, list) or len(codes) > 20 or any(not isinstance(code, str) for code in codes)
                or len(set(codes)) != len(codes)):
            raise ValueError('Attach at most 20 distinct files')
        return [attachment(code)[0] for code in codes]

    def records(self, table):
        return [json.loads(row[0]) for row in self.sql.do_query(
            'SELECT record FROM ' + table + ' WHERE owner=' + self.sql.quote(self.owner))]

    def load(self, table, code, missing=False):
        rows = self.sql.do_query('SELECT owner,record FROM ' + table + ' WHERE code=' + self.sql.quote(code))
        if not rows:
            if missing:
                return None
            raise ValueError('Agent request or connection is unavailable')
        if rows[0][0] != self.owner:
            raise ValueError('Agent request or connection is unavailable')
        return json.loads(rows[0][1])

    def save(self, table, code, record):
        exists = self.load(table, code, missing=True)
        marker = self.sql.get_database_impl().get_parameter()
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False)
        if exists:
            statement = f'UPDATE {table} SET record={marker} WHERE code={marker}'
            values = [encoded, code]
        else:
            statement = f'INSERT INTO {table} (code,owner,record) VALUES ({marker},{marker},{marker})'
            values = [code, self.owner, encoded]
        self.sql._do_update(statement, parameters=values)

    def expire(self, row):
        if row['status'] == 'queued' and self.now - row['created'] > REQUEST_TTL:
            host = self.load('spt_agent_host', row['host_id'])
            if self.now - host['seen'] > REQUEST_TTL:
                row.update(status='interrupted', error='External agent disconnected. Inspect changes before sending a new request.')
                self.save('spt_agent_request', row['request_id'], row)
        if row['status'] in ('running', 'cancelling') and self.now - row['seen'] > REQUEST_TTL:
            row.update(status='interrupted', error='External agent disconnected. Inspect changes before sending a new request.')
            self.save('spt_agent_request', row['request_id'], row)
