<script setup>
import { computed, inject, Fragment, reactive, h } from 'vue'
import { t } from '../../i18n.js'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import { mobile } from '../../mobile.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import MiddleElide from '../../controls/MiddleElide.vue'
import { prettySize } from '../checkin/files.js'
import { timestampLabel, timestampFullLabel } from '../activity/activity.js'
import { bindingValue, layoutUrl, layoutElements } from './itemLayout.js'

const props = defineProps({ layout: Object, node: Object, parent: {type:String,default:''}, only: String, readOnly: Boolean, editing: Boolean, selectedElement: String, presentation: {type:Object,default:()=>({})} })
const emit = defineEmits(['action', 'completion', 'element', 'controls'])
const openObjectTab = inject('openObjectTab', null)
// Fragment needs an array of children, rather than a dynamic component's slots object.
const LayoutContainer=(props,{attrs,slots})=>h(props.tag,attrs,slots.default?.())
LayoutContainer.props=['tag']
const elements = computed(() => layoutElements(props.layout, props.node, props.parent).filter(item => (!props.only || item.name === props.only) && visible(item)))
const presentationState=props.presentation.state || reactive({titleActionsFit:true})
const childPresentation=computed(()=>({...props.presentation,state:presentationState}))
const container = computed(() => props.layout.elements.find(item => item.name === props.parent))
const nativeFlow=computed(()=>(props.parent ? container.value?.flow : props.layout.flow)==='contents')
const roleClasses={preview:'result-preview',copy:'result-item-copy','title-line':'result-title-line','title-actions':'result-title-actions',description:'result-description',metadata:'result-metadata',actions:'result-item-actions','hover-actions':'result-hover-actions',communication:'result-communication','task-button':'result-task-button','note-button':'result-note-button','mobile-actions':'result-mobile-actions','file-offline':'result-file-offline'}
const tracks = computed(() => props.parent ? `repeat(${container.value?.columns || 12}, minmax(0, 1fr))` : props.layout.tracks?.replace(/\b1fr\b/g, 'minmax(0, 1fr)') || `repeat(${props.layout.columns}, minmax(0, 1fr))`)
const mobileTracks = computed(() => tracks.value.replace(/(\d+)px/g, 'min(48px, $1px)'))
const title = computed(() => props.node.kind==='snapshot' && props.node.snapshot_display ? (props.node.snapshot_display.multiple ? t('Multiple files | {count}',{count:props.node.snapshot_display.multiple}) : props.node.snapshot_display.title) : props.node.title || props.node.record?.name || props.node.record?.title || props.node.record?.code || String(props.node.record?.id || ''))
const process = computed(() => props.node.branch?.kind === 'process')
const snapshot = computed(() => props.node.snapshot_display || {})

