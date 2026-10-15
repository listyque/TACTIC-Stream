"""Native link resolution: identity, saved views, parents, privacy and ACL."""
import ast
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlencode

import test_transport
from pyasm.security.authenticator import hash_password


class NavigationLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_resolution_and_access(self):
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            auth = dict(ticket=ticket, project='one')
            def call(link, status=200, **values):
                req = Request(test_transport.Transport.url + '/admin/navigation-link', data=json.dumps(dict(auth, link=link, **values)).encode(), headers={'Content-Type': 'application/json'})
                try: response = urlopen(req)
                except HTTPError as failure: response = failure
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, status, body)
                    return body.get('result', body)
            key = 'skey://contract/entity?project=one&code=A'
            object = call(key)
            self.assertEqual(object['object']['code'], 'A')
            by_id = call('skey://contract/entity?project_code=one&id=' + str(object['object']['id']))
            self.assertEqual(by_id['object'], object['object'])
            note = proxy.insert(auth, 'sthpw/note', dict(note='Linked private note', login='admin', access='private', process='publish', project_code='one', search_type='contract/entity?project=one', search_code='A'))
            note_link = 'skey://' + note['__search_key__']
            resolved = call(note_link)
            self.assertEqual(resolved['kind'], 'note')
            self.assertEqual(resolved['parent']['code'], 'A')
            self.assertEqual(resolved['process'], 'publish')
            task = proxy.insert(auth, 'sthpw/task', dict(process='publish', project_code='one', search_type='contract/entity?project=one', search_code='A'))
            self.assertEqual(call('skey://' + task['__search_key__'])['parent']['code'], 'A')
            snapshot = proxy.create_snapshot(auth, object['object']['__search_key__'], 'publish')
            resolved = call('skey://' + snapshot['__search_key__'])
            self.assertEqual(resolved['kind'], 'snapshot')
            self.assertEqual(resolved['parent']['code'], 'A')
            self.assertEqual(resolved['preview']['snapshot_key'], snapshot['__search_key__'])
            user = call('skey://sthpw/login?code=admin')
            self.assertEqual(user['object']['login'], 'admin')
            self.assertNotIn('password', user['object'])
            preset = proxy.insert(auth, 'config/widget_config', dict(search_type='contract/entity', view='link_search:linked:contract/entity', category='search_filter', title='Linked entities', config='<config><view name="link_search:linked:contract/entity"><filter><values>{"filters": []}</values></filter></view></config>'))
            saved_link = 'tactic-search://open?' + urlencode(dict(project='one', search_type='contract/entity', view=preset['view']))
            saved = call(saved_link)
            self.assertEqual(saved['kind'], 'saved-search')
            self.assertEqual(saved['preset']['title'], 'Linked entities')
            for value in ('javascript://anything', 'skey://contract/entity', 'tactic-search://other?project=one', '', None, key + '\n'):
                call(value, 400)
            call(key, 403, ticket='invalid')
            call(key, 400, arbitrary=True)
            call('skey://contract/entity?project=two&code=A', 400)
            call('skey://contract/entity?code=missing', 400)
            proxy.insert(auth, 'sthpw/login', dict(login='link_reader', password=hash_password('reader-password')))
            reader = proxy.get_ticket('link_reader', 'reader-password')
            call(key, 403, ticket=reader)
            group = proxy.insert(auth, 'sthpw/login_group', dict(login_group='link_access', access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="view"/></rules>'))
            proxy.insert(auth, 'sthpw/login_in_group', dict(login='link_reader', login_group='link_access'))
            self.assertEqual(call(key, ticket=reader)['object']['code'], 'A')
            call(note_link, 400, ticket=reader)
            proxy.update(auth, note['__search_key__'], dict(access='public'))
            self.assertEqual(call(note_link, ticket=reader)['parent']['code'], 'A')
            proxy.update(auth, group['__search_key__'], dict(access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="deny"/></rules>'))
            call(note_link, 403, ticket=reader)
            call(saved_link, 403, ticket=reader)

    def test_selected_file_in_multi_file_snapshot(self):
        from xmlrpc.client import Binary
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            proxy.upload_file(auth, 'first.txt', Binary(b'First file'))
            snapshot = proxy.simple_checkin(auth, 'contract/entity?project=one&code=A', 'publish/file-menu', 'first.txt', dict(mode='uploaded',create_icon=False))
            proxy.upload_file(auth, 'second.txt', Binary(b'Selected second file'))
            proxy.add_file(auth, snapshot['code'], 'second.txt', 'support', False, 'uploaded')
            files = ast.literal_eval(proxy.query(auth, 'sthpw/file', [('snapshot_code', snapshot['code'])]))
            self.assertEqual(len(files), 2)
            for file in files:
                request = Request(self.url+'/admin/navigation-link', data=json.dumps(dict(auth, link='skey://'+file['__search_key__'])).encode(), headers={'Content-Type':'application/json'})
                with urlopen(request) as response:
                    preview = json.load(response)['result']['preview']
                self.assertEqual(preview['fileCode'], file['code'])
                selected = next(item for item in preview['files'] if item['code'] == preview['fileCode'])
                self.assertTrue(selected['path'].endswith(file['file_name']), selected)
                with urlopen(self.url+selected['href']) as response:
                    self.assertEqual(response.read(), b'First file' if file['type']=='main' else b'Selected second file')

    def test_previews_and_chat_privacy(self):
        from test_messages import Messages
        import uuid
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            def call(values, status=200, actor=auth):
                req = Request(self.url + '/admin/navigation-link', data=json.dumps(dict(actor, **values)).encode(), headers={'Content-Type': 'application/json'})
                try: response = urlopen(req)
                except HTTPError as failure: response = failure
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, status, body)
                    return body.get('result', body)
            key = 'skey://contract/entity?project=one&code=A'
            note = proxy.insert(auth, 'sthpw/note', dict(note='Review\n' + key + '\n' + key, login='admin', access='public', process='publish', project_code='one', search_type='contract/entity?project=one', search_code='A'))
            task = proxy.insert(auth, 'sthpw/task', dict(process='publish', project_code='one', search_type='contract/entity?project=one', search_code='A'))
            snapshot = proxy.create_snapshot(auth, 'contract/entity?project=one&code=A', 'publish')
            keys = [key, 'skey://' + note['__search_key__'], 'skey://' + task['__search_key__'], 'skey://' + snapshot['__search_key__'], 'skey://sthpw/login?code=admin', 'skey://sthpw/project?code=one', 'skey://contract/entity?project=one&code=missing']
            result = call({'keys': keys + [key]})['previews']
            self.assertEqual([row['kind'] for row in result], ['sobject', 'note', 'task', 'snapshot', 'user', 'project', 'sobject'])
            self.assertEqual(result[0]['status'], 'ready', result)
            self.assertEqual(result[1]['body'], 'Review')
            self.assertEqual(result[1]['nestedPreviewCount'], 1)
            self.assertEqual(result[1]['nestedPreviews'][0]['searchKey'], key)
            self.assertEqual(result[3]['version'], 'v{:03d}'.format(snapshot['version']))
            self.assertEqual(result[-1]['status'], 'error')
            self.assertNotIn('password', json.dumps(result))
            orphan = proxy.create_snapshot(auth, 'contract/entity?project=one&code=A', 'orphan')
            # Imported legacy rows can outlive their parent metadata.
            with test_transport.Transport.store.connection(write=True) as db:
                db.execute("UPDATE snapshot SET search_type='' WHERE code=?", (orphan['code'],))
            self.assertEqual(call({'keys': ['skey://' + orphan['__search_key__']]})['previews'][0]['status'], 'ready')
            foreign = call({'keys': ['skey://contract/entity?project=two&code=A']})['previews'][0]
            self.assertEqual(foreign['status'], 'ready', foreign)
            self.assertIn('two', foreign['detail'])
            from xmlrpc.client import Binary
            proxy.upload_file(auth, 'skey-note.txt', Binary(b'Attachment on a linked note'))
            proxy.simple_checkin(auth, note['__search_key__'], 'attachment/plain', 'skey-note.txt', 'file', 'Linked note file', False, 'main', True, None, {}, None, False, {}, True, False)
            attached_note = call({'keys': [keys[1]]})['previews'][0]
            self.assertEqual(attached_note['attachmentCount'], 1, attached_note)
            self.assertEqual(attached_note['attachments'][0]['extension'], 'TXT')
            for invalid in ([], ['javascript://bad'], [key] * 51, [None], [key + '\n']):
                call({'keys': invalid}, 400)
            self.assertEqual(call({'keys': ['skey://[bad']})['previews'][0]['status'], 'error')
            call({'link': key, 'keys': [key]}, 400)
            helper = Messages(); helper.url = self.url
            helper.call('initialize', auth)
            proxy.insert(auth, 'sthpw/login', dict(login='preview_stranger', password=hash_password('preview-password')))
            stranger = dict(ticket=proxy.get_ticket('preview_stranger', 'preview-password'), project='one')
            proxy.insert(auth, 'sthpw/login_group', dict(login_group='preview_access', access_rules='<rules><rule group="project" code="one" access="allow"/></rules>'))
            proxy.insert(auth, 'sthpw/login_in_group', dict(login='preview_stranger', login_group='preview_access'))
            chat = helper.call('create', auth)['conversationId']
            message = helper.call('send', auth, message_code=chat, message='Private preview body')['message']
            link = 'skey://' + message['__search_key__']
            self.assertEqual(call({'link': link})['kind'], 'message')
            self.assertEqual(call({'keys': [link]})['previews'][0]['body'], 'Private preview body')
            call({'link': link}, 403, stranger)
            denied = call({'keys': [link]}, actor=stranger)['previews'][0]
            self.assertEqual(denied['status'], 'error'); self.assertNotIn('body', denied)
            attachment = helper.upload(auth, chat, str(uuid.uuid4()), 'secret.txt', b'Private file')
            helper.call('send', auth, message_code=chat, message='Attachment', attachment_keys=[attachment['__search_key__']])
            attachment_link = 'skey://' + attachment['__search_key__']
            private = call({'keys': [attachment_link]})['previews'][0]
            self.assertEqual(private['status'], 'ready', private)
            self.assertEqual(private['privateAttachment']['chat'], chat)
            self.assertFalse(private['previewUrl'])
            self.assertNotIn('href', json.dumps(private))
            self.assertEqual(call({'link': attachment_link})['kind'], 'chat-attachment')
            call({'link': attachment_link}, 403, stranger)
            self.assertNotIn('privateAttachment', call({'keys': [attachment_link]}, actor=stranger)['previews'][0])
            member_chat = helper.call('create', auth, recipients=['preview_stranger'])['conversationId']
            member_message = helper.call('send', auth, message_code=member_chat, message='Visible to the participant')['message']
            member_preview = call({'keys': ['skey://' + member_message['__search_key__']]}, actor=stranger)['previews'][0]
            self.assertEqual(member_preview['status'], 'ready', member_preview)
            self.assertEqual(member_preview['body'], 'Visible to the participant')
            self.assertEqual(call({'keys': ['skey://sthpw/login?code=admin']}, actor=stranger)['previews'][0]['status'], 'error')
            helper.call('delete-message', auth, message_log_code=message['__search_key__'])
            call({'link': link}, 403)
            self.assertEqual(call({'keys': [link]})['previews'][0]['status'], 'error')


if __name__ == '__main__':
    unittest.main()
