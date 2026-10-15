"""0.7 real CherryPy/config/Select/CSV, isolated TEST schema and authentication."""
import argparse,csv,io,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9167');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/0.7/http-07.json'));a=p.parse_args()
s=requests.Session();h={'X-Tactic-UI':'1'};results=[]
base={'project':'fixture','target':'fixture_columns/formatted'}
def check(name,value):
 assert value,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def call(method,path,data=None,headers=None):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers or h,timeout=30)
def ok(method,path,data):
 r=call(method,path,data);assert r.status_code==200,(path,r.status_code,r.text[:1200]);return r.json()
def rows(r,delimiter=','):
 assert r.status_code==200,(r.status_code,r.text[:1000]);return list(csv.reader(io.StringIO(r.content.decode('utf-8-sig')),delimiter=delimiter))
try:
 check('Resolved config requires session',call('GET','/resolved-view',base).status_code==401)
 check('CSV requires session',call('POST','/export-csv',base).status_code==401)
 login=ok('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=login['csrf']
 opened=ok('GET','/open',base);spec=opened['spec'];names=[f['name'] for f in spec['fields']];by={f['name']:f for f in spec['fields']}
 check('Original handler/options route to configured table',opened['handler']=='tactic.ui.panel.TableLayoutWdg' and spec['type']=='fixture/columns07')
 check('Widget order and virtual dot identifier preserved',names==['code','name','department','amount','ratio','approved','url','timestamp','alias','column.custom'])
 check('Format handler and options inherited from definition',by['amount']['handler']=='tactic.ui.table.FormatElementWdg' and by['amount']['display_options']['format']=='-1234.12')
 check('Column width and alias originate in XML',by['name']['width']=='230' and by['alias']['value_column']=='name')
 check('Unknown custom column remains explicit unsupported',by['column.custom']['display_support']=='unsupported' and by['column.custom']['reason'])
 check('Protected storage not exposed by config inspection','password' not in str(spec))
 page=ok('POST','/query',base);items=page['items'];first=items[0]
 check('Source search_limit used when client limit omitted',len(items)==20 and page['total']==235)
 check('Source multi-column sorting preserves both terms',first['values']['code']=='ROW0234' and all(x['values']['department']=='A' for x in items))
 check('Numeric raw and formatted values stay separate',first['values']['amount']==1468.567 and first['cells']['amount']['text']=='1468.57')
 check('Percent uses original formatter, not raw fraction',first['values']['ratio']==.125 and first['cells']['ratio']['text']=='12.50%')
 check('Date format/timezone follows widget options',first['cells']['timestamp']['text']=='01/10/2026')
 check('Boolean cell typed and not injected widget HTML',first['cells']['approved']=={'kind':'boolean','checked':False,'text':'False'})
 check('Column alias reads original source value',first['values']['alias']==first['values']['name'])
 check('Original Search summaries are page-scoped',len(page['summaries'])==2 and all(x['scope']=='page' for x in page['summaries']) and abs(page['summaries'][0]['value']-sum(x['values']['amount'] for x in items))<.00001)
 nextpage=ok('POST','/query',dict(base,offset=20));check('Pagination retains configured multi-sort',nextpage['items'][0]['values']['code']=='ROW0194')
 audit=ok('GET','/resolved-view',base);check('Audit exposes actual layers, options, ownership',len(audit['layers'])==3 and sum(l['owns_order'] for l in audit['layers'])==1 and audit['fields'][3]['options']['total_summary']=='total')
 inline=dict(base,target='fixture_columns/inline');i=ok('GET','/open',inline)['spec'];check('Inline XML overrides order but inherits definitions',[f['name'] for f in i['fields']]==['name','amount','code'] and i['fields'][0]['label']=='Имя из inline')
 check('Inline own formatting applied in data response',ok('POST','/query',inline)['items'][0]['cells']['amount']['text']=='1469')
 code=dict(base,target='fixture_columns/code_view');c=ok('GET','/resolved-view',code);check('config_code uses stored view alone',c['resolved_view']=='card' and len(c['layers'])==1 and [f['name'] for f in c['fields']]==['code'])
 compact=ok('GET','/open',dict(base,target='fixture_columns/compact'))['spec'];check('Configured table flags remain separate from ACL',all(not compact['table_options'][k] for k in ('show_header','show_select','show_shelf','show_search','show_context_menu','show_search_limit')))
 export=dict(base,columns=['code','name','department','amount','ratio','approved','timestamp','alias'],config_revision=spec['revision'])
 check('CSV POST requires CSRF even when read-only',call('POST','/export-csv',export,headers={'X-Tactic-UI':'1'}).status_code==403)
 r=call('POST','/export-csv',export);values=rows(r)
 check('CSV exports 235 matches, not visible 20 rows',len(values)==236 and values[0]==export['columns'])
 check('CSV preserves configured sort and formatted values',values[1][0]=='ROW0234' and values[1][3:7]==['1468.57','12.50%','False','01/10/2026'])
 check('CSV exact UTF8 escaped text including quotes/comma',values[1][1]=='Строка 234, "тест"')
 check('CSV formula values protected, not executed',next(x for x in values[1:] if x[0]=='ROW0000')[1].startswith("'=HYPERLINK"))
 check('CSV is an attachment with UTF8 BOM',r.headers['content-type'].startswith('text/csv') and 'attachment' in r.headers['content-disposition'] and r.content.startswith(b'\xef\xbb\xbf'))
 check('CSV headers forbid caching and content sniffing','no-store' in r.headers.get('cache-control','') and r.headers.get('x-content-type-options')=='nosniff')
 check('Config revision conflict yields no partial CSV',call('POST','/export-csv',dict(export,config_revision='old')).status_code==409)
 check('Sensitive columns denied even in raw export',call('POST','/export-csv',dict(export,columns=['password'],value_mode='raw')).status_code==403)
 check('Unknown renderer cannot silently export raw instead',call('POST','/export-csv',dict(export,columns=['column.custom'])).status_code==501)
 check('Raw virtual alias export refused',call('POST','/export-csv',dict(export,columns=['alias'],value_mode='raw')).status_code==400)
 check('Unsafe link formatting prevents misleading CSV',call('POST','/export-csv',dict(export,columns=['url'])).status_code==422)
 raw=rows(call('POST','/export-csv',dict(export,columns=['amount','ratio'],value_mode='raw')));check('Raw export preserves unrounded storage',raw[1]==['1468.567','0.125'])
 selected=rows(call('POST','/export-csv',dict(export,selection='selected',keys=[items[2]['key'],items[0]['key']])));check('Selected export preserves current sort not input key order',len(selected)==3 and [x[0] for x in selected[1:]]==['ROW0234','ROW0230'])
 check('Cross-project selected key denied',call('POST','/export-csv',dict(export,selection='selected',keys=['fixture/columns07?id=236'])).status_code in (403,404))
 check('Duplicate selected keys rejected',call('POST','/export-csv',dict(export,selection='selected',keys=[items[0]['key']]*2)).status_code==400)
 filtered=dict(base,target='fixture_columns/filtered');fs=ok('GET','/open',filtered)['spec'];fe=dict(filtered,columns=['code','department'],config_revision=fs['revision']);filteredrows=rows(call('POST','/export-csv',fe))
 check('Saved hidden filter also constrains CSV',len(filteredrows)==119 and all(x[1]=='A' for x in filteredrows[1:]))
 check('Selected record outside saved filter cannot export',call('POST','/export-csv',dict(fe,selection='selected',keys=['fixture/columns07?id=2'])).status_code==409)
 empty=rows(call('POST','/export-csv',dict(fe,where={'op':'and','children':[{'field':'department','op':'eq','value':'B'}]})));check('User filter ANDs with saved filter, never replaces it',empty==[['code','department']])
 semi=call('POST','/export-csv',dict(export,delimiter=';',columns=['code','name']));check('Delimiter choice retains CSV escaping',len(rows(semi,';'))==236)
 check('Client cannot substitute another SearchType or inline config',rows(call('POST','/export-csv',dict(export,columns=['code'],search_type='sthpw/login',config_xml='<config/>')))[1][0]=='ROW0234')
 check('Cross-project target cannot be opened',call('GET','/open',dict(base,project='other')).status_code in (403,404))
 check('Unsupported HTTP verb cannot export',call('GET','/export-csv',export).status_code in (404,405))
 check('Production writes remain disabled',json.loads((Path(__file__).resolve().parents[2]/'src/tactic/ui_api/config.json').read_text())['allow_writes'] is False)
except Exception as e:
 results.append({'scenario':'failure','passed':False,'error':str(e)});raise
finally:
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'backend':'real config/Select/format/CSV, TEST schema/auth/database table','scenarios':results},ensure_ascii=False,indent=2)+'\n')
