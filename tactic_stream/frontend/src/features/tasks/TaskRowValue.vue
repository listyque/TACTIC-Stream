<script setup>
import { computed } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import TaskCellDisplay from './TaskCellDisplay.vue';
import { t } from '../../i18n.js';
import { fieldEditable } from '../../../../src/tactic_stream/shared_ui/features/tasks/cells.ui.mjs';
const props = defineProps({ task: Object, column: Object, blocked: Boolean });
const emit = defineEmits(['edit']);
const editable = computed(() => fieldEditable(props.task, props.column.key));
const source = computed(() => props.column.sourceKey);
const model = computed(() => {
  const task = props.task,
    key = source.value;
  if (key === 'status')
    return {
      text: task.__status__?.label || task.status || t('No status'),
      showAccent: true,
      accent: task.__status__?.color || 'action'
    };
  if (['assigned', 'supervisor'].includes(key))
    return {
      text:
        !task[key + 'Login'] &&
        !task[key + 'User']?.value &&
        ['—', 'Not assigned', 'No supervisor'].includes(task[key])
          ? t(key === 'supervisor' ? 'No supervisor' : 'Not assigned')
          : task[key],
      avatarLabel: task[key + 'Login']
        ? task[key]
        : key === 'supervisor'
          ? 'No supervisor'
          : 'Not assigned',
      avatar: true
    };
  if (key === 'priority')
    return {
      text: task.priority
        ? task.priorityLabel || String(task.priority)
        : t('No priority'),
      actionField: false,
      indicator: true,
      showAccent: true,
      accent: task.priorityColor || task.__priority__?.color || 'action'
    };
  return {
    text: task.milestone_code
      ? task.milestoneLabel || task.milestone_code
      : t('No milestone'),
    actionField: true
  };
});
const painted = computed(
  () => !['dates', 'progress', 'hours'].includes(props.column.key)
);
</script>
<template>
  <span class="task-row-value" :data-task-cell="source">
    <AppButton
      class="task-cell-value"
      :class="{ 'task-cell-input': !painted }"
      :disabled="blocked || task.deleting || !editable"
      :aria-label="
        t('Edit {column}', { column: t(column.label) }) + ': ' + task.title
      "
      @click="emit('edit', $event)"
    >
      <TaskCellDisplay
        v-if="painted"
        :user="task[source + 'User']"
        :model="{
          ...model,
          enabled: !blocked && !task.deleting && editable,
          actionField: model.actionField !== false
        }"
      />
    </AppButton>
  </span>
</template>
<style>
.task-row-value {
  display: block;
  width: 100%;
  height: 100%;
}
.task-row-value > .task-cell-value {
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: var(--item-radius);
  font-weight: 400;
}
.task-row-value
  > button.task-cell-value:is(:hover, :focus-visible, :active):not(:disabled),
.task-row-value > button.task-cell-value:disabled {
  background: transparent;
}
.task-cell-value:focus-visible
  .task-cell-display
  [data-frame='taskTableCellSurface'] {
  box-shadow: inset 0 0 0 1px var(--primary);
}
.task-row-value > .task-cell-input {
  opacity: 0;
}
</style>
