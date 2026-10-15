"""Saved scripts, native audit history and optimistic writes through HTTP."""
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import test_transport
from pyasm.security.authenticator import hash_password


class ScriptEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_storage_history_rights_and_conflicts(self):
        with test_transport.Transport.store.connection(write=True) as db:
            db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)', ('editor_reader', 'editor_reader', hash_password('reader-password')))
        with test_transport.Transport.proxy(self) as proxy:
            admin = proxy.get_ticket('admin', 'private-test-password')
            reader = proxy.get_ticket('editor_reader', 'reader-password')
            def call(action, ticket=admin, status=200, project='one', **values):
                req = Request(test_transport.Transport.url + '/admin/script-editor/' + action,
                    data=json.dumps(dict(ticket=ticket, project=project, **values)).encode(), headers={'Content-Type': 'application/json'})
                try: response = urlopen(req)
                except HTTPError as error: response = error
                with response:
                    self.assertEqual(response.status, status)
                    value = json.load(response)
                    return value.get('result', value)
            catalog = call('read')
            self.assertTrue(catalog['canEdit'])
            payload = dict(folder='demo\\nested', title='hello', language='python', source="return {'value': 1}", revision=catalog['revision'])
            created = call('save', **payload)
            code = created['savedCode']; row = next(row for row in created['scripts'] if row['code'] == code)
            self.assertEqual(row['folder'], 'demo/nested')
            call('save', status=409, **payload)
            self.assertEqual(len(call('read')['scripts']), len(created['scripts']))
            self.assertFalse(call('read', ticket=reader)['canEdit'])
            source = "# 😀\nimport json as data\ndata.du"
            cursor = len(source.encode('utf-16-le')) // 2
            analysed = call('analyse', source=source, cursor=cursor, manual=True)
            self.assertEqual(analysed['completions'][0]['label'], 'dump')
            self.assertEqual(analysed['completions'][0]['start'], cursor - 2)
            self.assertEqual(analysed['moduleNames'], ['data'])
            call('analyse', ticket=reader, status=403, source=source, cursor=cursor)
            call('analyse', status=400, source=source, cursor=True)
            call('analyse', status=400, source=source, cursor=cursor + 1)
            call('analyse', status=400, source='😀', cursor=1)
            call('save', ticket=reader, status=403, code=code, **dict(payload, revision=row['revision']))
            call('save', status=400, code=code, **dict(payload, folder='../escape', revision=row['revision']))
            call('save', status=400, code=code, **dict(payload, language='local_python', revision=row['revision']))
            changed = call('save', code=code, **dict(payload, source="return {'value': 2}", revision=row['revision']))
            latest = next(row for row in changed['scripts'] if row['code'] == code)
            call('delete', status=409, code=code, revision=row['revision'])
            history = call('history', code=code)['history']
            self.assertGreaterEqual(len(history), 2)
            old = call('revision', code=code, revision_id=history[-1]['revisionId'])['revision']
            self.assertEqual(old['script'], payload['source'])
            self.assertEqual(call('read')['scripts'][0]['source'], "return {'value': 2}")
            call('revision', status=400, code=code, revision_id='nonexistent')
            call('history', status=400, project='admin', code=code)
            self.assertEqual(proxy.execute_python_script(dict(ticket=admin, project='one'), 'demo/nested/hello', {})['info'], {'value': 2})
            deleted = call('delete', code=code, revision=latest['revision'])
            self.assertFalse(any(row['code'] == code for row in deleted['scripts']))
