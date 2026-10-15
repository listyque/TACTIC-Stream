"""Actual old/new account writes, including explicit security bug corrections."""
from pathlib import Path
import shutil
import tempfile
import test_read_parity as read_tests
from pyasm.search.storage import Store
from pyasm.search.search import RequestContext, request_context
from tools.security_lifecycle_probe import run_security_lifecycle_case


class SecurityLifecycleParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        operations = ['registration', 'password', 'membership', 'cached_membership', 'duplicate_membership',
                      'ticket', 'expired_ticket', 'invalid_login', 'stolen_ticket', 'password_revocation',
                      'disabled_login', 'group_deletion', 'attempts']
        cls.cases = [{'method': 'security_lifecycle_contract', 'name': operation, 'operation': operation,
                      'project': 'admin'} for operation in operations]
        cls.cases.append(dict(method='security_lifecycle_contract', name='pending_ticket', operation='ticket',
                              project='admin', commit=False))

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='tactic-stream-security-parity-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_security_lifecycle_case(case)

    def assert_case_result(self, case, result, original):
        # Exact equality cases stay exact. Intentional source bugs have separate
        # old/new expectations, never equality between matching exceptions.
        operation = case['operation']
        if operation == 'cached_membership':
            self.assertEqual(original['after'], original['before'])
            self.assertEqual(result, {'before': original['before'], 'after': []})
        elif operation == 'duplicate_membership':
            self.assertEqual(original, {'count': 2})
            self.assertEqual(result, {'count': 1})
        elif operation == 'ticket':
            if case.get('commit') is False:
                self.assertEqual(result, original)
                self.assertFalse(result['stored'])
                return
            self.assertFalse(original['expiry'])
            expected = dict(original, expiry=True)
            self.assertEqual(result, expected)
        elif operation in ('expired_ticket', 'password_revocation'):
            self.assertEqual(original, {'valid': True})
            self.assertEqual(result, {'valid': False})
        elif operation == 'invalid_login':
            self.assertTrue(original['logged_in'])
            self.assertEqual(original['user'], 'admin')
            self.assertEqual(result, {'login': False, 'logged_in': False, 'user': None, 'sudo': False})
        elif operation == 'stolen_ticket':
            self.assertFalse(original['rejected'])
            self.assertEqual(result, {'rejected': True, 'owner': 'admin', 'logged_in': False})
        elif operation == 'disabled_login':
            self.assertEqual(original, {'accepted': True})
            self.assertEqual(result, {'accepted': False})
        elif operation == 'group_deletion':
            self.assertEqual(original, {'memberships': 1})
            self.assertEqual(result, {'memberships': 0})
        elif operation == 'attempts':
            self.assertEqual(original['error'], 'AttributeError')
            self.assertEqual(result, {'allowed': True, 'attempts': {'invalid_logins': 1}})
        else:
            self.assertNotIn('error', original)
            self.assertNotIn('error', result)
            self.assertEqual(result, original)
