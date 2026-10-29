"""Run the focused Frame platform gate in both independent products.

This composes existing drivers; full Administration/original-reference suites
remain separate release checks. Every child, including browser descendants, is
terminated on interruption or timeout.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
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


def run(name, command, directory, environment, timeout=120):
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
            status = process.wait(timeout=timeout)
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
        ROOT / 'src/tactic_stream/compatibility/table_action_runtime.js',
        ROOT / 'src/pyasm/common/js/client_api.js',
        ROOT.parent / 'cg/config_custom_script.spt',
        ROOT.parent / 'cg/config_widget_config.spt',
        handler / 'tests/test_table_scripts.py',
        handler / 'tests/test_table_service_workflows.py',
        handler / 'tests/test_table_nested.py',
        handler / 'tests/test_table_snapshot_gallery.py',
        handler / 'tests/fixtures/table_snapshot_gallery.json',
        handler / 'tests/test_table_append.py',
        handler / 'tests/test_table_checkout.py',
        handler / 'tests/test_table_connections.py',
        handler / 'tests/test_table_dependencies.py',
        handler / 'tests/test_table_parent_group.py',
        handler / 'thlib/ui/table/parent_group.py',
        handler / 'thlib/ui/workspace_models/results_organization.py',
        handler / 'tests/test_frame_variable_rows.py',
        handler / 'thlib/repository_download.py',
        handler / 'thlib/tactic_classes.py',
        handler / 'thlib/side/client/tactic_client_lib/tactic_server_stub.py',
        ROOT / 'frontend/tests/table_script_runtime.mjs',
        ROOT / 'frontend/tests/table_script_worker.mjs',
        ROOT / 'tests/fixtures/table_widget_aliases.json',
        ROOT / 'tests/fixtures/frame_table_values.json',
        ROOT / 'tests/fixtures/frame_table_nested.json',
        ROOT / 'tests/fixtures/frame_table_dependencies.json',
        ROOT / 'tests/fixtures/frame_table_parent.json',
        ROOT / 'tests/test_table_parent_group.py',
        ROOT / 'tests/test_table_publish.py',
        ROOT / 'frontend/tests/table_publish.mjs',
        handler / 'tests/test_sobject_editor.py',
        handler / 'thlib/tactic_widgets.py',
        handler / 'tests/test_upload_multipart.py',
        handler / 'thlib/side/client/tactic_client_lib/common/upload_multipart.py',
        ROOT / 'frontend/tests/table_parent.mjs',
        ROOT / 'frontend/tests/table_dependencies.mjs',
        ROOT / 'tests/test_table_dependencies.py',
        ROOT / 'src/pyasm/widget/dependency_wdg.py',
        ROOT / 'src/pyasm/widget/file_wdg.py',
        *sorted((ROOT / 'src/tactic/ui/table').glob('*.py')),
        *[ROOT / path for path in (
            'tests/test_table_stage_one.py', 'tests/test_table_services.py',
            'tests/test_table_drop_links.py', 'src/pyasm/widget/parallel_status.py',
            'tests/test_table_nested.py', 'tests/test_table_snapshot_gallery.py',
            'tests/fixtures/frame_table_gallery.json', 'frontend/tests/table_snapshot_gallery.mjs',
            'tests/test_table_time.py',
            'tests/test_table_file_actions.py',
            'src/pyasm/widget/gantt_wdg.py', 'src/pyasm/widget/timecard_wdg.py',
            'src/pyasm/widget/my_tactic_summary_wdg.py',
            'src/pyasm/widget/table_element_wdg.py',
            'src/tactic/ui/input/process_group_select_wdg.py',
            'src/tactic/ui/panel/security_manager_wdg.py',
            'src/tactic/ui/widget/misc_input_wdg.py',
            'src/tactic/ui/widget/file_browser_wdg.py',
            'src/tactic/ui/widget/upload_wdg.py',
            'src/tactic/command/notification_cmd.py',
        )],
    ]
    checks += [
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
            "frame_dependencies_state.mjs",
            "frame_parent_state.mjs",
            "frame_variable_rows_state.mjs",
            "frame_variable_rows.mjs",
            "table_nested.mjs",
            "table_connections.mjs",
            "handler_table.mjs",
            "table_cells.mjs",
            "table_append.mjs",
            "columns_editor.mjs",
            "search_library.mjs",
            "search_suggestions.mjs",
            "process_visibility.mjs",
            "result_disclosure.mjs",
            "branch_filter.mjs",
            "profile_activity.mjs",
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
            "frame_schedule.mjs",
            "frame_schedule_state.mjs",
            "frame_messages_state.mjs",
            "frame_communication_reference.mjs",
            "notifications_layout.mjs",
            "frame_messages.mjs",
            "messages_ui.mjs",
            "messages.mjs",
            "notifications.mjs",
            "activity_feed.mjs",
            "activity_paging.mjs",
            "notification_history.mjs",
            "notification_stack.mjs",
            "frame_files.mjs",
            "frame_files_state.mjs",
            "frame_files_queue.mjs",
            "frame_files_object_checkin.mjs",
            "frame_files_snapshot_checkout.mjs",
            "checkin.mjs",
            "file-workspace-inspection.mjs",
            "gantt_calendar.mjs",
            "gantt_scroll_stability.mjs",
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
        ROOT / "tests/test_table_embedded_widgets.py",
        ROOT / "src/pyasm/search/search.py",
        ROOT / "src/pyasm/biz/schema.py",
        ROOT / "src/pyasm/search/sobject_log.py",
        ROOT / "src/tactic/ui/table/nested_scope.py",
        ROOT / "src/tactic_stream/server/activity_query.py",
        ROOT / "tests/test_vfx_relationships.py",
        ROOT / "src/pyasm/widget/discussion_wdg.py",
        ROOT / "src/pyasm/widget/task_wdg.py",
        ROOT / "src/tactic/ui/widget/discussion_wdg.py",
        ROOT / "src/tactic/ui/table/task_element_wdg.py",
        ROOT / "src/tactic/ui/app/message_wdg.py",
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
    checks += [
        path
        for path in (ROOT / "tools/frame_schedule").iterdir()
        if path.is_file() and path.suffix in (".vue", ".mjs", ".py", ".html")
    ]
    checks += [
        handler / "tests" / (name + ".py")
        for name in (
            "test_frame_schedule",
            "test_task_gantt_scroll_qml",
            "test_task_gantt_schedule",
            "test_milestones",
        )
    ]
    checks += [
        path
        for path in (ROOT / "tools/frame_messages").iterdir()
        if path.is_file() and path.suffix in (".vue", ".mjs", ".py", ".html", ".json")
    ]
    checks += [
        handler / "tests" / name
        for name in (
            "test_frame_messages.py",
            "frame_messages_fixture.py",
            "fixtures/frame_messages.json",
            "test_notes_qml.py",
            "test_communication_feed.py",
            "test_activity_feed_qml.py",
            "test_activity_feed_loading.py",
            "test_notifications_qml.py",
            "test_emoji.py",
            "test_message_bubble_rendering.py",
            "test_topbar_activity.py",
        )
    ]
    checks += [
        ROOT / "src/tactic/ui/table/task_schedule.py",
        ROOT / "tests/test_task_schedule.py",
    ]
    checks += [
        ROOT / "frontend/tests" / name
        for name in (
            "frame_scripts_state.mjs",
            "frame_scripts.mjs",
            "script_editor.mjs",
            "script_shelf.mjs",
        )
    ]
    checks += [
        handler / "tests" / name
        for name in (
            "frame_scripts_fixture.py",
            "test_frame_script_tools.py",
            "test_script_editor.py",
            "test_script_shelf.py",
            "test_script_shelf_qml.py",
            "test_script_triggers.py",
            "test_handler_server_controller.py",
            "test_maya_connector.py",
        )
    ]
    checks += [
        path
        for path in (handler / "side_tools/frame_tool").iterdir()
        if path.suffix in (".py", ".qml", ".mjs", ".md")
    ]
    checks += list((handler / "side_tools/batch_scheduler").glob("*.py"))
    checks += [
        path
        for path in (ROOT / "tools/frame_files").iterdir()
        if path.is_file() and path.suffix in (".vue", ".mjs", ".py", ".html", ".json")
    ]
    checks += [
        handler / "tests" / name
        for name in (
            "test_frame_queue.py",
            "test_frame_sync.py",
            "test_frame_screenshot.py",
            "test_frame_repository_prompts.py",
            "test_commit_queue.py",
            "test_drop_plate.py",
            "test_ingest_files.py",
            "test_repository_sync.py",
            "test_repository_sync_editor.py",
            "test_repository_sync_scope.py",
            "test_repository_download_errors.py",
            "test_screenshot_controller.py",
            "test_matching_templates_layout.py",
            "test_item_checkin_dialogs.py",
            "test_frame_ingest.py",
            "test_frame_drop_plate.py",
            "test_commit_queue_layout.py",
            "test_theme_controls.py",
            "frame_files_fixture.py",
            "fixtures/frame_files.json",
        )
    ]
    checks += [
        ROOT / "tests" / name
        for name in (
            "test_file_workspace_layout.py",
            "test_handler_file_workspace_ui.py",
            "test_file_workspace_drag_ui.py",
            "test_file_workspace_ui.py",
            "test_native_file_integration.py",
        )
    ]
    checks += [
        ROOT / "frontend/tests" / name
        for name in (
            "frame_remaining.mjs",
            "frame_remaining_workflows.mjs",
            "frame_remaining_capture.mjs",
        )
    ]
    checks += [
        handler / "tests" / name
        for name in (
            "frame_remaining_fixture.py",
            "fixtures/FrameRemainingHarness.qml",
            "test_frame_remaining.py",
            "test_knowledge_base.py",
            "test_work_hours.py",
        )
    ]
    checks += [
        path
        for path in (ROOT / "tools/frame_remaining").iterdir()
        if path.is_file() and path.suffix in (".py", ".vue", ".mjs", ".html", ".json")
    ]
    checks += [
        ROOT / "src/tactic_stream/server/messages.py",
        ROOT / "tests/test_messages.py",
        ROOT / "tests/test_triggers.py",
        ROOT / "tests/test_workflow_triggers_notifications.py",
        ROOT / "src/pyasm/command/trigger.py",
        ROOT / "src/pyasm/command/subprocess_trigger.py",
        ROOT / "src/pyasm/command/email_handler.py",
        ROOT / "src/pyasm/command/email_trigger.py",
        ROOT / "src/tactic/command/pipeline_task_trigger.py",
        ROOT / "src/tactic/core/filter_data.py",
        ROOT / "src/tactic/core/notification_filters.py",
    ]
    for index, path in enumerate(checks):
        result[f"check/{index}/{path.name}"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    parser.add_argument(
        "--only", help="Regex of stage names for an inner-loop run; never counts as the gate"
    )
    parser.add_argument("--list", action="store_true", help="Print stage names and exit")
    parser.add_argument(
        "--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2),
        help="Parallel stages; 1 restores the old serial run"
    )
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
    # Partial runs must not overwrite the full-gate evidence consumed by release reports.
    path = OUTPUT / ("partial.json" if args.only or args.list else "gate.json")
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
        (
            "messaging-state",
            ["node", "frontend/tests/frame_messages_state.mjs"],
            ROOT,
            {},
        ),
        ("notification-state", ["node", "frontend/tests/notifications.mjs"], ROOT, {}),
        ("files-state", ["node", "frontend/tests/frame_files_state.mjs"], ROOT, {}),
        ("scripts-state", ["node", "frontend/tests/frame_scripts_state.mjs"], ROOT, {}),
        ("remaining-state", ["node", "frontend/tests/frame_remaining.mjs"], ROOT, {}),
        (
            "remaining-production-workflows",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_transport.Transport.test_knowledge_base_in_chromium",
                "test_transport.Transport.test_api_documentation_and_console",
                "test_transport.Transport.test_snapshot_append_in_chromium",
                "test_messages",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "remaining-browser-input",
            ["node", "frontend/tests/frame_remaining_workflows.mjs"],
            ROOT,
            {},
        ),
        *[
            (
                "native-remaining-" + name,
                python + ["-m", "unittest", "-q", "tests." + module],
                handler,
                {"QT_QUICK_CONTROLS_STYLE": "Basic"},
            )
            for name, module in (
                ("knowledge", "test_knowledge_base"),
                ("work-hours", "test_work_hours"),
                ("input", "test_frame_remaining"),
            )
        ],
        (
            "remaining-inventory",
            python
            + ["tools/frame_foundation/inventory.py", "--handler-root", str(handler)],
            ROOT,
            {},
        ),
        (
            "remaining-coverage",
            python + ["tools/frame_remaining/coverage.py"],
            ROOT,
            {},
        ),
        (
            "scripts-server",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_script_features",
                "tests.test_script_editor",
                "tests.test_script_shelf",
                "tests.test_triggers",
                "tests.test_workflow_triggers_notifications",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        *[
            (
                "native-scripts-" + name,
                python + ["-m", "unittest", "-q", "tests." + module],
                handler,
                {"QT_QUICK_CONTROLS_STYLE": "Basic"},
            )
            for name, module in (
                ("editor-owners", "test_script_editor"),
                ("shelf-owners", "test_script_shelf"),
                ("shelf-input", "test_script_shelf_qml"),
                ("triggers", "test_script_triggers"),
                ("tools-input", "test_frame_script_tools"),
                ("dcc-owners", "test_maya_connector"),
                ("server-owners", "test_handler_server_controller"),
            )
        ],
        (
            "native-script-editor-input",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_tasks_controller.TasksQmlTests.test_script_editor_is_compact_and_output_collapses_at_minimum_size",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
        (
            "native-batch-existing",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "side_tools.batch_scheduler.test_scheduler_classes",
            ],
            handler,
            {},
        ),
        (
            "browser-script-editor",
            python + ["tools/result_browser.py", "script_editor.mjs"],
            ROOT,
            {},
        ),
        (
            "browser-script-shelf",
            python + ["tools/result_browser.py", "script_shelf.mjs"],
            ROOT,
            {},
        ),
        (
            "native-files-owners",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_commit_queue",
                "tests.test_drop_plate",
                "tests.test_ingest_files",
                "tests.test_repository_sync",
                "tests.test_repository_sync_editor",
                "tests.test_repository_sync_scope",
                "tests.test_repository_download_errors",
                "tests.test_screenshot_controller",
                "tests.test_matching_templates_layout",
                "tests.test_commit_queue_layout",
                "tests.test_item_checkin_dialogs",
                "tests.test_frame_ingest",
                "tests.test_frame_drop_plate",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
        (
            "browser-file-queue-input",
            ["node", "frontend/tests/frame_files_queue.mjs"],
            ROOT,
            {},
        ),
        (
            "browser-object-checkin-input",
            ["node", "frontend/tests/frame_files_object_checkin.mjs"],
            ROOT,
            {},
        ),
        (
            "browser-snapshot-checkout-input",
            ["node", "frontend/tests/frame_files_snapshot_checkout.mjs"],
            ROOT,
            {},
        ),
        (
            "native-files-input",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_frame_queue",
                "tests.test_commit_queue_layout",
                "tests.test_frame_sync",
                "tests.test_frame_screenshot",
                "tests.test_frame_repository_prompts",
                "tests.test_item_checkin_dialogs",
                "tests.test_theme_controls.ThemeControlTests.test_material_ripple_has_no_idle_effect_or_animation_graph",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
        (
            "native-file-workspace-layout",
            python + ["-m", "unittest", "-q", "test_file_workspace_layout"],
            ROOT,
            {
                "PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src"),
                "QT_QUICK_CONTROLS_STYLE": "Basic",
            },
        ),
        (
            "native-file-workspace-journey",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_handler_file_workspace_ui.HandlerFileWorkspaceUiTest.test_native_qml_upload_submit_have_history_and_small_layout",
                "test_handler_file_workspace_ui.HandlerFileWorkspaceUiTest.test_pointer_range_context_menu_and_file_move_against_native_api",
            ],
            ROOT,
            {
                "PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src"),
                "QT_QUICK_CONTROLS_STYLE": "Basic",
            },
        ),
        (
            "browser-file-workspace-journey",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_file_workspace_ui.FileWorkspaceUiTest.test_stream_interface_in_chromium",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "browser-checkin-journey",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "test_transport.Transport.test_drop_plate_commit_queue_in_chromium",
            ],
            ROOT,
            {"PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src")},
        ),
        (
            "native-sync-preset-server",
            python + ["-m", "unittest", "-q", "test_native_file_integration"],
            ROOT,
            {
                "PYTHONPATH": str(ROOT / "tests") + os.pathsep + str(ROOT / "src"),
                "QT_QUICK_CONTROLS_STYLE": "Basic",
            },
        ),
        (
            "browser-messaging-lifecycle",
            ["node", "frontend/tests/messages_ui.mjs"],
            ROOT,
            {},
        ),
        (
            "native-communication",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_frame_messages",
                "tests.test_notes_qml",
                "tests.test_emoji",
                "tests.test_activity_feed_qml",
                "tests.test_activity_feed_loading",
                "tests.test_notifications_qml",
                "tests.test_message_bubble_rendering",
                "tests.test_communication_feed",
                "tests.test_topbar_activity",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
        ("search-state", ["node", "frontend/tests/frame_search_state.mjs"], ROOT, {}),
        ("table-state", ["node", "frontend/tests/frame_table_state.mjs"], ROOT, {}),
        ("dependencies-state", ["node", "frontend/tests/frame_dependencies_state.mjs"], ROOT, {}),
        ("parent-state", ["node", "frontend/tests/frame_parent_state.mjs"], ROOT, {}),
        ("tasks-state", ["node", "frontend/tests/frame_tasks_state.mjs"], ROOT, {}),
        (
            "schedule-state",
            ["node", "frontend/tests/frame_schedule_state.mjs"],
            ROOT,
            {},
        ),
        (
            "browser-production-schedule",
            ["node", "frontend/tests/gantt_calendar.mjs"],
            ROOT,
            {},
        ),
        (
            "native-production-schedule",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_frame_schedule.FrameScheduleTests",
                "tests.test_task_gantt_schedule",
                "tests.test_task_gantt_scroll_qml.GanttScrollTests",
                "tests.test_milestones.MilestoneControllerTests",
                "tests.test_tasks_controller.TasksQmlTests.test_gantt_edge_grips_and_progress_drag_at_extremes",
            ],
            handler,
            {"QT_QUICK_CONTROLS_STYLE": "Basic"},
        ),
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
        ("table-script-runtime", ["node", "frontend/tests/table_script_runtime.mjs"], ROOT, {}),
        ("table-script-worker", ["node", "frontend/tests/table_script_worker.mjs"], ROOT, {}),
        ("variable-rows-state", ["node", "frontend/tests/frame_variable_rows_state.mjs"], ROOT, {}),
        ("browser-variable-rows", ["node", "frontend/tests/frame_variable_rows.mjs"], ROOT, {}),
        ("browser-nested-table", ["node", "frontend/tests/table_nested.mjs"], ROOT, {}),
        ("browser-search-filter-menu", ["node", "frontend/tests/search_result_menu.mjs"], ROOT, {}),
        ("browser-table-header-color", ["node", "frontend/tests/table_header_color.mjs"], ROOT, {}),
        ("native-table-header-color", python + ["-m", "unittest", "-q", "tests.test_table_header_color"], handler, {}),
        ("browser-card-image-contrast", ["node", "frontend/tests/card_image_contrast.mjs"], ROOT, {}),
        ("native-card-image-contrast", python + ["-m", "unittest", "-q", "tests.test_card_image_contrast"], handler, {}),
        ("browser-snapshot-gallery", ["node", "frontend/tests/table_snapshot_gallery.mjs"], ROOT, {}),
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
                "tests.test_table_scripts",
                "tests.test_table_service_workflows",
                "tests.test_upload_multipart",
                "tests.test_table_nested",
                "tests.test_table_snapshot_gallery",
                "tests.test_custom_layout",
                "tests.test_sidebar_navigation_targets",
                "tests.test_table_append",
                "tests.test_table_checkout",
                "tests.test_table_connections",
                "tests.test_table_dependencies",
                "tests.test_table_parent_group",
                "tests.test_frame_variable_rows",
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
                "test_table_embedded_widgets",
                "test_table_services",
                "test_table_drop_links",
                "test_table_stage_one",
                "test_table_nested",
                "test_table_snapshot_gallery",
                "test_table_time",
                "test_table_file_actions",
                "test_table_connections",
                "test_table_summary",
                "test_table_dependencies",
                "test_table_parent_group",
                "test_table_publish",
                "test_vfx_standard_widgets",
                "test_vfx_composition",
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
                "test_transport.Transport.test_handler_full_checkin_cells_match_stream_for_tasks_and_notes",
                "test_transport.Transport.test_handler_connection_fallback_and_removal_through_xmlrpc",
                "test_transport.Transport.test_handler_object_summary_and_project_scope_through_xmlrpc",
                "test_transport.Transport.test_handler_dependencies_through_xmlrpc",
                "test_transport.Transport.test_handler_parent_group_through_xmlrpc",
                "test_transport.Transport.test_handler_publish_fallback_through_xmlrpc",
                "test_transport.Transport.test_handler_configured_publish_actions_through_xmlrpc",
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
                ("browser-connection-cells", "test_table_connections_in_chromium"),
                ("browser-dependencies", "test_table_dependencies_in_chromium"),
                ("browser-parent-group", "test_table_parent_group_in_chromium"),
                ("browser-publish", "test_table_publish_in_chromium"),
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
            "browser-result-disclosure",
            ["node", "frontend/tests/result_disclosure.mjs"],
            ROOT,
            {},
        ),
        ("branch-filter", ["node", "frontend/tests/branch_filter.mjs"], ROOT, {}),
        (
            "browser-profile-activity",
            ["node", "frontend/tests/profile_activity.mjs"],
            ROOT,
            {},
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
    if args.list:
        print("\n".join(name for name, *_ in steps))
        return
    if args.only:
        steps = [step for step in steps if re.search(args.only, step[0])]
        assert steps, "No stages match --only"
        report["only"] = args.only
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
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
            def stage(step):
                name, command, directory, extra = step
                # Each stage gets its own settings/TMP so parallel Qt/browser runs cannot share state.
                own = Path(settings) / name
                temp = ROOT / ".tmp/frame-tests" / name
                own.mkdir(parents=True, exist_ok=True)
                temp.mkdir(parents=True, exist_ok=True)
                env = dict(
                    environment,
                    LOCALAPPDATA=str(own),
                    APPDATA=str(own),
                    XDG_CONFIG_HOME=str(own),
                    XDG_CACHE_HOME=str(own),
                    TMP=str(temp),
                    TEMP=str(temp),
                )
                try:
                    # shortcut: fixed 3x timeout under load, tune if slow stages time out
                    return run(name, command, directory, dict(env, **extra),
                               120 if args.jobs == 1 else 360)
                except Exception as error:
                    return error

            with ThreadPoolExecutor(max(1, args.jobs)) as pool:
                results = list(pool.map(stage, steps))
            if args.jobs > 1:
                # Timing-sensitive Qt/server stages can fail only under parallel load;
                # rerun those alone once and keep their names visible in the report.
                retry = [i for i, item in enumerate(results) if isinstance(item, Exception)]
                report["retried"] = [steps[i][0] for i in retry]
                for i in retry:
                    print("serial retry:", steps[i][0], flush=True)
                    results[i] = stage(steps[i])
            failures = [str(item) for item in results if isinstance(item, Exception)]
            report["steps"] = [item for item in results if isinstance(item, dict)]
            if failures:
                raise RuntimeError("\n".join(failures))
            assert report["sources"] == fingerprints(handler), (
                "UI source changed during the gate"
            )
            report["status"] = "partial" if args.only else "passed"
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.only:
        print(f"{len(steps)} selected stages passed; this is NOT the full gate.")
        return
    print("Frame platform gate passed; full release scenarios remain separate.")


if __name__ == "__main__":
    main()
