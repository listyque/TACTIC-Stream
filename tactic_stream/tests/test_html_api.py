"""Native HTML and server-JS entry contracts through the unchanged XML-RPC SDK."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from xmlrpc.client import Fault

import test_transport
from tactic_client_lib import TacticServerStub


class HtmlApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.addClassCleanup(test_transport.Transport.tearDownClass)
        cls.store = test_transport.Transport.store
        cls.temp = test_transport.Transport.temp
        cls.baseline = test_transport.Transport.baseline
        cls.url = test_transport.Transport.url

    def setUp(self):
        test_transport.Transport.setUp(self)
        self.client = TacticServerStub(setup=False, protocol='xmlrpc')
        self.client.set_server(self.url)
        self.client.set_project('one')
        self.client.set_ticket(self.client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(self.client.server.__exit__, None, None, None)
        self.auth = self.client.ticket
        self.keys = ['contract/entity?project=one&code=A', 'contract/entity?project=one&code=B']

    def test_widget_forms_and_request_palette_do_not_leak(self):
        self.assertEqual(self.client.get_widget('pyasm.web.HtmlElement', {'type': 'span', 'child': 'Hello'}), '<span>Hello</span>')
        self.assertIn('linear-gradient(', self.client.get_widget('html_api_widgets.EchoWdg', {'gradient':True}))
        html = self.client.get_widget('html_api_widgets.EchoWdg', {'text': 'first '}, {'value': 'second'})
        self.assertIn('first second', html)
        result = self.client.execute_python_script('', {'code': """
