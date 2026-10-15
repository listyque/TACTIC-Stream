"""Queries run through the extracted ORIGINAL filter methods.
SQLite here checks predicate truth tables, not TACTIC's DB integration.
"""
import json
import re
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
R = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(R/'src'),str(R/'src/client')]
from tactic.core.query_model import normalize_tree, apply_tree, apply_saved, encode_saved, combine
from tactic.ui_api.contracts import coerce_value, ApiError

FIELDS = [{'name': n, 'label': n, 'kind': k, 'storage': True} for n,k in [('name','text'),('age','integer'),('flag','boolean'),('created','datetime')]]
def leaf(n,op,value=None): return {'field':n,'op':op,'value':value}
def group(op,*nodes): return {'op':op,'children':list(nodes)}

class PredicateSearch:
    """Search protocol spy. add_op uses the same postfix grouping contract."""
    def __init__(self): self.wheres=[]
    def get_database_impl(self):
        from pyasm.search.database_impl import PostgresImpl
        return PostgresImpl()
    def get_base_search_type(self): return 'test/item'
    def get_full_search_type(self): return 'test/item?project=test'
    def get_search_type_obj(self): return object()
    def get_select(self): return self
    def get_wheres(self): return self.wheres
    def add_op(self,op,idx=None):
        if idx is None:self.wheres.append(op)
        else:self.wheres.insert(idx,op)
    def add_where(self,sql): self.wheres.append(('sql',sql))
    def add_filter(self,column,value,op='=',**kw):
        self.wheres.append(('leaf',column,op,value))
    def add_filters(self,column,values,op='in'): self.wheres.append(('many',column,op,list(values)))
    def add_regex_filter(self,column,value,op='EQI'):self.wheres.append(('regex',column,op,value))
    def sql(self):
        stack=[[]]
        def quote(v):return 'NULL' if v is None else str(int(v)) if isinstance(v,bool) else "'"+str(v).replace("'","''")+"'"
        for item in self.wheres:
            if item=='begin':stack.append([])
            elif item in ('and','or'):
                children=stack.pop();stack[-1].append('('+(' '+item+' ').join(children or ['1'])+')')
            elif item[0]=='sql':stack[-1].append(item[1])
            elif item[0]=='leaf':
                _,name,op,value=item
                if name=='flag' and value is not None:
                    from pyasm.search.database_impl import SqliteImpl
                    value=SqliteImpl().process_value(name,value,'boolean')['value']
                if value is None:op='is not' if op in ('!=','is not') else 'is'
                stack[-1].append('"'+name+'" '+op+' '+quote(value))
            elif item[0]=='many':stack[-1].append('"'+item[1]+'" '+item[2]+' ('+','.join(quote(x) for x in item[3])+')')
            else:
                _,name,op,value=item
                stack[-1].append(('not ' if op=='NEQI' else '')+'regexp('+quote(value)+',"'+name+'")')
        if len(stack)!=1:raise AssertionError(('unclosed',stack,self.wheres))
        return ' and '.join(stack[0]) or '1'

class QueryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.create_function('regexp',2,lambda p,v: None if v is None else bool(re.search(p,str(v),re.I)))
        self.db.execute('create table records(name text,age integer,flag boolean,created text)')
        self.db.executemany('insert into records values (?,?,?,?)',[(None,0,0,'2026-01-01'),('',5,1,'2026-01-02'),('Alpha',10,1,'2026-02-01'),('Beta',20,0,'2026-03-01'),('a.b',30,0,'2026-04-01'),('axb',40,1,'2026-05-01')])
        self.patches=[patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in [f['name'] for f in FIELDS]),patch('pyasm.search.SearchType.get_tactic_type',side_effect=lambda st,n:{'age':'integer','flag':'boolean','created':'timestamp'}.get(n,'varchar'))]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.db.close()
    def normalized(self,tree): return normalize_tree(tree,FIELDS,coerce_value)
    def ids(self,s): return [r[0] for r in self.db.execute('select rowid from records where '+s.sql())]
    def run_tree(self,tree):
        s=PredicateSearch();apply_tree(s,self.normalized(tree),FIELDS);return self.ids(s)
    def run_saved(self,raw):
        s=PredicateSearch();apply_saved(s,raw,login='bob',project='test');return self.ids(s)
    def test_null_vs_empty(self):
        self.assertEqual(self.run_tree(leaf('name','null')),[1]);self.assertEqual(self.run_tree(leaf('name','empty')),[1,2])
    def test_not_equal_includes_null(self):self.assertEqual(self.run_tree(leaf('name','ne','Alpha')),[1,2,4,5,6])
    def test_negative_contains_includes_null(self):self.assertEqual(self.run_tree(leaf('name','not_contains','a')),[1,2])
    def test_literal_contains_not_arbitrary_regex(self):self.assertEqual(self.run_tree(leaf('name','contains','a.b')),[5])
    def test_zero_not_omitted(self):self.assertEqual(self.run_tree(leaf('age','eq',0)),[1])
    def test_false_is_not_lost_or_cast_to_string(self):self.assertEqual(self.run_tree(leaf('flag','eq',False)),[1,4,5])
    def test_in_and_not_in(self):self.assertEqual(self.run_tree(leaf('age','in',[0,20])),[1,4]);self.assertEqual(self.run_tree(leaf('age','not_in',[0,20])),[2,3,5,6])
    def test_nested_boolean(self):self.assertEqual(self.run_tree(group('and',group('or',leaf('age','eq',0),leaf('name','eq','Alpha')),leaf('age','lt',5))),[1])
    def test_unknown_fields(self):
        with self.assertRaises(ValueError):self.normalized(leaf('password','eq','x'))
    def test_too_many(self):
        with self.assertRaises(ValueError):self.normalized(group('and',*[leaf('age','eq',1)]*41))
    def test_empty_nested_group(self):
        with self.assertRaises(ValueError):self.normalized(group('or',group('and')))
    def test_json_injection_ignored_never(self):
        with self.assertRaises(ValueError):self.normalized(dict(leaf('name','eq','x'),sql='1=1'))
    def test_number_injection(self):
        with self.assertRaises(ApiError):self.normalized(leaf('age','gt','0);drop table records;--'))
    def test_saved_defaults_enabled_and_empty(self):
        self.assertEqual(self.run_saved([{'main_body_column':'name','main_body_relation':'is empty'}]),[1,2])
    def test_saved_regex_retains_original(self):
        self.assertEqual(self.run_saved([{'main_body_column':'name','main_body_relation':'contains','main_body_value':'a.b'}]),[5,6])
    def test_saved_injection_blocked(self):
        with self.assertRaises(ValueError):self.run_saved([{'main_body_column':'age','main_body_relation':'is greater than','main_body_value':'0 OR 1=1'}])
    def test_saved_expression_not_executed(self):
        with patch('pyasm.search.Search.eval',side_effect=AssertionError('MUST NOT EXECUTE')):
            with self.assertRaises(ValueError):self.run_saved([{'main_body_column':'name','main_body_relation':'is','main_body_value':'{@SOBJECT(sthpw/login)}'}])
    def test_unknown_saved_prefix_does_not_expand_results(self):
        with self.assertRaises(ValueError):self.run_saved([{'prefix':'expression','expression_value':'whatever'}])
    def test_unknown_saved_relation_rejected(self):
        with self.assertRaises(ValueError):self.run_saved([{'main_body_column':'name','main_body_relation':'custom_sql','main_body_value':'x'}])
    def test_filter_container_restored(self):
        from pyasm.common import Container
        marker=object();Container.put('FilterData',marker)
        self.run_saved([{'main_body_column':'name','main_body_relation':'is','main_body_value':'Alpha'}])
        self.assertIs(Container.get('FilterData'),marker)
    def test_saved_round_trip_simple(self):
        tree=group('and',leaf('name','contains','a.b'),leaf('age','gt',0))
        self.assertEqual(self.run_tree(tree),self.run_saved(encode_saved(self.normalized(tree),FIELDS)))
    def test_saved_round_trip_all_group_operators(self):
        a,b,c,d=leaf('age','eq',0),leaf('age','eq',10),leaf('age','lt',25),leaf('name','ne','Alpha')
        for outer in ('and','or'):
            for op1 in ('and','or'):
                for op2 in ('and','or'):
                    tree=group(outer,group(op1,a,b),group(op2,c,d))
                    with self.subTest(tree=tree):self.assertEqual(self.run_tree(tree),self.run_saved(encode_saved(self.normalized(tree),FIELDS)))
    def test_saved_singleton_groups(self):
        for outer in ('and','or'):
            tree=group(outer,leaf('name','empty'),group('and',leaf('age','gt',5),leaf('name','ne','Alpha')))
            self.assertEqual(self.run_tree(tree),self.run_saved(encode_saved(self.normalized(tree),FIELDS)))
    def test_saved_deeper_groups_explicitly_rejected(self):
        with self.assertRaises(ValueError):encode_saved(group('and',group('or',group('and',leaf('age','eq',0)))),FIELDS)
    def test_text_null_not_silently_encoded_as_empty(self):
        with self.assertRaises(ValueError):encode_saved(group('and',leaf('name','null')),FIELDS)
    def test_combine_no_mutation(self):
        left=group('or',leaf('age','eq',1),leaf('age','eq',2));copy=json.loads(json.dumps(left));self.assertEqual(combine(None,left)['children'],[left]);self.assertEqual(left,copy)

if __name__=='__main__':unittest.main()
