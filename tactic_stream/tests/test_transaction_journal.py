"""Native journal read projection, private values, compressed XML and project boundaries."""
import json
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import test_transport as transport


class TransactionJournal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        transport.Transport.setUpClass()
        cls.url = transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        transport.Transport.tearDownClass()

    def test_native_journal(self):
        with transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            auth = dict(ticket=ticket, project='one')

            def call(path, status=200, **values):
                request = Request(transport.Transport.url + path, data=json.dumps(dict(auth, **values)).encode(), headers={'Content-Type': 'application/json'})
                try: response = urlopen(request)
                except HTTPError as failure: response = failure
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, status, body)
                    return body.get('result', body)

            # Use native Command/journaling, including >10KB zlib storage.
            proxy.update(auth, 'contract/entity?project=one&code=A', dict(name='Journal large ' + 'x' * 12000))
            result = call('/admin/search-configuration/query', search_type='sthpw/transaction_log', limit=2, offset=0, include_total=True)
            self.assertTrue(result['records'])
            self.assertGreater(result['total'], 0)
            row = result['records'][0]
            self.assertEqual(row['namespace'], 'one')
            self.assertNotIn('ticket', row)
            self.assertNotIn('transaction', row)
            detail = call('/admin/transaction-log/details', search_key=row['__search_key__'])
            self.assertIn('Journal large ', detail['xml'])
            self.assertIn('<transaction', detail['xml'])
            with transport.Transport.store.connection(write=True) as db:
                source = db.execute('SELECT "transaction" FROM transaction_log WHERE code=?', (row['code'],)).fetchone()[0]
                db.execute('UPDATE transaction_log SET "transaction"=? WHERE code=?', ('<broken>', row['code']))
            try:
                call('/admin/transaction-log/details', 400, search_key=row['__search_key__'])
            finally:
                with transport.Transport.store.connection(write=True) as db:
                    db.execute('UPDATE transaction_log SET "transaction"=? WHERE code=?', (source, row['code']))
            call('/admin/transaction-log/details', 400, search_key='contract/entity?code=A')
            call('/admin/transaction-log/details', 400, search_key='sthpw/transaction_log')
            call('/admin/transaction-log/details', 400, search_key='sthpw/transaction_log?project=two&code=' + row['code'])
            call('/admin/transaction-log/details', 400, search_key=row['__search_key__'], project='two')
            call('/admin/transaction-log/details', 400, search_key=row['__search_key__'], unknown=True)
            call('/admin/transaction-log/details', 403, search_key=row['__search_key__'], ticket='invalid')
            call('/admin/search-configuration/query', 400, search_type='sthpw/transaction_log', filters=[['ticket', '=', ticket]])
            call('/admin/search-configuration/query', 400, search_type='sthpw/transaction_log', columns=['ticket'])
            call('/admin/search-configuration/query', 400, search_type='sthpw/transaction_log', order_bys=['transaction'])
            call('/admin/search-configuration/query', 400, search_type='sthpw/transaction_log', records=[dict(column='_expression', relation='match', value='@SOBJECT(sthpw/ticket)', rowEnabled=True, operator='begin')])
            settings = call('/admin/search-configuration/settings', search_type='sthpw/transaction_log')
            self.assertNotIn('ticket', settings['columns'])
            suggestions = call('/admin/search-configuration/suggestions', search_type='sthpw/transaction_log', keyword=row['code'])
            self.assertTrue(suggestions['records'])
            self.assertNotIn('ticket', json.dumps(suggestions['records']))
            definition = call('/admin/interface', search_type='sthpw/transaction_log')
            self.assertFalse(definition['operations']['create'])
            self.assertNotIn('transaction', definition['columns'])
            self.assertTrue(next(item for item in definition['table']['elements'] if item['name'] == 'transaction_log_hidden')['cell']['supported'])
            link = call('/admin/navigation-link', link='skey://' + row['__search_key__'])
            self.assertNotIn('ticket', link['object'])
            self.assertNotIn('transaction', link['object'])

            proxy.insert(auth, 'sthpw/login', dict(login='journal_secret', password='hidden-password'))
            rows = call('/admin/search-configuration/query', search_type='sthpw/transaction_log', limit=100, offset=0)
            first = call('/admin/search-configuration/query', search_type='sthpw/transaction_log', limit=1, offset=0, include_total=True)
            second = call('/admin/search-configuration/query', search_type='sthpw/transaction_log', limit=1, offset=1, include_total=True)
            self.assertEqual([first['records'][0]['code'], second['records'][0]['code']], [item['code'] for item in rows[:2]])
            self.assertEqual(first['total'], second['total'])
            xml = '\n'.join(call('/admin/transaction-log/details', search_key=item['__search_key__'])['xml'] for item in rows)
            self.assertNotIn('hidden-password', xml)
            self.assertNotIn(ticket, xml)
            self.assertIn('[redacted]', xml)
            from tactic_stream.server.transaction_journal import mask_json_text
            packed = mask_json_text(json.dumps({'rows': [{'password': 'nested-secret', 'name': 'Visible'}]}))
            self.assertNotIn('nested-secret', packed)
            self.assertIn('Visible', packed)
            backup = mask_json_text(json.dumps({'columns': [{'name': 'name'}, {'name': 'password'}], 'rows': [['Visible', 'schema-secret']]}))
            self.assertNotIn('schema-secret', backup)
            self.assertIn('Visible', backup)
            from pyasm.security.authenticator import hash_password
            proxy.insert(auth, 'sthpw/login', dict(login='journal_reader', password=hash_password('reader-password')))
            reader = proxy.get_ticket('journal_reader', 'reader-password')
            call('/admin/search-configuration/query', 403, search_type='sthpw/transaction_log', ticket=reader)
            call('/admin/transaction-log/details', 403, search_key=row['__search_key__'], ticket=reader)
            # The generic XML-RPC policy remains guarded; no full raw-journal exposure.
            from xmlrpc.client import Fault
            with self.assertRaises(Fault):
                proxy.query(auth, 'sthpw/transaction_log')


if __name__ == '__main__':
    unittest.main()
