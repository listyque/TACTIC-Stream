import shutil
import sys
import tempfile
import ast
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class UploadForm(read_tests.ReadParity):
    test_expressions_and_sql_remain_explicitly_unsupported = None

    def test_stock_preview_metadata_and_image_checkin(self):
        from PIL import Image
        from pyasm.command import Command
        from pyasm.common import Environment
        from pyasm.search import Search, SearchType, WidgetDbConfig
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        from tactic_stream.server.interface import read_form
        import upload_form_contract

        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                def configure():
                    config = SearchType.create('config/widget_config')
                    config.set_value('search_type', 'contract/work_item')
                    config.set_value('view', 'preview_test')
                    config.set_value('config', '''<config><preview_test>
                      <element name="preview"><display class="tactic.ui.widget.SimpleUploadWdg">
                        <icon_size>100%</icon_size>
                      </display><action class="pyasm.command.UploadAction"/></element>
                    </preview_test></config>''')
                    config.commit()
                command = Command()
                command.execute = configure
                command.get_transaction().set_sync(False)
                Command.execute_cmd(command)
                WidgetDbConfig.clear_cache()
                form = read_form('contract/work_item', 'preview_test', upload_form_contract.PARENT)
                field = form['fields'][0]
                self.assertEqual(field['options']['icon_size'], '100%')
                self.assertEqual(field['input'], dict(type='file', context='icon', column='preview'))
                self.assertEqual(field['action']['handler'], 'pyasm.command.UploadAction')
                path = Path(Environment.get_upload_dir()) / 'selected.png'
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', (80, 60), 'blue').save(path)
                original = path.read_bytes()
                web = WebContainer.get_web()
                web.params.clear()
                for suffix, value in dict(path=path.name, ticket=Environment.get_ticket(), context='icon', column='preview').items():
                    web.set_form_value('edit|preview|' + suffix, value)
                command = EditCmd(search_key=upload_form_contract.PARENT, view='preview_test',
                    input_prefix='edit', element_names=['preview'], expected_revision=form['expected_revision'])
                command.get_transaction().set_sync(False)
                Command.execute_cmd(command)
                snapshots = Search('sthpw/snapshot')
                snapshots.add_sobject_filter(Search.get_by_search_key(upload_form_contract.PARENT))
                snapshots.add_filter('context', 'icon')
                snapshot = snapshots.get_sobject()
                self.assertIsNotNone(snapshot)
                files = {file.get_type(): Path(file.get_lib_path()) for file in snapshot.get_all_file_objects()}
                self.assertTrue({'main', 'web', 'icon'} <= files.keys())
                self.assertEqual(files['main'].read_bytes(), original)
                for kind in ('web', 'icon'):
                    with Image.open(files[kind]) as image:
                        image.verify()
                self.assertEqual(Search.get_by_search_key(upload_form_contract.PARENT).get_value('name'), 'Parent')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import workflow_form_contract, upload_form_contract
        with cls.store.connection(write=True) as db:
            workflow_form_contract.install_fixture(db)
            upload_form_contract.install_fixture(db)
        cls.cases = [dict(method='upload_form_contract', name=mode, operation=mode, project='one') for mode in ('metadata', 'edit', 'revision', 'multi_specified', 'multi_arbitrary', 'multi_custom_icon', 'rich_metadata', 'rich_edit', 'rich_revision', 'rich_subcontext')]

    def new_result(self, case):
        import upload_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                return upload_form_contract.run(case)

    def assert_case_result(self, case, result, original):
        if case['operation'].startswith('rich_'):
            if case['operation'] == 'rich_revision':
                self.assertEqual(original['snapshots'][1][1:3], [2, 0])
                self.assertEqual(result['snapshots'][1][1:3], [1, 1])
                original['snapshots'][1][1:3] = result['snapshots'][1][1:3]
            if case['operation'] == 'rich_subcontext':
                self.assertEqual([row[0] for row in original['snapshots']], ['upload_rich_subcontext'] * 2)
                self.assertEqual([row[0] for row in result['snapshots']], ['upload_rich_subcontext/draft'] * 2)
                for row in original['snapshots']:
                    row[0] = 'upload_rich_subcontext/draft'
            self.assertEqual(result, original)
            return
        if case['operation'] == 'multi_custom_icon':
            self.assertIn('The uploaded icon file must be an image file', original['source_error'])
            self.assertEqual(result, dict(file_types=['icon', 'icon_main', 'main', 'web']))
            return
        if case['operation'].startswith('multi_'):
            self.assertEqual(result, original)
            return
        self.assertEqual(original['parent_value'], result['parent_value'].replace('&', '&amp;'))
        original['parent_value'] = result['parent_value']
        if case['operation'] == 'revision':
            # Original checkbox never reads the form; native honors is_revision.
            self.assertEqual(original['files'][1][:2], [2, 0])
            self.assertEqual(result['files'][1][:2], [1, 1])
            original['files'][1][:2] = result['files'][1][:2]
        self.assertEqual(result, original)

    def test_multi_handoff_revision_guards_and_rollback(self):
        import upload_form_contract
        from pyasm.command import Command, MultiUploadAction
        from pyasm.common import Environment, UserException, TacticException
        from pyasm.common.errors import SecurityException
        from pyasm.search import Search
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        from tactic_stream.server.interface import read_form
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                result = upload_form_contract.run({'operation': 'multi_revision'})
                self.assertEqual(result['snapshot'], [1, 1, 'Two files'])
                self.assertEqual(result['stored'], '||finish||review||')
                form = read_form('contract/work_item', upload_form_contract.MULTI_VIEW, upload_form_contract.PARENT)
                selector = next(field for field in form['fields'] if field['name'] == 'with_pipeline_type')
                self.assertEqual(selector['input']['value'], ['review', 'finish'])
                files = next(field for field in form['fields'] if field['name'] == 'attachments')['input']
                self.assertEqual(files['fields'], [dict(name='primary', required=True), dict(name='secondary', required=False)])
                self.assertEqual(files['context']['choices'], ['publish', 'review'])
                web = WebContainer.get_web()
                web.params.clear()
                path = Path(Environment.get_upload_dir()) / 'rollback.bin'
                path.write_bytes(b'multi rollback')
                web.set_form_value('edit|name', 'Must roll back')
                web.set_form_value('edit|primary|path', path.name)
                web.set_form_value('edit|primary|ticket', 'wrong_ticket')
                web.set_form_value('edit|attachments|context', 'rollback_multi')
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                def command():
                    cmd = EditCmd(search_key=upload_form_contract.PARENT, view=upload_form_contract.MULTI_VIEW, element_names=['name', 'attachments'])
                    cmd.get_transaction().set_sync(False)
                    return cmd
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(command())
                self.assertEqual(path.read_bytes(), b'multi rollback')
                web.set_form_value('edit|primary|ticket', Environment.get_ticket())
                web.set_form_value('edit|secondary|path', path.name)
                with self.assertRaises(UserException):
                    Command.execute_cmd(command())
                self.assertTrue(path.is_file())
                web.params.pop('edit|secondary|path')
                original = MultiUploadAction.postprocess
                def fail(action):
                    original(action)
                    raise ValueError('Late multi-upload failure')
                with patch.object(MultiUploadAction, 'postprocess', fail), self.assertRaises(ValueError):
                    Command.execute_cmd(command())
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                self.assertEqual(Search.get_by_search_key(upload_form_contract.PARENT).get_value('name'), 'Parent')
                self.assertTrue(any(file.read_bytes() == b'multi rollback' for file in (Path(Environment.get_tmp_dir()) / 'undo').rglob('*.bin')))
                web.params.clear()
                with self.assertRaises(UserException):
                    Command.execute_cmd(command())
                malformed = MultiUploadAction()
                malformed.set_name('attachments')
                malformed.set_option('names', 'primary|secondary')
                malformed.set_option('types', 'main')
                with self.assertRaises(TacticException):
                    malformed._upload_specified_files()
                from pyasm.widget import MultiSelectWdg
                self.assertTrue(MultiSelectWdg()._is_selected(0, [0]))
                # A custom icon's type takes precedence even when its input name differs.
                from PIL import Image
                for name, size in [('main.png', (32, 32)), ('preview.png', (16, 16))]:
                    Image.new('RGB', size, 'blue').save(Path(Environment.get_upload_dir()) / name)
                web.set_form_value('edit|primary|path', 'main.png')
                web.set_form_value('edit|thumbnail|path', 'preview.png')
                action = MultiUploadAction()
                action.set_name('attachments')
                action.set_input_prefix('edit')
                action.set_sobject(Search.get_by_search_key(upload_form_contract.PARENT))
                action.set_option('names', 'primary|thumbnail')
                action.set_option('types', 'main|icon_main')
                web.set_form_value('edit|attachments|context', 'custom_icon')
                cmd = Command()
                cmd.execute = action.postprocess
                cmd.get_transaction().set_sync(False)
                from pyasm.command import Trigger
                with patch.object(Trigger, 'call', wraps=Trigger.call) as events:
                    Command.execute_cmd(cmd)
                self.assertEqual(action.file_types, ['main', 'icon_main', 'web', 'icon'])
                self.assertTrue(any(call.args[:2] == (action, 'email') for call in events.call_args_list))

    def test_upload_guards_and_late_failure_restore_files_and_rows(self):
        import upload_form_contract
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException, TacticException
        from pyasm.command import Command
        from pyasm.search import Search, SearchType
        from tactic.ui.panel import EditCmd
        from tactic_stream.server.interface import read_form
        from pyasm.web import WebContainer
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                upload_form_contract.setup()
                form = read_form('contract/work_task', upload_form_contract.VIEW)
                parent = next(field for field in form['fields'] if field['name'] == 'parent_key')
                self.assertEqual(parent['values'], [upload_form_contract.PARENT])
                self.assertEqual(parent['input']['label'], 'PARENT')
                form = read_form('contract/work_task', upload_form_contract.VIEW, upload_form_contract.TASK)
                self.assertTrue(next(field for field in form['fields'] if field['name'] == 'parent_key')['input']['read_only'])
                from tactic.ui.input import TaskSObjectInputWdg
                field = TaskSObjectInputWdg('parent_key')
                field.set_sobject(SearchType.create('contract/work_task'))
                field.set_option('parent_key', 'contract/work_item?project=one&code=MISSING')
                with self.assertRaises(ValueError):
                    field.get_input()
                # Original metadata preparation can read an accessible foreign parent.
                field.set_option('parent_key', 'contract/work_item?project=two&code=PARENT')
                self.assertEqual(field.get_input().get_value(), 'contract/work_item?project=two&code=PARENT')
                self.assertEqual(field.parent_label, 'PARENT')
                path = Path(Environment.get_upload_dir()) / 'rollback.txt'
                path.write_bytes(b'unchanged upload')
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                web = WebContainer.get_web()
                web.set_form_value('edit|name', 'Must roll back')
                web.set_form_value('edit|attachment|path', path.name)
                web.set_form_value('edit|attachment|context', 'rollback_form')
                web.set_form_value('edit|attachment|ticket', 'another_session')
                def command():
                    cmd = EditCmd(search_key=upload_form_contract.PARENT, view=upload_form_contract.VIEW, element_names=['name', 'attachment'])
                    cmd.get_transaction().set_sync(False)
                    return cmd
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(command())
                web.set_form_value('edit|attachment|ticket', Environment.get_ticket())
                from pyasm.command import UploadAction
                original = UploadAction.postprocess
                def failing(action):
                    original(action)
                    raise ValueError('Failure after file check-in')
                with patch.object(UploadAction, 'postprocess', failing), self.assertRaises(ValueError):
                    Command.execute_cmd(command())
                # Original create/uploaded undo keeps consumed sources in the undo cache.
                self.assertTrue(any(file.read_bytes() == b'unchanged upload' for file in (Path(Environment.get_tmp_dir()) / 'undo').rglob('*.txt')))
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                self.assertEqual(Search.get_by_search_key(upload_form_contract.PARENT).get_value('name'), 'Parent')
                web.params.clear()
                cmd = EditCmd(search_key=upload_form_contract.PARENT, view=upload_form_contract.VIEW,
                    element_names=['name'], extra_action={'pyasm.command.UploadAction': {'file_required': 'true'}})
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(TacticException):
                    Command.execute_cmd(cmd)
                self.assertEqual(Search.get_by_search_key(upload_form_contract.PARENT).get_value('name'), 'Parent')

    def test_rich_metadata_default_context_and_subcontext_guard(self):
        import upload_form_contract
        from pyasm.command import Command
        from pyasm.common import Environment, UserException
        from pyasm.search import Search
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        from tactic.ui.widget import SimpleUploadWdg, UploadWdg
        from tactic_stream.server.interface import read_form
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                result = upload_form_contract.run({'operation': 'rich_metadata'})
                self.assertEqual(result['controls'][1]['choices'], ['publish', 'review'])
                self.assertEqual(result['controls'][4]['choices'], ['model', 'review', 'finish'])
                obj = Search.get_by_search_key(upload_form_contract.PARENT)
                self.assertEqual(obj.get_icon_context(), 'icon')
                self.assertEqual(obj.get_icon_context('thumbnail'), 'thumbnail')
                simple = SimpleUploadWdg(key='attachment')
                simple.set_sobject(obj)
                self.assertEqual(simple.get_input().context, 'icon')
                form = read_form('contract/work_item', 'rich_upload_form_test', upload_form_contract.PARENT)
                field = next(field for field in form['fields'] if field['name'] == 'attachment')
                self.assertEqual(field['class_name'], 'tactic.ui.widget.upload_wdg.UploadWdg')
                self.assertEqual(field['input']['context']['choices'], ['publish', 'review'])
                self.assertEqual(field['input']['context']['value'], 'publish')
                self.assertEqual(field['input']['fields'], [dict(name='attachment', required=False)])
                self.assertTrue(field['input']['subcontext'])
                web = WebContainer.get_web()
                web.params.clear()
                path = Path(Environment.get_upload_dir()) / 'invalid_context.txt'
                path.write_bytes(b'must stay staged')
                web.set_form_value('edit|name', 'Must roll back')
                web.set_form_value('edit|attachment|path', path.name)
                web.set_form_value('edit|attachment|ticket', Environment.get_ticket())
                web.set_form_value('edit|attachment|subcontext', 'invalid')
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                cmd = EditCmd(search_key=upload_form_contract.PARENT, view='rich_upload_form_test', element_names=['name', 'attachment'])
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(UserException):
                    Command.execute_cmd(cmd)
                self.assertEqual(path.read_bytes(), b'must stay staged')
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                self.assertEqual(Search.get_by_search_key(upload_form_contract.PARENT).get_value('name'), 'Parent')
                web.params.clear()
                unsupported = UploadWdg(key='attachment', client_action='icon_checkin')
                from pyasm.common.errors import UnsupportedContract
                with self.assertRaises(UnsupportedContract):
                    unsupported.get_input()

    def test_original_client_upload_handler_metadata_and_form_checkin(self):
        from test_transport import Transport
        from test_foundation import LEGACY
        import workflow_form_contract, upload_form_contract
        class FixtureServer(Transport):
            pass
        FixtureServer.setUpClass()
        self.addCleanup(FixtureServer.tearDownClass)
        with FixtureServer.store.connection(write=True) as db:
            db.execute("DELETE FROM schema WHERE code='one' OR project_code='one'")
            workflow_form_contract.install_fixture(db)
            upload_form_contract.install_fixture(db)
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_upload_form_client', LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(FixtureServer.url)
        client.set_project('one')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        source = (Path(__file__).parent / 'scripts/upload_form_contract.py').read_text(encoding='utf-8')
        client.execute_python_script('', kwargs={'code': source + '\nreturn run({"operation": "metadata"})'})
        handler = Path('D:/grav/Tactic Stream/TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(handler).body if isinstance(node, ast.FunctionDef) and node.name == 'query_EditWdg')
        code = ast.get_source_segment(handler, function) + '\nreturn query_EditWdg(args=kwargs["form_args"], search_type=kwargs["kind"])'
        result = json.loads(client.execute_python_script('', kwargs=dict(code=code, kind='contract/work_item',
            form_args=dict(search_type='contract/work_item', search_key=upload_form_contract.PARENT, view=upload_form_contract.VIEW)))['info'])
        attachment = next(item for item in result['InputWidgets'] if item['name'] == 'attachment')
        self.assertEqual(attachment['context'], 'form_upload')
        path = Path(FixtureServer.temp.name) / 'client.txt'
        path.write_bytes(b'XML-RPC form upload')
        client.upload_file(str(path))
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=upload_form_contract.PARENT,
            view=upload_form_contract.VIEW, element_names=['attachment']), values={
                'edit|attachment|path': path.name, 'edit|attachment|ticket': client.transaction_ticket,
                'edit|attachment|context': 'xmlrpc_form', 'edit|attachment|description': 'Client attachment',
            })
        snapshot = client.get_snapshot(upload_form_contract.PARENT, 'xmlrpc_form', include_files=True)
        main = next(file for file in snapshot['__files__'] if file['type'] == 'main')
        self.assertEqual((Path(main['checkin_dir']) / main['file_name']).read_bytes(), b'XML-RPC form upload')
        client.execute_python_script('', kwargs={'code': source + '\nsetup_multi(True)\nreturn True'})
        values = {'edit|attachments|context': 'client_multi', 'edit|attachments|subcontext': 'draft',
                  'edit|with_pipeline_type': ['review', 'finish']}
        for index, payload in enumerate((b'First XML-RPC file', b'Second XML-RPC file')):
            path = Path(FixtureServer.temp.name) / ('multi%d.txt' % index)
            path.write_bytes(payload)
            client.upload_file(str(path))
            values['edit|attachments%d|path' % index] = path.name
            values['edit|attachments%d|ticket' % index] = client.transaction_ticket
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=upload_form_contract.PARENT,
            view=upload_form_contract.MULTI_VIEW, element_names=['with_pipeline_type', 'attachments']), values=values)
        snapshot = client.get_snapshot(upload_form_contract.PARENT, 'client_multi/draft', include_files=True)
        self.assertEqual(sorted((Path(file['checkin_dir']) / file['file_name']).read_bytes() for file in snapshot['__files__']),
                         [b'First XML-RPC file', b'Second XML-RPC file'])
        client.execute_python_script('', kwargs={'code': source + '\nreturn run({"operation": "rich_metadata"})'})
        path = Path(FixtureServer.temp.name) / 'rich_client.txt'
        path.write_bytes(b'Rich XML-RPC upload')
        client.upload_file(str(path))
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=upload_form_contract.PARENT,
            view='rich_upload_form_test', element_names=['attachment']), values={
                'edit|attachment|path': path.name, 'edit|attachment|ticket': client.transaction_ticket,
                'edit|attachment|context': 'client_rich', 'edit|attachment|subcontext': 'draft',
                'edit|attachment|description': 'Rich SDK',
            })
        snapshot = client.get_snapshot(upload_form_contract.PARENT, 'client_rich/draft', include_files=True)
        self.assertEqual(snapshot['description'], 'Rich SDK')
        main = next(file for file in snapshot['__files__'] if file['type'] == 'main')
        self.assertEqual((Path(main['checkin_dir']) / main['file_name']).read_bytes(), b'Rich XML-RPC upload')
        import compound_form_contract
        with FixtureServer.store.connection(write=True) as db:
            compound_form_contract.install_fixture(db)
        source = (Path(__file__).parent / 'scripts/compound_form_contract.py').read_text(encoding='utf-8')
        client.execute_python_script('', kwargs={'code': source + '\nsetup()\nreturn True'})
        path = Path(FixtureServer.temp.name) / 'client_objects.zip'
        path.write_bytes(compound_form_contract.archive_payload())
        client.upload_file(str(path))
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=compound_form_contract.KEY,
            view=compound_form_contract.VIEW, element_names=['clock', 'attachments']), values={
                'edit|clock': '06:45', 'edit|attachments0|path': path.name,
                'edit|attachments0|ticket': client.transaction_ticket, 'edit|attachments|context': 'client_archive',
            })
        self.assertEqual(client.get_by_code('contract/work_item', 'PARENT')['clock'], '06:45:00')
        for code, count in [('PARENT', 2), ('SECOND', 1)]:
            snapshot = client.get_snapshot('contract/work_item?project=one&code=' + code, 'client_archive', include_files=True)
            self.assertEqual(len(snapshot['__files__']), count)
            self.assertTrue(all((Path(file['checkin_dir']) / file['file_name']).is_file() for file in snapshot['__files__']))
