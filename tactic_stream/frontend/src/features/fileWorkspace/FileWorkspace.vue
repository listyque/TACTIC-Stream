<script>
import { markRaw } from 'vue'
import interaction, { changeTreeRows } from './interaction.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppCheckBox from '../../controls/AppCheckBox.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import AppTabButton from '../../controls/AppTabButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import FileWorkspaceTree from './FileWorkspaceTree.vue'
import FileWorkspaceLog from './FileWorkspaceLog.vue'
import FileWorkspaceInspector from './FileWorkspaceInspector.vue'
import FileWorkspaceMappings from './FileWorkspaceMappings.vue'
import { operationTitle, userError } from './log.js'
import { logEvent, redact } from '../debug/debugLog.js'
import WorkspaceTabs from '../../controls/WorkspaceTabs.vue'
import { copyText } from '../../controls/clipboard.js'
import { randomId as requestId } from '../../controls/identity.js'
import { prettySize } from '../checkin/files.js'
const viewPresets=[
  {id:'files',title:'Files',kind:'files',source:'selection',icon:'file'},
  {id:'pending',title:'Pending',kind:'changes',state:'pending',states:['pending','shelved'],icon:'clock'},
  {id:'submitted',title:'Submitted',kind:'changes',state:'submitted',icon:'check'},
  {id:'history',title:'History',kind:'history',icon:'history'},
  {id:'shelved',title:'Shelved',kind:'changes',state:'shelved',icon:'archive'},
  {id:'reverted',title:'Reverted',kind:'changes',state:'reverted',icon:'undo'},
  {id:'conflicts',title:'Conflicts',kind:'conflicts',icon:'warning'},
  {id:'tasks',title:'Transfers',kind:'tasks',icon:'cloud-upload'},
]
export default {
  mixins:[interaction],
  components:{WorkspaceTabs,AppButton,AppSelect,AppCheckBox,AppTextField,AppTextArea,AppSplitter,AppMenu,AppMenuItem,AppTabButton,AppIcon,FileWorkspaceTree,FileWorkspaceLog,FileWorkspaceInspector,FileWorkspaceMappings},
  props:{ticket:String,project:String,login:String,canAdminister:Boolean},emits:['help','ready','debug'],
  data(){return {tabs:viewPresets.slice(0,4).map(tab=>({...tab})),activeTabId:'pending',treeView:'depot',workspaceTree:[],workspaceRoot:'',filesContext:{stream:'',prefix:'',source:'depot'},tabDraft:{},tabEditing:false,
    busy:false,error:'',notice:'',operationLog:[],logSequence:0,operationName:'',workspaces:[],streams:[],depots:[],changes:[],tasks:[],workspace:'',activeRevision:0,
    change:null,description:'',state:'pending',view:'change',rows:[],after:null,cursors:[],pageCursor:'',changesAfter:null,workspaceAfter:null,streamAfter:null,
    selected:[],locks:{},history:[],historyPath:'',preview:'',comparison:null,conflicts:[],conflictsAfter:null,resolvedConflicts:[],conflictSelection:[],showResolved:false,review:null,reviewOperation:'submit',reviewPaths:[],reviewRequest:{},shelves:[],shelvesAfter:null,shelfChoice:'',shelfOperation:'compare_shelf',taskFiles:[],taskFilesAfter:null,progress:{},tasksAfter:null,
    depotTree:[],depotHeads:{},treeSelection:'',changeChildren:{},expandedChanges:[],
    depotAfter:null,prefix:'',published:null,historyStream:'',width:320,detailsHeight:220,setup:false,setupOriginal:null,editingWorkspace:false,caseSensitive:true,mappingPreview:null,samplePath:'',setupKind:'workspace',code:'',root:'',stream:'',depot:'',mappings:'',target:'',shelf:'',source:'',aborter:null,disposed:false,monitor:null,polling:false,storage:null,policy:{},gc:null,storageOpen:false,detailsView:'history',detail:null,treeOpen:false,editorKind:'description',draft:''}},
  computed:{viewPresets(){return viewPresets},activeTab(){return this.tabs.find(tab=>tab.id===this.activeTabId) || {}},
    reviewTitle(){return {submit:'Review submit',merge_begin:'Review integration',unshelve_begin:'Review integration',rebase_begin:'Review integration',compare_shelf:'Compare pending with shelf'}[this.reviewOperation] || 'Review shelving'},
    detailTab(){return ['history','conflicts','tasks'].includes(this.activeTab.kind)},ws(){return this.workspaces.find(item=>item.code===this.workspace)},pending(){return this.change?.state==='pending'},editable(){return this.canAdminister && this.pending && this.change.depot_writable!==false && this.change.owner===this.login && this.change.workspace===this.workspace && !this.change.active_transfer && !this.change.active_bulk},
    integration(){const job=this.change?.integration;return job?{change:this.change.code,edit_revision:this.change.edit_revision,integration:job.code}:null},
    workspaceOptions(){return this.workspaces.map(item=>({value:item.code,label:item.code+' · '+item.stream}))},
    streamOptions(){return this.streams.map(item=>({value:item.code,label:item.code}))},
    stateOptions(){return ['pending','submitted','shelved','reverted'].map(value=>({value,label:{pending:'Pending',submitted:'Submitted',shelved:'Shelved',reverted:'Reverted'}[value]}))},
    viewOptions(){return [{value:'selection',label:'Selected tree'},{value:'change',label:'Changelist files'},{value:'depot',label:'Depot files'},{value:'have',label:'Have'}]},
    dirty(){return !!this.change && this.description!==this.change.description},
    changeTree(){return changeTreeRows(this.changes,this.changeChildren,this.expandedChanges).filter(row=>['change','more'].includes(row.kind)||(!this.nameFilter||row.path.toLowerCase().includes(this.nameFilter.toLowerCase()))&&(!this.statusFilter||this.badges(row).some(badge=>badge.label===this.statusFilter)))},
  },
  watch:{error(value){if(value&&this.operationLog.at(-1)?.message!==t(value))this.appendLog('WARNING',t(value))},detail(){this.preview=''},detailsView(){this.preview=''},setup:{flush:'sync',handler(value){if(value)this.setupOriginal={root:this.root,stream:this.stream,mappings:this.mappings,caseSensitive:this.caseSensitive,code:this.code,source:this.source,depot:this.depot};else if(this.setupOriginal){Object.assign(this,this.setupOriginal);this.setupOriginal=null}this.$nextTick(()=>value?this.$refs.setupDialog.showModal():this.$refs.setupDialog.close())}},storageOpen(value){this.$nextTick(()=>value?this.$refs.storageDialog.showModal():this.$refs.storageDialog.close())},width(){this.rememberGeometry()},detailsHeight(){this.rememberGeometry()},treeView(){this.rememberGeometry()}},
  mounted(){try{const saved=JSON.parse(localStorage.getItem(`file-workspace/${this.login}/${this.project}`));if(saved){if(Array.isArray(saved.tabs)){this.tabs=saved.tabs.slice(0,32);this.activeTabId=saved.activeTabId || saved.tabs[0]?.id || ''}this.filesContext=saved.filesContext || this.filesContext;this.fileFocus=saved.fileFocus || null;this.depotExpanded=saved.depotExpanded || [];this.workspaceExpanded=saved.workspaceExpanded || [];this.viewStates=saved.viewStates || {};this.restoreView(this.activeTabId);this.treeView=saved.treeView || 'depot';this.width=Math.max(220,Math.min(600,saved.width || 280));this.detailsHeight=Math.max(140,Math.min(600,saved.detailsHeight || 220))}}catch{}this.load().then(()=>{const reference=new URLSearchParams(location.search).get('changelist');if(reference&&!this.error)this.gotoChange(reference)});this.monitor=setInterval(()=>this.pollTasks(),2000);window.addEventListener('beforeunload',this.beforeUnload);this.$emit('ready')},
  beforeUnmount(){this.captureView();this.disposed=true;this.aborter?.abort();this.pollAborter?.abort();clearInterval(this.monitor);window.removeEventListener('beforeunload',this.beforeUnload)},
  methods:{t,prettySize,confirm:message=>window.confirm(message),
    tabTitle(tab){return tab.custom?tab.title:t(tab.title)},
    async activateTab(tab){
      if(this.busy || !this.canLeave())return
      this.captureView();this.restoreView(tab.id);this.activeTabId=tab.id;this.detail=null;this.rememberGeometry()
      if(tab.kind==='files'){this.view=tab.source==='selection'?this.filesContext.source:tab.source || 'depot';this.stream=this.filesContext.stream || this.stream;this.prefix=tab.source==='selection'?(tab.prefix || this.filesContext.prefix):(tab.prefix || '');await this.showFiles()}
      else if(tab.kind==='changes'){this.view='change';this.state=tab.state;if(!(tab.states || [tab.state]).includes(this.change?.state)){this.change=null;this.description='';this.selected=[]}await this.run(async client=>{await this.changePage(client);if(this.change)await this.filesPage(client)})}
      else {this.detailsView=tab.kind;if(tab.kind==='history'&&!tab.pinned&&this.fileFocus){this.historyPath=this.fileFocus.path;this.historyStream=this.fileFocus.stream}if(tab.kind==='history'&&this.historyPath)await this.historyFor({path:this.historyPath,stream:this.historyStream});else if(tab.kind==='conflicts')await this.run(client=>this.loadConflicts(client))}
    },
    async openView(id){const preset=viewPresets.find(tab=>tab.id===id);if(!preset || this.busy)return;let tab=this.tabs.find(tab=>tab.id===id);if(!tab){tab={...preset};this.tabs.push(tab)}await this.activateTab(tab)},
    async closeTab(id=this.activeTabId){if(this.busy)return;const active=this.activeTabId===id;if(active&&!this.canLeave())return;this.captureView();delete this.viewStates[id];this.tabs=this.tabs.filter(tab=>tab.id!==id);if(active)this.activeTabId='';this.rememberGeometry();if(active&&this.tabs.length)await this.activateTab(this.tabs[0])},
    reorderTabs(from,to){if(this.busy||from<0||to<0||from>=this.tabs.length||to>=this.tabs.length)return;const tab=this.tabs.splice(from,1)[0];this.tabs.splice(to,0,tab);this.rememberGeometry()},
    moveTab(direction){const index=this.tabs.findIndex(tab=>tab.id===this.activeTabId),target=index+direction;if(this.busy||target<0||target>=this.tabs.length)return;const tab=this.tabs.splice(index,1)[0];this.tabs.splice(target,0,tab);this.rememberGeometry()},
    editTab(creating){const current=creating?viewPresets[0]:this.activeTab;const preset=viewPresets.find(tab=>tab.kind===current.kind&&(tab.kind!=='changes'||tab.state===current.state)) || viewPresets[0];this.tabDraft={id:creating?'':current.id,title:creating?'':current.title,preset:preset.id,source:current.source || 'depot',prefix:current.prefix || '',scope:current.scope || 'mine',pinned:current.pinned || false};this.$refs.tabEditor.showModal()},
    async saveTab(){if(this.busy||!this.tabDraft.title.trim()||this.tabs.length>=32&&!this.tabDraft.id)return;const preset=viewPresets.find(tab=>tab.id===this.tabDraft.preset),tab={...preset,...this.tabDraft,id:this.tabDraft.id || requestId(),title:this.tabDraft.title.trim().slice(0,120),custom:true};const index=this.tabs.findIndex(row=>row.id===tab.id);if(index<0)this.tabs.push(tab);else this.tabs[index]=tab;this.$refs.tabEditor.close();await this.activateTab(tab)},
    async copyChangeLink(){try{await copyText(new URL('/projects/'+encodeURIComponent(this.project)+'/?changelist='+encodeURIComponent(this.change.code),location.origin).href)}catch(error){this.error=error.message}},
    async copyChange(){try{await copyText('#'+(this.change.number || this.change.code))}catch(error){this.error=error.message}},

    openEditor(kind){this.editorKind=kind;this.draft=kind==='description'?this.description:'';this.$refs.editor.showModal()},
    async saveEditor(){if(this.editorKind==='goto'){await this.gotoChange(this.draft)}else if(this.editorKind==='description'){this.description=this.draft;await this.mutate('update_change',{description:this.description})}else if(this.editorKind==='offer'){await this.mutate('offer_change',{recipient:this.draft})}else if(this.editorKind==='rename'){await this.renameSelected()}else if(this.editorKind==='move'){this.target=this.draft;await this.move()}else await this.integrationBegin(this.editorKind==='merge'?'merge_begin':'unshelve_begin',this.editorKind==='merge'?{source_stream:this.draft}:{shelf:this.draft});if(!this.error)this.$refs.editor.close()},
    fileMenu(event,row){this.rowMenu(event,'files',row)},

    beforeUnload(event){this.captureView();if(this.busy||this.dirty){event.preventDefault();event.returnValue=''}},
    rememberGeometry(){try{localStorage.setItem(`file-workspace/${this.login}/${this.project}`,JSON.stringify({width:this.width,detailsHeight:this.detailsHeight,filesContext:this.filesContext,fileFocus:this.fileFocus,depotExpanded:this.depotTree.filter(row=>row.expanded).map(row=>row.id),workspaceExpanded:this.workspaceTree.filter(row=>row.expanded).map(row=>row.id),tabs:this.tabs,activeTabId:this.activeTabId,treeView:this.treeView,viewStates:Object.fromEntries(Object.entries(this.viewStates).map(([id,state])=>[id,Object.fromEntries(Object.entries({...state,changeRef:state.change?.code || state.changeRef,selectionRecords:Object.fromEntries(Object.entries(state.selectionRecords || {}).map(([id,row])=>[id,Object.fromEntries(Object.entries(row).filter(([key])=>['id','path','source_path','local_path','stream','parent','kind','workspace','code','change','number','deleted'].includes(key)))]))}).filter(([key])=>['historyPath','historyStream','changeRef','selectionIds','selectionScope','selectionQuery','selectionRecords','anchorId','focusId','selected','expandedChanges','prefix','stream','view','state','columns','sortColumn','sortDesc','nameFilter','statusFilter','scroll'].includes(key)))]))}))}catch{}},
    canLeave(){return !this.busy && (!this.dirty || window.confirm(t('Discard the unsaved changelist description?')))},
    appendLog(level,message,path=''){this.operationLog.push({id:++this.logSequence,time:new Date().toLocaleTimeString(),level,operation:this.operationName || t('File operation'),message:redact(message),path:redact(path)});if(this.operationLog.length>1000)this.operationLog.shift()},
    async copyLog(){try{await copyText(this.operationLog.map(entry=>[entry.time,entry.operation,entry.message,entry.path].filter(Boolean).join(' · ')).join('\n'))}catch(error){this.reportFailure(error)}},
    reportFailure(error){const summary=userError(error);this.appendLog(summary.level,summary.message,summary.path);this.error=summary.message;logEvent({level:summary.level==='INFO'?'LOG':summary.level,group:'file-workspace',source:'File workspace',message:String(error.message || error),stacktrace:error.stack || '',details:this.operationName})},
    async run(operation){if(this.busy)return;this.busy=true;this.error='';this.notice='';this.operationName=t('File operation');this.aborter=markRaw(new AbortController());let started=false;const client={call:(action,values={})=>{if(!started){started=true;this.operationName=operationTitle(action);this.appendLog('INFO',t('Started'))}return this.command(action,values)}}
      try{const result=await operation(client);if(!this.disposed)this.appendLog('INFO',t('Completed'));return result}catch(error){if(!this.disposed)this.reportFailure(error)}
      finally{if(!this.disposed){this.busy=false;this.$nextTick(()=>{const table=this.$el?.querySelector('.file-workspace-table');if(table)table.scrollTop=this.scroll.files || 0});if(this.progress.state==='resolving')this.progress={...this.progress,state:this.integration?'Awaiting conflict resolution':'complete'}}}},
    async command(action,values={},signal=this.aborter?.signal) {
      const deadline=performance.now()+120000,previous=this.progress;let waiting=false
      try{while(true){
        signal?.throwIfAborted();if(this.disposed)throw new DOMException('Workspace closed','AbortError')
        const response=await fetch('/file-project/command?'+new URLSearchParams({project:this.project}),{method:'POST',signal,headers:{'Content-Type':'application/json','X-Tactic-Ticket':this.ticket},body:JSON.stringify({action,...values})})
        const body=await response.json()
        if(response.status===503 && response.headers.get('X-Tactic-Error')==='file_project_busy' && performance.now()<deadline){
          if(this.busy){this.progress={...previous,state:'Waiting for server'};waiting=true}
          await new Promise(resolve=>setTimeout(resolve,1000));continue
        }
        if(!response.ok)throw new Error(body.error || response.statusText);return body
      }}finally{if(waiting&&!this.disposed&&this.progress.state==='Waiting for server')this.progress=previous}
    },
    async pollTasks(){
      if(this.busy||this.polling||this.disposed||!this.tasks.some(item=>['collecting','queued','running','streaming'].includes(item.state)))return
      this.polling=true;this.pollAborter=markRaw(new AbortController())
      try{const page=await this.command('transfer_tasks',{limit:200},this.pollAborter.signal);if(!this.disposed&&!this.busy){this.tasks=page.items;this.tasksAfter=page.after;const active=page.items.find(item=>item.task===this.progress.task);if(active)this.progress=active}}
      catch(error){if(!this.disposed&&error.name!=='AbortError'&&this.error!==userError(error).message)this.reportFailure(error)}finally{this.polling=false}
    },
    async storageStatus(){await this.run(async client=>{this.storage=await client.call('storage_status');this.policy=Object.fromEntries(['bytes_limit','files_limit','max_parallel','upload_retention_seconds','reverted_retention_seconds','task_retention_seconds','shelf_retention_seconds','gc_grace_seconds','gc_interval_seconds'].map(key=>[key,this.storage[key]]));this.storageOpen=true})},
    async savePolicy(){await this.run(async client=>{const policy=Object.fromEntries(Object.entries(this.policy).map(([key,value])=>[key,Number(value)]));if(Object.values(policy).some(value=>!Number.isSafeInteger(value)||value<0))throw new Error('Storage values must be non-negative safe integers.');this.storage=await client.call('storage_policy',{revision:this.storage.revision,policy})})},
    async startGc(dry_run){if(!dry_run&&!window.confirm(t('Run safe GC using the configured retention policy?')))return;await this.run(async client=>{this.gc=await client.call('gc_begin',{dry_run})})},
    async gcStatus(){await this.run(async client=>{this.gc=await client.call('gc_status',{task:this.gc.code})})},
    depotRoots(){
      this.workspaceRoot='';this.workspaceTree=this.workspace?[{id:'workspace/'+this.workspace,kind:'workspace',name:this.workspace,depth:0,directory:'',expanded:false}]:[]
      this.depotHeads={};this.depotTree=this.depots.flatMap(item=>[
        {id:'depot/'+item.code,kind:'depot',name:item.code,depth:0,expanded:true},
        ...this.streams.filter(row=>row.depot===item.code).map(row=>({id:'stream/'+row.code,kind:'stream',name:row.code,depth:1,stream:row.code,directory:'',expanded:false}))])
    },
    async depotBranch(node,more=false){await this.run(client=>this.depotBranchPage(client,node,more))},
    async depotBranchPage(client,node,more=false){
      const index=this.depotTree.findIndex(row=>row.id===node.id);let end=index+1
      while(end<this.depotTree.length&&this.depotTree[end].depth>node.depth)end++
      if(node.expanded&&!more){this.depotTree.splice(index+1,end-index-1);node.expanded=false;return}
      let children
      if(node.kind==='depot')children=this.streams.filter(row=>row.depot===node.name).map(row=>({id:'stream/'+row.code,kind:'stream',name:row.code,depth:node.depth+1,stream:row.code,directory:'',expanded:false}))
      else{
        const page=await client.call('browse',{stream:node.stream,directory:node.directory,limit:200,...(this.depotHeads[node.stream]?{published_change:this.depotHeads[node.stream]}:{}),...(more?{after:node.after}:{})})
        this.depotHeads[node.stream]=page.published_change;node.after=page.after
        children=page.items.map(row=>({...row,id:'path/'+node.stream+'/'+row.path,depth:node.depth+1,stream:node.stream,directory:row.kind==='directory'?row.path:'',expanded:false}))
        if(page.after)children.push({id:node.id+'//more',kind:'more',depth:node.depth+1,parent:node.id})
      }
      if(more){const position=this.depotTree.findIndex(row=>row.parent===node.id&&row.kind==='more');this.depotTree.splice(position,1,...children)}
      else this.depotTree.splice(index+1,end-index-1,...children)
      node.expanded=true
    },
    async workspaceBranch(node,more=false){await this.run(client=>this.workspaceBranchPage(client,node,more))},
    async workspaceBranchPage(client,node,more=false){
      const index=this.workspaceTree.findIndex(row=>row.id===node.id);let end=index+1
      while(end<this.workspaceTree.length&&this.workspaceTree[end].depth>node.depth)end++
      if(node.expanded&&!more){this.workspaceTree.splice(index+1,end-index-1);node.expanded=false;return}
      const page=await client.call('workspace_browse',{workspace:this.workspace,directory:node.directory,root:this.workspaceRoot || null,limit:200,...(more?{after:node.after}:{})})
      this.workspaceRoot=page.root;node.after=page.after;node.expanded=true
      const children=page.items.map(row=>({...row,id:'workspace-path/'+row.path,depth:node.depth+1,directory:row.kind==='directory'?row.path:'',expanded:false,workspace:true}))
      if(page.after)children.push({id:node.id+'//more',kind:'more',parent:node.id,depth:node.depth+1,workspace:true})
      if(more){const position=this.workspaceTree.findIndex(row=>row.parent===node.id&&row.kind==='more');this.workspaceTree.splice(position,1,...children)}else this.workspaceTree.splice(index+1,end-index-1,...children)
    },
    async workspaceSelect(node){if(node.kind==='more')return this.workspaceBranch(this.workspaceTree.find(row=>row.id===node.parent),true);if(node.kind==='file'){this.treeSelection=node.id;this.historyPath=node.source_path || node.path;this.historyStream=node.stream || this.stream;this.history=[];return}this.filesContext={prefix:node.directory,stream:this.stream,source:'have'};this.treeSelection=node.id;if(this.activeTab.kind==='files'){this.view=this.activeTab.source==='selection'?'have':this.activeTab.source;this.prefix=this.activeTab.source==='selection'?(this.activeTab.prefix || node.directory):(this.activeTab.prefix || '');await this.showFiles()}},
    async depotSelect(node){
      if(node.kind==='more')return this.depotBranch(this.depotTree.find(row=>row.id===node.parent),true)
      if(node.kind==='depot')return this.depotBranch(node)
      if(node.kind==='file'){this.treeSelection=node.id;this.historyPath=node.source_path || node.path;this.historyStream=node.stream || this.stream;this.history=[];return}
      this.filesContext={stream:node.stream,prefix:node.directory,source:'depot'};this.treeSelection=node.id
      if(this.activeTab.kind==='files')await this.run(async client=>{this.stream=node.stream;this.view=this.activeTab.source==='selection'?'depot':this.activeTab.source;this.prefix=this.activeTab.source==='selection'?(this.activeTab.prefix || node.directory):(this.activeTab.prefix || '');this.cursors=[];await this.filesPage(client)})
    },
    async changeBranch(node,more=false){await this.run(async client=>{
      if(this.expandedChanges.includes(node.code)&&!more){this.expandedChanges=this.expandedChanges.filter(code=>code!==node.code);delete this.changeChildren[node.code];return}
      await this.changeBranchPage(client,node,more)
    })},
    async changeBranchPage(client,node,more=false){
      const previous=this.changeChildren[node.code],page=await client.call(node.editable===false?'inspect_change_files':'change_files',{[node.state==='shelved'?'shelf':'change']:node.code,limit:200,
        ...(node.state==='pending'&&more?{edit_revision:previous.edit_revision}:{}),...(more?{after:previous.after}:{})})
      if(page.info){const clean=!this.dirty;Object.assign(node,page.info);if(this.change?.code===node.code){this.change={...this.change,...page.info};if(clean)this.description=this.change.description || ''}}
      await this.fileStates(client,page.items,node.stream);await this.pageLocks(client,page.items,node.stream)
      // shortcut: retain 1000 loaded children; whole queries use server selections.
      if(more)page.items=[...previous.items,...page.items].slice(-1000)
      this.changeChildren[node.code]=page;if(!this.expandedChanges.includes(node.code))this.expandedChanges.push(node.code)
    },
    async changeSelect(node){
      if(node.kind==='more')return this.changeBranch(this.changes.find(row=>row.code===node.parent),true)
      if(node.kind==='change')return this.selectChange(node)
      this.detailsView='history';return this.historyFor(node)
    },
    async changeFileSelection(row,checked){
      if(this.change?.code!==row.parent){
        const page=this.changeChildren[row.parent]
        await this.selectChange(this.changes.find(item=>item.code===row.parent))
        if(this.change?.code!==row.parent || this.error)return
        if(page.edit_revision!==this.change.edit_revision){this.error='Changelist changed; refresh the file list.';return}
        this.changeChildren[row.parent]=page
      }
      this.toggle(row.path,checked)
    },
    async changeFileMenu(event,row){
      await this.changeFileSelection(row,true)
      if(!this.error && this.change?.code===row.parent)this.$refs.fileMenu.openAt(event)
    },
    async catalog(client){
      const [ws,streams,depots,active,tasks]=await Promise.all([client.call('workspaces'),client.call('streams'),client.call('depots'),client.call('workspace_active'),client.call('transfer_tasks',{limit:200})])
      this.workspaces=ws.items;this.workspaceAfter=ws.after;this.streams=streams.items;this.streamAfter=streams.after;this.depots=depots.items;this.depotAfter=depots.after;this.tasks=tasks.items;this.tasksAfter=tasks.after
      this.depotRoots()
      this.workspace=active.workspace || this.workspace || ws.items[0]?.code || '';this.activeRevision=active.revision
      if(active.info && !this.workspaces.some(item=>item.code===active.workspace))this.workspaces.push(active.info)
      this.workspaceTree=this.workspace?[{id:'workspace/'+this.workspace,kind:'workspace',name:this.workspace,depth:0,directory:'',expanded:false}]:[]
      this.stream=this.ws?.stream || streams.items[0]?.code || '';this.depot=depots.items[0]?.code || ''
    },
    async changePage(client,after=''){const page=this.activeTab.change?{items:[await client.call('inspect_change',{change:this.activeTab.change})],after:null}:await client.call('changes',{workspace:['all','stream','mine'].includes(this.activeTab.scope || 'mine')?undefined:this.workspace,scope:this.activeTab.scope || 'mine',stream:this.stream,state:this.state,states:this.activeTab.kind==='changes'?this.activeTab.states:undefined,after,limit:100});this.changes=page.items;this.changesAfter=page.after;const current=page.items.find(item=>item.code===(this.change?.code || this.changeRef));if(current){const clean=!this.dirty;this.change=current;if(clean)this.description=current.description || ''}const codes=new Set(page.items.map(item=>item.code));this.expandedChanges=this.expandedChanges.filter(code=>codes.has(code));this.changeChildren=Object.fromEntries(Object.entries(this.changeChildren).filter(([code])=>codes.has(code)))},
    async load(){this.depotExpanded=this.depotTree.length?this.depotTree.filter(row=>row.expanded).map(row=>row.id):this.depotExpanded;this.workspaceExpanded=this.workspaceTree.length?this.workspaceTree.filter(row=>row.expanded).map(row=>row.id):this.workspaceExpanded;if(this.dirty&&!this.canLeave())return;await this.run(async client=>{await this.catalog(client);if(this.activeTab.kind==='changes'){this.state=this.activeTab.state;this.view='change'}else if(this.activeTab.kind==='files'){this.view=this.activeTab.source==='selection'?this.filesContext.source:this.activeTab.source;this.prefix=this.activeTab.source==='selection'?(this.activeTab.prefix || this.filesContext.prefix):(this.activeTab.prefix || '')}await this.changePage(client);if(this.change){const updated=this.changes.find(item=>item.code===this.change.code);this.change=updated || null;this.description=this.change?.description || ''}await this.filesPage(client);
      if(this.activeTab.kind==='history'&&this.historyPath){const page=await client.call('history',{stream:this.historyStream,path:this.historyPath,limit:1000});this.history=page.items;this.detailsView='history';this.detail=this.history[0] || null}
      for(const id of this.depotExpanded){const node=this.depotTree.find(row=>row.id===id);if(node&&!node.expanded)await this.depotBranchPage(client,node)}
      for(const id of this.workspaceExpanded){const node=this.workspaceTree.find(row=>row.id===id);if(node&&!node.expanded)await this.workspaceBranchPage(client,node)}
      for(const code of [...this.expandedChanges]){const node=this.changes.find(change=>change.code===code);if(node)await this.changeBranchPage(client,node)}
    })},
    async chooseWorkspace(code){if(!this.canLeave())return;await this.run(async client=>{const preview=await client.call('workspace_switch_preview',{workspace:code});if(preview.previous&&(preview.pending_changes==null || preview.pending_changes || preview.active_transfer || preview.active_bulk_tasks)&&!this.confirm(t('Pending changes and server tasks remain in the previous workspace. Local files are kept.')))return;await client.call('switch_workspace',{workspace:code,revision:preview.revision,request_id:requestId()});this.workspace=code;this.change=null;this.rows=[];this.history=[];this.prefix='';this.changeChildren={};this.expandedChanges=[];await this.catalog(client);await this.changePage(client);await this.filesPage(client)})},
    async selectChange(item){if(this.dirty&&!this.canLeave())return;await this.run(async client=>{this.change=item;this.description=item.description || '';this.view='change';this.prefix='';this.cursors=[];this.history=[];this.detail=null;this.preview='';await this.filesPage(client);await this.loadConflicts(client)})},
    async changeState(){if(this.dirty&&!this.canLeave())return;await this.run(async client=>{this.change=null;this.description='';this.rows=[];this.prefix='';this.changeChildren={};this.expandedChanges=[];await this.changePage(client)})},
    async filesPage(client,after='',forward=false){
      const old=this.pageCursor;let page={items:[],after:null};
      if(this.view==='have'&&this.workspace)page=await client.call('have',{workspace:this.workspace,after,prefix:this.prefix,limit:200})
      else if(this.view==='depot'&&this.stream)page=await client.call('list',{stream:this.stream,after,prefix:this.prefix,limit:200,...(this.depotHeads[this.stream] || after&&this.published?{published_change:this.depotHeads[this.stream] || this.published}:{})})
      else if(this.view==='change'&&this.change)page=await client.call(this.change.editable===false?'inspect_change_files':'change_files',{[this.change.state==='shelved'?'shelf':'change']:this.change.code,after,prefix:this.prefix,limit:200,...(this.pending&&after?{edit_revision:this.change.edit_revision}:{})})
      if(this.view==='change'&&page.info){const clean=!this.dirty;this.change={...this.change,...page.info};if(clean)this.description=this.change.description || '';const listed=this.changes.find(item=>item.code===this.change.code);if(listed)Object.assign(listed,page.info)}
      this.rows=page.items;await this.fileStates(client,this.rows,this.change?.stream || this.stream);this.after=page.after;this.published=page.published_change;this.pageCursor=after;if(forward)this.cursors.push(old);else if(!after)this.cursors=[]
      if(this.view==='change'&&this.change&&!this.prefix&&!after){this.changeChildren[this.change.code]=page;if(!this.expandedChanges.includes(this.change.code))this.expandedChanges.push(this.change.code)}
      await this.pageLocks(client,this.rows,this.change?.stream || this.stream)
    },
    async fileStates(client,rows,defaultStream){
      if(!rows.length || !this.workspace)return
      const page=await client.call('file_states',{workspace:this.workspace,paths:rows.map(row=>({stream:row.stream || defaultStream,path:row.source_path || row.path}))})
      for(let index=0;index<rows.length;index++){
        const {path,stream,...state}=page.items[index];Object.assign(rows[index],state)
        if(this.view==='change'&&this.change)rows[index].change_state=this.change.state
      }
    },
    async pageLocks(client,rows,defaultStream){
      const streams=new Map();for(const row of rows){const stream=row.stream || defaultStream,path=row.source_path || row.path;this.locks[stream+'\0'+path]=[];if(!streams.has(stream))streams.set(stream,[]);streams.get(stream).push(path)}
      for(const [stream,paths] of streams){if(!stream||!paths.length)continue;const result=await client.call('locks',{stream,paths});for(const item of result.items)this.locks[stream+'\0'+item.path]=item.holders}
    },
    async showFiles(){await this.run(client=>this.filesPage(client))},
    async nextPage(){await this.run(client=>this.filesPage(client,this.after,true))},
    async previousPage(){const cursor=this.cursors.pop();await this.run(client=>this.filesPage(client,cursor))},
    toggle(path,checked){this.selected=checked?[...this.selected,path]:this.selected.filter(item=>item!==path)},
    holders(row){return (this.locks[(row.stream || this.change?.stream || this.stream)+'\0'+(row.source_path || row.path)] || []).map(item=>item.owner+' · '+t(item.mode==='exclusive'?'Exclusive checkout':'Ordinary checkout')+' · '+item.change).join('\n')},
    paths(){const rows=this.selectionIds.length?this.selectedRows().filter(row=>row.path&&(row.kind || 'file')==='file'):(this.view==='change'?this.changeChildren[this.change?.code]?.items || []:this.rows).filter(row=>this.selected.includes(row.path));if(rows.some(row=>row.stream && row.stream!==this.change.stream || row.writable===false || row.parent && row.parent!==this.change.code))throw new Error('Select writable files from one changelist stream.');return rows.map(row=>row.source_path || row.path)},
    async refreshChange(client){this.change=await client.call('status',{change:this.change.code});this.description=this.change.description || '';await this.filesPage(client);await this.loadConflicts(client);await this.changePage(client);for(const code of [...this.expandedChanges]){const node=this.changes.find(change=>change.code===code);if(node)await this.changeBranchPage(client,node)}if(!this.integration && this.progress.state==='Awaiting conflict resolution')this.progress={state:'complete'}},
    async newChange(){await this.run(async client=>{this.change=await client.call('create_change',{workspace:this.workspace,stream:this.stream || this.ws.stream,description:''});this.description='';this.selected=[];this.selectionIds=[];this.selectionRecords={};this.selectionQuery=null;this.anchorId='';this.focusId='';this.state='pending';this.view='change';if(!this.tabs.some(tab=>tab.id==='pending'))this.tabs.push({...viewPresets[1]});this.activeTabId='pending';this.rememberGeometry();await this.changePage(client);await this.filesPage(client)})},
    async mutate(action,values={}){await this.run(async client=>{if(['checkout','remove_files'].includes(action))values.paths=this.paths();await client.call(action,{change:this.change.code,edit_revision:this.change.edit_revision,request_id:requestId(),...values});await this.refreshChange(client)})},
    async submit(){await this.reviewChange('submit')},
    async reviewChange(operation,paths=[],values={}){this.review=null;this.reviewOperation=operation;this.reviewPaths=paths;this.reviewRequest=values;await this.run(async client=>{this.review=await client.call(operation==='compare_shelf'?'compare_shelf':'change_preview',{change:this.change.code,edit_revision:this.change.edit_revision,limit:200,...values,...(paths.length?{paths}:{})})});if(this.review)this.$refs.reviewDialog.showModal()},
    async applyReview(){const reviewed=this.review;if(reviewed.edit_revision!==this.change.edit_revision){this.error='Changelist changed; review the files again.';return}
      await this.run(async client=>{let revision=reviewed.edit_revision;
        if(['unshelve_begin','rebase_begin','merge_begin'].includes(this.reviewOperation)){
          await client.call(this.reviewOperation,{change:this.change.code,edit_revision:revision,request_id:requestId(),...this.reviewRequest,preview_head_revision:reviewed.preview_head_revision,preview_source_root:reviewed.preview_source_root});
          this.change=await client.call('status',{change:this.change.code});await this.advanceIntegration(client);this.$refs.reviewDialog.close();return
        }
        if(this.reviewOperation==='update_shelf'){
          await client.call('update_shelf',{change:this.change.code,edit_revision:revision,request_id:requestId(),...this.reviewRequest,paths:this.reviewPaths});await this.refreshChange(client);this.$refs.reviewDialog.close();return
        }
        if(this.reviewOperation==='submit'&&this.dirty){const updated=await client.call('update_change',{change:this.change.code,edit_revision:revision,description:this.description,request_id:requestId()});revision=updated.edit_revision}
        await client.call(this.reviewOperation==='submit'?'submit':'shelve',{change:this.change.code,edit_revision:revision,request_id:requestId(),...(this.reviewPaths.length?{paths:this.reviewPaths}:{}),...(this.reviewOperation==='shelve_revert'?{revert:true}:{})});
        if(this.reviewOperation==='submit'){this.state='submitted';this.depotRoots();let tab=this.tabs.find(tab=>tab.id==='submitted');if(!tab){tab={...viewPresets[2]};this.tabs.push(tab)}this.activeTabId='submitted'}
        await this.refreshChange(client);this.progress={state:this.reviewOperation==='submit'?'submitted':'complete',change:this.change.code};this.$refs.reviewDialog.close()
      })},
    async move(){await this.run(async client=>{const destination=await client.call('status',{change:this.target});await client.call('move_files',{change:this.change.code,target_change:this.target,paths:this.paths(),edit_revision:this.change.edit_revision,target_edit_revision:destination.edit_revision,request_id:requestId()});await this.refreshChange(client)})},
    async integrationBegin(action,values={}){this.review=null;this.reviewOperation=action;this.reviewPaths=[];this.reviewRequest=values;await this.run(async client=>{this.review=await client.call('integration_preview',{change:this.change.code,edit_revision:this.change.edit_revision,kind:action.replace('_begin',''),limit:200,...values});Object.assign(this.review,{number:this.change.number,editable:this.editable,files_unknown:true})});if(this.review)this.$refs.reviewDialog.showModal()},
    async nextReview(){await this.run(async client=>{const operation=this.reviewOperation,method=['unshelve_begin','rebase_begin','merge_begin'].includes(operation)?'integration_preview':operation==='compare_shelf'?'compare_shelf':'change_preview';const values={change:this.change.code,edit_revision:this.review.edit_revision,after:this.review.after,limit:200,...this.reviewRequest,...(this.review.shelf_revision!==undefined?{shelf_revision:this.review.shelf_revision}:{})};if(method==='integration_preview')Object.assign(values,{kind:operation.replace('_begin',''),preview_head_revision:this.review.preview_head_revision,preview_source_root:this.review.preview_source_root});this.review=await client.call(method,values);if(method==='integration_preview')Object.assign(this.review,{number:this.change.number,editable:this.editable,files_unknown:true})})},
    async pickShelf(operation,after=''){this.shelfOperation=operation;await this.run(async client=>{const page=await client.call('changes',{stream:this.change.stream,scope:'stream',state:'shelved',after,limit:200});this.shelves=page.items.filter(row=>operation!=='update_shelf'||row.owner===this.login);this.shelvesAfter=page.after;this.shelfChoice=''});this.$refs.shelfDialog.showModal()},
    async shelfReview(){const shelf=this.shelves.find(row=>row.code===this.shelfChoice);if(!shelf)return;this.$refs.shelfDialog.close();if(this.shelfOperation==='diff_shelf'){await this.compareFile('shelf');return}await this.reviewChange(this.shelfOperation,this.shelfOperation==='update_shelf'?this.paths():[],{shelf:shelf.code,shelf_revision:shelf.edit_revision})},
    async compareFile(mode){
      await this.run(async client=>{
        let left,right
        if(mode==='revisions'){
          const rows=this.selectedRows()
          if(rows.length!==2)throw new Error('Select exactly two published revisions.')
          ;[left,right]=rows.map(row=>({stream:row.stream,path:row.path,published_change:row.change}))
        }else if(mode==='shelf'){
          const shelf=this.shelves.find(row=>row.code===this.shelfChoice),rows=this.selectedRows()
          if(!shelf || rows.length!==1)throw new Error('Select one file to compare.')
          const common={stream:this.change.stream,path:rows[0].source_path || rows[0].path}
          left={...common,shelf:shelf.code};right={...common,change:this.change.code}
        }else{
          const common={...this.integration,path:this.detail.path}
          left={...common,conflict_side:mode==='base_ours'?'base':'ours'}
          right={...common,conflict_side:mode==='base_ours'?'ours':'theirs'}
        }
        this.comparison=await client.call('compare_files',{left,right})
      })
      if(this.comparison)this.$refs.comparisonDialog.show()
    },
    async deleteShelfFiles(){const rows=this.selectedRows();if(!rows.length || rows.some(row=>row.parent!==this.change.code || (row.kind || 'file')!=='file')){this.error='Select files from this shelf only.';return}if(!this.confirm(t('Delete selected shelved files? Previous shelf contents remain available.')))return;await this.run(async client=>{await client.call('update_shelf',{shelf:this.change.code,shelf_revision:this.change.edit_revision,paths:this.paths(),delete:true,request_id:requestId()});this.selectionIds=[];this.selected=[];this.selectionRecords={};await this.refreshChange(client)})},
    async acceptChange(){await this.run(async client=>{this.change=await client.call('accept_change',{change:this.change.code,workspace:this.workspace,edit_revision:this.change.edit_revision,handoff:this.change.handoff.code,request_id:requestId()});await this.refreshChange(client)})},
    async taskFilesPage(task,after=''){await this.run(async client=>{const page=await client.call('transfer_items',{task:task.task,after,limit:200});this.taskFiles=page.items;this.taskFilesAfter=page.after})},
    clearCompletedTasks(){this.tasks=this.tasks.filter(task=>!['complete','ready','submitted','error','cancelled','expired'].includes(task.state));this.taskFiles=[];this.taskFilesAfter=null;if(['complete','ready','submitted','error','cancelled','expired'].includes(this.progress.state))this.progress={}},
    async advanceIntegration(client){let result;do{result=await client.call('integration_next',{...this.integration,request_id:requestId()});this.progress={state:'resolving',path:result.after || '',conflicts:result.conflicts,total_known:false}}while(!result.complete);this.change=await client.call('status',{change:this.change.code});await this.loadConflicts(client);if(!result.conflicts){await client.call('integration_finish',{...this.integration,request_id:requestId()});await this.refreshChange(client)}},
    async resumeIntegration(){await this.run(client=>this.advanceIntegration(client))},
    async cancelIntegration(){await this.run(async client=>{let result;do{result=await client.call('integration_cancel',{...this.integration,request_id:requestId()})}while(!result.complete);await this.refreshChange(client)})},
    async loadConflicts(client,after=''){if(!this.integration){this.conflicts=[];this.resolvedConflicts=[];this.conflictSelection=[];this.conflictsAfter=null;return}const page=await client.call('conflicts',{...this.integration,after,limit:100});this.conflicts=page.items;this.conflictsAfter=page.after;this.resolvedConflicts=(await client.call('resolved_files',{...this.integration,limit:200})).items;this.conflictSelection=this.conflictSelection.filter(path=>this.conflicts.some(row=>row.path===path));this.detailsView='conflicts';this.detail=(this.showResolved?this.resolvedConflicts:this.conflicts)[0] || null},
    async resolve(row,choice){const selected=this.conflictSelection.length?this.conflictSelection:[row.path],paths=new Set(selected);for(const path of selected){const conflict=this.conflicts.find(row=>row.path===path);if(conflict?.rename_partner)paths.add(conflict.rename_partner)}await this.run(async client=>{await client.call('resolve',{...this.integration,request_id:requestId(),resolutions:[...paths].map(path=>({path,choice}))});await this.loadConflicts(client)})},
    async undoResolution(){await this.run(async client=>{await client.call('undo_resolve',{...this.integration,request_id:requestId(),paths:this.detail.rename_partner?[this.detail.path,this.detail.rename_partner]:[this.detail.path]});this.showResolved=false;await this.loadConflicts(client)})},
    async historyFor(row){
      const path=row.source_path || row.path,stream=row.stream || this.change?.stream || this.stream
      if(this.activeTab.kind!=='history' || this.activeTab.pinned&&(path!==this.historyPath || stream!==this.historyStream)){
        this.captureView()
        let tab=this.tabs.find(tab=>tab.kind==='history'&&!tab.pinned)
        if(!tab){if(this.tabs.length>=32){this.error='Close a view tab before opening another.';return}tab={...viewPresets[3],id:requestId()};this.tabs.push(tab)}
        this.activeTabId=tab.id
      }
      this.rememberGeometry();await this.run(async client=>{this.historyPath=row.source_path || row.path;this.historyStream=row.stream || this.change?.stream || this.stream;const result=await client.call('history',{stream:this.historyStream,path:this.historyPath,limit:1000});this.history=result.items;this.detailsView='history';this.detail=this.history[0] || null;this.preview='';if(result.more)this.notice='Showing the latest 1000 published revisions.'})},
    async previewFile(values){await this.run(async client=>{const result=await client.call('file_preview',values);this.preview=result.text || result.kind+' · '+prettySize(result.size)+' · '+result.sha256;this.notice=result.truncated?'Preview shows the first 256 KiB':''})},
    stop(){this.aborter?.abort()},
    async taskAction(task,action){await this.run(async client=>{const method=task.kind==='mutation'?(action==='refresh'?'bulk_status':'bulk_cancel'):(action==='refresh'?'transfer_status':'transfer_cancel');this.progress=await client.call(method,{task:task.code || task.task});const page=await client.call('transfer_tasks',{limit:200});this.tasks=page.items})},
    async waitBulk(client,job){
      this.progress=job
      const deadline=performance.now()+86400000
      while(['queued','running'].includes(job.state)){
        this.aborter.signal.throwIfAborted()
        if(performance.now()>deadline)throw new Error('Bulk task continues on the server; refresh or resume waiting.')
        await new Promise(resolve=>setTimeout(resolve,500))
        job=await client.call('bulk_status',{task:job.task});this.progress=job
      }
      if(job.state==='error')throw new Error(job.error)
      return job
    },
    async bulkTarget(){
      await this.run(async client=>{
        const draft=this.targetDraft
        if(!draft.target&&!draft.creating)throw new Error('Choose a target changelist or create one explicitly.')
        if(!(await client.call('capabilities')).files_service_configured)throw new Error('Enable the files service before starting server bulk operations.')
        const destination=draft.creating?await client.call('create_change',{workspace:this.workspace,stream:draft.operation==='bulk_move'?this.change.stream:this.stream,description:draft.description,request_id:requestId()}):await client.call('status',{change:draft.target})
        const source=draft.operation==='bulk_move'?this.change:destination
        const options={operation:draft.operation==='bulk_move'?'move_files':'checkout',change:source.code,edit_revision:source.edit_revision,
          selection:this.selectionQuery.selection,mode:draft.mode,request_id:requestId()}
        if(draft.operation==='bulk_move')Object.assign(options,{target_change:destination.code,target_edit_revision:destination.edit_revision})
        await this.waitBulk(client,await client.call('bulk_begin',options))
        this.selectionQuery=null;this.change=source;await this.refreshChange(client)
      })
      if(!this.error)this.$refs.targetDialog.close()
    },
    async bulkQuery(operation){
      if(!this.confirm(t('Apply the pinned query to all matching server files? The batch is atomic; local files are kept.')))return
      await this.run(async client=>{
        if(!(await client.call('capabilities')).files_service_configured)throw new Error('Enable the files service before starting server bulk operations.')
        await this.waitBulk(client,await client.call('bulk_begin',{operation,change:this.change.code,edit_revision:this.change.edit_revision,selection:this.selectionQuery.selection,request_id:requestId()}))
        this.selectionQuery=null;await this.refreshChange(client)
      })
    },

    editWorkspace(){this.editingWorkspace=true;this.setup=true;this.setupKind='workspace';this.code=this.workspace;this.root=this.ws.local_root;this.stream=this.ws.stream;this.caseSensitive=this.ws.case_sensitive!==false;this.mappingPreview=null;this.mappings=JSON.stringify(this.ws.mappings || [{stream:this.ws.stream,source:'...',target:'...',writable:true}],null,2)},
    async previewMappings(){await this.run(async client=>{this.mappingPreview=await client.call('workspace_preview',{stream:this.stream,case_sensitive:this.caseSensitive,mappings:this.mappings.trim()?JSON.parse(this.mappings):[{stream:this.stream,source:'...',target:'...',writable:true}],paths:this.samplePath?[{stream:this.stream,path:this.samplePath}]:[]})})},
    async saveSetup(){await this.run(async client=>{const values={code:this.code};if(this.setupKind==='depot')values.title=this.code;else if(this.setupKind==='stream'){values.depot=this.depot;if(this.source)values.parent=this.source}else{values.stream=this.stream;values.local_root=this.root;values.case_sensitive=this.caseSensitive;if(this.mappings.trim())values.mappings=JSON.parse(this.mappings)}if(this.editingWorkspace){delete values.code;values.workspace=this.workspace;values.view_revision=this.ws.view_revision || 0;values.request_id=requestId()}await client.call(this.editingWorkspace?'update_workspace':'create_'+this.setupKind,values);this.setup=false;this.editingWorkspace=false;await this.catalog(client);await this.changePage(client)})},
  }
}
</script>
<template>
  <section class="file-workspace" :aria-label="t('Perforce-like workspace')" :aria-busy="busy" @dragend="dragDraft='';dropTarget=''">
    <header class="file-workspace-toolbar">
      <AppMenu label="View" icon="tab" show-label overlay>
        <AppMenuItem label="Depot Tree" icon="database" :checked="treeView==='depot'" @click="treeView='depot'" />
        <AppMenuItem label="Workspace Tree" icon="desktop" :checked="treeView==='workspace'" @click="treeView='workspace'" />
        <hr>
        <AppMenuItem v-for="preset in viewPresets" :key="preset.id" :label="preset.title" :icon="preset.icon" :checked="tabs.some(tab=>tab.id===preset.id)" :disabled="busy" @click="openView(preset.id)" />
        <hr><AppMenuItem label="New view tab" icon="add" :disabled="busy" @click="editTab(true)" /><AppMenuItem label="Edit view tab" icon="edit" :disabled="busy || !activeTabId" @click="editTab(false)" />
        <AppMenuItem label="Move tab left" icon="previous" :disabled="busy" @click="moveTab(-1)" /><AppMenuItem label="Move tab right" icon="next" :disabled="busy" @click="moveTab(1)" />
        <AppMenuItem label="Close tab" icon="close" :disabled="busy || !activeTabId" @click="closeTab" />
      </AppMenu>
      <AppMenu label="Actions" icon="play" show-label overlay>
        <AppMenuItem label="Go to changelist" icon="search" :disabled="busy" @click="openEditor('goto')" />
        <AppMenuItem label="File actions" icon="file" :disabled="busy || !selected.length" @click="$refs.fileMenu?.openAt($event)" />
        <AppMenuItem label="Changelist actions" icon="archive" :disabled="busy || !change" @click="$refs.changeMenu?.openAt($event)" />
        <AppMenuItem label="New changelist" icon="add" :disabled="busy || !workspace || !canAdminister" @click="newChange" />
      </AppMenu>
      <AppMenu label="Tools" icon="settings" show-label overlay>
        <AppMenuItem label="Columns" icon="table" :disabled="busy" @click="$refs.columnsDialog.showModal()" />
        <AppMenuItem label="Select all matching server files" icon="check" :disabled="busy || !['depot','have','change'].includes(view)" @click="selectQuery" />
        <AppMenu label="Selected server query" icon="check" submenu overlay>
          <AppMenuItem label="Checkout query (ordinary)" icon="edit" :disabled="busy || !canAdminister || !selectionQuery" @click="pickTarget('bulk_checkout','ordinary')" />
          <AppMenuItem label="Checkout query (exclusive)" icon="lock" :disabled="busy || !canAdminister || !selectionQuery" @click="pickTarget('bulk_checkout','exclusive')" />
          <AppMenuItem label="Move query files…" icon="move" :disabled="!editable || view!=='change' || !selectionQuery" @click="pickTarget('bulk_move')" />
          <AppMenuItem label="Revert query files" icon="undo" :disabled="!editable || view!=='change' || !selectionQuery" @click="bulkQuery('remove_files')" />
          <AppMenuItem label="Mark query files for delete" icon="delete" :disabled="!editable || view!=='change' || !selectionQuery" @click="bulkQuery('mark_delete')" />
        </AppMenu>
        <AppMenuItem label="Help" icon="help" @click="$emit('help','file_workspace')" />
      </AppMenu>
      <AppButton class="file-workspace-tree-toggle" icon-only label="Depots and changelists" icon="account-tree" :aria-pressed="treeOpen" @click="treeOpen=!treeOpen" />
      <AppSelect :model-value="workspace" :options="workspaceOptions" label="Workspace" :translate-labels="false" :disabled="busy" @update:model-value="chooseWorkspace" />
      <span class="file-workspace-root muted" :title="ws?.local_root">{{ ws?.local_root || stream }}</span>
      <AppButton icon-only label="Refresh" icon="refresh" :disabled="busy" @click="load" />
      <AppButton icon-only label="New changelist" icon="add" :disabled="busy || !workspace || !canAdminister" @click="newChange" />
      <AppMenu ref="workspaceMenu" label="Workspace actions" show-label overlay>
        <AppMenuItem label="Edit workspace" icon="edit" :disabled="busy || !ws" @click="editWorkspace" />
        <AppMenuItem label="Workspace setup" icon="settings" :disabled="busy" @click="editingWorkspace=false;setup=true" />
        <AppMenuItem v-if="canAdminister" label="Storage administration" icon="settings" :disabled="busy" @click="storageStatus" />
        <AppMenuItem v-if="workspaceAfter" label="Next workspaces" icon="next" :disabled="busy" @click="run(async client=>{const page=await client.call('workspaces',{after:workspaceAfter});workspaces=page.items;workspaceAfter=page.after})" />
        <AppMenuItem v-if="streamAfter" label="Next streams" icon="next" :disabled="busy" @click="run(async client=>{const page=await client.call('streams',{after:streamAfter});streams=page.items;streamAfter=page.after;depotRoots()})" />
        <AppMenuItem v-if="depotAfter" label="Next depots" icon="next" :disabled="busy" @click="run(async client=>{const page=await client.call('depots',{after:depotAfter});depots=page.items;depotAfter=page.after;depotRoots()})" />
        <AppMenuItem label="Help" icon="help" @click="$emit('help','file_workspace')" />
      </AppMenu>
    </header>
    <div class="file-workspace-address">
      <AppButton icon-only label="Back" icon="previous" :disabled="navigationIndex<=0" @click="navigationIndex--;navigate(navigation[navigationIndex],true)" />
      <AppButton icon-only label="Forward" icon="next" :disabled="navigationIndex+1>=navigation.length" @click="navigationIndex++;navigate(navigation[navigationIndex],true)" />
      <AppButton icon-only label="Parent folder" icon="folder-open" @click="navigate('//'+stream+'/'+prefix.replace(/\/?[^/]+\/?$/,''))" />
      <AppTextField :model-value="'//'+stream+'/'+prefix" label="Workspace or depot path" @keydown.enter="navigate($event.target.value)" />
    </div>
    <p v-if="notice" class="muted" role="status">{{ t(notice) }}</p>
    <div class="file-workspace-body" :class="{'tree-open':treeOpen}" :style="{'--file-tree-width':width+'px','--file-details-height':detailsHeight+'px'}">
      <nav class="file-workspace-tree" :aria-label="t('Depots')">
        <section class="file-workspace-tree-section">
          <div class="file-workspace-tree-tabs" role="tablist" :aria-label="t('Tree views')"><AppTabButton v-for="item in [{id:'depot',title:'Depot',icon:'database'},{id:'workspace',title:'Workspace',icon:'desktop'}]" :key="item.id" :label="item.title" :icon="item.icon" :checked="treeView===item.id" role="tab" :aria-selected="treeView===item.id" @click="treeView=item.id" /></div>
          <FileWorkspaceTree v-if="treeView==='depot'" :nodes="depotTree" :busy="busy" :selected="treeSelection" :selected-ids="selectionScope==='depot'?selectionIds:[]" label="Depot tree" @background="$refs.workspaceMenu.openAt($event)" @expand="depotBranch" @select="(row,event)=>{selectRow('depot',row,event);if(!event?.ctrlKey&&!event?.shiftKey)depotSelect(row)}" @menu="(event,row)=>rowMenu(event,'depot',row)" @drag="(event,row)=>dragFiles(event,'depot',row)" @keydown="keySelection($event,'depot')" />
          <FileWorkspaceTree v-else :nodes="workspaceTree" :busy="busy" :selected="treeSelection" :selected-ids="selectionScope==='workspace'?selectionIds:[]" label="Workspace tree" @background="$refs.workspaceMenu.openAt($event)" @expand="workspaceBranch" @select="(row,event)=>{selectRow('workspace',row,event);if(!event?.ctrlKey&&!event?.shiftKey)workspaceSelect(row)}" @menu="(event,row)=>rowMenu(event,'workspace',row)" @drag="(event,row)=>dragFiles(event,'workspace',row)" @keydown="keySelection($event,'workspace')" />
        </section>
      </nav>
      <AppSplitter v-model="width" label="Depots" :min="220" :max="600" />
      <div class="file-workspace-content">
        <WorkspaceTabs kind="view" :tabs="tabs.map(tab=>({...tab,title:tabTitle(tab)}))" :selected="activeTabId" :disabled="busy" @select="activateTab(tabs.find(tab=>tab.id===$event))" @close="closeTab" @reorder="reorderTabs" />
        <p v-if="!tabs.length" class="muted">{{ t('Open a view from the View menu') }}</p>
        <section v-show="['files','changes'].includes(activeTab.kind)" class="file-workspace-files">
          <header class="file-workspace-file-heading"><strong :title="change?.code">{{ view==='depot' ? '//'+stream+'/'+prefix : change ? t('Changelist #{number}',{number:change.number})+' · '+(change.description || t('No description')) : t('Select a changelist or depot folder') }}</strong>
            <AppButton label="Submit" icon="publish" :disabled="busy || !editable || !!integration" @click="submit" />
            <AppMenu ref="changeMenu" label="Changelist actions" show-label overlay>
              <AppMenuItem label="New changelist" icon="add" :disabled="busy || !workspace || !canAdminister" @click="newChange" />
              <AppMenuItem label="Submit" icon="publish" :disabled="(busy || !editable || !!integration) || !!selectionReason('submit')" @click="submit" :disabled-reason="selectionReason('submit') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Copy changelist link" icon="link" :disabled="!change" @click="copyChangeLink" />
            <AppMenuItem label="Copy changelist number" icon="copy" :disabled="!change" @click="copyChange" />
              <AppMenuItem label="Changelist description" icon="edit" :disabled="(busy || !editable) || !!selectionReason('description')" @click="openEditor('description')" :disabled-reason="selectionReason('description') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Move all files…" icon="move" :disabled="busy || !editable || !!integration || change?.opened_files===0 || !!selectionReason('move_all_files')" :disabled-reason="selectionReason('move_all_files') || 'Choose an owned pending changelist'" @click="moveWholeChange" />
              <AppMenuItem label="Shelve" icon="archive" :disabled="(busy || !editable || !!integration) || !!selectionReason('shelve')" @click="reviewChange('shelve')" :disabled-reason="selectionReason('shelve') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Shelve selected files" icon="archive" :disabled="(busy || !editable || !!integration || !selected.length) || !!selectionReason('shelve_selected')" @click="reviewChange('shelve',paths())" :disabled-reason="selectionReason('shelve_selected') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Shelve and revert" icon="undo" :disabled="(busy || !editable || !!integration) || !!selectionReason('shelve_revert')" @click="reviewChange('shelve_revert')" :disabled-reason="selectionReason('shelve_revert') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Compare pending with shelf" icon="compare" :disabled="(busy || !editable || !!integration) || !!selectionReason('compare_shelf')" @click="pickShelf('compare_shelf')" :disabled-reason="selectionReason('compare_shelf') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Replace selected files in shelf" icon="archive" :disabled="(busy || !editable || !!integration || !selected.length) || !!selectionReason('replace_shelf')" @click="pickShelf('update_shelf')" :disabled-reason="selectionReason('replace_shelf') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Delete selected shelved files" icon="delete" :disabled="(busy || !canAdminister || change?.state!=='shelved' || change.owner!==login || !selected.length) || !!selectionReason('delete_shelf_files')" @click="deleteShelfFiles" :disabled-reason="selectionReason('delete_shelf_files') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Offer changelist ownership" icon="account" :disabled="(busy || !editable || !!integration) || !!selectionReason('offer_change')" @click="openEditor('offer')" :disabled-reason="selectionReason('offer_change') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Accept changelist ownership" icon="check" :disabled="busy || !canAdminister || change?.handoff?.recipient!==login" @click="acceptChange" />
              <AppMenuItem label="Unshelve" icon="archive" :disabled="(busy || !canAdminister || (!editable && change?.state!=='shelved') || !!integration) || !!selectionReason('unshelve_begin')" @click="change?.state==='shelved' ? pickTarget('unshelve_begin') : openEditor('unshelve')" :disabled-reason="selectionReason('unshelve_begin') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Diff pending against shelf" icon="compare" :disabled="(busy || !editable || selectedRows().length!==1) || !!selectionReason('diff_shelf')" @click="pickShelf('diff_shelf')" :disabled-reason="selectionReason('diff_shelf') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Rebase / resolve" icon="account-tree" :disabled="(busy || !editable || !!integration) || !!selectionReason('rebase_begin')" @click="integrationBegin('rebase_begin')" :disabled-reason="selectionReason('rebase_begin') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Index pending metadata" icon="refresh" :disabled="busy || !pending || change.owner!==login" @click="run(async client=>{let result;do{result=await client.call('index_change',{change:change.code})}while(!result.complete);await refreshChange(client)})" />
              <AppMenuItem label="Merge stream" icon="account-tree" :disabled="(busy || !editable || !!integration) || !!selectionReason('merge_begin')" @click="openEditor('merge')" :disabled-reason="selectionReason('merge_begin') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Delete changelist / shelf…" icon="delete" :disabled="(busy || !canAdminister || !change || !['pending','shelved'].includes(change.state)) || !!selectionReason('delete_change')" @click="deleteChange" :disabled-reason="selectionReason('delete_change') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
              <AppMenuItem label="Revert changelist" icon="undo" :disabled="(busy || !editable || !!integration) || !!selectionReason('revert')" @click="confirm(t('Revert the changelist? Local files will be kept.')) && mutate('revert')" :disabled-reason="selectionReason('revert') || (!canAdminister ? 'Read-only inspection' : 'Choose an owned pending changelist')" />
            </AppMenu>
          </header>
          <div class="file-workspace-filter"><template v-if="activeTab.kind==='files'"><AppTextField v-model="prefix" label="Path prefix" placeholder="Path prefix" :disabled="busy" @keydown.enter="showFiles" /><AppButton icon-only label="Filter" icon="filter" :disabled="busy" @click="showFiles" /></template>
            <AppMenu ref="fileMenu" label="File actions" show-label overlay>
              <AppMenuItem label="Reveal in other tree" icon="account-tree" :disabled="(busy || selected.length!==1) || !!selectionReason('reveal_tree')" @click="revealTree" :disabled-reason="selectionReason('reveal_tree') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              <AppMenu label="Checkout" icon="lock" submenu overlay>
                <AppMenuItem label="Ordinary checkout" icon="unlock" :disabled="(!canAdminister || !!selectionReason('checkout_ordinary') || !!integration) || !!selectionReason('checkout_ordinary')" @click="pickTarget('checkout','ordinary')" :disabled-reason="selectionReason('checkout_ordinary') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
                <AppMenuItem label="Exclusive checkout" icon="lock" :disabled="(!canAdminister || !!selectionReason('checkout_exclusive') || !!integration) || !!selectionReason('checkout_exclusive')" @click="pickTarget('checkout','exclusive')" :disabled-reason="selectionReason('checkout_exclusive') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              </AppMenu>
              <AppMenu label="Changelist edits" icon="edit" submenu overlay>
                <AppMenuItem label="Revert selected files" icon="undo" :disabled="(busy || !editable || !selected.length || view!=='change') || !!selectionReason('remove_files')" @click="confirm(t('Remove the selected edits from the changelist? Local files are kept.')) && mutate('remove_files')" :disabled-reason="selectionReason('remove_files') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
                <AppMenuItem label="Rename file" icon="edit" :disabled="(busy || !editable || selected.length!==1) || !!selectionReason('rename_file')" @click="renameFile" :disabled-reason="selectionReason('rename_file') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
                <AppMenuItem label="Move files" icon="move" :disabled="(!editable || !!selectionReason('move_files') || view!=='change' || !!integration) || !!selectionReason('move_files')" @click="pickTarget('move_files')" :disabled-reason="selectionReason('move_files') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
                <AppMenuItem label="Remove selected from changelist" icon="close" :disabled="(!editable || !!selectionReason('remove_files') || view!=='change' || !!integration) || !!selectionReason('remove_files')" @click="mutate('remove_files')" :disabled-reason="selectionReason('remove_files') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              </AppMenu>
              <AppMenu label="Delete" icon="delete" submenu overlay>
                <AppMenuItem label="Mark for depot deletion" icon="delete" :disabled="(busy || !canAdminister || !selected.length) || !!selectionReason('mark_delete')" @click="pickTarget('mark_delete')" :disabled-reason="selectionReason('mark_delete') || (!canAdminister ? 'Read-only inspection' : integration ? 'Resolve the integration first' : 'Choose an owned pending changelist')" />
              </AppMenu>
              <AppMenu label="Copy" icon="copy" submenu overlay>
                <AppMenuItem label="Copy depot path" icon="copy" @click="copyPaths('depot')" />
                <AppMenuItem label="Copy local path" icon="copy" @click="copyPaths('local')" />
              </AppMenu>
              <AppMenuItem label="Columns" icon="table" @click="$refs.columnsDialog.showModal()" />
            </AppMenu>
          </div>
          <template v-if="activeTab.kind==='changes'">
            <div class="file-workspace-filter"><AppIcon name="archive" /><strong>{{ t('Changelists') }}</strong><AppButton v-if="changesAfter" icon-only label="Next changelists" icon="next" :disabled="busy" @click="run(client=>changePage(client,changesAfter))" /></div>
            <FileWorkspaceTree :nodes="changeTree" :busy="busy" :selected="change?.code" :selected-ids="selectionScope==='changes'?selectionIds:[]" :drop-target="dropTarget" :drop-reason="dropReason" :drop-caption="dropCaption" :can-drop="canAdminister" label="Changelist tree" @background="$refs.changeMenu.openAt($event)" @expand="changeBranch" @select="(row,event)=>{selectRow('changes',row,event);if(row.kind==='more')changeSelect(row)}" @menu="(event,row)=>rowMenu(event,'changes',row)" @drag="(event,row)=>dragFiles(event,'changes',row)" @dragover="acceptDrop" @dragend="dragDraft='';dropTarget=''" @drop="dropFiles" @keydown="keySelection($event,'changes')">
              <template #file="{node:row}">
                <div class="file-workspace-change-file" :class="{selected:rowSelected('changes',row)}" tabindex="0" @click="selectRow('changes',row,$event)" @dblclick="historyFor(row)" @contextmenu.prevent.stop="rowMenu($event,'changes',row)">
                  <AppCheckBox hide-label :translate-label="false" :model-value="rowSelected('changes',row)" :label="row.path" :disabled="busy" @click.stop @update:model-value="selectFile('changes',row,$event)" />
                  <AppIcon :name="badges(row)[0].icon" :class="'file-tone-'+badges(row)[0].tone" /><span class="file-name">{{ row.path }}</span>
                  <span :class="'file-tone-'+badges(row)[0].tone">{{ badges(row).map(badge=>t(badge.label)).join(' · ') }}</span>
                  <span :title="holders(row)">{{ holders(row) || t('No active checkout') }}</span>
                  <span>#{{ row.file?.number || row.number || '—' }}</span>
                  <span>{{ prettySize(row.file?.size ?? row.size ?? 0) }}</span>
                </div>
              </template>
            </FileWorkspaceTree>
          </template>
          <div v-else class="file-workspace-table" tabindex="0" @contextmenu.self.prevent="$refs.fileMenu.openAt($event)" @keydown="keySelection($event,'files')" @scroll="scroll.files=$event.target.scrollTop"><table><thead><tr><th><AppButton icon-only label="Select loaded files" icon="check" @click="keySelection({key:'a',ctrlKey:true,preventDefault(){}},'files')" /></th><th v-for="column in visibleColumns" :key="column.key" :style="{width:column.width+'px',minWidth:column.width+'px'}"><AppButton :label="column.title" @click="sortFiles(column.key)">{{ t(column.title) }} {{ sortColumn===column.key?(sortDesc?'↓':'↑'):'' }}</AppButton></th></tr></thead><tbody>
            <tr v-for="row in visibleRows" :key="rowId(row)" :class="{selected:rowSelected('files',row),focused:focusId===rowId(row)}" tabindex="0" :aria-selected="rowSelected('files',row)" draggable="true" @click="selectRow('files',row,$event)" @dblclick="historyFor(row)" @contextmenu.prevent.stop="rowMenu($event,'files',row)" @dragstart="dragFiles($event,'files',row)">
              <td><AppCheckBox hide-label :translate-label="false" :model-value="rowSelected('files',row)" :label="row.path" :disabled="busy" @click.stop @update:model-value="selectFile('files',row,$event)" /></td>
              <td v-for="column in visibleColumns" :key="column.key"><template v-if="column.key==='path'"><AppIcon :name="badges(row)[0].icon" :class="'file-tone-'+badges(row)[0].tone" /></template><span :class="column.key==='server_status'?'file-tone-'+badges(row)[0].tone:''">{{ columnValue(row,column.key) }}</span></td>
            </tr>
          </tbody></table><p v-if="!visibleRows.length" class="file-workspace-empty muted">{{ t('No files on this page') }}</p></div>
          <div class="file-workspace-filter"><AppTextField v-model="nameFilter" label="Filter loaded files" /><AppSelect v-model="statusFilter" label="File status" :options="[{value:'',label:'All states'},...['Modified','Added','Missing','Uploaded','Marked for delete'].map(label=>({value:label,label}))]" /></div>
          <p v-if="selectionQuery" class="muted" role="status">{{ selectionQuery.count_known?selectionQuery.files:t('All matching server files') }} {{ t('selected') }} · {{ t('Pinned server selection') }}</p>
          <AppButton label="Select all matching server files" icon="select-all" :disabled="busy" @click="selectQuery" />
          <footer class="file-workspace-pagination"><span class="muted">{{ view==='change'?changeTree.filter(row=>row.kind==='file').length:rows.length }} {{ t('files') }} · {{ selected.length }} {{ t('selected') }}</span><AppButton v-if="view!=='change'" icon-only label="Previous page" icon="previous" :disabled="busy || !cursors.length" @click="previousPage" /><AppButton v-if="view!=='change'" icon-only label="Next page" icon="next" :disabled="busy || !after" @click="nextPage" /></footer>
          <FileWorkspaceInspector v-if="activeTab.kind==='files'" :call="command" :row="contextRow?.path && (contextRow.kind || 'file')==='file' ? contextRow : fileFocus" :workspace="workspace" :stream="stream" :scope="selectionScope==='changes' ? contextRow?.parent : ''" :shelved="change?.state==='shelved'" />
        </section>
        <section v-show="detailTab" class="file-workspace-details" :aria-label="t('History and conflicts')">
          <header class="file-workspace-detail-tabs">            <strong>{{ tabTitle(activeTab) }}</strong>
            <AppMenu ref="detailMenu" label="Detail actions" overlay>
              <template v-if="detailsView==='history'"><AppMenuItem label="Compare selected revisions" icon="compare" :disabled="busy || selectedRows().length!==2" @click="compareFile('revisions')" /><AppMenuItem label="Preview revision" icon="visibility" :disabled="busy || !detail || detail.deleted" @click="previewFile({stream:detail.stream,path:detail.path,published_change:detail.change})" /><AppMenuItem label="Restore revision in changelist" icon="undo" :disabled="busy || !canAdminister || !detail || detail.deleted || selectionIds.length>1" @click="pickTarget('restore_file')" /></template>
              <template v-else-if="detailsView==='conflicts'">
                <AppMenu label="Preview" icon="visibility" submenu overlay>
                  <AppMenuItem label="Compare Base / Ours" icon="compare" :disabled="busy || !integration || !detail" @click="compareFile('base_ours')" /><AppMenuItem label="Compare Ours / Theirs" icon="compare" :disabled="busy || !integration || !detail" @click="compareFile('ours_theirs')" /><AppMenuItem v-for="side in ['base','ours','theirs']" :key="side" :label="{base:'Preview base',ours:'Preview ours',theirs:'Preview theirs'}[side]" icon="visibility" :disabled="busy || !integration || !detail?.[side] || detail[side].deleted" @click="previewFile({...integration,path:detail.path,conflict_side:side})" />
                </AppMenu>
                <AppMenuItem label="Use ours" icon="check" :disabled="busy || !integration || !detail || showResolved" @click="resolve(detail,'ours')" />
                <AppMenuItem label="Use theirs" icon="check" :disabled="busy || !integration || !detail || showResolved" @click="resolve(detail,'theirs')" />
                <AppMenuItem label="Undo resolution" icon="undo" :disabled="busy || !integration || !showResolved || !detail" @click="undoResolution" />
                <AppMenuItem label="Continue integration" icon="play" :disabled="busy || !integration" @click="resumeIntegration" />
                <AppMenuItem label="Finish integration" icon="check" :disabled="busy || !integration || conflicts.length>0 || !change.integration.complete" @click="mutate('integration_finish',{integration:integration.integration})" />
                <AppMenuItem label="Cancel integration" icon="cancel" :disabled="busy || !integration" @click="cancelIntegration" />
                <AppMenuItem v-if="conflictsAfter" label="Next conflicts" icon="next" :disabled="busy" @click="run(client=>loadConflicts(client,conflictsAfter))" />
              </template>
              <template v-else><AppMenuItem v-if="detail?.kind==='mutation'" label="Resume waiting for batch" icon="play" :disabled="busy || !['queued','running'].includes(detail.state)" @click="run(client=>waitBulk(client,detail))" /><AppMenuItem label="Transfer status" icon="refresh" :disabled="busy || !detail" @click="taskAction(detail,'refresh')" /><AppMenuItem label="Cancel transfer" icon="cancel" :disabled="busy || !detail || ['ready','complete','submitted','cancelled','expired'].includes(detail.state)" @click="taskAction(detail,'cancel')" /><AppMenuItem label="Clear completed transfers" icon="close" :disabled="busy" @click="clearCompletedTasks" /><AppMenuItem v-if="tasksAfter" label="Next transfers" icon="next" :disabled="busy" @click="run(async client=>{const page=await client.call('transfer_tasks',{after:tasksAfter,limit:200});tasks=page.items;tasksAfter=page.after})" /></template>
            </AppMenu>
          </header>
          <div class="file-workspace-detail-body">
            <div v-if="detailsView==='conflicts'" class="file-workspace-detail-tabs"><AppTabButton label="Unresolved" :checked="!showResolved" @click="showResolved=false;detail=conflicts[0] || null" /><AppTabButton label="Resolved" :checked="showResolved" @click="showResolved=true;detail=resolvedConflicts[0] || null" /></div>
            <div class="file-workspace-detail-list" :aria-label="t(detailsView==='history'?'History':detailsView==='conflicts'?'Conflicts':'Transfers')">
              <template v-if="detailsView==='history'"><AppButton v-for="item in history" :key="item.code" :aria-label="'#'+item.number+' · '+item.path" :aria-pressed="rowSelected('history',item)" icon="history" :disabled="busy" @click="detail=item;selectRow('history',item,$event)" @contextmenu.prevent="detail=item;selectRow('history',item,{},true);$refs.detailMenu.openAt($event)" @dblclick="previewFile({stream:item.stream,path:item.path,published_change:item.change})">#{{ item.number }} · {{ item.path }} · {{ prettySize(item.size) }} · #{{ item.change_number }} · {{ item.author }} · {{ item.submitted_at ? new Date(item.submitted_at/1000).toLocaleString() : "—" }} · {{ item.action }} · {{ item.description }}</AppButton><p v-if="!history.length" class="file-workspace-empty muted">{{ t('Select a file to view history') }}</p></template>
              <template v-else-if="detailsView==='conflicts'"><AppButton v-for="row in (showResolved?resolvedConflicts:conflicts)" :key="row.path" :aria-label="row.path" :aria-pressed="showResolved?detail?.path===row.path:conflictSelection.includes(row.path)" :icon="showResolved?'check':'warning'" :disabled="busy" @click="event=>{detail=row;if(!showResolved)conflictSelection=event.ctrlKey?(conflictSelection.includes(row.path)?conflictSelection.filter(path=>path!==row.path):[...conflictSelection,row.path]):[row.path]}">{{ row.path }}</AppButton><p v-if="!(showResolved?resolvedConflicts:conflicts).length" class="file-workspace-empty muted">{{ t('No conflicts') }}</p></template>
              <template v-else><AppButton v-for="task in tasks" :key="task.code || task.task" :aria-label="task.task || task.code" :aria-pressed="detail===task" icon="cloud-upload" :disabled="busy" @click="detail=task;taskFilesPage(task)">{{ task.change || task.workspace }} · {{ t(task.kind==='download'&&task.state==='blocked'?'Sync stopped':task.state) }} · {{ task.files_done || 0 }}</AppButton><p v-if="detail?.error" class="error" role="alert">{{ detail.error }}</p><p v-if="!tasks.length" class="file-workspace-empty muted">{{ t('No transfers') }}</p></template>
            </div>
            <AppTextArea v-if="preview" :model-value="preview" readonly label="File preview" />
            <div v-if="detailsView==='tasks'" class="file-workspace-detail-list"><p v-for="file in taskFiles" :key="file.path">{{ file.path }} · {{ t(file.state) }} · {{ prettySize(file.received) }} / {{ prettySize(file.size) }}</p><AppButton v-if="taskFilesAfter" label="Next files" icon="next" :disabled="busy" @click="taskFilesPage(detail,taskFilesAfter)" /></div>
          </div>
        </section>
      </div>
    </div>
    <FileWorkspaceLog :entries="operationLog" @clear="operationLog=[]" @copy="copyLog" @debug="$emit('debug')" />
    <footer class="file-workspace-progress" role="status"><span>{{ t(progress.state || 'Ready') }} · {{ progress.files_done || 0 }} {{ t('files') }} · {{ prettySize(progress.bytes_done || 0) }}<span v-if="progress.total_known"> / {{ progress.files_total }} · {{ prettySize(progress.bytes_total || 0) }}</span></span><span :title="progress.path">{{ progress.path || progress.change || '' }}</span><progress v-if="busy" :value="progress.total_known ? progress.bytes_done || 0 : undefined" :max="progress.bytes_total || 1" :aria-label="t('Transfer progress')"></progress><AppButton v-if="busy" icon-only label="Stop waiting" icon="close" @click="stop" /></footer>
    <dialog ref="reviewDialog" class="record-dialog file-workspace-dialog" :aria-label="t(reviewTitle)" @cancel.prevent="!busy && $refs.reviewDialog.close()">
      <form v-if="review" @submit.prevent="applyReview">
        <header><h2>{{ t(reviewTitle) }} · #{{ review.number }}</h2><AppButton icon-only label="Close" icon="close" :disabled="busy" @click="$refs.reviewDialog.close()" /></header>
        <AppTextArea :model-value="description" readonly label="Changelist description" />
        <p>{{ review.files_unknown?review.items.length:review.files || review.items.length }} {{ t(review.files_unknown?'files on this page':'files') }} · {{ prettySize(review.bytes || 0) }}</p>
        <p v-if="review.source">{{ review.source }} → {{ review.target }}</p>
        <p v-if="review.active_transfer || review.integration || review.rebase_required" class="error">{{ t(review.active_transfer?'Finish or cancel the upload before submit':review.integration?'Resolve all conflicts before submit':'Stream head changed; rebase before submit') }}</p>
        <p v-if="reviewOperation==='submit' && review.waiting_uploads!==0" class="error">{{ t(review.waiting_uploads==null?'Index pending metadata before submit':'Files waiting for upload: %1').replace('%1',review.waiting_uploads) }}</p>
        <p v-if="reviewOperation==='shelve_revert'" class="muted">{{ t('The shelf is saved before reverting. Local files are kept.') }}</p>
        <div class="file-workspace-review-files"><p v-for="row in review.items" :key="row.path">{{ row.path }} · {{ t(row.excluded?'Excluded by workspace mapping':row.conflict?'Conflict':row.action || '') }}</p></div>
        <AppButton v-if="review.after" label="Next page" icon="next" :disabled="busy" @click="nextReview" />
        <footer><AppButton label="Cancel" icon="close" :disabled="busy" @click="$refs.reviewDialog.close()" /><AppButton v-if="reviewOperation!=='compare_shelf'" :label="{submit:'Submit',merge_begin:'Merge stream',unshelve_begin:'Unshelve',rebase_begin:'Rebase / resolve',update_shelf:'Replace shelf files'}[reviewOperation] || 'Shelve'" :icon="reviewOperation==='submit'?'publish':'archive'" type="submit" highlighted :disabled="busy || !review.editable || !!review.active_transfer || !!review.integration || ['submit','merge_begin','unshelve_begin'].includes(reviewOperation) && review.rebase_required || reviewOperation==='submit' && review.waiting_uploads!==0" /></footer>
      </form>
    </dialog>
    <dialog ref="shelfDialog" class="record-dialog file-workspace-dialog" :aria-label="t('Shelved changelist')" @cancel.prevent="!busy && $refs.shelfDialog.close()">
      <form @submit.prevent="shelfReview"><header><h2>{{ t(shelfOperation==='update_shelf'?'Replace selected files in shelf':'Compare pending with shelf') }}</h2><AppButton icon-only label="Close" icon="close" :disabled="busy" @click="$refs.shelfDialog.close()" /></header>
        <AppSelect v-model="shelfChoice" label="Shelved changelist" :options="shelves.map(row=>({value:row.code,label:'#'+row.number+' · '+row.owner+' · '+row.description}))" :translate-labels="false" />
        <AppButton v-if="shelvesAfter" label="Next shelves" icon="next" :disabled="busy" @click="pickShelf(shelfOperation,shelvesAfter)" />
        <footer><AppButton label="Cancel" icon="close" :disabled="busy" @click="$refs.shelfDialog.close()" /><AppButton label="Review" icon="visibility" type="submit" highlighted :disabled="busy || !shelfChoice" /></footer>
      </form>
    </dialog>
    <dialog ref="nonemptyDelete" class="record-dialog file-workspace-dialog" :aria-label="t('This changelist contains files')" @cancel.prevent="$refs.nonemptyDelete.close()">
      <header><h2>{{ t('This changelist contains files') }}</h2></header>
      <p>{{ t('Move all files to another changelist, then delete the empty changelist. Or revert this changelist; it will appear in Reverted. Local files are kept.') }}</p>
      <footer><AppButton label="Cancel" icon="close" @click="$refs.nonemptyDelete.close()" /><AppButton label="Move files…" icon="move" @click="moveWholeChange" /><AppButton label="Revert changelist" icon="undo" @click="$refs.nonemptyDelete.close();confirm(t('Revert the changelist? Local files will be kept.')) && mutate('revert')" /></footer>
    </dialog>
    <dialog ref="targetDialog" class="record-dialog file-workspace-dialog" :aria-label="t('Choose target changelist')" @cancel.prevent="!busy && $refs.targetDialog.close()">
      <form @submit.prevent="targetFiles">
        <header><h2>{{ t('Choose target changelist') }}</h2><AppButton icon-only label="Close" icon="close" :disabled="busy" @click="$refs.targetDialog.close()" /></header>
        <p>{{ selected.length }} {{ t('selected') }} · {{ t(targetDraft.operation==='move_files'?'Move files':targetDraft.operation==='mark_delete'?'Mark for depot deletion':'Checkout') }}</p>
        <AppSelect v-model="targetDraft.target" label="Target changelist" :translate-labels="false" :disabled="busy || targetDraft.creating" :options="targetChanges.filter(change=>change.depot_writable!==false && change.state==='pending' && change.owner===login && change.workspace===workspace && change.stream===targetDraft.stream && !change.active_transfer && !change.active_bulk && !change.integration && (!['move_files','bulk_move'].includes(targetDraft.operation) || change.code!==this.change?.code)).map(change=>({value:change.code,label:'#'+change.number+' · '+(change.description || t('No description'))}))" />
        <AppButton v-if="targetAfter" label="Next changelists" icon="next" :disabled="busy" @click="run(async client=>{const page=await client.call('changes',{state:'pending',workspace,after:targetAfter,limit:200});targetChanges=page.items;targetAfter=page.after})" />
        <AppCheckBox v-model="targetDraft.creating" label="Create a new changelist" :disabled="busy" />
        <AppTextField v-if="targetDraft.creating" v-model="targetDraft.description" label="Changelist description" :disabled="busy" />
        <p v-if="targetDraft.operation==='mark_delete'" class="muted">{{ t('Depot deletion is published only by Submit. Local files are kept.') }}</p>
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <footer><AppButton label="Cancel" icon="close" :disabled="busy" @click="$refs.targetDialog.close()" /><AppButton label="Stage selected files" icon="check" type="submit" highlighted :disabled="busy || !targetDraft.creating && !targetDraft.target" /></footer>
      </form>
    </dialog>
    <dialog ref="columnsDialog" class="record-dialog" :aria-label="t('File columns')" @cancel.prevent="$refs.columnsDialog.close()">
      <h3>{{ t('File columns') }}</h3>
      <div v-for="(column,index) in columns" :key="column.key" class="file-workspace-column-editor">
        <AppCheckBox v-model="column.visible" :label="column.title" :disabled="column.key==='path'" />
        <AppTextField v-model.number="column.width" label="Column width" inputmode="numeric" @change="column.width=Math.max(48,Math.min(900,column.width));captureView()" />
        <AppButton icon-only label="Move column left" icon="previous" @click="moveColumn(index,-1)" /><AppButton icon-only label="Move column right" icon="next" @click="moveColumn(index,1)" />
      </div><AppButton label="Close" @click="captureView();$refs.columnsDialog.close()" />
    </dialog>
    <dialog v-window="{type:'dialog'}" ref="tabEditor" class="configuration-dialog file-workspace-editor" :aria-label="t('Edit view tab')">
      <header><h2>{{ t('Edit view tab') }}</h2><AppButton icon-only label="Close" icon="close" @click="$refs.tabEditor.close()" /></header>
      <AppTextField v-model="tabDraft.title" label="Tab title" /><AppSelect v-model="tabDraft.preset" :options="viewPresets.map(tab=>({value:tab.id,label:tab.title}))" label="View" />
      <AppCheckBox v-if="tabDraft.preset==='history'" v-model="tabDraft.pinned" label="Pin file history" />
      <AppSelect v-if="tabDraft.preset!=='files'" v-model="tabDraft.scope" label="Changelist scope" :options="[{value:'mine',label:'My changes'},{value:'workspace',label:'This workspace'},{value:'stream',label:'This stream'},{value:'all',label:'All permitted changes'}]" />
      <AppSelect v-model="tabDraft.source" :options="viewOptions" label="File source" /><AppTextField v-model="tabDraft.prefix" label="Path prefix" />
      <footer><AppButton label="Cancel" @click="$refs.tabEditor.close()" /><AppButton label="Save" icon="save" :disabled="!tabDraft.title?.trim()" @click="saveTab" /></footer>
    </dialog>
    <dialog v-window="{ type:'popup' }" ref="comparisonDialog" class="record-dialog file-workspace-dialog" :aria-label="t('File comparison')" @cancel.prevent="!busy && $refs.comparisonDialog.close()">
      <header><h2>{{ t('File comparison') }}</h2><AppButton icon-only label="Close" icon="close" @click="$refs.comparisonDialog.close()" /></header>
      <div v-if="comparison" class="file-workspace-form">
        <p v-for="side in ['left','right']" :key="side">{{ comparison[side].path }} · {{ prettySize(comparison[side].size || 0) }} · {{ comparison[side].sha256 || '—' }}</p>
        <p v-if="comparison.kind!=='text'">{{ t('Open TACTIC-Handler for external comparison of binary or large files.') }}</p>
        <AppTextArea :model-value="comparison.text || ''" readonly label="Comparison result" />
      </div>
      <footer><AppButton label="Close" icon="close" @click="$refs.comparisonDialog.close()" /></footer>
    </dialog>
    <dialog ref="editor" class="record-dialog file-workspace-dialog" :aria-label="t({description:'Changelist description',offer:'Recipient login',goto:'Changelist number',rename:'New depot path',move:'Target changelist',unshelve:'Shelf changelist',merge:'Merge source stream'}[editorKind])" @cancel.prevent="!busy && $refs.editor.close()">
      <form @submit.prevent="saveEditor"><header><h2>{{ t({description:'Changelist description',offer:'Recipient login',goto:'Changelist number',rename:'New depot path',move:'Target changelist',unshelve:'Shelf changelist',merge:'Merge source stream'}[editorKind]) }}</h2><AppButton icon-only :label="busy ? 'Stop waiting' : 'Close'" icon="close" @click="busy ? stop() : ($refs.editor.close())" /></header>
        <AppTextArea v-if="editorKind==='description'" v-model="draft" label="Changelist description" :disabled="busy" />
        <AppSelect v-else-if="editorKind==='move'" v-model="draft" :options="changes.filter(item=>item.state==='pending'&&item.code!==change.code&&item.stream===change.stream).map(item=>({value:item.code,label:'#'+item.number+' · '+item.description}))" label="Target changelist" :translate-labels="false" :disabled="busy" />
        <AppTextField v-else v-model="draft" :placeholder="['unshelve','goto'].includes(editorKind) ? 'Changelist number, e.g. #42' : ''" :label="{offer:'Recipient login',goto:'Changelist number',rename:'New depot path',unshelve:'Shelf changelist',merge:'Merge source stream'}[editorKind]" :disabled="busy" />
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <p v-if="busy && progress.state==='Waiting for server'" role="status">{{ t('Waiting for server') }}</p>
        <footer><AppButton label="Cancel" icon="close" :disabled="busy" @click="$refs.editor.close()" /><AppButton :icon="{description:'save',offer:'account',goto:'search',move:'move',rename:'edit',unshelve:'archive',merge:'workflow'}[editorKind]" :label="{description:'Save description',offer:'Offer changelist ownership',goto:'Go to changelist',move:'Move files',rename:'Rename file',unshelve:'Unshelve',merge:'Merge stream'}[editorKind]" type="submit" highlighted :disabled="busy || (editorKind!=='description' && !draft)" /></footer>
      </form>
    </dialog>
    <dialog ref="setupDialog" class="record-dialog file-workspace-dialog" :aria-label="t(editingWorkspace?'Edit workspace':'Workspace setup')" @cancel.prevent="!busy && (setup=false)">
      <header><h2>{{ t(editingWorkspace?'Edit workspace':'Workspace setup') }}</h2><AppButton icon-only :label="busy ? 'Stop waiting' : 'Close'" icon="close" @click="busy ? stop() : (setup=false)" /></header><p v-if="error" class="error" role="alert">{{ t(error) }}</p><p v-if="busy && progress.state==='Waiting for server'" role="status">{{ t('Waiting for server') }}</p><div class="file-workspace-form"><AppSelect v-model="setupKind" :disabled="editingWorkspace" label="Create" :options="[{value:'workspace',label:'Workspace'},{value:'stream',label:'Stream'},{value:'depot',label:'Depot',disabled:!canAdminister}]" /><AppTextField :disabled="busy || editingWorkspace" v-model="code" label="Code" placeholder="Code" /><AppSelect :disabled="busy" v-if="setupKind === 'stream'" v-model="depot" :options="depots.map(item => ({value:item.code,label:item.title}))" label="Depot" :translate-labels="false" /><AppSelect :disabled="busy" v-if="setupKind === 'workspace'" v-model="stream" :options="streamOptions" label="Stream" :translate-labels="false" /><AppTextField :disabled="busy" v-if="setupKind === 'workspace'" v-model="root" label="Local workspace root" placeholder="Local workspace root" /><template v-if="setupKind==='workspace'"><AppCheckBox v-model="caseSensitive" label="Case-sensitive local paths" :disabled="busy" /><FileWorkspaceMappings v-model="mappings" :stream="stream" :disabled="busy" /><AppTextField :disabled="busy" v-model="samplePath" label="Sample depot path" /><AppButton label="Preview mappings" icon="visibility" :disabled="busy || !stream" @click="previewMappings" /><p v-for="row in mappingPreview?.items || []" :key="row.stream+'/'+row.source_path">{{ row.source_path }} → {{ row.excluded?t('Excluded by workspace mapping'):row.local_path }} · {{ t(row.writable?'Writable':'Read-only') }}</p></template><AppSelect :disabled="busy" v-if="setupKind === 'stream'" v-model="source" :options="[{value:'',label:'No parent stream'},...streamOptions]" label="Parent stream" :translate-labels="false" /><AppButton :label="editingWorkspace ? 'Save workspace' : 'Create'" :disabled="busy || !code" @click="saveSetup" /></div>
    </dialog>
    <dialog ref="storageDialog" class="record-dialog file-workspace-dialog" :aria-label="t('Storage administration')" @cancel.prevent="!busy && (storageOpen=false)">
      <header><h2>{{ t('Storage administration') }}</h2><AppButton icon-only :label="busy ? 'Stop waiting' : 'Close'" icon="close" @click="busy ? stop() : (storageOpen=false)" /></header><p v-if="error" class="error" role="alert">{{ t(error) }}</p><p v-if="busy && progress.state==='Waiting for server'" role="status">{{ t('Waiting for server') }}</p><div v-if="storage" class="file-workspace-form">      <p>{{ t('Allocated storage') }}: {{ prettySize(storage.allocated_bytes) }} · {{ storage.allocated_files }} {{ t('files') }}</p>
      <label>{{ t('Byte quota (0 = unlimited)') }}<AppTextField v-model="policy.bytes_limit" label="Byte quota (0 = unlimited)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('File quota (0 = unlimited)') }}<AppTextField v-model="policy.files_limit" label="File quota (0 = unlimited)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('Concurrent transfers') }}<AppTextField v-model="policy.max_parallel" label="Concurrent transfers" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('Upload retention (seconds)') }}<AppTextField v-model="policy.upload_retention_seconds" label="Upload retention (seconds)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('Reverted retention (seconds)') }}<AppTextField v-model="policy.reverted_retention_seconds" label="Reverted retention (seconds)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('Task retention (seconds)') }}<AppTextField v-model="policy.task_retention_seconds" label="Task retention (seconds)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('Shelf retention (seconds; 0 = keep)') }}<AppTextField v-model="policy.shelf_retention_seconds" label="Shelf retention (seconds; 0 = keep)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('GC grace period (seconds)') }}<AppTextField v-model="policy.gc_grace_seconds" label="GC grace period (seconds)" inputmode="numeric" :disabled="busy" /></label>
      <label>{{ t('GC interval (seconds; 0 = disabled)') }}<AppTextField v-model="policy.gc_interval_seconds" label="GC interval (seconds; 0 = disabled)" inputmode="numeric" :disabled="busy" /></label>
      <AppButton label="Save storage policy" :disabled="busy" @click="savePolicy" /><AppButton label="GC dry run" :disabled="busy" @click="startGc(true)" /><AppButton label="Run safe GC" :disabled="busy" @click="startGc(false)" />
      <p v-if="gc">{{ gc.code }} · {{ t(gc.state) }} · {{ gc.objects_done }} · {{ t('GC candidates') }}: {{ gc.candidates }} · {{ prettySize(gc.candidate_bytes) }} {{ gc.error }}</p><AppButton v-if="gc" label="GC status" :disabled="busy" @click="gcStatus" />
