"""Concrete sequence checkout paths consumed by the unchanged XML-RPC SDK."""
from functools import partial

import test_plugin_installation as plugin_tests
import test_user_checkout as checkout_tests
import test_configs as config_tests


class UserGroupCheckout(plugin_tests.PluginInstallation):
    exercise = staticmethod(partial(checkout_tests.exercise, groups=True))


class UserGroupCheckoutTransport(checkout_tests.UserCheckoutTransport):
    exercise = staticmethod(partial(checkout_tests.exercise, groups=True, cross_project=True))


class GroupCheckoutParity(config_tests.CommandApiParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='command_api_contract', name='group_checkout', snapshot=True, groups=True)]

    def assert_case_result(self, case, result, original):
        names = ['example.%04d.txt' % frame for frame in (1, 3, 5)]
        self.assertEqual(result.pop('names'), {name: names for name in ('client_lib_paths', 'sandbox_paths', 'web_paths')})
        self.assertEqual(original.pop('names'), {name: ['example.####.txt'] for name in ('client_lib_paths', 'sandbox_paths', 'web_paths')})
        self.assertEqual(result.pop('paths'), dict(client_lib_paths=3, sandbox_paths=3, web_paths=3))
        self.assertEqual(original.pop('paths'), dict(client_lib_paths=1, sandbox_paths=1, web_paths=1))
        self.assertEqual(result.pop('trigger'), 'command_api_snapshot')
        self.assertEqual(original.pop('trigger'), '')
        self.assertIsNone(result['checkout_error'])
        self.assertTrue(result['cache_unchanged'])
        self.assertEqual(result['xml']['file'], 'example.####.txt')
        self.assertEqual(result, original)
