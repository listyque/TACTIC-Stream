"""Compare new reads with the real original Search/SObject/ApiXMLRPC runtime."""
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib

from test_foundation import ROOT, LEGACY, fixture
from tactic_stream.server.api import Api
from pyasm.search.search import RequestContext, Search, request_context
from pyasm.common.errors import UnsupportedContract
from pyasm.search.keys import SearchKey
from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store


def read_fixture(store):
    fixture(store)
    for project in ("one", "two"):
        with store.connection(project, write=True) as db:
            db.execute("ALTER TABLE entity ADD COLUMN active boolean")
            db.execute("ALTER TABLE entity ADD COLUMN metadata text")
            db.execute("ALTER TABLE entity ADD COLUMN timestamp timestamp")
            db.execute("UPDATE entity SET active=1, metadata=?, timestamp=? WHERE code='A'",
                       ('{"owner":"Тест","nested":{"flag":false}}', '2026-10-01 12:30:00.123'))
            db.execute("UPDATE entity SET active=0, metadata='' WHERE code='B'")
            db.execute("UPDATE entity SET active='false', metadata='invalid JSON' WHERE id=4")
            compressed = "zlib:" + zlib.compress(b'{"compressed":true}').hex()
            db.executemany("INSERT INTO entity VALUES (?,?,?,?,?,?,?,?)", [
                (5, "D", "alpha_beta", 0, None, None, compressed, "2026-10-02T13:00:00+03:00"),
                (6, "E", "Alpha 100%", 9, None, "True", "null", "2026-10-03 00:00:00"),
                (7, "F", None, None, None, "0", "[1,2]", None),
                (8, "G", "", -2, None, 1, None, None),
            ])


