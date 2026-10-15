"""Saved XML definitions: native writes, revision conflicts, rollback and permissions."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.command import Command
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.columns_editor import columns_editor_request as request
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def exercise(store):
    check = unittest.TestCase(); api = Api(store); ticket = api.get_ticket('admin', 'columns-test-admin')
    def write(operation):
        command = Command(); command.execute = operation; command.get_transaction().set_sync(False)
        return Command.execute_cmd(command)
    with request_context(RequestContext(store, login='admin', project='admin')):
        api.auth.bind_security('admin', ticket)
        item = SearchType.create('config/widget_config')
        item.set_value('search_type', 'sthpw/project'); item.set_value('view', 'table')
        original = '<config><!--keep--><table><element name="code" title="Code"><display class="custom.Wdg"><parameter>keep</parameter></display></element></table></config>'
        item.set_value('config', original); write(item.commit)
        catalog = request('read', {}); json.dumps(catalog)
        row = next(row for row in catalog['records'] if row['id'] == item.get_id())
        check.assertEqual(row['config'], original)
        check.assertTrue(any(choice['value'] == 'sthpw/project' for choice in catalog['searchTypes']))
        changed = original.replace('title="Code"', 'title="Project code"')
        saved = request('save', dict(source_id=item.get_id(), xml=changed, revision=catalog['revision']))
        check.assertEqual(saved['selected'], row['identity'])
        check.assertEqual(next(row for row in saved['records'] if row['id'] == item.get_id())['config'], changed)
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(source_id=item.get_id(), xml=original, revision=catalog['revision']))
        with check.assertRaisesRegex(ValueError, 'Document types'):
            request('save', dict(source_id=item.get_id(), xml='<!DOCTYPE config><config/>', revision=saved['revision']))
        with patch.object(WidgetDbConfig, 'commit', side_effect=ValueError('write failure')):
            with check.assertRaisesRegex(ValueError, 'write failure'):
                request('save', dict(source_id=item.get_id(), xml=original, revision=saved['revision']))
        check.assertEqual(next(row for row in request('read', {})['records'] if row['id'] == item.get_id())['config'], changed)
        # Native/XML-RPC writes invalidate the editor, including A -> B -> A.
        native = Search.get_by_id('config/widget_config', item.get_id())
        native.set_value('config', original); write(native.commit)
        native.set_value('config', changed); write(native.commit)
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(source_id=item.get_id(), xml=original, revision=saved['revision']))
        # Catalog reads the source, without attempting to render a Mako body.
        search = Search('config/widget_config')
        placeholder = search._placeholder()
        table = SearchType.get('config/widget_config').get_table()
        write(lambda: search.get_sql()._do_update(
            f'UPDATE "{table}" SET "config" = {placeholder} WHERE "id" = {placeholder}',
            parameters=('<config><table>${unsupported_template}</table></config>', item.get_id())))
        raw = request('read', {})
        check.assertIn('${unsupported_template}', next(row for row in raw['records'] if row['id'] == item.get_id())['config'])
        request('save', dict(source_id=item.get_id(), xml=original, revision=raw['revision']))
        from pyasm.security import Login
        Login.create('reader', 'reader-password')
        from scripts.table_cells_contract import exercise as cells
        cells(api, ticket)
    reader = api.get_ticket('reader', 'reader-password')
    with request_context(RequestContext(store, login='reader', project='admin')):
        api.auth.bind_security('reader', reader)
        for action in ('read', 'save'):
            with check.assertRaises(SecurityException):
                request(action, {})
        from tactic_stream.server.table_cells import read_table_cells
        with check.assertRaises(SecurityException):
            read_table_cells('sthpw/login_group', 'cells_native', [])
        for name in ('DiscussionReadCmd', 'DiscussionAddNoteCmd', 'DiscussionChangeNoteCmd'):
            with check.assertRaises(SecurityException):
                api.dispatch('execute_cmd', (dict(ticket=reader, project='admin'),
                    'tactic.ui.widget.discussion_wdg.'+name, dict(search_key='sthpw/login_group?code=CELL_A', note='Denied')))
        with check.assertRaises(SecurityException):
            api.dispatch('execute_cmd', (dict(ticket=reader, project='admin'),
                'tactic.ui.table.task_inspector.TaskInspectorCmd', dict(search_key='sthpw/project?code=admin', process='publish')))
        with check.assertRaises(SecurityException):
            api.dispatch('execute_cmd', (dict(ticket=reader, project='admin'),
                'tactic.ui.table.work_hours.WorkHoursCmd', dict(search_key='sthpw/project?code=admin', process='publish')))
        for command in ('task_workspace.TaskWorkspaceCmd', 'task_workspace_edits.TaskWorkspaceEditCmd'):
            with check.assertRaises(SecurityException):
                api.dispatch('execute_cmd', (dict(ticket=reader, project='admin'),
                    'tactic.ui.table.' + command, dict(action='prepare', plans=[])))


class ColumnsEditor(unittest.TestCase):
    def test_saved_definition_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config(); store = Store(root / 'sqlite')
                store.initialize(hash_password('columns-test-admin')); exercise(store)
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import uuid
            import psycopg
            from psycopg import sql
            from xml.etree.ElementTree import Element, SubElement, tostring
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            database = 'stream_columns_' + uuid.uuid4().hex[:12]
            config = Element('config', version='2'); section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'], **{key: value for key, value in credentials.items() if key != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'; path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config(); store = Store(root / 'postgres')
                        store.initialize(hash_password('columns-test-admin')); exercise(store)
                finally:
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier('progress_' + root.name)))
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                    Config.reload_config()


if __name__ == '__main__':
    unittest.main()
