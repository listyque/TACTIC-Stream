"""TACTIC Schema reads and backend search-type registration; adapted from pyasm/biz/schema.py.

The original predefined XML lives in compatibility/predefined_schemas.json.
Relationship order, wildcard selection and inherited definitions stay intact.
"""
from importlib.resources import files
import json
import xml.etree.ElementTree as ET

from pyasm.biz.project import Project
from pyasm.search.search import Search, SearchType, SObject, _context
from pyasm.common.errors import UnsupportedContract


class Schema(SObject):
    SEARCH_TYPE = "sthpw/schema"

    def get_xml(self):
        from pyasm.common import Xml
        return Xml(doc=self.xml)

    def set_xml(self, xml):
        self.set_value('schema', xml)
        self.init()

    def __init__(self, search_type, columns=None, result=None, dependencies=True, fast_data=None):
        super().__init__(search_type, columns, result, fast_data=fast_data)
        self._project_code = self.get_value('project_code', no_exception=True) or Project.get_project_code()
        self.parent_schema = self.sthpw_schema = None
        self.relationships = {}
        self.init()
        if dependencies and self.get_value("code", no_exception=True):
            loading = _context.get().schema_loading
            code = self.get_code()
            if code in loading:
                raise ValueError("Cyclic schema inheritance: " + code)
            loading.add(code)
            try:
                self.parent_schema = self.get_parent_schema()
                if code != "admin":
                    self.sthpw_schema = self.get_admin_schema()
            finally:
                loading.remove(code)

    @staticmethod
    def create(code, description, schema='<schema/>'):
        from pyasm.common import Environment
        sobject = Schema(Schema.SEARCH_TYPE, dependencies=False)
        sobject.set_value('code', code)
        sobject.set_value('description', description)
        sobject.set_value('schema', schema)
        sobject.set_value('login', Environment.get_user_name())
        sobject.init()
        sobject.commit()
        return sobject

    def add_search_type(self, search_type, parent_type=None, commit=True):
        if not isinstance(search_type, str) or not search_type:
            raise ValueError('A schema search type name is required')
        if not any(node.get('name') == search_type for node in self.xml.findall('search_type')):
            ET.SubElement(self.xml, 'search_type', {'name': search_type, 'xpos': '0', 'ypos': '0'})
        if parent_type:
            self.edit_connection(search_type, parent_type, mode='add', commit=False)
        self.relationships.clear()
        if commit:
            self.set_value('schema', ET.tostring(self.xml, encoding='unicode'))

    def edit_connection(self, from_search_type, to_search_type, mode='remove', commit=True):
        if mode not in ('add', 'remove'):
            raise ValueError('Unknown schema connection mode: %s' % mode)
        if not all(isinstance(value, str) and value for value in (from_search_type, to_search_type)):
            raise ValueError('Both connection search types are required')
        node = next((node for node in self.xml.findall('connect')
                     if node.get('from') == from_search_type and node.get('to') == to_search_type), None)
        if node is not None:
            if mode == 'remove':
                self.xml.remove(node)
        elif mode == 'add':
            ET.SubElement(self.xml, 'connect', {'from': from_search_type, 'to': to_search_type,
                                             'relationship': 'code', 'type': 'hierarchy'})
        self.relationships.clear()
        if commit:
            self.set_value('schema', ET.tostring(self.xml, encoding='unicode'))

    def init(self):
        self.relationships.clear()
        value = self.get_value("schema", no_exception=True) or "<schema/>"
        if "<!DOCTYPE" in value or "<!ENTITY" in value:
            raise ValueError("DTD/entity declarations are not accepted in schemas")
        try:
            parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
            self.xml = ET.fromstring(value, parser=parser)
        except ET.ParseError as exc:
            raise ValueError("Invalid schema XML") from exc
        if self.xml.tag != "schema":
            raise ValueError("Expected a schema XML root")

    def get_parent_schema(self):
        code = self.xml.get("parent")
        if code:
            return None if code == "__NONE__" else self.get_by_code(code)
        project = Project.get_by_code(self.get_code())
        project_type = project.get_base_type() if project else ""
        return self.get_predefined_schema(project_type) if project_type else None

    def get_attrs_by_search_type(self, search_type):
        for node in self.xml.findall("search_type"):
            if node.get("name") == search_type:
                return dict(node.attrib)
        for schema in (self.parent_schema, self.sthpw_schema):
            if schema:
                attrs = schema.get_attrs_by_search_type(search_type)
                if attrs:
                    return attrs
        return {}

    def get_attr_by_search_type(self, search_type, attr):
        for node in self.xml.findall("search_type"):
            if node.get("name") == search_type:
                return node.get(attr)
        return {}

    def get_search_types(self, hierarchy=True):
        result = []
        if hierarchy:
            for schema in (self.sthpw_schema, self.parent_schema):
                if schema:
                    result.extend(schema.get_search_types())
        result.extend(node.get("name", "") for node in self.xml.findall("search_type"))
        return result

    def get_related_search_types(self, search_type, direction=None):
        result = []
        connects = self.xml.findall("connect")
        if not direction or direction == "parent":
            result.extend(node.get("to", "") for node in connects if node.get("from") == search_type)
        if not direction or direction == "children":
            result.extend(node.get("from", "") for node in connects if node.get("to") == search_type)
        for schema in (self.parent_schema, self.sthpw_schema):
            if schema:
                result.extend(schema.get_related_search_types(search_type, direction))
        return result

    def get_parent_type(self, search_type, relationship=None):
        search_type = search_type.split("?", 1)[0]
        if self.get_code() != "admin" and search_type.startswith("sthpw/"):
            parent = self.get_admin_schema().get_parent_type(search_type, relationship)
            if parent:
                return parent
        connects = [node for node in self.xml.findall("connect")
                    if node.get("from") == search_type and node.get("relationship") != "instance"]
        for node in connects:
            if node.get("relationship") and node.get("type") == "hierarchy":
                return node.get("to", "")
        if connects:
            return connects[0].get("to", "")
        return self.parent_schema.get_parent_type(search_type, relationship) if self.parent_schema else ""

    def get_child_types(self, search_type, relationship="hierarchy", hierarchy=True):
        search_type = search_type.split("?", 1)[0]
        result = []
        if hierarchy:
            for schema in (self.sthpw_schema, self.parent_schema):
                if schema:
                    result.extend(schema.get_child_types(search_type, relationship))
        result.extend(node.get("from", "") for node in self.xml.findall("connect")
                      if node.get("to") in (search_type, "*") and node.get("relationship")
                      and node.get("from") != search_type)
        return result

    def get_types_from_instance(self, search_type):
        for node in self.xml.findall("connect"):
            if node.get("instance_type") == search_type:
                return node.get("from", ""), node.get("to", "")
        return "", ""

    def get_instance_type(self, search_type, related_search_type):
        for node in self.xml.findall("connect"):
            if node.get("to") == search_type and node.get("from") == related_search_type:
                if node.get("type") != "many_to_many":
                    return ""
                value = node.get("instance_type")
                if not value:
                    raise ValueError("No instance_type defined")
                return value
        return ""

    def get_relationship_attrs(self, search_type, search_type2, path=None, cache=True, type=None):
        search_type = SearchType.build_search_type(search_type, self._project_code)
        search_type2 = SearchType.build_search_type(search_type2, self._project_code)
        key = (search_type, search_type2, path, type)
        if cache and key in self.relationships:
            return self.relationships[key]
        first, second = search_type.split("?", 1)[0], search_type2.split("?", 1)[0]
        connect = with_path = None
        connections = self.relationships.get('connections') if cache else None
        if cache and connections is None:
            connections = {}
            for node in self.xml.findall("connect"):
                connections.setdefault((node.get("from"), node.get("to")), []).append(node)
            # Native XML callers invalidate this through relationships.clear().
            self.relationships['connections'] = connections
        connects = self.xml.findall("connect") if not cache else None
        # Original XPath priority: direct, reverse, first wildcard, second wildcard.
        for source, target in ((first, second), (second, first), (first, "*"), (second, "*")):
            nodes = connections.get((source, target), ()) if cache else connects
            for node in nodes:
                if node.get("from") != source or node.get("to") != target or type and node.get("type") != type:
                    continue
                if path:
                    if node.get("path") != path:
                        continue
                elif node.get("path"):
                    # Original fallback takes the last path-only match.
                    with_path = node
                    continue
                connect = node
                break
            if connect is not None:
                break
        if connect is None:
            connect = with_path
        if connect is None:
            for schema in (self.parent_schema, self.sthpw_schema):
                if schema:
                    attrs = schema.get_relationship_attrs(search_type, search_type2, path=path, cache=cache, type=type)
                    if attrs:
                        return attrs
            return {}
        attrs = dict(connect.attrib)
        relationship = attrs.get("relationship")
        if not relationship and attrs.get("type") == "hierarchy":
            relationship = attrs["relationship"] = "code"
        source, target = (search_type, search_type2) if attrs.get("from") == first else (search_type2, search_type)
        if relationship in ("code", "id", "instance"):
            from_col, to_col = attrs.get("from_col"), attrs.get("to_col")
            if not from_col:
                attrs["from_col"] = "code" if relationship == "instance" else SearchType.get(target).get_table() + "_" + relationship
                from_col = attrs["from_col"]
            if not to_col:
                to_col = attrs["to_col"] = "id" if relationship == "id" else "code"
            if not SearchType.column_exists(target, to_col):
                attrs["disabled"] = True
            if not SearchType.column_exists(source, from_col):
                attrs["disabled"] = True
        if cache and not attrs.get("disabled"):
            self.relationships[key] = attrs
        return attrs

    def _get_self_instance_edges(self, instance_type, related_type):
        edges = []
        for path in ('child', 'parent'):
            edge = self.get_relationship_attrs(instance_type, related_type, path=path)
            if (edge.get('path') != path or edge.get('from') != instance_type
                    or edge.get('relationship') not in ('code', 'id') or edge.get('disabled')):
                raise UnsupportedContract('Self-instance children require explicit parent and child endpoint paths')
            edges.append(edge)
        if edges[0]['from_col'] == edges[1]['from_col']:
            raise UnsupportedContract('Self-instance endpoints must use different link columns')
        return edges

    def get_relationship(self, search_type, search_type2):
        attrs = self.get_relationship_attrs(search_type, search_type2)
        relationship = attrs.get("relationship")
        if relationship == "search_type":
            return self.resolve_search_type_relationship(attrs, search_type, search_type2)
        return relationship

    def resolve_search_type_relationship(self, attrs, search_type, search_type2):
        if attrs.get("relationship") != "search_type":
            raise ValueError("Expected a search_type relationship")
        parent = search_type2 if attrs["from"] == search_type else search_type
        return "search_code" if SearchType.column_exists(parent, "code") else "search_id"

    def resolve_relationship_attrs(self, attrs, search_type, search_type2):
        if attrs.get("relationship") not in ("search_type", "search_code", "search_id"):
            return attrs
        attrs = dict(attrs)
        forward = attrs["from"] == SearchType.get(search_type).get_base_key()
        child = search_type if forward else search_type2
        parent = search_type2 if forward else search_type
        prefix = attrs.get("prefix", "")
        prefix = prefix + "_" if prefix else ""
        has_code = SearchType.column_exists(child, prefix + "search_code") and SearchType.column_exists(parent, "code")
        child_col, parent_col = prefix + ("search_code" if has_code else "search_id"), "code" if has_code else "id"
        attrs["from_col"], attrs["to_col"] = (child_col, parent_col) if forward else (parent_col, child_col)
        attrs["relationship"] = "search_code" if has_code else "search_id"
        return attrs

    def get_foreign_keys(self, search_type, search_type2, path=None):
        attrs = self.get_relationship_attrs(search_type, search_type2, path)
        relationship = attrs.get("relationship")
        if relationship not in ("id", "code", "search_type"):
            raise UnsupportedContract("Unsupported foreign-key relationship: " + str(relationship))
        from_col = attrs.get("from_col") or ("search_id" if relationship == "search_type" else "whatever_id")
        to_col = attrs.get("to_col") or "id"
        return (to_col, from_col) if attrs["from"] == search_type else (from_col, to_col)

    _PREDEFINED_DEFINITIONS = None

    @classmethod
    def get_predefined_schema(cls, code):
        if not code:
            raise ValueError("A schema code is required")
        cache = _context.get().schemas
        key = ("predefined", code)
        if key not in cache:
            if cls._PREDEFINED_DEFINITIONS is None:
                cls._PREDEFINED_DEFINITIONS = json.loads((files("tactic_stream") / "compatibility/predefined_schemas.json").read_text(encoding="utf-8"))
            cache[key] = cls(cls.SEARCH_TYPE, {"code": code, "schema": cls._PREDEFINED_DEFINITIONS.get(code) or "<schema/>"}, dependencies=False)
        return cache[key]

    @classmethod
    def get_admin_schema(cls):
        return cls.get_predefined_schema("admin")

    @classmethod
    def get_by_code(cls, code, show_retired=True):
        return Search.get_by_code(cls.SEARCH_TYPE, code, show_retired=show_retired)

    @classmethod
    def get(cls, reset_cache=False, project_code=None):
        project_code = project_code or Project.get_project_code()
        if project_code in ("sthpw", "admin"):
            return cls.get_admin_schema()
        context = _context.get()
        key = ("project", project_code)
        if not reset_cache and key in context.schemas:
            return context.schemas[key]
        search = Search(cls.SEARCH_TYPE)
        search.add_op("begin")
        if project_code != "unittest":
            search.add_filter("code", project_code)
        search.add_filter("project_code", project_code)
        search.add_op("or")
        search.add_order_by("id asc")
        schemas = search.get_sobjects()
        if project_code == "unittest":
            schema = cls.get_predefined_schema(project_code)
            schema.sthpw_schema = cls.get_admin_schema()
        elif schemas:
            schema = schemas[0]
        else:
            schema = cls(cls.SEARCH_TYPE, {"code": project_code, "schema": "<schema/>"})
        schema._project_code = project_code
        context.schemas[key] = schema
        return schema

    @classmethod
    def get_by_project_code(cls, project_code):
        return cls.get(project_code=project_code)

    @classmethod
    def get_by_sobject(cls, sobject):
        if sobject.get_search_type().startswith("sthpw/"):
            return cls.get_admin_schema()
        return cls.get(project_code=sobject.get_project_code())
