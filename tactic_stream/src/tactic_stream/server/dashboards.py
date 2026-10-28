"""Compose native CustomLayout data from typed bricks, without generated code."""
from urllib.parse import urlsplit
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from .interface import _require_table_access, read_interface
from .navigation_links import check_project
from tactic_stream.dashboard_plan import DashboardDocument, DashboardPageFilter


def field_kind(column):
    import re
    data_type = column.get('data_type', 'text').lower()
    if 'bool' in data_type:
        return 'boolean'
    if re.search(r'int|numeric|decimal|real|double|float', data_type):
        return 'number'
    if data_type == 'date' or 'timestamp' in data_type:
        return 'date'
    if re.search(r'json|array|blob|bytea', data_type):
        return 'complex'
    return 'text'


def native_condition(condition):
    if condition.value is None:
        if condition.relation not in ('=', '!='):
            raise ValueError('Empty values require Is empty or Is not empty')
        return [condition.column, 'is empty' if condition.relation == '=' else 'is not empty', '']
    if condition.value == '':
        raise ValueError('Enter a filter value or choose Is empty')
    if isinstance(condition.value, str) and (
        condition.value == 'NULL' or Search.is_expr(condition.value)
        or condition.value.startswith('{') and condition.value.endswith('}')
    ):
        raise ValueError('Use literal filter values; native expressions and the NULL keyword are not supported here')
    return [condition.column, condition.relation, condition.value]


def validate_filter_value(condition, column):
    from datetime import datetime
    kind, value = field_kind(column), condition.value
    if value is None:
        native_condition(condition)
        return
    if kind == 'complex':
        raise ValueError('Filters require a scalar field')
    if kind == 'number' and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise ValueError('Enter a valid number')
    if kind == 'boolean' and not isinstance(value, bool):
        raise ValueError('Choose Yes or No')
    if kind in ('date', 'text') and not isinstance(value, str):
        raise ValueError('Enter a text value for this field')
    if kind == 'date':
        try:
            datetime.fromisoformat(value)
        except ValueError:
            raise ValueError('Choose a valid date') from None
    if condition.relation == 'like' and kind != 'text':
        raise ValueError('Text pattern filters require a text field')
    native_condition(condition)


def report_data(block, filters, *, check_only=False):
    from decimal import Decimal
    import math
    from tactic_stream.dashboard_plan import DashboardAggregate
    columns = SearchType.get_column_info(block.search_type)
    groups = [(item.column, item.period) for item in block.group_by]
    if len(set(groups)) != len(groups):
        raise ValueError('Choose distinct report groups')
    for column, _ in groups:
        if column not in columns or field_kind(columns[column]) == 'complex':
            raise ValueError('Report groups require existing scalar fields')
    for column, period in groups:
        if period != 'value' and field_kind(columns[column]) != 'date':
            raise ValueError('Date grouping requires a date or timestamp field')
    measures = block.aggregates or [DashboardAggregate(name='count', title='Count')]
    names = {item.name for item in measures}
    if len(names) != len(measures) or names & {'group_%d' % index for index in range(len(groups))}:
        raise ValueError('Report measure names must be unique')
    if block.measure and block.measure not in {item.name for item in measures}:
        raise ValueError('Choose an existing report measure')
    if block.kind == 'metric' and (groups or len(measures) != 1):
        raise ValueError('A metric requires one aggregate without grouping')
    for item in measures:
        if item.column and item.column not in columns:
            raise ValueError('Choose an existing report field')
        if item.function != 'count' and (not item.column or field_kind(columns[item.column]) != 'number'):
            raise ValueError('This aggregate requires a numeric field')
    if check_only:
        return
    search = Search(block.search_type)
    search.add_op_filters(filters)
    rows = search.get_aggregates(groups, [(item.function, item.column) for item in measures],
                                 limit=block.group_limit, order=block.group_order)
    def scalar(value):
        if isinstance(value, Decimal):
            value = float(value)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Report aggregate is not a finite number')
        return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
    return dict(
        columns=[dict(key='group_%d' % index, title=block.group_by[index].title or columns[column].get('title') or column, kind='group')
                 for index, (column, _) in enumerate(groups)] + [
            dict(key=item.name, title=item.title, kind='measure') for item in measures],
        rows=[{key: scalar(value) for key, value in zip(
            ['group_%d' % index for index in range(len(groups))] + [item.name for item in measures], row
        )} for row in rows[:block.group_limit]],
        measure=block.measure or measures[0].name, truncated=len(rows) > block.group_limit,
    )


