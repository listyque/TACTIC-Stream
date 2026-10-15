"""Pipeline graph/default selection against the actual original kernel."""
import ast
from contextlib import redirect_stdout
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest

import test_read_parity as read_tests
from test_settings import settings_fixture
from tools.capture_legacy import pipeline_schema
from tools.pipeline_probe import run_pipeline_case
from pyasm.common.common import Container
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.biz.pipeline import Pipeline, ProjectPipeline, Process, ProcessConnect
from pyasm.search.search import RequestContext, Search, SearchType, SObject, request_context
from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store


GRAPH = '''<pipeline>
  <process name="start" group="artists" color="#5577aa" label="Начало" completion="50" handler="handler.Start">
    <action event="done" scope="dependent" class="handler.Done"><flag>false</flag><empty/></action>
    <action event="done" scope="all" class="handler.All"><flag>true</flag></action>
  </process>
  <process name="build" type="auto" task_pipeline="custom"/>
  <process name="review" type="approval"/>
  <process name="end" type="manual"/>
  <connect from="start" to="build" name="main" title="Связь"/>
  <connect from="build" to="review" context="image" from_attr="preview" to_attr="review"/>
  <connect from="review" to="end"/>
  <connect from="*" to="end" context="wildcard"/>
  <connect from="end" to="end" context="loop"/>
  <connect from="GRAPH/end" to="end" context="full-loop"/>
  <connect from="start" to="external" to_pipeline="REMOTE" context="remote"/>
</pipeline>'''


