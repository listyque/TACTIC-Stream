<script setup>
// Handler MilestoneManagerView.qml (EPL-1.0), presenter only.
import { ref } from 'vue'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import AppDateField from '../../controls/AppDateField.vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
const props = defineProps({ project: String, result: Object, rows: Array, query: String, busy: Boolean, error: String,
  uncertain: String, confirmation: String, deleting: String, focused: String })
const emit = defineEmits(['query', 'create', 'change', 'save', 'discard', 'delete', 'review', 'refresh', 'inspect-server', 'close', 'keep-editing', 'confirm', 'cancel-delete', 'confirm-delete'])
const dialog = ref(null)
const editable = name => props.result?.fields.some(field => field.name === name && field.editable)
function focusRow(code, input = false) { const row = [...(dialog.value?.querySelectorAll('[data-milestone]') || [])].find(row => row.dataset.milestone === code); row?.scrollIntoView({ block: 'nearest' }); if (input) row?.querySelector('input')?.focus() }
function dateBadge(value, month = false) { const date = new Date(value + 'T12:00:00'); return Number.isNaN(date.getTime()) ? '—' : month ? date.toLocaleDateString(appearance.language, { month: 'short' }) : date.getDate() }
defineExpose({ open: () => { if (!dialog.value.open) dialog.value.show() }, close: () => dialog.value?.close(), focusRow })
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{kind:'milestone_manager', type:'window' }" ref="dialog" class="configuration-dialog milestone-manager" :aria-label="t('Project milestones')" @cancel.prevent="emit('close')">
      <header class="task-manager-heading"><div><h2>{{ t('Project milestones') }}</h2><small class="muted">{{ project }} · {{ t('Reusable deadlines and the plan of linked tasks.') }}</small></div>
        <div class="configuration-actions"><AppButton label="Refresh" icon="refresh" icon-only :disabled="busy" @click="emit('refresh')" /><AppButton label="New milestone" icon="add" :disabled="busy || !!uncertain || !result?.canCreate" @click="emit('create')" /><AppButton label="Close" icon="close" icon-only :disabled="busy" @click="emit('close')" /></div></header>
      <aside v-if="confirmation" class="notice"><p>{{ t(confirmation === 'close' ? 'Discard unsaved milestone changes?' : 'Refreshing will discard every unsaved milestone change.') }}</p><AppButton label="Keep editing" @click="emit('keep-editing')" /><AppButton label="Discard changes" destructive @click="emit('confirm')" /></aside>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <aside v-if="uncertain" class="notice" role="alert"><p>{{ t('The server may have saved this milestone. Inspect the server data before discarding the draft; saving is blocked.') }}</p><AppButton label="Inspect current server data" icon="refresh" :disabled="busy" @click="emit('inspect-server')" /><AppButton label="Discard changes" :disabled="busy" @click="emit('discard', uncertain)" /></aside>
      <div v-if="uncertain && result" class="milestone-server-data"><strong>{{ t('Current server data') }}</strong><p v-for="row in result.records" :key="row.code">{{ row.code }} · {{ row.description }} · {{ row.dueDate }}</p></div>
      <label class="workspace-search milestone-search"><AppIcon name="search" /><input type="search" :value="query" :placeholder="t('Find a milestone')" :aria-label="t('Find a milestone')" @input="emit('query', $event.target.value)" /><span>{{ rows.length }}</span></label>
      <div class="milestone-results" :aria-busy="busy">
        <article v-for="row in rows" :key="row.code" class="milestone-row" :class="{ selected: focused === row.code }" :data-milestone="row.code">
          <div class="milestone-date"><strong>{{ dateBadge(row.dueDate) }}</strong><small>{{ dateBadge(row.dueDate, true) }}</small></div>
          <div class="milestone-content">
            <div class="milestone-row-heading"><small class="muted">{{ t(row.isNew ? 'New milestone' : 'Milestone') }} · {{ t(row.saving ? 'Saving…' : row.dirty ? 'Unsaved changes' : 'Saved') }}</small>
              <div class="configuration-actions"><AppButton label="Discard changes" icon="undo" icon-only :disabled="busy || !row.dirty && !row.uncertain" @click="emit('discard', row.code)" /><AppButton label="Save milestone" icon="save" icon-only highlighted :disabled="busy || !!uncertain || !row.dirty" @click="emit('save', row.code)" /><AppButton label="Delete milestone" icon="delete" icon-only destructive :disabled="busy || !!uncertain || !result?.canDelete" @click="emit('delete', row.code)" /></div>
            </div>
            <form class="milestone-fields" @submit.prevent="emit('save', row.code)">
              <label>{{ t('Milestone name') }}<input :value="row.description" maxlength="4096" :aria-label="t('Milestone name')" :disabled="busy || !!uncertain || !editable('description')" @input="emit('change', row.code, 'description', $event.target.value)" /></label>
              <label>{{ t('Due date') }}<AppDateField :model-value="row.dueDate" label="Due date" :include-time="false" :disabled="busy || !!uncertain || !editable('due_date')" @update:model-value="emit('change', row.code, 'dueDate', $event)" /></label>
            </form>
            <div class="milestone-plan"><strong><AppIcon name="MDI_FLAG_VARIANT" /> {{ t('Linked task plan') }}</strong>
              <span>{{ row.completedCount ?? '—' }} / {{ row.taskCount }} {{ t('tasks complete') }}</span>
              <small>{{ row.planStartDate || '—' }} → {{ row.dueDate || '—' }}<template v-if="row.plannedHours !== null"> · {{ row.plannedHours }} {{ t('h') }}</template></small>
              <small v-if="row.processSummary" class="muted">{{ row.processSummary }}</small>
              <div v-if="row.completion !== null" class="milestone-progress"><progress max="100" :value="Math.min(100, row.completion)" :aria-label="t('Task completion')" /><span>{{ row.completion }}%</span></div>
              <small v-if="row.overdueCount" class="error">{{ t('{count} overdue tasks', { count: row.overdueCount }) }}</small>
            </div>
            <p v-if="row.error" class="error" role="alert">{{ t(row.error) }} <AppButton v-if="!uncertain" label="Review current milestone revision" icon="refresh" :disabled="busy" @click="emit('review', row.code)" /></p>
          </div>
        </article>
        <p v-if="!rows.length" class="table-message">{{ t(busy ? 'Loading data…' : query ? 'No milestones match your search.' : 'No project milestones yet.') }}</p>
      </div>
      <aside v-if="deleting" class="notice milestone-delete" role="alert"><p>{{ t('Delete this milestone? It can only be deleted when no tasks use it.') }}</p><AppButton label="Cancel" :disabled="busy" @click="emit('cancel-delete')" /><AppButton label="Delete milestone" icon="delete" destructive :disabled="busy || !!uncertain" @click="emit('confirm-delete')" /></aside>
    </dialog>
  </Teleport>
</template>
