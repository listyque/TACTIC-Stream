"""Native SQL builders against the unchanged original runtime and XML-RPC SDK."""
import ast
import importlib.util
import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

import test_read_parity as read_tests
import test_transport
from tools.statement_probe import run_builder_case
from pyasm.command import Command
from pyasm.common.errors import UnsupportedContract
from pyasm.search import DbContainer, DbResource, Insert, Update, Select, Sql, Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.sql import SqlException


def select_cases():
    def step(method, *args, **kwargs):
        return dict(method=method, args=list(args), kwargs=kwargs)
    result = []
    def case(name, *steps, **options):
        result.append(dict(name=name, method='sql_builder', kind='Select',
                           steps=[*steps, step('get_statement')], **options))
    case('all_rows')
    case('projection', step('add_column', 'code'), step('add_column', 'name', as_column='label'),
         step('add_order_by', 'id', 'desc'), step('set_limit', 2), step('set_offset', 1))
    case('literal_null', step('add_filter', 'name', None))
    case('quoted_text', step('add_filter', 'name', "O'Reilly"))
    case('boolean', step('add_filter', 'active', True))
    case('json', step('add_filter', 'metadata->>owner', 'Тест'))
    case('lists', step('add_filters', 'code', ['A', "B's"]))
    case('empty_list', step('add_filters', 'code', []))
    case('postfix', step('add_op', 'begin'), step('add_filter', 'code', 'A'),
         step('add_filter', 'code', 'B'), step('add_op', 'or'), step('add_filter', 'amount', 0, op='>='))
    case('where_removal', step('add_where', 'amount > 2'), step('add_where', 'amount < 5'),
         step('remove_where', 'amount < 5'))
    case('distinct', step('add_column', 'active', distinct=True))
    case('group', step('add_column', 'active'), step('add_column', 'COUNT(*)', quoted=False, as_column='total'),
         step('add_group_by', 'active'), step('add_having', 'COUNT(*) > 0'))
    case('aggregate', step('add_group_aggregate_filter', ['active'], 'amount'))
    case('join', step('add_join', 'child', column='id', column2='entity_id'))
    case('join_fanout_bug', step('add_join', 'child', column='id', column2='entity_id'),
         step('add_join', 'another_child', column='id', column2='entity_id'))
    case('enumeration', step('add_enum_order_by', 'code', ['B', 'A']))
    case('count', step('add_filter', 'active', True), step('set_limit', 1), step('get_count'))
    case('copy_bug', step('add_column', 'code', as_column='label'), step('copy'))
    case('roundtrip_bug', step('add_column', 'code', as_column='label'), dict(method='dumps', roundtrip=True))
    case('explicit_statement_bug', step('set_statement', 'SELECT 7 AS value'))
    case('group_order_bug', step('add_column', 'active'), step('add_group_by', 'active'),
         step('add_order_by', 'active', 'desc'))
    case('enum_quote_bug', step('add_enum_order_by', 'code', ["O'Reilly", 'A']))
    return result


