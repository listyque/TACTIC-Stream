<script setup>
// Handler TasksController staged/bulk editing, thlib/ui/tasks.py (EPL-1.0).
import TaskField from '../objects/TaskField.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppButton from '../../controls/AppButton.vue'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
defineProps({ editor: Object, busy: Boolean, immediate: Boolean })
const emit = defineEmits(['change', 'enable', 'process', 'apply', 'cancel', 'milestones'])
const titles = { process: 'Process', context: 'Context', status: 'Status', assigned: 'Assigned to', supervisor: 'Supervisor',
  bid_start_date: 'Start date', bid_end_date: 'End date', bid_duration: 'Planned hours', progress: 'Progress',
  completion: 'Progress', description: 'Description', priority: 'Priority', milestone_code: 'Milestone' }
</script>

<template>
  <form v-if="editor" class="record-form" @submit.prevent="!immediate && emit('apply')">
    <p v-if="!mobile || !immediate" class="muted">{{ t('Changes remain pending until Save.') }}</p>
    <label v-for="field in editor.fields" :key="field.name" :data-task-field="field.name">
      <AppCheckbox v-if="!immediate && editor.plans.length > 1" :label="titles[field.name] || field.name" :model-value="editor.enabled.includes(field.name)" :disabled="busy" @update:model-value="emit('enable', field.name, $event)" />
      <span v-else>{{ t(titles[field.name] || field.name) }}</span>
      <TaskField :field="field" :value="editor.values[field.name]" :statuses="editor.statuses" :users="editor.users" :catalog="editor.catalog"
        :busy="busy || editor.plans.length > 1 && !editor.enabled.includes(field.name)"
        @change="field.name === 'process' && editor.creating ? emit('process', $event) : emit('change', field.name, $event)" />
      <AppButton v-if="field.name === 'milestone_code'" label="Project milestones" icon="MDI_FLAG_VARIANT" :disabled="busy" @click="emit('milestones')" />
    </label>
    <footer v-if="!immediate" class="configuration-actions"><AppButton label="Cancel" :disabled="busy" @click="emit('cancel')" /><AppButton label="Apply to draft" icon="check" type="submit" highlighted :disabled="busy" /></footer>
  </form>
</template>
