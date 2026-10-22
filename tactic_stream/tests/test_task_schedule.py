"""Compare copied calendar/Gantt/weekday calculations with the Handler source."""
import ast
import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
import unittest

from tactic.ui.table import task_schedule as native


class TaskSchedule(unittest.TestCase):
    def test_handler_projections_and_transformations(self):
        root = Path(__file__).resolve().parents[2].parent / 'TH/thlib/ui'
        if not root.is_dir():
            self.skipTest('Sibling Handler checkout required for source comparison')
        namespace = dict(calendar=calendar, date=date, datetime=datetime, timedelta=timedelta)
        # Pure original functions, no Qt, client imports or Handler modification.
        for path, names in [(root / 'task_data.py', {'parse_datetime', 'progress_value', 'due_state', 'calendar_cells', 'gantt_layout'}),
                            (root / 'task_workspace/gantt_schedule.py', None)]:
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and (names is None or node.name in names)]
            exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
        records = [dict(taskCode='A', parentTitle='Alpha', start='2030-01-04 09:13:00', end='2030-01-08 17:20:00', assigned='same', progress=25, groupKey='same'),
                   dict(taskCode='B', parentTitle='Beta', start='2030-01-07T08:00:00', end='2030-01-09T16:45:00', assigned='same', progress=75, groupKey='same'),
                   dict(taskCode='C', start='', end='', progress=0),
                   dict(taskCode='D', start='2030-01-10', end='2030-01-09', progress=0)]
        milestones = [dict(value='release', label='Release', dueDate='2030-01-12')]
        for name, args in [('calendar_cells', (2030, 1, records, date(2030, 1, 8), milestones)),
                           ('gantt_layout', (records, date(2030, 1, 8), milestones))]:
            self.assertEqual(getattr(native, name)(*args), namespace[name](*args))
        peers = [(row['taskCode'], row) for row in records[:2]]
        for working in (False, True):
            for operation in ('shift', 'align-start', 'align-end', 'extend', 'shorten', 'sequence'):
                for amount in (-2, 0, 3):
                    self.assertEqual(native.batch_schedule_edits(peers, operation, amount, working), namespace['batch_schedule_edits'](peers, operation, amount, working))
            self.assertEqual(native.schedule_dates(records[0], '2030-01-01', 4, 3, working), namespace['schedule_dates'](records[0], '2030-01-01', 4, 3, working))
            self.assertEqual(native.shifted_selection_edits(records[0], '2030-01-09', peers, working), namespace['shifted_selection_edits'](records[0], '2030-01-09', peers, working))
        self.assertEqual(native.schedule_dates(records[0], '2030-01-01', 4, 3, True), dict(start='2030-01-07 09:13:00', end='2030-01-09 17:20:00'))
        grid = native.calendar_cells(2030, 1, records)
        self.assertEqual(len(grid), 42)
        self.assertEqual(date.fromisoformat(grid[0]['date']).weekday(), 0)
        self.assertIn('Assignee has overlapping tasks', native.gantt_layout(records)['records'][0]['ganttWarning'])

    def test_bounded_presentation_input(self):
        for value in ([dict(taskCode='A', progress=float('nan'))], [dict(taskCode='A', start='0001-01-01')],
                      [dict(taskCode='A'), dict(taskCode='A')], [dict(taskCode=str(i)) for i in range(501)],
                      [dict(taskCode='A', start='1900-01-01', end='2100-01-01')]):
            with self.assertRaises(ValueError):
                native.checked_records(value)
        self.assertEqual(native.checked_records([dict(taskCode='A', start='')])[0]['dueState'], 'unscheduled')

    def test_draft_keeps_original_gantt_section(self):
        record = dict(taskCode='A', start='2030-01-04', end='2030-01-08', _ganttSectionScheduled=False)
        checked = native.checked_records([record])
        projected = native.gantt_layout(checked)['records'][0]
        self.assertTrue(projected['ganttScheduled'])
        self.assertEqual(projected['ganttSection'], 'unscheduled')
        with self.assertRaises(ValueError):
            native.checked_records([{**record, '_ganttSectionScheduled': 'false'}])


if __name__ == '__main__':
    unittest.main()
