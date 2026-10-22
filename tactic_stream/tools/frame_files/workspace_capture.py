"""Capture the real Workspace presenters on disposable native project records."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]
import test_file_workspace_layout as layout
from PySide6.QtCore import QPoint, QObject
from PySide6.QtTest import QTest
from native_capture import snapshot
from tests.profile_ui_responsiveness import frame
from thlib.ui.localization import CatalogTranslator


def capture(app, qml, case, original, output):
    previous = layout.QML
    layout.QML = qml
    layout.FileWorkspaceLayoutTest.app = app
    fixture = layout.FileWorkspaceLayoutTest("runTest")
    translator = (
        CatalogTranslator(Path("D:/grav/Tactic Stream/TH/thlib/ui/translations/ru.json"))
        if case["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
    fixture.setUp()
    view = None
    try:
        fixture.view.setVisible(False)
        fixture.theme.setProperty("styleName", case["style"])
        fixture.theme.setProperty("dark", case["dark"])
        for name in (
            "fadeAnimationsEnabled",
            "hoverAnimationsEnabled",
            "clickAnimationsEnabled",
            "popupAnimationsEnabled",
        ):
            fixture.theme.setProperty(name, False)
        fixture.engine.setUiLanguage(case["language"])
        fixture.resize(case["width"], case["height"])
        state = fixture.controller._data
        screen = case["screen"]
        model = {}
        if screen.startswith("workspace-inspector"):
            path = "assets/Робот — robot.ma"
            change = fixture.call(
                "create_change", workspace="work", description="Reviewed model"
            )
            blob = fixture.upload(
                change["code"], b"// Maya ASCII\n// Asset: Hero Robot\n"
            )
            fixture.call(
                "edit",
                change=change["code"],
                edit_revision=0,
                chunk="capture",
                operations=[{"path": path, "blob": blob}],
            )
            fixture.call("submit", change=change["code"])
            info = fixture.call(
                "file_info", stream="main", path=path, workspace="work", preview=True
            )
            preview = info["preview"]
            tab = (
                "preview"
                if screen.endswith("preview")
                else "checkout"
                if screen.endswith("checkout")
                else "details"
            )
            model = {
                "info": info,
                "preview": preview,
                "tab": tab,
                "history": False,
                "busy": False,
                "error": "",
            }
            view = fixture.create(
                "FileWorkspaceInspector.qml",
                {
                    "theme": fixture.theme,
                    "info": info,
                    "preview": preview,
                    "currentTab": tab,
                },
            )
        elif screen.startswith("workspace-depots"):
            rows = fixture.call("depots")["items"]
            state.update(
                catalog_source="depots",
                catalog_rows=rows,
                catalog_detail=rows[0],
                administrator=True,
                catalog_capabilities={"repositories": ["main", "archive"]},
            )
            if screen.endswith("edit"):
                draft = {
                    "creating": False,
                    "code": rows[0]["code"],
                    "title": "Main depot",
                    "repository": "main",
                }
                state.update(depot_draft=draft, depot_original=dict(draft))
            else:
                state.update(depot_draft={}, depot_original={})
            fixture.controller.stateChanged.emit()
            model = {
                "rows": rows,
                "selected": rows[0],
                "draft": state["depot_draft"] or None,
                "repositories": ["main", "archive"],
                "administrator": True,
                "busy": False,
                "after": "",
            }
            view = fixture.create(
                "FileWorkspaceDepots.qml",
                {"theme": fixture.theme, "controller": fixture.controller},
            )
        elif screen == "workspace-storage":
            status = fixture.call("storage_status")
            draft = {
                "revision": status["policy_revision"],
                "policy": status["policy_values"],
            }
            state.update(
                storage_info=status,
                storage_draft=draft,
                storage_original=status["policy_values"],
                catalog_capabilities={"files_service_configured": False},
            )
            fixture.controller.stateChanged.emit()
            model = {
                "status": status,
                "draft": draft,
                "busy": False,
                "indexing": False,
                "filesService": False,
            }
            view = fixture.create(
                "FileWorkspaceStorage.qml",
                {"theme": fixture.theme, "controller": fixture.controller},
            )
        elif case.get("nativeOnly"):
            change = fixture.call(
                "create_change", workspace="work", description="Reviewed model"
            )
            blob = fixture.upload(change["code"], b"// Reviewed model\n")
            fixture.call(
                "edit",
                change=change["code"],
                edit_revision=0,
                chunk="capture",
                operations=[{"path": "assets/robot.ma", "blob": blob}],
            )
            change = fixture.call("status", change=change["code"])
            state.update(
                change=change,
                changes=[change],
                workspace="work",
                stream="main",
                root=fixture.temp.name,
            )
            state["review"] = fixture.call(
                "change_preview",
                change=change["code"],
                edit_revision=change["edit_revision"],
                operation="submit",
            )
            fixture.controller.stateChanged.emit()
            if screen == "workspace-main":
                view = fixture.view
                view.setVisible(True)
            elif screen == "workspace-graph":
                fixture.call(
                    "create_stream",
                    code="dev",
                    depot="main",
                    parent="main",
                    title="Development",
                )
                state["graph_nodes"] = fixture.call("streams")["items"]
                fixture.controller.stateChanged.emit()
                view = fixture.create(
                    "FileWorkspaceStreamGraph.qml",
                    {"theme": fixture.theme, "controller": fixture.controller},
                )
            elif screen == "workspace-mappings":
                import json

                view = fixture.create(
                    "FileWorkspaceMappings.qml",
                    {
                        "theme": fixture.theme,
                        "primaryStream": "main",
                        "value": json.dumps(
                            [
                                {
                                    "stream": "main",
                                    "prefix": "assets",
                                    "local": "assets",
                                    "writable": True,
                                }
                            ]
                        ),
                    },
                )
            elif screen == "workspace-log":
                fixture.controller._log(
                    "info", "Reviewed model uploaded", "assets/robot.ma"
                )
                view = fixture.create(
                    "FileWorkspaceLog.qml",
                    {"theme": fixture.theme, "controller": fixture.controller},
                )
            else:
                names = {
                    "workspace-submit": "workspaceSubmitDialog",
                    "workspace-revert": "workspaceRevertDialog",
                    "workspace-revision": "workspaceGetRevisionDialog",
                    "workspace-shelf": "workspaceShelfDialog",
                    "workspace-target": "workspaceTargetDialog",
                    "workspace-review": "workspaceReviewDialog",
                    "workspace-comparison": "workspaceComparisonDialog",
                }
                if screen == "workspace-submit":
                    state["submit_review"] = dict(
                        change=change["code"],
                        shelves=fixture.call("submit_shelves", change=change["code"]),
                        tasks=fixture.call("submit_tasks", change=change["code"]),
                        shelf_files={},
                        saved="",
                    )
                if screen == "workspace-shelf":
                    fixture.call(
                        "shelve",
                        change=change["code"],
                        edit_revision=change["edit_revision"],
                        request_id="capture-shelf",
                    )
                    state["shelves"] = fixture.call(
                        "submit_shelves", change=change["code"]
                    )["items"]
                fixture.controller.stateChanged.emit()
                dialog = fixture.view.findChild(QObject, names[screen])
                assert dialog is not None, names[screen]
                dialog.open()
                view = fixture.view
                QTest.qWait(60)
        else:
            raise AssertionError(screen)
        view.setParentItem(fixture.window.contentItem())
        view.setWidth(case["width"])
        view.setHeight(case["height"])
        QTest.mouseMove(fixture.window, QPoint(case["width"] - 1, case["height"] - 1))
        for _ in range(3):
            frame(fixture.window)
        assert not fixture.warnings, "\n".join(fixture.warnings)
        measured = snapshot(fixture.window, check_icons=not original)
        name = (
            "-".join(
                [
                    screen,
                    "original" if original else "native",
                    case["style"],
                    "dark" if case["dark"] else "light",
                    case["language"],
                    str(case["width"]),
                ]
            )
            + ".png"
        )
        assert fixture.window.grabWindow().save(str(output / name))
        return dict(
            fixture=dict(case, model={"workspace": model}),
            original=original,
            image=name,
            indicatorPaint={},
            editableParts={},
            **measured,
        )
    finally:
        if view is not None and view is not fixture.view:
            view.deleteLater()
        fixture.tearDown()
        fixture.doCleanups()
        if translator:
            app.removeTranslator(translator)
        layout.QML = previous
