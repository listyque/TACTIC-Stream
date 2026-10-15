/* Persistent UI state uses original TACTIC WidgetSettings, never localStorage.
   One in-flight write per channel. Pending changes are coalesced, not replayed
   after an ambiguous failure or a revision conflict. No record drafts go here. */
export default (() => {
 const channels=new Map();
 const clone=value=>JSON.parse(JSON.stringify(value));
 const key=a=>JSON.stringify([a.project,a.scope,a.target||'']);
 const announce=(type,detail)=>window.dispatchEvent(new CustomEvent('tactic:state-'+type,{detail}));
 function channel(args){const k=key(args);if(!channels.has(k))channels.set(k,{args:{...args},loaded:false,read:null,revision:null,value:null,writable:false,pending:null,running:null,timer:null,error:null});return channels.get(k)}
 async function read(c,force=false){
  if(c.read)return c.read;
  if(c.loaded&&!force)return c;
  c.read=api.request('/ui-state',c.args).then(r=>{c.revision=r.revision;c.value=r.value;c.writable=r.can_write;c.loaded=true;c.error=null;if(r.warning)announce('warning',r.warning);return c}).finally(()=>c.read=null);
  return c.read;
 }
 async function pump(c){
  clearTimeout(c.timer);c.timer=null;
  if(c.running)return c.running;
  c.running=(async()=>{
   await read(c);
   while(c.pending!==null){
    if(c.error)throw c.error;
    if(!c.writable){c.pending=null;announce('warning','Настройки доступны только для чтения: сохранение в БД выключено.');return}
    const value=c.pending;c.pending=null;
    if(JSON.stringify(value)===JSON.stringify(c.value))continue;
    announce('status','Сохранение настроек…');
    try{const r=await api.request('/ui-state',{...c.args,revision:c.revision,value},'PATCH');c.revision=r.revision;c.value=r.value;announce('status','Настройки сохранены в TACTIC')}
    catch(e){c.error=e;c.pending=null;throw e}
   }
  })().catch(e=>{c.error=e;announce('error','Настройки не сохранены: '+e.message);throw e}).finally(()=>{c.running=null});
  return c.running;
 }
 return {
  async load(args){const c=channel(args);await read(c);return {value:clone(c.value),can_write:c.writable,revision:c.revision}},
  schedule(args,value){const c=channel(args);c.pending=clone(value);clearTimeout(c.timer);c.timer=setTimeout(()=>pump(c).catch(()=>{}),300)},
  async flush(){await Promise.all([...channels.values()].map(c=>(c.pending!==null||c.running||c.timer)?pump(c):Promise.resolve()));const bad=[...channels.values()].find(c=>c.error);if(bad)throw bad.error},
  clear(){for(const c of channels.values())clearTimeout(c.timer);channels.clear()},
  hasPending(){return [...channels.values()].some(c=>c.pending!==null||c.running||c.timer)}
 };
})();
