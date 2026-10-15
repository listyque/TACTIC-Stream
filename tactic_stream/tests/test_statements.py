"""SQL and pending SObject state compared with the actual original runtime."""
import ast
from contextlib import redirect_stdout
import inspect
import io

import test_read_parity as read_tests
from test_sobject_state import state_fixture
from tools.legacy_read_probe import run_sobject_case
from tools.statement_probe import run_builder_case, run_statement_case
from pyasm.command.command import Command
from pyasm.common.common import Common, Container
from pyasm.search.database_impl import DatabaseImpl, SqliteImpl
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SearchType, SObject, SObjectException, request_context
from pyasm.search.sql import DbResource, DbContainer, Insert, Update, Sql, SqlException
from pyasm.search.transaction import Transaction


def statement_cases():
    cases = []
    def step(method, *args, **kwargs):
        return {"method": method, "args": list(args), "kwargs": kwargs}
    def builder(name, kind, steps, **options):
        cases.append({"name": name, "method": "sql_builder", "kind": kind, "steps": steps, **options})
    def sobject(name, steps=(), **options):
        cases.append({"name": name, "method": "sobject_statement", "steps": list(steps), **options})
    for value in (None, "", "O'Reilly", "Русский\\path", 3, 3.5, True, False,
                  [], ["a", "b's"], (), ("a",), [3], {"a": "b's"}):
        for flags in ({}, {"has_outside_quotes": False}, {"has_outside_quotes": False, "escape": True}, {"unicode_escape": True}):
            builder("quote_" + str(len(cases)), "quote", [step("quote", value, **flags)])
    builder("quote_date", "quote", [{"method": "quote", "date": "2026-10-05"}])
    builder("quote_datetime", "quote", [{"method": "quote", "datetime": "2026-10-05T13:00:00+03:00"}])
    builder("quote_bytes", "quote", [{"method": "quote", "bytes": "61c3a962"}])
    for digits in (None, 0, 1, 10, 19):
        builder("random_" + str(digits), "random", [step("generate_random_key", digits)])
    for args in ((), (0,), (3,), (2, "week"), (2, "weeks", "-"), (1, "hour"), (-2, "day", "-")):
        builder("timestamp_" + str(args), "impl", [step("get_timestamp_now", *args)])
    for column, values in {"timestamp": ("NOW", "CURRENT_TIMESTAMP", "DATETIME('now','2 days')", "NULL", "bad", None, 3),
                           "boolean": ("true", "True", "TRUE", "0", "NULL", None, 1, 2),
                           "integer": (None, "NULL", "12", 12)}.items():
        for value in values:
            builder("process_" + str(len(cases)), "impl", [step("process_value", "column", value, column)])
    builder("process_datetime", "impl", [{"method": "process_value", "args": ["timestamp"],
                                           "datetime": "2026-10-05T13:00:00", "kwargs": {"column_type": "timestamp"}}])
    for method in ("get_column_info", "get_column_types"):
        for table in ("entity", "absent"):
            builder(method + "_" + table, "impl", [{"method": method, "args": [table], "resource_argument": "one"}])
    for kind in ("Insert", "Update"):
        for connector in ("resource", "sql", "none"):
            builder(kind + "_" + connector, kind, [step("set_value", "name", "O'Reilly"), step("set_value", "code", "NEW"),
                    step("set_value", "active", "True"), step("set_value", "amount", 3.5), step("set_value", "timestamp", "NOW"),
                    step("get_statement"), step("get_statement")], connector=connector)
        builder(kind + "_empty", kind, [step("get_statement")])
        builder(kind + "_nulls", kind, [step("set_value", "name", None), step("set_value", "active", None),
                step("set_value", "timestamp", None), step("get_statement")])
        builder(kind + "_retain_flags", kind, [step("set_value", "name", "NULL"), step("set_value", "name", "next"),
                step("set_value", "code", "first", escape_quoted=True), step("set_value", "code", "second"), step("get_statement")])
        builder(kind + "_raw_explicit_type", kind, [step("set_value", "amount", "amount + 1", quoted=False, column_type="integer"),
                step("set_value", "name", "CURRENT_TIMESTAMP", quoted=False), step("get_statement")])
        builder(kind + "_none_quoted_flag", kind, [step("set_value", "name", "next", quoted=None, column_type="varchar"), step("get_statement")])
        builder(kind + "_numeric_escape_flag", kind, [step("set_value", "name", "next", escape_quoted=1), step("get_statement")])
        builder(kind + "_dictionary", kind, [step("set_value", "metadata", {"a": "value"}), step("get_statement")])
        builder(kind + "_bytes", kind, [{"method": "set_value", "args": ["name"], "bytes": "61c3a962"}, step("get_statement")])
        builder(kind + "_data_reference", kind, [step("set_value", "name", "first"),
                {"method": "get_data", "mutate_result": {"name": "mutated"}}, step("get_statement")])
        builder(kind + "_sthpw_string", kind, [step("set_value", "title", "changed"), step("get_statement")], connector="string", table="project")
    for args in (("id", 1), ("name", "O'Reilly"), ("metadata->owner", "owner"), ("active", True), ("name", None),
                 ("id", 1, "integer", "entity", False)):
        builder("filter_" + str(args), "Update", [step("set_value", "name", "next"), step("add_filter", *args), step("get_statement")])
    builder("multiple_filters_source_commas", "Update", [step("set_value", "name", "next"), step("add_filter", "id", 1),
            step("add_where", '"active" = 1'), step("get_statement"), step("remove_filter", '"id" = 1'), step("get_statement")])
    builder("empty_where_ignored", "Update", [step("set_value", "name", "next"), step("add_where", ""), step("get_statement")])
    for constructor in ("create", "sobject", "read"):
        sobject("prepare_empty_" + constructor, [step("get_statement"), step("get_statement")], constructor=constructor)
        sobject("prepare_values_" + constructor, [step("set_value", "code", "NEW"), step("set_value", "name", "O'Reilly"),
                step("set_value", "active", True), step("set_value", "metadata", {"owner": "Тест"}),
                step("get_statement"), step("set_value", "name", "next"), step("get_statement")], constructor=constructor)
    for flags in ({}, {"triggers": False}, {"triggers": 0}, {"triggers": 1}, {"triggers": "none"}, {"triggers": "ingest"}, {"triggers": "invalid"},
                  {"log_transaction": False, "cache": False}):
        sobject("commit_options_" + str(flags), [step("set_value", "name", "next"), step("commit", return_sql=True, **flags)])
    sobject("id_override", [step("set_id", 55), step("set_value", "name", "next"), step("get_statement"), step("get_statement")], constructor="read")
    sobject("force_insert", [step("set_force_insert"), step("get_statement")], constructor="read")
    sobject("string_minus_one", [step("set_value", "id", "-1", temp=True), step("get_statement")], constructor="read")
    sobject("unmarked_update_buffer", [step("set_update_data", {"name": "buffer", "code": "NEW"}), step("get_statement")], constructor="read")
    for value in (None, "NULL", "NOW", "2026-10-05T13:00:00", "2026-10-05T13:00:00+03:00", "invalid date"):
        sobject("timestamp_value_" + str(value), [step("set_value", "timestamp", value, allow_none=True), step("get_statement")], constructor="read")
    sobject("datetime_value", [{"method": "set_value", "args": ["timestamp"], "datetime": "2026-10-05T13:00:00+03:00"}, step("get_statement")])
    sobject("day_value", [step("set_value", "review_day", "2026-10-05T00:00:00+03:00"), step("get_statement")])
    sobject("unknown_column_prepares_sql", [step("set_value", "not_a_column", "next"), step("get_statement")], constructor="read")
    sobject("search_type_object", [step("set_value", "title", "Renamed"), step("get_statement")], constructor="read", search_type="sthpw/search_object", code="contract/entity")
    sobject("without_code_column", [step("get_statement"), step("set_value", "name", "next"), step("get_statement")], search_type="contract/id_entity")
    for name, hooks in {
        "defaults": {"defaults": {"code": "DEFAULT", "name": "from default", "active": False}},
        "default_error": {"defaults_error": True},
        "validate_false": {"valid": False},
        "validate_exception": {"validation_error": True},
        "security_denied": {"allowed": False},
    }.items():
        sobject("hooks_" + name, [step("get_statement")], constructor="sobject", hooks=hooks)
    sobject("hooks_explicit_value_preserved", [step("set_value", "name", "explicit"), step("get_statement")],
            constructor="sobject", hooks={"defaults": {"name": "default", "code": "DEFAULT"}})
    sobject("hooks_update_validation", [step("set_value", "name", "next"), step("get_statement")],
            constructor="sobject", columns=["id", "code", "name"], row=[1, "A", "Первый"], hooks={"validation_error": True})
    cases.append(dict(name='api_insert_metadata', method='command_api_contract', insert_metadata=True))
    return cases