from pyasm.web import Palette
before = Palette.get().color('color')
server.set_palette('DARK')
html = server.get_widget('html_api_widgets.EchoWdg', {'text':'dark'})
Palette.pop_palette()
return {'before': before, 'after': Palette.get().color('color'), 'html': html}
"""})['info']
        self.assertEqual(result['before'], result['after'])
        self.assertIn('color: #CCC', result['html'])
        self.assertEqual(self.client.get_widget('html_api_widgets.EchoWdg', {'text':'first '}, {'value':'second'}), html)
        self.assertIsNone(self.client.set_palette('DARK'))

    def test_render_failures_roll_back_writes_and_reject_non_widgets(self):
        with self.assertRaises(Fault):
            self.client.get_widget('html_api_widgets.BrokenWdg')
        self.assertEqual(self.client.query('sthpw/note', filters=[('note', 'render must roll back')]), [])
        with self.assertRaises(Fault):
            self.client.get_widget('pyasm.common.Common')
        with self.assertRaises(Fault) as missing:
            self.client.get_widget('absent.Widget')
        self.assertEqual(missing.exception.faultCode, 501)
        self.assertIn('Native HTML widget class is unavailable', missing.exception.faultString)
        with self.assertRaises(Fault):
            self.client.server.get_widget(self.auth, 'pyasm.web.HtmlElement', {}, {}, {'spt_help': True})
        self.assertEqual(self.client.get_widget('pyasm.web.HtmlElement', {'type': 'span', 'child': 'after'}), '<span>after</span>')

    def test_native_column_cells_and_source_single_key_quirk(self):
        column_widgets = lambda keys, column: self.client.server.get_column_widgets(self.auth, 'contract/entity', keys, column)
        cells = column_widgets(self.keys, 'name')
        self.assertEqual([len(row) for row in cells], [1, 1])
        self.assertIn('Первый', cells[0][0])
        self.assertIn("O'Reilly", cells[1][0])
        self.assertTrue(all('<td ' in row[0] and 'spt_cell_edit' in row[0] and 'spt_input_value' in row[0] for row in cells))
        self.assertEqual(column_widgets(self.keys[:1], 'name'), [])
        self.assertEqual(column_widgets([], 'name'), [])
        cells2 = column_widgets(['contract/entity?project=one&id=-1'] + self.keys, 'code')
        self.assertIn('>A<', cells2[0][0]); self.assertIn('>B<', cells2[1][0])
        with self.assertRaises(Fault):
            column_widgets(self.keys + ['contract/entity?project=one&code=absent'], 'name')

    def test_top_layout_round_trip_nested_xml_and_other_layout_denial(self):
        values = {'query': 'a<&b', 'nonstring': [1]}
        options = {'text': 'Hello', 'nested': {'first': 'value', 'deep': {'second': 'other'}}}
        state = lambda panel, widget, opts, vals={}: self.client.server.set_application_state(self.client.ticket, 'top_layout', panel, widget, opts, vals)
        self.assertIs(state('main_body', 'html_api_widgets.EchoWdg', options, values), True)
        setting = lambda: self.client.server.get_widget_setting(self.client.ticket, 'top_layout')
        stored = setting()
        self.assertIn('html_api_widgets.EchoWdg', stored)
        from xml.etree import ElementTree as ET
        tree = ET.fromstring(stored)
        self.assertEqual(tree.findtext("application/element[@name='main_body']/display/nested/first"), 'value')
        self.assertEqual(tree.findtext("application/element[@name='main_body']/display/nested/deep/second"), 'other')
        self.assertIn('a&lt;&amp;b', stored)
        self.assertNotIn('nonstring', stored)
        self.assertIs(state('left_nav', 'pyasm.web.DivWdg', {}), True)
        self.assertIn('html_api_widgets.EchoWdg', setting())
        with self.assertRaises(Fault):
            self.client.server.set_application_state(self.auth, 'browser_layout', 'main_body', 'pyasm.web.DivWdg', {})
        self.client.set_project('two')
        self.assertFalse(setting())

    def test_js_saved_path_precedence_kwargs_and_native_api_writes(self):
        self.client.insert('config/custom_script', {'folder':'api8', 'title':'run', 'language':'server_js',
            'script': "var obj = server.insert('sthpw/note', {note: input.text}); return {key: obj.__search_key__, ping: server.ping(), value: input.value};"})
        result = self.client.execute_js_script('api8/run', {'input': {'text':'JS note', 'value':7}, 'code':'return false;'})
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['description'], 'Run JsCmd with script path [api8/run]')
        self.assertEqual(result['info']['value'], 7)
        self.assertEqual(result['info']['ping'], 'OK')
        self.assertEqual(self.client.get_by_search_key(result['info']['key'])['note'], 'JS note')
        self.assertEqual(self.client.execute_js_script('', {'code': "return server.query('sthpw/note', {filters:[['note','JS note']], columns:['note'], single:true});"})['info']['note'], 'JS note')

    def test_js_late_and_api_errors_roll_back_and_preserve_useful_errors(self):
        for code in ("server.insert('sthpw/note', {note:'JS rollback'}); throw new Error('late JS failure');",
                     "server.insert('sthpw/note', {note:'JS rollback'}); server.update('contract/entity?project=one&code=A', {missing_column:'fail'});",
                     "return server._delegate('get_ticket', ['admin', 'forbidden']);"):
            with self.subTest(code=code), self.assertRaises(Fault) as error:
                self.client.execute_js_script('', {'code':code})
            self.assertTrue(any(text in error.exception.faultString for text in ('late JS failure','missing_column','get_ticket')))
            self.assertEqual(self.client.query('sthpw/note', filters=[('note','JS rollback')]), [])
        self.assertEqual(self.client.execute_js_script('', {'code':"try {server.update('contract/entity?project=one&code=A', {missing_column:1});} catch (e) {return e.message;}"})['info'].find('missing_column') >= 0, True)
        self.assertIsNone(self.client.execute_js_script('', {'code':'var noReturn = 1;'})['info'])
        with self.assertRaises(Fault):
            self.client.execute_js_script('missing/script')

    def test_js_contexts_do_not_leak_between_concurrent_requests(self):
        def run(number):
            client = TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(self.url); client.set_project('one'); client.set_ticket(self.auth['ticket'])
            try:
                result = client.execute_js_script('', {'code': 'globalThis.secret = value; return {secret:secret, absent:typeof other};', 'value': number})['info']
                return result
            finally:
                client.server.__exit__(None, None, None)
        with ThreadPoolExecutor(max_workers=3) as pool:
            self.assertEqual(list(pool.map(run, range(6))), [{'secret': n, 'absent':'undefined'} for n in range(6)])

    def test_palette_rejects_python_execution_and_unprivileged_html_js_are_denied(self):
        with self.assertRaises(Fault):
            self.client.set_palette("__import__('os').getcwd()")
        from pyasm.security.authenticator import hash_password
        self.client.insert('sthpw/login', {'login': 'api8-reader', 'password':hash_password('private-reader-password')})
        self.client.set_ticket(self.client.get_ticket('api8-reader', 'private-reader-password'))
        for method, args in [('get_widget', ('pyasm.web.DivWdg',)), ('execute_js_script', ('', {'code':'return 1;'})),
                             ('get_column_widgets', ('contract/entity', self.keys, 'name'))]:
            with self.subTest(method=method), self.assertRaises(Fault):
                getattr(self.client.server, method)(self.client.ticket, *args)

    def test_server_js_rejects_promise_and_cyclic_results_with_rollback(self):
        for tail in ('return Promise.resolve(1);', 'var a={}; a.self=a; return a;'):
            with self.subTest(tail=tail), self.assertRaises(Fault):
                self.client.execute_js_script('', {'code': "server.insert('sthpw/note', {note:'api8-serialization'});" + tail})
            self.assertEqual(self.client.query('sthpw/note', filters=[['note','api8-serialization']]), [])

    def test_widget_key_binds_owner_and_arguments_and_nested_web_state(self):
        result = self.client.execute_python_script('', {'code': """
