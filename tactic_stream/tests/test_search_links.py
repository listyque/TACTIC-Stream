"""Compare joins, subqueries and instance mappings with the original kernel."""
import xml.etree.ElementTree as ET
import test_read_parity as read_tests
from test_schema import key, relationship_fixture
from tools.legacy_read_probe import run_link_case
from pyasm.search.search import RequestContext, Search, request_context
from pyasm.common.errors import UnsupportedContract
from pyasm.biz.schema import Schema


def link_fixture(store):
    relationship_fixture(store)
    links = '''
        <connect from="contract/collection" to="contract/entity" relationship="instance" instance_type="contract/entity_in_collection"/>
        <connect from="contract/entity_in_collection" to="contract/collection" relationship="code" from_col="collection_code"/>
        <connect from="contract/entity_in_collection" to="contract/entity" relationship="code" from_col="entity_code"/>
        <connect from="sthpw/contract_ref" to="*" relationship="search_type"/>
        <connect from="sthpw/contract_id_ref" to="*" relationship="search_type"/>
    '''
    with store.connection(write=True) as db:
        for name in ("collection", "entity_in_collection"):
            stype = "contract/" + name
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                       "VALUES (?,?,'contract','{project}',?,'pyasm.search.SObject')", (stype, stype, name))
        for name, columns in (("contract_ref", "search_code text, search_id integer"), ("contract_id_ref", "search_id integer")):
            stype = "sthpw/" + name
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                       "VALUES (?,?,'sthpw','sthpw',?,'pyasm.search.SObject')", (stype, stype, name))
            db.execute(f'CREATE TABLE "{name}" (id INTEGER PRIMARY KEY, code text, search_type text, {columns}, s_status text)')
        db.executemany("INSERT INTO contract_ref VALUES (?,?,?,?,?,?)", [
            (1, "S1", "contract/entity?project=one", "A", 1, None),
            (2, "S2", "contract/entity?project=one", "B", 2, "retired"),
            (3, "S3", "contract/entity?project=one", "C", 3, None),
            (4, "S4", "contract/entity?project=two", "A", 1, None),
            (5, "S5", "contract/entity?project=one", None, None, None),
        ])
        db.executemany("INSERT INTO contract_id_ref VALUES (?,?,?,?,?)", [
            (1, "SI1", "contract/id_entity?project=one", 1, None),
            (2, "SI2", "contract/id_entity?project=one", 2, None),
        ])
        rows = db.execute('SELECT id,"schema" FROM "schema" WHERE project_code IN (\'one\',\'two\')').fetchall()
        for row in rows:
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?', (row["schema"].replace("</schema>", links + "</schema>"), row["id"]))
    for project in ("one", "two"):
        with store.connection(project, write=True) as db:
            db.execute("CREATE TABLE collection (id INTEGER PRIMARY KEY, code text, name text, s_status text)")
            db.execute("CREATE TABLE entity_in_collection (id INTEGER PRIMARY KEY, code text, collection_code text, entity_code text, s_status text)")
            db.executemany("INSERT INTO collection VALUES (?,?,?,?)", [
                (1, "G1", "First", None), (2, "G2", "Second", "retired"),
                (3, "A", "Shared code", None), (4, "EMPTY", "No links", None),
            ])
            db.executemany("INSERT INTO entity_in_collection VALUES (?,?,?,?,?)", [
                (1, "J1", "G1", "A", None), (2, "J2", "G1", "A", None),
                (3, "J3", "G1", "B", "retired"), (4, "J4", "G1", "C", None),
                (5, "J5", "G2", "A", None), (6, "J6", "G2", "missing", None),
                (7, "J7", "A", "B", None), (8, "J8", None, "D", None),
            ])


