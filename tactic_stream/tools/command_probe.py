"""Shared instrumentation of native Command/Transaction/Trigger calls.

Run only on disposable parity fixtures. Neither the kernel nor SQL is mocked.
The recorded participants are test commands with ordinary lifecycle callbacks.
"""
import copy


def run_command_case(case):
    from pyasm.command import Command, CommandExitException, Trigger
    from pyasm.common import Container
    from pyasm.search import Transaction

    events, commands = [], []

    def record(name, phase):
        tx = Transaction.get()
        events.append([name, phase, tx.counter if tx else None,
                       [item.label for item in Container.get_seq(Command.TOP_CMD_KEY)]])

    class RecordedCommand(Command):
        __module__ = "contract_commands"

        def __init__(self, description):
            super().__init__(option="kept")
            self.spec = description
            self.label = description.get("label", "parent")
            commands.append(self)

        def phase(self, name):
            record(self.label, name)
            if self.spec.get("fail") == name or (name == "execute" and self.spec.get("fail") == "rollback"):
                error = self.spec.get("error", "value")
                if error == "exit":
                    raise CommandExitException("stopped")
                if error == "interrupt":
                    raise KeyboardInterrupt()
                raise ValueError("failed " + self.label + ":" + name)

        def check_security(self):
            self.phase("security")
            return self.spec.get("security", True)

        def check(self):
            self.phase("check")
            return self.spec.get("check", True)

        def start(self):
            self.phase("start")

        def preprocess(self):
            self.phase("preprocess")

        def get_data(self):
            self.phase("data")

        def execute(self):
            self.phase("execute")
            self.add_description(self.spec.get("description", self.label))
            for spec in self.spec.get("children", []):
                child = RecordedCommand(spec)
                try:
                    Command.execute_cmd(child)
                except Exception as exc:
                    if not self.spec.get("catch_child"):
                        raise
                    record(self.label, "caught:" + type(exc).__name__)
            for spec in self.spec.get("triggers", []):
                trigger = RecordedTrigger(spec)
                trigger.set_input(spec.get("input", {"value": 1}))
                Trigger.append_trigger(self, trigger, spec.get("event", "changed"))
            return self.spec.get("result")

        def postprocess(self):
            self.phase("postprocess")

        def commit(self):
            self.phase("commit")

        def rollback(self):
            self.phase("rollback")

        def notify_listeners(self):
            self.phase("notify")

    class RecordedTrigger(Trigger):
        __module__ = "contract_commands"

        def __init__(self, description):
            super().__init__(option="discarded")
            self.spec = description
            self.label = description.get("label", "trigger")
            commands.append(self)

        def start(self):
            record(self.label, "start")

        def execute(self):
            record(self.label, "execute")
            if self.spec.get("recursive"):
                other = RecordedTrigger({"label": "recursive"})
                other.set_input(self.get_input().copy())
                Trigger.append_trigger(self, other, self.get_event())
            if self.spec.get("fail"):
                raise ValueError("failed " + self.label)
            return self.spec.get("result")

        def commit(self):
            record(self.label, "commit")

        def rollback(self):
            record(self.label, "rollback")

        def notify_listeners(self):
            record(self.label, "notify")

    outputs = []
    for spec in case.get("commands", [{}]):
        cmd = RecordedCommand(spec)
        if "info" in spec:
            cmd.info = spec["info"]
        if spec.get("explicit_transaction"):
            tx = Transaction()
            if spec.get("start_transaction"):
                tx.start()
            cmd.set_transaction(tx)
        if spec.get("reuse_previous"):
            cmd = commands[0]
        try:
            if spec.get("entry") == "execute_transaction":
                result = cmd.execute_transaction(call_trigger=spec.get("call_trigger", True))
            else:
                result = Command.execute_cmd(cmd, call_trigger=spec.get("call_trigger", True))
            outputs.append({"value": result})
        except BaseException as exc:
            outputs.append({"error": type(exc).__name__, "message": str(exc)})
    tx = Transaction.get()
    return copy.deepcopy({"events": events, "outputs": outputs,
        "commands": [{"label": cmd.label, "info": cmd.info, "errors": cmd.errors,
                      "description": cmd.description, "kwargs": cmd.kwargs,
                      "counter": cmd.transaction.counter if cmd.transaction else None,
                      "ret_val": cmd.get_ret_val() if isinstance(cmd, Trigger) else None} for cmd in commands],
        "transaction": None if not tx else {"counter": tx.counter, "description": tx.description,
                      "command_class": tx.command_class, "participants": [obj.label for obj in tx.transaction_objs]},
        "top": [obj.label for obj in Container.get_seq(Command.TOP_CMD_KEY)],
        "queued": [obj.label for obj in Container.get("Trigger:called_triggers") or []],
        "previous": Container.get("Trigger:prev_called_triggers") or []})


