import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT.parent / "legacy"
sys.path.insert(0, str(ROOT / "src"))

from tactic_stream.server.api import Api, SUPPORTED_METHODS, compatibility_manifest
from pyasm.biz.project import Project
from pyasm.search.search import RequestContext, Search, SearchType, request_context
from pyasm.common.errors import AuthenticationError, TacticException, UnsupportedContract
from pyasm.search.keys import SearchKey
from pyasm.security.authenticator import hash_password, verify_password
from pyasm.search.storage import Store


def fixture(store):
    """Only private, disposable data; same registry and physical table conventions."""
    with store.connection(write=True) as db:
        db.executemany("INSERT INTO project (code,title) VALUES (?,?)", [("one", "One"), ("two", "Two")])
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                   "VALUES ('contract/entity','contract/entity','contract','{project}','entity','pyasm.search.SObject')")
    for project, label in (("one", "Первый"), ("two", "Второй")):
        with closing(sqlite3.connect(store.database_path(project))) as db, db:
            tables = json.loads((ROOT / 'src/tactic_stream/compatibility/project_schema.json').read_text(encoding='utf-8'))
            tables.update(json.loads((ROOT / 'src/tactic_stream/compatibility/config_upgrade.json').read_text(encoding='utf-8'))['tables'])
            for name, statement in tables.items():
                if name != 'spt_process':
                    db.execute(statement)
            for migration in Store._get_upgrade()['columns']:
                if migration['table'] in tables and migration['table'] != 'spt_process':
                    columns = {row[1] for row in db.execute('PRAGMA table_info("%s")' % migration['table'])}
                    if migration['column'] not in columns:
                        db.execute(migration['sql'])
            db.execute('CREATE TABLE spt_process (id integer PRIMARY KEY, code text, process text, pipeline_code text, workflow text, sort_order integer, subcontext_options text, color text, description text, subpipeline_code varchar(256))')
            db.execute("CREATE TABLE entity (id INTEGER PRIMARY KEY, code varchar(256), name text, "
                       "amount integer, s_status varchar(256))")
            db.executemany("INSERT INTO entity VALUES (?,?,?,?,?)", [
                (1, "A", label, 0, None), (2, "B", "O'Reilly", None, None),
                (3, "C", "Archived", 5, "retired"), (4, None, "By id", 7, None),
            ])


