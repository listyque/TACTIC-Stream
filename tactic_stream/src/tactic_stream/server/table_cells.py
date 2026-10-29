"""Typed cells for the Vue table, using native TACTIC widget value methods."""

import json
from importlib.resources import files
from urllib.parse import urlsplit

from pyasm.biz import Project
from pyasm.common import SecurityException
from pyasm.search import Search, SearchKey, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.interface import _require_table_access
from pyasm.widget import ArrayTableElementWdg, ThumbWdg, WidgetConfigView, XmlWdg
from pyasm.widget.discussion_wdg import DiscussionWdg as LegacyDiscussionWdg
from pyasm.widget.task_wdg import SObjectTaskTableElement, TaskParentSpacingTableElement
from tactic.ui.app.message_wdg import MessageTableElementWdg
from pyasm.widget.statistic_wdg import TaskCompletionWdg as FormerTaskCompletionWdg
from pyasm.widget.table_element_wdg import CheckboxColWdg, SearchTypeElementWdg, WikiElementWdg
from tactic.ui.app.search_type_element_wdg import SearchTypeHasTableElementWdg
from tactic.ui.common import RawTableElementWdg, SimpleTableElementWdg
from tactic.ui.table import (
    CheckinButtonElementWdg,
    CheckoutButtonElementWdg,
    DeleteElementWdg,
    ExplorerElementWdg,
    ExplorerTableElementWdg,
    ExpressionElementWdg,
    ExpressionValueElementWdg,
    FormatElementWdg,
    JsonElementWdg,
    LinkElementWdg,
    MetadataElementWdg,
    SnapshotVersionElementWdg,
    SObjectDetailElementWdg,
    SObjectFilesElementWdg,
    TaskCompletionWdg,
    TaskElementWdg,
)
from tactic.ui.table.preference_wdg import PreferenceDescriptionWdg
from tactic.ui.table.project_wdg import ProjectWdg
from tactic.ui.table.related_element_wdg import RelatedElementWdg
from tactic.ui.table.snapshot_element_wdg import (
    SnapshotInfoWdg,
    SnapshotFileElementWdg,
    SnapshotLockedElementWdg,
)
from tactic.ui.table.statistic_wdg import (
    MilestoneCompletionWdg,
    TaskDaysDueElementWdg,
    TaskGroupCompletionWdg,
)
from tactic.ui.table.subcontext_wdg import SubContextElementWdg
from tactic.ui.table.table_element_wdg import RecipientElementWdg
from tactic.ui.table.task_element_wdg import TaskSummaryElementWdg
from tactic.ui.widget.discussion_wdg import DiscussionElementWdg, DiscussionWdg
from pyasm.widget.my_tactic_summary_wdg import MyTacticSummaryWdg
from pyasm.widget.table_element_wdg import UpdateWdg
from tactic.ui.input.process_group_select_wdg import LoginTableElementWdg
from tactic.ui.panel.security_manager_wdg import SecurityManagerButtonWdg
from tactic.ui.table.preference_wdg import PreferenceEditWdg
from tactic.ui.table.project_wdg import ProjectTemplateUpdateWdg
from tactic.ui.table.table_element_wdg import NotificationTriggerElementWdg
from tactic.ui.table.button_wdg import ButtonElementWdg
from pyasm.widget.parallel_status import ParallelStatusWdg, ParallelStatusEditWdg
from tactic.ui.table.subcontext_wdg import ProcessElementWdg
from tactic.ui.table.sobject_detail_wdg import SObjectTaskStatusElementWdg
from tactic.ui.table.task_element_wdg import WorkElementWdg
from tactic.ui.widget.misc_input_wdg import TaskStatusElementWdg
from tactic.ui.table.drop_element_wdg import DropElementWdg
from pyasm.widget.sobject_browser_wdg import SObjectConnectionElement
from pyasm.widget.dependency_wdg import DependencyLink
from tactic.ui.table.group_element_wdg import ParentGroupTableElementWdg, read_parent_cells
from pyasm.widget.table_element_wdg import PublishTableElement
from tactic.ui.table.table_element_wdg import GeneralPublishElementWdg
from tactic.ui.table.sobject_summary_wdg import SObjectSummaryElementWdg

