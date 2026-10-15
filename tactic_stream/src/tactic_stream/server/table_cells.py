"""Typed cells for the Vue table, using native TACTIC widget value methods."""
from urllib.parse import urlsplit

from pyasm.search import Search, SearchType, SearchKey
from pyasm.biz import Project
from pyasm.widget import WidgetConfigView, ThumbWdg, ArrayTableElementWdg, XmlWdg
from pyasm.security.security import _require_admin
from tactic.ui.common import SimpleTableElementWdg, RawTableElementWdg
from tactic.ui.table import FormatElementWdg, LinkElementWdg, ExpressionElementWdg, ExpressionValueElementWdg, TaskElementWdg, TaskCompletionWdg, JsonElementWdg, SnapshotVersionElementWdg
from tactic.ui.widget.discussion_wdg import DiscussionElementWdg
from tactic.ui.table import SObjectDetailElementWdg, CheckinButtonElementWdg, ExplorerElementWdg, ExplorerTableElementWdg, SObjectFilesElementWdg, MetadataElementWdg, DeleteElementWdg


WIDGETS = {
    'tactic.ui.table.SObjectDetailElementWdg': SObjectDetailElementWdg,
    'tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg': SObjectDetailElementWdg,
    'tactic.ui.table.CheckinButtonElementWdg': CheckinButtonElementWdg,
    'tactic.ui.table.table_element_wdg.CheckinButtonElementWdg': CheckinButtonElementWdg,
    'tactic.ui.table.ExploreElementWdg': ExplorerElementWdg,
    'tactic.ui.table.ExplorerElementWdg': ExplorerElementWdg,
    'tactic.ui.table.ExplorerTableElementWdg': ExplorerTableElementWdg,
    'tactic.ui.table.explorer_wdg.ExplorerElementWdg': ExplorerElementWdg,
    'tactic.ui.table.SObjectFilesElementWdg': SObjectFilesElementWdg,
    'tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg': SObjectFilesElementWdg,
    'tactic.ui.table.MetadataElementWdg': MetadataElementWdg,
    'tactic.ui.table.metadata_element_wdg.MetadataElementWdg': MetadataElementWdg,
    'tactic.ui.table.DeleteElementWdg': DeleteElementWdg,
    'tactic.ui.table.delete_element_wdg.DeleteElementWdg': DeleteElementWdg,
    'ArrayTableElementWdg': ArrayTableElementWdg,
    'pyasm.widget.ArrayTableElementWdg': ArrayTableElementWdg,
    'pyasm.widget.table_element_wdg.ArrayTableElementWdg': ArrayTableElementWdg,
    'XmlWdg': XmlWdg,
    'pyasm.widget.XmlWdg': XmlWdg,
    'pyasm.widget.table_element_wdg.XmlWdg': XmlWdg,
    'tactic.ui.table.JsonElementWdg': JsonElementWdg,
    'tactic.ui.table.json_element_wdg.JsonElementWdg': JsonElementWdg,
    'tactic.ui.table.SnapshotVersionElementWdg': SnapshotVersionElementWdg,
    'tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg': SnapshotVersionElementWdg,
    'ThumbWdg': ThumbWdg,
    'TextWdg': SimpleTableElementWdg,
    'tactic.ui.table.TaskCompletionWdg': TaskCompletionWdg,
    'tactic.ui.table.statistic_wdg.TaskCompletionWdg': TaskCompletionWdg,
    'tactic.ui.table.TaskElementWdg': TaskElementWdg,
    'tactic.ui.table.task_element_wdg.TaskElementWdg': TaskElementWdg,
    'tactic.ui.widget.DiscussionElementWdg': DiscussionElementWdg,
    'tactic.ui.widget.discussion_wdg.DiscussionElementWdg': DiscussionElementWdg,
    'pyasm.widget.ThumbWdg': ThumbWdg,
    'pyasm.widget.file_wdg.ThumbWdg': ThumbWdg,
    '': SimpleTableElementWdg, 'pyasm.widget.TextWdg': SimpleTableElementWdg,
    'tactic.ui.common.SimpleTableElementWdg': SimpleTableElementWdg,
    'tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg': SimpleTableElementWdg,
    'tactic.ui.common.RawTableElementWdg': RawTableElementWdg,
    'tactic.ui.common.base_table_element_wdg.RawTableElementWdg': RawTableElementWdg,
    'tactic.ui.table.FormatElementWdg': FormatElementWdg,
    'tactic.ui.table.format_element_wdg.FormatElementWdg': FormatElementWdg,
    'tactic.ui.table.LinkElementWdg': LinkElementWdg,
    'tactic.ui.table.link_element_wdg.LinkElementWdg': LinkElementWdg,
    'tactic.ui.table.ExpressionElementWdg': ExpressionElementWdg,
    'tactic.ui.table.expression_element_wdg.ExpressionElementWdg': ExpressionElementWdg,
    'tactic.ui.table.ExpressionValueElementWdg': ExpressionValueElementWdg,
    'tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg': ExpressionValueElementWdg,
}

