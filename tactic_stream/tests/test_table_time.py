"""Configured table schedules and hours use real tasks and WorkHour records."""
import datetime
import json
from types import SimpleNamespace
import unittest
import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Task
from pyasm.search import Search, SearchType
from tactic.ui.table.gantt_element_wdg import GanttCbk, GanttElementWdg, table_schedule
from tactic.ui.table.work_hours_element_wdg import WorkHoursElementAction, WorkHoursElementWdg
from pyasm.widget.gantt_wdg import GanttWdg
from pyasm.widget.timecard_wdg import TimecardInfoTableElement, WeekTableElement
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
        work_el = dict(name='work_hours', display=dict(handler='tactic.ui.table.WorkHoursElementWdg', options={}),
                       action=dict(handler='WorkHoursElementAction', options={}))
        self.assertTrue(describe_cell(work_el, {})['supported'])
        gantt_el = dict(name='gantt', display=dict(handler='GanttWdg', options=dict(handlers='ResourceUsageGanttWdg', width='550')),
                        action=dict(handler='', options={}))
        self.assertTrue(describe_cell(gantt_el, {})['supported'])
        week_el = dict(name='week', display=dict(handler='WeekTableElement', options=dict(width='550')),
                       action=dict(handler='', options={}))
        self.assertTrue(describe_cell(week_el, {})['supported'])

    def test_gantt_cbk_default_and_cascade_and_resource_usage_handler(self):
        t1 = self.task('A', '2031-04-03', '2031-04-09')
        t2 = write(lambda: Task.create(Search.get_by_code('contract/entity', 'A'), 'rig',
            start_date='2031-04-05', end_date='2031-04-09', assigned='admin', triggers=False))
        parent = t1.get_parent()

        def run_default():
            cbk = GanttCbk()
            cbk.set_option('options', json.dumps([dict(mode='default', prefix='bid')]))
            cbk.set_sobject(t1)
            cbk.value = json.dumps({'bar_0': dict(index=0, search_key=t1.get_search_key(),
                start_date='2031-04-04', end_date='2031-04-10',
                orig_start_date='2031-04-03', orig_end_date='2031-04-09')})
            cbk.execute()
        write(run_default)
        t1_reloaded = Search.get_by_search_key(t1.get_search_key())
        self.assertEqual(str(t1_reloaded.get_value('bid_start_date'))[:10], '2031-04-04')
        self.assertEqual(str(t1_reloaded.get_value('bid_end_date'))[:10], '2031-04-10')

        def run_cascade():
            cbk = GanttCbk()
            cbk.set_option('options', json.dumps([dict(mode='cascade', prefix='bid', sobjects='@SOBJECT(sthpw/task)')]))
            cbk.set_sobject(parent)
            cbk.value = json.dumps({'bar_0': dict(index=0,
                start_date='2031-04-06', end_date='2031-04-12',
                orig_start_date='2031-04-04', orig_end_date='2031-04-10')})
            cbk.execute()
        write(run_cascade)
        self.assertEqual(str(Search.get_by_search_key(t1.get_search_key()).get_value('bid_start_date'))[:10], '2031-04-06')
        self.assertEqual(str(Search.get_by_search_key(t2.get_search_key()).get_value('bid_start_date'))[:10], '2031-04-07')

        admin_user = Search.get_by_code('sthpw/login', 'admin')
        w = GanttWdg(handlers='ResourceUsageGanttWdg', width='500')
        w.set_sobjects([admin_user])
        w.preprocess()
        w.set_current_index(0)
        usage_cell = w.get_cell_value()
        self.assertEqual(usage_cell['login'], 'admin')
        self.assertEqual(usage_cell['widthHint'], 500)
        self.assertTrue(any(bar['color'] == '#d9534f' for bar in usage_cell['timeline']['bars']))

    def test_work_hours_action_and_week_timecard_totals(self):
        task = self.task('A', '2031-04-03', '2031-04-09')
        day_str = '2031-04-07'

        def apply_hours():
            act = WorkHoursElementAction()
            act.set_option('unit', 'hour')
            act.set_option('use_straight_time', 'true')
            act.set_sobject(task)
            act.value = json.dumps({'day_2031_04_07': '4', 'otday_2031_04_07': '1.5'})
            act.execute()
        write(apply_hours)

        w = WorkHoursElementWdg(show_overtime='true', start_date=day_str)
        w.set_sobjects([task])
        w.preprocess()
        w.set_current_index(0)
        cell = w.get_cell_value()
        self.assertEqual(float(cell['timeDays'][0]['value']), 4.0)
        self.assertEqual(float(cell['timeDays'][0]['overtime']), 1.5)
        self.assertEqual(cell['total'], 4.0)
        self.assertEqual(cell['overtimeTotal'], 1.5)
        self.assertEqual(cell['dailyTotals'][day_str], 4.0)

        def delete_hours():
            act = WorkHoursElementAction()
            act.set_option('unit', 'hour')
            act.set_option('use_straight_time', 'true')
            act.set_sobject(task)
            act.value = json.dumps({'day_2031_04_07': '0'})
            act.execute()
        write(delete_hours)
        w.preprocess()
        self.assertEqual(float(w.get_cell_value()['timeDays'][0]['value']), 0.0)

        tc_values = dict(search_type=task.get_search_type(), search_id=task.get_id(), login='admin',
                         year=2031, week=15, mon=3, tue=5)
        tc = SimpleNamespace(get_value=lambda name, **kw: tc_values.get(name, ''))
        week_wdg = WeekTableElement(width='550')
        week_wdg.set_sobjects([tc])
        week_wdg.preprocess()
        week_wdg.set_current_index(0)
        tc_cell = week_wdg.get_cell_value()
        self.assertEqual(tc_cell['widthHint'], 550)
        self.assertEqual(tc_cell['total'], 8.0)
        self.assertEqual(tc_cell['dailyTotals']['mon'], 3.0)
        self.assertEqual(tc_cell['taskKey'], task.get_search_key())
        self.assertEqual(tc_cell['actions'][0]['name'], 'work-hours')

        info_wdg = TimecardInfoTableElement()
        info_wdg.set_sobjects([tc])
        info_wdg.preprocess()
        info_wdg.set_current_index(0)
        info_cell = info_wdg.get_cell_value()
        self.assertEqual(info_cell['targetSearchKey'], task.get_search_key())