from tactic.ui.table.custom_layout_element_wdg import CustomLayoutElementWdg
from tactic.ui.table.hidden_row_element_wdg import HiddenRowElementWdg, RowAddElementWdg
from pyasm.widget.table_element_wdg import HiddenRowToggleWdg, AuxDataWdg, FileAppendLinkTableElement

NESTED_WIDGETS = (HiddenRowElementWdg, RowAddElementWdg, HiddenRowToggleWdg)
from pyasm.widget.gantt_wdg import GanttWdg
from pyasm.widget.timecard_wdg import TimecardInfoTableElement, WeekTableElement
from tactic.ui.table.gantt_element_wdg import GanttElementWdg
from tactic.ui.table.work_hours_element_wdg import WorkHoursElementWdg
TIME_WIDGETS = (GanttWdg, GanttElementWdg, TimecardInfoTableElement, WeekTableElement, WorkHoursElementWdg)

SERVICE_WIDGETS = (PublishTableElement, GeneralPublishElementWdg, ParentGroupTableElementWdg, DependencyLink, SObjectSummaryElementWdg, SObjectConnectionElement, CheckoutButtonElementWdg, FileAppendLinkTableElement, *TIME_WIDGETS, *NESTED_WIDGETS, CustomLayoutElementWdg, UpdateWdg, SecurityManagerButtonWdg, PreferenceEditWdg,
                   ProjectTemplateUpdateWdg, NotificationTriggerElementWdg, ButtonElementWdg,
                   ParallelStatusWdg, ParallelStatusEditWdg, SObjectTaskStatusElementWdg, WorkElementWdg, DropElementWdg)

_CLASSES = {
    cls.__module__ + "." + cls.__name__: cls
    for cls in (
        *SERVICE_WIDGETS,
        AuxDataWdg,
        WikiElementWdg,
        LoginTableElementWdg,
        MyTacticSummaryWdg,
        ProcessElementWdg,
        TaskStatusElementWdg,
        ThumbWdg,
        LegacyDiscussionWdg,
        SObjectTaskTableElement,
        TaskParentSpacingTableElement,
        MessageTableElementWdg,
        FormerTaskCompletionWdg,
        ArrayTableElementWdg,
        CheckboxColWdg,
        SearchTypeElementWdg,
        XmlWdg,
        SearchTypeHasTableElementWdg,
        RawTableElementWdg,
        SimpleTableElementWdg,
        DeleteElementWdg,
        ExplorerElementWdg,
        ExplorerTableElementWdg,
        ExpressionElementWdg,
        ExpressionValueElementWdg,
        FormatElementWdg,
        JsonElementWdg,
        LinkElementWdg,
        MetadataElementWdg,
        PreferenceDescriptionWdg,
        ProjectWdg,
        RelatedElementWdg,
        SnapshotInfoWdg,
        SnapshotFileElementWdg,
        SnapshotLockedElementWdg,
        SnapshotVersionElementWdg,
        SObjectDetailElementWdg,
        SObjectFilesElementWdg,
        MilestoneCompletionWdg,
        TaskCompletionWdg,
        TaskDaysDueElementWdg,
        TaskGroupCompletionWdg,
        SubContextElementWdg,
        CheckinButtonElementWdg,
        RecipientElementWdg,
        TaskElementWdg,
        TaskSummaryElementWdg,
        DiscussionElementWdg,
        DiscussionWdg,
    )
}
_catalog = json.loads(
    (files("tactic_stream") / "shared_ui/features/table/widgets.json").read_text(
        encoding="utf-8"
    )
)
WIDGETS = {
    alias: _CLASSES[entry["class"]] for entry in _catalog for alias in entry["aliases"]
}
assert len(WIDGETS) == sum(len(entry["aliases"]) for entry in _catalog), (
    "Duplicate table widget alias"
)
NOTE_WIDGETS = (DiscussionElementWdg, DiscussionWdg, LegacyDiscussionWdg)
TASK_WIDGETS = (TaskElementWdg, TaskSummaryElementWdg, SObjectTaskTableElement)

