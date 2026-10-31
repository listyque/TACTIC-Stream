<script setup>
import AppSelect from '../../controls/AppSelect.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import AppTextField from '../../controls/AppTextField.vue';
import AppDateField from '../../controls/AppDateField.vue';
import AppSlider from '../../controls/AppSlider.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppSpinBox from '../../controls/forms/AppSpinBox.vue';
import UserComboBox from '../../controls/UserComboBox.vue';
import { t } from '../../i18n.js';

const props = defineProps({
  field: Object,
  value: [String, Number],
  statuses: Array,
  users: Array,
  busy: Boolean,
  catalog: Object,
  compact: Boolean
});
const emit = defineEmits(['change']);
const titles = {
  status: 'Status',
  assigned: 'Assigned to',
  supervisor: 'Supervisor',
  bid_start_date: 'Start date',
  bid_end_date: 'End date',
  bid_duration: 'Planned hours',
  completion: 'Progress',
  progress: 'Progress',
  description: 'Description',
  process: 'Process',
  context: 'Context',
  priority: 'Priority',
  milestone_code: 'Milestone'
};
function date(value) {
  return value ? String(value).replace(' ', 'T').slice(0, 16) : '';
}
const hourScale = () =>
  props.field.name === 'bid_duration' &&
  props.catalog?.bidDurationUnit === 'minute'
    ? 60
    : 1;
const numericValue = () =>
  hourScale() === 1
    ? Number(props.value || 0)
    : Math.round((Number(props.value || 0) / hourScale()) * 100) / 100;
</script>

<template>
  <UserComboBox
    v-if="['assigned', 'supervisor'].includes(field.name)"
    :value="value || ''"
    :empty-label="
      field.name === 'supervisor' ? 'No supervisor' : 'Not assigned'
    "
    :options="users"
    :label="titles[field.name]"
    :action-field="compact"
    :disabled="busy || !field.editable"
    @change="emit('change', $event)"
  />
  <AppSelect
    v-else-if="field.name === 'status'"
    :model-value="value ?? ''"
    :label="titles[field.name]"
    :translate-labels="false"
    :options="[
      { value: '', label: t('Select status'), disabled: true },
      ...statuses.map((value) => ({ value, label: value }))
    ]"
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  />
  <AppTextArea
    v-else-if="field.name === 'description'"
    :model-value="value || ''"
    label="Description"
    rows="2"
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  />
  <AppSelect
    v-else-if="
      ['priority', 'milestone_code'].includes(field.name) ||
      (field.name === 'process' && catalog?.processes?.length)
    "
    :model-value="value ?? ''"
    :label="titles[field.name]"
    :translate-labels="false"
    :options="
      (
        (field.name === 'priority'
          ? catalog?.priorityChoices
          : field.name === 'milestone_code'
            ? catalog?.milestoneChoices
            : catalog?.processes) || []
      ).map((item) =>
        item.value === '' &&
        ['No priority', 'No milestone'].includes(item.label)
          ? { ...item, label: t(item.label) }
          : item
      )
    "
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  />
  <AppTextField
    v-else-if="['process', 'context'].includes(field.name)"
    type="text"
    :model-value="value || ''"
    :label="titles[field.name]"
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  >
  </AppTextField>
  <AppDateField
    include-time
    v-else-if="field.name.endsWith('_date')"
    :model-value="date(value)"
    :label="titles[field.name]"
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  />
  <div v-else-if="field.name === 'bid_duration'" class="task-hours-field">
    <AppIcon name="schedule" />
    <AppSpinBox
      :min="0"
      :max="100000"
      :step="0.25"
      :decimals="2"
      :model-value="numericValue()"
      :label="titles[field.name]"
      :disabled="busy || !field.editable"
      @update:model-value="emit('change', $event * hourScale())"
    />
    <span class="muted">{{ t('h') }}</span>
  </div>
  <div
    v-else-if="['progress', 'completion'].includes(field.name)"
    class="task-progress-field"
  >
    <AppSlider
      :model-value="Number(value || 0)"
      label="Progress"
      :disabled="busy || !field.editable"
      @update:model-value="emit('change', $event)"
    />
    <output>{{ Number(value || 0) }}%</output>
  </div>
  <AppTextField
    v-else
    type="number"
    min="0"
    max="100"
    step="1"
    :model-value="numericValue()"
    :label="titles[field.name]"
    :disabled="busy || !field.editable"
    @update:model-value="emit('change', $event)"
  />
</template>

<style>
.task-progress-field,
.task-hours-field {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  min-width: 0;
}
.task-progress-field > .app-slider,
.task-hours-field > .app-spin-box {
  flex: 1;
  min-width: 0;
}
.task-progress-field > output {
  min-width: 4ch;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.task-hours-field > .app-spin-box {
  max-height: 100%;
}
.task-hours-field > .app-icon {
  color: var(--muted);
}
</style>
