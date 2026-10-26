"""Persistent user/project folders and chat metadata, independent of model turns."""
from copy import deepcopy
import unittest
from uuid import uuid4

from tests import test_agent_requests as fixture


class AgentLibrary(unittest.TestCase):
    setUp=fixture.AgentRequests.setUp
    call=fixture.AgentRequests.call
    submit=fixture.AgentRequests.submit

    def test_project_without_config_tables_does_not_break_history(self):
        from pyasm.search.search import RequestContext,request_context
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            # A physical project DB may exist before configuration upgrades finish.
            self.api.dispatch('insert',(self.auth,'sthpw/project',dict(code='unupgraded',title='Unupgraded')))
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.store.database_path('unupgraded'))) as db, db:
            db.execute('CREATE TABLE unrelated (id integer)')
        result=self.call('library')
        self.assertFalse(next(item for item in result['projects'] if item['code']=='unupgraded')['agent_available'])

    def create(self):
        return self.call('draft',request_id=str(uuid4()),context=deepcopy(self.document['context']))

    def edit(self, row, **changes):
        current=self.call('read',request_id=row['request_id'])['library_summary']
        document={key:current[key] for key in ('title','group','pinned','archived')}
        document.update(changes)
        return self.call('organize',request_id=row['request_id'],expected_revision=current['library_revision'],document=document)

    def test_named_draft_pin_folder_and_first_send_keep_capture_and_metadata(self):
        draft=self.create()
        state=self.call('state')
        folders=self.call('group_save',group='',name='Review',expected_revision=state['groups_revision'])
        group=folders['groups'][0]['id']
        edited=self.edit(draft,title='Episode planning',group=group,pinned=True)
        self.assertEqual(edited['messages'],[])
        self.assertIsNone(self.call('claim',host_id=self.host)['request'])
        sent,_=self.submit(request_id=draft['request_id'])
        self.assertEqual(sent['document'],self.document)
        self.assertEqual(sent['library']['title'],'Episode planning')
        self.assertEqual(sent['library']['group'],group)
        self.assertTrue(sent['library']['pinned'])
        self.assertEqual(self.call('state')['requests'][0]['title'],'Episode planning')
        self.assertEqual(self.call('claim',host_id=self.host)['request']['request_id'],draft['request_id'])
        with self.assertRaisesRegex(ValueError,'current turn'):
            self.edit(sent,archived=True)

    def test_source_revision_conflicts_and_folder_remove_preserve_conversation(self):
        row,_=self.submit();self.call('claim',host_id=self.host)
        self.call('update',request_id=row['request_id'],host_id=self.host,status='completed',answer='Original answer')
        original=self.call('read',request_id=row['request_id'])
        state=self.call('state')
        folder=self.call('group_save',group='',name='Work',expected_revision=state['groups_revision'])
        code=folder['groups'][0]['id']
        self.edit(row,title='Review results',group=code)
        with self.assertRaisesRegex(ValueError,'settings changed'):
            self.call('organize',request_id=row['request_id'],expected_revision=original['library_summary']['library_revision'],
                document=dict(title='Wrong stale title',group='',pinned=False,archived=False))
        self.call('group_save',group=code,name='Delivery',expected_revision=folder['groups_revision'])
        with self.assertRaisesRegex(ValueError,'folders changed'):
            self.call('group_remove',group=code,expected_revision=folder['groups_revision'])
        latest=self.call('state')
        self.call('group_remove',group=code,expected_revision=latest['groups_revision'])
        saved=self.call('read',request_id=row['request_id'])
        for key in ('document','messages','status','host_id'):
            self.assertEqual(saved[key],original[key])
        self.assertEqual(saved['library']['group'],'')
        self.assertEqual(saved['library']['title'],'Review results')

    def test_archive_restore_and_full_text_search_do_not_replay_execution(self):
        row,_=self.submit();self.call('claim',host_id=self.host)
        self.call('update',request_id=row['request_id'],host_id=self.host,status='completed',answer='Unique answer needle')
        self.assertEqual(len(self.call('state',query='answer needle')['requests']),1)
        self.edit(row,archived=True)
        self.assertEqual(self.call('state')['requests'],[])
        archived=self.call('state',archived=True)['requests']
        self.assertEqual(archived[0]['request_id'],row['request_id'])
        with self.assertRaisesRegex(ValueError,'Restore'):
            self.call('message',request_id=row['request_id'],message_id=str(uuid4()),text='Continue')
        self.edit(row,archived=False)
        self.assertEqual(len(self.call('state')['requests']),1)
        self.assertIsNone(self.call('claim',host_id=self.host)['request'])

    def test_pagination_pins_and_user_project_boundaries(self):
        from pyasm.search.search import RequestContext,request_context
        from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
        from pyasm.search import Search
        row=self.create()
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            command=AgentRequestCmd();command.owner='admin';command.sql=Search('config/trigger').get_sql()
            for index in range(104):
                item=dict(deepcopy(row),request_id=str(uuid4()),created=1000+index,activity=1000+index)
                item['document']['prompt']='Chat '+str(index)
                command.save('spt_agent_request',item['request_id'],item)
        self.edit(row,title='Pinned old chat',pinned=True)
        first=self.call('state');second=self.call('state',offset=first['next_offset'])
        self.assertEqual(first['requests'][0]['title'],'Pinned old chat')
        self.assertEqual(first['total'],105)
        self.assertEqual(len(first['requests']),100)
        self.assertEqual(len(second['requests']),5)
        self.assertTrue(set(item['request_id'] for item in first['requests']).isdisjoint(item['request_id'] for item in second['requests']))
        first=self.call('library');second=self.call('library',offset=first['next_offset'])
        self.assertEqual(first['total'],105)
        self.assertEqual(len(first['requests']),100)
        self.assertEqual(len(second['requests']),5)
        self.assertTrue({row['key'] for row in first['requests']}.isdisjoint(row['key'] for row in second['requests']))
        with self.assertRaises(ValueError):self.call('state',offset=-1)
        other=dict(self.document['context'],project='foreign')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            self.call('draft',request_id=str(uuid4()),context=other)

    def test_all_projects_library_keeps_owner_context_and_execution_local(self):
        from pyasm.search.search import RequestContext,request_context
        from pyasm.biz import Project
        from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
        from pyasm.search import Search
        row=self.create()
        self.api.dispatch('execute_cmd',(dict(self.auth,project='admin'),'tactic.command.CreateProjectCmd',
            dict(project_code='empty',project_title='Empty project')))
        def other(action,**values):
            return self.api.dispatch('execute_cmd',(dict(self.auth,project='empty'),fixture.COMMAND,
                dict(action=action,project_code='empty',**values)))['info']
        # The new project has no agent inbox yet; its library still finds old chats.
        library=other('library')
        self.assertEqual([(r['project'],r['request_id']) for r in library['requests']],[('one',row['request_id'])])
        self.assertTrue(any(p['code']=='empty' for p in library['projects']))
        self.assertEqual(other('library',project_filter='empty')['requests'],[])
        catalog=other('host_projects')
        self.assertEqual(catalog['requests'],[])
        self.assertTrue(next(p for p in catalog['projects'] if p['code']=='empty')['agent_available'])
        duplicate=other('draft',request_id=row['request_id'],context=dict(self.document['context'],project='empty',search_keys=[]))
        with request_context(RequestContext(self.store,'admin','empty')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            command=AgentRequestCmd();command.owner='another-login';command.sql=Search('config/trigger').get_sql()
            private=dict(deepcopy(duplicate),request_id=str(uuid4()))
            command.save('spt_agent_request',private['request_id'],private)
        library=other('library')
        self.assertEqual(len(library['requests']),2)
        self.assertEqual(len({item['key'] for item in library['requests']}),2)
        self.assertEqual(len(other('state')['requests']),1)
        self.assertEqual(other('state')['active_requests'],[])
        self.assertEqual(other('read',request_id=row['request_id'])['document']['context']['project'],'empty')
        self.assertEqual(self.call('read',request_id=row['request_id'])['document']['context']['project'],'one')
        self.assertEqual(len(other('library',project_filter='one')['requests']),1)
        self.assertEqual(len(other('library',query='Empty project')['requests']),1)
        self.assertEqual(other('library',archived=True)['requests'],[])
        with self.assertRaisesRegex(ValueError,'unavailable'):other('library',project_filter='not_registered')
        # Aggregation must restore the caller's authenticated project.
        with request_context(RequestContext(self.store,'admin','empty')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            command=AgentRequestCmd(action='library',project_code='empty');command.execute()
            self.assertEqual(Project.get_project_code(),'empty')
        database=self.store.database_path('empty')
        database.rename(database.with_suffix('.unavailable'))
        library=self.call('library')
        self.assertEqual(library['unavailable_projects'],['empty'])
        self.assertFalse(next(p for p in self.call('host_projects')['projects'] if p['code']=='empty').get('agent_available',False))
        self.assertEqual(len(library['requests']),1)
        self.assertFalse(database.exists())
