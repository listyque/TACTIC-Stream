"""Capture actual native control states and paint; shared declarations are not evidence alone."""

import itertools
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/code/th_codex")
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Material",
)
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]
from PySide6.QtCore import QEventLoop, QTimer, Qt, QPoint, QPointF
from PySide6.QtGui import QFontMetricsF
from PySide6.QtTest import QTest
from tests.test_frame_controls import FrameControlsTests
from tests.profile_ui_responsiveness import frame
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes, controls
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests

OUT = Path(__file__).with_name("output")
OUT.mkdir(exist_ok=True)


def content_snapshot(window):
    result = {}
    for name, item in controls(window).items():
        if name not in {
            "button",
            "primary",
            "danger",
            "segment",
            "iconButton",
            "field",
            "area",
            "choice",
            "date",
            "user",
            "color",
            "icon",
            "menu",
            "checkLabel",
        } and not name.startswith("caption_"):
            continue
        descendants = list(SidebarEditorQmlTests.descendants(item))
        text = (
            item
            if name.startswith("caption_") or name in ("checkLabel", "field")
            else next(
                (
                    child
                    for child in descendants
                    if child.isVisible()
                    and child.objectName()
                    in (
                        "buttonLabel",
                        "comboBoxDisplayLabel",
                        "userComboBoxDisplayLabel",
                        "dateFieldPresentationLabel",
                    )
                ),
                None,
            )
        )
        if name == "area":
            text = next(
                child
                for child in descendants
                if "TextArea" in child.metaObject().className()
                and child.property("cursorRectangle") is not None
            )
        row = dict(icons=[])
        if text is not None:
            value = text.property("text")
            point = text.mapToScene(QPointF())
            row["text"] = dict(
                value=value,
                x=point.x() + (text.property("leftPadding") or 0),
                baseline=point.y() + text.property("baselineOffset"),
                advance=QFontMetricsF(text.property("font")).horizontalAdvance(value),
            )
        for glyph in descendants:
            if glyph.objectName() != "materialIconGlyph" or not glyph.isVisible():
                continue
            point = glyph.mapToScene(QPointF())
            row["icons"].append(
                dict(
                    value=glyph.property("text"),
                    family=glyph.property("resolvedSet"),
                    fontSize=glyph.property("font").pixelSize(),
                    x=point.x(),
                    y=point.y(),
                    width=glyph.width(),
                    height=glyph.height(),
                )
            )
        result[name] = row
    return result


def image(window, path):
    request = window.contentItem().grabToImage()
    assert request, "No renderable control catalog"
    ready = []
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    request.ready.connect(lambda: (ready.append(True), loop.quit()))
    timer.timeout.connect(loop.quit)
    timer.start(3000)
    loop.exec()
    timer.stop()
    assert ready and not request.image().isNull(), "No painted catalog frame"
    result = request.image()
    samples = {
        result.pixelColor(x, y).name()
        for x in range(0, result.width(), 13)
        for y in range(0, result.height(), 13)
    }
    assert len(samples) > 4, "Blank control capture"
    assert result.save(str(path))


def paints(window):
    result = {}
    for name, item in controls(window).items():
        if name not in (
            "button",
            "primary",
            "danger",
            "segment",
            "field",
            "check",
            "choice",
        ):
            continue
        surface = (
            item.property("indicator")
            if name == "check"
            else item.property("background")
        )
        if surface is None or surface.property("color") is None:
            continue
        color = surface.property("color")
        result[name] = dict(
            background=color.name(),
            alpha=color.alphaF(),
            content=(item.property("contentColor") or item.property("color")).name()
            if item.property("contentColor") or item.property("color")
            else "",
        )
    return result


