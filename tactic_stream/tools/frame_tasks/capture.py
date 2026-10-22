"""Fresh production task presenters against the pinned pre-B09 Handler UI."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = ROOT / os.environ.get("TASK_FRAME_OUTPUT", "tools/frame_tasks/output")
REFERENCE = "0297005238226e9bd9bd7461e729177ac365ade7"
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
from PySide6.QtCore import QUrl, QCoreApplication, QEvent, QPointF
from PySide6.QtQml import QQmlEngine, QQmlComponent, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from native_capture import snapshot, source_hashes, controls
from object_fixtures import Locale
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_tasks_controller import (
    FakeApplication,
    FakeTask,
    TaskConfigurationProbe,
    TasksQmlTests,
)
from thlib.environment import env_mode
from thlib.ui.tasks import TasksController
from thlib.ui.workspace_models.records import RecordListModel
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures(smoke):
    states = [
        ("table", 1280, 540),
        ("table", 520, 540),
        ("columns", 1600, 540),
        ("grouped", 1000, 540),
        ("expanded", 1000, 660),
        ("pending", 900, 540),
        ("bulk", 1000, 540),
        ("cards", 900, 420),
        ("compact", 520, 420),
        ("empty", 900, 540),
    ]
    variants = (
        [("md3", True, "en"), ("md3", True, "ru")]
        if smoke
        else [
            (style, dark, language)
            for style in ("md3", "material5", "fluent")
            for dark in (False, True)
            for language in ("en", "ru")
        ]
    )
    for style, dark, language in variants:
        for screen, width, height in states:
            yield dict(
                screen=screen,
                width=width,
                height=height,
                style=style,
                dark=dark,
                language=language,
            )


def export_model(controller, fixture):
    aliases = {
        "assignee": "assigned",
        "hours": "bid_duration",
        "milestone": "milestone_code",
    }
    records = controller.table_model._records
    tasks = []
    for record in records:
        if not record.get("taskCode"):
            continue
        login = record.get("assigned") or ""
        task = dict(
            key=record["taskCode"],
            __search_key__=record.get("taskKey")
            or "sthpw/task?code=" + record["taskCode"],
            title=record["parentTitle"],
            process=record["process"],
            context=record.get("context", ""),
            status=record.get("status", ""),
            assigned=record.get("assignedLabel") or "—",
            assignedLogin=login,
            assignedUser=dict(
                value=login,
                displayName=record.get("assignedLabel") or "",
                initials="".join(
                    word[0] for word in (record.get("assignedLabel") or "").split()[:2]
                ).upper(),
                avatarUrl="",
            ),
            supervisor=record.get("supervisorLabel") or "—",
            supervisorUser={},
            supervisorLogin=record.get("supervisor") or "",
            priority=record.get("priority") or "",
            priorityLabel=record.get("priorityLabel") or "No priority",
            priorityColor=record.get("priorityColor") or "",
            milestoneLabel=record.get("milestoneLabel") or "No milestone",
            milestone_code=record.get("milestoneCode") or "",
            notes=record.get("notes", 0),
            progress=record.get("progress", 0),
            bid_duration=record.get("plannedHours", 0),
            bid_start_date=record.get("start") or "",
            bid_end_date=record.get("end") or "",
            description=record.get("description") or "",
            parent={
                "__search_key__": record["parentKey"],
                "__preview__": {"image": ""},
            },
            __status__={
                "label": record.get("statusLabel") or record.get("status") or "",
                "color": record.get("statusColor") or "",
            },
            __process__={
                "label": record["processLabel"],
                "color": record["processColor"],
            },
            pending=record.get("dirty", False),
            deleting=False,
            __hours__={
                "approved": record.get("approvedHours", 0),
                "pending": record.get("pendingHours", 0),
            },
            __group_key__=record.get("groupKey") or "",
            __group_label__=record.get("groupLabel") or record.get("group") or "",
        )
        tasks.append(task)
    groups = []
    for task in tasks:
        group = next(
            (group for group in groups if group["key"] == task["__group_key__"]), None
        )
        if group is None:
            group = dict(
                key=task["__group_key__"],
                label=task["__group_label__"],
                color=next(
                    (
                        row.get("groupColor")
                        for row in records
                        if row.get("groupKey") == task["__group_key__"]
                    ),
                    "",
                ),
                tasks=[],
            )
            groups.append(group)
        group["tasks"].append(task)
    columns = [
        dict(row, key=aliases.get(row["key"], row["key"]))
        for row in controller.taskColumns
    ]
    scope = (
        "selected"
        if controller.advancedScope in ("object", "multiple")
        else controller.advancedScope
    )
    toolbar = dict(
        embedded=True,
        scope=scope,
        scopeLabel="SELECTED",
        scopeIcon="inventory-2",
        selectedIcon="inventory-2",
        searchTypeTitle=controller.searchTypeScopeName,
        searchTypeAvailable=controller.searchTypeScopeAvailable,
        personal=controller.personalScope,
        canCreate=controller.canCreateAdvancedTask,
        canRefresh=controller.advancedDirtyCount == 0,
        filtersActive=controller.advancedFiltersActive,
        sort=controller.sortMode,
        sortOptions=controller.sortOptions,
        group=controller.groupMode,
        groupOptions=controller.groupOptions,
        surface="workspace",
        text=controller.advancedFilters.get("text", ""),
    )
    editors = {}
    for record in records:
        if not record.get("taskCode"):
            continue
        code = record["taskCode"]
        values = {
            "status": record.get("status", ""),
            "assigned": record.get("assigned", ""),
            "supervisor": record.get("supervisor", ""),
            "bid_start_date": record.get("start", ""),
            "bid_end_date": record.get("end", ""),
            "bid_duration": record.get("plannedHours", 0),
            "progress": record.get("progress", 0),
            "description": record.get("description", ""),
            "priority": record.get("priority", ""),
            "milestone_code": record.get("milestoneCode", ""),
        }
        fields = [{"name": key, "editable": True} for key in values]
        catalog = {
            "priorityChoices": record.get("priorityChoices", []),
            "milestoneChoices": record.get("milestoneChoices", []),
            "bidDurationUnit": "hour",
        }
        editors[code] = dict(
            plans=[{"operation": "update"}],
            fields=fields,
            values=values,
            statusChoices=record.get("statusChoices", []),
            statuses=[row["value"] for row in record.get("statusChoices", [])],
            users=record.get("userChoices", []),
            catalog=catalog,
        )
    processes = []
    for record in controller.process_model._records:
        values = {
            "status": record.get("status", ""),
            "assigned": record.get("assigned", ""),
        }
        processes.append(
            dict(
                value=record["process"],
                label=record["label"],
                color=record["color"],
                choices=record.get("taskChoices", []),
                plan={
                    "task_key": record.get("currentTaskCode", ""),
                    "fields": [{"name": key, "editable": True} for key in values],
                },
                values=values,
                statuses=record.get("statusChoices", []),
                users=record.get("userChoices", []),
                notes=record.get("notes", 0),
                dirty=record.get("dirty", False),
            )
        )
    return dict(
        tasks=tasks,
        groups=groups,
        columns=columns,
        toolbar=toolbar,
        editors=editors,
        processes=processes,
        title=controller.targetTitle,
        checked=list(controller._advanced_checked),
        active=controller._selected_advanced_code,
        dirty=controller.advancedDirtyCount,
        processCount=controller.advancedProcessCount,
        scope=scope,
        footer={
            "loaded": controller.advancedLoadedCount,
            "total": controller.advancedTotalCount,
            "visible": controller.advancedVisibleCount,
            "filtered": controller.advancedFiltersActive,
            "processes": controller.advancedProcessCount,
            "checked": controller.advancedCheckedCount,
            "showModes": True,
            "view": "table",
        },
        processDirty=controller.dirtyProcessCount,
    )


def capture(app, qml, fixture, original):
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    application = FakeApplication()
    application.workspace_state._task_sobjects = (
        []
        if fixture["screen"] == "empty"
        else [
            FakeTask(
                code="TASK0001",
                description="Model geometry",
                bid_duration=4.5,
                bid_start_date="2026-08-03 09:00:00",
            ),
            FakeTask(
                code="TASK0002",
                context="model/alternate",
                status="Pending",
                assigned="",
                progress=10,
                description="Alternate branch",
                bid_duration=2.0,
            ),
            FakeTask(
                code="TASK0003",
                process="publish",
                context="publish",
                status="Pending",
                assigned="artist",
                progress=70,
                description="Publish review",
                bid_duration=1.0,
            ),
        ]
    )
    controller = TasksController(application)
    controller.open_workspace()
    if fixture["screen"] == "columns":
        for key in ["priority", "milestone", "supervisor"]:
            controller.set_task_column_visible(key, True)
    controller.set_group_mode("process" if fixture["screen"] == "grouped" else "none")
    if fixture["screen"] == "pending":
        controller.stage_advanced_value(
            "TASK0001", "description", "Pending geometry review"
        )
    if fixture["screen"] == "bulk":
        controller.toggle_advanced_checked("TASK0001")
        controller.toggle_advanced_checked("TASK0002")
    if fixture["screen"] in ("cards", "compact"):
        controller.set_quick_view_mode(fixture["screen"])
    users = RecordListModel(("login", "displayName", "initials", "avatarUrl"))
    users.replace(
        [dict(login="artist", displayName="artist", initials="A", avatarUrl="")]
    )
    locale = Locale(fixture["language"])
    configuration = TaskConfigurationProbe()
    for name, value in dict(
        qml_icon_bindings(TH, app),
        tasksController=controller,
        advancedTaskModel=controller.advanced_model,
        advancedTaskTableModel=controller.table_model,
        taskGanttModel=controller.gantt_model,
        taskProcessModel=controller.process_model,
        userListModel=users,
        localizationController=locale,
        configurationController=configuration,
        appController=configuration,
    ).items():
        engine.rootContext().setContextProperty(name, value)
    translator = (
        CatalogTranslator(TH / "thlib/ui/translations/ru.json")
        if fixture["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Theme.qml")))
    theme = theme_component.createWithInitialProperties(
        dict(
            dark=fixture["dark"],
            styleName=fixture["style"],
            fadeAnimationsEnabled=False,
            hoverAnimationsEnabled=False,
            clickAnimationsEnabled=False,
            popupAnimationsEnabled=False,
        )
    )
    assert theme, [error.toString() for error in theme_component.errors()]
    quick = fixture["screen"] in ("cards", "compact")
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(
            str(qml / ("TaskProcessPanel.qml" if quick else "TasksWorkspaceView.qml"))
        ),
    )
    view = component.createWithInitialProperties(
        dict(
            theme=theme,
            width=fixture["width"],
            height=fixture["height"],
            **({} if quick else {"embedded": True}),
        )
    )
    assert view, [error.toString() for error in component.errors()]
    window = QQuickWindow()
    window.resize(fixture["width"], fixture["height"])
    window.setColor(theme.property("background"))
    view.setParentItem(window.contentItem())
    window.show()
    try:
        for _ in range(8):
            frame(window)
        if fixture["screen"] == "expanded":
            table = TasksQmlTests.visual_find(view, "taskBrowserTable")
            assert table is not None
            expression = QQmlExpression(
                QQmlEngine.contextForObject(table),
                table,
                'toggleTaskDetails("TASK0001")',
            )
            expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            for _ in range(5):
                frame(window)
        assert not warnings, "\n".join(warnings)
        name = (
            "-".join(
                [
                    fixture["screen"],
                    "original" if original else "native",
                    fixture["style"],
                    "dark" if fixture["dark"] else "light",
                    fixture["language"],
                    str(fixture["width"]),
                ]
            )
            + ".png"
        )
        assert window.grabWindow().save(str(OUT / name))
        filled = {}
        create = TasksQmlTests.visual_find(view, "taskWorkspaceCreateButton")
        if create is not None:
            paint = next(
                child
                for child in create.childItems()
                if child.property("radius") is not None
                and child.property("color") is not None
            )
            point = paint.mapToScene(QPointF(0, 0))
            filled["taskWorkspaceCreateButton"] = {
                "x": point.x(),
                "y": point.y(),
                "width": paint.width(),
                "height": paint.height(),
                "radius": paint.property("radius"),
                "color": paint.property("color").name(),
            }
        arrow = TasksQmlTests.visual_find(view, "taskWorkspaceEmptyArrow")
        arrow_color = (
            arrow.property("strokeColor").name() if arrow is not None else None
        )
        measured = snapshot(window, check_icons=not original)
        frame_ids = set(measured["frameIds"])
        painted = controls(window)
        texts = {
            name: str(item.property("text"))
            for name, item in painted.items()
            if name in frame_ids
            and item.property("text") is not None
            and item.property("font") is not None
        }
        choices = {
            name: str(item.property("currentText"))
            for name, item in painted.items()
            if name in frame_ids and item.property("currentText") is not None
        }
        return dict(
            fixture=dict(fixture, model=export_model(controller, fixture)),
            original=original,
            image=name,
            filledActions=filled,
            arrowColor=arrow_color,
            texts=texts,
            choices=choices,
            **measured,
        )
    finally:
        window.close()
        view.setParentItem(None)
        view.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if translator:
            app.removeTranslator(translator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    archived = ROOT / ".tmp/b09/reference-029700523822"
    assert (archived / "thlib/ui/qml/TasksWorkspaceView.qml").is_file(), (
        "Create the pinned Git archive before capturing"
    )
    names = (
        ["thlib/ui/tasks.py", "thlib/ui/translations/ru.json"]
        + [
            path.relative_to(TH).as_posix()
            for path in (TH / "thlib/ui/qml").glob("Task*.qml")
        ]
        + [
            path.relative_to(TH).as_posix()
            for path in (TH / "thlib/ui/qml/features/tasks").glob("*.qml")
        ]
    )
    shared, native = source_hashes(ROOT, TH, names)
    drivers = {
        str(path.relative_to(ROOT).as_posix()): digest(path)
        for path in Path(__file__).parent.glob("*.py")
    }
    app = gui_test_application()
    rows = []
    previous = env_mode.current_path
    with tempfile.TemporaryDirectory(prefix="frame-tasks-") as isolated:
        env_mode.current_path = isolated
        try:
            for original in (True, False):
                for fixture in fixtures(args.smoke):
                    rows.append(
                        capture(
                            app,
                            (archived if original else TH) / "thlib/ui/qml",
                            fixture,
                            original,
                        )
                    )
                    print(
                        "Captured",
                        "original" if original else "native",
                        fixture["screen"],
                        fixture["style"],
                        fixture["language"],
                        flush=True,
                    )
        finally:
            env_mode.current_path = previous
    assert (shared, native) == source_hashes(ROOT, TH, names), (
        "Sources changed during task captures"
    )
    assert all(digest(ROOT / name) == value for name, value in drivers.items()), (
        "Capture drivers changed"
    )
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                reference=REFERENCE,
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
    print("Task production captures:", len(rows))


if __name__ == "__main__":
    main()
