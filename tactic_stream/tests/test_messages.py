"""Fixed Messages operations through HTTP, native storage and ordinary user ACLs."""
import ast
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from xmlrpc.client import Fault

import test_transport
from pyasm.security.authenticator import hash_password


class Messages(unittest.TestCase):
    def setUp(self):
        test_transport.Transport.setUpClass()
        self.url = test_transport.Transport.url

    def tearDown(self):
        test_transport.Transport.tearDownClass()

    def call(self, action, auth, status=200, **arguments):
        request = Request(self.url + '/admin/messages/' + action,
            data=json.dumps(dict(auth, **arguments)).encode(), headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            body = json.load(response)
            self.assertEqual(response.status, status, body)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return body.get('result', body)

    def upload(self, auth, chat, token, filename, content, status=200, purpose='attachment'):
        boundary = 'chat-test-boundary'
        body = b''
        for name, value in dict(auth, message_code=chat, token=token, purpose=purpose).items():
            body += ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode()
        body += ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n' % (boundary, filename)).encode() + content + ('\r\n--%s--\r\n' % boundary).encode()
        request = Request(self.url + '/admin/messages/upload', data=body,
            headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            result = json.load(response)
            self.assertEqual(response.status, status, result)
            return result.get('result', result)

    def test_initialization_matches_handler_and_reads_leave_schema_unchanged(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')

            def knowledge():
                request = Request(self.url + '/admin/knowledge/list',
                    data=json.dumps(auth).encode(), headers={'Content-Type': 'application/json'})
                with urlopen(request, timeout=20) as response:
                    return json.load(response)['result']

            self.assertFalse(knowledge()['initialized'])
            self.call('list', auth)
            self.assertFalse(knowledge()['initialized'])
            self.assertTrue(self.call('initialize', auth)['initialized'])
            self.assertTrue(knowledge()['initialized'])
            self.assertTrue(self.call('initialize', auth)['initialized'])
            self.assertEqual(knowledge()['catalog'], [])

    def test_attachment_checkin_and_private_download(self):
        import base64
        import uuid
        with test_transport.Transport.proxy(self) as proxy:
            admin = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            self.call('initialize', admin)
            rules = '<rules><rule group="project" code="one" access="allow"/>'
            rules += ''.join('<rule group="search_type" code="sthpw/%s" access="%s"/>' % (kind, access)
                for kind, access in [('login', 'view'), ('login_in_group', 'view')] + [(kind, 'edit') for kind in ('message', 'message_log', 'subscription', 'connection', 'snapshot', 'file')]) + '</rules>'
            proxy.insert(admin, 'sthpw/login_group', dict(code='chat_uploaders', login_group='chat_uploaders', access_rules=rules))
            for name in ('uploader', 'download_reader'):
                proxy.insert(admin, 'sthpw/login', dict(code=name, login=name, password=hash_password('chat-files-password')))
                proxy.insert(admin, 'sthpw/login_in_group', dict(login=name, login_group='chat_uploaders'))
            actor = dict(ticket=proxy.get_ticket('uploader', 'chat-files-password'), project='one')
            reader = dict(ticket=proxy.get_ticket('download_reader', 'chat-files-password'), project='one')
            chat = self.call('create', actor, recipients=['admin'])['conversationId']
            token = str(uuid.uuid4())
            png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7u0AAAAASUVORK5CYII=')
            snapshot = self.upload(actor, chat, token, 'test.png', png)
            self.assertEqual(snapshot['search_type'], 'sthpw/message')
            self.assertEqual(snapshot['search_code'], chat)
            self.assertEqual(snapshot['version'], 1)
            self.assertTrue(snapshot['__files__'])
            self.assertEqual(self.upload(actor, chat, token, 'test.png', png)['code'], snapshot['code'])
            self.assertEqual(self.upload(actor, chat, token, 'changed.txt', b'changed', status=400)['error_code'], 'invalid_request')
            file = next(row for row in snapshot['__files__'] if row['type'] == 'preview')
            arguments = dict(message_code=chat, snapshot_code=snapshot['code'], file_code=file['code'])
            self.call('file', reader, status=403, **arguments)
            self.call('file', admin, status=403, **arguments)
            message = self.call('send', actor, message_code=chat, message='', attachment_keys=[snapshot['__search_key__']])['message']
            request = Request(self.url + '/admin/messages/file', data=json.dumps(dict(admin, **arguments)).encode(), headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertEqual(response.read(), png)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['Content-Type'], 'image/png')
            info = self.call('file-info', actor, **arguments)
            self.assertEqual(info['snapshot']['code'], snapshot['code'])
            self.assertEqual(info['file']['code'], file['code'])
            self.assertEqual(info['filename'], 'test.png')
            self.assertNotIn('\\', info['path'])
            self.assertTrue(info['path'].endswith('/' + file['file_name']))
            self.call('file-info', reader, status=403, **arguments)
            personal = self.call('create', admin)['conversationId']
            self.call('forward', admin, message_log_keys=[message['__search_key__']], target_message_codes=[personal])
            forwarded = {**admin, **arguments, 'message_code': personal}
            with urlopen(Request(self.url + '/admin/messages/file', data=json.dumps(forwarded).encode(), headers={'Content-Type': 'application/json'})) as response:
                self.assertEqual(response.read(), png)
            self.assertEqual(self.call('files', admin, message_code=personal)['snapshots'][0]['code'], snapshot['code'])
            preview = self.upload(actor, chat, str(uuid.uuid4()), 'avatar.png', png, purpose='preview')
            self.call('file', actor, status=403, **dict(arguments, file_code=preview['__files__'][0]['code']))
            preview_file = preview['__files__'][0]
            preview_args = dict(admin, message_code=chat, snapshot_code=preview['code'], file_code=preview_file['code'])
            with urlopen(Request(self.url + '/admin/messages/file', data=json.dumps(preview_args).encode(), headers={'Content-Type': 'application/json'})) as response:
                self.assertEqual(response.read(), png)
            relative_dir = file['relative_dir']
            proxy.update(admin, 'sthpw/file?code=' + file['code'], {'relative_dir': '../../outside-chat-repository'})
            self.call('file', actor, status=403, **arguments)
            self.call('file-info', actor, status=403, **arguments)
            proxy.update(admin, 'sthpw/file?code=' + file['code'], {'relative_dir': relative_dir})
            self.call('delete-message', actor, message_log_code=message['__search_key__'])
            self.call('file', admin, status=403, **arguments)
            self.call('file', actor, status=403, **arguments)
            self.call('file-info', actor, status=403, **arguments)
            self.upload(reader, chat, str(uuid.uuid4()), 'forbidden.txt', b'no', status=403)
            failed = str(uuid.uuid4())
            from tactic_stream.server.messages_files import FileCheckin
            execute = FileCheckin.execute
            def fail_late(checkin):
                from pyasm.common import Container, Environment
                from pyasm.biz import Project
                from pyasm.search import FileUndo, SearchType
                from pyasm.common.errors import SecurityException
                from pathlib import Path
                self.assertTrue(Container.get('Chat:attachment'))
                self.assertFalse(Environment.get_security().is_admin())
                with self.assertRaises(SecurityException):
                    Project.set_project('two')
                with self.assertRaises(SecurityException):
                    FileUndo.create(str(Path(Environment.get_tmp_dir()) / 'scope-escape.txt'))
                wrong = SearchType.create('sthpw/snapshot')
                wrong.set_value('search_type', 'sthpw/message')
                wrong.set_value('search_code', personal)
                with self.assertRaises(SecurityException):
                    wrong.commit(triggers=False)
                execute(checkin)
                raise ValueError('late attachment failure')
            before = len(ast.literal_eval(proxy.query(admin, 'sthpw/snapshot')))
            with patch.object(FileCheckin, 'execute', fail_late):
                self.upload(actor, chat, failed, 'rollback.txt', b'rollback', status=400)
            self.assertEqual(len(ast.literal_eval(proxy.query(admin, 'sthpw/snapshot'))), before)
            self.assertEqual(self.upload(actor, chat, failed, 'rollback.txt', b'rollback')['version'], 1)

    def test_regular_user_lifecycle_and_boundaries(self):
        with test_transport.Transport.proxy(self) as proxy:
            admin = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            self.assertFalse(self.call('list', admin)['initialized'])
            self.assertFalse(self.call('list', admin)['initialized'], 'No automatic DDL on read')
            self.assertTrue(self.call('initialize', admin)['initialized'])
            self.assertTrue(self.call('initialize', admin)['initialized'], 'Initialization is idempotent')
            read_rules = ''.join('<rule group="search_type" code="sthpw/%s" access="view"/>' % kind
                for kind in ('login', 'login_in_group'))
            read_rules += '<rule group="search_type" code="sthpw/login_group" access="deny"/>'
            project_rule = '<rule group="project" code="one" access="allow"/>'
            for group, access in (('chat_users', 'edit'), ('chat_readers', 'view')):
                rules = ''.join('<rule group="search_type" code="sthpw/%s" access="%s"/>' % (kind, access)
                    for kind in ('message', 'message_log', 'subscription', 'connection'))
                proxy.insert(admin, 'sthpw/login_group', dict(code=group, login_group=group,
                    access_rules='<rules>' + project_rule + read_rules + rules + '</rules>'))
            actors = {}
            for login in ('alice', 'bob', 'outsider', 'reader'):
                proxy.insert(admin, 'sthpw/login', dict(code=login, login=login, password=hash_password('chat-password')))
                proxy.insert(admin, 'sthpw/login_in_group', dict(login=login,
                    login_group='chat_readers' if login == 'reader' else 'chat_users'))
                actors[login] = dict(ticket=proxy.get_ticket(login, 'chat-password'), project='one')
            alice, bob, outsider, reader = (actors[name] for name in ('alice', 'bob', 'outsider', 'reader'))
            self.assertTrue(self.call('list', dict(alice, project=''))['initialized'],
                            'Global conversations work before choosing a project')
            self.call('initialize', dict(alice, project=''), status=403)
            self.call('list', dict(alice, project=None), status=400)
            self.call('list', dict(alice, project='missing-project'), status=400)
            self.assertFalse(self.call('list', alice)['canCreateGroup'])
            self.assertTrue(self.call('list', alice)['permissions']['send'])
            self.assertFalse(any(self.call('list', reader)['permissions'].values()))
            self.call('initialize', alice, status=403)
            people = self.call('people', alice)['users']
            self.assertIn('bob', [row['login'] for row in people])
            self.assertFalse(any('password' in row or 'data' in row for row in people))
            self.assertTrue(next(row for row in people if row['login'] == 'alice')['current'])
            self.assertFalse(next(row for row in people if row['login'] == 'bob')['current'])
            self.assertTrue(all(row['groups'] == [] and row['primaryGroup'] == 'Ungrouped' for row in people),
                            'Group labels are hidden when login_group view is not allowed')
            admin_people = self.call('people', admin)['users']
            self.assertEqual(next(row for row in admin_people if row['login'] == 'alice')['groups'], ['Chat Users'])
            self.assertFalse(any('accessRules' in row or 'access_rules' in row for row in admin_people))
            self.call('create', alice, status=403, recipients=['bob', 'reader'], title='Not a supervisor')
            chat = self.call('create', alice, recipients=['bob'])['conversationId']
            self.assertEqual(self.call('create', alice, recipients=['bob', 'bob']),
                             dict(conversationId=chat, created=False))
            before = next(row for row in self.call('list', alice)['conversations'] if row['conversationId'] == chat)
            first = self.call('send', alice, message_code=chat, message='Hello')['message']
            second = self.call('send', bob, message_code=chat, message='Reply', reply_to=first['__search_key__'])['message']
            after = next(row for row in self.call('list', alice)['conversations'] if row['conversationId'] == chat)
            self.assertEqual(after['createdBy'], 'alice')
            self.assertEqual(after['createdAt'], before['createdAt'])
            history = self.call('history', alice, message_code=chat)
            self.assertEqual(len(history['messages']), 2)
            self.assertEqual(second['login'], 'bob')
            self.call('history', outsider, status=403, message_code=chat)
            self.call('send', outsider, status=403, message_code=chat, message='Leak')
            self.call('reaction', outsider, status=403, message_log_code=first['__search_key__'], emoji='👍')
            self.call('edit', bob, status=403, message_log_code=first['__search_key__'], message='Hijacked')
            self.call('rename', bob, status=403, message_code=chat, title='Hijacked')
            self.call('members', alice, status=403, message_code=chat, recipients=['reader'])
            self.call('delete', alice, status=403, message_code=chat)
            self.call('rename', alice, message_code=chat, title='Renamed')
            self.call('edit', alice, message_log_code=first['__search_key__'], message='Edited')
            self.call('reaction', bob, message_log_code=first['__search_key__'], emoji='👍')
            self.call('pin', alice, message_log_code=first['__search_key__'])
            self.call('read', bob, message_code=chat, timestamp=first['timestamp'][:19])
            self.call('history', bob, status=400, message_code=chat, limit=True)
            self.call('send', alice, status=400, message_code=chat, message='Bad', code='return 1')
            self.call('reaction', alice, status=400, message_log_code='sthpw/login?code=bob', emoji='👍')
            self.call('pin', alice, status=400, message_log_code='sthpw/message_log?project=one&code=bad')
            self.call('read', bob, status=400, message_code=chat, timestamp='9999')
            personal = self.call('create', bob, recipients=[])['conversationId']
            # A fresh native conversation has NULL status, and must still be a valid destination.
            forwarded = self.call('forward', bob, message_log_keys=[first['__search_key__']],
                                  target_message_codes=[personal])
            self.assertTrue(forwarded)
            self.assertEqual(len(self.call('history', bob, message_code=personal)['messages']), 1)
            self.assertEqual(self.call('clear', bob, message_code=personal)['cleared'], 1)
            snapshot = proxy.create_snapshot(admin, 'sthpw/message?code=' + chat, 'attachment', 'file')
            attached = self.call('send', alice, message_code=chat, message='',
                                 attachment_keys=[snapshot['__search_key__']])['message']
            self.assertTrue(self.call('authorize-attachment', bob, message_code=chat,
                                     snapshot_code=snapshot['code'])['allowed'])
            self.call('authorize-attachment', outsider, status=403, message_code=chat, snapshot_code=snapshot['code'])
            self.call('send', alice, status=400, message_code=chat, message='Wrong type',
                      attachment_keys=['sthpw/login?code=bob'])
            self.call('delete-message', alice, message_log_code=attached['__search_key__'])
            self.assertFalse(self.call('authorize-attachment', bob, message_code=chat,
                                      snapshot_code=snapshot['code'])['allowed'])
            self.call('delete-message', alice, message_log_code=first['__search_key__'])
            self.call('reaction', alice, status=403, message_log_code=first['__search_key__'], emoji='👍')
            # Read-only members see messages without receipt or summary repair writes.
            readonly_chat = self.call('create', alice, recipients=['reader'])['conversationId']
            readonly_message = self.call('send', alice, message_code=readonly_chat, message='Read only')['message']
            stored_before = ast.literal_eval(proxy.query(admin, 'sthpw/message_log', [('code', readonly_message['code'])]))[0]
            self.assertEqual(len(self.call('history', reader, message_code=readonly_chat)['messages']), 1)
            stored_after = ast.literal_eval(proxy.query(admin, 'sthpw/message_log', [('code', readonly_message['code'])]))[0]
            self.assertEqual(stored_before, stored_after)
            self.call('send', reader, status=403, message_code=readonly_chat, message='Forbidden')
            self.call('read', reader, status=403, message_code=readonly_chat, timestamp=readonly_message['timestamp'][:19])
            long_body = 'Long history ' * 1500
            long_message = self.call('send', alice, message_code=chat, message=long_body)['message']
            self.call('edit', alice, message_log_code=long_message['__search_key__'], message='Short now')
            stored = ast.literal_eval(proxy.query(admin, 'sthpw/message_log', [('code', long_message['code'])]))[0]
            self.assertTrue(stored['metadata'].startswith('zlib:'))
            self.call('reaction', bob, message_log_code=long_message['__search_key__'], emoji='👍')
            self.call('edit', alice, message_log_code=long_message['__search_key__'], message='Second edit')
            edited = next(row for row in self.call('history', bob, message_code=chat)['messages']
                          if row['code'] == long_message['code'])
            self.assertEqual(edited['__edit_history__'][0]['body'], long_body)
            self.assertEqual(edited['__edit_history__'][1]['body'], 'Short now')
            self.assertTrue(edited['__reactions__'])
            # Fixed chat operations cannot grant generic Python, object CRUD or security writes.
            for auth in (alice, bob, reader):
                for method, arguments in (
                    (proxy.execute_python_script, ('', {'code': 'return 1'})),
                    (proxy.insert, ('sthpw/message', {'code': 'UNAUTHORIZED'})),
                    (proxy.update, ('sthpw/login?code=bob', {'first_name': 'Hijacked'}))):
                    with self.assertRaises(Fault) as denied:
                        method(auth, *arguments)
                    self.assertEqual(denied.exception.faultCode, 403)
            # Native transaction rollback includes a successful send before a late failure.
            from tactic_stream.server import messages_query
            original = messages_query.send_chat_message

            def fail_late(**arguments):
                from pyasm.biz import Project
                from pyasm.common import Container, Environment
                from pyasm.search.sql import DbContainer, SqlException
                from pyasm.common.errors import SecurityException
                from tactic_client_lib import TacticServerStub
                self.assertEqual(Project.get_project_code(), 'one')
                self.assertEqual(Environment.get_user_name(), 'alice')
                self.assertFalse(Environment.get_security().is_admin())
                self.assertTrue(Container.get('Chat:writing'))
                server = TacticServerStub.get(protocol='local')
                with self.assertRaises(SecurityException):
                    server.insert('sthpw/project', {'code': 'ESCAPED_SCOPE'})
                sql = DbContainer.get('sthpw')
                for statement in ("UPDATE login SET first_name='Escaped' WHERE login='bob'",
                                  'CREATE TABLE escaped_scope (id integer)'):
                    with self.assertRaises(SqlException):
                        sql.do_update(statement)
                original(**arguments)
                raise ValueError('Late send failure')

            before = self.call('history', bob, message_code=chat)
            with patch.object(messages_query, 'send_chat_message', fail_late):
                self.call('send', alice, status=400, message_code=chat, message='Must roll back')
            self.assertEqual(self.call('history', bob, message_code=chat), before)
            from tactic_stream.server import messages
            original_request = messages.messages_request
            restored = []

            def check_scope(*arguments):
                from pyasm.biz import Project
                from pyasm.common import Container, Environment
                previous, project = Container.get('Chat:writing'), Project.get_project_code()
                try:
                    return original_request(*arguments)
                finally:
                    restored.append((Container.get('Chat:writing') == previous,
                                     Project.get_project_code() == project,
                                     Environment.get_security().is_admin()))

            with patch.object(messages, 'messages_request', check_scope):
                self.call('send', alice, message_code=chat, message='Scope restoration')
                self.call('history', alice, status=403, message_code='Missing chat')
            self.assertEqual(restored, [(True, True, False), (True, True, False)])
            # Serialized exact-participant creation cannot duplicate subscriptions/chats.
            with ThreadPoolExecutor(max_workers=2) as executor:
                created = list(executor.map(lambda _: self.call('create', outsider, recipients=['bob']), range(2)))
            self.assertEqual(created[0]['conversationId'], created[1]['conversationId'])
            self.assertEqual(sorted(row['created'] for row in created), [False, True])
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(lambda actor: self.call('reaction', actor,
                    message_log_code=long_message['__search_key__'], emoji='❤️'), [alice, bob]))
            reacted = next(row for row in self.call('history', alice, message_code=chat)['messages']
                           if row['code'] == long_message['code'])
            self.assertEqual(set(reacted['__reactions__']['❤️']), {'alice', 'bob'})
            group = self.call('create', admin, recipients=['alice', 'bob'], title='Group')['conversationId']
            changed = self.call('members', admin, message_code=group, recipients=['reader'], replace=True)
            self.assertEqual(set(changed['removed']), {'alice', 'bob'})
            self.call('history', alice, status=403, message_code=group)
            self.call('delete', admin, message_code=group)
            self.call('history', reader, status=403, message_code=group)
            proxy.insert(admin, 'sthpw/login_group', dict(code='shot_supervisor', login_group='shot_supervisor'))
            proxy.insert(admin, 'sthpw/login_in_group', dict(login='outsider', login_group='shot_supervisor'))
            supervisor_group = self.call('create', outsider, recipients=['alice', 'bob'], title='Supervisor group')['conversationId']
            self.call('members', outsider, message_code=supervisor_group, recipients=['alice'], replace=True)
            self.call('history', bob, status=403, message_code=supervisor_group)
            self.call('delete', outsider, message_code=supervisor_group)
            # Deleted conversation subscriptions cannot be used to read or send.
            proxy.update(admin, 'sthpw/message?code=' + chat, {'status': 'deleted'})
            self.call('history', alice, status=403, message_code=chat)
            self.call('send', alice, status=403, message_code=chat, message='Deleted chat')
            proxy.update(admin, 'sthpw/login_group?code=chat_readers', {'access_rules':
                '<rules>' + project_rule + read_rules + '<rule group="search_type" code="sthpw/message" access="deny"/></rules>'})
            self.call('list', reader, status=403)
