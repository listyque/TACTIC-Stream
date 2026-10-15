"""Real transport journal, native audit, privacy, paging and request boundaries."""
import ast
import inspect
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_transport
from pyasm.security.authenticator import hash_password
from tactic_stream.server.activity_query import query_user_recent_activity


class ActivityFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_instance_audit_uses_requested_project_from_system_context(self):
        store = test_transport.Transport.store
        with store.connection('one', write=True) as db:
            db.execute('ALTER TABLE entity_in_collection RENAME COLUMN entity_code TO member_code')
            db.execute('ALTER TABLE entity_in_collection RENAME COLUMN collection_code TO owner_code')
        with store.connection(write=True) as db:
            schema = ET.fromstring(db.execute('SELECT "schema" FROM "schema" WHERE code=\'one\'').fetchone()[0])
            for edge in schema.findall('connect'):
                if edge.get('from') == 'contract/entity_in_collection':
                    edge.set('from_col', 'member_code' if edge.get('to') == 'contract/entity' else 'owner_code')
            db.execute('UPDATE "schema" SET "schema"=? WHERE code=\'one\'', (ET.tostring(schema, encoding='unicode'),))
            db.execute('INSERT INTO transaction_log (code, login, namespace, timestamp, "transaction") VALUES (?,?,?,?,?)',
                       ('FEED_LINK', 'admin', 'one', '2026-10-11 12:00:00', '''<transaction>
                         <sobject search_type="contract/entity_in_collection" search_code="J1" action="insert">
                           <column name="owner_code" to="G1"/>
                           <column name="member_code" to="A"/>
                         </sobject></transaction>'''))
        handler_path = Path(__file__).resolve().parents[3] / 'th_codex/thlib/tactic_query.py'
        handler_source = handler_path.read_text(encoding='utf-8')
        handler_query = next(node for node in ast.parse(handler_source).body
                             if isinstance(node, ast.FunctionDef) and node.name == 'query_user_recent_activity')
        sources = {'stream': inspect.getsource(query_user_recent_activity),
                   'handler': ast.get_source_segment(handler_source, handler_query)}
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            for name, source in sources.items():
                with self.subTest(client=name):
                    code = source + "\nreturn query_user_recent_activity(project_code='one', kinds=['create'], instance_relations={'contract/entity_in_collection': ['contract/entity', 'contract/collection']})"
                    records = proxy.execute_python_script(dict(ticket=ticket, project='sthpw'), '', dict(code=code))['info']
                    event = next(row for row in records if row.get('relationAction') == 'link')
                    self.assertEqual((event['itemType'], event['itemTitle']), ('contract/entity', 'Первый'))
                    self.assertEqual((event['targetType'], event['targetTitle']), ('contract/collection', 'First'))
                    self.assertIn('project=one', event['targetSearchKey'])
                    self.assertNotIn('J1', str(event))
            request = Request(self.url + '/admin/activity-feed',
                              data=json.dumps(dict(ticket=ticket, project='one')).encode(),
                              headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                records = json.load(response)['result']['records']
            event = next(row for row in records if row.get('relationAction') == 'link')
            self.assertEqual({event['itemType'], event['targetType']}, {'contract/entity', 'contract/collection'})

    def test_journal_and_boundaries(self):
        with test_transport.Transport.store.connection(write=True) as db:
            db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)',
                       ('feed_reader', 'feed_reader', hash_password('reader-password')))
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            reader = proxy.get_ticket('feed_reader', 'reader-password')
            auth = dict(ticket=ticket, project='one')
            def call(status=200, **values):
                req = Request(test_transport.Transport.url + '/admin/activity-feed',
                    data=json.dumps(dict(auth, **values)).encode(), headers={'Content-Type': 'application/json'})
                try: response = urlopen(req)
                except HTTPError as failure: response = failure
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, status, body)
                    return body.get('result', body)
            code = """
from pyasm.search import SearchType, Search
obj = Search.get_by_code('contract/entity', 'A')
for index in range(29):
    note = SearchType.create('sthpw/note')
    note.set_value('note', 'Activity note %s' % index)
    note.set_value('process', 'publish')
    note.set_value('login', 'admin')
    note.set_value('project_code', 'one')
    note.set_value('access', 'public')
    note.add_related_sobject(obj)
    note.commit()
obj.set_value('amount', 22)
obj.commit()
return obj.get_search_key()
"""
            proxy.execute_python_script(auth, '', {'code': code})
            result = call()
            more = call(offset=result['nextOffset'])
            self.assertTrue(any(row['kind'] == 'change' for row in result['records'] + more['records']))
            notes = call(filter='notes')
            self.assertEqual(len(notes['records']), 25)
            self.assertTrue(notes['hasMore'])
            older = call(filter='notes', offset=notes['nextOffset'])
            self.assertEqual(len(older['records']), 4)
            self.assertFalse(older['hasMore'])
            self.assertFalse({row['eventId'] for row in notes['records']} & {row['eventId'] for row in older['records']})
            self.assertTrue(all(row['targetSearchKey'] and row['targetTitle'] for row in notes['records']))
            counts = call(filter='notes', counts_only=True)
            self.assertEqual(sum(row['count'] for row in counts['dayCounts']), 29)
            self.assertEqual(counts['records'], [])
            day = counts['dayCounts'][0]['dateKey']
            self.assertEqual(len(call(filter='notes', day=day)['records']), 25)
            self.assertEqual(call(filter='notes', exclude_own=True)['records'], [])
            call(403, ticket=reader)
            call(403, ticket=reader, counts_only=True)
            group = proxy.insert(auth, 'sthpw/login_group', dict(login_group='feed_access', access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="deny"/></rules>'))
            proxy.insert(auth, 'sthpw/login_in_group', dict(login='feed_reader', login_group='feed_access'))
            self.assertEqual(call(ticket=reader)['records'], [])
            self.assertEqual(call(ticket=reader, counts_only=True)['dayCounts'], [])
            proxy.update(auth, group['__search_key__'], dict(access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" project="one" access="view"/></rules>'))
            public = call(ticket=reader, filter='notes')
            self.assertEqual(len(public['records']), 25)
            note_key = notes['records'][0]['searchKey']
            proxy.update(auth, note_key, dict(access='private'))
            self.assertNotIn(note_key, [row['searchKey'] for row in call(ticket=reader, filter='notes')['records']])
            self.assertEqual(sum(row['count'] for row in call(ticket=reader, filter='notes', counts_only=True)['dayCounts']), 28)
            call(403, ticket='invalid')
            for values in ({'filter': 'unknown'}, {'offset': True}, {'users': 'admin'}, {'counts_only': 1}, {'day': '2026-02-30'}, {'arbitrary': True}):
                call(400, **values)
            call(400, project='missing')


if __name__ == '__main__':
    unittest.main()
