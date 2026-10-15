"""Compare whole dock geometry with the archived Python tree and real Qt panels."""

import ast
import importlib.util
import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
OUT = Path(__file__).resolve().parent / "output"
REFERENCE = "fa3f594c5cd09ce565ea14acb533302e79c9308a"
os.environ.update(
    QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QSG_RENDER_LOOP="basic"
)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from native_capture import source_hashes
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from tests.dock_layout_fixture import three_column_layout
from tests.profile_ui_responsiveness import frame
from tests.qt_application import gui_test_application
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.workspace_models.docks import DockPanelModel
from thlib.ui.workspace_models.docks_tree import serialize_layout


def archived(name):
    return subprocess.check_output(
        ["git", "-C", str(TH), "show", REFERENCE + ":thlib/ui/workspace_models/" + name]
    ).decode("utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "original_tree.py"
    path.write_text(archived("docks_tree.py"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("dock_original", path)
    original = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = original
    spec.loader.exec_module(original)
    sizes_ast = ast.parse(archived("docks_resizing.py"))
    minimums = next(
        ast.literal_eval(node.value)
        for node in ast.walk(sizes_ast)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "pixel_sizes"
            for target in node.targets
        )
    )
    app = gui_test_application()
    base = serialize_layout(three_column_layout())
    # The archived dataclass has its own identity; deserialize before using it.
    tree = original.deserialize_layout(
        base,
        {
            "results",
            "tasks",
            "notes",
            "task_calendar",
            "timesheet",
            "work_reports",
            "cost_reports",
            "snapshot",
            "description",
        },
    )
    cases = [
        ("single", original.stack("results"), ["results"], []),
        (
            "three-columns",
            tree,
            ["results", "tasks", "notes", "task_calendar", "snapshot"],
            [],
        ),
        (
            "hidden-largest-tab",
            tree,
            ["results", "tasks", "task_calendar", "snapshot"],
            [],
        ),
        ("hidden-middle", tree, ["results", "notes"], []),
        ("floating-inspector", tree, ["results", "tasks", "notes"], ["notes"]),
        (
            "nested-vertical",
            original.insert_relative(tree, "tasks", "description", "bottom"),
            ["results", "tasks", "notes", "description"],
            [],
        ),
        (
            "queue-stack",
            original.tabify(tree, "results", "commit_queue"),
            ["results", "commit_queue", "tasks", "notes"],
            [],
        ),
        ("hidden-right", tree, ["results", "tasks"], []),
    ]
    captures, samples = [], []
    for label, tree, visible, floating in cases:
        for width, height in [(1800, 1000), (1100, 800), (760, 640)]:
            kinds = {panel.panel_id: panel.kind for panel in DockPanelModel._defaults()}
            available = set(visible) - set(floating)
            sizes = {
                id: tuple(
                    min(1, size / extent)
                    for size, extent in zip(
                        minimums.get(kinds[id], (320, 220)), (width, height)
                    )
                )
                for id in available
            }
            projected = original.clamp_layout_ratios(tree, available, sizes)
            expected = original.layout_rectangles(projected, available)
            rows = []
            for panel in DockPanelModel._defaults():
                value = {
                    "panel_id": panel.panel_id,
                    "kind": panel.kind,
                    "title": panel.title,
                    "visible": panel.panel_id in visible,
                    "closable": panel.closable,
                    "detached": False,
                    "dock_area": "floating" if panel.panel_id in floating else "docked",
                    "x": 0.15,
                    "y": 0.15,
                    "width": 0.6,
                    "height": 0.6,
                    "z": panel.z,
                }
                rows.append(value)
            configuration = {"layout": original.serialize_layout(tree), "panels": rows}
            sample = {
                "id": label + "-" + str(width),
                "width": width,
                "height": height,
                "configuration": configuration,
            }
            samples.append(sample)
            for archived_ui in (True, False):
                model = DockPanelModel({})
                assert model.apply_layout(configuration)
                model.ensure_minimum_sizes(width, height)
                for panel in model._panels:
                    if panel.panel_id in available:
                        wanted = expected[panel.panel_id]
                        actual = (panel.x, panel.y, panel.width, panel.height)
                        assert all(abs(a - b) < 1e-9 for a, b in zip(actual, wanted)), (
                            sample["id"],
                            panel.panel_id,
                            actual,
                            wanted,
                        )
                if archived_ui:
                    model._panels = [
                        replace(
                            panel,
                            x=expected[panel.panel_id][0],
                            y=expected[panel.panel_id][1],
                            width=expected[panel.panel_id][2],
                            height=expected[panel.panel_id][3],
                        )
                        if panel.panel_id in expected
                        else panel
                        for panel in model._panels
                    ]
                qml = (
                    ROOT / "tools/frame_foundation/reference/main/thlib/ui/qml"
                    if archived_ui
                    else TH / "thlib/ui/qml"
                )
                engine, warnings = QQmlEngine(), []
                engine.warnings.connect(
                    lambda errors, warnings=warnings: warnings.extend(
                        error.toString() for error in errors
                    )
                )
                for name, value in dict(
                    qml_icon_bindings(TH, app), dockModel=model
                ).items():
                    engine.rootContext().setContextProperty(name, value)
                component = QQmlComponent(engine)
                source = (
                    (TH / "tests/fixtures/DockWorkspaceHarness.qml")
                    .read_text(encoding="utf-8")
                    .replace("__QML_ROOT__", qml.as_uri())
                )
                component.setData(source.encode("utf-8"), QUrl())
                assert component.isReady(), [
                    error.toString() for error in component.errors()
                ]
                window = component.createWithInitialProperties(
                    {"width": width, "height": height}
                )
                assert window
                try:
                    frame(window)
                    geometry = {}
                    for item in SidebarEditorQmlTests.descendants(window.contentItem()):
                        name = item.objectName()
                        if name.startswith("dockPanel_") and item.isVisible():
                            geometry[name.removeprefix("dockPanel_")] = [
                                item.x(),
                                item.y(),
                                item.width(),
                                item.height(),
                            ]
                    assert geometry and not warnings, warnings
                    filename = (
                        ("original-" if archived_ui else "native-")
                        + sample["id"]
                        + ".png"
                    )
                    grab = window.contentItem().grabToImage()
                    for _ in range(10):
                        frame(window)
                        if not grab.image().isNull():
                            break
                    assert grab.saveToFile(str(OUT / filename))
                    captures.append(
                        {
                            "id": sample["id"],
                            "original": archived_ui,
                            "geometry": geometry,
                            "image": filename,
                        }
                    )
                finally:
                    window.close()
                    window.deleteLater()
                    engine.deleteLater()
                    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    # Includes Python↔Qt JS conversion and public model projection, not just JS execution.
    model = DockPanelModel({})
    assert model.apply_layout(samples[1]["configuration"])
    started = time.perf_counter()
    for _ in range(200):
        model.ensure_minimum_sizes(1100, 800)
    projection_ms = (time.perf_counter() - started) * 1000 / 200
    shared, native = source_hashes(
        ROOT,
        TH,
        [
            "thlib/ui/workspace_models/" + name
            for name in [
                "docks_tree.py",
                "docks_projection.py",
                "docks_resizing.py",
                "docks_placement.py",
            ]
        ]
        + [
            "thlib/ui/qml/shell/docks/DockPanel.qml",
            "tests/fixtures/DockWorkspaceHarness.qml",
        ],
    )
    (OUT / "native.json").write_text(
        json.dumps(
            {
                "captures": captures,
                "samples": samples,
                "sha256": shared,
                "nativeSources": native,
                "reference": REFERENCE,
                "projectionMs": projection_ms,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"{len(samples)} whole-layout original/native cases; public Qt projection {projection_ms:.3f} ms/update."
    )


if __name__ == "__main__":
    main()
