"""Exclude proven production dependencies, retaining shared fallback definitions."""
import unittest
from tools.frame_table.inventory import inventory, ROOT


class TableInventory(unittest.TestCase):
    def test_wiki_has_a_working_source_and_is_not_excluded_by_its_old_docstring(self):
        row = next(row for row in inventory()['widgets']
                   if row['widget'] == 'pyasm.widget.table_element_wdg.WikiElementWdg')
        self.assertNotIn(row['status'], ('excluded-unfinished', 'excluded-production'))

    def test_mandatory_production_wrappers_are_excluded_but_shared_defaults_stay(self):
        rows = {row['widget']: row for row in inventory()['widgets']}
        for name in ('pyasm.widget.table_element_wdg.RenderLinkTableElement',
                'pyasm.widget.table_element_wdg.SubmissionLinkTableElement',
                'tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg'):
            with self.subTest(name=name):
                self.assertEqual(rows[name]['status'], 'excluded-production')
                self.assertIn('legacy/src/', rows[name]['reason'])
        for name in ('pyasm.widget.table_element_wdg.PublishTableElement',
                'tactic.ui.table.table_element_wdg.GeneralPublishElementWdg',
                'tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg'):
            self.assertNotEqual(rows[name]['status'], 'excluded-production')
