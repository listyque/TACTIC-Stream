import { copyText } from '../../controls/clipboard.js'
import { randomId } from '../../controls/identity.js'
import { t } from '../../i18n.js'

export function selectionReason(ctx,command) {
    const rows=Object.values(ctx.selectionRecords || {})
    const files=["checkout_ordinary","checkout_exclusive","move_files","remove_files","rename_file","mark_delete","upload_selected","stage_deletions","revert_unchanged","shelve_selected","replace_shelf","delete_shelf_files","apply_reconcile","open_local","reveal_local","delete_local","diff_local","diff_have","diff_shelf","file_history","sync_selected","revision_selected","reveal_tree"]
    if(files.indexOf(command)<0){
        const mutations=["submit","description","shelve","shelve_revert","compare_shelf","offer_change","revert","delete_change","unshelve_begin","rebase_begin","merge_begin","resume_upload","index_change","move_all_files"]
        if(mutations.indexOf(command)>=0){
            if(ctx.change?.depot_writable===false || ctx.streams.some(stream=>stream.code===ctx.change?.stream && stream.writable===false))return t("Depot write access is required")
            if(ctx.selectionScope==="changes" && new Set(rows.map(row=>row.parent || row.code)).size>1)return t("Select one changelist")
            if(ctx.change?.active_transfer || ctx.change?.active_bulk)return t("Finish the active changelist operation first")
            if(ctx.change?.integration)return t("Resolve the integration first")
        }
        return ""
    }
    if(!rows.length)return t("Select files first")
    if(rows.some(row=>(row.kind || "file")!=="file" || !row.path))return t("Select files without folders or changelists")
    if(ctx.selectionQuery)return t("Use the actions for the selected server query")
    const writes=["checkout_ordinary","checkout_exclusive","move_files","remove_files","rename_file","mark_delete","upload_selected","stage_deletions","revert_unchanged","shelve_selected","replace_shelf","delete_shelf_files","apply_reconcile"]
    if(writes.indexOf(command)>=0){
        if(rows.some(row=>row.depot_writable===false || ctx.streams.some(stream=>stream.code===(row.stream || ctx.stream) && stream.writable===false)))return t("Depot write access is required")
        if(rows.some(row=>row.writable===false))return t("Selection includes a read-only mapping")
        if(new Set(rows.map(row=>row.stream || ctx.stream)).size>1)return t("Select files from one stream")
        if(rows.some(row=>(ctx.locks[(row.stream || ctx.stream)+"\0"+(row.source_path || row.path)] || []).some(holder=>(holder.mode==="exclusive" || command==="checkout_exclusive") && (holder.owner!==ctx.login || holder.workspace!==ctx.workspace))))return t("The selected checkout conflicts with another changelist or workspace")
    }
    const pending=["move_files","remove_files","rename_file","revert_unchanged","shelve_selected","replace_shelf","diff_shelf"]
    if(pending.indexOf(command)>=0 && (ctx.view!=="change" && ctx.selectionScope!=="changes" || rows.some(row=>row.parent && row.parent!==ctx.change?.code || row.change_state && row.change_state!=="pending" || row.owner && row.owner!==ctx.login || row.workspace && row.workspace!==ctx.workspace)))return t("Select files from the current owned pending changelist")
    if(command==="delete_shelf_files" && rows.some(row=>row.parent && row.parent!==ctx.change?.code || row.change_state && row.change_state!=="shelved"))return t("Select files from the current shelf")
    if(["rename_file","diff_local","diff_have","diff_shelf","file_history","reveal_tree"].indexOf(command)>=0 && rows.length!==1)return t("Select one file")
    if(["open_local","delete_local","diff_local","diff_have"].indexOf(command)>=0 && rows.some(row=>["missing","unmapped"].indexOf(row.local_status)>=0))return t("A local copy is missing or not mapped")
    if(command==="reveal_local" && rows.some(row=>row.local_status==="unmapped"))return t("A local copy is missing or not mapped")
    if(command==="stage_deletions" && rows.some(row=>row.local_status!=="missing"))return t("Select missing local files")
    if(command==="upload_selected" && rows.some(row=>["added","modified"].indexOf(row.local_status)<0))return t("Select added or modified local files")
    if(command==="apply_reconcile" && rows.some(row=>["added","modified","missing"].indexOf(row.local_status)<0))return t("Select local changes")
    return ""
}

