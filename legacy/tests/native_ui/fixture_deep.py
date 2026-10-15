"""TEST ONLY: original XML configuration + synthetic mutable UI contracts.
Does not replace TACTIC or establish live PostgreSQL/workflow compatibility.
"""
import copy
import json
import tempfile
from pathlib import Path
from fixture_backend import FixtureBackend as Base
from tactic.core.config_model import ConfigModel, ConfigSource, parse_xml, xml_text, view_node
from tactic.core.graph_model import graph_spec, apply_graph_edits, PROCESS_TYPES, normalize_workflow_settings
from tactic.core.view_edits import patch_view
from tactic.ui_api.contracts import ApiError, revision, clean_values
from tactic.ui_api.file_payload import FilePayload

class FixtureBackend(Base):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.values = {}; self.notes_data = {}; self.view_overrides = {}; self.saved_targets = {}
        self.graph_settings = {}; self.rules = '<rules custom="keep"><!-- preserve --><rule group="search_type" key="*" access="allow"/></rules>'
        self.fixture_file = Path(tempfile.mkdtemp(prefix='tactic-ui-test-')) / 'fixture.txt'
        self.fixture_file.write_text('TACTIC native UI 0.3 test file\n', encoding='utf-8')
        self.new_projects = []
        self.user_values = [{'key':'sthpw/login?code=fixture','values':{'login':'fixture','display_name':'Fixture user','email':'fixture@example.invalid'}}, {'key':'sthpw/login?code=second','values':{'login':'second','display_name':'Second fixture','email':''}}]
    def projects(self): return super().projects() + self.new_projects
    def _tree(self):
        tree, targets = super()._tree()
        if 'my_view_fixture' in self.overrides:
            from tactic.core.config_model import SidebarProjection
            p = SidebarProjection(self._loader, lambda n:True, self.state.get(), 'fixture')
            tree += p.build(['my_view_fixture']); targets.update(p.targets)
        return tree, targets
    def view(self, stype, view, options=None):
        spec = super().view(stype, view, options)
        # The source task configuration defines these fields. Synthetic values
        # exercise the native editor, not a replacement application data model.
        if stype == 'sthpw/task':
            keep = ['code','description','status','assigned','bid_start_date','bid_end_date']
            spec['fields'] = [{'name':n,'label':n,'storage':True,'supported':True,'read_only':n=='code','kind':'date' if n.endswith('_date') else 'text','options':[], 'reason':'','handler':'fixture'} for n in keep]
            spec['capabilities'] = {'create':False,'update':True,'retire':False}
        key=(stype,view)
        if key in self.view_overrides:
            model=ConfigModel(view,[ConfigSource(self.view_overrides[key],view,'TEST widget_config')])
            existing={f['name']:f for f in spec['fields']}
            spec['fields']=[{**existing.get(el['name'],{'name':el['name'],'storage':True,'kind':'text','supported':True,'read_only':False,'options':[],'reason':'','handler':'fixture'}),'label':el['title'],'hidden':el['attributes'].get('is_visible')=='false'} for el in model.elements()]
        spec['views'] = list(dict.fromkeys([view,'table','edit']))
        return spec
    def open_target(self,key):
        if '/~related/' in key:
            return {'id':key,'kind':'table','name':'related','title':'Related tasks · TEST','search_type':'sthpw/task','view':'table','options':{},'attributes':{},'spec':self.view('sthpw/task','table')}
        return super().open_target(key)
    def _row(self, stype, spec, i):
        key=stype+'?code=FIXTURE'+str(i)
        values={f['name']:('fixture' if i==0 else f'{f["label"]} {i+1}') for f in spec['fields']}
        for field in spec['fields']:
            n=field['name']
            if n.endswith('_date'): values[n]='2026-09-%02d 12:00:00' % (5+i+(3 if 'end' in n else 0))
            if n=='status': values[n]=['In Progress','Complete'][i%2]
        values.update(self.values.get(key,{}))
        return {'key':key,'values':values,'revision':revision(values)}
    def query(self,stype,spec,q):
        rows=[self._row(stype,spec,i) for i in range(12)]
        for f in q['filters']:
            if f['op']=='contains': rows=[r for r in rows if str(f['value']).lower() in str(r['values'].get(f['field'],'')).lower()]
            if f['op']=='eq': rows=[r for r in rows if r['values'].get(f['field'])==f['value']]
        n=len(rows); rows=rows[q['offset']:q['offset']+q['limit']]
        return {'items':rows,'total':n,'offset':q['offset'],'limit':q['limit'],'has_more':q['offset']+len(rows)<n}
    def record(self,stype,key,spec):
        i=int(key.split('FIXTURE')[-1]); return self._row(stype,spec,i)
    def form(self,stype,key=None):
        spec=self.view(stype,'table');return {'spec':spec,'record':self.record(stype,key,spec) if key else None}
    def update(self,stype,key,values,expected,spec):
        old=self.record(stype,key,spec)
        if old['revision']!=expected: raise ApiError(409,'conflict','Запись изменена')
        self.values.setdefault(key,{}).update(values)
        return self.record(stype,key,spec)
    def snapshots(self,stype,key):
        return {'items':[{'key':'sthpw/snapshot?code=TEST','code':'TEST','context':'publish','version':1,'timestamp':'2026-09-30 12:00:00','login':'fixture','description':'Test fixture only','files':[{'code':'TESTFILE','name':'fixture.txt','size':self.fixture_file.stat().st_size,'type':'main','mime':'text/plain','preview':False}]}],'can_upload':False,'notice':'TEST FIXTURE: not a production repository'}
    def _view_model(self,stype,view):
        text=self.view_overrides.get((stype,view))
        if text is None:
            import xml.etree.ElementTree as ET
            root=ET.Element('config'); node=ET.SubElement(root,view)
            for f in self.view(stype,view)['fields']: ET.SubElement(node,'element',name=f['name'],title=f['label'])
            text=xml_text(root)
        return ConfigModel(view,[ConfigSource(text,view,'TEST widget_config')]),text
    def config_operation(self,method,path,data):
        if path=='/graph':
            kind=data['kind']
            if not data.get('key'):
                if method=='POST': return {'created':True,'key':'sthpw/pipeline?code=FIXTURE'}
                return {'items':[{'key':'sthpw/'+kind+'?code=FIXTURE','code':'FIXTURE','name':'TEST '+kind}], 'can_create':kind=='pipeline','node_types':list(PROCESS_TYPES)}
            raw=self.pipeline if kind=='pipeline' else self.schema
            current=revision({'xml':raw,'settings':self.graph_settings if kind=='pipeline' else {}})
            if method=='PATCH':
                if data['revision']!=current: raise ApiError(409,'conflict','Граф изменён')
                result=apply_graph_edits(raw,kind,data.get('operations',[]))
                if kind=='pipeline':
                    self.pipeline=result['xml']
                    for k,v in data.get('settings',{}).items(): self.graph_settings.setdefault(k,{'workflow':{}})['workflow'].update(normalize_workflow_settings(v))
                else: self.schema=result['xml']
                return {'saved':True,'notice':'TEST: graph XML stored in memory'}
            return {'key':data['key'],'code':'FIXTURE','xml':raw,'revision':current,'graph':graph_spec(raw,kind),'can_edit':True,'can_save_positions':True,'node_types':list(PROCESS_TYPES),'settings':self.graph_settings,'search_types':[{'code':'fixture/item','name':'Fixture Item'},{'code':'sthpw/task','name':'Tasks'},{'code':'sthpw/note','name':'Notes'}]}
        if path=='/view-config':
            stype,view=data['search_type'],data['view'];model,raw=self._view_model(stype,view)
            if method=='PATCH':
                if model.fingerprint()!=data['revision']:raise ApiError(409,'conflict','View изменён')
                self.view_overrides[(stype,view)]=patch_view(raw,view,data['operations']);return {'saved':True}
            return {'search_type':stype,'view':view,'elements':model.elements(),'layers':[{'origin':'TEST config','view':view,'xml':raw}],'revision':model.fingerprint(),'can_write':True,'columns':{f['name']:{} for f in self.view(stype,view)['fields']},'views':['table','edit']}
        if path=='/saved-view':
            import xml.etree.ElementTree as ET
            view='my_view_fixture';root=parse_xml(self.overrides.get(view,'<config><my_view_fixture/></config>'));v=view_node(root,view);e=ET.SubElement(v,'element',name='saved_'+str(len(list(v))),title=data['title']);d=ET.SubElement(e,'display',{'class':'tactic.ui.panel.ViewPanelWdg'})
            for k,value in [('search_type',self.open_target(data['target'])['search_type']),('view',self.open_target(data['target'])['view'])]:ET.SubElement(d,k).text=value
            self.overrides[view]=xml_text(root);return {'saved':True}
        if path=='/relations': return {'items':[{'search_type':'sthpw/task','count':12,'relationship':'search_type','target':data['target']+'/~related/TEST'}]}
        if path=='/notes':
            notes=self.notes_data.setdefault(data['key'],[])
            if method=='POST': notes.insert(0,{'key':'sthpw/note?code=TEST'+str(len(notes)),'login':'fixture','timestamp':'2026-09-30 12:00:00','process':data['process'],'note':data['note'],'access':'public'});return {'created':True}
            return {'items':notes,'can_write':True}
        if path=='/file':
            if data.get('snapshot')!='sthpw/snapshot?code=TEST' or data.get('file')!='TESTFILE':raise ApiError(404,'file','No such test version')
            return FilePayload(str(self.fixture_file),'fixture.txt','text/plain',False)
        if path=='/bulk-records':
            target=self.open_target(data['target']);stype=target['search_type'];spec=target['spec']
            for item in data['records']:
                if self.record(stype,item['key'],spec)['revision']!=item['revision']:raise ApiError(409,'conflict','Bulk conflict')
            for item in data['records']: self.update(stype,item['key'],clean_values(item['values'],spec['fields']),item['revision'],spec)
            return {'saved':True,'count':len(data['records'])}
        if path=='/users':
            fields=[{'name':n,'label':n,'kind':'text'} for n in ['login','display_name','email']]
            if method=='GET': return {'items':[{**r,'revision':revision(r['values'])} for r in self.user_values],'fields':fields,'edit_fields':[{'name':n,'label':n} for n in ['display_name','email']],'can_write':True}
            if method=='POST':self.user_values.append({'key':'sthpw/login?code='+data['login'],'values':{'login':data['login'],**data.get('values',{})}});return {'created':True}
            for r in self.user_values:
                if r['key']==data['key']:
                    if revision(r['values'])!=data['revision']:raise ApiError(409,'conflict','User conflict')
                    r['values'].update(data['values']);return {'saved':True}
            raise ApiError(404,'user','No such test user')
        if path=='/security':
            if not data.get('key'):return {'items':[{'key':'sthpw/login_group?code=fixture','name':'fixture','description':'TEST'}],'can_write':True}
            if method=='PATCH':
                if data['revision']!=revision(self.rules):raise ApiError(409,'conflict','Rules conflict')
                parse_xml(data['xml']);self.rules=data['xml'];return {'saved':True,'notice':'TEST rules saved'}
            return {'key':data['key'],'name':'fixture','xml':self.rules,'revision':revision(self.rules),'can_write':True}
        if path=='/project-create':
            if method=='POST':self.new_projects.append({'code':data['code'],'name':data['title']});return {'created':True,'notice':'TEST: in-memory project; no real database created'}
            return {'types':[{'code':'simple','title':'Simple'}],'can_write':True}
        if path=='/system':return {'version':'5.0.0.a02','native_ui':'0.3','database':'TEST ONLY','project_count':len(self.projects())}
        return super().config_operation(method,path,data)
