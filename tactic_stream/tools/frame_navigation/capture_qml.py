"""Capture the shipped drawer against the archived native container."""

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).resolve().parent / "output"
os.environ.update(
    QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QSG_RENDER_LOOP="basic"
)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtGui import QFontInfo
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
import tests.test_sidebar_editor_qml as fixture
from thlib.ui.models import NavigationEntry, NavigationModel
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import source_hashes


def records():
    return [
        NavigationEntry("group", "Assets", "", "", "", entry_type="section"),
        *[
            NavigationEntry(
                f"entry{i}",
                f"Asset {i}",
                "cube",
                "",
                "open",
                badge=7 if i == 0 else 0,
                depth=1,
            )
            for i in range(16)
        ],
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = gui_test_application()
    icons = qml_icon_bindings(TH, app)
    translator = CatalogTranslator(TH / "thlib/ui/translations/ru.json")
    captures = []
    for original in (True, False):
        qml = (
            ROOT / "tools/frame_foundation/reference/main/thlib/ui/qml"
            if original
            else TH / "thlib/ui/qml"
        )
        assert qml.is_dir(), (
            "Run tools/frame_menus/capture_qml.py to extract the authorized archive first"
        )
        for width in (900, 320):
            for style in ("md3", "material5", "fluent"):
                for language in ("en", "ru"):
                    if language == "ru":
                        app.installTranslator(translator)
                    engine = QQmlEngine()
                    warnings = []
                    engine.warnings.connect(
                        lambda errors: warnings.extend(e.toString() for e in errors)
                    )
                    for name, value in icons.items():
                        engine.rootContext().setContextProperty(name, value)
                    model = NavigationModel(records())
                    engine.rootContext().setContextProperty("navModel", model)
                    source = f'''import QtQuick
import QtQuick.Controls
import "{qml.as_uri()}" as TH
ApplicationWindow {{
    id: window; visible:true; width:{width}; height:640; color:theme.workspace
    TH.Theme {{id:theme;dark:{str(language == "en").lower()};styleName:"{style}";fadeAnimationsEnabled:false;popupAnimationsEnabled:false;hoverAnimationsEnabled:false}}
    TH.NavigationDrawer {{id:drawer;objectName:"drawer";model:navModel;theme:theme;selectedKey:"entry0";sidebarEditingAvailable:true}}
    function showDrawer() {{drawer.open()}}
}}'''
                    component = QQmlComponent(engine)
                    component.setData(source.encode(), QUrl())
                    assert component.isReady(), [
                        e.toString() for e in component.errors()
                    ]
                    window = component.create()
                    assert window
                    try:
                        window.showDrawer()
                        for _ in range(3):
                            frame(window)
                        drawer = window.findChild(QObject, "drawer")
                        boxes = {}
                        captions = {}
                        for item in fixture.SidebarEditorQmlTests.descendants(drawer):
                            name = item.objectName()
                            text = item.property("text")
                            if name.startswith("navigation") and name in (
                                "navigationSurface",
                                "navigationTitle",
                                "navigationSubtitle",
                                "navigationDivider",
                                "navigationList",
                            ):
                                key = name
                            elif original and text in (
                                "Navigation",
                                "Project workspace",
                                "Навигация",
                                "Рабочее пространство проекта",
                            ):
                                key = (
                                    "navigationTitle"
                                    if text in ("Navigation", "Навигация")
                                    else "navigationSubtitle"
                                )
                            elif (
                                original
                                and item.property("spacing") == 0
                                and item.property("count") == 17
                            ):
                                key = "navigationList"
                            elif name == "editSidebarButton":
                                key = "navigationEdit"
                            elif name == "navigationCloseButton":
                                key = "navigationClose"
                            else:
                                continue
                            point = item.mapToItem(drawer, QPointF())
                            boxes[key] = dict(
                                x=point.x(),
                                y=point.y(),
                                width=item.width(),
                                height=item.height(),
                            )
                            if key in ("navigationTitle", "navigationSubtitle"):
                                captions[key] = str(item.property("text"))
                                font = item.property("font")
                                boxes[key]["fontSize"] = QFontInfo(font).pixelSize()
                        rows = {}
                        for item in fixture.SidebarEditorQmlTests.descendants(drawer):
                            if item.property("rowType") not in (
                                "section",
                                "link",
                            ) or item.property("title") not in (
                                "Assets",
                                "Asset 0",
                                "Asset 1",
                            ):
                                continue
                            point = item.mapToItem(drawer, QPointF())
                            rows[item.property("title")] = dict(
                                x=point.x(),
                                y=point.y(),
                                width=item.width(),
                                height=item.height(),
                            )
                        assert len(captions) == 2, (language, captions)
                        sample = f"{width}-{style}-{language}"
                        image = f"{'original' if original else 'native'}-{sample}.png"
                        assert window.grabWindow().save(str(OUT / image))
                        assert not warnings, warnings
                        captures.append(
                            dict(
                                id=sample,
                                original=original,
                                boxes=boxes,
                                captions=captions,
                                rows=rows,
                                image=image,
                            )
                        )
                    finally:
                        window.close()
                        window.deleteLater()
                        engine.deleteLater()
                        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                    if language == "ru":
                        app.removeTranslator(translator)
    shared, native = source_hashes(
        ROOT,
        TH,
        [
            "thlib/ui/qml/NavigationDrawer.qml",
            "thlib/ui/qml/controls/NavigationRow.qml",
            "thlib/ui/models.py",
        ],
    )
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                captures=captures,
                sha256=shared,
                nativeSources=native,
                reference="fa3f594c5cd09ce565ea14acb533302e79c9308a",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print("12 original/current drawer pairs, zero QML warnings.")


if __name__ == "__main__":
    main()
