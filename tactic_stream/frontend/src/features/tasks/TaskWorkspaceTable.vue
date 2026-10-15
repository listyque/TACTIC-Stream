<script setup>
// Handler TaskBrowserTable/TaskHiddenDetails: presentation only, EPL-1.0.
// TaskManager owns the native plans, selection, column preferences and drafts.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import TaskHiddenDetails from './TaskHiddenDetails.vue'
import { t } from '../../i18n.js'
const props = defineProps({ groups: Array, columns: Array, selected: Array, collapsed: Array, busy: Boolean, blocked: Boolean,
  allSelected: Boolean, active: String, expanded: Array, editors: Object })
const emit = defineEmits(['select', 'select-all', 'collapse', 'sort', 'inspect', 'object', 'operate', 'activate', 'key', 'expand', 'change', 'edit-cell', 'milestones', 'size-column', 'columns', 'column-context'])
const table = ref(null), resizing = ref(null)
const width = ref(0)
let observer
onMounted(() => { observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width }); observer.observe(table.value.parentElement) })
onBeforeUnmount(() => observer?.disconnect())
const spacing = computed(() => width.value < 420 ? 3 : width.value < 1100 ? 5 : 7)
const visibleColumns = computed(() => {
  const minimums = { assigned: 520, dates: 700, progress: 800, bid_duration: 900, notes: 480, priority: 980, milestone_code: 1180, supervisor: 1380 }
  const dense = { status: 105, assigned: 118, dates: 90, progress: 72, bid_duration: 72, notes: 38, priority: 80, milestone_code: 105, supervisor: 118 }
  return props.columns.filter(column => column.visible && column.key !== 'process' && width.value >= (minimums[column.key] || 0)).map(column => {
    const size = column.key === 'object' ? Math.max(132, Math.min(column.width, width.value * .25, 210)) : column.key === 'status' && width.value < 420 ? Math.min(column.width, 88) : width.value < 1100 ? Math.min(column.width, dense[column.key] || column.width) : column.width
    return { ...column, size: size + spacing.value }
  })
})
const tableWidth = computed(() => Math.max(width.value, visibleColumns.value.reduce((total, column) => total + column.size, 98 + spacing.value)))
const layoutColumns = computed(() => {
  const extra = tableWidth.value - visibleColumns.value.reduce((total, column) => total + column.size, 98 + spacing.value)
  return visibleColumns.value.map(column => ({ ...column, size: column.size + (column.key === 'status' ? extra : 0) }))
})
const initials = value => value.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase()
const hours = value => { const text = Number(value || 0).toFixed(2).replace(/0$/, ''); return text.endsWith('.') ? text + '0' : text }
const plannedHours = task => task.pending ? Number(task.bid_duration || 0) / (props.editors[task.key]?.catalog.bidDurationUnit === 'minute' ? 60 : 1) : task.__hours__?.planned || Number(task.bid_duration || 0)
const progress = task => Math.max(0, Math.min(100, Number(task.progress ?? task.completion ?? 0)))
let checkboxModifiers = {}
const modifiers = event => ({ shiftKey: event.shiftKey, ctrlKey: event.ctrlKey, metaKey: event.metaKey })
function actions(task, event) { emit('operate', task, event.currentTarget.getBoundingClientRect()) }
function cell(task, column, event) {
  emit('activate', task.key, modifiers(event))
  if (!event.shiftKey && !event.ctrlKey && !event.metaKey) emit('edit-cell', task, column, event.currentTarget.getBoundingClientRect())
}
function activate(task, event) { if (!event.target.closest('button, input, select, textarea, label, a')) emit('activate', task.key, modifiers(event)) }
function keyboard(event) {
  if (event.target.closest('input, textarea, select, button, [contenteditable="true"]') || !['ArrowDown', 'ArrowUp', 'Home', 'End', ' ', 'a'].includes(event.key) || event.key === 'a' && !(event.ctrlKey || event.metaKey)) return
  event.preventDefault(); emit('key', event.key, modifiers(event))
}
function resize(column, event) {
  if (event.pointerType !== 'mouse' || event.button !== 0) return
  event.preventDefault(); event.stopPropagation(); event.currentTarget.setPointerCapture(event.pointerId)
  resizing.value = { key: column.key, width: column.width, x: event.clientX, id: event.pointerId }
}
function move(event) { if (resizing.value?.id === event.pointerId) emit('size-column', resizing.value.key, resizing.value.width + event.clientX - resizing.value.x) }
function resizeKey(column, event) { if (['ArrowLeft', 'ArrowRight'].includes(event.key)) { event.preventDefault(); event.stopPropagation(); emit('size-column', column.key, column.width + (event.key === 'ArrowRight' ? 10 : -10)) } }
function focusRow(key) { const row = [...table.value.querySelectorAll('[data-task-key]')].find(row => row.dataset.taskKey === key); row?.focus({ preventScroll: true }); row?.scrollIntoView({ block: 'nearest', inline: 'nearest' }) }
defineExpose({ focusRow })
</script>

