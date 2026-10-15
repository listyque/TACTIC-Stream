"""Database-clock filters compared with the source, including independent bug fixes."""
import ast
import importlib.util
import unittest
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.search import Search, Select
from pyasm.search.search import RequestContext, request_context
from pyasm.search.database_impl import SqliteImpl, PostgresImpl
from pyasm.security.authenticator import hash_password
from tools.snapshot_probe import run_snapshot_case


class DynamicTimestampFilters(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            db.execute("INSERT INTO search_object(code,search_type,namespace,database,table_name,class_name) VALUES ('contract/clock','contract/clock','contract','{project}','clock_entity','pyasm.search.SObject')")
        for project in ('one','two'):
            with cls.store.connection(project,write=True) as db:
                db.execute('CREATE TABLE clock_entity(id integer PRIMARY KEY,code varchar(256),timestamp timestamp,other_time datetime,third_time datetime2,due_date timestamp,s_status varchar(256))')
                rows=[('PAST','2000-01-01 00:00:00',None),
                      ('BEFORE','2026-10-09 11:59:59.999999',None),
                      ('SAME','2026-10-09 12:00:00',None),
                      ('OFFSET','2026-10-09 15:00:00+03:00',None),
                      ('PRECISE','2026-10-09 12:00:00.000001',None),
                      ('FUTURE','2999-01-01 00:00:00',None),
                      ('EMPTY',None,None),('RETIRED','2000-01-01 00:00:00','retired')]
                for index,(code,value,status) in enumerate(rows,1):
                    db.execute('INSERT INTO clock_entity VALUES (?,?,?,?,?,?,?)',(index,code,value,value,value,value[:10] if value else None,status))
        source_greater=['FUTURE','OFFSET','PRECISE']
        cls.cases=[dict(method='expression_contract',timestamp_filters=True,project='one',
                        name=name,value=value,expected=expected,**options)
                   for name,value,expected,options in [
                       ('now','NOW',['BEFORE','PAST'],{}),
                       ('current','CURRENT_TIMESTAMP',['BEFORE','PAST'],{}),
                       ('now_equal','NOW',['OFFSET','SAME'],{'op':'=','source_value':['SAME']}),
                       ('now_not_equal','NOW',['BEFORE','FUTURE','PAST','PRECISE'],{'op':'!=','source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE']}),
                       ('current_greater','CURRENT_TIMESTAMP',['FUTURE','PRECISE'],{'op':'>','source_value':source_greater}),
                       ('current_gte','CURRENT_TIMESTAMP',['FUTURE','OFFSET','PRECISE','SAME'],{'op':'>='}),
                       ('current_lte','CURRENT_TIMESTAMP',['BEFORE','OFFSET','PAST','SAME'],{'op':'<=','source_value':['BEFORE','PAST','SAME']}),
                       ('lower_now','now',['BEFORE','PAST'],{'source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME']}),
                       ('mixed_now','nOw',['BEFORE','PAST'],{'source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME']}),
                       ('lower_current','current_timestamp',['BEFORE','PAST'],{'source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME']}),
                       ('qualified','NOW',['BEFORE','PAST'],{'column':'clock_entity.timestamp','source_value':{'error':'SqlException'}}),
                       ('quoted_now','NOW',['BEFORE','PAST'],{'quoted':True}),
                       ('quoted_current_literal','CURRENT_TIMESTAMP',['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME'],{'quoted':True}),
                       ('unquoted_current','CURRENT_TIMESTAMP',['BEFORE','PAST'],{'quoted':False}),
                       ('datetime_now',"DATETIME('now')",['BEFORE','PAST'],{}),
                       ('datetime_no_args','DATETIME()',['BEFORE','PAST'],{}),
                       ('datetime_past',"DATETIME('2000-01-01 00:00:00')",['PAST'],{'op':'='}),
                       ('datetime_offset_literal',"DATETIME('2026-10-09 15:00:00+03:00')",['OFFSET','SAME'],{'op':'=','source_value':['SAME']}),
                       ('datetime_milliseconds',"DATETIME('2026-10-09 12:00:00.000001')",['OFFSET','SAME'],{'op':'=','source_value':['SAME']}),
                       ('datetime_modifiers',"DATETIME('now','start of day','+12 hours')",['OFFSET','SAME'],{'op':'=','source_value':['SAME']}),
                       ('datetime_epoch',"DATETIME(0,'unixepoch')",['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME'],{'op':'>'}),
                       ('datetime_scientific',"DATETIME(1.e0,'unixepoch')",['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME'],{'op':'>'}),
                       ('datetime_null','DATETIME(NULL)',[],{}),
                       ('datetime_unknown',"DATETIME('now','not a modifier')",[],{}),
                       ('datetime_quoted_text',"DATETIME('now','O''Reilly')",[],{}),
                       ('day_column','CURRENT_TIMESTAMP',['BEFORE','OFFSET','PAST','PRECISE','SAME'],{'column':'due_date'}),
                       ('api_current_literal','CURRENT_TIMESTAMP',['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME'],{'filter_document':True}),
                       ('api_now','NOW',['BEFORE','PAST'],{'filter_document':True}),
                       ('api_day_before','NOW',['BEFORE','OFFSET','PAST','SAME'],{'filter_document':True,'op':'is before','source_value':['BEFORE','PAST','SAME']}),
                       ('range_requires_dates','NOW',{'error':'ParserError'},{'date_range':True}),
                       ('generated_day','unused',['BEFORE','OFFSET','PAST','PRECISE','SAME'],{'generated':{'offset':1,'type':'day'}}),
                       ('generated_minus_day','unused',['PAST'],{'generated':{'offset':1,'type':'day','op':'-'}}),
                       ('generated_week','unused',['BEFORE','OFFSET','PAST','PRECISE','SAME'],{'generated':{'offset':1,'type':'week'}}),
                       ('generated_fraction','unused',['BEFORE','OFFSET','PAST','PRECISE','SAME'],{'generated':{'offset':0.5,'type':'day'}}),
                       ('datetime_type','NOW',['BEFORE','PAST'],{'column':'other_time','source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME']}),
                       ('datetime2_type','NOW',['BEFORE','PAST'],{'column':'third_time','source_value':['BEFORE','FUTURE','OFFSET','PAST','PRECISE','SAME']}),
                       ('sql_injection',"DATETIME('now') OR 1=1 --",{'error':'ValueError'},{'source_value':['BEFORE','EMPTY','FUTURE','OFFSET','PAST','PRECISE','RETIRED','SAME']}),
                       ('current_injection','CURRENT_TIMESTAMP OR 1=1 --',{'error':'ValueError'},{'source_value':['BEFORE','EMPTY','FUTURE','OFFSET','PAST','PRECISE','RETIRED','SAME']}),
                       ('sqlite_processor','NOW',{'value':'CURRENT_TIMESTAMP','quoted':False},{'processor':'sqlite'}),
                       ('sqlite_null',None,{'value':None,'quoted':False},{'processor':'sqlite','source_value':{'error':'AttributeError'}}),
                       ('sqlite_bad_type',3,{'error':'TypeError'},{'processor':'sqlite','source_value':{'error':'AttributeError'}}),
                       ('postgres_processor','NOW',{'value':'now()','quoted':False},{'processor':'postgres','source_value':{'value':'now()','quoted':True}}),
                   ]]

    def new_result(self,case):
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self,case,result,original):
        self.assertEqual(result,case['expected'])
        self.assertEqual(original,case.get('source_value',case['expected']))

    def test_shared_validator_rejects_payloads_without_sql_or_data_changes(self):
        bad=("DATETIME('now') OR 1=1 --","CURRENT_TIMESTAMP; DELETE FROM clock_entity",
             "DATETIME((SELECT password FROM login))","DATETIME('now');DROP TABLE clock_entity")
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.ticket)
            sql=Search('contract/clock').get_sql()
            for value in bad:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        Search('contract/clock').add_filter('timestamp',value)
                    with self.assertRaises(ValueError):
                        SqliteImpl().process_value('timestamp',value,'timestamp')
                    select=Select()
                    select.set_database(sql)
                    select.add_table('clock_entity')
                    with self.assertRaises(ValueError):
                        select.add_filter('timestamp',value)
            self.assertEqual(Search('contract/clock').get_count(),7)
            for value in ('now() OR 1=1',"now() + '1 day'::interval;DELETE FROM note",'CURRENT_TIMESTAMP(7)',"DATETIME('now')"):
                with self.subTest(value=value),self.assertRaises(ValueError):
                    PostgresImpl().process_value('timestamp',value,'timestamp')
            impl=PostgresImpl()
            for unit in ('day','week','millisecond','centuries'):
                value=impl.get_timestamp_now(offset=1,type=unit)
                self.assertEqual(impl.get_timestamp_filter(value),value)

    def test_authenticated_reader_database_clock(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('clock_reader','clock_reader',?)",(hash_password('private-clock-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('clock_readers','clock_readers',?)",('<rules><rule group="search_type" default="allow"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('clock_reader_group','clock_reader','clock_readers')")
        ticket={'ticket':self.api.get_ticket('clock_reader','private-clock-reader'),'project':'one'}
        try:
            filters=[['code','in','PAST|FUTURE'],['timestamp','<','NOW']]
            result=ast.literal_eval(self.api.dispatch('query',(ticket,'contract/clock'),{'filters':filters}))
            self.assertEqual([row['code'] for row in result],['PAST'])
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='clock_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='clock_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='clock_readers'")
                db.execute("DELETE FROM login WHERE code='clock_reader'")


class DynamicTimestampTransport(unittest.TestCase):
    def test_original_sdk_database_clock_and_failed_filter_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            with test_transport.Transport.store.connection('one',write=True) as db:
                db.execute('ALTER TABLE entity ADD COLUMN timestamp timestamp')
            spec=importlib.util.spec_from_file_location('tactic_client_lib.source_clock_client',read_tests.LEGACY/'src/client/tactic_client_lib/tactic_server_stub.py')
            original=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client=original.TacticServerStub(setup=False,protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin','private-test-password'))
            with client.server:
                client.update('contract/entity?project=one&code=A',{'timestamp':'2000-01-01 00:00:00'})
                self.assertEqual(client.query('contract/entity',filters=[['code','A'],['timestamp','<','NOW']])[0]['code'],'A')
                body="""from pyasm.search import Search
search=Search('contract/entity')
search.add_filter('code','A')
search.add_filter('timestamp',search.get_database_impl().get_timestamp_now(),op='<')
return search.get_sobject_codes()"""
                self.assertEqual(client.execute_python_script('',{'code':body})['info'],['A'])
                with self.assertRaises(Fault):
                    client.query('contract/entity',filters=[['amount',"@IF(@UPDATE(@SOBJECT(contract/entity['code','A']),amount,99),'0','0')"],['timestamp',"DATETIME('now') OR 1=1 --"]])
                self.assertEqual(client.query('contract/entity',filters=[['code','A']])[0]['amount'],0)
        finally:
            test_transport.Transport.tearDownClass()
