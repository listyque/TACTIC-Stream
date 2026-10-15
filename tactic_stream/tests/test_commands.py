"""Compare command hooks, nesting and trigger queues to the unmodified kernel."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
import ast
import inspect
import io
import sqlite3
from threading import Barrier

import test_read_parity as read_tests
from tools.command_probe import run_command_case, run_transaction_case, run_trigger_state_case
from pyasm.command.command import Command, CommandException
from pyasm.common.common import Base, Container, SecurityException
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, request_context
from pyasm.search.transaction import Transaction
from pyasm.command.trigger import Trigger


def lifecycle_cases():
    cases = []

    def add(name, method="command_lifecycle", **data):
        cases.append({"name": name, "method": method, **data})

    for value in (None, False, 0, "", [], {}, {"value": 12}):
        add("return_" + repr(value), commands=[{"result": value, "info": {"before": True}}])
    add("execute_transaction_returns_none", commands=[{"entry": "execute_transaction", "result": {"value": 12}}])
    add("batch_ignores_check", commands=[{"check": False}])
    add("security_rejection", commands=[{"security": False}])
    for phase in ("security", "start", "preprocess", "data", "execute", "postprocess", "commit", "rollback", "notify"):
        add("fail_" + phase, commands=[{"fail": phase}])
    for phase in ("preprocess", "data", "execute", "postprocess"):
        for error in ("exit", "interrupt"):
            add(error + "_" + phase, commands=[{"fail": phase, "error": error}])
    add("nested_success", commands=[{"children": [{"label": "first", "result": {"child": 1}}, {"label": "second"}], "result": {"parent": 2}}])
    add("three_levels", commands=[{"children": [{"label": "child", "children": [{"label": "grandchild"}]}]}])
    for phase in ("security", "start", "preprocess", "data", "execute", "postprocess"):
        add("nested_error_" + phase, commands=[{"children": [{"label": "child", "fail": phase}]}])
    add("nested_exit", commands=[{"children": [{"label": "child", "fail": "execute", "error": "exit"}]}])
    add("nested_interrupt", commands=[{"children": [{"label": "child", "fail": "execute", "error": "interrupt"}]}])
    add("caught_child_error_original_stack", commands=[{"catch_child": True, "children": [{"label": "child", "fail": "execute"}]}])
    add("two_commands_same_request", commands=[{"label": "first"}, {"label": "second"}])
    add("reuse_cached_transaction_original_error", commands=[{"label": "first"}, {"reuse_previous": True}])
    add("explicit_unstarted_transaction", commands=[{"explicit_transaction": True}])
    add("explicit_started_transaction", commands=[{"explicit_transaction": True, "start_transaction": True}])
    for triggers, name in (([{"label": "one", "result": False}], "one"),
                           ([{"label": "one"}, {"label": "duplicate"}], "duplicate"),
                           ([{"label": "one", "input": {"value": 1}}, {"label": "two", "input": {"value": 2}}], "different_inputs"),
                           ([{"label": "one", "event": "first"}, {"label": "two", "event": "second"}], "different_events"),
                           ([{"label": "one", "recursive": True}], "recursive"),
                           ([{"label": "broken", "fail": True}, {"label": "next", "input": {"value": 2}}], "error_continues")):
        add("trigger_" + name, commands=[{"triggers": triggers}])
    add("false_call_trigger_still_dispatches", commands=[{"call_trigger": False, "triggers": [{"label": "one"}]}])
    add("failed_caller_keeps_trigger_queue", commands=[{"fail": "postprocess", "triggers": [{"label": "one"}]}])
    add("nested_trigger_runs_after_parent_commit", commands=[{"children": [{"label": "child", "triggers": [{"label": "one"}]}]}])
    for name, steps in {
        "inactive_register": [["register", "first"], ["register_database", "second"]],
        "commit_without_start": [["commit"]], "rollback_without_start": [["rollback"]],
        "abort_without_start": [["abort"]],
        "nested_commit": [["start"], ["register", "first"], ["start"], ["register", "second"], ["commit"], ["commit"]],
        "nested_rollback": [["start"], ["register", "first"], ["start"], ["register", "second"], ["rollback"]],
        "nested_abort": [["start"], ["start"], ["register", "first"], ["abort"]],
        "commit_all": [["start"], ["start"], ["register", "first"], ["commit_all"]],
        "empty_commit_all": [["commit_all"]],
        "database_dedup": [["start"], ["register_database", "first"], ["register_database", "first"], ["register_database", "second"], ["commit"]],
        "participant_duplicates": [["start"], ["register", "first"], ["register", "first"], ["rollback"]],
        "metadata_reset": [["set_description", "old"], ["set_title", "title"], ["set_command_class", "class"],
                            ["set_record", False], ["set_sync", False], ["start"], ["add_description", "one"],
                            ["add_description", "two"], ["start"], ["add_description", "three"], ["commit"], ["commit"]],
        "get_no_create": [["get"]], "get_creates_and_reuses": [["get", True], ["get", True], ["commit"], ["commit"], ["get", True]],
        "force_creates_stack": [["get", True], ["get", False, True], ["get"], ["commit"], ["get", True]],
        "reuse_after_rollback": [["get", True], ["register", "first"], ["rollback"], ["get", True], ["commit"]],
        "commit_failure": [["start"], ["register", "first"], ["register", "second"], ["commit"], ["rollback"]],
        "rollback_failure": [["start"], ["register", "first"], ["register", "second"], ["rollback"]],
    }.items():
        add("transaction_" + name, "transaction_lifecycle", steps=steps,
            fail_commit="first" if name == "commit_failure" else None,
            fail_rollback="first" if name == "rollback_failure" else None)
    for data in ("", '{"value":0}', '[1,2]', "null", "invalid"):
        add("trigger_state_" + data, "trigger_state", operation="state", data=data)
    definitions = [{"event": "changed", "label": "plain"}, {"event": "changed", "process": "model", "label": "process"},
                   {"event": "changed", "process": "ignored", "listen_process": "model", "label": "listen"},
                   {"event": "other", "label": "other"}, {"event": "changed", "startup": True, "label": "startup"},
                   {"event": "changed", "integral": True, "label": "integral"},
                   {"event": "changed", "integral": True, "startup": True, "label": "startup_integral"}]
    for process in (None, "model", "ignored", "missing"):
        add("registry_" + str(process), "trigger_state", definitions=definitions, process=process, new_request=True)
    return cases


class CommandParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = lifecycle_cases()

    def new_result(self, case):
        runners = {"command_lifecycle": run_command_case, "transaction_lifecycle": run_transaction_case,
                   "trigger_state": run_trigger_state_case}
        with request_context(RequestContext(self.store, "admin", "one")), redirect_stderr(io.StringIO()):
            return runners[case["method"]](case)

    def assert_case_result(self, case, result, original):
        if case['name'] in ('nested_error_preprocess', 'nested_error_data',
                            'nested_error_execute', 'nested_error_postprocess'):
            # Source pops only the child, leaving a failed root on the stack.
            self.assertEqual(original['top'], ['parent'])
            self.assertEqual(result['top'], [])
            original['top'] = []
        if case['name'].startswith('registry_'):
            # The source registered startup static triggers twice in this request.
            startup = dict(event='changed', label='startup', startup=True)
            self.assertEqual(original['static'].count(startup), 2)
            self.assertEqual(result['static'].count(startup), 1)
            original['static'].remove(startup)
            if original['matching'].count(startup):
                self.assertEqual(original['matching'].count(startup), 2)
                self.assertEqual(result['matching'].count(startup), 1)
                original['matching'].remove(startup)
        elif case['name'].startswith('interrupt_'):
            self.assertEqual(original['events'][-1], ['parent', 'commit', 0, ['parent']])
            self.assertEqual(result['events'][-1], ['parent', 'rollback', 1, ['parent']])
            original['events'][-1] = ['parent', 'rollback', 1, ['parent']]
        elif case['name'] == 'nested_interrupt':
            self.assertEqual(original['events'][-2:], [['parent', 'commit', 0, []], ['child', 'commit', 0, []]])
            expected = [[name, 'rollback', 2, ['parent', 'child']] for name in ('parent', 'child')]
            self.assertEqual(result['events'][-2:], expected)
            original['events'][-2:] = expected
        elif case['name'] == 'fail_commit':
            self.assertEqual(original['top'], ['parent'])
            self.assertEqual(result['top'], [])
            original['top'] = []
            self.assertEqual(original['events'][-1], ['parent', 'commit', 0, ['parent']])
            original['events'].append(['parent', 'rollback', 1, ['parent']])
            self.assertEqual(original['transaction']['participants'], ['parent'])
            original['transaction'].update(description='', participants=[])
        elif case['name'] == 'transaction_commit_failure':
            self.assertEqual(original['events'], [['first', 'start'], ['second', 'start'], ['first', 'commit']])
            original['events'].extend([['first', 'rollback'], ['second', 'rollback']])
            for output in original['outputs'][3:]:
                self.assertEqual(output['state']['participants'], ['first', 'second'])
                output['state']['participants'] = []
        elif case['name'] == 'fail_rollback':
            self.assertEqual(original['outputs'], [{'error': 'ValueError', 'message': 'failed parent:rollback'}])
            self.assertEqual(result['outputs'], [{'error': 'TransactionException', 'message': 'Rollback cleanup failed: failed parent:rollback'}])
            original['outputs'] = result['outputs']
        elif case['name'] == 'transaction_rollback_failure':
            self.assertEqual(original['events'], [['first', 'start'], ['second', 'start'], ['first', 'rollback']])
            self.assertEqual(result['events'], original['events'] + [['second', 'rollback']])
            original['events'] = result['events']
            self.assertEqual(original['outputs'][-1]['error'], 'ValueError')
            self.assertEqual(original['outputs'][-1]['message'], 'participant rollback failed')
            self.assertEqual(result['outputs'][-1]['error'], 'TransactionException')
            self.assertEqual(result['outputs'][-1]['message'], 'Rollback cleanup failed: participant rollback failed')
            original['outputs'][-1].update(error=result['outputs'][-1]['error'], message=result['outputs'][-1]['message'])
        super().assert_case_result(case, result, original)

    def test_original_imports_and_core_inheritance(self):
        from pyasm.command import Command as ImportedCommand, Trigger as ImportedTrigger
        from pyasm.command.command import Command as ModuleCommand
        from pyasm.command.trigger import Trigger as ModuleTrigger
        from pyasm.search import Transaction as ImportedTransaction
        from pyasm.search.transaction import Transaction as ModuleTransaction
        from pyasm.common.container import Container as ImportedContainer
        from pyasm.common.common_exception import SecurityException as ImportedSecurity
        for actual, expected in ((ImportedCommand, Command), (ModuleCommand, Command), (ImportedTrigger, Trigger),
                                 (ModuleTrigger, Trigger), (ImportedTransaction, Transaction),
                                 (ModuleTransaction, Transaction), (ImportedContainer, Container), (ImportedSecurity, SecurityException)):
            self.assertIs(actual, expected)
        self.assertTrue(issubclass(Command, Base))
        self.assertTrue(issubclass(Search, Base))
        self.assertTrue(issubclass(Transaction, Base))
        self.assertTrue(issubclass(Trigger, Command))
        self.assertEqual(str(inspect.signature(Command.execute_cmd)), "(cmd, call_trigger=True)")
        self.assertEqual(str(inspect.signature(Transaction.get)), "(create=False, force=False)")

    def test_ported_method_signatures_match_the_source(self):
        for owner, path in ((Command, "command/command.py"), (Transaction, "search/transaction.py"),
                            (Trigger, "command/trigger.py"), (Container, "common/container.py"), (Base, "common/base.py")):
            source = ast.parse((read_tests.LEGACY / "src/pyasm" / path).read_text(encoding="utf-8"))
            original = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == owner.__name__)
            for node in original.body:
                if not isinstance(node, ast.FunctionDef) or node.name not in owner.__dict__:
                    continue
                actual = inspect.signature(getattr(owner, node.name))
                arguments = [arg.arg for arg in node.args.args]
                if arguments and arguments[0] == "cls":
                    arguments = arguments[1:]
                if node.args.kwarg:
                    arguments.append(node.args.kwarg.arg)
                with self.subTest(owner=owner.__name__, method=node.name):
                    self.assertEqual(list(actual.parameters), arguments)
                    defaults = [parameter.default for parameter in actual.parameters.values()
                                if parameter.default is not inspect.Parameter.empty]
                    self.assertEqual(defaults, [ast.literal_eval(value) for value in node.args.defaults])

    def test_registered_database_commit_and_rollback_have_real_effects(self):
        class Database:
            def __init__(self):
                self.db = sqlite3.connect(":memory:")
                self.db.execute("CREATE TABLE item (value TEXT)")
            def get_database_name(self):
                return "memory"
            def start(self):
                self.db.execute("BEGIN")
            def commit(self):
                self.db.commit()
            def rollback(self):
                self.db.rollback()
        database = Database()
        self.addCleanup(database.db.close)
        tx = Transaction()
        tx.start()
        tx.register_database(database)
        database.db.execute("INSERT INTO item VALUES ('kept')")
        tx.start()
        tx.commit()
        self.assertTrue(database.db.in_transaction)
        tx.commit()
        self.assertFalse(database.db.in_transaction)
        tx.start()
        tx.register_database(database)
        database.db.execute("INSERT INTO item VALUES ('discarded')")
        tx.rollback()
        self.assertEqual(database.db.execute("SELECT value FROM item").fetchall(), [("kept",)])

    def test_request_isolation_and_parent_context_restoration(self):
        barrier = Barrier(2)

        def run(label):
            with request_context(RequestContext(self.store, "admin", label)):
                Container.put("label", label)
                tx = Transaction.get(create=True)
                Trigger.append_trigger(None, Trigger(), label)
                barrier.wait(timeout=5)
                self.assertEqual(Container.get("label"), label)
                self.assertIs(Transaction.get(), tx)
                with request_context(RequestContext(self.store, "admin", "nested")):
                    self.assertIsNone(Transaction.get())
                    self.assertEqual(Container.get_seq("Trigger:called_triggers"), [])
                    Container.put("label", "nested")
                self.assertEqual(Container.get("label"), label)
                return tx, Container.get_instance()
        with ThreadPoolExecutor(max_workers=2) as executor:
            values = list(executor.map(run, ("one", "two")))
        self.assertIsNot(values[0][0], values[1][0])
        self.assertIsNot(values[0][1], values[1][1])

    def test_command_writes_are_blocked_in_all_hooks(self):
        before = {path: path.read_bytes() for path in self.store.data_dir.glob("db/*.db")}
        for phase in ("check_security", "start", "preprocess", "get_data", "execute", "postprocess", "commit", "notify_listeners"):
            with self.subTest(phase=phase), request_context(RequestContext(self.store, "admin", "one")):
                class Writer(Command):
                    def execute(self):
                        return "read-only"
                def write(self):
                    with store.connection("one", write=True) as db:
                        db.execute("UPDATE entity SET name='bad'")
                store = self.store
                setattr(Writer, phase, write)
                with self.assertRaises(UnsupportedContract):
                    Command.execute_cmd(Writer())
                self.assertEqual(Container.get_seq("Command:executing"), [])
        with request_context(RequestContext(self.store, "admin", "one")):
            Transaction.get(create=True)
            with self.assertRaises(UnsupportedContract), self.store.connection(write=True):
                pass
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_reads_work_inside_commands_and_unported_paths_raise(self):
        store = self.store
        class Reader(Command):
            def execute(self):
                return Search.get_by_code("contract/entity", "A").get_value("name")
        with request_context(RequestContext(store, "admin", "one")):
            self.assertEqual(Command.execute_cmd(Reader()), "Первый")
            tx = Transaction()
            change = tx.get_change_timestamp('contract/entity', 'A')
            self.assertEqual(change.get_id(), -1)
            self.assertEqual(change.get_json_value('changed_on'), {})
            self.assertIs(change, tx.get_change_timestamp('contract/entity', 'A'))
            self.assertEqual(tx.create_log_node('file').tag, 'file')
            with self.assertRaises(CommandException):
                Command().handle_pipeline(None, 'model', 'changed')
            for operation, args in ((tx.commit_log, ()),
                                    (Trigger.serialize_data, ({"set": {1, 2}},))):
                with self.subTest(operation=operation), self.assertRaises(UnsupportedContract):
                    operation(*args)
