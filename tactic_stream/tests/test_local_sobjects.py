import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from tools.snapshot_probe import run_snapshot_case


class LocalSObjectsParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='local_sobjects_contract', name='local_sdk_objects', project='admin'),
                     dict(method='local_sobjects_contract', name='base_dirs_api', project='admin', base_dirs=True)]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            return run_snapshot_case(case)

    def test_projection_mixed_types_and_id_keys(self):
        result = self.new_result(dict(method='local_sobjects_contract', fixes=True))
        self.assertTrue(result['unchanged'])
        project, file = result['projected']
        self.assertEqual(set(file), {'code', '__search_key__', '__search_type__'})
        self.assertEqual(file['__search_key__'], 'sthpw/file?id=37')
        self.assertEqual(file['__search_type__'], 'sthpw/file')
        self.assertIn('sthpw/project?', project['__search_key__'])
        self.assertIn('id=', project['__search_key__'])

    def test_local_conversion_requires_security_and_current_request(self):
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException, UnsupportedContract
        from pyasm.web.api_xmlrpc import ApiXMLRPC
        from pyasm.search import Search
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            api = ApiXMLRPC()
            obj = Search.get_by_code('sthpw/project', 'admin')
            security = Environment.get_security()
            Environment.set_security(None)
            with self.assertRaises(SecurityException):
                api._get_sobjects_dict([obj])
            with self.assertRaises(SecurityException):
                api._get_sobjects(obj.get_search_key())
            Environment.set_security(security)
            self.assertEqual(api._get_sobject_dict(obj)['code'], 'admin')
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            with self.assertRaises(UnsupportedContract):
                api._get_sobjects_dict([obj])
            with self.assertRaises(UnsupportedContract):
                api._get_sobjects(obj.get_search_key())

    def test_local_lookup_original_key_contract(self):
        from pyasm.web.api_xmlrpc import ApiXMLRPC, ApiException
        from pyasm.search import SObject
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            api = ApiXMLRPC()
            key = 'contract/entity?project=one&code=A'
            rows = api._get_sobjects([key.replace('&', '&amp;amp;'),
                                     {'__search_key__': key}, key])
            self.assertEqual([obj.get_code() for obj in rows], ['A', 'A', 'A'])
            self.assertTrue(all(isinstance(obj, SObject) for obj in rows))
            self.assertIs(rows[0], rows[1])
            self.assertEqual(api._get_sobjects(key)[0].get_code(), 'A')
            self.assertEqual(rows[0].get_attr_value('code'), 'A')
            from pyasm.common import Environment
            from pyasm.common.errors import SecurityException
            from unittest.mock import patch
            with patch.object(Environment.get_security(), 'is_admin', return_value=False):
                with self.assertRaises(SecurityException):
                    api._get_sobjects('sthpw/login?code=admin')
            missing = 'contract/entity?project=one&code=NO_SUCH_OBJECT'
            self.assertEqual(api._get_sobjects([key, missing], no_exception=True), [])
            for value, message in ((missing, 'does not exist'), ({'code': 'A'}, 'Not a valid search key'),
                                   ({}, 'is None'),
                                   ([], 'is None'), (None, 'is None')):
                with self.subTest(value=value), self.assertRaisesRegex(ApiException, message):
                    api._get_sobjects(value, no_exception=True if value != missing else False)