def link_cases():
    result = []
    def add(name, operation, **options):
        result.append({"name": name, "method": "search_links", "operation": operation, **options})
    for source, target, codes in (("entity", "collection", ["A", "B", "C", "D"]),
                                  ("collection", "entity", ["G1", "G2", "A", "EMPTY"])):
        for code in codes:
            add(f"instance_single_{source}_{code}", "add_relationship_filter", search_type="contract/" + target, key=key(source, code))
        for retired in (False, True):
            keys = [key(source, code) for code in codes]
            add(f"instance_list_{source}_{retired}", "add_relationship_filters", search_type="contract/" + target, keys=keys[:1], show_retired=retired)
            add(f"instance_map_{source}_{retired}", "get_related_by_sobjects", search_type="contract/" + target, keys=keys, kwargs={"show_retired": retired})
        add("instance_subquery_" + source, "add_relationship_search_filter", search_type="contract/" + target,
            sub={"search_type": "contract/" + source, "filters": [["code", codes[:2]]]}, kwargs={"op": "not in"})
    add("empty_map", "get_related_by_sobjects", keys=[])
    add("null_map", "get_related_by_sobjects", keys=[""])
    add("same_type_map", "get_related_by_sobjects", keys=[key("entity", "A")])
    for source, target, codes, kwargs in (
        ("entity", "child", ["A", "B", "C", "G"], {}),
        ("child", "entity", ["CH1", "CH2", "CH4", "CH5"], {}),
        ("child", "entity", ["CH1", "CH2"], {"path": "alternate"}),
        ("entity", "ref", ["A", "B", "C"], {}),
        ("ref", "entity", ["R1", "R3", "R4", "R6"], {}),
        ("id_entity", "id_ref", ["1", "2"], {}),
        ("id_ref", "id_entity", ["IR1", "IR3"], {}),
        ("entity", "link", ["A", "B"], {}),
    ):
        keys = [f"contract/id_entity?project=one&id={code}" if source == "id_entity" else key(source, code) for code in codes]
        add("map_" + source + "_" + target, "get_related_by_sobjects", search_type="contract/" + target, keys=keys, kwargs=kwargs)
    add("instance_map_filtered", "get_related_by_sobjects", search_type="contract/collection", keys=[key("entity", "A"), key("entity", "B")], kwargs={"filters": [["code", "A"]]})
    for retired in (False, True):
        for target, source in (("contract/child", "contract/entity"), ("contract/ref", "contract/entity"),
                               ("sthpw/contract_ref", "contract/entity"), ("contract/entity", "sthpw/contract_ref")):
            add(f"retired_subquery_{target}_{source}_{retired}", "add_relationship_search_filter", search_type=target,
                sub={"search_type": source, "show_retired": retired}, kwargs={"use_multidb": False})
    for op in ("in", "not in"):
        for project in ("one", "two"):
            for preload in (None, "objects", "count"):
                add(f"subquery_{op}_{project}_{preload}", "add_search_filter", search_type="contract/child", column="entity_code",
                    sub={"search_type": "contract/entity?project=" + project, "columns": [{"column": "code"}], "preload": preload}, kwargs={"op": op})
        add("subquery_capture_" + op, "add_search_filter", search_type="contract/child", column="entity_code",
            sub={"search_type": "contract/entity", "columns": [{"column": "code"}], "filters": [["code", "A"]], "change_after_capture": True}, kwargs={"op": op})
        add("subquery_page_" + op, "add_search_filter", search_type="contract/child", column="entity_code",
            sub={"search_type": "contract/entity", "columns": [{"column": "code"}], "limit": 2, "offset": 1, "order_bys": ["code desc"]}, kwargs={"op": op})
        for target, source, path in (("child", "entity", None), ("entity", "child", None),
                                     ("child", "entity", "by_id"), ("child", "entity", "alternate"),
                                     ("ref", "entity", None), ("entity", "ref", None),
                                     ("id_ref", "id_entity", None), ("id_entity", "id_ref", None),
                                     ("entity", "entity", None)):
            add(f"relationship_subquery_{op}_{target}_{source}_{path}", "add_relationship_search_filter", search_type="contract/" + target,
                sub={"search_type": "contract/" + source}, kwargs={"op": op, "path": path})
        for target, source in (("sthpw/contract_ref", "contract/entity"), ("contract/entity", "sthpw/contract_ref"),
                               ("sthpw/contract_id_ref", "contract/id_entity"), ("contract/id_entity", "sthpw/contract_id_ref")):
            for empty in (False, True):
                for delay in (False, True):
                    add(f"system_subquery_{op}_{target}_{empty}_{delay}", "add_relationship_search_filter", search_type=target,
                        sub={"search_type": source, "filters": [["id", -100]] if empty else []}, kwargs={"op": op, "delay_null": delay})
    add("null_search", "add_relationship_search_filter", sub=None)
    add("cross_database_ignores_table", "add_search_filter", search_type="contract/child", column="entity_code",
        sub={"search_type": "contract/entity?project=two", "columns": [{"column": "code"}]}, kwargs={"table": "unused"})
    for join in ("LEFT OUTER", "INNER", "RIGHT OUTER"):
        add("join_" + join, "join", search_type="contract/child", joins=[{"to_search_type": "contract/entity", "join": join}],
            columns=[{"column": "*"}, {"column": "name", "table": "entity", "as_column": "parent_name"}], order_bys=["entity.name desc"], limit=3)
    add("join_count_ignores_page_distinct", "join", joins=[{"to_search_type": "contract/child"}],
        columns=[{"column": "name", "distinct": True}], limit=1)
    add("join_deduplicated", "join", search_type="contract/child", joins=[{"to_search_type": "contract/entity"}, {"to_search_type": "contract/entity", "path": "alternate"}])
    add("instance_three_tables", "join", joins=[{"to_search_type": "contract/entity_in_collection"}, {"to_search_type": "contract/collection", "from_search_type": "contract/entity_in_collection"}],
        columns=[{"column": "*"}, {"column": "code", "table": "collection", "as_column": "_related_code"}], filters=[["code", "A"]])
    for retired in (False, True):
        for projection in (None, ["code", "_related_code"]):
            result.append({"name": f"xmlrpc_instance_{retired}_{projection}", "method": "query", "search_type": "contract/collection",
                           "options": {"parent_key": key("entity", "A"), "show_retired": retired, "columns": projection}})
    result.append({"name": "xmlrpc_instance_reverse", "method": "query",
                   "options": {"parent_key": key("collection", "G1")}})
    for target, order in (("contract/entity", "entity_in_collection.collection.name desc"),
                           ("contract/child", "contract/entity.name"),
                           ("contract/entity", "child.code")):
        result.append({"name": "xmlrpc_join_order_" + target, "method": "query", "search_type": target,
                       "options": {"order_bys": [order], "limit": 5}})
    result.append({"name": "sort_first_direction_wins", "method": "query",
                   "options": {"order_bys": ["code desc", "code asc"]}})
    for target, source, code, expected in (
        ('entity', 'collection', 'G1', ['A', 'A', 'B']),
        ('entity', 'collection', 'A', ['B']),
        ('entity', 'collection', 'EMPTY', []),
        ('entity', 'collection', 'G2', ['A']),
        ('collection', 'entity', 'A', ['G1', 'G1']),
        ('collection', 'entity', 'B', ['A', 'G1']),
        ('collection', 'entity', 'D', []),
    ):
        add(f'instance_children_{target}_{code}', 'children_alter_search', search_type='contract/' + target,
            key=key(source, code), source_error='SqlException', expected_codes=expected)
    for source, target, code, included, excluded in (
        ('entity', 'collection', 'A', ['G1', 'G1'], ['A', 'G1', 'G1']),
        ('collection', 'entity', 'G1', ['A', 'A', 'B'], ['A', 'B']),
    ):
        for op, expected in (('in', included), ('not in', excluded)):
            add(f'instance_batch_{source}_{op}', 'add_relationship_filters',
                search_type='contract/' + target, keys=[key(source, code)], kwargs={'op': op},
                expected_codes=expected)
            for preload in (None, 'objects', 'count'):
                add(f'instance_query_{source}_{op}_{preload}', 'add_relationship_search_filter',
                    search_type='contract/' + target,
                    sub={'search_type': 'contract/' + source, 'filters': [['code', code]], 'preload': preload},
                    kwargs={'op': op}, expected_codes=expected)
        for op in ('in', 'not in'):
            add(f'instance_query_empty_{source}_{op}', 'add_relationship_search_filter',
                search_type='contract/' + target,
                sub={'search_type': 'contract/' + source, 'filters': [['code', 'no-match']]},
                kwargs={'op': op}, expected_codes=[])
    for method, expected in (('codes', 'A'), ('ids', 1)):
        for label, columns, source_value in (
            ('name', [{'column': 'name'}], 'Первый'),
            ('star', [{'column': '*'}], 1),
            ('aliases', [{'column': 'name', 'as_column': 'code'}, {'column': 'code', 'as_column': 'id'}], 'Первый'),
        ):
            add(f'key_helper_{method}_{label}', method, filters=[['code', 'A']], columns=columns,
                expected_values=[expected], source_values=[source_value])
        add(f'key_helper_{method}_null_code', method, filters=[['id', 4]], columns=[{'column': 'name'}],
            expected_values=[None if method == 'codes' else 4], source_values=['By id'])
        add(f'key_helper_{method}_retired', method, filters=[['code', 'C']], columns=[{'column': 'name'}],
            show_retired=True, expected_values=['C' if method == 'codes' else 3], source_values=['Archived'])
        add(f'key_helper_{method}_hidden_retired', method, filters=[['code', 'C']], columns=[{'column': 'name'}],
            expected_values=[], source_values=[])
        add(f'key_helper_{method}_page', method, filters=[['code', ['A', 'B']]], columns=[{'column': 'name'}],
            order_bys=['id desc'], limit=1, expected_values=['B' if method == 'codes' else 2], source_values=["O'Reilly"])
        add(f'key_helper_{method}_null_filter', method, columns=[{'column': 'name'}], null_filter=True,
            expected_values=[])
        add(f'key_helper_{method}_project_two', method, filters=[['code', 'A']], columns=[{'column': 'name'}],
            project='two', expected_values=[expected], source_values=['Второй'])
        for label, column, source_value in (('name', 'name', 'First'), ('code', 'code', 'G1')):
            add(f'key_helper_{method}_joined_{label}', method,
                joins=[{'to_search_type': 'contract/entity_in_collection'},
                       {'to_search_type': 'contract/collection', 'from_search_type': 'contract/entity_in_collection'}],
                columns=[{'column': column, 'table': 'collection', 'as_column': 'code'}],
                filters=[['code', 'A'], ['collection.code', 'G1']],
                expected_values=[expected, expected], source_values=[source_value, source_value])
    return result


class SearchLinksParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        link_fixture(cls.store)
        cls.cases = link_cases()

    def new_result(self, case):
        if case["method"] == "query":
            return super().new_result(case)
        with request_context(RequestContext(self.store, "admin", case.get("project", "one"))):
            return run_link_case(Search, case)

    def assert_case_result(self, case, result, original):
        if case['name'].startswith('key_helper_'):
            self.assertEqual(result['values'], case['expected_values'])
            self.assertEqual(result['columns'], original['columns'])
            if 'source_values' in case:
                self.assertEqual(original['values'], case['source_values'])
        elif case['name'].startswith(('instance_batch_', 'instance_query_')):
            if case['name'].startswith('instance_batch_'):
                # The source JOIN contains rows for inputs that were never supplied.
                requested = 'A' if '_entity_' in case['name'] else 'G1'
                self.assertTrue(any(row['_related_code'] != requested for row in original['rows']))
            else:
                # The source count also bypasses the null flag of an empty search.
                if '_empty_' in case['name']:
                    expected_source_count = 1 if '_entity_' in case['name'] else 5
                else:
                    expected_source_count = 2 if '_entity_' in case['name'] else 3
                self.assertEqual(original['count'], expected_source_count)
            self.assertEqual([row['code'] for row in result['rows']], case['expected_codes'])
            self.assertEqual(result['count'], len(case['expected_codes']))
        elif case['name'].startswith('instance_list_'):
            source = 'entity' if '_entity_' in case['name'] else 'collection'
            if source == 'entity':
                expected = ['G1', 'G1', 'G2'] if case['show_retired'] else ['G1', 'G1']
            else:
                expected = ['A', 'A', 'B', 'C'] if case['show_retired'] else ['A', 'A', 'B']
            self.assertGreater(original['count'], len(expected))
            self.assertEqual([row['code'] for row in result['rows']], expected)
            self.assertEqual(result['count'], len(expected))
        elif case['name'] == 'instance_subquery_entity':
            self.assertEqual([row['code'] for row in original['rows']], ['A', 'G1', 'G1', 'G1'])
            self.assertEqual([row['code'] for row in result['rows']], ['G1'])
            self.assertEqual(result['rows'][0]['_related_code'], 'C')
        elif case['name'] == 'instance_subquery_collection':
            self.assertEqual([row['code'] for row in original['rows']], ['A', 'A', 'B'])
            self.assertEqual([row['code'] for row in result['rows']], ['A', 'B'])
            self.assertEqual(result['count'], 2)
        elif case.get('operation') == 'children_alter_search':
            self.assertEqual(original['error'], 'SqlException')
            self.assertIn('no such column', original['message'])
            self.assertTrue(result['applied'])
            self.assertEqual([row['code'] for row in result['rows']], case['expected_codes'])
            self.assertEqual(result['count'], len(case['expected_codes']))
        elif case['name'].startswith('instance_single_collection_'):
            code = case['name'].removeprefix('instance_single_collection_')
            self.assertEqual([row['code'] for row in original['rows']], ['A', 'A', 'A'] if code == 'A' else [])
            expected = {'G1': ['A', 'A', 'B'], 'G2': ['A'], 'A': ['B'], 'EMPTY': []}[code]
            self.assertEqual([row['code'] for row in result['rows']], expected)
            self.assertEqual(result['count'], len(expected))
            self.assertEqual({row['_related_code'] for row in result['rows']}, {code} if expected else set())
        elif case['name'].startswith('xmlrpc_instance_') and case['name'] != 'xmlrpc_instance_reverse':
            import ast
            source_rows, rows = ast.literal_eval(original), ast.literal_eval(result)
            retired = case['options']['show_retired']
            self.assertEqual({row['code'] for row in source_rows}, {'G1', 'G2', 'A', 'EMPTY'} if retired else {'G1', 'A', 'EMPTY'})
            self.assertEqual([row['code'] for row in rows], ['G1', 'G1', 'G2'] if retired else ['G1', 'G1'])
        elif case['name'] == 'xmlrpc_instance_reverse':
            import ast
            self.assertEqual({row['code'] for row in ast.literal_eval(original)}, {None, 'A', 'B', 'D', 'E', 'F', 'G'})
            self.assertEqual([row['code'] for row in ast.literal_eval(result)], ['A', 'A', 'B'])
            self.assertEqual({row['_related_code'] for row in ast.literal_eval(result)}, {'G1'})
        else:
            super().assert_case_result(case, result, original)

    def test_object_reference_joins_and_named_sort_paths(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            search = Search("contract/ref")
            search.add_join("contract/entity")
            self.assertEqual(search.get_sobject_codes(), ['R1', 'R2', 'R4', 'R6'])
            search = Search("contract/child")
            search.add_order_by("alternate:contract/entity.name")
            self.assertEqual(search.get_sobject_codes(), ['CH1', 'CH2', 'CH4', 'CH5'])

    def test_key_helpers_preserve_projection_duplicates_hooks_and_rollback(self):
        from pyasm.command import Command
        from pyasm.search import SObject
        from unittest.mock import patch
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_search_key(key('collection', 'G1'))
            result = parent.get_all_children_search('contract/entity')
            before = tuple(result.select.as_columns)
            self.assertEqual(result.get_sobject_codes(), ['A', 'A', 'B'])
            self.assertEqual(result.get_sobject_ids(), [1, 1, 2])
            self.assertEqual(result.get_sobject_codes(), ['A', 'A', 'B'])
            self.assertEqual(tuple(result.select.as_columns[:len(before)]), before)
            self.assertEqual(result.select.columns.count('code'), 1)
            self.assertEqual(result.select.columns.count('id'), 1)
            self.assertEqual([obj.get_code() for obj in result.get_sobjects()], ['A', 'A', 'B'])
            staged = Search.get_by_search_key(key('entity', 'A'))
            staged.set_value('code', 'UNCOMMITTED_KEY')
            stored = Search('contract/entity')
            stored.add_filter('id', 1)
            self.assertEqual(stored.get_sobject_codes(), ['A'])
            self.assertEqual(stored.get_sobject_ids(), [1])
            staged.set_value('code', 'A')
            distinct = Search('contract/entity')
            distinct.add_join('contract/entity_in_collection')
            distinct.add_join('contract/collection', from_search_type='contract/entity_in_collection')
            distinct.add_column('name', table='collection', distinct=True)
            distinct.add_filter('code', 'A')
            self.assertEqual(distinct.get_sobject_codes(), ['A', 'A'])
            self.assertEqual(distinct.get_sobject_ids(), [1, 1])
            search = Search('contract/entity')
            search.add_column('name')
            with patch.object(SObject, 'alter_search', side_effect=lambda query: query.add_filter('code', 'A')) as hook:
                self.assertEqual(search.get_sobject_codes(), ['A'])
                self.assertEqual(search.get_sobject_ids(), [1])
                self.assertEqual(hook.call_count, 1)
            def execute():
                obj = Search.get_by_search_key(key('entity', 'A'))
                obj.set_value('name', 'temporary key helper write')
                obj.commit()
                search = Search('contract/entity')
                search.add_column('name', as_column='code')
                search.add_filter('code', 'A')
                self.assertEqual(search.get_sobject_codes(), ['A'])
                self.assertEqual(search.get_sobject_ids(), [1])
                raise ValueError('key helper rollback')
            command = Command()
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'key helper rollback'):
                Command.execute_cmd(command)
            self.assertEqual(Search.get_by_search_key(key('entity', 'A')).get_value('name'), 'Первый')

    def test_key_helpers_recheck_nested_read_policy_and_restore(self):
        from pyasm.common import Container
        from pyasm.common.errors import SecurityException
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            search = Search('contract/entity')
            search.add_column('name')
            search.add_filter('code', 'A')
            self.assertEqual(search.get_sobject_codes(), ['A'])
            def deny(base):
                if base == 'contract/entity':
                    raise SecurityException('key helper nested read denied')
            previous = Container.get('Expression:check_record_access')
            try:
                Container.put('Expression:check_record_access', deny)
                for lookup in (search.get_sobject_codes, search.get_sobject_ids):
                    with self.assertRaisesRegex(SecurityException, 'key helper nested read'):
                        lookup()
            finally:
                Container.put('Expression:check_record_access', previous)
            self.assertEqual(search.get_sobject_codes(), ['A'])
            self.assertEqual(search.get_sobject_ids(), [1])

    def test_public_sort_cannot_join_security_records(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            # Schema changes here live only in this request, without database writes.
            schema = Schema.get(project_code="sthpw")
            ET.SubElement(schema.xml, "connect", {"from": "sthpw/project", "to": "sthpw/login",
                          "relationship": "code", "from_col": "code", "to_col": "login"})
            from pyasm.common.errors import SecurityException
            with self.assertRaisesRegex(SecurityException, 'administrator access'):
                self.api.query({}, "sthpw/project", order_bys=["login.password"])

    def test_instance_children_use_actual_join_columns_and_restore_after_rollback(self):
        from pyasm.command import Command
        from pyasm.biz import Schema
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            schema = Schema.get()
            for node in schema.xml.findall('connect'):
                if (node.get('from'), node.get('to')) == ('contract/collection', 'contract/entity'):
                    node.set('from_col', 'name')
                    node.set('to_col', 'code')
                elif (node.get('from'), node.get('to')) == ('contract/entity_in_collection', 'contract/collection'):
                    node.set('to_col', 'name')
            def execute():
                links = Search('contract/entity_in_collection')
                links.set_show_retired(True)
                links.add_filter('collection_code', 'G1')
                for link in links.get_sobjects():
                    link.set_value('collection_code', 'First')
                    link.commit()
                parent = Search.get_by_search_key(key('collection', 'G1'))
                self.assertEqual([obj.get_code() for obj in parent.get_all_children('contract/entity')], ['A', 'A', 'B'])
                grouped = Search.get_related_by_sobjects([parent], 'contract/entity')
                self.assertEqual([obj.get_code() for obj in grouped[parent.get_search_key()]], ['A', 'A', 'B'])
                self.assertEqual([obj.get_value('_related_code') for obj in grouped[parent.get_search_key()]], ['First'] * 3)
                for source, target, identity, expected in (
                    ('collection', 'entity', 'G1', ['A', 'A', 'B']),
                    ('entity', 'collection', 'A', ['G1', 'G1']),
                ):
                    selected = Search('contract/' + source)
                    selected.add_column('name', as_column='code')
                    selected.add_column('code', as_column='name')
                    selected.add_filter('code', identity)
                    selected.get_sobjects()
                    result = Search('contract/' + target)
                    result.add_relationship_search_filter(selected)
                    self.assertEqual([obj.get_code() for obj in result.get_sobjects()], expected)
                parent = Search.get_by_search_key(key('entity', 'A'))
                self.assertEqual([obj.get_code() for obj in parent.get_all_children('contract/collection')], ['G1', 'G1'])
                raise ValueError('instance relationship rollback')
            command = Command()
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'instance relationship rollback'):
                Command.execute_cmd(command)
        auth = {'ticket': self.ticket, 'project': 'one'}
        rows = self.api.dispatch('get_all_children', (auth, key('collection', 'G1'), 'contract/entity'), {'columns': ['code']})
        self.assertEqual([row['code'] for row in rows], ['A', 'A', 'B'])

    def test_instance_children_require_instance_read_access(self):
        from pyasm.security.authenticator import hash_password
        from pyasm.common.errors import SecurityException
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('instance_reader','instance_reader',?)", (hash_password('private-reader-password'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('instance_readers','instance_readers',?)", ('<rules><rule group="search_type" code="contract/entity_in_collection" project="one" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('instance_reader_group','instance_reader','instance_readers')")
        auth = {'ticket': self.api.get_ticket('instance_reader', 'private-reader-password'), 'project': 'one'}
        try:
            self.assertEqual(self.api.dispatch('get_by_search_key', (auth, key('collection', 'G1')))['code'], 'G1')
            self.assertEqual(self.api.dispatch('get_by_search_key', (auth, key('entity', 'A')))['code'], 'A')
            for parent, child in ((key('collection', 'G1'), 'contract/entity'), (key('entity', 'A'), 'contract/collection')):
                with self.assertRaises(SecurityException):
                    self.api.dispatch('get_all_children', (auth, parent, child), {'columns': ['code']})
            with request_context(RequestContext(self.store, 'instance_reader', 'one')):
                self.api.auth.bind_security('instance_reader', auth['ticket'])
                from pyasm.security import Sudo
                sudo = Sudo()
                try:
                    forbidden = Search('contract/entity_in_collection')
                finally:
                    sudo.exit()
                self.assertEqual(forbidden.get_sobject_codes(), [])
                self.assertEqual(forbidden.get_sobject_ids(), [])
                source = Search.get_by_search_key(key('collection', 'G1'))
                with self.assertRaises(SecurityException):
                    Search('contract/entity').add_relationship_filters([source])
                selected = Search('contract/collection')
                selected.add_filter('code', 'G1')
                with self.assertRaises(SecurityException):
                    Search('contract/entity').add_relationship_search_filter(selected)
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='instance_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='instance_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='instance_readers'")
                db.execute("DELETE FROM login WHERE code='instance_reader'")

    def test_instance_children_reject_ambiguous_self_and_cross_resource_links(self):
        from pyasm.biz import Schema
        from pyasm.common.errors import UnsupportedContract
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_search_key(key('collection', 'G1'))
            with self.assertRaisesRegex(UnsupportedContract, 'Cross-resource instance'):
                parent.get_all_children('contract/entity?project=two')
            with self.assertRaisesRegex(UnsupportedContract, 'Cross-resource instance'):
                Search('contract/entity?project=two').add_relationship_search_filter(Search('contract/collection'))
            for objects in ([parent], [parent, Search.get_by_search_key(key('collection', 'G1', 'two'))],
                            [parent, Search.get_by_search_key(key('entity', 'A'))]):
                with self.assertRaisesRegex(UnsupportedContract, 'Instance lists require'):
                    Search('contract/entity?project=two').add_relationship_filters(objects)
            schema = Schema.get()
            ET.SubElement(schema.xml, 'connect', {'from': 'contract/entity', 'to': 'contract/entity', 'relationship': 'instance', 'instance_type': 'contract/entity_in_collection'})
            parent = Search.get_by_search_key(key('entity', 'A'))
            with self.assertRaises(UnsupportedContract):
                parent.get_all_children('contract/entity')