VALUE_WIDGETS = (
    *SERVICE_WIDGETS,
    WikiElementWdg,
    AuxDataWdg,
    LoginTableElementWdg,
    MyTacticSummaryWdg,
    ProcessElementWdg,
    TaskStatusElementWdg,
    LegacyDiscussionWdg,
    SObjectTaskTableElement,
    TaskParentSpacingTableElement,
    MessageTableElementWdg,
    SnapshotLockedElementWdg,
    SnapshotInfoWdg,
    SnapshotFileElementWdg,
    MilestoneCompletionWdg,
    TaskGroupCompletionWdg,
    TaskDaysDueElementWdg,
    SubContextElementWdg,
    CheckboxColWdg,
    SearchTypeElementWdg,
    TaskSummaryElementWdg,
    FormerTaskCompletionWdg,
    DiscussionWdg,
    ProjectWdg,
    PreferenceDescriptionWdg,
    RelatedElementWdg,
    RecipientElementWdg,
    SearchTypeHasTableElementWdg,
)

ACTION_KINDS = {
    SObjectDetailElementWdg: "sobject_detail",
    CheckinButtonElementWdg: "checkin",
    ExplorerElementWdg: "explorer",
    ExplorerTableElementWdg: "explorer",
    SObjectFilesElementWdg: "file_list",
    MetadataElementWdg: "metadata",
    DeleteElementWdg: "delete",
}


