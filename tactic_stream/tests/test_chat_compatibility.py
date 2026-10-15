"""Current Handler chat procedures, unchanged, over the actual XML-RPC transport."""
import ast
import json
from pathlib import Path
import unittest
from xmlrpc.client import Fault

import test_transport
from pyasm.security.authenticator import hash_password


class ChatCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path('D:/code/th_codex/thlib/tactic_query.py').read_text(encoding='utf-8-sig')
        cls.procedures = {
            node.name: '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
            and ('chat' in node.name and node.name != 'query_server_updates')
        }
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_conversation_lifecycle(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='sthpw')

            def call(name, actor=auth, **kwargs):
                code = self.procedures[name] + '\nreturn ' + name + '(**params)'
                value = proxy.execute_python_script(actor, '', dict(code=code, params=kwargs))['info']
                return json.loads(value) if isinstance(value, str) else value

            database = proxy.execute_python_script(auth, '', {'code': """
from pyasm.search import Search
search = Search('sthpw/message_log')
return {'type': search.get_database_type(),
        'impl': search.get_database_impl().get_database_type(),
        'parameter': search.get_database_impl().get_parameter()}
"""})['info']
            self.assertEqual(database, dict(type='Sqlite', impl='Sqlite', parameter='?'))
            initial = call('query_chat_conversations')
            self.assertFalse(initial['initialized'])
            self.assertEqual(initial['conversations'], [])
            self.assertEqual({row['searchType'] for row in initial['missingColumns']},
                             {'sthpw/message', 'sthpw/message_log'})
            self.assertFalse(call('query_chat_conversations')['initialized'], 'Reading must not perform DDL')
            # Handler's explicit initialization adds these two columns via the core API.
            for kind in ('sthpw/message', 'sthpw/message_log'):
                proxy.add_column_to_search_type(auth, kind, 'metadata', 'text')
            self.assertTrue(call('query_chat_conversations')['initialized'])
            for invalid in ('{}', [], None):
                with self.assertRaises(Fault) as rejected:
                    proxy.insert(auth, 'sthpw/message', dict(code='INVALID_METADATA', metadata=invalid))
                self.assertEqual(rejected.exception.faultCode, 400)
            self.assertTrue(proxy.execute_python_script(auth, '', {'code':
                "from pyasm.search import Search\nreturn Search.get_by_code('sthpw/message', 'INVALID_METADATA') is None"})['info'])
            for login in ('chat_bob', 'chat_carol', 'chat_outsider'):
                proxy.insert(auth, 'sthpw/login', dict(code=login, login=login, password=hash_password('chat-password')))
                proxy.insert(auth, 'sthpw/login_in_group', dict(login=login, login_group='admin'))
            bob = dict(ticket=proxy.get_ticket('chat_bob', 'chat-password'), project='sthpw')
            outsider = dict(ticket=proxy.get_ticket('chat_outsider', 'chat-password'), project='sthpw')
            proxy.insert(auth, 'sthpw/login', dict(code='chat_reader', login='chat_reader', password=hash_password('chat-password')))
            reader = dict(ticket=proxy.get_ticket('chat_reader', 'chat-password'), project='sthpw')
            # Arbitrary Python is still deliberately admin-only in this transport.
            with self.assertRaises(Fault) as denied:
                call('query_chat_conversations', actor=reader)
            self.assertEqual(denied.exception.faultCode, 403)
            personal = call('create_chat_conversation', recipients=[])['conversationId']
            self.assertFalse(call('create_chat_conversation', recipients=[])['created'])
            created = call('create_chat_conversation', recipients=['chat_bob'])
            chat = created['conversationId']
            self.assertTrue(created['created'])
            self.assertEqual(call('create_chat_conversation', recipients=['chat_bob', 'chat_bob']),
                             dict(conversationId=chat, created=False))
            for name in ('query_chat_history', 'send_chat_message', 'mark_chat_read'):
                values = dict(message_code=chat)
                if name == 'send_chat_message':
                    values['message'] = 'Forbidden'
                if name == 'mark_chat_read':
                    values['timestamp'] = '2099-01-01 00:00:00'
                with self.assertRaisesRegex(Fault, 'not a chat participant'):
                    call(name, actor=outsider, **values)
            self.assertEqual(call('query_chat_conversations', actor=outsider)['conversations'], [])
            with self.assertRaisesRegex(Fault, 'Unknown TACTIC login'):
                call('create_chat_conversation', recipients=['missing'])
            self.assertEqual(len(call('query_chat_conversations')['conversations']), 2)
            with self.assertRaisesRegex(Fault, 'Group chat title is required'):
                call('create_chat_conversation', recipients=['chat_bob', 'chat_carol'])
            group = call('create_chat_conversation', recipients=['chat_bob', 'chat_carol'], title={'value': 'Production'})['conversationId']
            group_summary = next(row for row in call('query_chat_conversations')['conversations'] if row['conversationId'] == group)
            self.assertEqual((group_summary['title'], group_summary['participantCount']), ('Production', 3))
            call('delete_chat_conversation', message_code=group)
            call('update_chat_conversation', message_code=chat, title={'value': 'Native chat'})
            self.assertEqual(call('add_chat_members', message_code=chat, recipients=['chat_carol'])['added'], ['chat_carol'])
            self.assertEqual(call('add_chat_members', message_code=chat, recipients=['chat_bob'], replace=True)['removed'], ['chat_carol'])
            with self.assertRaisesRegex(Fault, 'fixed title'):
                call('update_chat_conversation', message_code=personal, title='Rename notes')
            with self.assertRaisesRegex(Fault, 'personal notes'):
                call('add_chat_members', message_code=personal, recipients=['chat_bob'])

            conversation = proxy.get_message(auth, chat)
            snapshot = proxy.create_snapshot(auth, conversation['__search_key__'], 'attachment', 'file')
            with self.assertRaisesRegex(Fault, 'does not belong to this chat'):
                call('send_chat_message', message_code=personal, message='Wrong attachment', attachment_keys=[snapshot['__search_key__']])
            self.assertEqual(call('query_chat_history', message_code=personal)['messages'], [])
            first = call('send_chat_message', message_code=chat, message='Hello, Привет!', attachment_keys=[snapshot['__search_key__']])['message']
            key = first['__search_key__']
            self.assertEqual(first['__delivery__']['sender'], 'admin')
            self.assertEqual(first['__delivery__']['recipients']['chat_bob'], dict(deliveredAt='', readAt=''))
            self.assertEqual(len(call('query_chat_history', message_code=chat)['messages']), 1,
                             'SQLite must create one message log, not two')
            received = call('query_chat_history', actor=bob, message_code=chat)['messages'][0]
            self.assertEqual(received['__attachments__'][0]['code'], snapshot['code'])
            self.assertTrue(call('authorize_chat_attachment', actor=bob, message_code=chat, snapshot_code=snapshot['code'])['allowed'])
            self.assertFalse(call('authorize_chat_attachment', actor=outsider, message_code=chat, snapshot_code=snapshot['code'])['allowed'])
            self.assertEqual(received['__delivery__']['status'], 'delivered')
            read = call('mark_chat_read', actor=bob, message_code=chat, timestamp=first['timestamp'])
            self.assertEqual(read['receiptsUpdated'], 1)
            self.assertEqual(call('mark_chat_read', actor=bob, message_code=chat, timestamp=first['timestamp'])['receiptsUpdated'], 0)
            self.assertEqual(call('query_chat_history', message_code=chat)['messages'][0]['__delivery__']['status'], 'read')
            reply = call('send_chat_message', message_code=chat, message='Reply', reply_to=key)['message']
            for name, values in (
                    ('edit_chat_message', dict(message_log_code=key, message='Forbidden')),
                    ('delete_chat_message', dict(message_log_code=key)),
                    ('toggle_chat_message_reaction', dict(message_log_code=key, emoji='👍')),
                    ('pin_chat_message', dict(message_log_code=key))):
                with self.assertRaisesRegex(Fault, 'not a chat participant'):
                    call(name, actor=outsider, **values)
            with self.assertRaisesRegex(Fault, 'cannot access a forwarded message'):
                call('forward_chat_messages', actor=outsider, message_log_keys=[key], target_message_codes=[chat])
            self.assertEqual(call('query_chat_history', message_code=chat)['messages'][0]['__reply__']['body'], 'Hello, Привет!')
            self.assertTrue(call('toggle_chat_message_reaction', message_log_code=key, emoji='👍')['active'])
            self.assertFalse(call('toggle_chat_message_reaction', message_log_code=key, emoji='👍')['active'])
            with self.assertRaisesRegex(Fault, 'Invalid message reaction'):
                call('toggle_chat_message_reaction', message_log_code=key, emoji='bad reaction')
            edited = call('edit_chat_message', message_log_code=key, message='Changed')
            self.assertEqual(edited['editHistory'][0]['body'], 'Hello, Привет!')
            self.assertFalse(call('edit_chat_message', message_log_code=key, message='Changed')['edited'])
            call('pin_chat_message', message_log_code=key)
            history = call('query_chat_history', message_code=chat)
            self.assertEqual(history['pinnedMessage']['body'], 'Changed')
            self.assertEqual(len(history['pinHistory']), 1)
            call('pin_chat_message', message_log_code=key, unpin=True)
            self.assertEqual(call('query_chat_history', message_code=chat)['pinnedMessage'], {})
            self.assertEqual(len(call('query_chat_history', message_code=chat, limit=1, offset=1)['messages']), 1)
            self.assertEqual(call('query_chat_history', message_code=chat, search_text='missing')['messages'], [])

            # The source rejects a pristine destination with NULL status. Keep the
            # original SQL semantics; record this Handler bug separately.
            with self.assertRaisesRegex(Fault, 'destination chat is not available'):
                call('forward_chat_messages', message_log_keys=[key], target_message_codes=[personal])
            call('send_chat_message', message_code=personal, message='Personal note')
            forwarded = call('forward_chat_messages', message_log_keys=[key, key], target_message_codes=[personal, personal])
            self.assertEqual(forwarded, dict(forwarded=1, destinations=1, messages=1))
            note = call('query_chat_history', message_code=personal)['messages'][0]
            self.assertEqual(note['__forwarded_from__']['body'], 'Changed')
            self.assertEqual(note['__forwarded_from__']['attachments'][0]['code'], snapshot['code'])
            with self.assertRaisesRegex(Fault, 'not available in this chat'):
                call('send_chat_message', message_code=chat, message='Wrong reply', reply_to=note['__search_key__'])
            self.assertEqual(call('clear_personal_chat', message_code=personal)['cleared'], 2)
            self.assertEqual(call('query_chat_history', message_code=personal)['messages'], [])
            self.assertEqual(call('authorize_chat_attachment', message_code=chat, snapshot_code='missing'), {'allowed': False})
            call('delete_chat_message', message_log_code=reply['__search_key__'])
            self.assertEqual(len(call('query_chat_history', message_code=chat)['messages']), 1)
            summaries = call('query_chat_conversations')['conversations']
            summary = next(row for row in summaries if row['conversationId'] == chat)
            self.assertEqual((summary['title'], summary['messageCount'], summary['lastMessage']), ('Native chat', 1, 'Changed'))
            self.assertEqual(summary['attachmentCount'], 1)
            # A failure after send must roll back the log, attachments and summary.
            code = self.procedures['send_chat_message'] + "\nsend_chat_message(**params)\nraise ValueError('Rollback chat send')"
            with self.assertRaisesRegex(Fault, 'Rollback chat send'):
                proxy.execute_python_script(auth, '', dict(code=code, params=dict(message_code=chat,
                    message='Must roll back', attachment_keys=[snapshot['__search_key__']])))
            self.assertEqual(len(call('query_chat_history', message_code=chat)['messages']), 1)
            self.assertEqual(next(row for row in call('query_chat_conversations')['conversations']
                                  if row['conversationId'] == chat), summary)
            proxy.update(auth, key, dict(timestamp='2000-01-01 00:00:00'))
            for name, values in (('edit_chat_message', dict(message='Too late')), ('delete_chat_message', {})):
                with self.assertRaisesRegex(Fault, 'within one hour'):
                    call(name, message_log_code=key, **values)
            with self.assertRaisesRegex(Fault, 'cannot be deleted'):
                call('delete_chat_conversation', message_code=personal)
            call('delete_chat_conversation', message_code=chat)
            self.assertNotIn(chat, [row['conversationId'] for row in call('query_chat_conversations')['conversations']])


if __name__ == '__main__':
    unittest.main()
