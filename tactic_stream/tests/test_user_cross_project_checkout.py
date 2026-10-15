"""Checkout in the actual parent's project from a different request project."""
from functools import partial

import test_plugin_installation as plugin_tests
import test_user_checkout as checkout_tests
import test_configs as config_tests


class UserCrossProjectCheckout(plugin_tests.PluginInstallation):
    exercise = staticmethod(partial(checkout_tests.exercise, cross_project=True))


class UserCrossProjectCheckoutTransport(checkout_tests.UserCheckoutTransport):
    exercise = staticmethod(partial(checkout_tests.exercise, cross_project=True))


class CrossProjectCheckoutParity(config_tests.CommandApiParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='command_api_contract', name='cross_project_checkout', snapshot=True, cross_project=True)]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['restored_project'], 'two')
        self.assertEqual(original['restored_project'], 'two')
        super().assert_case_result(case, result, original)