def dashboard_sources(
    search_type: str = '', query: str | None = None, record_key: str = '', edit_view: str = 'edit'
) -> dict:
    from .widget_configuration import read_widget_configuration
    from tactic.ui.panel.agent_request_cmd import selected_object

    project = Project.get()
    if not isinstance(search_type, str) or len(search_type) > 256 or '?' in search_type:
        raise ValueError('Select a data source in the current project')
    if not search_type:
        rows = project.get_search_types(
            include_sthpw=True, include_config=True, include_multi_project=True
        )
        return dict(searchTypes=[
            dict(value=row.get_code(), label=row.get_value('title') or row.get_code(),
                 projectOwned=row.get_database() == project.get_code())
            for row in rows if row.get_database() in ('sthpw', project.get_code())
        ])
    info = SearchType.get(search_type)
    if info.get_database() not in ('sthpw', project.get_code()):
        raise ValueError('Dashboard Search Type belongs to another project')
    _require_table_access(search_type)
    configuration = read_widget_configuration(search_type, 'table')
    interface = read_interface(search_type, 'table')
    titles = {
        row['name']: row.get('title') or row['name']
        for row in interface.get('table', {}).get('elements', [])
    }
    columns = SearchType.get_column_info(search_type)
    result = dict(
        searchType=search_type, title=info.get_title(),
        fields=[
            dict(value=name, label=titles.get(name) or column.get('title') or name,
                 dataType=column.get('data_type') or 'text')
            for name, column in columns.items()
        ],
        tableViews=[dict(value=row['view'], label=row['title'])
                    for row in configuration['table_views']],
        itemViews=[dict(value=name, label=name) for name in configuration['layout_views']],
        records=[], more=False,
    )

    from pyasm.widget import WidgetConfigView
    import re
    if not isinstance(edit_view,str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}',edit_view):
        raise ValueError('Invalid view name')
    edit = WidgetConfigView.get_by_search_type(search_type, edit_view, use_cache=False)
    result['editView'] = edit_view
    result['editFields'] = [dict(value=name, label=edit.get_element_attributes(name).get('title') or name) for name in edit.get_element_names()]

    def choice(row):
        label = next((
            str(row.get_value(name, no_exception=True))
            for name in ('name', 'title', 'code', 'login', 'id')
            if row.get_value(name, no_exception=True) not in ('', None)
        ), row.get_search_key())
        code = row.get_code()
        if code and code != label:
            label += ' · ' + str(code)
        return dict(value=row.get_search_key(), label=label)

    if record_key:
        if not isinstance(record_key, str) or len(record_key) > 2048:
            raise ValueError('Choose a source record')
        selected = selected_object(record_key)
        if selected.get_base_search_type() != search_type:
            raise ValueError('The record belongs to another data source')
        result['records'].append(choice(selected))
    if query is not None:
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError('Enter at most 256 characters to find records')
        search = Search(search_type)
        column = next((name for name in ('name', 'title', 'code', 'login', 'id')
                       if name in columns), 'id')
        if query:
            if column == 'id':
                if not query.isdecimal():
                    return result
                search.add_filter(column, int(query))
            else:
                search.add_op('begin')
                for name in ('name', 'title', 'code', 'login'):
                    if name in columns:
                        search.add_filter(name, '%' + query + '%', op='like')
                search.add_op('or')
        search.add_order_by(column)
        search.add_limit(51)
        rows = search.get_sobjects()
        result['more'] = len(rows) > 50
        known = {row['value'] for row in result['records']}
        result['records'].extend(
            choice(row) for row in rows[:50] if row.get_search_key() not in known
        )
    return result


