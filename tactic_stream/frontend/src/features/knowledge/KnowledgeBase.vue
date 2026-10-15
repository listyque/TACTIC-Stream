<script setup>
import { randomId } from '../../controls/identity.js'
// Handler KnowledgeBaseView, KnowledgeNavigation and KnowledgeController (EPL-1.0).
import { computed, inject, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { knowledgeRequest, messageFileRequest, linkPreviews } from '../../api.js'
import { t } from '../../i18n.js'
import { copyText } from '../../controls/clipboard.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AttachmentCard from '../../controls/AttachmentCard.vue'
import SKeyPreviewCard from '../objects/SKeyPreviewCard.vue'
import { messageDate } from '../messages/messages.js'
import { appearance } from '../../appearance.js'
import { extractSkeys } from '../../controls/richText.js'
import KnowledgeEditor from './KnowledgeEditor.vue'
import { articleHtml, plainText } from './markdown.js'

const props=defineProps({ ticket:String, project:String, login:String, active:Boolean, selection:Array, target:String })
const emit=defineEmits(['session-expired','changed','open-link','location'])
const openObjectTab=inject('openObjectTab',null)
const host=ref(null), width=ref(0), initialized=ref(false), canEdit=ref(false), canInitialize=ref(false)
const catalog=ref([]), query=ref(''), identity=ref(''), searchKey=ref(''), revision=ref(''), catalogRevision=ref(''), selected=ref('')
const document=ref(null), metadata=ref({}), files=ref([]), editing=ref(false), step=ref(0), expandedMetadata=ref(false)
const navigationExpanded=ref(true), navigationPage=ref(true), tocVisible=ref(true), resourcesVisible=ref(false), attachmentsVisible=ref(false)
const loading=ref(false), saving=ref(false), error=ref(''), storageError=ref(false), loaded=ref(false)
const drafts=reactive({}), collapsed=reactive(new Set()), organization=ref(null), dragging=ref(''), dropTarget=ref('')
const editor=ref(null), viewer=ref(null), fileInput=ref(null), confirmation=ref(null), historyDialog=ref(null), deletion=ref(null), moveDialog=ref(null)
const pendingFiles=ref([]), copying=ref(''), deletingFile=ref(null), deleteGroups=ref([]), deleteTypes=ref([]), moveParent=ref(''), moveIdentity=ref('')
const histories=ref([]), historyPreview=ref(null), references=ref({}), linkedIndex=ref(0)
const stagedFiles=new Map()
let request=0, historyRequest=0, previewRequest=0, observer, searchTimer, original='', context=''
const scope=computed(()=>`tactic_stream.knowledge.${props.login}.${props.project}`)
const narrow=computed(()=>width.value<720), single=computed(()=>narrow.value||!navigationExpanded.value)
const pageWidth=computed(()=>width.value-16-(single.value?0:17+Math.min(310,(width.value-16)*.34)))
const articleNarrow=computed(()=>pageWidth.value<720)
const creating=computed(()=>identity.value.startsWith('local:'))
const dirty=computed(()=>editing.value&&JSON.stringify(document.value)!==original)
const shown=computed(()=>historyPreview.value?.document||document.value)
const html=computed(()=>articleHtml(shown.value?.contentMarkdown||'',props.project))
const toc=computed(()=>{ const root=documentElement(html.value); return [...root.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(node=>({title:node.textContent,level:Number(node.tagName[1]),id:node.id})) })
const minutes=computed(()=>Math.max(1,Math.ceil((shown.value?.contentText||plainText(shown.value?.contentMarkdown)).trim().split(/\s+/).filter(Boolean).length/200)))
const entries=computed(()=>{
  const rows=new Map(catalog.value.map(row=>[row.identity,row]))
  for (const [id,draft] of Object.entries(drafts)) if (!query.value || `${draft.document.title}\n${draft.document.description}\n${draft.document.contentMarkdown}`.toLowerCase().includes(query.value.toLowerCase())) rows.set(id,{identity:id,title:draft.document.title||t('Untitled article'),description:draft.document.description,parentCode:draft.document.parentCode,kind:draft.document.kind,sortOrder:draft.document.sortOrder||0,draft:draft.document.draft,localDraft:true})
  const values=[...rows.values()], result=[], seen=new Set()
  function append(parent,depth) { for (const row of values.filter(row=>row.parentCode===parent).sort(compare)) { if(seen.has(row.identity)) continue; seen.add(row.identity); const children=values.some(child=>child.parentCode===row.identity); result.push({...row,depth,hasChildren:children,expanded:!collapsed.has(row.identity)}); if(children&&!collapsed.has(row.identity)) append(row.identity,depth+1) } }
  append('',0)
  for (const row of values) if (!seen.has(row.identity) && !values.some(parent=>parent.identity===row.parentCode)) { result.push({...row,depth:0,hasChildren:false});seen.add(row.identity) }
  return result
})
const sectionEntries=computed(()=>{
  const result=[],seen=new Set()
  function append(parent,level) { for(const row of catalog.value.filter(row=>row.parentCode===parent).sort(compare)) { if(seen.has(row.identity))continue; seen.add(row.identity);result.push({...row,level});append(row.identity,level+1) } }
  append(identity.value,1);return result
})
const parentTitle=computed(()=>catalog.value.find(row=>row.identity===document.value?.parentCode)?.title||t('Knowledge Base root'))
const sectionOptions=computed(()=>[{value:'',label:t('Knowledge Base root')},...catalog.value.filter(row=>row.kind==='section').map(row=>({value:row.identity,label:row.title}))])
const linked=computed(()=>document.value?.linkedSearchKeys||[])
const linkedObject=computed(()=>references.value[linked.value[linkedIndex.value]])
const resourceKeys=computed(()=>[...new Set([...linked.value,...extractSkeys(shown.value?.contentMarkdown||'')])])
const clipboardAvailable=!!navigator.clipboard?.read
function documentElement(text) { const root=window.document.createElement('div');root.innerHTML=text;return root }
function compare(a,b) { return a.sortOrder-b.sortOrder||Number(a.kind!=='section')-Number(b.kind!=='section')||a.title.localeCompare(b.title) }
function storeDrafts() {
  try { localStorage.setItem(scope.value,JSON.stringify(drafts));storageError.value=false;return true }
  catch { storageError.value=true;error.value=t('Local drafts could not be saved. Keep this page open and save to the server.');return false }
}
function checkpoint() {
  if(identity.value&&scope.value===context)try{localStorage.setItem(scope.value+'.state',JSON.stringify({identity:identity.value,navigationExpanded:navigationExpanded.value,tocVisible:tocVisible.value,collapsed:[...collapsed]}))}catch{storageError.value=true}
  if (!editing.value||!document.value||!identity.value) return
  if (dirty.value||creating.value) drafts[identity.value]={document:JSON.parse(JSON.stringify(document.value)),revision:revision.value,searchKey:searchKey.value,step:step.value,attachments:files.value,metadata:metadata.value}
  storeDrafts()
}
function clearPage(forget=false) { if(forget){try{localStorage.removeItem(scope.value+'.state')}catch{storageError.value=true};emit('location','')};document.value=null; identity.value='';selected.value='';searchKey.value='';revision.value='';editing.value=false;files.value=[];histories.value=[];historyPreview.value=null; navigationPage.value=true }
function applyCommon(result) { initialized.value=result.initialized;canEdit.value=result.canEdit;canInitialize.value=result.canInitialize;if(result.catalog)catalog.value=result.catalog;if(result.catalogRevision)catalogRevision.value=result.catalogRevision }
function applyPage(result,edit=false) {
  applyCommon(result)
  if(result.entryMissing){clearPage(true);error.value=t('This page is no longer available.');return}
  document.value=result.document;identity.value=selected.value=result.identity;searchKey.value=result.searchKey;revision.value=result.revision;metadata.value=result.articleMetadata||{};files.value=result.attachments||[]
  if(searchKey.value)emit('location',searchKey.value)
  original=JSON.stringify(document.value);editing.value=edit;step.value=1;expandedMetadata.value=false;navigationPage.value=false;historyPreview.value=null;histories.value=[];resourcesVisible.value=false;linkedIndex.value=0
}
async function call(action,values={}) { return knowledgeRequest(action,props.ticket,props.project,values) }
function fail(reason) { error.value=t(reason.message);if(reason.code==='authentication_failed')emit('session-expired') }
async function reload() {
  if(saving.value||organization.value||!props.ticket||!props.project)return
  checkpoint();const id=++request;loading.value=true;error.value=''
  try {const result=await call('list',{query:query.value});if(id!==request)return;applyCommon(result);loaded.value=true;if(!identity.value){const state=JSON.parse(localStorage.getItem(scope.value+'.state')||'{}');if(state.identity)await select(state.identity)}}
  catch(reason){if(id===request)fail(reason)}finally{if(id===request)loading.value=false}
}
async function select(id) {
  if(saving.value)return
  checkpoint();stagedFiles.set(identity.value,pendingFiles.value);pendingFiles.value=stagedFiles.get(id)||[];selected.value=id;navigationPage.value=false;const turn=++request;loading.value=true;error.value=''
  const draft=drafts[id]
  if(draft){document.value=JSON.parse(JSON.stringify(draft.document));identity.value=id;searchKey.value=draft.searchKey;revision.value=draft.revision;files.value=draft.attachments||[];metadata.value=draft.metadata||{};editing.value=true;step.value=draft.step||0;expandedMetadata.value=step.value===0||document.value.kind==='section';original='';historyPreview.value=null;loading.value=false;emit('location',searchKey.value||'');return}
  try {const result=await call('load',{identity:id,query:query.value});if(turn!==request)return;if(drafts[result.identity]){applyCommon(result);await select(result.identity)}else applyPage(result)}
  catch(reason){if(turn===request)fail(reason)}finally{if(turn===request)loading.value=false}
}
function create(kind) {
  if(saving.value||organization.value)return
  checkpoint();stagedFiles.set(identity.value,pendingFiles.value);pendingFiles.value=[];request++;const parent=document.value?.kind==='section'?identity.value:document.value?.parentCode||''
  identity.value=selected.value='local:'+randomId();searchKey.value='';revision.value='';metadata.value={};files.value=[]
  document.value={title:'',description:'',kind,parentCode:parent.startsWith('local:')?'':parent,contentMarkdown:'',contentText:'',linkedSearchKeys:[],sortOrder:0,draft:true}
  original='';editing.value=true;step.value=0;expandedMetadata.value=true;navigationPage.value=false;attachmentsVisible.value=false;historyPreview.value=null;error.value='';checkpoint();emit('location','')
}
function beginEdit() {if(organization.value)return;editing.value=true;expandedMetadata.value=document.value.kind==='section';step.value=1;original=JSON.stringify(document.value)}
async function save(draft=false,reserve=false) {
  if(saving.value||!document.value)return false
  if(!document.value.title.trim()){error.value=t('Enter a title');expandedMetadata.value=true;step.value=0;return false}
  const current=identity.value,turn=request, ticket=props.ticket,project=props.project
  const values=JSON.parse(JSON.stringify(document.value));values.contentText=plainText(values.contentMarkdown)
  saving.value=true;error.value='';checkpoint()
  try {
    const result=await knowledgeRequest(reserve?'reserve':draft?'save_draft':'save',ticket,project,{identity:creating.value?'':current,expected_revision:revision.value,document:values})
    if(turn!==request||ticket!==props.ticket||project!==props.project)return false
    delete drafts[current];storeDrafts();applyPage(result,draft||reserve);emit('changed');return true
  }catch(reason){if(turn===request)fail(reason);return false}finally{saving.value=false}
}
async function discard() {
  const id=identity.value;delete drafts[id];storeDrafts()
  if(creating.value){clearPage(true);return}
  editing.value=false;await select(id)
}
function search() {if(organization.value||saving.value)return;clearTimeout(searchTimer);searchTimer=setTimeout(reload,220)}
function move(source,target,placement='inside') {
  if(!canEdit.value||saving.value||editing.value||creating.value)return
  const rows=JSON.parse(JSON.stringify(catalog.value)), item=rows.find(row=>row.identity===source),to=rows.find(row=>row.identity===target)
  if(!item||!to||item===to)return
  const parent=placement==='inside'?to.identity:to.parentCode
  if(placement==='inside'&&to.kind!=='section')return
  let ancestor=parent;const seen=new Set([source])
  while(ancestor){if(seen.has(ancestor)){error.value=t('A section cannot be moved inside its child');return};seen.add(ancestor);ancestor=rows.find(row=>row.identity===ancestor)?.parentCode||''}
  organization.value ||= JSON.parse(JSON.stringify(catalog.value))
  item.parentCode=parent
  const siblings=rows.filter(row=>row.parentCode===parent&&row.identity!==source).sort(compare)
  const index=placement==='inside'?siblings.length:siblings.findIndex(row=>row.identity===target)+(placement==='after'?1:0)
  siblings.splice(Math.max(0,index),0,item);siblings.forEach((row,index)=>{row.sortOrder=index})
  catalog.value=rows;dropTarget.value='';if(document.value&&identity.value===source)document.value.parentCode=parent
}
function drop(event,row) {event.preventDefault();const box=event.currentTarget.getBoundingClientRect(),point=(event.clientY-box.top)/box.height;move(dragging.value,row.identity,point<.34?'before':point>.66?'after':row.kind==='section'?'inside':'after');dragging.value='';dropTarget.value=''}
function reorder(id,direction) {const item=catalog.value.find(row=>row.identity===id),siblings=catalog.value.filter(row=>row.parentCode===item.parentCode).sort(compare),target=siblings[siblings.indexOf(item)+direction];if(target)move(id,target.identity,direction<0?'before':'after')}
async function saveOrder() {
  if(!organization.value||saving.value)return;saving.value=true;error.value=''
  try {const result=await call('organize',{organization:catalog.value.map(({identity,parentCode,sortOrder})=>({identity,parentCode,sortOrder})),expected_revision:catalogRevision.value});applyCommon(result);organization.value=null;emit('changed')}
  catch(reason){fail(reason)}finally{saving.value=false}
}
function undoOrder(){catalog.value=organization.value;organization.value=null;if(document.value)document.value.parentCode=catalog.value.find(row=>row.identity===identity.value)?.parentCode||''}
function openMove(id){moveIdentity.value=id;moveParent.value=catalog.value.find(row=>row.identity===id)?.parentCode||'';moveDialog.value.showModal()}
function applyMove(){if(moveParent.value)move(moveIdentity.value,moveParent.value,'inside');else{const root=catalog.value.find(row=>!row.parentCode&&row.identity!==moveIdentity.value);if(root)move(moveIdentity.value,root.identity,'after');else{organization.value ||= JSON.parse(JSON.stringify(catalog.value));catalog.value=catalog.value.map(row=>row.identity===moveIdentity.value?{...row,parentCode:''}:row)}};moveDialog.value.close()}
async function initialize(){confirmation.value.close();saving.value=true;error.value='';try{applyCommon(await call('initialize'));loaded.value=true}catch(reason){fail(reason)}finally{saving.value=false}}
async function history(event){if(!event.target.open)return;histories.value=[];const id=++historyRequest;try{const result=await call('history',{identity:identity.value});if(id===historyRequest)histories.value=result.history}catch(reason){if(id===historyRequest)fail(reason)}}
async function previewHistory(id){const current=identity.value,turn=++historyRequest;try{const result=await call('history_revision',{identity:current,history_revision:id});if(current===identity.value&&turn===historyRequest){historyPreview.value=result.historyRevision;historyDialog.value.close()}}catch(reason){if(turn===historyRequest)fail(reason)}}
async function refreshFiles(){const id=request,current=identity.value;const result=await call('attachments',{identity:current});if(id===request&&current===identity.value){files.value=result.attachments||[];checkpoint()}}
async function addFiles(selectedFiles){
  if(!canEdit.value||saving.value||!selectedFiles.length)return
  pendingFiles.value.push(...selectedFiles.map(file=>({file,status:'ready',error:''})));attachmentsVisible.value=true
  if(creating.value && !await save(true,true))return
  await uploadPending()
}
async function uploadPending(){
  if(saving.value||creating.value)return
  const current=identity.value,project=props.project,ticket=props.ticket;saving.value=true
  try{for(const entry of pendingFiles.value.filter(entry=>entry.status!=='done')){entry.status='uploading';entry.error='';try{const result=await messageFileRequest(ticket,project,{identity:current},entry.file,'knowledge');entry.status='done';if(identity.value===current&&project===props.project)files.value=result.attachments||[]}catch(reason){entry.status='failed';entry.error=reason.message}}checkpoint()}finally{saving.value=false}
}
async function pasteImage(){try{const items=await navigator.clipboard.read();const selected=[];for(const item of items){const type=item.types.find(type=>type.startsWith('image/'));if(type)selected.push(new File([await item.getType(type)],'clipboard.png',{type}))}await addFiles(selected)}catch(reason){fail(reason)}}
function confirmFile(file){deletingFile.value=file;deletion.value.showModal()}
async function removeFile(){const file=deletingFile.value;deletion.value.close();saving.value=true;try{const result=await call('delete_attachment',{identity:identity.value,attachment_key:file.snapshotKey});files.value=result.attachments||[];checkpoint()}catch(reason){fail(reason)}finally{saving.value=false}}
async function copy(value,token=''){try{await copyText(value);copying.value=token}catch(reason){fail(reason)}}
async function openDeletion(){if(creating.value){await discard();return};deleteGroups.value=[];deleteTypes.value=[];deletingFile.value=null;deletion.value.showModal();loading.value=true;try{const result=await call('deletion',{identity:identity.value});deleteGroups.value=result.groups;deleteTypes.value=result.groups.filter(row=>row.selected).map(row=>row.search_type)}catch(reason){fail(reason);deletion.value.close()}finally{loading.value=false}}
async function deletePage(){saving.value=true;error.value='';try{applyCommon(await call('delete',{identity:identity.value,expected_revision:revision.value,related_types:deleteTypes.value}));delete drafts[identity.value];storeDrafts();deletion.value.close();clearPage(true);emit('changed')}catch(reason){fail(reason)}finally{saving.value=false}}
function linkSelection(){const keys=(props.selection||[]).map(row=>'skey://'+row.__search_key__.replace(/^skey:\/\//,''));document.value.linkedSearchKeys=[...new Set([...linked.value,...keys])].slice(0,128);checkpoint()}
function unlink(){document.value.linkedSearchKeys=linked.value.filter((_,index)=>index!==linkedIndex.value);linkedIndex.value=Math.max(0,linkedIndex.value-1);checkpoint()}
async function loadReferences(){const turn=++previewRequest,keys=resourceKeys.value;try{const result=await linkPreviews(props.ticket,props.project,keys);if(turn===previewRequest)references.value=Object.fromEntries(result.previews.map(row=>[row.searchKey,row]))}catch(reason){if(turn===previewRequest)fail(reason)}}
function activate(event){const anchor=event.target.closest('a'),image=event.target.closest('img');if(anchor){const link=anchor.dataset.link||anchor.getAttribute('href');if(link?.startsWith('#')){event.preventDefault();viewer.value?.querySelector('#'+CSS.escape(link.slice(1)))?.scrollIntoView({block:'start'});return};if(/^(skey|tactic-search):/i.test(link)&&!event.ctrlKey&&!event.metaKey){event.preventDefault();openLink(link)}}else if(image)window.open(image.dataset.original||image.src,'_blank','noopener')}
function openLink(value){if(openObjectTab)openObjectTab(value,props.project);else emit('open-link',value)}
function imageError(event){const image=event.target;if(image.tagName!=='IMG')return;const file=files.value.find(file=>file.webUrl===(image.dataset.original||image.getAttribute('src')));if(file&&file.previewUrl!==file.webUrl&&image.src!==new URL(file.previewUrl,location.href).href){image.dataset.original=file.webUrl;image.src=file.previewUrl}}
function openFile(file){window.open(file.webUrl,'_blank','noopener')}
function scrollHeading(id){viewer.value?.querySelector('#'+CSS.escape(id))?.scrollIntoView({block:'start'})}
function date(value){const stamp=messageDate(value);return Number.isNaN(stamp.getTime())?'':stamp.toLocaleString(appearance.language)}
function beforeUnload(event){checkpoint();if(saving.value||storageError.value&&dirty.value||organization.value){event.preventDefault();event.returnValue=''}}
function canLeave(){checkpoint();if(saving.value||organization.value||storageError.value&&dirty.value){error.value=t('Finish the current operation or save/discard order changes before leaving.');return false}return true}
watch(document,checkpoint,{deep:true})
watch(resourceKeys,()=>{references.value={};if(resourceKeys.value.length)loadReferences()})
watch(()=>[props.ticket,props.project,props.login],()=>{
  request++;historyRequest++;previewRequest++;clearTimeout(searchTimer);context=scope.value;clearPage();catalog.value=[];query.value='';organization.value=null;pendingFiles.value=[];stagedFiles.clear();loaded.value=false
  for(const id of Object.keys(drafts))delete drafts[id]
  try{const state=JSON.parse(localStorage.getItem(context+'.state')||'{}');navigationExpanded.value=state.navigationExpanded!==false;tocVisible.value=state.tocVisible!==false;collapsed.clear();for(const id of state.collapsed||[])collapsed.add(id);const saved=JSON.parse(localStorage.getItem(context)||'{}');for(const [id,entry]of Object.entries(saved))if(entry?.document&&typeof entry.document.title==='string'&&typeof entry.document.contentMarkdown==='string')drafts[id]=entry}catch{error.value=t('Local drafts could not be restored.')}
  if(props.active)reload()
},{immediate:true})
watch(()=>props.active,value=>{if(value&&!loaded.value)reload();else if(!value)checkpoint()})
watch(()=>[props.target,props.project],([value,project])=>{if(!value)return;try{const address=new URL(value);if((address.searchParams.get('project')||project)===project)select(address.searchParams.get('id')||address.searchParams.get('code'))}catch{fail(new Error(t('Invalid TACTIC link')))}},{immediate:true})
onMounted(()=>{observer=new ResizeObserver(entries=>{width.value=entries[0].contentRect.width});observer.observe(host.value);window.addEventListener('beforeunload',beforeUnload)})
onBeforeUnmount(()=>{checkpoint();request++;historyRequest++;previewRequest++;observer?.disconnect();clearTimeout(searchTimer);window.removeEventListener('beforeunload',beforeUnload)})
defineExpose({open:select,reload,canLeave})
</script>
<template>
    <div ref="host" class="knowledge-base" :class="{narrow,single}">
      <header class="knowledge-heading"><AppIcon name="book-open" /><h2>{{ t('Knowledge Base') }}</h2>
        <AppButton v-if="initialized&&!narrow" icon-only :icon="navigationExpanded?'previous':'next'" :label="navigationExpanded?'Hide article navigation':'Show article navigation'" @click="navigationExpanded=!navigationExpanded" />
        <template v-if="organization"><AppButton icon="save" label="Save order" highlighted :disabled="saving" @click="saveOrder" /><AppButton icon-only icon="undo" label="Discard order changes" :disabled="saving" @click="undoOrder" /></template>
        <template v-if="initialized&&canEdit"><AppButton icon-only icon="create-article" label="Create article" :disabled="saving||!!organization" @click="create('article')" /><AppButton icon-only icon="folder-plus" label="Create section" :disabled="saving||!!organization" @click="create('section')" /></template>
        <AppButton icon-only icon="refresh" label="Reload articles" :disabled="loading||saving||!!organization" @click="reload" />
      </header>
      <div v-if="error" class="knowledge-error" role="alert"><AppIcon name="exclamation-circle" /><span>{{ error }}</span><AppButton icon-only icon="close" label="Dismiss error" @click="error=''" /></div>
      <div v-if="!initialized" class="knowledge-empty"><AppIcon name="book-open" /><h3>{{ t('Knowledge Base is not initialized') }}</h3><p>{{ t('An administrator must initialize project articles and collaboration metadata.') }}</p><AppButton v-if="canInitialize" label="Initialize Knowledge Base" icon="plus" :disabled="saving||loading" @click="confirmation.showModal()" /></div>
      <div v-else class="knowledge-layout">
        <nav v-show="!single||navigationPage" class="knowledge-navigation" :aria-label="t('Articles')"><AppSearchField v-model="query" class="knowledge-search" label="Search sections and articles" :placeholder="t('Search sections and articles')" :disabled="saving||!!organization" @update:model-value="search" @search="reload" />
          <div class="knowledge-tree" role="tree"><div v-for="row in entries" :key="row.identity" class="knowledge-tree-row" :class="{selected:row.identity===selected,drop:dropTarget===row.identity,section:row.kind==='section'}" :style="{'--depth':row.depth}" role="treeitem" :aria-selected="row.identity===selected" :aria-expanded="row.hasChildren?row.expanded:undefined" :data-knowledge-entry="row.identity" :draggable="canEdit&&!editing&&!row.localDraft" @dragstart="dragging=row.identity" @dragover.prevent="dropTarget=row.identity" @dragleave="dropTarget=''" @drop="drop($event,row)" @dragend="dragging='';dropTarget=''">
            <span class="knowledge-disclosure"><AppButton v-if="row.hasChildren" icon-only :icon="row.expanded?'chevron-down':'next'" :label="row.expanded?'Collapse section':'Expand section'" @click="collapsed.has(row.identity)?collapsed.delete(row.identity):collapsed.add(row.identity)" /></span>
            <AppButton class="knowledge-page-link" :label="row.title" @click="select(row.identity)"><AppIcon :name="row.kind==='section'?(row.expanded?'folder-open':'folder'):'file'" /><span><strong>{{ row.title }}</strong><small v-if="row.kind==='section'?row.description:query&&row.excerpt">{{ row.kind==='section'?row.description:row.excerpt }}</small><small v-if="row.localDraft||row.draft" class="knowledge-draft">{{ t(row.localDraft?'Local draft':'Draft') }}</small></span></AppButton>
            <AppMenu v-if="canEdit&&!row.localDraft" class="knowledge-row-menu" label="Organize page" overlay :width="220"><AppMenuItem label="Move up" icon="arrow-up" :disabled="editing||saving" @click="reorder(row.identity,-1)" /><AppMenuItem label="Move down" icon="arrow-down" :disabled="editing||saving" @click="reorder(row.identity,1)" /><AppMenuItem label="Move to section" icon="folder" :disabled="editing||saving" @click="openMove(row.identity)" /></AppMenu>
          </div><p v-if="!entries.length&&!loading" class="knowledge-no-entries">{{ t(query?'No matching articles':'No articles yet') }}</p></div>
        </nav>
        <main v-show="!single||!navigationPage" class="knowledge-page" :class="{'article-narrow':articleNarrow}">
          <div v-if="loading" class="knowledge-loading" role="status">{{ t('Loading…') }}</div>
          <div v-else-if="!document" class="knowledge-empty"><AppIcon name="file" /><h3>{{ t('Choose an article') }}</h3><p>{{ t('Sections, full-text search, files, and object links stay together here.') }}</p></div>
          <template v-else-if="editing">
            <header class="knowledge-editor-heading"><AppButton v-if="single" icon-only icon="previous" label="Back to articles" @click="checkpoint();navigationPage=true" /><AppIcon :name="document.kind==='article'?'file':'folder'" /><h3>{{ t(document.kind==='article'?'Edit article':'Edit section') }}</h3><small v-if="creating&&document.kind==='article'">{{ t('Step {step} of 2',{step:step+1}) }}</small>
              <AppButton v-if="!creating&&document.kind==='article'" icon-only :icon="expandedMetadata?'chevron-up':'chevron-down'" :label="expandedMetadata?'Hide title and summary':'Show title and summary'" @click="expandedMetadata=!expandedMetadata" />
              <AppButton v-if="selection?.length&&document.kind==='article'" icon-only icon="link" label="Link selected objects to article" @click="linkSelection" />
              <AppButton label="Cancel" icon="close" :icon-only="pageWidth<1180" :disabled="saving" @click="discard" /><AppButton v-if="!creating" :label="document.kind==='article'?'Delete article':'Delete section'" icon="delete" destructive :icon-only="pageWidth<1180" :disabled="saving||!!organization" @click="openDeletion" />
              <AppButton v-if="document.kind==='article'&&(creating||document.draft)" label="Save as draft" icon="save" :icon-only="narrow" :disabled="saving" @click="save(true)" /><AppButton :label="creating||document.draft?'Publish':'Save'" icon="save" highlighted :icon-only="narrow" :disabled="saving||!dirty&&!document.draft" @click="save()" />
            </header>
            <div v-if="creating&&step===0" class="knowledge-parent"><AppIcon name="folder" /><span><small>{{ t('Parent section') }}</small>{{ parentTitle }}</span></div>
            <div v-if="document.kind==='section'||creating&&step===0||expandedMetadata&&!creating" class="knowledge-metadata-fields"><label>{{ t('Title') }}<AppTextField v-model="document.title" label="Title" placeholder="A short, recognizable title" :disabled="saving" /></label><label>{{ t('Summary') }}<AppTextArea v-model="document.description" label="Summary" placeholder="What this page is about" :disabled="saving" /></label><label v-if="document.kind==='section'">{{ t('Parent section') }}<AppSelect v-model="document.parentCode" :options="sectionOptions.filter(row=>row.value!==identity)" label="Parent section" /></label><AppButton v-if="creating&&document.kind==='article'" label="Continue to content" icon="next" :disabled="!document.title.trim()" @click="step=1;expandedMetadata=false;checkpoint()" /></div>
            <template v-if="document.kind==='article'&&(!creating||step===1)">
              <AppButton v-if="creating" class="knowledge-back-metadata" label="Back to title and summary" icon="previous" @click="step=0" />
              <div v-if="linkedObject" class="knowledge-linked-header"><AppButton v-if="linked.length>1" icon-only icon="previous" label="Previous linked object" @click="linkedIndex=(linkedIndex+linked.length-1)%linked.length" /><SKeyPreviewCard :preview="linkedObject" compact @open="openLink" /><AppButton v-if="linked.length>1" icon-only icon="next" label="Next linked object" @click="linkedIndex=(linkedIndex+1)%linked.length" /><AppButton icon-only icon="link-off" label="Unlink object" @click="unlink" /></div>
              <KnowledgeEditor ref="editor" v-model="document.contentMarkdown" :project="project" :attachments="files" :disabled="saving" @attachments="attachmentsVisible=!attachmentsVisible" @upload="addFiles">
                <template #attachments>
              <section v-if="attachmentsVisible" class="knowledge-attachment-library"><header><AppIcon name="attachments-editor" /><div><h4>{{ t('Attached files') }}</h4><p>{{ t('Files are uploaded and attached before you insert their permanent links into the article.') }}</p></div><AppButton icon-only label="Attach files" icon="attachments-editor" :disabled="saving" @click="fileInput.click()" /><AppButton icon-only icon="close" label="Hide attached files" @click="attachmentsVisible=false" /></header><div class="knowledge-staging" @dragover.prevent @drop.prevent="addFiles([...$event.dataTransfer.files])"><header><AppIcon name="attachments-editor" /><small>{{ t('Attachments') }}</small><AppButton icon-only icon="content-paste" label="Paste image" :disabled="saving||!clipboardAvailable" @click="pasteImage" /><AppButton v-if="pendingFiles.length" icon-only icon="close" label="Clear staged files" :disabled="saving" @click="pendingFiles=[]" /></header><AppButton class="knowledge-stage-empty" label="Drop files here or attach them from disk" :disabled="saving" @click="fileInput.click()"><AppIcon name="attachments-editor" /><span>{{ t('Drop files here or attach them from disk') }}</span></AppButton></div>
                <div v-for="(entry,index) in pendingFiles" :key="index" v-show="entry.status!=='done'" class="knowledge-pending"><span>{{ entry.file.name }} · {{ t(entry.status==='failed'?'Failed':entry.status==='uploading'?'Uploading':'Ready') }}</span><small v-if="entry.error" class="error">{{ entry.error }}</small><AppButton v-if="entry.status==='failed'" icon-only icon="refresh" label="Retry" :disabled="saving" @click="uploadPending" /><AppButton icon-only icon="close" label="Remove staged file" :disabled="saving" @click="pendingFiles.splice(index,1)" /></div>
                <div v-for="file in files" :key="file.token" class="knowledge-library-file"><AttachmentCard compact :activation-icon="file.isImage?'image':'link'" :activation-label="file.isImage?'Insert image':'Insert link'" :title="file.title" :extension="file.extension" :preview-url="file.previewUrl" :size-text="String(file.size||0)+' B'" @activated="editor.insertAttachment(file)" /><AppButton icon-only :icon="copying===file.token?'check':'copy'" :label="copying===file.token?'Copied':'Copy web link'" @click="copy(file.webUrl,file.token)" /><AppButton icon-only icon="delete" label="Delete file" :disabled="saving" @click="confirmFile(file)" /></div><p v-if="!files.length">{{ t('No files uploaded to this article yet.') }}</p>
              </section>
                </template>
              </KnowledgeEditor>
            </template>
          </template>
          <template v-else>
            <header class="knowledge-viewer-heading"><AppButton v-if="single" icon-only icon="previous" label="Back to articles" @click="navigationPage=true" /><div class="knowledge-kind-tile"><AppIcon :name="shown.kind==='section'?'folder-open':'file'" /></div><div class="knowledge-title"><h3>{{ shown.title }}</h3><small>{{ shown.description }}<span v-if="shown.kind==='article'"><span v-if="shown.description"> • </span><AppIcon name="schedule" />{{ t('{minutes} min read',{minutes}) }}</span></small></div><AppButton icon-only icon="copy" label="Copy search key" @click="copy(searchKey)" /><AppMenu v-if="shown.kind==='article'" ref="historyDialog" icon="history" label="Change history" overlay :width="390" :close-on-select="false" class="knowledge-history-menu" @toggle="history"><h4><AppIcon name="history" />{{ t('Change history') }}</h4><AppButton v-for="row in histories" :key="row.revisionId" icon="history" :label="row.title" @click="previewHistory(row.revisionId)"><span><strong>{{ row.title }}</strong><small>{{ row.actor }} · {{ date(row.timestamp) }}</small><small>{{ row.changedFields.join(', ') }}</small></span></AppButton><p v-if="!histories.length">{{ t('Loading…') }}</p></AppMenu><AppButton v-if="toc.length&&shown.kind==='article'" icon-only icon="list-ul" :label="tocVisible?'Hide table of contents':'Show table of contents'" :tonal="tocVisible" @click="tocVisible=!tocVisible" /><AppButton v-if="files.length||resourceKeys.length" icon-only icon="attachments-editor" :label="resourcesVisible?'Hide linked objects and attached files':'Show linked objects and attached files'" :tonal="resourcesVisible" @click="resourcesVisible=!resourcesVisible" /><template v-if="canEdit&&!historyPreview"><AppButton :label="shown.kind==='article'?'Delete article':'Delete section'" icon="delete" destructive :icon-only="articleNarrow" :disabled="saving||!!organization" @click="openDeletion" /><AppButton label="Edit" icon="edit" tonal :icon-only="articleNarrow" @click="beginEdit" /></template></header>
            <div v-if="historyPreview" class="knowledge-history-banner"><span>{{ t('Previewing an earlier revision') }} · {{ historyPreview.actor }} · {{ date(historyPreview.timestamp) }}</span><AppButton label="Return to current article" icon="close" @click="historyPreview=null" /></div>
            <div v-if="shown.kind==='section'" class="knowledge-section-contents"><AppButton v-for="row in sectionEntries" :key="row.identity" :style="{paddingLeft:(7+(row.level-1)*18)+'px'}" :label="row.title" @click="select(row.identity)"><AppIcon :name="row.kind==='section'?'folder-open':'file'" /><span>{{ row.title }}<small v-if="row.kind==='section'">{{ t('Section') }}</small></span></AppButton><p v-if="!sectionEntries.length">{{ t('This section has no pages yet.') }}</p></div>
            <div v-else class="knowledge-reading" :class="{'side-outline':!articleNarrow&&tocVisible&&toc.length}"><div class="knowledge-reading-scroll">
              <div v-if="linkedObject&&!historyPreview" class="knowledge-linked-header"><AppButton v-if="linked.length>1" icon-only icon="previous" label="Previous linked object" @click="linkedIndex=(linkedIndex+linked.length-1)%linked.length" /><SKeyPreviewCard :preview="linkedObject" compact @open="openLink" /><AppButton v-if="linked.length>1" icon-only icon="next" label="Next linked object" @click="linkedIndex=(linkedIndex+1)%linked.length" /></div>
              <aside v-if="articleNarrow&&tocVisible&&toc.length" class="knowledge-outline"><h4><AppIcon name="list-ul" />{{ t('On this page') }}</h4><AppButton v-for="heading in toc" :key="heading.id" :label="heading.title" :style="{paddingLeft:(7+(heading.level-1)*11)+'px'}" @click="scrollHeading(heading.id)">{{ heading.title }}</AppButton></aside>
              <article ref="viewer" class="knowledge-document" v-html="html" @click="activate" @error.capture="imageError" />
              <section v-if="resourcesVisible&&!historyPreview" class="knowledge-resources"><h4>{{ t('Linked objects and files') }}</h4><SKeyPreviewCard v-for="key in resourceKeys" :key="key" :preview="references[key]||{searchKey:key,status:'loading'}" @open="openLink" @retry="loadReferences" @copy="copy" /><AttachmentCard v-for="file in files" :key="file.token" :title="file.title" :extension="file.extension" :preview-url="file.previewUrl" :size-text="String(file.size||0)+' B'" @activated="openFile(file)" /></section>
              <footer class="knowledge-article-metadata"><span>{{ t('Author') }}: {{ (historyPreview?.articleMetadata||metadata).author }}</span><span>{{ t('Created') }}: {{ date((historyPreview?.articleMetadata||metadata).createdAt) }}</span><span>{{ t('Updated') }}: {{ date((historyPreview?.articleMetadata||metadata).updatedAt) }}</span></footer>
            </div><aside v-if="!articleNarrow&&tocVisible&&toc.length" class="knowledge-outline"><h4><AppIcon name="list-ul" />{{ t('On this page') }}</h4><AppButton v-for="heading in toc" :key="heading.id" :label="heading.title" :style="{paddingLeft:(7+(heading.level-1)*11)+'px'}" @click="scrollHeading(heading.id)">{{ heading.title }}</AppButton></aside></div>
          </template>
        </main>
      </div>
      <input ref="fileInput" type="file" multiple hidden @change="addFiles([...$event.target.files]);$event.target.value=''">
      <dialog ref="confirmation" class="record-dialog knowledge-initialization" :aria-label="t('Initialize Knowledge Base')"><header><h2>{{ t('Initialize Knowledge Base') }}</h2><AppButton icon-only icon="close" label="Close" @click="confirmation.close()" /></header><p>{{ t('This creates the project article Search Type and missing content columns, and adds metadata to Messages and Message Log. Existing data is preserved.') }}</p><ul><li>{{ project }}/th_knowledge_article: kind, parent_code, content, content_text, sort_order, updated_by, linked_skeys</li><li><code>{{ 'sthpw/message: metadata' }}</code></li><li><code>{{ 'sthpw/message_log: metadata' }}</code></li></ul><footer><AppButton label="Cancel" @click="confirmation.close()" /><AppButton label="Initialize" highlighted @click="initialize" /></footer></dialog>
      <dialog ref="deletion" class="record-dialog knowledge-deletion" :aria-label="t(deletingFile?'Delete article file?':'Delete record')"><header><h2>{{ t(deletingFile?'Delete article file?':'Delete record') }}</h2><AppButton icon-only icon="close" label="Close" :disabled="saving" @click="deletion.close()" /></header><template v-if="deletingFile"><p>{{ deletingFile.title }}</p><p>{{ t('The attachment snapshot will be retired. Existing article links are retained.') }}</p></template><template v-else><p>{{ document?.title }}</p><p>{{ t('Review dependencies before deleting this page. Linked project objects are preserved.') }}</p><AppCheckbox v-for="group in deleteGroups" :key="group.search_type" :model-value="deleteTypes.includes(group.search_type)" :label="group.title+' · '+group.count" @update:model-value="value=>{deleteTypes=value?[...deleteTypes,group.search_type]:deleteTypes.filter(kind=>kind!==group.search_type)}" /></template><footer><AppButton label="Cancel" :disabled="saving" @click="deletion.close()" /><AppButton label="Delete" destructive :disabled="saving||loading" @click="deletingFile?removeFile():deletePage()" /></footer></dialog>
      <dialog ref="moveDialog" class="record-dialog" :aria-label="t('Move to section')"><header><h2>{{ t('Move to section') }}</h2><AppButton icon-only icon="close" label="Close" @click="moveDialog.close()" /></header><AppSelect v-model="moveParent" :options="sectionOptions.filter(row=>row.value!==moveIdentity)" label="Parent section" /><footer><AppButton label="Cancel" @click="moveDialog.close()" /><AppButton label="Move" @click="applyMove" /></footer></dialog>
    </div>
</template>
<style>
.knowledge-base { display:flex; flex-direction:column; gap:7px; height:100%; min-width:0; min-height:0; padding:8px; color:var(--on-surface); background:var(--page); }
.knowledge-heading { display:flex; align-items:center; gap:7px; flex:none; }
.knowledge-heading > .app-icon { font-size:20px; color:var(--primary); }
.knowledge-heading h2 { flex:1; margin:0; font-size:var(--text-title); font-weight:600; }
.knowledge-base .knowledge-heading .icon-button,.knowledge-base .knowledge-editor-heading .icon-button,.knowledge-base .knowledge-viewer-heading .icon-button { width:30px; height:30px; min-width:30px; min-height:30px; flex-shrink:0; }
.knowledge-base .icon-button .app-icon { width:16px; height:16px; font-size:16px; }
.knowledge-layout { display:flex; flex:1; min-width:0; min-height:0; gap:17px; }
.knowledge-navigation { flex:0 0 min(310px,34%); position:relative; padding:8px; display:flex; flex-direction:column; gap:7px; min-width:0; min-height:0; }
.knowledge-navigation::after { content:''; position:absolute; top:0; bottom:0; right:-9px; width:1px; background:var(--outline-variant); }
.knowledge-base.single .knowledge-navigation { flex:1; }
.knowledge-base.single .knowledge-navigation::after { display:none; }
.knowledge-search { display:flex; align-items:center; flex:none; background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:var(--item-radius); padding-left:10px; height:var(--control-height); }
.knowledge-search > .app-icon { width:18px; height:18px; font-size:18px; color:var(--muted); }
.knowledge-search input { width:100%; background:transparent; border:0; height:100%; }
.knowledge-tree { flex:1; overflow:auto; padding-right:12px; }
.knowledge-tree-row { display:flex; align-items:flex-start; padding:4px 6px 4px calc(2px + var(--depth)*18px); gap:4px; border-radius:var(--item-radius); margin-bottom:1px; min-height:32px; }
.knowledge-tree-row.selected { background:var(--surface-high); }
.knowledge-tree-row:hover { background:var(--hover); }
.knowledge-tree-row.drop { outline:1px solid var(--primary); }
.knowledge-disclosure { width:24px; height:24px; flex:none; }
.knowledge-disclosure .app-button { width:24px!important; height:24px!important; min-width:24px!important; min-height:24px!important; }
.knowledge-page-link.app-button { justify-content:flex-start; flex:1; padding:0; min-width:0; min-height:24px; height:auto; gap:4px; border:0; background:transparent; text-align:left; border-radius:0; align-items:flex-start; }
.knowledge-page-link > .app-icon { flex:none; width:17px; height:17px; font-size:17px; margin-top:4px; color:var(--primary); }
.knowledge-page-link > span:not(.app-icon) { display:flex; flex-direction:column; min-width:0; gap:2px; }
.knowledge-page-link strong { font-size:var(--text-body); font-weight:400; line-height:20px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.knowledge-tree-row:has(.knowledge-page-link .app-icon[data-icon="folder"]) strong { font-weight:600; }
.knowledge-page-link small { font-size:var(--text-caption); color:var(--muted); line-height:16px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.knowledge-draft { color:var(--primary)!important; }
.knowledge-row-menu { opacity:0; flex:none; }
.knowledge-row-menu > summary { width:24px; height:24px; min-width:24px; min-height:24px; }
.knowledge-tree-row:hover .knowledge-row-menu,.knowledge-tree-row:focus-within .knowledge-row-menu { opacity:1; }
.knowledge-page { display:flex; flex-direction:column; flex:1; min-height:0; min-width:0; gap:7px; }
.knowledge-empty { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:8px; padding:24px; color:var(--muted); }
.knowledge-empty > .app-icon { font-size:28px; }
.knowledge-empty h3,.knowledge-empty p { margin:0; }
.knowledge-error { display:flex; align-items:center; gap:7px; padding:7px; border:1px solid var(--error); border-radius:var(--item-radius); background:color-mix(in srgb,var(--error) 14%,var(--surface)); font-size:var(--text-caption); }
.knowledge-error > span { flex:1; }
.knowledge-viewer-heading { display:flex; align-items:center; gap:9px; padding:10px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface); flex:none; }
.knowledge-kind-tile { width:40px; height:40px; border-radius:var(--item-radius); border:1px solid var(--outline-variant); background:var(--surface-high); display:grid; place-items:center; flex:none; }
.knowledge-kind-tile .app-icon { font-size:20px; color:var(--primary); }
.knowledge-title { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }
.knowledge-title h3 { font-size:var(--text-title); font-weight:600; margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.knowledge-title small { display:flex; align-items:center; gap:4px; font-size:var(--text-caption); color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.knowledge-editor-heading { display:flex; align-items:center; gap:7px; flex:none; min-width:0; }
.knowledge-editor-heading h3 { flex:1; font-size:var(--text-title); margin:0; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.knowledge-editor-heading > .app-icon { color:var(--primary); font-size:20px; flex:none; }
.knowledge-editor-heading small { color:var(--muted); font-size:var(--text-caption); }
.knowledge-parent { display:flex; gap:8px; padding:8px; border-radius:var(--item-radius); background:var(--surface); border:1px solid var(--outline-variant); }
.knowledge-parent > span { display:flex; flex-direction:column; gap:1px; }
.knowledge-parent small { font-size:var(--text-caption); color:var(--muted); }
.knowledge-metadata-fields { display:flex; flex-direction:column; gap:9px; overflow:auto; min-height:0; padding:8px; }
.knowledge-metadata-fields label { display:flex; flex-direction:column; gap:7px; font-size:var(--text-label); }
.knowledge-metadata-fields textarea { min-height:74px; }
.knowledge-metadata-fields > button { align-self:flex-end; }
.knowledge-back-metadata { align-self:flex-start; }
.knowledge-reading { display:flex; flex:1; min-height:0; min-width:0; gap:10px; }
.knowledge-reading-scroll { flex:1; min-width:0; overflow:auto; display:flex; flex-direction:column; gap:0; }
.knowledge-document { font-family:var(--font-family); font-size:var(--text-body); line-height:1.45; font-weight:400; overflow-wrap:anywhere; }
.knowledge-document p,.knowledge-document div { margin:0 0 8px; }
.knowledge-document h1 { font-size:var(--text-heading); }
.knowledge-document h2 { font-size:var(--text-title); }
.knowledge-document h3 { font-size:var(--text-body-large); }
.knowledge-document h4,.knowledge-document h5,.knowledge-document h6 { font-size:var(--text-body); }
.knowledge-document h1,.knowledge-document h2,.knowledge-document h3,.knowledge-document h4,.knowledge-document h5,.knowledge-document h6 { font-weight:600; margin:12px 0 8px; line-height:1.25; }
.knowledge-document > :first-child { margin-top:0; }
.knowledge-document img { max-width:100%; object-fit:contain; height:auto; cursor:pointer; }
.knowledge-document img[data-fit="content"] { width:100%; }
.knowledge-document a { color:var(--primary); }
.knowledge-document ul,.knowledge-document ol { padding-left:24px; margin:0 0 8px; }
.knowledge-document li p { margin:0; }
.knowledge-document blockquote { position:relative; margin:8px 0; padding:12px 20px; background:var(--surface); border-left:3px solid var(--primary); border-radius:var(--item-radius); }
.knowledge-document blockquote::before { content:'“'; color:var(--primary); font-size:28px; position:absolute; left:4px; top:0; }
.knowledge-document pre { position:relative; font-family:var(--font-mono); font-size:var(--text-body); border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface); padding:28px 12px 12px; white-space:pre-wrap; overflow:auto; }
.knowledge-document pre::before { content:attr(data-language); position:absolute; top:6px; left:12px; color:var(--muted); font-size:var(--text-caption); }
.knowledge-document table { border-collapse:collapse; width:100%; table-layout:fixed; }
.knowledge-document td,.knowledge-document th { padding:6px; border:1px solid var(--outline-variant); }
.knowledge-document code { font-family:var(--font-mono); }
.knowledge-document :not(pre)>code { background:var(--surface-high); padding:1px 4px; border-radius:4px; }
.knowledge-outline { width:220px; flex:none; max-height:260px; overflow:auto; padding:8px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface); }
.knowledge-outline h4 { display:flex; align-items:center; gap:6px; font-size:var(--text-label); margin:0 0 6px; font-weight:600; }
.knowledge-outline h4 .app-icon { font-size:15px; color:var(--primary); }
.knowledge-outline .app-button { display:flex; width:100%; justify-content:flex-start; height:29px; min-height:29px; padding:0 6px; border:0; background:transparent; font-size:var(--text-body); font-weight:400; text-align:left; }
.knowledge-base.narrow .knowledge-outline { width:100%; max-height:210px; }
.knowledge-linked-header { display:flex; align-items:center; min-width:0; gap:6px; flex:none; }
.knowledge-linked-header .skey-preview-card { flex:1; }
.knowledge-resources { display:flex; flex-direction:column; gap:7px; }
.knowledge-resources h4 { margin:0; font-size:var(--text-label); color:var(--muted); }
.knowledge-article-metadata { display:flex; flex-direction:column; gap:4px; padding-top:8px; border-top:1px solid var(--outline-variant); font-size:var(--text-caption); color:var(--muted); }
.knowledge-section-contents { display:flex; flex-direction:column; gap:1px; overflow:auto; }
.knowledge-section-contents .app-button { justify-content:flex-start; text-align:left; border:0; border-radius:var(--item-radius); background:transparent; gap:7px; height:36px; min-height:36px; font-weight:400; }
.knowledge-section-contents small { color:var(--muted); font-size:var(--text-caption); margin-left:8px; }
.knowledge-attachment-library { max-height:70%; overflow:auto; padding:10px; background:var(--surface); border:1px solid var(--outline-variant); border-radius:var(--surface-radius); flex-shrink:0; }
.knowledge-attachment-library > header { display:flex; align-items:center; gap:7px; }
.knowledge-attachment-library h4 { margin:0; font-size:var(--text-body-large); font-weight:600; }
.knowledge-attachment-library p { color:var(--muted); font-size:var(--text-caption); margin:1px 0 0; }
.knowledge-library-file { display:flex; align-items:center; gap:5px; margin-top:8px; }
.knowledge-library-file .attachment-card { flex:1; }
.knowledge-staging { display:flex; flex-direction:column; margin-top:8px; padding:10px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface-high); }
.knowledge-staging > span { flex:1; font-size:var(--text-caption); color:var(--muted); }
.knowledge-pending { display:flex; align-items:center; gap:7px; flex-wrap:wrap; font-size:var(--text-caption); }
.knowledge-history .app-button { display:flex; width:100%; border:0; border-radius:var(--item-radius); background:transparent; padding:8px; text-align:left; height:auto; }
.knowledge-history .app-button > span { display:flex; flex-direction:column; gap:3px; }
.knowledge-history small { color:var(--muted); font-size:var(--text-caption); }
.knowledge-history-banner { display:flex; align-items:center; gap:8px; padding:7px; background:var(--surface); border:1px solid var(--outline-variant); border-radius:var(--item-radius); flex:none; }
.knowledge-history-banner > span { flex:1; font-size:var(--text-caption); }
.knowledge-no-entries { color:var(--muted); font-size:var(--text-body); }
.knowledge-initialization,.knowledge-deletion { width:min(580px,calc(100vw - 24px)); }
.knowledge-loading { color:var(--muted); }
@media(pointer:coarse) { .knowledge-row-menu { opacity:1; } }
.knowledge-history-menu .account-panel { max-height:440px; padding:4px; }
.knowledge-history-menu h4 { display:flex; align-items:center; gap:7px; margin:0; height:36px; padding:0 9px; font-size:var(--text-body); font-weight:600; }
.knowledge-history-menu h4 .app-icon { font-size:18px; color:var(--primary); }
.knowledge-history-menu .app-button { width:100%; height:62px; border:0; background:transparent; justify-content:flex-start; text-align:left; padding:7px 9px; }
.knowledge-history-menu .app-button>span { display:flex; flex-direction:column; min-width:0; gap:3px; }
.knowledge-history-menu .app-button strong { font-size:var(--text-body); font-weight:600; }
.knowledge-history-menu .app-button small { color:var(--muted); font-size:var(--text-caption); overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.knowledge-document { font-size:12.333px; font-weight:400; line-height:1.3; }
.knowledge-document h1 { font-size:24px; }
.knowledge-document h2 { font-size:18px; }
.knowledge-document h3 { font-size:14px; }
.knowledge-document p { margin:0 0 8px; }
.knowledge-document h1,.knowledge-document h2,.knowledge-document h3 { margin:0 0 7px; }
.knowledge-tree-row strong { font-weight:400; }
.knowledge-tree-row.section strong { font-weight:600; }
.knowledge-tree-row.section .knowledge-entry>.app-icon { color:var(--tertiary); }
.knowledge-article-metadata { flex-direction:row; flex-wrap:wrap; column-gap:16px; color:var(--muted); }
.knowledge-outline { max-height:none; }
.knowledge-base.narrow .knowledge-outline { max-height:210px; }
.knowledge-editor-heading .app-button.icon-button { background:var(--surface-high); border-radius:50%; }
.knowledge-editor-heading .app-button.icon-button.danger { border:1px solid var(--error); }
.knowledge-page-link { padding-left:0 !important; }
.knowledge-tree-row .knowledge-page-link>.app-icon { width:17px; height:17px; font-size:17px; }
.knowledge-tree-row.section .knowledge-page-link>.app-icon { color:var(--tertiary); }
.knowledge-page.article-narrow .knowledge-outline { width:100%; max-height:210px; }
.knowledge-title small .app-icon { width:13px; height:13px; font-size:13px; }
.knowledge-viewer-heading .app-button.danger { border:1px solid var(--error); background:var(--surface-high); }
.knowledge-attachment-library>header>div { flex:1; min-width:0; }
.knowledge-attachment-library>header>.app-icon { color:var(--primary); font-size:18px; }
.knowledge-attachment-library .icon-button { width:30px; height:30px; min-width:30px; min-height:30px; }
.knowledge-staging>header { display:flex; align-items:center; gap:7px; }
.knowledge-staging>header>small { flex:1; color:var(--muted); }
.knowledge-staging>header>.app-icon { color:var(--primary); font-size:18px; }
.knowledge-stage-empty.app-button { display:flex; flex-direction:column; justify-content:center; gap:8px; border:0; background:transparent; height:96px; min-height:96px; font-size:var(--text-body); font-weight:400; color:var(--muted); }
.knowledge-stage-empty>.app-icon { font-size:32px; }
</style>
