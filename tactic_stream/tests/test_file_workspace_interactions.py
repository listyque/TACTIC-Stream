"""Basic file interaction keeps selection identity, native rights and rollback."""
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import FileProjectRecord
from pyasm.common.errors import SecurityException
from test_file_project import FileProjectFixture
import test_file_project_resilience as resilience

sys.path.insert(0, 'D:/grav/Tactic Stream/TH')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from thlib.environment import env_inst, env_mode
from thlib.ui.file_workspace import FileWorkspaceController, initial_state
from thlib.ui.file_workspace_interaction import file_identity


class Application(QObject):
    project_changed = Signal(str, str)
    server_state_changed = Signal()
    signing_out = Signal()
    project_state_changed = Signal()
    current_project_code = 'files'


class FileWorkspaceInteractionTest(FileProjectFixture, unittest.TestCase):
    client = resilience.FileProjectResilience.client
    writer = resilience.FileProjectResilience.writer

    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_whole_change_selection_ignores_visible_filters_and_moves_every_file(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from test_file_transfer import FileTransferTest
        source=self.change();target=self.change();blob=self.upload(source,b'fresh move data')
        for index in range(2):
            self.call('edit',change=source,edit_revision=index,chunk='move'+str(index),operations=[
                {'path':'folder/%04d.txt'%i,'blob':blob} for i in range(index*1000,min(1005,(index+1)*1000))])
        client=FileTransferClient('http://unused','unused','files',rpc=self.call)
        state=initial_state();state.update(workspace='work',stream='main',change=self.call('status',change=source),
            view='local',prefix='unrelated/',name_filter='nothing',status_filter='Missing')
        FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','select_query',{'whole_change':True},threading.Event())
        self.assertEqual(state['selection_query']['files'],1005)
        self.assertEqual(state['selection_ids'],[])
        with FileTransferTest.http(self,worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','bulk_target',
                {'operation':'move_files','target':target},threading.Event())
        self.assertEqual(self.call('status',change=source)['files'],0)
        self.assertEqual(self.call('status',change=target)['files'],1005)
        self.call('delete_change',change=source,edit_revision=self.call('status',change=source)['edit_revision'],request_id='delete-after-move')
        self.assertEqual(self.call('status',change=target)['files'],1005)

    def test_depot_write_hint_uses_native_security_and_never_grants_permission(self):
        artist=self.writer()
        pending=self.client(artist,'create_change',workspace='artist')
        self.assertTrue(self.client(artist,'streams')['items'][0]['writable'])
        self.api.dispatch('update',({'ticket':self.token,'project':'admin'},'sthpw/login_group?code=artists',
            {'access_rules':'<rules><rule group="project" code="files" access="allow"/><rule group="file_depot" code="main" project="files" access="view"/></rules>'}))
        self.assertFalse(self.client(artist,'streams')['items'][0]['writable'])
        self.assertFalse(self.client(artist,'stream_status',stream='main')['writable'])
        self.assertFalse(self.client(artist,'status',change=pending['code'])['depot_writable'])
        self.assertFalse(self.client(artist,'inspect_change',change=pending['code'])['depot_writable'])
        self.assertFalse(self.client(artist,'changes')['items'][0]['depot_writable'])
        self.assertFalse(self.client(artist,'change_files',change=pending['code'])['info']['depot_writable'])
        self.assertFalse(self.client(artist,'file_states',workspace='artist',paths=[{'stream':'main','path':'untracked.txt'}])['items'][0]['depot_writable'])
        with self.assertRaises(SecurityException):self.client(artist,'create_change',workspace='artist')
        self.assertTrue(self.call('stream_status',stream='main')['writable'])

    def test_changelist_link_navigation_preserves_native_shelf_read_rights(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        source=self.change();blob=self.upload(source,b'shared shelf')
        self.call('edit',change=source,edit_revision=0,chunk='shelf',operations=[{'path':'shared.txt','blob':blob}])
        shelf=self.call('shelve',change=source,edit_revision=1,request_id='shared')
        artist=self.writer()
        client=FileTransferClient('http://unused','unused','files',rpc=lambda action,**kwargs:self.client(artist,action,**kwargs))
        state=initial_state();state.update(workspace='artist',stream='main')
        for reference in ('#'+str(shelf['number']),'http://unused/projects/files/?changelist='+shelf['code']):
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','goto_change',{'change':reference},threading.Event())
            self.assertEqual(state['change']['code'],shelf['code'])
            self.assertEqual(state['rows'][0]['path'],'shared.txt')
        with self.assertRaisesRegex(ValueError,'current project'):
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','goto_change',{'change':'http://unused/projects/private/?changelist='+shelf['code']},threading.Event())
        with self.assertRaises(SecurityException):
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','goto_change',{'change':'http://unused/projects/files/?changelist='+source},threading.Event())

    def test_file_checkbox_starts_file_selection_without_the_changelist_header(self):
        with patch.object(env_inst,'projects',{}),patch.object(env_mode,'current_path',self.temp.name):
            application=Application();controller=FileWorkspaceController(application)
            change={'kind':'change','id':'one','code':'one','description':''}
            first={'kind':'file','id':'one/a.txt','path':'a.txt','parent':'one'}
            second={'kind':'file','id':'one/b.txt','path':'b.txt','parent':'one'}
            controller._data.update(change=change,changes=[change],change_tree=[change,first,second])
            controller.select_row('changes','one',0)
            controller.select_file_row('changes','one/a.txt',True)
            self.assertEqual(controller.data['selection_ids'],['one/a.txt'])
            controller.select_file_row('changes','one/b.txt',True)
            self.assertEqual(controller.data['selected'],['a.txt','b.txt'])
            controller.select_file_row('changes','one/a.txt',False)
            self.assertEqual(controller.data['selected'],['b.txt'])
            controller.deleteLater();application.deleteLater()

    def test_ctrl_shift_menu_and_scope_identity(self):
        with patch.object(env_inst, 'projects', {}), patch.object(env_mode, 'current_path', self.temp.name):
            application = Application()
            controller = FileWorkspaceController(application)
            controller._data.update(workspace='work', stream='main', view='depot',
                rows=[{'path':str(index)+'.txt'} for index in range(5)])
            ids = [file_identity(row, controller.data) for row in controller.data['rows']]
            controller.select_row('files', ids[1], 0)
            controller.select_row('files', ids[3], 0x04000000)
            self.assertEqual(controller.data['selected'], ['1.txt', '3.txt'])
            controller.select_row('files', ids[3], 0, True)
            self.assertEqual(controller.data['selection_ids'], [ids[1], ids[3]])
            controller.select_row('files', ids[4], 0x02000000)
            self.assertEqual(controller.data['selected'], ['3.txt', '4.txt'])
            controller.step_selection('files', -1, 0x02000000)
            self.assertEqual(controller.data['selected'], ['3.txt'])
            controller.select_loaded('files', True)
            self.assertEqual(len(controller.data['selected']), 5)
            same = {'path':'1.txt','stream':'other'}
            self.assertNotEqual(file_identity(same, controller.data), ids[1])
            controller.select_loaded('files', False)
            self.assertEqual(controller.data['selection_ids'], [])
            controller.deleteLater();application.deleteLater()

    def test_tabs_restore_selection_filter_columns_and_disclosure(self):
        with patch.object(env_inst, 'projects', {}), patch.object(env_mode, 'current_path', self.temp.name):
            application = Application()
            controller = FileWorkspaceController(application)
            controller._data.update(workspace='work', stream='main', name_filter='hero',
                selection_ids=['first'], selected=['a.txt'], expanded_changes=['one'])
            controller._capture_view()
            with patch.object(controller, 'action'):
                controller.activate_tab('files')
                controller.configure_column('size', 175, False)
                controller.activate_tab('pending')
            self.assertEqual(controller.data['selection_ids'], ['first'])
            self.assertEqual(controller.data['name_filter'], 'hero')
            self.assertEqual(controller.data['expanded_changes'], ['one'])
            self.assertTrue(next(column for column in controller.data['columns'] if column['key']=='size')['visible'])
            controller.deleteLater();application.deleteLater()

    def test_workspace_setup_cancel_restores_active_root_and_mapping_flags(self):
        with patch.object(env_inst,'projects',{}),patch.object(env_mode,'current_path',self.temp.name):
            application=Application();controller=FileWorkspaceController(application)
            controller._data.update(root='D:/active',stream='main',mappings='[]',case_sensitive=True)
            controller.set_value('setup',True)
            controller.set_value('root','D:/draft')
            controller.set_value('stream','different')
            controller.set_value('case_sensitive',False)
            controller.set_value('mapping_preview',{'valid':True})
            self.assertFalse(controller.data['case_sensitive'])
            self.assertTrue(controller.data['mapping_preview']['valid'])
            controller.set_value('setup',False)
            self.assertEqual((controller.data['root'],controller.data['stream'],controller.data['case_sensitive']),('D:/active','main',True))
            controller.deleteLater();application.deleteLater()

    def test_restart_preferences_store_references_and_file_context_not_server_rows(self):
        from thlib.environment import env_read_config
        with patch.object(env_inst,'projects',{}),patch.object(env_mode,'current_path',self.temp.name):
            app=Application();controller=FileWorkspaceController(app)
            controller._data.update(workspace='work',files_source='local',files_prefix='assets/',files_stream='main',change={'code':'selected-change','description':''})
            controller._data['selection_records']={'one':{'path':'assets/a.txt','stream':'main','file':{'blob':'private-id'},'head':{'size':100}}}
            controller._data['workspace_tree']=[{'id':'workspace/work','expanded':False}]
            controller._data['workspace_expanded']=['workspace/work']
            controller._capture_view()
            saved=env_read_config(unique_id=controller._tabs_key(),filename='tabs',long_abs_path=True)
            self.assertEqual(saved['files_prefix'],'assets/');self.assertEqual(saved['workspace_expanded'],[])
            view=saved['tab_states']['pending'];self.assertEqual(view['change_ref'],'selected-change')
            self.assertEqual(view['selection_records']['one'],{'path':'assets/a.txt','stream':'main'})
            self.assertNotIn('change',view);self.assertNotIn('rows',view)
            controller.deleteLater();app.deleteLater()

    def test_selection_retains_previous_page_and_pinned_history(self):
        with patch.object(env_inst,'projects',{}),patch.object(env_mode,'current_path',self.temp.name):
            application=Application();controller=FileWorkspaceController(application)
            controller._data.update(workspace='work',stream='main',view='depot',rows=[{'path':'first.txt'}])
            first=file_identity(controller.data['rows'][0],controller.data)
            controller.select_row('files',first)
            controller._data['rows']=[{'path':'second.txt'}]
            second=file_identity(controller.data['rows'][0],controller.data)
            controller.select_row('files',second,0x04000000)
            self.assertEqual(controller.data['selected'],['first.txt','second.txt'])
            self.assertEqual(len(controller.data['selection_records']),2)
            with patch.object(controller,'action'):
                controller.activate_tab('history')
                self.assertEqual(controller.data['history_path'],'second.txt')
                controller._data['tabs'][-1]['pinned']=True
                controller._data['file_focus']={'path':'third.txt','stream':'main'}
                controller.activate_tab('pending');controller.activate_tab('history')
                self.assertEqual(controller.data['history_path'],'second.txt')
            controller.select_loaded('files',False)
            self.assertEqual(controller.data['selection_records'],{})
            controller.deleteLater();application.deleteLater()

    def test_delete_empty_and_shelf_native_owner_revision_and_retry(self):
        change = self.call('create_change', workspace='work')
        params = {'change':change['code'], 'edit_revision':0, 'request_id':'empty-delete'}
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.call('delete_change', **{**params,'edit_revision':1})
        result = self.call('delete_change', **params)
        self.assertEqual(result, self.call('delete_change', **params))
        self.assertNotIn(change['code'], [row['code'] for row in self.call('changes', state='pending')['items']])
        source = self.change()
        blob = self.upload(source)
        self.call('edit', change=source, edit_revision=0, chunk='edit', operations=[{'path':'a.txt','blob':blob}])
        with self.assertRaisesRegex(ValueError, 'Move or revert'):
            self.call('delete_change', change=source, edit_revision=1, request_id='nonempty')
        shelf = self.call('shelve', change=source, edit_revision=1, request_id='shelf')
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist, 'delete_change', change=shelf['code'], edit_revision=1, request_id='foreign')
        self.call('delete_change', change=shelf['code'], edit_revision=1, request_id='shelf-delete')
        self.assertEqual(self.call('change_files', change=source)['items'][0]['path'], 'a.txt')
        self.assertEqual(self.call('changes', state='shelved')['items'], [])

    def test_delete_trigger_failure_rolls_back_record_and_workspace(self):
        change = self.call('create_change', workspace='work')
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data').get('state') == 'expired':
                raise ValueError('injected delete failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', fail), self.assertRaisesRegex(ValueError, 'injected delete failure'):
            self.call('delete_change', change=change['code'], edit_revision=0, request_id='failure')
        self.assertEqual(self.call('status', change=change['code'])['state'], 'pending')
        self.assertEqual(self.call('status', change=change['code'])['edit_revision'], 0)

    def test_batch_delete_is_atomic_authorized_revision_checked_and_retryable(self):
        changes = sorted([self.call('create_change', workspace='work') for _ in range(2)], key=lambda row: row['code'])
        targets = [{'change': row['code'], 'edit_revision': 0} for row in changes]
        def pending():
            for row in changes:
                self.assertEqual(self.call('status', change=row['code'])['state'], 'pending')
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.call('delete_change', changes=[targets[0], {**targets[1], 'edit_revision': 1}], request_id='batch')
        pending()
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_code() == changes[1]['code'] and record.get_json_value('data').get('state') == 'expired':
                raise ValueError('second deletion failed')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', fail), self.assertRaisesRegex(ValueError, 'second deletion'):
            self.call('delete_change', changes=targets, request_id='batch')
        pending()
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist, 'delete_change', changes=targets, request_id='foreign-batch')
        pending()
        for invalid in ([], targets * 501, [targets[0], targets[0]], [{'change': changes[0]['code']}], 'wrong'):
            with self.assertRaises(ValueError):
                self.call('delete_change', changes=invalid, request_id='bad-batch')
        result = self.call('delete_change', changes=targets, request_id='batch')
        self.assertEqual(result, self.call('delete_change', changes=targets, request_id='batch'))
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(self.call('changes', state='pending')['items'], [])

    def test_batch_delete_rejects_nonempty_without_deleting_empty_peer(self):
        changes = sorted([self.call('create_change', workspace='work') for _ in range(2)], key=lambda row: row['code'])
        self.call('checkout', change=changes[1]['code'], edit_revision=0, request_id='local', paths=['local.txt'])
        with self.assertRaisesRegex(ValueError, 'Move or revert'):
            self.call('delete_change', changes=[{'change': changes[0]['code'], 'edit_revision': 0},
                {'change': changes[1]['code'], 'edit_revision': 1}], request_id='nonempty-batch')
        self.assertEqual(len(self.call('changes', state='pending')['items']), 2)
        self.assertEqual(self.call('change_files', change=changes[1]['code'])['items'][0]['path'], 'local.txt')

    def test_query_selection_is_pinned_bounded_and_owner_scoped(self):
        change=self.change();blob=self.upload(change)
        self.call('edit',change=change,edit_revision=0,chunk='query',operations=[
            {'path':'folder/%04d.txt'%index,'blob':blob} for index in range(700)])
        self.call('submit',change=change)
        selected=self.call('select_query',source='depot',stream='main',prefix='folder/')
        self.assertEqual(selected['files'],700)
        second=self.change()
        self.call('edit',change=second,edit_revision=0,chunk='new',operations=[{'path':'folder/extra.txt','blob':self.upload(second)}])
        self.call('submit',change=second)
        page=self.call('selection_page',selection=selected['selection'],limit=3)
        self.assertEqual(len(page['items']),3)
        self.assertEqual(page['after'],'folder/0002.txt')
        self.assertNotIn('folder/extra.txt',[row['path'] for row in self.call('selection_page',selection=selected['selection'],after='folder/0698.txt')['items']])
        artist=self.writer()
        with self.assertRaises(SecurityException):self.client(artist,'selection_page',selection=selected['selection'])
        filtered=self.call('select_query',source='depot',stream='main',name='0699')
        self.assertFalse(filtered['count_known'])
        self.assertEqual(self.call('selection_page',selection=filtered['selection'],after='folder/0698.txt')['items'][0]['path'],'folder/0699.txt')

    def test_changelist_inspection_matches_existing_depot_read_permissions(self):
        published=self.change();blob=self.upload(published)
        self.call('edit',change=published,edit_revision=0,chunk='public',operations=[{'path':'public.txt','blob':blob}])
        self.call('submit',change=published)
        pending=self.change();self.call('checkout',change=pending,edit_revision=0,request_id='pending',mode='ordinary',paths=['public.txt'])
        shelf=self.call('shelve',change=pending,edit_revision=1,request_id='shelf')
        artist=self.writer()
        # Existing native APIs already expose published files and shared shelves with depot read permission.
        self.assertEqual(self.client(artist,'list',stream='main')['items'][0]['path'],'public.txt')
        self.assertEqual(self.client(artist,'change_files',shelf=shelf['code'])['items'][0]['path'],'public.txt')
        visible=self.client(artist,'changes',scope='all',states=['pending','submitted','shelved'])['items']
        self.assertIn(published,[row['code'] for row in visible])
        self.assertIn(shelf['code'],[row['code'] for row in visible])
        self.assertNotIn(pending,[row['code'] for row in visible])
        self.assertEqual(self.client(artist,'inspect_change_files',change=published)['items'][0]['path'],'public.txt')
        with self.assertRaises(SecurityException):self.client(artist,'inspect_change_files',change=pending)
        with self.assertRaises(SecurityException):self.client(artist,'remove_files',change=pending,edit_revision=1,request_id='foreign',paths=['public.txt'])
        self.call('create_depot',code='private');self.call('create_stream',code='private',depot='private')
        self.call('create_workspace',code='private-work',stream='private',local_root=str(Path(self.temp.name)/'private'))
        private=self.call('create_change',workspace='private-work')
        with self.assertRaises(SecurityException):self.client(artist,'inspect_change_files',change=private['code'])
        self.assertNotIn(private['code'],[row['code'] for row in self.client(artist,'changes',scope='all')['items']])
        own=self.client(artist,'create_change',workspace='artist')
        self.assertEqual(self.call('inspect_change',change=own['code'])['owner'],'artist')

    def test_native_rename_preserves_history_and_rejects_collision(self):
        first = self.change()
        blob = self.upload(first)
        self.call('edit', change=first, edit_revision=0, chunk='first', operations=[{'path':'old.txt','blob':blob}])
        self.call('submit', change=first)
        second = self.change()
        args = {'change':second,'edit_revision':0,'request_id':'rename','renames':[{'source':'old.txt','target':'new.txt'}]}
        renamed = self.call('rename_files', **args)
        self.assertEqual(renamed, self.call('rename_files', **args))
        self.assertEqual([row['action'] for row in self.call('change_files', change=second)['items']], ['move/add','move/delete'])
        self.call('submit', change=second)
        self.assertEqual([row['path'] for row in self.call('history',stream='main',path='new.txt')['items']], ['new.txt','old.txt'])
        third = self.change()
        with self.assertRaisesRegex(ValueError, 'destination'):
            self.call('rename_files', change=third,edit_revision=0,request_id='collision',renames=[{'source':'new.txt','target':'old.txt'}])
        self.assertEqual(self.call('status',change=third)['edit_revision'],0)

    def test_status_batch_retains_workspace_owner_and_depot_read_permissions(self):
        change=self.change();blob=self.upload(change)
        self.call('edit',change=change,edit_revision=0,chunk='status',operations=[{'path':'a.txt','blob':blob}])
        self.call('submit',change=change)
        values={'workspace':'work','paths':[{'stream':'main','path':'a.txt'},{'stream':'main','path':'absent'}]}
        rows=self.call('file_states',**values)['items']
        self.assertEqual(rows[0]['head_state'],'server-only');self.assertIsNone(rows[0]['have'])
        self.assertEqual(rows[1]['head_state'],'server-absent');self.assertIsNone(rows[1]['head'])
        artist=self.writer()
        with self.assertRaises(SecurityException):self.client(artist,'file_states',**values)
        self.call('create_depot',code='private');self.call('create_stream',code='private',depot='private')
        with self.assertRaises(SecurityException):
            self.client(artist,'file_states',workspace='artist',paths=[{'stream':'private','path':'a'}])
        with self.assertRaises(ValueError):self.call('file_states',workspace='work',paths=[{'stream':'main','path':'../outside'}])

    def test_restore_deleted_revision_is_atomic_and_does_not_reupload_bytes(self):
        original=self.change();blob=self.upload(original,b'old content')
        self.call('edit',change=original,edit_revision=0,chunk='original',operations=[{'path':'a.txt','blob':blob}]);self.call('submit',change=original)
        deleted=self.change()
        self.call('edit',change=deleted,edit_revision=0,chunk='delete',operations=[{'path':'a.txt','delete':True}]);self.call('submit',change=deleted)
        restored=self.change()
        values={'change':restored,'edit_revision':0,'request_id':'restore','path':'a.txt','published_change':original}
        trigger=FileProjectRecord._call_triggers
        def fail(record,*args,**kwargs):
            if record.get_base_search_type()=='file_project/change' and record.get_code()==restored and record.get_json_value('data')['edit_revision']==1:
                raise ValueError('injected restore failure')
            return trigger(record,*args,**kwargs)
        with patch.object(FileProjectRecord,'_call_triggers',fail),self.assertRaisesRegex(ValueError,'injected restore'):
            self.call('restore_file',**values)
        self.assertEqual(self.call('status',change=restored)['edit_revision'],0)
        self.assertEqual(self.call('change_files',change=restored)['items'],[])
        result=self.call('restore_file',**values)
        self.assertEqual(self.call('restore_file',**values),result)
        self.call('submit',change=restored)
        head=self.call('list',stream='main')['items'][0]
        self.assertEqual(head['blob'],blob);self.assertEqual(head['number'],3)
        self.assertEqual(len(self.call('history',stream='main',path='a.txt')['items']),3)

    def test_reveal_other_tree_seeks_only_ancestors_of_one_authorized_file(self):
        original=self.change();blob=self.upload(original)
        path='assets/空/new.txt'
        self.call('edit',change=original,edit_revision=0,chunk='tree',operations=[{'path':path,'blob':blob}]);self.call('submit',change=original)
        state=initial_state();state.update(workspace='work',stream='main',root=self.temp.name,view='depot')
        row={'kind':'file','path':path,'stream':'main','parent':original}
        identity=file_identity(row,state);state.update(selection_ids=[identity],selection_records={identity:row},selection_scope='files')
        fixture=self;calls=[]
        class Client:
            def rpc(self,action,**values):calls.append(action);return fixture.call(action,**values)
        from thlib.ui.file_workspace_files import execute_files
        execute_files(Client(),state,Path(self.temp.name)/'cache','reveal_tree',{},threading.Event())
        self.assertEqual(calls,['file_states'])
        self.assertEqual(state['tree_view'],'workspace');self.assertEqual(len(state['workspace_tree']),4)
        self.assertEqual(state['workspace_tree'][-1]['local_status'],'missing')
        self.assertNotIn('parent',state['workspace_tree'][-1])
        execute_files(Client(),state,Path(self.temp.name)/'cache','reveal_tree',{},threading.Event())
        self.assertEqual(calls,['file_states','file_states','stream_status'])
        self.assertEqual(state['tree_view'],'depot');self.assertEqual(state['depot_tree'][-1]['path'],path)

    def test_internal_drop_moves_files_via_native_atomic_command(self):
        source, target = self.change(), self.change()
        blob = self.upload(source)
        self.call('edit', change=source, edit_revision=0, chunk='drop', operations=[{'path':'a.txt','blob':blob}])
        state = initial_state()
        state.update(workspace='work',stream='main',changes=self.call('changes',state='pending')['items'])
        fixture = self
        class Client:
            def rpc(self, action, **values):
                return fixture.call(action, **values)
        payload = json.dumps({'project':'files','workspace':'work','scope':'changes',
                             'rows':[{'parent':source,'path':'a.txt','stream':'main'}]})
        FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','drop_files',
            {'target':target,'payload':payload,'project':'files'},threading.Event())
        self.assertEqual(self.call('change_files', change=source)['items'], [])
        self.assertEqual(self.call('change_files', change=target)['items'][0]['path'], 'a.txt')
        with self.assertRaisesRegex(ValueError, 'current project'):
            FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','drop_files',
                {'target':source,'payload':payload,'project':'other'},threading.Event())

    def test_show_missing_changelist_file_opens_mapped_existing_parent(self):
        from thlib.ui.file_workspace_files import execute_files
        root=Path(self.temp.name)/'workspace'
        (root/'local'/'existing').mkdir(parents=True)
        self.call('create_workspace',code='mapped',stream='main',local_root=str(root),mappings=[
            {'stream':'main','source':'depot/...','target':'local/...','writable':True}])
        change=self.call('create_change',workspace='mapped')
        row={'kind':'file','path':'depot/existing/absent/deep/file — 空.txt','stream':'main'}
        state=initial_state()
        state.update(workspace='mapped',stream='main',root=str(root),view='local',selection_scope='changes',
            change=change,selection_ids=['file'],selection_records={'file':row})
        fixture=self
        class Client:
            def rpc(self,action,**values):return fixture.call(action,**values)
        with patch('subprocess.Popen') as launched:
            execute_files(Client(),state,Path(self.temp.name)/'cache','reveal_local',{},threading.Event())
        parent=root/'local/existing'
        self.assertEqual(launched.call_args.args[0],['explorer.exe' if os.name=='nt' else 'xdg-open',str(parent)])
        self.assertEqual(state['progress']['state'],'complete')
        self.assertEqual(state['operation_notice']['level'],'INFO')
        self.assertEqual(state['operation_notice']['path'],str(root/'local/existing/absent/deep/file — 空.txt'))
        self.assertFalse((root/'depot').exists())
        self.assertFalse((parent/'absent').exists())
        target=root/'local/existing/absent/deep/file — 空.txt'
        target.parent.mkdir(parents=True);target.write_bytes(b'existing')
        state.pop('operation_notice')
        with patch('subprocess.Popen') as launched:
            execute_files(Client(),state,Path(self.temp.name)/'cache','reveal_local',{},threading.Event())
        expected=['explorer.exe','/select,',str(target)] if os.name=='nt' else ['xdg-open',str(target.parent)]
        self.assertEqual(launched.call_args.args[0],expected)
        self.assertNotIn('operation_notice',state)

    def test_absent_workspace_and_missing_open_delete_are_normal_notices(self):
        from thlib.ui.file_workspace_files import execute_files
        root=Path(self.temp.name)/'workspace'
        row={'kind':'file','path':'folder/file.txt'}
        state=initial_state()
        state.update(root=str(root),view='local',selection_scope='files',selection_ids=['file'],selection_records={'file':row})
        class Client:
            def rpc(self,*args,**values):raise AssertionError('No server call for local selection')
        with patch('subprocess.Popen') as launched:
            execute_files(Client(),state,Path(self.temp.name)/'cache','reveal_local',{},threading.Event())
            launched.assert_not_called()
        self.assertEqual(state['progress']['reason'],'workspace_root_missing')
        self.assertFalse(root.exists())
        root.mkdir()
        for action in ('open_local','delete_local'):
            with patch('os.startfile',create=True) as opened,patch('thlib.ui.file_workspace_files.QFile.moveToTrash') as trashed:
                execute_files(Client(),state,Path(self.temp.name)/'cache',action,{},threading.Event())
                opened.assert_not_called();trashed.assert_not_called()
            self.assertEqual(state['progress']['reason'],'local_file_missing')
            self.assertEqual(state['operation_notice']['level'],'WARNING')

    def test_drop_stream_folder_expands_nested_files_in_one_native_checkout(self):
        source=self.change();blob=self.upload(source)
        for index,paths in enumerate((['folder/deep/f%04d.txt'%n for n in range(1000)],
                ['folder/deep/f%04d.txt'%n for n in range(1000,1105)]+['folder-extra/outside.txt','outside.txt'])):
            self.call('edit',change=source,edit_revision=index,chunk='publish%d'%index,
                operations=[{'path':path,'blob':blob} for path in paths])
        self.call('submit',change=source)
        target=self.change()
        state=initial_state();state.update(workspace='work',stream='main',changes=self.call('changes',state='pending')['items'])
        calls=[];fixture=self
        class Client:
            def rpc(self,action,**values):calls.append((action,values));return fixture.call(action,**values)
        payload=json.dumps({'project':'files','workspace':'work','scope':'depot','rows':[
            {'kind':'directory','path':'folder/','directory':'folder/','stream':'main'},
            {'kind':'directory','path':'folder/deep/','directory':'folder/deep/','stream':'main'},
            {'kind':'file','path':'folder/deep/f0000.txt','stream':'main'}]})
        FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','drop_files',
            {'target':target,'payload':payload,'project':'files'},threading.Event())
        checkout=[values for action,values in calls if action=='checkout']
        self.assertEqual(len(checkout),1)
        self.assertEqual(checkout[0]['directories'],['folder/','folder/deep/'])
        self.assertEqual(next(row for row in self.call('changes',state='pending')['items'] if row['code']==target)['opened_files'],1105)
        self.assertEqual(state['progress']['files_done'],1105)
        page=self.call('change_files',change=target,limit=1000)
        self.assertEqual(len(page['items']),1000)
        tail=self.call('change_files',change=target,after=page['after'])['items']
        self.assertEqual(len(tail),105)
        self.assertFalse(any(row['path'].startswith('folder-extra/') for row in page['items']+tail))
        self.assertEqual(self.call('status',change=target)['edit_revision'],1)

    def test_recursive_checkout_rolls_back_early_chunks_on_late_lock_conflict(self):
        source=self.change();blob=self.upload(source)
        self.call('edit',change=source,edit_revision=0,chunk='first',operations=[{'path':'folder/f%04d'%n,'blob':blob} for n in range(1000)])
        self.call('edit',change=source,edit_revision=1,chunk='last',operations=[{'path':'folder/z-last','blob':blob}])
        self.call('submit',change=source)
        held,target=self.change(),self.change()
        self.call('checkout',change=held,paths=['folder/z-last'],mode='exclusive')
        before=self.call('status',change=target)
        with self.assertRaisesRegex(ValueError,'Exclusive checkout conflict'):
            self.call('checkout',change=target,edit_revision=0,request_id='atomic-folder',directories=['folder/'])
        after=self.call('status',change=target)
        self.assertEqual(after['edit_revision'],before['edit_revision'])
        self.assertEqual(after['work_root'],before['work_root'])
        locked=self.call('locks',stream='main',paths=['folder/f0000','folder/z-last'])['items']
        self.assertEqual([row['path'] for row in locked],['folder/z-last'])
        self.assertEqual(locked[0]['holders'][0]['change'],held)
        self.call('revert',change=held)
        original=FileProjectRecord._call_triggers
        def fail_last(record,*args,**kwargs):
            if record.get_base_search_type()=='file_project/checkout' and record.get_json_value('data')['path']=='folder/z-last':
                raise ValueError('late folder checkout trigger')
            return original(record,*args,**kwargs)
        with patch.object(FileProjectRecord,'_call_triggers',fail_last):
            with self.assertRaisesRegex(ValueError,'late folder checkout trigger'):
                self.call('checkout',change=target,edit_revision=0,request_id='atomic-folder',directories=['folder/'])
        self.assertEqual(self.call('change_files',change=target)['items'],[])
        self.assertEqual(self.call('locks',stream='main',paths=['folder/f0000'])['items'],[])
        result=self.call('checkout',change=target,edit_revision=0,request_id='atomic-folder',directories=['folder/'])
        self.assertEqual(result['paths'],1001)
        self.assertEqual(self.call('checkout',change=target,edit_revision=0,request_id='atomic-folder',directories=['folder/']),result)

    def test_folder_checkout_uses_workspace_mapping_exclusions_and_rights(self):
        source=self.change();blob=self.upload(source)
        self.call('edit',change=source,edit_revision=0,chunk='files',operations=[{'path':path,'blob':blob} for path in ['folder/a','folder/deep/b','folder/private/c','outside']])
        self.call('submit',change=source)
        self.call('create_workspace',code='mapped',stream='main',local_root='D:/mapped',mappings=[
            {'stream':'main','source':'...','target':'src/...','writable':True},
            {'stream':'main','source':'folder/private/...','exclude':True}])
        target=self.call('create_change',workspace='mapped')['code']
        result=self.call('checkout',change=target,local_directories=['src/folder/'])
        self.assertEqual(result['paths'],2)
        self.assertEqual([row['path'] for row in self.call('change_files',change=target)['items']],['folder/a','folder/deep/b'])
        self.call('create_workspace',code='read-only',stream='main',local_root='D:/read-only',mappings=[
            {'stream':'main','source':'...','target':'src/...','writable':True},
            {'stream':'main','source':'folder/deep/...','target':'read-only/...','writable':False}])
        denied=self.call('create_change',workspace='read-only')['code']
        with self.assertRaises(SecurityException):self.call('checkout',change=denied,directories=['folder/'])
        self.assertEqual(self.call('change_files',change=denied)['items'],[])
        artist=self.writer()
        with self.assertRaises(SecurityException):self.client(artist,'checkout',change=target,directories=[''])
        with self.assertRaises(ValueError):self.call('checkout',change=target,directories=['../'])
        with self.assertRaises(ValueError):self.call('checkout',change=target,directories=['folder'])


if __name__ == '__main__':
    unittest.main()
