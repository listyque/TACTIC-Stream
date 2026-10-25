"""Used value widgets: compare source display bodies and native typed cells."""

import ast
import binascii
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyasm.common import Common, Config, Xml, XmlException, jsondumps
from pyasm.search.search import RequestContext, request_context
from pyasm.widget import ArrayTableElementWdg, XmlWdg
from pyasm.widget.table_element_wdg import WikiElementWdg
from tactic.ui.table import JsonElementWdg, SnapshotVersionElementWdg
from tactic_stream.server.table_cells import describe_cell

LEGACY = Path(__file__).resolve().parents[2] / "legacy/src"


class Div:
    def __init__(self, value=""):
        self.children = [str(value)] if value else []

    def add(self, value):
        self.children.append(value)

    def add_style(self, *args):
        pass

    def text(self):
        return "".join(
            child.text() if isinstance(child, Div) else str(child)
            for child in self.children
        )


def source_display(path, name):
    tree = ast.parse((LEGACY / path).read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    method = next(
        n
        for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name == "get_display"
    )
    scope = dict(
        json=json,
        jsondumps=jsondumps,
        Common=Common,
        Config=Config,
        Xml=Xml,
        XmlException=XmlException,
        basestring=str,
        DivWdg=Div,
        HtmlElement=SimpleNamespace(pre=Div),
        IconWdg=lambda *args: "",
        SpanWdg=Div,
    )
    if name == "XmlWdg":
        xml_tree = ast.parse(
            (LEGACY / "pyasm/common/lxml_wrapper.py").read_text(encoding="utf-8")
        )
        xml_cls = next(
            n for n in xml_tree.body if isinstance(n, ast.ClassDef) and n.name == "Xml"
        )
        escape = next(
            n
            for n in xml_cls.body
            if isinstance(n, ast.FunctionDef) and n.name == "to_html"
        )
        escaping = {}
        exec(
            compile(
                ast.Module(body=[escape], type_ignores=[]), "legacy Xml.to_html", "exec"
            ),
            escaping,
        )

        class SourceXml(Xml):
            to_html = staticmethod(escaping["to_html"])

        scope["Xml"] = SourceXml
    exec(
        compile(ast.Module(body=[method], type_ignores=[]), str(LEGACY / path), "exec"),
        scope,
    )
    return scope["get_display"]


class TableValueWidgets(unittest.TestCase):
    def setUp(self):
        self.scope = request_context(RequestContext(None, "admin"))
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

    def widget(self, cls, value, name="value"):
        widget = cls(name=name)
        record = SimpleNamespace(
            get_value=lambda key, **kwargs: value,
            get_json_value=lambda key: value,
            is_insert=lambda: False,
        )
        widget.set_sobjects([record])
        widget.top = Div()
        return widget

    def test_wiki_original_escaped_text_and_line_breaks_match_native_plain_text(self):
        from test_table_embedded_widgets import original_method
        tree = ast.parse((LEGACY / 'pyasm/web/web_tools.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'WikiUtil')
        scope = dict(basestring=str, re=re)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), 'original WikiUtil', 'exec'), scope)
        original = original_method('pyasm/widget/table_element_wdg.py', 'WikiElementWdg', 'get_display',
                                   dict(WikiUtil=scope['WikiUtil']))
        for value in ('', 0, False, '<img src=x onerror=alert(1)>\nSecond line', 'Строка\nДругая строка'):
            widget = self.widget(WikiElementWdg, value)
            text = original(widget).replace('&spt_lt;', '<').replace('&spt_gt;', '>').replace('<br/>', '\n')
            self.assertEqual(widget.get_cell_value(), dict(text=text, multiline=True))

    def test_array_original_display(self):
        original = source_display(
            "pyasm/widget/table_element_wdg.py", "ArrayTableElementWdg"
        )
        for value in ["", "||A||B||", "||||A||||B||||", "||Кадр||Материал||"]:
            widget = self.widget(ArrayTableElementWdg, value)
            self.assertEqual(widget.get_cell_value()["text"], original(widget))
            self.assertEqual(widget.get_text_value(), original(widget))
        with self.assertRaises(AttributeError):
            original(self.widget(ArrayTableElementWdg, None))
        self.assertEqual(
            self.widget(ArrayTableElementWdg, None).get_cell_value()["text"], ""
        )

    def test_json_original_display_and_raw_sdk_value(self):
        original = source_display(
            "tactic/ui/table/json_element_wdg.py", "JsonElementWdg"
        )
        for value in [
            {},
            [],
            None,
            {"z": "<script>alert(1)</script>", "a": ["кадр", 1]},
            [1, True],
        ]:
            widget = self.widget(JsonElementWdg, value)
            expected = original(widget).text()
            self.assertEqual(widget.get_cell_value()["text"], expected)
            self.assertEqual(
                widget.get_text_value(), value, "SDK raw value must remain unchanged"
            )

    def test_xml_original_display_compression_and_diagnostic(self):
        original = source_display("pyasm/widget/table_element_wdg.py", "XmlWdg")
        xml = "<config><value>&lt;script&gt;</value></config>"
        for value in [xml, Common.compress_transaction(xml)]:
            widget = self.widget(XmlWdg, value)
            displayed = (
                original(widget)
                .text()
                .replace("&spt_lt;", "<")
                .replace("&spt_gt;", ">")
            )
            self.assertEqual(widget.get_cell_value()["text"], displayed)
            self.assertEqual(
                widget.get_text_value(), value, "CSV/raw SDK keeps compression"
            )
            self.assertEqual(widget.get_cell_value()["diagnostic"], "")
        invalid = self.widget(XmlWdg, "<broken>").get_cell_value()
        self.assertTrue(invalid["diagnostic"])
        self.assertEqual(invalid["text"], "<broken>")
        dtd = '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///private">]><x>&e;</x>'
        self.assertTrue(self.widget(XmlWdg, dtd).get_cell_value()["diagnostic"])
        with self.assertRaises(binascii.Error):
            self.widget(XmlWdg, "zlib:broken").get_cell_value()

    def test_version_original_display_and_padding(self):
        original = source_display(
            "tactic/ui/table/snapshot_element_wdg.py", "SnapshotVersionElementWdg"
        )
        for padding in [None, "3", "5"]:
            with patch.object(Config, "get_value", return_value=padding):
                for value in ["", -1, 0, 1, 1234]:
                    widget = self.widget(SnapshotVersionElementWdg, value, "version")
                    self.assertEqual(
                        widget.get_cell_value()["text"], original(widget).text()
                    )
                    self.assertEqual(widget.get_text_value(), value)
        self.assertEqual(
            self.widget(SnapshotVersionElementWdg, None).get_cell_value()["text"],
            "No version",
        )

    def test_descriptors_and_option_rejection(self):
        for handler, kind in [
            ("ArrayTableElementWdg", "text"),
            ("XmlWdg", "structured"),
            ("tactic.ui.table.JsonElementWdg", "structured"),
            ("tactic.ui.table.SnapshotVersionElementWdg", "text"),
        ]:
            element = dict(
                name="value",
                display=dict(handler=handler, options={}),
                action=dict(handler=""),
            )
            cell = describe_cell(element, {"value": {"data_type": "text"}})
            self.assertTrue(cell["supported"] and cell["server"])
            self.assertEqual(cell["kind"], kind)
            if "Json" in handler:
                self.assertFalse(cell["sortable"])
                element["display"]["options"] = {"height": "72px"}
                self.assertTrue(describe_cell(element, {"value": {}})["supported"])
            element["display"]["options"] = {"height": "999999px"}
            self.assertFalse(describe_cell(element, {"value": {}})["supported"])

    def test_handler_transport_matches_both_server_paths(self):
        path = Path("D:/grav/Tactic Stream/TH/thlib/tactic_query.py")
        method = next(
            n
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(n, ast.FunctionDef) and n.name == "action_cell_values"
        )
        scope = {"json": json}
        exec(
            compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"),
            scope,
        )
        for cls, value, name in [
            (JsonElementWdg, {"b": 2, "a": 1}, "value"),
            (XmlWdg, "<config/>", "value"),
            (ArrayTableElementWdg, "||A||B||", "value"),
            (SnapshotVersionElementWdg, 2, "version"),
        ]:
            widget = self.widget(cls, value, name)
            legacy_widget = SimpleNamespace(get_text_value=widget.get_text_value)
            column = {"name": name, "displayOptions": {}}
            with patch.object(Config, "get_value", return_value="3"):
                expected = widget.get_cell_value()
                for presenter in [widget, legacy_widget]:
                    self.assertEqual(
                        scope["action_cell_values"](
                            widget.get_class_name(),
                            column,
                            widget.get_current_sobject(),
                            presenter,
                        ),
                        expected,
                    )
        empty = self.widget(ArrayTableElementWdg, None)
        self.assertEqual(
            scope["action_cell_values"](
                empty.get_class_name(),
                {"name": "value"},
                empty.get_current_sobject(),
                SimpleNamespace(),
            ),
            {"text": "", "error": ""},
        )


if __name__ == "__main__":
    unittest.main()