ACTION_KINDS = {SObjectDetailElementWdg: 'sobject_detail', CheckinButtonElementWdg: 'checkin',
    ExplorerElementWdg: 'explorer', ExplorerTableElementWdg: 'explorer',
    SObjectFilesElementWdg: 'file_list', MetadataElementWdg: 'metadata', DeleteElementWdg: 'delete'}


def describe_cell(element, columns, search_type=''):
    options = element['display']['options']
    if search_type == 'sthpw/transaction_log' and element['display']['handler'] == 'tactic.ui.table.HiddenRowElementWdg':
        flags = {'show_search_limit', 'show_insert', 'show_select', 'show_gear', 'show_shelf'}
        supported = (not set(options) - {'search_type', 'view', 'dynamic_class', *flags}
            and all(options.get(name) in (None, False, 'false') for name in flags)
            and options.get('search_type') == search_type and options.get('view') == 'log'
            and options.get('dynamic_class') == 'tactic.ui.panel.FastTableLayoutWdg' and not element['action']['handler'])
        return dict(kind='journal-details', field='', supported=supported, sortable=False, sort_field='', server=False)
    widget = WIDGETS.get(element['display']['handler'])
    field = options.get('column') or element['name']
    computed = widget in ACTION_KINDS or widget in (ThumbWdg, DiscussionElementWdg, TaskElementWdg, TaskCompletionWdg) or (widget is ExpressionElementWdg and isinstance(options.get('expression'), str) and bool(options['expression']))
    action = element['action']['handler']
    native_task_action = widget is TaskElementWdg and action in ('tactic.ui.table.TaskElementCbk', 'tactic.ui.table.task_element_wdg.TaskElementCbk') and not element['action']['options']
    supported = widget is not None and isinstance(field, str) and (field in columns or computed) and (not action or native_task_action)
    allowed = {'column'}
    if widget is SObjectDetailElementWdg:
        allowed |= set(widget.ARGS_KEYS)
    elif widget is CheckinButtonElementWdg:
        allowed |= {'process', 'mode', 'transfer_mode', 'sobject_mode', 'lock_process', 'show_context', 'show_links', 'subcontext', 'width'}
        supported = supported and options.get('sobject_mode', 'parent') in ('', 'parent', 'connect', 'expression', 'self')
    elif widget in (ExplorerElementWdg, ExplorerTableElementWdg):
        allowed |= {'mode', 'decrement'}
        supported = supported and options.get('mode', 'sandbox') in ('', 'sandbox', 'repository')
    elif widget is MetadataElementWdg:
        allowed.add('context')
    elif widget is SObjectFilesElementWdg:
        allowed.add('icon_size')
    elif widget is JsonElementWdg:
        allowed.add('height')
        height = str(options.get('height', '300')).removesuffix('px')
        supported = supported and height.isdecimal() and 1 <= int(height) <= 600
    elif widget is FormatElementWdg:
        allowed |= {'type', 'format', 'fps', 'timezone', 'justify', 'constraint'}
    elif widget is LinkElementWdg:
        allowed.add('icon')
    elif widget is ExpressionElementWdg:
        allowed |= {'expression', 'alt_expression', 'display_expression', 'display_format', 'return',
                    'mode', 'expression_mode', 'calc_mode', 'show_retired', 'use_cache', 'order_by',
                    'group_by', 'group_by_time', 'justify', 'empty'}
        supported = supported and options.get('mode', 'value') in ('', 'value', 'boolean', 'check')
        supported = supported and (options.get('use_cache') not in (True, 'true') or field in columns)
    elif widget is ThumbWdg:
        allowed |= {'icon_context', 'cascade_search', 'filename', 'file_type', 'latest_icon', 'original', 'protocol', 'image_link_order'}
        # Handler uses its shared circular preview, independent of legacy HTML sizing.
        allowed |= {'icon_size', 'min_icon_size', 'detail', 'show_resize_scroll', 'context'}
        supported = supported and options.get('protocol', 'http') in ('', 'http')
    elif widget is DiscussionElementWdg:
        allowed |= {'process', 'context', 'use_parent', 'mode', 'allow_email'}
        allowed |= set(DiscussionElementWdg.ARGS_KEYS) | {'sticky'}
        # Handler opens its inspector rather than the old HTML/email popup.
        supported = supported and options.get('mode') in (None, '', 'default', 'icon')
    elif widget is TaskElementWdg:
        allowed |= {'process', 'context', 'processes', 'pipeline_code', 'parent_process',
                    'task_filter', 'show_current_pipeline_only', 'show_filler_tasks', 'expression'}
        # Native task selection, with Handler's fixed compact card presentation.
        allowed |= set(TaskElementWdg.ARGS_KEYS) - {'cbjs_action', 'script_path'}
        allowed |= {'collate_columns', 'status_color', 'font_size'}
    elif widget is TaskCompletionWdg:
        allowed |= {'task_expr', 'width'}
    supported = supported and not set(options) - allowed
    kind = ACTION_KINDS.get(widget, 'text')
    if widget is TaskElementWdg:
        kind = 'tasks'
    elif widget in (JsonElementWdg, XmlWdg):
        kind = 'structured'
    elif widget is TaskCompletionWdg:
        kind = 'completion'
    elif widget is DiscussionElementWdg:
        kind = 'notes'
    elif widget is ThumbWdg:
        kind = 'thumbnail'
    elif widget is LinkElementWdg:
        kind = 'link'
    elif widget is ExpressionElementWdg and options.get('mode') in ('boolean', 'check'):
        kind = options['mode']
    elif (widget is FormatElementWdg and options.get('format') == 'Checkbox') or (
            isinstance(field, str) and columns.get(field, {}).get('data_type', '').lower() in ('bool', 'boolean')):
        kind = 'boolean'
    sort_field = field
    sortable = supported and widget not in ACTION_KINDS and widget not in (LinkElementWdg, ThumbWdg, DiscussionElementWdg, TaskElementWdg, TaskCompletionWdg, JsonElementWdg)
    if widget is ExpressionElementWdg and supported:
        native = ExpressionElementWdg(name=element['name'], **options)
        native.preprocess()
        sort_field = field if options.get('use_cache') in (True, 'true') else native.get_option('order_by')
        sortable = supported and native.is_sortable() and sort_field in columns
    return dict(kind=kind, field=field, supported=bool(supported), sort_field=sort_field,
        sortable=bool(sortable), server=bool(supported and (widget in ACTION_KINDS or widget in (
            FormatElementWdg, LinkElementWdg, ExpressionElementWdg, ExpressionValueElementWdg, ThumbWdg, DiscussionElementWdg, TaskElementWdg, TaskCompletionWdg, ArrayTableElementWdg, XmlWdg, JsonElementWdg, SnapshotVersionElementWdg))))


