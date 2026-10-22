"""TACTIC view descriptors and primitive EditWdg form preparation, without HTML."""
import hashlib
import re

from pyasm.biz import Project
from pyasm.common import Container
from pyasm.search import Search, SearchKey, SearchType, WidgetDbConfig
from pyasm.security.security import _require_admin
from pyasm.widget import WidgetConfig, WidgetConfigView


def read_form(search_type, view='edit', search_key=None, default=None, source_key=None, search_keys=None, parent_key=None, connect_key=None, element_names=None, ignore=None):
    _require_admin()
    if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
        raise ValueError('Invalid view name')
    if isinstance(ignore, str):
        ignore = ignore.split('|')
    if ignore is not None and (not isinstance(ignore,list) or len(ignore)>128 or any(not isinstance(name,str) or len(name)>128 for name in ignore)):
        raise ValueError('Invalid ignored form fields')
    project = Project.get_project_code()
    SearchType.get(search_type)
    for name, key in (('parent_key', parent_key), ('connect_key', connect_key)):
        if key is None:
            continue
        if not isinstance(key, str) or not key or view != 'insert' or search_key or search_keys is not None:
            raise ValueError('Related creation requires an insert form and a valid ' + name)
        from tactic_stream.server.object_operations import selected_objects, read_relations
        target = selected_objects(SearchKey.extract_base_search_type(key), [key])[0]
        if name == 'parent_key':
            relations = read_relations(target.get_base_search_type(), key)['relations']
            if not any(item['search_type'] == SearchKey.extract_base_search_type(search_type) and item['can_create'] for item in relations):
                raise ValueError('Related creation is unavailable for this relationship')
    records = []
    if search_keys is not None:
        if search_key or source_key or default or view == 'insert' or not isinstance(search_keys, list):
            raise ValueError('Batch editing requires an edit form without overrides')
        from tactic_stream.server.object_operations import selected_objects
        records = selected_objects(search_type, search_keys)
        search_key = records[0].get_search_key(use_id=True)
    if source_key and (search_key or view != 'insert' or default):
        raise ValueError('Duplication requires an insert form without overrides')
    for key in (search_type, search_key, source_key):
        if key:
            data = SearchType.breakup_search_type(key)
            if data.get('project') and data['project'] != project:
                raise ValueError('Select the target project before reading its form')
    for key in (search_key, source_key):
        if key and SearchKey.extract_base_search_type(key) != SearchKey.extract_base_search_type(search_type):
            raise ValueError('Search key does not belong to this search type')
    if source_key and SearchKey.extract_base_search_type(search_type) in ('sthpw/file', 'sthpw/snapshot'):
        raise ValueError('Repository objects require the dedicated copy/check-in path')
    from tactic.ui.panel import EditWdg
    from tactic.ui.widget import CalendarInputWdg, TimeInputWdg, SimpleUploadWdg
    from tactic.ui.widget.upload_wdg import UploadWdg as RichUploadWdg
    from tactic.ui.input import TaskSObjectInputWdg
    from tactic.ui.input import ColorInputWdg
    from pyasm.widget import HiddenWdg, MultiSelectWdg, UploadWdg, SelectWdg, ThumbInputWdg
    if element_names is not None:
        config = WidgetConfigView.get_by_search_type(search_type, view, use_cache=False)
        if not isinstance(element_names, list) or not element_names or any(not isinstance(name, str) or name not in config.get_element_names() for name in element_names):
            raise ValueError('This column is not in the native edit view')
    widget = EditWdg(search_type=search_type, view=view, search_key=source_key or search_key,
                     default=default, parent_key=parent_key, mode='insert' if source_key else None,
                     element_names=','.join(element_names) if element_names is not None else None, ignore=ignore)
    widget.explicit_display()
    fields = []
    for item in widget.get_widgets():
        if source_key and (item.get_option('column') or item.get_name()) in ('id', 'code', 'timestamp', 'last_update'):
            continue
        prepared = getattr(item, 'input', item)
        if prepared is None:
            continue
        field = dict(name=item.get_name(), title=item.get_display_title(),
                     class_name=item.get_class_name(), values=item.get_values(for_display=True),
                     options=item.options, attributes=item._attributes,
                     action=dict(handler=widget.config.get_action_handler(item.name),
                                 options=widget.config.get_action_options(item.name)))
        if hasattr(prepared, 'get_select_values'):
            field['labels'], field['choices'] = prepared.get_select_values()
        if hasattr(item, 'get_input'):
            from pyasm.widget import SelectWdg
            field['input'] = dict(type='select' if isinstance(prepared, SelectWdg) else 'text')
            if isinstance(prepared, SelectWdg) and prepared.empty_option_flag:
                field['input']['empty_label'] = prepared.empty_option_label
        if isinstance(prepared, HiddenWdg):
            field['values'] = prepared.get_values(for_display=True)
            field['input'] = dict(type='hidden')
        if isinstance(item, ColorInputWdg):
            field['input'] = dict(type='color', value=prepared.get_value(for_display=True))
        if isinstance(item, TaskSObjectInputWdg):
            field['input'].update(type='parent', label=item.parent_label, project=item.parent_project,
                                  no_parent_type=item.no_parent_type, read_only=widget.mode != 'insert')
        if isinstance(item, SimpleUploadWdg):
            field['values'] = []
            field['input'] = dict(type='file', context=item.context, column=item.get_option('column') or item.name)
        if isinstance(item, ThumbInputWdg):
            field['values'] = []
            field['input'] = dict(type='thumbnail', read_only=True)
        if isinstance(item, MultiSelectWdg):
            field['input'] = dict(type='multiselect', value=[value for value in field['choices'] if item._is_selected(value, field['values'])])
        if isinstance(item, TimeInputWdg):
            field['input'] = dict(type='time', value=item.input_value,
                                  unchanged_value=field['values'][0] if field['values'] else item.input_value)
        if isinstance(item, (UploadWdg, RichUploadWdg)):
            control = item.context_input
            context = dict(type='select' if isinstance(control, SelectWdg) else 'text', value=control.get_value(for_display=True))
            if isinstance(control, SelectWdg):
                context['labels'], context['choices'] = control.get_select_values()
                if not context['value'] and context['choices']:
                    context['value'] = context['choices'][0]
            field['values'] = []
            field['input'] = dict(type='multi-upload', arbitrary=item.get_option('upload_type') == 'arbitrary',
                                  fields=item.upload_fields, context=context, subcontext=item.subcontext)
            if isinstance(item, RichUploadWdg):
                field['input']['column'] = item.get_option('column') or item.name
        if isinstance(item, CalendarInputWdg):
            from dateutil import parser
            from pyasm.biz import PrefSetting, ProjectSetting
            from pyasm.common import Config, SPTDate
            from pyasm.common.errors import UnsupportedContract
            from pyasm.search import SObject
            column = item.get_option('column') or item.name
            data_type = SearchType.get_column_type(search_type, column)
            if data_type == 'time':
                raise UnsupportedContract('Time-only calendar input is not migrated')
            day = data_type == 'date' or SObject.is_day_column(column)
            timezone = item.get_option('timezone') or PrefSetting.get_value_by_key('timezone') or 'local'
            value = field['values'][0] if field['values'] else ''
            show_time = item.get_option('show_time') in (True, 'true') and not day
            input_value = ''
            unchanged_value = value
            if value:
                date = parser.parse(str(value))
                current = item.get_current_sobject()
                if current and not current.is_insert() and data_type != 'date':
                    unchanged_value = (date if SPTDate.has_timezone(date) else SPTDate.add_gmt_timezone(date)).isoformat()
                    if not day:
                        date = item.get_timezone_value(date)
                input_value = date.strftime('%Y-%m-%dT%H:%M' if show_time else '%Y-%m-%d')
                # Native browser controls accept milliseconds; retain full raw precision for unchanged fields.
                milliseconds = date.microsecond // 1000
                if show_time and (date.second or milliseconds):
                    input_value += date.strftime(':%S')
                    if milliseconds:
                        input_value += ('.%03d' % milliseconds).rstrip('0')
            mode = item.get_option('display_mode') or ProjectSetting.get_value_by_key('calendar_display_mode') or Config.get_value('global_setting', 'calendar_display_mode') or 'browser'
            field['input'] = dict(type='datetime-local' if show_time else 'date', value=input_value,
                                  unchanged_value=unchanged_value, timezone=None if day else timezone, display_mode=mode,
                                  value_suffix='T12:00:00+00:00' if day and data_type != 'date' else '')
        if records:
            column = field['action']['options'].get('column') or item.get_option('column') or item.name
            if SearchType.column_exists(search_type, column):
                values = [record.get_value(column, no_exception=True) for record in records]
                field['mixed'] = any(value != values[0] for value in values[1:])
        fields.append(field)
    result = dict(schema_version=1, project=project, search_type=search_type, view=widget.view,
                search_key=search_key, source_key=source_key, mode=widget.mode, input_prefix=widget.input_prefix,
                element_names=widget.element_names, skipped=widget.skipped_element_names, fields=fields)
    if records:
        result['search_keys'] = [record.get_search_key(use_id=True) for record in records]
    if parent_key is not None:
        result['parent_key'] = parent_key
    if connect_key is not None:
        result['connect_key'] = connect_key
    return result


