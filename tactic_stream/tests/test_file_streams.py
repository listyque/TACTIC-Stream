"""Native stream editing, immutable ancestry and desktop hierarchy."""
import unittest
from pyasm.command import Trigger
from pyasm.common.errors import SecurityException
from test_file_project import FileProjectFixture
from test_file_workspace import FileWorkspaceTest


class RejectStreamEdit(Trigger):
    def execute(self):
        raise ValueError('Reject stream edit')


class FileStreamTest(FileProjectFixture, unittest.TestCase):
    writer=FileWorkspaceTest.writer
    client=FileWorkspaceTest.client
    publish=FileWorkspaceTest.publish
    edit=FileWorkspaceTest.edit

    def test_deep_hierarchy_edit_reparent_retains_published_merge_base(self):
        base=self.publish({'base.txt':b'base'})
        self.call('create_stream',code='dev',depot='main',parent='main',title='Development')
        child=self.call('create_stream',code='feature',depot='main',parent='dev',description='Feature work')
        original=self.call('stream_status',stream='feature')
        self.call('create_stream',code='other',depot='main',parent='main')
        edited=self.call('update_stream',stream='feature',spec_revision=0,parent='other',title='Updated title',description='Details',locked=True)
        self.assertEqual(edited['parent'],'other');self.assertEqual(edited['branch_parent'],'dev')
        for field in ('root','revision','head_change','fork_root','parent_change'):
            self.assertEqual(edited[field],original[field])
        self.assertEqual(edited['spec_revision'],1)
        with self.assertRaisesRegex(ValueError,'settings changed'):
            self.call('update_stream',stream='feature',spec_revision=0,title='Stale')
        with self.assertRaisesRegex(ValueError,'cycle'):
            self.call('update_stream',stream='other',spec_revision=0,parent='feature')
        self.assertEqual(self.call('stream_status',stream='other')['parent'],'main')
        graph=self.call('stream_graph')
        self.assertIn({'source':'other','target':'feature','kind':'parent','change':None},graph['edges'])
        self.call('update_stream',stream='feature',spec_revision=1,description='New description')
        with self.assertRaisesRegex(ValueError,'Graph changed'):
            self.call('stream_graph',heads=graph['heads'])
        self.publish({'new.txt':b'new'})
        self.call('create_workspace',code='feature-work',stream='feature',local_root='D:/feature')
        change=self.call('create_change',workspace='feature-work')['code']
        integration=self.call('merge_begin',change=change,source_stream='main',edit_revision=0,request_id='merge')
        self.assertEqual(integration['kind'],'merge')

    def test_spec_permissions_native_rollback_and_supported_types(self):
        artist=self.writer()
        protected=self.call('create_stream',code='protected',depot='main',parent='main',locked=True)
        with self.assertRaises(SecurityException):
            self.client(artist,'update_stream',stream='protected',spec_revision=0,description='Not allowed')
        self.call('update_stream',stream='protected',spec_revision=0,locked=False)
        changed=self.client(artist,'update_stream',stream='protected',spec_revision=1,title='Artist title')
        self.assertEqual(changed['title'],'Artist title')
        self.call('create_stream',code='release',depot='main',parent='main',stream_type='release')
        with self.assertRaises(ValueError):
            self.call('create_stream',code='invalid',depot='main',parent='release',stream_type='development')
        with self.assertRaisesRegex(ValueError,'not implemented'):
            self.call('create_stream',code='virtual',depot='main',parent='main',stream_type='virtual')
        self.api.dispatch('insert',(self.ticket,'config/trigger',{'code':'reject-stream-edit',
            'event':'update|file_project/stream','class_name':'test_file_streams.RejectStreamEdit',
            'mode':'same process,same transaction'}))
        with self.assertRaisesRegex(ValueError,'Reject stream edit'):
            self.call('update_stream',stream='protected',spec_revision=2,description='Must roll back')
        result=self.call('stream_status',stream='protected')
        self.assertEqual(result['spec_revision'],2)
        self.assertEqual(result['description'],'')
