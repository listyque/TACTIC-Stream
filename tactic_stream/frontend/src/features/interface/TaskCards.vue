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
  expanded: Boolean,
  height: { type: Number, default: 58 }
});
const layout = computed(() =>
  Cells.taskCardLayout(props.height, props.expanded, appearance.theme)
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
      '--task-editor-height': layout.editorHeight + 'px',
      '--task-card-width':
        (expanded ? Cells.metrics.taskPreviewWidth : Cells.metrics.taskWidth) +
        'px',
      '--task-heading-height': layout.headingHeight + 'px',
      '--task-dates-height': layout.datesHeight + 'px'
    }"
  >
    <article
      v-for="task in tasks"
      :key="task.taskSearchKey || task.process"
      class="task-card"
      :class="{ pending: task.pending, expanded }"
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
            fontRole: expanded ? 'body' : 'caption'
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
            fontRole: expanded ? 'body' : 'caption'
          }"
      /></AppButton>
      <AppButton
        v-if="layout.dates"
        class="task-card-dates"
        label="Edit task dates"
        icon="calendar"
        :disabled="!Cells.taskEditable(task, 'bid_start_date', editable)"
        @click="edit(task, 'bid_start_date', $event)"
        ><span>{{ Cells.taskDateRange(task) }}</span></AppButton
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
  width: var(--task-card-width);
  flex: 0 0 var(--task-card-width);
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
  flex: 0 0 var(--task-heading-height);
  height: var(--task-heading-height);
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
  flex: 0 0 var(--task-dates-height);
  height: var(--task-dates-height);
  padding: 0 7px;
  gap: 4px;
  color: var(--muted);
}
.task-cards .task-card-dates .app-icon {
  width: 11px;
  height: 11px;
  font-size: 11px;
}
.task-cards .task-card.expanded {
  padding: calc(var(--space-compact) - 1px);
  gap: var(--space-tight);
}
.task-cards .task-card.expanded .app-button {
  font-size: var(--font-body-size);
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
