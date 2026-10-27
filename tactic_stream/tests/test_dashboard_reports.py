"""Real native aggregates and page parameter scope on disposable databases."""
import copy
import unittest
from uuid import uuid4

from test_foundation import Foundation

COMMAND = 'tactic.ui.panel.dashboard_cmd.DashboardCmd'


class DashboardReports(unittest.TestCase):
    call = Foundation.call

    def setUp(self):
        Foundation.setUp(self)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO search_object(code,search_type,namespace,database,table_name,class_name) "
                       "VALUES ('contract/report','contract/report','contract','{project}','report_entry','pyasm.search.SObject')")
        with self.store.connection('one', write=True) as db:
            db.execute('CREATE TABLE report_entry(id INTEGER PRIMARY KEY,code varchar(256),department text,amount numeric,created timestamp,active boolean,s_status varchar(256))')
            db.executemany('INSERT INTO report_entry VALUES(?,?,?,?,?,?,?)', [
                (1,'A','CG',10,'2026-01-31T23:30:00-02:00',True,None),
                (2,'B','CG',20,'2026-02-05 03:00:00.000 +0300',True,None),
                (3,'C','FX',-5,'2026-02-06T00:00:00Z',False,None),
                (4,'D',None,None,'2026-01-02',True,None),
                (5,'E','CG',100,'2026-02-06',True,'retired'),
            ])

    def command(self, action, **values):
        return self.call('execute_cmd', COMMAND, dict(action=action,project_code='one',**values))['info']

    def document(self):
        return dict(name='annual_report',title='Annual report',filters=[dict(
            name='department',title='Department',search_type='contract/report',column='department',
            relation='=',value='CG',enabled=False)],blocks=[dict(
                kind='summary',search_type='contract/report',group_by=[dict(column='department',title='Department')],
                aggregates=[dict(name=name,title=name,function=name,column='' if name=='count' else 'amount')
                            for name in ('count','sum','avg','min','max')])])

    def preview(self, document, **values):
        return self.command('preview',document=document,expected_revision=self.command('read')['revision'],**values)['model']

    def test_all_aggregates_nulls_retired_rows_and_limit_after_grouping(self):
        document=self.document()
        report=self.preview(document)['layoutNodes'][0]['report']
        rows={row['group_0']:row for row in report['rows']}
        self.assertEqual(report['columns'][0]['title'],'Department')
        self.assertEqual(rows['CG'],dict(group_0='CG',count=2,sum=30,avg=15,min=10,max=20))
        self.assertEqual(rows['FX']['sum'],-5)
        self.assertIsNone(rows[None]['sum'])
        document['blocks'][0].update(group_order='value_desc',group_limit=1)
        report=self.preview(document)['layoutNodes'][0]['report']
        self.assertTrue(report['truncated'])
        self.assertEqual(report['rows'][0]['count'],2)

    def test_common_values_maps_and_runtime_reset_are_not_saved(self):
        document=self.document()
        document['blocks'] += [dict(kind='metric',search_type='contract/report'),
            dict(kind='metric',search_type='contract/entity',page_filters={'department':'code'})]
        model=self.preview(document,filter_values={'department':dict(enabled=True,value='CG')})
        self.assertEqual(len(model['layoutNodes'][0]['report']['rows']),1)
        self.assertEqual(model['layoutNodes'][1]['value'],2)
        self.assertEqual(model['layoutNodes'][2]['value'],0)
        document['blocks'][1]['page_filters']={}
        self.assertEqual(self.preview(document,filter_values={'department':dict(enabled=True,value='CG')})['layoutNodes'][1]['value'],4)
        self.assertEqual(self.preview(document,filter_values={})['layoutNodes'][1]['value'],4)
        revision=self.command('read')['revision'];operation=str(uuid4())
        result=self.command('apply',document=document,expected_revision=revision,operation_id=operation)
        self.assertEqual(self.command('apply',document=document,expected_revision=revision,operation_id=operation),result)
        self.assertFalse(self.command('read',name=document['name'])['document']['filters'][0]['enabled'])

    def test_utc_periods_empty_sets_and_scalar_metric(self):
        document=self.document();block=document['blocks'][0]
        block['group_by']=[dict(column='created',period='month')]
        rows={row['group_0']:row for row in self.preview(document)['layoutNodes'][0]['report']['rows']}
        self.assertEqual(rows['2026-02']['count'],3)
        self.assertEqual(rows['2026-01']['count'],1)
        block.update(kind='metric',group_by=[],aggregates=[dict(name='total',title='Total',function='sum',column='amount')])
        self.assertEqual(self.preview(document)['layoutNodes'][0]['value'],25)
        block['filters']=[dict(column='code',value='missing')]
        self.assertIsNone(self.preview(document)['layoutNodes'][0]['value'])

    def test_invalid_sources_columns_functions_and_runtime_overrides(self):
        baseline=self.document()
        for edits in [dict(group_by=[dict(column='amount',period='month')]),
                      dict(aggregates=[dict(name='group_0',title='Conflicting name',function='count')]),
                      dict(aggregates=[dict(name='bad',title='Bad',function='sum',column='department')]),
                      dict(group_by=[dict(column='code); DROP TABLE report_entry;--')]),
                      dict(page_filters={'unknown':'code'}),dict(group_limit=101),dict(search_type='contract/report?project=two')]:
            document=copy.deepcopy(baseline);document['blocks'][0].update(edits)
            with self.subTest(edits=edits),self.assertRaises(Exception):self.preview(document)
        for overrides in [{'missing':dict(enabled=True,value='CG')},{'department':dict(enabled=True,value='@SOBJECT(sthpw/login)')},
                          {'department':dict(enabled=True,value='CG',column='code')}]:
            with self.subTest(overrides=overrides),self.assertRaises(Exception):self.preview(baseline,filter_values=overrides)
