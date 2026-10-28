"""Nested item references through the built app and a private server."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class NestedItemLinksBrowser(unittest.TestCase):
    def test_nested_chain_return_and_draft_guards(self):
        from test_transport import Transport
        from tactic_stream.server.api import Api

        class Fixture(Transport):
            pass

        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        api = Api(Fixture.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one')
        records = [
            ('contract/entity', 'nested_parent', '<element name="title"><display class="title"/></element><element name="nested" search_type="contract/collection"><display class="view"><view>nested_child</view></display></element>'),
            ('contract/collection', 'nested_child', '<element name="inner"><display class="view"><view>nested_leaf</view></display></element>'),
            ('contract/collection', 'nested_leaf', '<element name="leaf"><display class="title"/></element>'),
            ('contract/entity', 'broken_parent', '<element name="broken"><display class="view"><view>absent_view</view></display></element>')]
        stored = []
        for search_type, view, elements in records:
            xml = f'<config><{view} layout="sobject-layout">{elements}</{view}></config>'
            record = api.dispatch('insert', (auth, 'config/widget_config', dict(search_type=search_type, view=view, config=xml)))
            stored.append((record['id'], xml))
        document = dict(name='work', title='Work', blocks=[dict(kind='items', search_type='contract/entity', view='nested_parent')])

        def call(action, **values):
            return api.dispatch('execute_cmd', (auth, 'tactic.ui.panel.dashboard_cmd.DashboardCmd',
                dict(action=action, project_code='one', **values)))['info']

        call('apply', document=document, expected_revision=call('read')['revision'], operation_id=str(uuid4()))
        root = Path(__file__).resolve().parents[1]
        output = root / '.screenshots/nested-layout-links'
        output.mkdir(parents=True, exist_ok=True)
        with (output / 'browser.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([shutil.which('node'), 'tests/nested_layout_links_browser.mjs', Fixture.url, str(output)],
                cwd=root / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache')),
                stdout=log, stderr=subprocess.STDOUT, timeout=120)
        self.assertEqual(result.returncode, 0, (output / 'browser.log').read_text(encoding='utf-8'))
        for identity, xml in stored:
            value = api.dispatch('query', (auth, 'config/widget_config'), dict(filters=[('id', identity)]))
            self.assertEqual(value[0]['config'], xml)
