<script>
// Handler TacticTableCellDisplay: one presenter for a typed server value.
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppButton from '../../controls/AppButton.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import TaskCell from './TaskCell.vue'
import CompletionCell from './CompletionCell.vue'
import StructuredCell from './StructuredCell.vue'
import { t } from '../../i18n.js'
import { timestampLabel, timestampFullLabel } from '../activity/activity.js'

export default {
  components: { AppCheckbox, AppIcon, AppButton, ItemPreview, TaskCell, CompletionCell, StructuredCell },
  props: { element: Object, record: Object, cell: Object, loading: Boolean, inspectable: Boolean, editable: Boolean, expanded: Boolean, selectedTaskPreview: Boolean, height: { type: Number, default: 58 }, accent: String, dataType: String },
  emits: ['inspect', 'preview', 'notes', 'tasks', 'task-edit', 'expand', 'action', 'task-hover'],
  computed: {
    value() { const value = this.cell?.text ?? this.record[this.element.field]; return this.cell?.label ? t(this.cell.label) : value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value) },
    displayValue() { return this.cell && Object.hasOwn(this.cell, 'text') ? this.value : this.value || '—' },
    checked() { return this.cell?.checked ?? ['1', 'true', 'yes', 'on'].includes(this.value.toLowerCase()) },
    initials() { const names = String(this.record.name || this.record.title || this.record.code || '').trim().split(/\s+/); return names[0] ? (names[0][0] + (names[1]?.[0] || '')).toUpperCase() : '?' },
    action() { return ({ sobject_detail: ['search', 'Open details'], checkin: ['upload', 'Check-in'], explorer: ['folder-open', 'Open folder'], file_list: ['inventory-2', 'Open files'], metadata: ['description', 'Open metadata'], delete: ['delete', 'Delete sObject'] })[this.element.cell?.kind] },
    date() { return /^(date|datetime|timestamptz|timestamp)/.test(this.dataType || '') && this.element.cell?.kind === 'text' },
    text() { return this.date ? timestampLabel(this.value) || this.displayValue : this.displayValue },
    tooltip() { return this.cell?.tooltip || (this.date ? timestampFullLabel(this.value) : this.value) },
  },
  methods: { t },
}
</script>

