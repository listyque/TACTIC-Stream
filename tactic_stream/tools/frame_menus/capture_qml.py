"""Real original/current native main-menu rows and footer captures."""

import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).resolve().parent / "output"
REFERENCE = "fa3f594c5cd09ce565ea14acb533302e79c9308a"
os.environ.update(
    QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QSG_RENDER_LOOP="basic"
)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRect, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
import tests.test_sidebar_editor_qml as fixture
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.ui.menu_schema import MenuRegistry
from native_capture import source_hashes


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reference = ROOT / "tools/frame_foundation/reference/main"
    with ZipFile(
        ROOT.parent / "backups/2026-10-15_103116_before_shared_ui_foundation/TH.zip"
    ) as archive:
        for name in archive.namelist():
            if name.startswith("thlib/ui/qml/") and not name.endswith("/"):
                target = reference / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
    app = gui_test_application()
    icons = qml_icon_bindings(TH, app)
    registry = MenuRegistry()
    translator = CatalogTranslator(TH / "thlib/ui/translations/ru.json")
    captures = []
    for original in (True, False):
        qml = reference / "thlib/ui/qml" if original else TH / "thlib/ui/qml"
        for theme in ("md3", "material5", "fluent"):
            for language in ("en", "ru"):
                if language == "ru":
                    app.installTranslator(translator)
                for kind in ("user", "configuration", "connection"):
                    engine = QQmlEngine()
                    warnings = []
                    engine.warnings.connect(
                        lambda errors: warnings.extend(e.toString() for e in errors)
                    )
                    for name, value in icons.items():
                        engine.rootContext().setContextProperty(name, value)
                    records = registry.actions(kind)
                    for record in records:
                        if record.get("command") == "show_messages":
                            record["badgeCount"] = 7
                        if record.get("command") == "update_summary":
                            record["status"] = "One batched server request"
                        if record.get("command") in ("update_mode_poll", "updates_30"):
                            record["checked"] = True
                    component = QQmlComponent(engine)
                    source = f'''import QtQuick
import QtQuick.Controls
import "{qml.as_uri()}" as TH
import "{(qml / "controls").as_uri()}" as Controls
Window {{
    id: window; visible:true; width:900; height:850
    color: uiTheme.workspace
    property var records: {json.dumps(records)}
    TH.Theme {{ id:uiTheme; dark:{str(language == "en").lower()}; styleName:"{theme}"; popupAnimationsEnabled:false; hoverAnimationsEnabled:false }}
    TH.ActionMenu {{ id:menu; objectName:"menu"; theme:uiTheme; usePopupWindow:false; preferredWidth:{330 if kind == "connection" else 244}
        {"frameComposition:true;" if not original else ""}
        actions:window.records
    }}
    Controls.DockWorkspaceFooter {{ objectName:"footer"; theme:uiTheme; width:300; anchors.bottom:parent.bottom }}
    function showMenu() {{ menu.openAt(window.contentItem,20,20,false) }}
    function closeMenu() {{ menu.close() }}
}}'''
                    component.setData(source.encode(), QUrl())
                    assert component.isReady(), [
                        e.toString() for e in component.errors()
                    ]
                    window = component.create()
                    assert window
                    window.showMenu()
                    frame(window)
                    menu = window.findChild(QObject, "menu")
                    content = menu.property("contentItem")
                    rows = []
                    for item in fixture.SidebarEditorQmlTests.descendants(content):
                        if item.objectName() != "actionMenuPrimaryTarget":
                            continue
                        parent = item.parentItem()
                        record = parent.property("modelData").toVariant()
                        boxes = {}
                        for child in fixture.SidebarEditorQmlTests.descendants(parent):
                            name = child.objectName()
                            if (
                                name
                                and child.isVisible()
                                and (
                                    name.startswith("menu")
                                    if not original
                                    else name.startswith("actionMenu")
                                )
                            ):
                                point = child.mapToItem(parent, QPointF())
                                boxes[name] = dict(
                                    x=point.x(),
                                    y=point.y(),
                                    width=child.width(),
                                    height=child.height(),
                                )
                                font = child.property("font")
                                if font is not None:
                                    boxes[name]["fontSize"] = font.pixelSize()
                        rows.append(
                            dict(
                                command=record.get("command", ""),
                                title=record.get("title", ""),
                                height=parent.height(),
                                width=parent.width(),
                                boxes=boxes,
                            )
                        )
                    label = f"{kind}-{theme}-{language}"
                    image = ("original-" if original else "native-") + label + ".png"
                    assert (
                        window.grabWindow()
                        .copy(
                            QRect(
                                int(menu.property("x")),
                                int(menu.property("y")),
                                int(menu.property("width")),
                                int(menu.property("height")),
                            )
                        )
                        .save(str(OUT / image))
                    )
                    footer = window.findChild(QObject, "footer")
                    footer_data = {
                        key: footer.property(key)
                        for key in (
                            "height",
                            "topLeftRadius",
                            "topRightRadius",
                            "bottomLeftRadius",
                            "bottomRightRadius",
                        )
                    }
                    footer_image = (
                        ("original-" if original else "native-") + label + "-footer.png"
                    )
                    assert (
                        window.grabWindow()
                        .copy(QRect(0, 792, 300, 58))
                        .save(str(OUT / footer_image))
                    )
                    captures.append(
                        dict(
                            id=label,
                            kind=kind,
                            theme=theme,
                            language=language,
                            original=original,
                            image=image,
                            rows=rows,
                            footer=footer_data,
                            footerImage=footer_image,
                        )
                    )
                    window.closeMenu()
                    frame(window)
                    window.close()
                    window.deleteLater()
                    engine.deleteLater()
                    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                    assert not warnings, warnings
                if language == "ru":
                    app.removeTranslator(translator)
    shared, native = source_hashes(
        ROOT,
        TH,
        [
            "thlib/ui/qml/ActionMenu.qml",
            "thlib/ui/qml/ActionMenuRow.qml",
            "thlib/ui/qml/Main.qml",
            "thlib/ui/qml/controls/DockWorkspaceFooter.qml",
            "thlib/ui/menu_schema.py",
        ],
    )
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                reference=REFERENCE,
                captures=captures,
                sha256=shared,
                nativeSources=native,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Main menus: 18 original + 18 Frame native captures, three themes, EN/RU; real ActionMenu and footer."
    )


if __name__ == "__main__":
    main()