class StatementParity(read_tests.ReadParity):
    def assert_case_result(self, case, native, original):
        if case['method'] == 'sql_builder' and case['kind'] == 'impl':
            step = case['steps'][0]
            if step['method'] == 'process_value' and step['args'] == ['column', None, 'timestamp']:
                self.assertEqual(native, [{'value': {'value': None, 'quoted': False}}])
                self.assertEqual(original, [{'error': 'AttributeError', 'message': "'NoneType' object has no attribute 'startswith'"}])
                return
            if step['method'] == 'process_value' and step['args'] == ['column', 3, 'timestamp']:
                self.assertEqual(native, [{'error': 'TypeError', 'message': 'Expected timestamp string or datetime'}])
                self.assertEqual(original, [{'error': 'AttributeError', 'message': "'int' object has no attribute 'startswith'"}])
                return
        if case['name'] == 'api_insert_metadata':
            metadata = {'title': 'Группа', 'summary': {'messageCount': 0}}
            self.assertEqual(original['inserted'], dict(metadata=metadata, flag=True))
            self.assertEqual(native['inserted'], dict(metadata, flag=True))
            self.assertEqual(original['updated'], dict(metadata=metadata, flag=True, title='Renamed'))
            self.assertEqual(native['updated'], dict(metadata, flag=True, title='Renamed'))
            return
        if case['name'] == 'hooks_default_error':
            # 0.83 intentional fix: source logs broken defaults and proceeds to INSERT.
            self.assertTrue(original[1]['value'].startswith('INSERT INTO "entity"'))
            self.assertEqual(original[0], native[0])
            self.assertEqual(native[1], dict(error='ValueError', message='Invalid defaults', state=native[0]['state']))
            return
        super().assert_case_result(case, native, original)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        state_fixture(cls.store)
        for project in ("one", "two"):
            with cls.store.connection(project, write=True) as db:
                db.execute("ALTER TABLE entity ADD COLUMN review_day timestamp")
        cls.cases = statement_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, "admin", case.get("project", "one"))), redirect_stdout(io.StringIO()):
            if case['method'] == 'command_api_contract':
                from tools.snapshot_probe import run_snapshot_case
                # Keep this existing read-probe harness non-mutating on its fixture.
                result = {}
                class RollbackProbe(Exception):
                    pass
                def execute():
                    result.update(run_snapshot_case(case))
                    raise RollbackProbe()
                command = Command()
                command.execute = execute
                try:
                    Command.execute_cmd(command)
                except RollbackProbe:
                    return result
            return run_builder_case(case) if case["method"] == "sql_builder" else run_statement_case(case, run_sobject_case)

    def test_preparation_inside_command_does_not_write_or_log(self):
        before = {path: path.read_bytes() for path in self.store.data_dir.glob("db/*.db")}
        class Prepare(Command):
            def execute(self):
                obj = SearchType.create("contract/entity")
                obj.set_value("name", "pending")
                statement = obj.get_statement()
                tx = Transaction.get()
                self.assertion = (len(tx.xml.get_root_node()), set(tx.get_databases()), obj.is_insert(), obj.has_updates)
                return statement
        with request_context(RequestContext(self.store, "admin", "one")):
            cmd = Prepare()
            self.assertIn('INSERT INTO "entity"', Command.execute_cmd(cmd))
            self.assertEqual(cmd.assertion, (0, {"sthpw", "one"}, True, True))
            self.assertEqual(Container.get("Search:sql_commit"), None)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_validation_and_security_hooks_precede_statement(self):
        class Validated(SObject):
            def validate(self):
                raise SObjectException("Invalid record")
        class Denied(SObject):
            def handle_commit_security(self):
                return False
        with request_context(RequestContext(self.store, "admin", "one")):
            obj = Validated("contract/entity")
            with self.assertRaisesRegex(SObjectException, "Invalid record"):
                obj.get_statement()
            self.assertIn("timestamp", obj.update_data)
            self.assertIsNone(obj.last_statement)
            from pyasm.common.errors import SecurityException
            with self.assertRaises(SecurityException):
                Denied("contract/entity").get_statement()
        with request_context(RequestContext(self.store, "missing", "one")):
            obj = SearchType.create("contract/entity")
            with self.assertRaises(UnsupportedContract):
                obj.get_statement()
            self.assertEqual(obj.update_data, {})

    def test_unported_defaults_and_persistence_are_explicit(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            for operation in (Insert().execute, Update().execute):
                with self.assertRaises(SqlException):
                    operation()
            obj = SearchType.create("contract/entity")
            obj.set_value("name", "pending")
            statement = obj.get_statement()
            staged = obj.get_data()
            for operation in (obj.commit, obj.delete):
                with self.assertRaises(UnsupportedContract):
                    operation()
            self.assertEqual(obj.get_data(), staged)
            self.assertEqual(obj.get_last_statement(), statement)
            with self.assertRaises(UnsupportedContract):
                DatabaseImpl.get("MySQL")
            from pyasm.biz.pipeline import Pipeline
            with self.assertRaises(UnsupportedContract):
                Pipeline().get_statement()

    def test_native_sqlite_metadata_cache_refreshes_explicitly(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            sql = Search("contract/entity").get_sql()
            impl = sql.get_database_impl()
            resource = sql.get_db_resource()
            columns = impl.get_column_info(resource, "entity")
            self.assertEqual(columns, SearchType.get_column_info("contract/entity"))
            self.assertIs(impl.get_column_info(sql, "entity"), columns)
            # The original SQLite method ignored use_cache=False. The migrated
            # method refreshes metadata so explicitly added columns become visible.
            with self.store.connection('one', write=True) as db:
                db.execute('ALTER TABLE entity ADD COLUMN chat_cache_probe TEXT')
            cached = impl.get_column_info(sql, 'entity')
            self.assertIn('chat_cache_probe', cached)
            refreshed = impl.get_column_info(sql, 'entity', use_cache=False)
            self.assertIsNot(refreshed, cached)
            self.assertIn('chat_cache_probe', refreshed)
            self.assertIs(impl.get_column_info(resource, 'entity'), refreshed)
            self.assertEqual(impl.get_column_info(resource, "absent"), {})
            self.assertEqual(sql.get_timestamp_now(), "CURRENT_TIMESTAMP")

    def test_original_imports_and_signatures(self):
        from pyasm.search import Insert as ImportedInsert, SqliteImpl as ImportedImpl
        self.assertIs(ImportedInsert, Insert)
        self.assertIs(ImportedImpl, SqliteImpl)
        for owner, path in ((Insert, "search/sql.py"), (Update, "search/sql.py"), (SqliteImpl, "search/database_impl.py"),
                            (SObject, "search/search.py"), (Common, "common/common.py")):
            source = ast.parse((read_tests.LEGACY / "src/pyasm" / path).read_text(encoding="utf-8"))
            original = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == owner.__name__)
            for node in original.body:
                if not isinstance(node, ast.FunctionDef) or node.name not in owner.__dict__:
                    continue
                expected = [arg.arg for arg in node.args.args]
                if node.args.vararg:
                    expected.append(node.args.vararg.arg)
                expected += [arg.arg for arg in node.args.kwonlyargs]
                if node.args.kwarg:
                    expected.append(node.args.kwarg.arg)
                if expected and expected[0] == "cls":
                    expected = expected[1:]
                with self.subTest(owner=owner.__name__, method=node.name):
                    actual = inspect.signature(getattr(owner, node.name))
                    self.assertEqual(list(actual.parameters), expected)
                    defaults = [parameter.default for parameter in actual.parameters.values() if parameter.default is not inspect.Parameter.empty]
                    self.assertEqual(defaults, [ast.literal_eval(value) for value in node.args.defaults])