def safe_link(value):
    value = str(value or '').strip()
    # Browser navigation uses server-generated URLs, never executable URL schemes.
    if not value or any(char.isspace() or ord(char) < 32 for char in value) or '\\' in value:
        return ''
    try:
        url = urlsplit(value)
        if url.scheme.lower() in ('http', 'https', 'mailto'):
            return value
        if not url.scheme and value.startswith('/') and not value.startswith('//'):
            return value
    except ValueError:
        pass
    return ''


def read_table_cells(search_type, view, search_keys):
    _require_admin()
    policy = SearchType.get(search_type).get_record_read_options()
    if policy.get('command'):
        from pyasm.common import Container
        if Container.get('FileProject:access') != Project.get_project_code():
            from pyasm.command import Command
            from tactic.command.file_project_cmd import FileProjectCmd
            command = FileProjectCmd(action='admin_search', operation='cells',
                payload={'search_type': search_type, 'view': view, 'search_keys': search_keys})
            Command.execute_cmd(command)
            return command.info
    if not isinstance(search_keys, list) or len(search_keys) > 500 or not all(isinstance(key, str) and key for key in search_keys):
        raise ValueError('Choose at most 500 table records')
    from tactic_stream.server.interface import describe_view
    from re import fullmatch
    if not isinstance(view, str) or not fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
        raise ValueError('Invalid view name')
    base = SearchType.get(search_type).get_base_key()
    for key in [search_type, *search_keys]:
        data = SearchType.breakup_search_type(key)
        if key.split('?')[0] != base or data.get('project') not in (None, '', Project.get_project_code()):
            raise ValueError('Table records belong to another type or project')
    config = WidgetConfigView.get_by_search_type(base, view)
    description = describe_view(config)
    if view != 'table' and not description['configured']:
        raise LookupError('View is not configured: ' + view)
    columns = SearchType.get_column_info(base)
    # Pages may mix code and id keys. The original batch helper refuses that
    # mixture; use its two native reads and restore the caller's order explicitly.
    # Preserve the key's project qualifier: stripping it loses custom-type
    # Task/Snapshot references in admin, although both types use the same DB.
    by_code, by_id = {}, {}
    for full_type in dict.fromkeys(SearchKey.extract_search_type(key) for key in search_keys):
        keys = [key for key in search_keys if SearchKey.extract_search_type(key) == full_type]
        codes = [SearchKey.extract_code(key) for key in keys if SearchKey.extract_code(key)]
        ids = [SearchKey.extract_id(key) for key in keys if not SearchKey.extract_code(key)]
        if codes:
            by_code.update(((full_type, obj.get_code()), obj) for obj in Search.get_by_code(full_type, codes))
        if ids:
            by_id.update(((full_type, str(obj.get_id())), obj) for obj in Search.get_by_id(full_type, ids))
    objects = [by_code.get((SearchKey.extract_search_type(key), SearchKey.extract_code(key))) if SearchKey.extract_code(key)
               else by_id.get((SearchKey.extract_search_type(key), str(SearchKey.extract_id(key)))) for key in search_keys]
    if any(obj is None for obj in objects):
        raise ValueError('A table record no longer exists or is not accessible')
    cells = {key: {} for key in search_keys}
    for element in description['elements']:
        descriptor = describe_cell(element, columns)
        if not descriptor['server'] or str(element['attributes'].get('hidden', '')).lower() in ('true', '1', 'yes', 'on'):
            continue
        widget_class = WIDGETS[element['display']['handler']]
        widget = widget_class(name=element['name'] if widget_class is ExpressionElementWdg else descriptor['field'], **element['display']['options'])
        widget.set_options(element['display']['options']); widget.set_attributes(element['attributes'])
        widget.set_sobjects(objects); widget.preprocess()
        for index, (key, obj) in enumerate(zip(search_keys, objects)):
            widget.set_current_index(index)
            try:
                value = widget.get_cell_value() if widget_class in ACTION_KINDS or widget_class in (ExpressionElementWdg, ExpressionValueElementWdg, ThumbWdg, DiscussionElementWdg, TaskElementWdg, TaskCompletionWdg, ArrayTableElementWdg, XmlWdg, JsonElementWdg, SnapshotVersionElementWdg) else widget.get_text_value()
                cell = value if isinstance(value, dict) else {'text': '' if value is None else str(value)}
                if widget_class is ThumbWdg:
                    cell['image'] = safe_link(cell['image'])
                    cell['text'] = safe_link(cell['text'])
                    for file in cell['files']:
                        file['href'] = safe_link(file['href'])
                if descriptor['kind'] == 'link':
                    link = str(value or '')
                    if link.startswith('{') and link.endswith('}'):
                        link = Search.eval(link)
                    cell = dict(text=str(link or ''), href=safe_link(link))
                cells[key][element['name']] = cell
            except Exception as error:
                cells[key][element['name']] = dict(text='', error=str(error))
    return cells