def main():
    hashes = source_hashes(
        ROOT,
        HANDLER,
        [
            "thlib/ui/qml/UserComboBox.qml",
            "thlib/ui/qml/UserPicker.qml",
            "thlib/ui/qml/IconPickerButton.qml",
            "thlib/ui/qml/ActionMenu.qml",
            "thlib/ui/qml/ActionMenuRow.qml",
            "thlib/ui/translations/ru.json",
            "tests/fixtures/FrameControlsHarness.qml",
            "tests/test_frame_controls.py",
        ],
    )
    FrameControlsTests.setUpClass()
    case = FrameControlsTests()
    case.setUp()
    translator = CatalogTranslator(HANDLER / "thlib/ui/translations/ru.json")
    translated = False
    rows = []
    try:
        for style, mode, language, width, state in itertools.product(
            ("md3", "material5", "fluent"),
            ("dark", "light"),
            ("en", "ru"),
            (900, 360),
            ("idle", "disabled", "readonly", "error", "loading", "long"),
        ):
            if translated != (language == "ru"):
                if language == "ru":
                    case.app.installTranslator(translator)
                else:
                    case.app.removeTranslator(translator)
                translated = language == "ru"
                case.engine.retranslate()
            for key, value in dict(
                styleName=style, dark=mode == "dark", language=language, status=state
            ).items():
                case.window.setProperty(key, value)
            case.window.resize(width, 900)
            case.scroll(0)
            frame(case.window)
            for part, offset in (
                [("top", 0), ("middle", 700), ("bottom", 10000)]
                if width == 360
                else [("top", 0), ("bottom", 10000)]
            ):
                case.scroll(offset)
                filename = f"{style}-{mode}-{language}-{width}-{state}-{part}.png"
                image(case.window, OUT / filename)
                rows.append(
                    dict(
                        style=style,
                        mode=mode,
                        language=language,
                        width=width,
                        state=state,
                        part=part,
                        offset=case.item("catalogScroll").property("contentY"),
                        image=filename,
                        scene=json.loads(case.evaluate("sceneJson()")),
                        paint=paints(case.window),
                        content=content_snapshot(case.window),
                        **snapshot(case.window),
                    )
                )
            assert not case.warnings, case.warnings
        case.app.removeTranslator(translator)
        case.engine.retranslate()
        case.window.setProperty("status", "idle")
        case.window.setProperty("styleName", "md3")
        case.window.setProperty("dark", True)
        case.window.setProperty("language", "en")
        case.window.resize(900, 900)
        case.scroll(0)
        for name in ("button", "primary", "danger", "segment"):
            case.window.blur()
            item = case.item(name)
            point = item.mapToScene(item.boundingRect().center()).toPoint()
            for state in ("hover", "pressed", "focus"):
                if state == "hover":
                    QTest.mouseMove(case.window, QPoint(890, 890))
                    QTest.mouseMove(case.window, point)
                elif state == "pressed":
                    QTest.mousePress(case.window, Qt.LeftButton, pos=point)
                else:
                    QTest.mouseRelease(case.window, Qt.LeftButton, pos=point)
                    QTest.mouseMove(case.window, QPoint(890, 890))
                    QTest.keyClick(case.window, Qt.Key_Tab)
                    QTest.keyClick(case.window, Qt.Key_Backtab)
                frame(case.window)
                assert item.property(
                    {"hover": "hovered", "pressed": "down", "focus": "visualFocus"}[
                        state
                    ]
                ), (name, state)
                filename = f"interaction-{name}-{state}.png"
                image(case.window, OUT / filename)
                rows.append(
                    dict(
                        style="md3",
                        mode="dark",
                        language="en",
                        width=900,
                        state=state,
                        target=name,
                        part="top",
                        offset=0,
                        image=filename,
                        scene=json.loads(case.evaluate("sceneJson()")),
                        paint=paints(case.window),
                        content=content_snapshot(case.window),
                        **snapshot(case.window),
                    )
                )
        assert not case.warnings, case.warnings
    finally:
        case.app.removeTranslator(translator)
        case.doCleanups()
    assert hashes == source_hashes(
        ROOT,
        HANDLER,
        [
            "thlib/ui/qml/UserComboBox.qml",
            "thlib/ui/qml/UserPicker.qml",
            "thlib/ui/qml/IconPickerButton.qml",
            "thlib/ui/qml/ActionMenu.qml",
            "thlib/ui/qml/ActionMenuRow.qml",
            "thlib/ui/translations/ru.json",
            "tests/fixtures/FrameControlsHarness.qml",
            "tests/test_frame_controls.py",
        ],
    )
    (OUT / "qml.json").write_text(
        json.dumps(
            dict(sha256=hashes[0], nativeSources=hashes[1], captures=rows),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Native control captures:", len(rows))


if __name__ == "__main__":
    main()
