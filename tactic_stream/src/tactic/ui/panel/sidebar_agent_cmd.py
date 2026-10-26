"""Agent adapter for the existing SidebarDraft/editor; no replacement navigation model."""
import json
from uuid import UUID
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search,SearchType
from pyasm.security.security import _require_admin
from tactic_stream.sidebar_plan import SidebarDocument
from tactic_stream.server.sidebar_editor import SidebarDraft,read_sidebar,save_sidebar,_element_parent,_element_container
from tactic_stream.server.widget_configuration import WidgetConfigConflict
from .page_cmd import digest


def summary(draft,revision):
    fields=('key','name','title','entryType','searchType','icon','color','isVisible','depth','targetView')
    return dict(revision=revision,source=draft._sidebar_source,
        entries=[{key:row.get(key) for key in fields} for row in draft.entries])


class SidebarAgentCmd(Command):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code')!=Project.get_project_code():
            raise ValueError('Sidebar project mismatch')
        action=self.kwargs.get('action')
        if action not in ('read','preview','apply','operation'):
            raise ValueError('Unknown sidebar agent operation')
        sql=Search('config/widget_config').get_sql()
        if action=='apply':
            sql.get_database_impl().lock_collection_table(sql,SearchType.get('config/widget_config').get_table())
        operation=self.kwargs.get('operation_id','')
        fingerprint=digest(['sidebar',self.kwargs.get('document'),self.kwargs.get('expected_revision')])
        if action in ('apply','operation'):
            if not isinstance(operation,str) or str(UUID(operation))!=operation:
                raise ValueError('A canonical UUID operation_id is required')
            key=digest([Environment.get_user_name(),Project.get_project_code(),operation])
            receipt=sql.do_query('SELECT request_hash,result FROM spt_page_operation WHERE code='+sql.quote(key))
            if receipt:
                result=json.loads(receipt[0][1])
                if result.get('kind')!='sidebar' or action=='apply' and receipt[0][0]!=fingerprint:
                    raise ValueError('Operation ID belongs to another request')
                return result
            if action=='operation':
                return dict(status='not_found',operation_id=operation)
        state=read_sidebar()
        document=SidebarDocument.model_validate(self.kwargs.get('document') or dict(source=self.kwargs.get('source','handler')))
        groups=[row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
        draft=SidebarDraft(state['documents'],groups,Project.get_project_code(),document.source)
        if action=='read':
            return summary(draft,state['revision'])
        if self.kwargs.get('expected_revision')!=state['revision']:
            raise WidgetConfigConflict('Sidebar changed. Reload before saving.')
        if not (document.groups or document.updates or document.hidden):
            raise ValueError('Provide sidebar groups, updates or hidden items')
        original=list(zip(draft.entries,draft._flat_refs))

        def reference(identity):
            found=[ref for row,ref in original if row['key']==identity]
            if not found:found=[ref for row,ref in original if row['name']==identity]
            if len(found)!=1:
                raise ValueError('Choose one sidebar item key from read: '+identity)
            return found[0]

        def select(ref):
            draft._selected_row=next(index for index,value in enumerate(draft._flat_refs) if value[1] is ref[1] and value[2] is ref[2])

        for update in document.updates:
            ref=reference(update.item);select(ref)
            for field,value in update.model_dump(exclude_none=True).items():
                if field!='item':draft.update_selected('isVisible' if field=='visible' else field,value)
        for identity in document.hidden:
            select(reference(identity));draft.update_selected('isVisible',False)
        moved=set()
        for group in document.groups:
            existing=[index for index,row in enumerate(draft.entries) if row['name']==group.name]
            if existing:
                if len(existing)!=1 or draft.entries[existing[0]]['entryType']!='section':
                    raise ValueError('Sidebar group name belongs to another item')
                draft._selected_row=existing[0]
            else:
                draft.check_name(group.name,None);draft._selected_row=-1;draft.add_entry('section')
                draft.update_selected('name',group.name)
            for field,value in dict(title=group.title,icon=group.icon,color=group.color).items():
                if value is not None:draft.update_selected(field,value)
            row=draft.entries[draft._selected_row]
            target=_element_container(draft._documents[row['targetView']])
            for identity in group.items:
                owner,selector,element=reference(identity)
                display=element.find('./display')
                if selector is None or id(selector) in moved or display is not None and display.get('class')=='SideBarSectionLinkWdg':
                    raise ValueError('Group each existing leaf item at most once')
                moved.add(id(selector))
                parent=_element_parent(draft._documents[owner],selector)
                if parent is None:raise ValueError('Sidebar item no longer exists')
                parent.remove(selector);target.append(selector)
            draft._rebuild_entries()
        if action=='preview':
            return dict(summary(draft,state['revision']),applied=False)
        saved=save_sidebar(draft,state['revision'])
        result=dict(summary(draft,saved['revision']),kind='sidebar',status='applied',operation_id=operation)
        marker=sql.get_database_impl().get_parameter()
        sql._do_update('INSERT INTO spt_page_operation (code,request_hash,result) VALUES ('+', '.join([marker]*3)+')',
            parameters=[key,fingerprint,json.dumps(result)])
        self.add_description('Update project sidebar')
        return result
