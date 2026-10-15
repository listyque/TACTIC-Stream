<script setup>
import { computed, inject, ref, watch, onBeforeUnmount } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import { mobile } from '../../mobile.js'
import { prettySize } from '../checkin/files.js'
import { timestampLabel, timestampFullLabel } from '../activity/activity.js'
import MiddleElide from '../../controls/MiddleElide.vue'

const props = defineProps({ node: Object, compact: Boolean, card: Boolean, tree: Boolean, selected: Boolean, checked: Boolean, selectable: Boolean, back: Boolean, navigable: { type: Boolean, default: true } })
const openObjectTab = inject('openObjectTab', null)
defineEmits(['back', 'upload', 'expand', 'activate', 'doubleclick', 'newtab', 'quickaction', 'relations', 'inspect', 'operate', 'select', 'preview', 'notes', 'tasks', 'create', 'completion', 'link'])
const record = computed(() => props.node.record || {})
const previewSource = computed(() => {
  const preview = props.node.preview
  return mobile.value && props.node.kind === 'object'
    ? preview?.files?.find(file => file.type === 'web' && file.href)?.href || preview?.image
    : preview?.image
})
const title = computed(() => props.node.kind === 'snapshot' && props.node.snapshot_display ? (props.node.snapshot_display.multiple
  ? t('Multiple files | {count}', { count: props.node.snapshot_display.multiple }) : props.node.snapshot_display.title)
  : props.node.title || record.value.name || record.value.title || record.value.code || String(record.value.id || ''))
// Handler global_functions.gen_acronym: capital letters, then the first letters
// as fallback. Numbers are not words ("Episode 01 — Arrival" becomes EA).
const initials = computed(() => {
  const text = title.value[0]?.toUpperCase() + title.value.slice(1)
  let acronym = [...text].filter(char => /[\p{Lu}]/u.test(char)).slice(0, 2).join('')
  if (acronym.length < 2) acronym += text.slice(1, 2)
  return acronym.toUpperCase() || '?'
})
const branch = computed(() => props.node.kind === 'branch')
const relation = computed(() => props.node.branch?.kind === 'relation')
const process = computed(() => props.node.branch?.kind === 'process')
const accent = computed(() => props.node.accent || record.value.color || 'var(--content-accent)')
const subtitle = computed(() => props.node.subtitle || record.value.description || (props.node.kind === 'snapshot' ? t('No description') : ''))
const controlHover = ref(false), titleActionsFit = ref(true)
let hoverTimer
function holdControls() { clearTimeout(hoverTimer); controlHover.value = true }
function releaseControls() {
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => { if (!props.node.menuVisible) controlHover.value = false }, 500)
}
function fitTitleActions(event) {
  if (mobile.value || !props.tree || props.node.kind !== 'object') return
  const line = event.currentTarget, count = line.querySelectorAll('.result-title-actions button').length
  titleActionsFit.value = line.querySelector('strong').scrollWidth + 8 + count * 28 + Math.max(0, count - 1) * 5 <= line.parentElement.clientWidth
}
watch(() => props.node.menuVisible, visible => { if (!visible) releaseControls() })
onBeforeUnmount(() => clearTimeout(hoverTimer))
</script>