<template>
  <div ref="table" class="task-workspace-surface" @keydown="keyboard">
  <table class="task-workspace-table" tabindex="0" :aria-label="t('Project task table')" :style="{ width: tableWidth + 'px', '--task-column-spacing': spacing + 'px', '--task-object-width': (layoutColumns.find(column => column.key === 'object')?.size - spacing) + 'px' }">
    <colgroup><col :style="{ width: 61 + spacing + 'px' }"><col v-for="column in layoutColumns" :key="column.key" :style="{ width: column.size + 'px' }"><col style="width: 37px"></colgroup>
    <thead><tr><th><AppCheckbox label="Select all tasks" :model-value="allSelected" :indeterminate="!!selected.length && !allSelected" :disabled="busy" @update:model-value="emit('select-all', $event)"><span class="visually-hidden">{{ t('Select all tasks') }}</span></AppCheckbox></th>
      <th v-for="column in layoutColumns" :key="column.key" :data-task-column="column.key" :title="t(column.label)" @contextmenu.prevent="emit('column-context', column, $event.currentTarget.getBoundingClientRect())">
        <AppButton v-if="column.sort" :disabled="busy" @click="emit('sort', column.sort)">{{ t(column.label) }}</AppButton><span v-else>{{ t(column.label) }}</span>
        <span class="task-column-resizer" role="separator" tabindex="0" :aria-label="t('Resize {column}', { column: t(column.label) })" aria-orientation="vertical" :aria-valuenow="column.width" aria-valuemin="40" aria-valuemax="480"
          @keydown="resizeKey(column, $event)" @pointerdown="resize(column, $event)" @pointermove="move" @pointerup="resizing = null" @pointercancel="resizing = null" @lostpointercapture="resizing = null" />
      </th><th><AppButton label="Task columns" icon="MDI_VIEW_COLUMN" icon-only @click="emit('columns')" /></th></tr></thead>
    <tbody v-for="group in groups" :key="group.key">
      <tr v-if="group.key" class="task-group"><th :colspan="layoutColumns.length + 2"><AppButton :icon="collapsed.includes(group.key) ? 'next' : 'MDI_CHEVRON_DOWN'" :aria-expanded="!collapsed.includes(group.key)" @click="emit('collapse', group.key)"><span>{{ group.label }}</span><small>{{ group.tasks.length }}</small></AppButton></th></tr>
      <template v-for="task in collapsed.includes(group.key) ? [] : group.tasks" :key="task.key">
      <tr :data-task-key="task.key" :tabindex="active === task.key ? 0 : -1" :style="{ '--task-process-color': task.__process__?.color || undefined }" :class="{ pending: task.pending, 'task-active': active === task.key, 'task-selected': selected.includes(task.key), 'task-deleted': task.deleting, 'task-row-expanded': expanded.includes(task.key) }"
        @click="activate(task, $event)" @dblclick="!$event.target.closest('button, input, select, textarea, label, a') && emit('object', task)" @contextmenu.prevent="actions(task, $event)">
        <td class="task-row-controls"><AppButton :label="expanded.includes(task.key) ? 'Collapse task details' : 'Expand task details'" :icon="expanded.includes(task.key) ? 'MDI_CHEVRON_DOWN' : 'next'" icon-only :aria-expanded="expanded.includes(task.key)" :disabled="busy || task.deleting || !task.parent" @click="emit('expand', task)" />
          <AppCheckbox :label="task.title + ': ' + task.process" :translate-label="false" :model-value="selected.includes(task.key)" :disabled="busy" @click.capture="$event.target.tagName === 'INPUT' && (checkboxModifiers = modifiers($event))" @update:model-value="emit('select', task.key, $event, checkboxModifiers); checkboxModifiers = {}"><span class="visually-hidden">{{ task.title }}</span></AppCheckbox></td>
        <td v-for="column in expanded.includes(task.key) ? layoutColumns.filter(column => column.key === 'object') : layoutColumns" :key="column.key" :data-task-cell="column.key" :colspan="expanded.includes(task.key) ? layoutColumns.length : 1">
          <template v-if="column.key === 'object'"><div class="record-link"><ItemPreview :source="task.parent?.__preview__?.image" :fallback-text="initials(task.title)" :accent="task.__process__?.color" :preview-size="34" /><span><strong>{{ task.title }}</strong><small>{{ task.__process__?.label || task.process }}{{ task.context && task.context !== task.process ? ' · ' + task.context : '' }}</small></span></div>
            <AppButton v-if="expanded.includes(task.key)" class="task-expanded-notes" :aria-label="t('Open notes') + ': ' + task.title" icon="comment" icon-only :badge-count="task.notes" :disabled="task.pending" @click="emit('inspect', task)" /></template>
          <AppButton v-else-if="column.key === 'notes'" :aria-label="t('Open notes') + ': ' + task.title" icon="comment" icon-only :badge-count="task.notes" :title="String(task.notes)" :disabled="task.pending" @click="emit('inspect', task)" />
          <AppButton v-else class="task-cell-value" :disabled="blocked || task.deleting" :aria-label="t('Edit {column}', { column: t(column.label) }) + ': ' + task.title" @click="cell(task, column, $event)">
            <span v-if="column.key === 'status'" class="task-cell-choice"><i class="task-status-dot" :style="{ background: task.__status__?.color || 'var(--primary)' }"></i>{{ task.__status__?.label && !task.pending ? task.__status__.label : task.status || t('No status') }}</span>
            <span v-else-if="['assigned', 'supervisor'].includes(column.key)" class="task-cell-choice"><ItemPreview :source="task[column.key + 'User']?.avatarUrl" :fallback-text="task[column.key + 'User']?.initials" fallback-icon="user" :accent="task[column.key + 'User']?.avatarColor" :preview-size="22" round outlined />{{ task[column.key] === '—' ? t('Not assigned') : task[column.key] }}</span>
            <span v-else-if="column.key === 'dates'" class="task-cell-dates"><small :title="task.bid_start_date">{{ task.bid_start_date?.slice(0, 10) || '—' }}</small><span :title="task.bid_end_date" :class="{ 'task-overdue': task.bid_end_date && task.bid_end_date.slice(0, 10) < new Date().toLocaleDateString('en-CA') && progress(task) < 100 }">{{ task.bid_end_date?.slice(0, 10) || '—' }}</span></span>
            <span v-else-if="column.key === 'progress'" class="task-cell-progress">{{ progress(task) }}%<i><i :style="{ width: progress(task) + '%', background: task.__process__?.color || 'var(--primary)' }"></i></i></span>
            <span v-else-if="column.key === 'bid_duration'" :class="{ 'task-overdue': task.__hours__?.approved > plannedHours(task), 'task-hours-pending': task.__hours__?.pending > 0 }">{{ hours(task.__hours__?.approved) }} / {{ hours(plannedHours(task)) }} h</span>
            <span v-else>{{ task[column.key] ?? '—' }}</span>
          </AppButton>
        </td>
        <td><AppButton label="Task actions" icon="more" icon-only :disabled="busy" @click="actions(task, $event)" /></td>
      </tr>
      <tr v-if="expanded.includes(task.key)" class="task-expanded-row"><td :colspan="layoutColumns.length + 2"><TaskHiddenDetails :aria-label="t('Task details') + ': ' + task.title" :editor="editors[task.key]" :columns="columns" :busy="blocked" @change="(name, value) => emit('change', task.key, name, value)" @milestones="emit('milestones')" /></td></tr>
      </template>
    </tbody>
  </table>
  </div>
</template>

<style>
.task-workspace-surface { min-width:0; }
</style>