class Foundation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))
        self.store.initialize(hash_password("private-test-password"))
        fixture(self.store)
        self.api = Api(self.store)
        self.token = self.api.get_ticket("admin", "private-test-password")
        self.ticket = {"ticket": self.token, "project": "one", "language": "python", "site": None}

    def call(self, name, *args):
        return self.api.dispatch(name, (self.ticket, *args))

    def test_bootstrap_refuses_existing_data_without_modification(self):
        path = self.store.database_path("sthpw")
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.initialize(hash_password("other"))
        self.assertEqual(path.read_bytes(), before)

    def test_deprecated_production_is_excluded_from_bootstrap_and_api(self):
        from tactic_stream.server.api import compatibility_manifest
        manifest = compatibility_manifest()
        self.assertFalse((ROOT / 'src/pyasm/prod').exists())
        import pyasm.biz
        self.assertFalse(hasattr(pyasm.biz, 'SnapshotType'))
        self.assertFalse(hasattr(pyasm.biz, 'FileAccess'))
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module('pyasm.prod')
        for method in ('commit_session', 'get_md5_info'):
            self.assertEqual(manifest['methods'][method]['status'], 'excluded')
            self.assertNotIn(method, manifest['implemented_methods'])
            self.assertFalse(hasattr(self.api, method))
            with self.assertRaisesRegex(UnsupportedContract, 'production API is excluded'):
                self.call(method)
        for project in ('sthpw', 'one', 'two'):
            with self.store.connection(project) as db:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertTrue(tables.isdisjoint({'asset', 'shot', 'texture', 'session_contents', 'snapshot_type', 'file_access'}))
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM search_object WHERE search_type LIKE 'prod/%'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM search_object WHERE search_type='sthpw/snapshot_type'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM search_object WHERE search_type='sthpw/file_access'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT class_name FROM search_object WHERE search_type='config/prod_setting'").fetchone()[0], 'pyasm.biz.ProjectSetting')
        with self.assertRaisesRegex(TacticException, 'Invalid or reserved project namespace'):
            self.call('execute_cmd', 'tactic.command.CreateProjectCmd',
                      {'project_code': 'excluded_prod', 'project_type': 'prod'})
        self.assertFalse(self.store.database_path('excluded_prod').exists())

    def test_admin_authentication_and_real_ticket(self):
        self.assertEqual(self.call("ping"), "OK")
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT login FROM ticket WHERE ticket=?", (self.token,)).fetchone()[0], "admin")
        with self.assertRaises(AuthenticationError):
            self.api.get_ticket("admin", "wrong")

    def test_revocation_is_checked_again_for_existing_ticket(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login (code,login,password) SELECT 'lead','lead',password FROM login WHERE login='admin'")
            db.execute("INSERT INTO login_in_group (login,login_group) VALUES ('lead','admin')")
        token = self.api.get_ticket('lead', 'private-test-password')
        ticket = {'ticket': token, 'project': 'one'}
        self.assertTrue(ast.literal_eval(self.api.dispatch('query', (ticket, 'sthpw/login'))))
        with self.store.connection(write=True) as db:
            db.execute("DELETE FROM login_in_group WHERE login='lead'")
        from pyasm.common.errors import SecurityException
        with self.assertRaises(SecurityException):
            self.api.dispatch('query', (ticket, 'sthpw/login'))
        self.assertEqual(self.api.dispatch('ping', (ticket,)), 'OK')

    def test_invalid_expired_and_retired_tickets(self):
        with self.assertRaises(AuthenticationError):
            self.api.dispatch("ping", ({"ticket": "bad", "project": "one"},))
        with self.store.connection(write=True) as db:
            db.execute("UPDATE ticket SET expiry='2000-01-01T00:00:00+00:00'")
        with self.assertRaises(AuthenticationError):
            self.call("ping")

    def test_query_wire_format_preserves_null_zero_and_unicode(self):
        raw = self.call("query", "contract/entity", [], [], ["id"])
        self.assertIsInstance(raw, str)
        rows = ast.literal_eval(raw)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["amount"], 0)
        self.assertIsNone(rows[1]["amount"])
        self.assertEqual(rows[0]["name"], "Первый")
        self.assertEqual(rows[0]["__search_key__"], "contract/entity?project=one&code=A")
        self.assertEqual(rows[-1]["__search_key__"], "contract/entity?project=one&id=4")
        self.assertNotIn("__search_type__", rows[0])

    def test_project_context_and_explicit_project_override(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.assertEqual(Project.get_by_code('admin').get_database_name(), 'sthpw')
            self.assertEqual(Project.get_by_code('sthpw').get_database_name(), 'sthpw')
            self.assertEqual(Project.get_by_code('one').get_database_name(), 'one')
            project = Project.get_by_code('one')
            project.data['database'] = 'shared_project'
            self.assertEqual(project.get_database_name(), 'shared_project')
        ticket = {**self.ticket, "project": "two"}
        rows = ast.literal_eval(self.api.dispatch("query", (ticket, "contract/entity", [["code", "A"]])))
        self.assertEqual(rows[0]["name"], "Второй")
        rows = ast.literal_eval(self.call("query", "contract/entity?project=two", [["code", "A"]]))
        self.assertEqual(rows[0]["__search_key__"], "contract/entity?project=two&code=A")

    def test_search_type_sql_routing_matches_original_methods(self):
        from pyasm.search import DbContainer
        tree = ast.parse((LEGACY / 'src/pyasm/search/search.py').read_text(encoding='utf-8'))
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'SearchType')
        method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'get_sql_by_search_type')
        namespace = dict(DbContainer=DbContainer)
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<original SearchType SQL>', 'exec'), namespace)
        tree = ast.parse((LEGACY / 'src/pyasm/search/sql.py').read_text(encoding='utf-8'))
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Sql')
        method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'table_exists')
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<original Sql table_exists>', 'exec'), namespace)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.token)
            for kind, database, table in (('sthpw/change_timestamp?project=admin', 'sthpw', 'change_timestamp'),
                                           ('contract/entity', 'one', 'entity'),
                                           ('contract/entity?project=two', 'two', 'entity'),
                                           ('config/widget_config?project=two', 'two', 'spt_widget_config')):
                with self.subTest(search_type=kind):
                    sql = SearchType.get_sql_by_search_type(kind)
                    self.assertIs(sql, namespace['get_sql_by_search_type'](SearchType, kind))
                    self.assertIs(sql, SearchType.get_sql_by_search_type(kind))
                    self.assertEqual(sql.get_database_name(), database)
                    for name in (table, 'missing_contract_table'):
                        self.assertEqual(sql.table_exists(name), namespace['table_exists'](sql, name))
                    self.assertTrue(sql.table_exists(table))
                    self.assertFalse(sql.table_exists('missing_contract_table'))

    def test_query_reuses_metadata_and_refreshes_it_after_write_and_rollback(self):
        from unittest.mock import patch
        from pyasm.command import Command
        from pyasm.search import DbContainer
        with patch.object(self.api.auth, 'bind_security', wraps=self.api.auth.bind_security) as bind:
            self.assertTrue(ast.literal_eval(self.api.dispatch('query', (self.ticket, 'sthpw/search_object'), {'limit': 51})))
            self.assertEqual(bind.call_count, 1)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.token)
            system = DbContainer.get('sthpw')
            entity = Search('contract/entity').get_sql()
            statements = []
            system.get_connection().set_trace_callback(statements.append)
            entity.get_connection().set_trace_callback(statements.append)
            self.store.resolve('contract/entity', 'one')
            SearchType.get_column_info('contract/entity')
            statements.clear()
            for _ in range(10):
                self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('one', 'entity'))
                self.assertIn('amount', SearchType.get_column_info('contract/entity'))
            self.assertEqual(statements, [])
            command = Command()
            command.get_transaction().set_sync(False)
            def execute():
                entity.add_column('entity', 'profile_extra', 'integer')
                self.assertIn('profile_extra', SearchType.get_column_info('contract/entity'))
                Project.set_project('two')
                self.assertNotIn('profile_extra', SearchType.get_column_info('contract/entity'))
                Project.set_project('one')
                system.do_update("UPDATE search_object SET table_name='renamed' WHERE search_type='contract/entity'")
                self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'renamed')
                raise ValueError('late metadata failure')
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'late metadata failure'):
                Command.execute_cmd(command)
            self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('one', 'entity'))
            self.assertNotIn('profile_extra', SearchType.get_column_info('contract/entity'))

    def test_read_connections_are_reused_only_inside_their_request_and_closed_on_failure(self):
        from unittest.mock import patch
        from pyasm.security import Security
        with patch('pyasm.search.storage.sqlite3.connect', wraps=sqlite3.connect) as connect, \
                patch.object(Security, '_find_all_login_groups', autospec=True,
                             side_effect=Security._find_all_login_groups) as discover:
            result = self.api.dispatch('query', ({**self.ticket, 'project': 'admin'}, 'sthpw/search_object'), {'limit': 10})
            self.assertEqual(len(ast.literal_eval(result)), 10)
            # Validation, request reader and native Sql share no sockets across requests.
            self.assertEqual(connect.call_count, 3)
            self.assertEqual(sum(len(call.args) == 1 for call in discover.call_args_list), 1)
        with self.assertRaisesRegex(ValueError, 'request failed'):
            with request_context(RequestContext(self.store, 'admin')):
                with self.store.connection() as first:
                    with self.store.connection() as second:
                        self.assertIs(first, second)
                        with self.assertRaises(sqlite3.OperationalError):
                            second.execute("DELETE FROM search_object")
                with request_context(RequestContext(self.store, 'admin')):
                    with self.store.connection() as nested:
                        self.assertIsNot(first, nested)
                first.execute('SELECT 1')
                with self.assertRaises(sqlite3.ProgrammingError):
                    nested.execute('SELECT 1')
                raise ValueError('request failed')
        with self.assertRaises(sqlite3.ProgrammingError):
            first.execute('SELECT 1')

    def test_fast_class_resolution_is_private_to_each_result_batch(self):
        from unittest.mock import patch
        from pyasm.common import Common
        import pyasm.search
        from pyasm.search import SObject

        class OldSignature(SObject):
            def __init__(self, search_type, columns=None, result=None):
                super().__init__(search_type, columns, result)

        class Replacement(OldSignature):
            pass

        with self.store.connection(write=True) as db:
            db.execute("UPDATE search_object SET class_name='pyasm.search.PerformanceEntity' WHERE search_type='contract/entity'")
        for object_class in (OldSignature, Replacement):
            with patch.object(pyasm.search, 'PerformanceEntity', object_class, create=True):
                with request_context(RequestContext(self.store, 'admin', 'one')):
                    search = Search('contract/entity')
                    search.add_order_by('id asc')
                    original = Common.resolve_class
                    with patch.object(Common, 'resolve_class', side_effect=original) as resolve:
                        objects = search.get_sobjects()
                    self.assertEqual(len(objects), 3)
                    self.assertTrue(all(type(obj) is object_class for obj in objects))
                    # A separate resolution may register the class's triggers;
                    # it must not repeat for each of the three row constructors.
                    self.assertLessEqual(sum(call.args == ('pyasm.search.PerformanceEntity',)
                                             for call in resolve.call_args_list), 2)
                    self.assertEqual(objects[0].get_value('name'), 'Первый')

    def test_gmt_conversion_matches_original_for_naive_and_aware_dates(self):
        from datetime import datetime, timezone, timedelta, date
        from dateutil import parser, tz
        from pyasm.common import SPTDate
        tree = ast.parse((LEGACY / 'src/pyasm/common/spt_date.py').read_text(encoding='utf-8'))
        source_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'SPTDate')
        method = next(node for node in source_class.body if isinstance(node, ast.FunctionDef) and node.name == 'convert')
        module = ast.Module(body=[method], type_ignores=[])
        namespace = dict(datetime=datetime, basestring=str, parser=parser, time=__import__('datetime').time,
                         TZLOCAL=tz.tzlocal(), TZGMT=tz.gettz('GMT'), TZUTC=tz.tzutc())
        exec(compile(ast.fix_missing_locations(module), str(LEGACY / 'src/pyasm/common/spt_date.py'), 'exec'), namespace)
        for value in (datetime(1960, 1, 2), datetime(2026, 10, 6, 12, 3, 4, 123456),
                      datetime(2026, 10, 6, 12, 3, 4, fold=1),
                      datetime(2026, 10, 6, tzinfo=timezone.utc),
                      datetime(2026, 10, 6, tzinfo=timezone(timedelta(hours=3))),
                      date(2026, 10, 6), '2026-10-06 12:03:04.123456', '2026-10-06T12:03:04+03:00',
                      'October 6, 2026 12:03:04', '2026-10-06'):
            for is_gmt in (True, False):
                with self.subTest(value=value, is_gmt=is_gmt):
                    actual, expected = SPTDate.convert(value, is_gmt), namespace['convert'](None, value, is_gmt)
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual.fold, expected.fold)
        with self.assertRaises(ValueError):
            SPTDate.convert('invalid timestamp', True)

    def test_projection_single_sort_paging_and_retirement(self):
        result = ast.literal_eval(self.call("query", "contract/entity", [], ["code"], ["id desc"], False, 1, 1, True))
        self.assertEqual(result, {"code": "B", "__search_key__": "contract/entity?project=one&code=B"})
        self.assertEqual(ast.literal_eval(self.call("query", "contract/entity", [["code", "missing"]], [], [], False, None, None, True)), {})
        self.assertEqual(len(ast.literal_eval(self.call("query", "contract/entity", [], [], [], True))), 4)

    def test_native_select_state_copy_and_trusted_expressions(self):
        from pyasm.search import Select
        from pyasm.common.errors import SecurityException
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.token)
            search = Search('contract/entity')
            self.assertIsInstance(search.get_select(), Select)
            search.order_by = False
            search.add_column('s_status')
            search.get_select().set_quoted_mode('none')
            search.add_column('count(*)', as_column='total')
            search.add_group_by('s_status')
            search.add_having('count(*) > 1')
            copied = search.copy()
            copied.add_having('count(*) > 10')
            self.assertIsNot(copied.select, search.select)
            self.assertIs(copied.order_bys, copied.select.order_bys)
            self.assertEqual(copied.get_sobjects(), [])
            self.assertEqual([(obj.get_value('s_status'), obj.get_value('total')) for obj in search.get_sobjects()], [('', 3)])
            raw = Search('contract/entity')
            raw.get_select().add_order_by('( CASE WHEN amount IS NULL THEN 1 ELSE 0 END )')
            raw.get_select().add_order_by('amount', direction='DESC')
            raw.add_order_by('id')
            self.assertEqual([obj.get_id() for obj in raw.get_sobjects()], [4, 1, 2])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            # Neither a login string nor Sudo bypasses trusted-script SQL ACLs.
            raw = Search('contract/entity')
            raw.get_select().add_order_by('(SELECT password FROM login)')
            with self.assertRaises(SecurityException):
                raw.get_sobjects()
            with self.assertRaises(SecurityException):
                raw.add_where('1 = 1')

    def test_filter_parameters_do_not_execute_sql(self):
        for value in ("A' OR 1=1 --", "';DROP TABLE entity;--"):
            self.assertEqual(ast.literal_eval(self.call("query", "contract/entity", [["code", value]])), [])
        rows = ast.literal_eval(self.call("query", "contract/entity", [["code", ["A", "B"]]]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(ast.literal_eval(self.call("query", "contract/entity", [["code", []]])), [])

    def test_read_operations_do_not_change_database_files(self):
        before = {p: p.read_bytes() for p in self.store.data_dir.glob("db/*.db")}
        self.call("query", "contract/entity", [["amount", ">", 0]])
        self.call("get_column_info", "contract/entity")
        self.call("get_by_search_key", "contract/entity?project=one&code=A")
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_record_by_key_code_id_and_retired_record(self):
        obj = self.call("get_by_search_key", "contract/entity?project=one&amp;code=C")
        self.assertEqual(obj["name"], "Archived")
        self.assertEqual(obj["__search_type__"], "contract/entity?project=one")
        self.assertEqual(self.call("get_by_search_key", "contract/entity|4")["id"], 4)
        self.assertEqual(self.call("get_by_code", "contract/entity", "missing"), {})
        with self.assertRaises(LookupError):
            self.call("get_by_search_key", "contract/entity?project=one&code=missing")

    def test_unsupported_contracts_fail_without_partial_write(self):
        before = self.store.database_path("one").read_bytes()
        with self.assertRaises(UnsupportedContract):
            self.call('execute_transaction', '<transaction><table action="create"/></transaction>')
        with self.assertRaises(UnsupportedContract):
            self.call("query", "contract/entity", ["code='A'"])
        with self.assertRaises(UnsupportedContract):
            self.call('insert', 'contract/entity', {'code': 'NO_WRITE'}, {'unsupported': 'metadata'})
        with self.assertRaises(UnsupportedContract):
            self.call('update', 'contract/entity?project=one&code=A', {'name': 'NO_WRITE'}, {'unsupported': 'metadata'})
        self.assertEqual(self.store.database_path("one").read_bytes(), before)

    def test_scope_does_not_escape_data_directory(self):
        with self.assertRaises(UnsupportedContract):
            self.store.database_path("../legacy/local_data/sthpw")
        with self.assertRaises(AuthenticationError):
            self.api.dispatch("ping", ({**self.ticket, "project": "missing"},))

    def test_request_context_isolated_between_threads(self):
        def read(project):
            with request_context(RequestContext(self.store, "admin", project)):
                self.assertEqual(Project.get().get_code(), project)
                return Search("contract/entity").get_sobject().get_search_key()
        with ThreadPoolExecutor(max_workers=2) as executor:
            keys = list(executor.map(read, ["one", "two"] * 10))
        self.assertTrue(all(f"project={project}&" in key for key, project in zip(keys, ["one", "two"] * 10)))
        with self.assertRaises(LookupError):
            Project.get_project_code()

    def test_registry_columns_match_original_sqlite_contract(self):
        info = self.call("get_column_info", "contract/entity")
        self.assertEqual(info["code"], {"data_type": "varchar", "size": 256, "nullable": True})
        self.assertEqual(info["amount"], {"data_type": "INTEGER", "size": 0, "nullable": True})
        with request_context(RequestContext(self.store, "admin", "one")):
            stype = SearchType.get("contract/entity")
            self.assertEqual(stype.get_table(), "entity")
            self.assertEqual(stype.get_database(), "one")
            with self.assertRaises(UnsupportedContract):
                Search("contract/entity").get_sobject().commit()


class ExtractedContracts(unittest.TestCase):
    def test_password_hashes_match_unchanged_original_hasher(self):
        path = LEGACY / "src/pyasm/security/drupal_password_hasher.py"
        spec = importlib.util.spec_from_file_location("original_password_hasher", path)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        stored = hash_password("кириллица and emoji 🚀")
        self.assertEqual(stored, original.DrupalPasswordHasher().encode("кириллица and emoji 🚀", stored[4:12], stored[3]))
        self.assertTrue(verify_password("кириллица and emoji 🚀", stored))
        self.assertFalse(verify_password("wrong", stored))
        self.assertTrue(verify_password("old", hashlib.md5(b"old").hexdigest()))
        self.assertFalse(verify_password("x", "$S$z12345678" + "x" * 43))

    def test_key_and_type_algorithms_match_original_source(self):
        tree = ast.parse((LEGACY / "src/pyasm/search/search.py").read_text(encoding="utf-8"))
        namespace = {}
        for owner_name, methods in (("SearchKey", {"build_search_key", "_get_data", "extract_search_type",
                                                "extract_project", "extract_code", "extract_id", "extract_base_search_type"}),
                                    ("SearchType", {"build_search_type", "breakup_search_type"})):
            owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner_name)
            owner.bases = []  # Isolate pure algorithms without importing the legacy SObject graph.
            owner.body = [n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name in methods or
                          isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in methods]
            exec(compile(ast.Module(body=[owner], type_ignores=[]), str(LEGACY), "exec"), namespace)
        original_key = namespace["SearchKey"]
        for stype in ("sthpw/login", "contract/entity", "contract/entity?project=two"):
            for column, value in (("code", "A"), ("id", 0), ("code", "кириллица")):
                with self.subTest(stype=stype, column=column):
                    expected = original_key.build_search_key(stype, value, column, "one")
                    self.assertEqual(SearchKey.build_search_key(stype, value, column, "one"), expected)
                    self.assertEqual(SearchKey._get_data(expected), original_key._get_data(expected))
            for method in ("build_search_type", "breakup_search_type"):
                args = (stype, "one") if method == "build_search_type" else (stype,)
                self.assertEqual(getattr(SearchType, method)(*args), getattr(namespace["SearchType"], method)(*args))

    def test_parsed_key_cache_preserves_mutability_errors_and_request_boundaries(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        store = Store(Path(temporary.name))
        search_key = 'contract/entity?project=one&code=A'
        with request_context(RequestContext(store, 'admin', 'one')) as context:
            base, parts = SearchKey._get_data(search_key)
            parts['project'] = 'two'
            self.assertEqual(SearchKey.extract_project(search_key), 'one')
            self.assertEqual(SearchKey.extract_base_search_type(search_key), base)
            for _ in range(2):
                with self.assertRaises(ValueError):
                    SearchKey._get_data('contract/entity?project')
            class CustomKey(str):
                calls = 0
                def split(self, *args, **kwargs):
                    self.calls += 1
                    return super().split(*args, **kwargs)
            custom = CustomKey(search_key)
            SearchKey._get_data(custom)
            calls = custom.calls
            SearchKey._get_data(custom)
            self.assertGreater(custom.calls, calls)
            nested = 'sthpw/message?code=chat|contract/entity?project=one&code=A&thread=main'
            self.assertEqual(SearchKey.extract_code(nested), nested.split('?code=', 1)[1])
            for index in range(300):
                self.assertEqual(SearchKey.extract_id('contract/entity?project=one&id=%s' % index), str(index))
            self.assertLessEqual(len(context.container.info['SearchKey:parsed']), 256)
            with request_context(RequestContext(store, 'admin', 'two')) as other:
                self.assertNotIn('SearchKey:parsed', other.container.info)
                self.assertEqual(SearchKey.extract_project(search_key), 'one')
            self.assertEqual(SearchKey.extract_project(search_key), 'one')

    def test_source_hashes_and_public_signatures_are_preserved(self):
        directory = ROOT / "src/tactic_stream/compatibility"
        sources = json.loads((directory / "source_manifest.json").read_text())
        for name, record in sources["sources"].items():
            root = ROOT.parent.parent / 'TH' if name.startswith('thlib/') else LEGACY
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), record["sha256"])
        from pyasm.common import Xml
        defaults = json.loads((directory / "widget_defaults.json").read_text(encoding='utf-8'))
        for text in defaults.values():
            self.assertNotIn('LicenseManagerWdg', text)
            self.assertFalse(Xml(text).get_nodes('/config//element[@name="license"]'))
        import inspect
        manifest = compatibility_manifest()
        self.assertFalse(manifest["full_api_parity_verified"])
        self.assertEqual(len(manifest['methods']), 129)  # Source's get_ticket_data exposure typo fixed.
        self.assertIn("execute_python_script", manifest["handler_call_candidates"])
        for name in SUPPORTED_METHODS:
            source = ast.parse("def function(" + manifest["methods"][name]["signature"] + "): pass").body[0]
            own = inspect.signature(getattr(Api, name))
            self.assertEqual(list(own.parameters), [n.arg for n in source.args.args])
            self.assertEqual([p.default for p in own.parameters.values() if p.default is not inspect.Parameter.empty],
                             [ast.literal_eval(n) for n in source.args.defaults])


if __name__ == "__main__":
    unittest.main()
