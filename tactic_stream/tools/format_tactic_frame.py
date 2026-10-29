"""Keep Frame source readable: Prettier for JS/Vue, Qt for native QML."""

import argparse
import shutil
import subprocess
from pathlib import Path

import PySide6

ROOT = Path(__file__).resolve().parents[1]
FORMATTER = Path(PySide6.__file__).parent / "qmlformat.exe"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--handler-root",
        type=Path,
        help="Format native renderers in an explicitly selected Handler checkout",
    )
    args = parser.parse_args()
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    assert npm, "npm is required for the pinned development formatter"
    command = [
        npm,
        "exec",
        "--yes",
        "--cache",
        str(ROOT / ".npm-cache"),
        "--package",
        "prettier@3.6.2",
        "--",
        "prettier",
        "--check" if args.check else "--write",
        "--single-quote",
        "--trailing-comma",
        "none",
        "--tab-width",
        "4",
        "src/tactic_stream/shared_ui/**/*.mjs",
    ]
    native_javascript_command = command[:-1]
    native_javascript_command.remove("--check" if args.check else "--write")
    native_javascript_command += ["--parser", "babel"]
    queued = []
    queued.append(list(command))
    command[-1] = "src/tactic_stream/compatibility/table_action_runtime.js"
    queued.append(list(command))
    command[-1] = "frontend/src/frame/**/*.{vue,css,js}"
    command[command.index("--tab-width") + 1] = "2"
    queued.append(list(command))
    command[-1] = "frontend/src/features/administration/**/*.{vue,js}"
    queued.append(list(command))
    command[-1] = (
        "frontend/src/features/debug/{DebugLog.vue,UiPerformance.vue,ErrorDetails.vue,debugLog.css,uiPerformance.css}"
    )
    queued.append(list(command))
    command[-1] = "frontend/src/features/users/*.{vue,css}"
    queued.append(list(command))
    command[-1] = "tools/frame_support/*.{html,mjs}"
    queued.append(list(command))
    command[-1] = (
        "frontend/tests/{frame_support*,profile_support,debug_log,ui_performance}.mjs"
    )
    queued.append(list(command))
    command[-1] = "frontend/src/features/connection/SignIn.vue"
    queued.append(list(command))
    command[-1] = "tools/frame_foundation/*.{vue,js,html,mjs}"
    queued.append(list(command))
    command[-1] = "tools/frame_controls/*.{vue,js,html,mjs}"
    queued.append(list(command))
    command[-1] = (
        "frontend/src/features/workspace/{WorkspacePage.vue,DockWorkspace.vue,NavigationDrawer.vue,NavigationTree.vue,docks.js,QuickFilterOptions.vue,SearchQuickFilters.vue,TagCloud.vue,SearchHeader.vue,SearchFooter.vue,SearchLibrary.vue,SearchPresetBar.vue,SearchEditorPart.vue,SearchResultMenu.vue,ConditionCards.vue,ConditionValue.vue,QuickFilterEditor.vue,ProcessVisibility.vue,ResultBody.vue,ResultItem.vue,ResultPresentation.vue,BranchFilter.vue,MobileResults.vue,resultViews.js}"
    )
    queued.append(list(command))
    command[-1] = "frontend/tests/{frame_control*,frame_icons,frame_variable_rows*,table_nested,table_connections,icons}.mjs"
    queued.append(list(command))
    command[-1] = "frontend/tests/{administration,frame_admin_state,frame_types}.mjs"
    queued.append(list(command))
    for pattern in [
        "frontend/tests/item_composition.mjs",
        "frontend/src/features/knowledge/*.{vue,js}",
        "frontend/src/features/collaboration/*.vue",
        "frontend/src/features/documentation/*.vue",
        "frontend/src/features/journal/*.vue",
        "frontend/src/features/objects/{TimeEntryPanel,WorkHourForm,WorkReportSurface}.vue",
        "frontend/tests/{frame_remaining*,knowledge}.mjs",
        "tools/frame_remaining/*.{vue,mjs,html}",
        "frontend/src/features/scripts/*.{vue,js,css}",
        "frontend/tests/{script_editor,script_shelf,frame_scripts_state}.mjs",
        "frontend/tests/frame_scripts.mjs",
        "tools/frame_scripts/*.{vue,mjs,html}",
        "frontend/src/features/configuration/*.{vue,js}",
        "frontend/src/features/projects/{ProjectCreation,ProjectTemplates,ProjectEditorSurface}.vue",
        "frontend/tests/frame_configuration*.mjs",
        "frontend/tests/{search_suggestions,search_library,process_visibility,frame_search_state,result_views,branch_filter,delivery_project}.mjs",
        "tools/frame_configuration/*.{vue,js,html,mjs}",
        "tools/frame_search/*.{vue,js,html,mjs}",
        "frontend/tests/frame_search*.mjs",
        "frontend/src/features/interface/{TableView,TableCell,NestedTable,NestedTableCell,TableInlineEditor,TableServiceCell,TableDocument,TableServiceDialogs,ConfiguredView,TaskCell,TaskCards,TaskSummaryCell,ValueFieldsCell,MessageTableCell,GroupedCompletionCell,CompletionCell}.vue",
        "tools/frame_table/*.{vue,html,mjs}",
        "tools/frame_tasks/*.{vue,html,mjs}",
        "tools/frame_schedule/*.{vue,html,mjs}",
        "frontend/src/features/tasks/{TaskGanttView,TaskCalendarView,TaskScheduleEditor,MilestonePanel,MilestoneRow,MilestoneContent}.vue",
        "frontend/tests/{frame_schedule*,gantt_calendar,gantt_scroll_stability}.mjs",
        "frontend/src/features/objects/{DescriptionEditor,DescriptionSurface,DescriptionValue,SnapshotToolbar,SnapshotSummary,SnapshotBrowser,ObjectOperations,ObjectFieldFrame,RecordForm,ObjectReport,ObjectReportSurface,ObjectSnapshotTree,ObjectAction,ObjectDeleteSurface,DuplicateSObject,ObjectDuplicateSurface,RelatedObjects,ObjectLinkSurface,ObjectLinkList,ObjectEditorSurface,ObjectFieldGrid,ObjectInspectorQuick,TaskInspectorHeader,TaskDetails,TaskField,WorkHoursSummary,RelatedTasks,NoteEntry,NoteBody,NoteDialogs,NotesPanel}.vue",
        "tools/frame_objects/*.{vue,html,mjs}",
        "frontend/src/features/tasks/{TaskEmptyState,TaskBulkBar,TaskCellDisplay,TaskColumns,TaskDetailValue,TaskHiddenDetails,TaskManager,TaskMobileCard,MobileTasks,TaskProcessItem,TaskProcessPanel,TaskProcessToolbar,TaskRowValue,TaskTableHeaderInput,TaskWorkspaceEditor,TaskWorkspaceFilters,TaskWorkspaceFooter,TaskWorkspaceOptions,TaskWorkspacePart,TaskWorkspaceRow,TaskWorkspaceScope,TaskWorkspaceSurfaceSwitcher,TaskWorkspaceTable,TaskWorkspaceToolbar}.vue",
        "frontend/tests/{frame_tasks,frame_tasks_state,task_manager,task_manager_context,task_process_panel,mobile_tasks,mobile_complete}.mjs",
        "frontend/src/features/objects/inspector.css",
        "frontend/src/features/workspace/links.js",
        "frontend/tests/{frame_objects*,description,snapshot_browser,object_report,record_create,object_links,object_batch,duplicate_sobject,mobile_objects,inspector_dock}.mjs",
        "frontend/tests/{frame_table*,handler_table,table_cells,table_append,columns_editor,table_definition_resize,table_script_*}.mjs",
        "frontend/src/features/interface/tableScript.js",
        "frontend/src/features/interface/{CustomLayoutView.vue,DashboardItems.vue,LayoutDocument.vue,ItemComposition.vue,customReport.js}",
        "frontend/tests/custom_urls.mjs",
        "frontend/tests/page_{canvas,data,reports,editor_browser,editor_parity}.mjs",
        "tools/frame_layout/PageHarness.vue",
        "frontend/tests/vfx_composition.mjs",
        "frontend/src/features/interface/TableDependencies.vue",
        "frontend/src/features/interface/TableParentPicker.vue",
        "frontend/tests/frame_parent_state.mjs",
        "frontend/tests/table_parent.mjs",
        "frontend/tests/table_publish.mjs",
        "frontend/src/controls/forms/AppFileInput.vue",
        "frontend/tests/table_dependencies.mjs",
        "frontend/tests/frame_dependencies_state.mjs",
        "tools/frame_messages/*.{vue,html,mjs,json}",
        "tools/frame_files/*.{vue,html,mjs,json}",
        "frontend/tests/frame_files*.mjs",
        "frontend/tests/{checkin,file-workspace-inspection}.mjs",
        "frontend/src/features/messages/*.{vue,js,css}",
        "frontend/src/features/activity/*.{vue,js,css}",
        "frontend/src/features/checkin/*.vue",
        "frontend/src/features/fileWorkspace/FileWorkspace{Inspection,Inspector,Tree,Log,Depots,Storage}.vue",
        "frontend/src/features/fileWorkspace/inspection/*.{vue,js}",
        "frontend/src/features/checkin/queue/*.{vue,js}",
        "frontend/src/frame/controls/display/*.vue",
        "frontend/tests/{frame_messages*,frame_communication_reference,messages*,notification*,activity*,mobile_activity_profile}.mjs",
        "frontend/src/features/help/**/*.{vue,js}",
        "tools/frame_help/*.{vue,js,html,mjs}",
        "frontend/tests/frame_{help*,window_lifecycle,dock_placement,dock_layout,dock_capture,dock_interaction,navigation*}.mjs",
    ]:
        command[-1] = pattern
        queued.append(list(command))
    for pattern in [
        "frontend/src/controls/{AttachmentCard,AppTextArea,StatusSelect}.vue",
        "src/tactic_stream/shared_ui/**/*.json",
        "tools/frame_menus/*.{vue,js,html}",
        "tools/frame_navigation/*.{vue,js,html}",
        "frontend/tests/frame_menus.mjs",
        "frontend/tests/frame_projects.mjs",
        "frontend/src/features/connection/ConnectionMenu.vue",
        "frontend/src/features/projects/{ProjectChooser,ProjectCard}.vue",
        "tools/frame_projects/*.{vue,js,html}",
    ]:
        command[-1] = pattern
        queued.append(list(command))
    controls = [
        "WorkspaceTabs.vue",
        "WorkspaceTabVisual.vue",
        "SectionTabVisual.vue",
        "ItemPreview.vue",
        "SectionTabRail.vue",
        "ActionRows.vue",
        "ActionRow.vue",
        "DockWorkspaceFooter.vue",
        "lists/VirtualCollection.vue",
        "DocumentPane.vue",
        "NavigationRow.vue",
        "AppButton.vue",
        "AppIcon.vue",
        "AppColorInput.vue",
        "AppCheckbox.vue",
        "AppDateField.vue",
        "AppMenu.vue",
        "AppMenuItem.vue",
        "AppSelect.vue",
        "AppEditableSelect.vue",
        "AppDialog.vue",
        "AppSplitter.vue",
        "AppTextArea.vue",
        "AppTextField.vue",
        "AppProgress.vue",
        "AppSegmentedButton.vue",
        "AppSlider.vue",
        "AppSearchField.vue",
        "AppTabButton.vue",
        "SettingRow.vue",
        "ResponsiveFlow.vue",
        "StatusSelect.vue",
        "CodeEditor.vue",
        "EmojiPicker.vue",
        "ripple.js",
        "AccentPresetPicker.vue",
        "BusyIndicator.vue",
        "ImagePicker.vue",
        "SummaryChip.vue",
        "UserIdentity.vue",
        "UserGroupSection.vue",
        "ProfileInfoRow.vue",
        "actions/*.vue",
        "display/*.vue",
        "forms/*.vue",
        "layout/*.vue",
        "lists/*.vue",
        "typography/*.js",
        "ColorPicker.vue",
        "IconPicker.vue",
        "UserComboBox.vue",
        "UserPicker.vue",
        "controlAppearance.js",
        "tooltip.js",
        "tooltip.css",
        "panelChrome.css",
        "dialog.css",
    ]
    command[-1:] = ["frontend/src/controls/" + name for name in controls]
    queued.append(list(command))
    command[-len(controls) :] = ["frontend/src/icons.js", "frontend/src/icons.css"]
    queued.append(list(command))
    # One npm/node start per option set instead of one per pattern (~0.8 s each).
    batches = {}
    for queued_command in queued:
        size = queued_command.index("--tab-width") + 2
        batches.setdefault(tuple(queued_command[:size]), []).extend(queued_command[size:])
    for prefix, patterns in batches.items():
        chunk = []
        for pattern in list(dict.fromkeys(patterns)) + [None]:
            # npm.cmd runs through cmd.exe, whose command line is limited to 8191 chars.
            if chunk and (pattern is None or len(" ".join([*prefix, *chunk, pattern])) > 7000):
                subprocess.run([*prefix, *chunk], cwd=ROOT, check=True)
                chunk = []
            if pattern is not None:
                chunk.append(pattern)
    changed = []
    files = []
    if args.handler_root:
        files += sorted(
            (args.handler_root / "thlib/ui/qml/tactic_frame").rglob("*.qml")
        )
        files += [
            path
            for path in sorted((args.handler_root / "thlib/ui/qml").glob("*.qml"))
            if "tactic_frame" in path.read_text(encoding="utf-8")
        ]
        files += [
            path
            for path in sorted(
                (args.handler_root / "thlib/ui/qml/controls").rglob("*.qml")
            )
            if "tactic_frame" in path.read_text(encoding="utf-8")
        ]
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/administration").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/support").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/configuration").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/search").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/table").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/objects").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/tasks").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/messages").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/activity").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/files").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/scripts").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/tools").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/knowledge").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/workhours").rglob("*.qml")
        )
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/collaboration").rglob("*.qml")
        )
        files += [args.handler_root / "tests/fixtures/FrameRemainingHarness.qml"]
        files += [args.handler_root / "side_tools/frame_tool/Main.qml"]
        files += [args.handler_root / "thlib/ui/qml/controls/DocumentPane.qml"]
        files += sorted((args.handler_root / "thlib/ui/qml/shell").rglob("*.qml"))
        files += [args.handler_root / "tests/fixtures/FrameControlsHarness.qml"]
        files += [args.handler_root / "tests/fixtures/DockWorkspaceHarness.qml"]
        files += sorted(
            (args.handler_root / "tests/fixtures/frame_controls").glob("*.qml")
        )
        files += [
            args.handler_root / "thlib/ui/qml/TacticSearchField.qml",
            args.handler_root / "thlib/ui/qml/SObjectFieldEditor.qml",
            args.handler_root / "thlib/ui/qml/controls/SearchField.qml",
        ]
        files += [
            args.handler_root / "thlib/ui/qml/controls/PreviewNavigationButton.qml"
        ]
        files += [args.handler_root / "thlib/ui/qml/controls/feedback/ProgressBar.qml"]
        files += [
            args.handler_root / "thlib/ui/qml/controls" / (name + ".qml")
            for name in (
                "PopupAction",
                "DisclosureButton",
                "AccentPresetPicker",
                "ItemPreview",
            )
        ]
        files = list(dict.fromkeys(files))
    for path in files:
        result = subprocess.run(
            [str(FORMATTER), "--newline", "unix", str(path)],
            capture_output=True,
            check=True,
        )
        formatted = result.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        assert formatted.strip(), path
        if formatted != path.read_bytes():
            changed.append(str(path))
            if not args.check:
                path.write_bytes(formatted)
    if args.handler_root:
        example = args.handler_root / "side_tools/frame_tool/selection.ui.mjs"
        result = subprocess.run(
            native_javascript_command,
            cwd=ROOT,
            input=example.read_text(encoding="utf-8"),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )
        if result.stdout.encode("utf-8") != example.read_bytes():
            changed.append(str(example))
            if not args.check:
                example.write_text(result.stdout, encoding="utf-8", newline="\n")
        for path in sorted(
            (args.handler_root / "thlib/ui/qml/features/files").rglob("*.js")
        ):
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines(keepends=True)
            header = ""
            while lines and (
                lines[0].startswith((".pragma ", ".import ")) or not lines[0].strip()
            ):
                header += lines.pop(0)
            result = subprocess.run(
                native_javascript_command,
                cwd=ROOT,
                input="".join(lines),
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            formatted = (header.rstrip() + "\n\n" + result.stdout).encode("utf-8")
            if formatted != path.read_bytes():
                changed.append(str(path))
                if not args.check:
                    path.write_bytes(formatted)
    if args.check and changed:
        raise SystemExit("Unformatted Tactic Frame modules:\n" + "\n".join(changed))
    if files:
        print(
            f"{'Checked' if args.check else 'Formatted'} {len(files)} native renderers; {len(changed)} changed"
        )


if __name__ == "__main__":
    main()