def cases():
    result = []
    filters = {
        "default_order": [],
        "two_value_null": [["name", None]],
        "empty_list": [["code", []]],
        "empty_string_list": [["code", [""]]],
        "empty_not_in": [["code", "not in", []]],
        "zero_in_list": [["amount", "in", [0, 9]]],
        "pipe_in": [["code", "in", "A|B||D"]],
        "pipe_not_in": [["code", "not in", "A|B"]],
        "null_sentinel": [["name", "is", "NULL"]],
        "is_not_including_null": [["name", "is not", "Первый"]],
        "ignored_empty_triple": [["name", "=", ""]],
        "plain_empty_string": [["name", ""]],
        "all_sentinel": [["code", "__ALL__"]],
        "numeric_alias": [["amount", "gte", 0], ["amount", "lt", 9]],
        "own_table_qualifier": [["entity.code", "A"]],
        "contains": [["name", "contains", "ALPHA"]],
        "contains_underscore_wildcard": [["name", "contains", "alpha_"]],
        "does_not_contain": [["name", "does not contain", "ALPHA"]],
        "startswith": [["name", "starts with", "Alpha"]],
        "endswith": [["name", "ends with", "%"]],
        "does_not_start": [["name", "does not start with", "Alpha"]],
        "does_not_end": [["name", "does not end with", "%"]],
        "eqi": [["name", "EQI", "REILLY"]],
        "neq": [["name", "NEQ", "Alpha"]],
        "boolean_python": [["active", True]],
        "boolean_text": [["active", "true"]],
        "boolean_false": [["active", False]],
        "boolean_triple": [["active", "=", True]],
        "postfix_or": ["begin", ["code", "A"], ["name", "contains", "Alpha"], "or"],
        "nested_groups": ["begin", "begin", ["code", "A"], ["code", "B"], "or",
                          "begin", ["amount", "gte", 0], ["amount", "lte", 9], "and", "or"],
        "implicit_group_end": ["begin", ["code", "A"], ["code", "B"]],
        "empty_group": ["begin", "or"],
        "group_markers_as_lists": [["begin"], ["code", "A"], ["code", "B"], ["or"]],
        "date_after": [["timestamp", "is after", "2026-10-01"]],
        "date_before": [["timestamp", "is before", "2026-10-03"]],
        "date_on": [["timestamp", "is on", "2026-10-02"]],
        "date_between": [["timestamp", "between", "2026-10-01", "2026-10-02"]],
        "date_open_range": [["timestamp", "between", "", "2026-10-02"]],
        "date_no_range": [["timestamp", "between", "", ""]],
        "directives": [["@ORDER_BY", "amount desc,code"], ["@LIMIT", 2], ["@OFFSET", 1]],
        "unique_directive": [["@UNIQUE", "name"]],
        "json_filters": json.dumps([["amount", "&gt;", 0]]),
        "literal_braces": [["name", "{literal}"]],
        "sql_value": [["name", "';DROP TABLE entity;--"]],
    }
    for name, value in filters.items():
        result.append({"name": name, "method": "query", "options": {"filters": value}})
    for name, options in {
        "projection_order": {"columns": ["name", "code", "missing"]},
        "distinct_values": {"distinct": "name"},
        "distinct_with_null": {"distinct": "amount"},
        "distinct_single": {"distinct": "amount", "single": True},
        "single_no_match": {"filters": [["code", "unknown"]], "single": True},
        "offset_without_limit": {"offset": 2},
        "paging": {"limit": 2, "offset": 2},
        "missing_order": {"order_bys": ["missing asc"]},
        "mixed_order": {"order_bys": ["missing asc", "amount desc", "id asc"]},
        "missing_order_directive": {"filters": [["@ORDER_BY", "missing asc,amount desc,id asc"]]},
        "retired": {"show_retired": True},
        "project_override": {"filters": [["code", "A"]]},
    }.items():
        result.append({"name": name, "method": "query", "options": options,
                       "project": "two" if name == "project_override" else "one"})
    for name, options in {
        "all_count": {}, "filtered_count": {"filters": [["name", "contains", "alpha"]]},
        "count_ignores_page": {"limit": 1, "offset": 100},
        "count_with_distinct": {"columns": ["name"], "distinct": True},
        "retired_count": {"show_retired": True},
    }.items():
        result.append({"name": name, "method": "count", "options": options})
    for method in ("codes", "ids", "columns", "tables", "keys"):
        result.append({"name": method, "method": method})
    for code in ("A", "B", "C", "D", "E", "F", "G"):
        result.append({"name": "record_" + code, "method": "record", "code": code})
    for mode in ("normal", "fast"):
        result.append({"name": "local_dict_" + mode, "method": "local_dict",
                       "options": {"filters": [["code", "A"]]}, "serialize": {"mode": mode}})
    result.append({"name": "local_dict_missing_column", "method": "local_dict",
                   "options": {"filters": [["code", "B"]]},
                   "serialize": {"columns": ["missing", "name", "amount", "metadata"], "language": "c#"}})
    for code in ("A", "B", "D", "E", "F", "G"):
        result.append({"name": "json_" + code, "method": "json", "column": "metadata",
                       "options": {"filters": [["code", code]]}, "read": {"default": {"empty": True}}})
    return result


class ReadParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="tactic-stream-read-parity-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.data = Path(cls.temp.name)
        cls.store = Store(cls.data / "new")
        cls.store.initialize(hash_password("private-test-password"))
        read_fixture(cls.store)
        cls.api = Api(cls.store)
        cls.ticket = cls.api.get_ticket("admin", "private-test-password")
        cls.cases = cases()

    def new_result(self, case):
        ticket = {"ticket": self.ticket, "project": case.get("project", "one")}
        search_type = case.get("search_type", "contract/entity")
        method, options = case["method"], case.get("options", {})
        if method == "query":
            with request_context(RequestContext(self.store, "admin", ticket["project"])):
                return self.api.query(ticket, search_type, **options)
        if method == "record":
            return self.api.dispatch("get_by_code", (ticket, search_type, case["code"]))
        if method in ("columns", "tables"):
            return self.api.dispatch("get_column_names" if method == "columns" else "get_table_info", (ticket, search_type))
        with request_context(RequestContext(self.store, "admin", ticket["project"])):
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
                return search.get_count()
            if method == "codes":
                return search.get_sobject_codes()
            if method == "ids":
                return search.get_sobject_ids()
            if method == "local_dict":
                return search.get_sobject().get_sobject_dict(**case.get("serialize", {}))
            if method == "json":
                return search.get_sobject().get_json_value(case["column"], **case.get("read", {}))
            if method == "keys":
                return SearchKey.get_by_sobjects(search.get_sobjects())
        raise ValueError(method)

    def test_reads_match_actual_original_runtime(self):
        interpreter = LEGACY / ".runtime/python/python.exe"
        if not interpreter.is_file():
            self.skipTest("Original embedded Python is required for runtime parity")
        original = self.data / "original"
        shutil.copytree(self.store.data_dir, original)
        (original / ".tactic-stream-parity").touch()
        (original / "cases.json").write_text(json.dumps(self.cases, ensure_ascii=False), encoding="utf-8")
        config = ET.Element("config", version="2")
        for section, values in {"database": {"vendor": "Sqlite", "sqlite_db_dir": str(original / "db")},
                                "security": {"version": "2", **getattr(self, 'security_config', {})},
                                "install": {}, "services": {}}.items():
            node = ET.SubElement(config, section)
            for name, value in values.items():
                ET.SubElement(node, name).text = value
        ET.ElementTree(config).write(original / "tactic-conf.xml", encoding="utf-8")
        with Store(original).connection(write=True) as db:
            # Fill original runtime dependencies only in the original fixture copy.
            for name in ("bootstrap_schema.sql", "sthpw_schema.sql"):
                schema = (LEGACY / "src/pyasm/search/upgrade/sqlite" / name).read_text(encoding="utf-8")
                schema = schema.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
                schema = schema.replace("INSERT INTO ", "INSERT OR IGNORE INTO ")
                schema = re.sub(r"CREATE (UNIQUE )?INDEX ", r"CREATE \1INDEX IF NOT EXISTS ", schema)
                db.executescript(schema)
        environment = os.environ.copy()
        environment.pop("TACTIC_TMP_CONFIG_PATH", None)
        run = subprocess.run([str(interpreter), "-B", "-X", "utf8", str(ROOT / "tools/legacy_read_probe.py"),
                              "--legacy", str(LEGACY), "--fixture", str(original)],
                             cwd=original, env=environment, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        expected = json.loads((original / "original_results.json").read_text(encoding="utf-8"))
        self.assertEqual(len(expected), len(self.cases))
        for case, record in zip(self.cases, expected):
            with self.subTest(case=case["name"]):
                self.assertEqual(record["name"], case["name"])
                result = json.loads(json.dumps(self.new_result(case), ensure_ascii=False))
                self.assert_case_result(case, result, record["result"])

    def assert_case_result(self, case, result, original):
        if case['name'] in ('date_on', 'date_between', 'date_open_range'):
            # Source includes midnight of the following day; native ranges are half-open.
            native_rows, source_rows = ast.literal_eval(result), ast.literal_eval(original)
            self.assertEqual({row['code'] for row in source_rows},
                             {'D', 'E'} if case['name'] == 'date_on' else {'A', 'D', 'E'})
            self.assertEqual(native_rows, [row for row in source_rows if row['code'] != 'E'])
            return
        if case['name'] in ('contains_underscore_wildcard', 'neq'):
            # Intentional correction: native SQLite used LIKE for regex and
            # ignored EQ/NEQ case sensitivity. Scripts need the PostgreSQL
            # regular-expression behavior (anchors, alternatives, literal _).
            actual_codes = {row['code'] for row in ast.literal_eval(result)}
            original_codes = {row['code'] for row in ast.literal_eval(original)}
            if case['name'] == 'contains_underscore_wildcard':
                self.assertEqual(actual_codes, {'D'})
                self.assertEqual(original_codes, {'D', 'E'})
            else:
                self.assertEqual(actual_codes, {None, 'A', 'B', 'D', 'G'})
                self.assertEqual(original_codes, {None, 'A', 'B', 'G'})
            return
        self.assertEqual(result, original)

    def test_read_subset_does_not_mutate_own_database(self):
        before = {path: path.read_bytes() for path in self.store.data_dir.glob("db/*.db")}
        for case in self.cases:
            self.new_result(case)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_unported_filter_dependencies_and_sql_are_rejected(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            self.api.auth.bind_security('admin', self.ticket)
            for filters in (["amount >= 0"],
                            [["other_table.code", "A"]], [["name", "@@", "secret"]]):
                with self.subTest(filters=filters), self.assertRaises(UnsupportedContract):
                    # Specialized fixtures may replace contract/entity; accounts exist in every fixture.
                    Search('sthpw/login').add_op_filters(filters)
