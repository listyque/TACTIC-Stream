"""Read-only, configured dashboard value hints on disposable native data."""
import copy
import unittest
from uuid import uuid4
from unittest.mock import patch
from tests import test_dashboard_reports as fixture


class PageFilterSearch(unittest.TestCase):
    setUp = fixture.DashboardReports.setUp
    call = fixture.DashboardReports.call
    command = fixture.DashboardReports.command
    document = fixture.DashboardReports.document

    def save(self, document):
        self.command('apply', document=document, expected_revision=self.command('read')['revision'], operation_id=str(uuid4()))

    def suggest(self, field='', text='', **values):
        return self.call('execute_cmd', 'tactic.ui.table.CustomLayoutReadCmd', dict(
            view='dashboard.annual_report', filter_query={'field': field, 'text': text}, **values))['info']['filterSuggestions']

    def test_actual_command_matches_values_and_keeps_source_scope(self):
        document = self.document()
        document['blocks'][0]['filters'] = [dict(column='amount', relation='>=', value=0)]
        document['blocks'].append(copy.deepcopy(document['blocks'][0]))
        self.save(document)
        from pyasm.search import Search
        original = Search.get_aggregates
        with patch.object(Search, 'get_aggregates', autospec=True, side_effect=original) as query:
            self.assertEqual(self.suggest(text='cg'), [{'name': 'department', 'value': 'CG'}])
            self.assertEqual(query.call_count, 1, 'Duplicate widgets share their suggestion query')
        self.assertEqual(self.suggest(text='FX'), [], 'A source constraint also constrains suggestions')
        self.assertEqual(self.suggest('department', '', filter_values={'department':dict(enabled=True,value='no-match')}),
                         [{'name':'department','value':'CG'}], 'Changing a condition omits only its current value')
        self.assertEqual(self.command('read', name=document['name'])['document']['filters'][0]['enabled'], False)

    def test_unknown_filters_and_invalid_queries_fail_before_querying(self):
        self.save(self.document())
        for query in ({'field':'password','text':''}, {'field':'department','text':'x'*257}, {'field':[],'text':''}, {'field':'department','text':'','column':'password'}):
            with self.subTest(query=query), self.assertRaises(Exception):
                self.call('execute_cmd', 'tactic.ui.table.CustomLayoutReadCmd', dict(view='dashboard.annual_report', filter_query=query))

    def test_null_values_are_distinct_and_retired_rows_stay_hidden(self):
        self.save(self.document())
        self.assertEqual(self.suggest('department'), [{'name':'department','value':None},
            {'name':'department','value':'CG'},{'name':'department','value':'FX'}])

    def test_scalar_hints_preserve_numeric_boolean_and_date_types(self):
        document=self.document()
        document['filters'] += [dict(name=name,title=name,search_type='contract/report',column=name,relation='=',value=value,enabled=False)
            for name,value in [('amount',0),('active',False),('created','2026-01-02')]]
        self.save(document)
        self.assertEqual(self.suggest('amount','10'),[{'name':'amount','value':10}])
        self.assertEqual(self.suggest('active','false'),[{'name':'active','value':False}])
        rows=self.suggest('created','2026-02-05')
        self.assertEqual(rows,[{'name':'created','value':'2026-02-05T03:00:00+03:00'}])

    def test_native_reader_can_search_but_source_denial_is_enforced(self):
        from pyasm.security.authenticator import hash_password
        from pyasm.common.errors import SecurityException
        self.save(self.document())
        self.call('insert','sthpw/login',dict(login='hint_reader',password=hash_password('hint-test-password')))
        group=self.call('insert','sthpw/login_group',dict(login_group='hint_readers',access_level='none',
            access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="*" access="view"/></rules>'))
        self.call('insert','sthpw/login_in_group',dict(login='hint_reader',login_group='hint_readers'))
        token=self.api.get_ticket('hint_reader','hint-test-password')
        def read():
            return self.api.dispatch('execute_cmd',({'ticket':token,'project':'one'},'tactic.ui.table.CustomLayoutReadCmd',
                dict(view='dashboard.annual_report',filter_query={'field':'department','text':'CG'})))['info']['filterSuggestions']
        self.assertEqual(read(),[{'name':'department','value':'CG'}])
        self.call('update',group['__search_key__'],dict(access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="*" access="view"/><rule group="search_type" code="contract/report" access="deny"/></rules>'))
        with self.assertRaises(SecurityException): read()
