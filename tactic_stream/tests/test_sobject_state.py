"""Original SObject state transitions; no commit or working data is used."""
import ast
import inspect
import json
import zlib
import test_read_parity as read_tests
from test_search_links import link_fixture
from test_schema import key
from tools.legacy_read_probe import run_sobject_case
from pyasm.search.search import RequestContext, Search, SearchType, SObject, SObjectException, request_context
from pyasm.biz.schema import Schema
from pyasm.common.errors import UnsupportedContract


def state_fixture(store):
    link_fixture(store)
    for project in ("one", "two"):
        with store.connection(project, write=True) as db:
            for column in ("required_text text NOT NULL DEFAULT 'required'", "required_number integer NOT NULL DEFAULT 3",
                           "required_active boolean NOT NULL DEFAULT 0", "properties json", "login text", "project_code text",
                           "date_value date", "decimal_value numeric", "float_value float"):
                db.execute("ALTER TABLE entity ADD COLUMN " + column)


def state_cases():
    result = []
    def add(name, steps=(), **options):
        result.append({"name": name, "method": "sobject_state", "steps": list(steps), **options})
    def step(method, *args, **kwargs):
        return {"method": method, "args": list(args), "kwargs": kwargs}
    for constructor in ("create", "sobject", "read"):
        add("initial_" + constructor, constructor=constructor)
        add("name_changes_" + constructor, [step("set_value", "name", "Changed"), step("get_value", "name"),
            step("set_value", "name", ""), step("get_value", "name", auto_convert=False), step("get_name", long=True),
            step("set_value", "name", "Changed again"), step("get_prev_value", "name")], constructor=constructor)
    for column, values in {
        "name": [None, "", 0, False, [], ["first", "second"], [None], {"field": "value"}, "NULL"],
        "amount": [None, "", "0", 0, 9.5, [], [None], "NULL"],
        "active": [None, "", "true", "True", "TRUE", "false", "0", "1", 0, 1, False, True, [], [None], "NULL"],
        "timestamp": [None, "", "2026-10-04 12:00:00", "2026-10-04T12:00:00+03:00", "invalid date", "NOW", "NULL"],
        "required_text": [None, "", "new", 0],
        "required_number": [None, "", "10", 0],
        "required_active": [None, "", False, True, [None]],
        "decimal_value": [None, "", "Decimal('1.5')", 0, 1.5],
        "float_value": [None, "", 0, 1.5],
        "unknown": [None, "", "local field", 1],
    }.items():
        for index, value in enumerate(values):
            add(f"set_{column}_{index}", [step("set_value", column, value), step("get_value", column, no_exception=True)], constructor="read")
    for column in ("name", "amount", "active", "timestamp", "required_text", "required_number", "required_active", "unknown"):
        for flags in ({"allow_none": True}, {"no_exception": True}, {"temp": True}):
            add("none_" + column + "_" + next(iter(flags)), [step("set_value", column, None, **flags), step("get_value", column, no_exception=True)], constructor="read")
    add("empty_column", [step("set_value", "", "test")])
    add("null_column", [step("set_value", None, "test")])
    add("same_value_still_marks_updates", [step("set_value", "name", "Первый")], constructor="read")
    add("revert_remains_pending", [step("set_value", "name", "changed"), step("set_value", "name", "Первый")], constructor="read")
    add("skip_missing_columns", [step("skip_invalid_column"), step("set_value", "unknown", "ignored"), step("set_value", "name", "real")])
    add("id_override", [step("set_id", 55), step("set_force_insert"), step("is_insert"), step("set_value", "id", 99)], constructor="read")
    add("string_minus_one", [step("set_value", "id", "-1", temp=True), step("is_insert")], constructor="read")
    add("set_project_user", [step("set_project"), step("set_user"), step("set_project", "two"), step("set_user", "other")])
    add("unmarked_update_buffer", [step("set_update_data", {"name": "buffer", "code": "NEW"}), step("get_value", "name"), step("has_value", "code"),
        step("get_data"), step("set_value", "active", True), step("get_value", "name")], constructor="read")
    add("set_data_copies_input", [{"method": "set_data", "args": [{"id": 12, "code": "REPLACED", "name": "row"}], "mutate_argument": {"name": "outside"}},
        step("set_value", "name", "buffer"), step("set_data", {"id": 13, "code": "NEXT", "name": "next row"}), step("get_value", "name")])
    add("set_update_data_copies_input", [{"method": "set_update_data", "args": [{"name": "pending"}], "mutate_argument": {"name": "outside"}}])
    add("merged_copy", [{"method": "get_data", "mutate_result": ["name", "outside"]}], constructor="read")
    add("stored_reference", [{"method": "get_data", "kwargs": {"merged": False}, "mutate_result": ["name", "outside"]}], constructor="read")
    for value in ({"owner": "Тест", "flag": False, "none": None}, [], None, "string", 12, {"large": "x" * 12000}):
        add("json_" + str(len(result)), [step("set_json_value", "metadata", value), step("get_json_value", "metadata")],
            compare_compressed_payload=isinstance(value, dict) and "large" in value)
        add("native_json_" + str(len(result)), [step("set_json_value", "properties", value), step("get_json_value", "properties")])
    for column in ("timestamp", "name"):
        for value in ("2026-10-04T12:00:00", "2026-10-04T12:00:00+03:00"):
            add("datetime_" + column + value, [{"method": "set_value", "args": [column], "datetime": value}, step("get_value", column)])
    add("json_datetime", [{"method": "set_json_value", "args": ["metadata"], "datetime": "2026-10-04T12:00:00+03:00"}])
    add("json_date", [{"method": "set_json_value", "args": ["metadata"], "date": "2026-10-04"}])
    add("json_dict_keys", [{"method": "set_json_value", "args": ["metadata"], "dict_keys": ["a", "b"]}])
    add("metadata_stale_cache", [step("get_metadata_dict"), step("set_json_value", "metadata", {"new": "value"}),
        step("get_metadata_dict"), step("get_metadata"), step("get_metadata_value", "new")], constructor="read")
    add("metadata_value_initial_empty", [step("get_metadata_value", "owner"), step("get_metadata_dict"), step("get_metadata_value", "owner"),
        step("set_metadata_value", "new", None), step("set_metadata_value", "owner", "Changed")], constructor="read")
    add("metadata_replaces_invalid_json", [step("set_metadata_value", "owner", "Changed")], constructor="read", code="C")
    for value in ("0", "12", "1.5", "false", None):
        add("json_field_" + str(value), [step("set_data_value", "metadata", "value", value), step("get_value", "metadata->value")], constructor="read")
    add("arrow_field", [step("set_value", "metadata->owner", "Changed"), step("get_value", "metadata->>owner"), step("has_value", "metadata->missing")], constructor="read")
    add("json_field_from_empty", [step("set_value", "metadata->value", "3")])
    add("json_field_from_invalid", [step("set_value", "metadata->value", "3")], constructor="read", code="C")
    add("pending_dictionary_reference", [step("set_value", "properties", {"a": 1}), {"method": "get_value", "args": ["properties"], "mutate_result": ["a", 2]}])
    add("stored_dictionary_copy", [step("set_data", {"id": -1, "properties": {"a": 1}}), {"method": "get_value", "args": ["properties"], "mutate_result": ["a", 2]}])
    add("missing_value_error", [step("get_value", "unknown"), step("get_value", "unknown", no_exception=True)], constructor="read")
    add("text_helpers", [step("get_seq_value", "name"), step("get_dict_value", "name"), step("set_value", "name", "a|b|a|"),
        step("get_seq_value", "name", delimiter="|"), step("get_dict_value", "name", delimiter="|")], constructor="read")
    add("datetime_helpers", [step("get_datetime_value", "timestamp"), step("get_datetime_display", "timestamp", "%Y-%m-%d %H:%M")], constructor="read")
    add("name_helpers", [step("get_name"), step("get_name", long=True), step("get_description"), step("get_update_description")], constructor="read", code="B")
    add("constructor_columns", [step("get_name", long=True)], constructor="sobject", columns=["id", "code", "name"], row=[3, "ROW", "row name"])
    for search_type in ("sthpw/project", "sthpw/project_type", "sthpw/schema", "sthpw/search_object"):
        add("create_" + search_type, search_type=search_type)
    add("searchtype_pending_definition", [step("set_value", "search_type", "contract/new"), step("set_value", "table_name", "public.new"),
        step("set_value", "database", "{project}"), step("get_base_key"), step("get_table"), step("get_database")], search_type="sthpw/search_object")
    for method in ("set_parent", "set_sobject_value", "add_related_sobject", "add_relationship"):
        for target, source in (("child", "entity"), ("ref", "entity"), ("id_ref", "id_entity")):
            source_key = key(source, "A") if source == "entity" else "contract/id_entity?project=one&id=1"
            add(method + target, [{"method": method, "object_keys": [source_key]}], search_type="contract/" + target)
    add("parent_from_key", [step("set_parent", key("entity", "A"))], search_type="contract/child")
    add("parent_missing", [step("set_parent", key("entity", "missing"))], search_type="contract/child")
    add("instance_draft", [{"method": "add_related_connection", "object_keys": [key("entity", "A"), key("collection", "G1")]}], search_type="contract/entity_in_collection")
    add("alternate_connection", [{"method": "add_related_sobject", "object_keys": [key("entity", "B")], "kwargs": {"src_path": "alternate"}}], search_type="contract/child")
    add("explicit_project", [step("set_project"), step("set_user")], search_type="contract/entity?project=two")
    compressed = "zlib:" + zlib.compress(json.dumps({"large": "x" * 12000}).encode()).hex()
    add("original_reads_new_compression", [step("set_value", "metadata", compressed), step("get_json_value", "metadata")])
    return result


class SObjectStateParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        state_fixture(cls.store)
        cls.cases = state_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, "admin", case.get("project", "one"))):
            return run_sobject_case(Search, SearchType, SObject, case)

    def test_prevalidation_runs_before_temp_and_null_handling(self):
        class Validated(SObject):
            def validate_set_value(self, name, value):
                if value == "invalid":
                    raise SObjectException("Rejected by the subclass")
        with request_context(RequestContext(self.store, "admin", "one")):
            obj = Validated("contract/entity")
            for flags in ({}, {"temp": True}, {"no_exception": True}):
                with self.assertRaises(SObjectException):
                    obj.set_value("name", "invalid", **flags)
            self.assertEqual(obj.update_data, {})
            self.assertFalse(obj.has_updates)

    def test_persistence_and_non_admin_edits_remain_blocked(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            obj = SearchType.create("contract/entity")
            obj.set_value("code", "STAGED")
            before = obj.get_data()
            for operation in (obj.commit, obj.delete):
                with self.assertRaises(UnsupportedContract):
                    operation()
            self.assertEqual(obj.get_data(), before)
            self.assertEqual(Search.get_by_code("contract/entity", "STAGED"), None)
        with request_context(RequestContext(self.store, "missing-user", "one")):
            obj = SearchType.create("contract/entity")
            with self.assertRaises(UnsupportedContract):
                obj.set_value("name", "Rejected")
            self.assertEqual(obj.update_data, {})

    def test_original_imports_and_method_signatures(self):
        from pyasm.common import TacticException
        from pyasm.search import SObjectException as ImportedException
        self.assertIs(ImportedException, SObjectException)
        self.assertTrue(issubclass(SObjectException, TacticException))
        self.assertEqual(str(inspect.signature(SObject.set_value)),
                         "(self, name, value, quoted=True, temp=False, no_exception=False, allow_none=False)")
        sources = {
            "search.py": ast.parse((read_tests.LEGACY / "src/pyasm/search/search.py").read_text(encoding="utf-8")),
            "schema.py": ast.parse((read_tests.LEGACY / "src/pyasm/biz/schema.py").read_text(encoding="utf-8")),
        }
        for filename, owner, methods in (("search.py", SObject, ("__init__", "set_value", "process_value", "set_parent", "set_sobject_value", "commit", "delete")),
                                         ("search.py", SearchType, ("__init__", "create", "get_database")),
                                         ("schema.py", Schema, ("__init__",))):
            original = next(node for node in sources[filename].body if isinstance(node, ast.ClassDef) and node.name == owner.__name__)
            for name in methods:
                node = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == name)
                arguments = node.args.args[1:] if name == "create" else node.args.args
                expected = [argument.arg for argument in arguments]
                with self.subTest(owner=owner.__name__, method=name):
                    self.assertEqual(list(inspect.signature(getattr(owner, name)).parameters), expected)
                    defaults = [parameter.default for parameter in inspect.signature(getattr(owner, name)).parameters.values()
                                if parameter.default is not inspect.Parameter.empty]
                    self.assertEqual(defaults, [ast.literal_eval(value) for value in node.args.defaults])
