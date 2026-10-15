"""Run original read methods on a marked temporary fixture, in legacy Python.

No source patching, server startup, upgrade or working database access. Batch
authentication and original Command errors write only to this disposable fixture.
"""
import argparse
import copy
import contextlib
from datetime import date, datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import zlib


def run_sobject_case(Search, SearchType, SObject, case):
    """Stage native object changes, capturing both values and pending state."""
    search_type = case.get("search_type", "contract/entity")
    constructor = case.get("constructor", "create")
    sobject_class = SObject
    if "hooks" in case:
        from pyasm.search import SObjectException
        class ContractObject(SObject):
            def handle_commit_security(self):
                return case["hooks"].get("allowed", True)
            def get_defaults(self):
                if case["hooks"].get("defaults_error"):
                    raise ValueError("Invalid defaults")
                return case["hooks"].get("defaults", {})
            def validate(self):
                if case["hooks"].get("validation_error"):
                    raise SObjectException("Invalid record")
                return case["hooks"].get("valid", True)
        sobject_class = ContractObject
    if constructor == "read":
        obj = Search.get_by_code(search_type, case.get("code", "A"))
    elif constructor == "sobject":
        obj = sobject_class(search_type, case.get("columns"), case.get("row"))
    else:
        obj = SearchType.create(search_type, case.get("columns"), case.get("row"))

    def state():
        return {"class": type(obj).__name__, "data": obj.get_data(), "stored": obj.get_data(merged=False).copy(),
                "update": obj.update_data.copy(), "quoted": obj.quoted_flag.copy(), "has_updates": obj.has_updates,
                "id": obj.get_id(), "code": obj.get_code(), "key": obj.get_search_key(),
                "insert": obj.is_insert(), "new_id": obj.new_id, "force_insert": obj.force_insert,
                "metadata": obj.metadata.copy() if isinstance(obj.metadata, dict) else obj.metadata,
                "prev_data": obj.prev_data.copy(), "prev_update": obj.get_prev_update_data().copy(),
                "last_statement": obj.get_last_statement()}

    results = [copy.deepcopy({"state": state()})]
    for step in case.get("steps", []):
        args = list(step.get("args", []))
        if "object_keys" in step:
            args = [Search.get_by_search_key(key) for key in step["object_keys"]] + args
        if "datetime" in step:
            args.append(datetime.fromisoformat(step["datetime"]))
        if "date" in step:
            args.append(date.fromisoformat(step["date"]))
        if "dict_keys" in step:
            args.append(dict.fromkeys(step["dict_keys"]).keys())
        try:
            value = getattr(obj, step["method"])(*args, **step.get("kwargs", {}))
            if step.get("mutate_result"):
                value[step["mutate_result"][0]] = step["mutate_result"][1]
            if step.get("mutate_argument"):
                args[0].update(step["mutate_argument"])
            result = {"value": value}
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
        result["state"] = state()
        results.append(copy.deepcopy(result))
    # Dates remain distinguishable from strings in comparisons, including pending data.
    def encode(value):
        if isinstance(value, (date, datetime)):
            return {"type": type(value).__name__, "iso": value.isoformat()}
        raise TypeError(type(value).__name__)
    result = json.loads(json.dumps(results, default=encode))
    if case.get("compare_compressed_payload"):
        # Compression output varies between zlib and Python 3.14's zlib-ng.
        # This case compares uncompressed bytes; all other cases compare raw state.
        def payloads(value):
            if isinstance(value, str) and value.startswith("zlib:"):
                return {"compressed_payload": zlib.decompress(bytes.fromhex(value[5:])).decode()}
            if isinstance(value, list):
                return [payloads(item) for item in value]
            if isinstance(value, dict):
                return {key: payloads(item) for key, item in value.items()}
            return value
        result = payloads(result)
    return result


def run_link_case(Search, case):
    """Exercise the same public kernel calls in original and new runtimes."""
    try:
        return _run_link_case(Search, case)
    except Exception as error:
        if type(error).__name__ != case.get('source_error'):
            raise
        return {'error': type(error).__name__, 'message': str(error)}


