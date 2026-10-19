<script setup>
import { computed } from 'vue';
import * as Cells from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import TaskCellDisplay from '../tasks/TaskCellDisplay.vue';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';

const props = defineProps({
  tasks: Array,
  editable: Boolean,
  height: { type: Number, default: 58 }
});
const layout = computed(() =>
  Cells.taskLayout(props.tasks?.length || 0, 0, props.height)
);
const emit = defineEmits(['inspect', 'edit']);
function edit(task, field, event) {
  const anchor = event.currentTarget;
  emit('edit', task, field, {
    ...anchor.getBoundingClientRect().toJSON(),
    anchor
  });
}
</script>

<template>
  <div
    class="task-cards"
    :style="{
      '--task-card-height': layout.cardHeight + 'px',
      '--task-editor-height': layout.editorHeight + 'px'
    }"
  >
    <article
      v-for="task in tasks"
      :key="task.taskSearchKey || task.process"
      class="task-card"
      :class="{ pending: task.pending }"
      :style="{
        '--task-accent':
          task.statusColor || task.processColor || 'var(--primary)'
      }"
    >
      <AppButton
        class="task-card-heading"
        label="Task Inspector"
        :icon="task.processType === 'progress' ? 'MDI_CHART_DONUT' : undefined"
        @click="emit('inspect', task)"
        >{{ task.processLabel || task.process || task.context }}</AppButton
      >
      <AppButton
        class="task-card-status frame-hit-target"
        label="Edit task status"
        :disabled="!Cells.taskEditable(task, 'status', editable)"
        @click="edit(task, 'status', $event)"
        ><TaskCellDisplay
          :height="layout.editorHeight"
          :model="{
            text: task.status || t('Select status'),
            enabled: Cells.taskEditable(task, 'status', editable),
            actionField: true,
            showAccent: true,
            accent: task.statusColor || task.processColor || 'action',
            fontRole: 'caption'
          }"
      /></AppButton>
      <AppButton
        class="task-card-assignee frame-hit-target"
        label="Edit task assignee"
        :disabled="!Cells.taskEditable(task, 'assigned', editable)"
        @click="edit(task, 'assigned', $event)"
        ><TaskCellDisplay
          :height="layout.editorHeight"
          :user="task.assignedIdentity"
          :model="{
            text: Cells.assigneeLabel(task, appearance.language),
            enabled: Cells.taskEditable(task, 'assigned', editable),
            actionField: true,
            avatar: true,
            avatarLabel: task.assigned
              ? Cells.assigneeLabel(task, appearance.language)
              : '',
            fontRole: 'caption'
          }"
      /></AppButton>
      <AppButton
        v-if="layout.dates"
        class="task-card-dates"
        label="Edit task dates"
        icon="calendar"
        :disabled="!Cells.taskEditable(task, 'bid_start_date', editable)"
        @click="edit(task, 'bid_start_date', $event)"
        ><span
          >{{ Cells.taskDate(task.bidStart, task.simpleDates) }} –
          {{ Cells.taskDate(task.bidEnd, task.simpleDates) }}</span
        ></AppButton
      >
    </article>
  </div>
</template>

<style>
.task-cards {
  gap: 4px;
  height: 100%;
  align-items: center;
}
.task-cards .task-card {
  width: 107px;
  flex: 0 0 107px;
  height: var(--task-card-height);
  padding: 1px 1px 1px 5px;
  gap: 1px;
  position: relative;
  border-left-width: 1px;
  overflow: visible;
}

.task-cards .task-card::before {
  content: '';
  position: absolute;
  left: -1px;
  top: -1px;
  bottom: -1px;
  width: 3px;
  border-radius: 1.5px;
  background: var(--task-accent);
}
.task-cards .task-card .app-button {
  font-size: var(--text-caption);
  min-height: 0;
  height: var(--task-editor-height);
  flex-shrink: 0;
  padding: 0 12px 0 11px;
  gap: 7px;
  border-radius: var(--field-radius);
  justify-content: flex-start;
  color: var(--on-surface);
}
.task-cards .task-card .task-card-heading {
  flex: 0 0 15px;
  height: 15px;
  justify-content: center;
  font-weight: 600;
  text-transform: uppercase;
  padding: 0;
  background: transparent;
}
.task-cards .task-card .app-button.frame-hit-target {
  padding: 0;
  gap: 0;
}
.task-cards .task-card .task-card-dates {
  flex: 0 0 14px;
  height: 14px;
  padding: 0 7px;
  gap: 4px;
  color: var(--muted);
}
.task-cards .task-card-dates .app-icon {
  width: 11px;
  height: 11px;
  font-size: 11px;
}
.handler-table-cell .table-task-cell {
  gap: 0;
}
.handler-table-cell .table-task-cell .task-preview-trigger {
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  margin: auto;
  flex-direction: row;
}
</style>