class SqlExecution(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = select_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            return run_builder_case(case)

    def assert_case_result(self, case, native, original):
        name = case['name']
        if name == 'join_fanout_bug':
            self.assertEqual(len(original[-1]['state']['joins']), 1)
            self.assertEqual(len(native[-1]['state']['joins']), 2)
            return
        if name == 'roundtrip_bug':
            self.assertEqual(original[-2]['value'], 'SELECT "entity".* FROM "entity"')
            self.assertEqual(native[-2]['value'], native[-1]['value'])
            return
        if name in ('copy_bug', 'explicit_statement_bug', 'group_order_bug'):
            self.assertTrue(any('error' in row for row in original), original)
            self.assertFalse(any('error' in row for row in native), native)
            if name == 'copy_bug':
                self.assertEqual(native[-2]['value'], native[-1]['value'])
            return
        if name == 'enum_quote_bug':
            self.assertIn("'O'Reilly'", original[-1]['value'])
            self.assertIn("'O''Reilly'", native[-1]['value'])
            return
        self.assertEqual(native, original)

    def test_select_execution_copy_serialization_and_read_scope(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            sql = DbContainer.get(DbResource.get_default('one'))
            select = Select()
            select.set_database(sql)
            select.add_table('entity')
            select.add_column('code', as_column='label')
            select.add_filters('code', ['A', 'B'])
            select.add_order_by('id', 'desc')
            select.set_limit(1)
            self.assertEqual(select.execute(), [('B',)])
            self.assertEqual(sql.do_query(select), [('B',)])
            self.assertEqual(select.execute_count(), 2)
            copied = select.copy()
            self.assertIs(copied.sql, sql)
            copied.add_filter('code', 'A')
            self.assertEqual(copied.execute(), [('A',)])
            self.assertEqual(select.execute(), [('B',)])
            restored = Select()
            restored.set_database(sql)
            restored.loads(select.dumps())
            self.assertEqual(restored.execute(), [('B',)])
            self.assertNotIn('sql', json.loads(select.dumps()))
            distinct = Select()
            distinct.set_database(sql)
            distinct.add_table('entity')
            distinct.add_column('active', distinct=True)
            self.assertEqual(distinct.execute_count(), len(distinct.execute()))
            grouped = Select()
            grouped.set_database(sql)
            grouped.add_table('entity')
            grouped.add_column('active')
            grouped.add_group_by('active')
            grouped.add_having('COUNT(*) >= 1')
            grouped.set_limit(1)
            self.assertGreater(grouped.execute_count(), len(grouped.execute()))
            malicious = Select()
            malicious.set_database(sql)
            malicious.set_statement('DELETE FROM entity')
            with self.assertRaises(SqlException):
                malicious.execute()
            self.assertEqual(select.execute_count(), 2)
            with self.assertRaises(SqlException):
                Select().execute()
            self.assertEqual(Sql.quote("O'Reilly"), "'O''Reilly'")

    def test_search_owned_select_cannot_discard_bound_filters(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            search = Search('contract/entity')
            search.add_filter('code', 'A')
            rows = DbContainer.get(DbResource.get_default('one')).do_query(search.get_select())
            self.assertEqual([row[1] for row in rows], ['A'])
            state = search.get_select().dumps()
            search.get_select().loads(state)
            self.assertEqual(search.get_sobject_codes(), ['A'])
            with self.assertRaises(UnsupportedContract):
                search.get_select().loads('{}')
            search.get_select().add_filter('code', 'B')
            self.assertEqual(search.get_sobjects(), [])
            self.assertEqual(search.get_count(), 0)

    def test_insert_update_execute_ids_and_command_rollback(self):
        class Rollback(Exception):
            pass
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            sql = DbContainer.get(DbResource.get_default('one'))
            before = sql.do_query('SELECT * FROM entity ORDER BY id')
            def write():
                insert = Insert()
                insert.set_database(sql)
                insert.set_table('entity')
                insert.set_value('code', 'SQL_TEST')
                insert.set_value('name', "O'Reilly")
                insert.set_value('amount', 5)
                insert.execute()
                identity = sql.get_int(insert.get_id_statement())
                self.assertGreater(identity, 8)
                update = Update()
                update.set_database(sql)
                update.set_table('entity')
                update.set_value('amount', 12)
                update.add_filter('id', identity)
                update.execute()
                self.assertEqual(sql.do_query(update.get_id_statement()), [(identity,)])
                self.assertEqual(sql.get_int('SELECT amount FROM entity WHERE id=%d' % identity), 12)
                update.set_value('amount', 17)
                sql.do_update(update)
                self.assertEqual(sql.get_row_count(), 1)
                second = Insert()
                second.set_database(sql)
                second.set_table('entity')
                second.set_value('code', 'SQL_TEST_SECOND')
                sql.do_update(second)
                with sql.read_connection():
                    with self.assertRaises(UnsupportedContract):
                        insert.execute()
                raise Rollback()
            cmd = Command()
            cmd.execute = write
            with self.assertRaises(Rollback):
                Command.execute_cmd(cmd)
            self.assertEqual(sql.do_query('SELECT * FROM entity ORDER BY id'), before)
        with request_context(RequestContext(self.store, 'missing', 'one')):
            denied = Insert()
            with self.assertRaises(UnsupportedContract):
                denied.set_database(DbContainer.get(DbResource.get_default('one')))
                denied.set_table('entity')
                denied.set_value('code', 'DENIED')
                denied.execute()

    def test_original_select_signatures(self):
        source = ast.parse((read_tests.LEGACY / 'src/pyasm/search/sql.py').read_text(encoding='utf-8'))
        original = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'Select')
        for method in original.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            with self.subTest(method=method.name):
                signature = inspect.signature(getattr(Select, method.name))
                self.assertEqual(list(signature.parameters), [arg.arg for arg in method.args.args])
                defaults = [p.default for p in signature.parameters.values() if p.default is not inspect.Parameter.empty]
                self.assertEqual(defaults, [ast.literal_eval(v) for v in method.args.defaults])


class SqlExecutionTransport(unittest.TestCase):
    def test_unchanged_original_sdk_script_and_failed_transaction(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_sql_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            self.addCleanup(client.server.__exit__, None, None, None)
            body = '''from pyasm.search import Select, Insert, Update, DbContainer, DbResource
sql = DbContainer.get(DbResource.get_default('one'))
insert = Insert()
insert.set_database(sql)
insert.set_table('entity')
insert.set_value('code', 'SDK_SQL')
insert.set_value('amount', 4)
insert.execute()
identity = sql.get_int(insert.get_id_statement())
update = Update()
update.set_database(sql)
update.set_table('entity')
update.set_value('amount', 13)
update.add_filter('id', identity)
sql.do_update(update)
select = Select()
select.set_database(sql)
select.add_table('entity')
select.add_column('amount')
select.add_filter('id', identity)
return {'rows': sql.do_query(select), 'count': select.execute_count(), 'ids': sql.do_query(update.get_id_statement())}'''
            result = client.execute_python_script('', dict(code=body))
            self.assertEqual(result['info']['rows'], [[13]])
            self.assertEqual(result['info']['count'], 1)
            self.assertEqual(len(client.query('contract/entity', [('code', 'SDK_SQL')])), 1)
            failing = body.replace('SDK_SQL', 'SDK_FAILED').replace("return {'rows':", "raise ValueError('SQL rollback')\nreturn {'rows':")
            with self.assertRaisesRegex(Exception, 'SQL rollback'):
                client.execute_python_script('', dict(code=failing))
            self.assertEqual(client.query('contract/entity', [('code', 'SDK_FAILED')]), [])
        finally:
            test_transport.Transport.tearDownClass()


@unittest.skipUnless(os.environ.get('STREAM_POSTGRES_HOST'), 'Real isolated PostgreSQL connection required')
class PostgreSQLSqlExecution(unittest.TestCase):
    def test_native_builders_schema_sequences_filters_and_rollback(self):
        import psycopg
        from pyasm.search.storage import Store
        from pyasm.security.authenticator import hash_password
        schema = 'sql_builder_' + uuid.uuid4().hex
        database = os.environ.get('STREAM_POSTGRES_DATABASE', 'sthpw')
        values = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                      user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                      port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                      password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        with psycopg.connect(dbname=database, **values) as owner:
            owner.execute(psycopg.sql.SQL('CREATE SCHEMA {}').format(psycopg.sql.Identifier(schema)))
            owner.commit()
            try:
                with tempfile.TemporaryDirectory(prefix='sql-builders-') as directory:
                    store = Store(Path(directory))
                    store.initialize(hash_password('private-sql-builders'))
                    with request_context(RequestContext(store, 'admin')):
                        sql = DbContainer.get(DbResource(database, vendor='PostgreSQL', schema=schema, **values))
                        sql.do_update('CREATE TABLE entity (id serial PRIMARY KEY, code text, name text, active boolean, amount integer)')
                        insert = Insert()
                        insert.set_database(sql)
                        insert.set_table('entity')
                        for code, amount in [('A', 3), ('B', 7), ('C', 11)]:
                            insert.set_value('code', code)
                            insert.set_value('name', 'alpha beta')
                            insert.set_value('amount', amount)
                            insert.set_value('active', True)
                            insert.execute()
                        identity = sql.get_int(insert.get_id_statement())
                        self.assertEqual(identity, 3)
                        select = Select()
                        select.set_database(sql)
                        select.add_table('entity')
                        select.add_column('code', as_column='label')
                        select.add_filter('active', True)
                        select.add_order_by('id', 'desc')
                        select.set_limit(1)
                        self.assertEqual(sql.do_query(select), [('C',)])
                        self.assertEqual(select.execute_count(), 3)
                        select.set_limit(None)
                        select.add_text_search_filter('name', ['alpha', 'beta'])
                        self.assertEqual(select.execute_count(), 3)
                        update = Update()
                        update.set_database(sql)
                        update.set_table('entity')
                        update.set_value('amount', 99)
                        update.add_filter('id', identity)
                        sql.start()
                        update.execute()
                        self.assertEqual(sql.do_query(update.get_id_statement()), [(identity,)])
                        self.assertEqual(sql.get_int('SELECT amount FROM entity WHERE id=3'), 99)
                        sql.rollback()
                        self.assertEqual(sql.get_int('SELECT amount FROM entity WHERE id=3'), 11)
                        grouped = Select()
                        grouped.set_database(sql)
                        grouped.add_table('entity')
                        grouped.add_column('active')
                        grouped.add_group_by('active')
                        grouped.add_having('COUNT(*) > 1')
                        self.assertEqual(grouped.execute_count(), 1)
                        restored = Select()
                        restored.set_database(sql)
                        restored.loads(select.dumps())
                        self.assertEqual(restored.execute(), select.execute())
                        sql.do_update('CREATE TABLE relation_one (entity_id integer)')
                        sql.do_update('CREATE TABLE relation_two (entity_id integer)')
                        sql.do_update('INSERT INTO relation_one VALUES(3)')
                        sql.do_update('INSERT INTO relation_two VALUES(3)')
                        joined = Select()
                        joined.set_database(sql)
                        joined.add_table('entity')
                        joined.add_column('code')
                        joined.add_join('relation_one', column='id', column2='entity_id', join='INNER')
                        joined.add_join('relation_two', column='id', column2='entity_id', join='INNER')
                        self.assertEqual(len(joined.joins), 2)
                        self.assertEqual(joined.execute(), [('C',)])
            finally:
                owner.rollback()
                owner.execute(psycopg.sql.SQL('DROP SCHEMA {} CASCADE').format(psycopg.sql.Identifier(schema)))
                owner.commit()
