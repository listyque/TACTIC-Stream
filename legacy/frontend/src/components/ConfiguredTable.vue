<script>
import api from '../api.js';
import uiState from '../uiState.js';
import TableToolbar from './TableToolbar.vue';
import TableColumns from './TableColumns.vue';
import ContextMenu from './ContextMenu.vue';
import WidgetDefinition from './WidgetDefinition.vue';
import WidgetCell from './WidgetCell.vue';
import FieldInput from './FieldInput.vue';
import WorkHoursPanel from './WorkHoursPanel.vue';

// The grid keeps ORIGINAL values and drafts separate. Editing only stages an
// input; Save Changes submits one batch through TACTIC's EditMultipleCmd.
export default {
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
</script>
<template>
<section class="table-region native-grid" :class="['density-'+density,{'wrap-cells':wrap,'is-resizing':resizeState}]" :aria-busy="busy||saving" @keydown="hotkeys" :data-table-target="target">
 <TableToolbar :spec="spec" :total="total" :selected-count="selected.length" :busy="busy||saving" :allow-writes="allowWrites" :search-open="searchOpen" :filter-count="filterCount" :presentation="presentation" :display-mode="mode" :record-state="recordState" :density="density" :wrap="wrap" :group-field="groupField" :dirty="dirty" :saving="saving" @action="toolbarAction"/>
 <div v-show="searchOpen&&(flags.show_search!==false||flags.show_keyword_search!==false)" class="table-search-panel"><slot name="filters"></slot></div>
 <slot name="status"></slot>
 <div v-if="dirty" class="grid-save-bar" role="status"><span class="pending-indicator"></span><strong>{{changedCells}} ячеек · {{changedRows.length}} строк</strong><span v-if="editor">Редактор открыт</span><small v-if="pendingOutsidePage">Вне страницы: {{pendingOutsidePage}} строк</small><span class="spacer"></span><button :disabled="saving" @click="discard">Отменить</button><button class="primary" :disabled="saving||loadingEditor" @click="saveAll">{{saving?'Сохранение…':'Сохранить изменения'}} <kbd>Ctrl S</kbd></button></div>
 <p v-if="error" class="error grid-feedback" role="alert">{{error}}</p><p v-if="notice" class="notice grid-feedback" role="status">{{notice}}</p><p v-if="loadingEditor" class="grid-feedback muted">Загрузка редактора из widget_config…</p>
 <div v-show="presentation==='data'" class="grid-content">
 <div v-if="mode==='table'" class="table-scroll grid-viewport"><table class="tactic-data-grid" role="grid" :aria-rowcount="total" :style="{width:gridWidth+'px',minWidth:'100%'}">
  <colgroup><col v-if="flags.show_select" style="width:42px"><col v-for="f in fields" :key="f.name" :style="{width:widthNumber(f)+'px'}"></colgroup>
  <thead v-if="flags.show_header"><tr><th v-if="flags.show_select" class="check-cell pinned-check"><input type="checkbox" :checked="allSelected" :indeterminate="selected.length>0&&!allSelected" @change="toggleAll" aria-label="Выбрать всю страницу"></th><th v-for="f in fields" :key="f.name" :style="columnStyle(f)" :class="{'pinned-column':pinned.includes(f.name)}" :title="f.handler||f.name" tabindex="0" @contextmenu="context($event,null,f)" @keydown="menuKey($event,null,f)" draggable="true" @dragstart="dragColumn=f.name" @dragover.prevent @drop.prevent="dropColumn(f)" @dragend="dragColumn=null"><div class="grid-column-heading"><button :disabled="!f.storage||f.sortable===false" :title="f.sort_reason||''" @click="$emit('sort',f.name)"><span>{{f.label}}</span><small v-if="!f.supported" class="unsupported-marker">◦</small></button><button class="column-menu-trigger" :aria-label="'Меню колонки '+f.label" @click="context($event,null,f)">⋮</button></div><span class="column-resizer" role="separator" aria-orientation="vertical" :aria-label="'Ширина '+f.label" @pointerdown="startResize($event,f)" @click.stop @dblclick.stop="delete widths[f.name];persistGeometry()"></span></th></tr></thead>
  <tbody><template v-for="group in groups" :key="group.key"><tr v-if="groupField" class="group-row"><td :colspan="fields.length+(flags.show_select?1:0)">{{group.key}} <span class="counter">{{group.rows.length}}</span><small>Текущая страница</small></td></tr><template v-for="row in group.rows" :key="row.key"><tr :class="{selected:selected.includes(row.key),'modified-row':drafts[row.key],'conflict-row':drafts[row.key]?.error}" @contextmenu="context($event,row)" tabindex="0" @keydown="menuKey($event,row)" :data-key="row.key"><td v-if="flags.show_select" class="check-cell pinned-check"><input type="checkbox" :checked="selected.includes(row.key)" @click="selectRow($event,row)" aria-label="Выбрать запись"></td><td v-for="f in fields" :key="f.name" :class="{'not-supported':!f.supported,'modified-cell':hasDraft(row,f),'active-cell':activeCell?.key===row.key&&activeCell?.field===f.name,'pinned-column':pinned.includes(f.name)}" :style="columnStyle(f)" :data-row="row.key" :data-field="f.name" :title="drafts[row.key]?.error||f.reason||cell(row,f)" tabindex="0" @focus="activeCell={key:row.key,field:f.name}" @keydown="gridKey($event,row,f)" @dblclick.stop="inline(row,f)">
   <div v-if="editor?.key===row.key&&editor.field.name===f.name" class="inline-editor" @keydown="editorKey"><FieldInput :field="editor.field" v-model="editor.value"/><div class="inline-actions"><button v-if="editor.field.nullable" class="null-input-button" @click="editor.value=null" title="Явное пустое значение">NULL</button><button class="primary" @click="stageCell" title="Применить в буфер, без записи в БД">Применить</button><button @click="cancelEditor" aria-label="Отменить ввод">×</button></div><small class="editor-source">edit → edit_item · Ctrl S — сохранить</small></div>
   <button v-else-if="f.renderer==='work-hours'" class="text-button" @click.stop="hours={row,field:f.name}">Открыть рабочее время</button><WidgetCell v-else :row="displayRow(row)" :field="f" :fallback="cell(row,f)" @open="cellOpen(row,$event)"/><span v-if="hasDraft(row,f)" class="dirty-corner" aria-label="Не сохранено"></span>
  </td></tr><tr v-if="expanded[row.key]" class="expanded-widget-row"><td :colspan="fields.length+(flags.show_select?1:0)"><button class="text-button" @click="expanded[row.key]=null">Свернуть</button><WidgetHost :project="project" :target="expanded[row.key]" :user="{allow_writes:spec.capabilities.update,allow_uploads:false}" @open="$emit('open',$event)" @changed="$emit('changed')"/></td></tr></template></template><tr v-if="!rows.length"><td :colspan="fields.length+1" class="table-empty"><strong>{{busy?'Загрузка данных…':(spec.table_options?.empty_message||'Нет записей')}}</strong><span v-if="!busy">Измените фильтры или добавьте запись через форму TACTIC.</span></td></tr></tbody>
  <tfoot v-if="summaries?.length"><tr><td v-if="flags.show_select"></td><td v-for="f in fields" :key="f.name" class="summary-cell"><template v-if="summary(f)"><small>{{summary(f).label}}</small>{{summary(f).cell.text}}</template></td></tr></tfoot>
 </table></div>
 <div v-else class="cards-scroll"><section v-for="group in groups" :key="group.key"><h3 v-if="groupField">{{group.key}} · {{group.rows.length}}</h3><div class="entity-cards"><article v-for="row in group.rows" :key="row.key" class="entity-card" :class="{selected:selected.includes(row.key)}" @contextmenu="context($event,row)"><header><input v-if="flags.show_select" type="checkbox" :checked="selected.includes(row.key)" @click="selectRow($event,row)"><button class="text-button" @click="$emit('inspect',row)">{{cardTitle(row)}}</button></header><dl><template v-for="f in fields" :key="f.name"><dt>{{f.label}}</dt><dd><button v-if="f.renderer==='work-hours'" class="text-button" @click="hours={row,field:f.name}">Рабочее время</button><WidgetCell v-else :row="displayRow(row)" :field="f" :fallback="cell(row,f)" @open="cellOpen(row,$event)"/></dd></template></dl><button :disabled="!spec.capabilities.update" @click="$emit('edit',row)">Редактировать</button></article></div></section></div>
 <footer class="pager grid-footer"><span>{{total??'—'}} записей <span v-if="selected.length">· Выбрано {{selected.length}}</span></span><small v-if="groupField||summaries?.length">Группы и итоги страницы · только сохранённые данные</small><span class="spacer"></span><small class="grid-keyboard-hint">F2 — ввод · Enter — применить · Ctrl S — сохранить</small><button v-if="flags.show_search_limit" :disabled="busy||saving||offset===0" @click="$emit('page',Math.max(0,offset-limit))" aria-label="Предыдущая страница">←</button><span>{{rows.length?offset+1:0}}–{{offset+rows.length}}</span><button v-if="flags.show_search_limit" :disabled="busy||saving||rows.length<limit||(total!==null&&offset+rows.length>=total)" @click="$emit('page',offset+limit)" aria-label="Следующая страница">→</button></footer>
 </div><slot v-if="presentation!=='data'" name="alternate"></slot>
 <Teleport to="body"><div v-if="fill" class="modal-backdrop" @click.self="closeFill"><section class="modal fill-selected-dialog" role="dialog" aria-modal="true" aria-label="Заполнить выбранные ячейки" @keydown.esc.stop="closeFill"><header><div><small>{{fill.rows.length}} выбранных строк · CellEditWdg</small><h2>Заполнить выбранные ячейки</h2></div><button :disabled="fill.busy" aria-label="Закрыть заполнение" @click="closeFill">×</button></header><div class="form-scroll"><p class="notice">Одинаковое значение проверяется по конфигурации каждой строки. Сначала предпросмотр, затем буфер; запись только через Save Changes.</p><label>Поле<select v-model="fill.name" :disabled="fill.busy" @change="loadFillField" aria-label="Поле заполнения"><option v-for="f in fillFields" :key="f.name" :value="f.name">{{f.label}} · {{f.name}}</option></select></label><div v-if="fill.field"><label>Значение</label><FieldInput :field="fill.field" :model-value="fill.value" @update:model-value="changeFill"/><button v-if="fill.field.nullable" class="null-button" :disabled="fill.busy" @click="changeFill(null)">Установить NULL</button></div><p v-if="fill.error" class="error" role="alert">{{fill.error}}</p><div v-if="fill.preview" class="fill-preview"><p>{{fill.preview.notice}}</p><div class="table-scroll"><table><thead><tr><th>Запись</th><th>Было / буфер</th><th>Станет</th></tr></thead><tbody><tr v-for="item in fill.preview.items" :key="item.key"><td>{{item.key}}</td><td>{{fillText(Object.hasOwn(drafts[item.key]?.values||{},fill.name)?drafts[item.key].values[fill.name]:item.original)}}</td><td>{{fillText(item.value)}}</td></tr></tbody></table></div></div></div><footer><button :disabled="fill.busy" @click="closeFill">Отмена</button><button :disabled="fill.busy||!fill.field" @click="previewFill">{{fill.busy?'Проверка…':'Предпросмотр'}}</button><button class="primary" :disabled="fill.busy||!fill.preview" @click="acceptFill">Применить в буфер</button></footer></section></div></Teleport>
 <TableColumns v-if="columnsOpen" :fields="spec.fields" :hidden="hidden" :pinned="pinned" @close="columnsOpen=false" @toggle="toggleColumn" @pin="togglePin" @reset="resetGeometry"/>
 <Teleport to="body"><div v-if="diagnosticsOpen" class="modal-backdrop" @click.self="diagnosticsOpen=false"><section class="modal table-diagnostics" role="dialog" aria-label="Ограничения виджетов"><header><h2>Ограничения виджетов</h2><button @click="diagnosticsOpen=false" aria-label="Закрыть ограничения">×</button></header><p v-if="!spec.diagnostics?.length">В текущем представлении нет диагностик неподдержанных колонок.</p><div v-for="(d,i) in spec.diagnostics" :key="i"><code>{{d.field}} · {{d.handler}}</code><p>{{d.reason}}</p></div><small>Отсутствие диагностик не означает полного совпадения всех пользовательских обработчиков с legacy.</small></section></div></Teleport>
 <Teleport to="body"><div v-if="cellWindow" class="modal-backdrop" @click.self="cellWindow=null"><section class="modal wide"><header><h2>{{cellWindow.title}}</h2><button @click="cellWindow=null;$emit('changed')">×</button></header><WidgetHost :project="project" :target="cellWindow.target" :user="{allow_writes:spec.capabilities.update,allow_uploads:false}" @close="cellWindow=null" @open="$emit('open',$event)" @changed="$emit('changed')"/></section></div><WorkHoursPanel v-if="hours" :project="project" :target="target" :record="hours.row" :task="hours.row" :field="hours.field" @close="hours=null" @changed="$emit('changed')"/><ContextMenu v-if="menu" :menu="menu" @action="act" @close="menu=null;menuSeq++"/><WidgetDefinition v-if="definition!==null" :project="project" :target="target" :field="definition" @close="definition=null"/><ConfigAudit v-if="audit" :project="project" :target="target" @close="audit=false"/><ViewDesigner v-if="designer!==null" :project="project" :search-type="spec.type" :initial-view="spec.view" :initial-element="designer" @close="designer=null" @saved="$emit('view-changed')"/></Teleport>
</section>
</template>
