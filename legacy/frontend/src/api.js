let csrf = '';
// Diagnostic intentions only. Never collect input text, clipboard, passwords,
// scripts, XML, response data or arbitrary DOM text. Correlation is not authorization.
let actionContext={project:'',target:''}, recentAction=null, actionQueue=[], actionTimer=null, actionSending=false, actionSerial=0;
function actionId(){return 'ui_'+Date.now().toString(36)+'_'+(++actionSerial).toString(36)+'_'+Math.random().toString(36).slice(2,8)}
function action(name,detail={}){
  if(!csrf)return;
  const project=detail.project||actionContext.project;
  if(!project)return;
  const entry={event:name,action_id:actionId(),target:detail.target??actionContext.target??''};
  for(const key of ['field','control'])if(typeof detail[key]==='string')entry[key]=detail[key].slice(0,100);
  if(Number.isInteger(detail.count))entry.count=detail.count;
  recentAction={project,target:entry.target,id:entry.action_id,at:Date.now()};
  if(actionQueue.length<96)actionQueue.push({project,event:entry});
  if(!actionTimer)actionTimer=setTimeout(()=>{actionTimer=null;flushActions()},120);
  return entry.action_id;
}
async function flushActions(){
  if(actionSending||!actionQueue.length||!csrf)return;
  actionSending=true;
  try{
    const project=actionQueue[0].project, batch=[];
    actionQueue=actionQueue.filter(item=>{if(item.project===project&&batch.length<32){batch.push(item.event);return false}return true});
    const url=new URL('/api/ui/v2/client-events',window.location.origin);
    // No retries: this must not delay or repeat the real operation.
    await fetch(url,{method:'POST',credentials:'same-origin',headers:{'X-Tactic-UI':'1','X-CSRF-Token':csrf,'Content-Type':'application/json'},body:JSON.stringify({project,events:batch})});
  }catch{}finally{actionSending=false;if(actionQueue.length&&!actionTimer)actionTimer=setTimeout(()=>{actionTimer=null;flushActions()},120)}
}
function traceHeaders(data){
  const current=recentAction;
  return current&&Date.now()-current.at<1500&&data.project===current.project&&(!data.target||data.target===current.target)?{'X-Tactic-Action-ID':current.id}:{};
}

export class HttpError extends Error { constructor(status, data) { super(data.error?.message || `HTTP ${status}`); this.status=status; this.details=data.error?.details; this.requestId=data.error?.request_id; } }
export default {
  action,
  setContext(project,target=''){actionContext={project,target}},
  flushActions,
  async request(path, data={}, method='GET') {
    const url = new URL('/api/ui/v2'+path, window.location.origin);
    const headers = {'X-Tactic-UI':'1',...traceHeaders(data)};
    const options = {method, credentials:'same-origin', headers};
    if (method==='GET') Object.entries(data).forEach(([k,v])=>{if(v!==undefined&&v!==null)url.searchParams.set(k,v)});
    else {headers['Content-Type']='application/json';headers['X-CSRF-Token']=csrf;options.body=JSON.stringify(data)}
    const response=await fetch(url,options); let result;
    try {result=await response.json()} catch {throw new Error('Сервер вернул не JSON. Проверьте запуск native API и журнал TACTIC.')}
    if(!response.ok)throw new HttpError(response.status,result);
    if(result.csrf)csrf=result.csrf;
    if(path==='/session'&&method==='DELETE'){csrf='';actionQueue=[];recentAction=null;actionContext={project:'',target:''}}
    return result;
  },
  async downloadCsv(data) {
    const response = await fetch('/api/ui/v2/export-csv', {method:'POST',credentials:'same-origin',headers:{'X-Tactic-UI':'1','X-CSRF-Token':csrf,'Content-Type':'application/json'},body:JSON.stringify(data)});
    if(!response.ok)throw new HttpError(response.status,await response.json());
    const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=(data.search_type||'TACTIC').replace(/[^a-zA-Z0-9_.-]/g,'_')+'.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
  },
  async uploadChunk(params,bytes,signal) {
    const url=new URL('/api/ui/v2/upload-chunk',location.origin);
    Object.entries(params).forEach(([key,value])=>url.searchParams.set(key,value));
    const response=await fetch(url,{method:'PATCH',credentials:'same-origin',signal,
      headers:{'X-Tactic-UI':'1','X-CSRF-Token':csrf,'Content-Type':'application/octet-stream'},body:bytes});
    const data=await response.json();if(!response.ok)throw new HttpError(response.status,data);return data;
  },
  async upload(params,file) {
    const url=new URL('/api/ui/v2/upload',location.origin);Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,v));
    const result=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'X-Tactic-UI':'1','X-CSRF-Token':csrf,'Content-Type':'application/octet-stream','Idempotency-Key':crypto.randomUUID()},body:file});
    const data=await result.json();if(!result.ok)throw new HttpError(result.status,data);return data;
  }
};
