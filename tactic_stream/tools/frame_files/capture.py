"""Capture pinned original and current native production file presenters."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
OUT = ROOT / os.environ.get("FILES_FRAME_OUTPUT", "tools/frame_files/output")
REFERENCE = "d1973ded2e30052effc851f91d05a716579b29bf"
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Basic",
    QT_QPA_FONTDIR="C:/Windows/Fonts",
)

from PySide6.QtCore import QCoreApplication, QEvent, QUrl, QPoint, QRectF, Qt
from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from workspace_capture import capture as capture_workspace
from queue_capture import prepare as prepare_queue, prepare_sync, prepare_screenshot
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.frame_files_fixture import Fixture
from thlib.environment import env_mode
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes, controls


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(smoke):
    variants = (
        [("md3", True, "en"), ("md3", False, "ru")]
        if smoke
        else [
            (style, dark, language)
            for style in ("md3", "material5", "fluent")
            for dark in (False, True)
            for language in ("en", "ru")
        ]
    )
    for style, dark, language in variants:
        for screen, width, height in [
            ("matching", 1000, 700),
            ("matching", 640, 500),
            ("matching-locked", 640, 500),
            ("ingest", 1000, 700),
            ("ingest", 390, 700),
            ("ingest-advanced", 1000, 700),
            ("ingest-advanced", 640, 760),
            ("ingest-empty", 390, 700),
            ("drop-plate", 1000, 700),
            ("drop-plate", 390, 700),
            ("drop-plate-empty", 640, 500),
            ("queue", 1000, 700),
            ("queue", 390, 700),
            ("queue-advanced", 1000, 800),
            ("queue-advanced", 390, 800),
            ("queue-empty", 640, 500),
            ("workspace-inspector", 1000, 420),
            ("workspace-inspector", 390, 640),
            ("workspace-inspector-checkout", 640, 420),
            ("workspace-inspector-preview", 640, 420),
            ("workspace-depots", 1000, 700),
            ("workspace-depots-edit", 640, 700),
            ("workspace-depots-edit", 390, 700),
            ("workspace-storage", 1000, 800),
            ("workspace-storage", 390, 800),
        ]:
            yield dict(
                screen=screen,
                width=width,
                height=height,
                style=style,
                dark=dark,
                language=language,
            )
        if (style, dark, language) in (("md3", True, "en"), ("md3", False, "ru")):
            for screen in ("sync-queue", "sync-editor", "screenshot"):
                for width in (1000, 390):
                    yield dict(
                        screen=screen,
                        width=width,
                        height=800,
                        style=style,
                        dark=dark,
                        language=language,
                        nativeOnly=True,
                    )
            for screen in (
                "main",
                "submit",
                "revert",
                "revision",
                "shelf",
                "target",
                "review",
                "comparison",
                "graph",
                "mappings",
                "log",
            ):
                for width, height in ((1000, 800), (390, 700)):
                    yield dict(
                        screen="workspace-" + screen,
                        width=width,
                        height=height,
                        style=style,
                        dark=dark,
                        language=language,
                        nativeOnly=True,
                    )


def capture(app, qml, case, original):
    if case["screen"].startswith("workspace-"):
        return capture_workspace(app, qml, case, original, OUT)
    engine = QQmlEngine()
    engine.addImportPath(str(qml))
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    translator = (
        CatalogTranslator(TH / "thlib/ui/translations/ru.json")
        if case["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
    fixture = Fixture(case["language"])
    queue = case["screen"].startswith("queue")
    sync = case["screen"].startswith("sync-")
    capture_screen = case["screen"] == "screenshot"
    sync_context = prepare_sync(fixture, case["screen"]) if sync else {}
    if capture_screen:
        sync_context = prepare_screenshot(fixture)
    queue_owner = screenshot = None
    queue_rows = []
    if queue:
        queue_owner, screenshot, queue_rows = prepare_queue(fixture, case["screen"])
        for name, value in dict(
            commitQueueController=queue_owner,
            commitQueueModel=queue_owner.model,
            screenshotController=screenshot,
        ).items():
            engine.rootContext().setContextProperty(name, value)
    for name, value in dict(qml_icon_bindings(TH, app), **fixture.context()).items():
        engine.rootContext().setContextProperty(name, value)
    for name, value in sync_context.items():
        engine.rootContext().setContextProperty(name, value)
    matching = case["screen"].startswith("matching")
    drop_plate = case["screen"].startswith("drop-plate")
    if case["screen"] == "ingest-empty":
        fixture.ingest.clear_files()
    if case["screen"] == "drop-plate-empty":
        fixture.drop.clear()
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Theme.qml")))
    theme = theme_component.createWithInitialProperties(
        dict(
            dark=case["dark"],
            styleName=case["style"],
            fadeAnimationsEnabled=False,
            hoverAnimationsEnabled=False,
            clickAnimationsEnabled=False,
            popupAnimationsEnabled=False,
        )
    )
    assert theme, [error.toString() for error in theme_component.errors()]
    window = QQuickWindow()
    host_window = window
    window.resize(case["width"], case["height"])
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(
            str(
                qml
                / (
                    "MatchingTemplatesView.qml"
                    if matching
                    else "ScreenshotMakerView.qml"
                    if capture_screen
                    else "RepositorySyncEditorView.qml"
                    if case["screen"] == "sync-editor"
                    else "RepositorySyncView.qml"
                    if sync
                    else "CommitQueueView.qml"
                    if queue
                    else "DropPlateView.qml"
                    if drop_plate
                    else "IngestFilesView.qml"
                )
            )
        ),
    )
    view = component.createWithInitialProperties(
        dict(
            theme=theme,
            width=case["width"],
            height=case["height"],
            parent=window.contentItem(),
            **(
                dict(windowId="matching_templates")
                if matching
                else dict(windowId="repository_sync_editor")
                if case["screen"] == "sync-editor"
                else {}
            ),
        )
    )
    assert view, [error.toString() for error in component.errors()]
    view.setParentItem(window.contentItem())
    try:
        window.show()
        window.requestActivate()
        if capture_screen:
            QTest.qWait(50)
            window = next(item for item in app.allWindows() if item is not host_window and item.isVisible())
            window.resize(case["width"], case["height"])
        for _ in range(3):
            frame(window)
        if capture_screen:
            QTest.mousePress(window, Qt.LeftButton, pos=QPoint(48, 80))
            QTest.mouseMove(window, QPoint(case["width"] - 48, 310), delay=20)
            QTest.mouseRelease(
                window, Qt.LeftButton, pos=QPoint(case["width"] - 48, 310)
            )
        selected = 0 if case["screen"] == "matching-locked" else 2
        if matching:
            fixture.matching.select_row(selected)
        elif not drop_plate and not queue and not sync and not capture_screen:
            fixture.ingest.select_rule(1)
            view.setProperty("advancedVisible", case["screen"] == "ingest-advanced")
        if queue and case["screen"] == "queue-advanced" and case["width"] < 700:
            view.setProperty("detailsVisible", True)
        QTest.mouseMove(window, QPoint(window.width() - 1, window.height() - 1))
        for _ in range(3):
            frame(window)
        if not original:
            assert not warnings, "\n".join(warnings)
        measured = snapshot(window, check_icons=not original)
        indicator_paint, editable_parts = {}, {}
        for key, item in controls(window).items():
            if key.startswith("matchingEnabled_"):
                color = item.property("indicator").property("color")
                indicator_paint[key] = dict(color=color.name(), alpha=color.alphaF())
            if key in ("matching_process", "matching_context"):
                indicator = item.property("indicator")
                box = indicator.mapRectToScene(
                    QRectF(0, 0, indicator.width(), indicator.height())
                )
                editable_parts[key] = dict(
                    indicator=dict(
                        x=box.x(), y=box.y(), width=box.width(), height=box.height()
                    )
                )
        name = (
            "-".join(
                [
                    case["screen"],
                    "original" if original else "native",
                    case["style"],
                    "dark" if case["dark"] else "light",
                    case["language"],
                    str(case["width"]),
                ]
            )
            + ".png"
        )
        assert window.grabWindow().save(str(OUT / name))
        data = dict(
            fixture.data, inspection=fixture.matching.model._records, selected=selected
        )
        if (
            not matching
            and not drop_plate
            and not queue
            and not sync
            and not capture_screen
        ):
            data["ingest"] = dict(
                fixture.data["ingest"],
                files=fixture.ingest.files.records(),
                options=fixture.ingest.options,
                rules=[
                    dict(
                        code=row["ruleId"],
                        title=row["title"],
                        subtitle=row["subtitle"],
                        key=row["searchKey"],
                        applicable=row["applicable"],
                        options=dict(
                            fixture.ingest._rule_payloads[row["ruleId"]],
                            extraData=json.loads(
                                fixture.ingest._rule_payloads[row["ruleId"]][
                                    "extraDataJson"
                                ]
                            ),
                        ),
                    )
                    for row in fixture.ingest.rules.records()
                ],
            )
        if drop_plate:
            data["groups"] = fixture.drop.model.records()
        if queue:
            data["queue"] = queue_rows
        return dict(
            fixture=dict(case, model=data),
            original=original,
            image=name,
            indicatorPaint=indicator_paint,
            editableParts=editable_parts,
            originalWarnings=warnings if original else [],
            **measured,
        )
    finally:
        window.close()
        if window is not host_window:
            host_window.close()
            host_window.deleteLater()
        view.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        theme.deleteLater()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        fixture.close()
        if translator:
            app.removeTranslator(translator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--screen", help="Capture one screen while developing a comparison"
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    archived = ROOT / ".tmp/b12/original"
    archive = ROOT / ".tmp/b12/original-handler.zip"
    with zipfile.ZipFile(archive) as reference:
        assert reference.comment.decode("ascii") == REFERENCE
        for name in reference.namelist():
            if name.startswith("thlib/ui/qml/") and not name.endswith("/"):
                assert (archived / name).read_bytes() == reference.read(name), (
                    "Modified original: " + name
                )
    names = [
        path.relative_to(TH).as_posix() for path in (TH / "thlib/ui/qml").rglob("*.qml")
    ]
    names += [
        "thlib/ui/matching_templates.py",
        "thlib/ui/ingest.py",
        "thlib/ui/drop_plate.py",
        "thlib/ui/workspace_models/records.py",
        "thlib/checkin_operation.py",
        "tests/test_drop_plate.py",
        "tests/frame_files_fixture.py",
        "tests/test_frame_queue.py",
        "tests/test_commit_queue.py",
        "tests/test_frame_sync.py",
        "tests/test_frame_screenshot.py",
        "tests/test_screenshot_controller.py",
        "tests/test_repository_sync_editor.py",
        "thlib/ui/commit_queue.py",
        "tests/fixtures/frame_files.json",
    ]
    names.extend(path.relative_to(TH).as_posix() for path in (TH / "thlib/ui").rglob("*.py"))
    shared, native = source_hashes(ROOT, TH, names)
    drivers = {
        p.relative_to(ROOT).as_posix(): digest(p)
        for p in Path(__file__).parent.iterdir()
        if p.suffix in (".py", ".json", ".vue", ".mjs", ".html")
    }
    drivers["tools/frame_admin/native_capture.py"] = digest(
        ROOT / "tools/frame_admin/native_capture.py"
    )
    for name in [
        "tests/test_file_workspace_layout.py",
        "tests/test_handler_file_workspace_ui.py",
        "tests/test_file_project.py",
    ]:
        drivers[name] = digest(ROOT / name)
    app = gui_test_application()
    assert QFontInfo(QFont("Segoe UI")).family() == "Segoe UI", (
        "Native text font missing"
    )
    previous = env_mode.current_path
    rows = []
    with tempfile.TemporaryDirectory(prefix="frame-files-") as isolated:
        env_mode.current_path = isolated
        try:
            for original in (True, False):
                for case in cases(args.smoke):
                    if args.screen and case["screen"] != args.screen:
                        continue
                    rows.append(
                        capture(
                            app,
                            (archived if original else TH) / "thlib/ui/qml",
                            case,
                            original,
                        )
                    )
                    print(
                        "Captured",
                        original,
                        case["screen"],
                        case["width"],
                        case["style"],
                        case["language"],
                        flush=True,
                    )
        finally:
            env_mode.current_path = previous
    assert (shared, native) == source_hashes(ROOT, TH, names), (
        "Sources changed during capture"
    )
    assert drivers == {name: digest(ROOT / name) for name in drivers}
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                reference=REFERENCE,
                archive=digest(archive),
                shared=shared,
                nativeSources=native,
                driverSources=drivers,
                scale=float(os.environ.get("QT_SCALE_FACTOR", "1")),
                captures=rows,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
