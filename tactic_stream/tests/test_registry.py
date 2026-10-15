"""Registered classes and built-ins compared with the original, private runtime."""
import ast
import test_read_parity as read_tests
from tools.registry_probe import run_registry_case
from pyasm.common.common import Common, Container
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SearchType, SObjectFactory, request_context


def registry_fixture(store):
    read_tests.read_fixture(store)
    with store.connection(write=True) as db:
        for name, cls in [('custom', 'CustomRow'), ('old_style', 'OldStyleRow'), ('retry', 'RetryRow')]:
            db.execute('INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES (?,?,?,?,?,?)',
                       ('contract/' + name, 'contract/' + name, 'contract', '{project}', 'entity', 'registry_contract.' + cls))
        for name in ('snapshot',):
            db.execute('CREATE TABLE IF NOT EXISTS ' + name + ' (id integer PRIMARY KEY, code text)')
            db.execute('DELETE FROM search_object WHERE search_type=?', ('sthpw/' + name,))
            db.execute('INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES (?,?,?,?,?,?)',
                       ('sthpw/' + name, 'sthpw/' + name, 'sthpw', 'sthpw', name, 'pyasm.search.SObject'))
        db.execute("DELETE FROM search_object WHERE search_type='config/prod_setting'")
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/prod_setting','config/prod_setting','config','{project}','prod_setting','pyasm.biz.ProjectSetting')")
    for project in ('one', 'two', 'sthpw'):
        with store.connection(project, write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS prod_setting (id integer PRIMARY KEY, code text, key text, value text, search_type text, project_code text, s_status text)')


def registry_cases():
    result = []
    def add(name, **kwargs):
        result.append({'name': name, 'method': 'registry_contract', **kwargs})
    for operation in ('get', 'search', 'create', 'direct'):
        for key in ('contract/entity', 'config/prod_setting', 'sthpw/project',
                    'sthpw/task', 'sthpw/login_group', 'sthpw/snapshot'):
            if operation == 'create' and key == 'sthpw/login_group':
                continue  # LoginGroup object methods are outside registration.
            add(operation + '_' + key, operation=operation, types=[key, key])
    for types in (['contract/entity', 'config/prod_setting', 'sthpw/task', 'sthpw/login_group', 'sthpw/snapshot'],
                  ['contract/entity', 'contract/entity?project=two', 'sthpw/snapshot', 'sthpw/snapshot'],
                  ['sthpw/snapshot', 'sthpw/task', 'sthpw/snapshot', 'sthpw/task'],
                  ['config/missing', 'contract/missing', 'contract/missing']):
        add('sequence_' + str(len(result)), types=types, no_exception=True)
    for value in ('Foo_BAR/baz, test\nFile-v01.png', 'Привет Мир, Тест/СЦЕНА', None, 12, ['a', 'b'], ''):
        for lower in (False, True):
            add('keywords_' + str(len(result)), operation='keywords', value=value, lower=lower,
                path='ShowABC/Scene001/test_asset-v002.final.exr')
    for handler in ('folder', 'login_group'):
        add('noop_' + handler, operation='noop', handler=handler)
    for input in ({}, {'search_key': 'sthpw/task?code=A', 'mode': 'insert'},
                  {'search_key': 'contract/entity?project=one&code=A', 'mode': 'update'},
                  {'search_key': 'contract/entity?project=one&code=A', 'mode': 'insert'}):
        add('task_creator_' + str(len(result)), operation='noop', handler='task_creator', input=input, caller=True)
    add('exceptions', operation='exceptions')
    add('automatic_insert', operation='automatic_insert')
    for search_type in ('contract/custom', 'contract/old_style', 'contract/retry'):
        for operation in ('search', 'class_search', 'metadata_search', 'create', 'factory'):
            add(search_type + '_' + operation, operation='script', script_operation=operation, search_type=search_type)
        add(search_type + '_project_two', operation='script', search_type=search_type, project='two')
        add(search_type + '_missing', operation='script', search_type=search_type, code='MISSING')
        add(search_type + '_projection', operation='script', search_type=search_type, columns=['code', 'name'])
    return result


class RegistryParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Parent fixture is already present; use a fresh private store for this domain.
        from pyasm.search.storage import Store
        from pyasm.security.authenticator import hash_password
        cls.store = Store(cls.data / 'registry')
        cls.store.initialize(hash_password('private-test-password'))
        registry_fixture(cls.store)
        from tactic_stream.server.api import Api
        cls.api = Api(cls.store)
        cls.ticket = cls.api.get_ticket('admin', 'private-test-password')
        cls.cases = registry_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_registry_case(case)

    def assert_case_result(self, case, result, original):
        if isinstance(result, dict):
            for row in result.get('rows', []):
                keys = row.get('arguments', {}).get('keys', [])
                self.assertNotIn('_object_classes', keys)
                # Native TIME support adds metadata without changing the original constructor values.
                if 'time_cols' in keys:
                    keys.remove('time_cols')
        if isinstance(result, list):
            for state in result:
                if 'static' not in state:
                    continue
                for row in state['static']:
                    if row['class'] == 'tactic.command.TaskCompleteTrigger':
                        self.assertEqual(row['mode'], 'same process,same transaction')
                        row['mode'] = ''
                        row['data'].pop('mode', None)
                        row['quoted'].pop('mode', None)
                status = [row for row in state['static'] if row['class'] == 'tactic.core.bootstrap.StatusLogTrigger']
                self.assertLessEqual(len(status), 1)
                state['static'] = [row for row in state['static'] if row not in status]
                if status and state['count'] is not None:
                    state['count'] -= 1
        super().assert_case_result(case, result, original)

    def test_entire_exception_and_namespace_modules_are_unchanged(self):
        for native, original in [('pyasm/common/common_exception.py', 'pyasm/common/common_exception.py'),
                                 ('tactic/__init__.py', 'tactic/__init__.py')]:
            self.assertEqual((read_tests.ROOT / 'src' / native).read_bytes(),
                             (read_tests.LEGACY / 'src' / original).read_bytes())
        from pyasm.common.errors import TacticException, SecurityException
        from pyasm.common.common_exception import TacticException as Alias, SecurityException as SecurityAlias
        from pyasm.search import SObjectFactory as FactoryAlias
        self.assertIs(TacticException, Alias)
        self.assertIs(SecurityException, SecurityAlias)
        self.assertIs(SObjectFactory, FactoryAlias)

    def test_whole_task_creator_and_disabled_handler_bodies_are_preserved(self):
        def owner(path, name):
            return next(node for node in ast.parse(path.read_text(encoding='utf-8')).body
                        if isinstance(node, ast.ClassDef) and node.name == name)
        old = read_tests.LEGACY / 'src/tactic/command'
        new = read_tests.ROOT / 'src/tactic/command'
        self.assertEqual(ast.dump(owner(old / 'pipeline_task_trigger.py', 'TaskCreatorTrigger')),
                         ast.dump(owner(new / 'pipeline_task_trigger.py', 'TaskCreatorTrigger')))
        for name, filename in [('LoginGroupTrigger', 'login_group_trigger.py'), ('FolderTrigger', 'global_search_trigger.py')]:
            source = next(node for node in owner(old / filename, name).body if isinstance(node, ast.FunctionDef) and node.name == 'execute')
            actual = next(node for node in owner(new / filename, name).body if isinstance(node, ast.FunctionDef) and node.name == 'execute')
            self.assertEqual(ast.dump(source), ast.dump(actual))

    def test_virtual_metadata_and_cache_are_request_local(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            metadata = SearchType.get('contract/entity')
            self.assertIs(metadata, SearchType.get('contract/entity?project=two'))
            metadata.set_value('title', 'Pending title')
            self.assertEqual(SearchType.get('contract/entity').get_title(), 'Pending title')
            SearchType.set_virtual('alias', metadata)
            self.assertIs(SearchType.get('alias'), metadata)
        with request_context(RequestContext(self.store, 'admin', 'two')):
            self.assertIsNone(SearchType.get_virtual('alias'))
            self.assertNotEqual(SearchType.get('contract/entity').get_title(), 'Pending title')

    def test_builtin_construction_and_reads_do_not_mutate_databases(self):
        from pyasm.biz import Task, Snapshot
        from tactic.command import GlobalSearchTrigger
        before = {path: path.read_bytes() for path in self.store.data_dir.glob('db/*.db')}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.assertIsInstance(Snapshot(), Snapshot)
            self.assertTrue(callable(Common.resolve_class('pyasm.command.SnapshotIsLatestTrigger')))
            self.assertEqual(GlobalSearchTrigger().get_child_codes('A', 'contract/entity'), [])
            with self.assertRaises(UnsupportedContract):
                Task.add_initial_tasks(None)
            obj = Search.get_by_code('contract/entity', 'A')
            trigger = GlobalSearchTrigger()
            trigger.set_caller(obj)
            trigger.set_input({'search_key': obj.get_search_key(), 'search_type': obj.get_search_type(), 'sobject': obj.get_data()})
            # Native index writes require installed authenticated Security, beyond a bare RequestContext.
            with self.assertRaisesRegex(UnsupportedContract, 'Sudo requires'):
                trigger.execute()
        self.assertEqual({path: path.read_bytes() for path in before}, before)