const subtitle=computed(()=>props.node.subtitle || props.node.record?.description || (props.node.kind==='snapshot'?t('No description'):''))
const initials=computed(()=>{
  const text=title.value[0]?.toUpperCase()+title.value.slice(1)
  let acronym=[...text].filter(char=>/[\p{Lu}]/u.test(char)).slice(0,2).join('')
  if(acronym.length<2)acronym+=text.slice(1,2)
  return acronym.toUpperCase() || '?'
})
function visible(item){
  const conditions={desktop:!mobile.value,mobile:mobile.value,tree:!!props.presentation.tree,'not-tree':!props.presentation.tree,object:props.node.kind==='object','object-or-process':props.node.kind==='object'||process.value,'not-branch':props.node.kind!=='branch',description:props.node.kind!=='branch'&&props.node.kind!=='snapshot'&&!!subtitle.value,snapshot:props.node.kind==='snapshot',branch:props.node.kind==='branch',relation:props.node.branch?.kind==='relation','mobile-upload':props.node.kind==='object'||process.value||props.presentation.back&&props.node.kind==='snapshot'}
  if(!(item.when||[]).every(condition=>conditions[condition]))return false
  if(item.kind==='button')return props.editing || href(item) || available(item.options.action)
  if(item.kind==='knowledge')return !!props.node.knowledge?.length
  if(item.kind==='snapshot-size')return snapshot.value.size!=null
  if(item.kind==='file-offline')return !!title.value&&!snapshot.value.exists
  return true
}
function tag(item){
  if(nativeFlow.value && ['button','knowledge','relations','snapshot-details','item-menu','snapshot-size'].includes(item.kind))return Fragment
  return item.kind==='title'&&props.presentation.back&&item.tag==='strong'?'h2':item.tag || 'div'
}
function classes(item){return [item.role==='preview' ? undefined : roleClasses[item.role],{'result-branch-summary muted':item.kind==='branch-summary',muted:item.kind==='snapshot-summary','result-branch-icon':item.role==='preview'&&props.node.kind==='branch','result-preview':item.role==='preview'&&props.node.kind!=='branch','actions-fit':item.role==='title-actions'&&presentationState.titleActionsFit,'result-communication-empty':item.role==='communication'&&process.value&&!props.node.task_count&&!props.node.note_count}]}
function fitTitleActions(event){
  if(mobile.value || !props.presentation.tree || props.node.kind!=='object')return
  const line=event.currentTarget,count=line.querySelectorAll('.result-title-actions button').length
  const text=line.querySelector('strong')
  if(text)presentationState.titleActionsFit=text.scrollWidth+8+count*28+Math.max(0,count-1)*5<=line.parentElement.clientWidth
}
function previewSource(item){
  return item.role==='preview'&&mobile.value&&props.node.kind==='object' ? props.node.preview?.files?.find(file=>file.type==='web'&&file.href)?.href || props.node.preview?.image : value(item)
}

function value(item) { const data = item.options.bind ? bindingValue(item.options.bind, props.node) : item.options.text || ''; return typeof data === 'object' ? JSON.stringify(data) : String(data) }
function href(item) { return layoutUrl(item.options.href_bind ? bindingValue(item.options.href_bind, props.node) : item.options.href) }
function badge(item) { const value = Number(bindingValue(item.options.badge, props.node)); return Number.isFinite(value) ? Math.max(0, value) : 0 }
function available(action) {
  if (!['inspect','operate','preview','tasks','notes','upload','create','link','relations'].includes(action)) return false
  if (['tasks', 'notes'].includes(action)) return props.node.kind === 'object' || process.value
  if (['create', 'link'].includes(action)) return props.node.branch?.kind === 'relation' && (action !== 'link' || props.node.branch.relationship === 'instance')
  if (action === 'relations') return props.node.kind === 'object'
  if (['inspect', 'preview'].includes(action)) return props.node.kind !== 'branch'
  return true
}
function act(action, event) { if (!props.readOnly && !props.editing && available(action)) emit('action', action, props.node, event) }
</script>

