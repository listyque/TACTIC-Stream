"""0.18 original TACTIC HTTP tests. Companion server owns temporary seed data."""
import argparse, json, uuid, time
from pathlib import Path
from urllib.parse import quote
import requests
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
s=requests.Session();h={'X-Tactic-UI':'1','Origin':a.url};pj='native11test';nonce='n18_'+uuid.uuid4().hex[:7]
r={'passed':False,'scenarios':[],'backend':'3 original TACTIC workers; SQLite seed; no fixture authentication or writes'}
def req(method,path,**d):return s.request(method,a.url+'/api/ui/v2'+path,params=d if method=='GET' else None,json=d if method!='GET' else None,headers=h,timeout=90)
def op(method,path,**d):return req(method,path,project=pj,**d)
def good(resp):
    if resp.status_code not in (200,201):raise AssertionError(str(resp.status_code)+' '+resp.text[:2400])
    return resp.json()
def check(name,condition=True):
    r['scenarios'].append({'scenario':name,'passed':bool(condition)});print(('PASS ' if condition else 'FAIL ')+name,flush=True)
    if not condition:raise AssertionError(name)
def links(tree):
    ans={}
    def walk(nodes):
        for n in nodes:
            if n.get('kind')=='link':ans[n['name']]=n['id']
            walk(n.get('children',[]))
    walk(tree['sections']);return ans
