"""Private native fixtures for the unmodified Handler Knowledge Base contract."""
import json
import tempfile
import unittest
from pathlib import Path

from test_foundation import fixture
from pyasm.search.storage import Store
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.knowledge import knowledge_request


class Knowledge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))
        from tactic.startup import FirstRunInit
        with request_context(RequestContext(self.store, 'admin')):
            FirstRunInit().execute()
        self.store.initialize(hash_password('private-test-password')); fixture(self.store)
        self.context = request_context(RequestContext(self.store, 'admin', 'one'))
        self.context.__enter__(); self.addCleanup(self.context.__exit__, None, None, None)
        self.api = Api(self.store)
        self.ticket = self.api.get_ticket('admin', 'private-test-password')
        self.api.auth.bind_security('admin', self.ticket)

    def call(self, action, **values):
        return knowledge_request(action, {'ticket': self.ticket, 'project': 'one', **values})

    def test_article_drafts_organization_history_and_attachments(self):
        self.assertFalse(self.call('list')['initialized'])
        self.assertTrue(self.call('initialize')['initialized'])
        section = self.call('save', document={'title': 'Guide', 'kind': 'section'})
        article = self.call('save_draft', document={'title': 'Workflow', 'parentCode': section['identity'],
            'contentMarkdown': '# Start\n\nHello', 'contentText': 'Start Hello',
            'linkedSearchKeys': ['skey://contract/entity?project=one&code=A']})
        self.assertTrue(article['document']['draft'])
        self.assertEqual(self.call('link_index')['links'], [])
        data = dict(article['document']); data['contentMarkdown'] += '\n\nWorld'
        published = self.call('save', identity=article['identity'], expected_revision=article['revision'], document=data)
        self.assertFalse(published['document']['draft'])
        self.assertEqual(len(self.call('link_index')['links']), 1)
        from tactic_stream.server.result_items import read_result_items
        item=read_result_items('contract/entity',['contract/entity?project=one&code=A'])['items'][0]
        self.assertEqual(item['knowledge'][0]['identity'],article['identity'])
        with self.assertRaisesRegex(ValueError, 'changed on the server'):
            self.call('save', identity=article['identity'], expected_revision=article['revision'], document=data)
        self.assertEqual(len(self.call('list', query='Hello')['catalog']), 1)
        history = self.call('history', identity=article['identity'])['history']
        self.assertGreaterEqual(len(history), 2, [row.get_data() for row in Search('sthpw/sobject_log').get_sobjects()])
        prior = self.call('history_revision', identity=article['identity'], history_revision=history[-1]['revisionId'])
        self.assertNotIn('World', prior['historyRevision']['document']['contentMarkdown'])
        with self.assertRaisesRegex(ValueError, 'inside its child'):
            self.call('organize', expected_revision=published['catalogRevision'], organization=[{'identity': section['identity'], 'parentCode': section['identity']}])
        uploaded = knowledge_request('upload', {'ticket': self.ticket, 'project': 'one', 'identity': article['identity']}, [('notes.txt', b'private attachment')])
        self.assertEqual(uploaded['attachments'][0]['title'], 'notes.txt')
        self.assertIn('/assets/', uploaded['attachments'][0]['webUrl'])
        removed = self.call('delete_attachment', identity=article['identity'], attachment_key=uploaded['attachments'][0]['snapshotKey'])
        self.assertEqual(removed['attachments'], [])

    def test_image_files_and_reader_permissions(self):
        from io import BytesIO
        from PIL import Image
        from pyasm.search import SearchKey
        from pyasm.common.errors import SecurityException
        from tactic_stream.server.navigation_links import navigation_link_request
        self.call('initialize')
        published = self.call('save', document={'title': 'Published', 'contentMarkdown': '# Read'})
        draft = self.call('save_draft', document={'title': 'Private draft', 'contentMarkdown': 'Unpublished'})
        image = BytesIO(); Image.new('RGB', (20, 10), 'red').save(image, format='PNG')
        uploaded = knowledge_request('upload', {'ticket':self.ticket,'project':'one','identity':published['identity']}, [('preview.png',image.getvalue())])
        self.assertEqual(uploaded['attachments'][0]['title'], 'preview.png')
        snapshot = SearchKey.get_by_search_key(uploaded['attachments'][0]['snapshotKey'].removeprefix('skey://'))
        paths = [file.get_lib_path() for file in snapshot.get_all_file_objects()]
        self.assertEqual(len(set(paths)), len(paths), paths)
        self.assertTrue(all(Path(path).is_file() for path in paths))
        file = snapshot.get_all_file_objects()[0]
        file.add_metadata(dict(type='sequence', template='$FILENAME.$FRAME.$EXT', new_template='$FILENAME.$FRAME.$EXT',
            new_filename='render', new_file_ext='png', new_padding=4, frameranges=['1-52']), replace=False)
        from pyasm.command import Command
        command = Command(); command.execute = lambda: file.commit(triggers=False)
        Command.execute_cmd(command)
        private_files = knowledge_request('upload', {'ticket':self.ticket,'project':'one','identity':draft['identity']}, [('private.txt',b'draft file')])
        private_snapshot = SearchKey.get_by_search_key(private_files['attachments'][0]['snapshotKey'].removeprefix('skey://'))
        reader = SearchType.create('sthpw/login'); reader.set_value('login','reader');reader.set_value('password',hash_password('reader-password'));reader.commit()
        group = SearchType.create('sthpw/login_group'); group.set_value('login_group','knowledge_reader')
        group.set_value('access_rules','<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="one/th_knowledge_article" project="one" access="view"/></rules>'); group.commit()
        member = SearchType.create('sthpw/login_in_group'); member.set_value('login','reader');member.set_value('login_group','knowledge_reader');member.commit()
        ticket = self.api.get_ticket('reader','reader-password')
        with request_context(RequestContext(self.store, 'reader', 'one')):
            self.api.auth.bind_security('reader',ticket)
            result = self.call('list')
            self.assertFalse(result['canEdit'])
            self.assertEqual([row['title'] for row in result['catalog']], ['Published'])
            self.assertTrue(self.call('load',identity=draft['identity'])['entryMissing'])
            self.assertEqual(self.call('load',identity=published['identity'])['attachments'][0]['title'],'preview.png')
            with self.assertRaises(SecurityException): self.call('save',document={'title':'Denied'})
            with self.assertRaises(LookupError): navigation_link_request({'link':draft['searchKey']})
            with self.assertRaises(LookupError): navigation_link_request({'link':'skey://' + private_snapshot.get_search_key()})
            with self.assertRaises(LookupError): navigation_link_request({'link':'skey://' + private_snapshot.get_all_file_objects()[0].get_search_key()})
            self.assertEqual(navigation_link_request({'link':published['searchKey']})['title'],'Published')
            from tactic_stream.server.result_items import read_result_items
            browser = read_result_items('one/th_knowledge_article',[published['searchKey'].removeprefix('skey://')],{'kind':'snapshot_browser','process':'attachment'})
            self.assertTrue(browser['rows'])
            members = [row for row in browser['rows'] if row.get('depth') == 3]
            self.assertEqual(members[0]['title'], 'render.0001.png')
            self.assertEqual(members[-1]['rowType'], 'more')
            page = read_result_items('sthpw/file',[file.get_search_key()],{'kind':'snapshot_members'},50,50)
            self.assertEqual([row['title'] for row in page['rows']], ['render.0051.png','render.0052.png'])
            with self.assertRaises(LookupError):
                read_result_items('sthpw/snapshot',[private_snapshot.get_search_key()],{'kind':'snapshot_browser'})
            sql = SearchType.get_sql_by_search_type('one/th_knowledge_article')
            with self.assertRaises(Exception): sql.do_query("UPDATE th_knowledge_article SET name='forbidden'")
            with self.assertRaises(Exception): sql.do_update("UPDATE th_knowledge_article SET name='forbidden'")
            self.assertEqual(self.call('load',identity=published['identity'])['document']['title'],'Published')

    def test_catalog_conflict_and_dependency_deletion(self):
        self.call('initialize')
        section = self.call('save',document={'title':'Guide','kind':'section'})
        article = self.call('save',document={'title':'Read','parentCode':section['identity']})
        with self.assertRaisesRegex(ValueError,'organization changed'):
            self.call('organize',expected_revision=section['catalogRevision'],organization=[{'identity':section['identity'],'sortOrder':1}])
        result = self.call('organize',expected_revision=article['catalogRevision'],organization=[{'identity':article['identity'],'parentCode':'','sortOrder':1}])
        self.assertNotEqual(result['catalogRevision'],article['catalogRevision'])
        groups = self.call('deletion',identity=article['identity'])['groups']
        loaded = self.call('load',identity=article['identity'])
        self.call('delete',identity=article['identity'],expected_revision=loaded['revision'],related_types=[row['search_type'] for row in groups if row['selected']])
        self.assertTrue(self.call('load',identity=article['identity'])['entryMissing'])


if __name__ == '__main__': unittest.main()
