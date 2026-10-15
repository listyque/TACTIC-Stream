"""Backend configurations compared with the actual original runtime."""
import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class ConfigParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='config_contract', name='config_failure', fail=True),
                     dict(method='config_contract', name='config_success'),
                     dict(method='config_contract', name='config_move', bug='move'),
                     dict(method='config_contract', name='config_warm', warm_cache=True),
                     dict(method='config_contract', name='config_extra_failure', extra_config=True, fail=True),
                     dict(method='config_contract', name='config_extra', extra_config=True),
                     dict(method='config_contract', name='config_bad_drop', extra_config=True, bug='property_drop')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('bug') == 'property_drop':
            self.assertEqual(result, dict(error='SqlException', widget_rows=0))
            self.assertEqual(original, dict(error='AssertionError', widget_rows=0))
            return
        if case.get('bug') == 'move':
            self.assertEqual(original.pop('move'), dict(error='AttributeError', names=['name']))
            self.assertEqual(result.pop('move'), dict(error=None, names=['amount', 'name']))
        if case.get('warm_cache'):
            self.assertEqual(original.pop('trigger'), [])
            self.assertEqual(original.pop('trigger_setting'), '')
            self.assertEqual(result.pop('trigger'), ['called'])
            self.assertEqual(result.pop('trigger_setting'), 'called')
        self.assertEqual(result, original)


class ExportParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='export_contract', name='export'),
                     dict(method='export_contract', name='export_quotes', bug='quotes'),
                     dict(method='export_contract', name='export_empty', bug='empty'),
                     dict(method='export_contract', name='export_failure', fail=True)]

    def assert_case_result(self, case, result, original):
        if case.get('fail'):
            self.assertEqual(original, dict(error='late export failure', previous=False, zip_exists=True, rows=0))
            self.assertEqual(result, dict(error='late export failure', previous=True, zip_exists=False, rows=0))
        elif case.get('bug') == 'quotes':
            self.assertEqual(original, dict(exists=True, rows=[['EXPORT_OBJ', "return '''точный текст'''", 23]]))
            self.assertEqual(result, dict(exists=True, rows=[['EXPORT_OBJ', 'return """точный текст"""', 23]]))
        elif case.get('bug') == 'empty':
            self.assertEqual(original, dict(exists=False, rows=[]))
            self.assertEqual(result, dict(exists=True, rows=[]))
        else:
            self.assertEqual(result, original)


class UninstallParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='uninstall_contract', name='uninstall'),
                     dict(method='uninstall_contract', name='uninstall_failure', fail=True),
                     dict(method='uninstall_contract', name='uninstall_delete', bug='delete'),
                     dict(method='uninstall_contract', name='uninstall_pipeline', pipeline=True),
                     dict(method='uninstall_contract', name='uninstall_results', results=True),
                     dict(method='uninstall_contract', name='uninstall_table', table=True)]

    def assert_case_result(self, case, result, original):
        if case.get('results'):
            self.assertEqual(original, dict(result_preserved=False))
            self.assertEqual(result, dict(result_preserved=True))
        elif case.get('pipeline'):
            self.assertTrue(original.pop('pipeline'))
            self.assertFalse(result.pop('pipeline'))
            self.assertEqual(result, original)
        elif case.get('table'):
            self.assertEqual(original, dict(absent=True, registry=True, id_preserved=False, name='Точный backup',
                                           null=True, null_literal=False, backup_removed=True))
            self.assertEqual(result, dict(absent=True, registry=True, id_preserved=True, name='Точный backup',
                                         null=True, null_literal=True, backup_removed=True))
        elif case.get('bug') == 'delete':
            self.assertEqual(original, dict(error=None, rows=1, contents=0, plugin=False, undo='undo called', files=True))
            self.assertEqual(result, dict(error='delete refused', rows=2, contents=1, plugin=True, undo='', files=True))
        else:
            self.assertEqual(result, original)


class TemplateCheckParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='template_check_contract', name='valid'),
                     dict(method='template_check_contract', name='type', bug='type'),
                     dict(method='template_check_contract', name='prefix', bug='prefix'),
                     dict(method='template_check_contract', name='namespace', bug='namespace')]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, dict(error='TacticException' if case.get('bug') else None))
        self.assertEqual(original, dict(error='NameError' if case.get('bug') in ('type', 'namespace') else 'TacticException'))


class TemplateExportParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='template_export_contract', name='template'),
                     dict(method='template_export_contract', name='namespace', namespace=True),
                     dict(method='template_export_contract', name='failure', fail=True)]

    def assert_case_result(self, case, result, original):
        if case.get('fail'):
            self.assertEqual(result, dict(previous=True, zip_exists=False))
            self.assertEqual(original, dict(previous=False, zip_exists=True))
            return
        self.assertEqual(result, dict(definition=True, script='return 42\n# Точный текст', sequence_floor=True, notification=True, zip_manifest=True, notice_subject=True))
        self.assertEqual(original, dict(definition=not case.get('namespace', False),
                                       script='return 42\n# Точный текст', sequence_floor=False, notification=True, zip_manifest=True, notice_subject=True))


class ConfigApiParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='config_api_contract', name='api'),
                     dict(method='config_api_contract', name='personal', bug='personal'),
                     dict(method='config_api_contract', name='subscription', bug='subscription'),
                     dict(method='config_api_contract', name='separator', bug='separator'),
                     dict(method='config_api_contract', name='attribute', bug='attribute')]

    def assert_case_result(self, case, result, original):
        if case.get('bug') == 'personal':
            self.assertEqual(result, dict(personal=True, global_names=['global'], personal_names=['personal']))
            self.assertEqual(original, dict(personal=False, global_names=['personal'], personal_names=['personal']))
        elif case.get('bug') == 'subscription':
            self.assertEqual(result, dict(other_subscribed=True))
            self.assertEqual(original, dict(other_subscribed=False))
        elif case.get('bug') == 'separator':
            self.assertEqual(result.pop('display'), 'SeparatorWdg')
            self.assertEqual(original.pop('display'), 'LinkWdg')
            self.assertEqual(result, original)
        elif case.get('bug') == 'attribute':
            self.assertEqual(result, dict(error=None, names=['second', 'first']))
            self.assertEqual(original, dict(error='AttributeError', names=[]))
        else:
            self.assertTrue(result.pop('security_preserved'))
            self.assertFalse(original.pop('security_preserved'))
            self.assertTrue(result.pop('definition_deleted'))
            self.assertTrue(original.pop('definition_deleted'))
            self.assertEqual(result.pop('queried'), 1)
            self.assertIsNone(result.pop('query_error'))
            self.assertIsNone(original.pop('queried'))
            self.assertEqual(original.pop('query_error'), 'SecurityException')
            self.assertEqual(result['definition']['options'].pop('text'), "O'Reilly & текст")
            self.assertEqual(original['definition']['options'].pop('text'), "O'Reilly &amp; текст")
            self.assertTrue(result.pop('options_preserved'))
            self.assertFalse(original.pop('options_preserved'))
            self.assertEqual(result, original)


class CommandApiParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='command_api_contract', name='commands'),
                     dict(method='command_api_contract', name='zero', zero=True),
                     dict(method='command_api_contract', name='snapshot', snapshot=True),
                     dict(method='command_api_contract', name='quotes', snapshot=True, quotes=True)]

    def assert_case_result(self, case, result, original):
        if case.get('zero'):
            self.assertEqual(result['queue'].pop('priority'), '0')
            self.assertEqual(original['queue'].pop('priority'), '9999')
        if case.get('snapshot'):
            self.assertEqual(result.pop('trigger'), 'command_api_snapshot')
            self.assertEqual(original.pop('trigger'), '')
            expected = dict(version='1', description='Текст & данные',
                            file="O'Reilly.txt" if case.get('quotes') else 'example.txt',
                            checkin_dir='input', source_path='input/source.txt')
            self.assertEqual(result['xml'], expected)
            self.assertIsNone(result['xml_error'])
            self.assertTrue(result['cache_unchanged'])
            self.assertIsNone(result['checkout_error'])
            self.assertEqual(result['paths'], dict(client_lib_paths=1, sandbox_paths=1, web_paths=1))
            if case.get('quotes'):
                self.assertIsNone(original.pop('xml'))
                self.assertEqual(original.pop('xml_error'), 'XmlException')
                result.pop('xml')
                result.pop('xml_error')
            self.assertEqual(result, original)
            return
        self.assertEqual(result.pop('claimed'), 'locked')
        self.assertEqual(original.pop('claimed'), 'pending')
        self.assertEqual(result, original)


class QueueParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='queue_contract', name='queue'),
                     dict(method='queue_contract', name='permanent', failure='tactic')]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, original)
        self.assertEqual(result['state'], 'error' if case.get('failure') else 'complete')
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['jobs'], 0)


class DiagnosticParity(ConfigParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='diagnostic_contract', name='standalone', standalone=True),
                     dict(method='diagnostic_contract', name='commit'),
                     dict(method='diagnostic_contract', name='rollback', fail=True),
                     dict(method='diagnostic_contract', name='api', api=True)]

    def assert_case_result(self, case, result, original):
        if case.get('fail'):
            # Source DebugLog advertises a separate transaction but rollback loses the row.
            self.assertEqual(original.pop('logs'), [])
            native_logs = result.pop('logs')
            self.assertEqual(len(native_logs), 1)
            self.assertEqual(result, original)
            result['logs'] = native_logs
        else:
            self.assertEqual(result, original)
        self.assertTrue(result['saved'])
        self.assertEqual(len(result['logs']), 1)
        if case.get('fail'):
            self.assertEqual(result['exceptions'], 1)
            self.assertEqual(result['error'], 'ValueError')
            self.assertFalse(result['value'])
