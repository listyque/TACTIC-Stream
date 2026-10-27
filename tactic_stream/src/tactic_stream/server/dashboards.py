"""Compose native CustomLayout data from typed bricks, without generated code."""
from urllib.parse import urlsplit
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from .interface import _require_table_access, read_interface
from .navigation_links import check_project
from tactic_stream.dashboard_plan import DashboardDocument


def dashboard_layout(document, view, search_key=''):
    document = DashboardDocument.model_validate(document)
    project = Project.get()
    check_project(project.get_code())
    target = Search.get_by_search_key(search_key) if search_key else project
    if target is None:
        raise ValueError('Dashboard target is unavailable')
    budget = [128]
    items_scope = []

    def compile_blocks(blocks, depth=0):
        if depth > 6:
            raise ValueError('Dashboard nesting exceeds six levels')
        nodes=[]
        for block in blocks:
            budget[0]-=1
            if budget[0]<0:
                raise ValueError('Dashboard exceeds 128 bricks')
            if block.kind in ('row','column'):
                if not block.children:
                    raise ValueError('Dashboard groups need child bricks')
                nodes.append(dict(kind='row' if block.kind=='row' else 'group',
                    children=compile_blocks(block.children,depth+1),weight=block.weight))
                continue
            if block.children:
                raise ValueError('Only row/column bricks may contain children')
            if block.kind=='text':
                nodes.append(dict(kind='text',text=block.text or block.title,weight=block.weight))
                continue
            if block.kind=='markdown':
                value=block.text
                if block.source_key or block.field:
                    from tactic.ui.panel.agent_request_cmd import selected_object
                    source=selected_object(block.source_key) if block.source_key else target
                    _require_table_access(source.get_base_search_type())
                    if not block.field or block.field not in SearchType.get_column_info(source.get_base_search_type()):
                        raise ValueError('Markdown requires an existing text field')
                    value=source.get_value(block.field) or ''
                    if not isinstance(value,str):
                        raise ValueError('Markdown source must be text')
                if len(value)>65536:
                    raise ValueError('Markdown brick exceeds 64 KiB; open the document file instead')
                nodes.append(dict(kind='markdown',text=value,weight=block.weight,height=block.height))
                continue
            if block.kind=='link':
                url=urlsplit(block.href)
                if url.scheme not in ('http','https','skey','tactic-search') or not url.netloc or url.username or url.password:
                    raise ValueError('Dashboard links require a safe HTTP or TACTIC address')
                nodes.append(dict(kind='link',text=block.title or block.href,href=block.href,weight=block.weight))
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
                nodes.append(dict(kind='metric',text=block.title or block.search_type,value=search.get_count(),weight=block.weight))
            elif block.kind=='items':
                if items_scope:
                    raise ValueError('A dashboard supports one native item workspace')
                if block.search_type.startswith(('sthpw/','config/')):
                    raise ValueError('Select a project-owned Search Type for the item workspace')
                read_interface(block.search_type,block.view)
                scope=dict(searchType=block.search_type,view=block.view,filters=filters,
                    parentKey=project.get_search_key(),initialLimit=25,
                    orderBy=next((name for name in ('name','code','id') if name in columns),'id'))
                items_scope.append(scope)
                nodes.append(dict(kind='items',text=block.title or info.get_title(),weight=block.weight,
                    height=block.height,items=scope))
            else:
                read_interface(block.search_type,block.view)
                controls=('search','searchLimit','shelf','selection','gear','insert')
                nodes.append(dict(kind='table',text=block.title or block.search_type,weight=block.weight,height=block.height,
                    table=dict(searchType=block.search_type,parentKey=target.get_search_key(),view=block.view,
                        projectScope=not block.search_type.startswith(('sthpw/', 'config/')),filters=filters,embedded=True,initialLimit=25,
                        **{name:block.controls is None or name in block.controls for name in controls})))
        return nodes

    nodes=compile_blocks(document.blocks)
    return dict(title=document.title,text='',layoutNodes=nodes,layoutItems=items_scope[0] if items_scope else None,
        targetSearchKey=target.get_search_key(),layoutView=view,layoutControls=[],layoutLoad=[],layoutForm='',
        layoutUser=Environment.get_user_name(),
        layoutRecord=dict(__search_key__=target.get_search_key(),code=target.get_code(),
            name=target.get_value('name',no_exception=True),title=target.get_value('title',no_exception=True)))
