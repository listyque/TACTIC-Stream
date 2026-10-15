"""One native sidebar lifecycle: tree/element XML/group rules/conflict/rollback."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from pyasm.common import Config
from tactic_stream.server.api import Api
from tactic_stream.server.sidebar_editor import read_sidebar, sidebar_request, _sidebar_rule_allowed
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def state(result):
    return {key: result[key] for key in ('documents', 'source', 'selected', 'collapsed', 'updates', 'previewGroup')}


class SidebarEditor(unittest.TestCase):
    def test_native_tree_permissions_xml_and_revision(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory))
            store.initialize(hash_password('sidebar-test-password'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'sidebar-test-password')
            auth = dict(ticket=ticket, project='admin', language='python')
            api.dispatch('insert', (auth, 'sthpw/login_group', dict(code='sidebar_editors', login_group='sidebar_editors', access_rules='<rules><rule group="search_type" code="*" access="view"/></rules>')))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket)
                loaded = read_sidebar()
                draft = sidebar_request('edit', dict(state=state(loaded), operation='add', value='section'))
                draft = sidebar_request('edit', dict(state=state(draft), operation='field', field='title', value='Workspace'))
                draft = sidebar_request('edit', dict(state=state(draft), operation='add', value='link'))
                draft = sidebar_request('edit', dict(state=state(draft), operation='field', field='searchType', value='sthpw/login'))
                self.assertEqual(draft['entries'][draft['selected']]['depth'], 1)
                draft = sidebar_request('edit', dict(state=state(draft), operation='group', field='sidebar_editors', value=True))
                draft = sidebar_request('edit', dict(state=state(draft), operation='field', field='name', value='people'))
                selected_xml = draft['xml'].replace('title="New sidebar item"', 'title="People"')
                selected_xml = selected_xml.replace('</element>', '<custom option="keep" /></element>')
                draft = sidebar_request('edit', dict(state=state(draft), operation='xml', xml=selected_xml))
                draft = sidebar_request('edit', dict(state=state(draft), operation='field', field='icon', value='FAS_USERS'))
                saved = sidebar_request('save', dict(state=state(draft), revision=loaded['revision']))
                self.assertIn('<custom option="keep"', saved['documents']['definition'])
                from pyasm.search import Search
                group = Search.get_by_code('sthpw/login_group', 'sidebar_editors')
                self.assertTrue(_sidebar_rule_allowed(group.get_value('access_rules'), 'people', 'admin'))
                self.assertIn('group="search_type"', group.get_value('access_rules'))
                with self.assertRaises(WidgetConfigConflict):
                    sidebar_request('save', dict(state=state(saved), revision=loaded['revision']))
                changed = sidebar_request('edit', dict(state=state(saved), operation='field', field='title', value='Must rollback'))
                changed = sidebar_request('edit', dict(state=state(changed), operation='group', field='sidebar_editors', value=False))
                with patch.object(type(group), 'commit', side_effect=ValueError('late group failure')):
                    with self.assertRaisesRegex(ValueError, 'late group failure'):
                        sidebar_request('save', dict(state=state(changed), revision=saved['revision']))
                self.assertEqual(read_sidebar()['documents'], saved['documents'])
                self.assertTrue(_sidebar_rule_allowed(Search.get_by_code('sthpw/login_group', 'sidebar_editors').get_value('access_rules'), 'people', 'admin'))


if __name__ == '__main__':
    unittest.main()
