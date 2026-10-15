"""Bounded native snapshots, changelist visibility and request-local reads."""
from contextlib import contextmanager
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json
import os
import sys
import threading
import unittest
from unittest.mock import patch
from test_file_project import FileProjectFixture
import test_file_workspace as workspaces
from pyasm.search.storage import Store
from pyasm.search import Search
from pyasm.common.errors import SecurityException


@contextmanager
def query_trace():
    statements=[]
    original=Store.connection
    def trace(statement):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)
    @contextmanager
    def connection(store,*args,**kwargs):
        with original(store,*args,**kwargs) as db:
            db.set_trace_callback(trace)
            try:
                yield db
            finally:
                db.set_trace_callback(None)
    with patch.object(Store,'connection',connection):
        yield statements


class FileWorkspaceReadTest(FileProjectFixture,unittest.TestCase):
    writer=workspaces.FileWorkspaceTest.writer
    client=workspaces.FileWorkspaceTest.client

    def test_read_batch_is_bounded_and_cannot_mutate_or_cross_private_work(self):
        pending=self.call('create_change',workspace='work',description='Private admin work')
        requests=[{'action':'streams','values':{'limit':200}},
                  {'action':'inspect_change','values':{'change':pending['code']}}]
        result=self.call('read_batch',requests=requests)['items']
        self.assertEqual(result[1]['description'],'Private admin work')
        with self.assertRaises(SecurityException):
            self.client(self.writer(),'read_batch',requests=requests)
        for requests in ([],[{'action':'streams','values':{}}]*17,
                         [{'action':'create_change','values':{'workspace':'work'}}],
                         [{'action':'read_batch','values':{'requests':[]}}]):
            with self.assertRaises(ValueError):
                self.call('read_batch',requests=requests)
        self.assertEqual([row['code'] for row in self.call('changes',state='pending')['items']],[pending['code']])

    def test_state_filter_precedes_page_and_new_empty_changes_are_visible(self):
        for index in range(115):
            change=self.call('create_change',workspace='work')
            self.call('revert',change=change['code'],edit_revision=0,request_id='revert-'+str(index))
        first=self.call('create_change',workspace='work',description='empty first')
        second=self.call('create_change',workspace='work',description='empty newest')
        self.assertEqual([row['code'] for row in self.call('changes',state='pending',limit=100)['items']],
                         [second['code'],first['code']])
        page=self.call('changes',state='pending',limit=1)
        self.assertEqual(page['items'][0]['code'],second['code'])
        self.assertEqual(self.call('changes',state='pending',after=page['after'],limit=1)['items'][0]['code'],first['code'])

    def test_create_change_retry_is_idempotent_and_different_payload_is_rejected(self):
        first=self.call('create_change',workspace='work',description='one',request_id='new-change')
        retry=self.call('create_change',workspace='work',description='one',request_id='new-change')
        self.assertEqual(first,retry)
        self.assertEqual(len(self.call('changes',state='pending')['items']),1)
        with self.assertRaisesRegex(ValueError,'different data'):
            self.call('create_change',workspace='work',description='different',request_id='new-change')

    def test_snapshot_stream_reads_do_not_grow_per_changelist_and_refresh_creates_nothing(self):
        for index in range(75):
            self.call('create_change',workspace='work',description='new-'+str(index))
        with query_trace() as statements:
            result=self.call('workspace_snapshot',workspace='work',stream='main',view='change',
                             tab={'kind':'changes','state':'pending','scope':'mine'},expanded=[])
        domains=Counter(table for query in statements for table in ('change','stream','workspace','page')
                        if '"'+table+'"' in query)
        self.assertEqual(len(result['changes']['items']),75)
        self.assertLessEqual(domains['stream'],1)
        self.assertLessEqual(domains['workspace'],1)
        self.assertLessEqual(domains['change'],1)
        self.assertEqual(len(self.call('changes',state='pending')['items']),75)
        self.call('create_change',workspace='work',description='next request')
        next_result=self.call('workspace_snapshot',workspace='work',stream='main',view='change',
                              tab={'kind':'changes','state':'pending'},expanded=[])
        self.assertEqual(len(next_result['changes']['items']),76)
        self.assertEqual(next_result['changes']['items'][0]['description'],'next request')

    def test_read_page_returns_current_holders_and_rechecks_permission_next_request(self):
        artist=self.writer()
        admin=self.call('create_change',workspace='work')
        blob=self.upload(admin['code'])
        self.call('edit',change=admin['code'],edit_revision=0,chunk='fresh',operations=[{'path':'fresh.txt','blob':blob}])
        self.call('submit',change=admin['code'])
        pending=self.client(artist,'create_change',workspace='artist')
        self.client(artist,'checkout',change=pending['code'],paths=['fresh.txt'],mode='ordinary')
        result=self.client(artist,'read_page',source='list',workspace_context='artist',stream='main',limit=200)
        self.assertEqual(result['items'][0]['holders'][0]['change'],pending['code'])
        self.assertIn('head',result['items'][0]);self.assertIn('have',result['items'][0])
        self.api.dispatch('update',({'ticket':self.token,'project':'admin'},'sthpw/login_group?code=artists',
            {'access_rules':'<rules><rule group="project" code="files" access="allow"/><rule group="file_depot" project="files" code="*" access="deny"/></rules>'}))
        with self.assertRaises(SecurityException):
            self.client(artist,'read_page',source='list',workspace_context='artist',stream='main')

    def test_handler_refresh_one_request_and_one_selected_file_page(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from thlib.environment import env_mode,env_server
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'])
        self.call('edit',change=change['code'],edit_revision=0,chunk='files',operations=[{'path':'new.txt','blob':blob}])
        self.call('switch_workspace',workspace='work',revision=0,request_id='work')
        state=initial_state();state.update(workspace='work',stream='main',change=change,expanded_changes=[change['code']])
        fixture=self;calls=[]
        class Client:
            url='http://owned.invalid';project='files'
            def rpc(self,action,**kwargs):
                calls.append(action)
                return fixture.call(action,**kwargs)
        with patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_user',return_value='admin'):
            result=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','refresh',{},threading.Event())
        self.assertEqual(calls,['workspace_snapshot'])
        self.assertEqual(result['rows'],result['change_children'][change['code']]['items'])
        self.assertEqual(result['rows'][0]['path'],'new.txt')
        self.assertEqual(len(result['changes']),1)

    def test_setup_reloads_metadata_once_and_transfer_cancel_skips_metadata(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from thlib.environment import env_mode,env_server
        state=initial_state();state.update(workspace='work',stream='main',code='extra')
        fixture=self;calls=[]
        class Client:
            url='http://owned.invalid';project='files'
            def rpc(self,action,**kwargs):
                calls.append((action,kwargs))
                if action=='transfer_cancel':return {'state':'cancelled'}
                return fixture.call(action,**kwargs)
        with patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_user',return_value='admin'):
            result=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','create_depot',{},threading.Event())
            self.assertEqual([action for action,_ in calls],['create_depot','workspace_snapshot'])
            self.assertTrue(any(row['code']=='extra' for row in result['depots']))
            calls.clear()
            result=FileWorkspaceController._execute(Client(),result,Path(self.temp.name)/'cache','transfer_cancel',{'task':'owned'},threading.Event())
            self.assertEqual([action for action,_ in calls],['transfer_cancel','workspace_snapshot'])
            self.assertFalse(calls[-1][1]['catalog'])
            self.assertEqual(result['progress']['state'],'cancelled')

    def test_workspace_filter_fills_page_and_handoff_stays_visible_to_new_owner(self):
        first=self.call('create_change',workspace='work')
        self.call('create_workspace',code='other',stream='main',local_root='D:/other')
        for _ in range(110):
            self.call('create_change',workspace='other')
        page=self.call('changes',workspace='work',scope='workspace',state='pending',limit=100)
        self.assertEqual([row['code'] for row in page['items']],[first['code']])
        artist=self.writer()
        offered=self.call('offer_change',change=first['code'],edit_revision=0,recipient='artist',request_id='offer')
        self.client(artist,'accept_change',change=first['code'],edit_revision=offered['edit_revision'],
                    handoff=offered['handoff']['code'],workspace='artist',request_id='accept')
        self.assertEqual([row['code'] for row in self.client(artist,'changes',state='pending')['items']],[first['code']])

    def test_filtered_page_keeps_tail_cursor_and_create_trigger_failure_rolls_back(self):
        self.call('create_workspace',code='other',stream='main',local_root='D:/other')
        expected=[]
        for index in range(7):
            change=self.call('create_change',workspace='work' if index%2==0 else 'other')
            if index%2==0:expected.append(change['code'])
        found=[];cursor=''
        while True:
            page=self.call('changes',workspace='work',scope='workspace',state='pending',limit=2,after=cursor)
            found.extend(row['code'] for row in page['items'])
            cursor=page['after']
            if not cursor:break
        self.assertEqual(found,list(reversed(expected)))
        from pyasm.biz.file_project import FileProjectRecord
        original=FileProjectRecord._call_triggers
        def fail(record,*args,**kwargs):
            original(record,*args,**kwargs)
            if record.get_base_search_type()=='file_project/change':
                raise ValueError('native create trigger failed')
        with patch.object(FileProjectRecord,'_call_triggers',fail),self.assertRaisesRegex(ValueError,'native create trigger'):
            self.call('create_change',workspace='work',description='must roll back',request_id='failed')
        self.assertFalse(any(row['description']=='must roll back' for row in self.call('changes',state='pending')['items']))
        retried=self.call('create_change',workspace='work',description='must roll back',request_id='failed')
        self.assertTrue(retried['code'])

    def test_refresh_expanded_nested_directories_uses_the_same_request(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from thlib.environment import env_mode,env_server
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'])
        self.call('edit',change=change['code'],edit_revision=0,chunk='dirs',operations=[
            {'path':path,'blob':blob} for path in ('docs/a.txt','docs/nested/b.txt')])
        self.call('submit',change=change['code'])
        self.call('switch_workspace',workspace='work',revision=0,request_id='active')
        state=initial_state();state.update(workspace='work',stream='main',
            depot_expanded=['stream/main','path/main/docs/','path/main/docs/nested/'])
        fixture=self;calls=[]
        class Client:
            url='http://owned.invalid';project='files'
            def rpc(self,action,**kwargs):
                calls.append(action)
                return fixture.call(action,**kwargs)
        with patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_user',return_value='admin'):
            result=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','refresh',{},threading.Event())
        self.assertEqual(calls,['workspace_snapshot'])
        self.assertTrue(any(row['id']=='path/main/docs/nested/b.txt' for row in result['depot_tree']))


if __name__=='__main__':
    unittest.main()