<template>
  <LayoutContainer :tag="nativeFlow ? Fragment : 'div'" class="item-layout" :class="{'item-layout-editing':editing}" :style="{gridTemplateColumns:tracks,'--item-mobile-tracks':mobileTracks}">
    <LayoutContainer :tag="tag(item)" v-for="item in elements" :key="item.name" class="item-layout-element" :class="[...classes(item),'item-widget-' + item.kind, 'item-tone-' + item.tone, {'item-element-selected':editing && selectedElement === item.name}]"
      :data-layout-element="item.name" :style="nativeFlow ? (item.layer ? {zIndex:item.layer} : undefined) : {zIndex:item.layer || 0,...(only ? {} : {gridColumn:`${item.column} / span ${item.span}`,gridRow:`${item.row} / span ${item.rows}`,alignSelf:item.align})}"
      @pointerenter="item.role==='actions'?emit('controls',true):item.role==='title-line'&&fitTitleActions($event)" @pointerleave="item.role==='actions'&&emit('controls',false)" @focusin="item.role==='title-line'&&fitTitleActions($event)" @click="editing ? (emit('element',item.name), $event.stopPropagation()) : item.role==='actions'&&$event.stopPropagation()">
      <ItemLayout v-if="item.kind === 'group'" :presentation="childPresentation" :layout="layout" :node="node" :parent="item.name" :read-only="readOnly" :editing="editing" :selected-element="selectedElement" @action="(...args)=>emit('action',...args)" @completion="(...args)=>emit('completion',...args)" @element="emit('element',$event)" @controls="emit('controls',$event)" />
      <ItemLayout v-else-if="item.kind === 'view' && item.widget_layout" :layout="item.widget_layout" :node="node" :presentation="childPresentation" :read-only="readOnly" :editing="editing" @action="(...args)=>emit('action',...args)" @completion="(...args)=>emit('completion',...args)" @controls="emit('controls',$event)" />
      <span v-else-if="item.kind === 'view'">{{ item.options.view || t('Choose a reusable view') }}</span>
      <template v-else-if="item.kind === 'image'">
        <AppIcon v-if="node.kind === 'branch'" :name="process ? (node.branch.process_type==='hierarchy'?'FAS_CODE_BRANCH':'FAS_CIRCLE') : 'stream'" />
        <ItemPreview v-else :source="layoutUrl(previewSource(item),true)" :fallback-text="node.kind === 'object' ? initials : ''" :fallback-icon="snapshot.multiple?'folder':node.snapshot_display&&!snapshot.exists?'FAS_EXCLAMATION_CIRCLE':'file'" :round="item.role==='preview'&&node.kind==='object'&&!presentation.card" :accent="node.accent || node.record?.color || 'var(--content-accent)'" :fill-mode="item.options.fit || 'cover'" :style="item.role==='preview'?undefined:{width:'100%',height:item.height+'px'}" />
      </template>
      <template v-else-if="item.kind === 'title' && nativeFlow && item.tag==='strong'"><MiddleElide v-if="presentation.tree&&node.kind==='snapshot'" :text="title" /><template v-else>{{ node.branch?.kind==='versions'?t(title):title }}</template></template>
      <strong v-else-if="item.kind === 'title'" class="item-layout-title"><MiddleElide v-if="node.kind === 'snapshot'" :text="value(item) || title" /><template v-else>{{ value(item) || title }}</template><small v-if="node.kind === 'snapshot' && !snapshot.exists"> ({{ t('File Offline') }})</small></strong>
      <span v-else-if="item.kind === 'text' || item.kind === 'description'">{{ item.role==='description'?subtitle:value(item) }}</span>
      <a v-else-if="item.kind === 'link' && href(item)" :href="href(item)" :tabindex="editing ? -1 : undefined" @click="editing ? $event.preventDefault() : $event.stopPropagation()" :target="href(item).startsWith('/') ? undefined : '_blank'" rel="noopener noreferrer">{{ value(item) || item.title }}</a>
      <span v-else-if="item.kind === 'link'">{{ value(item) || item.title }}</span>
      <AppButton :class="nativeFlow ? roleClasses[item.role] : undefined" v-else-if="item.kind === 'button' && (editing || href(item) || available(item.options.action))" :href="!readOnly && !editing ? href(item) || undefined : undefined" :label="item.options.bind ? value(item) || item.title : item.options.text || item.title" :translate-label="!item.options.bind" :icon="item.options.icon" :icon-only="!!item.options.icon && !item.options.text && !item.options.bind" :badge-count="badge(item)" :disabled="readOnly || editing" @click.stop="act(item.options.action,$event)"><template v-if="item.options.bind">{{ value(item) }}</template></AppButton>
      <LayoutContainer :tag="item.role==='metadata'?Fragment:'div'" v-else-if="item.kind === 'metadata' && node.kind === 'object'" class="result-metadata">
        <AppButton v-for="progress in presentation.compact ? node.progress_items?.slice(0,1) : node.progress_items || []" :key="progress.name" class="result-progress" icon="MDI_CHART_DONUT" :style="{'--chip-accent':progress.accent || node.accent}" :disabled="readOnly || editing" :title="t('Open tracked objects')" @click.stop="emit('completion',node,progress)">{{ progress.name }}: {{ progress.approved }} / {{ progress.total }}</AppButton>
        <span v-if="node.progress_items?.length && node.info_items?.length" class="muted">|</span>
        <template v-for="(info,index) in node.info_items || []" :key="info.column"><span v-if="index" class="muted">|</span><a v-if="layoutUrl(info.url)" :href="layoutUrl(info.url)" :title="info.tooltip" target="_blank" rel="noopener noreferrer" @click.stop="editing && $event.preventDefault()">{{ info.text }}</a><span v-else :title="info.tooltip">{{ info.text }}</span></template>
      </LayoutContainer>
      <template v-else-if="item.kind === 'snapshot-details' && node.kind === 'snapshot'">
        <div class="result-snapshot-technical"><span class="result-snapshot-version">{{ snapshot.version }}</span><span v-if="snapshot.revision">{{ snapshot.revision }}</span><span v-if="node.record?.repo" :style="{color:snapshot.repositoryColor}">{{ snapshot.repository || node.record?.repo }}</span><small v-if="snapshot.latest" class="result-snapshot-latest">{{ t('Latest') }}</small><time class="result-snapshot-date" :datetime="node.record?.timestamp" :title="timestampFullLabel(node.record?.timestamp)"><span>{{ timestampLabel(node.record?.timestamp) }}</span><span>{{ timestampFullLabel(node.record?.timestamp) }}</span></time></div>
        <div class="result-snapshot-description"><em v-if="snapshot.author">{{ snapshot.author }}{{ subtitle ? ':' : '' }}</em><span>{{ subtitle }}</span><small><template v-for="(chip,index) in snapshot.infoChips || []" :key="chip.label"><template v-if="index"> | </template><span :title="chip.label+': '+chip.value">{{ chip.value }}</span></template></small></div>
      </template>
      <template v-else-if="item.kind === 'quick-actions' && node.kind !== 'branch'">
        <LayoutContainer :tag="nativeFlow?Fragment:'div'" class="item-quick-actions"><AppButton v-if="node.kind==='object'||node.kind==='snapshot'" label="Save snapshot" icon="save" icon-only :disabled="readOnly || editing" @click.stop="emit('action','quickaction',node,'save')" /><AppButton v-if="node.kind === 'snapshot' || node.has_snapshot" label="Open snapshot" icon="folder-open" icon-only :disabled="readOnly || editing" @click.stop="emit('action','quickaction',node,'open')" /></LayoutContainer>
      </template>
      <template v-else-if="item.kind==='snapshot-size'"><span class="result-snapshot-size">{{ prettySize(snapshot.size) }}</span></template>
      <template v-else-if="item.kind==='snapshot-summary'">{{ node.record?.context }} · <template v-if="node.record?.version < 0">{{ t('Versionless') }}</template><template v-else>{{ t('Version') }} {{ node.record?.version }}</template></template>
      <template v-else-if="item.kind==='file-offline'">({{ t('File Offline') }})</template>
      <template v-else-if="item.kind==='branch-summary'">{{ t(node.branch?.kind==='relation'?'Objects':'Versions') }}: {{ node.branch.count ?? node.children?.length ?? 0 }}<template v-if="node.hasNext">+</template><template v-if="process&&!node.branch.count&&node.hasChildren"> · {{ t('Versionless') }}</template></template>
      <AppMenu v-else-if="item.kind==='item-menu'" label="Item actions" overlay>
        <AppCheckbox v-if="presentation.selectable" label="Select record" :model-value="presentation.checked" :disabled="readOnly||editing" @update:model-value="emit('action','select',node,$event)" />
        <AppMenuItem v-if="node.kind!=='branch'" label="Object details" icon="MDI_INFORMATION_OUTLINE" :disabled="readOnly||editing" @click="act('inspect',$event)" />
        <AppMenuItem v-if="node.kind!=='branch'" label="File preview" icon="image" :disabled="readOnly||editing" @click="act('preview',$event)" />
        <template v-if="node.kind==='object'||process">
          <AppMenuItem label="Tasks" icon="FAR_CALENDAR_CHECK" :disabled="readOnly||editing" @click="act('tasks',$event)" />
          <AppMenuItem label="Notes" icon="FAS_COMMENT_ALT" :disabled="readOnly||editing" @click="act('notes',$event)" />
        </template>
        <template v-if="node.branch?.kind==='relation'">
          <AppMenuItem v-if="node.branch.relationship==='instance'" label="Link existing objects" icon="link" :disabled="readOnly||editing" @click="act('link',$event)" />
          <AppMenuItem label="Create related object" icon="add" :disabled="readOnly||editing" @click="act('create',$event)" />
        </template>
        <AppMenuItem v-for="article in node.knowledge || []" :key="article.identity" :label="article.title" :translate="false" icon="book-open" :disabled="readOnly||editing" @click="openObjectTab?.(article.searchKey)" />
        <AppMenuItem label="Object actions" icon="more" :disabled="readOnly||editing" @click="act('operate',$event)" />
      </AppMenu>
      <template v-else-if="item.kind === 'knowledge'">
        <AppButton v-if="node.knowledge?.length === 1" label="Knowledge Base" icon="book-open" icon-only :disabled="editing || readOnly" @click.stop="openObjectTab?.(node.knowledge[0].searchKey)" />
        <AppMenu v-else-if="node.knowledge?.length > 1" label="Knowledge Base" icon="book-open" overlay><AppMenuItem v-for="article in node.knowledge" :key="article.identity" :label="article.title" :translate="false" icon="file" :disabled="editing || readOnly" @click="openObjectTab?.(article.searchKey)" /></AppMenu>
      </template>
      <LayoutContainer :tag="nativeFlow?Fragment:'div'" v-else-if="item.kind === 'relations' && node.branch?.kind === 'relation'" class="item-quick-actions"><AppButton v-if="node.branch.relationship === 'instance'" label="Link existing objects" icon="link" icon-only :disabled="readOnly || editing" @click.stop="act('link',$event)" /><AppButton label="Create related object" icon="add" icon-only :disabled="readOnly || editing" @click.stop="act('create',$event)" /><small v-if="node.branch.count>0" class="result-relation-count muted">| &nbsp;{{ node.branch.count }}</small></LayoutContainer>
    </LayoutContainer>
  </LayoutContainer>
</template>

<style>
.item-layout { display:grid; gap:3px 8px; align-items:center; min-width:0; width:100%; isolation:isolate; }
.item-layout-element { min-width:0; overflow-wrap:anywhere; }
.item-layout-title { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:var(--result-title-size,var(--text-body)); }
.item-widget-description, .item-tone-muted { color:var(--muted); }
.item-tone-strong { font-weight:600; }
.item-quick-actions { display:flex; align-items:center; gap:5px; }
.item-layout-editing .item-layout-element { outline:1px dashed var(--outline); cursor:pointer; min-height:24px; }
.item-layout-editing .item-element-selected { outline:2px solid var(--primary); }
.item-widget-quick-actions:not(.result-title-actions):not(:hover):not(:focus-within) .item-quick-actions { opacity:0; }
.item-layout-editing .item-widget-quick-actions .item-quick-actions { opacity:1; }
@media (max-width:600px) { .item-layout { grid-template-columns:var(--item-mobile-tracks) !important; } }
</style>
