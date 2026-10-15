<script setup>
import { ref } from 'vue'
import AppDateField from '../../controls/AppDateField.vue'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import { t } from '../../i18n.js'
const props = defineProps({ dockTarget:String, dockReport:String, data: Object, draft: Object, editing: Boolean, busy: Boolean, error: String, uncertain: Boolean, deleting: String, users: Array,
  mode: { type: String, default: 'task' }, week: String, login: String, selected: Array, report: String, canCreate: Boolean, confirmation: Boolean })
const emit = defineEmits(['create', 'edit', 'save', 'action', 'cancel-edit', 'delete', 'close', 'refresh', 'change',
  'scope', 'move-week', 'select', 'clear-selection', 'bulk', 'keep-editing', 'discard-close'])
const dialog = ref(null)
const form = ref(null)
const opened = ref(false)
defineExpose({ open: () => { opened.value = true; if (!props.dockTarget) dialog.value.show() }, close: () => { opened.value = false; if (!props.dockTarget) dialog.value?.close() }, isOpen: () => props.dockTarget ? opened.value : !!dialog.value?.open })
</script>

<template>
  <Teleport defer :to="dockTarget || 'body'"><component :is="dockTarget ? 'section' : 'dialog'" v-show="!dockTarget || opened" v-window="dockTarget ? false : { type:'window' }" ref="dialog" class="time-entry-panel" :class="{ 'record-dialog':!dockTarget, 'time-entry-panel-docked':!!dockTarget }" :role="dockTarget ? 'region' : 'dialog'" :aria-label="t(mode === 'task' ? 'Task timesheet' : mode === 'report' ? dockReport === 'labor_cost' ? 'Cost Reports' : 'Work reports' : 'Weekly timesheet')" :aria-busy="busy" @cancel.prevent="emit('close')">
    <header><div><h2>{{ t(mode === 'task' ? 'Task timesheet' : mode === 'report' ? dockReport === 'labor_cost' ? 'Cost Reports' : 'Work reports' : 'Weekly timesheet') }}</h2><small>{{ mode === 'task' ? t('Time entries for the selected task') : `${data?.week_start || week} — ${data?.week_end || ''}` }}</small></div><AppButton label="Close" icon="close" icon-only :disabled="busy" @click="emit('close')" /></header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <p v-if="uncertain" class="notice">{{ t('Refresh and check the timesheet before retrying. The server may have saved the changes.') }}</p>
    <aside v-if="confirmation" class="notice" role="alert"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Keep editing" @click="emit('keep-editing')" /><AppButton label="Discard changes" destructive @click="emit('discard-close')" /></aside>
    <div class="configuration-actions">
      <AppButton v-if="mode !== 'report'" label="Log time" icon="add" :disabled="busy || uncertain || editing || !data || !canCreate" :title="!canCreate ? t('Select a task before logging time') : undefined" @click="emit('create')" />
      <AppButton v-if="mode !== 'week'" label="Weekly timesheet" icon="table" :disabled="busy || uncertain || editing" @click="emit('scope', 'mode', 'week')" />
      <AppButton v-if="mode !== 'task' && canCreate" label="Task timesheet" icon="MDI_CLOCK_OUTLINE" :disabled="busy || uncertain || editing" @click="emit('scope', 'mode', 'task')" />
      <AppButton v-if="mode !== 'report'" label="Open work reports" icon="MDI_CHART_BAR" :disabled="busy || uncertain || editing" @click="emit('scope', 'mode', 'report')" />
      <AppButton label="Refresh" icon="refresh" :disabled="busy" @click="emit('refresh')" /></div>
    <div v-if="mode !== 'task'" class="timesheet-filters">
      <div class="timesheet-week"><AppButton label="Previous week" icon="previous" icon-only :disabled="busy || uncertain || editing" @click="emit('move-week', -1)" /><label>{{ t('Week') }}<AppDateField :model-value="week" label="Week" :include-time="false" :allow-clear="false" :disabled="busy || uncertain || editing" @change="emit('scope', 'week', $event)" /></label><AppButton label="Next week" icon="next" icon-only :disabled="busy || uncertain || editing" @click="emit('move-week', 1)" /></div>
      <label>{{ t('Team member') }}<AppSelect :model-value="login" :options="[{ value: '', label: t('All users') }, ...users]" label="Team member" :translate-labels="false" :disabled="busy || uncertain || editing" @update:model-value="emit('scope', 'login', $event)" /></label>
    </div>
    <template v-if="mode === 'week'">
      <dl v-if="data" class="timesheet-summary"><div v-for="(label, name) in { logged: 'Logged', approved: 'Approved', pending: 'Pending', overtime: 'Overtime' }" :key="name"><dt>{{ t(label) }}</dt><dd>{{ data.summary[name] }} {{ t('h') }}</dd></div></dl>
      <div v-if="selected?.length" class="configuration-actions"><span>{{ t('{count} selected', { count: selected.length }) }}</span><AppButton label="Approve selected entries" icon="check" :disabled="busy || uncertain || editing" @click="emit('bulk', 'approve')" /><AppButton label="Return selected entries to pending" icon="MDI_UNDO" :disabled="busy || uncertain || editing" @click="emit('bulk', 'reject')" /><AppButton label="Clear selection" icon="close" :disabled="busy" @click="emit('clear-selection')" /></div>
    </template>
    <section v-if="mode === 'report'" class="work-reports">
      <label>{{ t('Report') }}<AppSelect :model-value="report" :options="(data?.reports || []).filter(row => !dockReport || row.value === dockReport)" label="Report" :disabled="busy || uncertain" @update:model-value="emit('scope', 'report', $event)" /></label>
      <p v-if="data?.reports">{{ t(data.reports.find(item => item.value === report)?.description || '') }}</p>
      <p v-if="data?.message" class="notice">{{ t(data.message) }}</p>
      <p v-if="data && !data.rows.length" class="muted">{{ t('No report data for this week') }}</p>
      <article v-for="(row, index) in data?.rows || []" :key="index" class="work-report-row"><strong>{{ row.localized ? t(row.label) : row.label }}</strong><progress :value="row.share" max="1" :aria-label="row.localized ? t(row.label) : row.label" /><span>{{ data.unit === 'cost' ? Number(row.value).toFixed(2) : `${row.value} ${t('h')}` }}</span></article>
    </section>
    <form v-if="editing" ref="form" class="time-entry-form" @submit.prevent="emit('save', false)">
      <h3>{{ t(draft.search_key ? 'Edit time entry' : 'Log time') }}</h3>
      <label>{{ t('Day') }}<AppDateField :model-value="draft.day" label="Day" :include-time="false" :allow-clear="false" required :disabled="busy || uncertain" @update:model-value="emit('change', 'day', $event)" /></label>
      <label>{{ t('Hours') }}<input type="number" min="0.01" max="24" step="0.01" required :value="draft.hours" :disabled="busy || uncertain" @input="emit('change', 'hours', $event.target.value)"></label>
      <label>{{ t('Category') }}<AppSelect :model-value="draft.category" :options="[{ value: 'regular', label: 'Regular' }, { value: 'overtime', label: 'Overtime' }]" label="Category" :disabled="busy || uncertain" @update:model-value="emit('change', 'category', $event)" /></label>
      <label>{{ t('User') }}<AppSelect :model-value="draft.login" :options="users" label="User" :translate-labels="false" :disabled="busy || uncertain" @update:model-value="emit('change', 'login', $event)" /></label>
      <label>{{ t('Description') }}<textarea rows="2" :value="draft.description" :disabled="busy || uncertain" @input="emit('change', 'description', $event.target.value)" /></label>
      <footer><AppButton label="Cancel" :disabled="busy" @click="emit('cancel-edit')" /><AppButton type="submit" label="Save" icon="save" :disabled="busy || uncertain" /><AppButton label="Save & Approve" icon="check" highlighted :disabled="busy || uncertain" @click="form.reportValidity() && emit('save', true)" /></footer>
    </form>
    <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
    <p v-else-if="mode !== 'report' && data && !data.entries.length" class="muted">{{ t(mode === 'week' ? 'No work hours for this week' : 'No time entries yet') }}</p>
    <div v-if="mode !== 'report'" class="time-entry-list">
      <article v-for="entry in data?.entries || []" :key="entry.search_key" class="note-entry">
        <header><AppCheckbox v-if="mode === 'week'" label="Select time entry" :model-value="selected.includes(entry.search_key)" :disabled="busy || uncertain || editing" @update:model-value="emit('select', entry.search_key, $event)"><span class="visually-hidden">{{ entry.task_title }} · {{ entry.day }}</span></AppCheckbox>
          <strong>{{ entry.day }} · {{ entry.hours }} {{ t('h') }}</strong><span>{{ entry.login }} · {{ t(entry.category === 'overtime' ? 'Overtime' : 'Regular') }} · {{ t(entry.status === 'approved' ? 'Approved' : 'Pending') }}</span></header>
        <p v-if="mode === 'week'">{{ entry.task_title || t('Removed task') }} · {{ entry.process }}</p>
        <p class="note-body">{{ entry.description }}</p>
        <div class="configuration-actions"><AppButton label="Edit time entry" icon="edit" icon-only :disabled="busy || uncertain || editing || entry.can_edit === false" @click="emit('edit', entry)" /><AppButton :label="entry.status === 'approved' ? 'Revoke approval' : 'Approve time entry'" icon="check" :disabled="busy || uncertain || editing" @click="emit('action', entry, entry.status === 'approved' ? 'reject' : 'approve')" /><AppButton label="Delete time entry" icon="delete" destructive icon-only :disabled="busy || uncertain || editing" @click="emit('delete', entry.search_key)" /></div>
        <div v-if="deleting === entry.search_key" class="notice"><p>{{ t('Delete this time entry?') }}</p><AppButton label="Delete time entry" icon="delete" destructive :disabled="busy || uncertain" @click="emit('action', entry, 'delete')" /><AppButton label="Cancel" :disabled="busy" @click="emit('delete', '')" /></div>
      </article>
    </div>
  </component></Teleport>
</template>
