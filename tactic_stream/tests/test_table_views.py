"""Saved table views use normal native transactions and revision/permission checks."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from pyasm.common.errors import SecurityException
from tactic_stream.server.api import Api
from tactic_stream.server.widget_configuration import WidgetConfigConflict, read_widget_configuration


class TableViewsTests(unittest.TestCase):
    def test_catalog_copy_rename_delete_and_conflicts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory) / 'sqlite')
            store.initialize(hash_password('views-password'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'views-password')
            with request_context(RequestContext(store, login='admin', project='admin')):
                api.auth.bind_security('admin', ticket)
                def write(operation):
                    command = Command()
                    command.execute = operation
                    command.get_transaction().set_sync(False)
                    return Command.execute_cmd(command)
                def add(view, xml):
                    item = SearchType.create('config/widget_config')
                    item.set_value('search_type', 'sthpw/project')
                    item.set_value('view', view)
                    item.set_value('config', xml)
                    write(item.commit)
                    return item
                default = add('table', '<config><table marker="keep"><element name="code" width="90"/><element name="description"/><option name="keep">yes</option></table></config>')
                for view in ('definition', 'edit', 'edit_definition', 'custom_filter', 'simple_filter'):
                    add(view, '<config><%s><element name="code"/></%s></config>' % (view, view))
                add('freeform', '<config><freeform layout="FreeformLayoutWdg"><element name="code"/></freeform></config>')
                def call(action='read', **values):
                    result = api.dispatch('execute_cmd', (dict(ticket=ticket, project='admin'), 'tactic.ui.table.views.TableViewsCmd', dict(search_type='sthpw/project', action=action, **values)))
                    info = json.loads(result['info']) if isinstance(result['info'], str) else result['info']
                    if action != 'read':
                        return dict(call(current=info['current']), selected=info['selected'])
                    return info
                state = call()
                self.assertEqual([row['view'] for row in state['views']], ['table'])
                visible = read_widget_configuration('sthpw/project')['table_views']
                self.assertEqual([row['view'] for row in visible], ['table'])
                copied = call('copy', view='table', title='Artists review', revision=state['revision'])
                view = copied['selected']
                self.assertEqual(view, 'th_table_artists_review')
                search = Search('config/widget_config'); search.add_filter('view', view)
                item = search.get_sobject()
                self.assertIn('width="90"', item.get_value('config'))
                self.assertIn('marker="keep"', item.get_value('config'))
                self.assertIn('<option name="keep">yes</option>', item.get_value('config'))
                with self.assertRaises(WidgetConfigConflict):
                    call('rename', view=view, title='Outdated rename', revision=state['revision'])
                renamed = call('rename', view=view, title='Lighting review', revision=copied['revision'])
                self.assertEqual(renamed['selected'], view)
                self.assertEqual(next(row for row in renamed['views'] if row['view']==view)['title'], 'Lighting review')
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    call('create', title='Lighting review', revision=renamed['revision'])
                reused = call('create', title='Artists review', revision=renamed['revision'])
                self.assertEqual(reused['selected'], 'th_table_artists_review_2')
                created = call('create', title='Fresh table', revision=reused['revision'])
                self.assertTrue(any(row['view']=='th_table_fresh_table' for row in created['views']))
                with self.assertRaisesRegex(ValueError, 'protected'):
                    call('delete', view='table', revision=created['revision'])
                removed = call('delete', view=view, current=view, revision=created['revision'])
                self.assertEqual(removed['current'], 'table')
                self.assertFalse(any(row['view']==view for row in removed['views']))
                self.assertIsNotNone(Search.get_by_id('config/widget_config', default.get_id()))
                history = Search('sthpw/transaction_log')
                history.add_order_by('id desc'); history.add_limit(1)
                transaction_id = history.get_sobject().get_id()
                api.dispatch('undo', (dict(ticket=ticket, project='admin'),), dict(transaction_id=transaction_id))
                restored = call()
                self.assertEqual(next(row['title'] for row in restored['views'] if row['view']==view), 'Lighting review')
                filtered = call('create', title='Light filter', revision=restored['revision'])
                self.assertTrue(any(row['view']=='th_table_light_filter' for row in filtered['views']))
                with self.assertRaisesRegex(ValueError, 'target project'):
                    api.dispatch('execute_cmd', (dict(ticket=ticket, project='admin'), 'tactic.ui.table.views.TableViewsCmd', dict(search_type='sthpw/project?project=elsewhere')))
                from pyasm.security import Login
                Login.create('reader', 'reader-password')
            reader = api.get_ticket('reader', 'reader-password')
            with request_context(RequestContext(store, login='reader', project='admin')):
                api.auth.bind_security('reader', reader)
                with self.assertRaises(SecurityException):
                    api.dispatch('execute_cmd', (dict(ticket=reader, project='admin'), 'tactic.ui.table.views.TableViewsCmd', dict(search_type='sthpw/project')))
