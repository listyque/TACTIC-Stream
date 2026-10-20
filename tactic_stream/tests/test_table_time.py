"""Configured table schedules and hours use real tasks and WorkHour records."""
import datetime
import json
import unittest
import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Task
from pyasm.search import Search, SearchType
from tactic.ui.table.gantt_element_wdg import GanttElementWdg, table_schedule
from tactic.ui.table.work_hours_element_wdg import WorkHoursElementWdg
from pyasm.widget.gantt_wdg import GanttWdg
from pyasm.widget.timecard_wdg import WeekTableElement
from tactic_stream.server.table_cells import describe_cell


class TableTime(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def task(self, code='A', start='2031-04-03', end='2031-04-09'):
        return write(lambda: Task.create(Search.get_by_code('contract/entity',code), 'model',
            start_date=start, end_date=end, assigned='admin', triggers=False))

    def test_direct_bars_share_page_range_and_preserve_readonly_actual_dates(self):
        tasks = [self.task(), self.task('B', '2031-05-02', '2031-05-10')]
        options = dict(options=json.dumps([dict(start_date_col='bid_start_date', end_date_col='bid_end_date',
            color='#4b4', edit='true'), dict(start_date_col='actual_start_date', end_date_col='actual_end_date', edit='false')]))
        cells = table_schedule(tasks, options)
        self.assertEqual({cell['timeline']['start'] for cell in cells.values()}, {'2031-04-01'})
        self.assertEqual({cell['timeline']['end'] for cell in cells.values()}, {'2031-05-31'})
        for cell in cells.values():
            self.assertTrue(cell['timeline']['bars'][0]['editable'])
            self.assertFalse(cell['timeline']['bars'][1]['editable'])
            self.assertIn('contract/entity', cell['targetSearchKey'])

    def test_aggregate_expression_and_invalid_options_are_not_silently_replaced(self):
        task = self.task()
        parent = task.get_parent()
        options = dict(options=json.dumps([dict(start_date_expr='@MIN(sthpw/task.bid_start_date)',
            end_date_expr='@MAX(sthpw/task.bid_end_date)', color='#33F')]))
        cell = table_schedule([parent], options)[parent.get_search_key()]
        self.assertEqual(cell['timeline']['bars'][0]['start'], '2031-04-03')
        for extra in (dict(week_start='8'), dict(bar_height='200'), dict(date_mode='evil'),
                      dict(range_start_date='2032-01-01', range_end_date='2031-01-01')):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                table_schedule([task], dict(options, **extra))

    def test_work_hours_exclude_other_users_and_never_double_count_overtime(self):
        task = self.task()
        monday = datetime.date.today()
        monday -= datetime.timedelta(days=monday.weekday())
        def entries():
            for login, category, regular, overtime in (
                ('admin','regular',2,1), ('admin','overtime',1,0), ('other','regular',10,0)):
                obj=SearchType.create('sthpw/work_hour')
                for name,value in dict(project_code='one', task_code=task.get_code(), login=login,
                    day=str(monday), category=category, straight_time=regular, over_time=overtime).items():
                    obj.set_value(name,value)
                obj.commit()
        write(entries)
        widget=WorkHoursElementWdg(show_overtime='true',unit='minute')
        widget.set_sobjects([task]);widget.preprocess();widget.set_current_index(0)
        cell=widget.get_cell_value()
        self.assertEqual(float(cell['timeDays'][0]['value']), 120)
        self.assertEqual(float(cell['timeDays'][0]['overtime']), 120)
        self.assertEqual(cell['taskKey'],task.get_search_key())
        self.assertEqual(cell['actions'][0]['name'],'work-hours')
        widget.set_option('show_all_users','true');widget.preprocess()
        self.assertEqual(float(widget.get_cell_value()['timeDays'][0]['value']),720)
        self.assertEqual(widget.get_cell_value()['actions'],[])

    def test_all_time_catalogue_classes_are_computed_and_unknown_options_fail(self):
        for name in ('GanttWdg','tactic.ui.table.GanttElementWdg','WeekTableElement',
                     'TimecardInfoTableElement','tactic.ui.table.WorkHoursElementWdg'):
            element=dict(name='time',display=dict(handler=name, options={}),action=dict(handler='',options={}))
            with self.subTest(name=name):
                descriptor=describe_cell(element,{})
                self.assertTrue(descriptor['supported'])
                self.assertEqual(descriptor['kind'],'commands')
                element['display']['options']['unimplemented']='yes'
                self.assertFalse(describe_cell(element,{})['supported'])