def describe_cell(element, columns, search_type=""):
    options = element["display"]["options"]
    if (
        search_type == "sthpw/transaction_log"
        and element["display"]["handler"] == "tactic.ui.table.HiddenRowElementWdg"
    ):
        flags = {
            "show_search_limit",
            "show_insert",
            "show_select",
            "show_gear",
            "show_shelf",
        }
        supported = (
            not set(options) - {"search_type", "view", "dynamic_class", *flags}
            and all(options.get(name) in (None, False, "false") for name in flags)
            and options.get("search_type") == search_type
            and options.get("view") == "log"
            and options.get("dynamic_class") == "tactic.ui.panel.FastTableLayoutWdg"
            and not element["action"]["handler"]
        )
        return dict(
            kind="journal-details",
            field="",
            supported=supported,
            sortable=False,
            sort_field="",
            server=False,
        )
    widget = WIDGETS.get(element["display"]["handler"])
    field = options.get("column") or element["name"]
    computed = (
        widget in VALUE_WIDGETS
        or widget in ACTION_KINDS
        or widget in (ThumbWdg, DiscussionElementWdg, TaskElementWdg, TaskCompletionWdg)
        or (
            widget is ExpressionElementWdg
            and isinstance(options.get("expression"), str)
            and bool(options["expression"])
        )
    )
    action = element["action"]["handler"]
    native_database_action = (
        widget is ExpressionElementWdg
        and action in (
            "DatabaseAction",
            "pyasm.command.DatabaseAction",
            "pyasm.command.edit_wdg_action.DatabaseAction",
        )
        and not set(element['action']['options']) - {'column'}
        and (element['action']['options'].get('column') or field) in columns
    )
    native_task_action = (
        widget in TASK_WIDGETS
        and action
        in (
            "tactic.ui.table.TaskElementCbk",
            "tactic.ui.table.task_element_wdg.TaskElementCbk",
        )
        and not element["action"]["options"]
    )
    native_time_action = (
        widget in (GanttWdg, GanttElementWdg)
        and action
        in (
            'tactic.ui.table.GanttCbk',
            'tactic.ui.table.gantt_element_wdg.GanttCbk',
            'tactic.ui.table.GanttChildrenCbk',
            'pyasm.widget.GanttCbk',
            'pyasm.widget.gantt_wdg.GanttCbk',
        )
    ) or (
        widget is WorkHoursElementWdg
        and action
        in (
            'WorkHoursElementAction',
            'tactic.ui.table.WorkHoursElementAction',
            'tactic.ui.table.work_hours_element_wdg.WorkHoursElementAction',
            'tactic.core.work_hours.WorkHoursElementAction',
        )
        and not element['action']['options']
    )
    native_parent_action = action in (
        'ParentGroupAction', 'tactic.ui.table.ParentGroupAction', 'tactic.ui.table.group_element_wdg.ParentGroupAction'
    ) and not element['action']['options']
    native_drop_action = widget is DropElementWdg and action in (
        'FileIngestCmd', 'tactic.ui.widget.FileIngestCmd', 'tactic.ui.widget.file_browser_wdg.FileIngestCmd'
    ) and not element['action']['options']
    native_drop_action = native_drop_action or (
        widget is DropElementWdg
        and action in ('DropElementAction', 'tactic.ui.table.DropElementAction',
                       'tactic.ui.table.drop_element_wdg.DropElementAction')
        and not set(element['action']['options']) - {'instance_type', 'path'}
        and all(value == options.get(name, '') for name, value in element['action']['options'].items())
    )
    supported = (
        widget is not None
        and isinstance(field, str)
        and (field in columns or computed)
        and (not action or native_database_action or native_task_action or native_time_action or native_parent_action or native_drop_action)
    )
    allowed = {"column"}
    if widget in TIME_WIDGETS:
        allowed |= set(widget.ARGS_KEYS) if hasattr(widget, 'ARGS_KEYS') else set()
        if widget is GanttWdg:
            handlers_raw = str(options.get('handlers') or '').strip()
            handlers = [h.strip() for h in handlers_raw.split('|') if h.strip()] if handlers_raw else []
            supported = supported and all(h in ('ScheduleGanttWdg', 'ResourceUsageGanttWdg') for h in handlers)
        for size in ('width', 'cal_margin', 'day_width'):
            raw = options.get(size)
            if raw not in (None, ''):
                supported = supported and str(raw).isdecimal() and int(raw) > 0
    elif widget in (PublishTableElement, GeneralPublishElementWdg):
        allowed |= set(widget.ARGS_KEYS)
        if widget is GeneralPublishElementWdg:
            supported = supported and options.get('preview') in (None, '', True, False, 'true', 'false')
    elif widget is ParentGroupTableElementWdg:
        allowed |= set(widget.ARGS_KEYS)
        supported = supported and options.get('disable') in (None, '', True, False, 'true', 'false')
    elif widget is CheckoutButtonElementWdg:
        allowed |= set(widget.ARGS_KEYS)
    elif widget is SObjectConnectionElement:
        allowed |= set(widget.ARGS_KEYS)
        icon_size = str(options.get('icon_size') or '60')
        supported = supported and options.get('direction', 'dst') in ('', 'src', 'dst')
        supported = supported and icon_size.isdecimal() and 16 <= int(icon_size) <= 256
    elif widget in NESTED_WIDGETS:
        allowed |= set(HiddenRowElementWdg.ARGS_KEYS)
        if (
            options.get('dynamic_class', options.get('dynamic'))
            == 'tactic.ui.panel.ViewPanelWdg'
            and options.get('search_type') == 'sthpw/snapshot'
            and options.get('layout') == 'tile'
        ):
            allowed |= {
                'process',
                'context',
                'checkin_type',
                'hide_checkbox',
                'show_context_menu',
                'allow_drag',
                'scale',
                'layout',
                'checkin_context',
                'search_key',
                'show_column_manager',
                'expand_mode',
                'show_help',
                'show_refresh',
                'show_expand',
                'show_keyword_search',
                'show_layout_switcher',
                'show_border',
                'show_drop_shadow',
                'no_results_mode',
                'gallery_align',
            }
        supported = supported and options.get('width') in (None, '', '100%')
    elif widget in (ButtonElementWdg, DropElementWdg, CustomLayoutElementWdg):
        allowed |= set(widget.ARGS_KEYS)
    elif widget in (ParallelStatusWdg, TaskStatusElementWdg, WorkElementWdg):
        allowed |= set(widget.ARGS_KEYS)
    elif widget is UpdateWdg:
        allowed |= {'edit', 'delete', 'retire', 'insert', 'edit_view', 'insert_view', 'width', 'user_filter'}
    elif widget is ProjectTemplateUpdateWdg:
        allowed.add('icon')
    elif widget is SObjectDetailElementWdg:
        allowed |= set(widget.ARGS_KEYS)
    elif widget is CheckinButtonElementWdg:
        allowed |= {
            "process",
            "mode",
            "transfer_mode",
            "sobject_mode",
            "lock_process",
            "show_context",
            "show_links",
            "subcontext",
            "width",
        }
        supported = supported and options.get("sobject_mode", "parent") in (
            "",
            "parent",
            "connect",
            "expression",
            "self",
        )
    elif widget in (ExplorerElementWdg, ExplorerTableElementWdg):
        allowed |= {"mode", "decrement"}
        supported = supported and options.get("mode", "sandbox") in (
            "",
            "sandbox",
            "repository",
        )
    elif widget is MetadataElementWdg:
        allowed.add("context")
    elif widget is SObjectFilesElementWdg:
        allowed.add("icon_size")
    elif widget is JsonElementWdg:
        allowed.add("height")
        height = str(options.get("height", "300")).removesuffix("px")
        supported = supported and height.isdecimal() and 1 <= int(height) <= 600
    elif widget is FormatElementWdg:
        allowed |= {"type", "format", "fps", "timezone", "justify", "constraint", "total_summary"}
        supported = supported and options.get("total_summary") in (None, "", "count", "total", "average")
    elif widget is LinkElementWdg:
        allowed |= set(widget.ARGS_KEYS)
    elif widget is SearchTypeElementWdg:
        allowed.add("filename")
    elif widget is SimpleTableElementWdg:
        allowed |= {"css_background", "css_background-color", "rowcss_background-color"}
    elif widget is ExpressionElementWdg:
        allowed |= {
            "expression",
            "alt_expression",
            "display_expression",
            "display_format",
            "return",
            "mode",
            "expression_mode",
            "calc_mode",
            "show_retired",
            "use_cache",
            "order_by",
            "group_by",
            "group_by_time",
            "justify",
            "empty",
            "bottom",
            "group_bottom",
            "inline_styles",
            "rowcss_background-color",
        }
        supported = supported and options.get("mode", "value") in (
            "",
            "value",
            "boolean",
            "check",
        )
        supported = supported and (
            options.get("use_cache") not in (True, "true") or field in columns
        )
    elif widget is ThumbWdg:
        allowed |= {
            "icon_context",
            "cascade_search",
            "filename",
            "file_type",
            "latest_icon",
            "original",
            "protocol",
            "image_link_order",
            "redirect",
            "redirect_expr",
        }
        # Handler uses its shared circular preview, independent of legacy HTML sizing.
        allowed |= {
            "icon_size",
            "min_icon_size",
            "detail",
            "show_resize_scroll",
            "context",
        }
        supported = supported and options.get("protocol", "http") in ("", "http")
    elif widget is LegacyDiscussionWdg:
        allowed |= {"process", "context", "setting", "append_setting", "include_submission", "scroll", "sticky"}
    elif widget in NOTE_WIDGETS:
        allowed |= {"process", "context", "use_parent", "mode", "allow_email"}
        allowed |= {'show_note_expand', 'context_hidden'}
        supported = supported and options.get('show_note_expand') in (None, '', False, 'false')
        supported = supported and options.get('context_hidden') in (None, '', True, False, 'true', 'false')
        allowed |= set(DiscussionElementWdg.ARGS_KEYS) | {"sticky"}
        # Handler opens its inspector rather than the old HTML/email popup.
        supported = supported and options.get("mode") in (None, "", "default", "icon")
    elif widget in TASK_WIDGETS:
        allowed |= {
            "process",
            "context",
            "processes",
            "pipeline_code",
            "parent_process",
            "task_filter",
            "show_current_pipeline_only",
            "show_filler_tasks",
            "expression",
        }
        # Native task selection, with Handler's fixed compact card presentation.
        allowed |= set(widget.ARGS_KEYS) - {"cbjs_action", "script_path"}
        # Legacy edit is redundant; native status/assignee editors retain their own ACL.
        allowed |= {"collate_columns", "status_color", "font_size", "edit"}
        supported = supported and options.get('edit') in (None, '', True, False, 'true', 'false')
        if widget is TaskSummaryElementWdg:
            supported = supported and options.get("mode") in (
                None,
                "",
                "default",
                "minimal",
            )
    elif widget in (
        TaskCompletionWdg,
        MilestoneCompletionWdg,
        TaskGroupCompletionWdg,
        FormerTaskCompletionWdg,
    ):
        allowed |= {"task_expr", "width"}
        if widget is TaskGroupCompletionWdg:
            allowed.add("options")
    elif widget is RelatedElementWdg:
        allowed |= {"template", "expression"}
    elif widget is TaskDaysDueElementWdg:
        allowed.add("due_date_col")
    supported = supported and not set(options) - allowed
    kind = ACTION_KINDS.get(widget, "text")
    if widget in SERVICE_WIDGETS or native_parent_action:
        kind = 'commands'
    elif widget is MyTacticSummaryWdg:
        kind = 'fields'
    elif widget is TaskSummaryElementWdg:
        kind = "task_summary"
    elif widget in TASK_WIDGETS:
        kind = "tasks"
    elif widget in (JsonElementWdg, XmlWdg):
        kind = "structured"
    elif widget in (TaskCompletionWdg, MilestoneCompletionWdg, FormerTaskCompletionWdg):
        kind = "completion"
    elif widget is TaskGroupCompletionWdg:
        kind = "group_completion"
    elif widget is SnapshotLockedElementWdg:
        kind = "locked"
    elif widget is SnapshotFileElementWdg:
        kind = "link"
    elif widget is CheckboxColWdg:
        kind = "selection"
    elif widget in (ProjectWdg, RecipientElementWdg):
        kind = "fields"
    elif widget is SearchTypeHasTableElementWdg:
        kind = "status_flag"
    elif widget is MessageTableElementWdg:
        kind = "message"
    elif widget in NOTE_WIDGETS:
        kind = "notes"
    elif widget is ThumbWdg:
        kind = "thumbnail"
    elif widget is LinkElementWdg:
        kind = "link"
    elif widget is ExpressionElementWdg and options.get("mode") in ("boolean", "check"):
        kind = options["mode"]
    elif (widget is FormatElementWdg and options.get("format") == "Checkbox") or (
        kind == "text"
        and isinstance(field, str)
        and columns.get(field, {}).get("data_type", "").lower() in ("bool", "boolean")
    ):
        kind = "boolean"
    sort_field = field
    sortable = (
        supported
        and (widget not in VALUE_WIDGETS or widget in (LoginTableElementWdg, ProcessElementWdg, TaskStatusElementWdg))
        and widget not in ACTION_KINDS
        and widget
        not in (
            LinkElementWdg,
            ThumbWdg,
            DiscussionElementWdg,
            TaskElementWdg,
            TaskCompletionWdg,
            JsonElementWdg,
        )
    )
    if widget is ExpressionElementWdg and supported:
        native = ExpressionElementWdg(name=element["name"], **options)
        native.preprocess()
        sort_field = (
            field
            if options.get("use_cache") in (True, "true")
            else native.get_option("order_by")
        )
        sortable = supported and native.is_sortable() and sort_field in columns
    return dict(
        kind=kind,
        field=field,
        supported=bool(supported),
        sort_field=sort_field,
        sortable=bool(sortable),
        summary=str(options.get("total_summary") or "") if widget is FormatElementWdg else ("total" if widget in (WorkHoursElementWdg, WeekTableElement) else ""),
        bottom=str(options.get("bottom") or "") if widget is ExpressionElementWdg else "",
        group_bottom=str(options.get("group_bottom") or "") if widget is ExpressionElementWdg else "",
        server=bool(
            supported
            and (
                widget in VALUE_WIDGETS
                or widget in ACTION_KINDS
                or widget
                in (
                    FormatElementWdg,
                    LinkElementWdg,
                    ExpressionElementWdg,
                    ExpressionValueElementWdg,
                    ThumbWdg,
                    DiscussionElementWdg,
                    TaskElementWdg,
                    TaskCompletionWdg,
                    ArrayTableElementWdg,
                    XmlWdg,
                    JsonElementWdg,
                    SnapshotVersionElementWdg,
                )
            )
        ),
    )


