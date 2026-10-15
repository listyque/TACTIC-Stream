/* TACTIC Vue 0.20.0-source-fork; templates precompiled with Vue 3.5.13. See vendor/VUE_LICENSE.txt. */
(function(){
const _Vue = Vue;
const api = (function(){
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

class HttpError extends Error { constructor(status, data) { super(data.error?.message || `HTTP ${status}`); this.status=status; this.details=data.error?.details; this.requestId=data.error?.request_id; } }
return {
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

})();
const uiState=(function(){
/* Persistent UI state uses original TACTIC WidgetSettings, never localStorage.
   One in-flight write per channel. Pending changes are coalesced, not replayed
   after an ambiguous failure or a revision conflict. No record drafts go here. */
return (() => {
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

})();
const CsvImportPanel = (function(){

const __component = {
 name:'CsvImportPanel',props:['project','target','searchType'],emits:['dirty','saved'],
 data(){return {text:'',delimiter:',',mapping:[],headers:[],fields:[],preview:null,busy:false,error:'',message:'',uncertain:false}},
 computed:{dirty(){return !!this.text.trim()}},watch:{dirty(v){this.$emit('dirty',v)},text(){this.preview=null;this.uncertain=false},delimiter(){this.preview=null}},
 async mounted(){try{this.fields=(await api.request('/stype-import',this.args())).fields}catch(e){this.error=e.message}},
 methods:{args(){return {project:this.project,target:this.target,search_type:this.searchType}},async file(e){const f=e.target.files?.[0];if(!f)return;if(f.size>1048576){this.error='CSV не более 1 МиБ';return}this.text=await f.text();this.mapping=[];this.headers=[]},
 async map(){this.error='';// First header parsed with the same quote convention; server parses every row again.
 try{const line=this.text.replace(/^\uFEFF/,'').split(/\r?\n/,1)[0];let out=[],part='',quoted=false;for(let i=0;i<line.length;i++){const ch=line[i];if(ch==='"'){if(quoted&&line[i+1]==='"'){part+='"';i++}else quoted=!quoted}else if(ch===this.delimiter&&!quoted){out.push(part);part=''}else part+=ch}if(quoted)throw Error('Многострочный заголовок: упростите первую строку CSV');out.push(part);if(out.length>30)throw Error('До 30 колонок');this.headers=out;this.mapping=out.map(n=>this.fields.find(f=>f.name===n.trim())?.name||'');this.preview=null}catch(e){this.error=e.message}},
 async inspect(){if(this.busy)return;this.busy=true;this.error='';try{this.preview=await api.request('/stype-import',{...this.args(),text:this.text,delimiter:this.delimiter,mapping:this.mapping,operation:'preview'},'POST')}catch(e){this.error=e.message;this.preview=null}finally{this.busy=false}},
 async commit(){if(this.busy||!this.preview||this.uncertain)return;if(!confirm('Импортировать '+this.preview.count+' новых записей? Исходные серверные триггеры будут выполнены.'))return;this.busy=true;this.error='';const body={...this.args(),text:this.text,delimiter:this.delimiter,mapping:[...this.mapping],operation:'import',confirm:'IMPORT_NEW_ROWS',preview_revision:this.preview.preview_revision};try{const r=await api.request('/stype-import',body,'POST');this.message=r.notice;this.text='';this.preview=null;this.$emit('saved')}catch(e){this.error=e.message+' Перед повтором проверьте таблицу и журнал: ответ мог быть потерян после записи.';this.uncertain=true}finally{this.busy=false}}
 }};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, resolveComponent: _resolveComponent, createVNode: _createVNode, renderList: _renderList, Fragment: _Fragment } = _Vue

    const _component_CodeEditor = _resolveComponent("CodeEditor")

    return (_openBlock(), _createElementBlock("section", { class: "csv-import-panel" }, [
      _createElementVNode("h3", null, "Импорт новых записей · " + _toDisplayString(searchType), 1),
      _createElementVNode("p", { class: "notice" }, "Исходный CsvImportCmd. Только новые строки в существующие колонки; пробелы по краям ячеек обрезаются. Обновление по ID, новые поля, заметки и отключение триггеров здесь не включены."),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      message
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, _toDisplayString(message), 1))
        : _createCommentVNode("", true),
      _createElementVNode("fieldset", { disabled: busy||uncertain }, [
        _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("input", {
          type: "file",
          accept: ".csv,.tsv,text/csv,text/plain",
          onChange: file
        }, null, 40, ["onChange"]), _createElementVNode("label", null, [_createTextVNode("Разделитель"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((delimiter) = $event) }, [_createElementVNode("option", { value: "," }, "Запятая"), _createElementVNode("option", { value: ";" }, "Точка с запятой"), _createElementVNode("option", { value: '\t' }, "Табуляция", 8, ["value"])], 8, ["onUpdate:modelValue"]), [[_vModelSelect, delimiter]])]), _createElementVNode("button", {
          type: "button",
          onClick: map,
          disabled: !text
        }, "Сопоставить колонки", 8, ["onClick", "disabled"])]),
        _createVNode(_component_CodeEditor, {
          modelValue: text,
          "onUpdate:modelValue": $event => ((text) = $event),
          language: "text",
          label: "CSV UTF-8, до 1 МиБ / 100 строк",
          height: "180px",
          readonly: busy||uncertain
        }, null, 8, ["modelValue", "onUpdate:modelValue", "readonly"]),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(headers, (head, i) => {
          return (_openBlock(), _createElementBlock("div", {
            key: i,
            class: "column-row"
          }, [_createElementVNode("span", null, _toDisplayString(head||'Колонка '+(i+1)), 1), _withDirectives(_createElementVNode("select", {
            "onUpdate:modelValue": $event => ((mapping[i]) = $event),
            onChange: $event => (preview=null)
          }, [_createElementVNode("option", { value: "" }, "Пропустить"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
            return (_openBlock(), _createElementBlock("option", {
              key: f.name,
              value: f.name
            }, _toDisplayString(f.label) + " · " + _toDisplayString(f.name), 9, ["value"]))
          }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, mapping[i]]])]))
        }), 128)),
        (mapping.length)
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              onClick: inspect
            }, "Предпросмотр без записи", 8, ["onClick"]))
          : _createCommentVNode("", true)
      ], 8, ["disabled"]),
      preview
        ? (_openBlock(), _createElementBlock("div", {
            key: 2,
            class: "table-scroll"
          }, [_createElementVNode("p", null, _toDisplayString(preview.count) + " новых записей. Показаны значения после исходной CSV-нормализации.", 1), _createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preview.columns, (col) => {
            return (_openBlock(), _createElementBlock("th", { key: col }, _toDisplayString(col), 1))
          }), 128))])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preview.rows, (r, i) => {
            return (_openBlock(), _createElementBlock("tr", { key: i }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preview.columns, (col) => {
              return (_openBlock(), _createElementBlock("td", { key: col }, _toDisplayString(r[col]), 1))
            }), 128))]))
          }), 128))])]), _createElementVNode("button", {
            class: "primary",
            disabled: busy||uncertain,
            onClick: commit
          }, "Импортировать " + _toDisplayString(preview.count), 9, ["disabled", "onClick"])]))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const CodeEditor = (function(){
const { markRaw } = Vue;
const __component = {
 name:'CodeEditor',props:{modelValue:{type:String,default:''},language:{type:String,default:'text'},readonly:Boolean,wrap:Boolean,label:{type:String,default:'Исходный код'},height:{type:String,default:'430px'}},emits:['update:modelValue','save','cursor'],
 data(){return {editor:null,observer:null,themeObserver:null,syncing:false,error:''}},
 mounted(){try{if(!window.ace)throw Error('Локальный Ace не загружен');const a=window.ace;a.config.set('basePath','/tactic-ui/vendor/ace');a.config.set('loadWorkerFromBlob',false);this.editor=markRaw(a.edit(this.$refs.editor,{fontSize:13,showPrintMargin:false,useWorker:false,readOnly:this.readonly,wrap:this.wrap,tabSize:4}));this.editor.session.setUseWorker(false);this.editor.session.setValue(this.modelValue);this.setLanguage();this.theme();this.editor.on('change',()=>{if(!this.syncing)this.$emit('update:modelValue',this.editor.getValue())});this.editor.selection.on('changeCursor',()=>{const p=this.editor.getCursorPosition();this.$emit('cursor',{line:p.row+1,column:p.column+1})});this.editor.commands.addCommand({name:'tacticSave',bindKey:{win:'Ctrl-S',mac:'Command-S'},exec:()=>this.$emit('save')});this.observer=new ResizeObserver(()=>this.editor?.resize());this.observer.observe(this.$refs.editor);this.themeObserver=new MutationObserver(()=>this.theme());this.themeObserver.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']})}catch(e){this.error=e.message}},
 beforeUnmount(){this.observer?.disconnect();this.themeObserver?.disconnect();this.editor?.destroy();this.editor=null},
 watch:{modelValue(value){if(this.editor&&value!==this.editor.getValue()){const p=this.editor.getCursorPosition();this.syncing=true;this.editor.session.setValue(value||'');this.editor.moveCursorToPosition(p);this.syncing=false}},language(){this.setLanguage()},readonly(value){this.editor?.setReadOnly(value)},wrap(value){this.editor?.session.setUseWrapMode(value)}},
 methods:{setLanguage(){if(!this.editor)return;const lang={python:'python',javascript:'javascript',server_js:'javascript',html:'html',xml:'xml',css:'css',expression:'text',mako:'html',text:'text'}[this.language]||'text';this.editor.session.setMode('ace/mode/'+lang)},theme(){this.editor?.setTheme(document.documentElement.dataset.theme==='dark'?'ace/theme/tomorrow_night':'ace/theme/textmate')},find(text){if(text)this.editor?.find(text,{wrap:true,caseSensitive:false,regExp:false});else this.editor?.execCommand('find')},focus(){this.editor?.focus()},undo(){this.editor?.undo()},redo(){this.editor?.redo()}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { vShow: _vShow, createElementVNode: _createElementVNode, withDirectives: _withDirectives, toDisplayString: _toDisplayString, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, normalizeStyle: _normalizeStyle } = _Vue

    return (_openBlock(), _createElementBlock("div", {
      class: "native-code-editor",
      style: _normalizeStyle({height})
    }, [_withDirectives(_createElementVNode("div", {
      ref: "editor",
      "aria-label": label,
      role: "textbox",
      "aria-multiline": "true",
      class: "ace-surface"
    }, null, 8, ["aria-label"]), [[_vShow, !error]]), error
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("small", { class: "notice" }, _toDisplayString(error) + " · доступен текстовый редактор", 1), _createElementVNode("textarea", {
          value: modelValue,
          onInput: $event => ($emit('update:modelValue',$event.target.value)),
          readonly: readonly,
          "aria-label": label,
          spellcheck: "false"
        }, null, 40, ["value", "onInput", "readonly", "aria-label"])], 64))
      : _createCommentVNode("", true)], 4))
  }
};
return __component;
})();
const LayoutPreview = (function(){
const { markRaw } = Vue;
const __component = {
 name:'LayoutPreview',
 props:{parts:Object,children:{type:Array,default:()=>[]},project:String,user:Object},
 emits:['open','dirty','changed'],
 data(){return {mounts:[],warnings:[],root:null,childDirty:{}}},
 mounted(){this.root=markRaw(this.$refs.host.attachShadow({mode:'open'}));this.root.addEventListener('submit',e=>e.preventDefault());this.paint()},
 watch:{parts:{deep:true,handler(){this.paint()}},children(){this.paint()}},
 beforeUnmount(){this.mounts=[]},
 methods:{
  childChanged(key,value){this.childDirty[key]=!!value;this.$emit('dirty',Object.values(this.childDirty).some(Boolean))},
  unsafeCss(css){return /[\\@]|url\s*\(|expression|behavior|-moz-binding|image\s*\(|image-set|cross-fade|paint\s*\(|https?:|\/\/|src\s*:|<\/style/i.test(css)},
  paint(){
   if(!this.root)return;
   this.mounts=[];this.warnings=[];
   const template=document.createElement('template');
   template.innerHTML=this.parts?.html||'<p>Пустой HTML</p>';
   const tags=new Set('div span p section article main header footer aside nav h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table thead tbody tfoot tr td th caption colgroup col pre code blockquote strong em b i u s small br hr a img label input textarea select option button form fieldset legend element'.split(' '));
   const attrs=new Set(['class','id','title','style','colspan','rowspan','width','height','alt','type','value','placeholder']);
   const slots=[];
   const clean=parent=>{
    for(const el of [...parent.children]){
     const tag=el.tagName.toLowerCase();
     if(!tags.has(tag)){el.remove();continue}
     if(tag==='element'){
      const n=slots.length,info=this.children[n];
      const holder=document.createElement('section');holder.className='native-layout-widget';holder.dataset.nativeSlot=String(n);
      if(info?.hidden)holder.hidden=true;
      if(!info)holder.textContent='Вложенный виджет: '+(el.getAttribute('name')||n)+' — доступен после сохранения и открытия layout';
      slots.push(info||null);el.replaceWith(holder);continue;
     }
     for(const a of [...el.attributes]){
      const key=a.name.toLowerCase();
      if(!attrs.has(key)||(key==='style'&&this.unsafeCss(a.value)))el.removeAttribute(a.name);
     }
     if(['input','textarea','select','button'].includes(tag))el.setAttribute('disabled','');
     clean(el);
    }
   };
   clean(template.content);
   const style=document.createElement('style');
   style.textContent=':host{display:block;color:inherit;font:inherit}.native-layout-widget{margin:12px 0;min-height:70px}';
   const css=this.parts?.style||'';
   if(css){
    if(this.unsafeCss(css))this.warnings.push('CSS с внешними ресурсами, escape-последовательностями или @-правилами не применяется в ограниченном preview');
    else style.textContent+='\n'+css;
   }
   const sheet=document.createElement('link');sheet.rel='stylesheet';sheet.href='/tactic-ui/styles.css';
   this.root.replaceChildren(sheet,style,template.content);
   this.mounts=[...this.root.querySelectorAll('[data-native-slot]')].filter(el=>slots[Number(el.dataset.nativeSlot)]&&!slots[Number(el.dataset.nativeSlot)].hidden).map(el=>({el:markRaw(el),info:slots[Number(el.dataset.nativeSlot)]}));
   if(this.parts?.mako||this.parts?.behavior||this.parts?.callback||/\[expr\]|<%|\$\{/.test(this.parts?.html||''))this.warnings.push('Mako, expressions, behaviors и callbacks сохранены, но этим preview не исполняются');
  }
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, resolveComponent: _resolveComponent, createVNode: _createVNode, Teleport: _Teleport, createBlock: _createBlock } = _Vue

    const _component_WidgetHost = _resolveComponent("WidgetHost")

    return (_openBlock(), _createElementBlock("section", { class: "layout-preview" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(warnings, (w) => {
      return (_openBlock(), _createElementBlock("p", {
        key: w,
        class: "notice"
      }, _toDisplayString(w), 1))
    }), 128)), _createElementVNode("div", {
      ref: "host",
      class: "layout-preview-surface"
    }, null, 512), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(mounts, (m) => {
      return (_openBlock(), _createBlock(_Teleport, {
        key: m.info.id,
        to: m.el
      }, [_createVNode(_component_WidgetHost, {
        project: project,
        target: m.info.id,
        user: user,
        onOpen: $event => ($emit('open',$event)),
        onDirty: $event => (childChanged(m.info.id,$event)),
        onChanged: $event => ($emit('changed',$event))
      }, null, 8, ["project", "target", "user", "onOpen", "onDirty", "onChanged"])], 8, ["to"]))
    }), 128))]))
  }
};
return __component;
})();
const CustomLayoutEditor = (function(){

const __component = {
 name:'CustomLayoutEditor',props:{project:String,target:String,user:Object},emits:['dirty','open','changed'],
 data(){return {items:[],total:0,offset:0,q:'',record:null,parts:{html:'',style:'',mako:'',kwargs:'',behavior:'',callback:''},originalParts:'',xml:'',originalXml:'',section:'html',raw:false,newName:'',personal:false,busy:false,saving:false,error:'',notice:'',preview:null,seq:0,catalogSeq:0,canWrite:false}},
 computed:{dirty(){return !!this.record&&(this.raw?this.xml!==this.originalXml:JSON.stringify(this.parts)!==this.originalParts)},language(){return {html:'html',style:'css',mako:'html',kwargs:'python',behavior:'xml',callback:'xml'}[this.section]||'text'}},watch:{dirty(v){this.$emit('dirty',v)}},mounted(){this.catalog()},beforeUnmount(){this.seq++;this.catalogSeq++},
 methods:{args(){return {project:this.project,target:this.target,kind:'layout'}},accept(r){this.record=r;this.parts={...(r.parts||{html:'',style:'',mako:'',kwargs:'',behavior:'',callback:''})};this.originalParts=JSON.stringify(this.parts);this.xml=r.xml;this.originalXml=r.xml;this.raw=!r.parts;this.preview=null;this.notice=r.notice||''},
 async catalog(){const seq=++this.catalogSeq;this.error='';try{const r=await api.request('/design-catalog',{...this.args(),q:this.q,offset:this.offset,limit:100});if(seq!==this.catalogSeq)return;this.items=r.items;this.total=r.total;this.canWrite=r.can_write}catch(e){this.error=e.message}},
 async load(key){if(this.saving)return;if(this.dirty&&!confirm('Отменить несохранённые изменения layout?'))return;const seq=++this.seq;this.busy=true;this.error='';try{const r=await api.request('/layout-document',{...this.args(),key});if(seq===this.seq)this.accept(r)}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 async create(copy=false){if(this.busy||this.saving||!this.newName)return;if(this.dirty&&!confirm('Создать новую запись без сохранения текущих правок?'))return;this.saving=true;this.error='';try{const r=await api.request('/layout-document',{...this.args(),view:this.newName.replaceAll('/','.'),login:this.personal?this.user.login:null,...(copy&&this.record?{source_key:this.record.key,source_revision:this.record.revision}:{})},'POST');this.accept(r);this.newName='';await this.catalog();this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 async save(){if(this.saving||this.busy||!this.dirty||!this.canWrite)return;this.saving=true;this.error='';const original=JSON.parse(this.originalParts);const changes=Object.fromEntries(Object.entries(this.parts).filter(([k,v])=>v!==original[k]));try{api.action?.('layout.save',{project:this.project,target:this.target});const r=await api.request('/layout-document',{...this.args(),key:this.record.key,revision:this.record.revision,...(this.raw?{xml:this.xml}:{changes})},'PATCH');this.accept(r);this.notice='Сохранено в исходный widget_config. Неизменённые секции сохранены.';await this.catalog();this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 toggleRaw(){if(this.dirty){this.error='Сохраните или отмените изменения перед сменой режима';return}this.raw=!this.raw},
 showPreview(){if(this.raw){this.error='Для XML-предпросмотра сначала сохраните и откройте layout';return}api.action?.('layout.preview',{project:this.project,target:this.target});this.preview=JSON.parse(JSON.stringify(this.parts))},
 openSaved(){if(this.dirty){this.error='Сначала сохраните layout: виджеты открываются по сохранённым определениям';return}this.$emit('open',{id:this.target+'/~design/layout:'+encodeURIComponent(this.record.key)})},
 async remove(){if(this.saving||this.busy||!this.record||!confirm('Удалить выбранное локальное переопределение layout? Нижние слои могут снова стать видимыми.'))return;this.saving=true;this.error='';try{await api.request('/layout-document',{...this.args(),key:this.record.key,revision:this.record.revision,confirm:'REMOVE_OVERRIDE'},'DELETE');this.record=null;this.preview=null;await this.catalog();this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 download(){const blob=new Blob([this.xml],{type:'application/xml'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=(this.record?.view||'layout')+'.xml';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, vModelText: _vModelText, createElementVNode: _createElementVNode, withDirectives: _withDirectives, withModifiers: _withModifiers, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, vModelCheckbox: _vModelCheckbox, resolveComponent: _resolveComponent, createBlock: _createBlock, createVNode: _createVNode } = _Vue

    const _component_CodeEditor = _resolveComponent("CodeEditor")
    const _component_LayoutPreview = _resolveComponent("LayoutPreview")

    return (_openBlock(), _createElementBlock("section", {
      class: "design-workbench",
      "data-testid": "custom-layout-editor",
      "aria-label": "Custom Layout Editor"
    }, [error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error",
          role: "alert"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), notice
      ? (_openBlock(), _createElementBlock("p", {
          key: 1,
          class: "notice"
        }, _toDisplayString(notice), 1))
      : _createCommentVNode("", true), _createElementVNode("div", { class: "admin-two-pane" }, [_createElementVNode("aside", { class: "admin-catalog" }, [
      _createElementVNode("form", {
        class: "toolbar",
        onSubmit: _withModifiers($event => {offset=0;catalog()}, ["prevent"])
      }, [_withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": $event => ((q) = $event),
        type: "search",
        placeholder: "Найти layout"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, q]]), _createElementVNode("button", null, "Поиск")], 40, ["onSubmit"]),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (i) => {
        return (_openBlock(), _createElementBlock("button", {
          key: i.key,
          class: "admin-catalog-item",
          "aria-selected": record?.key===i.key,
          onClick: $event => (load(i.key))
        }, [_createElementVNode("b", null, _toDisplayString(i.view), 1), _createElementVNode("small", null, _toDisplayString(i.login||'Общий') + " · priority " + _toDisplayString(i.priority||0), 1)], 8, ["aria-selected", "onClick"]))
      }), 128)),
      _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
        disabled: offset===0,
        onClick: $event => {offset-=100;catalog()}
      }, "←", 8, ["disabled", "onClick"]), _createElementVNode("span", null, _toDisplayString(offset+items.length) + " / " + _toDisplayString(total), 1), _createElementVNode("button", {
        disabled: offset+items.length>=total,
        onClick: $event => {offset+=100;catalog()}
      }, "→", 8, ["disabled", "onClick"])]),
      _createElementVNode("div", { class: "design-new" }, [_createElementVNode("label", null, [_createTextVNode("Имя нового view"), _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": $event => ((newName) = $event),
        placeholder: "dashboard.overview"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newName]])]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
        type: "checkbox",
        "onUpdate:modelValue": $event => ((personal) = $event)
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, personal]]), _createTextVNode("Личный")]), _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
        disabled: !canWrite||!newName||saving,
        onClick: $event => (create(false))
      }, "Создать", 8, ["disabled", "onClick"]), _createElementVNode("button", {
        disabled: !canWrite||!newName||!record||saving,
        onClick: $event => (create(true))
      }, "Копировать", 8, ["disabled", "onClick"])])])
    ]), _createElementVNode("main", { class: "admin-editor-pane" }, [record
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
          _createElementVNode("div", { class: "toolbar" }, [
            _createElementVNode("code", null, _toDisplayString(record.view), 1),
            dirty
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  class: "editor-status",
                  role: "status"
                }, "● Несохранённые изменения"))
              : _createCommentVNode("", true),
            _createElementVNode("span", { class: "spacer" }),
            _createElementVNode("button", { onClick: toggleRaw }, _toDisplayString(raw?'Разделы':'Исходный XML'), 9, ["onClick"]),
            _createElementVNode("button", {
              onClick: showPreview,
              disabled: raw
            }, "Preview", 8, ["onClick", "disabled"]),
            _createElementVNode("button", { onClick: openSaved }, "Открыть layout", 8, ["onClick"]),
            _createElementVNode("button", { onClick: download }, "В файл", 8, ["onClick"]),
            _createElementVNode("button", {
              class: "primary",
              disabled: !dirty||!canWrite||saving||busy,
              onClick: save
            }, "Сохранить", 8, ["disabled", "onClick"]),
            _createElementVNode("details", { class: "design-more" }, [_createElementVNode("summary", null, "⋯"), _createElementVNode("button", {
              class: "danger",
              onClick: remove,
              disabled: !canWrite||saving
            }, "Удалить переопределение", 8, ["onClick", "disabled"])])
          ]),
          (!raw)
            ? (_openBlock(), _createElementBlock("nav", {
                key: 0,
                class: "admin-section-tabs"
              }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['html','style','mako','kwargs','behavior','callback'], (s) => {
                return (_openBlock(), _createElementBlock("button", {
                  key: s,
                  "aria-selected": section===s,
                  onClick: $event => (section=s)
                }, _toDisplayString(s==='style'?'CSS':s.toUpperCase()), 9, ["aria-selected", "onClick"]))
              }), 128))]))
            : _createCommentVNode("", true),
          raw
            ? (_openBlock(), _createBlock(_component_CodeEditor, {
                key: 1,
                modelValue: xml,
                "onUpdate:modelValue": $event => ((xml) = $event),
                language: "xml",
                label: "Исходный XML layout",
                readonly: !canWrite||saving,
                onSave: save
              }, null, 8, ["modelValue", "onUpdate:modelValue", "readonly", "onSave"]))
            : (_openBlock(), _createBlock(_component_CodeEditor, {
                key: section,
                modelValue: parts[section],
                "onUpdate:modelValue": $event => ((parts[section]) = $event),
                language: language,
                label: 'Layout '+section,
                readonly: !canWrite||saving,
                onSave: save
              }, null, 8, ["modelValue", "onUpdate:modelValue", "language", "label", "readonly", "onSave"])),
          _createElementVNode("p", { class: "muted" }, "CSS хранится в html/style. Behavior и callback — XML-блоки; код внутри CDATA. Preview не выполняет Mako/JS. Вложенные нативные виджеты доступны в сохранённом layout."),
          preview
            ? (_openBlock(), _createElementBlock("div", {
                key: 3,
                class: "design-preview-block"
              }, [_createElementVNode("h3", null, "Статический предпросмотр"), _createVNode(_component_LayoutPreview, {
                parts: preview,
                project: project,
                user: user
              }, null, 8, ["parts", "project", "user"])]))
            : _createCommentVNode("", true)
        ], 64))
      : (_openBlock(), _createElementBlock("p", {
          key: 1,
          class: "muted"
        }, "Выберите исходный Custom Layout или создайте новый."))])])]))
  }
};
return __component;
})();
const ManageViews = (function(){

const __component = {
 name:'ManageViews',props:{project:String,target:String,screen:Object,user:Object},emits:['open','dirty','changed'],
 data(){return {types:[],stype:this.screen?.search_type||'',items:[],views:[],total:0,offset:0,selected:'table',record:null,xml:'',original:'',newName:'',personal:true,busy:false,saving:false,error:'',notice:'',designer:false,showXml:false,seq:0,catalogSeq:0,disposed:false,q:''}},
 computed:{dirty(){return !!this.record&&this.xml!==this.original},choices(){return [...new Set([...this.views,...this.items.map(i=>i.view)])].filter(v=>!this.q||v.toLowerCase().includes(this.q.toLowerCase()))}},
 watch:{dirty(v){this.$emit('dirty',v)}},mounted(){this.catalog()},beforeUnmount(){this.disposed=true;this.seq++;this.catalogSeq++},
 methods:{args(){return {project:this.project,target:this.target,search_type:this.stype}},
 async catalog(){const seq=++this.catalogSeq,args=this.args();this.error='';try{const r=await api.request('/design-catalog',{...args,offset:this.offset,limit:100});if(seq!==this.catalogSeq||this.disposed||args.search_type!==this.stype)return;this.types=r.types||this.types;this.items=r.items;this.views=r.views||[];this.total=r.total;if(this.stype&&!this.record)await this.choose(this.selected)}catch(e){if(seq===this.catalogSeq)this.error=e.message}},
 async typeChanged(){if(this.dirty){this.error='Сохраните XML перед сменой типа';this.stype=this.record?.search_type||this.stype;return}this.record=null;this.offset=0;await this.catalog()},
 async choose(view,key=null){if(this.dirty&&!confirm('Отменить правки XML?'))return;const seq=++this.seq;this.busy=true;this.error='';try{const r=await api.request('/view-document',{...this.args(),view,key});if(seq===this.seq&&!this.disposed){this.selected=view;this.record={...r,search_type:this.stype};this.xml=r.xml;this.original=r.xml;this.notice=''}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 async create(copy){if(!this.newName||this.saving||this.busy)return;if(this.dirty&&!confirm('Создать новую запись без сохранения текущего XML-черновика?'))return;this.saving=true;this.error='';try{const source=copy&&this.record?(this.record.key?{source_key:this.record.key,source_revision:this.record.revision}:{source_view:this.record.view,source_revision:this.record.revision}):{};const r=await api.request('/view-document',{...this.args(),view:this.newName,login:this.personal?this.user.login:null,...source},'POST');this.record=null;this.selected=r.view;this.newName='';await this.catalog();await this.choose(r.view,r.key);this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 async save(){if(this.saving||this.busy||!this.dirty)return;this.saving=true;this.error='';try{const r=await api.request('/view-document',{...this.args(),view:this.record.view,key:this.record.key,revision:this.record.revision,xml:this.xml,login:this.personal?this.user.login:null,expected_source_revision:this.record.inherited?this.record.revision:undefined},this.record.key?'PATCH':'POST');this.record={...r,search_type:this.stype};this.original=this.xml=r.xml;this.notice='View сохранён. Другие views и definitions не удалены.';await this.catalog();this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 async remove(){if(this.saving||this.busy||!this.record?.key||!confirm('Удалить только это переопределение? Исходное унаследованное представление останется.'))return;this.saving=true;this.error='';try{await api.request('/view-document',{...this.args(),key:this.record.key,revision:this.record.revision,confirm:'REMOVE_OVERRIDE'},'DELETE');this.record=null;await this.catalog();this.$emit('changed')}catch(e){this.error=e.message}finally{this.saving=false}},
 design(){if(this.dirty){this.error='Сначала сохраните XML';return}this.designer=true},
 async designSaved(){this.designer=false;this.record=null;await this.catalog();this.$emit('changed')},
 preview(){if(this.dirty){this.error='Сначала сохраните изменения';return}this.$emit('open',{id:this.target+'/~design/view:'+encodeURIComponent(JSON.stringify([this.stype,this.selected]))})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, createCommentVNode: _createCommentVNode, vModelText: _vModelText, vModelCheckbox: _vModelCheckbox, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_CodeEditor = _resolveComponent("CodeEditor")
    const _component_ViewDesigner = _resolveComponent("ViewDesigner")

    return (_openBlock(), _createElementBlock("section", {
      class: "design-workbench",
      "data-testid": "manage-views",
      "aria-label": "Manage Views"
    }, [
      _createElementVNode("header", {
        class: "widget-toolbar",
        role: "group",
        "aria-label": "Выбор SearchType"
      }, [_createElementVNode("label", null, [_createTextVNode("SearchType"), _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((stype) = $event),
        onChange: typeChanged,
        disabled: dirty||saving||busy
      }, [_createElementVNode("option", { value: "" }, "Выберите тип…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(types, (t) => {
        return (_openBlock(), _createElementBlock("option", {
          key: t.code,
          value: t.code
        }, _toDisplayString(t.name) + " · " + _toDisplayString(t.code), 9, ["value"]))
      }), 128))], 40, ["onUpdate:modelValue", "onChange", "disabled"]), [[_vModelSelect, stype]])])]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            role: "alert",
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "admin-two-pane" }, [_createElementVNode("aside", { class: "admin-catalog" }, [
        _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((q) = $event),
          type: "search",
          placeholder: "Имя view…"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, q]]),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(choices, (v) => {
          return (_openBlock(), _createElementBlock("div", { key: v }, [_createElementVNode("button", {
            class: "admin-catalog-item",
            "aria-selected": selected===v,
            onClick: $event => (choose(v)),
            disabled: saving
          }, [_createElementVNode("b", null, _toDisplayString(v), 1), _createElementVNode("small", null, "Разрешённое представление")], 8, ["aria-selected", "onClick", "disabled"]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items.filter(x=>x.view===v), (i) => {
            return (_openBlock(), _createElementBlock("button", {
              key: i.key,
              class: "design-layer-choice",
              "data-key": i.key,
              "aria-pressed": record?.key===i.key,
              onClick: $event => (choose(v,i.key)),
              disabled: saving
            }, _toDisplayString(i.login||'Общий override') + " · " + _toDisplayString(i.priority||0), 9, ["data-key", "aria-pressed", "onClick", "disabled"]))
          }), 128))]))
        }), 128)),
        _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
          disabled: offset===0,
          onClick: $event => {offset-=100;catalog()}
        }, "←", 8, ["disabled", "onClick"]), _createElementVNode("small", null, "DB " + _toDisplayString(offset+items.length) + " / " + _toDisplayString(total), 1), _createElementVNode("button", {
          disabled: offset+items.length>=total,
          onClick: $event => {offset+=100;catalog()}
        }, "→", 8, ["disabled", "onClick"])]),
        _createElementVNode("div", { class: "design-new" }, [_createElementVNode("label", null, [_createTextVNode("Новый view"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((newName) = $event),
          placeholder: "my_view"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newName]])]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
          type: "checkbox",
          "onUpdate:modelValue": $event => ((personal) = $event)
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, personal]]), _createTextVNode("Личное переопределение")]), _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
          disabled: !stype||!newName||!user?.allow_writes||saving,
          onClick: $event => (create(false))
        }, "Создать", 8, ["disabled", "onClick"]), _createElementVNode("button", {
          disabled: !record||!newName||!user?.allow_writes||saving,
          onClick: $event => (create(true))
        }, "Копировать", 8, ["disabled", "onClick"])])])
      ]), _createElementVNode("main", { class: "admin-editor-pane" }, [record
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
            _createElementVNode("div", { class: "toolbar" }, [
              _createElementVNode("code", null, _toDisplayString(stype) + " / " + _toDisplayString(selected), 1),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", { onClick: preview }, "Открыть", 8, ["onClick"]),
              _createElementVNode("button", { onClick: design }, "Элементы и определения", 8, ["onClick"]),
              _createElementVNode("button", { onClick: $event => (showXml=!showXml) }, "XML", 8, ["onClick"]),
              _createElementVNode("button", {
                class: "primary",
                disabled: !dirty||!record.can_write||saving,
                onClick: save
              }, "Сохранить XML", 8, ["disabled", "onClick"])
            ]),
            _createElementVNode("p", { class: "notice" }, _toDisplayString(record.inherited?'Показан снимок разрешённых параметров. При записи будет создано выбранное локальное переопределение.':'Выбрана конкретная запись БД. Изменение затрагивает только этот view.'), 1),
            (showXml||record.key)
              ? (_openBlock(), _createBlock(_component_CodeEditor, {
                  key: 0,
                  modelValue: xml,
                  "onUpdate:modelValue": $event => ((xml) = $event),
                  language: "xml",
                  label: "XML представления",
                  readonly: !record.can_write||saving,
                  onSave: save
                }, null, 8, ["modelValue", "onUpdate:modelValue", "readonly", "onSave"]))
              : (_openBlock(), _createElementBlock("div", {
                  key: 1,
                  class: "table-scroll"
                }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Элемент"), _createElementVNode("th", null, "Display handler"), _createElementVNode("th", null, "Edit handler")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record.elements, (e, i) => {
                  return (_openBlock(), _createElementBlock("tr", { key: i }, [_createElementVNode("td", null, [_createTextVNode(_toDisplayString(e.title), 1), _createElementVNode("small", null, _toDisplayString(e.name), 1)]), _createElementVNode("td", null, [_createElementVNode("code", null, _toDisplayString(e.handler||'Наследовать'), 1)]), _createElementVNode("td", null, [_createElementVNode("code", null, _toDisplayString(e.edit_handler||'Наследовать'), 1)])]))
                }), 128))])])])),
            (record.layers)
              ? (_openBlock(), _createElementBlock("details", { key: 2 }, [_createElementVNode("summary", null, "Слои наследования"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(record.layers,null,2)), 1)]))
              : _createCommentVNode("", true),
            (record.key)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 3,
                  class: "danger subtle",
                  disabled: !record.can_write||saving,
                  onClick: remove
                }, "Удалить только этот override", 8, ["disabled", "onClick"]))
              : _createCommentVNode("", true)
          ], 64))
        : (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "muted"
          }, "Выберите SearchType и представление. Именованные views остаются частью оригинального widget_config."))])]),
      designer
        ? (_openBlock(), _createBlock(_component_ViewDesigner, {
            key: 2,
            project: project,
            "search-type": stype,
            "initial-view": selected,
            login: user?.login,
            onClose: $event => (designer=false),
            onSaved: designSaved
          }, null, 8, ["project", "search-type", "initial-view", "login", "onClose", "onSaved"]))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const ContextMenu = (function(){

const __component = {
 name:'ContextMenu',props:{menu:Object},emits:['action','close'],
 data(){return {left:0,top:0,trail:[],focusIndex:-1,origin:null,restoreFocus:true}},
 computed:{items(){let items=this.menu?.items||[];for(const i of this.trail)items=items[i]?.children||[];return items}},
 watch:{menu:{deep:true,handler(){this.trail=[];this.position()}},items(){this.position()}},
 mounted(){api.action?.('menu.open',{control:this.menu?.scope||'menu'});this.origin=document.activeElement;this.outside=e=>{if(this.menu?.anchor&&this.origin?.contains(e.target))return;if(!this.$refs.panel?.contains(e.target)){this.restoreFocus=false;this.$emit('close')}};this.resize=()=>this.$emit('close');document.addEventListener('pointerdown',this.outside,true);window.addEventListener('resize',this.resize);this.position()},
 beforeUnmount(){document.removeEventListener('pointerdown',this.outside,true);window.removeEventListener('resize',this.resize);if(this.restoreFocus&&this.origin?.isConnected)this.origin.focus({preventScroll:true})},
 methods:{
  position(){this.left=Math.max(4,this.menu?.x||0);this.top=Math.max(4,this.menu?.y||0);this.$nextTick(()=>{
   const box=this.$refs.panel?.getBoundingClientRect(),anchor=this.menu?.anchor;
   if(box){if(anchor){this.left=this.menu.align==='end'?anchor.right-box.width:anchor.left;this.top=anchor.bottom+6;if(this.top+box.height>innerHeight-8&&anchor.top-box.height-6>=8)this.top=anchor.top-box.height-6}
    this.left=Math.max(8,Math.min(this.left,innerWidth-box.width-8));this.top=Math.max(8,Math.min(this.top,innerHeight-box.height-8))}this.focusFirst()})},
  buttons(){return Array.from(this.$refs.panel?.querySelectorAll('[role="menuitem"],[role="menuitemradio"],[role="menuitemcheckbox"]')||[])},
  focusFirst(){const b=this.buttons();this.focusIndex=0;(b[0]||this.$refs.panel)?.focus({preventScroll:true})},
  choose(item,index){if(item.enabled===false)return;api.action?.('menu.select',{control:String(item.id||'submenu')});if(item.children){this.trail.push(index);return}this.$emit('action',item)},
  key(event){const b=this.buttons();const keys=['ArrowDown','ArrowUp','Home','End','Escape','ArrowLeft','ArrowRight','Tab'];if(!keys.includes(event.key))return;if(event.key==='Tab'){this.restoreFocus=false;this.$emit('close');return}event.preventDefault();event.stopPropagation();if(event.key==='Escape'){this.$emit('close');return}if(event.key==='ArrowLeft'){if(this.trail.length)this.trail.pop();return}if(event.key==='ArrowRight'){const focused=document.activeElement;if(focused?.getAttribute('aria-haspopup')==='menu')focused.click();return}if(!b.length)return;const at=b.indexOf(document.activeElement);this.focusIndex=event.key==='Home'?0:event.key==='End'?b.length-1:event.key==='ArrowDown'?(at+1)%b.length:(at-1+b.length)%b.length;b[this.focusIndex]?.focus({preventScroll:true})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, createElementVNode: _createElementVNode, normalizeClass: _normalizeClass, withModifiers: _withModifiers, normalizeStyle: _normalizeStyle, Teleport: _Teleport, createBlock: _createBlock } = _Vue

    return (_openBlock(), _createBlock(_Teleport, { to: "body" }, [_createElementVNode("section", {
      ref: "panel",
      class: _normalizeClass(["context-menu native-menu", menu.variant||'']),
      role: "menu",
      tabindex: "-1",
      "aria-label": menu.title||'Контекстное меню TACTIC',
      style: _normalizeStyle({left:left+'px',top:top+'px'}),
      onKeydown: key,
      onContextmenu: _withModifiers(() => {}, ["prevent"]),
      onClick: _withModifiers(() => {}, ["stop"])
    }, [
      (menu.title)
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "menu-heading"
          }, _toDisplayString(menu.title), 1))
        : _createCommentVNode("", true),
      (trail.length)
        ? (_openBlock(), _createElementBlock("button", {
            key: 1,
            role: "menuitem",
            onClick: $event => (trail.pop())
          }, "← Назад", 8, ["onClick"]))
        : _createCommentVNode("", true),
      (menu.loading)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "Загрузка действий…"))
        : _createCommentVNode("", true),
      (menu.error)
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "error"
          }, _toDisplayString(menu.error), 1))
        : _createCommentVNode("", true),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (item, index) => {
        return (_openBlock(), _createElementBlock(_Fragment, { key: item.id||index }, [(item.type==='separator')
          ? (_openBlock(), _createElementBlock("hr", {
              key: 0,
              role: "separator"
            }))
          : (item.type==='title')
            ? (_openBlock(), _createElementBlock("div", {
                key: 1,
                class: "menu-heading"
              }, _toDisplayString(item.label), 1))
            : (_openBlock(), _createElementBlock("button", {
                key: 2,
                role: item.role==='radio'?'menuitemradio':item.role==='checkbox'?'menuitemcheckbox':'menuitem',
                "aria-checked": item.role?Boolean(item.checked):undefined,
                tabindex: "-1",
                "aria-disabled": item.enabled===false,
                "aria-haspopup": item.children?'menu':undefined,
                class: _normalizeClass({unavailable:item.enabled===false,checked:item.checked===true}),
                title: item.reason||item.legacy_label||'',
                "data-action": item.id,
                onClick: $event => (choose(item,index))
              }, [
                _createElementVNode("span", { class: "menu-label" }, [(item.role)
                  ? (_openBlock(), _createElementBlock("span", {
                      key: 0,
                      class: "menu-check",
                      "aria-hidden": "true"
                    }, _toDisplayString(item.checked?'✓':''), 1))
                  : _createCommentVNode("", true), _createTextVNode(_toDisplayString(item.label), 1)]),
                (item.shortcut)
                  ? (_openBlock(), _createElementBlock("kbd", { key: 0 }, _toDisplayString(item.shortcut), 1))
                  : _createCommentVNode("", true),
                (item.children)
                  ? (_openBlock(), _createElementBlock("span", {
                      key: 1,
                      "aria-hidden": "true"
                    }, "›"))
                  : _createCommentVNode("", true),
                (item.enabled===false&&item.reason)
                  ? (_openBlock(), _createElementBlock("small", { key: 2 }, _toDisplayString(item.reason), 1))
                  : _createCommentVNode("", true)
              ], 10, ["role", "aria-checked", "aria-disabled", "aria-haspopup", "title", "data-action", "onClick"]))], 64))
      }), 128)),
      (menu.source)
        ? (_openBlock(), _createElementBlock("small", {
            key: 4,
            class: "menu-source"
          }, _toDisplayString(menu.source), 1))
        : _createCommentVNode("", true)
    ], 46, ["aria-label", "onKeydown", "onContextmenu", "onClick"])]))
  }
};
return __component;
})();
const TableToolbar = (function(){

// Presentation of the existing table commands. No new query/save implementation.
// Source: BaseTableLayoutWdg shelf + DgTableGearMenuWdg File/Edit/View groups.
const __component = {
 name:'TableToolbar', components:{ContextMenu},
 props:{spec:Object,total:Number,selectedCount:{type:Number,default:0},busy:Boolean,
  allowWrites:Boolean,searchOpen:Boolean,filterCount:{type:Number,default:0},
  presentation:{type:String,default:'data'},displayMode:String,recordState:String,
  density:String,wrap:Boolean,groupField:String,dirty:Boolean,saving:Boolean},
 emits:['action'],
 data(){return {menu:null,opened:''}},
 computed:{
  flags(){return Object.assign({show_shelf:true,show_gear:true,show_refresh:true,show_insert:true,
   show_search:true,show_keyword_search:true,show_column_manager:true,show_layout_switcher:true},this.spec.table_options||{})},
  viewLabel(){return this.presentation==='data'?(this.displayMode==='cards'?'Карточки':'Таблица'):
   ({tree:'Дерево связей',timeline:'Gantt / календарь',collections:'Коллекции'})[this.presentation]||'Вид'},
  canSearch(){return this.flags.show_search||this.flags.show_keyword_search},
  canCreate(){return this.flags.show_insert&&Boolean(this.spec.capabilities?.create)},
  hasTimeline(){return this.spec.fields.some(f=>f.renderer==='gantt'||['date','datetime'].includes(f.kind))},
  viewItems(){
   const items=[];
   if(this.flags.show_layout_switcher){
    items.push({type:'title',label:'Представление'});
    for(const [value,label] of [['table','Таблица'],['cards','Карточки'],['tree','Дерево связей'],['timeline','Gantt / календарь'],['collections','Коллекции']]){
     if(value==='timeline'&&!this.hasTimeline||value==='collections'&&!this.spec.collection_supported)continue;
     items.push({id:'layout-'+value,label,value,command:'layout',role:'radio',checked:
      value==='table'||value==='cards'?this.presentation==='data'&&this.displayMode===value:this.presentation===value});
    }
   }
   if(this.flags.show_column_manager){
    items.push({type:'separator'},this.action('columns','Колонки…',true));
   }
   items.push({type:'separator'},{id:'density',label:'Плотность',children:[
    ['compact','Компактная'],['comfortable','Обычная'],['spacious','Свободная']
   ].map(([value,label])=>({id:'density-'+value,label,value,command:'density',role:'radio',checked:this.density===value}))},
    {id:'wrap',label:'Перенос текста',role:'checkbox',checked:this.wrap},
    {id:'group',label:'Группировка страницы',children:[{id:'group-none',label:'Без группировки',command:'group',value:'',role:'radio',checked:!this.groupField},
     ...this.spec.fields.filter(f=>f.storage).map(f=>({id:'group-'+f.name,label:f.label,command:'group',value:f.name,role:'radio',checked:this.groupField===f.name}))]},
    this.action('reset-geometry','Сбросить геометрию'));
   // Geometry still belongs to the live grid when an alternate view is open.
   return items;
  },
  selectionItems(){return [
   this.action('bulk','Изменить выбранные…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,
    this.selectedCount>100?'Не более 100 записей за операцию':!this.spec.capabilities?.update?'Редактирование недоступно для этого представления':'Выберите записи'),
   this.action('fill-selected','Заполнить выбранные ячейки…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,'Нужны 1–100 выбранных строк с доступным редактором'),
   this.action('export','Экспорт выбранных…',!this.busy),
   {type:'separator'},this.action('clear-selection','Снять выделение')
  ]},
  gearItems(){
   const file=[this.action('export','Экспорт CSV…',!this.busy)];
   const edit=[];
   if(this.canCreate)edit.push(this.action('create','Новая запись…',!this.busy));
   edit.push(this.action('bulk','Изменить выбранные…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,
    this.selectedCount>100?'Не более 100 записей':!this.spec.capabilities?.update?'Запись отключена':'Сначала выберите записи'));
   edit.push(this.action('fill-selected','Заполнить выбранные ячейки…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,'Сначала выберите до 100 строк'));
   if(this.dirty)edit.push({type:'separator'},{...this.action('save','Сохранить изменения',!this.saving),shortcut:'Ctrl S'},this.action('discard','Отменить несохранённые правки',!this.saving));
   const view=[this.action('save-view','Сохранить поиск в sidebar…',this.allowWrites,'Запись отключена')];
   if(this.flags.show_column_manager)view.push(this.action('designer','Настроить представление…'));
   view.push({type:'separator'},{id:'record-state',label:'Состояние записей',children:
    [['active','Активные'],['retired','Архив'],['all','Все записи']].map(([value,label])=>({id:'state-'+value,label,command:'state',value,role:'radio',checked:(this.recordState||'active')===value}))});
   const config=[this.action('audit','Источник колонок'),this.action('diagnostics','Ограничения виджетов'+(this.spec.diagnostics?.length?' · '+this.spec.diagnostics.length:''))];
   return [{id:'file',label:'Файл',legacy_label:'File',children:file},
    {id:'edit',label:'Правка',legacy_label:'Edit',children:edit},
    {id:'view',label:'Представление',legacy_label:'View',children:view},
    {type:'separator'},{id:'configuration',label:'Конфигурация',children:config}];
  }
 },
 watch:{spec(){this.close()},presentation(){this.close()}},
 methods:{
  action(id,label,enabled=true,reason=''){return {id,label,enabled,reason:enabled?'':reason}},
  toggle(event,kind){
   if(this.opened===kind){this.close();return}
   const rect=event.currentTarget.getBoundingClientRect();event.currentTarget.focus({preventScroll:true});
   this.opened=kind;
   this.menu={title:kind==='view'?'Вид таблицы':kind==='selection'?'Выбрано: '+this.selectedCount:'Меню таблицы',
    x:rect.right,y:rect.bottom+6,anchor:{left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom},align:'end',variant:'table-command-menu',
    items:kind==='view'?this.viewItems:kind==='selection'?this.selectionItems:this.gearItems};
  },
  keyboard(event,kind){if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();if(this.opened!==kind)this.toggle(event,kind)}},
  choose(item){this.close();this.$emit('action',{id:item.command||item.id,value:item.value})},
  close(){this.menu=null;this.opened=''},
  send(id){this.close();this.$emit('action',{id})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, normalizeClass: _normalizeClass, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_ContextMenu = _resolveComponent("ContextMenu")

    return (flags.show_shelf)
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "table-commandbar",
          role: "toolbar",
          "aria-label": "Инструменты таблицы"
        }, [
          canCreate
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                class: "primary table-create",
                disabled: busy,
                onClick: $event => (send('create')),
                title: "Открыть исходную форму добавления"
              }, [_createElementVNode("span", { "aria-hidden": "true" }, "＋"), _createElementVNode("span", null, "Новая запись")], 8, ["disabled", "onClick"]))
            : _createCommentVNode("", true),
          (flags.show_refresh)
            ? (_openBlock(), _createElementBlock("button", {
                key: 1,
                class: "table-icon-button",
                disabled: busy,
                "aria-label": "Обновить",
                title: "Обновить данные",
                onClick: $event => (send('refresh'))
              }, [(_openBlock(), _createElementBlock("svg", {
                viewBox: "0 0 24 24",
                "aria-hidden": "true"
              }, [_createElementVNode("path", { d: "M20 7v5h-5M4 17v-5h5M5.6 7a8 8 0 0 1 13.3-1L20 8M4 16l1.1 2a8 8 0 0 0 13.3-1" })]))], 8, ["disabled", "onClick"]))
            : _createCommentVNode("", true),
          canSearch
            ? (_openBlock(), _createElementBlock("button", {
                key: 2,
                class: _normalizeClass(["table-menu-button", {active:searchOpen||filterCount}]),
                "aria-expanded": searchOpen,
                onClick: $event => (send('search'))
              }, [(_openBlock(), _createElementBlock("svg", {
                viewBox: "0 0 24 24",
                "aria-hidden": "true"
              }, [_createElementVNode("path", { d: "M4 5h16M7 12h10M10 19h4" }), _createElementVNode("circle", {
                cx: "9",
                cy: "5",
                r: "2"
              }), _createElementVNode("circle", {
                cx: "15",
                cy: "12",
                r: "2"
              })])), _createElementVNode("span", null, "Поиск"), filterCount
                ? (_openBlock(), _createElementBlock("span", {
                    key: 0,
                    class: "counter"
                  }, _toDisplayString(filterCount), 1))
                : _createCommentVNode("", true)], 10, ["aria-expanded", "onClick"]))
            : _createCommentVNode("", true),
          selectedCount
            ? (_openBlock(), _createElementBlock("button", {
                key: 3,
                class: "table-menu-button table-selection-menu",
                "aria-haspopup": "menu",
                "aria-expanded": opened==='selection',
                "aria-label": "Действия с выбранными записями",
                onClick: $event => (toggle($event,'selection')),
                onKeydown: $event => (keyboard($event,'selection'))
              }, [_createElementVNode("span", null, _toDisplayString(selectedCount) + " выбрано", 1), _createElementVNode("span", { "aria-hidden": "true" }, "⌄")], 40, ["aria-expanded", "onClick", "onKeydown"]))
            : _createCommentVNode("", true),
          _createElementVNode("span", { class: "spacer" }),
          _createElementVNode("span", {
            class: "table-result-count",
            "aria-live": "polite"
          }, _toDisplayString(total===null||total===undefined?'—':total) + " записей", 1),
          (flags.show_layout_switcher||flags.show_column_manager)
            ? (_openBlock(), _createElementBlock("button", {
                key: 4,
                class: "table-menu-button table-view-menu",
                "aria-label": "Вид таблицы",
                "aria-haspopup": "menu",
                "aria-expanded": opened==='view',
                onClick: $event => (toggle($event,'view')),
                onKeydown: $event => (keyboard($event,'view'))
              }, [(_openBlock(), _createElementBlock("svg", {
                viewBox: "0 0 24 24",
                "aria-hidden": "true"
              }, [_createElementVNode("rect", {
                x: "4",
                y: "4",
                width: "16",
                height: "16",
                rx: "2"
              }), _createElementVNode("path", { d: "M4 9h16M10 9v11" })])), _createElementVNode("span", null, _toDisplayString(viewLabel), 1), _createElementVNode("span", { "aria-hidden": "true" }, "⌄")], 40, ["aria-expanded", "onClick", "onKeydown"]))
            : _createCommentVNode("", true),
          (flags.show_gear)
            ? (_openBlock(), _createElementBlock("button", {
                key: 5,
                class: _normalizeClass(["table-icon-button table-gear-menu", {active:opened==='gear'}]),
                "aria-label": "Меню таблицы",
                title: "Файл, правка, представление и конфигурация",
                "aria-haspopup": "menu",
                "aria-expanded": opened==='gear',
                onClick: $event => (toggle($event,'gear')),
                onKeydown: $event => (keyboard($event,'gear'))
              }, [(_openBlock(), _createElementBlock("svg", {
                viewBox: "0 0 24 24",
                "aria-hidden": "true"
              }, [_createElementVNode("path", { d: "m10 3-.6 2-2 .8-1.8-1-2 3.4L5 9.7v2.6L3.6 14l2 3.4 1.8-.9 2 .8.6 2.1h4l.6-2.1 2-.8 1.8.9 2-3.4-1.4-1.7V9.7l1.4-1.5-2-3.4-1.8 1-2-.8L14 3Z" }), _createElementVNode("circle", {
                cx: "12",
                cy: "11.2",
                r: "3"
              })]))], 42, ["aria-expanded", "onClick", "onKeydown"]))
            : _createCommentVNode("", true),
          menu
            ? (_openBlock(), _createBlock(_component_ContextMenu, {
                key: opened,
                menu: menu,
                onAction: choose,
                onClose: close
              }, null, 8, ["menu", "onAction", "onClose"]))
            : _createCommentVNode("", true)
        ]))
      : _createCommentVNode("", true)
  }
};
return __component;
})();
const TableColumns = (function(){
// Column visibility and pinning are local view preferences, NOT a DB schema edit.
const __component = {
 name:'TableColumns',props:{fields:Array,hidden:Array,pinned:Array},emits:['close','toggle','pin','reset'],
 data(){return {search:'',origin:null}},
 computed:{filtered(){const needle=this.search.trim().toLocaleLowerCase();return this.fields.filter(f=>!needle||(f.label+' '+f.name).toLocaleLowerCase().includes(needle))}},
 mounted(){this.origin=document.activeElement;this.$refs.dialog.showModal();this.$refs.search.focus()},
 beforeUnmount(){this.$refs.dialog?.close();if(this.origin?.isConnected)this.origin.focus({preventScroll:true})},
 methods:{backdrop(e){if(e.target!==this.$refs.dialog)return;const r=this.$refs.dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.$emit('close')}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, vModelText: _vModelText, withDirectives: _withDirectives, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, createTextVNode: _createTextVNode, normalizeClass: _normalizeClass, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers, Teleport: _Teleport, createBlock: _createBlock } = _Vue

    return (_openBlock(), _createBlock(_Teleport, { to: "body" }, [_createElementVNode("dialog", {
      ref: "dialog",
      class: "table-columns-dialog",
      "aria-label": "Колонки таблицы",
      onCancel: _withModifiers($event => ($emit('close')), ["prevent"]),
      onClick: backdrop
    }, [
      _createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("h2", null, "Колонки таблицы"), _createElementVNode("small", null, _toDisplayString(fields.length-hidden.length) + " из " + _toDisplayString(fields.length) + " показано", 1)]), _createElementVNode("button", {
        "aria-label": "Закрыть выбор колонок",
        onClick: $event => ($emit('close'))
      }, "×", 8, ["onClick"])]),
      _withDirectives(_createElementVNode("input", {
        ref: "search",
        "onUpdate:modelValue": $event => ((search) = $event),
        class: "column-search",
        placeholder: "Найти колонку…",
        "aria-label": "Найти колонку"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, search]]),
      _createElementVNode("div", { class: "table-column-list" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(filtered, (f) => {
        return (_openBlock(), _createElementBlock("div", {
          key: f.name,
          class: "table-column-option"
        }, [_createElementVNode("label", null, [_createElementVNode("input", {
          type: "checkbox",
          checked: !hidden.includes(f.name),
          onChange: $event => ($emit('toggle',f.name))
        }, null, 40, ["checked", "onChange"]), _createElementVNode("span", null, [_createTextVNode(_toDisplayString(f.label), 1), _createElementVNode("small", null, _toDisplayString(f.name), 1)])]), _createElementVNode("button", {
          class: _normalizeClass(["column-pin", {active:pinned.includes(f.name)}]),
          "aria-pressed": pinned.includes(f.name),
          "aria-label": 'Закрепить '+f.label,
          onClick: $event => ($emit('pin',f))
        }, [(_openBlock(), _createElementBlock("svg", {
          viewBox: "0 0 24 24",
          "aria-hidden": "true"
        }, [_createElementVNode("path", { d: "M8 3h8l-1 6 3 3v2H6v-2l3-3Z M12 14v7" })]))], 10, ["aria-pressed", "aria-label", "onClick"])]))
      }), 128)), (!filtered.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "muted"
          }, "Колонки не найдены."))
        : _createCommentVNode("", true)]),
      _createElementVNode("footer", null, [_createElementVNode("small", null, [_createTextVNode("Видимость и геометрия — в этом браузере."), _createElementVNode("br"), _createTextVNode("Определения — в widget_config.")]), _createElementVNode("button", { onClick: $event => ($emit('reset')) }, "Сбросить геометрию", 8, ["onClick"])])
    ], 40, ["onCancel", "onClick"])]))
  }
};
return __component;
})();
const WidgetDefinition = (function(){

const __component = {name:'WidgetDefinition',props:{project:String,target:String,field:String,formField:Boolean,recordKey:String},emits:['close'],data(){return {data:null,error:''}},async mounted(){try{this.data=await api.request('/open',{project:this.project,target:this.target});if(this.field){const form=this.formField?await api.request('/form',{project:this.project,target:this.target,key:this.recordKey}):null;const spec=form?.spec||this.data.spec;const f=spec?.fields?.find(f=>f.name===this.field);this.data={target:this.target,field:f||this.field,widget:this.formField?'EditWdg':this.data.handler,view:spec?.view||this.data.view}}}catch(e){this.error=e.message}}};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers, Teleport: _Teleport, createBlock: _createBlock } = _Vue

    return (_openBlock(), _createBlock(_Teleport, { to: "body" }, [_createElementVNode("div", {
      class: "modal-backdrop",
      onClick: _withModifiers($event => ($emit('close')), ["self"])
    }, [_createElementVNode("section", {
      class: "modal widget-definition",
      role: "dialog",
      "aria-modal": "true",
      "aria-label": "Определение виджета"
    }, [_createElementVNode("header", null, [_createElementVNode("h2", null, "Определение виджета"), _createElementVNode("button", {
      onClick: $event => ($emit('close')),
      "aria-label": "Закрыть"
    }, "×", 8, ["onClick"])]), _createElementVNode("p", { class: "notice" }, "Описание прочитано из исходной конфигурации. Неперенесённые обработчики не исполняются как HTML/JavaScript."), error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error"
        }, _toDisplayString(error), 1))
      : (_openBlock(), _createElementBlock("pre", { key: 1 }, _toDisplayString(data?JSON.stringify(data,null,2):'Загрузка…'), 1))])], 8, ["onClick"])]))
  }
};
return __component;
})();
const SidebarNode = (function(){
const __component = {
 name:'SidebarNode', props:{node:Object,selected:String,folders:{type:Object,default:()=>({})}}, emits:['open','context','folder'],
 computed:{expanded(){return Object.hasOwn(this.folders,this.node.id)?this.folders[this.node.id]:this.node.open===true},isFolder(){return this.node.kind==='folder'}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, normalizeClass: _normalizeClass, renderList: _renderList, Fragment: _Fragment, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_SidebarNode = _resolveComponent("SidebarNode")

    return (node.kind==='separator')
      ? (_openBlock(), _createElementBlock("li", {
          key: 0,
          class: "nav-separator",
          role: "separator"
        }))
      : (node.kind==='title')
        ? (_openBlock(), _createElementBlock("li", {
            key: 1,
            class: "nav-caption"
          }, _toDisplayString(node.title), 1))
        : (node.kind==='diagnostic')
          ? (_openBlock(), _createElementBlock("li", {
              key: 2,
              class: "nav-warning"
            }, _toDisplayString(node.title), 1))
          : (_openBlock(), _createElementBlock("li", { key: 3 }, [_createElementVNode("button", {
              class: _normalizeClass(["nav-item", {active:selected===node.id,folder:isFolder}]),
              title: node.name,
              "aria-expanded": isFolder?expanded:undefined,
              onClick: $event => (isFolder?$emit('folder',{id:node.id,open:!expanded}):$emit('open',node)),
              onContextmenu: $event => (!isFolder&&$emit('context',{event:$event,node})),
              onKeydown: $event => (($event.key==='ContextMenu'||($event.shiftKey&&$event.key==='F10'))&&!isFolder&&$emit('context',{event:$event,node,keyboard:true}))
            }, [_createElementVNode("span", { class: "nav-symbol" }, _toDisplayString(isFolder?(expanded?'▾':'▸'):'◫'), 1), _createElementVNode("span", null, _toDisplayString(node.title), 1), (!isFolder&&node.renderer==='unsupported')
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  class: "not-ported",
                  title: "Обработчик ещё не перенесён"
                }, "·"))
              : _createCommentVNode("", true)], 42, ["title", "aria-expanded", "onClick", "onContextmenu", "onKeydown"]), (isFolder&&expanded)
              ? (_openBlock(), _createElementBlock("ul", {
                  key: 0,
                  class: "nav-children"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(node.children, (child) => {
                  return (_openBlock(), _createBlock(_component_SidebarNode, {
                    key: child.id,
                    node: child,
                    selected: selected,
                    folders: folders,
                    onFolder: $event => ($emit('folder',$event)),
                    onOpen: $event => ($emit('open',$event)),
                    onContext: $event => ($emit('context',$event))
                  }, null, 8, ["node", "selected", "folders", "onFolder", "onOpen", "onContext"]))
                }), 128))]))
              : _createCommentVNode("", true)]))
  }
};
return __component;
})();
const WidgetCell = (function(){
const __component = {
 name:'WidgetCell',props:{row:Object,field:Object,fallback:String},emits:['open'],
 computed:{
  cell(){return this.row?.cells?.[this.field.name]},
  text(){return this.cell?this.cell.text:this.fallback},
  initials(){return String(this.cell?.empty?'':this.text||'').trim().split(/\s+/).slice(0,2).map(s=>s[0]||'').join('').toUpperCase()},
  css(){return {'cell-error':this.cell?.kind==='error','cell-negative':this.cell?.negative,'cell-single-line':this.field.single_line}},
  safeColor(){const value=String(this.cell?.color||'');return /^(#[0-9a-f]{3,8}|[a-z]+|(?:rgb|rgba|hsl|hsla)\([0-9.,% +\-]+\))$/i.test(value)?value:undefined}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, withModifiers: _withModifiers, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, normalizeClass: _normalizeClass, normalizeStyle: _normalizeStyle, createTextVNode: _createTextVNode } = _Vue

    return (_openBlock(), _createElementBlock("span", { class: _normalizeClass(["widget-cell-value", css]) }, [(cell?.kind==='thumbnail')
      ? (_openBlock(), _createElementBlock("span", {
          key: 0,
          class: _normalizeClass(["thumbnail-cell", 'thumbnail-'+cell.state]),
          style: _normalizeStyle({'--thumb-size':cell.size+'px'})
        }, [(cell.image && cell.detail!=='false' && cell.detail!=='none')
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              class: "thumb-open",
              onClick: _withModifiers($event => ($emit('open',{record_detail:true})), ["stop"]),
              title: cell.text
            }, [_createElementVNode("img", {
              src: cell.image,
              alt: cell.text,
              loading: "lazy"
            }, null, 8, ["src", "alt"])], 8, ["onClick", "title"]))
          : (cell.image && cell.detail==='none')
            ? (_openBlock(), _createElementBlock("img", {
                key: 1,
                src: cell.image,
                alt: cell.text,
                loading: "lazy"
              }, null, 8, ["src", "alt"]))
            : (cell.image)
              ? (_openBlock(), _createElementBlock("a", {
                  key: 2,
                  href: cell.href,
                  target: "_blank",
                  rel: "noopener noreferrer",
                  onClick: _withModifiers(() => {}, ["stop"]),
                  title: cell.text
                }, [_createElementVNode("img", {
                  src: cell.image,
                  alt: cell.text,
                  loading: "lazy"
                }, null, 8, ["src", "alt"])], 8, ["href", "onClick", "title"]))
              : (_openBlock(), _createElementBlock("span", {
                  key: 3,
                  class: "thumbnail-placeholder",
                  title: cell.text
                }, _toDisplayString(cell.state==='file'?'▤':cell.state==='error'||cell.state==='missing'?'!':'▧'), 9, ["title"])), (cell.show_filename||cell.state==='file')
          ? (_openBlock(), _createElementBlock("small", { key: 4 }, _toDisplayString(cell.text), 1))
          : _createCommentVNode("", true)], 6))
      : (cell?.kind==='project-database')
        ? (_openBlock(), _createElementBlock("span", {
            key: 1,
            class: "project-db-cell"
          }, [_createElementVNode("span", { class: _normalizeClass(cell.exists?'ok':'cell-error') }, "Exists: " + _toDisplayString(cell.exists?'Yes':'No'), 3), _createElementVNode("span", { class: _normalizeClass(cell.current?'ok':'warning') }, "Version: " + _toDisplayString(cell.version||'—'), 3)]))
        : (cell?.kind==='status')
          ? (_openBlock(), _createElementBlock("span", {
              key: 2,
              class: _normalizeClass(["status-chip", {empty:cell.empty}]),
              style: _normalizeStyle({'--status-color':safeColor})
            }, [_createElementVNode("span", { class: "status-dot" }), _createTextVNode(_toDisplayString(cell.text), 1)], 6))
          : (cell?.kind==='login')
            ? (_openBlock(), _createElementBlock("span", {
                key: 3,
                class: _normalizeClass(["login-cell", {empty:cell.empty}]),
                title: cell.login
              }, [(!cell.empty)
                ? (_openBlock(), _createElementBlock("span", {
                    key: 0,
                    class: "avatar-initials"
                  }, _toDisplayString(initials), 1))
                : _createCommentVNode("", true), _createElementVNode("span", null, _toDisplayString(cell.text), 1)], 10, ["title"]))
            : (cell?.kind==='color')
              ? (_openBlock(), _createElementBlock("span", {
                  key: 4,
                  class: "color-cell"
                }, [_createElementVNode("span", {
                  class: "color-swatch",
                  style: _normalizeStyle({background:safeColor})
                }, null, 4), _createElementVNode("code", null, _toDisplayString(cell.text||'—'), 1)]))
              : (cell?.kind==='boolean')
                ? (_openBlock(), _createElementBlock("input", {
                    key: 5,
                    class: "display-checkbox",
                    type: "checkbox",
                    checked: cell.checked,
                    disabled: "",
                    "aria-label": cell.text
                  }, null, 8, ["checked", "aria-label"]))
                : (cell?.kind==='widget')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 6,
                      class: "text-button widget-cell-link",
                      onClick: _withModifiers($event => ($emit('open',cell)), ["stop"])
                    }, _toDisplayString(cell.text), 9, ["onClick"]))
                  : (cell?.kind==='xml')
                    ? (_openBlock(), _createElementBlock("details", { key: 7 }, [_createElementVNode("summary", null, "XML"), _createElementVNode("pre", { class: "xml-cell" }, _toDisplayString(cell.text), 1)]))
                    : (cell?.kind==='link')
                      ? (_openBlock(), _createElementBlock("a", {
                          key: 8,
                          href: cell.href,
                          target: cell.external?'_blank':undefined,
                          rel: "noopener noreferrer",
                          onClick: _withModifiers(() => {}, ["stop"]),
                          title: cell.text
                        }, "↗ " + _toDisplayString(cell.text), 9, ["href", "target", "onClick", "title"]))
                      : (_openBlock(), _createElementBlock("span", { key: 9 }, _toDisplayString(text), 1))], 2))
  }
};
return __component;
})();
const ConfigAudit = (function(){

const __component = {name:'ConfigAudit',props:{project:String,target:String},emits:['close'],data(){return {data:null,error:'',busy:false,selected:null}},async mounted(){this.busy=true;try{this.data=await api.request('/resolved-view',{project:this.project,target:this.target})}catch(e){this.error=e.message}finally{this.busy=false}},methods:{text(v){return JSON.stringify(v,null,2)},support(f){return {native:'Нативный обработчик',raw:'Только исходное значение',unsupported:'Не перенесён'}[f.support]||f.support}}};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, normalizeClass: _normalizeClass, withModifiers: _withModifiers } = _Vue

    return (_openBlock(), _createElementBlock("div", {
      class: "modal-backdrop",
      onClick: _withModifiers($event => ($emit('close')), ["self"])
    }, [_createElementVNode("section", {
      class: "modal config-audit",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "audit-title"
    }, [_createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, "WIDGET CONFIG · RESOLVED VIEW"), _createElementVNode("h2", { id: "audit-title" }, "Источник колонок")]), _createElementVNode("button", {
      "aria-label": "Закрыть проверку конфигурации",
      onClick: $event => ($emit('close'))
    }, "×", 8, ["onClick"])]), _createElementVNode("div", { class: "audit-scroll" }, [busy
      ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Разрешение конфигурации TACTIC…"))
      : _createCommentVNode("", true), error
      ? (_openBlock(), _createElementBlock("p", {
          key: 1,
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), data
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
          _createElementVNode("p", null, [_createElementVNode("code", null, _toDisplayString(data.search_type) + " · " + _toDisplayString(data.view), 1), (data.resolved_view!==data.view)
            ? (_openBlock(), _createElementBlock("span", { key: 0 }, " → " + _toDisplayString(data.resolved_view), 1))
            : _createCommentVNode("", true)]),
          _createElementVNode("p", { class: "notice" }, _toDisplayString(data.notice), 1),
          _createElementVNode("h3", null, "Слои в порядке приоритета"),
          _createElementVNode("ol", { class: "config-layers" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.layers, (layer) => {
            return (_openBlock(), _createElementBlock("li", { key: layer.index }, [_createElementVNode("code", null, _toDisplayString(layer.view), 1), _createTextVNode(" — " + _toDisplayString(layer.origin), 1)]))
          }), 128))]),
          _createElementVNode("details", null, [_createElementVNode("summary", null, "Параметры таблицы и сортировка"), _createElementVNode("pre", null, _toDisplayString(text({options:data.options,ui:data.table_options,sort:data.default_sort})), 1)]),
          (data.sort_error)
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "error"
              }, _toDisplayString(data.sort_error), 1))
            : _createCommentVNode("", true),
          _createElementVNode("h3", null, "Колонки в разрешённом порядке"),
          _createElementVNode("div", { class: "audit-fields" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.fields, (f) => {
            return (_openBlock(), _createElementBlock("button", {
              key: f.name,
              class: _normalizeClass({active:selected===f.name}),
              onClick: $event => (selected=f.name)
            }, [_createElementVNode("strong", null, _toDisplayString(f.label), 1), _createElementVNode("code", null, _toDisplayString(f.name), 1), _createElementVNode("span", { class: _normalizeClass({warning:f.support!=='native'}) }, _toDisplayString(support(f)), 3)], 10, ["onClick"]))
          }), 128))]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.fields.filter(f=>f.name===selected), (f) => {
            return (_openBlock(), _createElementBlock(_Fragment, { key: f.name }, [_createElementVNode("h3", null, _toDisplayString(f.label), 1), _createElementVNode("dl", { class: "audit-definition" }, [
              _createElementVNode("dt", null, "Display handler"),
              _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(f.display_handler||'Штатный default по layout/типу колонки'), 1)]),
              _createElementVNode("dt", null, "Edit handler"),
              _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(f.edit_handler||'Определяется edit-view'), 1)]),
              _createElementVNode("dt", null, "Action"),
              _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(f.action||'Default action исходного вида'), 1)]),
              _createElementVNode("dt", null, "Состояние"),
              _createElementVNode("dd", null, [_createTextVNode(_toDisplayString(support(f)), 1), (f.reason)
                ? (_openBlock(), _createElementBlock("p", { key: 0 }, _toDisplayString(f.reason), 1))
                : _createCommentVNode("", true)])
            ]), _createElementVNode("pre", null, _toDisplayString(text({options:f.options,attributes:f.attributes,sort:{allowed:f.sortable,reason:f.sort_reason},sources:f.sources})), 1)], 64))
          }), 128))
        ], 64))
      : _createCommentVNode("", true)]), _createElementVNode("footer", null, [_createElementVNode("button", { onClick: $event => ($emit('close')) }, "Закрыть", 8, ["onClick"])])])], 8, ["onClick"]))
  }
};
return __component;
})();
const CsvExport = (function(){

const __component = {name:'CsvExport',props:{project:String,target:String,spec:Object,query:Object,selectedKeys:Array},emits:['close'],data(){return {columns:this.spec.fields.filter(f=>!f.hidden&&f.supported&&!['gantt','work-hours'].includes(f.renderer)&&f.kind!=='heading').map(f=>f.name),selection:this.selectedKeys?.length?'selected':'matched',valueMode:'display',delimiter:',',busy:false,error:'',success:false}},methods:{async save(){this.busy=true;this.error='';this.success=false;try{await api.downloadCsv({...this.query,project:this.project,target:this.target,config_revision:this.spec.revision,search_type:this.spec.type,columns:this.columns,selection:this.selection,keys:this.selectedKeys,value_mode:this.valueMode,delimiter:this.delimiter});this.success=true}catch(e){this.error=e.message}finally{this.busy=false}}}};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, vModelCheckbox: _vModelCheckbox, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers } = _Vue

    return (_openBlock(), _createElementBlock("div", {
      class: "modal-backdrop",
      onClick: _withModifiers($event => (!busy&&$emit('close')), ["self"])
    }, [_createElementVNode("section", {
      class: "modal csv-export",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "csv-title"
    }, [_createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, _toDisplayString(spec.type) + " · " + _toDisplayString(spec.view), 1), _createElementVNode("h2", { id: "csv-title" }, "Экспорт CSV из представления")]), _createElementVNode("button", {
      disabled: busy,
      onClick: $event => ($emit('close')),
      "aria-label": "Закрыть экспорт"
    }, "×", 8, ["disabled", "onClick"])]), _createElementVNode("div", { class: "audit-scroll" }, [
      _createElementVNode("p", { class: "notice" }, "Используются текущие фильтры и конфигурация. До 10 000 записей / 32 МиБ. Опасные для электронных таблиц значения защищаются апострофом; формулы не создаются."),
      _createElementVNode("label", null, [_createTextVNode("Выборка"), _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((selection) = $event),
        "aria-label": "Выборка экспорта"
      }, [_createElementVNode("option", { value: "matched" }, "Все совпадения поиска"), _createElementVNode("option", {
        value: "selected",
        disabled: !selectedKeys?.length
      }, "Выбранные записи (" + _toDisplayString(selectedKeys?.length||0) + ")", 9, ["disabled"])], 8, ["onUpdate:modelValue"]), [[_vModelSelect, selection]])]),
      _createElementVNode("label", null, [_createTextVNode("Значения"), _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((valueMode) = $event),
        "aria-label": "Значения экспорта"
      }, [_createElementVNode("option", { value: "display" }, "Отображаемые значения виджетов"), _createElementVNode("option", { value: "raw" }, "Исходные значения обычных полей")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, valueMode]])]),
      _createElementVNode("label", null, [_createTextVNode("Разделитель"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((delimiter) = $event) }, [_createElementVNode("option", { value: "," }, "Запятая"), _createElementVNode("option", { value: ";" }, "Точка с запятой"), _createElementVNode("option", { value: "\t" }, "Табуляция")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, delimiter]])]),
      _createElementVNode("h3", null, "Колонки в порядке выбора"),
      _createElementVNode("div", { class: "export-columns" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(spec.fields.filter(f=>f.kind!=='heading'), (f) => {
        return (_openBlock(), _createElementBlock("label", { key: f.name }, [
          _withDirectives(_createElementVNode("input", {
            type: "checkbox",
            value: f.name,
            "onUpdate:modelValue": $event => ((columns) = $event)
          }, null, 8, ["value", "onUpdate:modelValue"]), [[_vModelCheckbox, columns]]),
          _createTextVNode(_toDisplayString(f.label) + " ", 1),
          _createElementVNode("code", null, _toDisplayString(f.name), 1),
          (!f.supported)
            ? (_openBlock(), _createElementBlock("small", { key: 0 }, " — виджет не перенесён"))
            : _createCommentVNode("", true)
        ]))
      }), 128))]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      success
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, "CSV сформирован и передан браузеру."))
        : _createCommentVNode("", true)
    ]), _createElementVNode("footer", null, [_createElementVNode("button", {
      disabled: busy,
      onClick: $event => ($emit('close'))
    }, "Закрыть", 8, ["disabled", "onClick"]), _createElementVNode("button", {
      class: "primary",
      disabled: busy||!columns.length,
      onClick: save
    }, _toDisplayString(busy?'Подготовка…':'Скачать CSV'), 9, ["disabled", "onClick"])])])], 8, ["onClick"]))
  }
};
return __component;
})();
const FieldInput = (function(){
const __component = {name:'FieldInput',props:{field:Object,modelValue:null},emits:['update:modelValue'],computed:{
 inputRows(){const n=Number(this.field.display_options?.rows||4);return Number.isInteger(n)?Math.max(1,Math.min(40,n)):4},
 placeholder(){const p=this.field.display_options?.placeholder;return typeof p==='string'?p:undefined},
 inputType(){const kind=this.field.kind;if(kind==='date'){const v=String(this.modelValue??'');return !v||/^\d{4}-\d{2}-\d{2}(?:[ T].*)?$/.test(v)?'date':'text'}if(kind==='datetime'){const v=String(this.modelValue??'');return !v||/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(v)?'datetime-local':'text'}return kind==='password'?'password':['integer','number'].includes(kind)?'number':'text'},
 inputValue(){const v=this.modelValue??'';if(typeof v!=='string')return v;if(this.inputType==='date')return v.slice(0,10);if(this.inputType==='datetime-local')return v.replace(' ','T');return v}
 },methods:{emit(e){this.$emit('update:modelValue',this.field.kind==='boolean'?e.target.checked:e.target.value)}}};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, createCommentVNode: _createCommentVNode } = _Vue

    return (_openBlock(), _createElementBlock("div", { class: "field-input" }, [(field.kind==='select')
      ? (_openBlock(), _createElementBlock("select", {
          key: 0,
          disabled: field.read_only,
          value: modelValue??'',
          onChange: emit
        }, [_createElementVNode("option", { value: "" }, "—"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(field.options, (o) => {
          return (_openBlock(), _createElementBlock("option", {
            key: o.value,
            value: o.value
          }, _toDisplayString(o.label), 9, ["value"]))
        }), 128))], 40, ["disabled", "value", "onChange"]))
      : (field.kind==='boolean')
        ? (_openBlock(), _createElementBlock("input", {
            key: 1,
            type: "checkbox",
            disabled: field.read_only,
            checked: modelValue===true,
            onChange: emit
          }, null, 40, ["disabled", "checked", "onChange"]))
        : (['textarea','json'].includes(field.kind))
          ? (_openBlock(), _createElementBlock("textarea", {
              key: 2,
              disabled: field.read_only,
              value: typeof modelValue==='object'&&modelValue!==null?JSON.stringify(modelValue,null,2):modelValue??'',
              rows: inputRows,
              placeholder: placeholder,
              onInput: emit
            }, null, 40, ["disabled", "value", "rows", "placeholder", "onInput"]))
          : (_openBlock(), _createElementBlock("input", {
              key: 3,
              type: inputType,
              placeholder: placeholder,
              step: field.kind==='integer'?1:'any',
              disabled: field.read_only,
              value: inputValue,
              autocomplete: field.kind==='password'?'new-password':undefined,
              onInput: emit
            }, null, 40, ["type", "placeholder", "step", "disabled", "value", "autocomplete", "onInput"])), (field.reason)
      ? (_openBlock(), _createElementBlock("small", {
          key: 4,
          class: "warning-text"
        }, _toDisplayString(field.reason), 1))
      : _createCommentVNode("", true)]))
  }
};
return __component;
})();
const ConfiguredForm = (function(){




const __component = {
 name:'ConfiguredForm',components:{FieldInput,ContextMenu,WidgetDefinition},
 props:{form:Object,busy:Boolean,error:String,embedded:Boolean,project:String,target:String},emits:['save','close','preview','dirty'],
 data(){return {values:{...(this.form.defaults||{}),...(this.form.record?.values||{})},dirty:{},menu:null,menuSequence:0,definition:null,submitting:false}},
 computed:{readOnly(){return this.form.widget?.mode==='view'||(!this.form.spec.capabilities?.create&&!this.form.spec.capabilities?.update)},hasChanges(){return Object.keys(this.dirty).length>0},titleId(){return 'form-title-'+this.$.uid}},
 watch:{busy(value){if(!value)this.submitting=false},form(){this.submitting=false}},
 beforeUnmount(){this.menuSequence++;this.$emit('dirty',false)},
 methods:{
  change(name,value){this.values[name]=value;const original=this.form.record?.values?.[name]??this.form.defaults?.[name];if(JSON.stringify(original)===JSON.stringify(value))delete this.dirty[name];else this.dirty[name]=value;this.$emit('dirty',this.hasChanges);if(this.form.record&&this.form.spec.fields.find(f=>f.name===name)?.choice_refresh){const v={};for(const f of this.form.spec.fields)if(f.choice_refresh&&Object.hasOwn(this.dirty,f.name))v[f.name]=this.dirty[f.name];this.$emit('preview',v)}},
  save(){if(this.busy||this.submitting||this.readOnly)return;api.action?.('form.save',{project:this.project,target:this.target,count:Object.keys(this.dirty).length});this.submitting=true;this.$emit('save',this.form.record?{...this.dirty}:{...(this.form.defaults||{}),...this.dirty});this.$nextTick(()=>{if(!this.busy)this.submitting=false})},
  close(){if(this.hasChanges&&!confirm('Закрыть форму без сохранения?'))return;api.action?.('form.cancel',{project:this.project,target:this.target});this.$emit('close')},
  hotkey(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();if(this.form.widget?.show_action!==false)this.save()}},
  async context(e,f){if(e.shiftKey||!this.project||!this.target)return;e.preventDefault();e.stopPropagation();const seq=++this.menuSequence;const r=e.currentTarget.getBoundingClientRect();this.menu={x:e.clientX||r.left,y:e.clientY||r.bottom,title:f.label,loading:true,items:[],field:f};try{const d=await api.request('/context-menu',{project:this.project,target:this.target,scope:'form-field',field:f.name,key:this.form.record?.key});if(seq===this.menuSequence&&this.menu)this.menu={...this.menu,...d,loading:false}}catch(error){if(seq===this.menuSequence&&this.menu)this.menu={...this.menu,loading:false,error:error.message}}},
  fieldMenu(e,f){if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){e.preventDefault();this.context({preventDefault(){},stopPropagation(){},currentTarget:e.currentTarget,clientX:0,clientY:0},f)}},
  menuAction(item){const f=this.menu.field;if(item.id==='definition')this.definition=f.name;else if(item.id==='reset_field')this.change(f.name,this.form.record?.values?.[f.name]??this.form.defaults?.[f.name]);else if(item.id==='null_field')this.change(f.name,null);this.menu=null;this.menuSequence++}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, normalizeClass: _normalizeClass, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, resolveComponent: _resolveComponent, createVNode: _createVNode, withModifiers: _withModifiers, createBlock: _createBlock } = _Vue

    const _component_FieldInput = _resolveComponent("FieldInput")
    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_WidgetDefinition = _resolveComponent("WidgetDefinition")

    return (_openBlock(), _createElementBlock("div", {
      class: _normalizeClass(embedded?'embedded-form-frame':'modal-backdrop'),
      onClick: _withModifiers($event => (!embedded&&close()), ["self"])
    }, [_createElementVNode("section", {
      class: _normalizeClass(embedded?'embedded-form':'modal'),
      role: embedded?'region':'dialog',
      "aria-modal": embedded?undefined:true,
      "aria-labelledby": form.widget?.show_header!==false?titleId:undefined,
      "aria-label": form.widget?.show_header===false?(form.widget?.title||'Форма записи TACTIC'):undefined,
      onKeydown: hotkey
    }, [
      (form.widget?.show_header!==false)
        ? (_openBlock(), _createElementBlock("header", {
            key: 0,
            class: _normalizeClass({'visually-hidden':embedded})
          }, [_createElementVNode("div", null, [_createElementVNode("small", null, _toDisplayString(form.spec.type) + " · " + _toDisplayString(form.spec.view), 1), _createElementVNode("h2", { id: titleId }, _toDisplayString(form.widget?.title||(form.bulk?'Изменить '+form.records.length+' записей':form.record?'Редактирование записи':'Новая запись')), 9, ["id"])]), (!embedded)
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                "aria-label": "Закрыть",
                onClick: close
              }, "×", 8, ["onClick"]))
            : _createCommentVNode("", true)], 2))
        : _createCommentVNode("", true),
      (form.spec.write_notice)
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, _toDisplayString(form.spec.write_notice), 1))
        : _createCommentVNode("", true),
      (form.dependency_notice)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, _toDisplayString(form.dependency_notice), 1))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("form", { onSubmit: _withModifiers(save, ["prevent"]) }, [_createElementVNode("div", { class: "form-scroll" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(form.spec.fields.filter(f=>!f.hidden), (f) => {
        return (_openBlock(), _createElementBlock("div", {
          key: f.name,
          class: _normalizeClass(f.kind==='heading'?'form-section-title':'form-row')
        }, [(f.kind==='heading')
          ? (_openBlock(), _createElementBlock("h3", { key: 0 }, _toDisplayString(f.label), 1))
          : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("label", {
              tabindex: "0",
              onContextmenu: $event => (context($event,f)),
              onKeydown: $event => (fieldMenu($event,f))
            }, [_createTextVNode(_toDisplayString(f.label), 1), _createElementVNode("small", null, _toDisplayString(f.name), 1)], 40, ["onContextmenu", "onKeydown"]), _createElementVNode("div", null, [_createVNode(_component_FieldInput, {
              field: f,
              "model-value": values[f.name],
              "onUpdate:modelValue": $event => (change(f.name,$event))
            }, null, 8, ["field", "model-value", "onUpdate:modelValue"]), (f.nullable&&!f.read_only&&!readOnly)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  class: "null-button",
                  type: "button",
                  onClick: $event => (change(f.name,null))
                }, "Установить NULL", 8, ["onClick"]))
              : _createCommentVNode("", true)])], 64))], 2))
      }), 128))]), (form.widget?.show_action!==false)
        ? (_openBlock(), _createElementBlock("footer", { key: 0 }, [_createElementVNode("span", null, "Поля и actions из widget_config"), _createElementVNode("button", {
            type: "button",
            onClick: close
          }, _toDisplayString(embedded?'Закрыть':'Отмена'), 9, ["onClick"]), (!readOnly)
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                type: "submit",
                class: "primary",
                disabled: busy||submitting||(!hasChanges&&!(!form.record&&Object.keys(form.defaults||{}).length))
              }, _toDisplayString(busy?'Сохранение…':'Сохранить'), 9, ["disabled"]))
            : _createCommentVNode("", true)]))
        : _createCommentVNode("", true)], 40, ["onSubmit"]),
      menu
        ? (_openBlock(), _createBlock(_component_ContextMenu, {
            key: 4,
            menu: menu,
            onAction: menuAction,
            onClose: $event => {menu=null;menuSequence++}
          }, null, 8, ["menu", "onAction", "onClose"]))
        : _createCommentVNode("", true),
      definition
        ? (_openBlock(), _createBlock(_component_WidgetDefinition, {
            key: 5,
            project: project,
            target: target,
            field: definition,
            "form-field": "",
            "record-key": form.record?.key,
            onClose: $event => (definition=null)
          }, null, 8, ["project", "target", "field", "record-key", "onClose"]))
        : _createCommentVNode("", true)
    ], 42, ["role", "aria-modal", "aria-labelledby", "aria-label", "onKeydown"])], 10, ["onClick"]))
  }
};
return __component;
})();
const CollectionPanel = (function(){


const __component = {
 name:'CollectionPanel',components:{ConfiguredForm},props:{project:String,target:String,selectedKeys:{type:Array,default:()=>[]},refreshKey:Number},emits:['changed','open'],
 data(){return {catalog:{items:[],total:0,offset:0,limit:40},members:null,trail:[],keyword:'',error:'',busy:false,memberSelection:[],form:null,formError:'',addDialog:false,candidates:{items:[],total:0,offset:0,limit:40},candidateKeyword:'',candidateSelection:[],deleteDialog:false,seq:0,alive:true}},
 watch:{refreshKey(){this.reload()}},
 mounted(){this.load()},beforeUnmount(){this.alive=false;this.seq++},
 methods:{
 async reload(){await this.load(this.catalog.offset);if(this.members)await this.page(this.members.offset)},
 args(extra={}){return {project:this.project,target:this.target,...extra}},
 isCollection(row){return [true,1,'true','t'].includes(row.values._is_collection)},
 title(row){return row.values.name||row.values.code},
 async load(offset=0){const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request('/collections',this.args({offset,limit:40,keyword:this.keyword}));if(!this.alive||seq!==this.seq)return;this.catalog=d;if(d.fixed_collection&&!this.members)await this.enter(d.fixed_collection,true)}catch(e){if(this.alive&&seq===this.seq)this.error=e.message}finally{if(this.alive&&seq===this.seq)this.busy=false}},
 async enter(row,replace=false){if(this.busy&&this.members)return;this.busy=true;this.error='';try{const d=await api.request('/collection-members',this.args({collection:row.key,offset:0,limit:40}));if(!this.alive)return;this.members=d;this.memberSelection=[];if(replace)this.trail=[d.collection];else this.trail.push(d.collection)}catch(e){if(this.alive)this.error=e.message}finally{if(this.alive)this.busy=false}},
 async page(offset=0){this.busy=true;this.error='';try{const d=await api.request('/collection-members',this.args({collection:this.members.collection.key,offset,limit:40}));if(this.alive){this.members=d;this.memberSelection=[]}}catch(e){if(this.alive)this.error=e.message}finally{if(this.alive)this.busy=false}},
 async back(index){if(index<0){this.members=null;this.trail=[];this.memberSelection=[];return}const row=this.trail[index];this.trail=this.trail.slice(0,index);await this.enter(row)},
 async findCandidates(offset=0){this.error='';try{this.candidates=await api.request('/collections',this.args({mode:'records',keyword:this.candidateKeyword,offset,limit:40}))}catch(e){this.error=e.message}},
 async adding(){this.addDialog=true;this.candidateSelection=[];await this.findCandidates()},
 async change(action,keys=[]){this.error='';this.busy=true;try{await api.request('/collection-change',this.args({collection:this.members.collection.key,revision:this.members.revision,action,keys,confirm:action==='delete'?'DELETE_COLLECTION':undefined}),'POST');this.addDialog=false;this.deleteDialog=false;if(action==='delete'){this.members=null;this.trail=[];await this.load()}else await this.page();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 create(){this.form=this.catalog.create_form;this.formError=''},
 async save(values){this.busy=true;this.formError='';try{const result=await api.request('/collections',this.args({values,collection:this.members?.collection.key,revision:this.members?.revision}),'POST');this.form=null;if(this.members)await this.page();else await this.load();this.$emit('changed')}catch(e){this.formError=e.message}finally{this.busy=false}},
 toggle(list,key,checked){const i=list.indexOf(key);if(checked&&i<0)list.push(key);else if(!checked&&i>=0)list.splice(i,1)},
 openObjects(){if(this.catalog.records_target)this.$emit('open',{id:this.catalog.records_target})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, vModelText: _vModelText, withDirectives: _withDirectives, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createBlock: _createBlock, Teleport: _Teleport } = _Vue

    const _component_ConfiguredForm = _resolveComponent("ConfiguredForm")

    return (_openBlock(), _createElementBlock("section", {
      class: "collection-panel",
      "aria-label": "Коллекции объектов"
    }, [
      _createElementVNode("header", {
        class: "widget-toolbar",
        role: "group",
        "aria-label": "Действия с коллекциями"
      }, [_createElementVNode("code", {
        class: "editor-context",
        title: catalog.instance_type
      }, _toDisplayString(catalog.search_type), 9, ["title"]), _createElementVNode("div", { class: "toolbar" }, [(catalog.records_target)
        ? (_openBlock(), _createElementBlock("button", {
            key: 0,
            onClick: openObjects
          }, "Таблица объектов", 8, ["onClick"]))
        : _createCommentVNode("", true), _createElementVNode("button", {
        disabled: busy||!catalog.can_create,
        onClick: create
      }, _toDisplayString(members?'Новая вложенная коллекция':'Новая коллекция'), 9, ["disabled", "onClick"])])]),
      _createElementVNode("p", { class: "notice" }, _toDisplayString(catalog.notice), 1),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("nav", { class: "collection-breadcrumb" }, [(!catalog.fixed_collection)
        ? (_openBlock(), _createElementBlock("button", {
            key: 0,
            onClick: $event => (back(-1))
          }, "Все коллекции", 8, ["onClick"]))
        : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(trail, (row, i) => {
        return (_openBlock(), _createElementBlock(_Fragment, { key: row.key }, [_createElementVNode("span", null, "›"), _createElementVNode("button", {
          disabled: i===trail.length-1||busy,
          onClick: $event => (back(i))
        }, _toDisplayString(title(row)), 9, ["disabled", "onClick"])], 64))
      }), 128))]),
      (!members)
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
            _createElementVNode("form", {
              class: "toolbar",
              onSubmit: _withModifiers($event => (load()), ["prevent"])
            }, [_withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((keyword) = $event),
              placeholder: "Название коллекции",
              "aria-label": "Найти коллекцию"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, keyword]]), _createElementVNode("button", { disabled: busy }, "Найти", 8, ["disabled"])], 40, ["onSubmit"]),
            _createElementVNode("div", { class: "collection-grid" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalog.items, (row) => {
              return (_openBlock(), _createElementBlock("button", {
                key: row.key,
                class: "collection-card",
                disabled: busy,
                onClick: $event => (enter(row))
              }, [_createElementVNode("span", { class: "eyebrow" }, "КОЛЛЕКЦИЯ"), _createElementVNode("b", null, _toDisplayString(title(row)), 1), _createElementVNode("small", null, _toDisplayString(row.values.description||row.values.code), 1)], 8, ["disabled", "onClick"]))
            }), 128))]),
            (!catalog.items.length&&!busy)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "muted"
                }, "Коллекций не найдено."))
              : _createCommentVNode("", true),
            _createElementVNode("footer", { class: "toolbar" }, [
              _createElementVNode("small", null, _toDisplayString(catalog.total) + " коллекций · " + _toDisplayString(catalog.offset+1) + "–" + _toDisplayString(catalog.offset+catalog.items.length), 1),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", {
                disabled: busy||!catalog.offset,
                onClick: $event => (load(Math.max(0,catalog.offset-40)))
              }, "Назад", 8, ["disabled", "onClick"]),
              _createElementVNode("button", {
                disabled: busy||!catalog.has_more,
                onClick: $event => (load(catalog.offset+40))
              }, "Далее", 8, ["disabled", "onClick"])
            ])
          ], 64))
        : (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
            _createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("h3", null, _toDisplayString(title(members.collection)), 1), _createElementVNode("p", null, _toDisplayString(members.collection.values.description), 1), _createElementVNode("small", null, _toDisplayString(members.total) + " объектов · " + _toDisplayString(members.links) + " instance-связей · родителей: " + _toDisplayString(members.parents), 1)])]),
            (members.duplicate_links||members.missing_members)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "notice"
                }, "Повторных связей: " + _toDisplayString(members.duplicate_links) + "; отсутствующих объектов: " + _toDisplayString(members.missing_members) + ". Диагностика не исправляет данные автоматически.", 1))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "toolbar" }, [
              _createElementVNode("button", {
                disabled: busy||!members.can_write,
                onClick: adding
              }, "Добавить существующие", 8, ["disabled", "onClick"]),
              (selectedKeys.length)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    disabled: busy||!members.can_write||selectedKeys.length>100,
                    onClick: $event => (change('add',selectedKeys))
                  }, "Добавить выбранные в таблице (" + _toDisplayString(selectedKeys.length) + ")", 9, ["disabled", "onClick"]))
                : _createCommentVNode("", true),
              _createElementVNode("button", {
                disabled: busy||!members.can_write||!memberSelection.length,
                onClick: $event => (change('remove',memberSelection))
              }, "Убрать из коллекции (" + _toDisplayString(memberSelection.length) + ")", 9, ["disabled", "onClick"]),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", {
                disabled: busy||!members.can_write,
                onClick: $event => (deleteDialog=true)
              }, "Удалить коллекцию…", 8, ["disabled", "onClick"])
            ]),
            _createElementVNode("div", { class: "collection-members" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(members.items, (row) => {
              return (_openBlock(), _createElementBlock("article", {
                key: row.key,
                class: "collection-member"
              }, [
                _createElementVNode("label", null, [_createElementVNode("input", {
                  type: "checkbox",
                  checked: memberSelection.includes(row.key),
                  disabled: busy,
                  onChange: $event => (toggle(memberSelection,row.key,$event.target.checked))
                }, null, 40, ["checked", "disabled", "onChange"]), (isCollection(row))
                  ? (_openBlock(), _createElementBlock("span", {
                      key: 0,
                      class: "tag"
                    }, "коллекция"))
                  : _createCommentVNode("", true), _createElementVNode("b", null, _toDisplayString(title(row)), 1)]),
                (row.values.s_status==='retired')
                  ? (_openBlock(), _createElementBlock("span", {
                      key: 0,
                      class: "tag"
                    }, "архив"))
                  : _createCommentVNode("", true),
                _createElementVNode("small", null, _toDisplayString(row.values.code), 1),
                (isCollection(row))
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 1,
                      disabled: busy||row.values.s_status==='retired'||!!catalog.fixed_collection,
                      onClick: $event => (enter(row))
                    }, "Открыть вложенную", 8, ["disabled", "onClick"]))
                  : _createCommentVNode("", true)
              ]))
            }), 128))]),
            (!members.items.length)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 1,
                  class: "muted"
                }, "Коллекция пуста."))
              : _createCommentVNode("", true),
            _createElementVNode("footer", { class: "toolbar" }, [
              _createElementVNode("small", null, _toDisplayString(members.offset+(members.total?1:0)) + "–" + _toDisplayString(members.offset+members.items.length) + " из " + _toDisplayString(members.total), 1),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", {
                disabled: busy||!members.offset,
                onClick: $event => (page(Math.max(0,members.offset-40)))
              }, "Назад", 8, ["disabled", "onClick"]),
              _createElementVNode("button", {
                disabled: busy||!members.has_more,
                onClick: $event => (page(members.offset+40))
              }, "Далее", 8, ["disabled", "onClick"])
            ]),
            _createElementVNode("p", { class: "muted" }, _toDisplayString(members.notice), 1)
          ], 64)),
      form
        ? (_openBlock(), _createBlock(_component_ConfiguredForm, {
            key: 3,
            form: form,
            busy: busy,
            error: formError,
            onSave: save,
            onClose: $event => (form=null)
          }, null, 8, ["form", "busy", "error", "onSave", "onClose"]))
        : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [addDialog
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop"
          }, [_createElementVNode("section", {
            class: "modal collection-add",
            role: "dialog"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h3", null, "Добавить существующие объекты"), _createElementVNode("button", { onClick: $event => (addDialog=false) }, "×", 8, ["onClick"])]),
            _createElementVNode("p", null, "Создаётся только instance-связь. Объект и его файлы не копируются."),
            error
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            _createElementVNode("form", {
              class: "toolbar",
              onSubmit: _withModifiers($event => (findCandidates()), ["prevent"])
            }, [_withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((candidateKeyword) = $event),
              placeholder: "Название объекта",
              "aria-label": "Поиск кандидатов"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, candidateKeyword]]), _createElementVNode("button", null, "Найти")], 40, ["onSubmit"]),
            _createElementVNode("div", { class: "candidate-list" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(candidates.items, (row) => {
              return (_openBlock(), _createElementBlock("label", { key: row.key }, [_createElementVNode("input", {
                type: "checkbox",
                checked: candidateSelection.includes(row.key),
                disabled: row.key===members.collection.key,
                onChange: $event => (toggle(candidateSelection,row.key,$event.target.checked))
              }, null, 40, ["checked", "disabled", "onChange"]), _createElementVNode("b", null, _toDisplayString(title(row)), 1), _createElementVNode("small", null, _toDisplayString(isCollection(row)?'коллекция':'объект') + " · " + _toDisplayString(row.values.code), 1)]))
            }), 128))]),
            _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("small", null, _toDisplayString(candidates.offset+1) + "–" + _toDisplayString(candidates.offset+candidates.items.length) + " из " + _toDisplayString(candidates.total), 1), _createElementVNode("button", {
              disabled: !candidates.offset,
              onClick: $event => (findCandidates(Math.max(0,candidates.offset-40)))
            }, "Назад", 8, ["disabled", "onClick"]), _createElementVNode("button", {
              disabled: !candidates.has_more,
              onClick: $event => (findCandidates(candidates.offset+40))
            }, "Далее", 8, ["disabled", "onClick"])]),
            _createElementVNode("footer", null, [_createElementVNode("small", null, _toDisplayString(candidateSelection.length) + " выбрано · до 100 за операцию", 1), _createElementVNode("button", {
              class: "primary",
              disabled: busy||!candidateSelection.length||candidateSelection.length>100,
              onClick: $event => (change('add',candidateSelection))
            }, "Добавить связи", 8, ["disabled", "onClick"])])
          ])]))
        : _createCommentVNode("", true), deleteDialog
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "modal-backdrop"
          }, [_createElementVNode("section", {
            class: "modal collection-delete",
            role: "dialog"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h3", null, "Удалить коллекцию «" + _toDisplayString(title(members.collection)) + "»?", 1), _createElementVNode("button", { onClick: $event => (deleteDialog=false) }, "×", 8, ["onClick"])]),
            _createElementVNode("p", null, "Штатный CollectionDeleteCmd удалит саму запись коллекции и входящие/исходящие связи. Содержимое коллекции — " + _toDisplayString(members.total) + " объектов — эта команда напрямую не удаляет. Пользовательские серверные триггеры остаются действующими.", 1),
            error
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            _createElementVNode("footer", null, [_createElementVNode("button", { onClick: $event => (deleteDialog=false) }, "Отмена", 8, ["onClick"]), _createElementVNode("button", {
              class: "danger",
              disabled: busy,
              onClick: $event => (change('delete'))
            }, "Удалить коллекцию и её связи", 8, ["disabled", "onClick"])])
          ])]))
        : _createCommentVNode("", true)]))
    ]))
  }
};
return __component;
})();
const WorkHoursPanel = (function(){

const __component = {
 name:'WorkHoursPanel',props:{project:String,target:String,record:Object,task:Object,field:{type:String,default:'work_hours'}},emits:['close','changed'],
 data(){return {start:'',data:null,values:{},dirty:{},busy:false,error:'',sequence:0}},
 computed:{end(){return this.data?.end||''},dayCount(){return this.data?.days_per_page||7},days(){if(!this.data)return [];const rows=[];const count=Math.round((new Date(this.data.end+'T12:00:00Z')-new Date(this.data.start+'T12:00:00Z'))/86400000)+1;for(let i=0;i<count;i++){const d=new Date(this.data.start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);const day=d.toISOString().slice(0,10);rows.push({day,regular:this.cell(day,'regular'),overtime:this.cell(day,'overtime')})}return rows},hasOvertime(){return this.data?.show_overtime||this.data?.items.some(x=>x.category==='overtime')}},
 mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key,task:this.task.key,start:this.start,field:this.field}},identity(day,category){return day+'|'+category},cell(day,category){const entries=this.data.items.filter(e=>String(e.day).slice(0,10)===day&&(category==='overtime'?e.category==='overtime':e.category!=='overtime')),blocked=entries.length>1||entries.some(e=>e.start_time||e.end_time||!['regular','overtime','',null,undefined].includes(e.category));return {entries,blocked,identity:this.identity(day,category),value:entries.length===1?entries[0].straight_time:''}},
 async load(){const seq=++this.sequence;this.busy=true;this.error='';try{const d=await api.request('/task-hours',this.args());if(seq===this.sequence){this.data=d;this.start=d.start;this.dirty={};this.values={};for(const r of this.days)for(const category of ['regular','overtime'])this.values[r[category].identity]=r[category].value??''}}catch(e){if(seq===this.sequence)this.error=e.message}finally{if(seq===this.sequence)this.busy=false}},
 async navigate(delta){if(Object.keys(this.dirty).length&&!confirm('Отбросить несохранённые изменения времени?'))return;const d=new Date(this.start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);this.start=d.toISOString().slice(0,10);await this.load()},
 async changeDate(e){const day=e.target.value;if(!day)return;if(Object.keys(this.dirty).length&&!confirm('Отбросить несохранённые изменения времени?')){e.target.value=this.start;return}this.start=day;await this.load()},
 edit(day,category,value){const id=this.identity(day,category);this.values[id]=value;this.dirty[id]={day,category,value}},
 async save(){if(this.busy||!this.data?.can_write)return;if(!confirm('Сохранить ваши записи рабочего времени? Ноль или пустое значение удаляет соответствующую запись work_hour.'))return;this.busy=true;this.error='';try{await api.request('/task-hours',{...this.args(),end:this.data.end,revision:this.data.revision,cells:Object.values(this.dirty),confirm:'SAVE_HOURS'},'PATCH');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 close(){if(this.busy)return;if(!Object.keys(this.dirty).length||confirm('Закрыть без сохранения рабочего времени?'))this.$emit('close')}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, createTextVNode: _createTextVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, withModifiers: _withModifiers } = _Vue

    return (_openBlock(), _createElementBlock("div", {
      class: "modal-backdrop",
      onClick: _withModifiers(close, ["self"])
    }, [_createElementVNode("section", {
      class: "modal work-hours-panel",
      role: "dialog",
      "aria-modal": "true"
    }, [
      _createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, _toDisplayString(task.key), 1), _createElementVNode("h2", null, "Рабочее время · " + _toDisplayString(task.task?.process||task.values?.process), 1)]), _createElementVNode("button", {
        disabled: busy,
        onClick: close,
        "aria-label": "Закрыть рабочее время"
      }, "×", 8, ["disabled", "onClick"])]),
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("button", {
          disabled: busy,
          onClick: $event => (navigate(-dayCount))
        }, "← Период", 8, ["disabled", "onClick"]),
        _createElementVNode("label", null, [_createTextVNode("Начало"), _createElementVNode("input", {
          type: "date",
          value: start,
          disabled: busy,
          onChange: changeDate
        }, null, 40, ["value", "disabled", "onChange"])]),
        _createElementVNode("span", null, "→ " + _toDisplayString(end), 1),
        _createElementVNode("button", {
          disabled: busy,
          onClick: $event => (navigate(dayCount))
        }, "Период →", 8, ["disabled", "onClick"])
      ]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      data
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, _toDisplayString(data.notice) + " · " + _toDisplayString(data.login) + " · " + _toDisplayString(data.unit==='minute'?'минуты':'часы'), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "form-scroll" }, [data
        ? (_openBlock(), _createElementBlock("table", {
            key: 0,
            class: "work-hours-table"
          }, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Дата"), _createElementVNode("th", null, "Обычное время"), hasOvertime
            ? (_openBlock(), _createElementBlock("th", { key: 0 }, "Сверхурочное"))
            : _createCommentVNode("", true)])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(days, (row) => {
            return (_openBlock(), _createElementBlock("tr", { key: row.day }, [_createElementVNode("th", null, _toDisplayString(row.day), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(hasOvertime?['regular','overtime']:['regular'], (category) => {
              return (_openBlock(), _createElementBlock("td", { key: category }, [(!row[category].blocked)
                ? (_openBlock(), _createElementBlock("input", {
                    key: 0,
                    type: "number",
                    min: "0",
                    max: data.unit==='minute'?1440:24,
                    step: "any",
                    value: values[row[category].identity],
                    disabled: busy||!data.can_write||(category==='overtime'&&!data.show_overtime),
                    "aria-label": row.day+' '+category,
                    onInput: $event => (edit(row.day,category,$event.target.value))
                  }, null, 40, ["max", "value", "disabled", "aria-label", "onInput"]))
                : (_openBlock(), _createElementBlock("details", { key: 1 }, [_createElementVNode("summary", null, _toDisplayString(row[category].entries.length) + " записей · только чтение", 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row[category].entries, (e) => {
                    return (_openBlock(), _createElementBlock("div", { key: e.key }, [_createElementVNode("code", null, _toDisplayString(e.key), 1), _createElementVNode("p", null, _toDisplayString(e.login) + " · " + _toDisplayString(e.category||'regular') + " · " + _toDisplayString(e.straight_time) + " · " + _toDisplayString(e.start_time) + " → " + _toDisplayString(e.end_time), 1)]))
                  }), 128))]))]))
            }), 128))]))
          }), 128))])]))
        : _createCommentVNode("", true)]),
      _createElementVNode("footer", null, [_createElementVNode("small", null, "Исходный WorkHoursElementAction"), _createElementVNode("button", {
        disabled: busy,
        onClick: close
      }, "Закрыть", 8, ["disabled", "onClick"]), _createElementVNode("button", {
        class: "primary",
        disabled: busy||!data?.can_write||!Object.keys(dirty).length,
        onClick: save
      }, _toDisplayString(busy?'Обработка…':'Сохранить время'), 9, ["disabled", "onClick"])])
    ])], 8, ["onClick"]))
  }
};
return __component;
})();
const ConfiguredTable = (function(){









// The grid keeps ORIGINAL values and drafts separate. Editing only stages an
// input; Save Changes submits one batch through TACTIC's EditMultipleCmd.
const __component = {
 name:'ConfiguredTable',
 components:{TableToolbar,TableColumns,FieldInput,WorkHoursPanel,WidgetCell,ContextMenu,WidgetDefinition},
 props:{spec:Object,rows:Array,busy:Boolean,total:Number,offset:Number,limit:Number,project:String,target:String,summaries:Array,presentation:{type:String,default:'data'},recordState:String,allowWrites:Boolean,filterCount:{type:Number,default:0},searchOpen:Boolean},
 emits:['inspect','edit','sort','page','changed','selection','edit-selected','dirty','view-changed','open','table-action'],
 data(){return {
  columnsOpen:false,diagnosticsOpen:false,selected:[],selectionAnchor:null,menu:null,menuSeq:0,definition:null,designer:null,audit:false,
  mode:'table',groupField:'',hidden:[],columnOrder:[],widths:{},pinned:[],density:'comfortable',wrap:false,
  editor:null,editorSeq:0,drafts:{},draftTableRevision:null,saving:false,loadingEditor:false,
  hours:null,error:'',notice:'',expanded:{},cellWindow:null,activeCell:null,dragColumn:null,
  stateReady:false,stateLoading:false,stateSeq:0,resizeState:null,lastSpec:null,resizeMove:null,resizeEnd:null,fill:null,fillSeq:0
 }},
 computed:{
  flags(){return Object.assign({show_header:true,show_select:true,show_shelf:true,show_search_limit:true,show_context_menu:true,show_column_manager:true,show_layout_switcher:true},this.spec.table_options||{})},
  fields(){
   const visible=this.spec.fields.filter(f=>!this.hidden.includes(f.name));
   const rank=name=>{const i=this.columnOrder.indexOf(name);return i<0?10000:i};
   return [...visible].sort((a,b)=>Number(this.pinned.includes(b.name))-Number(this.pinned.includes(a.name))||rank(a.name)-rank(b.name));
  },
  groups(){if(!this.groupField)return [{key:'',rows:this.rows}];const groups=new Map();for(const row of this.rows){const key=String(row.values[this.groupField]??'—');if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row)}return Array.from(groups,([key,rows])=>({key,rows}))},
  fillFields(){return this.spec.fields.filter(f=>f.storage&&f.supported&&!['id','code','timestamp','s_status'].includes(f.name)&&!['work-hours','gantt'].includes(f.renderer))},
  allSelected(){return this.rows.length>0&&this.rows.every(r=>this.selected.includes(r.key))},
  changedRows(){return Object.values(this.drafts).filter(d=>Object.keys(d.values).length)},
  changedCells(){return this.changedRows.reduce((n,d)=>n+Object.keys(d.values).length,0)},
  dirty(){return this.changedCells>0||Boolean(this.editor)},
  gridWidth(){return this.fields.reduce((n,f)=>n+this.widthNumber(f),this.flags.show_select?42:0)},
  pendingOutsidePage(){const visible=new Set(this.rows.map(r=>r.key));return this.changedRows.filter(d=>!visible.has(d.key)).length}
 },
 watch:{
  spec:{immediate:true,handler(value){
   if(this.lastSpec!==value.type+'|'+value.view){
    this.lastSpec=value.type+'|'+value.view;
    this.mode=value.table_options?.initial_mode||'table';
    this.hidden=value.fields.filter(f=>f.hidden).map(f=>f.name);
    this.columnOrder=value.fields.map(f=>f.name);
    this.restoreGeometry();
   }
   if(this.groupField&&!value.fields.some(f=>f.name===this.groupField))this.groupField='';
  }},
  dirty(value){this.$emit('dirty',value)},
  selected(value){this.$emit('selection',value)},
  rows(){this.selected=this.selected.filter(k=>this.rows.some(r=>r.key===k))},
  target(){this.selected=[];this.activeCell=null;this.lastSpec=null},
  density(){this.persistGeometry()},wrap(){this.persistGeometry()},hidden:{deep:true,handler(){this.persistGeometry()}},mode(){this.persistGeometry()},groupField(){this.persistGeometry()}
 },
 mounted(){this.resizeMove=e=>this.resizeColumn(e);this.resizeEnd=()=>this.finishResize();window.addEventListener('pointermove',this.resizeMove);window.addEventListener('pointerup',this.resizeEnd);this.beforeExit=e=>{if(this.dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',this.beforeExit)},
 beforeUnmount(){this.stateSeq++;this.fillSeq++;this.menuSeq++;this.editorSeq++;window.removeEventListener('pointermove',this.resizeMove);window.removeEventListener('pointerup',this.resizeEnd);window.removeEventListener('beforeunload',this.beforeExit)},
 methods:{
  toolbarAction(action){
   const {id,value}=action;
   if(id==='layout'){
    if(value==='table'||value==='cards'){this.mode=value;this.$emit('table-action',{id:'mode',value:'data'})}
    else this.$emit('table-action',{id:'mode',value});
   }
   else if(id==='fill-selected')this.openFill();
   else if(id==='columns')this.columnsOpen=true;
   else if(id==='density')this.density=value;
   else if(id==='wrap')this.wrap=!this.wrap;
   else if(id==='group')this.groupField=value;
   else if(id==='reset-geometry')this.resetGeometry();
   else if(id==='clear-selection')this.selected=[];
   else if(id==='save')this.saveAll();
   else if(id==='discard')this.discard();
   else if(id==='diagnostics')this.diagnosticsOpen=true;
   else this.$emit('table-action',action);
  },
  fillSignature(){return JSON.stringify({drafts:this.drafts,revision:this.spec.revision,rows:this.rows.map(r=>[r.key,r.revision])})},
  async openFill(){
   if(this.saving||this.loadingEditor||!this.spec.capabilities.update||!this.selected.length||this.selected.length>100)return;
   if(this.editor&&!this.stageCell())return;
   const selected=this.rows.filter(r=>this.selected.includes(r.key));if(!selected.length)return;
   const name=this.fillFields.find(f=>f.name===this.activeCell?.field)?.name||this.fillFields[0]?.name;
   if(!name){this.error='В этом представлении нет обычных полей для заполнения';return}
   this.fill={rows:selected,name,field:null,value:null,preview:null,error:'',busy:false,signature:''};
   await this.loadFillField();
  },
  closeFill(){if(this.fill?.busy)return;this.fillSeq++;this.fill=null},
  async loadFillField(){
   const f=this.fill;if(!f)return;f.preview=null;f.error='';f.field=null;f.busy=true;const seq=++this.fillSeq;
   try{const row=f.rows[0],d=this.drafts[row.key];const e=await api.request('/cell-editor',{project:this.project,target:this.target,key:row.key,field:f.name,revision:d?.revision||row.revision,pending:d?.values||{}},'POST');
    if(seq!==this.fillSeq||this.fill!==f)return;f.field=e.field;f.value=Object.hasOwn(d?.values||{},f.name)?d.values[f.name]:e.value;
   }catch(e){if(seq===this.fillSeq)f.error=e.message}finally{if(seq===this.fillSeq)f.busy=false}
  },
  changeFill(value){if(!this.fill)return;this.fill.value=value;this.fill.preview=null},
  async previewFill(){
   const f=this.fill;if(!f||f.busy||!f.field)return;f.busy=true;f.error='';f.preview=null;const seq=++this.fillSeq;
   const signature=this.fillSignature();
   try{const records=f.rows.map(row=>{const d=this.drafts[row.key];return {key:row.key,revision:d?.revision||row.revision,config_revision:d?.config_revision,pending:d?.values||{}}});
    const result=await api.request('/table-fill-preview',{project:this.project,target:this.target,field:f.name,value:f.value,table_revision:this.draftTableRevision||this.spec.revision,records},'POST');
    if(seq!==this.fillSeq||this.fill!==f)return;if(signature!==this.fillSignature())throw Error('Таблица изменилась во время проверки. Повторите предпросмотр.');
    f.preview=result;f.signature=signature;
   }catch(e){if(seq===this.fillSeq)f.error=e.message}finally{if(seq===this.fillSeq)f.busy=false}
  },
  acceptFill(){
   const f=this.fill;if(!f?.preview||f.busy)return;
   if(f.signature!==this.fillSignature()){f.error='Буфер или таблица изменились. Повторите предпросмотр.';f.preview=null;return}
   // Stage in a detached copy; a malformed value cannot apply only a prefix.
   const oldDrafts=this.drafts,oldRev=this.draftTableRevision;this.drafts=JSON.parse(JSON.stringify(oldDrafts));
   for(const item of f.preview.items){this.editor={...item,original:item.original,value:item.value};
    if(!this.stageCell()){this.drafts=oldDrafts;this.draftTableRevision=oldRev;this.editor=null;f.error=this.error;return}}
   this.notice='Заполнение добавлено в буфер: '+f.preview.items.length+' строк. Нажмите «Сохранить изменения», чтобы записать в TACTIC.';this.closeFill();
  },
  fillText(value){return value===null?'NULL':typeof value==='object'?JSON.stringify(value):String(value??'')},
  toggleColumn(name){this.hidden=this.hidden.includes(name)?this.hidden.filter(n=>n!==name):[...this.hidden,name]},
  cellOpen(row,cell){if(cell.record_detail){this.$emit('inspect',row);return}if(cell.open_mode==='tab'){this.$emit('open',{id:cell.target});return}if(cell.inline)this.expanded[row.key]=this.expanded[row.key]===cell.target?null:cell.target;else this.cellWindow={target:cell.target,title:cell.text}},
  originalText(row,f){if(row.cells?.[f.name])return row.cells[f.name].text;if(!f.supported&&!f.storage)return 'Не перенесено';const v=row.values[f.name];if(v===null||v===undefined)return '—';if(f.renderer==='gantt')return (v.bars||[]).map(b=>(b.start||'—')+' → '+(b.end||'—')).join('; ');if(typeof v==='object')return JSON.stringify(v);if(f.kind==='boolean')return v?'Да':'Нет';return f.options?.find(o=>String(o.value)===String(v))?.label||String(v)},
  hasDraft(row,f){return Object.prototype.hasOwnProperty.call(this.drafts[row.key]?.values||{},f.name)},
  displayRow(row){
   const d=this.drafts[row.key];if(!d)return row;
   const cells={...(row.cells||{})};
   for(const [name,value] of Object.entries(d.values)){
    const field=d.fields[name],option=field?.options?.find(o=>String(o.value)===String(value));
    const old=cells[name];let text=value===null?'NULL':typeof value==='object'?JSON.stringify(value):String(value??'');
    if(option)text=option.label;
    if(old?.kind==='status')cells[name]={kind:'status',text,color:option?.color||null};
    else if(old?.kind==='login')cells[name]={kind:'login',text,login:value};
    else if(old?.kind==='color')cells[name]={kind:'color',text,color:/^#[0-9a-f]{3,8}$/i.test(text)?text:null};
    else if(field?.kind==='boolean')cells[name]={kind:'boolean',text:value?'Да':'Нет',checked:Boolean(value)};
    else cells[name]={kind:'text',text};
   }
   return {...row,values:{...row.values,...d.values},cells};
  },
  cell(row,f){return this.originalText(this.displayRow(row),f)},
  cardTitle(row){return row?.values.name||row?.values.title||row?.values.code||row?.key||this.spec.title||'Таблица'},
  summary(field){return (this.summaries||[]).find(s=>s.field===field.name)},
  widthNumber(f){const local=this.widths[f.name];if(Number.isFinite(local))return local;const v=String(f.width||'');if(/^\d+(?:\.\d+)?(?:px)?$/.test(v))return Math.max(64,Math.min(1200,parseFloat(v)));return f.kind==='boolean'?90:f.provider==='status'?160:f.kind==='date'?155:f.name==='description'?300:200},
  columnStyle(f){const w=this.widthNumber(f);let left=42*(this.flags.show_select?1:0);for(const col of this.fields){if(col.name===f.name)break;if(this.pinned.includes(col.name))left+=this.widthNumber(col)}return {width:w+'px',minWidth:w+'px',maxWidth:w+'px',textAlign:f.justify||undefined,...(this.pinned.includes(f.name)?{position:'sticky',left:left+'px',zIndex:2}:{})}},
  async restoreGeometry(){
   const seq=++this.stateSeq;this.stateReady=false;this.stateLoading=true;
   try{const result=await uiState.load({project:this.project,target:this.target,scope:'geometry'});if(seq!==this.stateSeq)return;const p=result.value;
    if(p){const names=new Set(this.spec.fields.map(f=>f.name));this.widths=p.widths;this.pinned=p.pinned;this.columnOrder=[...p.order,...this.spec.fields.map(f=>f.name).filter(n=>!p.order.includes(n))];this.hidden=p.hidden;this.density=p.density;this.wrap=p.wrap;this.groupField=p.groupField;this.mode=p.mode}
    await this.$nextTick();if(seq===this.stateSeq)this.stateReady=true;
   }catch(e){if(seq===this.stateSeq)this.error='Настройки таблицы не восстановлены: '+e.message}finally{if(seq===this.stateSeq)this.stateLoading=false}
  },
  persistGeometry(){if(this.stateReady&&!this.stateLoading&&this.allowWrites)uiState.schedule({project:this.project,target:this.target,scope:'geometry'},{widths:this.widths,pinned:this.pinned,order:this.columnOrder,hidden:this.hidden,density:this.density,wrap:this.wrap,groupField:this.groupField,mode:this.mode})},
  resetGeometry(){this.widths={};this.pinned=[];this.columnOrder=this.spec.fields.map(f=>f.name);this.hidden=this.spec.fields.filter(f=>f.hidden).map(f=>f.name);this.persistGeometry()},
  startResize(e,f){if(e.button!==0)return;e.preventDefault();e.stopPropagation();this.resizeState={name:f.name,x:e.clientX,width:this.widthNumber(f)}},
  resizeColumn(e){if(this.resizeState)this.widths[this.resizeState.name]=Math.max(64,Math.min(1200,this.resizeState.width+e.clientX-this.resizeState.x))},
  finishResize(){if(this.resizeState){this.resizeState=null;this.persistGeometry()}},
  dropColumn(f){const source=this.dragColumn;this.dragColumn=null;if(!source||source===f.name)return;const next=this.columnOrder.filter(n=>n!==source);next.splice(next.indexOf(f.name),0,source);this.columnOrder=next;this.persistGeometry()},
  togglePin(f){this.pinned=this.pinned.includes(f.name)?this.pinned.filter(n=>n!==f.name):[...this.pinned,f.name];this.persistGeometry()},
  toggleAll(){this.selected=this.allSelected?[]:this.rows.map(r=>r.key)},
  selectRow(e,row){const i=this.rows.findIndex(r=>r.key===row.key);if(e.shiftKey&&this.selectionAnchor!==null){const range=this.rows.slice(Math.min(i,this.selectionAnchor),Math.max(i,this.selectionAnchor)+1).map(r=>r.key);this.selected=Array.from(new Set([...this.selected,...range]))}else{this.selected=this.selected.includes(row.key)?this.selected.filter(k=>k!==row.key):[...this.selected,row.key];this.selectionAnchor=i}},
  async context(event,row,field=null){
   if(!this.flags.show_context_menu||event.shiftKey||event.target?.closest('input,textarea,select,[contenteditable=true]'))return;
   event.preventDefault();event.stopPropagation();if(row&&this.flags.show_select&&!this.selected.includes(row.key))this.selected=[row.key];
   api.setContext?.(this.project,this.target);
   const seq=++this.menuSeq,rect=event.currentTarget.getBoundingClientRect();
   this.menu={x:event.clientX||rect.left,y:event.clientY||rect.bottom,row,field,title:field?.label||this.cardTitle(row),loading:true,items:[]};
   try{const d=await api.request('/context-menu',{project:this.project,target:this.target,scope:field?'column':'row',field:field?.name,key:row?.key,pending_cell:Boolean(this.editor)||this.changedCells>0});
    if(seq===this.menuSeq&&this.menu){d.items=(d.items||[]).map(item=>item.id==='save_cell'?{...item,label:'Сохранить изменения таблицы',enabled:!this.saving}:item);this.menu={...this.menu,...d,loading:false}}}
   catch(error){if(seq===this.menuSeq&&this.menu)this.menu={...this.menu,loading:false,error:error.message}}
  },
  menuKey(e,row,field=null){if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){e.preventDefault();this.context({currentTarget:e.currentTarget,target:e.currentTarget,preventDefault(){},stopPropagation(){}},row,field)}},
  act(item){const {row,field}=this.menu;this.menu=null;this.menuSeq++;const action=item.id;
   if(action==='inspect')this.$emit('inspect',row);
   else if(action==='edit'){if(this.selected.length>1&&this.selected.includes(row.key))this.$emit('edit-selected');else this.$emit('edit',row)}
   else if(['files','history','subscription','state'].includes(action))this.$emit('inspect',{...row,_section:action==='state'?'history':action});
   else if(action==='save_cell')this.saveAll();
   else if(action==='sort_asc'||action==='sort_desc')this.$emit('sort',{field:field.name,direction:action==='sort_asc'?'asc':'desc'});
   else if(action==='group_page')this.groupField=field.name;else if(action==='ungroup')this.groupField='';
   else if(action==='hide_column')this.hidden=[...new Set([...this.hidden,field.name])];
   else if(action==='restore_columns')this.hidden=this.spec.fields.filter(f=>f.hidden).map(f=>f.name);
   else if(action==='definition')this.definition=field?.name||'';else if(action==='columns')this.designer=field?.name||'';else if(action==='audit')this.audit=true;
  },
  numericKey(value){const m=/^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(String(value).trim());if(!m)return null;let digits=(m[2]+(m[3]||'')).replace(/^0+/,'');if(!digits)return '0';let exponent=Number(m[4]||0)-(m[3]||'').length;if(!Number.isSafeInteger(exponent))return null;const trailing=/0+$/.exec(digits)?.[0].length||0;digits=digits.slice(0,digits.length-trailing);return (m[1]==='-'?'-':'')+digits+'e'+(exponent+trailing)},
  equalValue(a,b,field){if(a===b)return true;if(a===null||b===null)return false;if(['integer','number','float','decimal'].includes(field.kind)&&a!==''&&b!==''){const x=this.numericKey(a),y=this.numericKey(b);if(x!==null&&y!==null)return x===y}return JSON.stringify(a)===JSON.stringify(b)},
  async inline(row,field){
   api.setContext?.(this.project,this.target);api.action?.('cell.edit',{project:this.project,target:this.target,field:field.name});
   if(this.saving||this.loadingEditor||this.fill)return;
   if(this.editor&&!this.stageCell())return;
   if(field.renderer==='work-hours'){this.hours={row,field:field.name};return}
   if(!this.spec.capabilities.update){this.error='Запись отключена для этой таблицы';return}
   this.error='';this.notice='';this.loadingEditor=true;const seq=++this.editorSeq;
   try{
    const draft=this.drafts[row.key];
    const result=await api.request('/cell-editor',{project:this.project,target:this.target,key:row.key,field:field.name,revision:draft?.revision||row.revision,pending:draft?.values||{}},'POST');
    if(seq!==this.editorSeq)return;
    if(draft&&draft.config_revision!==result.config_revision)throw Error('Конфигурация редакторов изменилась. Сбросьте либо перепроверьте буфер.');
    this.editor={key:row.key,field:result.field,revision:result.revision,config_revision:result.config_revision,table_revision:result.table_revision,original:result.value,value:draft&&Object.prototype.hasOwnProperty.call(draft.values,field.name)?draft.values[field.name]:result.value};
    this.activeCell={key:row.key,field:field.name};
    this.$nextTick(()=>this.$el.querySelector('.inline-editor input,.inline-editor textarea,.inline-editor select')?.focus());
   }catch(e){this.error=e.message}finally{if(seq===this.editorSeq)this.loadingEditor=false}
  },
  stageCell(){
   const e=this.editor;if(!e)return true;
   let value=e.value;
   if(e.field.kind==='json'&&typeof value==='string'&&value.trim()){try{value=JSON.parse(value)}catch{this.error='Некорректный JSON: исправьте значение перед применением';return false}}
   let draft=this.drafts[e.key];
   if(!draft)draft={key:e.key,revision:e.revision,config_revision:e.config_revision,values:{},base:{},fields:{},error:''};
   const original=Object.prototype.hasOwnProperty.call(draft.base,e.field.name)?draft.base[e.field.name]:e.original;
   if(this.equalValue(value,original,e.field)){delete draft.values[e.field.name];delete draft.base[e.field.name];delete draft.fields[e.field.name]}
   else{draft.values[e.field.name]=value;draft.base[e.field.name]=original;draft.fields[e.field.name]=e.field}
   if(Object.keys(draft.values).length)this.drafts[e.key]=draft;else delete this.drafts[e.key];
   if(this.changedCells&&!this.draftTableRevision)this.draftTableRevision=e.table_revision;
   if(!this.changedCells)this.draftTableRevision=null;
   api.action?.('cell.stage',{project:this.project,target:this.target,field:e.field.name,count:this.changedCells});
   this.editor=null;this.error='';return true;
  },
  cancelEditor(){api.action?.('cell.cancel',{project:this.project,target:this.target,field:this.editor?.field?.name||''});this.editorSeq++;this.editor=null;this.loadingEditor=false},
  discard(){if(this.dirty&&!confirm('Отменить все несохранённые изменения таблицы?'))return;api.action?.('buffer.discard',{project:this.project,target:this.target,count:this.changedCells});this.drafts={};this.draftTableRevision=null;this.editor=null;this.error='';this.notice='Изменения отменены. База не изменялась.'},
  async saveAll(){
   if(this.saving||this.fill||!this.stageCell()||!this.changedCells)return;
   api.action?.('buffer.save',{project:this.project,target:this.target,count:this.changedCells});
   this.saving=true;this.error='';this.notice='';
   const records=this.changedRows.map(d=>({key:d.key,revision:d.revision,config_revision:d.config_revision,values:{...d.values}}));
   try{const result=await api.request('/table-changes',{project:this.project,target:this.target,table_revision:this.draftTableRevision,records},'POST');this.drafts={};this.draftTableRevision=null;this.notice=`Сохранено: ${result.updated} строк, ${result.cells} ячеек.`;this.$emit('dirty',false);this.$emit('changed')}
   catch(e){this.error=e.message+' Буфер изменений сохранён.';const key=e.details?.key;if(key&&this.drafts[key])this.drafts[key].error=e.message}
   finally{this.saving=false}
  },
  gridKey(e,row,field){
   this.menuKey(e,row);if(e.defaultPrevented||e.target.closest('input,textarea,select,button,a,[contenteditable=true]'))return;
   if(e.key==='Enter'||e.key==='F2'){e.preventDefault();this.inline(row,field);return}
   let ri=this.rows.findIndex(r=>r.key===row.key),ci=this.fields.findIndex(f=>f.name===field.name);
   if(e.key==='ArrowDown')ri++;else if(e.key==='ArrowUp')ri--;else if(e.key==='ArrowRight')ci++;else if(e.key==='ArrowLeft')ci--;
   else if(e.key==='Home'){ci=0;if(e.ctrlKey)ri=0}else if(e.key==='End'){ci=this.fields.length-1;if(e.ctrlKey)ri=this.rows.length-1}else return;
   e.preventDefault();ri=Math.max(0,Math.min(this.rows.length-1,ri));ci=Math.max(0,Math.min(this.fields.length-1,ci));
   this.activeCell={key:this.rows[ri].key,field:this.fields[ci].name};
   this.$nextTick(()=>Array.from(this.$el.querySelectorAll('td[data-field]')).find(td=>td.dataset.row===this.activeCell.key&&td.dataset.field===this.activeCell.field)?.focus());
  },
  editorKey(e){if(e.key==='Escape'){e.preventDefault();e.stopPropagation();this.cancelEditor()}else if(e.key==='Enter'&&!['textarea','json'].includes(this.editor?.field.kind)&&!e.shiftKey){e.preventDefault();this.stageCell()}},
  hotkeys(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();e.stopPropagation();this.saveAll()}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { resolveComponent: _resolveComponent, createVNode: _createVNode, renderSlot: _renderSlot, vShow: _vShow, createElementVNode: _createElementVNode, withDirectives: _withDirectives, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createTextVNode: _createTextVNode, renderList: _renderList, Fragment: _Fragment, normalizeStyle: _normalizeStyle, withModifiers: _withModifiers, normalizeClass: _normalizeClass, createBlock: _createBlock, vModelSelect: _vModelSelect, withKeys: _withKeys, Teleport: _Teleport } = _Vue

    const _component_TableToolbar = _resolveComponent("TableToolbar")
    const _component_FieldInput = _resolveComponent("FieldInput")
    const _component_WidgetCell = _resolveComponent("WidgetCell")
    const _component_WidgetHost = _resolveComponent("WidgetHost")
    const _component_TableColumns = _resolveComponent("TableColumns")
    const _component_WorkHoursPanel = _resolveComponent("WorkHoursPanel")
    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_WidgetDefinition = _resolveComponent("WidgetDefinition")
    const _component_ConfigAudit = _resolveComponent("ConfigAudit")
    const _component_ViewDesigner = _resolveComponent("ViewDesigner")

    return (_openBlock(), _createElementBlock("section", {
      class: _normalizeClass(["table-region native-grid", ['density-'+density,{'wrap-cells':wrap,'is-resizing':resizeState}]]),
      "aria-busy": busy||saving,
      onKeydown: hotkeys,
      "data-table-target": target
    }, [
      _createVNode(_component_TableToolbar, {
        spec: spec,
        total: total,
        "selected-count": selected.length,
        busy: busy||saving,
        "allow-writes": allowWrites,
        "search-open": searchOpen,
        "filter-count": filterCount,
        presentation: presentation,
        "display-mode": mode,
        "record-state": recordState,
        density: density,
        wrap: wrap,
        "group-field": groupField,
        dirty: dirty,
        saving: saving,
        onAction: toolbarAction
      }, null, 8, ["spec", "total", "selected-count", "busy", "allow-writes", "search-open", "filter-count", "presentation", "display-mode", "record-state", "density", "wrap", "group-field", "dirty", "saving", "onAction"]),
      _withDirectives(_createElementVNode("div", { class: "table-search-panel" }, [_renderSlot($slots, "filters")], 512), [[_vShow, searchOpen&&(flags.show_search!==false||flags.show_keyword_search!==false)]]),
      _renderSlot($slots, "status"),
      dirty
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "grid-save-bar",
            role: "status"
          }, [
            _createElementVNode("span", { class: "pending-indicator" }),
            _createElementVNode("strong", null, _toDisplayString(changedCells) + " ячеек · " + _toDisplayString(changedRows.length) + " строк", 1),
            editor
              ? (_openBlock(), _createElementBlock("span", { key: 0 }, "Редактор открыт"))
              : _createCommentVNode("", true),
            pendingOutsidePage
              ? (_openBlock(), _createElementBlock("small", { key: 1 }, "Вне страницы: " + _toDisplayString(pendingOutsidePage) + " строк", 1))
              : _createCommentVNode("", true),
            _createElementVNode("span", { class: "spacer" }),
            _createElementVNode("button", {
              disabled: saving,
              onClick: discard
            }, "Отменить", 8, ["disabled", "onClick"]),
            _createElementVNode("button", {
              class: "primary",
              disabled: saving||loadingEditor,
              onClick: saveAll
            }, [_createTextVNode(_toDisplayString(saving?'Сохранение…':'Сохранить изменения') + " ", 1), _createElementVNode("kbd", null, "Ctrl S")], 8, ["disabled", "onClick"])
          ]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error grid-feedback",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice grid-feedback",
            role: "status"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      loadingEditor
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "grid-feedback muted"
          }, "Загрузка редактора из widget_config…"))
        : _createCommentVNode("", true),
      _withDirectives(_createElementVNode("div", { class: "grid-content" }, [(mode==='table')
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "table-scroll grid-viewport"
          }, [_createElementVNode("table", {
            class: "tactic-data-grid",
            role: "grid",
            "aria-rowcount": total,
            style: _normalizeStyle({width:gridWidth+'px',minWidth:'100%'})
          }, [
            _createElementVNode("colgroup", null, [(flags.show_select)
              ? (_openBlock(), _createElementBlock("col", {
                  key: 0,
                  style: {"width":"42px"}
                }))
              : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
              return (_openBlock(), _createElementBlock("col", {
                key: f.name,
                style: _normalizeStyle({width:widthNumber(f)+'px'})
              }, null, 4))
            }), 128))]),
            (flags.show_header)
              ? (_openBlock(), _createElementBlock("thead", { key: 0 }, [_createElementVNode("tr", null, [(flags.show_select)
                  ? (_openBlock(), _createElementBlock("th", {
                      key: 0,
                      class: "check-cell pinned-check"
                    }, [_createElementVNode("input", {
                      type: "checkbox",
                      checked: allSelected,
                      indeterminate: selected.length>0&&!allSelected,
                      onChange: toggleAll,
                      "aria-label": "Выбрать всю страницу"
                    }, null, 40, ["checked", "indeterminate", "onChange"])]))
                  : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
                  return (_openBlock(), _createElementBlock("th", {
                    key: f.name,
                    style: _normalizeStyle(columnStyle(f)),
                    class: _normalizeClass({'pinned-column':pinned.includes(f.name)}),
                    title: f.handler||f.name,
                    tabindex: "0",
                    onContextmenu: $event => (context($event,null,f)),
                    onKeydown: $event => (menuKey($event,null,f)),
                    draggable: "true",
                    onDragstart: $event => (dragColumn=f.name),
                    onDragover: _withModifiers(() => {}, ["prevent"]),
                    onDrop: _withModifiers($event => (dropColumn(f)), ["prevent"]),
                    onDragend: $event => (dragColumn=null)
                  }, [_createElementVNode("div", { class: "grid-column-heading" }, [_createElementVNode("button", {
                    disabled: !f.storage||f.sortable===false,
                    title: f.sort_reason||'',
                    onClick: $event => ($emit('sort',f.name))
                  }, [_createElementVNode("span", null, _toDisplayString(f.label), 1), (!f.supported)
                    ? (_openBlock(), _createElementBlock("small", {
                        key: 0,
                        class: "unsupported-marker"
                      }, "◦"))
                    : _createCommentVNode("", true)], 8, ["disabled", "title", "onClick"]), _createElementVNode("button", {
                    class: "column-menu-trigger",
                    "aria-label": 'Меню колонки '+f.label,
                    onClick: $event => (context($event,null,f))
                  }, "⋮", 8, ["aria-label", "onClick"])]), _createElementVNode("span", {
                    class: "column-resizer",
                    role: "separator",
                    "aria-orientation": "vertical",
                    "aria-label": 'Ширина '+f.label,
                    onPointerdown: $event => (startResize($event,f)),
                    onClick: _withModifiers(() => {}, ["stop"]),
                    onDblclick: _withModifiers($event => {delete widths[f.name];persistGeometry()}, ["stop"])
                  }, null, 40, ["aria-label", "onPointerdown", "onClick", "onDblclick"])], 46, ["title", "onContextmenu", "onKeydown", "onDragstart", "onDragover", "onDrop", "onDragend"]))
                }), 128))])]))
              : _createCommentVNode("", true),
            _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (group) => {
              return (_openBlock(), _createElementBlock(_Fragment, { key: group.key }, [groupField
                ? (_openBlock(), _createElementBlock("tr", {
                    key: 0,
                    class: "group-row"
                  }, [_createElementVNode("td", { colspan: fields.length+(flags.show_select?1:0) }, [_createTextVNode(_toDisplayString(group.key) + " ", 1), _createElementVNode("span", { class: "counter" }, _toDisplayString(group.rows.length), 1), _createElementVNode("small", null, "Текущая страница")], 8, ["colspan"])]))
                : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.rows, (row) => {
                return (_openBlock(), _createElementBlock(_Fragment, { key: row.key }, [_createElementVNode("tr", {
                  class: _normalizeClass({selected:selected.includes(row.key),'modified-row':drafts[row.key],'conflict-row':drafts[row.key]?.error}),
                  onContextmenu: $event => (context($event,row)),
                  tabindex: "0",
                  onKeydown: $event => (menuKey($event,row)),
                  "data-key": row.key
                }, [(flags.show_select)
                  ? (_openBlock(), _createElementBlock("td", {
                      key: 0,
                      class: "check-cell pinned-check"
                    }, [_createElementVNode("input", {
                      type: "checkbox",
                      checked: selected.includes(row.key),
                      onClick: $event => (selectRow($event,row)),
                      "aria-label": "Выбрать запись"
                    }, null, 8, ["checked", "onClick"])]))
                  : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
                  return (_openBlock(), _createElementBlock("td", {
                    key: f.name,
                    class: _normalizeClass({'not-supported':!f.supported,'modified-cell':hasDraft(row,f),'active-cell':activeCell?.key===row.key&&activeCell?.field===f.name,'pinned-column':pinned.includes(f.name)}),
                    style: _normalizeStyle(columnStyle(f)),
                    "data-row": row.key,
                    "data-field": f.name,
                    title: drafts[row.key]?.error||f.reason||cell(row,f),
                    tabindex: "0",
                    onFocus: $event => (activeCell={key:row.key,field:f.name}),
                    onKeydown: $event => (gridKey($event,row,f)),
                    onDblclick: _withModifiers($event => (inline(row,f)), ["stop"])
                  }, [(editor?.key===row.key&&editor.field.name===f.name)
                    ? (_openBlock(), _createElementBlock("div", {
                        key: 0,
                        class: "inline-editor",
                        onKeydown: editorKey
                      }, [_createVNode(_component_FieldInput, {
                        field: editor.field,
                        modelValue: editor.value,
                        "onUpdate:modelValue": $event => ((editor.value) = $event)
                      }, null, 8, ["field", "modelValue", "onUpdate:modelValue"]), _createElementVNode("div", { class: "inline-actions" }, [(editor.field.nullable)
                        ? (_openBlock(), _createElementBlock("button", {
                            key: 0,
                            class: "null-input-button",
                            onClick: $event => (editor.value=null),
                            title: "Явное пустое значение"
                          }, "NULL", 8, ["onClick"]))
                        : _createCommentVNode("", true), _createElementVNode("button", {
                        class: "primary",
                        onClick: stageCell,
                        title: "Применить в буфер, без записи в БД"
                      }, "Применить", 8, ["onClick"]), _createElementVNode("button", {
                        onClick: cancelEditor,
                        "aria-label": "Отменить ввод"
                      }, "×", 8, ["onClick"])]), _createElementVNode("small", { class: "editor-source" }, "edit → edit_item · Ctrl S — сохранить")], 40, ["onKeydown"]))
                    : (f.renderer==='work-hours')
                      ? (_openBlock(), _createElementBlock("button", {
                          key: 1,
                          class: "text-button",
                          onClick: _withModifiers($event => (hours={row,field:f.name}), ["stop"])
                        }, "Открыть рабочее время", 8, ["onClick"]))
                      : (_openBlock(), _createBlock(_component_WidgetCell, {
                          key: 2,
                          row: displayRow(row),
                          field: f,
                          fallback: cell(row,f),
                          onOpen: $event => (cellOpen(row,$event))
                        }, null, 8, ["row", "field", "fallback", "onOpen"])), (hasDraft(row,f))
                    ? (_openBlock(), _createElementBlock("span", {
                        key: 3,
                        class: "dirty-corner",
                        "aria-label": "Не сохранено"
                      }))
                    : _createCommentVNode("", true)], 46, ["data-row", "data-field", "title", "onFocus", "onKeydown", "onDblclick"]))
                }), 128))], 42, ["onContextmenu", "onKeydown", "data-key"]), (expanded[row.key])
                  ? (_openBlock(), _createElementBlock("tr", {
                      key: 0,
                      class: "expanded-widget-row"
                    }, [_createElementVNode("td", { colspan: fields.length+(flags.show_select?1:0) }, [_createElementVNode("button", {
                      class: "text-button",
                      onClick: $event => (expanded[row.key]=null)
                    }, "Свернуть", 8, ["onClick"]), _createVNode(_component_WidgetHost, {
                      project: project,
                      target: expanded[row.key],
                      user: {allow_writes:spec.capabilities.update,allow_uploads:false},
                      onOpen: $event => ($emit('open',$event)),
                      onChanged: $event => ($emit('changed'))
                    }, null, 8, ["project", "target", "user", "onOpen", "onChanged"])], 8, ["colspan"])]))
                  : _createCommentVNode("", true)], 64))
              }), 128))], 64))
            }), 128)), (!rows.length)
              ? (_openBlock(), _createElementBlock("tr", { key: 0 }, [_createElementVNode("td", {
                  colspan: fields.length+1,
                  class: "table-empty"
                }, [_createElementVNode("strong", null, _toDisplayString(busy?'Загрузка данных…':(spec.table_options?.empty_message||'Нет записей')), 1), (!busy)
                  ? (_openBlock(), _createElementBlock("span", { key: 0 }, "Измените фильтры или добавьте запись через форму TACTIC."))
                  : _createCommentVNode("", true)], 8, ["colspan"])]))
              : _createCommentVNode("", true)]),
            (summaries?.length)
              ? (_openBlock(), _createElementBlock("tfoot", { key: 1 }, [_createElementVNode("tr", null, [(flags.show_select)
                  ? (_openBlock(), _createElementBlock("td", { key: 0 }))
                  : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
                  return (_openBlock(), _createElementBlock("td", {
                    key: f.name,
                    class: "summary-cell"
                  }, [(summary(f))
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("small", null, _toDisplayString(summary(f).label), 1), _createTextVNode(_toDisplayString(summary(f).cell.text), 1)], 64))
                    : _createCommentVNode("", true)]))
                }), 128))])]))
              : _createCommentVNode("", true)
          ], 12, ["aria-rowcount"])]))
        : (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "cards-scroll"
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (group) => {
            return (_openBlock(), _createElementBlock("section", { key: group.key }, [groupField
              ? (_openBlock(), _createElementBlock("h3", { key: 0 }, _toDisplayString(group.key) + " · " + _toDisplayString(group.rows.length), 1))
              : _createCommentVNode("", true), _createElementVNode("div", { class: "entity-cards" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.rows, (row) => {
              return (_openBlock(), _createElementBlock("article", {
                key: row.key,
                class: _normalizeClass(["entity-card", {selected:selected.includes(row.key)}]),
                onContextmenu: $event => (context($event,row))
              }, [_createElementVNode("header", null, [(flags.show_select)
                ? (_openBlock(), _createElementBlock("input", {
                    key: 0,
                    type: "checkbox",
                    checked: selected.includes(row.key),
                    onClick: $event => (selectRow($event,row))
                  }, null, 8, ["checked", "onClick"]))
                : _createCommentVNode("", true), _createElementVNode("button", {
                class: "text-button",
                onClick: $event => ($emit('inspect',row))
              }, _toDisplayString(cardTitle(row)), 9, ["onClick"])]), _createElementVNode("dl", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
                return (_openBlock(), _createElementBlock(_Fragment, { key: f.name }, [_createElementVNode("dt", null, _toDisplayString(f.label), 1), _createElementVNode("dd", null, [(f.renderer==='work-hours')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "text-button",
                      onClick: $event => (hours={row,field:f.name})
                    }, "Рабочее время", 8, ["onClick"]))
                  : (_openBlock(), _createBlock(_component_WidgetCell, {
                      key: 1,
                      row: displayRow(row),
                      field: f,
                      fallback: cell(row,f),
                      onOpen: $event => (cellOpen(row,$event))
                    }, null, 8, ["row", "field", "fallback", "onOpen"]))])], 64))
              }), 128))]), _createElementVNode("button", {
                disabled: !spec.capabilities.update,
                onClick: $event => ($emit('edit',row))
              }, "Редактировать", 8, ["disabled", "onClick"])], 42, ["onContextmenu"]))
            }), 128))])]))
          }), 128))])), _createElementVNode("footer", { class: "pager grid-footer" }, [
        _createElementVNode("span", null, [_createTextVNode(_toDisplayString(total??'—') + " записей ", 1), (selected.length)
          ? (_openBlock(), _createElementBlock("span", { key: 0 }, "· Выбрано " + _toDisplayString(selected.length), 1))
          : _createCommentVNode("", true)]),
        (groupField||summaries?.length)
          ? (_openBlock(), _createElementBlock("small", { key: 0 }, "Группы и итоги страницы · только сохранённые данные"))
          : _createCommentVNode("", true),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("small", { class: "grid-keyboard-hint" }, "F2 — ввод · Enter — применить · Ctrl S — сохранить"),
        (flags.show_search_limit)
          ? (_openBlock(), _createElementBlock("button", {
              key: 1,
              disabled: busy||saving||offset===0,
              onClick: $event => ($emit('page',Math.max(0,offset-limit))),
              "aria-label": "Предыдущая страница"
            }, "←", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true),
        _createElementVNode("span", null, _toDisplayString(rows.length?offset+1:0) + "–" + _toDisplayString(offset+rows.length), 1),
        (flags.show_search_limit)
          ? (_openBlock(), _createElementBlock("button", {
              key: 2,
              disabled: busy||saving||rows.length<limit||(total!==null&&offset+rows.length>=total),
              onClick: $event => ($emit('page',offset+limit)),
              "aria-label": "Следующая страница"
            }, "→", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true)
      ])], 512), [[_vShow, presentation==='data']]),
      (presentation!=='data')
        ? _renderSlot($slots, "alternate", { key: 4 })
        : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [fill
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop",
            onClick: _withModifiers(closeFill, ["self"])
          }, [_createElementVNode("section", {
            class: "modal fill-selected-dialog",
            role: "dialog",
            "aria-modal": "true",
            "aria-label": "Заполнить выбранные ячейки",
            onKeydown: _withKeys(_withModifiers(closeFill, ["stop"]), ["esc"])
          }, [_createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, _toDisplayString(fill.rows.length) + " выбранных строк · CellEditWdg", 1), _createElementVNode("h2", null, "Заполнить выбранные ячейки")]), _createElementVNode("button", {
            disabled: fill.busy,
            "aria-label": "Закрыть заполнение",
            onClick: closeFill
          }, "×", 8, ["disabled", "onClick"])]), _createElementVNode("div", { class: "form-scroll" }, [
            _createElementVNode("p", { class: "notice" }, "Одинаковое значение проверяется по конфигурации каждой строки. Сначала предпросмотр, затем буфер; запись только через Save Changes."),
            _createElementVNode("label", null, [_createTextVNode("Поле"), _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": $event => ((fill.name) = $event),
              disabled: fill.busy,
              onChange: loadFillField,
              "aria-label": "Поле заполнения"
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fillFields, (f) => {
              return (_openBlock(), _createElementBlock("option", {
                key: f.name,
                value: f.name
              }, _toDisplayString(f.label) + " · " + _toDisplayString(f.name), 9, ["value"]))
            }), 128))], 40, ["onUpdate:modelValue", "disabled", "onChange"]), [[_vModelSelect, fill.name]])]),
            (fill.field)
              ? (_openBlock(), _createElementBlock("div", { key: 0 }, [_createElementVNode("label", null, "Значение"), _createVNode(_component_FieldInput, {
                  field: fill.field,
                  "model-value": fill.value,
                  "onUpdate:modelValue": changeFill
                }, null, 8, ["field", "model-value", "onUpdate:modelValue"]), (fill.field.nullable)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "null-button",
                      disabled: fill.busy,
                      onClick: $event => (changeFill(null))
                    }, "Установить NULL", 8, ["disabled", "onClick"]))
                  : _createCommentVNode("", true)]))
              : _createCommentVNode("", true),
            (fill.error)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 1,
                  class: "error",
                  role: "alert"
                }, _toDisplayString(fill.error), 1))
              : _createCommentVNode("", true),
            (fill.preview)
              ? (_openBlock(), _createElementBlock("div", {
                  key: 2,
                  class: "fill-preview"
                }, [_createElementVNode("p", null, _toDisplayString(fill.preview.notice), 1), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Запись"), _createElementVNode("th", null, "Было / буфер"), _createElementVNode("th", null, "Станет")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fill.preview.items, (item) => {
                  return (_openBlock(), _createElementBlock("tr", { key: item.key }, [_createElementVNode("td", null, _toDisplayString(item.key), 1), _createElementVNode("td", null, _toDisplayString(fillText(Object.hasOwn(drafts[item.key]?.values||{},fill.name)?drafts[item.key].values[fill.name]:item.original)), 1), _createElementVNode("td", null, _toDisplayString(fillText(item.value)), 1)]))
                }), 128))])])])]))
              : _createCommentVNode("", true)
          ]), _createElementVNode("footer", null, [_createElementVNode("button", {
            disabled: fill.busy,
            onClick: closeFill
          }, "Отмена", 8, ["disabled", "onClick"]), _createElementVNode("button", {
            disabled: fill.busy||!fill.field,
            onClick: previewFill
          }, _toDisplayString(fill.busy?'Проверка…':'Предпросмотр'), 9, ["disabled", "onClick"]), _createElementVNode("button", {
            class: "primary",
            disabled: fill.busy||!fill.preview,
            onClick: acceptFill
          }, "Применить в буфер", 8, ["disabled", "onClick"])])], 40, ["onKeydown"])], 8, ["onClick"]))
        : _createCommentVNode("", true)])),
      columnsOpen
        ? (_openBlock(), _createBlock(_component_TableColumns, {
            key: 5,
            fields: spec.fields,
            hidden: hidden,
            pinned: pinned,
            onClose: $event => (columnsOpen=false),
            onToggle: toggleColumn,
            onPin: togglePin,
            onReset: resetGeometry
          }, null, 8, ["fields", "hidden", "pinned", "onClose", "onToggle", "onPin", "onReset"]))
        : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [diagnosticsOpen
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop",
            onClick: _withModifiers($event => (diagnosticsOpen=false), ["self"])
          }, [_createElementVNode("section", {
            class: "modal table-diagnostics",
            role: "dialog",
            "aria-label": "Ограничения виджетов"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h2", null, "Ограничения виджетов"), _createElementVNode("button", {
              onClick: $event => (diagnosticsOpen=false),
              "aria-label": "Закрыть ограничения"
            }, "×", 8, ["onClick"])]),
            (!spec.diagnostics?.length)
              ? (_openBlock(), _createElementBlock("p", { key: 0 }, "В текущем представлении нет диагностик неподдержанных колонок."))
              : _createCommentVNode("", true),
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(spec.diagnostics, (d, i) => {
              return (_openBlock(), _createElementBlock("div", { key: i }, [_createElementVNode("code", null, _toDisplayString(d.field) + " · " + _toDisplayString(d.handler), 1), _createElementVNode("p", null, _toDisplayString(d.reason), 1)]))
            }), 128)),
            _createElementVNode("small", null, "Отсутствие диагностик не означает полного совпадения всех пользовательских обработчиков с legacy.")
          ])], 8, ["onClick"]))
        : _createCommentVNode("", true)])),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [
        cellWindow
          ? (_openBlock(), _createElementBlock("div", {
              key: 0,
              class: "modal-backdrop",
              onClick: _withModifiers($event => (cellWindow=null), ["self"])
            }, [_createElementVNode("section", { class: "modal wide" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, _toDisplayString(cellWindow.title), 1), _createElementVNode("button", { onClick: $event => {cellWindow=null;$emit('changed')} }, "×", 8, ["onClick"])]), _createVNode(_component_WidgetHost, {
              project: project,
              target: cellWindow.target,
              user: {allow_writes:spec.capabilities.update,allow_uploads:false},
              onClose: $event => (cellWindow=null),
              onOpen: $event => ($emit('open',$event)),
              onChanged: $event => ($emit('changed'))
            }, null, 8, ["project", "target", "user", "onClose", "onOpen", "onChanged"])])], 8, ["onClick"]))
          : _createCommentVNode("", true),
        hours
          ? (_openBlock(), _createBlock(_component_WorkHoursPanel, {
              key: 1,
              project: project,
              target: target,
              record: hours.row,
              task: hours.row,
              field: hours.field,
              onClose: $event => (hours=null),
              onChanged: $event => ($emit('changed'))
            }, null, 8, ["project", "target", "record", "task", "field", "onClose", "onChanged"]))
          : _createCommentVNode("", true),
        menu
          ? (_openBlock(), _createBlock(_component_ContextMenu, {
              key: 2,
              menu: menu,
              onAction: act,
              onClose: $event => {menu=null;menuSeq++}
            }, null, 8, ["menu", "onAction", "onClose"]))
          : _createCommentVNode("", true),
        (definition!==null)
          ? (_openBlock(), _createBlock(_component_WidgetDefinition, {
              key: 3,
              project: project,
              target: target,
              field: definition,
              onClose: $event => (definition=null)
            }, null, 8, ["project", "target", "field", "onClose"]))
          : _createCommentVNode("", true),
        audit
          ? (_openBlock(), _createBlock(_component_ConfigAudit, {
              key: 4,
              project: project,
              target: target,
              onClose: $event => (audit=false)
            }, null, 8, ["project", "target", "onClose"]))
          : _createCommentVNode("", true),
        (designer!==null)
          ? (_openBlock(), _createBlock(_component_ViewDesigner, {
              key: 5,
              project: project,
              "search-type": spec.type,
              "initial-view": spec.view,
              "initial-element": designer,
              onClose: $event => (designer=null),
              onSaved: $event => ($emit('view-changed'))
            }, null, 8, ["project", "search-type", "initial-view", "initial-element", "onClose", "onSaved"]))
          : _createCommentVNode("", true)
      ]))
    ], 42, ["aria-busy", "onKeydown", "data-table-target"]))
  }
};
return __component;
})();
const FilterGroup = (function(){
const __component = {
 name:'FilterGroup',props:{node:Object,fields:Array,depth:{type:Number,default:0}},emits:['remove'],
 computed:{count(){const walk=n=>n.children?n.children.reduce((a,x)=>a+walk(x),0):1;return walk(this.node)}},
 methods:{field(n){return this.fields.find(f=>f.name===n.field)||{}},
 operators(n){const k=this.field(n).kind;const ops=[['eq','равно'],['ne','не равно (включая NULL)'],['null','NULL'],['not_null','не NULL'],['empty','пусто'],['not_empty','не пусто'],['in','в списке'],['not_in','не в списке']];if(['text','textarea','select'].includes(k))ops.push(['contains','содержит'],['not_contains','не содержит'],['starts','начинается'],['ends','заканчивается']);if(['integer','number','date','datetime','text'].includes(k))ops.push(['gt','больше'],['gte','не меньше'],['lt','меньше'],['lte','не больше']);return ops},
 changed(n){n.op=['text','textarea','select'].includes(this.field(n).kind)?'contains':'eq';n.value=this.field(n).kind==='boolean'?false:''},
 add(){const f=this.fields[0];if(f)this.node.children.push({field:f.name,op:'eq',value:''})},
 addGroup(){this.node.children.push({op:this.node.op==='and'?'or':'and',children:[]})},
 nullOp(n){return ['null','not_null','empty','not_empty'].includes(n.op)},
 list(n,event){n.value=event.target.value.split(/\r?\n/).filter(x=>x.length>0)},
 type(n){return {integer:'number',number:'number',date:'date',datetime:'datetime-local'}[this.field(n).kind]||'text'}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, vModelSelect: _vModelSelect, withDirectives: _withDirectives, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, resolveComponent: _resolveComponent, createBlock: _createBlock, toDisplayString: _toDisplayString, vModelDynamic: _vModelDynamic } = _Vue

    const _component_FilterGroup = _resolveComponent("FilterGroup")

    return (_openBlock(), _createElementBlock("fieldset", { class: "filter-group" }, [_createElementVNode("legend", null, [_withDirectives(_createElementVNode("select", {
      "onUpdate:modelValue": $event => ((node.op) = $event),
      "aria-label": "Логика группы"
    }, [_createElementVNode("option", { value: "and" }, "И · все условия"), _createElementVNode("option", { value: "or" }, "ИЛИ · любое условие")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, node.op]]), depth
      ? (_openBlock(), _createElementBlock("button", {
          key: 0,
          type: "button",
          onClick: $event => ($emit('remove')),
          "aria-label": "Удалить группу"
        }, "×", 8, ["onClick"]))
      : _createCommentVNode("", true)]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(node.children, (child, i) => {
      return (_openBlock(), _createElementBlock("div", {
        key: i,
        class: "filter-node"
      }, [(child.children)
        ? (_openBlock(), _createBlock(_component_FilterGroup, {
            key: 0,
            node: child,
            fields: fields,
            depth: depth+1,
            onRemove: $event => (node.children.splice(i,1))
          }, null, 8, ["node", "fields", "depth", "onRemove"]))
        : (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "filter-clause"
          }, [
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": $event => ((child.field) = $event),
              onChange: $event => (changed(child)),
              "aria-label": "Поле условия"
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
              return (_openBlock(), _createElementBlock("option", {
                key: f.name,
                value: f.name
              }, _toDisplayString(f.label), 9, ["value"]))
            }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, child.field]]),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": $event => ((child.op) = $event),
              "aria-label": "Оператор условия",
              onChange: $event => (child.value=['in','not_in'].includes(child.op)?[]:child.value)
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(operators(child), (o) => {
              return (_openBlock(), _createElementBlock("option", {
                key: o[0],
                value: o[0]
              }, _toDisplayString(o[1]), 9, ["value"]))
            }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, child.op]]),
            (nullOp(child))
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  class: "muted"
                }, "без значения"))
              : (['in','not_in'].includes(child.op))
                ? (_openBlock(), _createElementBlock("textarea", {
                    key: 1,
                    value: Array.isArray(child.value)?child.value.join('\n'):'',
                    onInput: $event => (list(child,$event)),
                    rows: "2",
                    placeholder: "Одно значение на строку",
                    "aria-label": "Значения списка"
                  }, null, 40, ["value", "onInput"]))
                : (field(child).kind==='boolean')
                  ? _withDirectives((_openBlock(), _createElementBlock("select", {
                      key: 2,
                      "onUpdate:modelValue": $event => ((child.value) = $event),
                      "aria-label": "Значение условия"
                    }, [_createElementVNode("option", { value: true }, "Да", 8, ["value"]), _createElementVNode("option", { value: false }, "Нет", 8, ["value"])], 8, ["onUpdate:modelValue"])), [[_vModelSelect, child.value]])
                  : _withDirectives((_openBlock(), _createElementBlock("input", {
                      key: 3,
                      "onUpdate:modelValue": $event => ((child.value) = $event),
                      type: type(child),
                      step: "any",
                      "aria-label": "Значение условия",
                      placeholder: "Значение"
                    }, null, 8, ["onUpdate:modelValue", "type"])), [[_vModelDynamic, child.value]]),
            _createElementVNode("button", {
              type: "button",
              onClick: $event => (node.children.splice(i,1)),
              "aria-label": "Удалить условие"
            }, "×", 8, ["onClick"])
          ]))]))
    }), 128)), _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
      type: "button",
      disabled: !fields.length||count>=40,
      onClick: add
    }, "+ Условие", 8, ["disabled", "onClick"]), (depth<1)
      ? (_openBlock(), _createElementBlock("button", {
          key: 0,
          type: "button",
          disabled: count>=40,
          onClick: addGroup
        }, "+ Группа", 8, ["disabled", "onClick"]))
      : _createCommentVNode("", true)])]))
  }
};
return __component;
})();
const AdvancedFilter = (function(){

const __component = {
 name:'AdvancedFilter',components:{FilterGroup},props:{value:Object,fields:Array,baseFilter:[String,Array]},emits:['apply'],
 data(){return {draft:JSON.parse(JSON.stringify(this.value||{op:'and',children:[]})),error:''}},
 computed:{usable(){return this.fields.filter(f=>f.storage&&f.kind!=='json')},base(){try{return typeof this.baseFilter==='string'?JSON.parse(this.baseFilter):this.baseFilter||[]}catch{return []}}},
 watch:{value:{deep:true,handler(v){this.draft=JSON.parse(JSON.stringify(v||{op:'and',children:[]}))}}},
 methods:{apply(){this.error='';let count=0;const check=n=>{if(n.children){if(!n.children.length&&n!==this.draft)throw Error('Удалите пустую вложенную группу');n.children.forEach(check)}else{count++;if(!this.usable.some(f=>f.name===n.field))throw Error('Выберите доступное поле')}};try{check(this.draft);if(count>40)throw Error('Не больше 40 условий');this.$emit('apply',JSON.parse(JSON.stringify(this.draft)))}catch(e){this.error=e.message}},clear(){this.draft={op:'and',children:[]};this.apply()}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, resolveComponent: _resolveComponent, createVNode: _createVNode } = _Vue

    const _component_FilterGroup = _resolveComponent("FilterGroup")

    return (_openBlock(), _createElementBlock("details", { class: "advanced-filter" }, [
      _createElementVNode("summary", null, "Составной поиск · И / ИЛИ"),
      _createElementVNode("p", { class: "muted" }, "Дополнительные условия объединяются с фильтром исходного представления. «Не равно» сохраняет NULL-семантику TACTIC. «Содержит» здесь ищет буквальный текст."),
      (base.length)
        ? (_openBlock(), _createElementBlock("details", { key: 0 }, [_createElementVNode("summary", null, "Условия, сохранённые в widget_config"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(base,null,2)), 1)]))
        : _createCommentVNode("", true),
      _createVNode(_component_FilterGroup, {
        node: draft,
        fields: usable
      }, null, 8, ["node", "fields"]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
        class: "primary",
        type: "button",
        onClick: apply
      }, "Применить составной поиск", 8, ["onClick"]), _createElementVNode("button", {
        type: "button",
        onClick: clear
      }, "Очистить дополнительные условия", 8, ["onClick"]), _createElementVNode("small", null, "До 40 условий. Сохранение в sidebar использует исходный формат FilterData; несовместимое выражение не упрощается.")])
    ]))
  }
};
return __component;
})();
const RelationTreeRow = (function(){

const __component = {
 name:'RelationTreeRow',props:{project:String,target:String,row:Object,spec:Object,ancestry:{type:Array,default:()=>[]},depth:{type:Number,default:0}},emits:['inspect','open'],
 data(){return {expanded:false,loaded:false,busy:false,error:'',relations:[],epoch:0}},
 computed:{cycle(){return this.ancestry.includes(this.row.key)},title(){const v=this.row.values;return v.name||v.title||v.code||v.description||this.row.key}},
 beforeUnmount(){this.epoch++},
 methods:{async expand(){this.expanded=!this.expanded;if(!this.expanded||this.loaded||this.cycle||this.depth>=7)return;const seq=++this.epoch;this.busy=true;this.error='';try{const d=await api.request('/relations',{project:this.project,target:this.target,key:this.row.key});if(seq===this.epoch){this.relations=d.items.map(r=>({...r,expanded:false,items:[],loaded:false,busy:false,error:r.error||'',offset:0,has_more:false,screen:null}));this.loaded=true}}catch(e){if(seq===this.epoch)this.error=e.message}finally{if(seq===this.epoch)this.busy=false}},
 async branch(r){r.expanded=!r.expanded;if(r.expanded&&!r.loaded)await this.more(r)},
 async more(r){if(r.busy||!r.target)return;r.busy=true;r.error='';const seq=this.epoch;try{if(!r.screen)r.screen=await api.request('/open',{project:this.project,target:r.target});const d=await api.request('/query',{project:this.project,target:r.target,offset:r.offset,limit:30,filters:[]},'POST');if(seq===this.epoch){r.items.push(...d.items);r.offset+=d.items.length;r.has_more=d.has_more;r.count=d.total;r.loaded=true}}catch(e){r.error=e.message}finally{r.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_RelationTreeRow = _resolveComponent("RelationTreeRow")

    return (_openBlock(), _createElementBlock("li", { class: "relation-tree-row" }, [_createElementVNode("div", { class: "tree-record" }, [
      _createElementVNode("button", {
        disabled: cycle||depth>=7,
        "aria-expanded": expanded,
        onClick: expand,
        title: cycle?'Объект уже встречался в этой ветке':depth>=7?'Достигнут предел глубины':'Раскрыть связи'
      }, _toDisplayString(expanded?'−':'+'), 9, ["disabled", "aria-expanded", "onClick", "title"]),
      _createElementVNode("button", {
        class: "text-button",
        onClick: $event => ($emit('inspect',{target,row}))
      }, _toDisplayString(title), 9, ["onClick"]),
      _createElementVNode("code", null, _toDisplayString(spec.type), 1),
      cycle
        ? (_openBlock(), _createElementBlock("small", { key: 0 }, "↩ цикл"))
        : _createCommentVNode("", true),
      (depth>=7)
        ? (_openBlock(), _createElementBlock("small", { key: 1 }, "предел глубины"))
        : _createCommentVNode("", true)
    ]), expanded
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "tree-children"
        }, [
          busy
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "muted"
              }, "Чтение связей…"))
            : _createCommentVNode("", true),
          error
            ? (_openBlock(), _createElementBlock("p", {
                key: 1,
                class: "error"
              }, _toDisplayString(error), 1))
            : _createCommentVNode("", true),
          _createElementVNode("ul", { role: "group" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(relations, (r) => {
            return (_openBlock(), _createElementBlock("li", {
              key: r.search_type,
              class: "tree-relation"
            }, [_createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
              disabled: !r.target,
              "aria-expanded": r.expanded,
              onClick: $event => (branch(r))
            }, _toDisplayString(r.expanded?'▾':'▸') + " " + _toDisplayString(r.search_type) + " · " + _toDisplayString(r.count??'—'), 9, ["disabled", "aria-expanded", "onClick"]), _createElementVNode("small", null, _toDisplayString(r.relationship), 1), (r.target)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  class: "text-button",
                  onClick: $event => ($emit('open',{id:r.target}))
                }, "Открыть таблицу", 8, ["onClick"]))
              : _createCommentVNode("", true)]), (r.error)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(r.error), 1))
              : _createCommentVNode("", true), (r.expanded)
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("ul", { role: "group" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(r.items, (child) => {
                  return (_openBlock(), _createBlock(_component_RelationTreeRow, {
                    key: child.key,
                    project: project,
                    target: r.target,
                    row: child,
                    spec: r.screen.spec,
                    depth: depth+1,
                    ancestry: [...ancestry,row.key],
                    onInspect: $event => ($emit('inspect',$event)),
                    onOpen: $event => ($emit('open',$event))
                  }, null, 8, ["project", "target", "row", "spec", "depth", "ancestry", "onInspect", "onOpen"]))
                }), 128))]), (r.has_more||r.busy)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      disabled: r.busy,
                      onClick: $event => (more(r))
                    }, _toDisplayString(r.busy?'Загрузка…':'Ещё 30'), 9, ["disabled", "onClick"]))
                  : _createCommentVNode("", true), (r.loaded&&!r.items.length)
                  ? (_openBlock(), _createElementBlock("small", { key: 1 }, "Нет связанных записей"))
                  : _createCommentVNode("", true)], 64))
              : _createCommentVNode("", true)]))
          }), 128))]),
          (loaded&&!relations.length)
            ? (_openBlock(), _createElementBlock("small", { key: 2 }, "Нет объявленных связей Schema"))
            : _createCommentVNode("", true)
        ]))
      : _createCommentVNode("", true)]))
  }
};
return __component;
})();
const RelationTree = (function(){

const __component = {name:'RelationTree',components:{RelationTreeRow},props:{project:String,target:String,spec:Object,rows:Array,total:Number,offset:Number,limit:Number,busy:Boolean},emits:['inspect','open','page'],data(){return {generation:0}}};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, resolveComponent: _resolveComponent, createBlock: _createBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString } = _Vue

    const _component_RelationTreeRow = _resolveComponent("RelationTreeRow")

    return (_openBlock(), _createElementBlock("section", { class: "relation-tree" }, [
      _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("p", { class: "notice" }, "Ленивое дерево исходной Schema. Каждый уровень загружается отдельно; instance-объекты не копируются."), _createElementVNode("button", { onClick: $event => (generation++) }, "Свернуть / перечитать дерево", 8, ["onClick"])]),
      (_openBlock(), _createElementBlock("ul", {
        key: generation,
        role: "tree"
      }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(rows, (row) => {
        return (_openBlock(), _createBlock(_component_RelationTreeRow, {
          key: row.key+row.revision,
          project: project,
          target: target,
          row: row,
          spec: spec,
          onInspect: $event => ($emit('inspect',$event)),
          onOpen: $event => ($emit('open',$event))
        }, null, 8, ["project", "target", "row", "spec", "onInspect", "onOpen"]))
      }), 128))])),
      (!rows.length&&!busy)
        ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Нет записей"))
        : _createCommentVNode("", true),
      _createElementVNode("footer", { class: "toolbar" }, [_createElementVNode("button", {
        disabled: busy||!offset,
        onClick: $event => ($emit('page',Math.max(0,offset-limit)))
      }, "←", 8, ["disabled", "onClick"]), _createElementVNode("span", null, _toDisplayString(offset+1) + "–" + _toDisplayString(offset+rows.length) + " из " + _toDisplayString(total??'—'), 1), _createElementVNode("button", {
        disabled: busy||offset+rows.length>=total,
        onClick: $event => ($emit('page',offset+limit))
      }, "→", 8, ["disabled", "onClick"])])
    ]))
  }
};
return __component;
})();
const TaskPanel = (function(){



const __component = {
 name:'TaskPanel',components:{ConfiguredForm,WorkHoursPanel},props:{project:String,target:String,record:Object},emits:['changed'],
 data(){return {data:null,busy:false,error:'',offset:0,mode:'board',dragging:null,form:null,formError:'',saving:false,formBusy:false,formFailed:false,formSequence:0,preview:null,selectedProcesses:[],startDate:'',generationBusy:false,hours:null}},
 computed:{
  groups(){
   if(!this.data)return [];
   return this.data.pipelines.map(p=>{
    const rows=this.data.items.filter(r=>r.task_pipeline===p.code);
    const names=p.statuses.map(s=>s.name);
    const unknown=[...new Set(rows.map(r=>r.task.status||'').filter(s=>!names.includes(s)))];
    const columns=[...p.statuses,...unknown.map(name=>({name,color:null}))].map(s=>({...s,rows:rows.filter(r=>(r.task.status||'')===s.name)}));
    return {...p,columns};
   });
  }
 },
 mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},
 async load(){this.busy=true;this.error='';try{this.data=await api.request('/tasks',{...this.args(),offset:this.offset,limit:100})}catch(e){this.error=e.message}finally{this.busy=false}},
 canMove(row,status){return this.data?.can_write&&!row.retired&&row.allowed_statuses.includes(status)&&row.task.status!==status},
 async move(row,status){if(!this.canMove(row,status)||this.busy)return;this.busy=true;this.error='';try{await api.request('/task-change',{...this.args(),task:row.key,revision:row.revision,values:{status}},'PATCH');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false;this.dragging=null}},
 dropped(p,status){const row=this.dragging;if(row?.task_pipeline===p.code)this.move(row,status)},
 async edit(row){this.formError='';this.formFailed=false;this.formSequence++;try{this.form=await api.request('/task-form',{...this.args(),task:row.key})}catch(e){this.error=e.message}},
 async previewForm(values){const seq=++this.formSequence,form=this.form;this.formBusy=true;this.formFailed=false;this.formError='';try{const d=await api.request('/task-form-preview',{...this.args(),task:form.record.key,revision:form.record.revision,values},'POST');if(seq===this.formSequence&&this.form===form)this.form=d}catch(e){if(seq===this.formSequence){this.formError=e.message;this.formFailed=true}}finally{if(seq===this.formSequence)this.formBusy=false}},
 async save(values){if(this.formBusy||this.formFailed)return;this.saving=true;this.formError='';try{await api.request('/task-change',{...this.args(),task:this.form.record.key,revision:this.form.record.revision,values},'PATCH');this.form=null;await this.load();this.$emit('changed')}catch(e){this.formError=e.message}finally{this.saving=false}},
 async generatePreview(){this.error='';try{this.preview=await api.request('/task-generate',this.args());this.selectedProcesses=[]}catch(e){this.error=e.message}},
 async generate(){if(!this.preview?.can_write||!confirm('Создать задачи штатным генератором TACTIC? Серверные defaults, расписание и триггеры будут выполнены.'))return;this.generationBusy=true;this.error='';try{const d=await api.request('/task-generate',{...this.args(),revision:this.preview.revision,processes:this.selectedProcesses,start_date:this.startDate||null,confirm:'GENERATE'},'POST');this.preview=null;await this.load();this.$emit('changed');this.error='';this.data.notice='Создано задач: '+d.created}catch(e){this.error=e.message}finally{this.generationBusy=false}},
 page(delta){this.offset=Math.max(0,this.offset+delta);this.load()},date(v){return v?String(v).slice(0,16).replace('T',' '):'—'}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, normalizeClass: _normalizeClass, toDisplayString: _toDisplayString, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, withModifiers: _withModifiers, normalizeStyle: _normalizeStyle, resolveComponent: _resolveComponent, createBlock: _createBlock, vModelCheckbox: _vModelCheckbox, withDirectives: _withDirectives, vModelText: _vModelText, Teleport: _Teleport } = _Vue

    const _component_WorkHoursPanel = _resolveComponent("WorkHoursPanel")
    const _component_ConfiguredForm = _resolveComponent("ConfiguredForm")

    return (_openBlock(), _createElementBlock("section", { class: "task-panel" }, [
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("button", {
          disabled: busy,
          onClick: load
        }, "Обновить задачи", 8, ["disabled", "onClick"]),
        (data?.can_generate)
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              onClick: generatePreview
            }, "Сгенерировать из pipeline", 8, ["onClick"]))
          : _createCommentVNode("", true),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("button", {
          class: _normalizeClass({primary:mode==='board'}),
          onClick: $event => (mode='board')
        }, "Доска", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:mode==='list'}),
          onClick: $event => (mode='list')
        }, "Список", 10, ["onClick"])
      ]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      busy
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "muted"
          }, "Чтение / сохранение…"))
        : _createCommentVNode("", true),
      data
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
            _createElementVNode("p", { class: "notice" }, _toDisplayString(data.parent_title) + " · " + _toDisplayString(data.total) + " задач. Статусы — из pipeline каждой задачи; перемещение вызывает исходный EditCmd.", 1),
            (data.notice)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "notice"
                }, _toDisplayString(data.notice), 1))
              : _createCommentVNode("", true),
            (mode==='board')
              ? (_openBlock(), _createElementBlock("div", {
                  key: 1,
                  class: "task-boards"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (p) => {
                  return (_openBlock(), _createElementBlock("section", {
                    key: p.code,
                    class: "task-board"
                  }, [_createElementVNode("h3", null, "Pipeline: " + _toDisplayString(p.code||'по умолчанию'), 1), _createElementVNode("div", { class: "task-lanes" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(p.columns, (status) => {
                    return (_openBlock(), _createElementBlock("section", {
                      key: status.name,
                      class: "task-lane",
                      style: _normalizeStyle({borderTopColor:status.color||undefined}),
                      onDragover: _withModifiers(() => {}, ["prevent"]),
                      onDrop: _withModifiers($event => (dropped(p,status.name)), ["prevent"])
                    }, [_createElementVNode("h4", null, [_createTextVNode(_toDisplayString(status.name||'Статус не задан') + " ", 1), _createElementVNode("small", null, _toDisplayString(status.rows.length), 1)]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(status.rows, (row) => {
                      return (_openBlock(), _createElementBlock("article", {
                        key: row.key,
                        class: "task-card",
                        draggable: data.can_write&&!busy,
                        onDragstart: $event => (dragging=row),
                        onDragend: $event => (dragging=null)
                      }, [
                        _createElementVNode("button", {
                          class: "text-button",
                          onClick: $event => (edit(row))
                        }, _toDisplayString(row.task.process||row.task.code||row.key), 9, ["onClick"]),
                        _createElementVNode("p", null, _toDisplayString(row.task.description), 1),
                        _createElementVNode("small", null, _toDisplayString(row.task.assigned||'Не назначена'), 1),
                        _createElementVNode("button", {
                          class: "text-button",
                          onClick: $event => (hours=row)
                        }, "Рабочее время", 8, ["onClick"]),
                        _createElementVNode("div", { class: "task-dates" }, _toDisplayString(date(row.task.bid_start_date)) + " → " + _toDisplayString(date(row.task.bid_end_date)), 1),
                        _createElementVNode("select", {
                          value: row.task.status||'',
                          disabled: !data.can_write||busy||row.retired,
                          onChange: $event => (move(row,$event.target.value)),
                          "aria-label": "Статус задачи"
                        }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList([...new Set([row.task.status||'',...row.allowed_statuses])], (s) => {
                          return (_openBlock(), _createElementBlock("option", {
                            key: s,
                            value: s
                          }, _toDisplayString(s||'—'), 9, ["value"]))
                        }), 128))], 40, ["value", "disabled", "onChange"])
                      ], 40, ["draggable", "onDragstart", "onDragend"]))
                    }), 128))], 44, ["onDragover", "onDrop"]))
                  }), 128))])]))
                }), 128))]))
              : (_openBlock(), _createElementBlock("table", {
                  key: 2,
                  class: "task-list"
                }, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                  _createElementVNode("th", null, "Процесс / контекст"),
                  _createElementVNode("th", null, "Статус"),
                  _createElementVNode("th", null, "Исполнитель"),
                  _createElementVNode("th", null, "Срок")
                ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.items, (row) => {
                  return (_openBlock(), _createElementBlock("tr", {
                    key: row.key,
                    onDblclick: $event => (edit(row))
                  }, [
                    _createElementVNode("td", null, [_createElementVNode("button", {
                      class: "text-button",
                      onClick: $event => (edit(row))
                    }, _toDisplayString(row.task.process||row.task.code), 9, ["onClick"]), _createElementVNode("small", null, _toDisplayString(row.task.context), 1), _createElementVNode("button", {
                      class: "text-button",
                      onClick: $event => (hours=row)
                    }, "Рабочее время", 8, ["onClick"])]),
                    _createElementVNode("td", null, _toDisplayString(row.task.status), 1),
                    _createElementVNode("td", null, _toDisplayString(row.task.assigned), 1),
                    _createElementVNode("td", null, _toDisplayString(date(row.task.bid_end_date)), 1)
                  ], 40, ["onDblclick"]))
                }), 128))])])),
            (!data.items.length)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 3,
                  class: "muted"
                }, "Задачи пока не созданы."))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
              disabled: busy||offset===0,
              onClick: $event => (page(-100))
            }, "←", 8, ["disabled", "onClick"]), _createElementVNode("span", null, _toDisplayString(data.items.length) + " показано · " + _toDisplayString(offset) + " пропущено · " + _toDisplayString(data.total) + " всего", 1), _createElementVNode("button", {
              disabled: busy||offset+data.items.length>=data.total,
              onClick: $event => (page(100))
            }, "→", 8, ["disabled", "onClick"])])
          ], 64))
        : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [hours
        ? (_openBlock(), _createBlock(_component_WorkHoursPanel, {
            key: hours.key,
            project: project,
            target: target,
            record: record,
            task: hours,
            onClose: $event => (hours=null),
            onChanged: $event => ($emit('changed'))
          }, null, 8, ["project", "target", "record", "task", "onClose", "onChanged"]))
        : _createCommentVNode("", true), preview
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "modal-backdrop",
            onClick: _withModifiers($event => (preview=null), ["self"])
          }, [_createElementVNode("section", { class: "modal task-generation" }, [
            _createElementVNode("header", null, [_createElementVNode("h2", null, "Генерация задач"), _createElementVNode("button", {
              disabled: generationBusy,
              onClick: $event => (preview=null)
            }, "×", 8, ["disabled", "onClick"])]),
            _createElementVNode("p", null, "Pipeline " + _toDisplayString(preview.pipeline) + " · уже есть " + _toDisplayString(preview.existing) + " задач", 1),
            _createElementVNode("p", { class: "notice" }, _toDisplayString(preview.notice), 1),
            _createElementVNode("div", { class: "process-checks" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preview.processes, (p) => {
              return (_openBlock(), _createElementBlock("label", { key: p.name }, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                value: p.name,
                "onUpdate:modelValue": $event => ((selectedProcesses) = $event)
              }, null, 8, ["value", "onUpdate:modelValue"]), [[_vModelCheckbox, selectedProcesses]]), _createTextVNode(_toDisplayString(p.name) + " ", 1), _createElementVNode("small", null, _toDisplayString(p.type), 1)]))
            }), 128))]),
            _createElementVNode("label", null, [_createTextVNode("Дата начала"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((startDate) = $event)
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, startDate]])]),
            error
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            _createElementVNode("footer", null, [_createElementVNode("button", {
              disabled: generationBusy,
              onClick: $event => (preview=null)
            }, "Отмена", 8, ["disabled", "onClick"]), _createElementVNode("button", {
              class: "primary",
              disabled: !preview.can_write||generationBusy,
              onClick: generate
            }, _toDisplayString(generationBusy?'Создание…':selectedProcesses.length?'Создать выбранные':'Штатная генерация всего pipeline'), 9, ["disabled", "onClick"])])
          ])], 8, ["onClick"]))
        : _createCommentVNode("", true), form
        ? (_openBlock(), _createBlock(_component_ConfiguredForm, {
            key: form.record.key,
            form: form,
            error: formError,
            busy: saving||formBusy||formFailed,
            onPreview: previewForm,
            onSave: save,
            onClose: $event => (form=null)
          }, null, 8, ["form", "error", "busy", "onPreview", "onSave", "onClose"]))
        : _createCommentVNode("", true)]))
    ]))
  }
};
return __component;
})();
const RelationshipEditor = (function(){

const __component = {
 name:'RelationshipEditor',props:{project:String,target:String,record:Object,relatedType:String},emits:['close','changed'],
 data(){return {data:null,descriptor:null,error:'',busy:false,keyword:'',offset:0,epoch:0}},
 mounted(){this.load()},beforeUnmount(){this.epoch++},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key,related_type:this.relatedType}},
 async load(){const seq=++this.epoch;this.busy=true;this.error='';try{const d=await api.request('/relationship',this.args());const rows=await api.request('/relation-candidates',{...this.args(),keyword:this.keyword,offset:this.offset,limit:30},'POST');if(seq===this.epoch){this.descriptor=d;this.data=rows}}catch(e){if(seq===this.epoch)this.error=e.message}finally{if(seq===this.epoch)this.busy=false}},
 title(row){const v=row.values;return v.name||v.title||v.code||v.description||row.key},
 search(){this.offset=0;this.load()},page(n){this.offset=n;this.load()},
 async change(row){if(!this.data.can_write||this.busy)return;if(row.linked&&!confirm('Удалить '+row.links+' записей связи? Сам объект не удаляется; настроенные серверные триггеры выполняются.'))return;this.busy=true;this.error='';try{await api.request('/relationship',{...this.args(),other_key:row.key,other_revision:row.revision,revision:this.data.revision,confirm_count:row.links},row.linked?'DELETE':'POST');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, createTextVNode: _createTextVNode, vModelText: _vModelText, withDirectives: _withDirectives, withModifiers: _withModifiers, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, normalizeClass: _normalizeClass, Teleport: _Teleport, createBlock: _createBlock } = _Vue

    return (_openBlock(), _createBlock(_Teleport, { to: "body" }, [_createElementVNode("div", {
      class: "modal-backdrop",
      onClick: _withModifiers($event => ($emit('close')), ["self"])
    }, [_createElementVNode("section", {
      class: "modal relation-editor",
      role: "dialog",
      "aria-modal": "true"
    }, [
      _createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, "INSTANCE RELATIONSHIP"), _createElementVNode("h2", null, _toDisplayString(relatedType), 1)]), _createElementVNode("button", { onClick: $event => ($emit('close')) }, "×", 8, ["onClick"])]),
      _createElementVNode("p", { class: "notice" }, [_createTextVNode(_toDisplayString(descriptor?.notice||'Связь разрешается исходной Schema'), 1), _createElementVNode("br"), _createElementVNode("code", null, _toDisplayString(descriptor?.instance_type), 1)]),
      _createElementVNode("form", {
        class: "toolbar",
        onSubmit: _withModifiers(search, ["prevent"])
      }, [_withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": $event => ((keyword) = $event),
        placeholder: "Найти связанный объект"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, keyword]]), _createElementVNode("button", { disabled: busy }, "Найти", 8, ["disabled"]), _createElementVNode("button", {
        type: "button",
        disabled: busy,
        onClick: load
      }, "Обновить", 8, ["disabled", "onClick"])], 40, ["onSubmit"]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "relation-candidates" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.items||[], (row) => {
        return (_openBlock(), _createElementBlock("article", { key: row.key }, [
          _createElementVNode("div", null, [_createElementVNode("b", null, _toDisplayString(title(row)), 1), _createElementVNode("code", null, _toDisplayString(row.key), 1)]),
          _createElementVNode("span", { class: "spacer" }),
          (row.linked)
            ? (_openBlock(), _createElementBlock("small", { key: 0 }, "Связей: " + _toDisplayString(row.links), 1))
            : _createCommentVNode("", true),
          _createElementVNode("button", {
            disabled: busy||!data.can_write,
            class: _normalizeClass({primary:!row.linked}),
            onClick: $event => (change(row))
          }, _toDisplayString(row.linked?'Отвязать':'Связать'), 11, ["disabled", "onClick"])
        ]))
      }), 128))]),
      _createElementVNode("footer", null, [_createElementVNode("button", {
        disabled: busy||offset===0,
        onClick: $event => (page(Math.max(0,offset-30)))
      }, "←", 8, ["disabled", "onClick"]), _createElementVNode("span", null, _toDisplayString(offset+1) + "–" + _toDisplayString(offset+(data?.items.length||0)) + " / " + _toDisplayString(data?.total??'—'), 1), _createElementVNode("button", {
        disabled: busy||offset+(data?.items.length||0)>=data?.total,
        onClick: $event => (page(offset+30))
      }, "→", 8, ["disabled", "onClick"])]),
      _createElementVNode("small", null, "Удаление связи вызывает SObject.remove_instance. Существующие атрибуты других связей сохраняются.")
    ])], 8, ["onClick"])]))
  }
};
return __component;
})();
const HistoryPanel = (function(){

const __component = {
 name:'HistoryPanel',props:{project:String,target:String,record:Object},emits:['changed'],
 data(){return {state:null,data:null,error:'',busy:false,source:'changes',offset:0}},
 mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},
 async load(){this.busy=true;this.error='';try{this.state=await api.request('/record-state',this.args());this.data=await api.request('/history',{...this.args(),source:this.source,offset:this.offset,limit:50})}catch(e){this.error=e.message}finally{this.busy=false}},
 sourceChanged(){this.offset=0;this.load()},page(n){this.offset=n;this.load()},
 async stateChange(){if(!this.state?.can_write||this.busy)return;const action=this.state.retired?'reactivate':'retire';if(!confirm(this.state.retired?'Восстановить запись из архива?':'Архивировать запись штатным SObject.retire? Физическое удаление не выполняется.'))return;this.busy=true;this.error='';try{await api.request('/record-state',{...this.args(),revision:this.state.revision,action,confirm:action.toUpperCase()},'POST');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, vModelSelect: _vModelSelect, withDirectives: _withDirectives, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "history-panel" }, [
      _createElementVNode("div", { class: "toolbar" }, [_withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((source) = $event),
        onChange: sourceChanged,
        "aria-label": "Вид истории"
      }, [_createElementVNode("option", { value: "changes" }, "Изменения объекта"), _createElementVNode("option", { value: "status" }, "История статусов"), _createElementVNode("option", { value: "retire" }, "Архивирование")], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, source]]), _createElementVNode("button", {
        disabled: busy,
        onClick: load
      }, "Обновить", 8, ["disabled", "onClick"])]),
      state
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "toolbar"
          }, [_createElementVNode("span", null, _toDisplayString(state.retired?'Запись архивирована':'Активная запись'), 1), (state.can_write)
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                disabled: busy,
                onClick: stateChange
              }, _toDisplayString(state.retired?'Восстановить из архива':'Архивировать'), 9, ["disabled", "onClick"]))
            : _createCommentVNode("", true)]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (data?.notice)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, _toDisplayString(data.notice), 1))
        : _createCommentVNode("", true),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.items||[], (item) => {
        return (_openBlock(), _createElementBlock("article", {
          key: item.key,
          class: "history-event"
        }, [_createElementVNode("header", null, [_createElementVNode("b", null, _toDisplayString(item.values?.login||item.login||'—'), 1), _createElementVNode("small", null, _toDisplayString(item.values?.timestamp||item.timestamp), 1)]), _createElementVNode("dl", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList((item.values||item), (v, k) => {
          return (_openBlock(), _createElementBlock(_Fragment, { key: k }, [(!['login','timestamp','key'].includes(k))
            ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("dt", null, _toDisplayString(k), 1), _createElementVNode("dd", null, _toDisplayString(v??'—'), 1)], 64))
            : _createCommentVNode("", true)], 64))
        }), 128))])]))
      }), 128)),
      (data&&!data.items.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "muted"
          }, "Записей этого вида истории нет."))
        : _createCommentVNode("", true),
      _createElementVNode("footer", { class: "toolbar" }, [_createElementVNode("button", {
        disabled: busy||offset===0,
        onClick: $event => (page(Math.max(0,offset-50)))
      }, "←", 8, ["disabled", "onClick"]), _createElementVNode("span", null, _toDisplayString(data?.total??'—') + " событий", 1), _createElementVNode("button", {
        disabled: busy||offset+(data?.items.length||0)>=data?.total,
        onClick: $event => (page(offset+50))
      }, "→", 8, ["disabled", "onClick"])]),
      _createElementVNode("small", null, "Исходные status_log / sobject_log / retire_log, не отдельный журнал нового интерфейса.")
    ]))
  }
};
return __component;
})();
const ConfigEditor = (function(){

const __component = {
 name:'ConfigEditor',props:{project:String,mode:String,initialView:String,allowWrites:Boolean},emits:['changed','dirty'],
 data(){return {items:[],key:'',record:null,xml:'',view:this.initialView||'project_view',effective:null,order:[],error:'',busy:false,changed:false,newMode:false,newType:'SideBarWdg',newView:'project_view',newLogin:''}},
 watch:{changed(v){this.$emit('dirty',v)}},
 async mounted(){await this.loadList();if(this.mode==='sidebar-editor')await this.loadEffective()},
 methods:{
 async run(fn){this.error='';this.busy=true;try{await fn()}catch(e){this.error=e.message}finally{this.busy=false}},
 async loadList(){await this.run(async()=>{this.items=(await api.request('/configs',{project:this.project,search_type:this.mode==='sidebar-editor'?'SideBarWdg':undefined})).items})},
 async load(){if(!this.key)return;await this.run(async()=>{this.record=await api.request('/config',{project:this.project,key:this.key});this.xml=this.record.xml;this.changed=false;this.newMode=false})},
 async loadEffective(){await this.run(async()=>{this.effective=await api.request('/config',{project:this.project,view:this.view});this.order=this.effective.elements.map((_,i)=>i)})},
 move(index,delta){const j=index+delta;if(j<0||j>=this.order.length)return;const a=[...this.order];[a[index],a[j]]=[a[j],a[index]];this.order=a},
 async saveOrder(){await this.run(async()=>{await api.request('/sidebar-order',{project:this.project,view:this.view,revision:this.effective.revision,order:this.order},'POST');await this.loadEffective();await this.loadList();this.$emit('changed')})},
 async save(){await this.run(async()=>{const res=await api.request('/config',{project:this.project,key:this.key,xml:this.xml,revision:this.record?.revision,view:this.newView,search_type:this.newType,login:this.newLogin},this.newMode?'POST':'PATCH');this.key=res.key;await this.loadList();await this.load();this.$emit('changed')})},
 create(){this.newMode=true;this.record=null;this.key='';this.xml='<config>\n  <project_view>\n    <element name="project_admin"/>\n  </project_view>\n</config>';this.changed=true}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withKeys: _withKeys, createElementVNode: _createElementVNode, withDirectives: _withDirectives, createTextVNode: _createTextVNode, renderList: _renderList, Fragment: _Fragment, vModelSelect: _vModelSelect } = _Vue

    return (_openBlock(), _createElementBlock("section", {
      class: "config-workbench",
      "aria-label": "Widget Config"
    }, [
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (mode==='sidebar-editor')
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "effective-editor"
          }, [_createElementVNode("div", { class: "toolbar" }, [_createElementVNode("label", null, [_createTextVNode("View "), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((view) = $event),
            onKeyup: _withKeys(loadEffective, ["enter"])
          }, null, 40, ["onUpdate:modelValue", "onKeyup"]), [[_vModelText, view]])]), _createElementVNode("button", {
            onClick: loadEffective,
            disabled: busy
          }, "Разрешить конфигурацию", 8, ["onClick", "disabled"]), _createElementVNode("button", {
            class: "primary",
            disabled: busy||!effective||!allowWrites,
            onClick: saveOrder
          }, "Сохранить порядок в TACTIC", 8, ["disabled", "onClick"])]), effective
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "config-columns"
              }, [_createElementVNode("ol", { class: "element-list" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(order, (index, pos) => {
                return (_openBlock(), _createElementBlock("li", { key: index }, [_createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(effective.elements[index].title), 1), _createElementVNode("small", null, _toDisplayString(effective.elements[index].name) + " · " + _toDisplayString(effective.elements[index].handler||'default'), 1)]), _createElementVNode("button", {
                  disabled: pos===0,
                  onClick: $event => (move(pos,-1)),
                  "aria-label": "Вверх"
                }, "↑", 8, ["disabled", "onClick"]), _createElementVNode("button", {
                  disabled: pos===order.length-1,
                  onClick: $event => (move(pos,1)),
                  "aria-label": "Вниз"
                }, "↓", 8, ["disabled", "onClick"])]))
              }), 128))]), _createElementVNode("div", { class: "layers" }, [_createElementVNode("h3", null, "Слои разрешения · по приоритету"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(effective.layers, (layer, i) => {
                return (_openBlock(), _createElementBlock("details", { key: i }, [_createElementVNode("summary", null, _toDisplayString(i+1) + ". " + _toDisplayString(layer.view) + " · " + _toDisplayString(layer.origin), 1), _createElementVNode("pre", null, _toDisplayString(layer.xml), 1)]))
              }), 128))])]))
            : _createCommentVNode("", true)]))
        : _createCommentVNode("", true),
      _createElementVNode("hr"),
      _createElementVNode("div", { class: "toolbar" }, [_withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((key) = $event),
        onChange: load
      }, [_createElementVNode("option", { value: "" }, "Запись из базы…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (row) => {
        return (_openBlock(), _createElementBlock("option", {
          key: row.key,
          value: row.key
        }, _toDisplayString(row.search_type) + " / " + _toDisplayString(row.view) + " " + _toDisplayString(row.login?'· '+row.login:''), 9, ["value"]))
      }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, key]]), _createElementVNode("button", { onClick: loadList }, "Обновить", 8, ["onClick"]), _createElementVNode("button", {
        disabled: !allowWrites,
        onClick: create
      }, "Новый widget_config", 8, ["disabled", "onClick"])]),
      (!items.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "В базе нет подходящих переопределений. Sidebar продолжает наследоваться из штатных XML."))
        : _createCommentVNode("", true),
      newMode
        ? (_openBlock(), _createElementBlock("div", {
            key: 3,
            class: "toolbar"
          }, [_createElementVNode("label", null, [_createTextVNode("Search type"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((newType) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newType]])]), _createElementVNode("label", null, [_createTextVNode("View"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((newView) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newView]])]), _createElementVNode("label", null, [_createTextVNode("Login (пусто — общий)"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((newLogin) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newLogin]])])]))
        : _createCommentVNode("", true),
      (record||newMode)
        ? (_openBlock(), _createElementBlock("div", {
            key: 4,
            class: "xml-editor"
          }, [_createElementVNode("div", { class: "toolbar" }, [_createElementVNode("code", null, _toDisplayString(record?.search_type||newType) + " / " + _toDisplayString(record?.view||newView), 1), _createElementVNode("span", { class: "spacer" }), _createElementVNode("button", {
            class: "primary",
            disabled: busy||!changed||!allowWrites,
            onClick: save
          }, "Сохранить XML", 8, ["disabled", "onClick"])]), _withDirectives(_createElementVNode("textarea", {
            spellcheck: "false",
            "onUpdate:modelValue": $event => ((xml) = $event),
            onInput: $event => (changed=true),
            readonly: !allowWrites,
            "aria-label": "Исходный XML widget_config"
          }, null, 40, ["onUpdate:modelValue", "onInput", "readonly"]), [[_vModelText, xml]]), _createElementVNode("p", { class: "muted" }, "Изменения конфигурации влияют на действующий проект. Неизвестные атрибуты и соседние views не удаляются автоматически.")]))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const GraphEditor = (function(){

const __component = {
 name:'GraphEditor',props:{project:String,kind:String,target:String},emits:['dirty'],
 data(){return {items:[],key:'',record:null,nodes:[],edges:[],selected:null,operations:[],settings:{},history:[],error:'',notice:'',busy:false,scale:1,drag:null,showXml:false,canCreate:false,newCode:'',newTitle:'',creating:false,newNode:'',newType:'manual',edgeFrom:'',edgeTo:'',props:{},settingsText:'{}',types:[],searchTypes:[],newSearchType:'',requestSeq:0,propertyBaseline:''}},
 computed:{propertiesDirty(){return Boolean(this.selected)&&this.propertyBaseline!==JSON.stringify({props:this.props,settingsText:this.settingsText})},dirty(){return this.operations.length>0||Object.keys(this.settings).length>0||this.propertiesDirty},chosenNode(){return this.selected?.kind==='node'?this.nodes.find(n=>n.name===this.selected.name):null},chosenEdge(){return this.selected?.kind==='edge'?this.edges[this.selected.index]:null}},
 watch:{dirty(value){this.$emit('dirty',value)}},
 async mounted(){this.unload=e=>{if(this.dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',this.unload);await this.list()},
 beforeUnmount(){this.requestSeq++;window.removeEventListener('beforeunload',this.unload)},
 methods:{
 async list(){this.error='';try{const data=await api.request('/graph',{project:this.project,target:this.target,kind:this.kind});this.items=data.items;this.canCreate=data.can_create;this.types=data.node_types||[];this.searchTypes=data.search_types||[];if(!this.key&&data.initial_key){this.key=data.initial_key;await this.load(true)}}catch(e){this.error=e.message}},
 async load(force=false){if(!force)api.action?.('graph.select',{project:this.project,target:this.target});if(!this.key){if(this.dirty&&!confirm('Отменить несохранённые изменения графа?')){this.key=this.record?.key||'';return}this.record=null;this.nodes=[];this.edges=[];this.operations=[];this.settings={};this.history=[];return;}if(this.dirty&&!force&&!confirm('Отменить несохранённые изменения графа?')){this.key=this.record?.key||'';return;}this.error='';this.busy=true;const sequence=++this.requestSeq;try{const loaded=await api.request('/graph',{project:this.project,target:this.target,kind:this.kind,key:this.key});if(sequence!==this.requestSeq)return;this.record=loaded;const graph=this.record.graph;this.nodes=JSON.parse(JSON.stringify(graph.nodes));this.edges=JSON.parse(JSON.stringify(graph.edges));this.operations=[];this.settings={};this.history=[];this.selected=null;this.types=this.record.node_types||this.types;this.notice=this.record.notice||''}catch(e){this.error=e.message}finally{this.busy=false}},
 async create(){api.action?.('graph.save',{project:this.project,target:this.target,control:'create'});this.busy=true;this.error='';try{const d=await api.request('/graph',{project:this.project,target:this.target,kind:'pipeline',code:this.newCode,name:this.newTitle,search_type:this.newSearchType},'POST');await this.list();this.key=d.key;this.creating=false;await this.load(true)}catch(e){this.error=e.message}finally{this.busy=false}},
 snapshot(){return JSON.stringify({nodes:this.nodes,edges:this.edges,operations:this.operations,settings:this.settings})},
 checkpoint(){api.action?.('graph.edit',{project:this.project,target:this.target,control:'local-change'});this.history.push(this.snapshot());if(this.history.length>100)this.history.shift()},
 undo(){if(!this.history.length)return;Object.assign(this,JSON.parse(this.history.pop()));this.selected=null},
 point(name){return this.nodes.find(n=>n.name===name)},
 edgePath(edge){const a=this.point(edge.from),b=this.point(edge.to);if(!a||!b)return '';return `M${a.x+190},${a.y+32} C${a.x+255},${a.y+32} ${b.x-65},${b.y+32} ${b.x},${b.y+32}`},
 choose(node){if(this.propertiesDirty&&this.selected?.name!==node.name&&!confirm('Отменить неприменённые свойства?'))return false;if(this.propertiesDirty&&this.selected?.name===node.name)return true;this.selected={kind:'node',name:node.name};this.props={name:node.name,type:node.type,label:node.attributes.label||'',color:node.attributes.color||'',description:node.attributes.description||'',xpos:node.x,ypos:node.y};this.settingsText=JSON.stringify(this.settings[node.name]||{},null,2);this.propertyBaseline=JSON.stringify({props:this.props,settingsText:this.settingsText});return true},
 chooseEdge(index){if(this.propertiesDirty&&!confirm('Отменить неприменённые свойства?'))return false;this.selected={kind:'edge',index};const e=this.edges[index];this.props={...e.attributes,from:e.from,to:e.to};this.settingsText='{}';this.propertyBaseline=JSON.stringify({props:this.props,settingsText:this.settingsText});return true},
 down(e,node){if(this.choose(node)===false)return;if(!this.record?.can_edit)return;this.drag={name:node.name,x:e.clientX,y:e.clientY,nx:node.x,ny:node.y,before:this.snapshot()};e.currentTarget.setPointerCapture(e.pointerId)},
 move(e){if(!this.drag)return;const n=this.point(this.drag.name);n.x=Math.round(this.drag.nx+(e.clientX-this.drag.x)/this.scale);n.y=Math.round(this.drag.ny+(e.clientY-this.drag.y)/this.scale);this.props.xpos=n.x;this.props.ypos=n.y},
 up(){if(!this.drag)return;const n=this.point(this.drag.name),d=this.drag;this.drag=null;if(n.x===d.nx&&n.y===d.ny)return;this.history.push(d.before);n.attributes.xpos=String(n.x);n.attributes.ypos=String(n.y);this.operations.push({op:'update_node',name:n.name,attributes:{xpos:n.x,ypos:n.y}})},
 addNode(){if(!this.newNode.trim())return;const name=this.newNode.trim();if(this.nodes.some(n=>n.name===name)){this.error='Такой узел уже существует';return}this.checkpoint();const attrs={xpos:80+(this.nodes.length%4)*240,ypos:80+Math.floor(this.nodes.length/4)*150};if(this.kind==='pipeline')attrs.type=this.newType;this.operations.push({op:'add_node',name,attributes:attrs});const n={name,type:this.kind==='pipeline'?this.newType:'search_type',x:attrs.xpos,y:attrs.ypos,attributes:{name,...attrs}};this.nodes.push(n);this.newNode='';this.choose(n)},
 remove(){if(!this.record?.can_edit||!this.selected)return;if(!confirm('Удалить выбранный элемент графа? История задач не удаляется; сервер блокирует используемые процессы.'))return;this.checkpoint();if(this.chosenNode){const name=this.chosenNode.name;this.operations.push({op:'remove_node',name});this.nodes=this.nodes.filter(n=>n.name!==name);this.edges=this.edges.filter(e=>e.from!==name&&e.to!==name);delete this.settings[name]}else if(this.chosenEdge){this.operations.push({op:'remove_edge',index:this.selected.index});this.edges.splice(this.selected.index,1)}this.selected=null},
 addEdge(){if(!this.edgeFrom||!this.edgeTo)return;this.checkpoint();const attributes=this.kind==='schema'?{relationship:'code'}:{};this.operations.push({op:'add_edge',from:this.edgeFrom,to:this.edgeTo,attributes});this.edges.push({from:this.edgeFrom,to:this.edgeTo,attributes:{from:this.edgeFrom,to:this.edgeTo,...attributes}});this.chooseEdge(this.edges.length-1)},
 applyProperties(){this.error='';const before=this.snapshot();const selection=this.selected?{...this.selected}:null;try{if(this.chosenNode&&(!Number.isFinite(Number(this.props.xpos))||!Number.isFinite(Number(this.props.ypos))))throw Error('Координаты должны быть числами');let patch={};if(this.chosenNode&&this.kind==='pipeline'){patch=JSON.parse(this.settingsText);if(!patch||Array.isArray(patch)||typeof patch!=='object')throw Error('Настройки должны быть JSON-объектом')}this.checkpoint();if(this.chosenNode){const n=this.chosenNode,old=n.name;let name=old;if(this.kind==='pipeline'&&this.props.name!==old){name=this.props.name.trim();if(!name||this.nodes.some(other=>other!==n&&other.name===name))throw Error('Имя пустое или занято');this.operations.push({op:'rename_node',name:old,new_name:name});n.name=name;n.attributes.name=name;this.edges.forEach(e=>{if(e.from===old){e.from=name;e.attributes.from=name}if(e.to===old){e.to=name;e.attributes.to=name}});if(this.settings[old]){this.settings[name]=this.settings[old];delete this.settings[old]}}
 const attrs={xpos:Number(this.props.xpos),ypos:Number(this.props.ypos)};for(const k of ['label','color',...(this.kind==='pipeline'?['type','description']:[])]){const v=this.props[k];if(v!==undefined&&String(v)!==String(n.attributes[k]??''))attrs[k]=v||null}this.operations.push({op:'update_node',name,attributes:attrs});Object.entries(attrs).forEach(([k,v])=>{if(v===null)delete n.attributes[k];else n.attributes[k]=v});n.x=attrs.xpos;n.y=attrs.ypos;n.type=n.attributes.type||'manual';if(Object.keys(patch).length)this.settings[name]=patch;else delete this.settings[name];this.propertyBaseline=JSON.stringify({props:this.props,settingsText:this.settingsText});this.choose(n)
 }else if(this.chosenEdge){const e=this.chosenEdge,allowed=this.kind==='schema'?['relationship','from_col','to_col','instance_type','path','label','color']:['from_attr','to_attr','type','label','color'];const attrs={};for(const k of allowed){const v=this.props[k]||'';if(v!==String(e.attributes[k]??''))attrs[k]=v||null}this.operations.push({op:'update_edge',index:this.selected.index,attributes:attrs});Object.entries(attrs).forEach(([k,v])=>{if(v===null)delete e.attributes[k];else e.attributes[k]=v})}
 this.propertyBaseline=JSON.stringify({props:this.props,settingsText:this.settingsText});return true}catch(e){Object.assign(this,JSON.parse(before));this.selected=selection;this.error=e.message;return false}},
 safeColor(value){return /^#[0-9a-fA-F]{3,8}$/.test(value||'')?value:'#6585aa'},
 async save(){api.action?.('graph.save',{project:this.project,target:this.target,count:this.operations.length});if(this.propertiesDirty&&this.applyProperties()===false)return;this.busy=true;this.error='';try{const result=await api.request('/graph',{project:this.project,target:this.target,kind:this.kind,key:this.key,revision:this.record.revision,operations:this.operations,settings:this.settings},'PATCH');await this.load(true);this.notice=result.notice||'Сохранено'}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withModifiers: _withModifiers, withKeys: _withKeys, normalizeClass: _normalizeClass, normalizeStyle: _normalizeStyle, createTextVNode: _createTextVNode } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "graph-editor" }, [
      _createElementVNode("div", { class: "toolbar" }, [
        _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((key) = $event),
          onChange: $event => (load())
        }, [_createElementVNode("option", { value: "" }, _toDisplayString(kind==='schema'?'Схема проекта…':'Pipeline…'), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (p) => {
          return (_openBlock(), _createElementBlock("option", {
            key: p.key,
            value: p.key
          }, _toDisplayString(p.name) + " · " + _toDisplayString(p.code), 9, ["value"]))
        }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, key]]),
        _createElementVNode("button", { onClick: list }, "Обновить", 8, ["onClick"]),
        canCreate
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              onClick: $event => (creating=!creating)
            }, "+ Pipeline", 8, ["onClick"]))
          : _createCommentVNode("", true),
        _createElementVNode("button", { onClick: $event => (scale=Math.max(.25,scale-.1)) }, "−", 8, ["onClick"]),
        _createElementVNode("span", null, _toDisplayString(Math.round(scale*100)) + "%", 1),
        _createElementVNode("button", { onClick: $event => (scale=Math.min(2,scale+.1)) }, "+", 8, ["onClick"]),
        _createElementVNode("button", { onClick: $event => (showXml=!showXml) }, "Исходный XML", 8, ["onClick"]),
        _createElementVNode("button", {
          disabled: !history.length||busy,
          onClick: undo
        }, "Отменить правку", 8, ["disabled", "onClick"]),
        _createElementVNode("span", { class: "spacer" }),
        dirty
          ? (_openBlock(), _createElementBlock("span", { key: 1 }, "Изменений: " + _toDisplayString(operations.length) + _toDisplayString(propertiesDirty?' + свойства':''), 1))
          : _createCommentVNode("", true),
        _createElementVNode("button", {
          class: "primary",
          disabled: busy||!record?.can_edit||!dirty,
          onClick: save
        }, "Сохранить граф", 8, ["disabled", "onClick"])
      ]),
      creating
        ? (_openBlock(), _createElementBlock("form", {
            key: 0,
            class: "toolbar",
            onSubmit: _withModifiers(create, ["prevent"])
          }, [
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((newCode) = $event),
              placeholder: "Код pipeline",
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newCode]]),
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((newTitle) = $event),
              placeholder: "Название"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newTitle]]),
            _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((newSearchType) = $event) }, [_createElementVNode("option", { value: "" }, "SearchType (не назначен)"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(searchTypes, (s) => {
              return (_openBlock(), _createElementBlock("option", {
                key: s.code,
                value: s.code
              }, _toDisplayString(s.name) + " · " + _toDisplayString(s.code), 9, ["value"]))
            }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, newSearchType]]),
            _createElementVNode("button", {
              class: "primary",
              disabled: busy
            }, "Создать", 8, ["disabled"])
          ], 40, ["onSubmit"]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      _createElementVNode("p", { class: "notice" }, _toDisplayString(kind==='schema'?'Связи используют существующие SearchType и поля. Изменение графа не создаёт столбцы и не перемещает данные.':'Процессы, связи, порты, свойства и координаты сохраняются в исходный XML через команду TACTIC. Узлы с историей защищены.'), 1),
      record
        ? (_openBlock(), _createElementBlock("div", {
            key: 3,
            class: "toolbar graph-tools"
          }, [
            (kind==='schema')
              ? _withDirectives((_openBlock(), _createElementBlock("select", {
                  key: 0,
                  "onUpdate:modelValue": $event => ((newNode) = $event)
                }, [_createElementVNode("option", { value: "" }, "SearchType…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record.search_types, (t) => {
                  return (_openBlock(), _createElementBlock("option", {
                    key: t.code,
                    value: t.code
                  }, _toDisplayString(t.name) + " · " + _toDisplayString(t.code), 9, ["value"]))
                }), 128))], 8, ["onUpdate:modelValue"])), [[_vModelSelect, newNode]])
              : _withDirectives((_openBlock(), _createElementBlock("input", {
                  key: 1,
                  "onUpdate:modelValue": $event => ((newNode) = $event),
                  placeholder: "Имя нового процесса",
                  onKeyup: _withKeys(addNode, ["enter"])
                }, null, 40, ["onUpdate:modelValue", "onKeyup"])), [[_vModelText, newNode]]),
            (kind==='pipeline')
              ? _withDirectives((_openBlock(), _createElementBlock("select", {
                  key: 2,
                  "onUpdate:modelValue": $event => ((newType) = $event)
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(types, (t) => {
                  return (_openBlock(), _createElementBlock("option", {
                    key: t,
                    value: t
                  }, _toDisplayString(t), 9, ["value"]))
                }), 128))], 8, ["onUpdate:modelValue"])), [[_vModelSelect, newType]])
              : _createCommentVNode("", true),
            _createElementVNode("button", {
              disabled: !record.can_edit||!newNode,
              onClick: addNode
            }, "+ Узел", 8, ["disabled", "onClick"]),
            _createElementVNode("span", null, "Связь:"),
            _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((edgeFrom) = $event) }, [_createElementVNode("option", { value: "" }, "Из…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(nodes, (n) => {
              return (_openBlock(), _createElementBlock("option", {
                key: n.name,
                value: n.name
              }, _toDisplayString(n.name), 9, ["value"]))
            }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, edgeFrom]]),
            _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((edgeTo) = $event) }, [_createElementVNode("option", { value: "" }, "В…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(nodes, (n) => {
              return (_openBlock(), _createElementBlock("option", {
                key: n.name,
                value: n.name
              }, _toDisplayString(n.name), 9, ["value"]))
            }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, edgeTo]]),
            _createElementVNode("button", {
              disabled: !record.can_edit||!edgeFrom||!edgeTo,
              onClick: addEdge
            }, "+ Связь", 8, ["disabled", "onClick"])
          ]))
        : _createCommentVNode("", true),
      (!record&&!items.length&&!busy)
        ? (_openBlock(), _createElementBlock("p", {
            key: 4,
            class: "empty-hint"
          }, _toDisplayString(kind==='pipeline'?'В выбранной области пока нет pipeline. Создайте новый либо проверьте проект и фильтр исходного виджета.':'Схема не определена.'), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "graph-body" }, [_createElementVNode("div", { class: "graph-scroll" }, [(_openBlock(), _createElementBlock("svg", {
        width: 2400*scale,
        height: 1500*scale,
        class: "graph-svg"
      }, [_createElementVNode("defs", null, [_createElementVNode("marker", {
        id: "native-graph-arrow",
        markerWidth: "9",
        markerHeight: "9",
        refX: "8",
        refY: "4",
        orient: "auto"
      }, [_createElementVNode("path", { d: "M0,0 L8,4 L0,8 Z" })])]), _createElementVNode("g", { transform: 'scale('+scale+')' }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(edges, (e, i) => {
        return (_openBlock(), _createElementBlock("g", {
          key: 'e'+i,
          onClick: $event => (chooseEdge(i))
        }, [_createElementVNode("path", {
          class: "graph-edge-hit",
          d: edgePath(e)
        }, null, 8, ["d"]), _createElementVNode("path", {
          class: _normalizeClass(["graph-edge", {chosen:chosenEdge===e}]),
          "marker-end": "url(#native-graph-arrow)",
          d: edgePath(e)
        }, null, 10, ["d"])], 8, ["onClick"]))
      }), 128)), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(nodes, (n) => {
        return (_openBlock(), _createElementBlock("g", {
          key: n.name,
          transform: 'translate('+n.x+','+n.y+')',
          class: _normalizeClass(["graph-node", {chosen:chosenNode?.name===n.name}]),
          onPointerdown: $event => (down($event,n)),
          onPointermove: move,
          onPointerup: up,
          onPointercancel: up
        }, [
          _createElementVNode("rect", {
            width: "190",
            height: "64",
            rx: "7"
          }),
          (n.attributes.color)
            ? (_openBlock(), _createElementBlock("rect", {
                key: 0,
                width: "5",
                height: "64",
                style: _normalizeStyle({fill:safeColor(n.attributes.color)})
              }, null, 4))
            : _createCommentVNode("", true),
          _createElementVNode("text", {
            x: "12",
            y: "25"
          }, _toDisplayString(n.attributes.label||n.name), 1),
          _createElementVNode("text", {
            class: "node-type",
            x: "12",
            y: "46"
          }, _toDisplayString(n.type), 1)
        ], 42, ["transform", "onPointerdown", "onPointermove", "onPointerup", "onPointercancel"]))
      }), 128))], 8, ["transform"])], 8, ["width", "height"]))]), _createElementVNode("aside", { class: "graph-properties" }, [selected
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("h3", null, _toDisplayString(chosenNode?.name||'Связь'), 1), _createElementVNode("form", { onSubmit: _withModifiers(applyProperties, ["prevent"]) }, [chosenNode
            ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                _createElementVNode("label", null, [_createTextVNode("Имя"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((props.name) = $event),
                  disabled: kind==='schema'||!record.can_edit
                }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, props.name]])]),
                (kind==='pipeline')
                  ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_createTextVNode("Тип"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((props.type) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(Array.from(new Set([...types,chosenNode.type])), (t) => {
                      return (_openBlock(), _createElementBlock("option", {
                        key: t,
                        value: t
                      }, _toDisplayString(t), 9, ["value"]))
                    }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, props.type]])]))
                  : _createCommentVNode("", true),
                _createElementVNode("label", null, [_createTextVNode("Подпись"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((props.label) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.label]])]),
                _createElementVNode("label", null, [_createTextVNode("Цвет"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((props.color) = $event),
                  placeholder: "#4488aa"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.color]])]),
                _createElementVNode("div", { class: "two-cols" }, [_createElementVNode("label", null, [_createTextVNode("X"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((props.xpos) = $event),
                  type: "number"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.xpos]])]), _createElementVNode("label", null, [_createTextVNode("Y"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((props.ypos) = $event),
                  type: "number"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.ypos]])])]),
                (kind==='pipeline')
                  ? (_openBlock(), _createElementBlock("label", { key: 1 }, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": $event => ((props.description) = $event),
                      rows: "3"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.description]])]))
                  : _createCommentVNode("", true),
                (kind==='pipeline')
                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [_createElementVNode("details", null, [_createElementVNode("summary", null, "Текущие настройки config/process"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(record.settings?.[chosenNode.name]||{},null,2)), 1)]), _createElementVNode("label", null, [_createTextVNode("Изменения workflow (JSON merge)"), _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": $event => ((settingsText) = $event),
                      class: "code-input",
                      rows: "8",
                      spellcheck: "false"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settingsText]])]), _createElementVNode("small", null, "Неизвестные настройки сохраняются. Исполняемые script/class callbacks этим редактором не изменяются.")], 64))
                  : _createCommentVNode("", true)
              ], 64))
            : chosenEdge
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("p", null, _toDisplayString(chosenEdge.from) + " → " + _toDisplayString(chosenEdge.to), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList((kind==='schema'?['relationship','from_col','to_col','instance_type','path','label','color']:['from_attr','to_attr','type','label','color']), (f) => {
                  return (_openBlock(), _createElementBlock("label", { key: f }, [_createTextVNode(_toDisplayString(f), 1), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((props[f]) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props[f]]])]))
                }), 128))], 64))
              : _createCommentVNode("", true), _createElementVNode("button", {
            disabled: !record.can_edit,
            class: "primary"
          }, "Применить свойства", 8, ["disabled"]), _createElementVNode("button", {
            type: "button",
            class: "danger",
            disabled: !record.can_edit,
            onClick: remove
          }, "Удалить из графа", 8, ["disabled", "onClick"])], 40, ["onSubmit"]), _createElementVNode("details", null, [_createElementVNode("summary", null, "Все исходные атрибуты"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(chosenNode?.attributes||chosenEdge?.attributes,null,2)), 1)])], 64))
        : (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "muted"
          }, "Выберите узел или связь.")), _createElementVNode("details", null, [_createElementVNode("summary", null, "Связи: " + _toDisplayString(edges.length), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(edges, (e, i) => {
        return (_openBlock(), _createElementBlock("button", {
          key: i,
          class: "text-button",
          onClick: $event => (chooseEdge(i))
        }, _toDisplayString(e.from) + " → " + _toDisplayString(e.to), 9, ["onClick"]))
      }), 128))])])]),
      showXml
        ? (_openBlock(), _createElementBlock("pre", {
            key: 5,
            class: "raw-xml"
          }, _toDisplayString(record?.xml), 1))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const MessageContent = (function(){
const __component = {
 name:'MessageContent',props:{content:Object},
 methods:{show(value){return typeof value==='object'?JSON.stringify(value,null,2):String(value??'—')}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList } = _Vue

    return content
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "message-content"
        }, [
          _createElementVNode("p", { class: "message-text" }, _toDisplayString(content.text), 1),
          (content.progress!==null&&content.progress!==undefined)
            ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("progress", {
                value: content.progress,
                max: "100"
              }, null, 8, ["value"]), _createElementVNode("small", null, _toDisplayString(content.progress) + "%", 1)], 64))
            : _createCommentVNode("", true),
          (content.object)
            ? (_openBlock(), _createElementBlock("small", { key: 1 }, [_createElementVNode("code", null, _toDisplayString(content.object.search_type) + " · " + _toDisplayString(content.object.code), 1)]))
            : _createCommentVNode("", true),
          (content.changes?.length)
            ? (_openBlock(), _createElementBlock("dl", {
                key: 2,
                class: "message-changes"
              }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(content.changes, (change) => {
                return (_openBlock(), _createElementBlock(_Fragment, { key: change.field }, [_createElementVNode("dt", null, _toDisplayString(change.field), 1), _createElementVNode("dd", null, _toDisplayString(show(change.value)), 1)], 64))
              }), 128))]))
            : _createCommentVNode("", true)
        ]))
      : _createCommentVNode("", true)
  }
};
return __component;
})();
const MessageCenter = (function(){


const __component = {
 name:'MessageCenter',components:{MessageContent},props:{active:{type:Boolean,default:true},project:String,target:{type:String,default:''},options:{type:Object,default:()=>({})},initialCode:{type:String,default:''},login:String},emits:['close'],
 data(){return {items:[],total:0,offset:0,limit:40,category:'',mode:'all',code:'',detail:null,history:[],error:'',listError:'',busy:false,loading:false,sending:false,historyBusy:false,seq:0,listSeq:0,disposed:false,timer:null,newChat:false,users:[],userQuery:'',usersBusy:false,userSeq:0,selectedUsers:[],draft:'',draftCode:'',sendToken:'',sendBody:'',chatToken:'',chatBody:'',canWrite:false}},
 computed:{fixedCategory(){return this.options.category||''},hasMore(){return this.offset+this.items.length<this.total},last(){return this.history[this.history.length-1]},latestWithoutLog(){return this.detail?.latest&&(!this.last||this.detail.latest.login!==this.last.login||this.detail.latest.status!==this.last.status||JSON.stringify(this.detail.latest.content)!==JSON.stringify(this.last.content))},title(){return this.detail?.category==='chat'?(this.detail.participants.filter(p=>p.login!==this.login).map(p=>p.login).join(', ')||'Переписка'):this.code},showHistory(){return ![false,'false'].includes(this.options.show_message_history)},showTimestamp(){return ![false,'false'].includes(this.options.show_timestamp)}},
 async mounted(){await this.loadList();if(this.initialCode)await this.choose(this.initialCode);this.schedule()},
 beforeUnmount(){this.disposed=true;this.seq++;this.listSeq++;this.userSeq++;clearTimeout(this.timer)},
 methods:{
 args(extra={}){return {project:this.project,...(this.target?{target:this.target}:{}),...extra}},
 token(){return crypto.randomUUID?crypto.randomUUID():('native_'+Date.now()+'_'+Math.random().toString(36).slice(2))},
 schedule(){clearTimeout(this.timer);if(this.disposed)return;this.timer=setTimeout(async()=>{if(this.active&&!document.hidden&&!this.sending&&!this.busy&&!this.loading){await this.loadList(true);if(this.code)await this.loadHistory(false,true)}this.schedule()},5000)},
 async loadList(quiet=false){const seq=++this.listSeq;if(!quiet)this.loading=true;this.listError='';try{const d=await api.request('/messages',this.args({category:this.fixedCategory||this.category,mode:this.mode,offset:this.offset,limit:this.limit}));if(seq!==this.listSeq||this.disposed)return;this.items=d.items;this.total=d.total;this.canWrite=d.can_write;if(this.offset>=d.total&&this.offset>0){this.offset=0;await this.loadList(quiet)}}catch(e){if(seq===this.listSeq&&!this.disposed)this.listError=e.message}finally{if(seq===this.listSeq)this.loading=false}},
 async changeFilter(){this.offset=0;await this.loadList()},
 async page(delta){this.offset=Math.max(0,this.offset+delta*this.limit);await this.loadList()},
 async choose(code){if(code===this.code)return;if(this.draft.trim()&&!confirm('Сменить переписку и очистить неотправленный текст?'))return;this.seq++;this.code=code;this.detail=null;this.history=[];this.draft='';this.sendToken='';this.sendBody='';this.error='';this.newChat=false;await this.loadHistory()},
 merge(rows){const map=new Map(this.history.map(m=>[m.id,m]));for(const m of rows)map.set(m.id,m);this.history=[...map.values()].sort((a,b)=>{const x=BigInt(a.id),y=BigInt(b.id);return x<y?-1:x>y?1:0})},
 async loadHistory(older=false,quiet=false){if(!this.code||older&&!this.detail?.next_before)return;const seq=++this.seq,code=this.code;if(!quiet){this.historyBusy=true;this.error=''}try{const d=await api.request('/message-history',this.args({message_code:code,...(older?{before:this.detail.next_before}:{})}));if(this.disposed||seq!==this.seq||code!==this.code)return;this.merge(d.items);if(older){this.detail={...d};}else{const previous=this.detail;this.detail={...d};if(previous&&this.history.length>d.items.length){this.detail.next_before=previous.next_before;this.detail.has_more=previous.has_more}}if(!older&&!quiet)await this.$nextTick(()=>{const el=this.$refs.log;if(el)el.scrollTop=el.scrollHeight})}catch(e){if(seq===this.seq&&!this.disposed)this.error=e.message}finally{if(seq===this.seq)this.historyBusy=false}},
 async acknowledge(){if(!this.detail)return;this.busy=true;this.error='';try{await api.request('/subscriptions',this.args({message_code:this.code,revision:this.detail.revision,action:'acknowledge'}),'PATCH');await this.loadHistory(false,true);await this.loadList(true)}catch(e){this.error=e.message}finally{this.busy=false}},
 async unsubscribe(){if(!confirm('Отписаться? Сообщения и история останутся в TACTIC.'))return;this.busy=true;this.error='';try{await api.request('/subscriptions',this.args({message_code:this.code,revision:this.detail.revision,confirm:'UNSUBSCRIBE'}),'DELETE');this.seq++;this.code='';this.detail=null;this.history=[];await this.loadList()}catch(e){this.error=e.message}finally{this.busy=false}},
 async send(){if(!this.draft.trim()||this.sending||!this.detail?.can_send)return;this.sending=true;this.error='';const code=this.code,body=this.draft;if(!this.sendToken||this.sendBody!==body||this.draftCode!==code){this.sendToken=this.token();this.sendBody=body;this.draftCode=code}try{await api.request('/message-send',this.args({message_code:code,message:body,request_id:this.sendToken}),'POST');if(this.code===code){this.draft='';this.sendToken='';await this.loadHistory();await this.loadList(true)}}catch(e){this.error=e.message+' Повторная отправка неизменённого текста использует тот же request_id.'}finally{this.sending=false}},
 async userSearch(){const seq=++this.userSeq;this.usersBusy=true;try{const d=await api.request('/chat-users',this.args({query:this.userQuery}));if(seq===this.userSeq&&!this.disposed)this.users=d.items}catch(e){this.error=e.message}finally{if(seq===this.userSeq)this.usersBusy=false}},
 toggleUser(user){this.selectedUsers=this.selectedUsers.includes(user)?this.selectedUsers.filter(x=>x!==user):[...this.selectedUsers,user]},
 async createChat(){if(!this.selectedUsers.length)return;this.busy=true;this.error='';const users=[...this.selectedUsers].sort(),body=JSON.stringify(users);if(this.chatBody!==body||!this.chatToken){this.chatToken=this.token();this.chatBody=body}try{const d=await api.request('/chats',this.args({users,request_id:this.chatToken}),'POST');this.newChat=false;this.draft='';this.chatToken='';await this.loadList();await this.choose(d.message_code)}catch(e){this.error=e.message}finally{this.busy=false}},
 preview(item){const value=item.latest?.content?.text||'Нет сообщений';return value.slice(0,150)},
 async beginChat(){if(this.draft.trim()&&!confirm('Открыть создание переписки? Текст текущего черновика сохранится до выбора нового чата.'))return;this.newChat=true;this.error='';await this.userSearch()}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createElementVNode: _createElementVNode, vModelSelect: _vModelSelect, withDirectives: _withDirectives, toDisplayString: _toDisplayString, renderList: _renderList, Fragment: _Fragment, normalizeClass: _normalizeClass, vModelText: _vModelText, withModifiers: _withModifiers, withKeys: _withKeys, createTextVNode: _createTextVNode, resolveComponent: _resolveComponent, createVNode: _createVNode } = _Vue

    const _component_MessageContent = _resolveComponent("MessageContent")

    return (_openBlock(), _createElementBlock("section", {
      class: "message-center",
      "aria-label": "Сообщения и подписки"
    }, [_createElementVNode("header", {
      class: "message-center-title widget-toolbar",
      role: "group",
      "aria-label": "Действия с сообщениями"
    }, [(!fixedCategory||fixedCategory==='chat')
      ? (_openBlock(), _createElementBlock("button", {
          key: 0,
          disabled: !canWrite||busy,
          onClick: beginChat
        }, "Новая переписка", 8, ["disabled", "onClick"]))
      : _createCommentVNode("", true), _createElementVNode("button", {
      onClick: $event => {loadList();code&&loadHistory()},
      disabled: busy||loading
    }, "Обновить", 8, ["onClick", "disabled"]), _createElementVNode("button", {
      onClick: $event => ($emit('close')),
      "aria-label": "Закрыть сообщения"
    }, "×", 8, ["onClick"])]), _createElementVNode("p", { class: "notice" }, "История — message_log, последнее состояние — message. «Отметить» меняет только ваш last_cleared, это не подтверждение прочтения. Общие legacy-чаты помечены отдельно."), _createElementVNode("div", { class: "message-layout" }, [_createElementVNode("aside", { class: "message-list" }, [
      _createElementVNode("div", { class: "toolbar" }, [_withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": $event => ((mode) = $event),
        onChange: changeFilter,
        "aria-label": "Фильтр событий"
      }, [_createElementVNode("option", { value: "all" }, "Все подписки"), _createElementVNode("option", { value: "new" }, "Неотмеченные события")], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, mode]]), (!fixedCategory)
        ? _withDirectives((_openBlock(), _createElementBlock("select", {
            key: 0,
            "onUpdate:modelValue": $event => ((category) = $event),
            onChange: changeFilter,
            "aria-label": "Категория сообщений"
          }, [
            _createElementVNode("option", { value: "" }, "Все категории"),
            _createElementVNode("option", { value: "chat" }, "Переписки"),
            _createElementVNode("option", { value: "sobject" }, "Объекты"),
            _createElementVNode("option", { value: "progress" }, "Прогресс"),
            _createElementVNode("option", { value: "script" }, "Скрипты"),
            _createElementVNode("option", { value: "default" }, "Общие")
          ], 40, ["onUpdate:modelValue", "onChange"])), [[_vModelSelect, category]])
        : _createCommentVNode("", true)]),
      listError
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(listError), 1))
        : _createCommentVNode("", true),
      loading
        ? (_openBlock(), _createElementBlock("small", { key: 1 }, "Загрузка…"))
        : _createCommentVNode("", true),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (item) => {
        return (_openBlock(), _createElementBlock("button", {
          key: item.subscription,
          class: _normalizeClass(["message-list-item", {active:code===item.message_code,'is-new':item.new}]),
          onClick: $event => (choose(item.message_code))
        }, [
          _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(item.category==='chat'?'Переписка':item.category), 1), (item.new)
            ? (_openBlock(), _createElementBlock("small", {
                key: 0,
                class: "message-badge"
              }, "Новое"))
            : _createCommentVNode("", true)]),
          _createElementVNode("p", null, _toDisplayString(preview(item)), 1),
          showTimestamp
            ? (_openBlock(), _createElementBlock("small", { key: 0 }, _toDisplayString(item.latest?.login) + " · " + _toDisplayString(item.latest?.timestamp), 1))
            : _createCommentVNode("", true),
          _createElementVNode("small", { class: "message-code" }, _toDisplayString(item.message_code), 1),
          (item.legacy_global)
            ? (_openBlock(), _createElementBlock("em", { key: 1 }, "Общая legacy-подписка"))
            : _createCommentVNode("", true)
        ], 10, ["onClick"]))
      }), 128)),
      (!items.length&&!loading)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "Нет подписок в этой выборке."))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
        disabled: offset===0||loading,
        onClick: $event => (page(-1))
      }, "Назад", 8, ["disabled", "onClick"]), _createElementVNode("small", null, _toDisplayString(items.length?offset+1:0) + "–" + _toDisplayString(offset+items.length) + " / " + _toDisplayString(total), 1), _createElementVNode("button", {
        disabled: !hasMore||loading,
        onClick: $event => (page(1))
      }, "Далее", 8, ["disabled", "onClick"])])
    ]), _createElementVNode("div", { class: "message-detail" }, [error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), newChat
      ? (_openBlock(), _createElementBlock("form", {
          key: 1,
          class: "chat-create",
          onSubmit: _withModifiers(createChat, ["prevent"])
        }, [
          _createElementVNode("h3", null, "Участники переписки"),
          _createElementVNode("p", { class: "notice" }, "Повторно откроется только чат с тем же полным составом участников, а не любая общая переписка."),
          _createElementVNode("div", { class: "toolbar" }, [_withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((userQuery) = $event),
            placeholder: "Логин или имя",
            onKeydown: _withKeys(_withModifiers(userSearch, ["prevent"]), ["enter"])
          }, null, 40, ["onUpdate:modelValue", "onKeydown"]), [[_vModelText, userQuery]]), _createElementVNode("button", {
            type: "button",
            onClick: userSearch,
            disabled: usersBusy
          }, "Найти", 8, ["onClick", "disabled"])]),
          _createElementVNode("div", { class: "chat-user-results" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(users, (u) => {
            return (_openBlock(), _createElementBlock("label", { key: u.login }, [_createElementVNode("input", {
              type: "checkbox",
              checked: selectedUsers.includes(u.login),
              onChange: $event => (toggleUser(u.login))
            }, null, 40, ["checked", "onChange"]), _createTextVNode(_toDisplayString(u.name) + " ", 1), _createElementVNode("small", null, _toDisplayString(u.login), 1)]))
          }), 128))]),
          _createElementVNode("p", null, "Выбраны: " + _toDisplayString(selectedUsers.join(', ')||'—'), 1),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            class: "primary",
            disabled: busy||!selectedUsers.length||selectedUsers.length>30
          }, "Открыть переписку", 8, ["disabled"]), _createElementVNode("button", {
            type: "button",
            onClick: $event => (newChat=false)
          }, "Отмена", 8, ["onClick"])])
        ], 40, ["onSubmit"]))
      : detail
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
            _createElementVNode("header", { class: "message-detail-head" }, [
              _createElementVNode("div", null, [_createElementVNode("h3", null, _toDisplayString(title), 1), _createElementVNode("code", null, _toDisplayString(code), 1), (detail.legacy_global)
                ? (_openBlock(), _createElementBlock("small", { key: 0 }, "Общий legacy-чат без project_code"))
                : _createCommentVNode("", true)]),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", {
                disabled: !detail.can_ack||busy,
                onClick: acknowledge
              }, "Отметить показанное", 8, ["disabled", "onClick"]),
              (detail.can_unsubscribe)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    disabled: busy,
                    onClick: unsubscribe
                  }, "Отписаться", 8, ["disabled", "onClick"]))
                : _createCommentVNode("", true)
            ]),
            (detail.participants.length)
              ? (_openBlock(), _createElementBlock("details", {
                  key: 0,
                  class: "message-participants"
                }, [_createElementVNode("summary", null, "Участники и отметки · " + _toDisplayString(detail.participants.length), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.participants, (p) => {
                  return (_openBlock(), _createElementBlock("p", { key: p.login }, [_createElementVNode("b", null, _toDisplayString(p.login), 1), _createTextVNode(" · отмечено до " + _toDisplayString(p.last_cleared||'—'), 1)]))
                }), 128))]))
              : _createCommentVNode("", true),
            _createElementVNode("small", null, "Ваша отметка: " + _toDisplayString(detail.last_cleared||'нет'), 1),
            _createElementVNode("div", {
              ref: "log",
              class: "message-history",
              "aria-live": "polite"
            }, [
              (showHistory&&detail.has_more)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    onClick: $event => (loadHistory(true)),
                    disabled: historyBusy
                  }, "Загрузить предыдущие сообщения", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList((showHistory?history:[]), (m) => {
                return (_openBlock(), _createElementBlock("article", {
                  key: m.id,
                  class: _normalizeClass(["message-event", {own:m.login===login}])
                }, [_createElementVNode("header", null, [_createElementVNode("b", null, _toDisplayString(m.login), 1), showTimestamp
                  ? (_openBlock(), _createElementBlock("small", { key: 0 }, _toDisplayString(m.timestamp), 1))
                  : _createCommentVNode("", true), (detail.legacy_global)
                  ? (_openBlock(), _createElementBlock("small", { key: 1 }, _toDisplayString(m.project), 1))
                  : _createCommentVNode("", true)]), _createVNode(_component_MessageContent, { content: m.content }, null, 8, ["content"]), (m.status)
                  ? (_openBlock(), _createElementBlock("small", { key: 0 }, _toDisplayString(m.status), 1))
                  : _createCommentVNode("", true)], 2))
              }), 128)),
              (latestWithoutLog||!showHistory)
                ? (_openBlock(), _createElementBlock("article", {
                    key: 1,
                    class: "message-event latest-state"
                  }, [_createElementVNode("small", null, "Последнее состояние, не отдельная запись истории"), _createVNode(_component_MessageContent, { content: detail.latest?.content }, null, 8, ["content"])]))
                : _createCommentVNode("", true),
              (!history.length&&!detail.latest)
                ? (_openBlock(), _createElementBlock("p", {
                    key: 2,
                    class: "muted"
                  }, "По этой подписке ещё не было событий."))
                : _createCommentVNode("", true)
            ], 512),
            (detail.can_send)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 1,
                  class: "message-compose",
                  onSubmit: _withModifiers(send, ["prevent"])
                }, [_withDirectives(_createElementVNode("textarea", {
                  "onUpdate:modelValue": $event => ((draft) = $event),
                  rows: "3",
                  maxlength: "16000",
                  placeholder: "Сообщение · Ctrl+Enter для отправки",
                  onKeydown: _withKeys(_withModifiers(send, ["ctrl","prevent"]), ["enter"]),
                  disabled: sending
                }, null, 40, ["onUpdate:modelValue", "onKeydown", "disabled"]), [[_vModelText, draft]]), _createElementVNode("button", {
                  class: "primary",
                  disabled: sending||!draft.trim()
                }, _toDisplayString(sending?'Отправка…':'Отправить сообщение'), 9, ["disabled"])], 40, ["onSubmit"]))
              : (_openBlock(), _createElementBlock("p", {
                  key: 2,
                  class: "muted"
                }, _toDisplayString(detail.category==='chat'?'Запись выключена настройками сервера.':'Системные события доступны только для чтения.'), 1))
          ], 64))
        : (!historyBusy)
          ? (_openBlock(), _createElementBlock("p", {
              key: 3,
              class: "message-empty"
            }, "Выберите подписку или переписку. История загружается по идентификаторам записей, одинаковые тексты не удаляются как дубликаты."))
          : (_openBlock(), _createElementBlock("p", { key: 4 }, "Загрузка истории…"))])])]))
  }
};
return __component;
})();
const SubscriptionPanel = (function(){

const __component = {
 name:'SubscriptionPanel',props:{project:String,target:String,record:Object},emits:['messages'],
 data(){return {state:null,error:'',busy:false}},mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},async load(){this.error='';try{this.state=await api.request('/record-subscription',this.args())}catch(e){this.error=e.message}},async change(){if(!this.state)return;if(this.state.subscribed&&!confirm('Отписаться от событий объекта? История останется в TACTIC.'))return;this.busy=true;this.error='';try{await api.request('/record-subscription',{...this.args(),revision:this.state.revision,...(this.state.subscribed?{confirm:'UNSUBSCRIBE'}:{})},this.state.subscribed?'DELETE':'POST');await this.load()}catch(e){this.error=e.message}finally{this.busy=false}}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, Fragment: _Fragment } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "subscription-panel" }, [_createElementVNode("h3", null, "События объекта"), error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), state
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          _createElementVNode("code", null, _toDisplayString(state.message_code), 1),
          _createElementVNode("p", { class: "notice" }, _toDisplayString(state.notice), 1),
          _createElementVNode("p", null, _toDisplayString(state.subscribed?'Вы подписаны на изменения.':'Подписки пока нет.'), 1),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            disabled: !state.can_write||busy,
            onClick: change
          }, _toDisplayString(state.subscribed?'Отписаться от объекта':'Подписаться на объект'), 9, ["disabled", "onClick"]), (state.subscribed)
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                onClick: $event => ($emit('messages',state.message_code))
              }, "Открыть события", 8, ["onClick"]))
            : _createCommentVNode("", true), _createElementVNode("button", {
            onClick: load,
            disabled: busy
          }, "Обновить", 8, ["onClick", "disabled"])])
        ], 64))
      : _createCommentVNode("", true)]))
  }
};
return __component;
})();
const UploadQueue = (function(){

const __component = {
 name:'UploadQueue',props:{project:String,target:String,recordKey:String},emits:['changed'],
 data(){return {jobs:[],limits:null,allowed:false,context:'publish',description:'',error:'',status:'',active:'',paused:false,alive:true,controller:null,files:new Map(),actionBusy:false}},
 mounted(){this.load()},beforeUnmount(){this.alive=false;this.paused=true;this.controller?.abort()},
 methods:{
 args(extra={}){return {project:this.project,target:this.target,key:this.recordKey,...extra}},
 bytes(n){return n>=1073741824?(n/1073741824).toFixed(2)+' ГиБ':n>=1048576?(n/1048576).toFixed(1)+' МиБ':n+' байт'},
 stateLabel(s){return ({uploading:'Приём файла',ready:'Готов к check-in',committing:'Выполняется check-in',uncertain:'Проверьте результат в версиях',complete:'Check-in завершён',cancelled:'Отменено'})[s]||s},
 update(job){if(!this.alive)return;const i=this.jobs.findIndex(x=>x.id===job.id);if(i<0)this.jobs.unshift(job);else this.jobs.splice(i,1,job)},
 async load(){this.error='';try{const data=await api.request('/uploads',this.args());if(!this.alive)return;this.jobs=data.items;this.limits=data.limits;this.allowed=data.can_upload}catch(e){if(this.alive)this.error=e.message}},
 async hash(buffer){if(!crypto.subtle)throw Error('SHA-256 требует безопасного контекста: localhost или HTTPS');return new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))},
 hex(bytes){return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')},
 async fingerprint(file){
  const chunk=this.limits.chunk_bytes;const hashes=new Uint8Array(Math.ceil(file.size/chunk)*32);
  for(let offset=0,i=0;offset<file.size;offset+=chunk,i++){
   if(!this.alive||this.paused)throw Error('Проверка файла остановлена');
   this.status='Проверка файла: '+this.bytes(Math.min(file.size,offset+chunk))+' / '+this.bytes(file.size);
   hashes.set(await this.hash(await file.slice(offset,offset+chunk).arrayBuffer()),i*32);
  }
  return this.hex(await this.hash(hashes));
 },
 async pick(event,existing=null){
  const selected=Array.from(event.target.files||[]);event.target.value='';if(!selected.length||this.active||this.actionBusy)return;
  this.error='';this.paused=false;this.active='scan';
  try{
   for(const file of selected){
    if(file.size<1||file.size>this.limits.max_file_bytes)throw Error('Файл вне лимита: '+file.name);
    if(existing&&(file.name!==existing.filename||file.size!==existing.size))throw Error('Выберите исходный файл с тем же именем и размером');
    const fingerprint=await this.fingerprint(file);if(!this.alive)return;
    if(existing&&fingerprint!==existing.fingerprint)throw Error('Содержимое выбранного файла отличается от исходного; продолжение запрещено');
    let job=existing||await api.request('/uploads',this.args({filename:file.name,size:file.size,fingerprint,context:this.context,description:this.description,request_id:crypto.randomUUID()}),'POST');
    this.files.set(job.id,file);this.update(job);await this.send(job,file);
    if(this.paused||!this.alive)break;
   }
  }catch(e){if(this.alive&&e.name!=='AbortError')this.error=e.message}finally{if(this.alive){this.active='';this.status='';this.controller=null}}
 },
 async send(job,file){
  job=await api.request('/upload-status',this.args({upload_id:job.id}));this.update(job);this.active=job.id;
  while(this.alive&&!this.paused&&job.state==='uploading'){
   const part=await file.slice(job.offset,job.offset+job.chunk_bytes).arrayBuffer();
   const sha256=this.hex(await this.hash(part));if(this.paused||!this.alive)break;
   this.controller=new AbortController();
   job=await api.uploadChunk(this.args({upload_id:job.id,offset:job.offset,sha256}),part,this.controller.signal);this.update(job);
  }
 },
 async resume(job){if(!this.files.has(job.id))return;this.active=job.id;this.paused=false;this.error='';try{await this.send(job,this.files.get(job.id))}catch(e){if(this.alive&&e.name!=='AbortError')this.error=e.message}finally{if(this.alive){this.active='';this.controller=null}}},
 pause(){this.paused=true;this.controller?.abort()},
 async finish(job){this.error='';this.actionBusy=true;try{const result=await api.request('/upload-finish',this.args({upload_id:job.id}),'POST');this.update(result);this.files.delete(job.id);if(this.alive)this.$emit('changed')}catch(e){if(this.alive)this.error=e.message;try{this.update(await api.request('/upload-status',this.args({upload_id:job.id})))}catch{}}finally{if(this.alive)this.actionBusy=false}},
 async cancel(job){if(!confirm('Удалить только временную загрузку «'+job.filename+'»?'))return;this.error='';try{this.update(await api.request('/uploads',this.args({upload_id:job.id}),'DELETE'));this.files.delete(job.id)}catch(e){this.error=e.message}},
 async check(job){try{this.update(await api.request('/upload-status',this.args({upload_id:job.id})))}catch(e){this.error=e.message}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withDirectives: _withDirectives, createTextVNode: _createTextVNode, renderList: _renderList, Fragment: _Fragment } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "upload-queue" }, [_createElementVNode("header", null, [_createElementVNode("h3", null, "Загрузка и check-in"), _createElementVNode("button", {
      disabled: !!active||actionBusy,
      onClick: load
    }, "Обновить очередь", 8, ["disabled", "onClick"])]), error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), limits
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          _createElementVNode("p", { class: "muted" }, "До " + _toDisplayString(bytes(limits.max_file_bytes)) + " на файл · части " + _toDisplayString(bytes(limits.chunk_bytes)) + ". После загрузки отдельно выполните check-in.", 1),
          allowed
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "upload-controls"
              }, [_createElementVNode("label", null, [_createTextVNode("Context"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((context) = $event),
                disabled: !!active||actionBusy
              }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, context]])]), _createElementVNode("label", null, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
                "onUpdate:modelValue": $event => ((description) = $event),
                rows: "2",
                disabled: !!active||actionBusy
              }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, description]])]), _createElementVNode("label", { class: "button" }, [_createTextVNode("Выбрать файлы"), _createElementVNode("input", {
                class: "upload-pick",
                type: "file",
                multiple: "",
                disabled: !!active||actionBusy,
                onChange: $event => (pick($event))
              }, null, 40, ["disabled", "onChange"])])]))
            : (_openBlock(), _createElementBlock("p", {
                key: 1,
                class: "notice"
              }, "Загрузка выключена: allow_writes и allow_uploads должны быть включены на тестовой установке.")),
          status
            ? (_openBlock(), _createElementBlock("p", {
                key: 2,
                role: "status"
              }, _toDisplayString(status), 1))
            : _createCommentVNode("", true),
          active
            ? (_openBlock(), _createElementBlock("button", {
                key: 3,
                onClick: pause
              }, "Приостановить", 8, ["onClick"]))
            : _createCommentVNode("", true),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(jobs, (j) => {
            return (_openBlock(), _createElementBlock("article", {
              key: j.id,
              class: "upload-job",
              "data-upload-id": j.id
            }, [
              _createElementVNode("header", null, [_createElementVNode("b", null, _toDisplayString(j.filename), 1), _createElementVNode("small", null, _toDisplayString(stateLabel(j.state)), 1)]),
              _createElementVNode("progress", {
                value: j.offset,
                max: j.size
              }, null, 8, ["value", "max"]),
              _createElementVNode("small", null, _toDisplayString(bytes(j.offset)) + " / " + _toDisplayString(bytes(j.size)) + " · " + _toDisplayString(j.context), 1),
              (['uploading','ready'].includes(j.state))
                ? (_openBlock(), _createElementBlock("small", {
                    key: 0,
                    class: "upload-expiry"
                  }, "Хранится до " + _toDisplayString(new Date(j.expires*1000).toLocaleString()), 1))
                : _createCommentVNode("", true),
              (j.state==='uncertain')
                ? (_openBlock(), _createElementBlock("p", {
                    key: 1,
                    class: "error"
                  }, "Check-in мог выполниться до обрыва. Проверьте версии и серверный журнал. Повтор и удаление временного файла автоматически не выполняются."))
                : _createCommentVNode("", true),
              (j.state==='complete'&&j.result?.snapshot)
                ? (_openBlock(), _createElementBlock("code", {
                    key: 2,
                    class: "receipt"
                  }, _toDisplayString(j.result.snapshot.code||j.result.snapshot.__search_key__), 1))
                : _createCommentVNode("", true),
              _createElementVNode("div", { class: "toolbar" }, [
                (allowed&&j.state==='uploading')
                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [(files.has(j.id))
                      ? (_openBlock(), _createElementBlock("button", {
                          key: 0,
                          disabled: !!active||actionBusy,
                          onClick: $event => (resume(j))
                        }, "Продолжить", 8, ["disabled", "onClick"]))
                      : (_openBlock(), _createElementBlock("label", {
                          key: 1,
                          class: "button"
                        }, [_createTextVNode("Выбрать тот же файл"), _createElementVNode("input", {
                          type: "file",
                          disabled: !!active||actionBusy,
                          onChange: $event => (pick($event,j))
                        }, null, 40, ["disabled", "onChange"])]))], 64))
                  : _createCommentVNode("", true),
                (j.state==='ready'&&allowed)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 1,
                      class: "primary",
                      disabled: !!active||actionBusy,
                      onClick: $event => (finish(j))
                    }, _toDisplayString(actionBusy?'Выполняется…':'Выполнить check-in'), 9, ["disabled", "onClick"]))
                  : _createCommentVNode("", true),
                (['uploading','ready'].includes(j.state)&&allowed)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 2,
                      disabled: !!active||actionBusy,
                      onClick: $event => (cancel(j))
                    }, "Отменить загрузку", 8, ["disabled", "onClick"]))
                  : _createCommentVNode("", true),
                (j.state==='committing')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 3,
                      disabled: actionBusy,
                      onClick: $event => (check(j))
                    }, "Проверить состояние", 8, ["disabled", "onClick"]))
                  : _createCommentVNode("", true)
              ])
            ], 8, ["data-upload-id"]))
          }), 128)),
          (!jobs.length)
            ? (_openBlock(), _createElementBlock("p", {
                key: 4,
                class: "muted"
              }, "Очередь пуста."))
            : _createCommentVNode("", true),
          _createElementVNode("small", null, "Подтверждённая позиция хранится на сервере. После перезахода выберите тот же файл; все его блоки проверяются SHA-256. Это временное хранилище, не новая версия TACTIC.")
        ], 64))
      : _createCommentVNode("", true)]))
  }
};
return __component;
})();
const FilePanel = (function(){


const __component = {
 name:'FilePanel',components:{UploadQueue},props:{project:String,target:String,recordKey:String},emits:['changed'],
 data(){return {page:{items:[],total:0,offset:0,limit:40},context:'',archives:false,error:'',busy:false,preview:null,currentChoice:null,seq:0,alive:true,uploadsOpen:false}},
 mounted(){this.load()},beforeUnmount(){this.alive=false;this.seq++},
 methods:{
 args(extra={}){return {project:this.project,target:this.target,key:this.recordKey,...extra}},
 async load(offset=0){const seq=++this.seq;this.busy=true;this.error='';try{const page=await api.request('/file-versions',this.args({offset,limit:40,context:this.context,record_state:this.archives?'all':'active'}));if(seq===this.seq&&this.alive)this.page=page}catch(e){if(seq===this.seq&&this.alive)this.error=e.message}finally{if(seq===this.seq&&this.alive)this.busy=false}},
 url(s,f,preview=false){const url=new URL('/api/ui/v2/file',location.origin);Object.entries(this.args({snapshot:s.key,file:f.code,preview:preview?'1':'0'})).forEach(([k,v])=>url.searchParams.set(k,v));return url.href},
 async choose(snapshot){this.error='';try{this.currentChoice=await api.request('/snapshot-current',this.args({snapshot:snapshot.key}))}catch(e){this.error=e.message}},
 async setCurrent(){this.busy=true;this.error='';try{await api.request('/snapshot-current',this.args({snapshot:this.currentChoice.selected.key,revision:this.currentChoice.revision,confirm:'SET_CURRENT'}),'POST');this.currentChoice=null;await this.load(this.page.offset);this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 checked(){this.load();this.$emit('changed')},
 truth(v){return v===true||v===1||v==='true'||v==='t'},
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, normalizeClass: _normalizeClass, resolveComponent: _resolveComponent, openBlock: _openBlock, createBlock: _createBlock, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withDirectives: _withDirectives, vModelCheckbox: _vModelCheckbox, createTextVNode: _createTextVNode, withModifiers: _withModifiers, toDisplayString: _toDisplayString, createElementBlock: _createElementBlock, renderList: _renderList, Fragment: _Fragment, Teleport: _Teleport } = _Vue

    const _component_UploadQueue = _resolveComponent("UploadQueue")

    return (_openBlock(), _createElementBlock("section", { class: "file-panel" }, [
      _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("h3", null, "Версии и файлы"), _createElementVNode("span", { class: "spacer" }), _createElementVNode("button", {
        class: _normalizeClass({primary:uploadsOpen}),
        onClick: $event => (uploadsOpen=!uploadsOpen)
      }, "Загрузка файлов", 10, ["onClick"])]),
      uploadsOpen
        ? (_openBlock(), _createBlock(_component_UploadQueue, {
            key: 0,
            project: project,
            target: target,
            "record-key": recordKey,
            onChanged: checked
          }, null, 8, ["project", "target", "record-key", "onChanged"]))
        : _createCommentVNode("", true),
      _createElementVNode("form", {
        class: "version-filter toolbar",
        onSubmit: _withModifiers($event => (load()), ["prevent"])
      }, [_withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": $event => ((context) = $event),
        placeholder: "Точный context или все",
        "aria-label": "Контекст версий"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, context]]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
        type: "checkbox",
        "onUpdate:modelValue": $event => ((archives) = $event),
        onChange: $event => (load())
      }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelCheckbox, archives]]), _createTextVNode("Включая архив")]), _createElementVNode("button", { disabled: busy }, "Применить", 8, ["disabled"])], 40, ["onSubmit"]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("p", { class: "notice" }, _toDisplayString(page.notice), 1),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(page.items, (s) => {
        return (_openBlock(), _createElementBlock("article", {
          key: s.key,
          class: "snapshot"
        }, [
          _createElementVNode("header", null, [
            _createElementVNode("b", null, _toDisplayString(s.context) + " · v" + _toDisplayString(s.version), 1),
            (truth(s.is_current))
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  class: "tag"
                }, "current"))
              : _createCommentVNode("", true),
            (truth(s.is_latest))
              ? (_openBlock(), _createElementBlock("span", {
                  key: 1,
                  class: "tag"
                }, "latest"))
              : _createCommentVNode("", true),
            (s.s_status==='retired')
              ? (_openBlock(), _createElementBlock("span", {
                  key: 2,
                  class: "tag"
                }, "архив"))
              : _createCommentVNode("", true)
          ]),
          _createElementVNode("small", null, _toDisplayString(s.timestamp) + " · " + _toDisplayString(s.login) + " · " + _toDisplayString(s.code), 1),
          _createElementVNode("p", null, _toDisplayString(s.description), 1),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(s.files, (f) => {
            return (_openBlock(), _createElementBlock("div", {
              key: f.code,
              class: "file-row"
            }, [(!f.missing_registration)
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("a", {
                  href: url(s,f),
                  download: ""
                }, _toDisplayString(f.name), 9, ["href"]), _createElementVNode("small", null, _toDisplayString(f.type) + " · " + _toDisplayString(f.size??'—') + " байт", 1), (f.preview)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      onClick: $event => (preview={url:url(s,f,true),mime:f.mime,name:f.name})
                    }, "Просмотр", 8, ["onClick"]))
                  : _createCommentVNode("", true)], 64))
              : (_openBlock(), _createElementBlock("p", {
                  key: 1,
                  class: "error"
                }, _toDisplayString(f.code) + ": запись файла отсутствует; содержимое не подменяется.", 1))]))
          }), 128)),
          (Number(s.version)>=0&&s.s_status!=='retired'&&!truth(s.is_current))
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                onClick: $event => (choose(s))
              }, "Выбрать current…", 8, ["onClick"]))
            : _createCommentVNode("", true)
        ]))
      }), 128)),
      (!busy&&!page.items.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "Версии не найдены."))
        : _createCommentVNode("", true),
      _createElementVNode("footer", { class: "toolbar" }, [
        _createElementVNode("small", null, _toDisplayString(page.total? page.offset+1:0) + "–" + _toDisplayString(page.offset+page.items.length) + " из " + _toDisplayString(page.total), 1),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("button", {
          disabled: busy||!page.offset,
          onClick: $event => (load(Math.max(0,page.offset-page.limit)))
        }, "Назад", 8, ["disabled", "onClick"]),
        _createElementVNode("button", {
          disabled: busy||!page.has_more,
          onClick: $event => (load(page.offset+page.limit))
        }, "Далее", 8, ["disabled", "onClick"])
      ]),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [currentChoice
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop"
          }, [_createElementVNode("section", {
            class: "modal current-dialog",
            role: "dialog"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h3", null, "Сменить current-версию"), _createElementVNode("button", { onClick: $event => (currentChoice=null) }, "×", 8, ["onClick"])]),
            _createElementVNode("p", null, _toDisplayString(currentChoice.selected.context) + " · v" + _toDisplayString(currentChoice.selected.version) + " · " + _toDisplayString(currentChoice.selected.code), 1),
            _createElementVNode("p", null, "Сейчас current: " + _toDisplayString(currentChoice.current.map(s=>s.code).join(', ')||'не выбрана'), 1),
            _createElementVNode("p", { class: "notice" }, _toDisplayString(currentChoice.notice), 1),
            error
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            _createElementVNode("button", {
              class: "primary",
              disabled: busy||!currentChoice.can_write,
              onClick: setCurrent
            }, "Подтвердить current", 8, ["disabled", "onClick"])
          ])]))
        : _createCommentVNode("", true), preview
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "modal-backdrop",
            onClick: _withModifiers($event => (preview=null), ["self"])
          }, [_createElementVNode("section", { class: "modal preview-modal" }, [_createElementVNode("header", null, [_createElementVNode("h3", null, _toDisplayString(preview.name), 1), _createElementVNode("button", { onClick: $event => (preview=null) }, "×", 8, ["onClick"])]), (preview.mime.startsWith('image/'))
            ? (_openBlock(), _createElementBlock("img", {
                key: 0,
                src: preview.url,
                alt: preview.name
              }, null, 8, ["src", "alt"]))
            : (preview.mime.startsWith('video/'))
              ? (_openBlock(), _createElementBlock("video", {
                  key: 1,
                  src: preview.url,
                  controls: ""
                }, null, 8, ["src"]))
              : (_openBlock(), _createElementBlock("audio", {
                  key: 2,
                  src: preview.url,
                  controls: ""
                }, null, 8, ["src"]))])], 8, ["onClick"]))
        : _createCommentVNode("", true)]))
    ]))
  }
};
return __component;
})();
const RecordInspector = (function(){






const __component = {
 name:'RecordInspector',components:{FilePanel,TaskPanel,HistoryPanel,RelationshipEditor,SubscriptionPanel},props:{project:String,target:String,record:Object,spec:Object,allowUploads:Boolean},emits:['close','edit','open','changed','messages'],
 data(){return {section:['files','history','subscription'].includes(this.record._section)?this.record._section:'fields',relations:[],notes:[],error:'',busy:false,comment:'',process:'publish',canNote:false,editingRelation:null}},
 methods:{
 args(){return {project:this.project,target:this.target,key:this.record.key}},
 files(){this.section='files';this.error=''},
 async related(){this.section='relations';this.error='';try{this.relations=(await api.request('/relations',this.args())).items}catch(e){this.error=e.message}},
 async discussion(){this.section='notes';this.error='';try{const d=await api.request('/notes',this.args());this.notes=d.items;this.canNote=d.can_write}catch(e){this.error=e.message}},
 async addNote(){this.busy=true;this.error='';try{await api.request('/notes',{...this.args(),note:this.comment,process:this.process},'POST');this.comment='';await this.discussion()}catch(e){this.error=e.message}finally{this.busy=false}},
 show(value){if(value===null||value===undefined)return '—';return typeof value==='object'?JSON.stringify(value,null,2):String(value)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, normalizeClass: _normalizeClass, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, resolveComponent: _resolveComponent, createBlock: _createBlock, vModelText: _vModelText, withDirectives: _withDirectives, createTextVNode: _createTextVNode, withModifiers: _withModifiers } = _Vue

    const _component_FilePanel = _resolveComponent("FilePanel")
    const _component_SubscriptionPanel = _resolveComponent("SubscriptionPanel")
    const _component_TaskPanel = _resolveComponent("TaskPanel")
    const _component_HistoryPanel = _resolveComponent("HistoryPanel")
    const _component_RelationshipEditor = _resolveComponent("RelationshipEditor")

    return (_openBlock(), _createElementBlock("aside", { class: "inspector" }, [
      _createElementVNode("header", null, [_createElementVNode("h2", null, "Запись TACTIC"), _createElementVNode("button", {
        onClick: $event => ($emit('close')),
        "aria-label": "Закрыть"
      }, "×", 8, ["onClick"])]),
      _createElementVNode("code", { class: "search-key" }, _toDisplayString(record.key), 1),
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='fields'}),
          onClick: $event => (section='fields')
        }, "Поля", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='files'}),
          onClick: files
        }, "Файлы", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='relations'}),
          onClick: related
        }, "Связи", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='notes'}),
          onClick: discussion
        }, "Обсуждение", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='tasks'}),
          onClick: $event => (section='tasks')
        }, "Задачи", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='history'}),
          onClick: $event => (section='history')
        }, "История", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:section==='subscription'}),
          onClick: $event => (section='subscription')
        }, "Подписка", 10, ["onClick"]),
        _createElementVNode("button", {
          disabled: !spec.capabilities.update,
          onClick: $event => ($emit('edit',record))
        }, "Изменить", 8, ["disabled", "onClick"])
      ]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (section==='fields')
        ? (_openBlock(), _createElementBlock("dl", { key: 1 }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(spec.fields, (f) => {
            return (_openBlock(), _createElementBlock(_Fragment, { key: f.name }, [_createElementVNode("dt", null, _toDisplayString(f.label), 1), _createElementVNode("dd", null, _toDisplayString(show(record.values[f.name])), 1)], 64))
          }), 128))]))
        : (section==='files')
          ? (_openBlock(), _createBlock(_component_FilePanel, {
              key: record.key,
              project: project,
              target: target,
              "record-key": record.key,
              onChanged: $event => ($emit('changed'))
            }, null, 8, ["project", "target", "record-key", "onChanged"]))
          : (section==='relations')
            ? (_openBlock(), _createElementBlock("div", { key: 3 }, [_createElementVNode("p", { class: "notice" }, "Связи разрешены исходной Schema, включая instance-таблицы."), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(relations, (r) => {
                return (_openBlock(), _createElementBlock("article", {
                  key: r.search_type,
                  class: "relation-row"
                }, [_createElementVNode("button", {
                  disabled: !r.target,
                  onClick: $event => ($emit('open',{id:r.target}))
                }, _toDisplayString(r.search_type) + " · " + _toDisplayString(r.count??'—'), 9, ["disabled", "onClick"]), _createElementVNode("small", null, _toDisplayString(r.relationship) + " " + _toDisplayString(r.error), 1), (r.relationship==='instance')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      onClick: $event => (editingRelation=r.search_type)
                    }, "Изменить связи", 8, ["onClick"]))
                  : _createCommentVNode("", true)]))
              }), 128)), (!relations.length)
                ? (_openBlock(), _createElementBlock("p", {
                    key: 0,
                    class: "muted"
                  }, "Нет объявленных связей."))
                : _createCommentVNode("", true)]))
            : (section==='notes')
              ? (_openBlock(), _createElementBlock("div", { key: 4 }, [canNote
                  ? (_openBlock(), _createElementBlock("form", {
                      key: 0,
                      onSubmit: _withModifiers(addNote, ["prevent"])
                    }, [_createElementVNode("label", null, [_createTextVNode("Процесс"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((process) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, process]])]), _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": $event => ((comment) = $event),
                      rows: "4",
                      placeholder: "Комментарий к объекту"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, comment]]), _createElementVNode("button", {
                      class: "primary",
                      disabled: busy||!comment.trim()
                    }, "Отправить", 8, ["disabled"])], 40, ["onSubmit"]))
                  : _createCommentVNode("", true), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(notes, (n) => {
                  return (_openBlock(), _createElementBlock("article", {
                    key: n.key,
                    class: "note"
                  }, [_createElementVNode("header", null, [_createElementVNode("b", null, _toDisplayString(n.login), 1), _createElementVNode("small", null, _toDisplayString(n.timestamp), 1)]), _createElementVNode("small", null, _toDisplayString(n.process) + " · " + _toDisplayString(n.access), 1), _createElementVNode("p", null, _toDisplayString(n.note), 1)]))
                }), 128)), (!notes.length)
                  ? (_openBlock(), _createElementBlock("p", {
                      key: 1,
                      class: "muted"
                    }, "Комментариев пока нет."))
                  : _createCommentVNode("", true)]))
              : (section==='subscription')
                ? (_openBlock(), _createBlock(_component_SubscriptionPanel, {
                    key: 5,
                    project: project,
                    target: target,
                    record: record,
                    onMessages: $event => ($emit('messages',$event))
                  }, null, 8, ["project", "target", "record", "onMessages"]))
                : (section==='tasks')
                  ? (_openBlock(), _createBlock(_component_TaskPanel, {
                      key: 6,
                      project: project,
                      target: target,
                      record: record,
                      onChanged: $event => ($emit('changed'))
                    }, null, 8, ["project", "target", "record", "onChanged"]))
                  : (section==='history')
                    ? (_openBlock(), _createBlock(_component_HistoryPanel, {
                        key: 7,
                        project: project,
                        target: target,
                        record: record,
                        onChanged: $event => ($emit('changed'))
                      }, null, 8, ["project", "target", "record", "onChanged"]))
                    : _createCommentVNode("", true),
      editingRelation
        ? (_openBlock(), _createBlock(_component_RelationshipEditor, {
            key: 8,
            project: project,
            target: target,
            record: record,
            "related-type": editingRelation,
            onClose: $event => (editingRelation=null),
            onChanged: $event => {related();$emit('changed')}
          }, null, 8, ["project", "target", "record", "related-type", "onClose", "onChanged"]))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const GroupMembership = (function(){

const __component = {
 name:'GroupMembership',props:['project','target','initialKey'],emits:['changed'],
 data(){return {groups:[],selected:'',group:null,members:[],query:'',busy:false,error:'',message:''}},
 computed:{users(){const q=this.query.toLowerCase();return (this.group?.users||[]).filter(u=>u.login.toLowerCase().includes(q)||u.name.toLowerCase().includes(q))},dirty(){return this.group&&JSON.stringify([...this.members].sort())!==JSON.stringify([...this.group.members].sort())}},
 async mounted(){try{this.groups=(await api.request('/memberships',{project:this.project,target:this.target})).items;if(this.initialKey){this.selected=this.initialKey;await this.load()}}catch(e){this.error=e.message}},
 methods:{
 async load(){this.error='';this.message='';this.group=null;this.busy=true;try{if(this.selected){this.group=await api.request('/memberships',{project:this.project,target:this.target,key:this.selected});this.members=[...this.group.members]}}catch(e){this.error=e.message}finally{this.busy=false}},
 async save(){this.error='';this.message='';this.busy=true;try{await api.request('/memberships',{project:this.project,target:this.target,key:this.group.key,members:this.members,revision:this.group.revision},'POST');await this.load();this.message='Состав группы сохранён через команду TACTIC';this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, vModelText: _vModelText, createCommentVNode: _createCommentVNode, vModelCheckbox: _vModelCheckbox } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "membership-panel" }, [
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("label", null, [_createTextVNode("Группа"), _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((selected) = $event),
          onChange: load,
          disabled: busy
        }, [_createElementVNode("option", { value: "" }, "Выберите группу…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (g) => {
          return (_openBlock(), _createElementBlock("option", {
            key: g.key,
            value: g.key
          }, _toDisplayString(g.name), 9, ["value"]))
        }), 128))], 40, ["onUpdate:modelValue", "onChange", "disabled"]), [[_vModelSelect, selected]])]),
        _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((query) = $event),
          placeholder: "Найти пользователя"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, query]]),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("button", {
          class: "primary",
          disabled: !group?.can_write||!dirty||busy,
          onClick: save
        }, "Сохранить состав", 8, ["disabled", "onClick"])
      ]),
      _createElementVNode("p", { class: "notice" }, "Назначения хранятся в sthpw/login_in_group. Удаление существующих участников группы admin через этот экран запрещено."),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      message
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, _toDisplayString(message), 1))
        : _createCommentVNode("", true),
      group
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [_createElementVNode("p", null, [_createTextVNode(_toDisplayString(members.length) + " участников · " + _toDisplayString(group.users.length) + " пользователей загружено", 1), dirty
            ? (_openBlock(), _createElementBlock("span", { key: 0 }, " · Есть несохранённые изменения"))
            : _createCommentVNode("", true)]), _createElementVNode("div", { class: "member-grid" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(users, (u) => {
            return (_openBlock(), _createElementBlock("label", {
              key: u.login,
              class: "member-row"
            }, [_withDirectives(_createElementVNode("input", {
              type: "checkbox",
              "onUpdate:modelValue": $event => ((members) = $event),
              value: u.login,
              disabled: busy||!group.can_write||(group.group==='admin'&&group.members.includes(u.login))
            }, null, 8, ["onUpdate:modelValue", "value", "disabled"]), [[_vModelCheckbox, members]]), _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(u.name), 1), _createElementVNode("code", null, _toDisplayString(u.login), 1)])]))
          }), 128))]), (group.users.length>=group.limit)
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "notice"
              }, "Показан лимит " + _toDisplayString(group.limit) + " пользователей. Неотображаемые участники сохраняются.", 1))
            : _createCommentVNode("", true)], 64))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const SearchTypes = (function(){


const __component = {
 name:'SearchTypes',props:['project','target','screen','user','allowWrites'],emits:['open','changed','dirty'],
 data(){return {types:[],selected:'',detail:null,tab:'columns',adding:false,name:'',title:'',description:'',columns:[],pipeline:false,preview:false,busy:false,error:'',message:'',filter:'',metadata:{},newColumns:[],designer:null,designerField:null,seq:0,dependencies:null,dependencyField:'',stateReady:false,importDirty:false}},
 computed:{canCreate(){return this.allowWrites&&!['admin','sthpw','default'].includes(this.project)},visibleTypes(){const q=this.filter.toLowerCase();return this.types.filter(t=>(t.code+' '+t.name).toLowerCase().includes(q))},dirty(){return this.importDirty||this.adding||this.newColumns.length>0||!!this.detail&&JSON.stringify(this.metadata)!==JSON.stringify(this.detail.metadata)}},
 watch:{dirty(v){this.$emit('dirty',v)},selected(){this.storeState()},tab(){this.storeState()}},async mounted(){await this.load();try{const s=await uiState.load({...this.args(),scope:'stype-editor'});const code=this.screen?.search_type||s.value?.selected;if(code&&this.types.some(t=>t.code===code))await this.choose(code);if(s.value?.tab)this.tab=s.value.tab}catch(e){this.error=e.message}this.stateReady=true},beforeUnmount(){this.seq++},
 methods:{
 storeState(){if(this.stateReady)uiState.schedule({...this.args(),scope:'stype-editor'},{selected:this.selected,tab:this.tab})},
 args(){return {project:this.project,target:this.target}},
 async load(){this.error='';try{this.types=(await api.request('/stype-editor',this.args())).types||[]}catch(e){this.error=e.message}},
 async choose(code){if(this.dirty&&!confirm('Отменить несохранённые изменения SearchType?'))return;this.adding=false;this.importDirty=false;this.dependencies=null;this.newColumns=[];const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request('/stype-editor',{...this.args(),search_type:code});if(seq!==this.seq)return;this.selected=code;this.detail=d;this.metadata={...d.metadata}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 async create(){if(this.busy)return;this.busy=true;this.error='';this.message='';try{const r=await api.request('/search-types',{...this.args(),name:this.name,title:this.title,description:this.description,columns:this.columns,pipeline:this.pipeline,preview:this.preview},'POST');this.adding=false;this.name='';this.title='';this.description='';this.columns=[];await this.load();this.detail=null;await this.choose(r.search_type);this.message='Создан '+r.search_type+' исходной SearchTypeCreatorCmd';this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 async saveMetadata(){if(this.busy)return;this.busy=true;this.error='';try{await api.request('/stype-editor',{...this.args(),search_type:this.selected,revision:this.detail.revision,values:this.metadata},'PATCH');this.detail.metadata={...this.metadata};const code=this.selected;await this.load();await this.choose(code);this.message='Метаданные исходного SearchType сохранены';this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 async addColumns(){if(this.busy||!this.newColumns.length)return;if(!confirm('Добавить физические колонки в базу проекта? Убедитесь, что есть резервная копия. Удаление/откат здесь не выполняется.'))return;this.busy=true;this.error='';try{const r=await api.request('/stype-editor',{...this.args(),search_type:this.selected,revision:this.detail.revision,columns:this.newColumns,confirm:'ADD_COLUMNS'},'POST');this.newColumns=[];await this.choose(this.selected);this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 openDesigner(view,field=null){this.designerField=field;if(this.dirty||this.busy){this.error='Сначала сохраните или отмените метаданные и новые колонки';return}this.designer=view},
 async inspectDependencies(field=''){if(this.busy)return;this.busy=true;this.error='';try{this.dependencies=await api.request('/stype-dependencies',{...this.args(),search_type:this.selected,field});this.dependencyField=field;this.tab='references'}catch(e){this.error=e.message}finally{this.busy=false}},
 openTool(tool){if(this.dirty){this.error='Сначала сохраните или отмените черновик';return}this.$emit('open',{id:this.target+'/~admin/stype-tool:'+tool+':'+encodeURIComponent(this.selected)})},
 selectTab(tab){if(this.importDirty&&this.tab==='import'&&tab!=='import'&&!confirm('Отменить CSV-черновик?'))return;this.importDirty=false;this.tab=tab},
 openTable(){this.$emit('open',{id:this.target+'/~admin/stype-table:'+encodeURIComponent(this.selected)})},
 startCreate(){if(this.dirty&&!confirm('Отменить текущие правки?'))return;this.adding=true;this.detail=null;this.newColumns=[]},
 async definitionSaved(){this.designer=null;this.newColumns=[];this.detail=null;await this.choose(this.selected);this.$emit('changed')}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createElementVNode: _createElementVNode, vModelText: _vModelText, withDirectives: _withDirectives, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode, vModelSelect: _vModelSelect, vModelCheckbox: _vModelCheckbox, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_CsvImportPanel = _resolveComponent("CsvImportPanel")

    return (_openBlock(), _createElementBlock("section", {
      class: "stype-workbench",
      "aria-label": "Manage SearchTypes"
    }, [error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          role: "alert",
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), message
      ? (_openBlock(), _createElementBlock("p", {
          key: 1,
          class: "success"
        }, _toDisplayString(message), 1))
      : _createCommentVNode("", true), _createElementVNode("div", { class: "admin-two-pane" }, [_createElementVNode("aside", { class: "admin-catalog" }, [
      _createElementVNode("div", { class: "catalog-actions" }, [_createElementVNode("button", {
        disabled: !canCreate||busy,
        class: "primary",
        onClick: startCreate
      }, "Новый SearchType", 8, ["disabled", "onClick"])]),
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": $event => ((filter) = $event),
        type: "search",
        placeholder: "Найти SearchType…"
      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, filter]]),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(visibleTypes, (t) => {
        return (_openBlock(), _createElementBlock("button", {
          key: t.code,
          class: "admin-catalog-item",
          "aria-selected": selected===t.code&&!adding,
          onClick: $event => (choose(t.code))
        }, [_createElementVNode("b", null, _toDisplayString(t.name), 1), _createElementVNode("code", null, _toDisplayString(t.code), 1), (!t.can_write)
          ? (_openBlock(), _createElementBlock("small", { key: 0 }, "Общий / только чтение"))
          : _createCommentVNode("", true)], 8, ["aria-selected", "onClick"]))
      }), 128)),
      (!types.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "muted"
          }, "Нет проектных типов. Выберите рабочий проект."))
        : _createCommentVNode("", true)
    ]), _createElementVNode("main", { class: "admin-editor-pane" }, [adding
      ? (_openBlock(), _createElementBlock("form", {
          key: 0,
          class: "type-create",
          onSubmit: _withModifiers(create, ["prevent"])
        }, [
          _createElementVNode("h3", null, "Новый SearchType / " + _toDisplayString(project), 1),
          _createElementVNode("div", { class: "field-grid" }, [_createElementVNode("label", null, [_createTextVNode("Системное имя"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((name) = $event),
            pattern: "[a-z][a-z0-9_]{0,49}",
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, name]])]), _createElementVNode("label", null, [_createTextVNode("Название"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((title) = $event),
            maxlength: "200",
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, title]])])]),
          _createElementVNode("label", null, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
            "onUpdate:modelValue": $event => ((description) = $event),
            rows: "2"
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, description]])]),
          _createElementVNode("h4", null, "Дополнительные поля"),
          _createElementVNode("p", { class: "muted" }, "Стандартные id, code, name, description и служебные поля создаются TACTIC."),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(columns, (c, i) => {
            return (_openBlock(), _createElementBlock("div", {
              key: i,
              class: "column-row"
            }, [_withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((c.name) = $event),
              pattern: "[a-z][a-z0-9_]{0,49}",
              placeholder: "Имя поля",
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, c.name]]), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((c.type) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['varchar','text','integer','float','boolean','timestamp','date','json'], (t) => {
              return (_openBlock(), _createElementBlock("option", {
                key: t,
                value: t
              }, _toDisplayString(t), 9, ["value"]))
            }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, c.type]]), _createElementVNode("button", {
              type: "button",
              onClick: $event => (columns.splice(i,1))
            }, "×", 8, ["onClick"])]))
          }), 128)),
          _createElementVNode("button", {
            type: "button",
            disabled: columns.length>=50,
            onClick: $event => (columns.push({name:'',type:'varchar'}))
          }, "Добавить поле", 8, ["disabled", "onClick"]),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((pipeline) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, pipeline]]), _createTextVNode(" Пайплайн")]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((preview) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, preview]]), _createTextVNode(" Превью")])]),
          _createElementVNode("p", { class: "notice" }, "Изменяет схему базы. Существующие таблицы не переиспользуются. При обрыве проверьте результат перед повтором."),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            class: "primary",
            disabled: busy
          }, "Создать через TACTIC", 8, ["disabled"]), _createElementVNode("button", {
            type: "button",
            onClick: $event => (adding=false)
          }, "Отменить", 8, ["onClick"])])
        ], 40, ["onSubmit"]))
      : detail
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
            _createElementVNode("header", { class: "toolbar" }, [
              _createElementVNode("code", null, _toDisplayString(selected), 1),
              _createElementVNode("span", { class: "spacer" }),
              _createElementVNode("button", {
                onClick: openTable,
                "aria-label": "Открыть таблицу"
              }, "Таблица", 8, ["onClick"]),
              _createElementVNode("button", { onClick: $event => (openTool('insert')) }, "Новая запись", 8, ["onClick"]),
              _createElementVNode("button", { onClick: $event => (openTool('workflow')) }, "Workflow", 8, ["onClick"]),
              _createElementVNode("button", { onClick: $event => (openTool('schema')) }, "Schema", 8, ["onClick"]),
              _createElementVNode("button", {
                disabled: dirty||busy,
                onClick: $event => (choose(selected))
              }, "Обновить", 8, ["disabled", "onClick"])
            ]),
            _createElementVNode("nav", { class: "admin-section-tabs" }, [
              _createElementVNode("button", {
                "aria-selected": tab==='columns',
                onClick: $event => (selectTab('columns'))
              }, "Колонки", 8, ["aria-selected", "onClick"]),
              _createElementVNode("button", {
                "aria-selected": tab==='metadata',
                onClick: $event => (selectTab('metadata'))
              }, "SearchType", 8, ["aria-selected", "onClick"]),
              _createElementVNode("button", {
                "aria-selected": tab==='views',
                onClick: $event => (selectTab('views'))
              }, "Представления", 8, ["aria-selected", "onClick"]),
              _createElementVNode("button", {
                "aria-selected": tab==='references',
                onClick: $event => {selectTab('references');inspectDependencies()}
              }, "Ссылки", 8, ["aria-selected", "onClick"]),
              _createElementVNode("button", {
                disabled: !detail.can_write,
                "aria-selected": tab==='import',
                onClick: $event => (selectTab('import'))
              }, "CSV-импорт", 8, ["disabled", "aria-selected", "onClick"])
            ]),
            (!detail.can_write)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "notice"
                }, "Системный или общий тип: изменение его физической схемы и регистрации здесь запрещено. Конфигурации текущего проекта доступны отдельно."))
              : _createCommentVNode("", true),
            (tab==='columns')
              ? (_openBlock(), _createElementBlock("section", { key: 1 }, [
                  _createElementVNode("p", { class: "muted" }, _toDisplayString(detail.notice), 1),
                  _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", { class: "schema-editor-table" }, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Колонка"), _createElementVNode("th", null, "Тип БД"), _createElementVNode("th", null, "Display / edit definition")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.columns, (c) => {
                    return (_openBlock(), _createElementBlock("tr", { key: c.name }, [_createElementVNode("td", null, [_createElementVNode("b", null, _toDisplayString(c.name), 1)]), _createElementVNode("td", null, [_createElementVNode("code", null, _toDisplayString(c.schema?.data_type||c.schema?.type||JSON.stringify(c.schema)), 1)]), _createElementVNode("td", null, [
                      _createElementVNode("small", null, _toDisplayString(c.definition.handler||'По умолчанию'), 1),
                      _createElementVNode("small", null, _toDisplayString(c.edit_definition.edit_handler||c.edit_definition.handler||'По умолчанию'), 1),
                      _createElementVNode("button", { onClick: $event => (openDesigner('definition',c.name)) }, "Определение", 8, ["onClick"]),
                      _createElementVNode("button", { onClick: $event => (inspectDependencies(c.name)) }, "Ссылки", 8, ["onClick"])
                    ])]))
                  }), 128))])])]),
                  _createElementVNode("div", { class: "toolbar" }, [
                    _createElementVNode("button", { onClick: $event => (openDesigner('definition')) }, "Определения display…", 8, ["onClick"]),
                    _createElementVNode("button", { onClick: $event => (openDesigner('edit_definition')) }, "Определения edit…", 8, ["onClick"]),
                    _createElementVNode("span", { class: "spacer" }),
                    _createElementVNode("button", {
                      disabled: !detail.can_write||newColumns.length>=30,
                      onClick: $event => (newColumns.push({name:'',data_type:'varchar',format:''}))
                    }, "Добавить физическую колонку", 8, ["disabled", "onClick"])
                  ]),
                  (newColumns.length)
                    ? (_openBlock(), _createElementBlock("form", {
                        key: 0,
                        class: "new-columns-form",
                        onSubmit: _withModifiers(addColumns, ["prevent"])
                      }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(newColumns, (c, i) => {
                        return (_openBlock(), _createElementBlock("div", {
                          key: i,
                          class: "column-row"
                        }, [
                          _withDirectives(_createElementVNode("input", {
                            "onUpdate:modelValue": $event => ((c.name) = $event),
                            pattern: "[a-z][a-z0-9_]{0,49}",
                            required: "",
                            placeholder: "Имя колонки"
                          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, c.name]]),
                          _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((c.data_type) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.column_types, (t) => {
                            return (_openBlock(), _createElementBlock("option", { key: t }, _toDisplayString(t), 1))
                          }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, c.data_type]]),
                          _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((c.format) = $event) }, [_createElementVNode("option", { value: "" }, "Без форматирования"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.formats.filter(Boolean), (f) => {
                            return (_openBlock(), _createElementBlock("option", { key: f }, _toDisplayString(f), 1))
                          }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, c.format]]),
                          _createElementVNode("button", {
                            type: "button",
                            onClick: $event => (newColumns.splice(i,1))
                          }, "×", 8, ["onClick"])
                        ]))
                      }), 128)), _createElementVNode("p", { class: "notice" }, "Выполнится ColumnEditCbk → ColumnAddCmd с записью definition/edit_definition. Состав таблицы задаётся отдельно её view."), _createElementVNode("button", {
                        class: "primary",
                        disabled: busy
                      }, "Создать " + _toDisplayString(newColumns.length) + " колонок", 9, ["disabled"])], 40, ["onSubmit"]))
                    : _createCommentVNode("", true)
                ]))
              : (tab==='metadata')
                ? (_openBlock(), _createElementBlock("form", {
                    key: 2,
                    onSubmit: _withModifiers(saveMetadata, ["prevent"])
                  }, [
                    _createElementVNode("div", { class: "field-grid" }, [_createElementVNode("label", null, [_createTextVNode("Название"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((metadata.title) = $event),
                      readonly: !detail.can_write,
                      required: ""
                    }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, metadata.title]])]), _createElementVNode("label", null, [_createTextVNode("Цвет"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((metadata.color) = $event),
                      readonly: !detail.can_write,
                      placeholder: "#RRGGBB"
                    }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, metadata.color]])])]),
                    _createElementVNode("label", null, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": $event => ((metadata.description) = $event),
                      readonly: !detail.can_write,
                      rows: "4"
                    }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, metadata.description]])]),
                    _createElementVNode("dl", { class: "system-summary" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.registry, (v, k) => {
                      return (_openBlock(), _createElementBlock("div", {
                        key: k,
                        class: "system-fact"
                      }, [_createElementVNode("dt", null, _toDisplayString(k), 1), _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(v), 1)])]))
                    }), 128))]),
                    _createElementVNode("button", {
                      class: "primary",
                      disabled: busy||!detail.can_write||!dirty
                    }, "Сохранить метаданные", 8, ["disabled"])
                  ], 40, ["onSubmit"]))
                : (tab==='views')
                  ? (_openBlock(), _createElementBlock("div", { key: 3 }, [_createElementVNode("button", { onClick: $event => (openTool('views')) }, "Открыть Manage Views", 8, ["onClick"]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.views, (v) => {
                      return (_openBlock(), _createElementBlock("div", {
                        class: "admin-view-row",
                        key: v.name
                      }, [_createElementVNode("b", null, _toDisplayString(v.name), 1), _createElementVNode("span", null, _toDisplayString(v.elements.join(', ')||'Пустое представление'), 1), _createElementVNode("button", { onClick: $event => (openDesigner(v.name)) }, "Редактировать widget_config", 8, ["onClick"])]))
                    }), 128)), _createElementVNode("p", { class: "muted" }, "Порядок полей, display/edit/action и параметры остаются в исходных XML-конфигурациях.")]))
                  : (tab==='references')
                    ? (_openBlock(), _createElementBlock("section", { key: 4 }, [_createElementVNode("p", { class: "notice" }, "Статические кандидаты текущего проекта, не доказательство отсутствия динамических зависимостей. Удаление и изменение типа колонок этим экраном не выполняются."), _createElementVNode("button", {
                        disabled: busy,
                        onClick: $event => (inspectDependencies(dependencyField))
                      }, "Обновить ссылки " + _toDisplayString(dependencyField), 9, ["disabled", "onClick"]), dependencies
                        ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                            _createElementVNode("p", null, "Связи Schema: " + _toDisplayString(dependencies.related_types.join(', ')||'нет'), 1),
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dependencies.references, (r) => {
                              return (_openBlock(), _createElementBlock("div", {
                                class: "admin-view-row",
                                key: r.key
                              }, [_createElementVNode("code", null, _toDisplayString(r.kind), 1), _createElementVNode("span", null, _toDisplayString(r.name), 1), _createElementVNode("small", null, _toDisplayString(r.views.join(', ')), 1)]))
                            }), 128)),
                            (!dependencies.references.length)
                              ? (_openBlock(), _createElementBlock("p", { key: 0 }, "В проверенных записях совпадений нет."))
                              : _createCommentVNode("", true),
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dependencies.errors, (e) => {
                              return (_openBlock(), _createElementBlock("p", {
                                key: e.key,
                                class: "notice"
                              }, _toDisplayString(e.key) + ": " + _toDisplayString(e.reason), 1))
                            }), 128))
                          ], 64))
                        : _createCommentVNode("", true)]))
                    : (tab==='import')
                      ? (_openBlock(), _createBlock(_component_CsvImportPanel, {
                          key: selected,
                          project: project,
                          target: target,
                          "search-type": selected,
                          onDirty: $event => (importDirty=$event),
                          onSaved: $event => ($emit('changed'))
                        }, null, 8, ["project", "target", "search-type", "onDirty", "onSaved"]))
                      : _createCommentVNode("", true)
          ], 64))
        : _createCommentVNode("", true)])])]))
  }
};
return __component;
})();
const ViewDesigner = (function(){

const __component = {
 name:'ViewDesigner',props:{project:String,searchType:String,initialView:String,initialElement:String,login:String},emits:['close','saved'],
 data(){return {currentLogin:'',view:this.initialView||'table',record:null,elements:[],selected:-1,operations:[],error:'',busy:false,scope:'personal',newName:'',props:{},displayOptions:'{}',editOptions:'{}',showLayers:false}},
 computed:{chosen(){return this.elements[this.selected]},dirty(){return this.operations.length>0},available(){return Object.keys(this.record?.columns||{}).filter(n=>!this.elements.some(e=>e.name===n))}},
 async mounted(){if(!this.login){try{this.currentLogin=(await api.request('/session')).user.login}catch(e){this.error=e.message;return}}await this.load()},
 methods:{
 async load(){if(this.dirty&&!confirm('Отменить правки представления?')){this.view=this.record?.view||this.initialView;return;}this.error='';this.busy=true;try{this.record=await api.request('/view-config',{project:this.project,search_type:this.searchType,view:this.view});this.elements=JSON.parse(JSON.stringify(this.record.elements));this.operations=[];this.selected=-1;if(this.initialElement){const i=this.elements.findIndex(e=>e.name===this.initialElement);if(i>=0)this.choose(i)}}catch(e){this.error=e.message}finally{this.busy=false}},
 choose(i){this.selected=i;const e=this.elements[i];this.props={title:e.title,width:e.attributes.width||'',edit:e.attributes.edit||'',is_visible:e.attributes.is_visible||'',handler:e.handler,edit_handler:e.edit_handler};this.displayOptions='{}';this.editOptions='{}'},
 move(i,d){const j=i+d;if(j<0||j>=this.elements.length)return;const order=this.elements.map((_,n)=>n);[order[i],order[j]]=[order[j],order[i]];this.operations.push({op:'reorder',order});[this.elements[i],this.elements[j]]=[this.elements[j],this.elements[i]];this.choose(j)},
 add(){const name=this.newName.trim();if(!name||this.elements.some(e=>e.name===name))return;this.operations.push({op:'add',name});this.elements.push({name,title:name,attributes:{},handler:'',edit_handler:'',options:{},edit_options:{},sources:[]});this.choose(this.elements.length-1);this.newName=''},
 remove(){if(this.selected<0)return;this.operations.push({op:'remove',index:this.selected});this.elements.splice(this.selected,1);this.selected=-1},
 apply(){this.error='';try{const display=JSON.parse(this.displayOptions),edit=JSON.parse(this.editOptions);for(const o of [display,edit])if(!o||typeof o!=='object'||Array.isArray(o))throw Error('Изменения options должны быть JSON-объектом');const e=this.chosen,attrs={};for(const k of ['title','width','edit','is_visible'])if(String(this.props[k])!==String(k==='title'?e.title:e.attributes[k]||''))attrs[k]=this.props[k]||null;const op={op:'update',index:this.selected,attributes:attrs};if(this.props.handler!==e.handler||Object.keys(display).length)op.display={...(this.props.handler!==e.handler?{class:this.props.handler||null,widget:null}:{}),options:display};if(this.props.edit_handler!==e.edit_handler||Object.keys(edit).length)op.edit={...(this.props.edit_handler!==e.edit_handler?{class:this.props.edit_handler||null,widget:null}:{}),options:edit};this.operations.push(op);Object.assign(e.attributes,attrs);e.title=this.props.title||e.name;e.handler=this.props.handler;e.edit_handler=this.props.edit_handler;Object.assign(e.options,display);Object.assign(e.edit_options,edit);this.displayOptions='{}';this.editOptions='{}'}catch(e){this.error=e.message}},
 async save(){this.busy=true;this.error='';try{await api.request('/view-config',{project:this.project,search_type:this.searchType,view:this.view,revision:this.record.revision,login:this.scope==='personal'?(this.login||this.currentLogin):null,operations:this.operations},'PATCH');this.operations=[];this.$emit('saved');await this.load()}catch(e){this.error=e.message}finally{this.busy=false}},
 close(){if(!this.dirty||confirm('Закрыть без сохранения правок?'))this.$emit('close')}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, createCommentVNode: _createCommentVNode, normalizeClass: _normalizeClass, vModelText: _vModelText, withModifiers: _withModifiers } = _Vue

    return (_openBlock(), _createElementBlock("div", { class: "modal-backdrop" }, [_createElementVNode("section", {
      class: "modal wide-modal",
      role: "dialog",
      "aria-modal": "true"
    }, [
      _createElementVNode("header", null, [_createElementVNode("div", null, [_createElementVNode("small", null, "config/widget_config · " + _toDisplayString(searchType), 1), _createElementVNode("h2", null, "Конструктор представления")]), _createElementVNode("button", {
        onClick: close,
        "aria-label": "Закрыть конструктор"
      }, "×", 8, ["onClick"])]),
      _createElementVNode("div", { class: "toolbar" }, [
        _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((view) = $event),
          onChange: load
        }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record?.views||[view], (v) => {
          return (_openBlock(), _createElementBlock("option", {
            key: v,
            value: v
          }, _toDisplayString(v), 9, ["value"]))
        }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, view]]),
        _createElementVNode("label", null, [_createTextVNode("Сохранить в"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((scope) = $event) }, [_createElementVNode("option", { value: "personal" }, "Личное переопределение"), _createElementVNode("option", { value: "global" }, "Общее переопределение")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, scope]])]),
        _createElementVNode("button", { onClick: $event => (showLayers=!showLayers) }, "Слои XML", 8, ["onClick"]),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("span", null, "Правок: " + _toDisplayString(operations.length), 1),
        _createElementVNode("button", {
          class: "primary",
          disabled: busy||!dirty||!record?.can_write,
          onClick: save
        }, "Сохранить widget_config", 8, ["disabled", "onClick"])
      ]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      _createElementVNode("p", { class: "notice" }, "Порядок и свойства записываются в штатный XML. Неназванные в правке параметры и другие views сохраняются."),
      _createElementVNode("div", { class: "designer-body" }, [_createElementVNode("aside", { class: "designer-list" }, [
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(elements, (e, i) => {
          return (_openBlock(), _createElementBlock("div", {
            key: i,
            class: _normalizeClass(["designer-row", {active:selected===i}])
          }, [_createElementVNode("button", { onClick: $event => (choose(i)) }, [_createTextVNode(_toDisplayString(e.title), 1), _createElementVNode("small", null, _toDisplayString(e.name), 1)], 8, ["onClick"]), _createElementVNode("button", {
            disabled: i===0,
            onClick: $event => (move(i,-1))
          }, "↑", 8, ["disabled", "onClick"]), _createElementVNode("button", {
            disabled: i===elements.length-1,
            onClick: $event => (move(i,1))
          }, "↓", 8, ["disabled", "onClick"])], 2))
        }), 128)),
        _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((newName) = $event) }, [_createElementVNode("option", { value: "" }, "Добавить поле…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(available, (n) => {
          return (_openBlock(), _createElementBlock("option", {
            key: n,
            value: n
          }, _toDisplayString(n), 9, ["value"]))
        }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, newName]]),
        _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((newName) = $event),
          placeholder: "Или имя custom element"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newName]]),
        _createElementVNode("button", {
          disabled: !newName||!record?.can_write,
          onClick: add
        }, "Добавить элемент", 8, ["disabled", "onClick"])
      ]), chosen
        ? (_openBlock(), _createElementBlock("form", {
            key: 0,
            class: "designer-properties",
            onSubmit: _withModifiers(apply, ["prevent"])
          }, [
            _createElementVNode("h3", null, _toDisplayString(chosen.name), 1),
            _createElementVNode("label", null, [_createTextVNode("Заголовок"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((props.title) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.title]])]),
            _createElementVNode("div", { class: "two-cols" }, [_createElementVNode("label", null, [_createTextVNode("Ширина"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((props.width) = $event),
              placeholder: "180px"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.width]])]), _createElementVNode("label", null, [_createTextVNode("Редактирование"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((props.edit) = $event) }, [_createElementVNode("option", { value: "" }, "Наследовать"), _createElementVNode("option", { value: "true" }, "Да"), _createElementVNode("option", { value: "false" }, "Нет")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, props.edit]])])]),
            _createElementVNode("label", null, [_createTextVNode("Видимость"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((props.is_visible) = $event) }, [_createElementVNode("option", { value: "" }, "Наследовать"), _createElementVNode("option", { value: "true" }, "Видимый"), _createElementVNode("option", { value: "false" }, "Скрытый")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, props.is_visible]])]),
            _createElementVNode("label", null, [_createTextVNode("Display handler"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((props.handler) = $event),
              spellcheck: "false"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.handler]])]),
            _createElementVNode("details", null, [_createElementVNode("summary", null, "Исходные display options"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(chosen.options,null,2)), 1)]),
            _createElementVNode("label", null, [_createTextVNode("Изменения display options"), _withDirectives(_createElementVNode("textarea", {
              "onUpdate:modelValue": $event => ((displayOptions) = $event),
              class: "code-input",
              rows: "5"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, displayOptions]])]),
            _createElementVNode("label", null, [_createTextVNode("Edit handler"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((props.edit_handler) = $event),
              spellcheck: "false"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, props.edit_handler]])]),
            _createElementVNode("details", null, [_createElementVNode("summary", null, "Исходные edit options"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(chosen.edit_options,null,2)), 1)]),
            _createElementVNode("label", null, [_createTextVNode("Изменения edit options"), _withDirectives(_createElementVNode("textarea", {
              "onUpdate:modelValue": $event => ((editOptions) = $event),
              class: "code-input",
              rows: "4"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editOptions]])]),
            _createElementVNode("small", null, "JSON: строка задаёт параметр, null удаляет его переопределение. Вложенный XML редактируется в XML-режиме."),
            _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
              class: "primary",
              disabled: !record?.can_write
            }, "Применить свойства", 8, ["disabled"]), _createElementVNode("button", {
              type: "button",
              class: "danger",
              disabled: !record?.can_write,
              onClick: remove
            }, "Убрать из view", 8, ["disabled", "onClick"])]),
            _createElementVNode("details", null, [_createElementVNode("summary", null, "Источники определения"), _createElementVNode("pre", null, _toDisplayString(chosen.sources.join('\n')), 1)])
          ], 40, ["onSubmit"]))
        : (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "muted"
          }, "Выберите элемент представления."))]),
      showLayers
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "layer-stack"
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record?.layers, (layer, i) => {
            return (_openBlock(), _createElementBlock("details", { key: i }, [_createElementVNode("summary", null, _toDisplayString(i+1) + " · " + _toDisplayString(layer.origin) + " · " + _toDisplayString(layer.view), 1), _createElementVNode("pre", null, _toDisplayString(layer.xml), 1)]))
          }), 128))]))
        : _createCommentVNode("", true)
    ])]))
  }
};
return __component;
})();
const TaskTimeline = (function(){


const __component = {
 name:'TaskTimeline',props:{project:String,target:String,query:Object,spec:Object,refreshKey:Number},emits:['inspect','edit','dates'],
 data(){const today=new Date().toISOString().slice(0,10);const end=new Date(Date.parse(today+'T00:00:00Z')+30*86400000).toISOString().slice(0,10);return {stateReady:false,stateWritable:false,mode:'gantt',startField:'',endField:'',month:today.slice(0,7),start:today,end,zoom:28,drag:null,rows:[],nextOffset:0,total:0,hasMore:false,busy:false,error:'',sequence:0,includeUndated:false,loadedWindow:null,notice:'',bars:[]}},
 computed:{dateFields(){return this.spec.fields.filter(f=>f.storage&&!f.hidden&&['date','datetime'].includes(f.kind))},configuredBars(){return this.spec.fields.filter(f=>!f.hidden&&f.renderer==='gantt').flatMap(f=>f.bars||[])},
  items(){return this.rows.map(row=>({row,bars:(row.timeline||[]).map(b=>({...b,start:this.day(b.start),end:this.day(b.end)}))}))},
  range(){const w=this.loadedWindow||this.requestWindow();const today=this.day(new Date().toISOString());return {start:this.day(w.start)??today,end:this.day(w.end)??today}} ,
  ticks(){return Array.from({length:Math.max(1,Math.min(366,this.range.end-this.range.start+1))},(_,i)=>this.range.start+i)},
  calendarDays(){const source=/^\d{4}-(0[1-9]|1[0-2])$/.test(this.month)?this.month:new Date().toISOString().slice(0,7);const [year,month]=source.split('-').map(Number),first=new Date(Date.UTC(year,month-1,1)),offset=(first.getUTCDay()+6)%7;const day=Math.floor(first.getTime()/86400000)-offset;return Array.from({length:42},(_,i)=>day+i)}},
 watch:{zoom(){this.saveState()},query:{deep:true,handler(){this.load()}},refreshKey(){this.load()}},
 mounted(){this.restoreState()},beforeUnmount(){this.sequence++},
 methods:{
 async restoreState(){this.stateReady=false;if(!this.configuredBars.length&&this.dateFields.length){this.startField=this.dateFields[0].name;this.endField=(this.dateFields[1]||this.dateFields[0]).name}try{const r=await uiState.load({project:this.project,target:this.target,scope:'timeline'});if(r.value)Object.assign(this,r.value);this.stateWritable=r.can_write;await this.$nextTick();this.stateReady=true}catch(e){this.error=e.message}await this.load()},
 saveState(){if(!this.stateReady||!this.stateWritable)return;uiState.schedule({project:this.project,target:this.target,scope:'timeline'},{mode:this.mode,start:this.start,end:this.end,month:this.month,zoom:this.zoom,startField:this.startField,endField:this.endField,includeUndated:this.includeUndated})},
  day(value){if(!value)return null;const ms=Date.parse(String(value).slice(0,10)+'T00:00:00Z');return Number.isFinite(ms)?Math.floor(ms/86400000):null},
  iso(day){return new Date(day*86400000).toISOString().slice(0,10)},label(day){return this.iso(day).slice(5,10)},title(row){return row.values.name||row.values.description||row.values.code||row.key},
  requestWindow(){if(this.mode==='calendar'){const days=this.calendarDays;return {start:this.iso(days[0]),end:this.iso(days[41])}}return {start:this.start,end:this.end}},
  async load(more=false){if(more&&(this.busy||!this.hasMore||this.rows.length>=2000))return;const seq=++this.sequence;this.busy=true;this.error='';const offset=more?this.nextOffset:0;const window=this.requestWindow();if(!more){this.rows=[];this.total=0;this.hasMore=false;this.loadedWindow=null}
   try{const result=await api.request('/timeline',{...this.query,project:this.project,target:this.target,...window,start_field:this.startField||undefined,end_field:this.endField||undefined,include_undated:this.includeUndated,offset,limit:200},'POST');if(seq!==this.sequence)return;
    // A mutable database is not a snapshot: deduplicate keys, keep the explicit
    // server offset separately so concurrent inserts cannot cause fetch loops.
    this.rows=more?[...this.rows,...result.items.filter(r=>!this.rows.some(x=>x.key===r.key))]:result.items;this.nextOffset=result.offset+result.items.length;this.total=result.total;this.hasMore=result.has_more;this.loadedWindow=result.window;this.notice=result.notice;this.bars=result.bars;this.saveState()
   }catch(e){if(seq===this.sequence)this.error=e.message}finally{if(seq===this.sequence)this.busy=false}},
  switchMode(mode){this.mode=mode;this.load()},
  shift(sign){if(this.mode==='calendar'){const d=new Date(this.month+'-01T00:00:00Z');d.setUTCMonth(d.getUTCMonth()+sign);this.month=d.toISOString().slice(0,7)}else{const n=(this.day(this.end)-this.day(this.start)+1)||31;this.start=this.iso(this.day(this.start)+sign*n);this.end=this.iso(this.day(this.end)+sign*n)}this.load()},
  bar(b,index){if(b.start===null)return {};const end=b.end===null?b.start:b.end;const a=Math.max(this.range.start,b.start),z=Math.min(this.range.end,Math.max(b.start,end));return {left:(a-this.range.start)*this.zoom+'px',width:Math.max(10,(z-a+1)*this.zoom-3)+'px',top:(index*26+4)+'px',height:'22px',...(b.color?{backgroundColor:b.color}:{})}},
  visibleBar(b){return b.start!==null&&(b.end===null||b.end>=b.start)&&b.start<=this.range.end&&(b.end??b.start)>=this.range.start},
  onDay(day){return this.items.flatMap(i=>i.bars.filter(b=>b.start!==null&&b.start<=day&&(b.end??b.start)>=day).map(b=>({row:i.row,bar:b})))},
  down(e,row,b){if(this.busy||b.start===null||b.end===null||!this.spec.capabilities?.update)return;this.drag={row,bar:b,x:e.clientX};e.currentTarget.setPointerCapture(e.pointerId)},
  up(e){if(!this.drag)return;const d=this.drag;this.drag=null;const delta=Math.round((e.clientX-d.x)/this.zoom);if(delta&&confirm('Перенести интервал «'+d.bar.label+'» на '+delta+' дней? Даты и ревизия будут проверены исходной формой TACTIC.'))this.$emit('dates',{row:d.row,startField:d.bar.start_field,endField:d.bar.end_field,delta})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { normalizeClass: _normalizeClass, createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, vModelText: _vModelText, createCommentVNode: _createCommentVNode, vModelCheckbox: _vModelCheckbox, normalizeStyle: _normalizeStyle } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "timeline" }, [
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("button", {
          class: _normalizeClass({primary:mode==='gantt'}),
          onClick: $event => (switchMode('gantt'))
        }, "Gantt", 10, ["onClick"]),
        _createElementVNode("button", {
          class: _normalizeClass({primary:mode==='calendar'}),
          onClick: $event => (switchMode('calendar'))
        }, "Календарь", 10, ["onClick"]),
        _createElementVNode("label", null, [_createTextVNode("Начало"), _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((startField) = $event),
          onChange: $event => (load())
        }, [_createElementVNode("option", { value: "" }, "Из Gantt widget_config"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dateFields, (f) => {
          return (_openBlock(), _createElementBlock("option", {
            key: f.name,
            value: f.name
          }, _toDisplayString(f.label), 9, ["value"]))
        }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, startField]])]),
        _createElementVNode("label", null, [_createTextVNode("Конец"), _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((endField) = $event),
          onChange: $event => (load())
        }, [_createElementVNode("option", { value: "" }, "Из Gantt widget_config"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dateFields, (f) => {
          return (_openBlock(), _createElementBlock("option", {
            key: f.name,
            value: f.name
          }, _toDisplayString(f.label), 9, ["value"]))
        }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, endField]])]),
        (mode==='calendar')
          ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_createTextVNode("Месяц"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((month) = $event),
              type: "month",
              onChange: $event => (load())
            }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, month]])]))
          : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("label", null, [_createTextVNode("Период с"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((start) = $event),
              type: "date",
              onChange: $event => (load())
            }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, start]])]), _createElementVNode("label", null, [_createTextVNode("по"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((end) = $event),
              type: "date",
              onChange: $event => (load())
            }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, end]])]), _createElementVNode("label", null, [_createTextVNode("Масштаб"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((zoom) = $event),
              type: "range",
              min: "10",
              max: "70"
            }, null, 8, ["onUpdate:modelValue"]), [[
              _vModelText,
              zoom,
              void 0,
              { number: true }
            ]])])], 64))
      ]),
      _createElementVNode("div", { class: "toolbar" }, [
        _createElementVNode("button", {
          disabled: busy,
          onClick: $event => (shift(-1))
        }, "← Период", 8, ["disabled", "onClick"]),
        _createElementVNode("button", {
          disabled: busy,
          onClick: $event => (shift(1))
        }, "Период →", 8, ["disabled", "onClick"]),
        _createElementVNode("button", {
          disabled: busy,
          onClick: $event => (load())
        }, "Обновить период", 8, ["disabled", "onClick"]),
        _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((includeUndated) = $event),
          type: "checkbox",
          onChange: $event => (load())
        }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelCheckbox, includeUndated]]), _createTextVNode("Также без даты начала")]),
        _createElementVNode("span", { class: "timeline-count" }, _toDisplayString(busy?'Загрузка…':('Загружено '+rows.length+' из '+total+' объектов периода')), 1)
      ]),
      _createElementVNode("p", { class: "notice" }, "Отдельная серверная выборка периода с фильтрами исходного view — не текущая страница таблицы. До 366 дней, 8 интервалов на объект. Перенос сохраняется через исходную форму. Зависимости, автоматическое планирование и ресурсный расчёт не реализованы."),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (mode==='gantt')
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "gantt-scroll"
          }, [_createElementVNode("div", {
            class: "gantt-sheet",
            style: _normalizeStyle({width:(240+ticks.length*zoom)+'px'})
          }, [_createElementVNode("div", { class: "gantt-header" }, [_createElementVNode("span", null, "Объект / интервалы из конфигурации"), _createElementVNode("div", { class: "gantt-axis" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(ticks, (d) => {
            return (_openBlock(), _createElementBlock("small", {
              key: d,
              style: _normalizeStyle({width:zoom+'px'})
            }, _toDisplayString(label(d)), 5))
          }), 128))])]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items, (item) => {
            return (_openBlock(), _createElementBlock("div", {
              key: item.row.key,
              class: "gantt-row",
              style: _normalizeStyle({height:Math.max(34,item.bars.length*26+8)+'px'})
            }, [_createElementVNode("button", { onClick: $event => ($emit('inspect',item.row)) }, _toDisplayString(title(item.row)), 9, ["onClick"]), _createElementVNode("div", {
              class: "gantt-track",
              style: _normalizeStyle({backgroundSize:zoom+'px 100%',height:'100%'})
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(item.bars, (b, index) => {
              return (_openBlock(), _createElementBlock(_Fragment, { key: b.id }, [(visibleBar(b))
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    class: "gantt-bar",
                    style: _normalizeStyle(bar(b,index)),
                    title: b.label+': '+iso(b.start)+' → '+iso(b.end??b.start),
                    onDblclick: $event => ($emit('edit',item.row)),
                    onPointerdown: $event => (down($event,item.row,b)),
                    onPointerup: up,
                    onPointercancel: $event => (drag=null)
                  }, _toDisplayString(b.label), 45, ["title", "onDblclick", "onPointerdown", "onPointerup", "onPointercancel"]))
                : (b.start===null)
                  ? (_openBlock(), _createElementBlock("span", {
                      key: 1,
                      class: "muted"
                    }, _toDisplayString(b.label) + ": нет даты начала ", 1))
                  : (b.end!==null&&b.end<b.start)
                    ? (_openBlock(), _createElementBlock("span", {
                        key: 2,
                        class: "error"
                      }, _toDisplayString(b.label) + ": конец раньше начала ", 1))
                    : _createCommentVNode("", true)], 64))
            }), 128))], 4)], 4))
          }), 128))], 4)]))
        : (_openBlock(), _createElementBlock("div", {
            key: 2,
            class: "calendar-grid"
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['Пн','Вт','Ср','Чт','Пт','Сб','Вс'], (d) => {
            return (_openBlock(), _createElementBlock("b", { key: d }, _toDisplayString(d), 1))
          }), 128)), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(calendarDays, (day) => {
            return (_openBlock(), _createElementBlock("div", {
              key: day,
              class: "calendar-day"
            }, [_createElementVNode("small", null, _toDisplayString(label(day)), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(onDay(day), (item) => {
              return (_openBlock(), _createElementBlock("button", {
                key: item.row.key+':'+item.bar.id,
                onClick: $event => ($emit('inspect',item.row)),
                title: item.bar.label
              }, _toDisplayString(title(item.row)) + " · " + _toDisplayString(item.bar.label), 9, ["onClick", "title"]))
            }), 128))]))
          }), 128))])),
      _createElementVNode("div", { class: "toolbar" }, [(hasMore&&rows.length<2000)
        ? (_openBlock(), _createElementBlock("button", {
            key: 0,
            disabled: busy,
            onClick: $event => (load(true))
          }, "Загрузить ещё 200 объектов", 8, ["disabled", "onClick"]))
        : _createCommentVNode("", true), (hasMore&&rows.length>=2000)
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, "Показаны первые 2000 объектов. Сузьте период или фильтры; это не полный результат."))
        : _createCommentVNode("", true), (!busy&&!error&&!rows.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "В этом периоде нет записей по текущему запросу."))
        : _createCommentVNode("", true)])
    ]))
  }
};
return __component;
})();
const ScriptEditor = (function(){

const __component = {
 name:'ScriptEditor',props:{project:String,target:String},emits:['dirty','open'],
 data(){return {items:[],total:0,offset:0,limit:40,q:'',folderFilter:null,busy:false,saving:false,error:'',notice:'',canWrite:false,languages:[],manageTarget:'',record:null,draft:{folder:'default',title:'',language:'javascript',description:'',script:''},baseline:'',check:null,requestSeq:0,loadSeq:0,cursor:{line:1,column:1},wrap:false,findText:'',canExecute:false,running:false,runUncertain:false,runResult:null,parameters:'{}',diff:null}},
 computed:{dirty(){return !!this.baseline&&JSON.stringify(this.draft)!==this.baseline},groups(){const groups=[];for(const row of this.items){let g=groups.find(g=>g.folder===row.values.folder);if(!g){g={folder:row.values.folder,items:[]};groups.push(g)}g.items.push(row)}return groups},lineCount(){return this.draft.script.split('\n').length}},
 watch:{dirty(value){this.$emit('dirty',value||this.running)},running(value){this.$emit('dirty',value||this.dirty)},'draft.script'(){this.check=null}},
 async mounted(){this.baseline=JSON.stringify(this.draft);window.addEventListener('beforeunload',this.unload);await this.reload(true)},
 beforeUnmount(){this.requestSeq++;this.loadSeq++;window.removeEventListener('beforeunload',this.unload);this.$emit('dirty',false)},
 methods:{
 unload(event){if(this.dirty){event.preventDefault();event.returnValue=''}},
 accept(record){this.record=record;this.draft={folder:record.values.folder??'',title:record.values.title??'',language:record.values.language||'javascript',description:record.values.description??'',script:record.values.script??''};this.baseline=JSON.stringify(this.draft);this.check=null;this.diff=null;this.runResult=null;this.runUncertain=false;this.cursor={line:1,column:1}},
 async reload(initial=false){const seq=++this.requestSeq;this.busy=true;this.error='';try{const result=await api.request('/scripts',{project:this.project,target:this.target,q:this.q,folder:this.folderFilter,offset:this.offset,limit:this.limit});if(seq!==this.requestSeq)return;this.items=result.items;this.total=result.total;this.canWrite=result.can_write;this.canExecute=result.can_execute;this.languages=result.languages;this.manageTarget=result.manage_target;if(initial&&(result.initial?.search_key||result.initial?.script_path))await this.load({key:result.initial.search_key,script_path:result.initial.script_path})}catch(e){if(seq===this.requestSeq)this.error=e.message}finally{if(seq===this.requestSeq)this.busy=false}},
 async load(selection){if(this.running)return;if(this.dirty&&!confirm('Отменить несохранённые правки скрипта?'))return;const seq=++this.loadSeq;this.error='';this.notice='';this.busy=true;try{const result=await api.request('/script',{project:this.project,target:this.target,...selection});if(seq===this.loadSeq)this.accept(result.record)}catch(e){if(seq===this.loadSeq)this.error=e.message}finally{if(seq===this.loadSeq)this.busy=false}},
 fresh(){if(this.running)return;if(this.dirty&&!confirm('Отменить несохранённые правки?'))return;this.loadSeq++;this.record=null;this.draft={folder:this.folderFilter||'default',title:'',language:'javascript',description:'',script:''};this.baseline=JSON.stringify(this.draft);this.error='';this.notice='';this.check=null;this.runUncertain=false;this.runResult=null;this.diff=null},
 copy(){if(this.running)return;this.runUncertain=false;this.runResult=null;this.diff=null;this.loadSeq++;this.record=null;this.baseline='new-copy';this.draft.title=this.draft.title+'_copy';this.notice='Копия ещё не сохранена. Исходная запись не изменяется.'},
 async save(){if(this.saving||this.busy||this.running||!this.canWrite)return;this.saving=true;this.error='';this.notice='';try{const result=await api.request('/script',{project:this.project,target:this.target,key:this.record?.key,revision:this.record?.revision,values:{...this.draft}},this.record?'PATCH':'POST');this.accept(result.record);this.notice=result.notice;await this.reload()}catch(e){this.error=e.message}finally{this.saving=false}},
 async syntax(){this.error='';const source=this.draft.script,language=this.draft.language;try{const result=await api.request('/script-check',{project:this.project,target:this.target,script:source,language},'POST');if(source===this.draft.script&&language===this.draft.language)this.check=result}catch(e){this.error=e.message}},
 async discard(){if(this.record)await this.load({key:this.record.key});else this.fresh()},
 filter(folder=null){this.folderFilter=folder;this.offset=0;this.reload()},
 search(){this.offset=0;this.reload()},
 page(delta){this.offset+=delta*this.limit;this.reload()},
 position(){const el=this.$refs.source;if(!el)return;const before=el.value.slice(0,el.selectionStart);const lines=before.split('\n');this.cursor={line:lines.length,column:lines[lines.length-1].length+1}},
 keydown(event){if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();this.save()}else if(event.key==='Tab'){event.preventDefault();const el=event.target,start=el.selectionStart,end=el.selectionEnd;this.draft.script=el.value.slice(0,start)+'    '+el.value.slice(end);this.$nextTick(()=>{el.selectionStart=el.selectionEnd=start+4;this.position()})}},
 find(){this.$refs.code?.find(this.findText)},
 async showDiff(){if(!this.record)return;this.error='';try{const r=await api.request('/script-diff',{project:this.project,target:this.target,key:this.record.key,revision:this.record.revision,script:this.draft.script},'POST');this.diff=r.diff||'(Нет изменений кода)'}catch(e){this.error=e.message}},
 async runSaved(){if(!this.record||this.dirty||this.running||this.runUncertain||!this.canExecute)return;if(!confirm('Выполнить сохранённый Python с правами сервера? Код может изменять БД и файлы. Это НЕ песочница.'))return;let input;try{input=JSON.parse(this.parameters);if(!input||typeof input!=='object'||Array.isArray(input))throw Error('input должен быть JSON-объектом')}catch(e){this.error=e.message;return}this.running=true;this.runResult=null;this.error='';try{api.action?.('script.run',{project:this.project,target:this.target});const r=await api.request('/script-run',{project:this.project,target:this.target,key:this.record.key,revision:this.record.revision,confirm:'RUN_SAVED_SCRIPT',parameters:input},'POST');this.runResult=r;this.runUncertain=false}catch(e){this.error=e.message;this.runUncertain=true}finally{this.running=false}},
 download(){const ext={python:'.py',javascript:'.js',server_js:'.js',xml:'.xml',expression:'.txt'}[this.draft.language]||'.txt';const blob=new Blob([this.draft.script],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=(this.draft.title||'untitled').replace(/[\\/:*?"<>|]/g,'_')+ext;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, vModelText: _vModelText, withDirectives: _withDirectives, withModifiers: _withModifiers, renderList: _renderList, Fragment: _Fragment, normalizeClass: _normalizeClass, createTextVNode: _createTextVNode, vModelSelect: _vModelSelect, withKeys: _withKeys, vModelCheckbox: _vModelCheckbox, resolveComponent: _resolveComponent, createVNode: _createVNode } = _Vue

    const _component_CodeEditor = _resolveComponent("CodeEditor")

    return (_openBlock(), _createElementBlock("section", {
      class: "script-editor",
      "data-testid": "script-editor",
      "aria-label": "Script Editor"
    }, [
      _createElementVNode("header", {
        class: "script-toolbar widget-toolbar",
        role: "group",
        "aria-label": "Действия со скриптами"
      }, [
        dirty
          ? (_openBlock(), _createElementBlock("span", {
              key: 0,
              class: "editor-status",
              role: "status"
            }, "● Несохранённые изменения"))
          : _createCommentVNode("", true),
        _createElementVNode("button", {
          onClick: fresh,
          disabled: saving||busy||running
        }, "Новый", 8, ["onClick", "disabled"]),
        _createElementVNode("button", {
          onClick: copy,
          disabled: !record||saving||busy
        }, "Создать копию", 8, ["onClick", "disabled"]),
        _createElementVNode("button", { onClick: download }, "В файл", 8, ["onClick"]),
        _createElementVNode("button", {
          onClick: $event => ($emit('open',{id:manageTarget})),
          disabled: !manageTarget
        }, "Таблица по конфигурации", 8, ["onClick", "disabled"])
      ]),
      _createElementVNode("p", { class: "notice" }, "Сохранение использует исходные insert/update TACTIC. Код не запускается в браузере; его могут использовать существующие workflow и триггеры. Запуск сохранённого Python требует отдельного разрешения сервера. Это не песочница; отладчик не перенесён."),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice",
            role: "status"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "script-layout" }, [_createElementVNode("aside", { class: "script-directory" }, [
        _createElementVNode("form", { onSubmit: _withModifiers(search, ["prevent"]) }, [_withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((q) = $event),
          "aria-label": "Поиск скриптов",
          placeholder: "Папка или название"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, q]]), _createElementVNode("button", { disabled: busy }, "Найти", 8, ["disabled"])], 40, ["onSubmit"]),
        _createElementVNode("div", { class: "script-folder-filter" }, [(folderFilter!==null)
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              onClick: $event => (filter(null))
            }, "Все папки ×", 8, ["onClick"]))
          : (_openBlock(), _createElementBlock("span", { key: 1 }, "Все папки · " + _toDisplayString(total) + " записей", 1))]),
        (!items.length&&!busy)
          ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Скрипты не найдены."))
          : _createCommentVNode("", true),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (group) => {
          return (_openBlock(), _createElementBlock("section", { key: String(group.folder) }, [_createElementVNode("button", {
            class: "script-folder",
            onClick: $event => (filter(group.folder??''))
          }, _toDisplayString(group.folder||'(без папки)'), 9, ["onClick"]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.items, (item) => {
            return (_openBlock(), _createElementBlock("button", {
              key: item.key,
              class: _normalizeClass(["script-entry", {active:item.key===record?.key}]),
              onClick: $event => (load({key:item.key}))
            }, [_createElementVNode("span", null, _toDisplayString(item.values.title), 1), _createElementVNode("small", null, _toDisplayString(item.values.language||'javascript'), 1)], 10, ["onClick"]))
          }), 128))]))
        }), 128)),
        _createElementVNode("footer", null, [_createElementVNode("button", {
          onClick: $event => (page(-1)),
          disabled: offset===0||busy
        }, "←", 8, ["onClick", "disabled"]), _createElementVNode("span", null, _toDisplayString(total?offset+1:0) + "–" + _toDisplayString(Math.min(offset+limit,total)) + " / " + _toDisplayString(total), 1), _createElementVNode("button", {
          onClick: $event => (page(1)),
          disabled: offset+limit>=total||busy
        }, "→", 8, ["onClick", "disabled"])])
      ]), _createElementVNode("div", {
        class: "script-document",
        "aria-busy": saving
      }, [
        _createElementVNode("div", { class: "script-fields" }, [_createElementVNode("label", null, [_createTextVNode("Папка"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((draft.folder) = $event),
          disabled: saving||busy||running,
          "aria-label": "Папка скрипта"
        }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, draft.folder]])]), _createElementVNode("label", null, [_createTextVNode("Название"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((draft.title) = $event),
          disabled: saving||busy||running,
          "aria-label": "Название скрипта"
        }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, draft.title]])]), _createElementVNode("label", null, [_createTextVNode("Язык"), _withDirectives(_createElementVNode("select", {
          "onUpdate:modelValue": $event => ((draft.language) = $event),
          disabled: saving||busy||running,
          "aria-label": "Язык скрипта"
        }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(languages, (l) => {
          return (_openBlock(), _createElementBlock("option", {
            key: l,
            value: l
          }, _toDisplayString(l), 9, ["value"]))
        }), 128)), (draft.language&&!languages.includes(draft.language))
          ? (_openBlock(), _createElementBlock("option", {
              key: 0,
              value: draft.language
            }, _toDisplayString(draft.language) + " (существующее значение)", 9, ["value"]))
          : _createCommentVNode("", true)], 8, ["onUpdate:modelValue", "disabled"]), [[_vModelSelect, draft.language]])])]),
        _createElementVNode("label", { class: "script-description" }, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((draft.description) = $event),
          disabled: saving||busy||running,
          "aria-label": "Описание скрипта"
        }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, draft.description]])]),
        _createElementVNode("div", { class: "script-source-tools" }, [
          _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((findText) = $event),
            "aria-label": "Найти в скрипте",
            placeholder: "Найти в тексте",
            onKeyup: _withKeys(find, ["enter"])
          }, null, 40, ["onUpdate:modelValue", "onKeyup"]), [[_vModelText, findText]]),
          _createElementVNode("button", { onClick: find }, "Следующее", 8, ["onClick"]),
          _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((wrap) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, wrap]]), _createTextVNode("Перенос строк")]),
          _createElementVNode("span", { class: "spacer" }),
          _createElementVNode("button", {
            onClick: showDiff,
            disabled: !record||saving||busy
          }, "Изменения", 8, ["onClick", "disabled"]),
          _createElementVNode("button", {
            onClick: syntax,
            disabled: saving||busy||running
          }, "Проверить синтаксис", 8, ["onClick", "disabled"])
        ]),
        _createVNode(_component_CodeEditor, {
          ref: "code",
          modelValue: draft.script,
          "onUpdate:modelValue": $event => ((draft.script) = $event),
          language: draft.language,
          readonly: saving||busy||running,
          wrap: wrap,
          label: "Код скрипта",
          onSave: save,
          onCursor: $event => (cursor=$event)
        }, null, 8, ["modelValue", "onUpdate:modelValue", "language", "readonly", "wrap", "onSave", "onCursor"]),
        _createElementVNode("div", { class: "script-status" }, [_createElementVNode("span", null, "Строка " + _toDisplayString(cursor.line) + ", столбец " + _toDisplayString(cursor.column) + " · " + _toDisplayString(lineCount) + " строк · " + _toDisplayString(draft.script.length) + " символов", 1), record
          ? (_openBlock(), _createElementBlock("code", { key: 0 }, _toDisplayString(record.values.code), 1))
          : _createCommentVNode("", true)]),
        check
          ? (_openBlock(), _createElementBlock("p", {
              key: 0,
              class: _normalizeClass(check.valid===false?'error':'notice')
            }, [_createTextVNode(_toDisplayString(check.checked?(check.valid?'Синтаксис корректен':'Ошибка синтаксиса'):'Проверка недоступна'), 1), (check.line)
              ? (_openBlock(), _createElementBlock("span", { key: 0 }, " · строка " + _toDisplayString(check.line) + ", столбец " + _toDisplayString(check.column), 1))
              : _createCommentVNode("", true), _createTextVNode(". " + _toDisplayString(check.message||check.notice) + " Код не выполнялся.", 1)], 2))
          : _createCommentVNode("", true),
        (diff!==null)
          ? (_openBlock(), _createElementBlock("details", {
              key: 1,
              open: ""
            }, [_createElementVNode("summary", null, "Diff: сохранённый код → черновик"), _createElementVNode("pre", { class: "script-diff" }, _toDisplayString(diff), 1)]))
          : _createCommentVNode("", true),
        _createElementVNode("details", { class: "script-run" }, [
          _createElementVNode("summary", null, "Запуск сохранённого Python " + _toDisplayString(canExecute?'':'(выключен на сервере)'), 1),
          _createElementVNode("p", { class: "notice" }, "Код выполняется оригинальным PythonCmd с правами сервера. Несохранённый текст не исполняется. Нет автоматического повтора после ошибки."),
          _createElementVNode("label", null, [_createTextVNode("input — JSON-параметры"), _withDirectives(_createElementVNode("textarea", {
            "onUpdate:modelValue": $event => ((parameters) = $event),
            rows: "3",
            disabled: running,
            spellcheck: "false"
          }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, parameters]])]),
          _createElementVNode("button", {
            class: "danger",
            disabled: !canExecute||!record||draft.language!=='python'||dirty||running||runUncertain,
            onClick: runSaved
          }, _toDisplayString(running?'Выполняется…':'Выполнить сохранённый Python'), 9, ["disabled", "onClick"]),
          runUncertain
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "error"
              }, "Результат может быть неопределён. Проверьте данные и журнал до повторного запуска."))
            : _createCommentVNode("", true),
          runResult
            ? (_openBlock(), _createElementBlock("pre", { key: 1 }, _toDisplayString(JSON.stringify(runResult,null,2)), 1))
            : _createCommentVNode("", true)
        ]),
        _createElementVNode("footer", { class: "script-actions" }, [
          _createElementVNode("button", {
            disabled: saving||busy||running||!dirty,
            onClick: discard
          }, "Отменить правки", 8, ["disabled", "onClick"]),
          _createElementVNode("span", { class: "spacer" }),
          (!canWrite)
            ? (_openBlock(), _createElementBlock("span", { key: 0 }, "Запись отключена на сервере"))
            : _createCommentVNode("", true),
          _createElementVNode("button", {
            class: "primary",
            disabled: saving||busy||running||!canWrite||!draft.title||(!dirty&&!!record),
            onClick: save
          }, _toDisplayString(saving?'Сохранение…':'Сохранить') + " · Ctrl+S", 9, ["disabled", "onClick"])
        ])
      ], 8, ["aria-busy"])])
    ]))
  }
};
return __component;
})();
const ProjectWizard = (function(){

const __component = {
 name:'ProjectWizard',props:{project:String,target:String},emits:['changed','dirty'],
 data(){return {step:0,busy:false,error:'',options:null,code:'',title:'',description:'',type:'default',review:null,result:null,jump:true,submitted:false}},
 async mounted(){try{this.options=await api.request('/project-create',{project:this.project,target:this.target})}catch(e){this.error=e.message}},
 computed:{summaryType(){return this.options?.types?.find(t=>t.code===this.type)?.title||this.type},validDetails(){return /^[a-z][a-z0-9_]{0,29}$/.test(this.code)&&this.title.trim().length>0&&this.title.length<=200}},
 watch:{code(){this.modified()},title(){this.modified()},description(){this.modified()},type(){this.modified()}},
 methods:{
  modified(){this.review=null;this.$emit('dirty',!this.result&&Boolean(this.code||this.title||this.description))},
  payload(){return {project:this.project,target:this.target,code:this.code,title:this.title,type:this.type,description:this.description}},
  async next(){if(this.busy)return;this.error='';if(this.step===0){if(!this.validDetails){this.error='Укажите название и код: до 30 строчных латинских букв, цифр или _, начиная с буквы.';return}this.step=1;return}
   this.busy=true;try{this.review=await api.request('/project-preflight',this.payload(),'POST');this.step=2}catch(e){this.error=e.message}finally{this.busy=false}},
  back(){if(this.busy||this.submitted)return;this.error='';this.step=Math.max(0,this.step-1);this.review=null},
  async create(){if(this.busy||!this.review||this.submitted)return;this.busy=true;this.error='';this.submitted=true;
   try{this.result=await api.request('/project-create',{...this.payload(),revision:this.review.revision},'POST');this.step=3;this.$emit('dirty',false);this.$emit('changed',{...this.result,open:this.jump})}
   catch(e){this.error=e.message;if(e.status&&e.status<500)this.submitted=false;else this.error+=' Перед повторной попыткой проверьте список проектов: ответ команды мог быть потерян.'}
   finally{this.busy=false}},
  openProject(){this.$emit('changed',{...this.result,open:true})}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, createElementVNode: _createElementVNode, createTextVNode: _createTextVNode, normalizeClass: _normalizeClass, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withDirectives: _withDirectives, vModelRadio: _vModelRadio, vModelCheckbox: _vModelCheckbox, withModifiers: _withModifiers } = _Vue

    return (_openBlock(), _createElementBlock("section", {
      class: "project-wizard",
      "aria-label": "Мастер создания проекта TACTIC",
      "aria-busy": busy
    }, [
      _createElementVNode("ol", {
        class: "wizard-steps",
        "aria-label": "Этапы"
      }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['Проект','Схема','Проверка','Готово'], (label, i) => {
        return (_openBlock(), _createElementBlock("li", {
          key: label,
          class: _normalizeClass({current:step===i,complete:step>i}),
          "aria-current": step===i?'step':undefined
        }, [_createElementVNode("span", null, _toDisplayString(step>i?'✓':i+1), 1), _createTextVNode(_toDisplayString(label), 1)], 10, ["aria-current"]))
      }), 128))]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (options&&!options.can_write)
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, "Создание выключено настройкой записи native UI. Включите запись для своей тестовой установки."))
        : _createCommentVNode("", true),
      (step<3)
        ? (_openBlock(), _createElementBlock("form", {
            key: 2,
            onSubmit: _withModifiers($event => (step===2?create():next()), ["prevent"])
          }, [_createElementVNode("fieldset", {
            disabled: busy||submitted,
            class: "wizard-fields"
          }, [(step===0)
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "wizard-details"
              }, [_createElementVNode("label", null, [_createTextVNode("Название"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((title) = $event),
                maxlength: "200",
                placeholder: "Название проекта",
                autocomplete: "off",
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, title]])]), _createElementVNode("label", null, [_createTextVNode("Код проекта"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((code) = $event),
                maxlength: "30",
                pattern: "[a-z][a-z0-9_]{0,29}",
                placeholder: "my_project",
                autocomplete: "off",
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, code]]), _createElementVNode("small", null, "Используется в имени базы и адресе. После создания не переименовывается этим мастером.")]), _createElementVNode("label", null, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
                "onUpdate:modelValue": $event => ((description) = $event),
                rows: "4",
                maxlength: "10000",
                placeholder: "Назначение проекта"
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, description]])])]))
            : (step===1)
              ? (_openBlock(), _createElementBlock("div", {
                  key: 1,
                  class: "wizard-sources"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(options?.types, (t) => {
                  return (_openBlock(), _createElementBlock("label", {
                    key: t.code,
                    class: _normalizeClass(["wizard-source", {selected:type===t.code}])
                  }, [_withDirectives(_createElementVNode("input", {
                    type: "radio",
                    "onUpdate:modelValue": $event => ((type) = $event),
                    value: t.code,
                    name: "project-type"
                  }, null, 8, ["onUpdate:modelValue", "value"]), [[_vModelRadio, type]]), _createElementVNode("strong", null, _toDisplayString(t.title), 1), _createElementVNode("p", null, _toDisplayString(t.description), 1)], 2))
                }), 128)), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(options?.unsupported, (note) => {
                  return (_openBlock(), _createElementBlock("p", {
                    class: "muted",
                    key: note
                  }, _toDisplayString(note), 1))
                }), 128))]))
              : (_openBlock(), _createElementBlock("div", {
                  key: 2,
                  class: "wizard-review"
                }, [_createElementVNode("dl", null, [
                  _createElementVNode("dt", null, "Название"),
                  _createElementVNode("dd", null, _toDisplayString(review?.summary.title), 1),
                  _createElementVNode("dt", null, "Код / база"),
                  _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(code), 1)]),
                  _createElementVNode("dt", null, "Исходная схема"),
                  _createElementVNode("dd", null, _toDisplayString(summaryType), 1),
                  _createElementVNode("dt", null, "Описание"),
                  _createElementVNode("dd", null, _toDisplayString(description||'—'), 1)
                ]), _createElementVNode("p", { class: "notice" }, _toDisplayString(review?.notice), 1), _createElementVNode("label", { class: "inline-label" }, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((jump) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, jump]]), _createTextVNode("Перейти в новый проект после создания")])]))], 8, ["disabled"]), _createElementVNode("footer", { class: "wizard-actions" }, [
            (step>0)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  type: "button",
                  disabled: busy||submitted,
                  onClick: back
                }, "Назад", 8, ["disabled", "onClick"]))
              : _createCommentVNode("", true),
            _createElementVNode("span", { class: "spacer" }),
            busy
              ? (_openBlock(), _createElementBlock("span", {
                  key: 1,
                  role: "status"
                }, _toDisplayString(step===2?'Создание базы и выполнение исходных команд…':'Проверка…'), 1))
              : _createCommentVNode("", true),
            _createElementVNode("button", {
              class: "primary",
              disabled: busy||submitted||!options?.can_write||step===0&&!validDetails
            }, _toDisplayString(step===2?'Создать проект':step===1?'Проверить':'Далее'), 9, ["disabled"])
          ])], 40, ["onSubmit"]))
        : (_openBlock(), _createElementBlock("div", {
            key: 3,
            class: "wizard-success"
          }, [
            _createElementVNode("h3", null, "Проект «" + _toDisplayString(result.title) + "» создан", 1),
            _createElementVNode("p", null, _toDisplayString(result.notice), 1),
            _createElementVNode("button", {
              class: "primary",
              onClick: openProject
            }, "Открыть проект →", 8, ["onClick"]),
            _createElementVNode("p", null, [_createElementVNode("code", null, _toDisplayString(result.project_url), 1)])
          ]))
    ], 8, ["aria-busy"]))
  }
};
return __component;
})();
const SecurityMatrix = (function(){

const __component = {
 name:'SecurityMatrix',props:['project','target','user','screen'],emits:['dirty','changed','open'],
 data(){return {matrix:null,category:'',groupKeys:[],pending:{},query:'',busy:false,error:'',message:'',section:'matrix',groupsScreen:null,advanced:false,userKey:'',childDirty:false,groupDirty:false,seq:0}},
 computed:{rows(){const q=this.query.toLowerCase();return (this.matrix?.rows||[]).filter(r=>[r.label,r.value,r.pipeline,r.section].some(v=>String(v||'').toLowerCase().includes(q)))},changes(){return Object.values(this.pending)},dirty(){return this.changes.length>0||this.childDirty||this.groupDirty},fixed(){return !!this.screen?.options?.native_fixed_group||/(?:Project|Link|GearMenu|SearchType|Process|Task|User)SecurityWdg$/.test(this.screen?.handler||'')}},
 watch:{dirty(v){this.$emit('dirty',v)}},mounted(){this.load()},beforeUnmount(){this.seq++},
 methods:{
 args(){return {project:this.project,target:this.target}},
 async load(category=this.category){const seq=++this.seq;this.busy=true;this.error='';try{const m=await api.request('/security-matrix',{...this.args(),category:category||undefined,groups:this.groupKeys.length?JSON.stringify(this.groupKeys):undefined});if(seq!==this.seq)return;this.matrix=m;this.category=m.category;this.groupKeys=m.groups.map(g=>g.key);this.pending={}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 choose(category){if(category===this.category)return;if(this.dirty&&!confirm('Отменить изменения текущей матрицы?'))return;this.groupKeys=[];this.load(category)},
 groupChange(){if(this.dirty&&!confirm('Отменить правки перед сменой групп?'))return;this.load()},
 value(row,group){return this.pending[JSON.stringify([row.id,group.key])]?.value??row.cells[group.key].checked},
 toggle(row,group,event){const cell=row.cells[group.key];if(this.busy||cell.read_only||!this.matrix.can_write)return;const id=JSON.stringify([row.id,group.key]),value=event.target.checked,next={...this.pending};if(value===cell.explicit)delete next[id];else next[id]={row:row.id,group:group.key,value};this.pending=next},
 discard(){if(this.dirty&&!confirm('Отменить все несохранённые изменения прав?'))return;this.pending={}},
 async save(){if(this.busy||!this.dirty)return;this.busy=true;this.error='';try{api.action?.('form.save',{...this.args(),control:'security-matrix',count:this.changes.length});const r=await api.request('/security-matrix',{...this.args(),category:this.category,groups:this.groupKeys,changes:this.changes,revision:this.matrix.revision},'PATCH');this.pending={};await this.load();this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 async showGroups(){if(this.dirty&&!confirm('Отменить правки матрицы и открыть группы?'))return;this.pending={};this.error='';try{this.groupsScreen=await api.request('/open',{project:this.project,target:this.target+'/~admin/groups-table'});this.section='groups'}catch(e){this.error=e.message}},
 editUser(row){if(this.dirty||this.busy){this.error='Сначала сохраните или отмените правки матрицы';return}if(this.category==='users'){this.childDirty=false;this.userKey=row.key}},
 openAdvanced(){if(this.dirty||this.busy){this.error='Сначала сохраните или отмените текущие правки';return}this.advanced=true;this.childDirty=false},
 closeChild(){if(this.childDirty&&!confirm('Отменить несохранённые изменения?'))return;this.advanced=false;this.userKey='';this.childDirty=false},
 showMatrix(){if(this.section==='matrix')return;if(this.groupDirty&&!confirm('Отменить правки таблицы групп?'))return;this.groupDirty=false;this.section='matrix';this.load()}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { normalizeClass: _normalizeClass, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, renderList: _renderList, Fragment: _Fragment, vModelText: _vModelText, withDirectives: _withDirectives, vModelCheckbox: _vModelCheckbox, createTextVNode: _createTextVNode, resolveComponent: _resolveComponent, createBlock: _createBlock, createVNode: _createVNode, Teleport: _Teleport } = _Vue

    const _component_WidgetTable = _resolveComponent("WidgetTable")
    const _component_AdminPanel = _resolveComponent("AdminPanel")
    const _component_UserGroups = _resolveComponent("UserGroups")

    return (_openBlock(), _createElementBlock("section", {
      class: "security-workspace",
      "aria-label": "Права TACTIC"
    }, [
      _createElementVNode("header", {
        class: "widget-toolbar",
        role: "group",
        "aria-label": "Инструменты прав"
      }, [_createElementVNode("div", { class: "toolbar" }, [(!fixed)
        ? (_openBlock(), _createElementBlock("button", {
            key: 0,
            class: _normalizeClass({primary:section==='matrix'}),
            onClick: showMatrix
          }, "Матрицы", 10, ["onClick"]))
        : _createCommentVNode("", true), (!fixed)
        ? (_openBlock(), _createElementBlock("button", {
            key: 1,
            onClick: showGroups
          }, "Группы", 8, ["onClick"]))
        : _createCommentVNode("", true), (category!=='users')
        ? (_openBlock(), _createElementBlock("button", {
            key: 2,
            disabled: busy||dirty,
            onClick: openAdvanced
          }, "XML правил…", 8, ["disabled", "onClick"]))
        : _createCommentVNode("", true)])]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      message
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, _toDisplayString(message), 1))
        : _createCommentVNode("", true),
      (section==='matrix')
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
            (matrix?.categories.length>1)
              ? (_openBlock(), _createElementBlock("nav", {
                  key: 0,
                  class: "admin-section-tabs",
                  "aria-label": "Категории прав"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(matrix.categories, (c) => {
                  return (_openBlock(), _createElementBlock("button", {
                    key: c.id,
                    "aria-selected": category===c.id,
                    onClick: $event => (choose(c.id))
                  }, _toDisplayString(c.label), 9, ["aria-selected", "onClick"]))
                }), 128))]))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "toolbar admin-matrix-tools" }, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((query) = $event),
                type: "search",
                placeholder: "Найти строку…",
                "aria-label": "Поиск в матрице"
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, query]]),
              matrix
                ? (_openBlock(), _createElementBlock("details", {
                    key: 0,
                    class: "admin-group-picker"
                  }, [_createElementVNode("summary", null, "Группы · " + _toDisplayString(matrix.groups.length), 1), _createElementVNode("div", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(matrix.available_groups, (g) => {
                    return (_openBlock(), _createElementBlock("label", { key: g.key }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      "onUpdate:modelValue": $event => ((groupKeys) = $event),
                      value: g.key,
                      disabled: busy||dirty
                    }, null, 8, ["onUpdate:modelValue", "value", "disabled"]), [[_vModelCheckbox, groupKeys]]), _createTextVNode(_toDisplayString(g.label||g.name) + " ", 1), _createElementVNode("small", null, _toDisplayString(g.project||'общая'), 1)]))
                  }), 128)), _createElementVNode("button", {
                    disabled: busy||!groupKeys.length||groupKeys.length>40||dirty,
                    onClick: groupChange
                  }, "Показать выбранные", 8, ["disabled", "onClick"])])]))
                : _createCommentVNode("", true),
              _createElementVNode("button", {
                disabled: busy||dirty,
                onClick: $event => (load())
              }, "Обновить", 8, ["disabled", "onClick"]),
              _createElementVNode("span", { class: "spacer" }),
              (changes.length)
                ? (_openBlock(), _createElementBlock("span", {
                    key: 1,
                    class: "pending-count"
                  }, _toDisplayString(changes.length) + " правок", 1))
                : _createCommentVNode("", true),
              (changes.length)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 2,
                    disabled: busy,
                    onClick: discard
                  }, "Отменить", 8, ["disabled", "onClick"]))
                : _createCommentVNode("", true),
              (changes.length)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 3,
                    class: "primary",
                    disabled: busy||!matrix.can_write,
                    onClick: save
                  }, "Сохранить изменения", 8, ["disabled", "onClick"]))
                : _createCommentVNode("", true)
            ]),
            busy
              ? (_openBlock(), _createElementBlock("p", {
                  key: 1,
                  class: "muted"
                }, "Загрузка…"))
              : _createCommentVNode("", true),
            matrix
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
                  _createElementVNode("p", { class: "muted admin-source-caption" }, [_createTextVNode(_toDisplayString(matrix.notice) + " · ", 1), _createElementVNode("code", null, _toDisplayString(matrix.command), 1)]),
                  (!matrix.can_write)
                    ? (_openBlock(), _createElementBlock("p", {
                        key: 0,
                        class: "notice"
                      }, "Запись отключена в настройках установки."))
                    : _createCommentVNode("", true),
                  _createElementVNode("div", { class: "table-scroll security-matrix-scroll" }, [_createElementVNode("table", { class: "security-matrix" }, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Область / объект"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(matrix.groups, (g) => {
                    return (_openBlock(), _createElementBlock("th", { key: g.key }, [_createElementVNode("b", null, _toDisplayString(g.label||g.name), 1), _createElementVNode("small", null, _toDisplayString(g.level) + " · " + _toDisplayString(g.project||'global'), 1)]))
                  }), 128))])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(rows, (row) => {
                    return (_openBlock(), _createElementBlock("tr", {
                      key: row.id,
                      "data-rule": row.value
                    }, [_createElementVNode("th", null, [(category==='users')
                      ? (_openBlock(), _createElementBlock("button", {
                          key: 0,
                          class: "text-button",
                          onClick: $event => (editUser(row))
                        }, _toDisplayString(row.label), 9, ["onClick"]))
                      : (_openBlock(), _createElementBlock("b", { key: 1 }, _toDisplayString(row.label), 1)), _createElementVNode("small", null, _toDisplayString(row.pipeline||row.submenu||row.section||row.value), 1)]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(matrix.groups, (g) => {
                      return (_openBlock(), _createElementBlock("td", {
                        key: g.key,
                        class: _normalizeClass({'matrix-pending':pending[JSON.stringify([row.id,g.key])],'matrix-inherited':row.cells[g.key].inherited}),
                        title: row.cells[g.key].reason||'Явное правило allow'
                      }, [_createElementVNode("label", { class: "matrix-checkbox" }, [_createElementVNode("input", {
                        type: "checkbox",
                        checked: value(row,g),
                        disabled: busy||row.cells[g.key].read_only||!matrix.can_write,
                        "aria-label": row.label+' — '+g.name,
                        onChange: $event => (toggle(row,g,$event))
                      }, null, 40, ["checked", "disabled", "aria-label", "onChange"]), (row.cells[g.key].inherited)
                        ? (_openBlock(), _createElementBlock("span", {
                            key: 0,
                            "aria-hidden": "true"
                          }, "↳"))
                        : (row.cells[g.key].read_only)
                          ? (_openBlock(), _createElementBlock("span", {
                              key: 1,
                              "aria-hidden": "true"
                            }, "•"))
                          : _createCommentVNode("", true)])], 10, ["title"]))
                    }), 128))], 8, ["data-rule"]))
                  }), 128))])])]),
                  (!matrix.groups.length)
                    ? (_openBlock(), _createElementBlock("p", {
                        key: 1,
                        class: "notice"
                      }, "Для этой категории нет групп текущего проекта. Назначьте группе проект в её исходной форме или Project Security."))
                    : _createCommentVNode("", true),
                  (!rows.length)
                    ? (_openBlock(), _createElementBlock("p", {
                        key: 2,
                        class: "muted"
                      }, "Подходящих строк нет."))
                    : _createCommentVNode("", true),
                  _createElementVNode("p", { class: "muted" }, "↳ задано access_level или общим правилом. Наведите указатель на недоступную ячейку для причины. XML и нетронутые категории сохраняются.")
                ], 64))
              : _createCommentVNode("", true)
          ], 64))
        : groupsScreen
          ? (_openBlock(), _createBlock(_component_WidgetTable, {
              key: 3,
              project: project,
              screen: groupsScreen,
              user: user,
              onOpen: $event => ($emit('open',$event)),
              onDirty: $event => (groupDirty=$event),
              onChanged: $event => ($emit('changed'))
            }, null, 8, ["project", "screen", "user", "onOpen", "onDirty", "onChanged"]))
          : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [advanced
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop"
          }, [_createElementVNode("section", { class: "modal widget-popup" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, "Исходные access_rules"), _createElementVNode("button", { onClick: closeChild }, "×", 8, ["onClick"])]), _createVNode(_component_AdminPanel, {
            project: project,
            target: target,
            kind: "security",
            "initial-key": matrix?.groups[0]?.key,
            onDirty: $event => (childDirty=$event),
            onChanged: $event => {load();$emit('changed')}
          }, null, 8, ["project", "target", "initial-key", "onDirty", "onChanged"])])]))
        : _createCommentVNode("", true), userKey
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "modal-backdrop"
          }, [_createElementVNode("section", { class: "modal widget-popup" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, "Группы пользователя"), _createElementVNode("button", { onClick: closeChild }, "×", 8, ["onClick"])]), _createVNode(_component_UserGroups, {
            project: project,
            target: target,
            "initial-key": userKey,
            onDirty: $event => (childDirty=$event),
            onChanged: $event => {load();$emit('changed')}
          }, null, 8, ["project", "target", "initial-key", "onDirty", "onChanged"])])]))
        : _createCommentVNode("", true)]))
    ]))
  }
};
return __component;
})();
const UserGroups = (function(){

const __component = {
 name:'UserGroups',props:['project','target','initialKey'],emits:['dirty','changed'],
 data(){return {users:[],key:this.initialKey||'',loadedKey:'',model:null,members:[],query:'',busy:false,error:'',message:'',seq:0}},
 computed:{dirty(){return this.model&&JSON.stringify([...this.members].sort())!==JSON.stringify([...this.model.members].sort())},groups(){const q=this.query.toLowerCase();return (this.model?.groups||[]).filter(g=>[g.name,g.title,g.project].some(v=>String(v||'').toLowerCase().includes(q)))}},
 watch:{dirty(v){this.$emit('dirty',!!v)}},async mounted(){if(this.key)await this.load(this.key);else try{this.users=(await api.request('/user-groups',{project:this.project,target:this.target})).users}catch(e){this.error=e.message}},beforeUnmount(){this.seq++},
 methods:{
 async change(){if(this.dirty&&!confirm('Отменить изменения групп пользователя?')){this.key=this.loadedKey;return}await this.load(this.key)},
 async load(key){if(!key){this.model=null;return}const seq=++this.seq;this.busy=true;this.error='';try{const m=await api.request('/user-groups',{project:this.project,target:this.target,key});if(seq!==this.seq)return;this.model=m;this.loadedKey=this.key=m.key;this.members=[...m.members]}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 async save(){if(this.busy||!this.dirty)return;this.busy=true;this.error='';try{const r=await api.request('/user-groups',{project:this.project,target:this.target,key:this.model.key,members:this.members,revision:this.model.revision},'PATCH');await this.load(this.model.key);this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createCommentVNode: _createCommentVNode, vModelText: _vModelText, createTextVNode: _createTextVNode, vModelCheckbox: _vModelCheckbox } = _Vue

    return (_openBlock(), _createElementBlock("section", { class: "membership-panel" }, [
      _createElementVNode("div", { class: "toolbar" }, [
        (!initialKey)
          ? _withDirectives((_openBlock(), _createElementBlock("select", {
              key: 0,
              "onUpdate:modelValue": $event => ((key) = $event),
              onChange: change,
              disabled: busy,
              "aria-label": "Пользователь"
            }, [_createElementVNode("option", { value: "" }, "Выберите пользователя…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(users, (u) => {
              return (_openBlock(), _createElementBlock("option", {
                key: u.key,
                value: u.key
              }, _toDisplayString(u.label) + " · " + _toDisplayString(u.login), 9, ["value"]))
            }), 128))], 40, ["onUpdate:modelValue", "onChange", "disabled"])), [[_vModelSelect, key]])
          : (_openBlock(), _createElementBlock("b", { key: 1 }, _toDisplayString(model?.login), 1)),
        _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((query) = $event),
          type: "search",
          placeholder: "Найти группу…"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, query]]),
        _createElementVNode("span", { class: "spacer" }),
        dirty
          ? (_openBlock(), _createElementBlock("button", {
              key: 2,
              onClick: $event => (members=[...model.members]),
              disabled: busy
            }, "Отменить", 8, ["onClick", "disabled"]))
          : _createCommentVNode("", true),
        _createElementVNode("button", {
          disabled: busy||!dirty||!model?.can_write,
          class: "primary",
          onClick: save
        }, "Сохранить состав", 8, ["disabled", "onClick"])
      ]),
      _createElementVNode("p", { class: "muted" }, "Исходный GroupAssignCbk · sthpw/login_in_group. Существующее членство в admin защищено. Неотображаемые назначения не снимаются фильтром."),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      message
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, _toDisplayString(message), 1))
        : _createCommentVNode("", true),
      model
        ? (_openBlock(), _createElementBlock("p", { key: 2 }, [_createTextVNode(_toDisplayString(members.length) + " групп ", 1), dirty
            ? (_openBlock(), _createElementBlock("span", { key: 0 }, "· Несохранённые изменения"))
            : _createCommentVNode("", true)]))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "member-grid" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(groups, (g) => {
        return (_openBlock(), _createElementBlock("label", {
          key: g.name,
          class: "member-row"
        }, [_withDirectives(_createElementVNode("input", {
          type: "checkbox",
          "onUpdate:modelValue": $event => ((members) = $event),
          value: g.name,
          disabled: busy||!model.can_write||(g.name==='admin'&&model.members.includes('admin'))
        }, null, 8, ["onUpdate:modelValue", "value", "disabled"]), [[_vModelCheckbox, members]]), _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(g.name), 1), _createElementVNode("small", null, _toDisplayString(g.project||'Общая группа') + " · " + _toDisplayString(g.title), 1)])]))
      }), 128))])
    ]))
  }
};
return __component;
})();
const UserManager = (function(){

const __component = {
 name:'UserManager',props:['project','target','user','screen','mode'],emits:['dirty','changed','open'],
 data(){return {section:'users',table:null,child:null,error:'',busy:false,dirty:false,seq:0}},
 computed:{standalone(){return this.mode==='groups'||this.screen?.handler?.endsWith('UserPanelWdg')}},
 mounted(){this.select(this.mode==='groups'?'groups':'users')},beforeUnmount(){this.seq++},
 methods:{mark(v){this.dirty=v;this.$emit('dirty',v)},async select(section){if(this.dirty&&!confirm('Отменить несохранённые изменения?'))return;const seq=++this.seq;this.busy=true;this.error='';const part=section==='users'?'users-table':section==='groups'?'groups-table':section==='assignment'?'assignment':'security';try{const s=await api.request('/open',{project:this.project,target:this.target+'/~admin/'+part});if(seq!==this.seq)return;this.section=section;if(s.kind==='table')this.table=s;else this.child=s;this.mark(false)}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_WidgetTable = _resolveComponent("WidgetTable")
    const _component_SecurityMatrix = _resolveComponent("SecurityMatrix")

    return (_openBlock(), _createElementBlock("section", { class: "user-manager" }, [
      (!standalone)
        ? (_openBlock(), _createElementBlock("nav", {
            key: 0,
            class: "admin-section-tabs",
            "aria-label": "Manage Users"
          }, [_createElementVNode("button", {
            "aria-selected": section==='users',
            onClick: $event => (select('users'))
          }, "Users", 8, ["aria-selected", "onClick"]), _createElementVNode("button", {
            "aria-selected": section==='assignment',
            onClick: $event => (select('assignment'))
          }, "Group Assignment", 8, ["aria-selected", "onClick"]), _createElementVNode("button", {
            "aria-selected": section==='security',
            onClick: $event => (select('security'))
          }, "Group Security", 8, ["aria-selected", "onClick"])]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      busy
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "muted"
          }, "Загрузка исходного виджета…"))
        : _createCommentVNode("", true),
      (['users','groups'].includes(section)&&table)
        ? (_openBlock(), _createBlock(_component_WidgetTable, {
            key: table.id,
            project: project,
            screen: table,
            user: user,
            onOpen: $event => ($emit('open',$event)),
            onDirty: mark,
            onChanged: $event => ($emit('changed'))
          }, null, 8, ["project", "screen", "user", "onOpen", "onDirty", "onChanged"]))
        : child
          ? (_openBlock(), _createBlock(_component_SecurityMatrix, {
              key: child.id,
              project: project,
              target: child.id,
              screen: child,
              user: user,
              onOpen: $event => ($emit('open',$event)),
              onDirty: mark,
              onChanged: $event => ($emit('changed'))
            }, null, 8, ["project", "target", "screen", "user", "onOpen", "onDirty", "onChanged"]))
          : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const SidebarEditor = (function(){

const __component = {
 name:'SidebarEditor',props:['project','target','initialView','allowWrites','user'],emits:['dirty','changed','open'],
 data(){return {view:this.initialView||'project_view',loadedView:'',model:null,working:[],operations:[],index:-1,draft:null,sourceDraft:'',busy:false,error:'',message:'',seq:0,trail:[],adding:false,newKind:'link',newName:'',newTitle:'',newType:'',newView:'table',newFolder:'',raw:false,rawDirty:false,menu:null}},
 computed:{elementDirty(){return !!this.draft&&JSON.stringify(this.draft)!==this.sourceDraft},dirty(){return this.operations.length>0||this.elementDirty||this.adding||this.rawDirty},chosen(){return this.working[this.index]},own(){return 'my_view_'+String(this.user?.login||'admin').replaceAll('\\','_')}},
 watch:{dirty(v){this.$emit('dirty',v)}},mounted(){this.load(this.view)},beforeUnmount(){this.seq++},
 methods:{
 openRaw(){if(this.dirty||this.busy){this.error='Сначала сохраните или отмените правки sidebar';return}this.rawDirty=false;this.raw=true},
 closeRaw(){if(this.rawDirty&&!confirm('Закрыть XML без сохранения?'))return;this.raw=false;this.rawDirty=false},
 args(){return {project:this.project,target:this.target,view:this.loadedView||this.view}},
 async changeView(){if(this.dirty&&!confirm('Отменить несохранённые правки sidebar?')){this.view=this.loadedView;return}this.trail=[];await this.load(this.view)},
 async load(view){const seq=++this.seq;this.busy=true;this.error='';try{const m=await api.request('/sidebar-editor',{project:this.project,target:this.target,view});if(seq!==this.seq)return;this.model=m;this.loadedView=this.view=m.view;this.working=JSON.parse(JSON.stringify(m.elements));this.operations=[];this.index=-1;this.draft=null;this.adding=false}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 select(index){if(this.elementDirty&&!confirm('Отменить несохранённое изменение выбранной ссылки?'))return;this.index=index;const e=this.working[index];this.draft={title:e.title,description:e.attributes.description||'',icon:e.attributes.icon||'',visible:e.attributes.is_visible!=='false',options:JSON.stringify(e.options||{},null,2),editOptions:false};this.sourceDraft=JSON.stringify(this.draft);this.adding=false},
 stage(){if(!this.elementDirty)return true;this.error='';try{const d=this.draft,e=this.chosen;const op={op:'edit',index:this.index,attributes:{title:d.title,description:d.description,icon:d.icon,is_visible:d.visible?'true':'false'}};if(d.editOptions){op.options=JSON.parse(d.options);op.handler=e.handler||'LinkWdg'}this.operations.push(op);this.working[this.index]={...e,title:d.title,attributes:{...e.attributes,...op.attributes},options:op.options||e.options};this.sourceDraft=JSON.stringify(d);return true}catch(e){this.error='Параметры: '+e.message;return false}},
 move(index,delta){if(this.elementDirty&&!this.stage())return;const j=index+delta;if(j<0||j>=this.working.length)return;const order=this.working.map((_,i)=>i);[order[index],order[j]]=[order[j],order[index]];this.operations.push({op:'reorder',order});const a=[...this.working];[a[index],a[j]]=[a[j],a[index]];this.working=a;this.index=-1;this.draft=null;this.select(j)},
 remove(index){if(!confirm('Убрать ссылку из этого раздела? Общая definition, объекты и вложенный view останутся.'))return;this.operations.push({op:'remove',index});this.working.splice(index,1);this.index=-1;this.draft=null},
 beginAdd(kind){if(this.elementDirty&&!this.stage())return;this.adding=true;this.newKind=kind;this.newName='';this.newTitle='';this.newType='';this.newView='table';this.newFolder=this.model?.personal?this.own+'__':'';this.index=-1;this.draft=null},
 add(){this.error='';if(!/^[A-Za-z_][A-Za-z0-9_.:-]{0,159}$/.test(this.newName)){this.error='Нужно корректное системное имя';return}let options={};if(this.newKind==='link'){if(!this.newType){this.error='Укажите SearchType';return}options={search_type:this.newType,view:this.newView||'table'}}else if(this.newKind==='folder')options={view:this.newFolder||this.newName};const attrs={title:this.newTitle||this.newName};const op={op:'add',name:this.newName,kind:this.newKind,options,attributes:attrs};this.operations.push(op);this.working.push({name:this.newName,title:attrs.title,kind:this.newKind,handler:({link:'LinkWdg',folder:'FolderWdg',separator:'SeparatorWdg',title:'TitleWdg'})[this.newKind],options,attributes:attrs,renderer:this.newKind==='link'?'table':this.newKind,sources:['Новая локальная definition'],can_edit_options:true});this.adding=false},
 async save(){if(this.busy||!this.stage())return;if(this.adding){this.error='Добавьте новый элемент в черновик или отмените его';return}if(!this.operations.length)return;this.busy=true;this.error='';try{api.action?.('form.save',{project:this.project,target:this.target||'',control:'sidebar-editor',count:this.operations.length});const r=await api.request('/sidebar-editor',{...this.args(),revision:this.model.revision,operations:this.operations},'PATCH');await this.load(this.loadedView);this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 async folder(e){if(e.kind!=='folder')return;if(this.dirty&&!confirm('Сначала нужно сохранить изменения. Перейти, отменив черновик?'))return;this.trail.push(this.loadedView);await this.load(e.options.view||e.name)},
 async back(){if(this.dirty&&!confirm('Отменить правки текущего раздела?'))return;const v=this.trail.pop();if(v)await this.load(v)},
 context(event,index){event.preventDefault();event.stopPropagation();this.menu={x:event.clientX,y:event.clientY,title:this.working[index].title,items:[{id:'edit',label:'Свойства'},{id:'up',label:'Выше',enabled:index>0},{id:'down',label:'Ниже',enabled:index<this.working.length-1},{id:'folder',label:'Открыть папку',enabled:this.working[index].kind==='folder'},{type:'separator'},{id:'remove',label:'Убрать ссылку',enabled:this.allowWrites}]};this.menu.index=index},
 action(item){const i=this.menu.index;this.menu=null;if(item.id==='edit')this.select(i);else if(item.id==='up')this.move(i,-1);else if(item.id==='down')this.move(i,1);else if(item.id==='folder')this.folder(this.working[i]);else if(item.id==='remove')this.remove(i)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, vModelText: _vModelText, withKeys: _withKeys, createElementVNode: _createElementVNode, withDirectives: _withDirectives, createTextVNode: _createTextVNode, renderList: _renderList, Fragment: _Fragment, normalizeClass: _normalizeClass, withModifiers: _withModifiers, vModelCheckbox: _vModelCheckbox, resolveComponent: _resolveComponent, createBlock: _createBlock, createVNode: _createVNode, Teleport: _Teleport } = _Vue

    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_ConfigEditor = _resolveComponent("ConfigEditor")

    return (_openBlock(), _createElementBlock("section", {
      class: "sidebar-workbench",
      "aria-label": "Редактор sidebar"
    }, [
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      message
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "success"
          }, _toDisplayString(message), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", { class: "toolbar sidebar-editor-tools" }, [
        (trail.length)
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              disabled: busy,
              onClick: back
            }, "← Назад", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true),
        _createElementVNode("label", null, [_createTextVNode("Раздел"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((view) = $event),
          list: "sidebar-views",
          onKeyup: _withKeys(changeView, ["enter"]),
          "aria-label": "Раздел sidebar"
        }, null, 40, ["onUpdate:modelValue", "onKeyup"]), [[_vModelText, view]])]),
        _createElementVNode("datalist", { id: "sidebar-views" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(model?.views||[], (v) => {
          return (_openBlock(), _createElementBlock("option", {
            key: v,
            value: v
          }, null, 8, ["value"]))
        }), 128))]),
        _createElementVNode("button", {
          disabled: busy,
          onClick: changeView
        }, "Открыть", 8, ["disabled", "onClick"]),
        _createElementVNode("span", { class: "pill" }, _toDisplayString(model?.personal?'Личный':'Общий') + " · " + _toDisplayString(project), 1),
        _createElementVNode("span", { class: "spacer" }),
        _createElementVNode("button", {
          disabled: busy||dirty,
          onClick: openRaw
        }, "Исходный XML…", 8, ["disabled", "onClick"]),
        _createElementVNode("details", { class: "admin-add-menu" }, [_createElementVNode("summary", null, "Добавить…"), _createElementVNode("div", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList({link:'Ссылка на таблицу',folder:'Папка',separator:'Разделитель',title:'Заголовок'}, (label, kind) => {
          return (_openBlock(), _createElementBlock("button", {
            key: kind,
            disabled: !allowWrites||busy,
            onClick: $event => (beginAdd(kind))
          }, _toDisplayString(label), 9, ["disabled", "onClick"]))
        }), 128))])]),
        dirty
          ? (_openBlock(), _createElementBlock("button", {
              key: 1,
              disabled: busy,
              onClick: changeView
            }, "Отменить", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true),
        _createElementVNode("button", {
          class: "primary",
          disabled: busy||!dirty||!allowWrites,
          onClick: save
        }, "Сохранить", 8, ["disabled", "onClick"])
      ]),
      _createElementVNode("p", { class: "muted" }, _toDisplayString(model?.notice), 1),
      _createElementVNode("div", { class: "admin-two-pane sidebar-designer-body" }, [_createElementVNode("aside", { class: "admin-catalog sidebar-outline" }, [_createElementVNode("ol", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(working, (e, i) => {
        return (_openBlock(), _createElementBlock("li", {
          key: i,
          class: _normalizeClass({selected:index===i}),
          onContextmenu: $event => (context($event,i))
        }, [_createElementVNode("button", {
          class: "sidebar-outline-name",
          "aria-label": e.title,
          onClick: $event => (select(i)),
          onDblclick: $event => (folder(e))
        }, [_createElementVNode("span", {
          class: "sidebar-kind",
          "aria-hidden": "true"
        }, _toDisplayString(({folder:'▸',separator:'—',title:'T',link:'↗'})[e.kind]), 1), _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(e.title), 1), _createElementVNode("small", null, _toDisplayString(e.name) + " · " + _toDisplayString(e.renderer), 1)])], 40, ["aria-label", "onClick", "onDblclick"]), allowWrites
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              disabled: i===0,
              onClick: $event => (move(i,-1)),
              "aria-label": "Выше"
            }, "↑", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true), allowWrites
          ? (_openBlock(), _createElementBlock("button", {
              key: 1,
              disabled: i===working.length-1,
              onClick: $event => (move(i,1)),
              "aria-label": "Ниже"
            }, "↓", 8, ["disabled", "onClick"]))
          : _createCommentVNode("", true)], 42, ["onContextmenu"]))
      }), 128))]), (!working.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "muted"
          }, "Пустой раздел. Можно добавить ссылку, папку или разделитель."))
        : _createCommentVNode("", true)]), _createElementVNode("main", { class: "admin-editor-pane" }, [adding
        ? (_openBlock(), _createElementBlock("form", {
            key: 0,
            onSubmit: _withModifiers(add, ["prevent"])
          }, [
            _createElementVNode("h3", null, "Новый элемент: " + _toDisplayString(newKind), 1),
            _createElementVNode("div", { class: "field-grid" }, [_createElementVNode("label", null, [_createTextVNode("Системное имя"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((newName) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newName]])]), _createElementVNode("label", null, [_createTextVNode("Заголовок"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((newTitle) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newTitle]])])]),
            (newKind==='link')
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("label", null, [_createTextVNode("SearchType"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((newType) = $event),
                  placeholder: "project/item",
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newType]])]), _createElementVNode("label", null, [_createTextVNode("View"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((newView) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, newView]])])], 64))
              : _createCommentVNode("", true),
            (newKind==='folder')
              ? (_openBlock(), _createElementBlock("label", { key: 1 }, [_createTextVNode("Новый view папки"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((newFolder) = $event),
                  placeholder: newName,
                  required: ""
                }, null, 8, ["onUpdate:modelValue", "placeholder"]), [[_vModelText, newFolder]])]))
              : _createCommentVNode("", true),
            _createElementVNode("p", { class: "muted" }, "Ссылка использует LinkWdg и исходную конфигурацию таблицы. Специальный редактор можно задать в display options после создания."),
            _createElementVNode("button", { class: "primary" }, "Добавить в черновик"),
            _createElementVNode("button", {
              type: "button",
              onClick: $event => (adding=false)
            }, "Отмена", 8, ["onClick"])
          ], 40, ["onSubmit"]))
        : draft
          ? (_openBlock(), _createElementBlock("form", {
              key: 1,
              onSubmit: _withModifiers(stage, ["prevent"])
            }, [
              _createElementVNode("h3", null, _toDisplayString(chosen.name), 1),
              _createElementVNode("div", { class: "field-grid" }, [_createElementVNode("label", null, [_createTextVNode("Заголовок"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((draft.title) = $event),
                readonly: !allowWrites
              }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, draft.title]])]), _createElementVNode("label", null, [_createTextVNode("Иконка"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((draft.icon) = $event),
                readonly: !allowWrites,
                placeholder: "FA_FOLDER / VIEW"
              }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, draft.icon]])])]),
              _createElementVNode("label", null, [_createTextVNode("Описание"), _withDirectives(_createElementVNode("textarea", {
                "onUpdate:modelValue": $event => ((draft.description) = $event),
                rows: "3",
                readonly: !allowWrites
              }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, draft.description]])]),
              _createElementVNode("label", { class: "checkbox-inline" }, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                "onUpdate:modelValue": $event => ((draft.visible) = $event),
                disabled: !allowWrites
              }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelCheckbox, draft.visible]]), _createTextVNode(" Показывать ссылку")]),
              _createElementVNode("div", { class: "admin-source-box" }, [_createElementVNode("code", null, _toDisplayString(chosen.handler||'default'), 1), _createElementVNode("p", null, _toDisplayString(chosen.sources?.join(' → ')), 1)]),
              (chosen.kind==='folder')
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    type: "button",
                    onClick: $event => (folder(chosen))
                  }, "Открыть вложенный view " + _toDisplayString(chosen.options.view), 9, ["onClick"]))
                : _createCommentVNode("", true),
              _createElementVNode("details", null, [
                _createElementVNode("summary", null, "Display options / исходные параметры"),
                (chosen.can_edit_options&&chosen.kind==='link')
                  ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      "onUpdate:modelValue": $event => ((draft.editOptions) = $event),
                      disabled: !allowWrites
                    }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelCheckbox, draft.editOptions]]), _createTextVNode(" Создать локальное переопределение параметров ссылки")]))
                  : _createCommentVNode("", true),
                _withDirectives(_createElementVNode("textarea", {
                  "onUpdate:modelValue": $event => ((draft.options) = $event),
                  class: "code-input",
                  rows: "12",
                  readonly: !allowWrites||!draft.editOptions,
                  spellcheck: "false"
                }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, draft.options]]),
                _createElementVNode("p", { class: "muted" }, "Неизменённые параметры и callbacks сохраняются. Неизвестный handler не превращается в готовый native-экран; его маршрут показывает диагностику.")
              ]),
              _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
                disabled: !allowWrites||!elementDirty,
                class: "primary"
              }, "Применить в черновик", 8, ["disabled"]), _createElementVNode("button", {
                type: "button",
                disabled: !allowWrites,
                onClick: $event => (remove(index))
              }, "Убрать ссылку…", 8, ["disabled", "onClick"])])
            ], 40, ["onSubmit"]))
          : (_openBlock(), _createElementBlock("div", { key: 2 }, [_createElementVNode("h3", null, "Состав раздела"), _createElementVNode("p", null, "Выберите элемент для редактирования. Двойной щелчок по папке открывает её раздел. Правый клик — операции со ссылкой."), _createElementVNode("details", null, [_createElementVNode("summary", null, "Источники конфигурации"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(model?.layers||[], (s, i) => {
              return (_openBlock(), _createElementBlock("p", { key: i }, [_createElementVNode("code", null, _toDisplayString(s.view), 1), _createTextVNode(" · " + _toDisplayString(s.origin), 1)]))
            }), 128))])]))])]),
      menu
        ? (_openBlock(), _createBlock(_component_ContextMenu, {
            key: 2,
            menu: menu,
            onClose: $event => (menu=null),
            onAction: action
          }, null, 8, ["menu", "onClose", "onAction"]))
        : _createCommentVNode("", true),
      (_openBlock(), _createBlock(_Teleport, { to: "body" }, [raw
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "modal-backdrop"
          }, [_createElementVNode("section", { class: "modal widget-popup" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, "Исходные widget_config"), _createElementVNode("button", { onClick: closeRaw }, "×", 8, ["onClick"])]), _createVNode(_component_ConfigEditor, {
            project: project,
            mode: "config-editor",
            "allow-writes": allowWrites,
            onDirty: $event => (rawDirty=$event),
            onChanged: $event => {load(loadedView);$emit('changed')}
          }, null, 8, ["project", "allow-writes", "onDirty", "onChanged"])])]))
        : _createCommentVNode("", true)]))
    ]))
  }
};
return __component;
})();
const AdminPanel = (function(){


const __component = {
 name:'AdminPanel',components:{ProjectWizard},props:{project:String,target:String,kind:String,initialKey:String},emits:['changed','dirty'],
 data(){return {data:null,error:'',notice:'',busy:false,section:'',form:null,groupKey:'',group:null,xml:'',ruleIndex:-1,ruleProps:{},creatingGroup:false,groupName:''}},
 async mounted(){this.section=this.kind==='security'?'security':this.kind;if(this.kind!=='project-create')await this.load();if(this.kind==='security'&&this.initialKey){this.groupKey=this.initialKey;await this.loadGroup()}},
 methods:{
 args(){return {project:this.project,target:this.target}},
 systemLabel(key){return ({core_version:'Ядро TACTIC',ui_version:'Нативный интерфейс',python:'Python',platform:'Система',http_server:'HTTP-сервер',database_vendor:'Движок базы',project:'Текущий проект',projects:'Проектов',database_checked:'Запрос к базе выполнен',allow_writes:'Запись разрешена',allow_uploads:'Загрузка разрешена',admin_only:'Только администраторы'})[key]||key},
 async load(){this.error='';this.busy=true;try{const path=this.section==='security'?'/security':this.kind==='project-create'?'/project-create':this.kind==='system'?'/system':'/users';this.data=await api.request(path,this.args());this.form=null}catch(e){this.error=e.message}finally{this.busy=false}},
 async switchSection(section){this.section=section;this.group=null;this.groupKey='';await this.load()},
 edit(row=null){this.form={record:row,login:row?.values.login||'',values:Object.fromEntries((this.data?.edit_fields||[]).map(f=>[f.name,row?.values[f.name]??''])),password:''};delete this.form.values.login},
 async saveUser(){this.busy=true;this.error='';try{const f=this.form,args={...this.args(),key:f.record?.key,revision:f.record?.revision,login:f.login,values:f.values};if(f.password)args.password=f.password;await api.request('/users',args,f.record?'PATCH':'POST');this.form.password='';this.form=null;await this.load();this.notice='Пользователь сохранён исходной моделью Login'}catch(e){this.error=e.message}finally{this.busy=false}},
 async loadGroup(){this.busy=true;this.error='';try{this.group=await api.request('/security',{...this.args(),key:this.groupKey});this.xml=this.group.xml;this.ruleIndex=-1}catch(e){this.error=e.message}finally{this.busy=false}},
 async addGroup(){this.busy=true;this.error='';try{const r=await api.request('/security',{...this.args(),name:this.groupName},'POST');await this.load();this.groupKey=r.key;this.creatingGroup=false;await this.loadGroup()}catch(e){this.error=e.message}finally{this.busy=false}},
 rules(){try{const d=new DOMParser().parseFromString(this.xml,'application/xml');return Array.from(d.documentElement.children).filter(n=>n.tagName==='rule').map(n=>Object.fromEntries(Array.from(n.attributes).map(a=>[a.name,a.value])))}catch{return []}},
 selectRule(index){this.ruleIndex=index;this.ruleProps={...(this.rules()[index]||{})}},
 editRule(remove=false){this.error='';try{const doc=new DOMParser().parseFromString(this.xml,'application/xml');if(doc.querySelector('parsererror')||doc.documentElement.tagName!=='rules')throw Error('Некорректный XML правил');const rules=Array.from(doc.documentElement.children).filter(n=>n.tagName==='rule');let rule=rules[this.ruleIndex];if(remove){if(rule)rule.remove()}else{if(!rule){rule=doc.createElement('rule');doc.documentElement.appendChild(rule)}for(const key of ['group','project','element','search_type','key','code','access']){const value=this.ruleProps[key];if(value===undefined)continue;if(value==='')rule.removeAttribute(key);else rule.setAttribute(key,value)}}this.xml=new XMLSerializer().serializeToString(doc);this.ruleIndex=-1;this.ruleProps={}}catch(e){this.error=e.message}},
 async saveGroup(){this.busy=true;this.error='';try{const r=await api.request('/security',{...this.args(),key:this.groupKey,revision:this.group.revision,xml:this.xml},'PATCH');await this.loadGroup();this.notice=r.notice}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { normalizeClass: _normalizeClass, createElementVNode: _createElementVNode, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, toDisplayString: _toDisplayString, renderList: _renderList, Fragment: _Fragment, vModelText: _vModelText, withDirectives: _withDirectives, createTextVNode: _createTextVNode, withModifiers: _withModifiers, vModelSelect: _vModelSelect, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_ProjectWizard = _resolveComponent("ProjectWizard")

    return (_openBlock(), _createElementBlock("section", { class: "admin-panel" }, [
      (kind==='users')
        ? (_openBlock(), _createElementBlock("div", {
            key: 0,
            class: "toolbar"
          }, [_createElementVNode("button", {
            class: _normalizeClass({primary:section==='users'}),
            onClick: $event => (switchSection('users'))
          }, "Пользователи", 10, ["onClick"]), _createElementVNode("button", {
            class: _normalizeClass({primary:section==='security'}),
            onClick: $event => (switchSection('security'))
          }, "Правила групп", 10, ["onClick"])]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      busy
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "muted"
          }, "Запрос к TACTIC…"))
        : _createCommentVNode("", true),
      (section==='users')
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 4 }, [_createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            class: "primary",
            disabled: busy||!data?.can_write,
            onClick: $event => (edit())
          }, "+ Пользователь", 8, ["disabled", "onClick"]), _createElementVNode("button", { onClick: load }, "Перечитать", 8, ["onClick"]), _createElementVNode("small", null, "Поля списка из manage_user widget_config. Пароли не возвращаются API.")]), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.fields, (f) => {
            return (_openBlock(), _createElementBlock("th", { key: f.name }, _toDisplayString(f.label), 1))
          }), 128)), _createElementVNode("th")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.items, (row) => {
            return (_openBlock(), _createElementBlock("tr", { key: row.key }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.fields, (f) => {
              return (_openBlock(), _createElementBlock("td", { key: f.name }, _toDisplayString(row.values[f.name]), 1))
            }), 128)), _createElementVNode("td", null, [_createElementVNode("button", {
              disabled: !data.can_write,
              onClick: $event => (edit(row))
            }, "Изменить", 8, ["disabled", "onClick"])])]))
          }), 128))])])]), form
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "modal-backdrop"
              }, [_createElementVNode("section", { class: "modal" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, _toDisplayString(form.record?'Изменить пользователя':'Новый пользователь'), 1), _createElementVNode("button", { onClick: $event => (form=null) }, "×", 8, ["onClick"])]), _createElementVNode("form", { onSubmit: _withModifiers(saveUser, ["prevent"]) }, [_createElementVNode("div", { class: "form-scroll" }, [
                _createElementVNode("label", null, [_createTextVNode("Логин"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((form.login) = $event),
                  disabled: !!form.record,
                  required: ""
                }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, form.login]])]),
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.edit_fields, (f) => {
                  return (_openBlock(), _createElementBlock("label", { key: f.name }, [_createTextVNode(_toDisplayString(f.label), 1), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((form.values[f.name]) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, form.values[f.name]]])]))
                }), 128)),
                _createElementVNode("label", null, [_createTextVNode(_toDisplayString(form.record?'Новый пароль (пусто — не менять)':'Начальный пароль'), 1), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((form.password) = $event),
                  type: "password",
                  autocomplete: "new-password",
                  required: !form.record,
                  minlength: "10"
                }, null, 8, ["onUpdate:modelValue", "required"]), [[_vModelText, form.password]])]),
                _createElementVNode("small", null, "Пароль передаётся штатному Login.set_password. Встроенный admin защищён."),
                error
                  ? (_openBlock(), _createElementBlock("p", {
                      key: 0,
                      class: "error"
                    }, _toDisplayString(error), 1))
                  : _createCommentVNode("", true)
              ]), _createElementVNode("footer", null, [_createElementVNode("button", {
                type: "button",
                onClick: $event => (form=null)
              }, "Отмена", 8, ["onClick"]), _createElementVNode("button", {
                class: "primary",
                disabled: busy
              }, "Сохранить", 8, ["disabled"])])], 40, ["onSubmit"])])]))
            : _createCommentVNode("", true)], 64))
        : (section==='security')
          ? (_openBlock(), _createElementBlock(_Fragment, { key: 5 }, [
              _createElementVNode("div", { class: "toolbar" }, [
                _withDirectives(_createElementVNode("select", {
                  "onUpdate:modelValue": $event => ((groupKey) = $event),
                  onChange: loadGroup
                }, [_createElementVNode("option", { value: "" }, "Группа…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.items, (g) => {
                  return (_openBlock(), _createElementBlock("option", {
                    key: g.key,
                    value: g.key
                  }, _toDisplayString(g.name), 9, ["value"]))
                }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, groupKey]]),
                _createElementVNode("button", {
                  disabled: !data?.can_write,
                  onClick: $event => (creatingGroup=!creatingGroup)
                }, "+ Группа", 8, ["disabled", "onClick"]),
                _createElementVNode("span", { class: "spacer" }),
                _createElementVNode("button", {
                  class: "primary",
                  disabled: busy||!group?.can_write||xml===group?.xml,
                  onClick: saveGroup
                }, "Сохранить правила", 8, ["disabled", "onClick"])
              ]),
              creatingGroup
                ? (_openBlock(), _createElementBlock("form", {
                    key: 0,
                    class: "toolbar",
                    onSubmit: _withModifiers(addGroup, ["prevent"])
                  }, [_withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((groupName) = $event),
                    placeholder: "Имя группы",
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, groupName]]), _createElementVNode("button", { disabled: busy }, "Создать", 8, ["disabled"])], 40, ["onSubmit"]))
                : _createCommentVNode("", true),
              _createElementVNode("p", { class: "notice" }, "Настоящие access_rules группы. Правки могут изменить доступ пользователей. Встроенная admin-группа защищена; вычислитель прав остаётся исходным."),
              group
                ? (_openBlock(), _createElementBlock("div", {
                    key: 1,
                    class: "security-editor"
                  }, [_createElementVNode("div", null, [
                    _createElementVNode("h3", null, _toDisplayString(group.name), 1),
                    _createElementVNode("button", {
                      disabled: !group.can_write,
                      onClick: $event => (selectRule(-1))
                    }, "Новое правило", 8, ["disabled", "onClick"]),
                    _createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Group"), _createElementVNode("th", null, "Element / Type"), _createElementVNode("th", null, "Access")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(rules(), (rule, i) => {
                      return (_openBlock(), _createElementBlock("tr", {
                        key: i,
                        onClick: $event => (selectRule(i)),
                        class: _normalizeClass({selected:ruleIndex===i})
                      }, [_createElementVNode("td", null, _toDisplayString(rule.group), 1), _createElementVNode("td", null, _toDisplayString(rule.element||rule.search_type||rule.code||rule.key), 1), _createElementVNode("td", null, _toDisplayString(rule.access), 1)], 10, ["onClick"]))
                    }), 128))])]),
                    _createElementVNode("form", { onSubmit: _withModifiers($event => (editRule()), ["prevent"]) }, [_createElementVNode("div", { class: "two-cols" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['group','project','element','search_type','key','code','access'], (f) => {
                      return (_openBlock(), _createElementBlock("label", { key: f }, [_createTextVNode(_toDisplayString(f), 1), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((ruleProps[f]) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, ruleProps[f]]])]))
                    }), 128))]), _createElementVNode("button", { disabled: !group.can_write }, "Применить правило", 8, ["disabled"]), _createElementVNode("button", {
                      type: "button",
                      disabled: !group.can_write||ruleIndex<0,
                      onClick: $event => (editRule(true))
                    }, "Удалить правило", 8, ["disabled", "onClick"])], 40, ["onSubmit"])
                  ]), _createElementVNode("label", null, [_createTextVNode("XML access_rules"), _withDirectives(_createElementVNode("textarea", {
                    "onUpdate:modelValue": $event => ((xml) = $event),
                    class: "code-input",
                    rows: "28",
                    readonly: !group.can_write,
                    spellcheck: "false"
                  }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, xml]])])]))
                : _createCommentVNode("", true)
            ], 64))
          : (kind==='project-create')
            ? (_openBlock(), _createBlock(_component_ProjectWizard, {
                key: 6,
                project: project,
                target: target,
                onDirty: $event => ($emit('dirty',$event)),
                onChanged: $event => ($emit('changed',$event))
              }, null, 8, ["project", "target", "onDirty", "onChanged"]))
            : (kind==='system')
              ? (_openBlock(), _createElementBlock("div", {
                  key: 7,
                  class: "system-panel"
                }, [
                  _createElementVNode("div", {
                    class: "widget-toolbar",
                    role: "group",
                    "aria-label": "Диагностика сервера"
                  }, [_createElementVNode("button", {
                    disabled: busy,
                    onClick: load
                  }, "Проверить снова", 8, ["disabled", "onClick"])]),
                  _createElementVNode("dl", { class: "system-summary" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data, (value, key) => {
                    return (_openBlock(), _createElementBlock(_Fragment, { key: key }, [(key!=='schema'&&key!=='notes'&&key!=='cluster')
                      ? (_openBlock(), _createElementBlock("div", {
                          key: 0,
                          class: "system-fact"
                        }, [_createElementVNode("dt", null, _toDisplayString(systemLabel(key)), 1), _createElementVNode("dd", null, _toDisplayString(typeof value==='boolean'?(value?'Да':'Нет'):value), 1)]))
                      : _createCommentVNode("", true)], 64))
                  }), 128))]),
                  (data?.cluster?.enabled)
                    ? (_openBlock(), _createElementBlock("section", {
                        key: 0,
                        class: "cluster-status",
                        "aria-label": "Рабочие процессы TACTIC"
                      }, [
                        _createElementVNode("header", { class: "toolbar" }, [
                          _createElementVNode("h3", null, "Рабочие процессы"),
                          _createElementVNode("span", { class: "cluster-state" }, _toDisplayString(({running:"Работает",starting:"Запуск",degraded:"Частично доступно",failed:"Ошибка",stopped:"Остановлено"})[data.cluster.state]||data.cluster.state), 1),
                          _createElementVNode("span", { class: "spacer" }),
                          _createElementVNode("small", null, "Ответил процесс " + _toDisplayString(data.cluster.current_worker), 1)
                        ]),
                        _createElementVNode("p", { class: "muted" }, "Чтение распределяется между доступными процессами. Вход, изменения и legacy API обслуживает ведущий процесс. Запись после обрыва не повторяется автоматически."),
                        _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                          _createElementVNode("th", null, "Процесс"),
                          _createElementVNode("th", null, "PID"),
                          _createElementVNode("th", null, "Роль"),
                          _createElementVNode("th", null, "Состояние"),
                          _createElementVNode("th", null, "Запросы"),
                          _createElementVNode("th", null, "Сейчас"),
                          _createElementVNode("th", null, "Перезапуски")
                        ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.cluster.workers, (w) => {
                          return (_openBlock(), _createElementBlock("tr", { key: w.id }, [
                            _createElementVNode("td", null, _toDisplayString(w.id), 1),
                            _createElementVNode("td", null, _toDisplayString(w.pid), 1),
                            _createElementVNode("td", null, _toDisplayString(w.role==='writer'?'Ведущий / чтение и запись':'Чтение'), 1),
                            _createElementVNode("td", null, [_createElementVNode("span", {
                              class: "cluster-health",
                              "data-state": w.healthy?'up':'down'
                            }, _toDisplayString(w.healthy?'Доступен':'Недоступен'), 9, ["data-state"])]),
                            _createElementVNode("td", null, _toDisplayString(w.requests), 1),
                            _createElementVNode("td", null, _toDisplayString(w.active), 1),
                            _createElementVNode("td", null, _toDisplayString(w.restarts), 1)
                          ]))
                        }), 128))])])]),
                        _createElementVNode("small", { class: "muted" }, "Обновлено: " + _toDisplayString(data.cluster.updated_at) + ". Это состояние процессов, не проверка целостности базы. Для offline-обновления необходимо остановить всю группу.", 1)
                      ]))
                    : _createCommentVNode("", true),
                  _createElementVNode("div", { class: "system-notes" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data?.notes, (note, i) => {
                    return (_openBlock(), _createElementBlock("p", {
                      key: i,
                      class: "muted"
                    }, _toDisplayString(note), 1))
                  }), 128))]),
                  (data?.schema)
                    ? (_openBlock(), _createElementBlock("section", {
                        key: 1,
                        class: "schema-health",
                        "aria-label": "Проверка схемы базы"
                      }, [
                        _createElementVNode("header", null, [_createElementVNode("h3", null, "Структура базы TACTIC"), _createElementVNode("strong", { class: _normalizeClass(data.schema.ready?'success':'error') }, _toDisplayString(data.schema.ready?'Обязательная структура найдена':'Требуется проверка схемы'), 3)]),
                        _createElementVNode("p", { class: "muted" }, _toDisplayString(data.schema.notice), 1),
                        _createElementVNode("p", { class: "notice" }, _toDisplayString(data.schema.upgrade_notice), 1),
                        (data.schema.error)
                          ? (_openBlock(), _createElementBlock("p", {
                              key: 0,
                              class: "error"
                            }, _toDisplayString(data.schema.error), 1))
                          : _createCommentVNode("", true),
                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.schema.databases, (db) => {
                          return (_openBlock(), _createElementBlock("section", {
                            key: db.project,
                            class: "schema-database"
                          }, [_createElementVNode("div", { class: "toolbar" }, [
                            _createElementVNode("h4", null, _toDisplayString(db.project), 1),
                            _createElementVNode("span", { class: "pill" }, _toDisplayString(db.vendor||'Метаданные недоступны'), 1),
                            _createElementVNode("span", { class: "spacer" }),
                            _createElementVNode("span", null, _toDisplayString(db.checked_tables||0) + " таблиц проверено", 1)
                          ]), (db.error)
                            ? (_openBlock(), _createElementBlock("p", {
                                key: 0,
                                class: "error"
                              }, _toDisplayString(db.notice), 1))
                            : _createCommentVNode("", true), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", { class: "schema-check-table" }, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Исходная таблица / SearchType"), _createElementVNode("th", null, "Состояние"), _createElementVNode("th", null, "Отсутствующие поля")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(db.checks, (check, i) => {
                            return (_openBlock(), _createElementBlock("tr", {
                              key: i,
                              "data-schema-state": check.state
                            }, [_createElementVNode("td", null, [_createElementVNode("code", null, _toDisplayString(check.table||check.search_type), 1)]), _createElementVNode("td", { class: _normalizeClass(check.state==='ok'?'muted':'error') }, _toDisplayString(({ok:'Найдена',missing_columns:'Нет полей',missing_table:'Нет таблицы',missing_registration:'Нет регистрации'})[check.state]||check.state), 3), _createElementVNode("td", null, _toDisplayString(check.missing_columns?.join(', ')||'—'), 1)], 8, ["data-schema-state"]))
                          }), 128))])])])]))
                        }), 128)),
                        _createElementVNode("p", { class: "muted" }, "Только чтение метаданных. Проверка не создаёт таблицы, не запускает миграции и не меняет widget_config.")
                      ]))
                    : _createCommentVNode("", true)
                ]))
              : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const GlobalSettings = (function(){

const __component = {
 name:'GlobalSettings',props:{project:String,target:String,kind:String},emits:['dirty'],
 data(){return {record:null,changes:{},xml:'',error:'',notice:'',busy:false,seq:0}},
 computed:{dirty(){return Object.keys(this.changes).length>0||Boolean(this.xml)},endpoint(){return this.kind==='license'?'/license':'/system-config'}},
 watch:{dirty(v){this.$emit('dirty',v)},target(){this.load()}},mounted(){this.load()},beforeUnmount(){this.seq++},
 methods:{args(){return {project:this.project,target:this.target}},
 async load(){if(this.dirty&&!confirm('Отменить несохранённые изменения?'))return;const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request(this.endpoint,this.args());if(seq===this.seq){this.record=d;this.changes={};this.xml=''}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 value(f){return Object.hasOwn(this.changes,f.name)?this.changes[f.name]:f.value},
 change(f,value){if(value===f.value)delete this.changes[f.name];else this.changes[f.name]=value},
 async choose(e){const file=e.target.files?.[0];if(!file)return;if(file.size>256*1024){this.error='Лицензия должна быть не больше 256 КиБ';return}this.xml=await file.text()},
 async save(){if(!this.record?.can_write||this.busy)return;if(!confirm(this.kind==='license'?'Заменить лицензию после проверки подписи TACTIC?':'Сохранить конфигурацию сервера с резервной копией? После сохранения потребуется ручной перезапуск.'))return;this.busy=true;this.error='';try{const data={...this.args(),revision:this.record.revision};if(this.kind==='license'){data.xml=this.xml;data.confirm='RENEW_LICENSE'}else{data.changes=this.changes;data.confirm='SAVE_SYSTEM_CONFIG'}const r=await api.request(this.endpoint,data,this.kind==='license'?'POST':'PATCH');this.changes={};this.xml='';await this.load();this.notice=r.notice||'Сохранено'}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, renderList: _renderList, Fragment: _Fragment, createTextVNode: _createTextVNode } = _Vue

    return (_openBlock(), _createElementBlock("section", {
      class: "global-settings",
      "aria-label": kind==='license'?'License Manager':'System Configuration'
    }, [
      _createElementVNode("header", {
        class: "widget-toolbar",
        role: "group",
        "aria-label": "Действия с настройками"
      }, [_createElementVNode("button", {
        onClick: load,
        disabled: busy
      }, "Обновить", 8, ["onClick", "disabled"]), _createElementVNode("button", {
        class: "primary",
        disabled: busy||!record?.can_write||!dirty,
        onClick: save
      }, _toDisplayString(busy?'Обработка…':'Сохранить'), 9, ["disabled", "onClick"])]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "notice"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      (record&&!record.can_write)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, "Режим чтения. Для изменения запустите MANAGE_TACTIC.bat configure --writes on на сервере и перезапустите TACTIC."))
        : _createCommentVNode("", true),
      (record&&kind==='system-config')
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 3 }, [_createElementVNode("p", { class: "notice" }, _toDisplayString(record.notice), 1), _createElementVNode("div", { class: "global-settings-grid" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record.groups, (g) => {
            return (_openBlock(), _createElementBlock("fieldset", { key: g.title }, [_createElementVNode("legend", null, _toDisplayString(g.title), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(g.fields, (f) => {
              return (_openBlock(), _createElementBlock("div", {
                key: f.name,
                class: "system-field"
              }, [_createElementVNode("label", { for: 'setting-'+f.name }, [_createTextVNode(_toDisplayString(f.label), 1), _createElementVNode("small", null, _toDisplayString(f.name), 1)], 8, ["for"]), (f.choices.length)
                ? (_openBlock(), _createElementBlock("select", {
                    key: 0,
                    id: 'setting-'+f.name,
                    disabled: !record.can_write,
                    value: value(f),
                    onChange: $event => (change(f,$event.target.value))
                  }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(f.choices, (o) => {
                    return (_openBlock(), _createElementBlock("option", {
                      value: o,
                      key: o
                    }, _toDisplayString(o), 9, ["value"]))
                  }), 128))], 40, ["id", "disabled", "value", "onChange"]))
                : (f.kind==='boolean')
                  ? (_openBlock(), _createElementBlock("select", {
                      key: 1,
                      id: 'setting-'+f.name,
                      disabled: !record.can_write,
                      value: value(f),
                      onChange: $event => (change(f,$event.target.value))
                    }, [_createElementVNode("option", { value: "" }, "По умолчанию"), _createElementVNode("option", { value: "true" }, "true"), _createElementVNode("option", { value: "false" }, "false")], 40, ["id", "disabled", "value", "onChange"]))
                  : (_openBlock(), _createElementBlock("input", {
                      key: 2,
                      id: 'setting-'+f.name,
                      disabled: !record.can_write,
                      type: f.secret?'password':f.kind==='integer'?'number':'text',
                      autocomplete: f.secret?'new-password':undefined,
                      value: value(f),
                      placeholder: f.secret&&f.configured?'Настроено; пустое поле не меняет секрет':'',
                      onInput: $event => (change(f,$event.target.value))
                    }, null, 40, ["id", "disabled", "type", "autocomplete", "value", "placeholder", "onInput"]))]))
            }), 128))]))
          }), 128))])], 64))
        : _createCommentVNode("", true),
      (record&&kind==='license')
        ? (_openBlock(), _createElementBlock(_Fragment, { key: 4 }, [(record.message)
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "warning-text"
              }, _toDisplayString(record.message), 1))
            : _createCommentVNode("", true), _createElementVNode("dl", { class: "license-info" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(record.info, (v, k) => {
            return (_openBlock(), _createElementBlock(_Fragment, { key: k }, [_createElementVNode("dt", null, _toDisplayString(k), 1), _createElementVNode("dd", null, _toDisplayString(v===null||v===''?'—':v), 1)], 64))
          }), 128)), _createElementVNode("dt", null, "Проверка TACTIC"), _createElementVNode("dd", null, _toDisplayString(record.licensed?'Лицензия подтверждена':'Нет подтверждённой лицензии'), 1)]), _createElementVNode("fieldset", null, [
            _createElementVNode("legend", null, "Renew License"),
            _createElementVNode("p", null, "Проверка подписи выполняется исходным License. Только после неё RenewLicenseCbk заменяет файл."),
            _createElementVNode("input", {
              type: "file",
              accept: ".xml,text/xml,application/xml",
              disabled: !record.can_write||busy,
              onChange: choose
            }, null, 40, ["disabled", "onChange"]),
            xml
              ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Файл выбран: " + _toDisplayString(xml.length) + " символов. Содержимое не выполняется и не выводится как HTML.", 1))
              : _createCommentVNode("", true)
          ])], 64))
        : _createCommentVNode("", true)
    ], 8, ["aria-label"]))
  }
};
return __component;
})();
const EmbeddedForm = (function(){


const __component = {
 name:'EmbeddedForm',components:{ConfiguredForm},props:{project:String,target:String,refreshKey:Number},emits:['close','dirty','changed'],
 data(){return {form:null,busy:false,error:'',success:'',generation:0,formKey:0,dirty:false,previewBusy:false,previewFailed:false}},
 mounted(){this.load()},beforeUnmount(){this.generation++},watch:{refreshKey(){if(!this.dirty||confirm('Обновить форму и отменить правки?'))this.load()}},
 methods:{
 async load(){const seq=++this.generation;this.busy=true;this.error='';try{const d=await api.request('/embedded-form',{project:this.project,target:this.target});if(seq===this.generation){this.form=d;this.formKey++;this.dirty=false;this.$emit('dirty',false)}}catch(e){if(seq===this.generation)this.error=e.message}finally{if(seq===this.generation)this.busy=false}},
 async save(values){if(this.busy||this.previewBusy||this.previewFailed)return;this.busy=true;this.error='';try{const result=await api.request('/embedded-form',{project:this.project,target:this.target,key:this.form.record?.key,revision:this.form.record?.revision,values},this.form.record?'PATCH':'POST');this.success='Сохранено: '+result.key;this.dirty=false;this.$emit('dirty',false);this.$emit('changed',result);if(this.form.widget?.single&&!this.form.record)this.$emit('close');else await this.load()}catch(e){this.error=e.message}finally{this.busy=false}},
 async preview(values){const seq=++this.generation;this.previewBusy=true;this.previewFailed=false;this.error='';try{const d=await api.request('/form-preview',{project:this.project,target:this.target,key:this.form.record?.key,revision:this.form.record?.revision,values},'POST');if(seq===this.generation)this.form={...d,widget:this.form.widget}}catch(e){if(seq===this.generation){this.error=e.message;this.previewFailed=true}}finally{if(seq===this.generation)this.previewBusy=false}},
 mark(value){this.dirty=value;this.$emit('dirty',value)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, resolveComponent: _resolveComponent, createBlock: _createBlock } = _Vue

    const _component_ConfiguredForm = _resolveComponent("ConfiguredForm")

    return (_openBlock(), _createElementBlock("section", { class: "embedded-widget" }, [
      success
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "notice"
          }, _toDisplayString(success), 1))
        : _createCommentVNode("", true),
      (!form&&busy)
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "muted"
          }, "Загрузка EditWdg…"))
        : _createCommentVNode("", true),
      (!form&&error)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      form
        ? (_openBlock(), _createBlock(_component_ConfiguredForm, {
            key: formKey,
            project: project,
            target: target,
            form: form,
            busy: busy||previewBusy||previewFailed,
            error: error,
            embedded: "",
            onDirty: mark,
            onPreview: preview,
            onSave: save,
            onClose: $event => ($emit('close'))
          }, null, 8, ["project", "target", "form", "busy", "error", "onDirty", "onPreview", "onSave", "onClose"]))
        : _createCommentVNode("", true)
    ]))
  }
};
return __component;
})();
const WidgetTable = (function(){












const __component = {
 name:'WidgetTable',components:{ConfiguredTable,ConfiguredForm,RecordInspector,AdvancedFilter,CsvExport,ConfigAudit,TaskTimeline,CollectionPanel,RelationTree,ViewDesigner},
 props:{project:String,screen:Object,user:Object,refreshKey:Number},emits:['open','dirty','changed','refresh'],
 data(){return {stateReady:false,stateSeq:0,rows:[],summaries:[],offset:0,limit:this.screen.spec?.table_options?.page_size||50,total:null,where:{op:'and',children:[]},sort:null,state:'active',mode:'data',error:'',busy:false,seq:0,selected:[],form:null,formError:'',saving:false,formKey:0,formSeq:0,previewBusy:false,previewFailed:false,inspected:null,exporting:false,audit:false,designer:false,dirty:false,searchOpen:false,quickField:'',quickText:'',filters:[]}},
 computed:{filterCount(){const count=n=>n?.children?n.children.reduce((v,c)=>v+count(c),0):n?.field?1:0;return count(this.where)+this.filters.length},query(){return {where:this.where,filters:this.filters,sort:this.sort||undefined,record_state:this.state}},spec(){return this.screen.spec}},
 mounted(){this.restoreState()},beforeUnmount(){this.seq++;this.formSeq++;this.stateSeq++},watch:{refreshKey(){this.load()},screen(){this.restoreState()},mode(){this.saveState()},searchOpen(){this.saveState()},quickField(){this.saveState()},quickText(){this.saveState()}},
 methods:{
  async restoreState(){const seq=++this.stateSeq,args=this.args(),current=()=>seq===this.stateSeq&&args.project===this.project&&args.target===this.screen.id;this.seq++;this.stateReady=false;try{const r=await uiState.load({...args,scope:'query'});if(!current())return;if(r.value){const q=r.value;Object.assign(this,{filters:q.filters,where:q.where,sort:q.sort,state:q.record_state,offset:q.offset,limit:q.limit,mode:q.presentation,searchOpen:q.search_open,quickField:q.quickField,quickText:q.quickText})}await this.$nextTick();if(!current())return;this.stateReady=true}catch(e){if(!current())return;this.error='Не удалось восстановить настройки: '+e.message}if(current())await this.load()},
  saveState(){if(this.stateReady&&this.user?.allow_writes)uiState.schedule({...this.args(),scope:'query'},{filters:this.filters,where:this.where,sort:this.sort,record_state:this.state,offset:this.offset,limit:this.limit,presentation:this.mode,search_open:this.searchOpen,quickField:this.quickField,quickText:this.quickText,quickOp:'contains'})},
  tableAction({id,value}){
   if(id==='create')this.edit(null);else if(id==='refresh')this.load();
   else if(id==='search')this.searchOpen=!this.searchOpen;
   else if(id==='bulk')this.bulk();else if(id==='export')this.exporting=true;
   else if(id==='designer')this.designer=true;else if(id==='audit')this.audit=true;
   else if(id==='save-view')this.saveSearch();else if(id==='mode')this.mode=value;
   else if(id==='state'){this.state=value;this.offset=0;this.load()}
  },
  quickSearch(){if(!this.quickField||!this.quickText.trim())return;this.filters=[{field:this.quickField,op:'contains',value:this.quickText}];this.offset=0;this.load()},
  clearQuickSearch(){this.filters=[];this.quickText='';this.offset=0;this.load()},
  args(){return {project:this.project,target:this.screen.id}},
  async load(){const seq=++this.seq,args=this.args(),current=()=>seq===this.seq&&args.project===this.project&&args.target===this.screen.id;this.busy=true;this.error='';try{const d=await api.request('/query',{...args,...this.query,offset:this.offset,limit:this.limit},'POST');if(current()){this.rows=d.items;this.summaries=d.summaries||[];this.total=d.total;this.saveState()}}catch(e){if(current())this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
  apply(where){this.where=where;this.offset=0;this.load()},page(offset){this.offset=offset;this.load()},
  order(field){this.sort=typeof field==='object'?field:{field,direction:this.sort?.field===field&&this.sort.direction==='asc'?'desc':'asc'};this.offset=0;this.load()},
  async edit(row){this.error='';this.formError='';this.previewFailed=false;try{this.form=await api.request('/form',{...this.args(),key:row?.key});this.formKey++}catch(e){this.error=e.message}},
  inspect(row){this.inspected=row},
  async preview(values){const seq=++this.formSeq;this.previewBusy=true;this.previewFailed=false;try{const f=await api.request('/form-preview',{...this.args(),key:this.form.record?.key,revision:this.form.record?.revision,values},'POST');if(seq===this.formSeq)this.form=f}catch(e){if(seq===this.formSeq){this.formError=e.message;this.previewFailed=true}}finally{if(seq===this.formSeq)this.previewBusy=false}},
  async save(values){if(this.previewFailed||this.previewBusy||this.saving)return;this.saving=true;this.formError='';try{if(this.form.records)await api.request('/bulk-records',{...this.args(),records:this.form.records.map(r=>({key:r.key,revision:r.revision,values}))},'PATCH');else await api.request('/record',{...this.args(),key:this.form.record?.key,revision:this.form.record?.revision,values},this.form.record?'PATCH':'POST');this.form=null;this.dirty=false;this.$emit('dirty',false);await this.load()}catch(e){this.formError=e.message}finally{this.saving=false}},
  async bulk(){if(!this.selected.length||this.selected.length>100)return;this.error='';try{const forms=[];for(const key of this.selected)forms.push(await api.request('/form',{...this.args(),key}));const fields=forms[0].spec.fields.filter(f=>!f.read_only&&forms.every(x=>x.spec.fields.some(g=>g.name===f.name&&!g.read_only&&g.kind===f.kind))).map(f=>({...f,options:(f.options||[]).filter(o=>forms.every(x=>x.spec.fields.find(g=>g.name===f.name).options?.some(v=>String(v.value)===String(o.value))))}));this.form={spec:{...forms[0].spec,fields},records:forms.map(f=>f.record),record:null,bulk:true};this.formKey++}catch(e){this.error=e.message}},
  async saveSearch(){const title=prompt('Название поиска в My Views');if(!title)return;try{await api.request('/saved-view',{...this.args(),...this.query,title},'POST');this.$emit('changed')}catch(e){this.error=e.message}},
  async dates(change){try{const form=await api.request('/form',{...this.args(),key:change.row.key});if(form.record.revision!==change.row.revision)throw Error('Запись изменилась; обновите период');const values={};for(const name of [change.startField,change.endField]){const f=form.spec.fields.find(f=>f.name===name);if(!f||f.read_only)throw Error('Дата недоступна для изменения');const m=/^(\d{4}-\d{2}-\d{2})(.*)$/.exec(String(form.record.values[name]));if(!m)throw Error('Некорректная дата');const d=new Date(m[1]+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+change.delta);values[name]=d.toISOString().slice(0,10)+(f.kind==='date'?'':m[2]||'T00:00:00')}await api.request('/record',{...this.args(),key:change.row.key,revision:form.record.revision,values},'PATCH');await this.load()}catch(e){this.error=e.message}},
  mark(value){this.dirty=value;this.$emit('dirty',value)}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, vModelText: _vModelText, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createBlock: _createBlock, withCtx: _withCtx, createVNode: _createVNode } = _Vue

    const _component_AdvancedFilter = _resolveComponent("AdvancedFilter")
    const _component_RelationTree = _resolveComponent("RelationTree")
    const _component_TaskTimeline = _resolveComponent("TaskTimeline")
    const _component_CollectionPanel = _resolveComponent("CollectionPanel")
    const _component_ConfiguredTable = _resolveComponent("ConfiguredTable")
    const _component_RecordInspector = _resolveComponent("RecordInspector")
    const _component_ConfiguredForm = _resolveComponent("ConfiguredForm")
    const _component_ConfigAudit = _resolveComponent("ConfigAudit")
    const _component_CsvExport = _resolveComponent("CsvExport")
    const _component_ViewDesigner = _resolveComponent("ViewDesigner")

    return (_openBlock(), _createElementBlock("section", {
      class: "widget-table",
      "aria-label": screen.title,
      "data-widget-target": screen.id
    }, [
      _createVNode(_component_ConfiguredTable, {
        project: project,
        target: screen.id,
        spec: spec,
        rows: rows,
        summaries: summaries,
        busy: busy,
        total: total,
        offset: offset,
        limit: limit,
        presentation: mode,
        "record-state": state,
        "allow-writes": user.allow_writes,
        "filter-count": filterCount,
        "search-open": searchOpen,
        onTableAction: tableAction,
        onInspect: inspect,
        onEdit: edit,
        onSort: order,
        onPage: page,
        onSelection: $event => (selected=$event),
        onEditSelected: bulk,
        onDirty: mark,
        onChanged: load,
        onOpen: $event => ($emit('open',$event)),
        onViewChanged: $event => ($emit('refresh'))
      }, {
        filters: _withCtx(() => [_createElementVNode("div", { class: "table-search-heading" }, [_createElementVNode("strong", null, "Поиск в представлении"), _createElementVNode("button", {
          class: "text-button",
          "aria-label": "Свернуть поиск",
          onClick: $event => (searchOpen=false)
        }, "×", 8, ["onClick"])]), (spec.table_options?.show_keyword_search!==false)
          ? (_openBlock(), _createElementBlock("form", {
              key: 0,
              class: "table-quick-search",
              onSubmit: _withModifiers(quickSearch, ["prevent"])
            }, [
              _withDirectives(_createElementVNode("select", {
                "onUpdate:modelValue": $event => ((quickField) = $event),
                "aria-label": "Поле поиска"
              }, [_createElementVNode("option", { value: "" }, "Поле…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(spec.fields.filter(f=>f.storage&&['text','textarea'].includes(f.kind)), (f) => {
                return (_openBlock(), _createElementBlock("option", {
                  key: f.name,
                  value: f.name
                }, _toDisplayString(f.label), 9, ["value"]))
              }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, quickField]]),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((quickText) = $event),
                placeholder: "Значение…",
                "aria-label": "Значение поиска"
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, quickText]]),
              _createElementVNode("button", {
                disabled: !quickField||!quickText.trim()||busy,
                class: "primary"
              }, "Найти", 8, ["disabled"]),
              (filters.length)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    type: "button",
                    onClick: clearQuickSearch
                  }, "Сбросить", 8, ["onClick"]))
                : _createCommentVNode("", true)
            ], 40, ["onSubmit"]))
          : _createCommentVNode("", true), (spec.table_options?.show_search!==false)
          ? (_openBlock(), _createBlock(_component_AdvancedFilter, {
              key: 1,
              value: where,
              fields: spec.fields,
              "base-filter": screen.options?.filter,
              onApply: apply
            }, null, 8, ["value", "fields", "base-filter", "onApply"]))
          : _createCommentVNode("", true)]),
        status: _withCtx(() => [(spec.write_notice)
          ? (_openBlock(), _createElementBlock("p", {
              key: 0,
              class: "notice write-mode-notice"
            }, _toDisplayString(spec.write_notice), 1))
          : _createCommentVNode("", true), error
          ? (_openBlock(), _createElementBlock("p", {
              key: 1,
              class: "error"
            }, _toDisplayString(error), 1))
          : _createCommentVNode("", true)]),
        alternate: _withCtx(() => [(mode==='tree')
          ? (_openBlock(), _createBlock(_component_RelationTree, {
              key: 0,
              project: project,
              target: screen.id,
              spec: spec,
              rows: rows,
              summaries: summaries,
              busy: busy,
              total: total,
              offset: offset,
              limit: limit,
              onOpen: $event => ($emit('open',$event)),
              onInspect: $event => ($emit('open',{id:$event.target})),
              onPage: page
            }, null, 8, ["project", "target", "spec", "rows", "summaries", "busy", "total", "offset", "limit", "onOpen", "onInspect", "onPage"]))
          : (mode==='timeline')
            ? (_openBlock(), _createBlock(_component_TaskTimeline, {
                key: 1,
                project: project,
                target: screen.id,
                spec: spec,
                query: query,
                "refresh-key": seq,
                onEdit: edit,
                onInspect: inspect,
                onDates: dates
              }, null, 8, ["project", "target", "spec", "query", "refresh-key", "onEdit", "onInspect", "onDates"]))
            : (mode==='collections')
              ? (_openBlock(), _createBlock(_component_CollectionPanel, {
                  key: 2,
                  project: project,
                  target: screen.id,
                  "selected-keys": selected,
                  onOpen: $event => ($emit('open',$event)),
                  onChanged: load
                }, null, 8, ["project", "target", "selected-keys", "onOpen", "onChanged"]))
              : _createCommentVNode("", true)]),
        _: 1
      }, 8, ["project", "target", "spec", "rows", "summaries", "busy", "total", "offset", "limit", "presentation", "record-state", "allow-writes", "filter-count", "search-open", "onTableAction", "onInspect", "onEdit", "onSort", "onPage", "onSelection", "onEditSelected", "onDirty", "onChanged", "onOpen", "onViewChanged"]),
      inspected
        ? (_openBlock(), _createBlock(_component_RecordInspector, {
            key: inspected.key+':'+(inspected._section||'fields'),
            project: project,
            target: screen.id,
            record: inspected,
            spec: spec,
            "allow-uploads": user.allow_uploads,
            onClose: $event => (inspected=null),
            onEdit: edit,
            onOpen: $event => ($emit('open',$event)),
            onChanged: load
          }, null, 8, ["project", "target", "record", "spec", "allow-uploads", "onClose", "onEdit", "onOpen", "onChanged"]))
        : _createCommentVNode("", true),
      form
        ? (_openBlock(), _createBlock(_component_ConfiguredForm, {
            key: formKey,
            project: project,
            target: screen.id,
            form: form,
            busy: saving||previewBusy||previewFailed,
            error: formError,
            onPreview: preview,
            onDirty: mark,
            onSave: save,
            onClose: $event => {form=null;mark(false)}
          }, null, 8, ["project", "target", "form", "busy", "error", "onPreview", "onDirty", "onSave", "onClose"]))
        : _createCommentVNode("", true),
      audit
        ? (_openBlock(), _createBlock(_component_ConfigAudit, {
            key: 2,
            project: project,
            target: screen.id,
            onClose: $event => (audit=false)
          }, null, 8, ["project", "target", "onClose"]))
        : _createCommentVNode("", true),
      exporting
        ? (_openBlock(), _createBlock(_component_CsvExport, {
            key: 3,
            project: project,
            target: screen.id,
            spec: spec,
            query: query,
            "selected-keys": selected,
            onClose: $event => (exporting=false)
          }, null, 8, ["project", "target", "spec", "query", "selected-keys", "onClose"]))
        : _createCommentVNode("", true),
      designer
        ? (_openBlock(), _createBlock(_component_ViewDesigner, {
            key: 4,
            project: project,
            "search-type": spec.type,
            "initial-view": spec.view,
            login: user.login,
            onClose: $event => (designer=false),
            onSaved: $event => {$emit('refresh');$emit('changed')}
          }, null, 8, ["project", "search-type", "initial-view", "login", "onClose", "onSaved"]))
        : _createCommentVNode("", true)
    ], 8, ["aria-label", "data-widget-target"]))
  }
};
return __component;
})();
const ConfiguredTabs = (function(){




const __component = {
 name:'ConfiguredTabs',components:{ContextMenu,WidgetDefinition},props:{project:String,screen:Object,user:Object,active:{type:Boolean,default:true},refreshKey:Number},emits:['open','close','dirty','changed'],
 data(){return {stateReady:false,stateSeq:0,children:[],selected:'',loaded:[],closed:[],dirty:{},titles:{},refreshes:{},menu:null,menuSeq:0,definition:null,error:'',dragged:null}},
 computed:{visible(){return this.children.filter(c=>!this.closed.includes(c.id))}},
 created(){this.restoreState()},watch:{screen(){this.restoreState()},refreshKey(){this.restoreState()},selected(){this.saveState()},closed:{deep:true,handler(){this.saveState()}},titles:{deep:true,handler(){this.saveState()}},children(){this.saveState()}},beforeUnmount(){this.stateSeq++;this.menuSeq++},
 methods:{
 async restoreState(){this.stateReady=false;const seq=++this.stateSeq;this.initialize();try{const result=await uiState.load({project:this.project,target:this.screen.id,scope:'tabs'});if(seq!==this.stateSeq)return;const p=result.value;if(p){const byName=new Map(this.children.map(c=>[c.name,c]));const order=[...p.order,...this.children.map(c=>c.name).filter(n=>!p.order.includes(n))];this.children=order.map(n=>byName.get(n)).filter(Boolean);this.closed=p.closed.map(n=>byName.get(n)?.id).filter(Boolean);this.titles=Object.fromEntries(Object.entries(p.titles).filter(([n])=>byName.has(n)).map(([n,v])=>[byName.get(n).id,v]));const child=byName.get(p.selected)||this.visible[0];if(child)this.choose(child)}await this.$nextTick();if(seq===this.stateSeq)this.stateReady=true}catch(e){this.error='Настройки вкладок: '+e.message}},
 saveState(){if(!this.stateReady||!this.user?.allow_writes)return;const byId=new Map(this.children.map(c=>[c.id,c.name]));uiState.schedule({project:this.project,target:this.screen.id,scope:'tabs'},{order:this.children.map(c=>c.name),closed:this.closed.map(id=>byId.get(id)).filter(Boolean),selected:byId.get(this.selected)||'',titles:Object.fromEntries(Object.entries(this.titles).filter(([id])=>byId.has(id)).map(([id,v])=>[byId.get(id),v]))})},
 initialize(){const list=this.screen.children||[];const ids=list.map(c=>c.id);this.children=list;this.closed=this.closed.filter(id=>ids.includes(id));this.loaded=this.loaded.filter(id=>ids.includes(id));for(const c of list)if(c.preload&&!this.loaded.includes(c.id))this.loaded.push(c.id);if(!this.visible.some(c=>c.id===this.selected))this.selected=this.visible.find(c=>c.selected)?.id||this.screen.container?.selected||this.visible[0]?.id||'';if(this.selected&&!this.loaded.includes(this.selected))this.loaded.push(this.selected)},
 choose(child){if(this.stateReady)api.action?.('tab.select',{project:this.project,target:child.id});this.selected=child.id;if(!this.loaded.includes(child.id))this.loaded.push(child.id)},
 mark(id,value){this.dirty[id]=value;this.$emit('dirty',Object.values(this.dirty).some(Boolean))},
 closeChild(child){if(!child.removable)return;if(this.dirty[child.id]&&!confirm('Закрыть вкладку без сохранения?'))return;this.closed.push(child.id);this.loaded=this.loaded.filter(id=>id!==child.id);this.mark(child.id,false);if(this.selected===child.id)this.choose(this.visible[0]||{id:''})},
 reopen(){this.closed=[];if(!this.selected&&this.visible[0])this.choose(this.visible[0])},
 async context(e,child){if(e.shiftKey||this.screen.container?.show_context_menu===false)return;e.preventDefault();e.stopPropagation();const seq=++this.menuSeq;const rect=e.currentTarget.getBoundingClientRect();this.menu={x:e.clientX||rect.left,y:e.clientY||rect.bottom,title:this.titles[child.id]||child.title,loading:true,items:[],child};try{const d=await api.request('/context-menu',{project:this.project,target:child.id,scope:'tab'});if(seq===this.menuSeq&&this.menu)this.menu={...this.menu,...d,loading:false}}catch(err){if(seq===this.menuSeq&&this.menu)this.menu={...this.menu,loading:false,error:err.message}}},
 key(e,child){if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){e.preventDefault();this.context({preventDefault(){},stopPropagation(){},currentTarget:e.currentTarget},child);return}if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const i=this.visible.indexOf(child);const n=e.key==='Home'?0:e.key==='End'?this.visible.length-1:(i+(e.key==='ArrowRight'?1:-1)+this.visible.length)%this.visible.length;this.choose(this.visible[n]);this.$nextTick(()=>this.$refs.strip?.querySelectorAll('[role="tab"]')[n]?.focus())}},
 act(item){const child=this.menu.child;this.menu=null;this.menuSeq++;if(item.id==='close')this.closeChild(child);else if(item.id==='close_others'){for(const c of [...this.visible])if(c.id!==child.id)this.closeChild(c);this.choose(child)}else if(item.id==='open_main')this.$emit('open',child);else if(item.id==='definition')this.definition=child.id;else if(item.id==='rename'){const name=prompt('Название вкладки в открытом контейнере',this.titles[child.id]||child.title);if(name?.trim())this.titles[child.id]=name.trim()}else if(item.id==='refresh'){if(this.dirty[child.id]&&!confirm('Обновить вкладку без сохранения?'))return;this.refreshes[child.id]=(this.refreshes[child.id]||0)+1;this.mark(child.id,false)}},
 drop(child){if(!this.dragged||this.screen.container?.allow_drag===false)return;const list=[...this.children],a=list.findIndex(c=>c.id===this.dragged),b=list.findIndex(c=>c.id===child.id);if(a>=0&&b>=0){const [moving]=list.splice(a,1);list.splice(b,0,moving);this.children=list}this.dragged=null}
 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, createCommentVNode: _createCommentVNode, createTextVNode: _createTextVNode, normalizeClass: _normalizeClass, createElementVNode: _createElementVNode, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createBlock: _createBlock, vShow: _vShow, withDirectives: _withDirectives } = _Vue

    const _component_WidgetHost = _resolveComponent("WidgetHost")
    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_WidgetDefinition = _resolveComponent("WidgetDefinition")

    return (_openBlock(), _createElementBlock("section", {
      class: "configured-tabs native-tabs",
      "data-tab-container": screen.id
    }, [
      (!screen.container?.hide_header)
        ? (_openBlock(), _createElementBlock("header", {
            key: 0,
            class: "native-tab-strip",
            ref: "strip",
            role: "tablist",
            "aria-label": screen.title
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(visible, (child) => {
            return (_openBlock(), _createElementBlock("div", {
              key: child.id,
              class: "native-tab-head",
              draggable: screen.container?.allow_drag!==false,
              onDragstart: $event => (dragged=child.id),
              onDragover: _withModifiers(() => {}, ["prevent"]),
              onDrop: _withModifiers($event => (drop(child)), ["prevent"])
            }, [_createElementVNode("button", {
              role: "tab",
              "aria-selected": selected===child.id,
              tabindex: selected===child.id?0:-1,
              class: _normalizeClass({active:selected===child.id}),
              onClick: $event => (choose(child)),
              onKeydown: $event => (key($event,child)),
              onContextmenu: $event => (context($event,child))
            }, [_createTextVNode(_toDisplayString(titles[child.id]||child.title), 1), (dirty[child.id])
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  title: "Несохранённые изменения"
                }, " ●"))
              : _createCommentVNode("", true)], 42, ["aria-selected", "tabindex", "onClick", "onKeydown", "onContextmenu"]), (child.removable)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  class: "tab-close",
                  "aria-label": "Закрыть вложенную вкладку",
                  onClick: $event => (closeChild(child))
                }, "×", 8, ["onClick"]))
              : _createCommentVNode("", true)], 40, ["draggable", "onDragstart", "onDragover", "onDrop"]))
          }), 128)), (closed.length)
            ? (_openBlock(), _createElementBlock("button", {
                key: 0,
                onClick: reopen
              }, "Вернуть закрытые (" + _toDisplayString(closed.length) + ")", 9, ["onClick"]))
            : _createCommentVNode("", true)], 8, ["aria-label"]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "error"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      (!visible.length)
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
            class: "notice"
          }, "В конфигурации нет видимых вкладок."))
        : _createCommentVNode("", true),
      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(children, (child) => {
        return (_openBlock(), _createElementBlock(_Fragment, { key: child.id }, [(loaded.includes(child.id)&&!closed.includes(child.id))
          ? _withDirectives((_openBlock(), _createElementBlock("div", {
              key: 0,
              role: "tabpanel",
              "aria-label": titles[child.id]||child.title,
              class: "native-tab-content"
            }, [(_openBlock(), _createBlock(_component_WidgetHost, {
              key: child.id+':'+(refreshes[child.id]||0),
              project: project,
              target: child.id,
              user: user,
              active: active&&selected===child.id,
              onOpen: $event => ($emit('open',$event)),
              onDirty: $event => (mark(child.id,$event)),
              onClose: $event => (closeChild(child)),
              onChanged: $event => ($emit('changed',$event))
            }, null, 8, ["project", "target", "user", "active", "onOpen", "onDirty", "onClose", "onChanged"]))], 8, ["aria-label"])), [[_vShow, selected===child.id]])
          : _createCommentVNode("", true)], 64))
      }), 128)),
      menu
        ? (_openBlock(), _createBlock(_component_ContextMenu, {
            key: 3,
            menu: menu,
            onAction: act,
            onClose: $event => {menu=null;menuSeq++}
          }, null, 8, ["menu", "onAction", "onClose"]))
        : _createCommentVNode("", true),
      definition
        ? (_openBlock(), _createBlock(_component_WidgetDefinition, {
            key: 4,
            project: project,
            target: definition,
            onClose: $event => (definition=null)
          }, null, 8, ["project", "target", "onClose"]))
        : _createCommentVNode("", true)
    ], 8, ["data-tab-container"]))
  }
};
return __component;
})();
const WidgetHost = (function(){


















const __component = {
 name:'WidgetHost',components:{SecurityMatrix,UserGroups,UserManager,SidebarEditor,GlobalSettings,ConfiguredTabs,EmbeddedForm,WidgetTable,GraphEditor,ScriptEditor,ConfigEditor,SearchTypes,GroupMembership,AdminPanel,MessageCenter,CollectionPanel,WidgetDefinition},
 props:{project:String,target:String,user:Object,active:{type:Boolean,default:true},initial:Object,refreshKey:Number},emits:['open','dirty','close','changed'],
 data(){return {screen:this.initial||null,error:'',busy:false,seq:0,definition:false,menu:null,menuSeq:0,dirty:false}},mounted(){if(!this.screen)this.load()},beforeUnmount(){this.seq++;this.menuSeq++},watch:{target(){this.load()},refreshKey(){this.load()}},
 methods:{
 async context(e){if(!this.screen||e.shiftKey||e.defaultPrevented||e.target.closest('input,textarea,select,[contenteditable=true]'))return;e.preventDefault();e.stopPropagation();const seq=++this.menuSeq;this.menu={x:e.clientX,y:e.clientY,title:this.screen.title,loading:true,items:[]};try{const d=await api.request('/context-menu',{project:this.project,target:this.target,scope:'widget'});if(this.menu&&seq===this.menuSeq)this.menu={...this.menu,...d,loading:false}}catch(err){if(this.menu&&seq===this.menuSeq)this.menu={...this.menu,loading:false,error:err.message}}},
 action(item){this.menu=null;this.menuSeq++;if(item.id==='definition')this.definition=true;else if(item.id==='refresh'){if(this.dirty&&!confirm('Обновить виджет и отменить правки?'))return;this.screen=null;this.$emit('dirty',false);this.load()}},
 mark(value){this.dirty=value;this.$emit('dirty',value)},
 async load(){const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request('/open',{project:this.project,target:this.target});if(seq===this.seq)this.screen=d}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}}}
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, resolveComponent: _resolveComponent, createBlock: _createBlock, createElementVNode: _createElementVNode, Fragment: _Fragment } = _Vue

    const _component_ConfiguredTabs = _resolveComponent("ConfiguredTabs")
    const _component_EmbeddedForm = _resolveComponent("EmbeddedForm")
    const _component_WidgetTable = _resolveComponent("WidgetTable")
    const _component_GraphEditor = _resolveComponent("GraphEditor")
    const _component_GlobalSettings = _resolveComponent("GlobalSettings")
    const _component_ScriptEditor = _resolveComponent("ScriptEditor")
    const _component_SidebarEditor = _resolveComponent("SidebarEditor")
    const _component_CustomLayoutEditor = _resolveComponent("CustomLayoutEditor")
    const _component_ManageViews = _resolveComponent("ManageViews")
    const _component_LayoutPreview = _resolveComponent("LayoutPreview")
    const _component_ConfigEditor = _resolveComponent("ConfigEditor")
    const _component_SearchTypes = _resolveComponent("SearchTypes")
    const _component_GroupMembership = _resolveComponent("GroupMembership")
    const _component_UserManager = _resolveComponent("UserManager")
    const _component_UserGroups = _resolveComponent("UserGroups")
    const _component_SecurityMatrix = _resolveComponent("SecurityMatrix")
    const _component_AdminPanel = _resolveComponent("AdminPanel")
    const _component_MessageCenter = _resolveComponent("MessageCenter")
    const _component_CollectionPanel = _resolveComponent("CollectionPanel")
    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_WidgetDefinition = _resolveComponent("WidgetDefinition")

    return (_openBlock(), _createElementBlock("div", {
      class: "widget-host",
      onContextmenu: context
    }, [error
      ? (_openBlock(), _createElementBlock("p", {
          key: 0,
          class: "error"
        }, _toDisplayString(error), 1))
      : _createCommentVNode("", true), (busy&&!screen)
      ? (_openBlock(), _createElementBlock("p", {
          key: 1,
          class: "muted"
        }, "Загрузка виджета…"))
      : _createCommentVNode("", true), screen
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [(screen.kind==='tabs')
          ? (_openBlock(), _createBlock(_component_ConfiguredTabs, {
              key: 0,
              project: project,
              screen: screen,
              user: user,
              active: active,
              "refresh-key": refreshKey,
              onOpen: $event => ($emit('open',$event)),
              onDirty: mark,
              onChanged: $event => ($emit('changed',$event))
            }, null, 8, ["project", "screen", "user", "active", "refresh-key", "onOpen", "onDirty", "onChanged"]))
          : (screen.kind==='form')
            ? (_openBlock(), _createBlock(_component_EmbeddedForm, {
                key: 1,
                project: project,
                target: screen.id,
                "refresh-key": refreshKey,
                onClose: $event => ($emit('close')),
                onDirty: mark,
                onChanged: $event => ($emit('changed',$event))
              }, null, 8, ["project", "target", "refresh-key", "onClose", "onDirty", "onChanged"]))
            : (screen.kind==='table')
              ? (_openBlock(), _createBlock(_component_WidgetTable, {
                  key: 2,
                  onRefresh: load,
                  project: project,
                  screen: screen,
                  user: user,
                  "refresh-key": refreshKey,
                  onOpen: $event => ($emit('open',$event)),
                  onDirty: mark,
                  onChanged: $event => ($emit('changed',$event))
                }, null, 8, ["onRefresh", "project", "screen", "user", "refresh-key", "onOpen", "onDirty", "onChanged"]))
              : (['pipeline','schema'].includes(screen.kind))
                ? (_openBlock(), _createBlock(_component_GraphEditor, {
                    key: project+screen.id+':'+(refreshKey||0),
                    project: project,
                    kind: screen.kind,
                    target: screen.id,
                    onDirty: mark
                  }, null, 8, ["project", "kind", "target", "onDirty"]))
                : (['system-config','license'].includes(screen.kind))
                  ? (_openBlock(), _createBlock(_component_GlobalSettings, {
                      key: 4,
                      project: project,
                      target: screen.id,
                      kind: screen.kind,
                      onDirty: mark
                    }, null, 8, ["project", "target", "kind", "onDirty"]))
                  : (screen.kind==='script-editor')
                    ? (_openBlock(), _createBlock(_component_ScriptEditor, {
                        key: 5,
                        project: project,
                        target: screen.id,
                        onDirty: mark,
                        onOpen: $event => ($emit('open',$event))
                      }, null, 8, ["project", "target", "onDirty", "onOpen"]))
                    : (screen.kind==='sidebar-editor')
                      ? (_openBlock(), _createBlock(_component_SidebarEditor, {
                          key: 6,
                          project: project,
                          target: screen.id,
                          "initial-view": screen.options?.view||(project==='admin'?'admin_views':'project_view'),
                          user: user,
                          "allow-writes": user.allow_writes,
                          onDirty: mark,
                          onChanged: $event => ($emit('changed',$event))
                        }, null, 8, ["project", "target", "initial-view", "user", "allow-writes", "onDirty", "onChanged"]))
                      : (screen.kind==='layout-editor')
                        ? (_openBlock(), _createBlock(_component_CustomLayoutEditor, {
                            key: project+screen.id,
                            project: project,
                            target: screen.id,
                            user: user,
                            onDirty: mark,
                            onOpen: $event => ($emit('open',$event)),
                            onChanged: $event => ($emit('changed',$event))
                          }, null, 8, ["project", "target", "user", "onDirty", "onOpen", "onChanged"]))
                        : (screen.kind==='views-manager')
                          ? (_openBlock(), _createBlock(_component_ManageViews, {
                              key: project+screen.id,
                              project: project,
                              target: screen.id,
                              screen: screen,
                              user: user,
                              onDirty: mark,
                              onOpen: $event => ($emit('open',$event)),
                              onChanged: $event => ($emit('changed',$event))
                            }, null, 8, ["project", "target", "screen", "user", "onDirty", "onOpen", "onChanged"]))
                          : (screen.kind==='custom-layout')
                            ? (_openBlock(), _createBlock(_component_LayoutPreview, {
                                key: project+screen.id,
                                parts: screen.layout.parts,
                                children: screen.layout.children,
                                project: project,
                                user: user,
                                onDirty: mark,
                                onOpen: $event => ($emit('open',$event)),
                                onChanged: $event => ($emit('changed',$event))
                              }, null, 8, ["parts", "children", "project", "user", "onDirty", "onOpen", "onChanged"]))
                            : (screen.kind==='config-editor')
                              ? (_openBlock(), _createBlock(_component_ConfigEditor, {
                                  key: 10,
                                  project: project,
                                  mode: screen.kind,
                                  "initial-view": screen.options?.view||(project==='admin'?'admin_views':'project_view'),
                                  "allow-writes": user.allow_writes,
                                  onChanged: $event => ($emit('changed',$event))
                                }, null, 8, ["project", "mode", "initial-view", "allow-writes", "onChanged"]))
                              : (screen.kind==='search-types')
                                ? (_openBlock(), _createBlock(_component_SearchTypes, {
                                    key: 11,
                                    project: project,
                                    target: screen.id,
                                    screen: screen,
                                    user: user,
                                    onDirty: mark,
                                    "allow-writes": user.allow_writes,
                                    onOpen: $event => ($emit('open',$event)),
                                    onChanged: $event => ($emit('changed',$event))
                                  }, null, 8, ["project", "target", "screen", "user", "onDirty", "allow-writes", "onOpen", "onChanged"]))
                                : (screen.kind==='group-membership')
                                  ? (_openBlock(), _createBlock(_component_GroupMembership, {
                                      key: 12,
                                      "initial-key": screen.options?.search_key,
                                      project: project,
                                      target: screen.id,
                                      onChanged: $event => ($emit('changed',$event))
                                    }, null, 8, ["initial-key", "project", "target", "onChanged"]))
                                  : (['users','groups'].includes(screen.kind))
                                    ? (_openBlock(), _createBlock(_component_UserManager, {
                                        key: 13,
                                        project: project,
                                        target: screen.id,
                                        screen: screen,
                                        mode: screen.kind,
                                        user: user,
                                        onDirty: mark,
                                        onChanged: $event => ($emit('changed',$event)),
                                        onOpen: $event => ($emit('open',$event))
                                      }, null, 8, ["project", "target", "screen", "mode", "user", "onDirty", "onChanged", "onOpen"]))
                                    : (screen.kind==='group-assignment'&&screen.handler.endsWith('GroupAssignWdg'))
                                      ? (_openBlock(), _createBlock(_component_UserGroups, {
                                          key: 14,
                                          project: project,
                                          target: screen.id,
                                          "initial-key": screen.options?.search_key,
                                          onDirty: mark,
                                          onChanged: $event => ($emit('changed',$event))
                                        }, null, 8, ["project", "target", "initial-key", "onDirty", "onChanged"]))
                                      : (['security','group-assignment'].includes(screen.kind))
                                        ? (_openBlock(), _createBlock(_component_SecurityMatrix, {
                                            key: 15,
                                            project: project,
                                            target: screen.id,
                                            screen: screen,
                                            user: user,
                                            onDirty: mark,
                                            onChanged: $event => ($emit('changed',$event)),
                                            onOpen: $event => ($emit('open',$event))
                                          }, null, 8, ["project", "target", "screen", "user", "onDirty", "onChanged", "onOpen"]))
                                        : (['project-create','system'].includes(screen.kind))
                                          ? (_openBlock(), _createBlock(_component_AdminPanel, {
                                              key: 16,
                                              "initial-key": screen.options?.search_key,
                                              project: project,
                                              target: screen.id,
                                              kind: screen.kind,
                                              onDirty: mark,
                                              onChanged: $event => ($emit('changed',$event))
                                            }, null, 8, ["initial-key", "project", "target", "kind", "onDirty", "onChanged"]))
                                          : (screen.kind==='message-center')
                                            ? (_openBlock(), _createBlock(_component_MessageCenter, {
                                                key: 17,
                                                project: project,
                                                target: screen.id,
                                                options: screen.options,
                                                login: user.login,
                                                active: active,
                                                onClose: $event => ($emit('close'))
                                              }, null, 8, ["project", "target", "options", "login", "active", "onClose"]))
                                            : (screen.kind==='collections')
                                              ? (_openBlock(), _createBlock(_component_CollectionPanel, {
                                                  key: 18,
                                                  project: project,
                                                  target: screen.id,
                                                  onChanged: $event => ($emit('changed',$event)),
                                                  onOpen: $event => ($emit('open',$event))
                                                }, null, 8, ["project", "target", "onChanged", "onOpen"]))
                                              : (_openBlock(), _createElementBlock("section", {
                                                  key: 19,
                                                  class: "unsupported-panel"
                                                }, [
                                                  _createElementVNode("h3", null, _toDisplayString(screen.title), 1),
                                                  _createElementVNode("p", null, "Обработчик присутствует в исходной конфигурации, но ещё не перенесён. Он не заменён таблицей."),
                                                  _createElementVNode("code", null, _toDisplayString(screen.handler), 1),
                                                  _createElementVNode("button", { onClick: $event => (definition=true) }, "Определение виджета", 8, ["onClick"])
                                                ])), menu
          ? (_openBlock(), _createBlock(_component_ContextMenu, {
              key: 20,
              menu: menu,
              onAction: action,
              onClose: $event => {menu=null;menuSeq++}
            }, null, 8, ["menu", "onAction", "onClose"]))
          : _createCommentVNode("", true), definition
          ? (_openBlock(), _createBlock(_component_WidgetDefinition, {
              key: 21,
              project: project,
              target: screen.id,
              onClose: $event => (definition=false)
            }, null, 8, ["project", "target", "onClose"]))
          : _createCommentVNode("", true)], 64))
      : _createCommentVNode("", true)], 40, ["onContextmenu"]))
  }
};
return __component;
})();
const App = (function(){




























const __component = {
 name:'TacticApp',components:{SecurityMatrix,UserGroups,UserManager,SidebarEditor,GlobalSettings,WidgetHost,ContextMenu,WidgetDefinition,ScriptEditor,CsvExport,ConfigAudit,CollectionPanel,AdvancedFilter,RelationTree,SidebarNode,ConfiguredTable,ConfiguredForm,ConfigEditor,GraphEditor,RecordInspector,GroupMembership,SearchTypes,ViewDesigner,TaskTimeline,AdminPanel,MessageCenter},
 data(){return {navigationSeq:0,navFolders:{},restoringState:false,restoringInputs:false,stateStatus:'',stateError:'',stateWarning:'',theme:'light',menu:null,menuSeq:0,widgetDefinition:null,popup:null,popupDirty:false,sidebarEditor:null,exporting:false,audit:false,user:null,login:'',password:'',twoFactor:'',projects:[],project:'',sidebar:{sections:[]},navError:'',error:'',busy:false,navOpen:true,tabs:[],active:'',form:null,formDirty:false,formError:'',saving:false,refreshing:false,previewBusy:false,previewSequence:0,previewFailed:false,inspected:null,keyword:'',filterField:'',filterOp:'contains',filterValue:'',types:[],loginBusy:false,designer:null,selected:[],tableMode:'data',saveViewTitle:'',showSaveView:false,searchOpen:false,lastProject:'',messagesOpen:false,messageCode:''}},
 computed:{tableFilterCount(){const count=n=>n?.children?n.children.reduce((v,c)=>v+count(c),0):n?.field?1:0;return (this.current?.filters?.length||0)+count(this.current?.where)},timelineQuery(){return this.current?{filters:this.current.filters,where:this.current.where,sort:this.current.sort||undefined,record_state:this.current.recordState}:{}},current(){return this.tabs.find(t=>t.id===this.active)},fields(){return this.current?.spec?.fields.filter(f=>f.storage)||[]},mainSections(){return this.sidebar.sections}},
 async mounted(){
  this.stateHandlers={status:e=>this.stateStatus=e.detail,error:e=>this.stateError=e.detail,warning:e=>this.stateWarning=e.detail};
  for(const [kind,fn] of Object.entries(this.stateHandlers))window.addEventListener('tactic:state-'+kind,fn);
  this.stateBeforeExit=e=>{if(uiState.hasPending()){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',this.stateBeforeExit);
  document.documentElement.dataset.theme=this.theme;
  try{const session=await api.request('/session');this.user=session.user;await this.initialize()}catch(e){if(e.status!==401)this.error=e.message}
 },
 beforeUnmount(){for(const [kind,fn] of Object.entries(this.stateHandlers||{}))window.removeEventListener('tactic:state-'+kind,fn);window.removeEventListener('beforeunload',this.stateBeforeExit)},
 watch:{searchOpen(){this.queryInputsChanged()},tableMode(){this.queryInputsChanged()},filterField(){this.queryInputsChanged()},filterOp(){this.queryInputsChanged()},filterValue(){this.queryInputsChanged()}},
 methods:{
 folderChanged(change){api.action?.('sidebar.toggle',{project:this.project,target:change.id,control:change.open?'open':'close'});this.navFolders={...this.navFolders,[change.id]:change.open};if(!this.restoringState&&this.user?.allow_writes)uiState.schedule({project:this.project,scope:'navigation'},{folders:this.navFolders})},
 toggleTheme(){api.action?.('theme.toggle',{project:this.project,control:this.theme==='dark'?'light':'dark'});this.theme=this.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=this.theme;if(this.user?.allow_writes&&this.project)uiState.schedule({project:this.project,scope:'appearance'},{theme:this.theme})},
 setTableMode(mode){this.tableMode=mode},
 tableAction({id,value}){
  api.action?.(id==='create'?'table.create':id==='search'?'table.search':'menu.select',{project:this.project,target:this.current?.id||'',control:id});
  if(id==='create')this.edit(null);else if(id==='refresh')this.refresh();
  else if(id==='search')this.searchOpen=!this.searchOpen;
  else if(id==='bulk')this.bulk();else if(id==='export')this.exporting=true;
  else if(id==='designer')this.designer={searchType:this.current.search_type,view:this.current.view};
  else if(id==='audit')this.audit=true;
  else if(id==='save-view')this.showSaveView=true;
  else if(id==='mode')this.setTableMode(value);
  else if(id==='state'){this.current.recordState=value;this.stateChanged()}
 },
 openMessages(code=''){this.messageCode=code;this.messagesOpen=true},
 async signIn(){this.loginBusy=true;this.error='';try{const s=await api.request('/session',{login:this.login,password:this.password,two_factor:this.twoFactor},'POST');this.password='';this.user=s.user;await this.initialize()}catch(e){this.error=e.message}finally{this.loginBusy=false}},
 async signOut(){if((this.popupDirty||this.formDirty||this.tabs.some(t=>t.dirty))&&!confirm('Выйти без сохранения правок?'))return;try{await uiState.flush()}catch(e){if(!confirm('Настройки не сохранены в БД. Всё равно выйти?'))return}this.navigationSeq++;try{await api.request('/session',{},'DELETE')}catch{}uiState.clear();this.restoringState=true;this.popup=null;this.menu=null;this.messagesOpen=false;this.user=null;this.tabs=[];this.sidebar={sections:[]};this.project='';this.lastProject='';this.restoringState=false},
 async initialize(){this.projects=(await api.request('/projects')).items;const parts=location.pathname.split('/').filter(Boolean).map(decodeURIComponent);const offset=this.user.site&&parts[1]===this.user.site?2:1;const requested=parts[0]==='tactic'?parts[offset]:'';const linkAt=parts.indexOf('link',offset+1);const link=linkAt>=0?parts[linkAt+1]:null;this.project=this.projects.some(p=>p.code===requested)?requested:(this.projects.find(p=>p.code==='admin')||this.projects[0])?.code||'';await this.switchProject();if(link){const find=(nodes)=>{for(const n of nodes){if(n.name===link&&n.kind==='link')return n;const hit=find(n.children||[]);if(hit)return hit}};for(const s of this.sidebar.sections){const hit=find(s.children);if(hit){await this.open(hit);break}}}},
 async reloadSidebar(){const project=this.project,seq=this.navigationSeq;this.navError='';try{const sidebar=await api.request('/sidebar',{project});if(project===this.project&&seq===this.navigationSeq)this.sidebar=sidebar}catch(e){if(project===this.project&&seq===this.navigationSeq)this.navError=e.message}},
 async switchProject(){
  if((this.popupDirty||this.formDirty||this.tabs.some(t=>t.dirty))&&!confirm('Сменить проект и отменить несохранённые правки?')){this.project=this.lastProject;return}
  try{await uiState.flush()}catch(e){this.stateError=e.message;if(!confirm('Настройки не сохранены. Перейти без их сохранения?')){this.project=this.lastProject;return}}
  const navigationEpoch=++this.navigationSeq,project=this.project;this.restoringState=true;this.lastProject=this.project;api.setContext?.(this.project,'');api.action?.('project.select',{project:this.project,target:''});this.popup=null;this.menu=null;this.sidebarEditor=null;this.widgetDefinition=null;this.audit=false;this.exporting=false;this.messagesOpen=false;this.designer=null;this.selected=[];this.showSaveView=false;this.tabs=[];this.active='';this.inspected=null;this.form=null;this.formDirty=false;this.error='';
  try{
   if(!project)return;await this.reloadSidebar();if(this.navError||navigationEpoch!==this.navigationSeq||project!==this.project)return;
   history.replaceState({},'', '/tactic/'+(this.user.site?encodeURIComponent(this.user.site)+'/':'')+encodeURIComponent(this.project)+'/');
   const [workspace,appearance,navigation]=await Promise.all([uiState.load({project:this.project,scope:'workspace'}),uiState.load({project:this.project,scope:'appearance'}),uiState.load({project:this.project,scope:'navigation'})]);if(navigationEpoch!==this.navigationSeq||project!==this.project)return;this.navFolders=navigation.value?.folders||{};
   this.theme=appearance.value?.theme||'light';document.documentElement.dataset.theme=this.theme;
   if(workspace.value){for(const id of workspace.value.ids.slice(0,32)){if(navigationEpoch!==this.navigationSeq||project!==this.project)return;await this.open({id},false)}if(this.tabs.some(t=>t.id===workspace.value.active))this.active=workspace.value.active}
   this.syncQueryInputs();
  }catch(e){if(navigationEpoch===this.navigationSeq)this.stateError='Не удалось восстановить настройки: '+e.message}finally{await this.$nextTick();if(navigationEpoch===this.navigationSeq)this.restoringState=false}
 },
 initialSort(screen){if(screen.spec?.default_sort?.length)return null;const m=/^([A-Za-z_][A-Za-z0-9_]*)(?: +(asc|desc))?$/i.exec(screen.options?.order_by||'');return m&&screen.spec?.fields.some(f=>f.name===m[1]&&f.storage)?{field:m[1],direction:(m[2]||'asc').toLowerCase()}:null},
 queryArgs(tab=this.current){return {project:tab.projectCode||this.project,target:tab.id,scope:'query'}},
 querySnapshot(tab){return {filters:tab.filters,where:tab.where,sort:tab.sort,record_state:tab.recordState,offset:tab.offset,limit:tab.limit,presentation:tab.presentation||'data',search_open:!!tab.searchOpen,quickField:tab.quickField||'',quickText:tab.quickText||'',quickOp:tab.quickOp||'contains'}},
 saveQuery(tab=this.current){if(tab?.kind==='table'&&tab.projectCode===this.project&&this.tabs.includes(tab)&&tab.stateReady&&!this.restoringState&&this.user?.allow_writes)uiState.schedule(this.queryArgs(tab),this.querySnapshot(tab))},
 syncQueryInputs(){this.restoringInputs=true;const t=this.current;this.tableMode=t?.presentation||'data';this.searchOpen=!!t?.searchOpen;this.filterField=t?.quickField||'';this.filterValue=t?.quickText||'';this.filterOp=t?.quickOp||'contains';this.$nextTick(()=>this.restoringInputs=false)},
 queryInputsChanged(){if(this.restoringState||this.restoringInputs||this.current?.kind!=='table')return;Object.assign(this.current,{presentation:this.tableMode,searchOpen:this.searchOpen,quickField:this.filterField,quickText:this.filterValue,quickOp:this.filterOp});this.saveQuery()},
 persist(){if(!this.restoringState&&this.user?.allow_writes&&this.project)uiState.schedule({project:this.project,scope:'workspace'},{ids:this.tabs.map(t=>t.id),active:this.active})},
 async open(node,persist=true){
  api.setContext?.(this.project,node.id);if(persist)api.action?.('view.open',{project:this.project,target:node.id});
  if(this.current?.dirty&&!['tabs','form'].includes(this.current.kind)&&!confirm('Оставить экран и отменить несохранённые правки?'))return;
  if(this.current&&!['tabs','form'].includes(this.current.kind))this.current.dirty=false;
  this.inspected=null;this.selected=[];this.error='';
  if(this.tabs.some(t=>t.id===node.id)){this.active=node.id;this.syncQueryInputs();if(persist)this.persist();if(window.innerWidth<800)this.navOpen=false;return}
  if(this.tabs.length>=32){this.error='Открыто 32 представления. Закройте одно перед открытием нового.';return}
  const project=this.project,navigation=this.navigationSeq;this.busy=true;
   try{const screen=await api.request('/open',{project,target:node.id});if(project!==this.project||navigation!==this.navigationSeq)return;
   const tab={...screen,projectCode:project,rows:[],offset:0,limit:screen.spec?.table_options?.page_size||50,total:null,filters:[],where:{op:'and',children:[]},recordState:'active',requestSeq:0,sort:this.initialSort(screen),error:'',loading:false,presentation:'data',searchOpen:false,stateReady:false};
   if(screen.kind==='table'){
    try{const saved=await uiState.load(this.queryArgs(tab));if(saved.value){const q=saved.value;Object.assign(tab,{filters:q.filters,where:q.where,sort:q.sort,recordState:q.record_state,offset:q.offset,limit:q.limit,presentation:q.presentation,searchOpen:q.search_open,quickField:q.quickField,quickText:q.quickText,quickOp:q.quickOp})}tab.stateReady=true}catch(e){this.stateError=e.message}
   }
   if(project!==this.project||navigation!==this.navigationSeq)return;this.tabs.push(tab);this.active=tab.id;this.syncQueryInputs();if(tab.kind==='table')await this.loadPage();if(persist&&project===this.project&&navigation===this.navigationSeq)this.persist();
  }catch(e){if(project===this.project&&navigation===this.navigationSeq)this.error=e.message}finally{if(navigation===this.navigationSeq){this.busy=false;if(window.innerWidth<800)this.navOpen=false}}
 },
 select(id){api.setContext?.(this.project,id);api.action?.('view.select',{project:this.project,target:id});if(id!==this.active&&this.current?.dirty&&!['tabs','form'].includes(this.current.kind)&&!confirm('Оставить экран и отменить несохранённые правки?'))return;if(this.current&&id!==this.active&&!['tabs','form'].includes(this.current.kind))this.current.dirty=false;this.active=id;this.selected=[];this.inspected=null;this.syncQueryInputs();this.persist()},
 close(id){api.action?.('view.close',{project:this.project,target:id});if(this.tabs.find(t=>t.id===id)?.dirty&&!confirm('Закрыть без сохранения?'))return;const i=this.tabs.findIndex(t=>t.id===id);this.tabs=this.tabs.filter(t=>t.id!==id);if(this.active===id)this.active=this.tabs[Math.max(0,i-1)]?.id||'';this.inspected=null;this.syncQueryInputs();this.persist()},
 async loadPage(){const tab=this.current,project=this.project;if(!tab||tab.projectCode!==project)return;tab.error='';tab.loading=true;const seq=++tab.requestSeq;const current=()=>seq===tab.requestSeq&&project===this.project&&this.tabs.includes(tab);try{const args={project,target:tab.id,offset:tab.offset,limit:tab.limit,filters:tab.filters,where:tab.where,record_state:tab.recordState};if(tab.sort)args.sort=tab.sort;const data=await api.request('/query',args,'POST');if(current()){tab.rows=data.items;tab.summaries=data.summaries||[];tab.total=data.total;this.saveQuery(tab)}}catch(e){if(current()){tab.error=e.message;tab.rows=[];tab.total=null}}finally{if(seq===tab.requestSeq)tab.loading=false}},
 async refresh(){
  const tab=this.current,project=this.project,epoch=this.navigationSeq;
  if(!tab||this.refreshing)return;
  if(tab.dirty&&!confirm('Обновить виджет и отменить несохранённые правки?'))return;
  this.refreshing=true;api.action?.('view.refresh',{project,target:tab.id});
  try{
   const fresh=await api.request('/open',{project,target:tab.id});
   if(epoch!==this.navigationSeq||project!==this.project||!this.tabs.includes(tab))return;
   const refreshKey=(tab.refreshKey||0)+1;
   Object.assign(tab,fresh,{refreshKey,dirty:false});
   await this.reloadSidebar();
   if(tab.kind==='table'&&this.current===tab)await this.loadPage();
  }catch(e){if(epoch===this.navigationSeq&&this.tabs.includes(tab)){tab.error=e.message;this.error=e.message}}
  finally{this.refreshing=false}
 },
 sort(field){const t=this.current;t.sort=typeof field==='object'?field:{field,direction:t.sort?.field===field&&t.sort.direction==='asc'?'desc':'asc'};t.offset=0;this.loadPage()},
 page(offset){this.current.offset=offset;this.loadPage()},
 addFilter(){if(!this.filterField)return;this.current.filters.push({field:this.filterField,op:this.filterOp,value:['null','not_null'].includes(this.filterOp)?null:this.filterValue});this.current.offset=0;this.loadPage()},
 removeFilter(i){this.current.filters.splice(i,1);this.current.offset=0;this.loadPage()},
 async edit(row=null){this.formError='';this.previewFailed=false;this.previewSequence++;this.previewBusy=false;try{const f=await api.request('/form',{project:this.project,target:this.active,key:row?.key});this.form={...f,target:this.active}}catch(e){this.error=e.message}},
 async previewForm(values){const seq=++this.previewSequence;const form=this.form;this.previewBusy=true;this.previewFailed=false;this.formError='';try{const next=await api.request('/form-preview',{project:this.project,target:form.target,key:form.record.key,revision:form.record.revision,values},'POST');if(seq===this.previewSequence&&this.form===form)this.form={...next,target:form.target}}catch(e){if(seq===this.previewSequence){this.formError=e.message;this.previewFailed=true}}finally{if(seq===this.previewSequence)this.previewBusy=false}},
 async save(values){if(this.previewBusy||this.previewFailed)return;this.saving=true;this.formError='';try{if(this.form.records){await api.request('/bulk-records',{project:this.project,target:this.form.target,records:this.form.records.map(r=>({key:r.key,revision:r.revision,values}))},'PATCH')}else await api.request('/record',{project:this.project,target:this.form.target,key:this.form.record?.key,revision:this.form.record?.revision,values},this.form.record?'PATCH':'POST');this.form=null;this.inspected=null;await this.loadPage()}catch(e){this.formError=e.message}finally{this.saving=false}},
 inspect(row){this.inspected=row},
 async configChanged(event){if(event?.created&&event?.code)return this.projectChanged(event);await this.reloadSidebar()},
 childrenLinks(section){return section.children.filter(n=>n.kind!=='separator')},
 async bulk(){this.error='';if(!this.selected.length||this.selected.length>100){this.error='Выберите от 1 до 100 записей';return}this.busy=true;try{const forms=[];for(const key of this.selected)forms.push(await api.request('/form',{project:this.project,target:this.active,key}));let fields=forms[0].spec.fields.filter(f=>!f.read_only&&forms.every(form=>form.spec.fields.some(other=>other.name===f.name&&!other.read_only&&other.kind===f.kind)));fields=fields.map(f=>{const out={...f};if(out.options?.length)out.options=out.options.filter(o=>forms.every(form=>form.spec.fields.find(x=>x.name===f.name).options.some(x=>String(x.value)===String(o.value))));return out});this.form={spec:{...forms[0].spec,fields},record:null,records:forms.map(f=>f.record),target:this.active,bulk:true};this.formError=''}catch(e){this.error=e.message}finally{this.busy=false}},
 async saveView(){this.error='';try{await api.request('/saved-view',{project:this.project,target:this.active,title:this.saveViewTitle,filters:this.current.filters,where:this.current.where,record_state:this.current.recordState,sort:this.current.sort||undefined},'POST');this.showSaveView=false;this.saveViewTitle='';await this.reloadSidebar()}catch(e){this.error=e.message}},
 async dates(change){this.error='';try{const f=await api.request('/form',{project:this.project,target:this.active,key:change.row.key});if(f.record.revision!==change.row.revision)throw Error('Запись изменилась после загрузки Gantt. Обновите период перед переносом.');const values={};for(const name of [change.startField,change.endField]){const field=f.spec.fields.find(x=>x.name===name);if(!field||field.read_only)throw Error('Дата '+name+' недоступна для изменения в исходной форме');const value=f.record.values[name];if(!value)throw Error('Для переноса обе даты должны быть заданы');const m=/^(\d{4}-\d{2}-\d{2})(.*)$/.exec(String(value));if(!m)throw Error('Неизвестный формат даты '+name);const d=new Date(m[1]+'T00:00:00Z');if(!Number.isFinite(d.getTime()))throw Error('Некорректная дата '+name);d.setUTCDate(d.getUTCDate()+change.delta);const day=d.toISOString().slice(0,10);values[name]=field.kind==='date'?day:day+(m[2]||'T00:00:00')}await api.request('/record',{project:this.project,target:this.active,key:change.row.key,revision:f.record.revision,values},'PATCH');await this.loadPage()}catch(e){this.error=e.message}},
 async projectChanged(event){
  try{this.projects=(await api.request('/projects')).items;if(event?.created&&event.open){
   if(!this.projects.some(p=>p.code===event.code))throw Error('Проект создан, но ещё не появился в доступном списке. Обновите список проектов, не создавайте его заново.');
   if(this.current)this.current.dirty=false;this.popupDirty=false;this.project=event.code;await this.switchProject();
  }else await this.reloadSidebar()}catch(e){this.error='Создание завершено, переход не выполнен: '+e.message}
 },
 advanced(where){this.current.where=where;this.current.offset=0;this.loadPage()},
 stateChanged(){this.current.offset=0;this.selected=[];this.loadPage()},
 async inspectRelated(event){await this.open({id:event.target});if(this.active===event.target)this.inspect(event.row)},
 async recordChanged(){const tab=this.current,key=this.inspected?.key;await this.loadPage();if(tab===this.current&&key&&this.inspected?.key===key){try{this.inspected=await api.request('/record',{project:this.project,target:tab.id,key})}catch(e){this.error=e.message}}},
 async designed(){await this.refresh()},
 async navMenu({event,node,keyboard=false},scope='sidebar'){if(event.shiftKey&&!keyboard)return;event.preventDefault();event.stopPropagation();const rect=event.currentTarget.getBoundingClientRect();const seq=++this.menuSeq;this.menu={x:keyboard?rect.left:event.clientX,y:keyboard?rect.bottom:event.clientY,title:node.title,loading:true,items:[],node,scope};try{const d=await api.request('/context-menu',{project:this.project,target:node.id,scope});if(seq===this.menuSeq&&this.menu)this.menu={...this.menu,...d,loading:false}}catch(e){if(seq===this.menuSeq&&this.menu)this.menu={...this.menu,loading:false,error:e.message}}},
 async navAction(item){const {node,scope}=this.menu;this.menu=null;this.menuSeq++;if(item.id==='open'||item.id==='open_main')await this.open(node);else if(item.id==='popup'){this.popup={id:node.id,title:node.title};this.popupDirty=false}else if(item.id==='definition')this.widgetDefinition=node.id;else if(item.id==='sidebar_config'){const full=await api.request('/open',{project:this.project,target:node.id});this.sidebarEditor=full.config_view||'project_view'}else if(item.id==='close')this.close(node.id);else if(item.id==='close_others'){for(const tab of [...this.tabs])if(tab.id!==node.id)this.close(tab.id)}else if(item.id==='rename'){const tab=this.tabs.find(t=>t.id===node.id),title=prompt('Название открытой вкладки',tab.title);if(title?.trim())tab.title=title.trim()}else if(item.id==='refresh'){this.select(node.id);await this.refresh()}},
 closePopup(){if(this.popupDirty&&!confirm('Закрыть панель без сохранения?'))return;this.popup=null;this.popupDirty=false}


 }
};
__component.render = function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, createTextVNode: _createTextVNode, toDisplayString: _toDisplayString, vModelText: _vModelText, withDirectives: _withDirectives, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers, renderList: _renderList, Fragment: _Fragment, vModelSelect: _vModelSelect, resolveComponent: _resolveComponent, createBlock: _createBlock, normalizeClass: _normalizeClass, withKeys: _withKeys, withCtx: _withCtx, Teleport: _Teleport, vShow: _vShow, createVNode: _createVNode } = _Vue

    const _component_SidebarNode = _resolveComponent("SidebarNode")
    const _component_CsvExport = _resolveComponent("CsvExport")
    const _component_ConfigAudit = _resolveComponent("ConfigAudit")
    const _component_AdvancedFilter = _resolveComponent("AdvancedFilter")
    const _component_CollectionPanel = _resolveComponent("CollectionPanel")
    const _component_TaskTimeline = _resolveComponent("TaskTimeline")
    const _component_RelationTree = _resolveComponent("RelationTree")
    const _component_ConfiguredTable = _resolveComponent("ConfiguredTable")
    const _component_SidebarEditor = _resolveComponent("SidebarEditor")
    const _component_CustomLayoutEditor = _resolveComponent("CustomLayoutEditor")
    const _component_ManageViews = _resolveComponent("ManageViews")
    const _component_LayoutPreview = _resolveComponent("LayoutPreview")
    const _component_ConfigEditor = _resolveComponent("ConfigEditor")
    const _component_GlobalSettings = _resolveComponent("GlobalSettings")
    const _component_GraphEditor = _resolveComponent("GraphEditor")
    const _component_ScriptEditor = _resolveComponent("ScriptEditor")
    const _component_SearchTypes = _resolveComponent("SearchTypes")
    const _component_GroupMembership = _resolveComponent("GroupMembership")
    const _component_MessageCenter = _resolveComponent("MessageCenter")
    const _component_UserManager = _resolveComponent("UserManager")
    const _component_UserGroups = _resolveComponent("UserGroups")
    const _component_SecurityMatrix = _resolveComponent("SecurityMatrix")
    const _component_AdminPanel = _resolveComponent("AdminPanel")
    const _component_WidgetHost = _resolveComponent("WidgetHost")
    const _component_RecordInspector = _resolveComponent("RecordInspector")
    const _component_ContextMenu = _resolveComponent("ContextMenu")
    const _component_WidgetDefinition = _resolveComponent("WidgetDefinition")
    const _component_ViewDesigner = _resolveComponent("ViewDesigner")
    const _component_ConfiguredForm = _resolveComponent("ConfiguredForm")

    return (!user)
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "login-screen"
        }, [_createElementVNode("form", {
          class: "login-card",
          onSubmit: _withModifiers(signIn, ["prevent"])
        }, [
          _createElementVNode("div", { class: "brand" }, [_createTextVNode("TACTIC "), _createElementVNode("span", null, "5.0 / VUE")]),
          _createElementVNode("button", {
            type: "button",
            class: "theme-toggle login-theme",
            onClick: toggleTheme
          }, _toDisplayString(theme==='dark'?'Светлая тема':'Тёмная тема'), 9, ["onClick"]),
          _createElementVNode("h1", null, "Вход в TACTIC"),
          _createElementVNode("p", null, "Настоящая учётная запись сервера. Демонстрационной базы здесь нет."),
          _createElementVNode("label", null, [_createTextVNode("Логин"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((login) = $event),
            autocomplete: "username",
            required: "",
            autofocus: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, login]])]),
          _createElementVNode("label", null, [_createTextVNode("Пароль"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((password) = $event),
            type: "password",
            autocomplete: "current-password",
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, password]])]),
          _createElementVNode("label", null, [_createTextVNode("Код подтверждения"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((twoFactor) = $event),
            inputmode: "numeric",
            autocomplete: "one-time-code"
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, twoFactor]])]),
          error
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "error"
              }, _toDisplayString(error), 1))
            : _createCommentVNode("", true),
          _createElementVNode("button", {
            class: "primary",
            disabled: loginBusy
          }, _toDisplayString(loginBusy?'Вход…':'Войти'), 9, ["disabled"]),
          _createElementVNode("small", null, "Native UI пока доступен администраторам.")
        ], 40, ["onSubmit"])]))
      : (_openBlock(), _createElementBlock("div", {
          key: 1,
          class: "application"
        }, [
          (user.mode==='test-fixture')
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "fixture-banner"
              }, "TEST FIXTURE · Меню из исходных XML TACTIC. Записи тестовые, не PostgreSQL."))
            : _createCommentVNode("", true),
          _createElementVNode("header", { class: "app-header" }, [
            _createElementVNode("button", {
              class: "nav-toggle",
              onClick: $event => (navOpen=!navOpen),
              "aria-label": "Открыть меню"
            }, "☰", 8, ["onClick"]),
            _createElementVNode("a", {
              class: "brand",
              href: "#",
              onClick: _withModifiers($event => (select('')), ["prevent"])
            }, [_createTextVNode("TACTIC "), _createElementVNode("span", null, "5.0 / VUE")], 8, ["onClick"]),
            _createElementVNode("div", { class: "project-picker" }, [_createElementVNode("small", null, "PROJECT"), _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": $event => ((project) = $event),
              onChange: switchProject,
              "aria-label": "Проект"
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(projects, (p) => {
              return (_openBlock(), _createElementBlock("option", {
                key: p.code,
                value: p.code
              }, _toDisplayString(p.name), 9, ["value"]))
            }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, project]])]),
            _createElementVNode("span", { class: "spacer" }),
            (!user.allow_writes)
              ? (_openBlock(), _createElementBlock("span", {
                  key: 0,
                  class: "read-only"
                }, "Запись отключена"))
              : _createCommentVNode("", true),
            _createElementVNode("button", {
              onClick: $event => (openMessages()),
              "aria-label": "Открыть сообщения"
            }, "Сообщения", 8, ["onClick"]),
            _createElementVNode("button", {
              class: "theme-toggle",
              onClick: toggleTheme,
              "aria-label": "Переключить тему"
            }, _toDisplayString(theme==='dark'?'Светлая тема':'Тёмная тема'), 9, ["onClick"]),
            _createElementVNode("span", { class: "user-name" }, _toDisplayString(user.display_name), 1),
            _createElementVNode("button", { onClick: signOut }, "Выйти", 8, ["onClick"])
          ]),
          _createElementVNode("div", { class: "app-body" }, [_createElementVNode("aside", { class: _normalizeClass(["sidebar", {collapsed:!navOpen}]) }, [
            _createElementVNode("div", { class: "sidebar-head" }, [_createElementVNode("small", null, "CONFIGURED VIEWS"), _createElementVNode("button", {
              onClick: reloadSidebar,
              title: "Перечитать widget_config"
            }, "↻", 8, ["onClick"])]),
            navError
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(navError), 1))
              : _createCommentVNode("", true),
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sidebar.sections, (section) => {
              return (_openBlock(), _createElementBlock("section", {
                key: section.view,
                class: "nav-section"
              }, [_createElementVNode("h2", null, _toDisplayString(section.title), 1), _createElementVNode("ul", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(section.children, (node) => {
                return (_openBlock(), _createBlock(_component_SidebarNode, {
                  key: node.id,
                  node: node,
                  selected: active,
                  folders: navFolders,
                  onFolder: folderChanged,
                  onOpen: open,
                  onContext: navMenu
                }, null, 8, ["node", "selected", "folders", "onFolder", "onOpen", "onContext"]))
              }), 128))])]))
            }), 128)),
            _createElementVNode("footer", { class: "sidebar-footer" }, [_createTextVNode("widget_config → native Vue"), _createElementVNode("br"), _createTextVNode("БД · project XML · DEFAULT")])
          ], 2), _createElementVNode("main", {
            class: "workspace",
            "aria-busy": restoringState
          }, [
            restoringState
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "notice",
                  role: "status"
                }, "Восстановление сохранённых представлений…"))
              : _createCommentVNode("", true),
            stateError
              ? (_openBlock(), _createElementBlock("p", {
                  key: 1,
                  class: "error state-sync-error",
                  role: "alert"
                }, [_createTextVNode(_toDisplayString(stateError) + " ", 1), _createElementVNode("button", {
                  class: "text-button",
                  onClick: $event => (stateError='')
                }, "Скрыть", 8, ["onClick"])]))
              : _createCommentVNode("", true),
            stateWarning
              ? (_openBlock(), _createElementBlock("p", {
                  key: 2,
                  class: "notice state-sync-error"
                }, [_createTextVNode(_toDisplayString(stateWarning) + " ", 1), _createElementVNode("button", {
                  class: "text-button",
                  onClick: $event => (stateWarning='')
                }, "Скрыть", 8, ["onClick"])]))
              : _createCommentVNode("", true),
            _createElementVNode("span", {
              class: "state-sync-status",
              role: "status",
              "aria-live": "polite"
            }, _toDisplayString(stateStatus), 1),
            _createElementVNode("div", { class: "workspace-tabbar" }, [_createElementVNode("nav", {
              class: "workspace-tabs",
              "aria-label": "Открытые представления"
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tabs, (tab) => {
              return (_openBlock(), _createElementBlock("div", {
                key: tab.id,
                class: _normalizeClass(["workspace-tab", {active:active===tab.id}])
              }, [_createElementVNode("button", {
                title: [tab.title,tab.config_view,tab.name].filter(Boolean).join(' / '),
                onClick: $event => (select(tab.id)),
                onContextmenu: $event => (navMenu({event:$event,node:tab},'tab')),
                onKeydown: $event => (($event.key==='ContextMenu'||($event.shiftKey&&$event.key==='F10'))&&navMenu({event:$event,node:tab,keyboard:true},'tab'))
              }, [_createTextVNode(_toDisplayString(tab.title), 1), (tab.dirty)
                ? (_openBlock(), _createElementBlock("span", { key: 0 }, " ●"))
                : _createCommentVNode("", true)], 40, ["title", "onClick", "onContextmenu", "onKeydown"]), _createElementVNode("button", {
                onClick: $event => (close(tab.id)),
                "aria-label": "Закрыть вкладку"
              }, "×", 8, ["onClick"])], 2))
            }), 128))]), current
              ? (_openBlock(), _createElementBlock("div", {
                  key: 0,
                  class: "workspace-actions",
                  role: "group",
                  "aria-label": "Действия открытого представления"
                }, [(current.kind==='form')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "workspace-action",
                      onClick: $event => (audit=true),
                      title: "Источник колонок",
                      "aria-label": "Источник колонок"
                    }, [(_openBlock(), _createElementBlock("svg", {
                      viewBox: "0 0 24 24",
                      "aria-hidden": "true"
                    }, [_createElementVNode("path", { d: "m8 6-6 6 6 6m8-12 6 6-6 6m-2-15-4 18" })]))], 8, ["onClick"]))
                  : _createCommentVNode("", true), (current.kind!=='table')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 1,
                      class: "workspace-action",
                      onClick: refresh,
                      disabled: busy||refreshing,
                      title: "Обновить представление",
                      "aria-label": "Обновить представление"
                    }, [(_openBlock(), _createElementBlock("svg", {
                      viewBox: "0 0 24 24",
                      "aria-hidden": "true"
                    }, [_createElementVNode("path", { d: "M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1" })]))], 8, ["onClick", "disabled"]))
                  : _createCommentVNode("", true), _createElementVNode("button", {
                  class: "workspace-action",
                  "aria-label": "Меню представления",
                  title: "Меню представления",
                  "aria-haspopup": "menu",
                  onClick: $event => (navMenu({event:$event,node:current,keyboard:true},'widget'))
                }, [(_openBlock(), _createElementBlock("svg", {
                  viewBox: "0 0 24 24",
                  "aria-hidden": "true"
                }, [_createElementVNode("circle", {
                  cx: "5",
                  cy: "12",
                  r: "1.5"
                }), _createElementVNode("circle", {
                  cx: "12",
                  cy: "12",
                  r: "1.5"
                }), _createElementVNode("circle", {
                  cx: "19",
                  cy: "12",
                  r: "1.5"
                })]))], 8, ["onClick"])]))
              : _createCommentVNode("", true)]),
            error
              ? (_openBlock(), _createElementBlock("p", {
                  key: 3,
                  class: "error global-error"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            (!current)
              ? (_openBlock(), _createElementBlock("section", {
                  key: 4,
                  class: "welcome",
                  "aria-label": sidebar.title||'Представления проекта'
                }, [_createElementVNode("p", null, "Разделы ниже собраны из конфигураций этого проекта. Откройте нужное представление в sidebar."), _createElementVNode("div", { class: "section-cards" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(mainSections, (s) => {
                  return (_openBlock(), _createElementBlock("article", { key: s.view }, [_createElementVNode("h2", null, _toDisplayString(s.title), 1), _createElementVNode("p", null, [_createElementVNode("code", null, _toDisplayString(s.view), 1)]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(childrenLinks(s).slice(0,10), (n) => {
                    return (_openBlock(), _createElementBlock("div", { key: n.id }, [(n.kind==='link')
                      ? (_openBlock(), _createElementBlock("button", {
                          key: 0,
                          class: "text-button",
                          onClick: $event => (open(n))
                        }, _toDisplayString(n.title) + " →", 9, ["onClick"]))
                      : (_openBlock(), _createElementBlock("span", {
                          key: 1,
                          class: "muted"
                        }, _toDisplayString(n.title), 1))]))
                  }), 128))]))
                }), 128))])], 8, ["aria-label"]))
              : (_openBlock(), _createElementBlock(_Fragment, { key: 5 }, [exporting
                  ? (_openBlock(), _createBlock(_component_CsvExport, {
                      key: project+active,
                      project: project,
                      target: active,
                      spec: current.spec,
                      query: timelineQuery,
                      "selected-keys": selected,
                      onClose: $event => (exporting=false)
                    }, null, 8, ["project", "target", "spec", "query", "selected-keys", "onClose"]))
                  : _createCommentVNode("", true), audit
                  ? (_openBlock(), _createBlock(_component_ConfigAudit, {
                      key: project+active,
                      project: project,
                      target: active,
                      onClose: $event => (audit=false)
                    }, null, 8, ["project", "target", "onClose"]))
                  : _createCommentVNode("", true), (current.kind==='table')
                  ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [(_openBlock(), _createBlock(_component_ConfiguredTable, {
                      key: current.id,
                      project: project,
                      target: active,
                      spec: current.spec,
                      rows: current.rows,
                      summaries: current.summaries,
                      busy: current.loading,
                      total: current.total,
                      offset: current.offset,
                      limit: current.limit,
                      presentation: tableMode,
                      "record-state": current.recordState,
                      "allow-writes": user.allow_writes,
                      "filter-count": tableFilterCount,
                      "search-open": searchOpen,
                      onTableAction: tableAction,
                      onSort: sort,
                      onPage: page,
                      onEdit: edit,
                      onInspect: inspect,
                      onChanged: loadPage,
                      onSelection: $event => (selected=$event),
                      onEditSelected: bulk,
                      onDirty: $event => (current.dirty=$event),
                      onViewChanged: refresh,
                      onOpen: open
                    }, {
                      filters: _withCtx(() => [
                        _createElementVNode("div", { class: "table-search-heading" }, [_createElementVNode("strong", null, "Поиск в представлении"), _createElementVNode("button", {
                          class: "text-button",
                          "aria-label": "Свернуть поиск",
                          onClick: $event => (searchOpen=false)
                        }, "×", 8, ["onClick"])]),
                        (current.spec.table_options?.show_keyword_search!==false)
                          ? (_openBlock(), _createElementBlock("div", {
                              key: 0,
                              class: "toolbar query-toolbar"
                            }, [
                              _withDirectives(_createElementVNode("select", {
                                "onUpdate:modelValue": $event => ((filterField) = $event),
                                "aria-label": "Поле быстрого фильтра"
                              }, [_createElementVNode("option", { value: "" }, "Поле фильтра…"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(fields, (f) => {
                                return (_openBlock(), _createElementBlock("option", {
                                  key: f.name,
                                  value: f.name
                                }, _toDisplayString(f.label), 9, ["value"]))
                              }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, filterField]]),
                              _withDirectives(_createElementVNode("select", {
                                "onUpdate:modelValue": $event => ((filterOp) = $event),
                                "aria-label": "Условие быстрого фильтра"
                              }, [
                                _createElementVNode("option", { value: "contains" }, "содержит"),
                                _createElementVNode("option", { value: "eq" }, "равно"),
                                _createElementVNode("option", { value: "ne" }, "не равно"),
                                _createElementVNode("option", { value: "gt" }, "больше"),
                                _createElementVNode("option", { value: "lt" }, "меньше"),
                                _createElementVNode("option", { value: "null" }, "NULL"),
                                _createElementVNode("option", { value: "not_null" }, "не NULL")
                              ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, filterOp]]),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": $event => ((filterValue) = $event),
                                placeholder: "Значение",
                                "aria-label": "Значение быстрого фильтра",
                                onKeyup: _withKeys(addFilter, ["enter"])
                              }, null, 40, ["onUpdate:modelValue", "onKeyup"]), [[_vModelText, filterValue]]),
                              _createElementVNode("button", {
                                onClick: addFilter,
                                disabled: !filterField
                              }, "Добавить фильтр", 8, ["onClick", "disabled"])
                            ]))
                          : _createCommentVNode("", true),
                        (current.filters.length)
                          ? (_openBlock(), _createElementBlock("div", {
                              key: 1,
                              class: "filter-chips"
                            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(current.filters, (f, i) => {
                              return (_openBlock(), _createElementBlock("button", {
                                key: i,
                                onClick: $event => (removeFilter(i))
                              }, _toDisplayString(f.field) + " " + _toDisplayString(f.op) + " " + _toDisplayString(f.value) + " ×", 9, ["onClick"]))
                            }), 128))]))
                          : _createCommentVNode("", true),
                        (current.spec.table_options?.show_search!==false)
                          ? (_openBlock(), _createBlock(_component_AdvancedFilter, {
                              key: current.id,
                              value: current.where,
                              fields: current.spec.fields,
                              "base-filter": current.options.filter,
                              onApply: advanced
                            }, null, 8, ["value", "fields", "base-filter", "onApply"]))
                          : _createCommentVNode("", true)
                      ]),
                      status: _withCtx(() => [(current.spec.write_notice)
                        ? (_openBlock(), _createElementBlock("p", {
                            key: 0,
                            class: "notice"
                          }, _toDisplayString(current.spec.write_notice), 1))
                        : _createCommentVNode("", true), (current.error)
                        ? (_openBlock(), _createElementBlock("p", {
                            key: 1,
                            class: "error"
                          }, _toDisplayString(current.error), 1))
                        : _createCommentVNode("", true)]),
                      alternate: _withCtx(() => [(tableMode==='collections')
                        ? (_openBlock(), _createBlock(_component_CollectionPanel, {
                            key: project+active,
                            project: project,
                            target: active,
                            "refresh-key": current.refreshKey,
                            "selected-keys": selected,
                            onChanged: loadPage,
                            onOpen: open
                          }, null, 8, ["project", "target", "refresh-key", "selected-keys", "onChanged", "onOpen"]))
                        : (tableMode==='timeline')
                          ? (_openBlock(), _createBlock(_component_TaskTimeline, {
                              key: current.id,
                              spec: current.spec,
                              project: project,
                              target: active,
                              query: timelineQuery,
                              "refresh-key": current.requestSeq,
                              onEdit: edit,
                              onInspect: inspect,
                              onDates: dates
                            }, null, 8, ["spec", "project", "target", "query", "refresh-key", "onEdit", "onInspect", "onDates"]))
                          : (tableMode==='tree')
                            ? (_openBlock(), _createBlock(_component_RelationTree, {
                                key: current.id,
                                project: project,
                                target: active,
                                spec: current.spec,
                                rows: current.rows,
                                summaries: current.summaries,
                                busy: current.loading,
                                total: current.total,
                                offset: current.offset,
                                limit: current.limit,
                                onInspect: inspectRelated,
                                onOpen: open,
                                onPage: page
                              }, null, 8, ["project", "target", "spec", "rows", "summaries", "busy", "total", "offset", "limit", "onInspect", "onOpen", "onPage"]))
                            : _createCommentVNode("", true)]),
                      _: 1
                    }, 8, ["project", "target", "spec", "rows", "summaries", "busy", "total", "offset", "limit", "presentation", "record-state", "allow-writes", "filter-count", "search-open", "onTableAction", "onSort", "onPage", "onEdit", "onInspect", "onChanged", "onSelection", "onEditSelected", "onDirty", "onViewChanged", "onOpen"])), (_openBlock(), _createBlock(_Teleport, { to: "body" }, [showSaveView
                      ? (_openBlock(), _createElementBlock("div", {
                          key: 0,
                          class: "modal-backdrop",
                          onClick: _withModifiers($event => (showSaveView=false), ["self"])
                        }, [_createElementVNode("form", {
                          class: "modal save-search-dialog",
                          role: "dialog",
                          "aria-label": "Сохранить поиск",
                          onSubmit: _withModifiers(saveView, ["prevent"])
                        }, [
                          _createElementVNode("header", null, [_createElementVNode("h2", null, "Сохранить поиск в sidebar"), _createElementVNode("button", {
                            type: "button",
                            "aria-label": "Закрыть сохранение поиска",
                            onClick: $event => (showSaveView=false)
                          }, "×", 8, ["onClick"])]),
                          _createElementVNode("label", null, [_createTextVNode("Название"), _withDirectives(_createElementVNode("input", {
                            "onUpdate:modelValue": $event => ((saveViewTitle) = $event),
                            placeholder: "Название личного представления",
                            required: ""
                          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, saveViewTitle]])]),
                          _createElementVNode("p", { class: "muted" }, "Представление сохраняется в исходный widget_config."),
                          _createElementVNode("button", { class: "primary" }, "Сохранить в widget_config")
                        ], 40, ["onSubmit"])], 8, ["onClick"]))
                      : _createCommentVNode("", true)]))], 64))
                  : (current.kind==='collections')
                    ? (_openBlock(), _createBlock(_component_CollectionPanel, {
                        key: project+active,
                        project: project,
                        target: active,
                        "refresh-key": current.refreshKey,
                        onChanged: configChanged,
                        onOpen: open
                      }, null, 8, ["project", "target", "refresh-key", "onChanged", "onOpen"]))
                    : (current.kind==='sidebar-editor')
                      ? (_openBlock(), _createBlock(_component_SidebarEditor, {
                          key: project+current.id+':'+(current.refreshKey||0),
                          project: project,
                          target: current.id,
                          "initial-view": current.options?.view||(project==='admin'?'admin_views':'project_view'),
                          user: user,
                          "allow-writes": user.allow_writes,
                          onDirty: $event => (current.dirty=$event),
                          onChanged: configChanged
                        }, null, 8, ["project", "target", "initial-view", "user", "allow-writes", "onDirty", "onChanged"]))
                      : (current.kind==='layout-editor')
                        ? (_openBlock(), _createBlock(_component_CustomLayoutEditor, {
                            key: project+current.id+':'+(current.refreshKey||0),
                            project: project,
                            target: current.id,
                            user: user,
                            onDirty: $event => (current.dirty=$event),
                            onOpen: open,
                            onChanged: configChanged
                          }, null, 8, ["project", "target", "user", "onDirty", "onOpen", "onChanged"]))
                        : (current.kind==='views-manager')
                          ? (_openBlock(), _createBlock(_component_ManageViews, {
                              key: project+current.id+':'+(current.refreshKey||0),
                              project: project,
                              target: current.id,
                              screen: current,
                              user: user,
                              onDirty: $event => (current.dirty=$event),
                              onOpen: open,
                              onChanged: configChanged
                            }, null, 8, ["project", "target", "screen", "user", "onDirty", "onOpen", "onChanged"]))
                          : (current.kind==='custom-layout')
                            ? (_openBlock(), _createBlock(_component_LayoutPreview, {
                                key: project+current.id+':'+(current.refreshKey||0),
                                parts: current.layout.parts,
                                children: current.layout.children,
                                project: project,
                                user: user,
                                onDirty: $event => (current.dirty=$event),
                                onOpen: open,
                                onChanged: configChanged
                              }, null, 8, ["parts", "children", "project", "user", "onDirty", "onOpen", "onChanged"]))
                            : (current.kind==='config-editor')
                              ? (_openBlock(), _createBlock(_component_ConfigEditor, {
                                  key: project+current.id+':'+(current.refreshKey||0),
                                  project: project,
                                  mode: current.kind,
                                  "initial-view": current.options.view==='my_view'?'my_view_'+user.login:current.options.view||(project==='admin'?'admin_views':'project_view'),
                                  "allow-writes": user.allow_writes,
                                  onChanged: configChanged
                                }, null, 8, ["project", "mode", "initial-view", "allow-writes", "onChanged"]))
                              : (['system-config','license'].includes(current.kind))
                                ? (_openBlock(), _createBlock(_component_GlobalSettings, {
                                    key: project+current.id+':'+(current.refreshKey||0),
                                    project: project,
                                    target: current.id,
                                    kind: current.kind,
                                    onDirty: $event => (current.dirty=$event)
                                  }, null, 8, ["project", "target", "kind", "onDirty"]))
                                : (['pipeline','schema'].includes(current.kind))
                                  ? (_openBlock(), _createBlock(_component_GraphEditor, {
                                      key: project+current.id+':'+(current.refreshKey||0),
                                      project: project,
                                      kind: current.kind,
                                      target: current.id,
                                      onDirty: $event => (current.dirty=$event)
                                    }, null, 8, ["project", "kind", "target", "onDirty"]))
                                  : (current.kind==='script-editor')
                                    ? (_openBlock(), _createBlock(_component_ScriptEditor, {
                                        key: project+current.id+':'+(current.refreshKey||0),
                                        project: project,
                                        target: current.id,
                                        onDirty: $event => (current.dirty=$event),
                                        onOpen: open
                                      }, null, 8, ["project", "target", "onDirty", "onOpen"]))
                                    : (current.kind==='search-types')
                                      ? (_openBlock(), _createBlock(_component_SearchTypes, {
                                          key: project+current.id+':'+(current.refreshKey||0),
                                          project: project,
                                          target: current.id,
                                          screen: current,
                                          user: user,
                                          "allow-writes": user.allow_writes,
                                          onDirty: $event => (current.dirty=$event),
                                          onOpen: open,
                                          onChanged: configChanged
                                        }, null, 8, ["project", "target", "screen", "user", "allow-writes", "onDirty", "onOpen", "onChanged"]))
                                      : (current.kind==='group-membership')
                                        ? (_openBlock(), _createBlock(_component_GroupMembership, {
                                            key: project+current.id+':'+(current.refreshKey||0),
                                            project: project,
                                            target: current.id,
                                            "initial-key": current.options?.search_key,
                                            onChanged: configChanged
                                          }, null, 8, ["project", "target", "initial-key", "onChanged"]))
                                        : (current.kind==='message-center')
                                          ? (_openBlock(), _createBlock(_component_MessageCenter, {
                                              key: project+current.id+':'+(current.refreshKey||0),
                                              project: project,
                                              target: current.id,
                                              options: current.options,
                                              login: user.login,
                                              onClose: $event => (close(current.id))
                                            }, null, 8, ["project", "target", "options", "login", "onClose"]))
                                          : (['users','groups'].includes(current.kind))
                                            ? (_openBlock(), _createBlock(_component_UserManager, {
                                                key: project+current.id+':'+(current.refreshKey||0),
                                                project: project,
                                                target: current.id,
                                                screen: current,
                                                mode: current.kind,
                                                user: user,
                                                onDirty: $event => (current.dirty=$event),
                                                onChanged: configChanged,
                                                onOpen: open
                                              }, null, 8, ["project", "target", "screen", "mode", "user", "onDirty", "onChanged", "onOpen"]))
                                            : (current.kind==='group-assignment'&&current.handler.endsWith('GroupAssignWdg'))
                                              ? (_openBlock(), _createBlock(_component_UserGroups, {
                                                  key: project+current.id+':'+(current.refreshKey||0),
                                                  project: project,
                                                  target: current.id,
                                                  "initial-key": current.options?.search_key,
                                                  onDirty: $event => (current.dirty=$event),
                                                  onChanged: configChanged
                                                }, null, 8, ["project", "target", "initial-key", "onDirty", "onChanged"]))
                                              : (['security','group-assignment'].includes(current.kind))
                                                ? (_openBlock(), _createBlock(_component_SecurityMatrix, {
                                                    key: project+current.id+':'+(current.refreshKey||0),
                                                    project: project,
                                                    target: current.id,
                                                    screen: current,
                                                    user: user,
                                                    onDirty: $event => (current.dirty=$event),
                                                    onChanged: configChanged,
                                                    onOpen: open
                                                  }, null, 8, ["project", "target", "screen", "user", "onDirty", "onChanged", "onOpen"]))
                                                : (['project-create','system'].includes(current.kind))
                                                  ? (_openBlock(), _createBlock(_component_AdminPanel, {
                                                      key: project+current.id+':'+(current.refreshKey||0),
                                                      project: project,
                                                      target: current.id,
                                                      kind: current.kind,
                                                      "initial-key": current.options?.search_key,
                                                      onDirty: $event => (current.dirty=$event),
                                                      onChanged: projectChanged
                                                    }, null, 8, ["project", "target", "kind", "initial-key", "onDirty", "onChanged"]))
                                                  : (['tabs','form'].includes(current.kind))
                                                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 19 }, [], 64))
                                                    : (_openBlock(), _createElementBlock("section", {
                                                        key: 20,
                                                        class: "unsupported-panel"
                                                      }, [
                                                        _createElementVNode("span", { class: "eyebrow" }, "НЕПЕРЕНЕСЁННЫЙ ОБРАБОТЧИК"),
                                                        _createElementVNode("h2", null, _toDisplayString(current.title), 1),
                                                        _createElementVNode("p", null, "Эта ссылка присутствует в исходном widget_config. Её специализированный экран пока не реализован на Vue и не заменяется произвольной таблицей."),
                                                        _createElementVNode("dl", null, [
                                                          _createElementVNode("dt", null, "Класс"),
                                                          _createElementVNode("dd", null, [_createElementVNode("code", null, _toDisplayString(current.handler), 1)]),
                                                          _createElementVNode("dt", null, "View конфигурации"),
                                                          _createElementVNode("dd", null, _toDisplayString(current.config_view), 1)
                                                        ]),
                                                        _createElementVNode("details", null, [_createElementVNode("summary", null, "Параметры из конфигурации"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(current.options,null,2)), 1)])
                                                      ]))], 64)),
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tabs.filter(t=>['tabs','form'].includes(t.kind)), (tab) => {
              return _withDirectives((_openBlock(), _createBlock(_component_WidgetHost, {
                key: tab.id+':'+(tab.refreshKey||0),
                project: project,
                target: tab.id,
                initial: tab,
                user: user,
                active: active===tab.id,
                onDirty: $event => (tab.dirty=$event),
                onOpen: open,
                onClose: $event => (close(tab.id)),
                onChanged: configChanged
              }, null, 8, ["project", "target", "initial", "user", "active", "onDirty", "onOpen", "onClose", "onChanged"])), [[_vShow, active===tab.id]])
            }), 128))
          ], 8, ["aria-busy"]), (inspected&&current?.spec)
            ? (_openBlock(), _createBlock(_component_RecordInspector, {
                key: inspected.key+':'+(inspected._section||'fields'),
                project: project,
                target: active,
                record: inspected,
                spec: current.spec,
                "allow-uploads": user.allow_uploads,
                onClose: $event => (inspected=null),
                onEdit: edit,
                onOpen: open,
                onChanged: recordChanged,
                onMessages: openMessages
              }, null, 8, ["project", "target", "record", "spec", "allow-uploads", "onClose", "onEdit", "onOpen", "onChanged", "onMessages"]))
            : _createCommentVNode("", true)]),
          (_openBlock(), _createBlock(_Teleport, { to: "body" }, [messagesOpen
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "modal-backdrop message-backdrop"
              }, [(_openBlock(), _createBlock(_component_MessageCenter, {
                key: project+messageCode,
                project: project,
                "initial-code": messageCode,
                login: user.login,
                onClose: $event => (messagesOpen=false)
              }, null, 8, ["project", "initial-code", "login", "onClose"]))]))
            : _createCommentVNode("", true)])),
          menu
            ? (_openBlock(), _createBlock(_component_ContextMenu, {
                key: 1,
                menu: menu,
                onAction: navAction,
                onClose: $event => {menu=null;menuSeq++}
              }, null, 8, ["menu", "onAction", "onClose"]))
            : _createCommentVNode("", true),
          widgetDefinition
            ? (_openBlock(), _createBlock(_component_WidgetDefinition, {
                key: 2,
                project: project,
                target: widgetDefinition,
                onClose: $event => (widgetDefinition=null)
              }, null, 8, ["project", "target", "onClose"]))
            : _createCommentVNode("", true),
          (_openBlock(), _createBlock(_Teleport, { to: "body" }, [popup
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "modal-backdrop widget-popup-backdrop"
              }, [_createElementVNode("section", {
                class: "modal widget-popup",
                role: "dialog",
                "aria-modal": "true"
              }, [_createElementVNode("header", null, [_createElementVNode("h2", null, _toDisplayString(popup.title), 1), _createElementVNode("button", {
                onClick: closePopup,
                "aria-label": "Закрыть отдельную панель"
              }, "×", 8, ["onClick"])]), _createVNode(_component_WidgetHost, {
                project: project,
                target: popup.id,
                user: user,
                onDirty: $event => (popupDirty=$event),
                onClose: closePopup,
                onOpen: open,
                onChanged: configChanged
              }, null, 8, ["project", "target", "user", "onDirty", "onClose", "onOpen", "onChanged"])])]))
            : _createCommentVNode("", true), sidebarEditor
            ? (_openBlock(), _createElementBlock("div", {
                key: 1,
                class: "modal-backdrop"
              }, [_createElementVNode("section", { class: "modal widget-popup" }, [_createElementVNode("header", null, [_createElementVNode("h2", null, "Sidebar · " + _toDisplayString(sidebarEditor), 1), _createElementVNode("button", { onClick: $event => (sidebarEditor=null) }, "×", 8, ["onClick"])]), _createVNode(_component_SidebarEditor, {
                project: project,
                "initial-view": sidebarEditor,
                user: user,
                "allow-writes": user.allow_writes,
                onDirty: $event => (popupDirty=$event),
                onChanged: configChanged
              }, null, 8, ["project", "initial-view", "user", "allow-writes", "onDirty", "onChanged"])])]))
            : _createCommentVNode("", true)])),
          designer
            ? (_openBlock(), _createBlock(_component_ViewDesigner, {
                key: 3,
                project: project,
                "search-type": designer.searchType,
                "initial-view": designer.view,
                login: user.login,
                onClose: $event => (designer=null),
                onSaved: designed
              }, null, 8, ["project", "search-type", "initial-view", "login", "onClose", "onSaved"]))
            : _createCommentVNode("", true),
          form
            ? (_openBlock(), _createBlock(_component_ConfiguredForm, {
                key: form.record?.key||'insert',
                project: project,
                target: form.target,
                form: form,
                busy: saving||previewBusy||previewFailed,
                error: formError,
                onPreview: previewForm,
                onDirty: $event => (formDirty=$event),
                onSave: save,
                onClose: $event => (form=null)
              }, null, 8, ["project", "target", "form", "busy", "error", "onPreview", "onDirty", "onSave", "onClose"]))
            : _createCommentVNode("", true)
        ]))
  }
};
return __component;
})();
const app=Vue.createApp(App);
app.component('CsvImportPanel', CsvImportPanel);
app.component('CodeEditor', CodeEditor);
app.component('LayoutPreview', LayoutPreview);
app.component('CustomLayoutEditor', CustomLayoutEditor);
app.component('ManageViews', ManageViews);
app.component('ContextMenu', ContextMenu);
app.component('TableToolbar', TableToolbar);
app.component('TableColumns', TableColumns);
app.component('WidgetDefinition', WidgetDefinition);
app.component('SidebarNode', SidebarNode);
app.component('WidgetCell', WidgetCell);
app.component('ConfigAudit', ConfigAudit);
app.component('CsvExport', CsvExport);
app.component('FieldInput', FieldInput);
app.component('ConfiguredForm', ConfiguredForm);
app.component('CollectionPanel', CollectionPanel);
app.component('WorkHoursPanel', WorkHoursPanel);
app.component('ConfiguredTable', ConfiguredTable);
app.component('FilterGroup', FilterGroup);
app.component('AdvancedFilter', AdvancedFilter);
app.component('RelationTreeRow', RelationTreeRow);
app.component('RelationTree', RelationTree);
app.component('TaskPanel', TaskPanel);
app.component('RelationshipEditor', RelationshipEditor);
app.component('HistoryPanel', HistoryPanel);
app.component('ConfigEditor', ConfigEditor);
app.component('GraphEditor', GraphEditor);
app.component('MessageContent', MessageContent);
app.component('MessageCenter', MessageCenter);
app.component('SubscriptionPanel', SubscriptionPanel);
app.component('UploadQueue', UploadQueue);
app.component('FilePanel', FilePanel);
app.component('RecordInspector', RecordInspector);
app.component('GroupMembership', GroupMembership);
app.component('SearchTypes', SearchTypes);
app.component('ViewDesigner', ViewDesigner);
app.component('TaskTimeline', TaskTimeline);
app.component('ScriptEditor', ScriptEditor);
app.component('ProjectWizard', ProjectWizard);
app.component('SecurityMatrix', SecurityMatrix);
app.component('UserGroups', UserGroups);
app.component('UserManager', UserManager);
app.component('SidebarEditor', SidebarEditor);
app.component('AdminPanel', AdminPanel);
app.component('GlobalSettings', GlobalSettings);
app.component('EmbeddedForm', EmbeddedForm);
app.component('WidgetTable', WidgetTable);
app.component('ConfiguredTabs', ConfiguredTabs);
app.component('WidgetHost', WidgetHost);
app.mount('#app');
})();