<template>
  <span v-if="!element.supported" class="muted">{{ t('Widget unavailable') }}</span>
  <span v-else-if="cell?.error" class="error-text" :title="cell.error" role="status">{{ t('Cell calculation failed') }}: {{ cell.error }}</span>
  <span v-else-if="loading && element.cell?.server && !cell" class="muted">{{ t('Loading data…') }}</span>
  <AppButton v-else-if="element.cell?.kind === 'journal-details'" :label="expanded ? 'Hide transaction details' : 'Show transaction details'" :icon="expanded ? 'MDI_CHEVRON_DOWN' : 'MDI_CHEVRON_RIGHT'" icon-only :aria-expanded="expanded" @click="$emit('expand')" />
  <TaskCell v-else-if="element.cell?.kind === 'tasks'" :cell="cell" :height="height - 6" :editable="editable" :selected-preview="selectedTaskPreview" @hover="$emit('task-hover', $event)" @inspect="task => $emit('tasks', cell, task)" @edit="(task, field, bounds) => $emit('task-edit', cell, task, field, bounds)" />
  <AppButton v-else-if="action" class="table-action" :label="action[1]" :icon="action[0]" icon-only :destructive="element.cell.kind === 'delete'" :disabled="(['delete','checkin'].includes(element.cell.kind) && !editable) || cell?.available === false" @click="$emit('action', element.cell.kind, cell)" />
  <CompletionCell v-else-if="element.cell?.kind === 'completion'" :percent="cell?.completion" :text="cell?.text" />
  <StructuredCell v-else-if="element.cell?.kind === 'structured'" :cell="cell" :height="Number(String(element.display?.options?.height || '').replace('px', '')) || undefined" />
  <span v-else-if="element.cell?.kind === 'notes'" class="table-notes">
    <AppButton v-for="item in cell?.processes || []" :key="item.process" class="table-note-chip" :style="{ '--note-accent': item.accent || accent || 'var(--primary)' }" :label="`${item.label || item.process} (${item.count})`" :translate-label="false" icon="comment" :disabled="!cell?.search_key" @click="$emit('notes', cell, item.process)"><span>{{ item.label || item.process }}</span><small>({{ item.count }})</small></AppButton>
    <AppButton v-if="!cell?.processes?.length" label="Add note" icon="comment" icon-only :badge-count="cell?.count" :disabled="!cell?.search_key" @click="$emit('notes', cell, element.display?.options?.process || '')" />
  </span>
  <AppButton v-else-if="element.cell?.kind === 'thumbnail'" class="table-thumbnail" label="File preview" :style="{ '--table-preview-size': Math.max(0, Math.min(element.width || 160, height) - 8) + 'px' }" @click="$emit('preview', cell)">
    <ItemPreview :source="cell?.image" :fallback-text="initials" :accent="accent" :preview-size="Math.min(element.width || 160, height) - 8" round />
  </AppButton>
  <AppCheckbox v-else-if="element.cell?.kind === 'boolean'" :model-value="checked" :label="element.title" :translate-label="false" disabled><span class="visually-hidden">{{ element.title }}</span></AppCheckbox>
  <span v-else-if="element.cell?.kind === 'check'" :aria-label="value" :title="value"><AppIcon v-if="checked" name="check" /></span>
  <a v-else-if="element.cell?.kind === 'link' && cell?.href" class="table-cell-link" :href="cell.href" :target="cell.href.startsWith('/') ? undefined : '_blank'" rel="noopener noreferrer">{{ value }}</a>
  <span v-else :title="tooltip" :class="{ 'error-text': cell?.negative }">{{ text }}</span>
</template>

<style>
.handler-table-cell .table-thumbnail { display:flex; justify-content:center; width:100%; height:100%; min-width:0; min-height:0; border:0; background:transparent; padding:0; }
.handler-table-cell .table-thumbnail .item-preview { width:var(--table-preview-size); height:var(--table-preview-size); flex-basis:var(--table-preview-size); }
.handler-table-cell .table-action { width:28px; height:28px; min-width:28px; min-height:28px; margin:auto; color:var(--primary); }
.handler-table-cell .table-action.danger { color:var(--error); }
.handler-table-cell .table-notes { width:100%; max-height:calc(var(--table-row-height) - 8px); padding:0 7px; overflow:auto; gap:2px; }
.table-notes .table-note-chip { width:100%; height:26px; min-height:26px; min-width:0; justify-content:flex-start; padding:0 7px; gap:5px; border:1px solid color-mix(in srgb, var(--note-accent) 32%, var(--outline-variant)); border-left:3px solid var(--note-accent); background:color-mix(in srgb, var(--note-accent) 8%, var(--surface-high)); border-radius:var(--item-radius); }
.table-notes .table-note-chip { position:relative; border-left-width:1px; overflow:visible; }
.table-note-chip::before { content:''; position:absolute; left:-1px; top:-1px; bottom:-1px; width:3px; border-radius:1.5px; background:var(--note-accent); }
.table-notes .table-note-chip:hover:not(:disabled) { border-color:color-mix(in srgb, var(--note-accent) 32%, var(--outline-variant)); background:color-mix(in srgb, var(--note-accent) 16%, var(--surface-high)); }
.table-note-chip > .app-icon { color:var(--note-accent); font-size:14px; }
.table-note-chip > span:not(.app-icon) { min-width:0; overflow:hidden; text-overflow:ellipsis; }
.table-note-chip > small { margin-left:auto; color:var(--note-accent); font-size:var(--text-small); }
</style>
