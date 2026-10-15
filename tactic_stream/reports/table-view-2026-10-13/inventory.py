from pathlib import Path
import ast,csv,html,io,json,re,tokenize,warnings,xml.etree.ElementTree as ET
warnings.filterwarnings("ignore",category=SyntaxWarning)
from collections import Counter
legacy=Path('D:/code/TACTIC_VUE/legacy/src');stream=Path('D:/code/TACTIC_VUE/tactic_stream');out=stream/'reports/table-view-2026-10-13'
modules={};classes={};errors=[]
def module_name(path,root):
    parts=list(path.relative_to(root).with_suffix('').parts)
    if parts[-1]=='__init__':parts.pop()
    return '.'.join(parts)
for namespace in ['pyasm','tactic']:
 for path in (legacy/namespace).rglob('*.py'):
    source=path.read_text(encoding='utf-8-sig',errors='replace');module=module_name(path,legacy)
    data={'imports':{},'stars':[],'path':path};modules[module]=data
    try:
        tree=ast.parse(source)
        imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        for n in imports:
            if isinstance(n,ast.ImportFrom):
                package=module if path.name=='__init__.py' else module.rsplit('.',1)[0]
                prefix='.'.join(package.split('.')[:len(package.split('.'))-n.level+1]) if n.level else ''
                target='.'.join(x for x in [prefix,n.module] if x)
                for a in n.names:
                    if a.name=='*':data['stars'].append(target)
                    else:data['imports'][a.asname or a.name]=target+'.'+a.name
            else:
                for a in n.names:data['imports'][a.asname or a.name.split('.')[0]]=a.name if a.asname else a.name.split('.')[0]
    except SyntaxError:
        for target,names in re.findall(r'^from\s+([\w.]+)\s+import\s+([^\n]+)',source,re.M):
            for name in names.split(','):
                name=name.strip().split('#')[0].strip()
                if name=='*':data['stars'].append(target)
                elif re.fullmatch(r'\w+(?:\s+as\s+\w+)?',name):
                    parts=name.split();data['imports'][parts[-1]]=target+'.'+parts[0]
    try:tokens=list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError,IndentationError) as e:errors.append({'file':str(path),'error':str(e)});continue
    for i,t in enumerate(tokens):
        if t.type!=tokenize.NAME or t.string!='class' or t.start[1]!=0:continue
        name=tokens[i+1].string;parts=[]
        for b in tokens[i+2:]:
            if b.string==':':break
            parts.append(b.string)
        bases=''.join(parts).strip('()').split(',')
        q=module+'.'+name
        classes[q]={'class':name,'module':module,'qualified_class':q,'legacy_file':str(path),'legacy_line':t.start[0],'bases':[b for b in bases if b]}
resolved_cache={}
def resolve(module,name,seen=None):
    key=(module,name)
    if key in resolved_cache:return resolved_cache[key]
    result=resolve_impl(module,name,seen)
    if result is not None or seen is None:resolved_cache[key]=result
    return result
def resolve_impl(module,name,seen=None):
    seen=set() if seen is None else seen
    key=(module,name)
    if key in seen:return None
    seen=seen|{key}
    if name in classes:return name
    local=module+'.'+name
    if local in classes:return local
    info=modules.get(module,{})
    imports=info.get('imports',{})
    head,*tail=name.split('.')
    if head in imports:
        target=imports[head]+('.'+'.'.join(tail) if tail else '')
        if target in classes:return target
        if '.' in target:
            mod,symbol=target.rsplit('.',1)
            match=resolve(mod,symbol,seen)
            if match:return match
    for star in reversed(info.get('stars',[])):
        match=resolve(star,name,seen)
        if match:return match
    if '.' in name:
        mod,symbol=name.rsplit('.',1)
        return resolve(mod,symbol,seen)
    return None
base={'pyasm.widget.table_element_wdg.BaseTableElementWdg','tactic.ui.common.base_table_element_wdg.BaseTableElementWdg'}
parents={q:[resolve(v['module'],b) for b in v['bases']] for q,v in classes.items()}
selected=set(base)
while True:
    more={q for q,p in parents.items() if set(p)&selected}
    if more<=selected:break
    selected|=more
selected-=base|{'pyasm.widget.table_element_wdg.FunctionalTableElement'}
unresolved_direct=[q for q,v in classes.items() if 'BaseTableElementWdg' in v['bases'] and q not in selected|base|{'pyasm.widget.table_element_wdg.FunctionalTableElement'}]
assert not unresolved_direct, unresolved_direct
assert 'pyasm.widget.timecard_wdg.TimecardTableElement' not in selected, 'Deprecated quoted class counted'
assert 'pyasm.widget.parallel_status.TaskGearElementWdg' not in selected, 'Quoted JS/old class counted'
handler_source=(legacy/'tactic/ui/common/widget_class_handler.py').read_text(encoding='utf-8')
block=handler_source.split('class TableElementClassHandler')[1]
root=ET.fromstring(re.search("base_config = '''(.*?)'''",block,re.S).group(1))
catalog=[{'alias':n.get('name'),'handler':n.find('display').get('class')} for n in root.findall('./widget_definition/element')]
registered={}
for row in catalog:
    target=resolve(*row['handler'].rsplit('.',1));row['resolved_class']=target
    if target:selected.add(target);registered.setdefault(target,[]).append(row['alias'])
backend_source=(stream/'src/tactic_stream/server/table_cells.py').read_text(encoding='utf-8')
backend_tree=ast.parse(backend_source)
widget_dict=next(n.value for n in backend_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='WIDGETS' for t in n.targets))
supported={}
for k,v in zip(widget_dict.keys,widget_dict.values):
    alias=k.value
    if not alias:continue
    target=resolve(*alias.rsplit('.',1)) if '.' in alias else resolve('pyasm.widget',alias)
    if target:selected.add(target);supported.setdefault(target,[]).append(alias)
stream_index={}
for folder in ['src/pyasm','src/tactic']:
 for path in (stream/folder).rglob('*.py'):
    try:tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    except (SyntaxError,UnicodeError):continue
    for n in tree.body:
        if isinstance(n,ast.ClassDef):stream_index[module_name(path,stream/'src')+'.'+n.name]=str(path)+':'+str(n.lineno)
print(json.dumps({'discovered_table_widgets':len(selected),'direct_table_module':sum(classes[q]['module'].startswith('tactic.ui.table.') for q in selected),'supported':{classes[q]['class']:a for q,a in supported.items()},'unresolved_catalog':[r for r in catalog if not r['resolved_class']],'lexing_errors':errors},ensure_ascii=False,indent=1))
(out/'source_inventory.json').write_text(json.dumps({'classes':[classes[q] for q in sorted(selected)],'catalog':catalog,'supported':supported,'stream_classes':stream_index,'lexing_errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
