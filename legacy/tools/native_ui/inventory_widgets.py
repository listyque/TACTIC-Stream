#!/usr/bin/env python3
"""Index all first-party UI candidates and static call/config references.

This does NOT mark a file ported because it parsed or contains a known class.
Dynamic DB widget_config, external plugins and generated class paths need a
separate runtime/config export. Third-party packages are not porting targets.
"""
from __future__ import annotations
import argparse,ast,collections,hashlib,json,re,warnings
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PREFIXES=('src/tactic/ui/','src/pyasm/widget/','src/pyasm/web/','src/pyasm/prod/site/','src/pyasm/prod/web/','src/context/spt_js/')
EXTS={'.py','.js','.xml','.css','.html','.htm','.jsx'}
REVIEWED={
 'src/tactic/ui/container/tab_wdg.py':{'status':'partial_semantic_review','methods':['get_display','add_context_menu','TabSaveStateCmd.execute'],'implementation':['src/tactic/core/widget_containers.py','frontend/src/components/ConfiguredTabs.vue'],'remaining':['save_state persistence','tear-off','count/custom callbacks','add view entries']},
 'src/tactic/ui/panel/edit_wdg.py':{'status':'partial_semantic_review','methods':['init','get_config','get_header_context_menu'],'implementation':['src/tactic/ui_api/widget_service.py','frontend/src/components/EmbeddedForm.vue'],'remaining':['custom edit commands/callbacks','parent/connect adapters','all input handlers/layout views']},
 'src/tactic/ui/panel/base_table_layout_wdg.py':{'status':'partial_semantic_review','methods':['get_smart_header_context_menu_data','get_data_row_smart_context_menu_details'],'implementation':['src/tactic/core/context_menus.py','frontend/src/components/ConfiguredTable.vue'],'remaining':['complete grouping semantics','cascade deletion','preview operations','all specialised columns']},
 'src/tactic/ui/panel/panel_wdg.py':{'status':'partial_semantic_review','methods':['SideBarPanelWdg.get_views','SideBarBookmarkMenuWdg.add_link_context_menu'],'implementation':['src/tactic/core/sidebar_config.py','src/tactic/ui_api/menu_service.py','frontend/src/components/SidebarNode.vue'],'remaining':['all sidebar management actions','remove-link exact update_config','external callbacks']},
}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 pa=argparse.ArgumentParser();pa.add_argument('--out',type=Path,default=ROOT/'docs/native-ui/1.0/inventory');args=pa.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 docs={};classes=[];files=[];errors=[]
 for p in sorted((ROOT/'src').rglob('*')):
  rel=p.relative_to(ROOT).as_posix()
  if not p.is_file() or p.suffix.lower() not in EXTS or any(x in p.parts for x in ('__pycache__','node_modules')):continue
  # New/native compiled code isn't a legacy-reference source.
  if rel.startswith(('src/tactic/ui_api/web/','src/client/')):continue
  text=p.read_text(encoding='utf-8',errors='replace');docs[rel]=text
  tree=None;error=None
  if p.suffix=='.py':
   try:
    with warnings.catch_warnings():warnings.simplefilter('ignore');tree=ast.parse(text)
   except (SyntaxError,ValueError) as exc:error={'type':type(exc).__name__,'line':getattr(exc,'lineno',None),'message':str(exc)[:240]}
  top=[n for n in (tree.body if tree else []) if isinstance(n,ast.ClassDef)]
  is_ui=rel.startswith(PREFIXES) or 'wdg' in p.stem.lower() or any(c.name.endswith('Wdg') for c in top)
  if not is_ui:continue
  f={'path':rel,'sha256':digest(p),'lines':len(text.splitlines()),'bytes':p.stat().st_size,'parse_error':error,'review':REVIEWED.get(rel,{'status':'not_individually_reviewed_in_1.0'}),'classes':[]}
  if error:errors.append(dict(path=rel,**error))
  module=rel[4:].removesuffix('.py').replace('/','.')
  for c in top:
   fq=module+'.'+c.name;item={'id':fq,'name':c.name,'source':rel,'line':c.lineno,'end_line':c.end_lineno,'bases':[ast.unparse(b) for b in c.bases],'methods':[{'name':m.name,'line':m.lineno,'end_line':m.end_lineno} for m in c.body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef))],'references':[],'reference_count':0,'port_status':'not_verified_by_static_index'}
   classes.append(item);f['classes'].append(fq)
  files.append(f)
 byname=collections.defaultdict(list);exact=collections.defaultdict(list)
 for c in classes:
  byname[c['name']].append(c);exact[c['id']].append(c)
  # package exports may create this alias; record as candidate, not proof.
  exact[c['id'].rsplit('.',2)[0]+'.'+c['name']].append(c)
 for rel,text in docs.items():
  for line_no,line in enumerate(text.splitlines(),1):
   for token in set(re.findall(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\b',line)):
    name=token.rsplit('.',1)[-1]
    if name not in byname:continue
    matches=exact.get(token) if '.' in token else byname[name]
    if not matches:continue
    for c in matches:
     if c['source']==rel and c['line']==line_no:continue
     c['reference_count']+=1
     if len(c['references'])<120:
      kind='exact_class_path' if token==c['id'] else 'package_export_candidate' if '.' in token else 'short_name_candidate'
      c['references'].append({'path':rel,'line':line_no,'token':token,'kind':kind,'ambiguous_name':len(byname[name])>1})
 for c in classes:c['references_truncated']=c['reference_count']>len(c['references'])
 stats={'ui_candidate_files':len(files),'classes':len(classes),'methods':sum(len(c['methods']) for c in classes),'source_files_scanned_for_refs':len(docs),'parse_errors':len(errors),'partially_reviewed_files_this_iteration':len(REVIEWED),'fully_verified_files_claimed':0}
 report={'scope':list(PREFIXES)+['first-party files named *wdg* and files declaring *Wdg classes'],'limits':['Not a full UI migration percentage','Per-class references capped at 120; total and truncation shown','Short names/package aliases are candidates, not verified call paths','DB configs, generated names and external plugins not available in this static inventory','No completeness claim for functions created dynamically'],'summary':stats,'files':files,'classes':classes,'parse_errors':errors}
 (args.out/'ui-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 rows=['# Пофайловая карта UI · 1.0','','Это статический индекс, не отметка о завершённом переносе. Фактическое поведение проверяется отдельными тестами.','','| Файл | Классов | Строк | Статус обзора в 1.0 |','|---|---:|---:|---|']
 for f in files:rows.append('| `'+f['path']+'` | '+str(len(f['classes']))+' | '+str(f['lines'])+' | '+f['review']['status']+(' / parse error' if f['parse_error'] else '')+' |')
 (args.out/'REVIEW_MATRIX.md').write_text('\n'.join(rows)+'\n');(args.out/'summary.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats))
if __name__=='__main__':main()