def run_transaction_case(case):
    from pyasm.common import Container
    from pyasm.search import Transaction

    events = []

    class Participant:
        def __init__(self, name):
            self.name = name

        def start(self):
            events.append([self.name, "start"])

        def commit(self):
            events.append([self.name, "commit"])
            if self.name == case.get("fail_commit"):
                raise ValueError("participant commit failed")

        def rollback(self):
            events.append([self.name, "rollback"])
            if self.name == case.get("fail_rollback"):
                raise ValueError("participant rollback failed")

        def get_database_name(self):
            return self.name

    tx = Transaction()
    participants = {name: Participant(name) for name in ("first", "second")}
    outputs = []
    for step in case["steps"]:
        method, args = step[0], step[1:]
        try:
            if method == "get":
                tx = Transaction.get(*args)
                result = None if tx is None else "transaction"
            elif method in ("register", "register_database"):
                result = getattr(tx, method)(participants[args[0]])
            else:
                result = getattr(tx, method)(*args)
            result = {"value": result}
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
        result["state"] = None if tx is None else {
            "counter": tx.counter, "active": tx.is_in_transaction(), "description": tx.description,
            "title": tx.title, "class": tx.command_class, "record": tx.record_flag, "sync": tx.sync_flag,
            "participants": [obj.name for obj in tx.transaction_objs], "databases": list(tx.get_databases()),
            "first_database": tx.get_database("first") is participants["first"],
            "change_timestamps": tx.get_change_timestamps(), "log": tx.get_transaction_log_sobj()}
        result["stack"] = [item.counter for item in Container.get_seq(Transaction.KEY)]
        outputs.append(copy.deepcopy(result))
    return {"events": events, "outputs": outputs}


def run_trigger_state_case(case):
    from pyasm.command import Command, Trigger
    from pyasm.common import Container

    class Definition:
        def __init__(self, data):
            self.data = data

        def get_value(self, name, no_exception=False):
            return self.data.get(name, "")

    # Limit class-global registrations to this disposable scenario in both runtimes.
    old_static, old_integral = Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS
    Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = [], []
    # Batch authentication has its own unported built-in listeners. Establish
    # an empty registry using its public Container API for these registration cases.
    Container.remove(Trigger.STATIC_TRIGGER_KEY)
    Container.remove(Trigger.INTEGRAL_TRIGGER_KEY)
    try:
        if case.get("operation") == "state":
            trigger, caller = Trigger(option="discarded"), Command(option="kept")
            trigger.set_trigger_sobj(Definition({"data": case.get("data", "")}))
            trigger.set_command(caller)
            trigger.set_event("changed")
            trigger.set_input({"value": 1})
            trigger.set_output(trigger.get_input())
            trigger.get_output()["extra"] = 2
            trigger.set_description("description")
            trigger.set_ret_val(False)
            try:
                data = {"value": trigger.get_trigger_data()}
            except Exception as exc:
                data = {"error": type(exc).__name__, "message": str(exc)}
            return {"kwargs": trigger.kwargs, "caller": trigger.get_command() is caller,
                    "caller_class": trigger.get_command_class(), "event": trigger.get_message(),
                    "input": trigger.get_input(), "output": trigger.get_output(),
                    "description": trigger.get_description(), "ret_val": trigger.get_ret_val(), "data": data}
        for spec in case.get("definitions", []):
            definition = Definition(spec)
            method = Trigger.append_integral_trigger if spec.get("integral") else Trigger.append_static_trigger
            method(definition, startup=spec.get("startup", False))
        snapshot = {"static": [obj.data for obj in Trigger.get_static_triggers()],
                    "integral": [obj.data for obj in Trigger.get_integral_triggers()],
                    "matching": [obj.data for obj in Trigger.get_static_triggers_by_event(case.get("event", "changed"), case.get("process"))]}
        if case.get("new_request"):
            Container.remove(Trigger.STATIC_TRIGGER_KEY)
            Container.remove(Trigger.INTEGRAL_TRIGGER_KEY)
        snapshot["next_static"] = [obj.data for obj in Trigger.get_static_triggers()]
        snapshot["next_integral"] = [obj.data for obj in Trigger.get_integral_triggers()]
        return snapshot
    finally:
        Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = old_static, old_integral
