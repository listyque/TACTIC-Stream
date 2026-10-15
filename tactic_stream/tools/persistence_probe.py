"""Exercise original SQL and in-memory journals on disposable parity data."""
import copy
from datetime import datetime


def run_sql_case(case):
    from pyasm.command import Command
    from pyasm.common import Container
    from pyasm.search import Search, Transaction, DbContainer, DbResource
    # Finish previous Batch connections without legacy release_thread_sql's
    # reconnect/commit fallback. Each scenario starts with fresh connections.
    DbContainer.close_thread_sql()
    DbContainer.close_all()
    Container.remove(Transaction.KEY)
    connections = {project: DbContainer.get(DbResource.get_default(project)) for project in ("one", "two")}
    for project, label in (("one", "Первый"), ("two", "Второй")):
        connections[project].do_update("UPDATE entity SET name='" + label + "' WHERE code='A'")
    sql, outputs = connections["one"], []

    class DatabaseCommand(Command):
        __module__ = "contract_persistence"
        def __init__(self, fail=False, nested=False):
            super().__init__()
            self.fail, self.nested = fail, nested
        def execute(self):
            current = Search("contract/entity").get_sql()
            current.do_update("UPDATE entity SET name='pending' WHERE code='A'")
            if self.nested:
                Command.execute_cmd(DatabaseCommand(self.fail))
            elif self.fail:
                raise ValueError("command failed")
            return Search.get_by_code("contract/entity", "A").get_value("name")

    for step in case["steps"]:
        method, args = step[0], step[1:]
        try:
            if method == "transaction_start":
                result = Transaction.get(create=True).counter
            elif method == "transaction_commit":
                result = Transaction.get().commit()
            elif method == "transaction_rollback":
                result = Transaction.get().rollback()
            elif method == "acquire":
                project = args[0] if args else "one"
                result = DbContainer.get(DbResource.get_default(project)) is connections[project]
                sql = connections[project]
            elif method == "search_value":
                result = Search.get_by_code("contract/entity", "A").get_value("name")
            elif method == "command":
                result = Command.execute_cmd(DatabaseCommand(*args))
            elif method == "resource":
                resource = DbResource.get_default("one")
                result = {key: getattr(resource, "get_" + key)() for key in ("database", "host", "port", "vendor", "user", "password", "schema", "key")}
                result["string"] = str(resource)
                result["cached"] = resource is DbResource.get_default("one")
                result["row_factory"] = sql.get_connection().row_factory is None
            else:
                result = getattr(sql, method)(*args)
            output = {"value": result}
        except Exception as exc:
            output = {"error": type(exc).__name__, "message": str(exc)}
        tx = Transaction.get()
        output["transaction_counter"] = None if tx is None else tx.counter
        output["sql_counter"] = sql.transaction_count
        output["row_count"] = sql.get_row_count()
        output["last_row_id"] = getattr(sql, "last_row_id", None)
        output["in_transaction"] = sql.get_connection().in_transaction
        outputs.append(copy.deepcopy(output))
    return outputs


def run_journal_case(case):
    from pyasm.common import Container
    from pyasm.search import Search, SearchType, SObject, SObjectUndo, Transaction, DbContainer, DbResource
    DbContainer.close_thread_sql()
    DbContainer.close_all()
    Container.remove(Transaction.KEY)
    DbContainer.get(DbResource.get_default("one")).do_update("UPDATE entity SET name='Первый' WHERE code='A'")
    if case.get("constructor") == "sobject":
        obj = SObject(case["search_type"])
    elif case.get("insert"):
        obj = SearchType.create(case.get("search_type", "contract/entity"))
    else:
        obj = Search.get_by_code(case.get("search_type", "contract/entity"), case.get("code") or "A")
    if case.get("data") is not None:
        obj.set_data(case["data"])
    updates = case.get("updates", {}).copy()
    for column, value in case.get("datetimes", {}).items():
        updates[column] = datetime.fromisoformat(value)
    obj.set_update_data(updates)
    tx = None if case.get("no_transaction") else Transaction.get(create=True)
    try:
        if case.get("delete"):
            value = SObjectUndo.log_undo_for_delete(obj)
        else:
            value = SObjectUndo.log_undo(obj, case.get("search_code", "A"), case.get("search_id", 1),
                                       case.get("insert", False), prev_code=case.get("prev_code"))
        output = {"value": value}
    except Exception as exc:
        output = {"error": type(exc).__name__, "message": str(exc)}
    output["xml"] = tx.get_xml().to_string() if tx else None
    output["raw_xml"] = tx.get_xml().to_string(pretty=False) if tx else None
    output["data"] = obj.get_data(False)
    output["pending"] = {key: str(value) if isinstance(value, datetime) else value for key, value in obj.update_data.items()}
    if tx:
        if case.get("finish"):
            tx.set_record(False)
            tx.commit()
        elif case.get("rollback"):
            tx.rollback()
        output["after"] = tx.get_xml().to_string()
    return output


def run_xml_case(case):
    from pyasm.common import Xml
    xml = Xml(case.get("xml", "<transaction/>"))
    outputs = []
    for step in case["steps"]:
        method, args = step[0], step[1:]
        if method == "append":
            child = xml.create_element(args[0], node=xml.get_root_node(), attrs=args[1])
            value = Xml.get_attributes(child)
        elif method in ("nodes", "attributes"):
            nodes = xml.get_nodes(*args)
            value = [Xml.get_attributes(node) for node in nodes] if method == "attributes" else [Xml.get_node_name(node) for node in nodes]
        else:
            value = getattr(xml, method)(*args)
        outputs.append(copy.deepcopy(value))
    return {"outputs": outputs, "pretty": xml.to_string(), "raw": xml.to_string(pretty=False)}
