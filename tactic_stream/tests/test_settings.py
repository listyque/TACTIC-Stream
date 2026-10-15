"""Project settings/defaults/code preparation against original TACTIC."""
import ast
import inspect
from unittest.mock import patch

import test_read_parity as read_tests
from test_sobject_state import state_fixture
from tools.settings_probe import run_settings_case
from pyasm.common.common import Container
from pyasm.common.errors import UnsupportedContract
from pyasm.biz.prod_setting import ProjectSetting, ProdSetting
from pyasm.search.search import RequestContext, Search, SearchType, SObject, request_context


def settings_fixture(store):
    state_fixture(store)
    with store.connection(write=True) as db:
        db.execute("INSERT OR IGNORE INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/prod_setting','config/prod_setting','config','{project}','prod_setting','pyasm.biz.ProjectSetting')")
        db.execute("UPDATE search_object SET database='{project}',table_name='prod_setting',class_name='pyasm.biz.ProjectSetting' WHERE search_type='config/prod_setting'")
    for project in ('one', 'two'):
        with store.connection(project, write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS prod_setting (id integer PRIMARY KEY, code text, "key" text, value text, "type" text, description text, search_type text, s_status text)')
            db.execute('ALTER TABLE entity ADD COLUMN pipeline_code text')
            rows = [
                (1, 'P1', 'autofill_pipeline_code', 'false', 'string', '', None, None),
                (2, 'P2', 'code_prefix', 'ENT' if project == 'one' else 'TWO', 'string', '', 'contract/entity', None),
                (3, 'P3', 'code_format', 'id' if project == 'one' else 'random', 'string', '', 'contract/entity', None),
                (4, 'P4', 'text', 'a|b|a|', 'string', '', None, None),
                (5, 'P5', 'pairs', 'a:1|b:2|a:3', 'string', '', None, None),
                (6, 'P6', 'invalid_pairs', 'a:1:2', 'string', '', None, None),
                (7, 'P7', 'json', '{"enabled":false,"owner":"Тест"}', 'string', '', None, None),
                (8, 'P8', 'empty', '', 'string', '', None, None),
                (9, 'P9', 'retired', 'hidden', 'string', '', None, 'retired'),
            ]
            db.executemany('INSERT INTO prod_setting (id,code,"key",value,"type",description,search_type,s_status) VALUES (?,?,?,?,?,?,?,?)', rows)


def settings_cases():
    cases = []
    def step(method, *args, **options):
        return {'method': method, 'args': list(args), **options}
    def add(name, steps, **options):
        cases.append({'name': name, 'method': 'project_settings', 'steps': steps, **options})
    for method in ('get_by_key', 'get_value_by_key', 'get_json_value_by_key', 'get_seq_by_key', 'get_map_by_key', 'get_dict_by_key'):
        for key in ('missing', 'empty', 'text', 'pairs', 'invalid_pairs', 'json', 'retired'):
            add(method + '_' + key, [step(method, key)])
    for project in ('one', 'two'):
        add('scoped_values_' + project, [step('get_value_by_key', 'code_prefix', 'contract/entity'),
            step('get_value_by_key', 'code_prefix', 'contract/child'), step('get_value_by_key', 'code_prefix')], project=project)
        add('code_' + project, [step('get_code_key', object=True)] + [step('generate_code', value, object=True) for value in (None, 1, 12, -1, '12', 'word', 1.5, True)], project=project)
    add('padded_task', [step('generate_code', 12, object=True)], search_type='sthpw/task')
    add('pipeline_autofill_disabled', [step('get_defaults', object=True), step('get_statement', object=True)])
    add('cache_identity_mutation_clear_quirk', [step('get_by_key', 'text'), step('get_by_key', 'text'),
        step('set_cached_value', 'mutated'), step('get_value_by_key', 'text'), step('clear_cache'), step('get_value_by_key', 'text')])
    add('cached_miss', [step('get_by_key', 'absent'), step('get_by_key', 'absent'), step('get_cached_obj', 'absent:None')])
    add('multi_cache', [step('get_by_search', 'pairs', is_multi=True), step('get_by_search', 'pairs', is_multi=True)])
    add('empty_multi_cache', [step('get_by_search', 'missing', is_multi=True), step('get_by_search', 'missing', is_multi=True)])
    add('null_cache_marker', [step('cache_sobject', 'probe', None), step('get_cached_obj', 'probe')])
    add('empty_list_cache_marker', [step('cache_sobject', 'probe', []), step('get_cached_obj', 'probe')])
    add('alias', [step('get_value_by_key', 'pairs'), step('get_by_key', 'pairs')], alias=True)
    add('admin_json_and_create_noop', [step('get_json_value_by_key', 'json'), step('create', 'key', 'value')], project='admin')
    add('system_json_and_create_noop', [step('get_json_value_by_key', 'json'), step('create', 'key', 'value')], project='sthpw')
    return cases


class SettingsParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings_fixture(cls.store)
        cls.cases = settings_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_settings_case(case)

    def test_cache_is_scoped_by_project_and_request(self):
        outer = RequestContext(self.store, 'admin', 'one')
        with request_context(outer):
            self.assertEqual(ProjectSetting.get_value_by_key('code_prefix', 'contract/entity'), 'ENT')
            with request_context(RequestContext(self.store, 'admin', 'two', container=outer.container)):
                self.assertEqual(ProjectSetting.get_value_by_key('code_prefix', 'contract/entity'), 'TWO')
            self.assertEqual(ProjectSetting.get_value_by_key('code_prefix', 'contract/entity'), 'ENT')
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.assertEqual(Container.get('one::config/prod_setting::cached_obj'), None)

    def test_empty_pipeline_defaults_and_unported_expression_writes(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            flag = ProjectSetting.get_by_key('autofill_pipeline_code')
            flag.set_value('value', 'true')
            self.assertEqual(SearchType.create('contract/entity').get_defaults(), {})
            self.assertIn('INSERT', SearchType.create('contract/entity').get_statement())
            prefix = ProjectSetting.get_by_key('code_prefix', 'contract/entity')
            prefix.set_value('value', '{@GET(code)}')
            with self.assertRaises(UnsupportedContract):
                SObject('contract/entity').generate_code(12)
            for method, args in ((ProjectSetting.create, ('new', 'value')), (ProjectSetting.add_value_by_key, ('text', 'new'))):
                with self.assertRaises(UnsupportedContract):
                    method(*args)

    def test_imports_inheritance_and_source_signatures(self):
        from pyasm.biz import ProjectSetting as Imported
        from pyasm.biz.prod_setting import ProdSetting as ImportedAlias
        self.assertIs(Imported, ProjectSetting)
        self.assertIs(ImportedAlias, ProdSetting)
        self.assertTrue(issubclass(ProjectSetting, SObject))
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.assertIsInstance(Search.get_by_code(ProjectSetting.SEARCH_TYPE, 'P1'), ProjectSetting)
        source = ast.parse((read_tests.LEGACY / 'src/pyasm/biz/prod_setting.py').read_text(encoding='utf-8'))
        original = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'ProjectSetting')
        for node in original.body:
            if not isinstance(node, ast.FunctionDef) or node.name not in ProjectSetting.__dict__:
                continue
            expected = [argument.arg for argument in node.args.args]
            if expected[0] == 'cls': expected = expected[1:]
            with self.subTest(method=node.name):
                actual = inspect.signature(getattr(ProjectSetting, node.name))
                self.assertEqual(list(actual.parameters), expected)
                defaults = [parameter.default for parameter in actual.parameters.values() if parameter.default is not inspect.Parameter.empty]
                self.assertEqual(defaults, [ast.literal_eval(value) for value in node.args.defaults])