export function dropReason(ctx,target,payload,urls) {
    if(ctx.busy)return t("An operation is running")
    if(target.kind!=="change" || target.state!=="pending")return t("Choose a pending target changelist")
    if(target.owner!==ctx.login || target.workspace!==ctx.workspace)return t("Choose an owned pending changelist")
    if(target.depot_writable===false || ctx.streams.some(stream=>stream.code===target.stream && stream.writable===false))return t("Depot write access is required")
    if(target.active_transfer || target.active_bulk || target.integration)return t("Finish the active changelist operation first")
    if(!payload)return (urls || []).length>0 && urls.length<=1000 ? "" : t("Drop 1..1000 selected file or folder roots.")
    let data
    try{data=JSON.parse(payload)}catch(error){return t("Invalid file drag payload.")}
    if(!data || typeof data!=="object" || Array.isArray(data))return t("Invalid file drag payload.")
    if(data.project!==ctx.project || data.workspace!==ctx.workspace)return t("Drag files within the current project and workspace.")
    if(!Array.isArray(data.rows) || !data.rows.length || data.rows.length>1000)return t("Drop 1..1000 selected file or folder roots.")
    const rows=data.rows
    if(rows.some(row=>!row || typeof row!=="object" || (row.kind || "file")==="file" && (typeof row.path!=="string" || !row.path)))return t("Invalid file drag payload.")
    if(rows.some(row=>row.writable===false || row.stream && row.stream!==target.stream))return t("Select writable files from one changelist stream.")
    if(rows.length===1 && rows[0].state==="shelved")return ""
    if(rows.some(row=>["file","directory","stream","workspace"].indexOf(row.kind || "file")<0))return t("Drop files, folders or one stream into a pending changelist.")
    const parents=new Set(rows.filter(row=>row.parent && row.change_state==="pending").map(row=>row.parent))
    if(parents.has(target.code))return t("The files are already in this changelist")
    if(parents.size>1 || parents.size && rows.some(row=>!row.parent || row.change_state!=="pending"))return t("Select files from one changelist.")
    return ""
}


export const columns = [
  {key:'path',title:'File',width:300,visible:true},
  {key:'server_status',title:'Server state',width:130,visible:true},
  {key:'checkout',title:'Checkout / locks',width:140,visible:true},
  {key:'number',title:'Version',width:80,visible:true},
  {key:'have_number',title:'Have',width:72,visible:true},
  {key:'head_number',title:'Head',width:72,visible:true},
  {key:'size',title:'Size',width:90,visible:true},
  {key:'type',title:'Type',width:70,visible:true},
]
const viewFields=['view','state','stream','prefix','change','description','rows','selected','selectionIds',
  'selectionScope','selectionQuery','selectionRecords','anchorId','focusId','changes','changesAfter','changeChildren','expandedChanges',
  'history','historyPath','historyStream','changeRef','columns','sortColumn','sortDesc','nameFilter','statusFilter','scroll']

export function badges(row,holders=[],user='') {
  const result=[],action=row.action || row.server_status || '',local=row.local_status || ''
  if(row.transfer_state && !['staged','verified'].includes(row.transfer_state))result.push({label:{waiting:'Waiting for upload',uploading:'Uploading',uploaded:'Uploaded; waiting for verification',verifying:'Verifying',error:'Failed'}[row.transfer_state] || row.transfer_state,icon:'cloud-upload',tone:row.transfer_state==='error'?'error':'action'})
  if(local==='unmapped'||action==='unmapped')result.push({label:'Not mapped to workspace',icon:'folder-lock',tone:'neutral'})
  if(action==='move/add'||action==='move/delete')result.push({label:'Renamed / moved',icon:'move',tone:'action'})
  if(action==='checkout'&&!row.base&&!row.file)result.push({label:'Waiting for upload',icon:'cloud-upload',tone:'warning'})
  if(row.conflict || row.needs_resolve)result.push({label:'Conflict',icon:'warning',tone:'error'})
  if(row.error)result.push({label:'Failed',icon:'error',tone:'error'})
  if(local==='modified')result.push({label:action==='write'&&row.change_state==='pending'&&row.staged_current===false?'Modified after upload':'Modified',icon:'edit',tone:'warning'})
  if(local==='added')result.push({label:'Added',icon:'add',tone:'success'})
  if(local==='missing')result.push({label:'Missing',icon:'file-remove',tone:'error'})
  if(action==='delete' || row.deleted)result.push({label:'Marked for delete',icon:'delete',tone:'error'})
  if(row.staged_current===false&&local!=='modified')result.push({label:'Modified after upload',icon:'edit',tone:'warning'})
  if(action==='write'&&row.staged_current!==false)result.push({label:row.change_state==='shelved'?'Shelved':row.change_state==='submitted'?'Submitted':'Uploaded',icon:'cloud-check',tone:'success'})
  if(action==='checkout')result.push({label:'Checked out',icon:'edit',tone:'action'})
  if(action==='newer')result.push({label:'Newer on server',icon:'download',tone:'warning'})
  if(action==='server-only')result.push({label:'Server only',icon:'cloud',tone:'neutral'})
  if(action==='deleted')result.push({label:'Deleted on server',icon:'delete',tone:'error'})
  if(row.head_state==='server-only'&&action!=='server-only')result.push({label:'Server only',icon:'cloud',tone:'neutral'})
  if(row.head_state==='newer'&&action!=='newer')result.push({label:'Newer on server',icon:'download',tone:'warning'})
  if(row.head_state==='deleted'&&action!=='deleted')result.push({label:'Deleted on server',icon:'delete',tone:'error'})
  if(action==='untracked')result.push({label:'Untracked',icon:'file-plus',tone:'warning'})
  for(const holder of holders)result.push({label:holder.owner===user?(holder.mode==='exclusive'?'Exclusive checkout by you':'Checked out by you'):(holder.mode==='exclusive'?'Exclusive checkout by another user':'Checked out by another user'),icon:holder.mode==='exclusive'?'lock':'edit',tone:holder.owner===user?'action':'other'})
  return result.length?result:[{label:action==='current'||row.head_state==='current'?'Current':row.head_state==='server-absent'?'Not on server':'Published',icon:'file',tone:'neutral'}]
}

