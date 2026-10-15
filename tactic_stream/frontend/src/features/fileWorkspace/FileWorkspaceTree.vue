<script setup>
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { onBeforeUnmount, ref } from 'vue'
import { t } from '../../i18n.js'
defineProps({nodes:Array,busy:Boolean,selected:String,label:String,selectedIds:Array,dropTarget:String,canDrop:Boolean,dropReason:Function,dropCaption:Function,canDrag:{type:Boolean,default:true}})
const emit=defineEmits(['expand','select','menu','background','drag','drop','dragover','dragend'])
const branch=node=>['depot','stream','workspace','directory','change'].includes(node.kind)
const title=node=>node.kind==='more' ? t('Load more') : node.kind==='change'
  ? t('Changelist #{number}',{number:node.number})+' · '+(node.description || t('No description')) : node.name || node.path
const icon=node=>({workspace:'desktop',depot:'database',stream:'workflow',directory:node.expanded?'folder-open':'folder',change:'archive',more:'add',file:'file'})[node.kind]
const state=node=>({pending:'Pending',submitted:'Submitted',shelved:'Shelved',reverted:'Reverted'})[node.state]
const counts=node=>node.file_actions?(node.file_actions.checkout || 0)+' '+t('waiting')+' / '+Object.entries(node.file_actions).filter(([action])=>action!=='checkout').reduce((sum,[,count])=>sum+count,0)+' '+t('staged'):t('Counts not indexed')
const invalid=ref('')
let hoverTimer,frame,hoverCode=''
function endDrag(){clearTimeout(hoverTimer);cancelAnimationFrame(frame);hoverCode='';invalid.value=''}
function dragOver(event,node){
  emit('dragover',event,node)
  if(!event.defaultPrevented){invalid.value=node.id;return}
  invalid.value=''
  if(hoverCode!==node.id){clearTimeout(hoverTimer);hoverCode=node.id;if(branch(node)&&!node.expanded)hoverTimer=setTimeout(()=>emit('expand',node),400)}
  const tree=event.currentTarget.closest('.file-workspace-branches'),bounds=tree.getBoundingClientRect(),direction=event.clientY<bounds.top+28?-1:event.clientY>bounds.bottom-28?1:0
  cancelAnimationFrame(frame)
  const scroll=()=>{if(direction){tree.scrollTop+=direction*8;frame=requestAnimationFrame(scroll)}}
  scroll()
}
onBeforeUnmount(endDrag)
function key(event,node){
  if(event.key==='ArrowRight' && branch(node) && !node.expanded){event.preventDefault();emit('expand',node)}
  else if(event.key==='ArrowLeft' && branch(node) && node.expanded){event.preventDefault();emit('expand',node)}
  else if(['ArrowUp','ArrowDown'].includes(event.key)){
    const rows=[...event.currentTarget.parentElement.querySelectorAll('.file-tree-select')],index=rows.indexOf(event.currentTarget.querySelector('.file-tree-select'))
    rows[index+(event.key==='ArrowUp'?-1:1)]?.focus();event.preventDefault()
  }
}
</script>
<template>
  <div class="file-workspace-branches" role="tree" :aria-label="t(label)" @contextmenu.prevent="emit('background',$event)">
    <div v-for="node in nodes" :key="node.id" class="file-tree-row" :class="{selected:selectedIds?.includes(node.id) || selected===node.id,change:node.kind==='change',drop:dropTarget===node.code,invalid:invalid===node.id}" role="treeitem"
      :aria-level="node.depth+1" :aria-expanded="branch(node)?!!node.expanded:undefined" :aria-selected="selectedIds?.includes(node.id) || selected===node.id" @keydown="key($event,node)"
      :style="{'--depth':node.depth}" :data-node="node.id" :title="invalid===node.id && dropReason ? dropReason(node) : dropTarget===node.code && dropCaption ? dropCaption(node) : undefined" :draggable="canDrag && !busy && ['file','change','directory','stream','workspace'].includes(node.kind)"
      @contextmenu.prevent.stop="emit('menu',$event,node)" @dragstart.stop="emit('drag',$event,node)"
      @dragover="canDrop && dragOver($event,node)" @dragleave="endDrag" @dragend="endDrag();emit('dragend')" @drop.stop="endDrag();canDrop && emit('drop',$event,node)">
      <AppButton v-if="branch(node)" icon-only :icon="node.expanded?'chevron-down':'next'" :aria-label="t(node.expanded?'Collapse {name}':'Expand {name}',{name:title(node)})" :disabled="busy" @click="emit('expand',node)" />
      <span v-else class="file-tree-indent"></span>
      <slot v-if="node.kind==='file' && $slots.file" name="file" :node="node"></slot>
      <AppButton v-else class="file-tree-select" :aria-label="title(node)" :title="title(node)" :disabled="busy" @click="emit('select',node,$event)">
        <AppIcon :name="icon(node)" :class="node.kind==='change'?'change-status-'+node.state:''" />
        <span class="file-tree-caption"><span>{{ title(node) }}</span><small v-if="node.kind==='change'" :title="node.owner+' · '+node.workspace+' · '+node.stream">{{ t(state(node)) }} · {{ node.owner }} · {{ node.workspace }} · {{ node.stream }} · {{ node.opened_files || 0 }} {{ t('files') }} · {{ counts(node) }} · {{ node.conflict_files || 0 }} {{ t('conflicts') }} · {{ ((node.opened_bytes || 0)/1048576).toFixed(1) }} MB</small></span>
        <AppIcon v-if="node.kind==='change'" :name="node.state==='submitted'?'check':node.state==='shelved'?'archive':node.state==='reverted'?'undo':'clock'" />
      </AppButton>
    </div>
    <p v-if="!nodes?.length" class="file-workspace-empty muted">{{ t('Nothing to display') }}</p>
  </div>
</template>
<style scoped>
.file-workspace-branches{overflow:auto;scrollbar-gutter:stable;min-height:0;flex:1;padding-right:4px}
.file-tree-row{display:flex;align-items:center;min-width:0;padding-left:calc(var(--depth)*14px);border-radius:var(--item-radius)}
.file-tree-row.drop{outline:2px solid var(--primary)}
.file-tree-row.invalid{outline:2px solid var(--error)}
.change-status-pending{color:var(--yellow)}
.change-status-shelved{color:var(--violet)}
.change-status-submitted{color:var(--success)}
.file-tree-row.selected{background:var(--selected)}
.file-tree-row>.icon-button,.file-tree-indent{width:24px;min-width:24px;height:28px;flex:none}
.file-tree-select{display:flex;justify-content:flex-start;gap:6px;min-height:30px;height:auto;min-width:0;flex:1;padding:3px 4px;border:0;border-radius:var(--item-radius);text-align:left;background:transparent}
.file-tree-select>.app-icon{flex:none}
.file-tree-caption{display:flex;flex-direction:column;flex:1;min-width:0}
.file-tree-caption>span,.file-tree-caption>small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.file-tree-caption>small{color:var(--muted);font-weight:400}
.file-tree-row.change .file-tree-select{height:42px;min-height:42px}
</style>
