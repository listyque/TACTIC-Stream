"""Native Handler update batch, access boundaries and actual XML-RPC source comparison."""
import ast
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xmlrpc.client import Fault

import test_transport
from pyasm.security.authenticator import hash_password


class ServerUpdates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_batch(self):
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            auth = dict(ticket=ticket, project='one')

            def call(status=200, **values):
                request = Request(self.url + '/admin/server-updates', data=json.dumps(dict(auth, **values)).encode(),
                    headers={'Content-Type': 'application/json'})
                try:
                    response = urlopen(request)
                except HTTPError as failure:
                    response = failure
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, status, body)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    return body.get('result', body)

            note = proxy.insert(auth, 'sthpw/note', dict(project_code='one', search_type='contract/entity',
                search_code='A', process='publish', login='admin', note='Batch public note', access='public'))
            private = proxy.insert(auth, 'sthpw/note', dict(project_code='one', search_type='contract/entity',
                search_code='A', process='publish', login='admin', note='Batch private note', access='private'))
            initial = call()
            self.assertTrue(any(row['code'] == note['code'] for row in initial['activity']))
            self.assertFalse(initial['messagesInitialized'])
            self.assertFalse(initial['presenceHeartbeatApplied'])
            self.assertEqual(initial['presence'], [])
            for key in ('messages', 'reactions', 'cacheChanges', 'cacheRetired'):
                self.assertEqual(initial[key], [])
            self.assertIn('utcStarted', initial['serverClock'])
            cursor = max(row['__event_timestamp__'] for row in initial['activity'])
            unchanged = call(activity_after=cursor, cache_after=initial['cacheCursor'])
            self.assertEqual(unchanged['activity'], [])
            self.assertEqual(unchanged['cacheChanges'], [])
            # Execute the unchanged current Handler procedure over the native XML-RPC API.
            source = Path('D:/code/th_codex/thlib/tactic_query.py').read_text(encoding='utf-8-sig')
            node = next(row for row in ast.parse(source).body if isinstance(row, ast.FunctionDef) and row.name == 'query_server_updates')
            code = '\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
            original = proxy.execute_python_script(auth, '', {'code': code + "\nreturn query_server_updates(project_code='one', include_cache_changes=True)"})['info']
            for key in ('messages', 'reactions', 'activity', 'presence', 'cacheChanges', 'cacheRetired', 'messagesInitialized'):
                self.assertEqual(initial[key], original[key], key)

            with test_transport.Transport.store.connection(write=True) as db:
                db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)',
                    ('batch_reader', 'batch_reader', hash_password('reader-password')))
            reader = proxy.get_ticket('batch_reader', 'reader-password')
            call(403, ticket=reader)
            group = proxy.insert(auth, 'sthpw/login_group', dict(login_group='batch_access',
                access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="view"/></rules>'))
            proxy.insert(auth, 'sthpw/login_in_group', dict(login='batch_reader', login_group='batch_access'))
            from pyasm.search.search import RequestContext, request_context
            from tactic_stream.server.api import Api
            from tactic_stream.server.server_updates import server_updates_request
            with request_context(RequestContext(test_transport.Transport.store, 'batch_reader', 'one')):
                Api(test_transport.Transport.store).auth.bind_security('batch_reader', reader)
                server_updates_request({})
            public = call(ticket=reader)
            self.assertTrue(any(row['code'] == note['code'] for row in public['activity']))
            self.assertNotIn(private['code'], [row.get('code') for row in public['activity']])
            self.assertFalse(public['presenceHeartbeatApplied'])
            proxy.update(auth, group['__search_key__'], dict(access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="deny"/></rules>'))
            self.assertFalse(any(row.get('search_type') == 'contract/entity' for row in call(ticket=reader)['activity']))
            call(403, ticket='invalid')
            call(400, project='missing')
            for values in ({'message_after': 1}, {'activity_after': None}, {'cache_after': 'a' * 1025},
                           {'reaction_after': []}, {'presence_ttl': True}, {'presence_ttl': 5}, {'include_messages': False}):
                call(400, **values)

            # Explicit schema setup through native commands, never automatic DDL from a poll.
            for kind in ('sthpw/message', 'sthpw/message_log'):
                proxy.add_column_to_search_type(auth, kind, 'metadata', 'json')
            conversation = proxy.insert(auth, 'sthpw/message', dict(code='BATCH_CHAT', category='chat',
                login='admin', project_code='sthpw', message='Chat', metadata={}))
            proxy.insert(auth, 'sthpw/subscription', dict(category='chat', login='admin', message_code=conversation['code']))
            proxy.insert(auth, 'sthpw/subscription', dict(category='chat', login='batch_reader', message_code=conversation['code']))
            proxy.insert(auth, 'sthpw/message_log', dict(code='BATCH_PRIVATE', category='chat', login='admin',
                project_code='sthpw', message_code='PRIVATE_CHAT', message='Unsubscribed message', metadata={}))
            message = proxy.insert(auth, 'sthpw/message_log', dict(code='BATCH_MESSAGE', category='chat', login='batch_reader',
                project_code='sthpw', message_code=conversation['code'], message='Shared message', status='sent'),
                {'reactions': {'like': ['admin']}, 'delivery': {'sender': 'batch_reader',
                    'recipients': {'admin': {'deliveredAt': '', 'readAt': ''}}}})
            proxy.update(auth, message['__search_key__'], {}, {'reactions': {'like': ['admin']}})
            chat = call()
            self.assertTrue(chat['messagesInitialized'])
            self.assertTrue(chat['presenceHeartbeatApplied'])
            self.assertTrue(any(row['login'] == 'admin' and row['online'] for row in chat['presence']))
            self.assertEqual([row['code'] for row in chat['messages']], [message['code']])
            self.assertEqual(chat['messages'][0]['__delivery__']['status'], 'delivered', chat['messages'][0]['metadata'])
            next_chat = call(message_after=chat['messages'][0]['__event_timestamp__'], reaction_after=chat['reactionCursor'])
            self.assertEqual(next_chat['messages'], [])
            self.assertEqual(len([row for row in next_chat['presence'] if row['login'] == 'admin']), 1)
            self.assertTrue(any(row['reactions'] == {'like': ['admin']} for row in chat['reactions']),
                proxy.execute_python_script(auth, '', {'code': "from pyasm.search import Search\nreturn [(row.get_value('search_type'), row.get_value('search_code')) for row in Search('sthpw/change_timestamp').get_sobjects() if 'message' in str(row.get_value('search_type'))]"})['info'])
            reader_chat = call(ticket=reader)
            self.assertEqual([row['code'] for row in reader_chat['messages']], [message['code']])
            self.assertFalse(reader_chat['presenceHeartbeatApplied'])
            journal_count = "from pyasm.search import Search\nreturn Search('sthpw/transaction_log').get_count()"
            journals = proxy.execute_python_script(auth, '', {'code': journal_count})['info']
            call()
            self.assertEqual(proxy.execute_python_script(auth, '', {'code': journal_count})['info'], journals,
                'A presence heartbeat must not create an empty Undo transaction')
            native_state = "from pyasm.search import Search\nreturn [(row.get_value('metadata'), row.get_value('timestamp')) for row in Search('sthpw/message_log').get_sobjects() if row.get_code() == 'BATCH_MESSAGE']"
            before = proxy.execute_python_script(auth, '', {'code': native_state})['info']
            with self.assertRaises(Fault):
                proxy.execute_python_script(auth, '', {'code': "from pyasm.search import Search\nrow = Search.get_by_code('sthpw/message_log', 'BATCH_MESSAGE')\nrow.set_metadata_value('reactions', {'bad': ['admin']})\nrow.commit()\nraise ValueError('Rollback chat update')"})
            self.assertEqual(proxy.execute_python_script(auth, '', {'code': native_state})['info'], before)


if __name__ == '__main__':
    unittest.main()
