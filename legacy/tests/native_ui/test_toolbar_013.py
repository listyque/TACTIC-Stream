"""Table shelf visibility follows the retained legacy get_setting, not Vue guesses."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from tactic.core.view_resolution import table_options
from tactic.core.table_settings import TableSettingsMixin

class ToolbarFlagsTests(unittest.TestCase):
    def assert_legacy(self, opts):
        before=copy.deepcopy(opts)
        actual=table_options(opts)
        for name in ('gear','insert','refresh','search','keyword_search','column_manager','layout_switcher','search_limit'):
            with self.subTest(name=name):
                expected=bool(TableSettingsMixin.get_setting(SimpleNamespace(kwargs=copy.deepcopy(opts)),name))
                self.assertEqual(actual['show_'+name],expected)
        self.assertEqual(opts,before,'Producing descriptors must not mutate cached widget config')
    def test_default(self):self.assert_legacy({})
    def test_disabled_gear(self):self.assert_legacy({'show_gear':False})
    def test_disabled_refresh(self):self.assert_legacy({'show_refresh':'false'})
    def test_disabled_insert(self):self.assert_legacy({'show_insert':False})
    def test_pipe_selection(self):self.assert_legacy({'settings':'insert|search|refresh'})
    def test_list_selection(self):self.assert_legacy({'settings':['search','layout_switcher']})
    def test_gear_dict(self):self.assert_legacy({'settings':{'gear':{'View':True},'search':True}})
    def test_nested_gear_settings_unchanged(self):self.assert_legacy({'settings':{'gear':True},'gear_settings':{'View':['Save a New View']}})
    def test_gear_pipe(self):self.assert_legacy({'settings':{'gear':True},'gear_settings':'File|Edit|View'})
    def test_gear_json(self):self.assert_legacy({'settings':{'gear':True},'gear_settings':"{'File': true, 'Edit': true}"})
    def test_original_empty_gear_is_not_reinterpreted(self):self.assert_legacy({'settings':{'gear':True}})
    def test_explicit_true_override(self):self.assert_legacy({'settings':'search','show_insert':'true','show_refresh':True})
    def test_mixed_false(self):self.assert_legacy({'settings':{'gear':False,'insert':False,'refresh':False},'show_refresh':True})
    def test_shelf_hides_entire_toolbar_not_authorization(self):
        flags=table_options({'show_shelf':False})
        self.assertFalse(flags['show_shelf']);self.assertTrue(flags['show_gear'])

if __name__=='__main__':unittest.main()
