<script setup>
import { computed, ref, markRaw } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppButton from '../../controls/AppButton.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import TaskRowValue from './TaskRowValue.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/table.ui.mjs';
const props = defineProps({
  task: Object,
  geometry: Object,
  active: Boolean,
  checked: Boolean,
  expanded: Boolean,
  busy: Boolean,
  blocked: Boolean,
  hours: Number
});
const emit = defineEmits([
  'expand',
  'select',
  'inspect',
  'operate',
  'edit-cell',
  'activate',
  'key',
  'context',
  'object'
]);
const hovered = ref(false);
let checkboxModifiers = {};
const modifiers = (event) => ({
  shiftKey: event.shiftKey,
  ctrlKey: event.ctrlKey,
  metaKey: event.metaKey
});
const segments = computed(() => UI.segments(props.geometry, props.expanded));
function activate(event) {
  if (!event.target.closest('button, input, select, textarea, label, a'))
    emit('activate', modifiers(event));
}
function capture(event) {
  if (event.target.tagName === 'INPUT') checkboxModifiers = modifiers(event);
}
function editCell(column, event) {
  const keys = modifiers(event);
  emit('activate', keys);
  if (!keys.shiftKey && !keys.ctrlKey && !keys.metaKey)
    emit(
      'edit-cell',
      { ...column, key: column.sourceKey },
      Object.assign(event.currentTarget.getBoundingClientRect(), {
        anchor: event.currentTarget
      })
    );
}
const initials = computed(() =>
  props.task.title
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
);
const scene = computed(() => {
  const task = props.task,
    progress = Number(task.progress ?? task.completion) || 0;
  const hours = (value) => Number(value || 0).toFixed(1);
  return UI.row(
    {
      code: task.key,
      title: task.title,
      process: task.process,
      processLabel: task.__process__?.label || task.process,
      context: task.context,
      processColor: task.__process__?.color,
      creating: !!task.__draft__,
      active: props.active,
      checked: props.checked,
      expanded: props.expanded,
      hovered: hovered.value,
      dirty: task.pending,
      actionAlert: !!task.conflict || !!task.error,
      busy: props.busy || task.deleting || !task.parent,
      start: task.bid_start_date,
      end: task.bid_end_date,
      overdue:
        !!task.bid_end_date &&
        task.bid_end_date.slice(0, 10) <
          new Date().toLocaleDateString('en-CA') &&
        progress < 100,
      progress,
      hoursLabel:
        hours(task.__hours__?.approved) + ' / ' + hours(props.hours) + ' h',
      overPlan: task.__hours__?.approved > props.hours,
      pendingHours: task.__hours__?.pending > 0,
      notes: task.notes,
      hasTask: !!task.__search_key__,
      editableCells: true
    },
    props.geometry,
    appearance.language
  );
});
const valuePort = markRaw(TaskRowValue),
  previewPort = markRaw(ItemPreview),
  actionPort = markRaw(AppButton);
const views = computed(() => ({
  preview: {
    component: previewPort,
    props: {
      source: props.task.parent?.__preview__?.image,
      fallbackText: initials.value,
      previewSize: 34,
      round: false,
      outlined: false,
      accent: props.task.__process__?.color
    }
  },
  actions: {
    component: actionPort,
    props: {
      label: 'Task actions',
      icon: 'more',
      iconOnly: true,
      disabled: props.busy,
      onClick: (event) =>
        emit('operate', event.currentTarget.getBoundingClientRect())
    }
  },
  ...Object.fromEntries(
    props.geometry.cells
      .filter((cell) => !['object', 'notes'].includes(cell.key))
      .map((column) => [
        column.key,
        {
          component: valuePort,
          props: {
            task: props.task,
            column,
            blocked: props.blocked,
            onEdit: (event) => editCell(column, event)
          }
        }
      ])
  )
}));
function event(action) {
  if (action.type === 'notes') emit('inspect');
  else if (action.type === 'expand') emit('expand');
  else if (action.type === 'select') {
    emit('select', action.value, checkboxModifiers);
    checkboxModifiers = {};
  }
}
</script>
<template>
  <tr
    :data-task-key="task.key"
    :tabindex="active ? 0 : -1"
    :class="{
      pending: task.pending,
      'task-active': active,
      'task-selected': checked,
      'task-deleted': task.deleting,
      'task-row-expanded': expanded
    }"
    @click="activate"
    @click.capture="capture"
    @dblclick="
      !$event.target.closest('button, input, select, textarea, label, a') &&
      emit('object')
    "
    @contextmenu.prevent="
      emit('operate', $event.currentTarget.getBoundingClientRect())
    "
    @pointerenter="hovered = true"
    @pointerleave="hovered = false"
  >
    <td
      v-for="segment in segments"
      :key="segment.key"
      :data-task-cell="segment.sourceKey"
      :class="{ 'task-row-controls': segment.key === 'leading' }"
      :colspan="segment.colspan || 1"
    >
      <div class="task-workspace-row" :style="{ height: scene.height + 'px' }">
        <FrameView
          :scene="UI.slice(scene, segment)"
          :views="views"
          @event="event"
        />
      </div>
    </td>
  </tr>
</template>
<style>
.task-workspace-row {
  position: relative;
  width: 100%;
}
</style>
