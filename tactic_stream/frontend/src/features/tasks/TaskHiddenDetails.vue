<script setup>
// Handler TaskHiddenDetails.qml (EPL-1.0): TaskManager owns its plan/draft.
import { computed, nextTick, ref, watch } from 'vue'
import TaskField from '../objects/TaskField.vue'
import StatusSelect from '../../controls/StatusSelect.vue'
import UserComboBox from '../../controls/UserComboBox.vue'
import AppButton from '../../controls/AppButton.vue'
import AppSlider from '../../controls/AppSlider.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import { t } from '../../i18n.js'
const props = defineProps({ editor: Object, columns: Array, busy: Boolean })
const emit = defineEmits(['change', 'milestones'])
const description = ref(''), editing = ref(false), area = ref(null)
const titles = { process: 'Process', status: 'Status', assigned: 'Assignee', supervisor: 'Supervisor', priority: 'Priority',
  milestone_code: 'Milestone', bid_start_date: 'Start', bid_end_date: 'Deadline', progress: 'Progress', completion: 'Progress', bid_duration: 'Expected work hours' }
const fields = computed(() => {
  const visible = key => props.columns.some(column => column.key === key && column.visible)
  const order = ['process', 'status', 'assigned', 'bid_start_date', 'bid_end_date', 'progress', 'completion', 'bid_duration', 'priority', 'milestone_code', 'supervisor']
  return order.flatMap(name => {
    const field = props.editor?.fields.find(field => field.name === name)
    const key = name.endsWith('_date') ? 'dates' : name === 'completion' ? 'progress' : name
    return field && (name === 'process' ? props.editor.plans[0].operation === 'create' : ['priority', 'milestone_code', 'supervisor'].includes(name) || visible(key)) ? [field] : []
  })
})
const descriptionField = computed(() => props.editor?.fields.find(field => field.name === 'description'))
const creating = computed(() => props.editor?.plans[0].operation === 'create')
watch(() => props.editor?.values.description, value => { if (!editing.value) description.value = value || '' }, { immediate: true })
watch(creating, value => { editing.value = !!value }, { immediate: true })
function finish() { if (!props.busy && descriptionField.value?.editable && description.value !== (props.editor.values.description || '')) emit('change', 'description', description.value); editing.value = creating.value }
async function editDescription() { if (editing.value) { finish(); area.value?.$el.blur() } else { editing.value = true; await nextTick(); area.value?.focus() } }
function escape(event) { description.value = props.editor.values.description || ''; editing.value = creating.value; event.target.blur() }
</script>
<template>
  <section v-if="editor" class="task-workspace-details">
    <div class="task-detail-grid">
      <label v-for="field in fields" :key="field.name" :data-task-field="field.name" class="task-detail-field">
        <span>{{ t(titles[field.name]) }}<output v-if="['progress', 'completion'].includes(field.name)">{{ editor.values[field.name] || 0 }}%</output></span>
        <StatusSelect v-if="field.name === 'status'" :value="editor.values.status || ''" :options="editor.statusChoices" :disabled="busy || !field.editable" @change="emit('change', field.name, $event)" />
        <UserComboBox v-else-if="['assigned', 'supervisor'].includes(field.name)" :label="titles[field.name]" :value="editor.values[field.name] || ''" :options="editor.users" :disabled="busy || !field.editable" @change="emit('change', field.name, $event)" />
        <AppSlider v-else-if="['progress', 'completion'].includes(field.name)" :label="titles[field.name]" :model-value="Number(editor.values[field.name] || 0)" :disabled="busy || !field.editable" @update:model-value="emit('change', field.name, $event)" />
        <div v-else-if="field.name === 'milestone_code'" class="task-detail-milestone"><TaskField :field="field" :value="editor.values[field.name]" :catalog="editor.catalog" :busy="busy" @change="emit('change', field.name, $event)" /><AppButton label="Project milestones" icon="add" icon-only :disabled="busy" @click="emit('milestones')" /></div>
        <TaskField v-else :field="field" :value="editor.values[field.name]" :catalog="editor.catalog" :busy="busy" @change="emit('change', field.name, $event)" />
      </label>
    </div>
    <div v-if="descriptionField" class="task-detail-description" data-task-field="description">
      <span>{{ t('Description') }}</span>
      <div><AppTextArea ref="area" v-model="description" label="Description" placeholder="Add task description…" :readonly="!editing" :disabled="busy || !descriptionField.editable" @blur="finish" @keydown.esc.prevent="escape" />
        <AppButton v-if="!creating" :label="editing ? 'Finish editing description' : 'Edit task description'" :icon="editing ? 'check' : 'edit'" icon-only :disabled="busy || !descriptionField.editable" @mousedown.prevent @click="editDescription" /></div>
    </div>
  </section>
</template>
