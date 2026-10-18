<script setup>
// Handler TaskBrowserTable/TaskHiddenDetails: presentation only, EPL-1.0.
// TaskManager owns the native plans, selection, column preferences and drafts.
import { computed, markRaw, onBeforeUnmount, onMounted, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import TaskHiddenDetails from './TaskHiddenDetails.vue';
import TaskWorkspaceRow from './TaskWorkspaceRow.vue';
import TaskTableHeaderInput from './TaskTableHeaderInput.vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/table.ui.mjs';
const props = defineProps({
  groups: Array,
  columns: Array,
  selected: Array,
  collapsed: Array,
  busy: Boolean,
  blocked: Boolean,
  allSelected: Boolean,
  active: String,
  expanded: Array,
  editors: Object
});
const emit = defineEmits([
  'select',
  'select-all',
  'collapse',
  'sort',
  'inspect',
  'object',
  'operate',
  'activate',
  'key',
  'expand',
  'change',
  'edit-cell',
  'milestones',
  'size-column',
  'columns',
  'column-context'
]);
const table = ref(null),
  resizing = ref(null);
const width = ref(0);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    width.value = entries[0].contentRect.width;
  });
  observer.observe(table.value.parentElement);
});
onBeforeUnmount(() => observer?.disconnect());
const geometry = computed(() =>
  UI.layout(
    props.columns.map((column) =>
      resizing.value?.key === column.key
        ? { ...column, width: resizing.value.preview }
        : column
    ),
    width.value
  )
);
const tableWidth = computed(() => geometry.value.width);
const modifiers = (event) => ({
  shiftKey: event.shiftKey,
  ctrlKey: event.ctrlKey,
  metaKey: event.metaKey
});
const plannedHours = (task) =>
  task.pending
    ? Number(task.bid_duration || 0) /
      (props.editors[task.key]?.catalog.bidDurationUnit === 'minute' ? 60 : 1)
    : task.__hours__?.planned || Number(task.bid_duration || 0);
function keyboard(event) {
  if (event.key === 'Escape' && resizing.value) {
    resizing.value = null;
    event.preventDefault();
    return;
  }
  if (
    event.target.closest(
      'input, textarea, select, button, [contenteditable="true"]'
    ) ||
    !['ArrowDown', 'ArrowUp', 'Home', 'End', ' ', 'a'].includes(event.key) ||
    (event.key === 'a' && !(event.ctrlKey || event.metaKey))
  )
    return;
  event.preventDefault();
  emit('key', event.key, modifiers(event));
}
function resize(column, event) {
  if (event.pointerType !== 'mouse' || event.button !== 0) return;
  event.preventDefault();
  event.stopPropagation();
  event.currentTarget.setPointerCapture(event.pointerId);
  resizing.value = {
    key: column.sourceKey,
    width: column.width,
    preview: column.width,
    x: event.clientX,
    id: event.pointerId
  };
}
function move(event) {
  if (resizing.value?.id === event.pointerId)
    resizing.value.preview = Math.max(
      40,
      Math.min(480, resizing.value.width + event.clientX - resizing.value.x)
    );
}
function finishResize(event) {
  const current = resizing.value;
  if (!current || current.id !== event.pointerId) return;
  resizing.value = null;
  if (event.type === 'pointerup')
    emit('size-column', current.key, current.preview);
}
function resizeKey(column, event) {
  if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
    event.preventDefault();
    event.stopPropagation();
    emit(
      'size-column',
      column.sourceKey,
      column.width + (event.key === 'ArrowRight' ? 10 : -10)
    );
  }
}
function focusRow(key) {
  const row = [...table.value.querySelectorAll('[data-task-key]')].find(
    (row) => row.dataset.taskKey === key
  );
  row?.focus({ preventScroll: true });
  row?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}
const headerScene = computed(() =>
  UI.header(
    {
      allSelected: props.allSelected,
      someSelected: !!props.selected.length,
      busy: props.busy
    },
    geometry.value,
    appearance.language
  )
);
const headerSegments = computed(() => UI.segments(geometry.value, false));
const headerPort = markRaw(TaskTableHeaderInput);
const headerViews = computed(() =>
  Object.fromEntries(
    geometry.value.cells.map((column) => [
      'header_' + column.key,
      {
        component: headerPort,
        nodeProps: true,
        props: {
          busy: props.busy,
          onSort: (value) => emit('sort', value),
          onContext: (cell, bounds) =>
            emit('column-context', { ...cell, key: cell.sourceKey }, bounds),
          onResize: resize,
          onMove: move,
          onFinish: finishResize,
          onResizeKey: resizeKey
        }
      }
    ])
  )
);
function headerEvent(action, source) {
  if (action.type === 'select-all') emit('select-all', action.value);
  else if (action.type === 'columns') emit('columns', source);
}
defineExpose({ focusRow });
</script>

<template>
  <div ref="table" class="task-workspace-surface" @keydown="keyboard">
    <table
      class="task-workspace-table"
      tabindex="0"
      :aria-label="t('Project task table')"
      :style="{ width: tableWidth + 'px' }"
    >
      <colgroup>
        <col
          v-for="segment in headerSegments"
          :key="segment.key"
          :style="{ width: segment.width + 'px' }"
        />
      </colgroup>
      <thead>
        <tr>
          <th
            v-for="segment in headerSegments"
            :key="segment.key"
            :data-task-column="segment.sourceKey"
            :aria-label="segment.label && t(segment.label)"
          >
            <div :style="{ height: headerScene.height + 'px' }">
              <FrameView
                :scene="UI.slice(headerScene, segment)"
                :views="headerViews"
                @event="headerEvent"
              />
            </div>
          </th>
        </tr>
      </thead>
      <tbody aria-hidden="true" class="task-header-gap">
        <tr>
          <td
            :colspan="headerSegments.length"
            :style="{ height: UI.metrics.headerGap + 'px' }"
          ></td>
        </tr>
      </tbody>
      <tbody v-for="group in groups" :key="group.key">
        <tr v-if="group.key" class="task-group">
          <th :colspan="headerSegments.length">
            <FrameView
              :scene="
                UI.group(
                  {
                    key: group.key,
                    label: group.label,
                    color: group.color,
                    count: group.tasks.length,
                    collapsed: collapsed.includes(group.key)
                  },
                  tableWidth
                )
              "
              @event="emit('collapse', group.key)"
            />
          </th>
        </tr>
        <template
          v-for="task in collapsed.includes(group.key) ? [] : group.tasks"
          :key="task.key"
        >
          <TaskWorkspaceRow
            :task="task"
            :geometry="geometry"
            :active="active === task.key"
            :checked="selected.includes(task.key)"
            :expanded="expanded.includes(task.key)"
            :busy="busy"
            :blocked="blocked"
            :hours="plannedHours(task)"
            @activate="emit('activate', task.key, $event)"
            @expand="emit('expand', task)"
            @select="(checked, keys) => emit('select', task.key, checked, keys)"
            @inspect="emit('inspect', task)"
            @object="emit('object', task)"
            @operate="emit('operate', task, $event)"
            @edit-cell="
              (column, bounds) => emit('edit-cell', task, column, bounds)
            "
          />
          <tr v-if="expanded.includes(task.key)" class="task-expanded-row">
            <td :colspan="headerSegments.length">
              <TaskHiddenDetails
                :aria-label="t('Task details') + ': ' + task.title"
                :editor="editors[task.key]"
                :columns="columns"
                :busy="blocked"
                @change="(name, value) => emit('change', task.key, name, value)"
                @milestones="emit('milestones')"
              />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
<style>
.task-workspace-surface {
  min-width: 0;
}
</style>