def dashboard_layout(document, view, search_key='', *, detail_key='', filter_values=None):
    document = DashboardDocument.model_validate(document)
    project = Project.get()
    check_project(project.get_code())
    from tactic.ui.panel.agent_request_cmd import selected_object
    target = selected_object(search_key) if search_key else project
    _require_table_access(target.get_base_search_type())
    if target is None:
        raise ValueError('Dashboard target is unavailable')
    definitions = {item.name: item for item in document.filters}
    if len(definitions) != len(document.filters):
        raise ValueError('Page filter names must be unique')
    if filter_values is None:
        filter_values = {}
    if not isinstance(filter_values, dict) or set(filter_values) - definitions.keys():
        raise ValueError('Choose configured page filters')
    page_filters, filter_controls = {}, []
    for name, definition in definitions.items():
        value = filter_values.get(name, {})
        if not isinstance(value, dict) or set(value) - {'enabled', 'value'}:
            raise ValueError('Invalid page filter values')
        item = DashboardPageFilter.model_validate(dict(definition.model_dump(), **value))
        info = SearchType.get(item.search_type)
        if info.get_database() not in ('sthpw', project.get_code()) or '?' in item.search_type:
            raise ValueError('Dashboard Search Type belongs to another project')
        _require_table_access(item.search_type)
        columns = SearchType.get_column_info(item.search_type)
        if item.column not in columns or field_kind(columns[item.column]) == 'complex':
            raise ValueError('Choose an existing source field')
        if item.enabled:
            validate_filter_value(item, columns[item.column])
        page_filters[name] = item
        filter_controls.append(dict(name=name, title=item.title, relation=item.relation,
            value=item.value, enabled=item.enabled, dataType=columns[item.column]['data_type']))
    budget = [128]
    items_scope = []
    detail_scope = []
    detail_path = []
    from tactic.ui.panel.agent_request_cmd import selected_object
    detail = selected_object(detail_key) if detail_key else None
    if detail is not None:
        _require_table_access(detail.get_base_search_type())

    def validate_binding(block, search_type='', in_details=False):
        if block.kind in ('image','form','action'):
            if block.field or block.binding == 'static':
                raise ValueError('Choose an object binding for this widget')
            if block.binding == 'selection' and not in_details:
                raise ValueError('Place selection-bound widgets inside Details')
            if block.binding == 'record' and not block.source_key:
                raise ValueError('Choose a source record')
            if block.binding in ('project','selection') and block.source_key:
                raise ValueError('This binding cannot also reference a fixed record')
            if block.source_key:
                source = selected_object(block.source_key)
                if block.search_type and source.get_base_search_type() != block.search_type:
                    raise ValueError('The record belongs to another data source')
                _require_table_access(source.get_base_search_type())
            return
        if block.kind == 'field' and not block.field:
            raise ValueError('Choose an existing source field')
        if block.kind not in ('text','heading','markdown','field'):
            if block.binding!='auto' or block.field or block.source_key:
                raise ValueError('Field bindings belong to Text or Markdown widgets')
            return
        if block.binding=='static':
            if block.field or block.source_key:
                raise ValueError('Static text cannot also reference a field')
            return
        if block.binding=='selection' and not in_details:
            raise ValueError('Place selection-bound widgets inside Details')
        if block.binding in ('project','selection') and block.source_key:
            raise ValueError('This binding cannot also reference a fixed record')
        if block.binding=='record' and not block.source_key:
            raise ValueError('Choose a source record')
        if block.binding!='auto' or block.source_key or block.field:
            if not block.field:
                raise ValueError('Choose a source field')
            if block.source_key:
                source=selected_object(block.source_key)
                source_type=source.get_base_search_type()
                if block.search_type and block.search_type!=source_type:
                    raise ValueError('The record belongs to another data source')
            elif block.binding=='project':
                source_type=project.get_base_search_type()
            else:
                source_type=block.search_type or search_type
            if not source_type:
                raise ValueError('Choose the selected record type for this field')
            info=SearchType.get(source_type)
            if info.get_database() not in ('sthpw',project.get_code()):
                raise ValueError('Dashboard Search Type belongs to another project')
            _require_table_access(source_type)
            if block.field not in SearchType.get_column_info(source_type):
                raise ValueError('Choose an existing source field')

    def binding_source(block,context):
        if block.source_key:
            return selected_object(block.source_key)
        return project if block.binding=='project' else context

    def filters_for(block):
        result = [native_condition(item) for item in block.filters]
        columns = SearchType.get_column_info(block.search_type)
        links = block.page_filters if block.page_filters is not None else {
            name: item.column for name, item in page_filters.items() if item.search_type == block.search_type
        }
        for name, column in links.items():
            if name not in page_filters or column not in columns:
                raise ValueError('Page filter mapping requires existing filters and fields')
            item = page_filters[name]
            original = SearchType.get_column_info(item.search_type)[item.column]
            if field_kind(columns[column]) != field_kind(original):
                raise ValueError('Mapped page filter fields must have the same data type')
            if item.enabled:
                condition = item.model_copy(update=dict(column=column))
                validate_filter_value(condition, columns[column])
                result.append(native_condition(condition))
        return result

    def validate_details(blocks, search_type='', depth=0):
        if depth > 6:
            raise ValueError('Dashboard nesting exceeds six levels')
        for block in blocks:
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError('Dashboard exceeds 128 bricks')
            if block.kind in ('details','items'):
                raise ValueError('Details reuse the existing item workspace; nesting another is unsupported')
            validate_binding(block,search_type,True)
            if block.kind in ('row','column','grid'):
                scoped_type = block.search_type or search_type
                if scoped_type:
                    info = SearchType.get(scoped_type)
                    if info.get_database() not in ('sthpw',project.get_code()):
                        raise ValueError('Details Search Type belongs to another project')
                    _require_table_access(scoped_type)
                validate_details(block.children,scoped_type,depth+1)
            elif block.children:
                raise ValueError('Only row/column bricks may contain children')
            if block.kind in ('metric','table','chart','summary'):
                info = SearchType.get(block.search_type)
                if info.get_database() not in ('sthpw',project.get_code()):
                    raise ValueError('Dashboard Search Type belongs to another project')
                _require_table_access(block.search_type)
                columns = SearchType.get_column_info(block.search_type)
                if any(condition.column not in columns for condition in block.filters):
                    raise ValueError('Dashboard filters require existing columns')
                filters_for(block)
                if block.kind in ('chart','summary') or block.aggregates or block.group_by:
                    report_data(block, filters_for(block), check_only=True)
                if block.kind == 'table':
                    read_interface(block.search_type,block.view)
            if block.source_key:
                source = selected_object(block.source_key)
                _require_table_access(source.get_base_search_type())
                if block.kind not in ('image','form','action') and block.field not in SearchType.get_column_info(source.get_base_search_type()):
                    raise ValueError('Detail source requires an existing field')
            if block.kind in ('link','button') and block.href:
                url = urlsplit(block.href)
                if url.scheme not in ('http','https','skey','tactic-search') or not url.netloc or url.username or url.password:
                    raise ValueError('Dashboard links require a safe HTTP or TACTIC address')
            if block.kind not in ('image','form','action') and block.field and not block.source_key and block.binding not in ('project','static'):
                if not (block.search_type or search_type) or block.field not in SearchType.get_column_info(block.search_type or search_type):
                    raise ValueError('Bind detail fields inside a group with an existing Search Type')

    def compile_blocks(blocks, depth=0, context=None, in_details=False, path=()):
        context = context if context is not None else target
        if depth > 6:
            raise ValueError('Dashboard nesting exceeds six levels')
        nodes=[]
        for index, block in enumerate(blocks):
            block_path = path + (index,)
            if block.kind not in ('metric','chart','summary') and (block.group_by or block.aggregates or block.measure):
                raise ValueError('Grouping and aggregates belong to report widgets')

            def emit(node):
                node.update(editorPath=list(block_path), padding=block.padding,
                            margin=block.margin, gap=block.gap,
                            offsetX=block.offset_x, offsetY=block.offset_y,
                            appearance=block.appearance.model_dump(), sizing=block.sizing.model_dump(),
                            columns=block.columns, min_cell_width=block.min_cell_width,
                            row_height=block.row_height, columnSpan=block.column_span, rowSpan=block.row_span,
                            collapseWidth=block.collapse_width,
                            textRole=('heading' if block.kind=='heading' else 'body') if block.text_role=='auto' else block.text_role,
                            textAlign=block.text_align, textColor=('outlineVariant' if block.kind=='divider' else 'primaryText') if block.text_color=='auto' else block.text_color,
                            textWeight=block.text_weight,
                            icon=block.icon, iconSize=block.icon_size)
                if block.sizing.width_mode == 'fixed' and block.width is None or block.sizing.height_mode == 'fixed' and block.height is None:
                    raise ValueError('Fixed sizing requires a numeric width or height')
                if block.height is not None:
                    node['height'] = block.height
                if block.width is not None:
                    node['width'] = str(block.width) + 'px'
                nodes.append(node)

            budget[0]-=1
            if budget[0]<0:
                raise ValueError('Dashboard exceeds 128 bricks')
            if detail_key and not in_details and block.kind not in ('row','column','grid','details'):
                continue
            if block.kind not in ('text','heading','markdown','field'):
                validate_binding(block,context.get_base_search_type(),in_details)
            if block.kind in ('row','column','grid'):
                if block.search_type and not in_details:
                    raise ValueError('Search Type conditions are only supported inside details')
                if block.search_type and block.search_type != context.get_base_search_type():
                    continue
                emit(dict(kind='row' if block.kind=='row' else 'grid' if block.kind=='grid' else 'group',
                    children=compile_blocks(block.children,depth+1,context,in_details,block_path),weight=block.weight))
                continue
            if block.kind=='details':
                if in_details or detail_scope:
                    raise ValueError('A dashboard supports one details pane')
                validate_details(block.children,depth=depth+1)
                detail_scope.append(block)
                detail_path.extend(block_path)
                emit(dict(kind='details',text=block.title,weight=block.weight,height=block.height))
                continue
            if block.children:
                raise ValueError('Only row/column bricks may contain children')
            validate_binding(block,context.get_base_search_type(),in_details)
            if (in_details and block.kind in ('text','heading','markdown','field') and block.binding in ('auto','selection')
                    and not block.source_key and block.search_type and block.search_type!=context.get_base_search_type()):
                continue
            if block.fields and block.kind != 'form':
                raise ValueError('Field lists belong to native forms')
            if block.kind in ('field','form','action'):
                from .dashboard_fields import form
                source = binding_source(block,context)
                _require_table_access(source.get_base_search_type())
                from .api import check_record_access
                check_record_access(source.get_base_search_type())
                if block.search_type and source.get_base_search_type() != block.search_type:
                    raise ValueError('The record belongs to another data source')
                target_key = source.get_search_key()
                if block.kind == 'field':
                    if not block.field or block.field not in SearchType.get_column_info(source.get_base_search_type()):
                        raise ValueError('Choose an existing source field')
                    value = source.get_value(block.field,auto_convert=False)
                    from decimal import Decimal
                    if isinstance(value,Decimal): value=float(value)
                    from datetime import date
                    if isinstance(value,date): value=value.isoformat()
                    import math
                    if isinstance(value,float) and not math.isfinite(value):
                        raise ValueError('Record field must be a finite number')
                    if not isinstance(value,(str,int,float,bool,type(None))):
                        raise ValueError('Text source must be a scalar')
                    if block.format == 'progress' and value is not None and (isinstance(value,bool) or not isinstance(value,(int,float))):
                        raise ValueError('Progress requires a numeric field')
                    emit(dict(kind='field',text=block.title,value=value,format=block.format,suffix=block.suffix,weight=block.weight))
                elif block.kind == 'form':
                    prepared = form(block,source)
                    prepared['scope'] = dict(view=view,path=list(block_path),search_key=target.get_search_key(),
                        detail_key=detail.get_search_key() if in_details and detail else '',filter_values=filter_values)
                    emit(dict(kind='form',text=block.title,form=prepared,weight=block.weight))
                else:
                    available=True
                    if block.native_action=='edit':
                        from pyasm.common.errors import SecurityException
                        try: _require_table_access(source.get_base_search_type(),'edit')
                        except SecurityException: available=False
                    emit(dict(kind='action',text=block.title,nativeAction=block.native_action,targetSearchKey=target_key,
                        available=available,process=source.get_value('process',no_exception=True) or '',
                        editView=block.edit_view,buttonStyle=block.button_style,weight=block.weight))
                continue
            if block.kind in ('text','heading'):
                value = block.text or block.title
                if block.field:
                    source=binding_source(block,context)
                    _require_table_access(source.get_base_search_type())
                    if block.field not in SearchType.get_column_info(source.get_base_search_type()):
                        raise ValueError('Text requires an existing field')
                    value = source.get_value(block.field)
                    if not isinstance(value,(str,int,float,bool,type(None))):
                        raise ValueError('Text source must be a scalar')
                    value = str(value) if value is not None else ''
                    if block.title and value:
                        value = block.title + ': ' + value
                if len(value)>65536:
                    raise ValueError('Text brick exceeds 64 KiB')
                emit(dict(kind='text',text=value,weight=block.weight))
                continue
            if block.kind=='markdown':
                value=block.text
                if block.source_key or block.field:
                    source=binding_source(block,context)
                    _require_table_access(source.get_base_search_type())
                    if not block.field or block.field not in SearchType.get_column_info(source.get_base_search_type()):
                        raise ValueError('Markdown requires an existing text field')
                    value=source.get_value(block.field) or ''
                    if not isinstance(value,str):
                        raise ValueError('Markdown source must be text')
                if len(value)>65536:
                    raise ValueError('Markdown brick exceeds 64 KiB; open the document file instead')
                if value:
                    if block.title:
                        value = '## ' + block.title + '\n\n' + value
                    emit(dict(kind='markdown',text=value,weight=block.weight,height=block.height))
                continue
            if block.kind in ('link','button'):
                url=urlsplit(block.href)
                if (block.href or block.kind=='link') and (url.scheme not in ('http','https','skey','tactic-search') or not url.netloc or url.username or url.password):
                    raise ValueError('Dashboard links require a safe HTTP or TACTIC address')
                emit(dict(kind=block.kind,text=block.title or block.href,href=block.href,buttonStyle=block.button_style,weight=block.weight))
                continue
            if block.kind in ('icon','divider','spacer'):
                emit(dict(kind=block.kind,text=block.title,weight=block.weight))
                continue
            if block.kind == 'image':
                from pyasm.widget import ThumbWdg
                from .table_cells import safe_link
                source = binding_source(block,context)
                _require_table_access(source.get_base_search_type())
                thumb = ThumbWdg(latest_icon='true',protocol='http')
                thumb.set_sobjects([source]); thumb.preprocess(); thumb.set_current_index(0)
                preview = thumb.get_cell_value()
                emit(dict(kind='image',text=block.title or source.get_code(),image=safe_link(preview.get('image') or ''),fit=block.image_fit,
                          target=source.get_search_key(),weight=block.weight))
                continue
            if not block.search_type or '?' in block.search_type:
                raise ValueError('Metric/table/items bricks require a base Search Type')
            info=SearchType.get(block.search_type)
            if info.get_database() not in ('sthpw',Project.get_project_code()):
                raise ValueError('Dashboard Search Type belongs to another project')
            _require_table_access(block.search_type)
            columns=set(SearchType.get_column_info(block.search_type))
            if any(condition.column not in columns for condition in block.filters):
                raise ValueError('Dashboard filters require existing columns')
            filters=filters_for(block)
            if block.kind in ('chart','summary') or block.kind=='metric' and (block.aggregates or block.group_by):
                report = report_data(block, filters)
                if block.kind == 'metric':
                    value = report['rows'][0][report['measure']] if report['rows'] else None
                    emit(dict(kind='metric', text=block.title or block.search_type, value=value, weight=block.weight))
                else:
                    emit(dict(kind=block.kind, text=block.title or info.get_title(), report=report, weight=block.weight,
                              height=block.height))
            elif block.kind=='metric':
                search=Search(block.search_type)
                for column,relation,value in filters:
                    if relation in ('is empty','is not empty'):
                        search.add_filter(column,'NULL',op='is' if relation=='is empty' else 'is not',quoted=False)
                    else:
                        search.add_filter(column,value,op=relation)
                emit(dict(kind='metric',text=block.title or block.search_type,value=search.get_count(),weight=block.weight))
            elif block.kind=='items':
                if in_details:
                    raise ValueError('Use the existing item workspace outside the details pane')
                if items_scope:
                    raise ValueError('A dashboard supports one native item workspace')
                if block.search_type.startswith(('sthpw/','config/')):
                    raise ValueError('Select a project-owned Search Type for the item workspace')
                read_interface(block.search_type,block.view)
                scope=dict(searchType=block.search_type,view=block.view,filters=filters,
                    parentKey=project.get_search_key(),initialLimit=25,
                    orderBy=next((name for name in ('name','code','id') if name in columns),'id'))
                items_scope.append(scope)
                emit(dict(kind='items',text=block.title or info.get_title(),weight=block.weight,
                    height=block.height,items=scope))
            else:
                read_interface(block.search_type,block.view)
                controls=('search','searchLimit','shelf','selection','gear','insert')
                emit(dict(kind='table',text=block.title or block.search_type,weight=block.weight,height=block.height,
                    table=dict(searchType=block.search_type,parentKey=context.get_search_key(),view=block.view,
                        projectScope=not block.search_type.startswith(('sthpw/', 'config/')),filters=filters,embedded=True,initialLimit=25,
                        **{name:block.controls is None or name in block.controls for name in controls})))
        return nodes

    nodes=compile_blocks(document.blocks)
    if detail_key:
        if not detail_scope:
            raise ValueError('This dashboard has no details pane')
        budget[0] = 128
        details=compile_blocks(detail_scope[0].children,1,detail,True,tuple(detail_path))
        return dict(layoutNodes=details,targetSearchKey=detail.get_search_key(),
            title=detail.get_value('name',no_exception=True) or detail.get_value('title',no_exception=True) or detail.get_code())
    if detail_scope and not items_scope:
        raise ValueError('A details pane requires the existing item workspace')
    return dict(title=document.title,text='',layoutNodes=nodes,layoutItems=items_scope[0] if items_scope else None,layoutHasDetails=bool(detail_scope),
        layoutFilters=filter_controls, layoutFilterValues={name:dict(enabled=item.enabled,value=item.value) for name,item in page_filters.items()},
        targetSearchKey=target.get_search_key(),layoutView=view,layoutControls=[],layoutLoad=[],layoutForm='',
        layoutUser=Environment.get_user_name(),
        layoutRecord=dict(__search_key__=target.get_search_key(),code=target.get_code(),
            name=target.get_value('name',no_exception=True),title=target.get_value('title',no_exception=True)))
