"""A real multi-feature package, installed in an ordinary disposable project."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from pyasm.common import Environment
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.checkin_benchmark import prepare


EXAMPLE = Path(__file__).parents[2] / 'examples' / 'studio_review'


class StudioReviewPluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one', language='python')

    def command(self, name, **values):
        return self.api.dispatch('execute_cmd', (self.auth, name, values))

    def manager(self, action, document=None, **values):
        if document:
            values.update(identity=document['identity'], expected_revision=document['revision'])
        return self.command('tactic.ui.app.PluginManagerCmd', action=action, project_code=self.auth['project'], **values)['info']

    def install(self, broken=False):
        import runpy
        archive = runpy.run_path(str(EXAMPLE / 'build.py'))['build'](Path(self.temp.name) / 'studio.zip')
        if broken:
            with zipfile.ZipFile(archive) as source:
                files = {name:source.read(name) for name in source.namelist()}
            files['studio_review/install.py'] += b"\nraise ValueError('late Studio Review install failure')\n"
            with zipfile.ZipFile(archive,'w') as output:
                for name,content in files.items():
                    output.writestr(name,content)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            target = Path(Environment.get_upload_dir()) / archive.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read_bytes())
        doc = self.manager('install', upload_file_name=archive.name)
        self.assertFalse(doc['metadata']['active'])
        return doc if broken else self.manager('activate', doc, confirmation=True)

    def test_install_render_python_export_reload_remove(self):
        doc = self.install()
        self.assertTrue(doc['metadata']['active'])
        self.assertTrue({'widget', 'column', 'theme', 'python', 'search_type', 'data'} <= {r['kind'] for r in doc['metadata']['resources']})
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            from tactic.ui.table.custom_layout_element_wdg import read_custom_layout
            from tactic_stream.server.interface import read_interface
            from tactic_stream.server.navigation import read_navigation
            self.assertEqual(3, Search('studio/review').get_count())
            review = Search.get_by_code('studio/review', 'STUDIO_REVIEW_001')
            cell = read_custom_layout(review.get_search_key(), 'studio_review.column')
            self.assertEqual('widget', cell['layoutNodes'][0]['kind'])
            self.assertEqual(65, cell['layoutNodes'][0]['sample']['record']['progress'])
            page = read_custom_layout(review.get_search_key(), 'studio_review.widget')
            nested = next(e for e in page['layoutNodes'][0]['layout']['elements'] if e['kind']=='view')
            self.assertEqual(2, len(nested['widget_layout']['elements']))
            table = read_interface('studio/review', 'studio_review.table')
            self.assertEqual('tactic.ui.table.CustomLayoutElementWdg', table['table']['elements'][2]['display']['handler'])
            navigation = read_navigation()
            self.assertTrue(any(e['name']=='studio_review' for e in navigation['entries']), navigation)
        script = next(r for r in doc['metadata']['resources'] if r['kind']=='python')
        doc = self.manager('open_resource', identity=doc['identity'], resource=script['key'])
        doc = self.manager('run_resource', doc, resource=script['key'], inputs=json.dumps(dict(review_code='STUDIO_REVIEW_001')), confirmation=True)
        self.assertIn('Approved', json.dumps(doc['metadata']['runResult']))
        theme = next(r for r in doc['metadata']['resources'] if r['kind']=='theme')
        doc = self.manager('apply_theme', doc, resource=theme['key'])
        self.assertEqual('#84c8db', doc['metadata']['pluginTheme']['dark']['accent'])
        doc = self.manager('export', doc)
        doc = self.manager('reload', doc, confirmation=True)
        self.assertTrue(doc['metadata']['active'])
        doc = self.manager('deactivate', doc, confirmation=True)
        self.assertFalse(doc['metadata']['active'])
        self.assertIsNone(doc['metadata']['pluginTheme'])
        self.assertEqual([], doc['metadata']['resources'])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            self.assertIsNone(Search.get_by_code('config/custom_script', 'STUDIO_REVIEW_APPROVE'))
            self.assertIsNone(Search.get_by_code('config/prod_setting', 'STUDIO_REVIEW_INSTALLED'))

    def test_late_python_failure_rolls_back_schema_records_navigation_and_registration(self):
        doc = self.install(broken=True)
        with self.assertRaisesRegex(Exception,'late Studio Review install failure'):
            self.manager('activate', doc, confirmation=True)
        current = self.manager('load', identity=doc['identity'])
        self.assertFalse(current['metadata']['active'])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            from pyasm.biz import Project
            from tactic_stream.server.navigation import read_navigation
            self.assertIsNone(Search.get_by_code('config/custom_script','STUDIO_REVIEW_APPROVE'))
            self.assertIsNone(Search.get_by_code('config/plugin','studio_review'))
            self.assertIsNone(Search.get_by_code('config/prod_setting','STUDIO_REVIEW_INSTALLED'))
            self.assertNotIn('studio_review',self.store.tables(Project.get().get_code()))
            self.assertFalse(any(item['name']=='studio_review' for item in read_navigation()['entries']))
            self.assertIsNotNone(Search.get_by_code('cg/scenes','EP001'))

    def test_same_package_in_empty_second_project_preserves_first_project(self):
        original=self.install()
        self.command('tactic.command.CreateProjectCmd',project_code='two',project_title='Empty plugin project',project_stype=[])
        self.auth['project']='two'
        doc=self.manager('load',identity=original['identity'])
        self.assertFalse(doc['metadata']['active'])
        doc=self.manager('activate',doc,confirmation=True)
        with request_context(RequestContext(self.store,'admin','two')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            from tactic_stream.server.navigation import read_navigation
            self.assertEqual(3,Search('studio/review').get_count())
            self.assertTrue(any(row['name']=='studio_review' for row in read_navigation()['entries']))
        self.manager('deactivate',doc,confirmation=True)
        self.auth['project']='one'
        doc=self.manager('load',identity=original['identity'])
        self.assertTrue(doc['metadata']['active'])
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            self.assertEqual(3,Search('studio/review').get_count())


if __name__ == '__main__':
    unittest.main()