def describe_view(config):
    elements = []
    previous = Container.get('WidgetConfig:metadata_only')
    try:
        Container.put('WidgetConfig:metadata_only', True)
        for name in config.get_element_names():
            handler = next((value for item in config.get_configs() if (value := item.get_display_handler(name))), '')
            elements.append(dict(name=name, title=config.get_element_title(name),
                attributes=config.get_element_attributes(name),
                display=dict(handler=handler, options=config.get_display_options(name)),
                action=dict(handler=config.get_action_handler(name), options=config.get_action_options(name))))
    finally:
        if previous is None:
            Container.remove('WidgetConfig:metadata_only')
        else:
            Container.put('WidgetConfig:metadata_only', previous)
    return dict(view=config.get_view(), layout=config.get_layout_handler(), attributes=config.get_view_attributes(), elements=elements,
                configured=any(item.has_view(config.get_view()) and getattr(item, 'file_path', None) != 'generated'
                               for item in config.get_configs()))


def describe_composition(config, search_type, path=(), budget=None, identity=''):
    """Resolve declarative TabWdg children; never construct their Python handlers."""
    if budget is None:
        budget = [64]
    key = (search_type, config.get_view(), identity)
    if key in path:
        raise ValueError('Cyclic interface reference: %s / %s' % key[:2])
    if len(path) >= 8 or budget[0] <= 0:
        raise ValueError('Interface composition limit exceeded')
    budget[0] -= 1
    result = describe_view(config)
    from .item_layout import LAYOUT, describe_item_layout
    if result['layout'] == LAYOUT:
        result['item_layout'] = describe_item_layout(result)
        for element in result['item_layout']['elements']:
            if element['kind'] != 'view':
                continue
            view = element['options']['view']
            child = WidgetConfigView.get_by_search_type(search_type, view)
            if not describe_view(child)['configured']:
                raise LookupError('View is not configured: ' + view)
            nested = describe_composition(child, search_type, (*path, key), budget)
            if 'item_layout' not in nested:
                raise ValueError('Reusable item widget requires a SObject layout')
            element['widget_layout'] = nested['item_layout']
        return result
    if result['layout'] != 'tactic.ui.container.TabWdg':
        if result['layout'] in ('tactic.ui.panel.TableLayoutWdg', 'TableWdg', 'TableLayoutWdg'):
            from tactic_stream.server.table_cells import describe_cell
            columns = SearchType.get_column_info(search_type)
            edit = WidgetConfigView.get_by_search_type(search_type, 'edit')
            edit_elements = {item['name']: item for item in describe_view(edit)['elements']}
            edit_definition = WidgetConfigView.get_by_search_type(search_type, 'edit_definition')
            definitions = {item['name']: item for item in describe_view(edit_definition)['elements']}
            for element in result['elements']:
                element['cell'] = describe_cell(element, columns, search_type)
                cell = element['cell']
                declared_target = definitions.get(element['name'],{}).get('action',{}).get('options',{}).get('column')
                name = element['name'] if element['name'] in edit_elements else ''
                editor_view = 'edit'
                if not name and element['name'] in definitions:
                    name, editor_view = element['name'], 'edit_definition'
                elif not name:
                    name = declared_target if declared_target in edit_elements else cell['field'] if cell['field'] in edit_elements else ''
                editor = (edit_elements if editor_view == 'edit' else definitions).get(name, {})
                options = editor.get('display', {}).get('options', {})
                action = editor.get('action', {}).get('options', {})
                target = action.get('column') or options.get('column') or name
                cell['editor'] = name
                cell['editor_view'] = editor_view
                cell['editable'] = bool(name and target in columns and target not in ('id','code','project_code','timestamp','login')
                    and cell['supported'] and cell['kind'] in ('text','boolean','link')
                    and element['attributes'].get('edit') not in (False,'false') and options.get('read_only') not in (True,'true'))
        return result
    path = (*path, key)
    for element in result['elements']:
        options = element['display']['options']
        handler = element['display']['handler']
        if element['action']['handler']:
            continue
        if handler == 'tactic.ui.panel.ViewPanelWdg':
            if set(options) - {'search_type', 'view', 'layout', 'search_limit', 'order_by',
                               'do_initial_search', 'show_refresh', 'show_search_limit'} or not options.get('search_type'):
                continue
            target = SearchType.get(options['search_type'])
            data = SearchType.breakup_search_type(options['search_type'])
            if data.get('project') and data['project'] != Project.get_project_code():
                raise ValueError('Nested interface belongs to another project')
            layout = options.get('layout')
            if not layout or layout == 'default':
                layout = target.get_value('default_layout', no_exception=True) or 'table'
            if layout != 'table':
                continue
            columns = SearchType.get_column_info(target.get_base_key())
            panel = dict(search_limit=50, order_by=[], do_initial_search=True, show_refresh=True, show_search_limit=True)
            if options.get('search_limit'):
                limit = options['search_limit']
                if not isinstance(limit, str) or not limit.isdecimal() or not 1 <= int(limit) <= 500:
                    raise ValueError('Native panel search_limit must be between 1 and 500')
                panel['search_limit'] = int(limit)
            order_by = options.get('order_by') or ''
            if not isinstance(order_by, str):
                raise ValueError('Native panel order_by requires a string')
            for order in order_by.split(','):
                if not order.strip():
                    continue
                parsed = re.fullmatch(r'([A-Za-z_]\w*)(?:\s+(asc|desc))?', order.strip(), re.IGNORECASE)
                if not parsed or parsed[1] not in columns:
                    raise ValueError('Native panel order_by requires a column and optional asc/desc')
                panel['order_by'].append(order.strip())
            for name in ('do_initial_search', 'show_refresh', 'show_search_limit'):
                value = options.get(name, 'true')
                if value not in ('true', 'false', 'hidden') or (value == 'hidden' and name != 'do_initial_search'):
                    raise ValueError('Invalid native panel option: ' + name)
                panel[name] = value == 'true'
            view = options.get('view') or 'table'
            if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
                raise ValueError('Invalid nested view name')
            child = WidgetConfigView.get_by_search_type(target.get_base_key(), view)
            if view != 'table' and not describe_view(child)['configured']:
                raise LookupError('View is not configured: ' + view)
            element['interface'] = dict(search_type=target.get_base_key(), columns=columns, panel=panel,
                                        table=describe_composition(child, target.get_base_key(), path, budget))
        elif handler == 'tactic.ui.container.TabWdg':
            if set(options) - {'view', 'config_xml', 'selected'}:
                continue
            view = options.get('view') or 'tab'
            if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
                raise ValueError('Invalid nested view name')
            xml = options.get('config_xml')
            identity = hashlib.sha256(xml.encode('utf-8')).hexdigest() if xml else ''
            if not xml:
                # Original TabWdg uses category/view, not the current SearchType.
                search = Search('config/widget_config')
                search.add_filter('category', 'TabWdg')
                search.add_filter('view', view)
                record = search.get_sobject()
                if record:
                    xml = record.get_value('config')
            if not xml:
                continue
            child = WidgetConfig.get(view=view, xml=xml)
            if not child.has_view():
                raise ValueError('Tab configuration does not contain its view')
            child = WidgetConfigView('TabWdg', view, [child], layout='tactic.ui.container.TabWdg')
            description = describe_composition(child, 'TabWdg', path, budget, identity)
            description['selected'] = options.get('selected') or ''
            element['interface'] = dict(search_type=search_type, columns={}, table=description)
    return result