</div>
    </dialog>
  </section>
</template>
<style>
.file-workspace { display:flex; flex-direction:column; height:100%; min-height:0; min-width:0; gap:6px; padding:10px; overflow:hidden; }
.file-workspace-toolbar { display:flex; align-items:center; gap:6px; min-height:40px; }
.file-workspace-toolbar > .app-select { width:320px; max-width:40%; min-width:0; }.file-workspace-root { flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }.file-workspace-tree-toggle { display:none; }
.file-workspace-body { display:flex; flex:1; min-height:0; overflow:hidden; }.file-workspace-tree { flex:0 0 var(--file-tree-width); min-width:0; display:flex; flex-direction:column; padding:8px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface-deep); overflow:hidden; }.file-workspace-tree-scroll { flex:1; min-height:0; overflow:auto; scrollbar-gutter:stable; }
.file-workspace-tree h3 { margin:8px 0; font-size:var(--text-caption); font-weight:600; color:var(--muted); }.file-workspace-tree details { margin-bottom:8px; }.file-workspace-tree summary { display:flex; gap:6px; align-items:center; min-height:28px; cursor:pointer; }.file-workspace-tree .app-select { width:100%; margin-bottom:6px; }
.file-workspace-tree .app-button:not(.icon-button),.file-workspace-detail-list > .app-button { width:100%; height:32px; min-height:32px; justify-content:flex-start; padding:0 8px; border:0; border-radius:var(--item-radius); background:transparent; font-weight:400; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.file-workspace-tree .app-button[aria-pressed="true"],.file-workspace-detail-list > .app-button[aria-pressed="true"] { background:var(--content-selection); }.file-workspace-change-node ul { margin:2px 0 6px; padding-left:24px; list-style:none; }.file-workspace-change-node li { display:flex; align-items:center; gap:6px; height:28px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:var(--text-caption); }
.file-workspace-content { display:flex; flex-direction:column; flex:1; min-width:0; min-height:0; padding-left:4px; }.file-workspace-files { display:flex; flex-direction:column; flex:1; min-height:160px; overflow:hidden; }.file-workspace-files,.file-workspace-details { border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface-deep); padding:8px; }
.file-workspace-file-heading,.file-workspace-filter,.file-workspace-detail-tabs,.file-workspace-pagination { display:flex; align-items:center; gap:6px; min-height:34px; flex-shrink:0; }.file-workspace-file-heading > strong { flex:1; min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; font-size:var(--text-label); }.file-workspace-filter { margin-block:4px; }.file-workspace-filter > .app-select { flex:0 0 180px; min-width:0; }.file-workspace-filter > .app-text-field { flex:1; min-width:0; }.file-workspace .icon-button,.file-workspace .workspace-menu > summary { width:28px; height:28px; min-width:28px; min-height:28px; }
.file-workspace-table { flex:1; min-height:0; overflow:auto; scrollbar-gutter:stable; }.file-workspace-table table { width:100%; border-collapse:collapse; white-space:nowrap; }.file-workspace-table th,.file-workspace-table td { padding:3px 8px; text-align:left; border-bottom:1px solid var(--outline-variant); font-size:var(--text-caption); height:32px; }.file-workspace-table th { position:sticky; top:0; background:var(--surface); color:var(--muted); font-weight:400; }.file-workspace-table tr.selected { background:var(--content-selection); }.file-workspace-table td:nth-child(2) > .app-button { height:28px; min-height:28px; border:0; padding:0; font-weight:400; background:transparent; }.file-workspace-table td:nth-child(2) { width:100%; }.file-workspace-table th:first-child { width:28px; }.file-workspace-pagination > span { flex:1; font-size:var(--text-caption); }
.file-workspace-details { flex:0 0 var(--file-details-height); min-height:0; max-height:45%; display:flex; flex-direction:column; overflow:hidden; }.file-workspace-detail-tabs > .workspace-menu { margin-left:auto; }.file-workspace-detail-body { display:flex; flex:1; min-height:0; min-width:0; gap:8px; margin-top:6px; }.file-workspace-detail-list { flex:1; min-height:0; min-width:0; overflow:auto; scrollbar-gutter:stable; }.file-workspace-detail-body > .app-text-area { flex:1; min-width:0; resize:none; font-family:monospace; }.file-workspace-empty { text-align:center; font-size:var(--text-caption); padding:16px 8px; }
.file-workspace-progress { display:flex; align-items:center; gap:8px; min-height:30px; border-top:1px solid var(--outline-variant); font-size:var(--text-caption); }.file-workspace-progress > span { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }.file-workspace-progress > span:nth-child(2) { flex:1; min-width:0; }.file-workspace-progress progress { width:120px; accent-color:var(--primary); }
.file-workspace-dialog { width:min(620px,calc(100vw - 24px)); max-height:calc(100dvh - 24px); }.file-workspace-dialog header { display:flex; align-items:center; gap:8px; margin-bottom:16px; }.file-workspace-dialog h2 { flex:1; min-width:0; margin:0; font-size:var(--text-title); }.file-workspace-dialog footer { display:flex; justify-content:flex-end; gap:8px; margin-top:16px; }.file-workspace-form { display:flex; flex-direction:column; gap:10px; }.file-workspace-form > label { display:grid; grid-template-columns:1fr 130px; align-items:center; gap:12px; }.file-workspace-dialog textarea { width:100%; min-height:100px; }.file-workspace-dialog form > .app-text-field { width:100%; }.file-workspace-dialog .error { overflow-wrap:anywhere; }
@media(max-width:800px) { .file-workspace-toolbar > .app-select { flex:1; width:auto; max-width:none; }.file-workspace-root { display:none; }.file-workspace-tree-toggle { display:flex; }.file-workspace-body { flex-direction:column; }.file-workspace-tree { display:none; }.file-workspace-body.tree-open > .file-workspace-tree { display:flex; flex:0 0 150px; margin-bottom:4px; }.file-workspace-body > .app-splitter { display:none; }.file-workspace-content { padding-left:0; }.file-workspace-filter { gap:4px; }.file-workspace-filter > .app-select { flex:0 0 120px; }.file-workspace-files,.file-workspace-details { padding:6px; }.file-workspace-details { max-height:40%; }.file-workspace-detail-tabs { gap:2px; }.file-workspace-detail-tabs > .app-tab-button { flex:1; min-width:0; padding-inline:3px; font-size:var(--text-caption); }.file-workspace-progress > span:nth-child(2) { display:none; }.file-workspace-progress > span:first-child { flex:1; min-width:0; }.file-workspace-progress progress { width:60px; }.file-workspace-detail-body { flex-direction:column; }.file-workspace-detail-body > .app-text-area { min-height:55px; } }
.file-workspace-tree-section{display:flex;flex-direction:column;flex:1;min-height:0;gap:4px;border-bottom:1px solid var(--outline-variant);padding-bottom:6px}
.file-workspace-tree-section h3{display:flex;align-items:center;gap:6px;margin:4px 0;font-size:var(--text-label)}
.file-workspace-change-file{display:grid;grid-template-columns:28px minmax(120px,1fr) 110px 140px 48px 70px;align-items:center;gap:6px;min-width:0;flex:1;height:34px;border-bottom:1px solid var(--outline-variant);font-size:var(--text-caption)}
.file-workspace-change-file.selected{background:var(--content-selection)}
.file-workspace-change-file>.app-button{height:28px;min-height:28px;justify-content:flex-start;background:transparent;border:0;padding:0;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.file-workspace-change-file>span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(max-width:800px){.file-workspace-change-file{grid-template-columns:28px minmax(0,1fr) 80px}.file-workspace-change-file>span:nth-of-type(n+2){display:none}}
@media(max-width:800px){.file-workspace-body.tree-open>.file-workspace-tree{flex-basis:320px;max-height:45vh}}
.file-workspace-view-tabs,.file-workspace-tree-tabs{display:flex;gap:4px;overflow:auto;scrollbar-gutter:stable;flex-shrink:0;padding-bottom:4px}
.file-workspace-view-tabs>.app-tab-button,.file-workspace-tree-tabs>.app-tab-button{flex-shrink:0}
.file-workspace-content>.file-workspace-details{flex:1;max-height:none}
.file-workspace-tree-tabs>.app-tab-button{width:auto;flex:1;min-width:0}
.file-workspace-toolbar>.workspace-menu.labelled-menu{flex:none;min-width:64px}
.file-workspace-toolbar>.workspace-menu.labelled-menu>summary{width:max-content;min-width:64px}
</style>

<style scoped>
.file-workspace-address,.file-workspace-column-editor{display:flex;gap:6px;align-items:center}
.file-workspace-address>.app-text-field{flex:1;min-width:0}
.file-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.file-tone-error{color:var(--error)}
.file-tone-warning{color:var(--yellow)}
.file-tone-success{color:var(--success)}
.file-tone-action{color:var(--primary)}
.file-workspace-table tr.focused:not(.selected){background:var(--hover)}
.file-workspace-table td .app-icon{margin-right:6px}
</style>

<style scoped>
.file-workspace .workspace-menu.labelled-menu>summary{width:max-content;min-width:64px}
.file-workspace .workspace-menu.labelled-menu{flex:none}
.file-workspace-review-files{max-height:260px;overflow:auto;scrollbar-gutter:stable;padding-right:8px}
</style>

<style scoped>
.file-tone-other{color:var(--violet)}
</style>
