"""Render the current Handler Task Manager using its isolated QML test fixture."""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path(os.environ.get("TACTIC_HANDLER_ROOT", "D:/grav/Tactic Stream/TH"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(HANDLER))

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.test_task_section_retention_qml import TaskSectionRetentionQmlTests, FakeTask, FakeTarget, QML, frame
from thlib.ui.icon_font import qml_icon_bindings


def main():
    output = ROOT / ".screenshots/handler-current"
    output.mkdir(parents=True, exist_ok=True)
    TaskSectionRetentionQmlTests.setUpClass()
    fixture = TaskSectionRetentionQmlTests()
    window = view = None
    try:
        fixture.setUp()
        for font in ("segoeui.ttf", "segoeuib.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
        bindings = qml_icon_bindings(HANDLER, fixture.engine)
        for name, value in bindings.items():
            fixture.engine.rootContext().setContextProperty(name, value)
        task = FakeTask(code="TASK_B", search_code="ASSET_B")
        target = FakeTarget([task], code="ASSET_B", title="Asset B")
        fixture.application.dock_model.show_panel("tasks")
        section = fixture._section("tasks-reference", target, task, fixture.application.dock_model.capture_layout())
        fixture.application._sessions = {section.entry_key: section}
        fixture.application.activate_section(section.entry_key)
        fixture.tasks.sync_presentation()
        records = [dict(record) for record in fixture.tasks.table_model._records]
        assert records, "Handler fixture must provide a real projected task row"
        component = QQmlComponent(fixture.engine, QUrl.fromLocalFile(str(QML / "TasksWorkspaceView.qml")))
        view = component.createWithInitialProperties({"theme": fixture.theme, "embedded": True})
        assert view is not None, [error.toString() for error in component.errors()]
        window = QQuickWindow()
        view.setParentItem(window.contentItem())
        window.show()
        geometry = {}
        fixture.tasks.advanced_model.replace([])
        fixture.tasks.table_model.replace([])
        fixture.tasks.advancedChanged.emit()
        for width in (1280, 1232, 320, 272):
            window.resize(width, 740)
            view.setSize(window.size())
            for _ in range(4):
                frame(window)
            QTest.qWait(450)
            picture = window.grabWindow()
            assert not picture.isNull() and picture.save(str(output / f"tasks-workspace-{width}.png"))
            geometry[str(width)] = {}
            for name in ("taskWorkspaceSearchField", "taskWorkspaceQuickFilterButton", "taskBrowserViewSwitcher", "taskCalendarButton"):
                item = fixture._find_item(view, name)
                if item:
                    geometry[str(width)][name] = {"width": item.width(), "height": item.height(), "visible": item.isVisible()}
        fixture.tasks.advanced_model.replace(records)
        fixture.tasks.table_model.replace(records)
        fixture.tasks.advancedChanged.emit()
        window.resize(1232, 740)
        view.setSize(window.size())
        for _ in range(4):
            frame(window)
        QTest.qWait(450)
        assert window.grabWindow().save(str(output / "tasks-workspace-populated.png"))
        (output / "tasks-workspace-geometry.json").write_text(json.dumps(geometry, indent=2), encoding="utf-8")
        fixture.tasks.set_view_mode('gantt')
        for _ in range(4): frame(window)
        QTest.qWait(450)
        assert window.grabWindow().save(str(output / 'tasks-gantt.png'))
        fixture.tasks.set_view_mode('list')
        view.setParentItem(None)
        view.deleteLater()
        component = QQmlComponent(fixture.engine, QUrl.fromLocalFile(str(QML / "TaskBrowserTable.qml")))
        view = component.createWithInitialProperties({"theme": fixture.theme})
        assert view is not None, [error.toString() for error in component.errors()]
        view.setParentItem(window.contentItem())
        for expanded in (False, True):
            view.setProperty("expandedTaskDetails", fixture.engine.toScriptValue({records[0]['taskCode']: expanded}))
            for width in (1232, 272):
                window.resize(width, 740)
                view.setSize(window.size())
                for _ in range(4):
                    frame(window)
                QTest.qWait(450)
                assert window.grabWindow().save(str(output / f"task-table-{'expanded' if expanded else 'rows'}-{width}.png"))
        view.setParentItem(None)
        view.deleteLater()
        fixture.engine.rootContext().setContextProperty("taskProcessModel", fixture.tasks.process_model)
        fixture.tasks._workspace_surface = "quick"
        fixture.tasks._rebuild_process_model()
        fixture.tasks.stateChanged.emit()
        component = QQmlComponent(fixture.engine, QUrl.fromLocalFile(str(QML / "TaskProcessPanel.qml")))
        view = component.createWithInitialProperties({"theme": fixture.theme})
        assert view is not None, [error.toString() for error in component.errors()]
        view.setParentItem(window.contentItem())
        for mode in ("cards", "compact"):
            fixture.tasks.set_quick_view_mode(mode)
            for width in (1232, 272):
                window.resize(width, 740)
                view.setSize(window.size())
                for _ in range(4):
                    frame(window)
                QTest.qWait(450)
                assert window.grabWindow().save(str(output / f"task-process-{mode}-{width}.png"))
        view.setParentItem(None)
        view.deleteLater()
        fixture.tasks._ensure_calendar_model()
        component = QQmlComponent(fixture.engine,QUrl.fromLocalFile(str(QML/'TaskCalendarView.qml')))
        view = component.createWithInitialProperties({'theme':fixture.theme})
        assert view is not None,[error.toString() for error in component.errors()]
        view.setParentItem(window.contentItem()); window.resize(1232,740); view.setSize(window.size())
        for _ in range(4): frame(window)
        QTest.qWait(450)
        assert window.grabWindow().save(str(output/'tasks-calendar.png'))
        print(json.dumps(geometry))
    finally:
        if window:
            window.close()
        if view:
            view.setParentItem(None)
            view.deleteLater()
        fixture.doCleanups()


if __name__ == "__main__":
    main()
