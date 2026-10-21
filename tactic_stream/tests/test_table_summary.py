"""Original object/project summary counts, hours and expanded query scopes."""
import unittest
import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Task
from pyasm.search import Search, SearchType
from tactic.ui.table.sobject_summary_wdg import read_summary_cell
from tactic.ui.table.nested_scope import read_nested_scope

class TableSummary(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def seed(self):
        def create():
            parents=[Search.get_by_code('contract/entity',code) for code in ('A','B')]
            for parent, amount in zip(parents,(2.5,10)):
                Task.create(parent,'model',triggers=False)
                for stype in ('sthpw/note','sthpw/work_hour'):
                    obj=SearchType.create(stype)
                    obj.set_parent(parent)
                    obj.set_value('project_code','one')
                    if stype=='sthpw/work_hour':
                        obj.set_value('straight_time',amount)
                        obj.set_value('over_time',100)
                    obj.commit(triggers=False)
            return parents
        return write(create)

    def test_object_summary_and_each_nested_action_stay_with_the_parent(self):
        parents=self.seed()
        result=read_summary_cell(parents[0].get_search_key())
        values={item['label']:item['value'] for item in result['summary']}
        self.assertEqual(values,{'Tasks':'1','Checkins':'0','Notes':'1','Work Hours':'2.5'})
        for entry in result['summary'][:2]:
            scope=entry['nestedTable']
            result=read_nested_scope(scope['parentKey'],scope['searchType'])
            self.assertTrue(all(row['search_code']=='A' for row in result['records']))

    def test_project_summary_uses_all_its_parents_and_sql_hour_aggregation(self):
        self.seed()
        parent=Search.get_by_code('sthpw/project','one')
        result=read_summary_cell(parent.get_search_key())
        values={item['label']:item['value'] for item in result['summary']}
        self.assertEqual(values,{'Tasks':'2','Checkins':'0','Notes':'2','Work Hours':'12.5'})
        scope=result['summary'][0]['nestedTable']
        records=read_nested_scope(scope['parentKey'],scope['searchType'])['records']
        self.assertEqual({row['search_code'] for row in records},{'A','B'})
        self.assertTrue(all(row['project_code']=='one' for row in records))

    def test_empty_summary_is_zero_and_private_scopes_are_rejected(self):
        parent=Search.get_by_code('contract/entity','A')
        self.assertEqual([item['value'] for item in read_summary_cell(parent.get_search_key())['summary']],['0']*4)
        with self.assertRaisesRegex(ValueError,'private messages'):
            read_nested_scope(parent.get_search_key(),'sthpw/message')

    def test_project_summary_excludes_a_second_projects_identically_named_parent(self):
        from pyasm.biz import Project
        self.seed()
        def create():
            Project.set_project('two')
            try:
                Task.create(Search.get_by_code('contract/entity','A'),'model',triggers=False)
            finally:
                Project.set_project('one')
        write(create)
        one=read_summary_cell(Search.get_by_code('sthpw/project','one').get_search_key())
        two=read_summary_cell(Search.get_by_code('sthpw/project','two').get_search_key())
        self.assertEqual(one['summary'][0]['value'],'2')
        self.assertEqual(two['summary'][0]['value'],'1')
        scope=two['summary'][0]['nestedTable']
        self.assertEqual(scope['projectCode'],'two')
        rows=read_nested_scope(scope['parentKey'],scope['searchType'])['records']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['project_code'],'two')
