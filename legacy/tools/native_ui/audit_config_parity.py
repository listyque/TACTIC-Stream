"""Differential comparison of original TACTIC metadata on SHIPPED XML only.

No DB priority/custom installed configuration coverage and no widget rendering
parity claim. Each view is compared with its file's definition layers using
real WidgetConfig/WidgetConfigView, not a second hand-written reference model.
"""
import argparse,json,sys,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from tactic.core.widget_config import WidgetConfig,WidgetConfigView
from tactic.core.config_model import ConfigModel,parse_xml
from pyasm.common import Container

def original_aliases():
 tree=ast.parse((ROOT/'src/tactic/ui/common/widget_class_handler.py').read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WidgetClassHandler')
 init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
 assignment=next(n for n in init.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='base_config' for t in n.targets))
 root=parse_xml(ast.literal_eval(assignment.value))
 return {n.get('name'):n.find('display').get('class') for n in root.findall('widget_definition/element') if n.find('display') is not None}

def audit():
 aliases=original_aliases()
 report={'scope':'shipped file views plus same-file definitions; not live DB or rendered widgets','files':0,'views':0,'elements':0,'checks':0,'differences':[],'errors':[]}
 for folder in ('src/config2/search_type/widget','src/tactic/ui/config'):
  for path in sorted((ROOT/folder).rglob('*.xml')):
   relative=str(path.relative_to(ROOT));raw=path.read_text(encoding='utf-8')
   try:root=parse_xml(raw)
   except Exception as exc:report['errors'].append({'file':relative,'error':str(exc)});continue
   if root.tag!='config':continue
   report['files']+=1
   for node in root:
    if not isinstance(node.tag,str):continue
    view=node.get('name') if node.tag=='view' else node.tag
    if not view:continue
    Container.create()
    try:
     layers=[view]+(['edit_definition'] if view in ('edit','insert') else [])+(['definition'] if view!='definition' else [])
     conf=WidgetConfigView(search_type=None,view=view,configs=[WidgetConfig.get(xml=raw,view=v) for v in layers])
     native=ConfigModel.from_tactic(conf)
     def compare(kind,expected,actual,element=None):
      report['checks']+=1
      if expected!=actual:report['differences'].append({'file':relative,'view':view,'element':element,'property':kind,'original':expected,'native':actual})
     compare('order',conf.get_element_names(),native.names());compare('view_attributes',conf.get_view_attributes(),native.attributes())
     report['views']+=1
     for name in native.names():
      if not name:continue
      report['elements']+=1
      compare('attributes',conf.get_element_attributes(name),native.attributes(name),name)
      compare('title',conf.get_element_title(name),native.describe(name)['title'],name)
      # These comparisons use declared handlers only: no layout fallback import.
      for kind in ('display','edit','action'):
       for source in conf.get_configs():
        element=source.get_element_node(name)
        if element is None:continue
        nodes=source.get_xml().get_nodes('config/%s/element[@name="%s"]/%s' % (source.view_xpath,name,kind))
        declared=''
        if nodes:
         declared=nodes[0].get('class') or aliases.get(nodes[0].get('widget'),'')
        if declared:
         compare(kind+'_handler',declared,native.handler(name,kind),name);break
      # Source-specific options special cases may import handler metadata but
      # never call get_display or instantiate a visual widget.
      compare('display_options',conf.get_display_options(name),native.options(name),name)
    except Exception as exc:
     report['errors'].append({'file':relative,'view':view,'error':type(exc).__name__+': '+str(exc)})
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'docs/native-ui/0.7/config-parity.json');a=p.parse_args();r=audit();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('differences','errors')},ensure_ascii=False));print('Differences:',len(r['differences']),'Errors:',len(r['errors']));raise SystemExit(bool(r['differences'] or r['errors']))
