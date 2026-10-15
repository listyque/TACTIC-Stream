"""Every Frame glyph must resolve through the native house catalog in all packs."""

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
QML = Path(sys.argv[1]) if len(sys.argv) > 1 else TH / "thlib/ui/qml"
os.environ.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
sys.path.insert(0, str(TH))
from PySide6.QtCore import QObject, Property, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from tests.qt_application import gui_test_application
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.ui.icon_font import qml_icon_bindings


class Selection(QObject):
    def __init__(self, pack):
        super().__init__()
        self.pack = pack

    @Property(str, constant=True)
    def icon_set(self):
        return self.pack


app = gui_test_application()
engine = QQmlEngine()
warnings = []
engine.warnings.connect(
    lambda errors: warnings.extend(error.toString() for error in errors)
)
bindings = qml_icon_bindings(TH, app)
for name, value in bindings.items():
    engine.rootContext().setContextProperty(name, value)
selection = Selection("material-design")
engine.rootContext().setContextProperty("appController", selection)
component = QQmlComponent(engine)
component.setData(
    (
        'import QtQuick\nimport "'
        + (QML / "controls").resolve().as_uri()
        + '" as C\nC.MaterialIcon{color:"white";name:"help"}'
    ).encode(),
    QUrl(),
)
assert component.isReady(), [error.toString() for error in component.errors()]
icon = component.create()
assert icon
glyph = next(
    item
    for item in SidebarEditorQmlTests.descendants(icon)
    if item.objectName() == "materialIconGlyph"
)
names = json.loads(
    (ROOT / "tools/frame_admin/output/icon-names.json").read_text(encoding="utf-8")
)
names = sorted(
    set(names)
    | {
        "save",
        "plus",
        "delete",
        "list",
        "help",
        "expand_more",
        "expand_less",
        "palette",
        "calendar",
        "more_vert",
        "more",
        "connection",
        "activity",
        "queue",
        "appearance",
        "fact-check",
        "text-fields",
        "check",
        "minus",
    }
)
missing = {}
resolved = {}
selections = [selection]
for pack in (
    "material-design",
    "fontawesome-solid",
    "fontawesome-outline",
    "fluent-regular",
    "fluent-filled",
):
    selection = Selection(pack)
    selections.append(selection)
    engine.rootContext().setContextProperty("appController", selection)
    missing[pack] = []
    resolved[pack] = {}
    for name in names:
        icon.setProperty("name", name)
        if not any(
            glyph.property(field)
            for field in ("fontAwesomeName", "materialName", "catalogGlyph")
        ):
            missing[pack].append(name)
        resolved[pack][name] = [glyph.property("resolvedSet"), glyph.property("text")]
    for name in ("constructor", "__proto__", "toString", "material-design:constructor"):
        icon.setProperty("name", name)
        assert not glyph.property("fontAwesomeName"), (pack, name)
        assert not glyph.property("materialName"), (pack, name)
        assert glyph.property("resolvedSet") == "fontawesome-solid", (pack, name)
        assert glyph.property("text"), (pack, name)
print(json.dumps(missing))
assert not any(missing.values()), "Unknown native Frame icons"
assert not warnings, warnings
(ROOT / "tools/frame_admin/output/icon-values.json").write_text(
    json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8"
)