<template>
  <article class="result-item" :class="{ 'result-item-compact': compact, 'result-item-card': card, 'result-item-branch': branch,
    'result-mobile-header': back, 'result-item-object': node.kind === 'object', 'result-item-relation': relation, 'result-item-process': process, 'result-item-snapshot': node.kind === 'snapshot', 'result-item-tree': tree, 'menu-open': node.menuVisible, 'control-hover': controlHover, selected }"
    :style="{ '--result-depth': node.depth || 0, '--result-accent': accent }"
    :data-result-key="record.__search_key__" :data-node-id="node.id" :aria-label="title" tabindex="0"
    @click="$emit('activate', node, $event)" @keydown.enter.self.prevent="$emit('activate', node, $event)" @keydown.space.self.prevent="$emit('activate', node, $event)"
    @dblclick="event => { if (!event.target.closest('button,a,summary')) $emit('doubleclick', node, event) }"
    @auxclick.middle.prevent="event => { if (!event.target.closest('button,a,summary')) { $emit('activate', node, event); $emit('newtab', node) } }"
    @keydown.right.self.prevent.stop="mobile ? navigable && $emit('activate', node, $event) : $emit('expand', node, true, $event)" @keydown.left.self.prevent.stop="!mobile && $emit('expand', node, false, $event)"
    @contextmenu.prevent.stop="event => { if (!mobile && !selected) $emit('activate', node, event); $emit('operate', node, event) }">
    <span class="result-surface" aria-hidden="true"></span>
    <span v-for="depth in node.depth || 0" :key="depth" class="result-guide" :class="{ 'result-guide-elbow': depth === node.depth }" :style="{ left: (11 + (depth - 1) * 24) + 'px' }" aria-hidden="true"></span>
    <AppIcon v-if="mobile && navigable" class="result-mobile-next" name="MDI_CHEVRON_RIGHT" />
    <AppButton v-if="mobile && back" class="result-mobile-back" label="Back" icon="MDI_ARROW_LEFT" icon-only @click.stop="$emit('back')" />
    <AppButton v-else-if="!mobile && node.hasChildren" class="result-expand" icon-only icon="MDI_CHEVRON_RIGHT" :class="{ expanded: node.expanded }"
      :label="node.expanded ? 'Collapse item' : 'Expand item'" :aria-expanded="!!node.expanded" :disabled="node.busy" @click.stop="$emit('expand', node, undefined, $event)" />
    <span v-else-if="!mobile" class="result-expand-spacer"></span>
    <component :is="tree || mobile ? 'span' : 'button'" v-if="node.kind !== 'branch'" class="result-preview" :aria-label="tree || mobile ? undefined : t('File preview')" @click="event => { if (!tree && !mobile) { event.stopPropagation(); $emit('preview', node) } }">
      <ItemPreview :source="previewSource" :fallback-text="node.kind === 'object' ? initials : ''" :fallback-icon="node.snapshot_display?.multiple ? 'folder' : node.snapshot_display && !node.snapshot_display.exists ? 'FAS_EXCLAMATION_CIRCLE' : 'file'" :round="node.kind === 'object' && !card" :accent="accent" />
    </component>
    <span v-else class="result-branch-icon"><AppIcon :name="process ? (node.branch.process_type === 'hierarchy' ? 'FAS_CODE_BRANCH' : 'FAS_CIRCLE') : 'stream'" /></span>
    <div class="result-item-copy">
      <div class="result-title-line" @pointerenter="fitTitleActions" @focusin="fitTitleActions"><component :is="back ? 'h2' : 'strong'"><MiddleElide v-if="tree && node.kind === 'snapshot'" :text="title" /><template v-else>{{ node.branch?.kind === 'versions' ? t(title) : title }}</template></component>
        <span v-if="tree && !branch" class="result-title-actions" :class="{ 'actions-fit': titleActionsFit }" @click.stop>
          <AppButton v-if="node.kind === 'object' || node.kind === 'snapshot'" label="Save snapshot" icon="save" icon-only @click="$emit('quickaction', node, 'save')" />
          <AppButton v-if="node.kind === 'snapshot' || node.has_snapshot" label="Open snapshot" icon="folder-open" icon-only @click="$emit('quickaction', node, 'open')" />
        </span>
        <span v-if="tree && node.kind === 'snapshot' && title && !node.snapshot_display?.exists" class="result-file-offline">({{ t('File Offline') }})</span>
      </div>
      <span v-if="!branch && node.kind !== 'snapshot' && subtitle" class="result-description">{{ subtitle }}</span>
      <div v-if="node.kind === 'object'" class="result-metadata">
        <AppButton v-for="item in compact ? node.progress_items?.slice(0, 1) : node.progress_items" :key="item.name" class="result-progress" icon="MDI_CHART_DONUT" :style="{ '--chip-accent': item.accent || accent }"
          :title="t('Open tracked objects')" @click.stop="$emit('completion', node, item)">{{ item.name }}: {{ item.approved }} / {{ item.total }}</AppButton>
        <span v-if="node.progress_items?.length && node.info_items?.length" class="muted">|</span>
        <template v-for="(item, index) in node.info_items" :key="item.column"><span v-if="index" class="muted">|</span>
          <a v-if="item.url" :href="item.url" :title="item.tooltip" target="_blank" rel="noopener noreferrer" @click.stop>{{ item.text }}</a>
          <span v-else :title="item.tooltip">{{ item.text }}</span>
        </template>
      </div>
      <template v-else-if="tree && node.kind === 'snapshot'">
        <div class="result-snapshot-technical"><span class="result-snapshot-version">{{ node.snapshot_display?.version }}</span><span v-if="node.snapshot_display?.revision">{{ node.snapshot_display.revision }}</span><span v-if="record.repo" :style="{ color: node.snapshot_display?.repositoryColor }">{{ node.snapshot_display?.repository || record.repo }}</span><small v-if="node.snapshot_display?.latest" class="result-snapshot-latest">{{ t('Latest') }}</small>
          <time class="result-snapshot-date" :datetime="record.timestamp" :title="timestampFullLabel(record.timestamp)"><span>{{ timestampLabel(record.timestamp) }}</span><span>{{ timestampFullLabel(record.timestamp) }}</span></time>
        </div>
        <div class="result-snapshot-description"><em v-if="node.snapshot_display?.author">{{ node.snapshot_display.author }}{{ subtitle ? ':' : '' }}</em><span>{{ subtitle }}</span><small><template v-for="(chip, index) in node.snapshot_display?.infoChips" :key="chip.label"><template v-if="index"> | </template><span :title="chip.label + ': ' + chip.value">{{ chip.value }}</span></template></small></div>
      </template>
      <small v-else-if="node.kind === 'snapshot'" class="muted">{{ record.context }} · <template v-if="record.version < 0">{{ t('Versionless') }}</template><template v-else>{{ t('Version') }} {{ record.version }}</template></small>
      <small v-else-if="mobile && branch" class="result-branch-summary muted">{{ t(relation ? 'Objects' : 'Versions') }}: {{ node.branch.count ?? node.children?.length ?? 0 }}<template v-if="node.hasNext">+</template><template v-if="process && !node.branch.count && node.hasChildren"> · {{ t('Versionless') }}</template></small>
    </div>
    <div class="result-item-actions" @click.stop @pointerenter="holdControls" @pointerleave="releaseControls">
    <div v-if="mobile && (node.kind === 'object' || process || back && node.kind === 'snapshot')" class="result-mobile-actions">
      <template v-if="node.kind === 'object' || process">
        <AppButton label="Tasks" icon="FAR_CALENDAR_CHECK" icon-only :badge-count="node.task_count || 0" @click="$emit('tasks', node, $event)" />
        <AppButton label="Notes" icon="FAS_COMMENT_ALT" icon-only :badge-count="node.note_count || 0" @click="$emit('notes', node, $event)" />
      </template>
      <AppButton label="Add files" icon="upload" icon-only @click="$emit('upload', node)" />
    </div>
      <span v-if="tree && node.kind === 'snapshot' && node.snapshot_display?.size != null" class="result-snapshot-size">{{ prettySize(node.snapshot_display.size) }}</span>
      <AppMenu v-if="mobile" label="Item actions" overlay>
        <AppCheckbox v-if="selectable" label="Select record" :model-value="checked" @update:model-value="$emit('select', node, $event)" />
        <AppMenuItem v-if="!branch" label="Object details" icon="MDI_INFORMATION_OUTLINE" @click="$emit('inspect', node)" />
        <AppMenuItem v-if="!branch" label="File preview" icon="image" @click="$emit('preview', node)" />
        <template v-if="node.kind === 'object' || process">
          <AppMenuItem label="Tasks" icon="FAR_CALENDAR_CHECK" @click="$emit('tasks', node, $event)" />
          <AppMenuItem label="Notes" icon="FAS_COMMENT_ALT" @click="$emit('notes', node, $event)" />
        </template>
        <template v-if="relation">
          <AppMenuItem v-if="node.branch.relationship === 'instance'" label="Link existing objects" icon="link" @click="$emit('link', node)" />
          <AppMenuItem label="Create related object" icon="add" @click="$emit('create', node)" />
        </template>
        <AppMenuItem v-for="article in node.knowledge || []" :key="article.identity" :label="article.title" :translate="false" icon="book-open" @click="openObjectTab?.(article.searchKey)" />
        <AppMenuItem label="Object actions" icon="more" @click="$emit('operate', node, $event)" />
      </AppMenu>
      <template v-else>
      <div v-if="tree && node.kind === 'object'" class="result-hover-actions"><AppButton label="Related and child objects" icon="FAS_SITEMAP" icon-only @click="$emit('relations', node, $event)" /></div>
      <div v-else-if="!tree" class="result-hover-actions"><AppButton v-if="!branch" class="result-details" label="Object details" icon="MDI_INFORMATION_OUTLINE" icon-only @click="$emit('inspect', node)" />
        <AppButton label="Object actions" icon="more" icon-only @click="$emit('operate', node, $event)" /></div>
      <template v-if="relation"><AppButton v-if="node.branch.relationship === 'instance'" label="Link existing objects" icon="link" icon-only @click="$emit('link', node)" />
        <AppButton label="Create related object" icon="add" icon-only @click="$emit('create', node)" />
        <small v-if="node.branch.count > 0" class="result-relation-count muted">| &nbsp;{{ node.branch.count }}</small></template>
      <AppButton v-if="node.knowledge?.length===1" icon-only icon="book-open" label="Knowledge Base" @click="openObjectTab?.(node.knowledge[0].searchKey)" />
      <AppMenu v-else-if="node.knowledge?.length>1" icon="book-open" label="Knowledge Base" overlay><AppMenuItem v-for="article in node.knowledge" :key="article.identity" :label="article.title" icon="file" @click="openObjectTab?.(article.searchKey)" /></AppMenu>
      <div v-if="node.kind === 'object' || process" class="result-communication" :class="{ 'result-communication-empty': process && !node.task_count && !node.note_count }">
        <AppButton class="result-task-button" label="Tasks" icon="FAR_CALENDAR_CHECK" icon-only :badge-count="node.task_count || 0" @click="$emit('tasks', node, $event)" />
        <AppButton class="result-note-button" label="Notes" icon="FAS_COMMENT_ALT" icon-only :badge-count="node.note_count || 0" @click="$emit('notes', node, $event)" />
      </div>
      </template>
    </div>
  </article>
</template>