def _run_link_case(Search, case):
    search = Search(case.get("search_type", "contract/entity"))
    search.set_show_retired(case.get("show_retired", False))
    for join in case.get("joins", []):
        search.add_join(**join)
    search.add_op_filters(case.get("filters", []))
    for column in case.get("columns", []):
        search.add_column(**column)
    for order in case.get("order_bys", []):
        search.add_order_by(order)
    if "limit" in case:
        search.set_limit(case["limit"])
    operation = case["operation"]
    options = case.get("kwargs", {})
    if operation in ("add_search_filter", "add_relationship_search_filter"):
        description = case.get("sub")
        source = Search(description.get("search_type", "contract/child")) if description else None
        if source:
            source.set_show_retired(description.get("show_retired", False))
            source.add_op_filters(description.get("filters", []))
            for column in description.get("columns", []):
                source.add_column(**column)
            if "limit" in description:
                source.set_limit(description["limit"])
            if "offset" in description:
                source.set_offset(description["offset"])
            for order in description.get("order_bys", []):
                source.add_order_by(order)
            if description.get("preload") == "objects":
                source.get_sobjects()
            elif description.get("preload") == "count":
                source.get_count()
        if operation == "add_search_filter":
            applied = search.add_search_filter(case["column"], source, **options)
        else:
            applied = search.add_relationship_search_filter(source, **options)
        if source and description.get("change_after_capture"):
            source.add_filter("code", "no-match")
    elif operation == "get_related_by_sobjects":
        objects = [Search.get_by_search_key(key) for key in case["keys"]]
        result = Search.get_related_by_sobjects(objects, search.get_search_type(), **options)
        return {key: [obj.get_data() for obj in values] for key, values in result.items()}
    elif operation == "add_relationship_filter":
        applied = search.add_relationship_filter(Search.get_by_search_key(case["key"]), **options)
    elif operation == "add_relationship_filters":
        applied = search.add_relationship_filters([Search.get_by_search_key(key) for key in case["keys"]], **options)
    elif operation == "join":
        applied = None
    elif operation == "children_alter_search":
        source = Search.get_by_search_key(case['key'])
        applied = source.children_alter_search(search, search.get_search_type())
        applied = applied is search
    elif operation in ('codes', 'ids'):
        if case.get('null_filter'):
            search.set_null_filter()
        values = search.get_sobject_codes() if operation == 'codes' else search.get_sobject_ids()
        return {'values': values, 'columns': search.get_select().get_columns()}
    else:
        raise ValueError(operation)
    return {"applied": applied, "rows": [obj.get_data() for obj in search.get_sobjects()],
            "count": search.get_count()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    legacy, fixture = args.legacy.resolve(), args.fixture.resolve()
    if fixture.is_relative_to(legacy) or not fixture.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("Only a temporary fixture outside legacy is accepted")
    if not (fixture / ".tactic-stream-parity").is_file():
        parser.error("Fixture marker is required")
    cases = json.loads((fixture / "cases.json").read_text(encoding="utf-8"))
    # The embedded interpreter's _pth omits the directory of the executed script.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(legacy / "tools/local"))
    from launch import configure_paths
    os.environ.pop("TACTIC_TMP_CONFIG_PATH", None)
    configure_paths(fixture, fixture / "tactic-conf.xml")
    os.environ["TACTIC_CLEANUP"] = "false"
    results = []
    environments = []
    with contextlib.redirect_stdout(sys.stderr):
        from pyasm.security import Batch
        from pyasm.search import Search, SearchType, SearchKey, SObject, DbContainer
        from pyasm.biz import Project, Schema
        from pyasm.prod.service import ApiXMLRPC
        # Tests use Stream's relocated API path; only the original runtime needs this mapping.
        import pyasm.prod.service.api_xmlrpc as original_api
        sys.modules['pyasm.web.api_xmlrpc'] = original_api
        if any(case['method'] in ('diagnostic_contract', 'queue_contract', 'command_api_contract', 'config_api_contract', 'template_export_contract', 'template_check_contract', 'uninstall_contract', 'export_contract', 'config_contract', 'plugin_contract', 'journal_reads', 'automatic_journal_contract', 'business_contract', 'generation_contract', 'workflow_contract', 'python_contract', 'engine_contract', 'snapshot_write_contract', 'expression_write_contract', 'file_contract', 'repository_contract', 'checkin_contract', 'versionless_contract', 'delete_contract', 'append_group_contract', 'preallocation_contract', 'upload_checkin_contract', 'compound_form_contract', 'upload_form_contract', 'icon_contract', 'batch_api_contract', 'file_api_contract', 'snapshot_levels_contract') for case in cases):
            # Transaction.get_change_timestamp still has a Python 2 absolute import.
            # Alias the original module without changing the method or source files.
            import pyasm.search.search as original_search
            sys.modules['search'] = original_search
        try:
            for case in cases:
                # A new container matches original XML-RPC request isolation.
                environment = Batch(project_code=case.get("project", "one"), login_code="admin")
                # Batch.__del__ closes the current global container's connections.
                # Keep previous environments alive until all requests have finished.
                environments.append(environment)
                api = ApiXMLRPC()
                api.set_protocol("xmlrpc")
                api.set_language("python")
                search_type = case.get("search_type", "contract/entity")
                options = case.get("options", {})
                method = case["method"]
                if method in ('diagnostic_contract', 'queue_contract', 'command_api_contract', 'config_api_contract'):
                    # The local source calls still initialize the HTTP adapter.
                    # Supply a request environment, keeping API bodies unchanged.
                    from pyasm.web.web_environment import WebEnvironment
                    web = WebEnvironment()
                    web.get_env = lambda name: {'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': '8081', 'HTTP_HOST': '127.0.0.1:8081'}.get(name, '')
                    ApiXMLRPC.get_adapter = lambda self: web
                if method in ('file_api_contract', 'snapshot_levels_contract'):
                    # Batch has no HTTP adapter; provide the original web path accessors.
                    from pyasm.common import Container
                    from pyasm.web.web_environment import WebEnvironment
                    web = WebEnvironment()
                    web.get_env = lambda name: {'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': '8081', 'HTTP_HOST': '127.0.0.1:8081'}.get(name, '')
                    Container.put('WebContainer::web', web)
                if method in ('edit_form_contract', 'calendar_form_contract', 'workflow_form_contract', 'compound_form_contract', 'upload_form_contract'):
                    from pyasm.common import Container
                    from pyasm.web.cherrypy30_adapter import CherryPyAdapter
                    from types import SimpleNamespace
                    web = CherryPyAdapter.__new__(CherryPyAdapter)
                    web.request = SimpleNamespace(params={}, wsgi_environ={})
                    Container.put('WebContainer::web', web)
                if method in ('schema_edit_contract', 'schema_template_contract'):
                    # Original creator reads missing optional kwargs from its HTTP form.
                    from pyasm.common import Container
                    from pyasm.web.web_environment import WebEnvironment
                    web = WebEnvironment()
                    web.get_form_value = lambda name: ''
                    web.get_form_values = lambda name: []
                    web.get_env = lambda name: {'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': '8081', 'HTTP_HOST': '127.0.0.1:8081'}.get(name, '')
                    Container.put('WebContainer::web', web)
                    ApiXMLRPC.get_adapter = lambda self: web
                    if method == 'schema_template_contract':
                        from pyasm.common import Config
                        temp = fixture / 'template_tmp'
                        (temp / 'temp').mkdir(parents=True, exist_ok=True)
                        Config.set_value('install', 'tmp_dir', str(temp).replace('\\', '/'))
                        # Source invokes PG shell tools even for SQLite. Keep its real failure
                        # inside this fixture: no binary can connect to a running database.
                        empty_path = fixture / 'empty_path'
                        empty_path.mkdir(exist_ok=True)
                        os.environ['PATH'] = str(empty_path)
                if method in ('automatic_journal_contract', 'preference_contract'):
                    from automatic_journal_probe import run_automatic_journal_case
                    result = run_automatic_journal_case(case)
                elif method == 'generation_contract':
                    from generation_probe import run_generation_case
                    result = run_generation_case(case)
                elif method == 'workflow_contract':
                    from workflow_probe import run_workflow_case
                    result = run_workflow_case(case)
                elif method == 'python_contract':
                    from python_probe import run_python_case
                    result = run_python_case(case)
                elif method == 'engine_contract':
                    from engine_probe import run_engine_case
                    result = run_engine_case(case)
                elif method in ('self_instance_contract', 'project_write_contract', 'user_status_contract', 'user_workflow_contract', 'workflow_project_contract', 'workflow_undo_contract', 'cross_project_undo_contract'):
                    import pyasm.search.search as original_search
                    sys.modules['search'] = original_search
                    from snapshot_probe import run_snapshot_case
                    result = run_snapshot_case(case)
                elif method in ('snapshot_contract', 'snapshot_write_contract', 'naming_contract', 'expression_contract', 'expression_write_contract', 'file_contract', 'repository_contract', 'checkin_contract', 'versionless_contract', 'delete_contract', 'append_group_contract', 'preallocation_contract', 'upload_checkin_contract', 'compound_form_contract', 'upload_form_contract', 'icon_contract', 'batch_api_contract', 'file_api_contract', 'snapshot_levels_contract', 'workflow_api_contract', 'schema_api_contract', 'schema_template_contract', 'schema_edit_contract', 'collection_contract', 'collection_commands_contract', 'edit_form_contract', 'calendar_form_contract', 'workflow_form_contract', 'compound_form_contract', 'upload_form_contract'):
                    from snapshot_probe import run_snapshot_case
                    try:
                        result = run_snapshot_case(case)
                    except Exception as error:
                        if method != 'schema_template_contract' and (method != 'collection_contract' or case.get('operation') != 'cte'):
                            raise
                        result = {'error': type(error).__name__, 'message': str(error)}
                elif method in ('directory_contract', 'ingestion_contract', 'command_listener_contract', 'workflow_nodes_contract', 'dependency_contract', 'process_commands_contract', 'pipeline_versions_contract', 'same_object_contract', 'process_delete_contract', 'process_type_contract', 'workflow_packages_contract', 'task_schedule_contract', 'task_status_contract'):
                    import pyasm.search.search as original_search
                    sys.modules['search'] = original_search
                    from snapshot_probe import run_snapshot_case
                    try:
                        result = run_snapshot_case(case)
                    except Exception as error:
                        if method not in ('dependency_contract', 'task_status_contract'):
                            raise
                        result = {'error': type(error).__name__, 'message': str(error)}
                elif method == 'handoff_contract':
                    from pyasm.common import Environment
                    from pyasm.web import WebContainer
                    # These API methods only use the web object for native directory access.
                    WebContainer.set_web(Environment.get_env_object())
                    from snapshot_probe import run_snapshot_case
                    result = run_snapshot_case(case)
                elif method == 'metadata_checkin_contract':
                    # Source BaseCheckin uses a Python-2 absolute sibling import.
                    from pyasm.checkin import metadata
                    sys.modules['metadata'] = metadata
                    from snapshot_probe import run_snapshot_case
                    result = run_snapshot_case(case)
                elif method in ('search_join_contract', 'rest_contract', 'schema_replay_contract', 'transaction_state_contract', 'undo_contract', 'local_sobjects_contract', 'widget_config_contract', 'diagnostic_contract', 'queue_contract', 'command_api_contract', 'config_api_contract', 'project_write_contract', 'plugin_contract', 'config_contract', 'export_contract', 'uninstall_contract', 'template_check_contract', 'template_export_contract'):
                    from snapshot_probe import run_snapshot_case
                    result = run_snapshot_case(case)
                elif method == 'api_remaining_contract':
                    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests/scripts'))
                    import api_remaining_contract
                    result = api_remaining_contract.run(case, api)
                elif method == 'html_api_contract':
                    from snapshot_probe import run_snapshot_case
                    result = run_snapshot_case(case)
                elif method == 'business_contract':
                    from business_probe import run_business_case
                    result = run_business_case(case)
                elif method == 'journal_write_contract':
                    from journal_write_probe import run_journal_write_case
                    result = run_journal_write_case(case)
                elif method == 'security_contract':
                    from security_probe import run_security_case
                    result = run_security_case(case)
                elif method == 'security_lifecycle_contract':
                    from security_lifecycle_probe import run_security_lifecycle_case
                    result = run_security_lifecycle_case(case)
                elif method == 'access_contract':
                    from access_probe import run_access_case
                    result = run_access_case(case)
                elif method == 'registry_contract':
                    from registry_probe import run_registry_case
                    result = run_registry_case(case)
                elif method == 'trigger_dispatch':
                    from trigger_probe import run_trigger_case
                    result = run_trigger_case(case)
                elif method == 'pipeline_reads':
                    from pipeline_probe import run_pipeline_case
                    result = run_pipeline_case(case)
                elif method == 'journal_reads':
                    from log_probe import run_log_case
                    result = run_log_case(case)
                elif method == "project_settings":
                    from settings_probe import run_settings_case
                    result = run_settings_case(case)
                elif method in ("sql_builder", "sobject_statement"):
                    from statement_probe import run_builder_case, run_statement_case
                    result = run_builder_case(case) if method == "sql_builder" else run_statement_case(case, run_sobject_case)
                elif method in ("sql_transaction", "sobject_journal", "xml_journal"):
                    from persistence_probe import run_sql_case, run_journal_case, run_xml_case
                    result = {"sql_transaction": run_sql_case, "sobject_journal": run_journal_case,
                              "xml_journal": run_xml_case}[method](case)
                elif method in ("command_lifecycle", "transaction_lifecycle", "trigger_state"):
                    from command_probe import run_command_case, run_transaction_case, run_trigger_state_case
                    runners = {"command_lifecycle": run_command_case, "transaction_lifecycle": run_transaction_case,
                               "trigger_state": run_trigger_state_case}
                    result = runners[method](case)
                elif method == "sobject_state":
                    result = run_sobject_case(Search, SearchType, SObject, case)
                elif method == "search_links":
                    result = run_link_case(Search, case)
                elif method == "query":
                    result = api._query(search_type, **options)
                elif method == "record":
                    result = api._get_sobject_dict(Search.get_by_code(search_type, case["code"]))
                elif method == "columns":
                    result = Search(search_type).get_columns()
                elif method == "tables":
                    resource = Project.get_db_resource_by_search_type(search_type)
                    result = resource.get_database_impl().get_table_info(resource)
                elif method == "schema":
                    schema = Schema.get_predefined_schema(case["predefined"]) if "predefined" in case else Schema.get()
                    result = getattr(schema, case["operation"])(*case.get("args", []), **case.get("kwargs", {}))
                elif method == "schema_error":
                    try:
                        Schema.get().get_relationship_attrs(*case["args"])
                    except AttributeError as exc:
                        result = {"error": type(exc).__name__, "message": str(exc)}
                    else:
                        raise AssertionError("Expected the original implicit-id error")
                elif method == "schema_resolve":
                    schema = Schema.get()
                    attrs = schema.get_relationship_attrs(*case["args"])
                    result = schema.resolve_relationship_attrs(attrs, *case["args"])
                elif method == "api_body":
                    # Call the original body after Batch, without its Command/auth wrapper.
                    decorated = getattr(ApiXMLRPC, case["call"])
                    closure = dict(zip(decorated.__code__.co_freevars, (cell.cell_contents for cell in decorated.__closure__)))
                    try:
                        result = closure["meth"](api, None, *case.get("args", []), **case.get("kwargs", {}))
                    except TypeError:
                        if not case.get('expect_type_error'):
                            raise
                        result = {'error': 'TypeError'}
                elif method in ("parent", "related", "children", "relationship_filter", "relationship_filters", "parent_filter", "parent_key", "stype_related"):
                    source = Search.get_by_search_key(case["key"]) if "key" in case else None
                    if method == "parent":
                        result = api._get_sobject_dict(source.get_parent(**case.get("kwargs", {})))
                    elif method == "parent_key":
                        result = source.get_parent_search_key()
                    elif method == "stype_related":
                        result = SearchType.get_related_types(search_type, **case.get("kwargs", {}))
                    else:
                        if method == "related":
                            objects = source.get_related_sobjects(search_type, **case.get("kwargs", {}))
                        elif method == "children":
                            objects = source.get_all_children(search_type)
                        else:
                            search = Search(search_type)
                            if method == "relationship_filters":
                                objects = [Search.get_by_search_key(key) for key in case["keys"]]
                                search.add_relationship_filters(objects, **case.get("kwargs", {}))
                            elif method == "relationship_filter":
                                search.add_relationship_filter(source, **case.get("kwargs", {}))
                            else:
                                search.add_parent_filter(source)
                            objects = search.get_sobjects()
                        result = [obj.get_search_key() for obj in objects]
                else:
                    search = Search(search_type)
                    search.add_op_filters(options.get("filters", []))
                    search.set_show_retired(options.get("show_retired", False))
                    for name in options.get("columns", []):
                        search.add_column(name, distinct=options.get("distinct", False))
                    if "limit" in options:
                        search.set_limit(options["limit"])
                    if "offset" in options:
                        search.set_offset(options["offset"])
                    if method == "count":
                        result = search.get_count()
                    elif method == "codes":
                        result = search.get_sobject_codes()
                    elif method == "ids":
                        result = search.get_sobject_ids()
                    elif method == "local_dict":
                        result = search.get_sobject().get_sobject_dict(**case.get("serialize", {}))
                    elif method == "json":
                        result = search.get_sobject().get_json_value(case["column"], **case.get("read", {}))
                    elif method == "keys":
                        result = SearchKey.get_by_sobjects(search.get_sobjects(), use_id=case.get("use_id", False))
                    else:
                        raise ValueError("Unknown probe method: " + method)
                results.append({"name": case["name"], "result": result})
                # close_all releases the thread pool and can reconnect closed Sql.
                # Close it first, as the persistence probes do, then clear all caches.
                DbContainer.close_thread_sql()
                DbContainer.close_all()
        finally:
            DbContainer.close_thread_sql()
            DbContainer.close_all()
    (fixture / "original_results.json").write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
