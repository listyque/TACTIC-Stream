import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class CalendarForm(read_tests.ReadParity):
    test_expressions_and_sql_remain_explicitly_unsupported = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import calendar_form_contract
        with cls.store.connection(write=True) as db:
            calendar_form_contract.install_fixture(db)
        cls.cases = [dict(method='calendar_form_contract', name=mode, operation=mode, project='one')
                     for mode in ('metadata', 'edit')]

    def new_result(self, case):
        import calendar_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return calendar_form_contract.run(case)

    def assert_case_result(self, case, result, original):
        # The source get_value refers to an unassigned date for *_day fields.
        self.assertEqual(original['display'][2], dict(error='UnboundLocalError'))
        self.assertEqual(result['display'][2], '2026-10-08')
        original['display'][2] = result['display'][2]
        if isinstance(original['display'][1], dict):
            self.assertEqual(original['display'][1], dict(error='ParserError'))
            self.assertEqual(result['display'][1], '2026-10-07 10:02')
            original['display'][1] = result['display'][1]
        if case['operation'] == 'edit':
            # The source commit formatter removes microseconds from datetime values.
            self.assertEqual(original['saved']['deadline'], '2026-11-02 01:30:15')
            self.assertEqual(original['after_error']['deadline'], '2026-11-02 01:30:15')
            original['saved']['deadline'] = result['saved']['deadline']
            original['after_error']['deadline'] = result['after_error']['deadline']
        self.assertEqual(result, original)
        if case['operation'] == 'edit':
            self.assertEqual(result['saved'], dict(deadline='2026-11-02 01:30:15.250000', due_day='2026-11-05'))
            self.assertEqual(result['saved'], result['after_error'])

    def test_timezone_defaults_and_invalid_dates(self):
        from pyasm.common import SPTDate
        from tactic.ui.panel import EditWdg
        from tactic.ui.widget import CalendarInputWdg
        from pyasm.search import Search
        import calendar_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                calendar_form_contract.run({'operation': 'metadata'})
                date = SPTDate.add_timezone('2026-11-02T10:30:15.250', 'Asia/Tokyo')
                self.assertTrue(SPTDate.has_timezone(date))
                self.assertFalse(SPTDate.has_timezone('2026-11-02T10:30'))
                self.assertEqual(str(SPTDate.convert(date)), '2026-11-02 01:30:15.250000')
                self.assertTrue(SPTDate.has_timezone(SPTDate.add_local_timezone('2026-11-02T10:30')))
                self.assertTrue(SPTDate.has_timezone(SPTDate.add_timezone('2026-11-02T10:30', 'local')))
                with self.assertRaisesRegex(ValueError, 'Unknown time zone'):
                    SPTDate.add_timezone('2026-11-02T10:30', 'bad/timezone')
                with self.assertRaisesRegex(ValueError, 'Unknown time zone'):
                    SPTDate.convert_to_timezone(date, 'bad/timezone')
                default = EditWdg.get_default_display_wdg('deadline', {'required': 'true'}, 'datetime')
                self.assertIsInstance(default, CalendarInputWdg)
                self.assertEqual(default.get_option('show_time'), 'true')
                self.assertEqual(default.get_option('required'), 'true')
                obj = Search.get_by_code('contract/calendar_entity', 'C')
                obj.set_value('deadline', 'invalid calendar value')
                calendar = CalendarInputWdg('deadline')
                calendar.set_sobject(obj)
                with self.assertRaisesRegex(ValueError, 'Invalid calendar value'):
                    calendar.get_value()
