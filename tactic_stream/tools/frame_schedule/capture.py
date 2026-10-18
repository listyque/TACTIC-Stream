"""Pinned original Handler, production Frame Handler and production Vue evidence."""

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
OUT = ROOT / os.environ.get("SCHEDULE_FRAME_OUTPUT", "tools/frame_schedule/output")
REFERENCE = "8d18661f1a070b68930eb56afa997c142708b622"
sys.path[:0] = [
    str(TH),
    str(ROOT / "tools/frame_admin"),
    str(ROOT / "tools/frame_objects"),
]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Basic",
)
from PySide6.QtCore import QCoreApplication, QEvent, QUrl, QPoint, QRectF, Qt
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from native_capture import snapshot, source_hashes, controls, click
from object_fixtures import Locale
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_tasks_controller import (
    FakeApplication,
    FakeTask,
    TaskConfigurationProbe,
)
from tests.test_milestones import FakeApplication as MilestoneApplication
from thlib.ui.tasks import TasksController
from thlib.ui.milestones import MilestoneController
from thlib.environment import env_mode
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures(smoke):
    cases = [
        ("gantt", 1200, 540),
        ("gantt", 520, 420),
        ("hover", 1200, 540),
        ("calendar", 800, 580),
        ("calendar", 360, 450),
        ("milestones", 900, 440),
        ("milestones", 420, 500),
        ("editor", 380, 280),
        ("empty", 800, 480),
        ("agenda", 800, 580),
        ("milestone-draft", 900, 440),
        ("milestone-error", 420, 560),
        ("milestone-empty", 800, 480),
    ]
    variants = (
        [("md3", True, "en"), ("md3", True, "ru")]
        if smoke
        else [
            (style, dark, lang)
            for style in ("md3", "material5", "fluent")
            for dark in (False, True)
            for lang in ("en", "ru")
        ]
    )
    for style, dark, language in variants:
        for screen, width, height in cases:
            yield dict(
                screen=screen,
                width=width,
                height=height,
                style=style,
                dark=dark,
                language=language,
            )


def data():
    fixture = json.loads(
        (ROOT / "frontend/tests/task_schedule_fixture.json").read_text(encoding="utf-8")
    )
    records = []
    for index, record in enumerate(fixture["gantt"]["records"]):
        records.append(
            dict(
                record,
                taskId=str(index + 1),
                dependencyId="1" if index == 1 else "",
                checked=False,
                selected=index == 1,
                parentPreviewUrl="",
                processColor=record.get("statusColor", ""),
                groupColor=record.get("statusColor", ""),
                groupCollapsed=False,
            )
        )
    fixture["gantt"]["records"] = records
    fixture["milestones"] = [
        dict(
            code="M1",
            description="Delivery",
            dueDate="2026-10-12",
            isNew=False,
            dirty=False,
            saving=False,
            error="",
            completion=50,
            taskCount=4,
            completedCount=2,
            overdueCount=1,
            planStartDate="2026-10-02",
            processSummary="model · publish",
            plannedHours=32,
        )
    ]
    fixture["schedule"] = dict(
        start="2026-10-02",
        duration=6,
        progress=35,
        dates=True,
        progressField="progress",
        move=False,
    )
    return fixture


