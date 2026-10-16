"""Actual archived/native chooser, card and workspace tab captures."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
OUT = Path(__file__).resolve().parent / "output"
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QSG_RENDER_LOOP="basic",
    QT_QPA_FONTDIR=str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"),
    QT_FONT_DPI="96",
)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
import tests.test_sidebar_editor_qml as fixture
from native_capture import source_hashes
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QRect, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from tests.profile_ui_responsiveness import frame
from tests.qt_application import gui_test_application
from tests.test_project_catalog import _Project
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.ui.models import ProjectModel
from thlib.ui.workspace_models.sections import SectionTab, SectionTabModel


def model():
    result = ProjectModel()
    projects = [
        _Project("one"),
        _Project("two"),
        _Project("empty", category=""),
        _Project("retired", retired=True),
        _Project("template", template=True, category="Templates"),
        _Project("builtin", builtin=True, category="System"),
    ]
    for project, title, description in zip(
        projects,
        [
            "Project one",
            "Project two",
            "Without category",
            "Archived project",
            "Template project",
            "Built-in project",
        ],
        [
            "Short description",
            "A much longer description that should wrap into several lines in a narrow project card with lots of extra data",
            "",
            "Archived description",
            "",
            "",
        ],
    ):
        project.info.update(
            name=title,
            description=description,
            type="classic"
            if project.code not in ("builtin", "empty")
            else "admin"
            if project.code == "builtin"
            else "",
            status="",
        )
    result.replace(projects)
    return result


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
        for style in ("md3", "material5", "fluent"):
            for language in ("en", "ru"):
                if language == "ru":
                    app.installTranslator(translator)
                for kind, variant in [
                    ("chooser", 0),
                    ("card", 0),
                    ("card", 1),
                    ("tab", 0),
                    ("tab", 1),
                    ("tab", 2),
                    ("rail", 0),
                    ("rail", 1),
                    ("rail", 2),
                    ("rail", 3),
                ]:
                    engine = QQmlEngine()
                    warnings = []
                    engine.warnings.connect(
                        lambda errors, warnings=warnings: warnings.extend(
                            error.toString() for error in errors
                        )
                    )
                    for name, value in icons.items():
                        engine.rootContext().setContextProperty(name, value)
                    catalog = model()
                    engine.rootContext().setContextProperty("projectCatalog", catalog)
                    details = dict(
                        catalog.groups[0]["projects"][variant if variant < 2 else 0]
                    )
                    section_model = SectionTabModel()
                    section_model.replace(
                        [
                            SectionTab("assets", "Assets", "#6f9fc1", True, "assets"),
                            SectionTab("shots", "Shots", "#9f80c1", False, "movie"),
                        ]
                    )
                    engine.rootContext().setContextProperty(
                        "sectionCatalog", section_model
                    )
                    if kind == "rail":
                        body = "TH.SectionTabRail {theme:theme;model:sectionCatalog;height:260} function showContent(){}"
                    elif kind == "chooser":
                        body = (
                            "TH.ProjectChooser{id:chooser;model:projectCatalog;theme:theme;usePopupWindow:false;"
                            + ("" if original else 'selectedCode:"one";')
                            + "} function showContent(){chooser.openCenteredIn(window.contentItem)}"
                        )
                    elif kind == "card":
                        body = f'Controls.ProjectCard{{objectName:"card";x:12;y:12;theme:theme;width:248;height:258;details:({json.dumps(details)})}} function showContent(){{}}'
                    else:
                        body = f'Controls.WorkspaceTabVisual{{theme:theme;width:180;height:50;title:"Assets";closable:true;current:{str(variant == 1).lower()};hovered:{str(variant == 2).lower()};dirty:{str(variant == 2).lower()};animateSelection:false}} function showContent(){{}}'
                    width, height = (
                        (900, 800)
                        if kind == "chooser"
                        else (272, 282)
                        if kind == "card"
                        else (400, 260)
                        if kind == "rail"
                        else (180, 50)
                    )
                    source = f'''import QtQuick
import QtQuick.Controls
import "{qml.as_uri()}" as TH
import "{(qml / "controls").as_uri()}" as Controls
ApplicationWindow{{id:window;visible:true;width:{width};height:{height};color:theme.workspace;TH.Theme{{id:theme;dark:{str(language == "en").lower()};styleName:"{style}";fadeAnimationsEnabled:false;popupAnimationsEnabled:false;hoverAnimationsEnabled:false;clickAnimationsEnabled:false}} {body} Item{{id:focusSink;objectName:"focusSink";focus:true;width:1;height:1}}}}'''
                    component = QQmlComponent(engine)
                    component.setData(source.encode(), QUrl())
                    assert component.isReady(), [
                        error.toString() for error in component.errors()
                    ]
                    window = component.create()
                    assert window
                    try:
                        frame(window)
                        window.showContent()
                        QTest.mouseMove(window, QPoint(1, 1))
                        for focus_item in fixture.SidebarEditorQmlTests.descendants(
                            window.contentItem()
                        ):
                            if focus_item.objectName() == "focusSink":
                                focus_item.forceActiveFocus()
                        if kind == "rail":
                            QTest.mouseMove(window, QPoint(390, 250))
                            QTest.qWait(400)
                            if variant:
                                point = QPoint(20, 28 if variant == 1 else 73)
                                QTest.mouseMove(window, point)
                                QTest.qWait(180)
                                if variant == 3:
                                    QTest.mousePress(window, Qt.LeftButton, pos=point)
                        for _ in range(3):
                            frame(window)
                        image = f"{'original' if original else 'native'}-{kind}-{style}-{language}-{variant}.png"
                        snapshot = window.grabWindow()
                        if kind == "card":
                            snapshot = snapshot.copy(QRect(12, 12, 248, 258))
                        assert snapshot.save(str(OUT / image))
                        boxes = {}
                        paints = {}
                        rounding = {}
                        for item in fixture.SidebarEditorQmlTests.descendants(
                            window.contentItem()
                        ):
                            name = item.objectName()
                            if kind == "rail" and name != "sectionRailBackground":
                                owner = item
                                while (
                                    owner and owner.objectName() != "sectionTabDelegate"
                                ):
                                    owner = owner.parentItem()
                                if owner and owner.property("index") != (
                                    1 if variant > 1 else 0
                                ):
                                    continue
                                if original and item.property("text") in (
                                    "Assets",
                                    "Shots",
                                ):
                                    name = "sectionTabTitle"

                            paint = (
                                item.property("fallbackColor")
                                if name == "projectGridPreview"
                                else item.property("color")
                            )
                            if name and isinstance(paint, QColor) and paint.isValid():
                                paints[name] = paint.name()
                            if not original and name == "sectionTabBadge":
                                rounding[name] = [
                                    item.property(corner)
                                    for corner in (
                                        "topLeftRadius",
                                        "topRightRadius",
                                        "bottomRightRadius",
                                        "bottomLeftRadius",
                                    )
                                ]

                            if original and kind == "card":
                                text = item.property("text")
                                mapping = {
                                    details["title"]: "projectCardTitle",
                                    details["description"]: "projectCardDescription",
                                    details["category"]: "projectCardCategory",
                                    details["projectType"]: "projectCardType",
                                }
                                name = mapping.get(text, name)
                            if (
                                original
                                and kind == "chooser"
                                and item.property("text") in ("Projects", "Проекты")
                            ):
                                name = "projectChooserTitle"

                            if (
                                name
                                in (
                                    "projectChooserTitle",
                                    "projectChooserSummary",
                                    "projectChooserDivider",
                                    "projectGridPreview",
                                    "projectCardTitle",
                                    "projectCardDescription",
                                    "projectCardCategory",
                                    "projectCardType",
                                    "workspaceTabSelectionIndicator",
                                    "workspaceTabSelectionLabel",
                                    "sectionTabSurface",
                                    "sectionTabBadge",
                                    "sectionTabTitle",
                                    "sectionTabIcon",
                                    "sectionTabCloseButton",
                                    "sectionRailBackground",
                                )
                                and item.isVisible()
                            ):
                                point = item.mapToItem(window.contentItem(), QPointF())
                                boxes[name] = {
                                    "x": point.x() - (12 if kind == "card" else 0),
                                    "y": point.y() - (12 if kind == "card" else 0),
                                    "width": item.width(),
                                    "height": item.height(),
                                }
                        assert not warnings, warnings
                        captures.append(
                            {
                                "id": f"{kind}-{style}-{language}-{variant}",
                                "kind": kind,
                                "style": style,
                                "language": language,
                                "variant": variant,
                                "original": original,
                                "image": image,
                                "boxes": boxes,
                                "paints": paints,
                                "rounding": rounding,
                            }
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
            "thlib/ui/qml/ProjectChooser.qml",
            "thlib/ui/qml/controls/ProjectCard.qml",
            "thlib/ui/qml/controls/WorkspaceTabVisual.qml",
            "thlib/ui/models.py",
            "thlib/ui/qml/SectionTabRail.qml",
            "thlib/ui/qml/qmldir",
            "thlib/ui/qml/ActionMenu.qml",
        ],
    )
    (OUT / "native.json").write_text(
        json.dumps(
            {"captures": captures, "sha256": shared, "nativeSources": native}, indent=2
        ),
        encoding="utf-8",
    )
    print("60 original/current native captures, zero QML warnings.")


if __name__ == "__main__":
    main()
