"""Default Site provider and expressions, with named-site boundaries kept explicit."""
import importlib.util
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.biz import ExpressionParser
from pyasm.common import Container, Environment
from pyasm.common.errors import AuthenticationError, SecurityException, UnsupportedContract
from pyasm.search.search import RequestContext, request_context
from pyasm.security import Site
from tools.snapshot_probe import run_snapshot_case


class ExpressionSite(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='expression_contract', site_context=True, project='one', name=name, **options)
                     for name, options in [
                         ('code', dict(expression='@GET(site.code)', expected=[''], source_error='AttributeError')),
                         ('single_code', dict(expression='@GET(site.code)', single=True, expected='', source_error='AttributeError')),
                         ('unknown', dict(expression='@GET(site.missing)', expected=[None], source_error='AttributeError')),
                         ('root_code', dict(expression='@GET(site.code)', root=True, expected=[''], source_error='AttributeError')),
                         ('site_root', dict(expression='@GET(.code)', site_root=True, expected=[''], source_error='AttributeError')),
                         ('site_env', dict(expression='@GET(site_object.code)', site_env=True, expected=[''], source_error='AttributeError')),
                         ('naming', dict(expression='before{@GET(site.code)}after', root=True, naming=True, expected='beforeafter', source_error='AttributeError')),
                         ('objects', dict(expression='@SOBJECT(site)', expected=[{'type':'sthpw/virtual','project':'admin','code':''}])),
                         ('count', dict(expression='@COUNT(site)', expected=1)),
                         ('current', dict(call='get_site', expected='')),
                         ('first', dict(call='get_first_site', expected='')),
                         ('stack', dict(call='get_sites', expected=None)),
                         ('empty_stack', dict(call='get_sites', sites=[], expected=[])),
                         ('pop_unset', dict(call='pop_site', expected='')),
                         ('pop_empty', dict(call='pop_site', sites=[], expected=None)),
                         ('default_project', dict(call='get_default_project', expected='one')),
                         ('user_project', dict(call='get_user_project', default_project='two', expected='two')),
                         ('root', dict(call='get_site_root', expected='')),
                         ('path_parts', dict(call='break_up_request_path', args=['/projects/one/'], expected=[])),
                         ('login_site', dict(call='get_by_login', args=['admin'], expected='')),
                         ('ticket_site', dict(call='get_by_ticket', args=['arbitrary'], expected='')),
                         ('build_ticket', dict(call='build_ticket', args=[{'ticket':'opaque','project':'one'}], expected={'ticket':'opaque','project':'one'})),
                         ('validate_hook', dict(call='validate_ticket', args=['not-an-authenticated-ticket'], expected=True)),
                         ('connect_data', dict(call='get_connect_data', args=['', 'sthpw'], expected={})),
                         ('db_resource', dict(call='get_db_resource', args=['', 'sthpw'], expected=None)),
                         ('asset_hook', dict(call='get_asset_dir', expected=None)),
                         ('web_hook', dict(call='get_web_dir', expected=None)),
                         ('guest', dict(call='allow_guest', expected=None)),
                         ('guest_hashes', dict(call='get_guest_hashes', expected=[])),
                         ('api_mode', dict(call='get_api_mode', expected=None)),
                         ('site_data', dict(call='get_site_data', args=[''], expected={})),
                         ('site_class_data', dict(call='get_site_data', class_call=True, args=[''], expected={}, source_error='TypeError')),
                         ('explicit_factory', dict(expression='@SOBJECT(site)', site_class='pyasm.security.security.Site', expected=[{'type':'sthpw/virtual','project':'admin','code':''}])),
                         ('init_default', dict(call='init_site', args=[''], expected=None)),
                         ('named_context', dict(call='get_site', sites=['tenant'], expected={'error':'UnsupportedContract'}, source_value='tenant')),
                         ('named_connect', dict(call='get_connect_data', args=['tenant', 'sthpw'], expected={'error':'UnsupportedContract'}, source_value={})),
                         ('custom_provider', dict(expression='@SOBJECT(site)', site_class='pyasm.security.NoSuchSiteProvider', expected={'error':'UnsupportedContract'},
                                                  source_value=[{'type':'sthpw/virtual','project':'admin','code':''}])),
                     ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, case['expected'])
        if case.get('source_error'):
            self.assertEqual(original, {'error': case['source_error']})
        elif 'source_value' in case:
            self.assertEqual(original, case['source_value'])
        else:
            self.assertEqual(result, original)

    def test_named_site_refusal_keeps_current_security_and_state(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = self.api.auth.bind_security('admin', self.ticket)
            sites = Container.get('sites')
            for operation in (lambda: Site.set_site('tenant'), lambda: Site.init_site('tenant'),
                              lambda: Site.start_site('tenant'), lambda: Site.get_db_resource('tenant', 'sthpw')):
                with self.assertRaisesRegex(UnsupportedContract, 'multi-site'):
                    operation()
                self.assertIs(Environment.get_security(), security)
                self.assertIs(Container.get('sites'), sites)
            self.assertEqual(ExpressionParser().eval('@GET(site.code)'), [''])
            self.assertEqual(Site.get().get_search_key(), 'sthpw/virtual?id=-1')
            self.assertEqual(Site.get().get_data(), {'code': ''})

    def test_nested_policy_and_ticket_boundaries(self):
        ticket = {'ticket': self.ticket, 'project': 'one'}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            def policy(base):
                if base == 'sthpw/virtual':
                    raise SecurityException('Denied site read')
            with patch('tactic_stream.server.api.check_record_access', side_effect=policy):
                with self.assertRaisesRegex(SecurityException, 'Denied site read'):
                    self.api.eval(ticket, '@GET(site.code)')
            self.assertIsNone(Container.get('Expression:check_record_access'))
            with self.assertRaisesRegex(UnsupportedContract, 'provider'):
                self.api.eval(ticket, '@SOBJECT(site)')
        with self.assertRaises(AuthenticationError):
            self.api.dispatch('eval', ({'ticket':'not-an-authenticated-ticket','project':'one'}, '@GET(site.code)'))
        with self.assertRaises(UnsupportedContract):
            self.api.dispatch('eval', (dict(ticket, site='tenant'), '@GET(site.code)'))
        with self.assertRaises(UnsupportedContract):
            self.api.get_ticket('admin', 'private-read-test', site='tenant')


class ExpressionSiteTransport(unittest.TestCase):
    def test_original_sdk_default_site_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_site_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            with client.server:
                self.assertEqual(client.eval('@GET(site.code)'), [''])
                body = '''from pyasm.security import Site
from pyasm.biz import ExpressionParser
return {'code': Site.get().get_value('code'),
        'expression': ExpressionParser().eval('@GET(site.code)'),
        'data': Site.get_site_data('')}'''
                self.assertEqual(client.execute_python_script('', dict(code=body))['info'],
                                 {'code':'','expression':[''],'data':{}})
                with self.assertRaises(Fault):
                    client.execute_python_script('', dict(code='''from pyasm.search import Search
from pyasm.security import Site
obj = Search.get_by_code('contract/entity', 'A')
obj.set_value('amount', 99)
obj.commit()
Site.set_site('tenant')'''))
                self.assertEqual(client.query('contract/entity', [('code','A')])[0]['amount'], 0)
                with self.assertRaises(Fault):
                    client.eval('@SOBJECT(site)')
        finally:
            test_transport.Transport.tearDownClass()
