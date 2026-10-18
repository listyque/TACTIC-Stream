"""Run the focused Frame platform gate in both independent products.

This composes existing drivers; full Administration/original-reference suites
remain separate release checks. Every child, including browser descendants, is
terminated on interruption or timeout.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "tools/frame_foundation/output/platform"


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run(name, command, directory, environment):
    log = OUTPUT / (name + ".log")
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        try:
            status = process.wait(timeout=120)
        finally:
            stop(process)
    print(name, status, flush=True)
    if status:
        raise RuntimeError(f"{name} failed; see {log}")
    text = log.read_text(encoding="utf-8")
    count = re.search(r"Ran (\d+) tests?", text)
    return dict(
        name=name, status=status, log=log.name, tests=int(count[1]) if count else None
    )


def fingerprints(handler):
    roots = [
        ("stream", ROOT / "frontend/src"),
        ("shared", ROOT / "src/tactic_stream/shared_ui"),
        ("handler", handler / "thlib/ui"),
    ]
    result = {}
    for product, directory in roots:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and (
                path.suffix in (".qml", ".mjs", ".json", ".vue", ".js", ".css", ".py")
                or path.name == "qmldir"
            ):
                result[product + "/" + path.relative_to(directory).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
    checks = [
        ROOT / "frontend/tests" / name
        for name in (
            "frame_contract.mjs",
            "frame_renderer_contract.mjs",
            "frame_capture.mjs",
            "frame_resize.mjs",
            "frame_platform.mjs",
            "frame_controls_contract.mjs",
            "frame_controls.mjs",
            "frame_controls_input.mjs",
            "frame_control_variants.mjs",
            "frame_control_variants_input.mjs",
            "frame_control_paint.mjs",
            "frame_control_catalog.mjs",
            "icons.mjs",
            "frame_help_state.mjs",
            "frame_configuration_state.mjs",
            "frame_search_state.mjs",
            "frame_table_state.mjs",
            "handler_table.mjs",
            "table_cells.mjs",
            "columns_editor.mjs",
            "search_library.mjs",
            "search_suggestions.mjs",
            "process_visibility.mjs",
            "tag_cloud.mjs",
            "workspace_tabs.mjs",
            "frame_configuration.mjs",
            "frame_help.mjs",
            "frame_navigation.mjs",
            "frame_navigation_drawer.mjs",
            "frame_projects.mjs",
            "frame_menus.mjs",
            "frame_dock_placement.mjs",
            "frame_dock_layout.mjs",
            "frame_dock_interaction.mjs",
            "frame_window_lifecycle.mjs",
            "window_types.mjs",
            "shared_help.mjs",
            "frame_main_browser.mjs",
            "workspace_lifecycle.mjs",
            "workspace_session.mjs",
            "session_expiry.mjs",
            "workspace_complete.mjs",
            "mobile_complete.mjs",
        )
    ]
    checks += [
        ROOT / "frontend/tests" / name
        for name in (
            "frame_objects.mjs",
            "frame_objects_state.mjs",
            "frame_tasks.mjs",
            "frame_tasks_state.mjs",
            "mobile_tasks.mjs",
            "task_manager.mjs",
            "task_manager_context.mjs",
            "task_process_panel.mjs",
            "inspector_dock.mjs",
            "object_report.mjs",
            "object_links.mjs",
            "object_batch.mjs",
            "description.mjs",
            "snapshot_browser.mjs",
            "record_create.mjs",
            "mobile_objects.mjs",
            "duplicate_sobject.mjs",
        )
    ]
    checks += [
        handler / "tests" / ("test_" + name + ".py")
        for name in (
            "frame_objects",
            "sobject_info",
            "sobject_link",
            "sobject_editor",
            "sobject_duplicate",
            "sobject_delete",
        )
    ]
    checks += [
        ROOT / "src/tactic_stream/server" / name
        for name in (
            "object_report.py",
            "object_operations.py",
            "activity_feed.py",
            "result_items.py",
        )
    ]
    checks += [
        handler / "tests/test_frame_platform.py",
        handler / "tests/test_frame_controls.py",
        handler / "tests/test_control_variants.py",
        handler / "tests/fixtures/frame_controls/ControlVariantsHarness.qml",
        handler / "tests/fixtures/frame_controls/ControlExample.qml",
        handler / "tests/fixtures/FrameControlsHarness.qml",
        handler / "tests/test_user_combo_box.py",
        handler / "tests/test_frame_help.py",
        handler / "tests/test_frame_navigation.py",
        handler / "tests/test_frame_projects.py",
        handler / "tests/test_frame_sections.py",
        handler / "tests/test_section_tab_rail.py",
        handler / "tests/test_frame_dock_input.py",
        handler / "tests/test_frame_menus.py",
        handler / "tests/test_frame_table.py",
        handler / "tests/test_columns_table_view.py",
        handler / "thlib/tactic_query.py",
        handler / "thlib/tactic_table_widgets.py",
        ROOT / "tests/test_handler_table.py",
        ROOT / "tests/test_table_extended_values.py",
        ROOT / "tests/test_table_value_widgets.py",
        ROOT / "tests/test_table_inventory.py",
        ROOT / "tools/frame_table/inventory.py",
        ROOT / "tests/test_transport.py",
        ROOT / "src/tactic_stream/server/table_cells.py",
        ROOT / "src/tactic_stream/compatibility/business_upgrade.json",
        handler / "tests/test_frame_dock_layout.py",
        handler / "tests/fixtures/DockWorkspaceHarness.qml",
        handler / "tests/test_dock_resizing.py",
        handler / "tests/test_dock_layout_tree.py",
        handler / "tests/test_retained_ui.py",
        handler / "tests/test_qml_smoke_harness.py",
        ROOT / "tests/test_frame_inventory.py",
        ROOT / "tests/test_tactic_frame_sync.py",
        ROOT / "tools/frame_foundation/check_platform.py",
        ROOT / "tools/frame_foundation/inventory.py",
        ROOT / "tools/frame_foundation/inventory_web.mjs",
        ROOT / "tools/sync_tactic_frame.py",
        ROOT / "tools/check_frame_package.py",
        ROOT / "tools/format_tactic_frame.py",
        ROOT / "tools/frame_foundation/check_main.py",
        ROOT / "tools/frame_foundation/main_qml.py",
        ROOT / "tools/frame_workspace/report.py",
        ROOT / "tools/frame_projects/capture_qml.py",
        ROOT / "tools/frame_projects/report.py",
        ROOT / "tools/frame_navigation/check_workflows.py",
        ROOT / "tests/test_workbench.py",
        handler / "tests/test_workspace_layout_presets.py",
        handler / "tests/test_controller_scenarios.py",
        handler / "tests/test_login_configuration.py",
        handler / "tests/test_configuration.py",
        handler / "tests/test_configuration_appearance.py",
        handler / "tests/test_configuration_layout.py",
        handler / "tests/test_project_creation.py",
        handler / "tests/frame_configuration_fixture.py",
        handler / "tests/test_search_contract.py",
        *[
            handler / "tests" / (name + ".py")
            for name in (
                "test_project_tasks",
                "test_task_combo_activation_qml",
                "test_task_section_retention_qml",
            )
        ],
        *[
            handler / "tests" / (name + ".py")
            for name in (
                "test_workspace_result_item",
                "test_process_menu_latency",
                "test_advanced_search_suggestions",
                "test_search_text_qml",
                "test_process_filter_editor",
                "test_quick_filter_editor_qml",
                "test_quick_filter_popup_qml",
                "test_tag_cloud_qml",
                "test_search_pagination_qml",
            )
        ],
        ROOT / "tests/test_search_configuration.py",
        ROOT / "tests/test_cg_template.py",
        *[
            ROOT / "src/tactic_stream/server" / (name + ".py")
            for name in (
                "app",
                "search_configuration",
                "result_items",
            )
        ],
        ROOT / "pyproject.toml",
        handler / "thlib/version.json",
        ROOT / "src/tactic_stream/shared_ui/README.md",
        handler / "thlib/ui/qml/tactic_frame/README.md",
        ROOT / "tools/frame_foundation/PlatformHarness.vue",
        ROOT / "tools/frame_foundation/platform.entry.js",
        ROOT / "tools/frame_foundation/platform.html",
    ]
    checks += [
        path
        for path in (ROOT / "tools/frame_controls").iterdir()
        if path.is_file()
        and path.suffix in (".vue", ".js", ".html", ".py", ".json", ".mjs")
    ]
    checks += [
        path
        for directory in ("frame_menus", "frame_navigation", "frame_projects")
        for path in (ROOT / "tools" / directory).iterdir()
        if path.is_file() and path.suffix in (".vue", ".js", ".html", ".py")
    ]
    for index, path in enumerate(checks):
        result[f"check/{index}/{path.name}"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    args = parser.parse_args()
    handler = args.handler_root.resolve()
    assert (handler / "tests/test_frame_platform.py").is_file(), (
        "Handler platform tests are required"
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (ROOT / ".tmp/frame-tests").mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PLAYWRIGHT_BROWSERS_PATH=os.environ.get(
            "PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".browser-cache")
        ),
        QT_QPA_PLATFORM="offscreen",
        QT_QPA_FONTDIR=str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"),
        QT_QUICK_BACKEND="software",
        QSG_RENDER_LOOP="basic",
        TMP=str(ROOT / ".tmp/frame-tests"),
        TEMP=str(ROOT / ".tmp/frame-tests"),
    )
    python = [sys.executable, "-B", "-X", "utf8"]
    version = json.loads((handler / "thlib/version.json").read_text(encoding="utf-8"))
    stream_version = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    report = dict(
        status="running",
        steps=[],
        sources=fingerprints(handler),
        versions={
            "handler": ".".join(
                version[key] for key in ("major", "minor", "build", "revision")
            ),
            "stream": stream_version,
        },
    )
    path = OUTPUT / "gate.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    steps = [
        (
            "format",
            python
            + [
                "tools/format_tactic_frame.py",
                "--check",
                "--handler-root",
                str(handler),
            ],
            ROOT,
            {},
        ),
        (
            "sync",
            python
            + ["tools/sync_tactic_frame.py", "--handler-root", str(handler), "--check"],
            ROOT,
            {},
        ),
        ("contract", ["node", "frontend/tests/frame_contract.mjs"], ROOT, {}),
        (
            "icons-contract",
            ["node", "frontend/tests/icons.mjs", str(handler)],
            ROOT,
            {},
        ),
        (
            "controls-contract",
            ["node", "frontend/tests/frame_controls_contract.mjs"],
            ROOT,
            {},
        ),
        (
            "renderers",
            ["node", "frontend/tests/frame_renderer_contract.mjs", str(handler)],
            ROOT,
            {},
        ),
        ("resize", ["node", "frontend/tests/frame_resize.mjs"], ROOT, {}),
        ("help-state", ["node", "frontend/tests/frame_help_state.mjs"], ROOT, {}),
        (
            "configuration-state",
            ["node", "frontend/tests/frame_configuration_state.mjs"],
            ROOT,
            {},
        ),
        ("search-state", ["node", "frontend/tests/frame_search_state.mjs"], ROOT, {}),
        ("table-state", ["node", "frontend/tests/frame_table_state.mjs"], ROOT, {}),
        ("tasks-state", ["node", "frontend/tests/frame_tasks_state.mjs"], ROOT, {}),
        ("browser-task-phone", ["node", "frontend/tests/mobile_tasks.mjs"], ROOT, {}),
        ("objects-state", ["node", "frontend/tests/frame_objects_state.mjs"], ROOT, {}),
        (
            "native-task-owners",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_tasks_controller.TasksControllerTests",
                "tests.test_tasks_controller.TasksQmlTests.test_task_workspace_creates_with_a_real_record",
                "tests.test_tasks_controller.TasksQmlTests.test_empty_task_workspace_keeps_heavy_surfaces_unloaded",
                "tests.test_tasks_controller.TasksQmlTests.test_filled_action_button_natural_width_does_not_clip_label",
                "tests.test_tasks_controller.TasksQmlTests.test_filled_action_button_clips_localized_text_to_its_width",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
        *[
            (
                "native-tasks-" + name.removeprefix("test_"),
                python + ["-m", "unittest", "-q", "tests." + name],
                handler,
                {"QT_QUICK_CONTROLS_STYLE": "Basic"},
            )
            for name in (
                "test_project_tasks",
                "test_task_combo_activation_qml",
                "test_task_section_retention_qml",
            )
        ],
        (
            "native-objects",
            python
            + ["-m", "unittest", "-q"]
            + [
                "tests." + name
                for name in (
                    "test_frame_objects.FrameObjectsTests",
                    "test_sobject_editor",
                    "test_sobject_duplicate",
                    "test_sobject_link",
                    "test_sobject_info",
                    "test_sobject_delete",
                )
            ],
            handler,
            {},
        ),
        ("browser-inspector", ["node", "frontend/tests/inspector_dock.mjs"], ROOT, {}),
        (
            "object-mutations",
            python
            + ["-m", "unittest", "-q"]
            + [
                "test_transport.Transport." + name
                for name in (
                    "test_record_creation_in_chromium",
                    "test_object_batch_in_chromium",
                    "test_object_links_in_chromium",
                    "test_advanced_duplicate_wizard_in_chromium",
                )
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "object-report-files",
            python
            + ["-m", "unittest", "-q"]
            + [
                "test_transport.Transport." + name
                for name in (
                    "test_object_report_pages_and_acl",
                    "test_description_editor_in_chromium",
                    "test_snapshot_browser_in_chromium",
                    "test_mobile_objects_in_chromium",
                )
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        ("browser-table", ["node", "frontend/tests/handler_table.mjs"], ROOT, {}),
        (
            "native-table",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_columns_table_view",
                "tests.test_frame_table",
            ],
            handler,
            {},
        ),
        (
            "table-api",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_handler_table",
                "test_table_value_widgets",
                "test_table_extended_values",
                "test_table_inventory",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "table-transport",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_transport.Transport.test_handler_extended_table_values_through_xmlrpc",
                "test_transport.Transport.test_handler_table_metadata_values_through_xmlrpc",
                "test_transport.Transport.test_handler_native_table_layout_through_xmlrpc",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        *[
            (
                name,
                python + ["-m", "unittest", "-q", "test_transport.Transport." + case],
                ROOT,
                {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
            )
            for name, case in (
                ("browser-columns-editor", "test_columns_editor_in_chromium"),
                ("browser-native-cells", "test_native_table_cells_in_chromium"),
            )
        ],
        # Popup suites own Qt's process-wide style, window grabs and scene graph.
        *[
            (
                "native-search-" + name.removeprefix("test_"),
                python + ["-m", "unittest", "-q", "tests." + name],
                handler,
                {},
            )
            for name in (
                "test_workspace_result_item",
                "test_process_menu_latency",
                "test_advanced_search_suggestions",
                "test_search_text_qml",
                "test_process_filter_editor",
                "test_quick_filter_editor_qml",
                "test_quick_filter_popup_qml",
                "test_search_pagination_qml",
                "test_tag_cloud_qml",
            )
        ],
        (
            "search-api",
            python
            + ["-m", "unittest", "-q", "test_search_configuration", "test_cg_template"],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "browser-search-library",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_transport.Transport.test_search_library_in_chromium",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "native-configuration-projects",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_configuration",
                "tests.test_configuration_appearance",
                "tests.test_configuration_layout",
                "tests.test_project_creation",
            ],
            handler,
            {},
        ),
        (
            "dock-placement",
            ["node", "frontend/tests/frame_dock_placement.mjs"],
            ROOT,
            {},
        ),
        ("dock-layout", ["node", "frontend/tests/frame_dock_layout.mjs"], ROOT, {}),
        (
            "inventory-tests",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_frame_inventory",
                "tests.test_tactic_frame_sync",
            ],
            ROOT,
            {},
        ),
        # Each GUI fixture owns its process-wide Qt style and native popup grabs.
        *[
            (
                f"native-{scale}-{case.rsplit('.', 1)[-1]}",
                python + ["-m", "unittest", "-q", case],
                handler,
                {"QT_SCALE_FACTOR": scale},
            )
            for scale in ("1", "1.5", "2")
            for case in (
                "tests.test_frame_platform.FramePlatformTests",
                "tests.test_frame_controls.FrameControlsTests",
                "tests.test_user_combo_box.UserPickerTests",
                "tests.test_frame_help.FrameHelpTests",
                "tests.test_frame_navigation.FrameNavigationTests",
                "tests.test_frame_projects.FrameProjectsTests",
                "tests.test_frame_sections.FrameSectionInputTests",
                "tests.test_section_tab_rail.SectionTabRailQmlTests",
                "tests.test_frame_dock_input.FrameDockInputTests",
                "tests.test_frame_menus.FrameMenuTests",
                "tests.test_frame_dock_layout.FrameDockLayoutTests",
            )
        ],
        ("browser", ["node", "tests/frame_platform.mjs"], ROOT / "frontend", {}),
        (
            "browser-controls",
            ["node", "frontend/tests/frame_controls.mjs", "--input-only"],
            ROOT,
            {},
        ),
        *[
            (
                f"native-control-variants-{scale}",
                python
                + [
                    "-m",
                    "unittest",
                    "-q",
                    "tests.test_control_variants.ControlVariantsTests",
                ],
                handler,
                {"QT_SCALE_FACTOR": scale},
            )
            for scale in ("1", "1.5", "2")
        ],
        *[
            (
                f"browser-control-variants-{scale}",
                ["node", "frontend/tests/frame_control_variants.mjs", "--input"],
                ROOT,
                {"FRAME_CONTROL_SCALE": scale},
            )
            for scale in ("1", "1.5", "2")
        ],
        (
            "control-catalog",
            ["node", "frontend/tests/frame_control_catalog.mjs"],
            ROOT,
            {},
        ),
        (
            "control-atlas",
            python
            + ["tools/frame_controls/elements.py", "--handler-root", str(handler)],
            ROOT,
            {},
        ),
        (
            "control-atlas-input",
            ["node", "tools/frame_controls/check_elements.mjs"],
            ROOT,
            {},
        ),
        (
            "smoke",
            python + ["-m", "unittest", "-q", "tests.test_qml_smoke_harness"],
            handler,
            {},
        ),
        *[
            (name, ["node", "frontend/tests/" + script + ".mjs"], ROOT, {})
            for name, script in [
                ("help-input", "frame_help"),
                ("help-launchers", "shared_help"),
                ("navigation-input", "frame_navigation"),
                ("navigation-drawer", "frame_navigation_drawer"),
                ("projects-tabs", "frame_projects"),
                ("menus-input", "frame_menus"),
                ("dock-input", "frame_dock_interaction"),
                ("window-input", "frame_window_lifecycle"),
                ("window-kinds", "window_types"),
            ]
        ],
        (
            "dock-rollback",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_dock_resizing",
                "tests.test_dock_layout_tree",
            ],
            handler,
            {},
        ),
        (
            "dock-retention",
            python
            + ["-m", "unittest", "-q"]
            + [
                "tests.test_retained_ui.RetainedUiTests." + name
                for name in [
                    "test_search_tab_selection_visual_changes_without_late_motion",
                    "test_search_tab_width_changes_settle_synchronously",
                    "test_unsnapped_dock_title_drag_keeps_the_dock_in_its_layout",
                    "test_dock_layout_switch_keeps_delegate_and_loaded_content",
                    "test_stacked_search_dock_keeps_move_grip_at_fixed_position",
                    "test_dock_content_reflows_live_during_resize",
                    "test_shared_dock_resize_grip_starts_on_first_press",
                ]
            ],
            handler,
            {},
        ),
        (
            "native-workspace-lifecycle",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_controller_scenarios",
                "tests.test_login_configuration",
                "tests.test_search_contract",
                "tests.test_workspace_layout_presets",
            ],
            handler,
            {},
        ),
        (
            "workspace-session",
            python + ["tools/frame_navigation/check_workflows.py"],
            ROOT,
            {},
        ),
        (
            "workspace-complete",
            python
            + [
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_workbench.py",
                "-q",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        ("package", python + ["tools/check_frame_package.py"], ROOT, {}),
        (
            "inventory",
            python
            + ["tools/frame_foundation/inventory.py", "--handler-root", str(handler)],
            ROOT,
            {},
        ),
    ]
    try:
        with tempfile.TemporaryDirectory(
            prefix="frame-platform-", dir=ROOT / ".tmp"
        ) as settings:
            assert Path(settings).resolve().is_relative_to((ROOT / ".tmp").resolve())
            environment.update(
                LOCALAPPDATA=settings,
                APPDATA=settings,
                XDG_CONFIG_HOME=settings,
                XDG_CACHE_HOME=settings,
            )
            for name, command, directory, extra in steps:
                report["steps"].append(
                    run(name, command, directory, dict(environment, **extra))
                )
            assert report["sources"] == fingerprints(handler), (
                "UI source changed during the gate"
            )
            report["status"] = "passed"
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Frame platform gate passed; full release scenarios remain separate.")


if __name__ == "__main__":
    main()
