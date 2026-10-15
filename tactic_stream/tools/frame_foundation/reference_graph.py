"""Capture the pre-Frame Handler graph as an independent reference."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
REFERENCE = HERE / "reference"
archive = Path("D:/code/TACTIC_VUE/backups/2026-10-15_103116_before_shared_ui_foundation/TH_git_HEAD_reference.zip")
with ZipFile(archive) as source:
    for name in source.namelist():
        if name.startswith("thlib/ui/qml/") and not name.endswith("/"):
            target = REFERENCE / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read(name))
os.environ.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QT_FONT_DPI="96")
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from PySide6.QtCore import QCoreApplication, QEvent, QUrl, QPointF
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from thlib.ui.admin.graph_editor import GraphEditor
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import snapshot, controls

app = gui_test_application()
app.setFont(QFont("Segoe UI", 10))
QQuickWindow.setTextRenderType(QQuickWindow.NativeTextRendering)
icons = qml_icon_bindings(TH, app)
rows = []
for mode in ("schema", "workflow"):
    fixture = json.loads((ROOT / "tools/frame_graph_editor/output" / (mode + ".json")).read_text())["fixture"]
    for original in (True, False):
        controller = GraphEditor(SimpleNamespace(can_manage_tools=False, can_administer=True, debug_log=None), mode)
        for key, value in {"_project": "demo", "_loaded": True, "_can_write": True, "_identity": fixture["identity"],
                           "_catalog": fixture["catalog"], "_document": fixture["document"], "_original": fixture["document"],
                           "_metadata": fixture["metadata"], "_revision": "fixture"}.items():
            setattr(controller, key, copy.deepcopy(value))
        controller._document_loaded()
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        for key, value in icons.items():
            engine.rootContext().setContextProperty(key, value)
        engine.rootContext().setContextProperty("graphFixture", controller)
        qml = (REFERENCE / "thlib/ui/qml") if original else TH / "thlib/ui/qml"
        component = QQmlComponent(engine)
        component.setData(('import QtQuick\nimport QtQuick.Controls\nimport "' + qml.as_uri() + '" as TH\n'
                           'ApplicationWindow {visible:true;width:1600;height:900;color:theme.workspace;'
                           'TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}'
                           'TH.AdminGraphView{anchors.fill:parent;theme:theme;controller:graphFixture}}').encode(), QUrl())
        assert component.isReady(), [error.toString() for error in component.errors()]
        window = component.create()
        assert window
        try:
            for phase in ("initial", "node", "edge"):
                if phase == "node":
                    controller.select_nodes([controller.nodes[0]["identity"]], controller.nodes[0]["identity"])
                elif phase == "edge":
                    controller.select_edge(0)
                frame(window)
                filename = mode + ("-original-" if original else "-frame-") + phase + ".png"
                image = window.grabWindow()
                if phase == 'initial':
                    items = controls(window)
                    first = controller.nodes[0]['identity']
                    second = controller.nodes[1]['identity']
                    source = items['graphOutput_' + first]
                    target = items['graphInput_' + second]
                    start = source.mapToScene(QPointF(source.width() / 2, source.height() / 2))
                    end = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
                    x, y = round((start.x() + end.x()) / 2), round((start.y() + end.y()) / 2)
                    background = image.pixelColor(x, y + 8).getRgb()[:3]
                    assert any(sum(abs(a-b) for a,b in zip(image.pixelColor(x, y+offset).getRgb()[:3], background)) > 30
                               for offset in (-1, 0, 1)), (mode, original, 'Connection pixels are missing')
                assert image.save(str(OUT / filename))
                rows.append({"mode": mode, "original": original, "phase": phase, "image": filename, **snapshot(window)})
            assert not warnings, warnings
        finally:
            controller.shutdown()
            window.close()
            window.deleteLater()
            engine.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
(OUT / "original-graph.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print("Captured 12 original/Frame graph states")
