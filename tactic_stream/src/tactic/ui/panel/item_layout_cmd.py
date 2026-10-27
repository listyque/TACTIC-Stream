"""Declarative item views through the native configuration editor and journal."""
import json
from uuid import UUID

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.widget_configuration import (
    read_widget_configuration, preview_widget_configuration, save_widget_configuration)
from .page_cmd import digest


class ItemLayoutCmd(Command):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Item layout project mismatch')
        action = self.kwargs.get('action')
        if action not in ('read', 'preview', 'apply', 'operation'):
            raise ValueError('Unknown item layout operation')
        sql = Search('config/widget_config').get_sql()
        if action == 'apply':
            sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        operation = self.kwargs.get('operation_id', '')
        payload = [self.kwargs.get(name) for name in ('search_type', 'view', 'source_id', 'xml', 'expected_revision')]
        fingerprint = digest(['item_layout', payload])
        if action in ('apply', 'operation'):
            if not isinstance(operation, str) or str(UUID(operation)) != operation:
                raise ValueError('A canonical UUID operation_id is required')
            key = digest([Environment.get_user_name(), Project.get_project_code(), operation])
            receipt = sql.do_query('SELECT request_hash,result FROM spt_page_operation WHERE code=' + sql.quote(key))
            if receipt:
                result = json.loads(receipt[0][1])
                if result.get('kind') != 'item_layout' or action == 'apply' and receipt[0][0] != fingerprint:
                    raise ValueError('Operation ID belongs to another request')
                return result
            if action == 'operation':
                return dict(status='not_found', operation_id=operation)
        search_type, view, source, xml, revision = payload
        if action == 'read':
            from tactic_stream.server.item_layout import WIDGETS, ACTIONS, VARIANTS
            state = read_widget_configuration(search_type, view)
            result = {name: state[name] for name in ('search_type', 'view', 'revision', 'sources', 'resolved', 'layout_views')}
            result.update(widgets=WIDGETS, actions=ACTIONS, variants=VARIANTS)
            return result
        checked = preview_widget_configuration(search_type, view, source, xml, revision)
        if not checked['interface'].get('table', {}).get('item_layout'):
            raise ValueError('Choose a declarative SObject item layout')
        if action == 'preview':
            return checked
        saved = save_widget_configuration(search_type, view, source, xml, revision)
        result = dict(kind='item_layout', status='applied', operation_id=operation,
                      project=Project.get_project_code(), search_type=search_type, view=view,
                      revision=saved['revision'], source_id=saved['sources'][0]['id'])
        marker = sql.get_database_impl().get_parameter()
        sql._do_update('INSERT INTO spt_page_operation (code,request_hash,result) VALUES (' + ', '.join([marker] * 3) + ')',
                       parameters=[key, fingerprint, json.dumps(result)])
        self.add_description('Save item layout [%s / %s]' % (search_type, view))
        return result
