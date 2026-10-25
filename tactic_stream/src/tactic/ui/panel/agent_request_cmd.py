"""User-owned external-agent requests; this command never runs a model or script."""
import json
import time
from uuid import UUID

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
        if action not in ('state', 'submit', 'read', 'selection', 'cancel', 'heartbeat', 'disconnect', 'claim', 'update'):
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
            if (not isinstance(capabilities, dict) or set(capabilities) != {'changes', 'trials'}
                    or any(type(value) is not bool for value in capabilities.values())):
                raise ValueError('Invalid host capabilities')
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
                prompt=row['document']['prompt'][:120], status=row['status']) for row in requests[:30]])
            return
        if action == 'submit':
            request_id = identity(self.kwargs.get('request_id'))
            document = self.kwargs.get('document')
            if not isinstance(document, dict) or set(document) != {'prompt', 'context', 'allow_changes'}:
                raise ValueError('Invalid agent request document')
            text(document['prompt'], 12000)
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
            if sum(row['status'] in ACTIVE for row in self.records('spt_agent_request')) >= 5:
                raise ValueError('Wait for an existing agent request to finish')
            row = dict(request_id=request_id, document=document, host_id=host['host_id'],
                       status='queued', created=self.now, seen=self.now, events=[], answer='', error='')
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
            if action == 'selection':
                from tactic_stream.server.api import Api
                items = []
                fields = ['code', 'name', 'title', 'description', 'process', 'search_code', 'pipeline_code', 'project_code', 'timestamp']
                for key in row['document']['context']['search_keys']:
                    items.append(selected_object(key))
                self.info = dict(objects=Api._get_sobjects_dict(items, columns=fields))
                return
            if action == 'cancel':
                if row['status'] == 'queued':
                    row['status'] = 'cancelled'
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
                    row.update(status=status, answer=text(self.kwargs.get('answer', ''), 64000, empty=True),
                               error=text(self.kwargs.get('error', ''), 4000, empty=True))
                event = self.kwargs.get('event', '')
                if event:
                    text(event, 3000)
                    row['events'] = (row['events'] + [event])[-100:]
        self.save('spt_agent_request', row['request_id'], row)
        self.info = row

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
