"""In-process parent-code migration contract, mocked object retrieval explicitly."""
import ast
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from tactic.core.search_code_migration import fix_search_code

class SearchCodeTests(unittest.TestCase):
 def bind(self,rows,parent=None):
  query=Mock(get_sobjects=lambda:rows);factory=Mock(return_value=query);factory.get_by_id.return_value=parent
  p=patch('pyasm.search.Search',factory);p.start();self.addCleanup(p.stop);return factory,query
 def obj(self,**values):
  o=Mock();o.get_value.side_effect=lambda n,**kw:values.get(n);o.get_search_key.return_value='sthpw/task?code=TEST';return o
 def test_existing_code_never_overwritten(self):
  row=self.obj(search_code='KEEP',search_type='demo/item',search_id=9);factory,_=self.bind([row])
  result=fix_search_code(['sthpw/task'],strict=True)
  row.set_value.assert_not_called();row.commit.assert_not_called();factory.get_by_id.assert_not_called();self.assertEqual(result['preserved'],1)
 def test_missing_code_written_using_original_commit(self):
  row=self.obj(search_type='demo/item',search_id=9);self.bind([row],self.obj(code='PARENT'))
  self.assertEqual(fix_search_code(['sthpw/task'],strict=True)['updated'],1);row.set_value.assert_called_once_with('search_code','PARENT');row.commit.assert_called_once_with(triggers=False)
 def test_retired_children_are_included(self):
  _,query=self.bind([]);fix_search_code(['sthpw/task']);query.set_show_retired.assert_called_once_with(True)
 def test_zero_parent_id_is_not_missing(self):
  row=self.obj(search_type='demo/item',search_id=0);factory,_=self.bind([row],self.obj(code='ZERO'))
  fix_search_code(['sthpw/task'],strict=True);factory.get_by_id.assert_called_once_with('demo/item',0)
 def test_unresolved_parent_is_actionable_failure(self):
  row=self.obj(search_type='demo/item',search_id=4);self.bind([row])
  with self.assertRaisesRegex(RuntimeError,'unresolved parents'):fix_search_code(['sthpw/task'],strict=True)
  row.commit.assert_not_called()
 def test_parentless_rows_reported_without_inventing_code(self):
  row=self.obj(search_type=None,search_id=-1);self.bind([row])
  r=fix_search_code(['sthpw/task'],strict=True);self.assertEqual(r['without_parent'],1);row.set_value.assert_not_called()
 def test_original_upgrade_step_calls_fix_in_same_process(self):
  source=(ROOT/'src/pyasm/search/upgrade/project/sthpw_upgrade.py').read_text()
  node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='upgrade_v4_0_0_b03_002')
  namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),'original-upgrade-step','exec'),namespace)
  with patch('tactic.core.search_code_migration.fix_search_code') as fix,patch('os.system') as shell:
   namespace[node.name](Mock(is_confirmed=True,quiet=True));fix.assert_called_once_with(verbose=False,strict=True);shell.assert_not_called()
 def test_original_upgrade_step_does_not_ignore_fix_error(self):
  source=(ROOT/'src/pyasm/search/upgrade/project/sthpw_upgrade.py').read_text()
  node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='upgrade_v4_0_0_b03_002')
  ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'original-upgrade-step','exec'),ns)
  with patch('tactic.core.search_code_migration.fix_search_code',side_effect=RuntimeError('unresolved parents')),self.assertRaises(RuntimeError):ns[node.name](Mock(is_confirmed=True,quiet=True))
