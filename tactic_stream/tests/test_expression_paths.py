"""Original LATEST/CURRENT expressions against owned snapshot/file fixtures."""
import ast
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

import test_read_parity as read_tests
import test_transport
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tools.snapshot_probe import run_snapshot_case


KEY = 'contract/snapshot_entity?project=admin&code=A'
OTHER = 'contract/snapshot_entity?project=admin&code=B'


class ExpressionPaths(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import sys
        sys.path.insert(0, str(read_tests.ROOT / 'tests/scripts'))
        import snapshot_contract
        import expression_contract
        with cls.store.connection(write=True) as db:
            snapshot_contract.install_fixture(db)
            expression_contract.install_file_paths_fixture(db)
        cls.cases = [dict(method='expression_contract', file_paths=True, project='admin',
                          name=name, expression=expression, roots=roots, **options)
                     for name, expression, roots, options in [
                         ('latest', '@LATEST()', [KEY], {}),
                         ('current', '@CURRENT()', [KEY], {}),
                         ('latest_context', '@LATEST(,publish)', [KEY], {}),
                         ('current_context', '@CURRENT(,publish)', [KEY], {}),
                         ('absolute_roots', '@LATEST(contract/snapshot_entity?project=admin,publish)', [], {}),
                         ('filtered_roots', "@CURRENT(contract/snapshot_entity?project=admin['code','A'],publish)", [], {}),
                         ('web', '@LATEST(,publish,web)', [KEY], {}),
                         ('asset_mode', '@CURRENT(,publish,client)', [KEY], {}),
                         ('multiple', '@LATEST()', [KEY, OTHER], {}),
                         ('texture', '@CURRENT(,texture)', [OTHER], {}),
                         ('empty_context', '@LATEST(,missing)', [KEY], {}),
                         ('empty_roots', '@CURRENT()', [], {}),
                         ('missing_roots', "@LATEST(contract/snapshot_entity['code','missing'])", [], {}),
                         ('single', '@CURRENT()', [KEY], {'single': True}),
                         ('single_missing', '@CURRENT(,missing)', [KEY], {'single': True}),
                         ('context_variable', '@LATEST(,$CONTEXT,web)', [KEY], {'vars': {'CONTEXT': 'publish'}}),
                         ('case_insensitive_method', '@current()', [KEY], {}),
                         ('naming', '{@CURRENT(sobject,publish,web)}', [KEY], {'naming': True}),
                         ('quoted_latest', '@LATEST(,$CONTEXT,web)', [KEY], {'vars': {'CONTEXT': "publish/O'Reilly"}, 'quoted_context': True}),
                         ('quoted_current', '@CURRENT(,$CONTEXT,web)', [KEY], {'vars': {'CONTEXT': "publish/O'Reilly"}, 'quoted_context': True}),
                     ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('quoted_context'):
            self.assertEqual(original, {'error': 'SyntaxError'})
            self.assertEqual(result, ['<web>/scenes/A/quoted.ma'])
        else:
            self.assertEqual(result, original)
        if case['name'] in ('latest_context', 'absolute_roots'):
            self.assertEqual(set(result), {'<assets>/scenes/A/' + name for name in ('api.ma', 'scene.ma', 'frame.####.exr')})
        if case['name'] in ('current_context', 'filtered_roots'):
            self.assertEqual(result, ['<assets>/scenes/A/current.ma'])
        if isinstance(result, list):
            self.assertFalse(any('excluded' in path for path in result))

    def test_paths_cache_follows_snapshot_flags_and_rollback(self):
        from pyasm.biz import ExpressionParser
        from pyasm.command import Command
        from pyasm.search import Search
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_search_key(KEY)
            parser = ExpressionParser()
            expression = '@CURRENT(,publish,web)'
            before = parser.eval(expression, parent)
            self.assertEqual(before, ['/assets/scenes/A/current.ma'])
            class Rollback(Exception):
                pass
            def change_flag():
                snapshot = Search.get_by_code('sthpw/snapshot', 'C0')
                snapshot.set_value('is_current', False)
                snapshot.commit()
                self.assertEqual(parser.eval(expression, parent), [])
                raise Rollback()
            cmd = Command()
            cmd.execute = change_flag
            with self.assertRaises(Rollback):
                Command.execute_cmd(cmd)
            self.assertEqual(parser.eval(expression, parent), before)

    def test_api_eval_and_nested_read_permissions(self):
        ticket = {'ticket': self.ticket, 'project': 'admin'}
        expected = self.new_result(self.cases[1])
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            base = Environment.get_asset_dir()
        paths = ast.literal_eval(self.api.dispatch('eval', (ticket, '@CURRENT()', [KEY])))
        self.assertEqual([path.replace(base, '<assets>', 1) for path in paths], expected)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('paths_reader','paths_reader',?)", (hash_password('private-paths-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('paths_readers','paths_readers',?)",
                       ('<rules><rule group="search_type" default="allow"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('paths_reader_group','paths_reader','paths_readers')")
        reader = {'ticket': self.api.get_ticket('paths_reader', 'private-paths-reader'), 'project': 'admin'}
        self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (reader, '@CURRENT()', [KEY]))), paths)
        with self.store.connection(write=True) as db:
            db.execute("UPDATE login_group SET access_rules=? WHERE code='paths_readers'",
                       ('<rules><rule group="search_type" default="allow"/><rule group="search_type" code="contract/snapshot_entity" access="deny"/></rules>',))
        with self.assertRaisesRegex(LookupError, 'SObject does not exist'):
            self.api.dispatch('eval', (reader, '@CURRENT()', [KEY]))
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            for denied in ('sthpw/snapshot', 'sthpw/file'):
                def policy(base):
                    if base == denied:
                        raise SecurityException('Denied nested read')
                with patch('tactic_stream.server.api.check_record_access', side_effect=policy):
                    with self.assertRaisesRegex(SecurityException, 'Denied nested read'):
                        self.api.eval(ticket, '@CURRENT()', [KEY])
                self.assertIsNone(Container.get('Expression:check_record_access'))


class ExpressionPathsTransport(unittest.TestCase):
    def test_unchanged_original_client_eval_and_python(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_expression_paths_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('admin')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            with client.server:
                expected = client.eval('@LATEST(,publish,web)', search_keys=[KEY])
                self.assertEqual(expected, ['/assets//api.ma'])
                body = '''from pyasm.biz import ExpressionParser
from pyasm.search import Search
parent = Search.get_by_search_key('contract/snapshot_entity?project=admin&code=A')
return ExpressionParser().eval('@LATEST(,publish,web)', parent)'''
                self.assertEqual(client.execute_python_script('', dict(code=body))['info'], expected)
                self.assertEqual(client.eval('@CURRENT(,missing)', search_keys=[KEY]), [])
        finally:
            test_transport.Transport.tearDownClass()


@unittest.skipUnless(os.environ.get('STREAM_POSTGRES_HOST'), 'Real isolated PostgreSQL connection required')
class PostgreSQLExpressionPaths(unittest.TestCase):
    def test_native_paths_in_private_database(self):
        import psycopg
        from xml.etree.ElementTree import Element, SubElement, tostring
        from pyasm.common import Config
        from pyasm.search.storage import Store
        from tactic_stream.server.api import Api
        database = 'expression_paths_' + uuid.uuid4().hex
        password_file = os.environ['STREAM_POSTGRES_PASSWORD_FILE']
        values = dict(host=os.environ['STREAM_POSTGRES_HOST'], user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                      port=os.environ.get('STREAM_POSTGRES_PORT', '5432'))
        with psycopg.connect(dbname='postgres', autocommit=True,
                             password=Path(password_file).read_text().strip(), **values) as maintenance:
            try:
                with tempfile.TemporaryDirectory(prefix='expression-paths-') as directory:
                    root = Element('config', version='2')
                    section = SubElement(root, 'database')
                    for name, value in dict(vendor='PostgreSQL', sobject_database=database,
                                            password_file=password_file, **values).items():
                        SubElement(section, name).text = value
                    config = Path(directory) / 'tactic-conf.xml'
                    config.write_bytes(tostring(root))
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(config), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config()
                        store = Store(Path(directory))
                        store.initialize(hash_password('private-paths-check'))
                        with psycopg.connect(dbname=database, password=Path(password_file).read_text().strip(), **values) as db:
                            parent_id = db.execute("SELECT id FROM project WHERE code='admin'").fetchone()[0]
                            for code, current, latest, context in [('PATH_CURRENT', True, False, 'publish'),
                                                                   ('PATH_LATEST', False, True, 'publish'),
                                                                   ('PATH_QUOTED', True, True, "Паблиш/O'Reilly")]:
                                db.execute("INSERT INTO snapshot (code,search_type,search_id,search_code,project_code,context,version,is_current,is_latest,snapshot,login,column_name) VALUES (%s,'sthpw/project',%s,'admin','admin',%s,1,%s,%s,'<snapshot/>','admin','snapshot')",
                                           (code, parent_id, context, current, latest))
                                db.execute("INSERT INTO file (code,file_name,relative_dir,snapshot_code,project_code,type,search_type,search_id,search_code) VALUES (%s,%s,'project/admin',%s,'admin','main','sthpw/project',%s,'admin')",
                                           (code + '_FILE', code + '.ma', code, parent_id))
                        api = Api(store)
                        ticket = {'ticket': api.get_ticket('admin', 'private-paths-check'), 'project': 'admin'}
                        for method, filename in [('CURRENT', 'PATH_CURRENT'), ('LATEST', 'PATH_LATEST')]:
                            result = ast.literal_eval(api.dispatch('eval', (ticket, '@%s(,publish,web)' % method, ['sthpw/project?code=admin'])))
                            self.assertEqual(result, ['/assets/project/admin/' + filename + '.ma'])
                            result = ast.literal_eval(api.dispatch('eval', (ticket, '@%s(,$CONTEXT,web)' % method, ['sthpw/project?code=admin']), {'vars': {'CONTEXT': "Паблиш/O'Reilly"}}))
                            self.assertEqual(result, ['/assets/project/admin/PATH_QUOTED.ma'])
                        result = ast.literal_eval(api.dispatch('eval', (ticket, "@FORMAT(@GET(sthpw/snapshot.version),'-1234.12')")))
                        self.assertEqual(result, ['1.00'] * 3)
                        result = ast.literal_eval(api.dispatch('eval', (ticket, "@FORMAT(@GET(sthpw/snapshot.is_current),'true|false')")))
                        self.assertEqual(result, ['true', 'false', 'true'])
                        result = ast.literal_eval(api.dispatch('eval', (ticket, "@FORMAT(1859,'HH:MM:SS:FF',30)")))
                        self.assertEqual(result, ['00:01:01:29'])
                        result = ast.literal_eval(api.dispatch('eval', (ticket, '@SOBJECT(date)')))
                        self.assertEqual(result[0]['__search_type__'], 'sthpw/virtual')
                        self.assertEqual(result[0]['__search_key__'], 'sthpw/virtual?id=-1')
                        self.assertEqual(set(result[0]), {'id', 'now', 'today', '__search_key__', '__search_type__'})
                        body = '''from pyasm.search import SearchType
from pyasm.biz import ExpressionParser
obj = SearchType.create('sthpw/virtual')
obj.set_value('label', 'temporary')
return {'object': obj.get_sobject_dict(),
        'state': ExpressionParser().eval('@GET(state.label)', state={'label': 'supplied'})}'''
                        result = api.dispatch('execute_python_script', (ticket, '', {'code': body}))['info']
                        self.assertEqual(result['object']['label'], 'temporary')
                        self.assertEqual(result['state'], ['supplied'])
                        body = '''from pyasm.search import Search
from pyasm.biz import SObjectConnection, ExpressionParser
first = Search.get_by_code('sthpw/project', 'admin')
second = Search.get_by_code('sthpw/snapshot', 'PATH_CURRENT')
SObjectConnection.create(first, second, context='pg-connect', direction='dst')
return ExpressionParser().eval("@GET(connect['@CONTEXT','pg-connect'].code)", first)'''
                        result = api.dispatch('execute_python_script', (ticket, '', {'code': body}))['info']
                        self.assertEqual(result, ['PATH_CURRENT'])
                        result = ast.literal_eval(api.dispatch('eval', (ticket, "@SOBJECT(connect['@CONTEXT','pg-connect'])", ['sthpw/project?code=admin'])))
                        self.assertEqual(result[0]['__search_type__'], 'sthpw/snapshot')
                        with self.assertRaisesRegex(ValueError, 'pg connection rollback'):
                            api.dispatch('execute_python_script', (ticket, '', {'code': body.replace("'pg-connect'", "'pg-connect-rollback'").replace(
                                'return ExpressionParser()', "raise ValueError('pg connection rollback')\nreturn ExpressionParser()")}))
                        result = ast.literal_eval(api.dispatch('eval', (ticket, "@GET(connect['@CONTEXT','pg-connect-rollback'].code)", ['sthpw/project?code=admin'])))
                        self.assertEqual(result, [])
                        result = ast.literal_eval(api.dispatch('eval', (ticket, '@GET(site.code)')))
                        self.assertEqual(result, [''])
                        body = '''from pyasm.security import Site
from pyasm.biz import ExpressionParser
return {'code': Site.get().get_value('code'), 'data': Site.get_site_data(''),
        'expression': ExpressionParser().eval('@GET(site.code)')}'''
                        result = api.dispatch('execute_python_script', (ticket, '', {'code': body}))['info']
                        self.assertEqual(result, {'code':'','data':{},'expression':['']})
                        from pyasm.common.errors import UnsupportedContract
                        before = api.dispatch('get_by_code', (ticket, 'sthpw/project', 'admin'))['description']
                        body = '''from pyasm.search import Search
from pyasm.security import Site
obj = Search.get_by_code('sthpw/project', 'admin')
obj.set_value('description', 'temporary site write')
obj.commit()
Site.set_site('tenant')'''
                        with self.assertRaisesRegex(UnsupportedContract, 'multi-site'):
                            api.dispatch('execute_python_script', (ticket, '', {'code': body}))
                        self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/project', 'admin'))['description'], before)
                        filters = [['code', "@GET(sthpw/project['code','admin'].code)"]]
                        result = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/project'), {'filters': filters}))
                        self.assertEqual([row['code'] for row in result], ['admin'])
                        filters = [['code', "@GET(sthpw/snapshot['code','PATH_CURRENT'].code)"]]
                        result = api.dispatch('query_snapshots', (ticket,), {'filters': filters})
                        self.assertEqual([row['code'] for row in result], ['PATH_CURRENT'])
                        result = api.dispatch('get_all_children', (ticket, 'sthpw/project?code=admin', 'sthpw/snapshot'), {'filters': filters})
                        self.assertEqual([row['code'] for row in result], ['PATH_CURRENT'])
                        result = api.dispatch('get_unique_sobject', (ticket, 'sthpw/project'), {'data': {'code': "@GET(sthpw/project['code','admin'].code)"}})
                        self.assertEqual(result['code'], 'admin')
                        write = "@IF(@UPDATE(@SOBJECT(sthpw/project['code','admin']),description,'temporary filter write'),'admin','admin')"
                        with self.assertRaises(UnsupportedContract):
                            api.dispatch('query', (ticket, 'sthpw/project'), {'filters': [['code', write], ['missing', 1]]})
                        self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/project', 'admin'))['description'], before)
                        api.dispatch('query', (ticket, 'sthpw/project'), {'filters': [['code', write]]})
                        self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/project', 'admin'))['description'], 'temporary filter write')
                        with psycopg.connect(dbname=database, password=Path(password_file).read_text().strip(), **values) as db:
                            db.execute("INSERT INTO note(code,timestamp,access,project_code) VALUES ('CLOCK_PAST','1900-01-01','public','admin'),('CLOCK_FUTURE','2999-01-01','public','admin')")
                        for value in ('NOW', 'CURRENT_TIMESTAMP', 'now()', 'CURRENT_TIMESTAMP(3)',
                                      "now() + '0.5 day'::interval", "now() - '1 century'::interval"):
                            body = '''from pyasm.search import Search
search = Search('sthpw/note')
search.add_filters('code',['CLOCK_PAST','CLOCK_FUTURE'])
search.add_filter('timestamp',%r,op='<')
return search.get_sobject_codes()''' % value
                            self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'], ['CLOCK_PAST'])
                        result = ast.literal_eval(api.dispatch('query',(ticket,'sthpw/note'),{'filters':[['code','in','CLOCK_PAST|CLOCK_FUTURE'],['timestamp','>','NOW']]}))
                        self.assertEqual([row['code'] for row in result], ['CLOCK_FUTURE'])
                        before_clock = api.dispatch('get_by_code',(ticket,'sthpw/project','admin'))['description']
                        write = "@IF(@UPDATE(@SOBJECT(sthpw/project['code','admin']),description,'temporary clock write'),'unused','unused')"
                        with self.assertRaises(ValueError):
                            api.dispatch('query',(ticket,'sthpw/note'),{'filters':[['code',write],['timestamp','CURRENT_TIMESTAMP OR 1=1 --']]})
                        self.assertEqual(api.dispatch('get_by_code',(ticket,'sthpw/project','admin'))['description'], before_clock)
                        body = '''from pyasm.search import Search, Select
search = Search('sthpw/note')
sql = search.get_sql()
select = Select()
select.set_database(sql)
select.add_table('note')
select.add_column('code')
select.add_filters('code',['CLOCK_PAST','CLOCK_FUTURE'])
select.add_filter('timestamp','NOW',op='>')
return [row[0] for row in sql.do_query(select.get_statement())]'''
                        self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'], ['CLOCK_FUTURE'])
                        body = '''from pyasm.search import Search
search=Search('sthpw/note')
search.add_filters('code',['CLOCK_PAST','CLOCK_FUTURE'])
select=search.get_select()
select.add_column('code')
select.add_where("'50%' = '50%' AND '%s' = '%s'")
select.add_filter('timestamp','NOW',op='>')
select.set_limit(1)
copy=select.copy()
copy.add_filter('code','CLOCK_PAST')
return {'codes':search.get_sobject_codes(), 'execute':select.execute(),
        'count':search.get_count(), 'select_count':select.execute_count(),
        'copy':copy.execute(), 'same':search.get_statement()==select.get_statement()}'''
                        self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'],
                                         {'codes':['CLOCK_FUTURE'], 'execute':[('CLOCK_FUTURE',)], 'count':1,
                                          'select_count':1, 'copy':[], 'same':True})
                        body = '''from pyasm.search import Search
search=Search('sthpw/note')
select=search.get_select()
select.add_join('project',column='project_code',column2='code',join='INNER')
select.add_filter('code','CLOCK_FUTURE')
select.add_filter('code','admin',table='project')
return search.get_sobject_codes()'''
                        self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'],['CLOCK_FUTURE'])
                        body = '''from pyasm.search import Search
search=Search('sthpw/note')
search.set_null_filter()
return {'rows':search.get_select().execute(),'count':search.get_select().execute_count()}'''
                        self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'],{'rows':[],'count':0})
                        body = '''from pyasm.search import Search
search=Search('sthpw/note')
search.get_select().add_where("'50%' = '50%' AND '%s' = '%s'")
search.get_select().add_filter('code','CLOCK_FUTURE')
ids=search.get_sobject_ids()
return ids == [Search.get_by_code('sthpw/note','CLOCK_FUTURE').get_id()]'''
                        self.assertTrue(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'])
                        body = '''import json
from pyasm.search import Search
search=Search('sthpw/note')
search.add_filter('code','CLOCK_FUTURE')
select=search.get_select()
select.add_column('code',as_column='label')
select.add_where("'50%' = '50%' AND '%s' = '%s' AND $tag$%s$tag$ = '%s'")
select.add_join('project',column='project_code',column2='code',join='INNER')
select.add_filter('code','admin',table='project')
select.set_limit(1)
state=json.loads(select.dumps())
state.pop('join_tables')
receiver=Search('sthpw/note')
receiver.get_select().loads(json.dumps(state))
receiver.add_filter('code','CLOCK_FUTURE')
return {'rows':receiver.get_select().execute(), 'count':receiver.get_select().execute_count(),
        'label':receiver.get_sobjects()[0].get_value('label'),'parameters':receiver.parameters}'''
                        self.assertEqual(api.dispatch('execute_python_script',(ticket,'',{'code':body}))['info'],
                                         {'rows':[('CLOCK_FUTURE',)],'count':1,'label':'CLOCK_FUTURE','parameters':['CLOCK_FUTURE']})
                        before = api.dispatch('get_by_code',(ticket,'sthpw/project','admin'))['description']
                        body = '''import json
from pyasm.search import Search
obj=Search.get_by_code('sthpw/project','admin')
obj.set_value('description','temporary serialized select write')
obj.commit()
select=Search('sthpw/note').get_select()
state=json.loads(select.dumps())
state['schema']='private'
select.loads(json.dumps(state))'''
                        with self.assertRaisesRegex(UnsupportedContract,'cannot replace the Search schema'):
                            api.dispatch('execute_python_script',(ticket,'',{'code':body}))
                        self.assertEqual(api.dispatch('get_by_code',(ticket,'sthpw/project','admin'))['description'], before)
            finally:
                Config.reload_config()
                if maintenance.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
                    maintenance.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(database)))