from pyasm.common import Config, Environment, jsondumps
from pyasm.web import DivWdg, WebState
from pathlib import Path
Config.set_value('security', 'api_widget_restricted', 'true')
key = DivWdg().generate_widget_key('html_api_widgets.EchoWdg', {'text':'bound'})
html = server.get_widget(key, {'text':'bound'})
denied = []
for args in ({'text':'changed'}, {'new':'value'}):
    try: server.get_widget(key, args)
    except Exception as error: denied.append(str(error))
path = Path(Environment.get_tmp_dir(include_ticket=True)) / ('widget_key_' + key[1:] + '.txt')
path.write_text(jsondumps({'method':'html_api_widgets.EchoWdg', 'login':'other', 'inputs':{}}), encoding='utf-8')
try: server.get_widget(key, {})
except Exception as error: denied.append(str(error))
state = WebState.get()
state.push({'outer': 'one'})
state.push({'inner': 'two'})
state.pop()
return {'html':html, 'denied':denied, 'state':state.get_current()}
"""})['info']
        self.assertIn('bound', result['html'])
        self.assertEqual(len(result['denied']), 3)
        self.assertIn('another user', result['denied'][2])
        self.assertEqual(result['state'], {'outer':'one'})

    def test_native_server_js_trigger_and_late_failure_rollback(self):
        script = self.client.insert('config/custom_script', {'folder':'api8', 'title':'trigger', 'language':'server_js',
            'script': "return {event:input.event, project:server.get_project(), html:server.get_widget('pyasm.web.HtmlElement', {args:{type:'span', child:'JS HTML'}})};"})
        code = """
from tactic.command import PythonTrigger
trigger = PythonTrigger(script_path='api8/trigger')
trigger.input = {'event':'contract|js'}
return trigger.execute()
"""
        self.assertEqual(self.client.execute_python_script('', {'code':code})['info'],
            {'event':'contract|js', 'project':'one', 'html':'<span>JS HTML</span>'})
        self.client.update(script['__search_key__'], {'script':"server.insert('sthpw/note', {note:'api8-trigger-rollback'}); throw new Error('late trigger JS error');"})
        with self.assertRaises(Fault):
            self.client.execute_python_script('', {'code':code})
        self.assertEqual(self.client.query('sthpw/note', filters=[['note','api8-trigger-rollback']]), [])
        with self.assertRaises(Fault):
            self.client.execute_js_script('', {'code': "server.insert('sthpw/note', {note:'api8-widget-js-rollback'}); return server.get_widget('absent.Widget', {args:{}});"})
        self.assertEqual(self.client.query('sthpw/note', filters=[['note','api8-widget-js-rollback']]), [])


if __name__ == '__main__':
    unittest.main()
