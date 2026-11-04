"""SQL transaction ownership and SObject journal parity before public writes."""
import ast
from contextlib import redirect_stderr
import inspect
import io
from pathlib import Path
import shutil
import sqlite3
import tempfile

import test_read_parity as read_tests
import test_sobject_state as state_tests
from tools.persistence_probe import run_sql_case, run_journal_case, run_xml_case
from pyasm.command.command import Command
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SObjectUndo, request_context
from pyasm.search.sql import Sql, SqlException, DbResource, DbContainer
from pyasm.search.storage import Store
from pyasm.search.transaction import Transaction
from pyasm.common.lxml_wrapper import Xml, XmlException


def persistence_cases():
    cases = []
    def add(name, method, **options):
        cases.append({"name": name, "method": method, **options})
    change = "UPDATE entity SET name='updated' WHERE code='A'"
    select = "SELECT name FROM entity WHERE code='A'"
    for name, steps in {
        "resource_fields": [["resource"], ["search_value"], ["resource"]],
        "query_fields": [["do_query", 'SELECT id AS "entity.id", name FROM entity WHERE code=\'A\''], ["get_columns_from_description"], ["get_value", "SELECT NULL"], ["get_value", "SELECT 0 WHERE 0"], ["get_int", "SELECT 12"], ["do_update", ""]],
        "autocommit": [["do_update", change], ["get_value", select]],
        "sql_nested": [["start"], ["start"], ["do_update", change], ["commit"], ["get_value", select], ["rollback"]],
        "sql_force_rollback": [["start"], ["do_update", change], ["rollback", True], ["get_value", select]],
        "transaction_commit": [["transaction_start"], ["acquire"], ["do_update", change], ["search_value"], ["transaction_commit"], ["get_value", select]],
        "transaction_rollback": [["transaction_start"], ["acquire"], ["do_update", change], ["search_value"], ["transaction_rollback"], ["get_value", select]],
        "nested_commit": [["transaction_start"], ["acquire"], ["do_update", change], ["transaction_start"], ["acquire"], ["transaction_commit"], ["get_value", select], ["transaction_commit"]],
        "nested_rollback": [["transaction_start"], ["acquire"], ["do_update", change], ["transaction_start"], ["transaction_rollback"], ["get_value", select]],
        "two_databases_commit": [["transaction_start"], ["acquire", "one"], ["do_update", change], ["acquire", "two"], ["do_update", change], ["transaction_commit"], ["get_value", select]],
        "two_databases_rollback": [["transaction_start"], ["acquire", "one"], ["do_update", change], ["acquire", "two"], ["do_update", change], ["transaction_rollback"], ["get_value", select]],
        "savepoint": [["transaction_start"], ["acquire"], ["do_update", change], ["set_savepoint"], ["do_update", "UPDATE entity SET name='discard' WHERE code='A'"], ["rollback_savepoint"], ["get_value", select], ["transaction_commit"]],
        "explicit_savepoint_sql": [["transaction_start"], ["acquire"], ["do_update", change], ["do_update", "SAVEPOINT inner_write"], ["do_update", "UPDATE entity SET name='discard' WHERE code='A'"], ["do_update", "ROLLBACK TO SAVEPOINT inner_write"], ["do_update", "RELEASE SAVEPOINT inner_write"], ["get_value", select], ["transaction_commit"]],
        "command_success": [["command", False], ["get_value", select]],
        "command_rollback": [["command", True], ["get_value", select]],
        "nested_command_success": [["command", False, True], ["get_value", select]],
        "nested_command_rollback": [["command", True, True], ["get_value", select]],
        "constraint_failure": [["transaction_start"], ["acquire"], ["do_update", change], ["do_update", "INSERT INTO entity (id) VALUES (1)", True], ["transaction_rollback"], ["get_value", select]],
    }.items():
        add(name, "sql_transaction", steps=steps)
    for insert in (False, True):
        for column, value in (("name", "Тест & < > \" '"), ("name", None), ("metadata", {"flag": False, "nested": [1, None]}),
                              ("amount", 0), ("active", True), ("active", False), ("active", 1), ("active", "1"),
                              ("timestamp", "2026-10-01 12:00:00+03:00")):
            add(("insert_" if insert else "update_") + column + repr(value), "sobject_journal", insert=insert, updates={column: value})
    add("datetime_update", "sobject_journal", datetimes={"timestamp": "2026-10-01T12:00:00+03:00"})
    add("datetime_insert", "sobject_journal", insert=True, datetimes={"timestamp": "2026-10-01T12:00:00+03:00"})
    add("no_changes", "sobject_journal")
    add("empty_insert", "sobject_journal", insert=True)
    add("no_transaction", "sobject_journal", no_transaction=True, updates={"name": "new"})
    add("code_change", "sobject_journal", search_code="NEW", prev_code="OLD", updates={"code": "NEW", "name": "new"})
    add("id_identity", "sobject_journal", search_code=None, search_id=33, updates={"name": "new"})
    add("rollback_journal", "sobject_journal", updates={"name": "new"}, rollback=True)
    add("unrecorded_commit", "sobject_journal", updates={"name": "new"}, finish=True)
    add("ignored_ticket", "sobject_journal", insert=True, constructor="sobject", search_type="sthpw/ticket", updates={"login": "admin"})
    add("delete", "sobject_journal", delete=True)
    add("delete_no_code", "sobject_journal", delete=True, code=None, data={"id": 11, "name": None})
    for name, xml, steps in (
        ("empty", "<transaction/>", [["nodes", "transaction/*"], ["get_value", "transaction/@missing"]]),
        ("attributes", "<transaction/>", [["append", "sobject", {"from": None, "to": False, "data": {"name": "Тест"}}], ["attributes", "transaction/sobject"], ["get_values", "transaction/sobject/@to"]]),
        ("relative_cache_miss", "<transaction/>", [["nodes", "transaction/*"], ["append", "sobject", {}], ["nodes", "transaction/*"], ["clear_xpath_cache"], ["nodes", "transaction/*"]]),
        ("absolute_cache_keeps_empty_result", "<transaction/>", [["nodes", "/transaction/*"], ["append", "sobject", {}], ["nodes", "/transaction/*"], ["clear_xpath_cache"], ["nodes", "/transaction/*"]]),
        ("strip_whitespace", "<transaction>\n  <sobject name=\"one\"/>\n</transaction>", [["nodes", "/transaction/sobject"]]),
        ("text_and_cdata", "<transaction><column><![CDATA[a&b]]></column></transaction>", [["get_value", "transaction/column"]]),
    ):
        add("xml_" + name, "xml_journal", xml=xml, steps=steps)
    return cases


class PersistenceParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        state_tests.state_fixture(cls.store)
        cls.cases = persistence_cases()

    def assert_case_result(self, case, result, original):
        if case["name"] == "savepoint":
            # Intentional correction: original SqliteImpl had no-op savepoints.
            expected = [dict(step, value="updated") if step.get("value") == "discard" else step for step in original]
            self.assertEqual(result, expected)
            return
        super().assert_case_result(case, result, original)

    def new_result(self, case):
        runner = {"sql_transaction": run_sql_case, "sobject_journal": run_journal_case, "xml_journal": run_xml_case}[case["method"]]
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "probe"
            shutil.copytree(self.store.data_dir, data)
            with request_context(RequestContext(Store(data), "admin", "one")), redirect_stderr(io.StringIO()):
                return runner(case)

    def test_request_exit_rolls_back_and_closes_connections(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "probe"
            shutil.copytree(self.store.data_dir, data)
            store = Store(data)
            with request_context(RequestContext(store, "admin", "one")):
                Transaction.get(create=True)
                sql = Search("contract/entity").get_sql()
                sql.do_update("UPDATE entity SET name='unfinished' WHERE code='A'")
                self.assertEqual(Search.get_by_code("contract/entity", "A").get_value("name"), "unfinished")
            self.assertIsNone(sql.get_connection())
            with store.connection("one") as db:
                self.assertEqual(db.execute("SELECT name FROM entity WHERE code='A'").fetchone()[0], "Первый")

    def test_unported_durable_journal_fails_before_sql_commit(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            class JournalCommand(Command):
                def execute(self):
                    Search("contract/entity").get_sql().do_update("UPDATE entity SET name='pending' WHERE code='A'")
                    node = Transaction.get().create_log_node("sobject")
                    Xml.set_attribute(node, "action", "update")
            with self.assertRaises(UnsupportedContract):
                Command.execute_cmd(JournalCommand())
            self.assertEqual(Search.get_by_code("contract/entity", "A").get_value("name"), "Первый")
            self.assertEqual(Transaction.get().counter, 0)

    def test_borrowed_reads_cannot_commit_or_mutate_sql(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            tx = Transaction.get(create=True)
            sql = Search("contract/entity").get_sql()
            sql.do_update("UPDATE entity SET name='pending' WHERE code='A'")
            with self.store.connection("one") as db:
                for statement in ("UPDATE entity SET name='bad'", "COMMIT", "PRAGMA user_version=123"):
                    with self.subTest(statement=statement), self.assertRaises(sqlite3.DatabaseError):
                        db.execute(statement)
            tx.rollback()
            self.assertEqual(sql.get_value("SELECT name FROM entity WHERE code='A'"), "Первый")

    def test_explicit_other_store_does_not_borrow_current_connections(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "other"
            shutil.copytree(self.store.data_dir, data)
            other = Store(data)
            with other.connection("one", write=True) as db:
                db.execute("UPDATE entity SET name='other store' WHERE code='A'")
            with request_context(RequestContext(self.store, "admin", "one")):
                tx = Transaction.get(create=True)
                Search("contract/entity").get_sql().do_update("UPDATE entity SET name='pending' WHERE code='A'")
                with other.connection("one") as db:
                    self.assertEqual(db.execute("SELECT name FROM entity WHERE code='A'").fetchone()[0], "other store")
                tx.rollback()

    def test_sql_and_xml_boundaries_and_original_signatures(self):
        from tactic.command import PluginCreator, PluginTools, PluginUninstaller, CopyProjectFromTemplateCmd, ProjectTemplateCheckCmd, ProjectTemplateCreatorCmd, ProjectTemplateUpdaterCmd
        from pyasm.web import WidgetSettings
        from pyasm.web import Url
        from pyasm.search import ExceptionLog
        from pyasm.biz import DebugLog
        from tactic.command import Queue, JobTask, Scheduler, SchedulerTask
        from tactic.command.scheduler import SchedulerTaskCmd
        from pyasm.biz import Subscription
        from pyasm.search import TableDataDumper, TableSchemaDumper, SqliteImpl, PostgresImpl, DropTable
        from pyasm.search.sql import Sql as ImportedSql
        from pyasm.search import SObjectUndo as ImportedUndo
        from pyasm.common.lxml_wrapper import Xml as ImportedXml
        self.assertIs(ImportedSql, Sql)
        self.assertIs(ImportedUndo, SObjectUndo)
        self.assertIs(ImportedXml, Xml)
        with request_context(RequestContext(self.store, "admin", "one")):
            sql = Search("contract/entity").get_sql()
            with self.assertRaises(SqlException):
                sql.do_query("UPDATE entity SET name='bad'")
            with self.assertRaises(SqlException):
                sql.do_update("ATTACH DATABASE ':memory:' AS external")
            with self.assertRaises(UnsupportedContract):
                DbResource("../outside")
            with self.assertRaises(UnsupportedContract):
                Xml().get_nodes("//sobject")
            with self.assertRaises(XmlException):
                Xml('<!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>')
            for xml in ('<a xmlns="urn:test"/>',):
                with self.assertRaises(UnsupportedContract):
                    Xml(xml)
            with request_context(RequestContext(self.store, "admin", "two")):
                with self.assertRaises(UnsupportedContract):
                    sql.do_query("SELECT 1")
        with request_context(RequestContext(self.store, "missing", "one")):
            with self.assertRaises(UnsupportedContract):
                Search("contract/entity").get_sql()
        for owner, path in ((Sql, "search/sql.py"), (DbResource, "search/sql.py"), (DbContainer, "search/sql.py"),
                            (Xml, "common/lxml_wrapper.py"), (SObjectUndo, "search/search.py"),
                            (PluginCreator, "../tactic/command/plugin.py"), (PluginTools, "../tactic/command/plugin.py"),
                            (PluginUninstaller, "../tactic/command/plugin.py"), (DropTable, "search/sql.py"),
                            (CopyProjectFromTemplateCmd, "../tactic/command/create_project_cmd.py"),
                            (ProjectTemplateCheckCmd, "../tactic/command/project_template_cmd.py"),
                            (ProjectTemplateCreatorCmd, "../tactic/command/project_template_cmd.py"),
                            (ProjectTemplateUpdaterCmd, "../tactic/command/project_template_cmd.py"),
                            (WidgetSettings, "web/widget.py"), (Url, "web/widget.py"),
                            (ExceptionLog, "search/exception_log.py"), (DebugLog, "biz/debug_log.py"),
                            (Queue, "../tactic/command/queue.py"), (JobTask, "../tactic/command/queue.py"),
                            (Scheduler, "../tactic/command/scheduler.py"), (SchedulerTask, "../tactic/command/scheduler.py"),
                            (SchedulerTaskCmd, "../tactic/command/scheduler.py"), (Subscription, "biz/subscription.py"),
                            (TableDataDumper, "search/sql_dumper.py"), (TableSchemaDumper, "search/sql_dumper.py"),
                            (SqliteImpl, "search/database_impl.py"), (PostgresImpl, "search/database_impl.py")):
            source = ast.parse((read_tests.LEGACY / "src/pyasm" / path).read_text(encoding="utf-8"))
            original = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == owner.__name__)
            for node in original.body:
                if not isinstance(node, ast.FunctionDef) or node.name not in owner.__dict__:
                    continue
                if owner in (SqliteImpl, PostgresImpl) and node.name != 'get_constraints':
                    continue
                args = [arg.arg for arg in node.args.args]
                if args and args[0] == "cls":
                    args = args[1:]
                if node.args.kwarg:
                    args.append(node.args.kwarg.arg)
                with self.subTest(owner=owner.__name__, method=node.name):
                    actual = inspect.signature(getattr(owner, node.name))
                    self.assertEqual(list(actual.parameters), args)
                    defaults = [value.default for value in actual.parameters.values() if value.default is not inspect.Parameter.empty]
                    expected = ["threaded", list(range(1, 8))] if owner is Scheduler and node.name == "add_daily_task" else [ast.literal_eval(value) for value in node.args.defaults]
                    self.assertEqual(defaults, expected)
