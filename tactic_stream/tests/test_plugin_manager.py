"""Real manager commands in an owned SQLite project, never production data."""
import tempfile
import unittest
import zipfile
import io
import hashlib
from pathlib import Path
from unittest.mock import patch

from pyasm.common import Environment
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.checkin_benchmark import prepare


class PluginManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one', language='python')

    def call(self, action, **values):
        return self.api.dispatch('execute_cmd', (self.auth, 'tactic.ui.app.PluginManagerCmd',
                                 dict(action=action, project_code='one', **values)))['info']

    def create(self):
        return self.call('create', document=dict(code='manager_example', title='Example', description='Test', type=''))

    def change(self, current, action, **values):
        return self.call(action, identity=current['identity'], expected_revision=current['revision'], **values)

    def test_package_file_manifest_publish_and_removal(self):
        doc = self.create()
        self.assertTrue(doc['metadata']['active'])
        doc = self.change(doc, 'new_folder', path='docs')
        doc = self.change(doc, 'new_file', path='docs/README.md')
        doc = self.call('open_file', identity=doc['identity'], file='docs/README.md', folder='docs')
        doc['document']['file']['content'] = '# Plugin documentation\n'
        doc = self.change(doc, 'save', document=doc['document'], folder='docs')
        self.assertEqual('# Plugin documentation\n', doc['document']['file']['content'])
        doc = self.change(doc, 'rename', path='docs/README.md', destination='README.md')
        doc['document']['title'] = 'Renamed'
        doc = self.change(doc, 'save', document=doc['document'], changed_fields=['title'])
        self.assertEqual(doc['document']['title'], 'Renamed')
        archive = self.change(doc, 'export')
        self.assertTrue(archive['download']['filename'].endswith('.zip'))
        published = self.change(archive, 'publish', version='1.0')
        self.assertEqual('1.0', published['document']['version'])
        self.assertFalse(published['metadata']['active'])
        with self.assertRaisesRegex(Exception, 'every project'):
            self.change(archive, 'delete', confirmation=True)
        doc = self.change(archive, 'deactivate', confirmation=True)
        self.assertFalse(doc['metadata']['active'])
        self.assertEqual('', self.change(doc, 'delete', confirmation=True)['identity'])
        published = self.call('load', identity=published['identity'])
        published = self.change(published, 'activate')
        self.assertTrue(published['metadata']['active'])
        published = self.change(published, 'reload', confirmation=True)
        self.assertTrue(published['metadata']['active'])

    def test_conflicts_traversal_and_transaction_rollback(self):
        doc = self.create()
        with self.assertRaisesRegex(Exception, 'Confirm'):
            self.change(doc, 'deactivate')
        with self.assertRaisesRegex(Exception, 'escapes'):
            self.change(doc, 'new_file', path='../escape.txt')
        changed = self.change(doc, 'new_file', path='a.txt')
        with self.assertRaisesRegex(Exception, 'changed on the server'):
            self.change(doc, 'new_file', path='b.txt')
        changed = self.call('load', identity=changed['identity'])
        with self.assertRaisesRegex(Exception, 'Publish'):
            self.change(changed, 'save', document=dict(changed['document'], manifest='<manifest code="other"/>'))
        current = self.call('load', identity=doc['identity'])
        self.assertEqual(current['document']['code'], 'manager_example')

    def test_upload_stages_without_activation_and_rejects_zip_slip(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            upload = Path(Environment.get_upload_dir())
            upload.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(upload / 'plugin.zip', 'w') as archive:
                archive.writestr('sample/manifest.xml', '<manifest><data><code>staged</code><version>1</version></data></manifest>')
            with zipfile.ZipFile(upload / 'bad.zip', 'w') as archive:
                archive.writestr('../escape', 'unsafe')
                archive.writestr('manifest.xml', '<manifest code="bad"/>')
        doc = self.call('install', upload_file_name='plugin.zip')
        self.assertFalse(doc['metadata']['active'])
        doc = self.change(doc, 'new_file', path='replace.txt')
        with self.assertRaisesRegex(Exception, 'Confirm replacement'):
            self.change(doc, 'upload', path='replace.txt', upload_file_name='plugin.zip')
        doc = self.change(doc, 'upload', path='replace.txt', upload_file_name='plugin.zip', confirmation=True)
        self.assertIsNone(doc['document']['file']['content'])
        with self.assertRaisesRegex(Exception, 'already exists'):
            self.call('install', upload_file_name='plugin.zip')
        with self.assertRaisesRegex(Exception, 'Unsafe ZIP'):
            self.call('install', upload_file_name='bad.zip')

    def test_builtin_is_readonly_and_all_operations_require_admin(self):
        builtin = self.store.data_dir / 'builtin_test'
        package = builtin / 'built'
        package.mkdir(parents=True)
        (package / 'manifest.xml').write_text('<manifest><data><code>built</code></data></manifest>', encoding='utf-8')
        with patch.object(Environment, 'get_builtin_plugin_dir', return_value=str(builtin)):
            doc = self.call('load', identity='builtin:built')
            self.assertFalse(doc['canWrite'])
            self.assertTrue(doc['metadata']['builtin'])
            with self.assertRaisesRegex(Exception, 'read-only'):
                self.change(doc, 'new_file', path='must-not-exist.txt')
            self.assertFalse((package / 'must-not-exist.txt').exists())
            doc = self.change(doc, 'activate')
            self.assertTrue(doc['metadata']['active'])
        with patch('pyasm.security.Security.is_admin', return_value=False):
            with self.assertRaisesRegex(Exception, 'administrator|admin'):
                self.call('list')

    def test_url_download_checksum_and_modern_template(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('manifest.xml', '<manifest><data><code>url_sample</code></data></manifest>')
        raw = archive.getvalue()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            with self.assertRaisesRegex(Exception, 'checksum'):
                self.call('download_url', url='https://example.invalid/plugin.zip', checksum='0' * 64)
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            doc = self.call('download_url', url='https://example.invalid/plugin.zip', checksum=hashlib.sha256(raw).hexdigest())
        self.assertEqual(doc['document']['code'], 'url_sample')
        doc = self.call('create', document=dict(code='sample_widget', title='Widget', type='widget'))
        self.assertIn('config/widget_config', doc['document']['manifest'])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            from pyasm.widget import WidgetConfig
            from pyasm.search import Search
            search = Search('config/widget_config'); search.add_filter('view', 'sample_widget')
            record = search.get_sobject()
            config = WidgetConfig.get(view='sample_widget', xml=record.get_value('config'), use_cache=False)
            self.assertTrue(config.has_view())
            self.assertEqual(config.get_view_attributes()['layout'], 'sobject-layout')
        template = self.call('create', document=dict(type='project'))
        self.assertEqual(template['identity'], '')
        self.assertTrue(template['download']['filename'].endswith('.zip'))

    def test_deleting_parent_cannot_remove_an_active_nested_package(self):
        parent = self.call('create', document=dict(code='parent', title='Parent'))
        parent = self.change(parent, 'deactivate', confirmation=True)
        self.call('create', document=dict(code='parent/child', title='Child'))
        parent = self.call('load', identity=parent['identity'])
        with self.assertRaisesRegex(Exception, 'every project'):
            self.change(parent, 'delete', confirmation=True)


if __name__ == '__main__':
    unittest.main()
