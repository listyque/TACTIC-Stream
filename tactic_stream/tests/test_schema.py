"""Schema and relationship parity against the original, on disposable projects."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

import test_read_parity as read_tests
from tactic_stream.server.api import Api
from pyasm.common.errors import UnsupportedContract
from pyasm.biz.project import Project, ProjectType
from pyasm.biz.schema import Schema
from pyasm.search.search import RequestContext, Search, SearchKey, SearchType, SObject, request_context
from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store


def relationship_fixture(store):
    base = '''<schema parent="__NONE__">
        <search_type name="contract/inherited" label="Inherited"/>
        <connect from="contract/inherited" to="contract/entity" relationship="code"/>
    </schema>'''
    xml = '''<schema parent="base">
        <search_type name="contract/entity" label="Entity"/>
        <search_type name="contract/child" label="Child"/>
        <search_type name="contract/ref"/>
        <connect from="contract/child" to="contract/entity" type="hierarchy" relationship="code" from_col="entity_code"/>
        <connect from="contract/child" to="contract/entity" path="alternate" relationship="code" from_col="alternate_entity_code"/>
        <connect from="contract/child" to="contract/entity" path="by_id" relationship="id" from_col="entity_id" to_col="id"/>
        <connect from="contract/id_child" to="contract/entity" relationship="id"/>
        <connect from="contract/broken" to="contract/entity" relationship="code" from_col="missing_column"/>
        <connect from="contract/ref" to="*" type="hierarchy" relationship="search_type"/>
        <connect from="contract/id_ref" to="*" type="hierarchy" relationship="search_type"/>
        <connect from="contract/link" to="*" type="hierarchy" relationship="search_type" prefix="src"/>
        <connect from="contract/tag" to="contract/entity" path="first" relationship="code" from_col="first_entity"/>
        <connect from="contract/tag" to="contract/entity" path="last" relationship="code" from_col="last_entity"/>
        <connect from="contract/old_child" to="contract/entity" type="hierarchy"/>
        <connect from="contract/many" to="contract/entity" relationship="instance" instance_type="contract/link"/>
    </schema>'''
    definitions = {
        "child": "entity_code text, alternate_entity_code text, entity_id integer",
        "id_child": "entity_id integer", "broken": "entity_code text",
        "ref": "search_type text, search_code text, search_id integer",
        "id_ref": "search_type text, search_id integer",
        "link": "src_search_type text, src_search_code text, search_code text",
        "id_entity": "name text", "tag": "first_entity text, last_entity text",
        "old_child": "entity_code text", "many": "entity_code text", "inherited": "entity_code text",
    }
    with store.connection(write=True) as db:
        for name in definitions:
            stype = "contract/" + name
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                       "VALUES (?,?,'contract','{project}',?,'pyasm.search.SObject')", (stype, stype, name))
        db.executemany('INSERT INTO "schema" (code,project_code,"schema") VALUES (?,?,?)', [
            ("base", None, base), ("one", "one", xml),
            ("two_definition", "two", xml.replace('from_col="entity_code"', 'from_col="alternate_entity_code"', 1)),
            ("later", "one", '<schema parent="__NONE__"><search_type name="ignored/later"/></schema>'),
        ])
        db.execute("INSERT INTO project_type (code,type) VALUES ('prod_kind','prod')")
        db.executemany("INSERT INTO project (code,title,type) VALUES (?,?,?)", [
            ("typed", "Typed", "prod_kind"), ("empty", "Empty", None), ("unittest", "Unit test", None)])
    for project in ("one", "two", "typed", "empty", "unittest"):
        if project in ("typed", "empty", "unittest"):
            store.database_path(project).touch()
        with store.connection(project, write=True) as db:
            for name, columns in definitions.items():
                # id_entity deliberately has no code column.
                code = "" if name == "id_entity" else "code text, "
                db.execute(f'CREATE TABLE "{name}" (id INTEGER PRIMARY KEY, {code}{columns}, s_status text)')
            db.executemany("INSERT INTO child VALUES (?,?,?,?,?,?)", [
                (1, "CH1", "A", "B", 2, None), (2, "CH2", "A", "A", 1, None),
                (3, "CH3", "B", "A", 1, "retired"), (4, "CH4", None, "A", None, None),
                (5, "CH5", "C", "A", 3, None),
            ])
            db.execute("INSERT INTO id_child VALUES (1,'IC1',1,NULL)")
            db.execute("INSERT INTO broken VALUES (1,'BROKEN','A',NULL)")
            db.executemany("INSERT INTO ref VALUES (?,?,?,?,?,?)", [
                (1, "R1", f"contract/entity?project={project}", "A", 1, None),
                (2, "R2", f"contract/entity?project={project}", "B", 2, None),
                (3, "R3", "contract/entity?project=other", "A", 1, None),
                (4, "R4", f"contract/entity?project={project}", "C", 3, None),
                (5, "R5", "", None, None, None),
                (6, "R6", f"contract/entity?project={project}", None, 1, None),
            ])
            db.executemany("INSERT INTO id_entity VALUES (?,?,?)", [(1, "By id", None), (2, "Retired", "retired")])
            db.executemany("INSERT INTO id_ref VALUES (?,?,?,?,?)", [
                (1, "IR1", f"contract/id_entity?project={project}", 1, None),
                (2, "IR2", f"contract/entity?project={project}", 2, None),
                (3, "IR3", f"contract/id_entity?project={project}", 2, None),
            ])
            db.execute("INSERT INTO link VALUES (1,'L1',?,'A','B',NULL)", (f"contract/entity?project={project}",))
            db.execute("INSERT INTO tag VALUES (1,'TAG','A','B',NULL)")
            db.execute("INSERT INTO old_child VALUES (1,'OLD','A',NULL)")
            db.execute("INSERT INTO inherited VALUES (1,'INH','A',NULL)")


def key(name, code, project="one"):
    return f"contract/{name}?project={project}&code={code}"


def relationship_cases():
    result = []
    def add(name, method, **values):
        result.append({"name": name, "method": method, **values})
    for name, operation, args, kwargs in [
        ("types", "get_search_types", [], {}), ("own_types", "get_search_types", [], {"hierarchy": False}),
        ("attrs_own", "get_attrs_by_search_type", ["contract/entity"], {}),
        ("attrs_inherited", "get_attrs_by_search_type", ["contract/inherited"], {}),
        ("attrs_admin", "get_attrs_by_search_type", ["sthpw/login"], {}),
        ("attr_missing", "get_attr_by_search_type", ["missing/type", "label"], {}),
        ("attr_no_inheritance", "get_attr_by_search_type", ["contract/inherited", "label"], {}),
        ("related_children", "get_related_search_types", ["contract/entity", "children"], {}),
        ("related_parent", "get_related_search_types", ["contract/child", "parent"], {}),
        ("parent_type", "get_parent_type", [key("child", "CH1")], {}),
        ("child_types", "get_child_types", ["contract/entity"], {}),
        ("own_child_types", "get_child_types", ["contract/entity"], {"hierarchy": False}),
        ("wildcard_parent_type", "get_parent_type", ["contract/ref"], {}),
        ("admin_parent_type", "get_parent_type", ["sthpw/task"], {}),
        ("schema_first_row", "get_code", [], {}),
        ("forward", "get_relationship_attrs", ["contract/child", "contract/entity"], {}),
        ("reverse", "get_relationship_attrs", ["contract/entity", "contract/child"], {}),
        ("alternate", "get_relationship_attrs", ["contract/child", "contract/entity"], {"path": "alternate"}),
        ("id", "get_relationship_attrs", ["contract/child", "contract/entity"], {"path": "by_id"}),
        ("disabled", "get_relationship_attrs", ["contract/broken", "contract/entity"], {}),
        ("hierarchy_filter", "get_relationship_attrs", ["contract/child", "contract/entity"], {"type": "hierarchy"}),
        ("path_missing", "get_relationship_attrs", ["contract/child", "contract/entity"], {"path": "missing"}),
        ("last_path_fallback", "get_relationship_attrs", ["contract/tag", "contract/entity"], {}),
        ("old_hierarchy", "get_relationship_attrs", ["contract/old_child", "contract/entity"], {}),
        ("unrelated", "get_relationship_attrs", ["contract/entity", "missing/type"], {}),
        ("wildcard", "get_relationship_attrs", ["contract/ref", "contract/entity"], {}),
        ("foreign_keys", "get_foreign_keys", ["contract/child", "contract/entity"], {}),
    ]:
        add(name, "schema", operation=operation, args=args, kwargs=kwargs)
    for code in ("admin", "simple", "prod", "flash", "unittest", "config"):
        add("predefined_" + code, "schema", predefined=code, operation="get_search_types")
    add("id_default_original_error", "schema_error", args=["contract/id_child", "contract/entity"])
    for project in ("two", "typed", "empty", "admin", "sthpw", "unittest"):
        add("project_schema_" + project, "schema", operation="get_search_types", project=project)
    add("schema_project_column", "schema", operation="get_code", project="two")
    for types in (("contract/ref", "contract/entity"), ("contract/entity", "contract/ref"),
                  ("contract/id_ref", "contract/id_entity"), ("contract/link", "contract/entity")):
        add("resolve_" + "_".join(types), "schema_resolve", args=list(types))
    for name, code in (("child", "CH1"), ("child", "CH4"), ("child", "CH5"),
                       ("ref", "R1"), ("ref", "R4"), ("ref", "R5"), ("ref", "R6"),
                       ("id_ref", "IR1"), ("id_ref", "IR2"), ("link", "L1")):
        add("parent_" + code, "parent", key=key(name, code))
    add("parent_retired_visible", "parent", key=key("child", "CH5"), kwargs={"show_retired": True})
    for call, args, kwargs in [
        ("get_related_types", ["contract/entity"], {}),
        ("get_parent_type", [key("child", "CH1")], {}),
        ("get_child_types", ["contract/entity"], {}),
        ("get_types_from_instance", ["contract/link"], {}),
        ("get_parent", [key("child", "CH1")], {}),
        ("get_parent", [{"__search_key__": key("child", "CH1")}], {"columns": ["name"]}),
        ("get_parent", [key("child", "CH1")], {"columns": ["name", "missing"]}),
        ("get_parent", [key("id_ref", "IR1")], {"columns": ["id", "name"]}),
        ("get_parent", [key("link", "L1")], {"columns": ["code"]}),
        ("get_parent", [key("ref", "R4")], {"columns": ["code"], "show_retired": False}),
        ("get_parent", [key("ref", "R4")], {"columns": ["code"], "show_retired": True}),
        ("get_parent", [key("ref", "R5")], {"columns": ["code"]}),
        ("get_parent", [key("child", "CH5")], {"show_retired": False}),
        ("get_parent", [key("ref", "R4")], {"show_retired": False}),
        ("get_parent", [key("ref", "R5")], {}),
        ("get_all_children", [key("entity", "A"), "contract/child"], {}),
        ("get_all_children", [key("entity", "A"), "contract/child"], {"filters": [["code", "CH2"]], "columns": ["code"]}),
        ("get_all_children", [key("entity", "A"), "contract/child"], {"columns": ["entity_code", "missing"]}),
        ("get_all_children", [key("entity", "A"), "contract/child"], {"columns": ["code"], "filters": [["code", "missing"]]}),
        ("get_all_children", [key("entity", "B"), "contract/child"], {"columns": ["code"]}),
    ]:
        add(f"api_{call}_{len(result)}", "api_body", call=call, args=args, kwargs=kwargs)
    for method in ("related", "children", "relationship_filter", "parent_filter"):
        add(method + "_code", method, key=key("entity", "A"), search_type="contract/child")
        add(method + "_polymorphic", method, key=key("entity", "A"), search_type="contract/ref")
    add("related_alternate", "related", key=key("entity", "A"), search_type="contract/child", kwargs={"path": "alternate"})
    add("related_by_id", "related", key=key("entity", "A"), search_type="contract/child", kwargs={"path": "by_id"})
    add("related_same", "related", key=key("entity", "A"), search_type="contract/entity")
    add("related_disabled", "related", key=key("entity", "A"), search_type="contract/broken")
    add("prefix_reverse_quirk", "related", key=key("link", "L1"), search_type="contract/entity")
    add("prefix_forward", "related", key=key("entity", "A"), search_type="contract/link")
    for stype, keys, kwargs in [
        ("contract/child", [key("entity", "A"), key("entity", "B")], {}),
        ("contract/child", [key("entity", "A")], {"op": "not in"}),
        ("contract/ref", [key("entity", "A"), key("entity", "B")], {}),
        ("contract/ref", [key("entity", "A"), key("entity", "A", "two")], {}),
        ("contract/entity", [key("ref", "R1"), key("ref", "R2"), key("ref", "R3")], {}),
        ("contract/entity", [key("entity", "A"), key("entity", "B")], {}),
        ("contract/child", [], {}),
    ]:
        add("relationship_many_" + str(len(result)), "relationship_filters", search_type=stype, keys=keys, kwargs=kwargs)
    for name, code in (("ref", "R1"), ("ref", "R6"), ("id_ref", "IR1")):
        add("parent_key_" + code, "parent_key", key=key(name, code))
    for stype in ("contract/child", "contract/ref"):
        add("query_parent_" + stype, "query", search_type=stype, options={"parent_key": key("entity", "A")})
    add("query_parent_same", "query", options={"parent_key": key("entity", "A")})
    add("query_parent_other_project", "query", search_type="contract/child?project=two", options={"parent_key": key("entity", "A", "two")})
    add("stype_related", "stype_related", search_type="contract/entity")
    return result


class SchemaParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        relationship_fixture(cls.store)
        cls.cases = relationship_cases()

    def new_result(self, case):
        method = case["method"]
        if method in ("query", "record", "columns", "tables"):
            return super().new_result(case)
        project = case.get("project", "one")
        ticket = {"ticket": self.ticket, "project": project}
        if method == "api_body":
            return self.api.dispatch(case["call"], (ticket, *case.get("args", []))) if not case.get("kwargs") else self.call_with_kwargs(ticket, case)
        with request_context(RequestContext(self.store, "admin", project)):
            if method == "schema":
                schema = Schema.get_predefined_schema(case["predefined"]) if "predefined" in case else Schema.get()
                return getattr(schema, case["operation"])(*case.get("args", []), **case.get("kwargs", {}))
            if method == "schema_resolve":
                schema = Schema.get()
                attrs = schema.get_relationship_attrs(*case["args"])
                return schema.resolve_relationship_attrs(attrs, *case["args"])
            if method == "schema_error":
                return Schema.get().get_relationship_attrs(*case["args"])
            if method == "stype_related":
                return SearchType.get_related_types(case["search_type"], **case.get("kwargs", {}))
            source = Search.get_by_search_key(case["key"]) if "key" in case else None
            if method == "parent":
                return Api._record(source.get_parent(**case.get("kwargs", {})))
            if method == "parent_key":
                return source.get_parent_search_key()
            stype = case["search_type"]
            if method == "related":
                objects = source.get_related_sobjects(stype, **case.get("kwargs", {}))
            elif method == "children":
                objects = source.get_all_children(stype)
            else:
                search = Search(stype)
                if method == "relationship_filters":
                    objects = [Search.get_by_search_key(key) for key in case["keys"]]
                    search.add_relationship_filters(objects, **case.get("kwargs", {}))
                elif method == "relationship_filter":
                    search.add_relationship_filter(source, **case.get("kwargs", {}))
                else:
                    search.add_parent_filter(source)
                objects = search.get_sobjects()
            return [obj.get_search_key() for obj in objects]

    def assert_case_result(self, case, result, original):
        if case['method'] == 'api_body' and case.get('kwargs', {}).get('columns'):
            # Source _get_sobjects_dict overwrites the requested columns with result.keys().
            columns = [*case['kwargs']['columns'], '__search_key__', '__search_type__']
            def projected(row):
                return {name: row.get(name) for name in columns} if row else {}
            expected = [projected(row) for row in original] if isinstance(original, list) else projected(original)
            self.assertEqual(result, expected)
        elif case['name'] == 'id_default_original_error':
            self.assertEqual(original['error'], 'AttributeError')
            self.assertEqual(result, dict(relationship='id', **{'from': 'contract/id_child', 'to': 'contract/entity'},
                                          from_col='entity_id', to_col='id'))
        else:
            super().assert_case_result(case, result, original)

    def call_with_kwargs(self, ticket, case):
        return self.api.dispatch(case['call'], (ticket, *case['args']), case['kwargs'])

    def test_relationship_api_projection_preserves_identity_and_input(self):
        ticket = {'ticket': self.ticket, 'project': 'one'}
        columns = ['name', 'missing']
        parent = self.api.dispatch('get_parent', (ticket, {'__search_key__': key('child', 'CH1')}), {'columns': columns})
        self.assertEqual(parent, {'name': 'Первый', 'missing': None, '__search_key__': key('entity', 'A'), '__search_type__': 'contract/entity?project=one'})
        self.assertEqual(columns, ['name', 'missing'])
        self.assertNotIn('code', parent)
        children = self.api.dispatch('get_all_children', (ticket, key('entity', 'A'), 'contract/child'), {'columns': ['code']})
        self.assertEqual([row['code'] for row in children], ['CH1', 'CH2'])
        for row in children:
            self.assertEqual(set(row), {'code', '__search_key__', '__search_type__'})
        self.assertIn('entity_code', self.api.dispatch('get_all_children', (ticket, key('entity', 'A'), 'contract/child'), {'columns': []})[0])
        self.assertIn('name', self.api.dispatch('get_parent', (ticket, key('child', 'CH1'))))

    def test_relationship_projection_does_not_grant_parent_access(self):
        from pyasm.common.errors import SecurityException
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('relation_reader','relation_reader',?)", (hash_password('private-reader-password'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('relation_readers','relation_readers',?)", ('<rules><rule group="search_type" code="contract/entity" project="one" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('relation_reader_group','relation_reader','relation_readers')")
        auth = {'ticket': self.api.get_ticket('relation_reader', 'private-reader-password'), 'project': 'one'}
        try:
            parent = self.api.dispatch('get_parent', (auth, key('id_ref', 'IR1')), {'columns': ['name']})
            self.assertEqual(parent['name'], 'By id')
            for columns in ([], ['code'], ['name', 'missing']):
                self.assertEqual(self.api.dispatch('get_parent', (auth, key('child', 'CH1')), {'columns': columns}), {})
                with self.assertRaisesRegex(LookupError, 'SObject does not exist'):
                    self.api.dispatch('get_all_children', (auth, key('entity', 'A'), 'contract/child'), {'columns': columns})
            with self.assertRaises(SecurityException):
                self.api.dispatch('get_all_children', (auth, 'sthpw/project?code=admin', 'sthpw/task'), {'filters': [['code', '@GET(sthpw/login.login)']], 'columns': ['code']})
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='relation_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='relation_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='relation_readers'")
                db.execute("DELETE FROM login WHERE code='relation_reader'")

    def test_class_hierarchy_and_original_import_paths(self):
        from pyasm.biz.project import Project as ImportedProject
        from pyasm.biz.schema import Schema as ImportedSchema
        from pyasm.search.search import SObject as ImportedSObject
        self.assertIs(ImportedSObject, SObject)
        self.assertIs(ImportedProject, Project)
        self.assertIs(ImportedSchema, Schema)
        for cls in (Project, ProjectType, Schema, SearchType):
            self.assertTrue(issubclass(cls, SObject))
        with request_context(RequestContext(self.store, "admin", "one")):
            self.assertIsInstance(Search("sthpw/schema").get_sobject(), Schema)
            self.assertIsInstance(Search("sthpw/project_type").get_sobject(), ProjectType)
            self.assertEqual(SearchKey.get_by_search_key(key("child", "CH1")).get_parent().get_code(), "A")

    def test_schema_cache_is_local_to_request_and_project(self):
        def read(project):
            with request_context(RequestContext(self.store, "admin", project)):
                first = Schema.get()
                self.assertIs(first, Schema.get())
                return first.get_relationship_attrs("contract/child", "contract/entity")["from_col"]
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(read, ["one", "two"] * 5))
        self.assertEqual(result, ["entity_code", "alternate_entity_code"] * 5)

    def test_project_schema_columns_from_system_context(self):
        with self.store.connection(write=True) as db:
            db.execute('UPDATE "schema" SET project_code=NULL WHERE code=\'one\'')
        self.addCleanup(self.restore_schema_project_code)
        with request_context(RequestContext(self.store, 'admin', 'sthpw')):
            for project, column in (('one', 'entity_code'), ('two', 'alternate_entity_code')):
                schema = Schema.get(project_code=project)
                attrs = schema.get_relationship_attrs('contract/child', 'contract/entity')
                self.assertEqual(attrs['from_col'], column)
                self.assertNotIn('disabled', attrs)
                self.assertEqual(schema.get_foreign_keys('contract/child', 'contract/entity'), ('code', column))
                inherited = schema.get_relationship_attrs('contract/inherited', 'contract/entity')
                self.assertEqual(inherited['from_col'], 'entity_code')
                self.assertNotIn('disabled', inherited)
            self.assertEqual(Project.get_project_code(), 'sthpw')

    def restore_schema_project_code(self):
        with self.store.connection(write=True) as db:
            db.execute('UPDATE "schema" SET project_code=\'one\' WHERE code=\'one\'')

    def test_invalid_schema_and_inheritance_fail_explicitly(self):
        with request_context(RequestContext(self.store, "admin", "one")):
            for xml in ('<!DOCTYPE schema [<!ENTITY x "expanded">]><schema>&x;</schema>', '<schema>', '<other/>'):
                with self.assertRaises(ValueError):
                    Schema("sthpw/schema", {"schema": xml}, dependencies=False)
            # The instance link discriminator belongs to another type; no matches.
            self.assertEqual(Search.get_by_code("contract/entity", "A").get_related_sobjects("contract/many"), [])
        with self.store.connection(write=True) as db:
            db.executemany('INSERT INTO "schema" (code,"schema") VALUES (?,?)', [
                ("cycle1", '<schema parent="cycle2"/>'), ("cycle2", '<schema parent="cycle1"/>')])
        try:
            with request_context(RequestContext(self.store, "admin", "one")), self.assertRaises(ValueError):
                Schema.get_by_code("cycle1")
        finally:
            with self.store.connection(write=True) as db:
                db.execute('DELETE FROM "schema" WHERE code IN (\'cycle1\',\'cycle2\')')


class RelationshipTransport(unittest.TestCase):
    def test_original_sdk_projection_retirement_projects_and_rollback(self):
        import importlib.util
        import test_transport
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_relationship_client', read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            parent = client.get_parent(key('child', 'CH1'), columns=['name'])
            self.assertEqual(set(parent), {'name', '__search_key__', '__search_type__'})
            self.assertEqual(parent['name'], 'Первый')
            rows = client.get_all_children(key('entity', 'A'), 'contract/child', filters=[['code', 'CH2']], columns=['code'])
            self.assertEqual(rows, [{'code': 'CH2', '__search_key__': key('child', 'CH2'), '__search_type__': 'contract/child?project=one'}])
            self.assertEqual(client.get_parent(key('ref', 'R4'), columns=['code']), {})
            self.assertEqual(client.get_parent(key('ref', 'R4'), columns=['code'], show_retired=True)['code'], 'C')
            children = client.get_all_children(key('collection', 'G1'), 'contract/entity', columns=['code'])
            self.assertEqual([row['code'] for row in children], ['A', 'A', 'B'])
            self.assertTrue(all(set(row) == {'code', '__search_key__', '__search_type__'} for row in children))
            self.assertEqual([row['code'] for row in client.get_all_children(key('entity', 'A'), 'contract/collection', columns=['code'])], ['G1', 'G1'])
            self.assertEqual(client.get_all_children(key('collection', 'EMPTY'), 'contract/entity'), [])
            self.assertEqual([row['code'] for row in client.query('contract/entity', parent_key=key('collection', 'G1'), filters=[['code', 'B']], columns=['code'])], ['B'])
            client.set_project('two')
            self.assertEqual(client.get_parent(key('child', 'CH1', 'two'), columns=['code'])['code'], 'B')
            self.assertEqual([row['code'] for row in client.get_all_children(key('collection', 'G1', 'two'), 'contract/entity', columns=['code'])], ['A', 'A', 'B'])
            client.set_project('one')
            before = client.get_by_code('contract/entity', 'A')['name']
            write = "@IF(@UPDATE(@SOBJECT(contract/entity['code','A']),name,'temporary relationship filter write'),'CH2','CH2')"
            with self.assertRaisesRegex(Exception, 'Unknown column or SQL expression: missing'):
                client.get_all_children(key('entity', 'A'), 'contract/child', filters=[['code', write], ['missing', 1]], columns=['code'])
            self.assertEqual(client.get_by_code('contract/entity', 'A')['name'], before)
            body = "return server.get_all_children('contract/entity?project=one&code=A', 'contract/child', columns=['code'])"
            local = client.execute_python_script('', {'code': body})['info']
            self.assertEqual([row['code'] for row in local], ['CH1', 'CH2'])
            self.assertTrue(all(set(row) == {'code', '__search_key__', '__search_type__'} for row in local))
            local = client.execute_python_script('', {'code': "return server.get_all_children('contract/collection?project=one&code=G1', 'contract/entity', columns=['code'])"})['info']
            self.assertEqual([row['code'] for row in local], ['A', 'A', 'B'])
            batch = '''from pyasm.search import Search
parent = Search.get_by_code('contract/collection', 'G1')
result = Search('contract/entity')
result.add_relationship_filters([parent])
grouped = Search.get_related_by_sobjects([parent], 'contract/entity')
selected = Search('contract/collection')
selected.add_column('name', as_column='code')
selected.add_filter('code', 'G1')
other = Search('contract/entity')
other.add_relationship_search_filter(selected, op='not in')
return {'list': [obj.get_code() for obj in result.get_sobjects()],
        'map': [obj.get_code() for obj in grouped[parent.get_search_key()]],
        'excluded': [obj.get_code() for obj in other.get_sobjects()],
        'codes': result.get_sobject_codes(), 'ids': result.get_sobject_ids()}
'''
            self.assertEqual(client.execute_python_script('', {'code': batch})['info'],
                             {'list': ['A', 'A', 'B'], 'map': ['A', 'A', 'B'], 'excluded': ['A', 'B'],
                              'codes': ['A', 'A', 'B'], 'ids': [1, 1, 2]})
            before = client.get_by_code('contract/collection', 'G1')['name']
            fail = batch.replace("return {'list':", "parent.set_value('name', 'temporary batch write')\nparent.commit()\nraise ValueError('batch relationship rollback')\nreturn {'list':")
            with self.assertRaisesRegex(Exception, 'batch relationship rollback'):
                client.execute_python_script('', {'code': fail})
            self.assertEqual(client.get_by_code('contract/collection', 'G1')['name'], before)
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()


class SchemaUpgrade(unittest.TestCase):
    def test_old_database_upgrade_is_atomic_and_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password("upgrade-password"))
            # Recreate the actual 0.2 six-table layout without changing accounts.
            with store.connection(write=True) as db:
                db.execute('DROP TABLE "schema"')
                db.execute('DROP TABLE project_type')
                db.execute('DROP TABLE db_resource')
                db.execute('ALTER TABLE project DROP COLUMN "database"')
                db.execute("DELETE FROM search_object WHERE search_type IN ('sthpw/schema','sthpw/project_type','sthpw/db_resource')")
                account = dict(db.execute("SELECT * FROM login").fetchone())
            self.assertTrue(store.upgrade())
            with store.connection() as db:
                self.assertEqual(dict(db.execute("SELECT * FROM login").fetchone()), account)
                self.assertIn("project_code", [row["name"] for row in db.execute('PRAGMA table_info("schema")')])
                self.assertIn('database', [row['name'] for row in db.execute('PRAGMA table_info(project)')])
                self.assertEqual(db.execute('SELECT count(*) FROM db_resource').fetchone()[0], 0)
            before = store.database_path("sthpw").read_bytes()
            self.assertFalse(store.upgrade())
            self.assertEqual(store.database_path("sthpw").read_bytes(), before)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE "schema"')
                db.execute("UPDATE search_object SET class_name='custom.Schema' WHERE search_type='sthpw/schema'")
            with self.assertRaises(ValueError):
                store.upgrade()
            with store.connection() as db:
                self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='schema'").fetchone())
