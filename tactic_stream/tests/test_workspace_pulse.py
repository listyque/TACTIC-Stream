"""The example ZIP installs through the real manager in unrelated projects."""
from pathlib import Path
import unittest
import zipfile

from pyasm.common import Environment
from pyasm.search.search import RequestContext, request_context
from tests import test_foundation

PACKAGE = Path(__file__).resolve().parents[2] / 'examples/workspace_pulse'
MANAGER = 'tactic.ui.app.PluginManagerCmd'
DASHBOARD = 'tactic.ui.panel.dashboard_cmd.DashboardCmd'


class WorkspacePulseTests(unittest.TestCase):
    setUp = test_foundation.Foundation.setUp
    call = test_foundation.Foundation.call

    def manager(self, action, **values):
        return self.call('execute_cmd', MANAGER, dict(
            action=action, project_code=self.ticket['project'], **values))['info']

    def dashboard(self, name):
        return self.call('execute_cmd', DASHBOARD, dict(action='read', name=name,
            project_code=self.ticket['project']))['info']

    def test_zip_activation_two_projects_and_removal(self):
        with self.store.connection('one') as db:
            before = list(db.execute('SELECT * FROM entity'))
        for project, status, due in [('one', 'Review', '2027-01-01'),
                                      ('one', 'Working', None), ('two', 'Review', None)]:
            values = dict(project_code=project, search_type='contract/entity', search_code='A',
                          description='Example task', process='model', assigned='admin', status=status)
            if due:
                values['bid_end_date'] = due
            self.api.dispatch('insert', (dict(self.ticket, project=project), 'sthpw/task', values),
                              {'triggers': False})
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.token)
            upload = Path(Environment.get_upload_dir())
            upload.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(upload / 'pulse.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(PACKAGE.iterdir()):
                    if path.is_file():
                        archive.write(path, 'workspace_pulse/' + path.name)
        staged = self.manager('install', upload_file_name='pulse.zip')
        identity = staged['identity']
        active = self.manager('activate', identity=identity, expected_revision=staged['revision'])
        self.assertTrue(active['metadata']['active'])
        document = self.dashboard('workspace_pulse')['document']
        self.assertEqual(document['blocks'][0]['children'][0]['filters'][0]['value'], 'one')
        state = self.dashboard('workspace_pulse')
        model = self.call('execute_cmd', DASHBOARD, dict(action='preview', project_code='one',
            document=document, expected_revision=state['revision']))['info']['model']
        self.assertEqual([row['value'] for row in model['layoutNodes'][0]['children']], [2, 1, 1, 2])
        filtered = self.call('execute_cmd', DASHBOARD, dict(action='preview', project_code='one',
            document=document, expected_revision=state['revision'],
            filter_values={'status': {'enabled': True, 'value': 'Review'}}))['info']['model']
        self.assertEqual([row['value'] for row in filtered['layoutNodes'][0]['children']], [1, 1, 0, 1])
        self.assertIn('no episode', self.dashboard('workspace_vfx')['document']['blocks'][0]['children'][0]['text'])
        with self.store.connection('one') as db:
            self.assertEqual(list(db.execute('SELECT * FROM entity')), before)

        self.ticket['project'] = 'two'
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO search_object(code,search_type,namespace,database,table_name,class_name,title) "
                       "VALUES ('studio/shot','studio/shot','studio','{project}','shot','pyasm.search.SObject','Shots')")
            db.execute("INSERT INTO search_object(code,search_type,namespace,database,table_name,class_name,title) "
                       "VALUES ('other/shot','other/shot','other','{project}','shot','pyasm.search.SObject','Unrelated shots')")
        with self.store.connection('two', write=True) as db:
            db.execute('CREATE TABLE shot (id INTEGER PRIMARY KEY, code varchar(256), name text, description text, s_status varchar(256))')
            db.execute("INSERT INTO shot (code,name) VALUES ('SHOT_X','A real shot')")
        self.call('execute_python_script', '', dict(code=
            "from pyasm.biz import Schema\n"
            "Schema.create('two', 'Fixture', '<schema><search_type name=\"studio/shot\"/></schema>')"))
        current = self.manager('load', identity=identity)
        self.manager('activate', identity=identity, expected_revision=current['revision'])
        vfx = self.dashboard('workspace_vfx')['document']
        self.assertEqual(vfx['blocks'][0]['children'][0]['search_type'], 'studio/shot')
        self.assertEqual(len(vfx['blocks'][0]['children']), 1)
        self.assertEqual(self.dashboard('workspace_pulse')['document']['blocks'][0]['children'][0]['filters'][0]['value'], 'two')
        # Render both actual documents, including grouped SQL and native table configs.
        for name in ('workspace_pulse', 'workspace_vfx'):
            state = self.dashboard(name)
            preview = self.call('execute_cmd', DASHBOARD, dict(action='preview',
                project_code='two', document=state['document'], expected_revision=state['revision']))['info']
            self.assertTrue(preview['model']['layoutNodes'])
        current = self.manager('load', identity=identity)
        reloaded = self.manager('reload', identity=identity,
            expected_revision=current['revision'], confirmation=True)
        self.assertTrue(reloaded['metadata']['active'])
        current = self.manager('load', identity=identity)
        self.manager('deactivate', identity=identity, expected_revision=current['revision'], confirmation=True)
        with self.store.connection('two') as db:
            self.assertEqual(db.execute('SELECT name FROM shot').fetchone()[0], 'A real shot')
            self.assertEqual(db.execute("SELECT count(*) FROM spt_widget_config WHERE view LIKE 'dashboard.workspace_%' OR view='workspace_pulse_table'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM spt_url WHERE url LIKE '/dashboard/workspace_%'").fetchone()[0], 0)
            self.assertFalse(any('dashboard_workspace_' in row[0] for row in db.execute(
                "SELECT config FROM spt_widget_config WHERE search_type='SideBarWdg'")))
        self.ticket['project'] = 'one'
        self.assertEqual(self.dashboard('workspace_pulse')['document'], document)

    def test_collision_rolls_back_without_overwriting_existing_view(self):
        config = '<config><view name="dashboard.workspace_pulse"><html>Keep me</html></view></config>'
        self.call('insert', 'config/widget_config', dict(search_type='CustomLayoutWdg',
            view='dashboard.workspace_pulse', config=config))
        with self.assertRaisesRegex(Exception, 'already exist'):
            self.call('execute_cmd', 'tactic.command.PluginInstaller', dict(
                plugin_dir=str(PACKAGE), verbose=False, register=True))
        with self.store.connection('one') as db:
            self.assertEqual(db.execute("SELECT config FROM spt_widget_config WHERE view='dashboard.workspace_pulse'").fetchone()[0], config)
            self.assertEqual(db.execute("SELECT count(*) FROM spt_widget_config WHERE view='workspace_pulse_table'").fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
