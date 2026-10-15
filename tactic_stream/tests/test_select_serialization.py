"""Original Select JSON contracts, corrected projections and native load boundaries."""
import json
import unittest

import test_search_select as select_tests
from pyasm.common.errors import UnsupportedContract
from pyasm.search import Search, Select
from pyasm.search.search import RequestContext, request_context


def serialization_cases():
    def step(method, *args, target='select', **kwargs):
        return dict(method=method,args=list(args),kwargs=kwargs,target=target)
    def case(name,*steps,**options):
        return dict(name=name,method='expression_contract',select_serialization=True,steps=list(steps),**options)
    return [
        case('plain'),
        case('bound',step('add_filter','code','A',target='search')),
        case('mixed',step('add_filter','amount',0,op='>=',target='search'),step('add_filter','code','A')),
        case('postfix',step('add_op','begin'),step('add_filter','code','A',target='search'),step('add_filter','code','B'),step('add_op','or')),
        case('page',step('set_limit',2),step('set_offset',1)),
        case('quoted',step('add_filter','name',"O'Reilly")),
        case('literal_marker',step('add_where',"'?' = '?'"),step('add_filter','code','A',target='search')),
        case('unicode',step('add_filter','name','Первый')),
        case('null',step('add_filter','name',None)),
        case('empty',step('add_filters','code',[])),
        case('null_scope',step('set_null_filter',target='search')),
        case('column',step('add_column','code'),step('add_filter','code','A'),projection=True),
        case('alias',step('add_column','code',as_column='label'),step('add_filter','code','A'),projection=True),
        case('join',step('add_join','child',column='id',column2='entity_id'),step('add_filter','code','CA',table='child')),
        case('legacy_join',step('add_join','child',column='id',column2='entity_id'),step('add_filter','code','CA',table='child'),omit_join_tables=True),
        case('standalone',step('add_filter','code','A',target='search'),standalone=True),
    ]


class SelectSerialization(select_tests.SearchSelect):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases=serialization_cases()

    def assert_case_result(self,case,native,original):
        name=case['name']
        if name=='plain':
            self.assertEqual(native,dict(values=['A','B',None,'D','E','F','G'],projection=8,secrets=False))
            self.assertEqual(original,dict(values=['A','B','C',None,'D','E','F','G'],projection=8,secrets=False))
        elif name=='page':
            self.assertEqual(native,dict(values=['B',None],projection=8,secrets=False))
            self.assertEqual(original,dict(values=['B','C'],projection=8,secrets=False))
        elif name=='null_scope':
            self.assertEqual(native,dict(values=[],projection=8,secrets=False))
            self.assertEqual(original,dict(values=['A','B','C',None,'D','E','F','G'],projection=8,secrets=False))
        elif name in ('column','alias'):
            self.assertEqual(native,dict(values=['A'],projection=['code' if name=='column' else 'label'],secrets=False))
            self.assertEqual(original,dict(values=['A'],projection=['id','code','name','amount','s_status','active','metadata','timestamp'],secrets=False))
        else:
            self.assertEqual(native,original)

    def test_invalid_load_is_atomic_and_cannot_change_search_authority(self):
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            search=Search('contract/entity')
            search.add_filter('code','A')
            select=search.get_select()
            state=json.loads(select.dumps())
            before=(select.get_statement(),list(search.parameters),select.wheres,select.columns)
            invalid=[{'tables':['login']},{'database':'two'},{'schema':'private'}, {'filters':{'code':['1=1']}},
                     {'set_statement':'SELECT * FROM login'}, {'columns':[None]}, {'columns':['missing'],'column_tables':['entity'],'as_columns':[None]},
                     {'limit':True},{'offset':-1},{'wheres':['id=?']},{'wheres':[False]}, {'distinct':1},
                     {'joins':['INNER JOIN "two"."public"."child" ON 1=1']}, {'joins':['INNER JOIN "private"."child" ON 1=1']},
                     {'joins':['INNER JOIN child ON 1=1']}, {'as_columns':[None]}, {'raw_filters':{}}, {'quoted_mode':'unexpected'}]
            for change in invalid:
                with self.subTest(change=change):
                    payload={**state,**change}
                    with self.assertRaises((ValueError,UnsupportedContract)): select.loads(json.dumps(payload))
                    self.assertEqual((select.get_statement(),search.parameters,select.wheres,select.columns),before)
                    self.assertIs(select.wheres,search.filters)
            select.loads(json.dumps({**state,'sql':'other','db_resource':{'password':'invented'},'_search_owned':None,'null_filter':False,'security_filter':True}))
            self.assertIs(select._search_owned,search)
            self.assertEqual(search.get_sobject_codes(),['A'])
            self.assertEqual(search.parameters,[])

    def test_restore_detaches_state_and_invalidates_cached_objects(self):
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            search=Search('contract/entity')
            search.add_filter('code','B')
            self.assertEqual(search.get_sobjects()[0].get_code(),'B')
            donor=Search('contract/entity')
            donor.add_filter('code','A')
            donor.get_select().add_column('code',as_column='label')
            search.get_select().loads(donor.get_select().dumps())
            self.assertFalse(search.is_search_done)
            self.assertEqual(search.get_sobjects()[0].get_value('label'),'A')
            search.get_select().add_filter('amount',0,op='>=')
            self.assertEqual(donor.parameters,['A'])
            self.assertEqual(search.parameters,['0'])
            self.assertEqual(search.get_select().copy().execute(),[('A',)])

    def test_original_unprojected_payload_can_be_loaded(self):
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            legacy={'tables':['entity'],'columns':[],'column_tables':[], 'wheres':['"entity"."code" = \'A\''],
                    'filters':{},'raw_filters':[],'filter_mode':'AND','group_bys':[],'havings':[],
                    'order_bys':[],'order_by_columns':[],'limit':None,'offset':0,'distinct':False,
                    'distinct_col':None,'joins':[],'schema':'','database':None,'id_col':'id','set_statement':None}
            search=Search('contract/entity')
            search.get_select().loads(json.dumps(legacy))
            self.assertEqual(search.get_sobject_codes(),['A'])

    def test_aggregate_distinct_and_quote_mode_roundtrip(self):
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            grouped=Search('contract/entity')
            grouped.add_filters('code',['A','D','E'])
            select=grouped.get_select()
            select.add_column('amount')
            select.add_column('COUNT(*)',table=None,as_column='total',quoted=False)
            select.add_group_by('amount')
            select.add_order_by('amount')
            select.add_having('COUNT(*) >= 1')
            target=Search('contract/entity').get_select()
            target.loads(select.dumps())
            self.assertEqual(target.execute(),[(0,2),(9,1)])
            self.assertEqual(target.execute_count(),2)
            self.assertEqual(target._search_owned.get_count(),3)
            distinct=Search('contract/entity')
            distinct.add_filters('code',['A','D'])
            distinct.get_select().add_column('amount',distinct=True)
            target.loads(distinct.get_select().dumps())
            self.assertEqual(target.execute(),[(0,)])
            raw=Search('contract/entity')
            raw.add_filter('code','A')
            raw.get_select().set_quoted_mode('none')
            raw.get_select().add_column('amount + 1',as_column='increment')
            target.loads(raw.get_select().dumps())
            self.assertEqual(target.execute(),[(1,)])
            standalone=Select()
            standalone.loads(raw.get_select().dumps())
            self.assertEqual(standalone.quoted_mode,'none')
            self.assertEqual(standalone.execute(raw.get_sql()),[(1,)])


if __name__=='__main__': unittest.main()
