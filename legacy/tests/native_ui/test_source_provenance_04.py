"""Verify unchanged algorithms against hashes of methods in the input ZIP.

The fixed hashes are accompanied by source file hashes and explicit symbol
renames. No new-implementation AST was used to derive the expected hashes.
"""
import ast,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=json.loads(Path(__file__).with_name('source-provenance-04.json').read_text())
class SourceProvenanceTests(unittest.TestCase):
 def check_method(self,name):
  entry=next(x for x in DATA['methods'] if x['method']==name)
  cls=next(n for n in ast.parse((ROOT/entry['file']).read_text()).body if isinstance(n,ast.ClassDef) and n.name==entry['class'])
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
  actual=hashlib.sha256(ast.dump(method,include_attributes=False).encode()).hexdigest()
  self.assertEqual(actual,entry['normalized_ast_sha256'])
 def test_original_time_filter(self):self.check_method('_add_time_filter')
 def test_original_value_filter(self):self.check_method('_evaluate_value')
 def test_original_column_filter(self):self.check_method('alter_sobject_search')
 def test_original_boolean_operator_stack(self):self.check_method('add_ops')
 def test_original_work_hour_mutation_algorithm(self):self.check_method('execute')
if __name__=='__main__':unittest.main()
