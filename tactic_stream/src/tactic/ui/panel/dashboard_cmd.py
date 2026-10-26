"""Native, revision-checked dashboard authoring with durable Page operation receipts."""
import json
from uuid import UUID
from xml.etree import ElementTree as ET
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.dashboard_plan import DashboardDocument
from tactic_stream.server.dashboards import dashboard_layout
from tactic_stream.server.widget_configuration import WidgetConfigConflict
from tactic_stream.server.sidebar_editor import SidebarDraft, read_sidebar, save_sidebar
from .page_cmd import digest, page_state


def dashboard_state():
    state=page_state('sthpw/project')
    urls=[row.get_data() for row in Search('config/url').get_sobjects()]
    state['revision']=digest([state['revision'],urls])
    state['bricks']=['row','column','text','markdown','metric','table','tree','link']
    state['dashboards']=[dict(view=row.get_value('view'),source_id=row.get_id())
        for row in Search('config/widget_config').get_sobjects()
        if (row.get_value('view') or '').startswith('dashboard.') and '<dashboard>' in (row.get_value('config') or '')]
    return state


class DashboardCmd(Command):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code')!=Project.get_project_code():
            raise ValueError('Dashboard project mismatch')
        action=self.kwargs.get('action')
        if action not in ('read','preview','apply','operation','tree'):
            raise ValueError('Unknown dashboard operation')
        if action=='tree':
            from tactic_stream.server.dashboard_tree import read_tree
            return read_tree(self.kwargs.get('tree'),self.kwargs.get('branch_path'),
                self.kwargs.get('parent_key',''),self.kwargs.get('offset',0),self.kwargs.get('limit',50))
        sql=Search('config/widget_config').get_sql()
        if action=='apply':
            sql.get_database_impl().lock_collection_table(sql,SearchType.get('config/widget_config').get_table())
        operation=self.kwargs.get('operation_id','')
        fingerprint=digest(['dashboard',self.kwargs.get('document'),self.kwargs.get('expected_revision')])
        if action in ('apply','operation'):
            if not isinstance(operation,str) or str(UUID(operation))!=operation:
                raise ValueError('A canonical UUID operation_id is required')
            key=digest([Environment.get_user_name(),Project.get_project_code(),operation])
            receipt=sql.do_query('SELECT request_hash,result FROM spt_page_operation WHERE code='+sql.quote(key))
            if receipt:
                result=json.loads(receipt[0][1])
                if result.get('kind')!='dashboard' or action=='apply' and receipt[0][0]!=fingerprint:
                    raise ValueError('Operation ID belongs to another request')
                return result
            if action=='operation':
                return dict(status='not_found',operation_id=operation)
        state=dashboard_state()
        if action=='read':
            name=self.kwargs.get('name','')
            if not isinstance(name,str) or len(name)>48:
                raise ValueError('Choose a dashboard name')
            if name:
                query=Search('config/widget_config');query.add_filter('view','dashboard.'+name)
                rows=query.get_sobjects()
                if len(rows)!=1:
                    raise ValueError('Choose an existing dashboard')
                source=ET.fromstring(rows[0].get_value('config')).findtext('.//dashboard')
                if not source:
                    raise ValueError('Choose an existing dashboard')
                state['document']=DashboardDocument.model_validate_json(source).model_dump(mode='json')
            return state
        if self.kwargs.get('expected_revision')!=state['revision']:
            raise WidgetConfigConflict('Dashboard dependencies changed. Reload before saving.')
        document=DashboardDocument.model_validate(self.kwargs.get('document')).model_dump(mode='json')
        view='dashboard.'+document['name']
        path='/dashboard/'+document['name']
        model=dashboard_layout(document,view)
        search=Search('config/widget_config');search.add_filter('view',view)
        sources=search.get_sobjects()
        if len(sources)>1 or sources and '<dashboard>' not in (sources[0].get_value('config') or ''):
            raise ValueError('Dashboard view belongs to another configuration')
        query=Search('config/url');query.add_filter('url',path)
        urls=query.get_sobjects()
        if len(urls)>1 or urls and '<view>'+view+'</view>' not in (urls[0].get_value('widget') or ''):
            raise ValueError('Dashboard URL belongs to another configuration')
        if action=='preview':
            return dict(kind='dashboard',document=document,model=model,view=view,path=path,revision=state['revision'],applied=False)
        root=ET.Element('config');definition=ET.SubElement(root,'view',name=view)
        ET.SubElement(definition,'dashboard').text=json.dumps(document,ensure_ascii=False)
        record=sources[0] if sources else SearchType.create('config/widget_config')
        for name,value in dict(search_type='CustomLayoutWdg',category='CustomLayoutWdg',view=view,
            config=ET.tostring(root,encoding='unicode')).items():
            record.set_value(name,value)
        record.commit()
        url=urls[0] if urls else SearchType.create('config/url')
        url.set_value('url',path);url.set_value('description',document['title'])
        url.set_value('widget',"<element><display class='tactic.ui.panel.CustomLayoutWdg'><view>"+view+'</view></display></element>')
        url.commit()
        sidebar=read_sidebar()
        groups=[row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
        source='handler' if state['navigation']['view']=='tactic_handler' else 'tactic'
        draft=SidebarDraft(sidebar['documents'],groups,Project.get_project_code(),source)
        if not sources:
            draft.check_name('dashboard_'+document['name'],None)
            draft._selected_row=-1
            draft.add_entry('link')
            for name,value in dict(name='dashboard_'+document['name'],title=document['title'],
                searchType='sthpw/project',widgetType='custom_layout',displayView=view,resultViewMode='table').items():
                draft.update_selected(name,value)
        else:
            rows=[index for index,row in enumerate(draft.entries) if row.get('name')=='dashboard_'+document['name']]
            if len(rows)!=1:
                raise ValueError('Dashboard navigation changed; inspect it in Sidebar Editor')
            draft._selected_row=rows[0]
            draft.update_selected('title',document['title'])
        save_sidebar(draft,sidebar['revision'])
        result=dict(kind='dashboard',status='applied',operation_id=operation,view=view,path=path,
            project=Project.get_project_code(),title=document['title'],model=model,base_revision=state['revision'])
        marker=sql.get_database_impl().get_parameter()
        sql._do_update('INSERT INTO spt_page_operation (code,request_hash,result) VALUES ('+', '.join([marker]*3)+')',
            parameters=[key,fingerprint,json.dumps(result)])
        self.add_description('Save dashboard ['+document['name']+']')
        return result
