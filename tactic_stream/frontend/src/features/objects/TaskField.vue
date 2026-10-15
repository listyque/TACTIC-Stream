<script setup>
import AppSelect from '../../controls/AppSelect.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppDateField from '../../controls/AppDateField.vue'
import UserComboBox from '../../controls/UserComboBox.vue'
import { t } from '../../i18n.js'

const props = defineProps({ field: Object, value: [String, Number], statuses: Array, users: Array, busy: Boolean, catalog: Object, compact: Boolean })
const emit = defineEmits(['change'])
const titles = { status: 'Status', assigned: 'Assigned to', supervisor: 'Supervisor', bid_start_date: 'Start date',
  bid_end_date: 'End date', bid_duration: 'Planned hours', completion: 'Progress', progress: 'Progress', description: 'Description',
  process: 'Process', context: 'Context', priority: 'Priority', milestone_code: 'Milestone' }
function date(value) { return value ? String(value).replace(' ', 'T').slice(0, 16) : '' }
const hourScale = () => props.field.name === 'bid_duration' && props.catalog?.bidDurationUnit === 'minute' ? 60 : 1
const numericValue = () => hourScale() === 1 ? Number(props.value || 0) : Math.round(Number(props.value || 0) / hourScale() * 100) / 100
</script>

<template>
  <UserComboBox v-if="['assigned','supervisor'].includes(field.name)" :value="value || ''" :options="users" :label="titles[field.name]" :action-field="compact" :disabled="busy || !field.editable" @change="emit('change',$event)" />
  <AppSelect v-else-if="field.name === 'status'" :model-value="value ?? ''" :label="titles[field.name]" :translate-labels="false"
    :options="[{ value: '', label: t('Select status'), disabled: true }, ...statuses.map(value => ({ value, label: value }))]"
    :disabled="busy || !field.editable" @update:model-value="emit('change', $event)" />
  <AppTextArea v-else-if="field.name === 'description'" :model-value="value || ''" label="Description" rows="2" :disabled="busy || !field.editable" @update:model-value="emit('change', $event)" />
  <AppSelect v-else-if="['priority', 'milestone_code'].includes(field.name) || field.name === 'process' && catalog?.processes?.length"
    :model-value="value ?? ''" :label="titles[field.name]" :translate-labels="false"
    :options="((field.name === 'priority' ? catalog?.priorityChoices : field.name === 'milestone_code' ? catalog?.milestoneChoices : catalog?.processes) || []).map(item => item.value === '' && ['No priority', 'No milestone'].includes(item.label) ? { ...item, label: t(item.label) } : item)"
    :disabled="busy || !field.editable" @update:model-value="emit('change', $event)" />
  <AppTextField v-else-if="['process', 'context'].includes(field.name)" type="text" :model-value="value || ''" :label="titles[field.name]" :disabled="busy || !field.editable" @update:model-value="emit('change', $event)">
  </AppTextField>
  <AppDateField v-else-if="field.name.endsWith('_date')" :model-value="date(value)" :label="titles[field.name]" :disabled="busy || !field.editable" @update:model-value="emit('change', $event)" />
  <AppTextField v-else type="number" min="0" :max="field.name === 'bid_duration' ? 100000 : 100" step="any" :model-value="numericValue()" :label="titles[field.name]" :disabled="busy || !field.editable" @update:model-value="emit('change', hourScale() === 1 ? $event : Number($event) * hourScale())" />
</template>
