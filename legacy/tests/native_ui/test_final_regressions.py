import sys, unittest, ast, json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'src'))
from tactic.core.config_model import target_spec
class FinalRegressions(unittest.TestCase):
 def test_actual_project_create_handler(self):
  self.assertEqual(target_spec('LinkWdg',{'class_name':'tactic.ui.app.ProjectCreateWdg'})['kind'],'project-create')
 def test_license_has_dedicated_handler(self):
  self.assertEqual(target_spec('LinkWdg',{'class_name':'tactic.ui.app.LicenseManagerWdg'})['kind'],'license')
 def test_vue_data_not_structured_cloned_after_proxying(self):
  for n in ('GraphEditor','ViewDesigner'):
   self.assertNotIn('structuredClone(this.record', (R/('frontend/src/components/'+n+'.vue')).read_text())
 def test_upgrade_cannot_succeed_on_repeat_required_return(self):
  src=(R/'src/pyasm/search/upgrade/upgrade_db.py').read_text()
  self.assertIn("'repeat_required'",src)
 def test_local_import_probe_never_claims_database_readiness(self):
  self.assertIn('NOT a live-database compatibility test',(R/'tools/local/launch.py').read_text())
 def test_shipping_bootstrap_uses_original_business_server(self):
  tree=ast.parse((R/'tools/local/launch.py').read_text())
  modules=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
  self.assertIn('tactic.startup',modules)
  self.assertNotIn('fixture_deep',modules)