def read_interface(search_type, view='table'):
    _require_admin()
    if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
        raise ValueError('Invalid view name')
    project = Project.get()
    SearchType.get(search_type)
    data = SearchType.breakup_search_type(search_type)
    if data.get('project') and data['project'] != project.get_code():
        raise ValueError('Select the target project before reading its interface')
    table = WidgetConfigView.get_by_search_type(search_type, view)
    description = describe_composition(table, SearchType.get(search_type).get_base_key())
    if view != 'table' and not description['configured']:
        raise LookupError('View is not configured: ' + view)
    from tactic_stream.server.api import _internal_widget_configs
    configs = []
    stored = WidgetDbConfig.get_by_search_type('SideBarWdg', 'project_view')
    if stored:
        configs.append(stored)
    configs.extend(_internal_widget_configs(['project_view'], base_only=True))
    stored = WidgetDbConfig.get_by_search_type('SideBarWdg', 'definition')
    if stored:
        configs.append(stored)
    configs.extend(_internal_widget_configs(['definition']))
    navigation = WidgetConfigView('SideBarWdg', 'project_view', configs)
    from pyasm.search import SObject
    base = SearchType.get(search_type).get_base_key()
    columns = SearchType.get_column_info(search_type)
    if base == 'sthpw/transaction_log':
        from .transaction_journal import columns as journal_columns
        columns = journal_columns()
    writable = (base in SObject.SECURITY_TYPES + SObject.BUSINESS_TYPES or not base.startswith(('sthpw/', 'config/'))) and not SearchType.get(search_type).get_record_read_options().get('readonly')
    attributes = description['attributes']
    operations = {name: writable and attributes.get(flag) not in (False, 'false')
                  for name, flag in (('create', 'insert'), ('edit', 'edit'), ('retire', 'retire'), ('delete', 'delete'))}
    operations['retire_column'] = SearchType.get(search_type).get_retire_col()
    operations['retire'] = operations['retire'] and operations['retire_column'] in columns
    # DeleteCmd routes File rows through their owner Snapshot and FileUndo.
    operations['checkin'] = operations['edit'] and base != 'sthpw/file'
    views = Search('config/widget_config')
    views.add_filters('search_type', [base, 'ALL'])
    views.add_order_by('view')
    from .item_layout import EXAMPLE_VIEWS
    custom_views = list(dict.fromkeys([*EXAMPLE_VIEWS] + [item.get_value('view') for item in views.get_sobjects()
        if isinstance(item.get_value('view'), str) and re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', item.get_value('view'))
        and not item.get_value('view').startswith('quick_filters@')
        and item.get_value('view') not in ('definition', 'edit_definition', 'edit', 'insert')]))
    return dict(schema_version=1, project=project.get_code(), search_type=search_type,
                administration=True,
                operations=operations,
                columns=columns, table=description, views=custom_views,
                navigation=describe_view(navigation))