def pipeline_fixture(store):
    settings_fixture(store)
    with store.connection(write=True) as db:
        db.execute("INSERT OR IGNORE INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/pipeline','config/pipeline','config','{project}','spt_pipeline','pyasm.biz.ProjectPipeline')")
        rows = [(1, 'GRAPH', GRAPH, 'contract/child', 'one', None),
                (2, 'REMOTE', '<pipeline><process name="external" type="approval"/></pipeline>', 'contract/child', 'two', None),
                (3, 'A_SHARED', '<pipeline/>', 'contract/entity', None, None),
                (4, 'B_ONE', '<pipeline/>', 'contract/entity', 'one', None),
                (5, 'C_TWO', '<pipeline/>', 'contract/entity', 'two', None),
                (6, 'D_MULTI', '<pipeline/>', 'contract/entity', '||one||two||', None),
                (7, 'E_EMPTY', '<pipeline/>', 'contract/entity', '', None),
                (8, 'Z_RETIRED', '<pipeline/>', 'contract/entity', 'one', 'retired'),
                (9, 'default', '<pipeline><process name="default_process"/></pipeline>', '', None, None),
                (10, 'BLANK', '', 'contract/child', 'one', None)]
        db.executemany('INSERT INTO pipeline (code,pipeline,search_type,project_code,s_status) VALUES (?,?,?,?,?)', [row[1:] for row in rows])
    for project in ('one', 'two'):
        with store.connection(project, write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
            if 'project_code' not in {row[1] for row in db.execute('PRAGMA table_info(spt_pipeline)')}:
                db.execute('ALTER TABLE spt_pipeline ADD COLUMN project_code text')
            db.execute("UPDATE prod_setting SET value='true' WHERE \"key\"='autofill_pipeline_code'")
            db.execute("UPDATE entity SET pipeline_code='GRAPH' WHERE code='B'")
            db.execute('INSERT INTO spt_pipeline (id,code,pipeline,search_type,project_code,s_status) VALUES (1,?,?,?,?,NULL)', ('REMOTE', '<pipeline><process name="external" type="manual" label="' + project + '"/></pipeline>', 'contract/child', project))
            db.executemany('INSERT INTO spt_process (id,code,process,pipeline_code,workflow) VALUES (?,?,?,?,?)', [
                (1, 'START', 'start', 'GRAPH', '{"version":2,"properties":{"task_pipeline":"task-v2"},"node_type":"manual"}'),
                (2, 'REVIEW', 'review', 'GRAPH', '{"version":1,"task_pipeline":"task-v1","node_type":"dependency"}'),
            ])


def pipeline_cases():
    result = []
    def step(method, *args, **options):
        return {'method': method, 'args': list(args), **options}
    def add(name, steps, **options):
        result.append({'name': name, 'method': 'pipeline_reads', 'steps': steps, **options})
    for method, arguments in (
        ('get_name', [(), (True,)]), ('get_process', [('start',), ('missing',)]),
        ('get_process_names', [(), (True,), (False, 'action'), (True, 'manual,approval'), (False, None, 'manual'), (True, None, 'manual')]),
        ('get_processes', [(), (True,), (False, 'action'), (False, ['manual', 'approval'])]),
        ('get_process_attrs', [('start',), ('missing',)]), ('get_index', [('start',), ('end',), ('missing',)]),
        ('get_dependent_processes', [('start', 'end'), ('missing', 'end')]),
        ('get_pipeline_xml', [()]), ('to_string', [()]), ('get_all_contexts', [()]),
    ):
        for args in arguments:
            add(method + repr(args), [step(method, *args)])
    for process in ('start', 'build', 'review', 'end', 'missing'):
        for method in ('get_input_process_names', 'get_output_process_names', 'get_input_connects', 'get_output_connects',
                       'get_input_streams', 'get_output_streams', 'get_input_contexts', 'get_output_contexts',
                       'get_forward_connects', 'get_backward_connects'):
            add(method + '_' + process, [step(method, process)])
    add('port_type_and_context_quirks', [step('get_input_process_names', 'end', kwargs={'type':'approval', 'to_attr':'input'}),
        step('get_output_process_names', 'start', kwargs={'type':'approval'}),
        step('get_output_process_names', 'build', kwargs={'from_attr':'output'}),
        step('get_output_process_names', 'build', kwargs={'from_attr':'preview'}),
        step('get_input_contexts', 'end', kwargs={'show_process':True}), step('get_output_contexts', 'start', kwargs={'show_process':True})])
    for method, args in (('get_attributes', ()), ('get_full_name', ()), ('get_type', ()), ('get_group', ()),
        ('get_color', ()), ('get_label', ()), ('get_completion', ()), ('get_handler', ()), ('get_node', ()),
        ('get_action_nodes', ()), ('get_action_nodes', (None,)), ('get_action_node', ('done',)),
        ('get_action_handler', ('done',)), ('get_action_options', ('done',)), ('get_action_options', ('missing',))):
        add('process_' + method + repr(args), [step(method, *args, process='start')])
    add('mutable_process', [step('set_attribute', 'label', 'Новая метка', process='start'), step('get_process_attrs', 'start'),
        step('set_sub_pipeline_process', True, process='start'), step('get_process_names', True)])
    add('task_pipeline_config_and_xml', [step('get_task_pipeline', process=name) for name in ('start','build','review','end')]
        + [step('get_task_pipeline', False, process='end')])
    add('connect_metadata', [step(method, connect=0) for method in ('get_from','get_to','get_name','get_title','get_from_attr',
        'get_to_attr','get_to_pipeline','get_from_pipeline','get_to_expression','get_from_expression','get_context')]
        + [step('get_context', True, connect=0), step('get_context', connect=5)])
    add('recursive_filter_cache_quirk', [step('get_processes', True, 'action'), step('get_processes', True), step('get_process_names', True)])
    for project in ('one','two'):
        add('code_lookup_'+project, [step('get_by_code', code, **{'class':True}) for code in ('REMOTE','GRAPH','missing','',None,'BLANK')], project=project)
        add('type_lookup_'+project, [step('get_by_search_type', stype, **{'class':True}) for stype in ('contract/entity','contract/entity?project=two','missing/type','')], project=project)
    for project_code in (None, '', 'one', 'two', ['one','two'], ['two'], []):
        for show_unset in (True,False):
            add('project_filter'+repr((project_code,show_unset)), [step('project_filter', project_code, show_unset)])
    add('entity_defaults_and_statement', [step('get_defaults', entity=True), step('set_value', 'amount', 42, entity=True),
        step('get_statement', entity=True), step('set_autofill','false'), step('get_defaults', entity=True)])
    add('existing_entity_pipeline', [step('get_defaults', entity=True), step('set_defaults', entity=True), step('get_by_sobject')], entity_code='B')
    add('lookup_cache', [step('get_by_search_type','contract/entity', **{'class':True}), step('get_by_code','A_SHARED', **{'class':True}), step('get_by_code','A_SHARED', **{'class':True})])
    add('default_fallback_read', [step('get_by_code','missing', kwargs={'allow_default':True}, **{'class':True}), step('get_default', **{'class':True})])
    add('xml_cache_and_reset', [step('set_pipeline','<pipeline><process name="changed"/></pipeline>'),
        step('reload'), step('set_pipeline','<pipeline><process name="ignored"/></pipeline>'), step('get_process_names')])
    add('malformed_xml_empty_fallback', [step('set_pipeline','<broken', kwargs={'cache':False}), step('get_process_names'), step('to_string')])
    add('pipeline_update_sql', [step('set_value','color','#ff5500'), step('get_statement')])
    add('new_entity_insert_defaults', [step('set_value','code','NEW',entity=True),
        step('set_value','name','Новый объект',entity=True), step('get_statement',entity=True)], entity_new=True)
    add('search_type_missing_and_no_exception', [step('get','missing/type', search_type_class=True),
        step('get','missing/type',kwargs={'no_exception':True}, search_type_class=True),
        step('get','missing/type?project=one',kwargs={'no_exception':True}, search_type_class=True)])
    for statuses, options in ((None,{}), (['open','','done'],{}), (['open','done'],{'process_types':['manual','approval']}),
        (['open','done'],{'process_types':['manual','approval'],'process_xpos':[0,20],'process_ypos':[0,30]})):
        add('create_xml'+repr((statuses,options)), [step('create_pipeline_xml', statuses, kwargs=options, **{'class':True})])
    return result


class PipelineParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        pipeline_fixture(cls.store)
        cls.cases = pipeline_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project','one'))):
            with redirect_stdout(io.StringIO()):
                return run_pipeline_case(case)

    def assert_case_result(self, case, result, original):
        if case['name'] == "get_process_names(False, None, 'manual')":
            # Source's non-recursive exclude fails to normalize implicit manual nodes.
            self.assertEqual(original[0]['value'], ['start', 'build', 'review', 'end'])
            self.assertEqual(result[0]['value'], ['build', 'review'])
            original[0]['value'] = result[0]['value']
        super().assert_case_result(case, result, original)

    def test_original_imports_classes_and_signatures(self):
        from pyasm.biz import Pipeline as Imported
        from pyasm.biz.pipeline import ProjectPipeline as ImportedProject
        self.assertIs(Imported, Pipeline)
        self.assertIs(ImportedProject, ProjectPipeline)
        self.assertTrue(issubclass(Pipeline,SObject))
        original = ast.parse((read_tests.LEGACY/'src/pyasm/biz/pipeline.py').read_text(encoding='utf-8'))
        for cls in (Pipeline, ProjectPipeline, Process, ProcessConnect):
            owner = next(node for node in original.body if isinstance(node,ast.ClassDef) and node.name==cls.__name__)
            methods = {node.name:node for node in owner.body if isinstance(node,ast.FunctionDef)}
            for name in cls.__dict__:
                if name not in methods: continue
                node = methods[name]
                expected = [arg.arg for arg in node.args.args]
                if expected and expected[0]=='cls': expected=expected[1:]
                actual = inspect.signature(getattr(cls,name))
                self.assertEqual(list(actual.parameters),expected,(cls.__name__,name))
                self.assertEqual([p.default for p in actual.parameters.values() if p.default is not inspect.Parameter.empty],
                                 [ast.literal_eval(value) for value in node.args.defaults])

    def test_unported_graphs_templates_and_writes_fail_before_changes(self):
        before = {path:path.read_bytes() for path in self.store.data_dir.glob('db/*.db')}
        with request_context(RequestContext(self.store,'admin','one')):
            obj = Pipeline.get_by_code('GRAPH')
            names = obj.get_process_names()
            for xml in ('<pipeline><pipeline name="GRAPH"/></pipeline>', '<!DOCTYPE pipeline><pipeline/>'):
                with self.assertRaises(UnsupportedContract): obj.set_pipeline(xml, cache=False)
                self.assertEqual(obj.get_process_names(),names)
            for method,args in ((Pipeline.create,('new','desc','contract/entity')), (Pipeline().get_statement,()),
                (obj.commit,()), (obj.delete,()), (obj.save_version,())):
                with self.assertRaises((UnsupportedContract, SecurityException)): method(*args)
            for code in ('task','approval','dependency','progress','milestone','snapshot'):
                pipeline = Pipeline.get_by_code(code)
                self.assertTrue(pipeline.get_process_names())
                self.assertEqual(pipeline.get_code(), code)
        self.assertEqual({path:path.read_bytes() for path in before},before)

    def test_project_cache_is_isolated_and_missing_config_is_optional(self):
        with request_context(RequestContext(self.store,'admin','one')):
            one = Pipeline.get_by_code('REMOTE')
            self.assertIsInstance(one,ProjectPipeline)
            self.assertEqual(one.get_process_attrs('external')['label'],'one')
        with request_context(RequestContext(self.store,'admin','two')):
            self.assertEqual(Pipeline.get_by_code('REMOTE').get_process_attrs('external')['label'],'two')
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-empty-config'))
            with request_context(RequestContext(store,'admin')):
                self.assertIsNone(Pipeline.get_by_code('missing'))
                with self.assertRaises(UnsupportedContract): Pipeline.get_by_code('missing',allow_default=True)
            with store.connection(write=True) as db:
                db.execute("UPDATE search_object SET table_name='missing_table' WHERE search_type='config/pipeline'")
            with request_context(RequestContext(store,'admin')):
                with self.assertRaisesRegex(LookupError,'Registered table does not exist'):
                    Pipeline.get_by_code('missing')


class PipelineUpgrade(unittest.TestCase):
    def test_original_metadata_upgrade_is_atomic_and_repeatable(self):
        metadata=json.loads((read_tests.ROOT/'src/tactic_stream/compatibility/pipeline_upgrade.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata,pipeline_schema(read_tests.LEGACY))
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-pipeline-upgrade'))
            with store.connection(write=True) as db:
                db.execute('DROP TABLE pipeline')
                db.execute("DELETE FROM search_object WHERE search_type='sthpw/pipeline'")
                account=dict(db.execute('SELECT * FROM login').fetchone())
            self.assertTrue(store.upgrade())
            with store.connection() as db:
                self.assertEqual(dict(db.execute('SELECT * FROM login').fetchone()),account)
                self.assertEqual(db.execute('SELECT count(*) FROM pipeline').fetchone()[0],0)
                for column in metadata['columns']:
                    self.assertIn(column['column'], {row['name'] for row in db.execute('PRAGMA table_info(pipeline)')})
            before=store.database_path('sthpw').read_bytes()
            self.assertFalse(store.upgrade())
            self.assertEqual(store.database_path('sthpw').read_bytes(),before)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE pipeline')
                db.execute("UPDATE search_object SET class_name='custom.Pipeline' WHERE search_type='sthpw/pipeline'")
            before=store.database_path('sthpw').read_bytes()
            with self.assertRaises(ValueError): store.upgrade()
            self.assertEqual(store.database_path('sthpw').read_bytes(),before)