export function changeTreeRows(changes,children,expanded) {
  const parents=new Set(changes.filter(change=>change.state!=='shelved').map(change=>change.code)),ordered=[]
  for(const change of changes){
    if(change.state==='shelved'&&parents.has(change.source_change))continue
    ordered.push([change,0])
    if(expanded.includes(change.code))for(const shelf of changes.filter(item=>item.state==='shelved'&&item.source_change===change.code))ordered.push([shelf,1])
  }
  return ordered.flatMap(([change,depth])=>[{...change,id:change.code,kind:'change',depth,expanded:expanded.includes(change.code)},
    ...(expanded.includes(change.code)?[...(children[change.code]?.items || []).map(row=>({...row,id:change.code+'/'+row.path,kind:'file',depth:depth+1,stream:change.stream,parent:change.code,change_state:change.state,owner:change.owner,workspace:change.workspace})),
      ...(children[change.code]?.after?[{id:change.code+'//more',kind:'more',depth:depth+1,parent:change.code}]:[])]:[])])
}

export default {
  data(){return {selectionQuery:null,selectionRecords:{},selectionIds:[],selectionScope:'',anchorId:'',focusId:'',contextRow:null,fileFocus:null,changeRef:'',depotExpanded:[],workspaceExpanded:[],viewStates:{},
    columns:columns.map(column=>({...column})),sortColumn:'path',sortDesc:false,nameFilter:'',statusFilter:'',
    scroll:{},navigation:[],navigationIndex:-1,dropTarget:'',dragDraft:'',dropDraft:null,targetDraft:{},targetChanges:[],targetAfter:null}},
  computed:{
    visibleRows(){
      const rows=this.rows.filter(row=>(!this.nameFilter || row.path.toLowerCase().includes(this.nameFilter.toLowerCase()))
        && (!this.statusFilter || badges(row).some(badge=>badge.label===this.statusFilter)))
      const value=row=>['number','have_number','head_number','size'].includes(this.sortColumn)
        ? this.sortColumn==='have_number'?row.have?.number || 0:this.sortColumn==='head_number'?row.head?.number || 0:(row.file || row.head || row.have || row)[this.sortColumn] || 0
        : this.sortColumn==='type'?row.path.split('.').slice(1).pop() || ''
        : this.sortColumn==='checkout'?this.holders(row):String(row[this.sortColumn] || '').toLocaleLowerCase()
      return rows.sort((a,b)=>{const x=value(a),y=value(b);return (typeof x==='number'?x-y:x.localeCompare(y))*(this.sortDesc?-1:1)})
    },
    visibleColumns(){return this.columns.filter(column=>column.visible)},
  },
  methods:{badges(row){return badges(row,this.locks[(row.stream || this.stream)+'\0'+(row.source_path || row.path)] || [],this.login)},
    rowId(row){return JSON.stringify([this.workspace,row.stream || this.stream,row.parent || '',row.source_path || row.path])},
    scopeRows(scope){return (scope==='changes'?this.changeTree:scope==='files'?this.visibleRows:
      scope==='depot'?this.depotTree:scope==='workspace'?this.workspaceTree:this.history)
      .filter(row=>row.kind!=='more').map(row=>({id:scope==='files'?this.rowId(row):row.id || row.code || row.version,row}))},
    selectRow(scope,row,event={},menu=false){
      if(scope==='changes'&&this.dirty&&(row.parent || row.code)!==this.change.code){this.error='Save the changelist description before switching views.';return}
      const rows=this.scopeRows(scope),keys=rows.map(item=>item.id),id=scope==='files'?this.rowId(row):row.id || row.code || row.version
      let selected=this.selectionScope===scope?new Set(this.selectionIds):new Set()
      if(!(menu&&selected.has(id))){
        if(event.shiftKey&&keys.includes(this.anchorId)){
          const [first,last]=[keys.indexOf(this.anchorId),keys.indexOf(id)].sort((a,b)=>a-b)
          selected=new Set([...(event.ctrlKey || event.metaKey?selected:[]),...keys.slice(first,last+1)])
        }else if(event.ctrlKey || event.metaKey){selected.has(id)?selected.delete(id):selected.add(id);this.anchorId=id}
        else{selected=new Set([id]);this.anchorId=id}
      }
      if(selected.size>1000){this.error='Select at most 1000 loaded items, or use a server query selection.';return}
      const records=this.selectionScope===scope?this.selectionRecords:{}
      for(const item of rows)if(selected.has(item.id))records[item.id]=JSON.parse(JSON.stringify(item.row))
      this.selectionRecords=Object.fromEntries([...selected].filter(key=>records[key]).map(key=>[key,records[key]]))
      this.selectionQuery=null;this.selectionScope=scope;this.selectionIds=[...selected];this.focusId=id;this.contextRow=row
      if(row.path&&(row.kind || 'file')==='file'&&scope!=='history')this.fileFocus={path:row.source_path || row.path,stream:row.stream || this.stream}
      this.selected=this.selectedRows().filter(row=>row.path&&(row.kind || 'file')==='file').map(row=>row.path)
      if(scope==='changes'){
        const change=this.changes.find(item=>item.code===(row.parent || row.code))
        if(change&&!this.dirty){this.change=change;this.description=change.description || '';this.rows=this.changeChildren[change.code]?.items || []}
      }
    },
    selectFile(scope,row,selected){
      if(this.rowSelected(scope,row)===selected)return
      const filesOnly=this.selectionScope===scope && this.selectedRows().every(file=>(file.kind || 'file')==='file')
      this.selectRow(scope,row,{ctrlKey:filesOnly})
    },
    rowSelected(scope,row){return this.selectionScope===scope&&this.selectionIds.includes(scope==='files'?this.rowId(row):row.id || row.code || row.version)},
    selectedRows(){return this.selectionIds.map(id=>this.selectionRecords[id]).filter(Boolean)},
    selectionReason(command='checkout_ordinary'){return selectionReason(this,command)},
    keySelection(event,scope){
      const rows=this.scopeRows(scope)
      if((event.ctrlKey || event.metaKey)&&event.shiftKey&&event.key.toLowerCase()==='a'){this.selectQuery();event.preventDefault()}
      else if((event.ctrlKey || event.metaKey)&&event.key.toLowerCase()==='a'){this.selectionQuery=null;
        this.selectionScope=scope;this.selectionIds=rows.slice(0,1000).map(item=>item.id);this.selectionRecords=Object.fromEntries(rows.slice(0,1000).map(item=>[item.id,JSON.parse(JSON.stringify(item.row))]));this.selected=this.selectedRows().filter(row=>row.path&&(row.kind || 'file')==='file').map(row=>row.path);event.preventDefault()
      }else if(event.key==='Escape'){this.selectionQuery=null;this.selectionIds=[];this.selectionRecords={};this.selected=[];event.preventDefault()}
      else if(['ArrowUp','ArrowDown'].includes(event.key)){
        const index=rows.findIndex(item=>item.id===this.focusId),target=rows[Math.max(0,Math.min(rows.length-1,index+(event.key==='ArrowUp'?-1:1)))]
        if(target){this.selectRow(scope,target.row,event);this.$nextTick(()=>this.$el.querySelector(scope==='files'?'.file-workspace-table .focused':scope==='history'?'.file-workspace-detail-list [aria-pressed="true"]':'.file-tree-row[data-node="'+CSS.escape(target.id)+'"]')?.scrollIntoView({block:'nearest',inline:'nearest'}))}event.preventDefault()
      }else if(event.key==='Delete'&&this.canAdminister){this.markDelete();event.preventDefault()}
      else if(event.key==='c'&&(event.ctrlKey || event.metaKey)){this.copyPaths('depot');event.preventDefault()}
    },
    async rowMenu(event,scope,row){
      event.preventDefault();this.selectRow(scope,row,{},true)
      if(row.kind==='change')this.$refs.changeMenu.openAt(event)
      else if(row.path)this.$refs.fileMenu.openAt(event)
      else this.$refs.workspaceMenu.openAt(event)
    },
    async copyPaths(kind){
      const rows=this.selectedRows()
      try{
        let values=rows.map(row=>kind==='number'?'#'+row.number:'//'+(row.stream || this.stream)+'/'+(row.source_path || row.path || row.directory || ''))
        if(kind==='local'){
          const result=await this.command('workspace_paths',{workspace:this.workspace,paths:rows.map(row=>({stream:row.stream || this.stream,path:row.source_path || row.path}))})
          if(result.items.some(row=>row.excluded))throw new Error('The selected file is not mapped to this workspace.')
          values=result.items.map(row=>this.ws.local_root+'/'+row.path)
        }
        await copyText(values.join('\n'))
      }catch(error){this.error=error.message}
    },
    async gotoChange(reference){
      if(!this.canLeave())return
      await this.run(async client=>{
        if(/^https?:\/\//.test(reference)){
          const link=new URL(reference)
          if(decodeURIComponent(link.pathname)!=='/projects/'+this.project+'/')throw new Error('Open a changelist link from the current project.')
          const references=link.searchParams.getAll('changelist')
          if(references.length!==1)throw new Error('Paste a changelist number or link.')
          reference=references[0]
        }
        const change=await client.call('inspect_change',{change:reference.trim()})
        const id='change/'+change.code
        if(!this.tabs.some(tab=>tab.id===id)){
          if(this.tabs.length>=32)throw new Error('Close a view tab before opening another.')
          this.tabs.push({id,title:'#'+change.number,kind:'changes',state:change.state,change:change.code,scope:'all',custom:true,icon:'archive'})
        }
        this.captureView();this.activeTabId=id;this.change=change;this.description=change.description || '';this.state=change.state;this.view='change';this.prefix=''
        this.changes=[change];this.expandedChanges=[];this.changeChildren={};this.selectionIds=[];this.selected=[];this.selectionRecords={}
        await this.filesPage(client);this.rememberGeometry()
      })
    },
    async revealTree(){await this.run(async client=>{
      const rows=this.selectedRows().filter(row=>row.path&&(row.kind || 'file')==='file')
      if(rows.length!==1)throw new Error('Select one file to reveal.')
      const row=rows[0],stream=row.stream || this.stream,source=row.source_path || row.path
      const info=(await client.call('file_states',{workspace:this.workspace,paths:[{stream,path:source}]})).items[0],workspace=this.treeView==='depot'
      if(workspace&&info.excluded)throw new Error('The file is not mapped to this workspace.')
      if(!workspace&&!info.head)throw new Error('The file is not on the server yet.')
      const metadata=workspace?null:await client.call('stream_status',{stream})
      const tree=workspace?[{id:'workspace/'+this.workspace,kind:'workspace',name:this.workspace,directory:'',depth:0,expanded:true}]:[{id:'depot/'+metadata.depot,kind:'depot',name:metadata.depot,depth:0,expanded:true},{id:'stream/'+stream,kind:'stream',name:stream,stream,directory:'',depth:1,expanded:true}]
      const path=workspace?info.local_path:source,prefix=workspace?'workspace-path/':'path/'+stream+'/',parts=path.split('/');let directory='',depth=workspace?1:2
      for(const part of parts.slice(0,-1)){directory+=part+'/';tree.push({id:prefix+directory,kind:'directory',name:part,path:directory,directory,stream,depth,expanded:true});depth++}
      const item={...row,...info,id:prefix+path,kind:'file',name:parts.at(-1),path,source_path:source,stream,directory:'',depth};delete item.parent;delete item.change_state;tree.push(item)
      this.treeView=workspace?'workspace':'depot';this[workspace?'workspaceTree':'depotTree']=tree;this.treeSelection=item.id
      this.selectionScope=this.treeView;this.selectionIds=[item.id];this.selectionRecords={[item.id]:item};this.selected=[path]
    })},
    captureView(){if(this.activeTabId)this.viewStates[this.activeTabId]=structuredClone(Object.fromEntries(viewFields.map(key=>[key,JSON.parse(JSON.stringify(this[key]))])));this.rememberGeometry()},
    restoreView(id){const state=this.viewStates[id];if(state){const restored=JSON.parse(JSON.stringify(state)),kind=this.tabs.find(tab=>tab.id===id)?.kind;const current=kind==='conflicts'||kind==='files'&&!restored.change?this.change:this.change?.code===restored.change?.code?this.change:this.changes.find(change=>change.code===restored.change?.code);if(current){restored.change=JSON.parse(JSON.stringify(current));restored.description=current.description || ''}Object.assign(this,restored)}else{this.selectionIds=[];this.selectionRecords={};this.selectionQuery=null;this.selected=[];this.focusId='';this.anchorId='';this.scroll={}}},
    sortFiles(key){this.sortDesc=key===this.sortColumn&&!this.sortDesc;this.sortColumn=key;this.captureView()},
    moveColumn(index,delta){const target=index+delta;if(target<0||target>=this.columns.length)return;const column=this.columns.splice(index,1)[0];this.columns.splice(target,0,column);this.captureView()},
    columnValue(row,key){const file=row.file || row.head || row.have || row;return key==='path'?row.path:key==='server_status'?badges(row).map(badge=>t(badge.label)).join(' · '):key==='checkout'?this.holders(row):key==='have_number'?(row.have?'#'+row.have.number:'—'):key==='head_number'?(row.head?'#'+row.head.number:'—'):key==='number'?'#'+(file.number || '—'):key==='size'?this.prettySize(file.size || 0):row.path.split('.').slice(1).pop() || '—'},
    dragFiles(event,scope,row){
      this.selectRow(scope,row,{},true)
      const rows=this.selectedRows()
      this.dragDraft=JSON.stringify({project:this.project,workspace:this.workspace,scope,source:scope==='files'?this.view:scope,rows});event.dataTransfer.setData('application/x-tactic-file-workspace',this.dragDraft);event.dataTransfer.effectAllowed='copyMove'
      const preview=document.createElement('div');preview.textContent=rows.length+' '+t('selected');preview.style.cssText='position:absolute;left:-10000px;padding:8px;background:var(--surface);color:var(--text);border:1px solid var(--primary)'
      this.$el.append(preview);event.dataTransfer.setDragImage(preview,8,8);requestAnimationFrame(()=>preview.remove())
    },
    dropReason(row,payload=this.dragDraft){return !this.canAdminister?t('Read-only inspection'):dropReason(this,row,payload,[])},
    dropCaption(row){
      if(!this.dragDraft)return ''
      const rows=JSON.parse(this.dragDraft).rows
      if(rows.length===1 && rows[0].state==='shelved')return t('Restore shelf into changelist #{number}',{number:row.number})
      if(rows.every(file=>file.parent && file.change_state==='pending'))return t('Move {count} files to changelist #{number}',{count:rows.length,number:row.number})
      return t(rows.some(file=>['directory','stream','workspace'].includes(file.kind))?'Add {count} file or folder roots to changelist #{number}':'Add {count} files to changelist #{number}',{count:rows.length,number:row.number})
    },
    acceptDrop(event,row){this.dropTarget='';if(this.dropReason(row))return;event.preventDefault();this.dropTarget=row.code},
    async dropFiles(event,row){
      event.preventDefault();this.dropTarget=''
      const text=event.dataTransfer.getData('application/x-tactic-file-workspace');if(!text)return
      const reason=this.dropReason(row,text);if(reason){this.error=reason;return}
      let payload;try{payload=JSON.parse(text)}catch{this.error='Invalid file drag payload.';return}
      if(payload.project!==this.project || payload.workspace!==this.workspace || row.workspace!==this.workspace){this.error='Drag files within the current project and workspace.';return}
      if(!this.confirm(t('Add dropped files to changelist {number}?',{number:row.number})))return
      if(payload.rows.length===1 && payload.rows[0].state==='shelved'){
        this.targetDraft={operation:'unshelve_begin',target:row.code,creating:false,shelf:payload.rows[0].code,shelfStream:payload.rows[0].stream}
        await this.targetFiles()
        return
      }
      await this.run(async client=>{
        if(!Array.isArray(payload.rows)||payload.rows.length<1||payload.rows.length>1000)throw new Error('Drop 1..1000 selected file or folder roots.')
        const destination=await client.call('status',{change:row.code}),parents=new Set(payload.rows.map(file=>file.parent))
        if(parents.size===1&&!parents.has(undefined)&&payload.rows.every(file=>(file.kind || 'file')==='file'&&(!file.change_state||file.change_state==='pending'))){
          const source=await client.call('status',{change:[...parents][0]})
          await client.call('move_files',{change:source.code,edit_revision:source.edit_revision,target_change:destination.code,target_edit_revision:destination.edit_revision,paths:payload.rows.map(file=>file.path),request_id:randomId()})

        }else{
          if(payload.rows.some(file=>file.stream&&file.stream!==destination.stream))throw new Error('Select writable files from one changelist stream.')
          const paths=[],directories=[],local_directories=[]
          for(const file of payload.rows){
            const kind=file.kind || 'file'
            if(kind==='file')paths.push(file.source_path || file.path)
            else if(['directory','stream','workspace'].includes(kind))(payload.scope==='workspace'?local_directories:directories).push(file.directory ?? file.path ?? '')
            else throw new Error('Drop files, folders or one stream into a pending changelist.')
          }
          const result=await client.call('checkout',{change:destination.code,edit_revision:destination.edit_revision,mode:'ordinary',paths,directories,local_directories,request_id:randomId()})
          this.progress={state:'complete',files_done:result.paths}
        }
        this.change=destination;await this.refreshChange(client)
      })
    },
    async selectQuery(){await this.run(async client=>{
      if(!['depot','have','change'].includes(this.view))throw new Error('Select a server file view for a query selection')
      if(!['','Uploaded','Marked for delete','Checked out'].includes(this.statusFilter))throw new Error('Query selections use server file actions; inspect local states with Reconcile.')
      const values={source:this.view,prefix:this.prefix,name:this.nameFilter,file_action:({'Uploaded':'write','Marked for delete':'delete','Checked out':'checkout'})[this.statusFilter] || ''}
      if(this.view==='depot')values.stream=this.stream;else if(this.view==='have')values.workspace=this.workspace;else values.change=this.change.code
      this.selectionQuery=await client.call('select_query',values);this.selectionIds=[];this.selected=[]
    })},
    async markDelete(){if(!this.canAdminister||!this.editable||!this.selected.length)return;if(!this.confirm(t('Mark the selected files for depot deletion on submit?')))return;await this.run(async client=>{await client.call('edit',{change:this.change.code,edit_revision:this.change.edit_revision,chunk:randomId(),operations:this.paths().map(path=>({path,delete:true}))});await this.refreshChange(client)})},
    async pickTarget(operation,mode='ordinary'){
      if(!this.canAdminister||this.busy||!this.selected.length&&!['restore_file','unshelve_begin'].includes(operation)&&!operation.startsWith('bulk_'))return
      await this.run(async client=>{
        const page=await client.call('changes',{state:'pending',workspace:this.workspace,limit:200})
        this.targetChanges=page.items;this.targetAfter=page.after
        this.targetDraft={operation,mode,revision:operation==='restore_file'?JSON.parse(JSON.stringify(this.detail)):null,shelf:operation==='unshelve_begin'?this.change.code:'',shelfStream:this.change?.stream,stream:['bulk_move','unshelve_begin','move_files'].includes(operation)?this.change?.stream:this.selectedRows()[0]?.stream || this.stream,target:this.editable&&!['move_files','bulk_move','bulk_checkout'].includes(operation)?this.change.code:'',creating:false,description:''}
      })
      if(!this.error)this.$refs.targetDialog.showModal()
    },
    async targetFiles(){
      if(this.targetDraft.operation==='unshelve_begin'){
        const draft=this.targetDraft
        await this.run(async client=>{
          if(!draft.target&&!draft.creating)throw new Error('Choose a target changelist or create one explicitly.')
          const destination=draft.creating?await client.call('create_change',{workspace:this.workspace,stream:draft.shelfStream,description:draft.description}):await client.call('status',{change:draft.target})
          if(destination.state!=='pending'||destination.stream!==draft.shelfStream)throw new Error('Choose a pending changelist in the shelf stream.')
          this.captureView();this.activeTabId='pending';if(!this.tabs.some(tab=>tab.id==='pending'))this.tabs.push({...this.viewPresets.find(tab=>tab.id==='pending')});this.state='pending';this.view='change';this.prefix='';this.stream=destination.stream;this.selectionIds=[];this.selectionRecords={};this.selected=[];
          this.change=destination;this.description=destination.description || '';await this.refreshChange(client);this.rememberGeometry()
        })
        if(!this.error){this.$refs.targetDialog.close();await this.integrationBegin('unshelve_begin',{shelf:draft.shelf})}
        return
      }
      if(this.targetDraft.operation.startsWith('bulk_')){await this.bulkTarget();return}
      await this.run(async client=>{
        const draft=this.targetDraft,rows=draft.operation==='restore_file'?[draft.revision]:this.selectedRows().filter(row=>row.path&&(row.kind || 'file')==='file')
        if(!rows.length)throw new Error('Select files first.')
        if(!draft.target&&!draft.creating)throw new Error('Choose a target changelist or create one explicitly.')
        const stream=rows[0].stream || this.change?.stream || this.stream,parents=new Set(rows.map(row=>row.parent))
        if(rows.some(row=>row.stream&&row.stream!==stream||row.writable===false))throw new Error('Select writable files from one changelist stream.')
        if(draft.operation==='move_files'&&parents.size>1)throw new Error('Select files from one changelist.')
        const source=draft.operation==='move_files'?await client.call('status',{change:rows[0].parent || this.change.code}):null
        const destination=draft.creating?await client.call('create_change',{workspace:this.workspace,stream,description:draft.description}):await client.call('status',{change:draft.target})
        if(destination.state!=='pending'||destination.stream!==stream)throw new Error('Choose a pending target in the selected stream.')
        const paths=rows.map(row=>row.source_path || row.path)
        if(draft.operation==='restore_file')await client.call('restore_file',{change:destination.code,edit_revision:destination.edit_revision,path:draft.revision.path,published_change:draft.revision.change,request_id:randomId()})
        else if(draft.operation==='move_files')await client.call('move_files',{change:source.code,edit_revision:source.edit_revision,target_change:destination.code,target_edit_revision:destination.edit_revision,paths,request_id:randomId()})
        else if(draft.operation==='mark_delete')await client.call('edit',{change:destination.code,edit_revision:destination.edit_revision,chunk:randomId(),operations:paths.map(path=>({path,delete:true}))})
        else await client.call('checkout',{change:destination.code,edit_revision:destination.edit_revision,paths,mode:draft.mode,request_id:randomId()})
        this.change=destination;this.description=destination.description || '';await this.refreshChange(client)
      })
      if(!this.error)this.$refs.targetDialog.close()
    },
    async renameFile(){if(this.selected.length!==1||!this.editable)return;this.editorKind='rename';this.draft=this.contextRow?.source_path || this.contextRow?.path || this.selected[0];this.$refs.editor.showModal()},
    async renameSelected(){await this.run(async client=>{await client.call('rename_files',{change:this.change.code,edit_revision:this.change.edit_revision,request_id:randomId(),renames:[{source:this.paths()[0],target:this.draft}]});await this.refreshChange(client)})},
    async deleteChange(){
      if(!this.canAdminister || !this.change || this.busy)return
      if(this.pending && this.change.opened_files!==0){this.$refs.nonemptyDelete.showModal();return}
      if(!this.confirm(t('Delete this empty changelist or shelf?')))return
      await this.run(async client=>{await client.call('delete_change',{change:this.change.code,edit_revision:this.change.edit_revision,request_id:randomId()});this.change=null;this.description='';this.selected=[];this.selectionIds=[];await this.changePage(client);this.rows=[]})
    },
    async moveWholeChange(){
      this.$refs.nonemptyDelete.close()
      await this.run(async client=>{this.selectionQuery=await client.call('select_query',{source:'change',change:this.change.code});this.selectionIds=[];this.selectionRecords={};this.selected=[]})
      if(!this.error)await this.pickTarget('bulk_move')
    },
    async navigate(path,restore=false){
      const match=/^\/\/([^/]+)\/(.*)$/.exec(path.trim());if(!match||!this.streams.some(stream=>stream.code===match[1])){this.error='Select a stream available in this project.';return}
      this.filesContext={stream:match[1],prefix:match[2],source:'depot'};this.stream=match[1];this.prefix=match[2]
      const tab=this.tabs.find(item=>item.kind==='files')
      if(tab)await this.activateTab(tab);else await this.openView('files')
      this.view='depot';this.stream=match[1];this.prefix=match[2];await this.showFiles()
      if(!restore){this.navigation.splice(this.navigationIndex+1);this.navigation.push(path);this.navigation=this.navigation.slice(-100);this.navigationIndex=this.navigation.length-1}
    },
  },
}
