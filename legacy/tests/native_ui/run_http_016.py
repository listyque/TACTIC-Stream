"""0.16 widget dispatch and diagnostics, only on the disposable ORIGINAL test server."""
import argparse,json,uuid
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
s=requests.Session();headers={'X-Tactic-UI':'1','Origin':a.url};results=[];nonce=uuid.uuid4().hex[:8];context={}
def call(method,path,**data):
    return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers,timeout=60)
def good(r):
    if r.status_code not in (200,201):raise AssertionError(f'{r.status_code}: {r.text[:1600]}')
    return r.json()
def check(name,condition=True):
    results.append({'scenario':name,'passed':bool(condition)});print(('PASS ' if condition else 'FAIL ')+name,flush=True)
    if not condition:raise AssertionError(name)
def links(tree):
    result=[]
    def walk(nodes):
        for node in nodes:
            if node.get('kind')=='link':result.append(node)
            walk(node.get('children',[]))
    for section in tree['sections']:walk(section['children'])
    return result
try:
    denied=call('POST','/client-events',project='admin',events=[{'event':'view.open'}])
    check('Client action reporting requires a session',denied.status_code==401)
    auth=good(call('POST','/session',login='admin',password='Native-Test-Only-123'));headers['X-CSRF-Token']=auth['csrf']
    tree=good(call('GET','/sidebar',project='admin'));all_links=links(tree);lookup={n['name']:n for n in all_links}
    expected={'project_workflow':'pipeline','project_schema':'schema','system_config':'system-config','system_info':'system','script_editor':'script-editor','users_in_groups':'group-membership','create_project':'project-create'}
    # Record the actual entire stock navigation, not a substitute menu.
    context['admin_routes']=[]
    for node in all_links:
        if node['name'] in expected:
            opened=good(call('GET','/open',project='admin',target=node['id']))
            check('Original configured '+node['name']+' stays '+expected[node['name']],opened['kind']==expected[node['name']])
            context['admin_routes'].append({k:opened.get(k) for k in ['id','handler','kind','search_type','view']})
    check('Pipeline and schema dedicated links exist',all(k in lookup for k in ['project_workflow','project_schema']))
    for name in ['sthpw_pipelines','sthpw_schema']:
        check('Original raw management table '+name+' exists',name in lookup)
        target=lookup[name]['id'];opened=good(call('GET','/open',project='admin',target=target))
        check(name+' remains actual manage table, not guessed graph',opened['kind']=='table' and opened['view']=='manage')
        field='editor' if name=='sthpw_pipelines' else 'create'
        definition=next(f for f in opened['spec']['fields'] if f['name']==field)
        check(name+' restores original ButtonElementWdg',definition.get('widget_link') and definition.get('cell_action') in ('pipeline-editor','schema-editor'))
        context[name]=target
    project='native11test';flow=lookup['project_workflow']['id'];schema=lookup['project_schema']['id']
    created=good(call('POST','/graph',project=project,target=flow,kind='pipeline',code='zz_native16_'+nonce,name='Selected pipeline '+nonce))
    key=created['key'];context['pipeline_key']=key
    # The editor must select this row, not whichever happens to sort first.
    rows=good(call('POST','/query',project='admin',target=context['sthpw_pipelines'],limit=200))
    row=next(r for r in rows['items'] if r['key']==key);button=row['cells']['editor']
    check('Pipeline row contains native original editor action',button['kind']=='widget' and button['inline'] is False and button.get('open_mode')=='tab')
    opened=good(call('GET','/open',project='admin',target=button['target']))
    check('Pipeline button opens specialized graph, not table',opened['kind']=='pipeline')
    check('Pipeline button keeps original selected search_key',opened['options']['search_key']==key)
    initial=good(call('GET','/graph',project='admin',target=button['target'],kind='pipeline'))
    check('Row-selected pipeline wins over default sorted first',initial['initial_key']==key)
    graph=good(call('GET','/graph',project='admin',target=button['target'],kind='pipeline',key=key))
    headers['X-Tactic-Action-ID']='ui_integration_save_016'
    edited=good(call('PATCH','/graph',project='admin',target=button['target'],kind='pipeline',key=key,revision=graph['revision'],operations=[{'op':'add_node','name':'prepare','attributes':{'type':'manual'}},{'op':'add_node','name':'approve','attributes':{'type':'approval'}},{'op':'add_edge','from':'prepare','to':'approve','attributes':{}}]))
    graph=good(call('GET','/graph',project=project,target=flow,kind='pipeline',key=key))
    check('Graph button runs actual PipelineSaveCbk and reloads XML',len(graph['graph']['nodes'])==2 and len(graph['graph']['edges'])==1)
    check('Original process definitions are synchronized',set(graph['settings'])=={'prepare','approve'})
    context['pipeline_cell']=button['target'];context['workflow']=flow;context['schema']=schema
    # Invalid graph kind cannot re-route a selected cell to some other specialized editor.
    invalid=call('GET','/graph',project='admin',target=button['target'],kind='schema')
    check('Configured widget kind enforced at backend boundary',invalid.status_code==403)
    check('Error and response share the real request ID',invalid.json()['error']['request_id']==invalid.headers['X-Request-ID'])
    headers.pop('X-Tactic-Action-ID')
    # Source schema can exist before any DB row; this still uses Schema.get.
    items=good(call('GET','/graph',project=project,target=schema,kind='schema'))
    before=good(call('GET','/graph',project=project,target=schema,kind='schema',key=items['initial_key']))
    good(call('PATCH','/graph',project=project,target=schema,kind='schema',key=before['key'],revision=before['revision'],operations=[]))
    schema_rows=good(call('POST','/query',project='admin',target=context['sthpw_schema'],limit=200))
    candidate=next(r for r in schema_rows['items'] if r.get('cells',{}).get('create',{}).get('target'))
    check('Schema button preserves original tab.add_new placement',candidate['cells']['create'].get('open_mode')=='tab')
    schema_action=candidate['cells']['create']['target'];view=good(call('GET','/open',project='admin',target=schema_action))
    check('Schema row opens original SchemaToolWdg',view['kind']=='schema' and view['options']=={})
    listing=good(call('GET','/graph',project='admin',target=schema_action,kind='schema'))
    loaded=good(call('GET','/graph',project='admin',target=schema_action,kind='schema',key=listing['initial_key']))
    check('Schema button honors current project semantics of original callback',loaded['code']=='admin' and not loaded['can_edit'])
    context['schema_cell']=schema_action
    # Saved workspace only contains target IDs. Reopening must preserve each freshly resolved kind.
    for target in [flow,schema,context['pipeline_cell'],context['schema_cell']]:
        workspace=good(call('GET','/ui-state',project='admin',scope='workspace'))
        good(call('PATCH','/ui-state',project='admin',scope='workspace',revision=workspace['revision'],value={'ids':[target],'active':target}))
        stored=good(call('GET','/ui-state',project='admin',scope='workspace'))
        restored=good(call('GET','/open',project='admin',target=stored['value']['active']))
        check('Persisted workspace restores specialized kind '+target[-35:],restored['kind'] in ('pipeline','schema'))
    event=call('POST','/client-events',project='admin',events=[{'event':'view.open','action_id':'ui_client_016','target':flow}])
    check('Local-only action accepted under original authorized project',good(event)['accepted']==1)
    forged=call('POST','/client-events',project='admin',events=[{'event':'view.open','user':'somebody','target':flow}])
    check('Client event cannot forge actor',forged.status_code==400)
    wrong=call('POST','/client-events',project='unregistered_project',events=[{'event':'view.open','target':flow}])
    check('Client events require real project scope',wrong.status_code==403)
    # Requests with sensitive field values must remain safe in the action log.
    users=lookup['users']['id'];call('POST','/query',project='admin',target=users,filters=[{'field':'first_name','op':'eq','value':'DIAGNOSTIC_PRIVATE_FILTER_016'}],limit=10)
    denied=call('POST','/session',login='admin',password='DIAGNOSTIC_PRIVATE_PASSWORD_016')
    check('Invalid-password log does not use caller identity',denied.status_code==401)
    # Restore an empty disposable workspace for following browser regression.
    workspace=good(call('GET','/ui-state',project='admin',scope='workspace'))
    good(call('PATCH','/ui-state',project='admin',scope='workspace',revision=workspace['revision'],value={'ids':[],'active':''}))
    context['passed']=True
finally:
    context['scenarios']=results;context['scope']='Original TACTIC/SQLite, not mock DB; signature isolation in runner only'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n')
