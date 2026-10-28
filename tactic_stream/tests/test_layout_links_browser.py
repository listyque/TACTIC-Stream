"""Editor navigation through real browser input and private server definitions."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class LayoutLinksBrowser(unittest.TestCase):
    def test_references_return_and_tree_selection(self):
        from test_transport import Transport
        from tactic_stream.server.api import Api
        from tactic_stream.server.item_layout import layout_templates

        class Fixture(Transport):
            pass

        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        api = Api(Fixture.store)
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one')
        for view, xml in [
            ('hub_items', layout_templates()[0]['xml'].replace('continuous_example', 'hub_items')),
            ('production', '<config><production><element name="code"/><element name="name"/></production></config>'),
        ]:
            api.dispatch('insert', (auth, 'config/widget_config', dict(
                search_type='contract/entity', view=view, config=xml)))

        def call(action, **values):
            return api.dispatch('execute_cmd', (auth, 'tactic.ui.panel.dashboard_cmd.DashboardCmd',
                dict(action=action, project_code='one', **values)))['info']

        document = dict(name='work', title='Work', blocks=[dict(kind='column', children=[
            dict(kind='items', search_type='contract/entity', view='hub_items', height=120),
            dict(kind='table', search_type='contract/entity', view='production', height=120),
            dict(kind='link', text='Report', href=Fixture.url + '/projects/one/dashboard/report', height=40),
            dict(kind='text', text='Selected on canvas', height=60),
        ])])
        for value in [document, dict(name='report', title='Report', blocks=[dict(kind='text', text='Report body')])]:
            call('apply', document=value, expected_revision=call('read')['revision'], operation_id=str(uuid4()))
        baseline = call('read', name='work')['document']
        root = Path(__file__).resolve().parents[1]
        output = root / '.screenshots/layout-links'
        output.mkdir(parents=True, exist_ok=True)
        with (output / 'browser.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([shutil.which('node'), 'tests/layout_editor_links_browser.mjs', Fixture.url, str(output)],
                cwd=root / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache')),
                stdout=log, stderr=subprocess.STDOUT, timeout=120)
        self.assertEqual(result.returncode, 0, (output / 'browser.log').read_text(encoding='utf-8'))
        self.assertEqual(call('read', name='work')['document'], baseline)
