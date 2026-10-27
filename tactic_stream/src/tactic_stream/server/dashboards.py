"""Compose native CustomLayout data from typed bricks, without generated code."""
from urllib.parse import urlsplit
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from .interface import _require_table_access, read_interface
from .navigation_links import check_project
from tactic_stream.dashboard_plan import DashboardDocument


def dashboard_layout(document, view, search_key='', *, detail_key=''):
    document = DashboardDocument.model_validate(document)
    project = Project.get()
    check_project(project.get_code())
    target = Search.get_by_search_key(search_key) if search_key else project
    if target is None:
        raise ValueError('Dashboard target is unavailable')
    budget = [128]
    items_scope = []
    detail_scope = []
    detail_path = []
    from tactic.ui.panel.agent_request_cmd import selected_object
    detail = selected_object(detail_key) if detail_key else None
    if detail is not None:
        _require_table_access(detail.get_base_search_type())

    def validate_details(blocks, search_type='', depth=0):
        if depth > 6:
            raise ValueError('Dashboard nesting exceeds six levels')
        for block in blocks:
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError('Dashboard exceeds 128 bricks')
            if block.kind in ('details','items'):
                raise ValueError('Details reuse the existing item workspace; nesting another is unsupported')
            if block.kind in ('row','column'):
                scoped_type = block.search_type or search_type
                if scoped_type:
                    info = SearchType.get(scoped_type)
                    if info.get_database() not in ('sthpw',project.get_code()):
                        raise ValueError('Details Search Type belongs to another project')
                    _require_table_access(scoped_type)
                validate_details(block.children,scoped_type,depth+1)
            elif block.children:
                raise ValueError('Only row/column bricks may contain children')
            if block.kind in ('metric','table'):
                info = SearchType.get(block.search_type)
                if info.get_database() not in ('sthpw',project.get_code()):
                    raise ValueError('Dashboard Search Type belongs to another project')
                _require_table_access(block.search_type)
                columns = SearchType.get_column_info(block.search_type)
                if any(condition.column not in columns for condition in block.filters):
                    raise ValueError('Dashboard filters require existing columns')
                if block.kind == 'table':
                    read_interface(block.search_type,block.view)
            if block.source_key:
                source = selected_object(block.source_key)
                _require_table_access(source.get_base_search_type())
                if block.field not in SearchType.get_column_info(source.get_base_search_type()):
                    raise ValueError('Detail source requires an existing field')
            if block.kind == 'link':
                url = urlsplit(block.href)
                if url.scheme not in ('http','https','skey','tactic-search') or not url.netloc or url.username or url.password:
                    raise ValueError('Dashboard links require a safe HTTP or TACTIC address')
            if block.field and not block.source_key:
                if not search_type or block.field not in SearchType.get_column_info(search_type):
                    raise ValueError('Bind detail fields inside a group with an existing Search Type')

    def compile_blocks(blocks, depth=0, context=None, in_details=False, path=()):
        context = context if context is not None else target
        if depth > 6:
            raise ValueError('Dashboard nesting exceeds six levels')
        nodes=[]
        for index, block in enumerate(blocks):
            block_path = path + (index,)

            def emit(node):
                node.update(editorPath=list(block_path), padding=block.padding,
                            margin=block.margin, gap=block.gap)
                if block.height is not None:
                    node['height'] = block.height
                if block.width is not None:
                    node['width'] = str(block.width) + 'px'
                nodes.append(node)

            budget[0]-=1
            if budget[0]<0:
                raise ValueError('Dashboard exceeds 128 bricks')
            if detail_key and not in_details and block.kind not in ('row','column','details'):
                continue
            if block.kind in ('row','column'):
                if block.search_type and not in_details:
                    raise ValueError('Search Type conditions are only supported inside details')
                if block.search_type and block.search_type != context.get_base_search_type():
                    continue
                emit(dict(kind='row' if block.kind=='row' else 'group',
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
            if block.kind=='text':
                value = block.text or block.title
                if block.field:
                    _require_table_access(context.get_base_search_type())
                    if block.field not in SearchType.get_column_info(context.get_base_search_type()):
                        raise ValueError('Text requires an existing field')
                    value = context.get_value(block.field)
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
                    source=selected_object(block.source_key) if block.source_key else context
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
            if block.kind=='link':
                url=urlsplit(block.href)
                if url.scheme not in ('http','https','skey','tactic-search') or not url.netloc or url.username or url.password:
                    raise ValueError('Dashboard links require a safe HTTP or TACTIC address')
                emit(dict(kind='link',text=block.title or block.href,href=block.href,weight=block.weight))
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
            filters=[[condition.column,condition.relation,condition.value] for condition in block.filters]
            if block.kind=='metric':
                search=Search(block.search_type)
                for column,relation,value in filters:
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
        targetSearchKey=target.get_search_key(),layoutView=view,layoutControls=[],layoutLoad=[],layoutForm='',
        layoutUser=Environment.get_user_name(),
        layoutRecord=dict(__search_key__=target.get_search_key(),code=target.get_code(),
            name=target.get_value('name',no_exception=True),title=target.get_value('title',no_exception=True)))
