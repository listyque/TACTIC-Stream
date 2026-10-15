"""Journal, access-rule and backend configuration subset of TACTIC Xml, using the standard library.

Adapted from pyasm/common/lxml_wrapper.py; see LICENSE.TACTIC/source_manifest.json.
Absolute paths, attributes and attribute equality/existence predicates joined
by AND and trusted UTF-8 file loading are supported. Full XPath and namespaces
remain unsupported.
"""
import copy
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from weakref import WeakKeyDictionary, ref

from pyasm.common.common import Base, TacticException
from pyasm.common.errors import UnsupportedContract


_ATTRIBUTE_TEST = r'''@[A-Za-z_][\w.-]*(?:\s*=\s*(?:'[^']*'|"[^"]*"))?'''
_STEP = r"(?:[A-Za-z_][\w.-]*|\*)(?:\[" + _ATTRIBUTE_TEST + r"(?:\s+and\s+" + _ATTRIBUTE_TEST + r")*\])*"
_PARENTS = WeakKeyDictionary()


class XmlException(TacticException):
    pass


class Xml(Base):
    @classmethod
    def get_node_values_of_children(cls, node):
        values = {}
        if node is None:
            return values
        for child in node:
            name = cls.get_attribute(child, 'name') or child.tag
            if isinstance(name, str):
                values[name] = child.text or ''
        return values

    def __init__(self, string=None, file_path=None, doc=None, strip_cdata=True):
        self.doc = None
        self.uri = "XmlWrapper"
        self.strip_cdata = strip_cdata
        self.cache_xpath = {}
        if string:
            self.read_string(string)
        elif file_path:
            self.read_file(file_path)
        elif doc is not None:
            self.doc = doc
            for parent in doc.iter():
                for child in parent:
                    _PARENTS[child] = ref(parent)

    def clear_xpath_cache(self):
        self.cache_xpath = {}

    def read_file(self, file_path, cache=True):
        # Files can change between calls; request-local WidgetConfig owns reuse.
        # Reuse read_string's DTD/entity checks and never share a mutable tree.
        self.uri = str(file_path)
        self.read_string(Path(file_path).read_text(encoding='utf-8-sig'))

    def read_string(self, xml_string, print_error=True, remove_blank_text=True):
        self.clear_xpath_cache()
        xml_string = str(xml_string)
        if "<!DOCTYPE" in xml_string or "<!ENTITY" in xml_string:
            raise XmlException("DTD/entities are not accepted")
        if re.search(r"<\?(?!xml\s)", xml_string):
            raise UnsupportedContract("Xml processing instructions are not migrated")
        if not self.strip_cdata and "<![CDATA[" in xml_string:
            raise UnsupportedContract("Preserving CDATA is not migrated")
        try:
            self.doc = ET.fromstring(xml_string, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        except ET.ParseError as exc:
            raise XmlException(str(exc)) from exc
        if any("{" in node.tag or any("{" in name for name in node.attrib) for node in self.doc.iter() if isinstance(node.tag, str)):
            raise UnsupportedContract("Xml namespaces are not migrated")
        for parent in self.doc.iter():
            for child in parent:
                _PARENTS[child] = ref(parent)
        if remove_blank_text:
            for node in self.doc.iter():
                if len(node) and node.text and not node.text.strip():
                    node.text = None
                if node.tail and not node.tail.strip():
                    node.tail = None

    def create_doc(self, root_name="snapshot", nsmap={}):
        if nsmap:
            raise UnsupportedContract("Xml namespaces are not migrated")
        self.doc = self.create_element(root_name)
        return self.doc

    def get_doc(self):
        return self.doc

    def get_root_node(self):
        return self.doc

    def create_element(self, name, node=None, attrs=None, nsmap={}):
        if nsmap or not re.fullmatch(r"[A-Za-z_][\w.-]*", name):
            raise UnsupportedContract("Only plain journal XML element names are migrated")
        element = ET.Element(name)
        if node is not None:
            self.append_child(node, element)
        for key, value in (attrs or {}).items():
            self.set_attribute(element, key, value)
        return element

    def create_text_element(self, name, text, node=None):
        element = self.create_element(name, node=node)
        self.set_node_value(element, str(text))
        return element

    def import_node(self, element, deep=True):
        # Original lxml implementation inserts into the root and returns None.
        # A detached copy is required by WidgetDbConfig.import_element_node.
        result = copy.deepcopy(element) if deep else ET.Element(element.tag, dict(element.attrib))
        if not deep:
            result.text, result.tail = element.text, element.tail
        return Xml(doc=result).get_root_node()

    @classmethod
    def get_parent(cls, node):
        parent = _PARENTS.get(node)
        return parent() if parent else None

    @classmethod
    def replace_child(cls, node, old_node, new_node):
        if old_node is new_node:
            return
        cls.append_child(node, new_node)
        index = list(node).index(old_node)
        cls.remove_child(node, old_node)
        node.remove(new_node)
        node.insert(index, new_node)

    @staticmethod
    def insert_before(new_element, ref_element, parent=None):
        parent = Xml.get_parent(ref_element)
        if parent is None:
            raise ValueError('Reference element has no parent')
        if new_element is ref_element:
            return
        Xml.append_child(parent, new_element)
        index = list(parent).index(ref_element)
        parent.remove(new_element)
        parent.insert(index, new_element)

    @staticmethod
    def insert_after(new_element, ref_element, parent=None):
        parent = Xml.get_parent(ref_element)
        if parent is None:
            raise ValueError('Reference element has no parent')
        if new_element is ref_element:
            return
        Xml.append_child(parent, new_element)
        index = list(parent).index(ref_element)
        parent.remove(new_element)
        parent.insert(index + 1, new_element)

    @classmethod
    def append_child(cls, node, child):
        # lxml moves nodes, including between documents. Weak refs avoid retaining trees.
        old_parent = _PARENTS.get(child)
        old_parent = old_parent() if old_parent else None
        ancestor = node
        while ancestor is not None:
            if ancestor is child:
                raise ValueError("cannot append parent to itself")
            parent = _PARENTS.get(ancestor)
            ancestor = parent() if parent else None
        if old_parent is not None:
            old_parent.remove(child)
        elif child in node:
            node.remove(child)
        node.append(child)
        _PARENTS[child] = ref(node)

    @classmethod
    def remove_child(cls, node, child):
        node.remove(child)
        _PARENTS.pop(child, None)

    def _evaluate(self, xpath, node=None):
        if node is None and xpath in self.cache_xpath:
            return self.cache_xpath[xpath]
        path = xpath.lstrip("/")
        if xpath.startswith("//") or not re.fullmatch(_STEP + r"(?:/{1,2}" + _STEP + r")*(?:/@[\w.-]+)?", path):
            raise UnsupportedContract("Only absolute Xml paths with attribute AND predicates are migrated")
        # Tokenize steps, keeping slashes and 'and' inside quoted values intact.
        parts = []
        last_end = 0
        for step in re.finditer(_STEP, path):
            value = step.group()
            name = value.split("[", 1)[0]
            tests = re.finditer(_ATTRIBUTE_TEST, value[len(name):])
            if parts:
                parts.append(path[last_end:step.start()])
            parts.append(name + "".join("[" + test.group() + "]" for test in tests))
            last_end = step.end()
            if step.end() == len(path) or path[step.end():].startswith("/@"):
                break
        suffix = path[step.end():]
        attribute = suffix[2:] if suffix else None
        # A temporary parent lets ElementTree also evaluate predicates on the root.
        if node is None:
            parent = ET.Element("_xpath_root")
            parent.append(self.doc)
        else:
            parent = node
        nodes = [node for node in parent.findall("".join(parts)) if isinstance(node.tag, str)]
        result = [item.get(attribute) for item in nodes if attribute in item.attrib] if attribute else nodes
        # Original looks up the caller's path, but stores its absolute form.
        if node is None:
            self.cache_xpath[xpath if xpath.startswith("/") else "/" + xpath] = result
        return result

    @classmethod
    def xpath(cls, node, xpath):
        return cls(doc=node)._evaluate(xpath, node=node)

    def get_nodes(self, xpath):
        return self._evaluate(xpath)

    def get_node(self, xpath):
        nodes = self.get_nodes(xpath)
        return nodes[0] if nodes else None

    def get_values(self, xpath):
        return [node if isinstance(node, str) else self.get_node_value(node) for node in self._evaluate(xpath)]

    def get_nodes_attr(self, xpath, attr):
        nodes = self.get_nodes(xpath)
        value_list = []
        for node in nodes:
            value_list.append(Xml.get_attribute(node, attr))
        return value_list

    def get_value(self, xpath):
        values = self.get_values(xpath)
        return values[0] if values else ""

    def get_xml(self):
        return self.to_string()

    def to_string(self, node=None, pretty=True, tree=False, method='xml', xml_declaration=False):
        if tree or method != "xml":
            raise UnsupportedContract("Xml tree/non-XML serialization is not migrated")
        output = copy.deepcopy(self.doc if node is None else node)
        preserved_whitespace = any(len(item) and item.text or item.tail for item in output.iter())
        if pretty and not preserved_whitespace:
            ET.indent(output, space="  ")
        value = ET.tostring(output, encoding="utf-8", xml_declaration=xml_declaration).decode()
        value = value.replace(" />", "/>")
        return value + "\n" if pretty else value

    @classmethod
    def get_attributes(cls, node):
        return dict(node.attrib)

    @classmethod
    def get_children(cls, node):
        return [child for child in node if isinstance(child.tag, str)]

    @classmethod
    def get_first_child(cls, node):
        children = cls.get_children(node)
        return children[0] if children else None

    @classmethod
    def get_attribute(cls, node, attribute):
        return node.get(attribute)

    @classmethod
    def del_attribute(cls, node, attribute):
        return node.attrib.pop(attribute, None)

    @classmethod
    def set_attribute(cls, node, attribute, value):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        if not isinstance(value, str):
            value = str(value)
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
            raise ValueError("All strings must be XML compatible: Unicode or ASCII, no NULL bytes or control characters")
        return node.set(attribute, value)

    @staticmethod
    def get_node_name(node):
        return node.tag

    @classmethod
    def get_node_value(cls, node):
        return "" if node.text is None else node.text

    @classmethod
    def get_recursive_node_values(cls, node):
        values = {}
        if node is None:
            return values
        cls._get_recursive_node_values(node, values)
        values = values.get(cls.get_node_name(node))
        if isinstance(values, str):
            values = values.strip()
        return values or {}

    @classmethod
    def _get_recursive_node_values(cls, node, values):
        children = cls.get_children(node)
        name = cls.get_node_name(node)
        if not children:
            values[name] = cls.get_node_value(node)
        else:
            child_values = {}
            values[name] = child_values
            for child in children:
                cls._get_recursive_node_values(child, child_values)

    @classmethod
    def set_node_value(cls, node, text):
        node.text = text
        return text
