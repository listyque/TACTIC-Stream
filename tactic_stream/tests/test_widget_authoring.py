"""Native authoring boundary; existing source contracts remain in test_widget_config."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path

from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api
from tactic_stream.server.widget_configuration import read_widget_configuration, check_widget_configuration, save_widget_configuration, WidgetConfigConflict


def concurrent_save(data_dir, password, source_id, xml, revision):
    from pyasm.search.storage import Store
    store = Store(Path(data_dir))
    api = Api(store)
    token = api.get_ticket('admin', password)
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        try:
            save_widget_configuration('sthpw/note', 'author_test', source_id, xml, revision)
        except WidgetConfigConflict:
            return 'conflict'
        return 'saved'


XML = '''<config><!--keep this--><author_test custom="yes"><element name="code" title="Code"><display class="custom.Unknown"><script><![CDATA[if a < b: pass]]></script></display></element><extension untouched="yes"/></author_test></config>'''


def exercise_authoring(store, password):
    api = Api(store)
    token = api.get_ticket('admin', password)
    ticket = dict(ticket=token, project='admin')
    def read():
        with request_context(RequestContext(store, 'admin', 'admin')):
            api.auth.bind_security('admin', token)
            return read_widget_configuration('sthpw/note', 'author_test')
    start = read()
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        checked = check_widget_configuration('sthpw/note', 'author_test', None, XML, start['revision'])
        assert checked['valid'] and 'stored.xml' in checked['diff']
        assert Search('config/widget_config').get_count() == 0
        saved = save_widget_configuration('sthpw/note', 'author_test', None, XML, start['revision'])
        assert saved['sources'][0]['xml'] == XML
        assert saved['revision'] == read_widget_configuration('sthpw/note', 'author_test')['revision']
        assert saved['resolved']['elements'][0]['display']['handler'] == 'custom.Unknown'
        try:
            save_widget_configuration('sthpw/note', 'author_test', None, XML, start['revision'])
        except WidgetConfigConflict:
            pass
        else:
            raise AssertionError('stale create made a duplicate')
        record = Search('config/widget_config').get_sobject()
        key = record.get_search_key()
    # Ordinary XML-RPC/core path A -> B -> A must invalidate the original revision.
    api.dispatch('update', (ticket, key, dict(config=XML.replace('untouched="yes"', 'untouched="no"'))))
    api.dispatch('update', (ticket, key, dict(config=XML)))
    changed = read()
    assert changed['sources'][0]['xml'] == XML
    assert changed['revision'] != saved['revision']
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        try:
            save_widget_configuration('sthpw/note', 'author_test', changed['sources'][0]['id'], XML, saved['revision'])
        except WidgetConfigConflict:
            pass
        else:
            raise AssertionError('ABA revision was accepted')
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        futures = [pool.submit(concurrent_save, str(store.data_dir), password, changed['sources'][0]['id'],
            XML.replace('untouched="yes"', 'untouched="%d"' % index), changed['revision']) for index in (1, 2)]
        assert sorted(future.result(timeout=30) for future in futures) == ['conflict', 'saved']
    # Equal results across vendors; which writer won is deliberately unspecified.
    return dict(xml=changed['sources'][0]['xml'], elements=changed['resolved']['elements'], source_count=len(changed['sources']))


class WidgetAuthoring(unittest.TestCase):
    def test_native_commands_and_http_boundary(self):
        from test_transport import Transport
        class FixtureServer(Transport):
            pass
        FixtureServer.setUpClass()
        self.addCleanup(FixtureServer.tearDownClass)
        result = exercise_authoring(FixtureServer.store, 'private-test-password')
        self.assertEqual(result['source_count'], 1)
        api = Api(FixtureServer.store)
        token = api.get_ticket('admin', 'private-test-password')
        def post(action, **options):
            payload = dict(ticket=token, project='admin', search_type='sthpw/note', view='author_test', **options)
            return urlopen(Request(FixtureServer.url + '/admin/widget-configuration/' + action,
                json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}))
        with post('read') as response:
            current = json.load(response)['result']
        for xml in ('<config>', '<other/>', '<!DOCTYPE config [<!ENTITY x "boom">]><config/>'):
            with self.assertRaises(HTTPError) as error:
                post('check', source_id=current['sources'][0]['id'], xml=xml, revision=current['revision'])
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(json.load(error.exception)['error_code'], 'invalid_widget_config')
            error.exception.close()
        with self.assertRaises(HTTPError) as error:
            post('save', source_id=current['sources'][0]['id'], xml=XML, revision='stale')
        self.assertEqual(error.exception.code, 409)
        error.exception.close()
        with post('read') as response:
            self.assertEqual(json.load(response)['result']['revision'], current['revision'])
        from pyasm.security.authenticator import hash_password
        api.dispatch('insert', (dict(ticket=token, project='admin'), 'sthpw/login',
            dict(login='xml_reader', code='xml_reader', password=hash_password('reader-password'))))
        reader = api.get_ticket('xml_reader', 'reader-password')
        request = Request(FixtureServer.url + '/admin/widget-configuration/read',
            json.dumps(dict(ticket=reader, project='admin', search_type='sthpw/note')).encode(),
            headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