def safe_link(value):
    value = str(value or "").strip()
    # Browser navigation uses server-generated URLs, never executable URL schemes.
    if (
        not value
        or any(char.isspace() or ord(char) < 32 for char in value)
        or "\\" in value
    ):
        return ""
    try:
        url = urlsplit(value)
        if url.scheme.lower() in ("http", "https", "mailto"):
            return value
        if not url.scheme and value.startswith("/") and not value.startswith("//"):
            return value
    except ValueError:
        pass
    return ""


def read_table_cells(search_type, view, search_keys):
    _require_table_access(search_type, 'view')
    policy = SearchType.get(search_type).get_record_read_options()
    if policy.get("command"):
        from pyasm.common import Container

        if Container.get("FileProject:access") != Project.get_project_code():
            from pyasm.command import Command
            from tactic.command.file_project_cmd import FileProjectCmd

            command = FileProjectCmd(
                action="admin_search",
                operation="cells",
                payload={
                    "search_type": search_type,
                    "view": view,
                    "search_keys": search_keys,
                },
            )
            Command.execute_cmd(command)
            return command.info
    if (
        not isinstance(search_keys, list)
        or len(search_keys) > 500
        or not all(isinstance(key, str) and key for key in search_keys)
    ):
        raise ValueError("Choose at most 500 table records")
    from re import fullmatch

    from tactic_stream.server.interface import describe_view

    if not isinstance(view, str) or not fullmatch(r"[A-Za-z_][\w.@-]{0,127}", view):
        raise ValueError("Invalid view name")
    base = SearchType.get(search_type).get_base_key()
    for key in [search_type, *search_keys]:
        data = SearchType.breakup_search_type(key)
        if key.split("?")[0] != base or data.get("project") not in (
            None,
            "",
            Project.get_project_code(),
        ):
            raise ValueError("Table records belong to another type or project")
    config = WidgetConfigView.get_by_search_type(base, view)
    description = describe_view(config)
    if view != "table" and not description["configured"]:
        raise LookupError("View is not configured: " + view)
    columns = SearchType.get_column_info(base)
    # Pages may mix code and id keys. The original batch helper refuses that
    # mixture; use its two native reads and restore the caller's order explicitly.
    # Preserve the key's project qualifier: stripping it loses custom-type
    # Task/Snapshot references in admin, although both types use the same DB.
    by_code, by_id = {}, {}
    for full_type in dict.fromkeys(
        SearchKey.extract_search_type(key) for key in search_keys
    ):
        keys = [
            key
            for key in search_keys
            if SearchKey.extract_search_type(key) == full_type
        ]
        codes = [
            SearchKey.extract_code(key) for key in keys if SearchKey.extract_code(key)
        ]
        ids = [
            SearchKey.extract_id(key) for key in keys if not SearchKey.extract_code(key)
        ]
        if codes:
            by_code.update(
                ((full_type, obj.get_code()), obj)
                for obj in Search.get_by_code(full_type, codes)
            )
        if ids:
            by_id.update(
                ((full_type, str(obj.get_id())), obj)
                for obj in Search.get_by_id(full_type, ids)
            )
    objects = [
        by_code.get((SearchKey.extract_search_type(key), SearchKey.extract_code(key)))
        if SearchKey.extract_code(key)
        else by_id.get(
            (SearchKey.extract_search_type(key), str(SearchKey.extract_id(key)))
        )
        for key in search_keys
    ]
    if any(obj is None for obj in objects):
        raise ValueError("A table record no longer exists or is not accessible")
    cells = {key: {} for key in search_keys}
    for element in description["elements"]:
        descriptor = describe_cell(element, columns)
        if not descriptor["server"] or str(
            element["attributes"].get("hidden", "")
        ).lower() in ("true", "1", "yes", "on"):
            continue
        widget_class = WIDGETS[element["display"]["handler"]]
        try:
            widget = widget_class(
                name=element["name"]
                if widget_class is ExpressionElementWdg
                else descriptor["field"],
                **element["display"]["options"],
            )
            widget.set_options(element["display"]["options"])
            widget.action_options = element["action"]["options"]
            widget.set_attributes(element["attributes"])
            widget.set_sobjects(objects)
            widget.preprocess()
            parent_action = element['action']['handler'] in (
                'ParentGroupAction', 'tactic.ui.table.ParentGroupAction', 'tactic.ui.table.group_element_wdg.ParentGroupAction'
            ) and not element['action']['options']
            parent_values = None
            if parent_action and widget_class is not ParentGroupTableElementWdg:
                parent_values = read_parent_cells([obj.get_search_key() for obj in objects])
        except SecurityException:
            raise
        except Exception as error:
            for key in search_keys:
                cells[key][element["name"]] = dict(text="", error=str(error))
            continue
        for index, (key, obj) in enumerate(zip(search_keys, objects)):
            widget.set_current_index(index)
            try:
                value = (
                    widget.get_cell_value()
                    if widget_class in VALUE_WIDGETS
                    or widget_class in ACTION_KINDS
                    or widget_class
                    in (
                        ExpressionElementWdg,
                        ExpressionValueElementWdg,
                        ThumbWdg,
                        DiscussionElementWdg,
                        TaskElementWdg,
                        TaskCompletionWdg,
                        ArrayTableElementWdg,
                        XmlWdg,
                        JsonElementWdg,
                        SnapshotVersionElementWdg,
                    )
                    else widget.get_text_value()
                )
                cell = (
                    value
                    if isinstance(value, dict)
                    else {"text": "" if value is None else str(value)}
                )
                if widget_class in TASK_WIDGETS:
                    cell["widthHint"] = widget.get_width()
                if parent_values is not None:
                    cell = dict(parent_values[obj.get_search_key()], **cell)
                    cell['parentGrouping'] = False
                if parent_action or widget_class is ParentGroupTableElementWdg:
                    cell.update(parentEditable=parent_action, tableView=view, columnName=element['name'])
                if widget_class is ButtonElementWdg:
                    cell['columnName'] = element['name']
                if widget_class is DropElementWdg:
                    cell['tableView'] = view
                if widget_class in TIME_WIDGETS:
                    cell['tableView'] = view
                    cell['columnName'] = element['name']
                    cell['actionOptions'] = element['action']['options']
                if widget_class is ThumbWdg:
                    cell["image"] = safe_link(cell["image"])
                    cell["text"] = safe_link(cell["text"])
                    for file in cell["files"]:
                        file["href"] = safe_link(file["href"])
                if descriptor["kind"] == "link":
                    if isinstance(value, dict):
                        cell["href"] = safe_link(cell.get("href"))
                    else:
                        link = str(value or "")
                        if link.startswith("{") and link.endswith("}"):
                            link = Search.eval(link)
                        cell = dict(text=str(link or ""), href=safe_link(link))
                cells[key][element["name"]] = cell
            except Exception as error:
                cells[key][element["name"]] = dict(text="", error=str(error))
    return cells
