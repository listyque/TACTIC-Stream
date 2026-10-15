"""Real TACTIC Search/Select/SqliteImpl SQL, executed on temporary SQLite.

Only schema metadata is supplied by this test. It does not initialize a TACTIC
installation, its ORM persistence, authentication or workflow database.
"""
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from pyasm.search import Search,Select
from pyasm.search.database_impl import DatabaseImpl,SqliteImpl,PostgresImpl
from tactic.core.query_model import apply_tree,apply_saved,encode_saved,merge_saved,normalize_tree
from tactic.ui_api.contracts import coerce_value,ApiError
from test_query_04 import leaf,group
FIELDS=[{'name':n,'label':n,'kind':k,'storage':True} for n,k in [('name','text'),('age','integer'),('flag','boolean')]]
TYPES={'name':'varchar','age':'integer','flag':'boolean'}

class BuilderSearch(Search):
 def __init__(self,impl=None,fields=FIELDS):
  self.database_impl=impl or SqliteImpl()
  types={f['name']:{'integer':'integer','number':'float','boolean':'boolean'}.get(f['kind'],'varchar') for f in fields}
  self.database_impl.get_column_types=lambda *a:types
  with patch.object(DatabaseImpl,'get',return_value=self.database_impl):self.select=Select()
  self.select.tables=['records'];self.select.db_resource=object()
 def get_base_search_type(self):return 'test/item'
 def get_full_search_type(self):return 'test/item?project=test'
 def get_search_type_obj(self):return object()
 def sql(self):
  # The WHERE clause is formed by the real Select's postfix Boolean processor.
  statement=self.select.get_statement()
  return statement.partition(' WHERE ')[2] or '1'

class SqlBuilderTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:');self.db.execute('create table records (name text,age integer,flag boolean)')
  self.names=[None,'','Alpha','Beta','a.b','axb','100%done','100Xdone','under_score','underXscore',"O'Reilly",r'c:\\path','a!b']
  self.db.executemany('insert into records values (?,?,?)',[(n,i,i%2==1) for i,n in enumerate(self.names)])
  self.patches=[patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in TYPES),patch('pyasm.search.SearchType.get_tactic_type',side_effect=lambda st,n:TYPES.get(n))]
  for p in self.patches:p.start()
 def tearDown(self):
  self.db.close()
  for p in self.patches:p.stop()
 def query(self,tree=None,saved=None):
  s=BuilderSearch()
  if saved is not None:apply_saved(s,saved,login='test',project='test')
  if tree is not None:apply_tree(s,normalize_tree(tree,FIELDS,coerce_value),FIELDS)
  return [r[0] for r in self.db.execute('select rowid from records where '+s.sql())]
 def test_null(self):self.assertEqual(self.query(leaf('name','null')),[1])
 def test_not_null_actual_select_bug_avoided(self):self.assertEqual(self.query(leaf('name','not_null')),list(range(2,14)))
 def test_empty(self):self.assertEqual(self.query(leaf('name','empty')),[1,2])
 def test_not_empty(self):self.assertEqual(self.query(leaf('name','not_empty')),list(range(3,14)))
 def test_numeric_empty(self):self.assertEqual(self.query(leaf('age','empty')),[])
 def test_numeric_not_empty(self):self.assertEqual(self.query(leaf('age','not_empty')),list(range(1,14)))
 def test_bool_false(self):self.assertEqual(self.query(leaf('flag','eq',False)),list(range(1,14,2)))
 def test_bool_true(self):self.assertEqual(self.query(leaf('flag','eq',True)),list(range(2,14,2)))
 def test_zero(self):self.assertEqual(self.query(leaf('age','eq',0)),[1])
 def test_ne_includes_null(self):self.assertEqual(self.query(leaf('name','ne','Alpha')),[x for x in range(1,14) if x!=3])
 def test_literal_period_sqlite_not_regex(self):self.assertEqual(self.query(leaf('name','contains','a.b')),[5])
 def test_literal_percent(self):self.assertEqual(self.query(leaf('name','contains','%')),[7])
 def test_literal_underscore(self):self.assertEqual(self.query(leaf('name','contains','_')),[9])
 def test_literal_apostrophe(self):self.assertEqual(self.query(leaf('name','contains',"O'Reilly")),[11])
 def test_literal_escape_character(self):self.assertEqual(self.query(leaf('name','contains','!')),[13])
 def test_literal_backslash(self):self.assertEqual(self.query(leaf('name','contains',r'c:\\')),[12])
 def test_starts_percent(self):self.assertEqual(self.query(leaf('name','starts','100%')),[7])
 def test_ends_underscore(self):self.assertEqual(self.query(leaf('name','ends','_score')),[9])
 def test_negative_literal_contains_null(self):self.assertEqual(self.query(leaf('name','not_contains','%')),[i for i in range(1,14) if i!=7])
 def test_boolean_group_real_postfix_stack(self):self.assertEqual(self.query(group('and',group('or',leaf('name','null'),leaf('name','contains','a.b')),leaf('age','lt',4))),[1])
 def test_bool_in(self):self.assertEqual(self.query(leaf('flag','in',[False])),list(range(1,14,2)))
 def test_bool_not_in(self):self.assertEqual(self.query(leaf('flag','not_in',[False])),list(range(2,14,2)))
 def test_empty_string_in_not_null(self):self.assertEqual(self.query(leaf('name','in',[''])),[2])
 def test_saved_boolean_in_sqlite(self):
  tree=group('and',leaf('flag','in',[False]));self.assertEqual(self.query(tree),self.query(saved=encode_saved(tree,FIELDS,'Sqlite')))
 def test_literal_NULL_string_not_keyword(self):
  self.db.execute("insert into records values ('NULL',14,0)");self.assertEqual(self.query(leaf('name','eq','NULL')),[14])
 def test_literal_NULL_in_string_list(self):
  self.db.execute("insert into records values ('NULL',14,0)");self.assertEqual(self.query(leaf('name','in',['NULL'])),[14])
 def test_null_literal_not_saved_as_old_keyword(self):
  with self.assertRaises(ValueError):encode_saved(group('and',leaf('name','eq','NULL')),FIELDS,'Sqlite')
 def test_nul_byte_rejected(self):
  with self.assertRaises((ValueError,ApiError)):self.query(leaf('name','eq','a\x00b'))
 def test_in(self):self.assertEqual(self.query(leaf('age','in',[0,4])),[1,5])
 def test_not_in(self):self.assertEqual(self.query(leaf('age','not_in',[0,4])),[i for i in range(1,14) if i not in (1,5)])
 def test_legacy_sqlite_contains_retains_original_like(self):self.assertEqual(self.query(saved=[{'main_body_column':'name','main_body_relation':'contains','main_body_value':'a.b'}]),[5])
 def test_saved_bool_and_literal_roundtrip(self):
  tree=group('and',leaf('name','contains','a.b'),leaf('flag','eq',False))
  self.assertEqual(self.query(tree),self.query(saved=encode_saved(tree,FIELDS,'Sqlite')))
 def test_saved_wildcard_literal_rejected_not_changed(self):
  for op in ('contains','not_contains','starts','ends'):
   with self.subTest(op=op):
    with self.assertRaises(ValueError):encode_saved(group('and',leaf('name',op,'_%')),FIELDS,'Sqlite')
 def test_legacy_negative_empty(self):self.assertEqual(self.query(saved=[{'main_body_column':'name','main_body_relation':'is not empty'}]),list(range(3,14)))
 def test_legacy_merge_bool_truth_table(self):
  base=[{'main_body_column':'age','main_body_relation':'is greater than','main_body_value':'2'}]
  tree=group('and',group('or',leaf('age','eq',4),leaf('age','eq',5)),leaf('flag','eq',False))
  self.assertEqual(self.query(tree,saved=base),self.query(saved=merge_saved(base,tree,FIELDS,'Sqlite')))
 def test_saved_apostrophe_no_sql_injection(self):
  tree=group('and',leaf('name','contains',"O'Reilly"));self.assertEqual(self.query(saved=encode_saved(tree,FIELDS,'Sqlite')),[11])
 def test_sql_injection_value_is_literal(self):self.assertEqual(self.query(leaf('name','contains',"x' OR 1=1 --")),[])
 def test_pg_regex_compiles_with_real_impl(self):
  s=BuilderSearch(PostgresImpl());apply_tree(s,leaf('name','contains','a.b'),FIELDS)
  self.assertIn("~* 'a\\.b'",s.sql());self.assertNotIn('LIKE',s.sql())
 def test_pg_like_uses_explicit_safe_escape(self):
  s=BuilderSearch(PostgresImpl());apply_tree(s,leaf('name','starts','100%'),FIELDS)
  self.assertIn("LIKE '100!%%' ESCAPE '!'",s.sql())
 def test_pg_null_uses_explicit_not_null(self):
  s=BuilderSearch(PostgresImpl());apply_tree(s,leaf('name','not_null'),FIELDS)
  self.assertIn('IS NOT NULL',s.sql())
 def test_pg_legacy_regex_not_changed(self):
  s=BuilderSearch(PostgresImpl());apply_saved(s,[{'main_body_column':'name','main_body_relation':'contains','main_body_value':'a.b'}])
  self.assertIn("~* 'a.b'",s.sql())

if __name__=='__main__':unittest.main()
