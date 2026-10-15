<script>
import SidebarEditor from './components/SidebarEditor.vue';
import UserManager from './components/UserManager.vue';
import UserGroups from './components/UserGroups.vue';
import SecurityMatrix from './components/SecurityMatrix.vue';
import api from './api.js';
import uiState from './uiState.js';
import WidgetHost from './components/WidgetHost.vue';
import GlobalSettings from './components/GlobalSettings.vue';
import ContextMenu from './components/ContextMenu.vue';
import WidgetDefinition from './components/WidgetDefinition.vue';
import ScriptEditor from './components/ScriptEditor.vue';
import CollectionPanel from './components/CollectionPanel.vue';
import AdvancedFilter from './components/AdvancedFilter.vue';
import RelationTree from './components/RelationTree.vue';
import SidebarNode from './components/SidebarNode.vue';
import CsvExport from './components/CsvExport.vue';
import ConfigAudit from './components/ConfigAudit.vue';
import ConfiguredTable from './components/ConfiguredTable.vue';
import ConfiguredForm from './components/ConfiguredForm.vue';
import ConfigEditor from './components/ConfigEditor.vue';
import GraphEditor from './components/GraphEditor.vue';
import RecordInspector from './components/RecordInspector.vue';
import GroupMembership from './components/GroupMembership.vue';
import SearchTypes from './components/SearchTypes.vue';
import ViewDesigner from './components/ViewDesigner.vue';
import TaskTimeline from './components/TaskTimeline.vue';
import AdminPanel from './components/AdminPanel.vue';
import MessageCenter from './components/MessageCenter.vue';
export default {
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
</script>
<template>
<div v-if="!user" class="login-screen"><form class="login-card" @submit.prevent="signIn"><div class="brand">TACTIC <span>5.0 / VUE</span></div><button type="button" class="theme-toggle login-theme" @click="toggleTheme">{{theme==='dark'?'Светлая тема':'Тёмная тема'}}</button><h1>Вход в TACTIC</h1><p>Настоящая учётная запись сервера. Демонстрационной базы здесь нет.</p><label>Логин<input v-model="login" autocomplete="username" required autofocus></label><label>Пароль<input v-model="password" type="password" autocomplete="current-password" required></label><label>Код подтверждения<input v-model="twoFactor" inputmode="numeric" autocomplete="one-time-code"></label><p v-if="error" class="error">{{error}}</p><button class="primary" :disabled="loginBusy">{{loginBusy?'Вход…':'Войти'}}</button><small>Native UI пока доступен администраторам.</small></form></div>
<div v-else class="application"><div v-if="user.mode==='test-fixture'" class="fixture-banner">TEST FIXTURE · Меню из исходных XML TACTIC. Записи тестовые, не PostgreSQL.</div>
 <header class="app-header"><button class="nav-toggle" @click="navOpen=!navOpen" aria-label="Открыть меню">☰</button><a class="brand" href="#" @click.prevent="select('')">TACTIC <span>5.0 / VUE</span></a><div class="project-picker"><small>PROJECT</small><select v-model="project" @change="switchProject" aria-label="Проект"><option v-for="p in projects" :key="p.code" :value="p.code">{{p.name}}</option></select></div><span class="spacer"></span><span v-if="!user.allow_writes" class="read-only">Запись отключена</span><button @click="openMessages()" aria-label="Открыть сообщения">Сообщения</button><button class="theme-toggle" @click="toggleTheme" aria-label="Переключить тему">{{theme==='dark'?'Светлая тема':'Тёмная тема'}}</button><span class="user-name">{{user.display_name}}</span><button @click="signOut">Выйти</button></header>
 <div class="app-body">
  <aside class="sidebar" :class="{collapsed:!navOpen}"><div class="sidebar-head"><small>CONFIGURED VIEWS</small><button @click="reloadSidebar" title="Перечитать widget_config">↻</button></div><p v-if="navError" class="error">{{navError}}</p><section v-for="section in sidebar.sections" :key="section.view" class="nav-section"><h2>{{section.title}}</h2><ul><SidebarNode v-for="node in section.children" :key="node.id" :node="node" :selected="active" :folders="navFolders" @folder="folderChanged" @open="open" @context="navMenu"/></ul></section><footer class="sidebar-footer">widget_config → native Vue<br>БД · project XML · DEFAULT</footer></aside>
  <main class="workspace" :aria-busy="restoringState">
   <p v-if="restoringState" class="notice" role="status">Восстановление сохранённых представлений…</p>
<p v-if="stateError" class="error state-sync-error" role="alert">{{stateError}} <button class="text-button" @click="stateError=''">Скрыть</button></p><p v-if="stateWarning" class="notice state-sync-error">{{stateWarning}} <button class="text-button" @click="stateWarning=''">Скрыть</button></p><span class="state-sync-status" role="status" aria-live="polite">{{stateStatus}}</span>
<div class="workspace-tabbar"><nav class="workspace-tabs" aria-label="Открытые представления"><div v-for="tab in tabs" :key="tab.id" class="workspace-tab" :class="{active:active===tab.id}"><button :title="[tab.title,tab.config_view,tab.name].filter(Boolean).join(' / ')" @click="select(tab.id)" @contextmenu="navMenu({event:$event,node:tab},'tab')" @keydown="($event.key==='ContextMenu'||($event.shiftKey&&$event.key==='F10'))&&navMenu({event:$event,node:tab,keyboard:true},'tab')">{{tab.title}}<span v-if="tab.dirty"> ●</span></button><button @click="close(tab.id)" aria-label="Закрыть вкладку">×</button></div></nav><div v-if="current" class="workspace-actions" role="group" aria-label="Действия открытого представления">
 <button v-if="current.kind==='form'" class="workspace-action" @click="audit=true" title="Источник колонок" aria-label="Источник колонок"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 6-6 6 6 6m8-12 6 6-6 6m-2-15-4 18"/></svg></button>
 <button v-if="current.kind!=='table'" class="workspace-action" @click="refresh" :disabled="busy||refreshing" title="Обновить представление" aria-label="Обновить представление"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/></svg></button>
 <button class="workspace-action" aria-label="Меню представления" title="Меню представления" aria-haspopup="menu" @click="navMenu({event:$event,node:current,keyboard:true},'widget')"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg></button>
</div></div>
   <p v-if="error" class="error global-error">{{error}}</p>
   <section v-if="!current" class="welcome" :aria-label="sidebar.title||'Представления проекта'"><p>Разделы ниже собраны из конфигураций этого проекта. Откройте нужное представление в sidebar.</p><div class="section-cards"><article v-for="s in mainSections" :key="s.view"><h2>{{s.title}}</h2><p><code>{{s.view}}</code></p><div v-for="n in childrenLinks(s).slice(0,10)" :key="n.id"><button v-if="n.kind==='link'" class="text-button" @click="open(n)">{{n.title}} →</button><span v-else class="muted">{{n.title}}</span></div></article></div></section>
   <template v-else>
    <CsvExport v-if="exporting" :key="project+active" :project="project" :target="active" :spec="current.spec" :query="timelineQuery" :selected-keys="selected" @close="exporting=false"/><ConfigAudit v-if="audit" :key="project+active" :project="project" :target="active" @close="audit=false"/>
    <template v-if="current.kind==='table'">
     <ConfiguredTable :key="current.id" :project="project" :target="active" :spec="current.spec" :rows="current.rows" :summaries="current.summaries" :busy="current.loading" :total="current.total" :offset="current.offset" :limit="current.limit" :presentation="tableMode" :record-state="current.recordState" :allow-writes="user.allow_writes" :filter-count="tableFilterCount" :search-open="searchOpen" @table-action="tableAction" @sort="sort" @page="page" @edit="edit" @inspect="inspect" @changed="loadPage" @selection="selected=$event" @edit-selected="bulk" @dirty="current.dirty=$event" @view-changed="refresh" @open="open">
      <template #filters>
       <div class="table-search-heading"><strong>Поиск в представлении</strong><button class="text-button" aria-label="Свернуть поиск" @click="searchOpen=false">×</button></div>
       <div v-if="current.spec.table_options?.show_keyword_search!==false" class="toolbar query-toolbar"><select v-model="filterField" aria-label="Поле быстрого фильтра"><option value="">Поле фильтра…</option><option v-for="f in fields" :key="f.name" :value="f.name">{{f.label}}</option></select><select v-model="filterOp" aria-label="Условие быстрого фильтра"><option value="contains">содержит</option><option value="eq">равно</option><option value="ne">не равно</option><option value="gt">больше</option><option value="lt">меньше</option><option value="null">NULL</option><option value="not_null">не NULL</option></select><input v-model="filterValue" placeholder="Значение" aria-label="Значение быстрого фильтра" @keyup.enter="addFilter"><button @click="addFilter" :disabled="!filterField">Добавить фильтр</button></div>
       <div v-if="current.filters.length" class="filter-chips"><button v-for="(f,i) in current.filters" :key="i" @click="removeFilter(i)">{{f.field}} {{f.op}} {{f.value}} ×</button></div>
       <AdvancedFilter v-if="current.spec.table_options?.show_search!==false" :key="current.id" :value="current.where" :fields="current.spec.fields" :base-filter="current.options.filter" @apply="advanced"/>
      </template>
      <template #status><p v-if="current.spec.write_notice" class="notice">{{current.spec.write_notice}}</p><p v-if="current.error" class="error">{{current.error}}</p></template>
      <template #alternate>
       <CollectionPanel v-if="tableMode==='collections'" :key="project+active" :project="project" :target="active" :refresh-key="current.refreshKey" :selected-keys="selected" @changed="loadPage" @open="open"/>
       <TaskTimeline v-else-if="tableMode==='timeline'" :key="current.id" :spec="current.spec" :project="project" :target="active" :query="timelineQuery" :refresh-key="current.requestSeq" @edit="edit" @inspect="inspect" @dates="dates"/>
       <RelationTree v-else-if="tableMode==='tree'" :key="current.id" :project="project" :target="active" :spec="current.spec" :rows="current.rows" :summaries="current.summaries" :busy="current.loading" :total="current.total" :offset="current.offset" :limit="current.limit" @inspect="inspectRelated" @open="open" @page="page"/>
      </template>
     </ConfiguredTable>
     <Teleport to="body"><div v-if="showSaveView" class="modal-backdrop" @click.self="showSaveView=false"><form class="modal save-search-dialog" role="dialog" aria-label="Сохранить поиск" @submit.prevent="saveView"><header><h2>Сохранить поиск в sidebar</h2><button type="button" aria-label="Закрыть сохранение поиска" @click="showSaveView=false">×</button></header><label>Название<input v-model="saveViewTitle" placeholder="Название личного представления" required></label><p class="muted">Представление сохраняется в исходный widget_config.</p><button class="primary">Сохранить в widget_config</button></form></div></Teleport>
    </template>
    <CollectionPanel v-else-if="current.kind==='collections'" :key="project+active" :project="project" :target="active" :refresh-key="current.refreshKey" @changed="configChanged" @open="open"/>
    <SidebarEditor v-else-if="current.kind==='sidebar-editor'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :initial-view="current.options?.view||(project==='admin'?'admin_views':'project_view')" :user="user" :allow-writes="user.allow_writes" @dirty="current.dirty=$event" @changed="configChanged"/>
 <CustomLayoutEditor v-else-if="current.kind==='layout-editor'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :user="user" @dirty="current.dirty=$event" @open="open" @changed="configChanged"/>
 <ManageViews v-else-if="current.kind==='views-manager'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :screen="current" :user="user" @dirty="current.dirty=$event" @open="open" @changed="configChanged"/>
 <LayoutPreview v-else-if="current.kind==='custom-layout'" :key="project+current.id+':'+(current.refreshKey||0)" :parts="current.layout.parts" :children="current.layout.children" :project="project" :user="user" @dirty="current.dirty=$event" @open="open" @changed="configChanged"/>
    <ConfigEditor v-else-if="current.kind==='config-editor'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :mode="current.kind" :initial-view="current.options.view==='my_view'?'my_view_'+user.login:current.options.view||(project==='admin'?'admin_views':'project_view')" :allow-writes="user.allow_writes" @changed="configChanged"/>
    <GlobalSettings v-else-if="['system-config','license'].includes(current.kind)" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :kind="current.kind" @dirty="current.dirty=$event"/>
    <GraphEditor v-else-if="['pipeline','schema'].includes(current.kind)" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :kind="current.kind" :target="current.id" @dirty="current.dirty=$event"/>
    <ScriptEditor v-else-if="current.kind==='script-editor'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" @dirty="current.dirty=$event" @open="open"/>
    <SearchTypes v-else-if="current.kind==='search-types'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :screen="current" :user="user" :allow-writes="user.allow_writes" @dirty="current.dirty=$event" @open="open" @changed="configChanged"/>
    <GroupMembership v-else-if="current.kind==='group-membership'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :initial-key="current.options?.search_key" @changed="configChanged"/>
    <MessageCenter v-else-if="current.kind==='message-center'" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :options="current.options" :login="user.login" @close="close(current.id)"/>
    <UserManager v-else-if="['users','groups'].includes(current.kind)" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :screen="current" :mode="current.kind" :user="user" @dirty="current.dirty=$event" @changed="configChanged" @open="open"/>
    <UserGroups v-else-if="current.kind==='group-assignment'&&current.handler.endsWith('GroupAssignWdg')" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :initial-key="current.options?.search_key" @dirty="current.dirty=$event" @changed="configChanged"/>
    <SecurityMatrix v-else-if="['security','group-assignment'].includes(current.kind)" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :screen="current" :user="user" @dirty="current.dirty=$event" @changed="configChanged" @open="open"/>
    <AdminPanel v-else-if="['project-create','system'].includes(current.kind)" :key="project+current.id+':'+(current.refreshKey||0)" :project="project" :target="current.id" :kind="current.kind" :initial-key="current.options?.search_key" @dirty="current.dirty=$event" @changed="projectChanged"/>
    <template v-else-if="['tabs','form'].includes(current.kind)"></template>
    <section v-else class="unsupported-panel"><span class="eyebrow">НЕПЕРЕНЕСЁННЫЙ ОБРАБОТЧИК</span><h2>{{current.title}}</h2><p>Эта ссылка присутствует в исходном widget_config. Её специализированный экран пока не реализован на Vue и не заменяется произвольной таблицей.</p><dl><dt>Класс</dt><dd><code>{{current.handler}}</code></dd><dt>View конфигурации</dt><dd>{{current.config_view}}</dd></dl><details><summary>Параметры из конфигурации</summary><pre>{{JSON.stringify(current.options,null,2)}}</pre></details></section>
   </template>
   <template v-for="tab in tabs.filter(t=>['tabs','form'].includes(t.kind))" :key="tab.id"><WidgetHost v-show="active===tab.id" :key="tab.id+':'+(tab.refreshKey||0)" :project="project" :target="tab.id" :initial="tab" :user="user" :active="active===tab.id" @dirty="tab.dirty=$event" @open="open" @close="close(tab.id)" @changed="configChanged"/></template>
  </main>
  <RecordInspector v-if="inspected&&current?.spec" :key="inspected.key+':'+(inspected._section||'fields')" :project="project" :target="active" :record="inspected" :spec="current.spec" :allow-uploads="user.allow_uploads" @close="inspected=null" @edit="edit" @open="open" @changed="recordChanged" @messages="openMessages"/>
 </div>
 <Teleport to="body"><div v-if="messagesOpen" class="modal-backdrop message-backdrop"><MessageCenter :key="project+messageCode" :project="project" :initial-code="messageCode" :login="user.login" @close="messagesOpen=false"/></div></Teleport>
 <ContextMenu v-if="menu" :menu="menu" @action="navAction" @close="menu=null;menuSeq++"/><WidgetDefinition v-if="widgetDefinition" :project="project" :target="widgetDefinition" @close="widgetDefinition=null"/>
 <Teleport to="body"><div v-if="popup" class="modal-backdrop widget-popup-backdrop"><section class="modal widget-popup" role="dialog" aria-modal="true"><header><h2>{{popup.title}}</h2><button @click="closePopup" aria-label="Закрыть отдельную панель">×</button></header><WidgetHost :project="project" :target="popup.id" :user="user" @dirty="popupDirty=$event" @close="closePopup" @open="open" @changed="configChanged"/></section></div><div v-if="sidebarEditor" class="modal-backdrop"><section class="modal widget-popup"><header><h2>Sidebar · {{sidebarEditor}}</h2><button @click="sidebarEditor=null">×</button></header><SidebarEditor :project="project" :initial-view="sidebarEditor" :user="user" :allow-writes="user.allow_writes" @dirty="popupDirty=$event" @changed="configChanged"/></section></div></Teleport>
 <ViewDesigner v-if="designer" :project="project" :search-type="designer.searchType" :initial-view="designer.view" :login="user.login" @close="designer=null" @saved="designed"/>
 <ConfiguredForm v-if="form" :key="form.record?.key||'insert'" :project="project" :target="form.target" :form="form" :busy="saving||previewBusy||previewFailed" :error="formError" @preview="previewForm" @dirty="formDirty=$event" @save="save" @close="form=null"/>
</div>
</template>
