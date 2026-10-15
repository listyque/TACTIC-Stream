"""Same statement calls against native and original kernels; never execute SQL."""
import copy
from datetime import date, datetime
import json
from unittest.mock import patch


def run_builder_case(case):
    from pyasm.search import DbContainer, DbResource, Insert, Update, Delete, Select, Sql, DatabaseImpl
    from pyasm.common import Common
    kind = case["kind"]
    builder = {"Insert": Insert, "Update": Update, "Delete": Delete, "Select": Select}.get(kind)
    obj = builder() if builder else None
    if obj and case.get("connector", "resource") != "none":
        connector = case.get("connector", "resource")
        resource = DbResource.get_default(case.get("database", "one"))
        obj.set_database(DbContainer.get(resource) if connector == "sql" else "sthpw" if connector == "string" else resource)
    if obj:
        if kind == 'Select':
            obj.add_table(case.get("table", "entity"))
        else:
            obj.set_table(case.get("table", "entity"))
    outputs = []
    for step in case["steps"]:
        args = list(step.get("args", []))
        if step.get("resource_argument"):
            args.insert(0, DbResource.get_default(step["resource_argument"]))
        if "datetime" in step:
            args.append(datetime.fromisoformat(step["datetime"]))
        if "date" in step:
            args.append(date.fromisoformat(step["date"]))
        if "bytes" in step:
            args.append(bytes.fromhex(step["bytes"]))
        owner = obj or (Sql if kind == "quote" else Common if kind == "random" else DatabaseImpl.get())
        try:
            # The entropy input is controlled, while the original method remains intact.
            with patch("os.urandom", lambda n: bytes(range(n))):
                if step.get('roundtrip'):
                    restored = Select()
                    if obj.sql:
                        restored.set_database(obj.sql)
                    restored.loads(obj.dumps())
                    value = restored.get_statement()
                else:
                    value = getattr(owner, step["method"])(*args, **step.get("kwargs", {}))
                    if step['method'] == 'copy':
                        value = value.get_statement()
            if step.get("mutate_result"):
                value.update(step["mutate_result"])
            output = {"value": value}
        except Exception as exc:
            output = {"error": type(exc).__name__, "message": str(exc)}
        if kind == 'Select':
            output['state'] = {name: copy.deepcopy(getattr(obj, name)) for name in
                               ('tables', 'columns', 'as_columns', 'column_tables', 'wheres', 'raw_filters',
                                'group_bys', 'havings', 'order_bys', 'order_by_columns', 'limit', 'offset',
                                'distinct', 'distinct_col', 'joins', 'database', 'schema')}
        elif kind == 'Delete':
            output['state'] = dict(raw_filters=copy.deepcopy(obj.raw_filters), database=obj.database)
        elif obj:
            output["state"] = {"data": obj.data.copy(), "unquoted": obj.unquoted_cols[:],
                               "escape": obj.escape_quoted_cols[:], "database": obj.database, "schema": obj.schema}
            if kind == "Update":
                output["state"].update(filters=obj.filters.copy(), raw_filters=copy.deepcopy(obj.raw_filters),
                                      wheres=list(obj.wheres))
        outputs.append(copy.deepcopy(output))
    def encode(value):
        if isinstance(value, (date, datetime)):
            return {"type": type(value).__name__, "iso": value.isoformat()}
        if isinstance(value, bytes):
            return {"bytes": value.hex()}
        raise TypeError(type(value).__name__)
    return json.loads(json.dumps(outputs, default=encode))


def run_statement_case(case, run_sobject_case):
    from pyasm.search import Search, SearchType, SObject
    with patch("os.urandom", lambda n: bytes(range(n))):
        return run_sobject_case(Search, SearchType, SObject, case)
