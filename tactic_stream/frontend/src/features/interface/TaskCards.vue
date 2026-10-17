<script setup>
import { computed } from 'vue';
import * as Cells from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
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
function date(value) {
  return value ? String(value).slice(0, 10) : '—';
}
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
        class="task-card-status"
        label="Edit task status"
        :disabled="!editable || task.processType === 'progress'"
        @click="edit(task, 'status', $event)"
        ><i aria-hidden="true" />
        <span>{{ task.status || t('Select status') }}</span></AppButton
      >
      <AppButton
        class="task-card-assignee"
        label="Edit task assignee"
        :disabled="!editable || task.processType === 'progress'"
        @click="edit(task, 'assigned', $event)"
      >
        <ItemPreview
          :source="task.assignedIdentity?.avatarUrl"
          :fallback-text="task.assignedIdentity?.initials"
          fallback-icon="person"
          :accent="task.assignedIdentity?.avatarColor"
          :preview-size="Math.max(0, Math.min(22, layout.editorHeight - 4))"
          round
          outlined
        />
        <span>{{ Cells.assigneeLabel(task, appearance.language) }}</span>
      </AppButton>
      <AppButton
        v-if="layout.dates"
        class="task-card-dates"
        label="Edit task dates"
        icon="calendar"
        :disabled="!editable || task.processType === 'progress'"
        @click="edit(task, 'bid_start_date', $event)"
        ><span
          >{{ date(task.bidStart) }} – {{ date(task.bidEnd) }}</span
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
.task-cards .task-card :is(.task-card-status, .task-card-assignee) {
  background: var(--surface);
}
.task-cards .task-card-status i {
  width: 9px;
  height: 9px;
  flex: 0 0 9px;
  border-radius: 50%;
  background: var(--task-accent);
}
.task-cards .task-card .item-preview {
  width: min(22px, calc(var(--task-editor-height) - 4px));
  height: min(22px, calc(var(--task-editor-height) - 4px));
  flex: 0 0 min(22px, calc(var(--task-editor-height) - 4px));
  font-size: 8px;
}
.task-cards .task-card .task-card-assignee > .app-icon {
  font-size: 12px;
}
.task-cards .task-card .task-card-dates {
  flex: 0 0 14px;
  height: 14px;
  color: var(--muted);
}
.task-cards .task-card-dates .app-icon {
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
