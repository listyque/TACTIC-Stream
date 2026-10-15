"""Differential tests against the extracted ORIGINAL WidgetConfigView class.

These instantiate real TACTIC Xml/WidgetConfig/WidgetConfigView, not a substitute
resolver. They do not need a database or render any widgets.
"""
import sys,os,subprocess,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'src'));sys.path.insert(0,str(R/'src/client'))
from tactic.core.widget_config import WidgetConfig,WidgetConfigView
from tactic.core.config_model import ConfigModel,parse_xml,view_node,title
from pyasm.common import Container,Common

class OriginalResolverTests(unittest.TestCase):
 def setUp(self):Container.create()
 def make(self,view,layers):
  return WidgetConfigView(search_type=None,view=view,configs=[WidgetConfig.get(xml=xml,view=v) for xml,v in layers])
 def test_order_and_attributes_all_sidebar_config_views(self):
  checked=0
  for path in (R/'src/tactic/ui/config').glob('*.xml'):
   xml=path.read_text();root=parse_xml(xml)
   if root.tag!='config':continue
   for node in root:
    if not isinstance(node.tag,str):continue
    v=node.get('name') if node.tag=='view' else node.tag
    if not v:continue
    conf=self.make(v,[(xml,v),(xml,'definition')]);model=ConfigModel.from_tactic(conf)
    with self.subTest(file=path.name,view=v):
     self.assertEqual(model.names(),conf.get_element_names())
     self.assertEqual(model.attributes(),conf.get_view_attributes())
     for name in model.names():
      if name:self.assertEqual(model.attributes(name),conf.get_element_attributes(name));self.assertEqual(model.describe(name)['title'],conf.get_element_title(name))
    checked+=1
  self.assertGreater(checked,50)
 def test_empty_db_view_suppresses_default_exactly(self):
  conf=self.make('table',[('<config><table/></config>','table'),('<config><table><element name="x"/></table></config>','table')]);self.assertEqual(ConfigModel.from_tactic(conf).names(),conf.get_element_names());self.assertEqual(conf.get_element_names(),[])
 def test_handler_cascades_independent_of_options(self):
  a='<config><table><element name="x"><display><values>a|b</values></display></element></table></config>'
  b='<config><definition><element name="x"><display class="example.DoesNotExist"><labels>A|B</labels></display><action class="DatabaseAction"/></element></definition></config>'
  conf=self.make('table',[(a,'table'),(b,'definition')]);m=ConfigModel.from_tactic(conf)
  self.assertEqual(m.handler('x'),conf.get_display_handler('x'));self.assertEqual(m.options('x'),conf.get_display_options('x'));self.assertEqual(m.handler('x','action'),conf.get_action_handler('x'))
 def test_core_metadata_import_does_not_import_presentation(self):
  env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(R/'src'),str(R/'src/client')])
  code="from tactic.core.widget_config import WidgetConfig,WidgetConfigView; import sys; bad=[n for n in sys.modules if n.startswith(('tactic.ui','pyasm.widget','pyasm.web'))]; assert not bad,bad"
  result=subprocess.run([sys.executable,'-W','ignore','-c',code],env=env,text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_titles_match_upstream(self):
  for name in ('first_name','viewPanel','URLValue','admin.custom_view','_my_admin',' Login '):self.assertEqual(title(name),Common.get_display_title(name))
 def test_standard_form_order_from_original_user_config(self):
  xml=(R/'src/config2/search_type/widget/sthpw/login-conf.xml').read_text()
  for v in ('table','edit','insert'):
   c=self.make(v,[(xml,v),(xml,'edit_definition' if v!='table' else 'definition')]);self.assertEqual(ConfigModel.from_tactic(c).names(),c.get_element_names())

if __name__=='__main__':unittest.main()
