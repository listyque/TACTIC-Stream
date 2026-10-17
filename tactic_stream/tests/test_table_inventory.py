"""The widget census groups real aliases without hiding unresolved workflows."""

import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tools.frame_table.inventory import database_sources, inventory


class TableInventory(unittest.TestCase):
    def test_aliases_and_nested_references_preserve_pending_classes(self):
        xml = """<config><table>
        <element name="a"><display class="AuxDataWdg"/></element>
        <element name="b"><display class="pyasm.widget.AuxDataWdg"/></element>
        <element name="c"><display class="tactic.ui.table.TaskSummaryElementWdg"/></element>
        <element name="d"><display class="tactic.ui.table.HiddenRowElementWdg">
          <dynamic_class>tactic.ui.table.GanttElementWdg</dynamic_class>
        </display></element></table></config>"""
        with patch(
            "tools.frame_table.inventory.sources", return_value=[("fixture", xml)]
        ):
            result = inventory()
        rows = {row["widget"]: row for row in result["widgets"]}
        aux = rows["pyasm.widget.table_element_wdg.AuxDataWdg"]
        self.assertEqual(aux["status"], "pending")
        self.assertEqual(len(aux["handlers"]), 2)
        self.assertEqual(len(aux["uses"]), 2)
        self.assertEqual(
            rows["tactic.ui.table.task_element_wdg.TaskSummaryElementWdg"]["status"],
            "adapted",
        )
        self.assertEqual(
            rows["tactic.ui.table.gantt_element_wdg.GanttElementWdg"]["status"],
            "pending",
        )

    def test_database_scan_does_not_modify_configurations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.db"
            with closing(sqlite3.connect(path)) as db:
                db.execute(
                    "CREATE TABLE spt_widget_config (code,search_type,view,s_status,config)"
                )
                db.execute(
                    "INSERT INTO spt_widget_config VALUES (?,?,?,?,?)",
                    ("A", "cg/assets", "table", "retired", "<config/>"),
                )
                db.commit()
            before = hashlib.sha256(path.read_bytes()).digest()
            self.assertEqual(len(list(database_sources(path))), 1)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
