"""Actual standalone house-control variants; no application session or server."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).with_name("output") / "variants"
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Material",
    QSG_RENDER_LOOP="basic",
    QT_QPA_FONTDIR=str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"),
    QT_FONT_DPI="96",
)
if "--native" in sys.argv or "--interactive" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ.pop("QT_QUICK_BACKEND", None)
    os.environ["QSG_RHI_BACKEND"] = "opengl"

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt, QUrl
from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.qt_application import (
    gui_test_application,
    suppress_windows_test_error_dialogs,
)
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.test_frame_controls import Cells
from tests.profile_ui_responsiveness import frame
from thlib.ui.source_editor import SourceEditorService
from thlib.ui.emoji import EmojiCatalog
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.ui.workspace_models.records import RecordListModel
from native_capture import source_hashes


def evaluate(engine, window, expression):
    call = QQmlExpression(engine.rootContext(), window, expression)
    value, _ = call.evaluate()
    assert not call.hasError(), call.error().toString()
    return value.toVariant() if hasattr(value, "toVariant") else value


def measure(window):
    items = SidebarEditorQmlTests.descendants(window.contentItem())
    result = {}
    for item in items:
        if not item.objectName() or not item.isVisible():
            continue
        if item.objectName() not in (
            "sample",
            "exampleControl",
            "exampleTitle",
            "exampleEvents",
        ):
            continue
        point = item.mapToScene(QPointF())
        result[item.objectName()] = dict(
            x=point.x(), y=point.y(), width=item.width(), height=item.height()
        )
    assert "sample" in result, result
    return result


def content(window, engine):
    """Read the instantiated text nodes, including icons, rather than the scene spec."""
    result = []
    sample = next(
        item
        for item in SidebarEditorQmlTests.descendants(window.contentItem())
        if item.objectName() == "sample"
    )
    for item in SidebarEditorQmlTests.descendants(sample):
        if (
            not item.isVisible()
            or item.property("text") is None
            or item.property("font") is None
        ):
            continue
        # Controls expose text too; only their painted Text/TextInput children count.
        if not any(
            item.inherits(name)
            for name in ("QQuickText", "QQuickTextInput", "QQuickTextEdit")
        ):
            continue
        font = item.property("font")
        color = item.property("color")
        point = item.mapToScene(QPointF())
        sample_point = sample.mapToScene(QPointF())
        if (
            point.y() + item.height() <= sample_point.y()
            or point.y() >= sample_point.y() + sample.height()
        ):
            continue
        alignment = evaluate(
            engine,
            item,
            'typeof horizontalAlignment === "undefined" ? 0 : Number(horizontalAlignment)',
        )
        content_width = item.property("contentWidth")
        painted_x = point.x() + (item.property("leftPadding") or 0)
        if alignment == 4:
            painted_x += max(
                0,
                (
                    item.width()
                    - (item.property("leftPadding") or 0)
                    - (item.property("rightPadding") or 0)
                    - content_width
                )
                / 2,
            )
        elif alignment == 2:
            painted_x += max(0, item.width() - content_width)
        baseline = point.y() + item.property("baselineOffset")
        if item.inherits("QQuickTextInput"):
            # Qt can retain an old baselineOffset after a Loader/layout resize.
            baseline = (
                point.y()
                + (item.property("topPadding") or 0)
                + evaluate(engine, item, "positionToRectangle(0).y")
                + QFontMetricsF(font).ascent()
            )
        result.append(
            dict(
                text=str(item.property("text")),
                name=item.objectName(),
                x=painted_x,
                y=point.y(),
                baseline=baseline,
                advance=QFontMetricsF(font).horizontalAdvance(
                    str(item.property("text"))
                ),
                width=item.width(),
                height=item.height(),
                fontSize=font.pixelSize()
                if font.pixelSize() > 0
                else font.pointSizeF() * 96 / 72,
                weight=int(font.weight()),
                family=font.family(),
                color=color.name() if hasattr(color, "name") else None,
            )
        )
    return result


def background(window):
    items = list(SidebarEditorQmlTests.descendants(window.contentItem()))
    item = next(
        (item for item in items if item.objectName() == "exampleControl"),
        next(item for item in items if item.objectName() == "sample"),
    )
    surface = item if item.inherits("QQuickRectangle") else item.property("background")
    if surface is None:
        surface = next(
            (
                child
                for child in item.childItems()
                if child.inherits("QQuickRectangle")
                and abs(child.width() - item.width()) < 0.1
                and abs(child.height() - item.height()) < 0.1
            ),
            None,
        )
    if surface is not None and (
        abs(surface.width() - item.width()) > 0.1
        or abs(surface.height() - item.height()) > 0.1
    ):
        return None
    color = surface.property("color") if surface else None
    return color.name() if color is not None and color.alphaF() == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--example", default="button")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not args.smoke and not args.interactive:
        (OUT / "native.json").write_text(
            json.dumps({"status": "capturing"}), encoding="utf-8"
        )
    if args.native or args.interactive:
        suppress_windows_test_error_dialogs()
        app = QGuiApplication([])
    else:
        app = gui_test_application()
    app.setFont(QFont("Segoe UI", 10))
    QQuickWindow.setTextRenderType(QQuickWindow.NativeTextRendering)
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    for name, value in qml_icon_bindings(HANDLER, app).items():
        engine.rootContext().setContextProperty(name, value)
    roles = (
        "login",
        "displayName",
        "initials",
        "avatarUrl",
        "avatarColor",
        "groups",
        "primaryGroup",
        "current",
        "retired",
    )
    users = RecordListModel(roles)
    emoji = EmojiCatalog(HANDLER)
    cells = Cells()
    source_editor = SourceEditorService()
    engine.rootContext().setContextProperty("controlCells", cells)
    engine.rootContext().setContextProperty("sourceEditor", source_editor)
    engine.rootContext().setContextProperty("userListModel", users)
    engine.rootContext().setContextProperty("emojiCatalog", emoji)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(
            str(HANDLER / "tests/fixtures/frame_controls/ControlVariantsHarness.qml")
        ),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None, [error.toString() for error in component.errors()]
    users.replace(json.loads(evaluate(engine, window, "userRecordsJson()")))
    translator = CatalogTranslator(HANDLER / "thlib/ui/translations/ru.json")
    captures = []
    try:
        if args.interactive:

            def change_language():
                if window.property("language") == "ru":
                    app.installTranslator(translator)
                else:
                    app.removeTranslator(translator)
                engine.retranslate()

            window.languageChanged.connect(change_language)
            window.setProperty("interactive", True)
            window.resize(900, 640)
            evaluate(engine, window, f'configure({json.dumps(args.example)}, "idle")')
            app.exec()
            return
        examples = evaluate(engine, window, "examplesJson()")
        examples = json.loads(examples)
        configurations = (
            [("md3", "dark", "en", 360)]
            if args.smoke or args.quick
            else [
                (style, mode, language, width)
                for style in ("md3", "material5", "fluent")
                for mode in ("dark", "light")
                for language in ("en", "ru")
                for width in (360, 900)
            ]
        )
        for style, mode, language, width in configurations:
            if language == "ru":
                app.installTranslator(translator)
            else:
                app.removeTranslator(translator)
            engine.retranslate()
            window.setProperty("dark", mode == "dark")
            window.setProperty("styleName", style)
            window.setProperty("language", language)
            window.setWidth(width)
            for example in examples:
                warnings.clear()
                QTest.keyClick(window, Qt.Key_Escape)
                evaluate(
                    engine, window, f'configure({json.dumps(example["id"])}, "idle")'
                )
                QTest.mouseMove(window, QPointF(width - 2, 500).toPoint())
                QTest.qWait(30)
                if example["id"] == "preview-broken":
                    image = next(
                        item
                        for item in SidebarEditorQmlTests.descendants(
                            window.contentItem()
                        )
                        if item.objectName() == "previewSourceImage"
                    )
                    for _ in range(100):
                        if evaluate(engine, image, "status === 3"):
                            break
                        QTest.qWait(10)
                    assert evaluate(engine, image, "status === 3"), (
                        "Broken preview never settled"
                    )
                window.update()
                if args.native:
                    assert not window.property("softwareRenderer"), (
                        "Mask evidence requires the production native graphics backend"
                    )
                expected_image_error = example["id"] == "preview-broken"
                unexpected = [
                    message
                    for message in warnings
                    if not (
                        expected_image_error
                        and "QQuickImage: Cannot open:" in message
                        and "missing-example.png" in message
                    )
                ]
                assert not unexpected, (example["id"], unexpected)
                boxes = measure(window)
                if example["id"] in (
                    "preview-photo",
                    "preview-contain",
                    "preview-selected",
                    "avatar-photo",
                ):
                    preview = next(
                        item
                        for item in SidebarEditorQmlTests.descendants(
                            window.contentItem()
                        )
                        if item.objectName() == "sample"
                        and item.property("sourcePixelWidth") is not None
                    )
                    for _ in range(100):
                        if preview.property("sourcePixelWidth") > 0:
                            break
                        QTest.qWait(10)
                    assert preview.property("sourcePixelWidth") > 0, example["id"]
                    if args.native:
                        frame(window)
                        frame(window)
                if example["kind"] not in json.loads(
                    evaluate(engine, window, "directKindsJson()")
                ):
                    assert "exampleControl" in boxes, example["id"]
                filename = f"{example['id']}-{style}-{mode}-{language}-{width}.png"
                if not args.smoke:
                    assert window.grabWindow().save(str(OUT / filename))
                captures.append(
                    dict(
                        id=example["id"],
                        family=example["family"],
                        kind=example["kind"],
                        style=style,
                        mode=mode,
                        language=language,
                        width=width,
                        state="idle",
                        boxes=boxes,
                        scene=json.loads(evaluate(engine, window, "sceneJson()")),
                        background=background(window),
                        content=content(window, engine),
                        image=filename,
                    )
                )
            print(
                style,
                mode,
                language,
                width,
                len(examples),
                "native variants passed",
                flush=True,
            )
        if not args.smoke:
            shared, sources = source_hashes(
                ROOT,
                HANDLER,
                [
                    "tests/fixtures/frame_controls/ControlVariantsHarness.qml",
                    "tests/fixtures/frame_controls/ControlExample.qml",
                    "thlib/ui/qml/UserIdentity.qml",
                    "thlib/ui/qml/UserPicker.qml",
                    "thlib/ui/qml/EmojiPicker.qml",
                    "thlib/ui/qml/MessageSendButton.qml",
                    *[
                        "thlib/ui/qml/" + name + ".qml"
                        for name in (
                            "UserComboBox",
                            "IconPickerButton",
                            "ActionMenu",
                            "ActionMenuRow",
                            "ContentLoadingOverlay",
                            "UserGroupSection",
                            "MessageReactionChip",
                            "ConfigurationSection",
                            "SObjectFieldFrame",
                            "QuickFilterChip",
                            "QuickFilterOptions",
                        )
                    ],
                    "thlib/ui/translations/ru.json",
                    "tests/test_control_variants.py",
                    "tests/profile_ui_responsiveness.py",
                ],
            )
            (OUT / "native.json").write_text(
                json.dumps(
                    dict(
                        status="captured",
                        captures=captures,
                        backend="windows-opengl"
                        if args.native
                        else "software-offscreen",
                        sha256=shared,
                        nativeSources=sources,
                        driverSources={
                            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                            for name in (
                                "tools/frame_controls/capture_variants.py",
                                "tools/frame_admin/native_capture.py",
                            )
                        },
                    ),
                    indent=2,
                ),
                encoding="utf-8",
            )
    finally:
        window.close()
        window.deleteLater()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


if __name__ == "__main__":
    main()