try:
    check('Anonymous layout endpoint denied',op('GET','/design-catalog',kind='layout',target='anything').status_code==401)
    auth=good(req('POST','/session',login='admin',password='Native-Test-Only-123'));h['X-CSRF-Token']=auth['csrf']
    nav=links(good(op('GET','/sidebar')))
    # Locate by actual original handler rather than substituting fixed data models.
    mapping={}
    for name,target in nav.items():
        if any(term in name for term in ('view','custom','script','search_type')):
            opened=op('GET','/open',target=target)
            if opened.status_code==200:
                kind=opened.json()['kind']
                if kind in ('layout-editor','views-manager','script-editor','search-types'):mapping[kind]=target
    check('All four original entry handlers resolve',set(mapping)=={'layout-editor','views-manager','script-editor','search-types'})
    r['targets']=mapping;r['project']=pj
    layout=mapping['layout-editor'];views=mapping['views-manager'];scripts=mapping['script-editor'];types=mapping['search-types']
    check('Layout operations reject an unrelated table',op('GET','/design-catalog',kind='layout',target=nav['users']).status_code==403)
    created=good(op('POST','/layout-document',target=layout,view=nonce,login=None));lk=created['key'];r['layout_key']=lk
    check('Original widget_config stores new category layout',created['saved'] and '<'+nonce+'>' in created['xml'])
    changed=good(op('PATCH','/layout-document',target=layout,key=lk,revision=created['revision'],changes={
        'html':'<section class="layout-card"><h2>Custom layout 0.18</h2><p>Unicode: Привет &amp; XML</p><element name="users"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>sthpw/login</search_type><view>table</view><element_names>login,first_name,last_name</element_names><show_insert>false</show_insert></display></element></section>',
        'style':'.layout-card { padding: 18px; border: 1px solid #8797b0; }',
        'mako':'<%\nprivate_marker = "DESIGN_PRIVATE_BODY_018"\n%>',
        'behavior':'<behavior type="load"><![CDATA[window.DESIGN_PRIVATE_BODY_018 = true;]]></behavior>',
        'kwargs':'{"record": "my_record"}'
    }));r['layout_revision']=changed['revision']
    check('Section edits preserve exact saved Mako and behavior', 'DESIGN_PRIVATE_BODY_018' in changed['parts']['mako'] and '<![CDATA[' in changed['parts']['behavior'])
    check('Saved HTML style is kept in original html/style format','<style type="text/css"><![CDATA[' in changed['xml'])
    check('Stale layout save conflicts',op('PATCH','/layout-document',target=layout,key=lk,revision=created['revision'],changes={'style':'x{}'}).status_code==409)
    child=layout+'/~design/layout:'+quote(lk,safe='');r['layout_target']=child
    view=good(op('GET','/open',target=child))
    check('Saved layout is a specialized widget',view['kind']=='custom-layout')
    check('Nested widget resolved from original element config',len(view['layout']['children'])==1 and view['layout']['children'][0]['kind']=='table')
    table=view['layout']['children'][0]['id'];nested=good(op('GET','/open',target=table))
    check('Nested table receives actual resolved view',nested['kind']=='table' and [f['name'] for f in nested['spec']['fields']]==['login','first_name','last_name'])
    rows=good(op('POST','/query',target=table,limit=25));check('Nested table loads original SObjects',bool(rows['items']))
    nested2=good(op('GET','/open',target=table+'/~cell/'+quote('forged',safe=''))) if False else None
    check('Forged hidden/out-of-range layout target denied',op('GET','/open',target=child+'/~layout/999').status_code==403)
    preview=good(op('POST','/layout-preview',target=layout,view=nonce,xml=changed['xml']));check('Preview never executes stored code',preview['executed'] is False)
    check('XML external entity input rejected',op('PATCH','/layout-document',target=layout,key=lk,revision=changed['revision'],xml='<!DOCTYPE config [<!ENTITY x SYSTEM "file:///etc/passwd">]><config><'+nonce+'/></config>').status_code==400)
    check('Cannot create another user personal layout',op('POST','/layout-document',target=layout,view=nonce+'_other',login='another').status_code==403)
    copy=good(op('POST','/layout-document',target=layout,view=nonce+'_copy',source_key=lk,source_revision=changed['revision']))
    check('Explicit copy keeps source unchanged',copy['key']!=lk and good(op('GET','/layout-document',target=layout,key=lk))['revision']==changed['revision'])
    check('Deletion requires explicit confirmation',op('DELETE','/layout-document',target=layout,key=copy['key'],revision=copy['revision']).status_code==400)
    good(op('DELETE','/layout-document',target=layout,key=copy['key'],revision=copy['revision'],confirm='REMOVE_OVERRIDE'))
    check('Deleted override is not returned as still-existing',op('GET','/layout-document',target=layout,key=copy['key']).status_code==404)
    shorthand=good(op('POST','/layout-document',target=layout,view=nonce+'_short',xml='<config><'+nonce+'_short><element name="users"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>sthpw/login</search_type><view>table</view></display></element><html><element name="users"/><element display_class="tactic.ui.panel.TableLayoutWdg" spt_search_type="sthpw/login" view="table"/><element load="none" name="hidden" display_class="tactic.ui.panel.TableLayoutWdg" search_type="sthpw/login"/></html></'+nonce+'_short></config>'))
    short_target=layout+'/~design/layout:'+quote(shorthand['key'],safe='')
    short=good(op('GET','/open',target=short_target))['layout']['children']
    check('Named layout reference uses original same-view definition',short[0]['kind']=='table' and short[0]['search_type']=='sthpw/login')
    check('display_class shorthand creates native table with options',short[1]['kind']=='table' and short[1]['search_type']=='sthpw/login')
    check('load none child cannot be requested directly',short[2]['hidden'] and op('GET','/open',target=short[2]['id']).status_code==403)
    check('Named-definition child executes original table query',good(op('POST','/query',target=short[0]['id'],limit=10))['total']>0)
    # New local type through original creator, then use its config.
    st=good(op('POST','/search-types',target=types,name=nonce,title='Design type '+nonce,description='Native test',columns=[{'name':'external_ref','type':'varchar'}],pipeline=True,preview=False))['search_type'];r['search_type']=st
    detail=good(op('GET','/stype-editor',target=types,search_type=st));check('Original SearchType created with column and config',any(c['name']=='external_ref' for c in detail['columns']))
    catalog=good(op('GET','/design-catalog',target=views,search_type=st));check('Manage Views lists inherited definitions',all(v in catalog['views'] for v in ('table','edit','insert')))
    source=good(op('GET','/view-document',target=views,search_type=st,view='table'))
    check('Inherited view carries resolved source revision',source['inherited'] and bool(source['revision']))
    copy=good(op('POST','/view-document',target=views,search_type=st,view='new_view_018',source_view='table',source_revision=source['revision'],login='admin'));r['view_key']=copy['key']
    check('View copy creates actual personal widget_config',copy['login']=='admin')
    xml=copy['xml'].replace('name="name"','name="name" title="Название 018"')
    edited=good(op('PATCH','/view-document',target=views,search_type=st,key=copy['key'],revision=copy['revision'],xml=xml))
    check('View XML edit persists', 'Название 018' in edited['xml'])
    check('View conflict preserves saved version',op('PATCH','/view-document',target=views,search_type=st,key=copy['key'],revision=copy['revision'],xml=xml).status_code==409)
    opened_target=views+'/~design/view:'+quote(json.dumps([st,'new_view_018']),safe='');r['view_target']=opened_target
    check('Opened managed view remains original configured table',good(op('GET','/open',target=opened_target))['kind']=='table')
    for tool,kind in [('views','views-manager'),('insert','form'),('workflow','pipeline'),('schema','schema')]:
        target=types+'/~admin/stype-tool:'+tool+':'+quote(st,safe='')
        check('SearchType '+tool+' opens original specialized path',good(op('GET','/open',target=target))['kind']==kind)
    selected={'selected':st,'tab':'columns'};state=good(op('GET','/ui-state',scope='stype-editor',target=types))
    good(op('PATCH','/ui-state',scope='stype-editor',target=types,revision=state['revision'],value=selected))
    check('SearchType selection persisted in original WidgetSettings',good(op('GET','/ui-state',scope='stype-editor',target=types))['value']==selected)
    check('Unknown type rejected from persisted editor state',op('PATCH','/ui-state',scope='stype-editor',target=types,revision=good(op('GET','/ui-state',scope='stype-editor',target=types))['revision'],value={'selected':'foreign/unknown','tab':'columns'}).status_code==400)
    dep=good(op('GET','/stype-dependencies',target=types,search_type=st,field='name'));check('Dependency inspector is honest about destructive limits',dep['can_drop'] is False and isinstance(dep['references'],list))
    # CSV through ORIGINAL command, not native fake persistence.
    csv=good(op('GET','/stype-import',target=types,search_type=st));r['csv_fields']=[f['name'] for f in csv['fields']]
    check('CSV mapper permits ordinary fields only','name' in r['csv_fields'] and 'id' not in r['csv_fields'])
    payload={'target':types,'search_type':st,'text':'Name,Description\r\n  CSV One  ,Unicode Привет\r\nCSV Two,Second\r\n','mapping':['name','description'],'delimiter':','}
    pr=good(op('POST','/stype-import',**payload,operation='preview'));check('CSV preview uses original trimming without creating rows',pr['rows'][0]['name']=='CSV One' and pr['executed'] is False)
    table=types+'/~admin/stype-table:'+quote(st,safe='')
    check('Preview leaves real table empty',good(op('POST','/query',target=table))['total']==0)
    check('CSV requires preview matching exact submitted content',op('POST','/stype-import',**payload,operation='import',preview_revision='forged',confirm='IMPORT_NEW_ROWS').status_code==409)
    imported=good(op('POST','/stype-import',**payload,operation='import',preview_revision=pr['preview_revision'],confirm='IMPORT_NEW_ROWS'));check('Original CsvImportCmd imports two rows',imported['created']==2 and imported['command']=='pyasm.command.CsvImportCmd')
    db=good(op('POST','/query',target=table,limit=50));check('Original model reads imported values',db['total']==2 and {x['values']['name'] for x in db['items']}=={'CSV One','CSV Two'})
    check('CSV cannot update existing IDs',op('POST','/stype-import',**dict(payload,mapping=['id','name']),operation='preview').status_code==400)
    # Saved Python source + real original execution, explicitly enabled in test config.
    sc=good(op('POST','/script',target=scripts,values={'folder':'native018','title':nonce,'language':'python','description':'Saved execution test','script':'return {"echo": input.get("value"), "ok": True}\n'}))['record'];r['script_key']=sc['key']
    check('Script catalog exposes explicit execution policy',good(op('GET','/scripts',target=scripts))['can_execute'] is True)
    diff=good(op('POST','/script-diff',target=scripts,key=sc['key'],revision=sc['revision'],script=sc['values']['script']+'# draft\n'));check('Server compares draft to exact saved script', '+# draft' in diff['diff'] and diff['executed'] is False)
    check('Script execution requires saved revision',op('POST','/script-run',target=scripts,key=sc['key'],revision='bad',confirm='RUN_SAVED_SCRIPT',parameters={}).status_code==409)
    check('Script execution rejects request-supplied source',op('POST','/script-run',target=scripts,key=sc['key'],revision=sc['revision'],confirm='RUN_SAVED_SCRIPT',parameters={},script='pass').status_code==400)
    start=time.monotonic();exe=good(op('POST','/script-run',target=scripts,key=sc['key'],revision=sc['revision'],confirm='RUN_SAVED_SCRIPT',parameters={'value':'original command'}));check('Original execute_python_script evaluates saved source',exe['result']['info']['echo']=='original command' and exe['executed'] is True)
    slow=good(op('PATCH','/script',target=scripts,key=sc['key'],revision=sc['revision'],values={**sc['values'],'script':'import time\ntime.sleep(6)\nreturn "finished"\n'})) if False else None
    # Explicit slow request proves RUNNING logging before response without fake sleep in transport.
    values={k:sc['values'].get(k,'') for k in ('folder','title','language','description','script')};values['script']='import time\ntime.sleep(6)\nreturn "finished"\n'
    slow=good(op('PATCH','/script',target=scripts,key=sc['key'],revision=sc['revision'],values=values))['record'];r['script_key']=slow['key']
    h['X-Tactic-Action-ID']='ui_slow_saved_script_018'
    exe=good(op('POST','/script-run',target=scripts,key=slow['key'],revision=slow['revision'],confirm='RUN_SAVED_SCRIPT',parameters={}));h.pop('X-Tactic-Action-ID')
    check('Long original script completes without timeout/retry',exe['result']['info']=='finished')
    r['passed']=True
except Exception as exc:
    r['error']=str(exc);import traceback;traceback.print_exc()
finally:
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
if not r['passed']:raise SystemExit(1)