def capture(app, qml, case, original):
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    application = FakeApplication()
    controller = TasksController(application)
    controller._progress_column = lambda: "progress"
    controller.open_workspace()
    payload = data()
    if case["screen"] == "empty":
        payload["gantt"]["records"] = []
        payload["gantt"]["rangeStart"] = ""
    if case["screen"] in ("milestone-draft", "milestone-error"):
        payload["milestones"][0]["dirty"] = True
        if case["screen"] == "milestone-error":
            payload["milestones"][0]["error"] = "Milestone operation failed"
    if case["screen"] == "milestone-empty":
        payload["milestones"] = []
    controller._gantt = payload["gantt"]
    controller.gantt_model.replace(payload["gantt"]["records"])
    controller.calendar_model.replace(payload["calendar"])
    controller.advancedChanged.emit()
    milestone_application = MilestoneApplication()
    milestones = MilestoneController(milestone_application)
    milestones._start_worker = lambda *args: None
    milestones._records = payload["milestones"]
    milestones._loaded_project_code = milestones.projectCode
    milestones._originals = {row["code"]: dict(row) for row in payload["milestones"]}
    milestones.model.replace(payload["milestones"])
    locale = Locale(case["language"])
    config = TaskConfigurationProbe()
    for name, value in dict(
        qml_icon_bindings(TH, app),
        tasksController=controller,
        taskGanttModel=controller.gantt_model,
        taskCalendarModel=controller.calendar_model,
        milestoneController=milestones,
        milestoneModel=milestones.model,
        localizationController=locale,
        configurationController=config,
        appController=config,
    ).items():
        engine.rootContext().setContextProperty(name, value)
    translator = (
        CatalogTranslator(TH / "thlib/ui/translations/ru.json")
        if case["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
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
    editor = case["screen"] == "editor" and not original
    filename = (
        "features/tasks/TaskScheduleDialog.qml"
        if editor
        else "MilestoneManagerView.qml"
        if case["screen"].startswith("milestone")
        else "TaskCalendarView.qml"
        if case["screen"] in ("calendar", "agenda")
        else "TaskGanttView.qml"
    )
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / filename)))
    window = QQuickWindow()
    window.resize(
        case["width"] + (40 if editor else 0), case["height"] + (200 if editor else 0)
    )
    window.setColor(theme.property("background"))
    properties = dict(theme=theme, width=case["width"], height=case["height"])
    if editor:
        properties = dict(
            theme=theme,
            width=case["width"] + 40,
            controller=controller,
            parent=window.contentItem(),
        )
    view = component.createWithInitialProperties(properties)
    assert view, [error.toString() for error in component.errors()]
    if editor:
        view.setProperty("record", payload["gantt"]["records"][0])
        expression = QQmlExpression(
            QQmlEngine.contextForObject(view), view, "showRecord(record)"
        )
        expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
    else:
        view.setParentItem(window.contentItem())
    window.show()
    try:
        for _ in range(5):
            frame(window)
        if case["screen"] == "agenda" and not original:
            click(window, controls(window)["calendarAgenda"])
        if case["screen"] == "hover":
            QTest.mouseMove(window, QPoint(480, 130))
            for _ in range(2):
                frame(window)
        if original and case["screen"].startswith("milestone"):
            # The pinned original references a missing Theme.controlRadius twice.
            # Preserve that evidence; current production must have no warnings.
            assert (
                all(
                    "MilestoneManagerView.qml:"
                    + line
                    + ": Unable to assign [undefined] to double"
                    in warning
                    for warning, line in zip(warnings, ["358:21", "370:29"])
                )
                and len(warnings) <= 2
            ), warnings
        else:
            assert not warnings, "\n".join(warnings)
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
        measured = snapshot(window, check_icons=not original)
        image = window.grabWindow()
        if editor:
            content = view.property("contentItem")
            bounds = content.mapRectToScene(
                QRectF(0, 0, content.width(), content.height())
            )
            assert (
                abs(bounds.width() - case["width"]) < 0.1
                and abs(bounds.height() - case["height"]) < 0.1
            ), bounds
            for group in ("boxes", "interiors"):
                for box in measured[group].values():
                    box["x"] -= bounds.x()
                    box["y"] -= bounds.y()
            ratio = image.devicePixelRatio()
            image = image.copy(
                round(bounds.x() * ratio),
                round(bounds.y() * ratio),
                round(bounds.width() * ratio),
                round(bounds.height() * ratio),
            )
        assert image.save(str(OUT / name))
        # Browser props are an exact projection of this same owner fixture.
        return dict(
            fixture=dict(case, model=payload),
            original=original,
            image=name,
            warnings=warnings,
            **measured,
        )
    finally:
        window.close()
        if not editor:
            view.setParentItem(None)
        view.deleteLater()
        window.deleteLater()
        controller.shutdown()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if translator:
            app.removeTranslator(translator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    archived = ROOT / ".tmp/b10/original"
    assert (archived / "thlib/ui/qml/TaskGanttView.qml").is_file(), (
        "Extract the pinned Git archive first"
    )
    with zipfile.ZipFile(ROOT / ".tmp/b10/original-handler.zip") as reference:
        assert reference.comment.decode("ascii") == REFERENCE, (
            "Wrong original Git archive"
        )
        for name in reference.namelist():
            if name.startswith("thlib/ui/qml/") and not name.endswith("/"):
                assert (archived / name).read_bytes() == reference.read(name), (
                    "Modified original: " + name
                )
    names = [
        path.relative_to(TH).as_posix() for path in (TH / "thlib/ui/qml").rglob("*.qml")
    ] + [
        "thlib/ui/tasks.py",
        "thlib/ui/task_data.py",
        "thlib/ui/task_workspace/store.py",
        "thlib/ui/milestones.py",
        "thlib/ui/translations/ru.json",
        "tests/test_frame_schedule.py",
    ]
    shared, native = source_hashes(ROOT, TH, names)
    drivers = {
        path.relative_to(ROOT).as_posix(): digest(path)
        for path in Path(__file__).parent.glob("*.py")
    }
    archive = digest(ROOT / ".tmp/b10/original-handler.zip")
    app = gui_test_application()
    rows = []
    previous = env_mode.current_path
    with tempfile.TemporaryDirectory(prefix="frame-schedule-") as isolated:
        env_mode.current_path = isolated
        try:
            for original in (True, False):
                for case in fixtures(args.smoke):
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
                        "original" if original else "native",
                        case["screen"],
                        case["style"],
                        case["language"],
                        case["width"],
                        flush=True,
                    )
        finally:
            env_mode.current_path = previous
    assert (shared, native) == source_hashes(ROOT, TH, names), (
        "Sources changed during captures"
    )
    assert all(digest(ROOT / name) == value for name, value in drivers.items()), (
        "Capture drivers changed"
    )
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                reference=REFERENCE,
                archiveSha256=archive,
                scale=float(os.environ.get("QT_SCALE_FACTOR", "1")),
                smoke=args.smoke,
                captures=rows,
                shared=shared,
                nativeSources=native,
                driverSources=drivers,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Schedule captures:", len(rows))


if __name__ == "__main__":
    main()
