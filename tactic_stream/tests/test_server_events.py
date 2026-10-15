"""Real SSE transport, native commit/rollback, cross-process wake-ups and idle load."""
import asyncio
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import test_transport
from tactic_stream.server.server_events import ServerEvents, read_event_clients
from pyasm.search.update_events import publish_changes
from tactic_stream.server.update_collector import UpdateCollector


def native_write(data_dir, auth):
    from tactic_stream.server.api import Api
    from pyasm.search.storage import Store
    Api(Store(Path(data_dir))).dispatch('update', [auth, 'contract/entity?project=one&code=A', {'name': 'SSE_WORKER'}])


class EventWatcher(unittest.IsolatedAsyncioTestCase):
    async def test_client_snapshots_all_workers_disconnect_and_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            UpdateCollector(directory).tick()
            first, second = ServerEvents(directory, .1), ServerEvents(directory, .1)
            subscription = dict(login='artist', channels=['cache'], search_types=['contract/entity'])
            try:
                left = await first.subscribe('one', subscription, dict(application='Web browser', address='127.0.0.1'))
                right = await second.subscribe('two', subscription, dict(application='TACTIC Handler', address='::1'))
                async def count(expected):
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        rows = read_event_clients(directory)
                        if len(rows) == expected:
                            return rows
                        await asyncio.sleep(.05)
                    self.fail('Connection snapshot did not converge')
                rows = await count(2)
                self.assertEqual({row['application'] for row in rows}, {'Web browser', 'TACTIC Handler'})
                self.assertEqual({row['project'] for row in rows}, {'one', 'two'})
                self.assertEqual(len({row['connection'] for row in rows}), 2)
                self.assertTrue(all(row['login'] == 'artist' and 'ticket' not in row for row in rows))
                first.unsubscribe(left)
                self.assertEqual((await count(1))[0]['project'], 'two')
                stale = second.clients_file.with_name('crashed.json')
                stale.write_text(json.dumps(dict(updated=time.time() - 46, clients=rows)))
                self.assertEqual(len(read_event_clients(directory)), 1)
                second.unsubscribe(right)
                await count(0)
            finally:
                await first.close()
                await second.close()
            self.assertFalse(first.clients_file.exists())
            self.assertFalse(second.clients_file.exists())

    async def test_shared_watcher_and_coalescing(self):
        with tempfile.TemporaryDirectory() as directory:
            collector = UpdateCollector(directory)
            collector.tick()
            subscription = dict(channels=["cache"], search_types=["contract/entity", "contract/child"])
            first, second = ServerEvents(directory), ServerEvents(directory)
            try:
                starts = []
                watch = first.watch
                async def counted_watch():
                    starts.append(True)
                    await watch()
                with patch.object(first, 'watch', counted_watch):
                    subscribers = await asyncio.gather(*(first.subscribe('one', subscription) for _ in range(100)))
                remote = await second.subscribe('one', subscription)
                other = await first.subscribe('two', subscription)
                unrelated = await first.subscribe('one', dict(channels=['cache'], search_types=['contract/unrelated']))
                # Different types survive a burst, with no per-client queue of commits.
                for _ in range(10):
                    publish_changes(directory, [('one', 'contract/entity'), ('one', 'contract/child')])
                collector.tick()
                await asyncio.wait_for(remote['event'].wait(), 3)
                await asyncio.wait_for(subscribers[-1]['event'].wait(), 3)
                self.assertFalse(other['event'].is_set())
                self.assertFalse(unrelated['event'].is_set())
                self.assertEqual(len(starts), 1, 'Concurrent subscribers must share one watcher')
                for subscriber in subscribers + [remote]:
                    self.assertEqual(subscriber['changes'], {('one', 'contract/entity', ''), ('one', 'contract/child', '')})
                    subscriber['changes'].clear()
                    subscriber['event'].clear()
                await asyncio.sleep(.7)
                self.assertTrue(all(not item['event'].is_set() for item in subscribers + [remote]))
                self.assertFalse(first.task.done())
                for subscriber in subscribers + [other, unrelated]:
                    first.unsubscribe(subscriber)
                publish_changes(directory, [('one', 'contract/entity')])
                collector.tick()
                reopened = await first.subscribe('one', subscription)
                await asyncio.sleep(.7)
                self.assertFalse(reopened['event'].is_set(), 'A new initial snapshot must not replay old wake-ups')
                artist = await first.subscribe('one', dict(login='artist', channels=['messages', 'reactions'], search_types=[]))
                observer = await first.subscribe('one', dict(login='other', channels=['messages', 'reactions'], search_types=[]))
                publish_changes(directory, [('sthpw', 'sthpw/message_log', 'artist')])
                # Filesystem timestamp resolution must not discard a newer commit.
                for marker in (Path(directory) / 'cache' / 'update-events').glob('*.json'):
                    os.utime(marker, (1, 1))
                collector.tick()
                await asyncio.wait_for(artist['event'].wait(), 3)
                self.assertFalse(observer['event'].is_set(), 'Private chat must not wake other users')
                restarted = UpdateCollector(directory)
                restarted.tick()
                artist['event'].clear()
                await asyncio.sleep(.7)
                self.assertFalse(artist['event'].is_set(), 'Producer restart must not replay revisions')
            finally:
                await first.close()
                await second.close()


class ServerEventsTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_connection_list_configuration_acl_and_interval_save(self):
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        from tactic_stream.server.api import Api
        from pyasm.security.authenticator import hash_password
        api = Api(test_transport.Transport.store)
        ticket = api.auth.get_ticket('admin', 'private-test-password')
        def post(path, payload):
            with urlopen(Request(test_transport.Transport.url + path, data=json.dumps(payload).encode(),
                         headers={'Content-Type': 'application/json'}), timeout=5) as response:
                return json.load(response)['result']
        initial = post('/admin/configuration', dict(ticket=ticket))
        self.assertIsInstance(initial['event_clients'], list)
        fields = {row['path']: row for group in initial['groups'] for row in group['settings']}
        self.assertTrue(fields['services/update_interval']['editable'])
        self.assertTrue(fields['services/update_interval']['restart'])
        api.dispatch('insert', [dict(ticket=ticket, project='one'), 'sthpw/login',
                     dict(login='sse_connection_reader', password=hash_password('private-reader-password'))])
        reader = api.auth.get_ticket('sse_connection_reader', 'private-reader-password')
        for credential in ('invalid', reader):
            with self.assertRaises(HTTPError) as denied:
                post('/admin/configuration', dict(ticket=credential))
            self.assertEqual(denied.exception.code, 403)
            denied.exception.close()
        for value in ('0.01', '2.1', 'nan'):
            with self.assertRaises(HTTPError) as invalid:
                post('/admin/configuration/save', dict(ticket=ticket, revision=initial['revision'],
                     changes={'services/update_interval': value}))
            self.assertEqual(invalid.exception.code, 400)
            self.assertEqual(json.load(invalid.exception)['error_field'], 'services/update_interval')
            invalid.exception.close()
        saved = post('/admin/configuration/save', dict(ticket=ticket, revision=initial['revision'],
                     changes={'services/update_interval': '0.75'}))
        self.assertTrue(saved['restart_required'])
        fields = {row['path']: row for group in saved['groups'] for row in group['settings']}
        self.assertEqual(fields['services/update_interval']['value'], '0.75')
        post('/admin/configuration/save', dict(ticket=ticket, revision=saved['revision'],
             changes={'services/update_interval': ''}))

    def test_collector_stops_even_when_event_cleanup_fails(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from tactic_stream.server.app import create_app
        application = create_app(test_transport.Transport.store.data_dir)
        spawn = Mock()
        process = spawn.Process.return_value
        process.is_alive.return_value = False
        stop = spawn.Value.return_value = SimpleNamespace(value=False)
        async def scenario():
            with patch('multiprocessing.get_context', return_value=spawn), patch.object(ServerEvents, 'close', side_effect=OSError('injected cleanup failure')):
                with self.assertRaises(OSError):
                    async with application.router.lifespan_context(application):
                        pass
            self.assertTrue(stop.value)
            process.join.assert_called_once_with(3)
            process.close.assert_called_once_with()
        asyncio.run(scenario())

    def test_disconnect_before_first_frame_removes_subscription(self):
        from tactic_stream.server.app import create_app
        from tactic_stream.server.api import Api
        from starlette.requests import ClientDisconnect
        api = Api(test_transport.Transport.store)
        ticket = api.auth.get_ticket('admin', 'private-test-password')
        body = json.dumps(dict(ticket=ticket, project='one', channels=[], search_types=[])).encode()
        original = ServerEvents.subscribe
        async def scenario(spec):
            owners = []
            async def subscribed(owner, *args, **kwargs):
                owners.append(owner)
                return await original(owner, *args, **kwargs)
            application = create_app(test_transport.Transport.store.data_dir, event_collector=False)
            sent_body = False
            async def receive():
                nonlocal sent_body
                if not sent_body:
                    sent_body = True
                    return dict(type='http.request', body=body, more_body=False)
                return dict(type='http.disconnect')
            async def send(message):
                if message['type'] == 'http.response.start':
                    if spec == '2.4':
                        raise OSError('Client disconnected before headers')
                    await asyncio.sleep(.1)
            scope = dict(type='http', asgi=dict(version='3.0', spec_version=spec), method='POST',
                         scheme='http', path='/admin/server-events', raw_path=b'/admin/server-events', query_string=b'',
                         headers=[(b'content-type', b'application/json')], client=('127.0.0.1', 1234), server=('127.0.0.1', 8081))
            try:
                with patch.object(ServerEvents, 'subscribe', subscribed):
                    if spec == '2.4':
                        with self.assertRaises(ClientDisconnect):
                            await application(scope, receive, send)
                    else:
                        await application(scope, receive, send)
                self.assertEqual(len(owners), 1)
                self.assertEqual(len(owners[0].subscribers), 0, 'An unstarted response generator must not leak its subscription')
            finally:
                for owner in owners:
                    await owner.close()
        asyncio.run(scenario('2.3'))
        asyncio.run(scenario('2.4'))

    def test_native_project_routing_and_chat_recipient_union(self):
        from tactic_stream.server.api import Api
        api = Api(test_transport.Transport.store)
        auth = dict(ticket=api.auth.get_ticket('admin', 'private-test-password'), project='one')
        changes = set()
        code = """from pyasm.search import Search, SearchType
from pyasm.biz import SObjectConnection, StatusLog, Task, Pipeline
import json
first = Search.get_by_code('contract/entity', 'A')
second = Search.get_by_code('contract/entity', 'B')
SObjectConnection.create(first, second, context='SSE_ROUTING')
task = Task.create(first, 'SSE_ROUTING', triggers=False)
StatusLog.create(task, 'Submitted', 'Ready')
Pipeline.create('Routing fixture', '', 'contract/entity', '<pipeline><process name="work"/></pipeline>', code='SSE_ROUTING_PIPE')
for login in ('alice', 'bob'):
    row = SearchType.create('sthpw/message_log')
    row.set_value('message_code', 'SSE_RECIPIENT_UNION')
    row.set_value('login', 'admin')
    row.set_value('message', 'Private routing fixture')
    row.set_value('metadata', json.dumps({'delivery': {'sender': 'admin', 'recipients': {login: {}}}}))
    row.commit(triggers=False)
connection = SearchType.create('sthpw/connection')
connection.set_value('src_search_type', first.get_search_type())
connection.set_value('src_search_id', first.get_id())
connection.set_value('dst_search_type', 'sthpw/message_log')
connection.set_value('dst_search_id', row.get_id())
connection.set_value('context', 'chat_attachment')
connection.set_value('project_code', 'sthpw')
connection.commit(triggers=False)
return True
"""
        with patch('pyasm.search.update_events.publish_changes', side_effect=lambda directory, values: changes.update(values)):
            self.assertTrue(api.dispatch('execute_python_script', [auth, '', dict(code=code)]))
        self.assertIn(('one', 'sthpw/connection', ''), changes)
        self.assertIn(('one', 'sthpw/status_log', ''), changes)
        self.assertIn(('one', 'sthpw/pipeline', ''), changes)
        self.assertEqual({login for project, kind, login in changes if kind == 'sthpw/message_log'}, {'alice', 'bob', 'admin'})
        self.assertEqual({login for project, kind, login in changes if project == 'sthpw' and kind == 'sthpw/connection'}, {'alice', 'bob', 'admin'})

    def test_publication_does_not_query_after_commit(self):
        from tactic_stream.server.api import Api
        from pyasm.search import Search
        from pyasm.search.update_events import publish_transaction
        api = Api(test_transport.Transport.store)
        auth = dict(ticket=api.auth.get_ticket('admin', 'private-test-password'), project='one')
        def publish(transaction):
            with patch.object(Search, 'get_sobjects', side_effect=AssertionError('Post-commit publication queried the database')):
                publish_transaction(transaction)
        with patch('pyasm.search.update_events.publish_transaction', publish):
            result = api.dispatch('update', [auth, 'contract/entity?project=one&code=A', {'name': 'NO_POST_COMMIT_READ'}])
        self.assertEqual(result['name'], 'NO_POST_COMMIT_READ')

    def test_native_sse(self):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from tactic_stream.server.server_updates import query_server_updates
        from pyasm.search.search import RequestContext, request_context, Search
        from pyasm.command import Command
        from tactic_stream.server.api import Api
        store = test_transport.Transport.store
        api = Api(store)
        ticket = api.auth.get_ticket('admin', 'private-test-password')
        auth = {'ticket': ticket, 'project': 'one'}
        full_queries = []

        def query(**arguments):
            if arguments.get('include_cache_changes'):
                full_queries.append(arguments)
            return query_server_updates(**arguments)

        async def scenario():
            def connect(payload):
                return urlopen(Request(test_transport.Transport.url + '/admin/server-events',
                    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=5)
            try:
                denied = await asyncio.to_thread(connect, dict(auth, ticket='invalid'))
            except HTTPError as denied:
                self.assertEqual(denied.code, 403)
                denied.close()
            else:
                denied.close()
                self.fail('Unauthenticated stream was accepted')
            for invalid in (dict(auth, activity_after=7), dict(auth, unexpected=True), dict(auth, project='missing'),
                            dict(auth, channels=['unknown']), dict(auth, search_types=['cg/assets?project=two']),
                            dict(auth, invalidated_types='cg/assets'), dict(auth, heartbeat='false')):
                try:
                    response = await asyncio.to_thread(connect, invalid)
                except HTTPError as error:
                    self.assertEqual(error.code, 400)
                    error.close()
                else:
                    response.close()
                    self.fail('Invalid stream request was accepted')
            with patch('tactic_stream.server.server_updates.query_server_updates', query), patch('tactic_stream.server.app.EVENT_HEARTBEAT', .7):
                response = await asyncio.to_thread(connect, dict(auth, channels=['cache'], search_types=['contract/entity']))
                with response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers['x-accel-buffering'], 'no')

                    def read_frame():
                        data = []
                        while True:
                            raw = response.readline()
                            if not raw:
                                raise AssertionError('Stream ended')
                            line = raw.decode().rstrip('\r\n')
                            if line.startswith('data: '):
                                data.append(line[6:])
                            if not line:
                                return json.loads('\n'.join(data)) if data else None

                    async def frame():
                        return await asyncio.to_thread(read_frame)

                    baseline = await frame()
                    self.assertIn('cacheCursor', baseline)
                    self.assertEqual([row['searchType'] for row in baseline['cacheChanges']], ['contract/entity'], 'Fresh stream must invalidate a retained cache without a cursor')
                    self.assertEqual(len(full_queries), 0, 'Initial type invalidation must not scan journals')
                    count = len(full_queries)
                    # Multiple heartbeat cycles produce comments, without full data queries/events.
                    self.assertIsNone(await frame())
                    self.assertIsNone(await frame())
                    self.assertEqual(len(full_queries), count)

                    def rollback():
                        with request_context(RequestContext(store, 'admin', 'one')):
                            api.auth.bind_security('admin', ticket)
                            command = Command()
                            def execute():
                                item = Search.get_by_code('contract/entity', 'A')
                                item.set_value('name', 'ROLLED_BACK')
                                item.commit()
                                raise ValueError('intentional rollback')
                            command.execute = execute
                            with self.assertRaises(ValueError):
                                Command.execute_cmd(command)
                    await asyncio.to_thread(rollback)
                    self.assertIsNone(await frame())
                    self.assertEqual(len(full_queries), count)

                    def another_worker():
                        process = multiprocessing.get_context('spawn').Process(target=native_write, args=(str(store.data_dir), auth))
                        try:
                            process.start()
                            process.join(20)
                            self.assertEqual(process.exitcode, 0)
                        finally:
                            if process.is_alive():
                                process.kill()
                                process.join(5)
                            process.close()
                    await asyncio.to_thread(another_worker)
                    for _ in range(8):
                        update = await frame()
                        if update is not None:
                            break
                    self.assertEqual(update, dict(channels=['cache'], search_types=['contract/entity']))
                    self.assertEqual(len(full_queries), count, 'Fanout must not query per subscriber')
                    def read_current():
                        request = Request(test_transport.Transport.url + '/admin/server-updates', data=json.dumps(dict(auth, channels=['cache'], search_types=['contract/entity'], invalidated_types=update['search_types'], heartbeat=False)).encode(), headers={'Content-Type':'application/json'})
                        with urlopen(request, timeout=5) as result:
                            return json.load(result)['result']
                    current = await asyncio.to_thread(read_current)
                    self.assertTrue(any(item['searchType'] == 'contract/entity' for item in current['cacheChanges']))
                    self.assertEqual(len(full_queries), count, 'Type invalidation must not rescan journals')
                    self.assertIsNone(await frame())
                    self.assertEqual(len(full_queries), count)

                    # Auth is rechecked on heartbeat, not only when establishing a stream.
                    with store.connection(write=True) as db:
                        db.execute('DELETE FROM ticket WHERE ticket=?', (ticket,))
                    for _ in range(4):
                        error = await frame()
                        if error is not None:
                            break
                    self.assertEqual(error['error_code'], 'authentication_failed')

        asyncio.run(scenario())

    def test_messages_and_presence_do_not_create_idle_loop(self):
        from urllib.request import Request, urlopen
        from tactic_stream.server.api import Api
        from tactic_stream.server.server_updates import query_server_updates
        api = Api(test_transport.Transport.store)
        auth = dict(ticket=api.auth.get_ticket('admin', 'private-test-password'), project='one')

        def call(action, values=None, identity=auth):
            request = Request(test_transport.Transport.url + '/admin/messages/' + action,
                data=json.dumps(dict(identity, **(values or {}))).encode(), headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=5) as response:
                return json.load(response)['result']
        call('initialize')
        api.dispatch('execute_python_script', [auth, '', {'code': """
from pyasm.search import Search, SearchType
from pyasm.security.authenticator import hash_password
user = Search.get_by_code('sthpw/login', 'sse_artist')
if not user:
    user = SearchType.create('sthpw/login')
    user.set_value('code', 'sse_artist'); user.set_value('login', 'sse_artist')
    user.set_value('password', hash_password('sse-test-password'))
    user.commit(); user.add_to_group('admin')
return True
"""}])
        artist = dict(ticket=api.auth.get_ticket('sse_artist', 'sse-test-password'), project='one')
        conversation = call('create', {'recipients': ['sse_artist'], 'title': 'SSE delivery'})['conversationId']
        queries = []
        def query(**arguments):
            if arguments.get('include_cache_changes'):
                queries.append(arguments)
            return query_server_updates(**arguments)

        async def scenario():
            request = Request(test_transport.Transport.url + '/admin/server-events', data=json.dumps(auth).encode(),
                headers={'Content-Type': 'application/json'})
            with patch('tactic_stream.server.server_updates.query_server_updates', query), patch('tactic_stream.server.app.EVENT_HEARTBEAT', .7):
                response = await asyncio.to_thread(urlopen, request, timeout=5)
                with response:
                    def read_frame():
                        data = []
                        while True:
                            raw = response.readline()
                            if not raw:
                                raise AssertionError('Stream ended')
                            line = raw.decode().rstrip('\r\n')
                            if line.startswith('data: '):
                                data.append(line[6:])
                            if not line:
                                return json.loads('\n'.join(data)) if data else None
                    baseline = await asyncio.to_thread(read_frame)
                    self.assertTrue(baseline['messagesInitialized'])
                    self.assertTrue(baseline['presence'])
                    count = len(queries)
                    for _ in range(3):
                        self.assertIsNone(await asyncio.to_thread(read_frame), 'lastSeen changes must not be data events')
                    self.assertEqual(len(queries), count)
                    await asyncio.to_thread(call, 'send', {'message_code': conversation, 'message': 'SSE_DELIVERY'}, artist)
                    update = None
                    for _ in range(10):
                        update = await asyncio.to_thread(read_frame)
                        if update is not None and 'channels' in update:
                            request = Request(test_transport.Transport.url + '/admin/server-updates', data=json.dumps(dict(auth, channels=update['channels'], heartbeat=False)).encode(), headers={'Content-Type':'application/json'})
                            def fetch():
                                with urlopen(request, timeout=5) as result:
                                    return json.load(result)['result']
                            update = await asyncio.to_thread(fetch)
                            if any(row.get('message') == 'SSE_DELIVERY' for row in update['messages']):
                                break
                    self.assertTrue(any(row.get('message') == 'SSE_DELIVERY' for row in update['messages']))
                    # One incoming message and its delivered receipt settle; presence never reawakens data reads.
                    for _ in range(5):
                        await asyncio.to_thread(read_frame)
                    count = len(queries)
                    self.assertLessEqual(count, 3)
                    for _ in range(3):
                        self.assertIsNone(await asyncio.to_thread(read_frame))
                    self.assertEqual(len(queries), count)
                    history = await asyncio.to_thread(call, 'history', {'message_code': conversation}, artist)
                    message = next(row for row in history['messages'] if row['message'] == 'SSE_DELIVERY')
                    self.assertEqual(message['__delivery__']['status'], 'delivered')
        asyncio.run(scenario())
