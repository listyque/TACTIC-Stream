<script setup>
// TaskInspector.qml contextHeader: 46px, 32px preview, process and task menus.
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import { mobile } from '../../mobile.js';
import UserIdentity from '../../controls/UserIdentity.vue';
import { t } from '../../i18n.js';
const props = defineProps({
  editor: Object,
  process: String,
  expanded: Boolean,
  busy: Boolean,
  editing: Boolean
});
const emit = defineEmits([
  'back',
  'help',
  'toggle',
  'preview',
  'process',
  'task',
  'refresh',
  'edit',
  'create',
  'action',
  'log',
  'timesheet'
]);
const selected = computed(() =>
  props.editor.processes.find((row) => row.value === props.process)
);
const title = computed(
  () =>
    props.editor.object.record.name ||
    props.editor.object.record.title ||
    props.editor.object.record.code ||
    String(props.editor.object.record.id)
);
const initials = computed(() =>
  title.value
    .trim()
    .split(/\s+|_+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
);
const host = ref(null),
  width = ref(0),
  anchors = ref({}),
  processMenu = ref(null),
  taskMenu = ref(null),
  actionsMenu = ref(null);
let observer;
const scene = computed(() =>
  UI.context(
    {
      title: title.value,
      typeTitle:
        props.editor.object.type_title || props.editor.object.search_type,
      previewUrl: props.editor.object.preview.image,
      initials: initials.value,
      expanded: props.expanded,
      taskCount: props.editor.task_choices.length,
      process: props.process,
      processLabel: selected.value?.label || props.process,
      processColor: selected.value?.color,
      isProgress: selected.value?.type === 'progress',
      busy: props.busy,
      phone: mobile.value,
      hasActions: mobile.value || props.editor.process_type !== 'progress'
    },
    width.value,
    appearance.language
  )
);
function event(action, source) {
  const menu =
    action.type === 'process-menu'
      ? processMenu
      : action.type === 'task-menu'
        ? taskMenu
        : action.type === 'task-actions'
          ? actionsMenu
          : null;
  if (menu) {
    anchors.value[action.type] = source;
    if (menu.value.open) {
      menu.value.close();
      return;
    }
    const box = source.getBoundingClientRect();
    menu.value.openAt({
      clientX: box.left,
      clientY: box.bottom + 6,
      target: source
    });
  } else emit(action.type);
}
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="inspector-context inspector-object"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="event" />
    <AppMenu
      external-trigger
      ref="processMenu"
      :anchor="anchors['process-menu']"
      class="inspector-process"
      label="Process"
      overlay
      :width="320"
      :aria-disabled="busy"
      @pointerdown.capture="busy && $event.preventDefault()"
      @keydown.capture="busy && $event.preventDefault()"
    >
      <strong class="inspector-menu-heading">{{
        t('Process and note context')
      }}</strong>
      <AppButton
        v-for="row in editor.processes"
        :key="row.value"
        :data-process-choice="row.value"
        :translate-label="false"
        :label="row.label"
        role="menuitemradio"
        :aria-checked="row.value === process"
        :disabled="busy"
        @click="emit('process', row.value)"
      >
        <span
          class="inspector-process-dot"
          :style="{ background: row.color || 'var(--primary)' }"
        ></span
        ><span class="inspector-choice-copy"
          ><strong>{{ row.label }}</strong
          ><small
            >{{
              row.type === 'progress'
                ? t('Related tasks')
                : row.type === 'built-in'
                  ? t('Built-in')
                  : row.type
            }}
            ·
            {{
              row.type === 'progress'
                ? (row.approved || 0) + ' / ' + (row.total || 0)
                : t('{count} notes', { count: row.count || 0 })
            }}</small
          ></span
        ><AppIcon v-if="row.value === process" name="check-circle" />
      </AppButton>
    </AppMenu>
    <AppMenu
      external-trigger
      ref="taskMenu"
      :anchor="anchors['task-menu']"
      v-if="editor.task_choices.length > 1"
      class="inspector-task-picker"
      label="Task"
      icon="MDI_SWAP_HORIZONTAL"
      overlay
      :width="330"
      :aria-disabled="busy"
      @pointerdown.capture="busy && $event.preventDefault()"
      @keydown.capture="busy && $event.preventDefault()"
    >
      <strong class="inspector-menu-heading">{{
        t('Tasks for this process')
      }}</strong>
      <AppButton
        v-for="row in editor.task_choices"
        :key="row.value"
        :data-task-choice="row.value"
        :translate-label="false"
        :label="row.label"
        role="menuitemradio"
        :aria-checked="row.value === editor.selected_task"
        :disabled="busy"
        @click="emit('task', row.value)"
        ><UserIdentity v-if="row.identity" v-bind="row.identity" /><span
          class="inspector-choice-copy"
          ><strong
            >{{ row.label
            }}<template v-if="row.primary"> · {{ t('Main') }}</template></strong
          ><small
            >{{ row.status }} ·
            {{ t('{count} notes', { count: row.count || 0 }) }}</small
          ></span
        ><AppIcon v-if="row.value === editor.selected_task" name="check-circle"
      /></AppButton>
    </AppMenu>
    <AppMenu
      external-trigger
      ref="actionsMenu"
      :anchor="anchors['task-actions']"
      v-if="mobile || editor.process_type !== 'progress'"
      class="inspector-task-actions"
      label="Task actions"
      overlay
    >
      <template v-if="mobile"
        ><AppButton
          :label="
            expanded ? 'Collapse Task Inspector' : 'Expand Task Inspector'
          "
          icon="MDI_CHEVRON_DOWN"
          :disabled="busy"
          @click="emit('toggle')" /><AppButton
          label="Refresh"
          icon="refresh"
          :disabled="busy"
          @click="emit('refresh')" /><template v-if="editor.work_hours"
          ><AppButton
            label="Log time"
            icon="MDI_ALARM_PLUS"
            :disabled="busy"
            @click="emit('log')" /><AppButton
            label="Open timesheet"
            icon="MDI_CALENDAR_MONTH"
            :disabled="busy"
            @click="emit('timesheet')"
        /></template>
        <hr
      /></template>
      <template v-if="editor.process_type !== 'progress'">
        <AppButton
          label="Edit task"
          icon="edit"
          :disabled="busy || editing"
          @click="emit('edit')"
        />
        <AppButton
          v-if="editor.selected_task"
          label="Add task assignee"
          icon="copy"
          :disabled="busy || editing"
          @click="emit('action', 'copy')"
        />
        <AppButton
          v-if="editor.selected_task"
          label="Delete task"
          icon="delete"
          destructive
          :disabled="busy || editing"
          @click="emit('action', 'delete')"
        />
        <AppButton
          v-else
          label="Create task"
          icon="add"
          :disabled="busy"
          @click="emit('create')"
        />
      </template>
    </AppMenu>
  </div>
</template>
<style>
.inspector-context.inspector-context {
  position: relative;
  display: block;
  min-width: 0;
  flex: none;
  padding: 0;
  margin: 0;
}
.inspector-context > .app-menu[open] {
  z-index: 10;
}
.inspector-process-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 50%;
}
.inspector-choice-copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 2px;
  text-align: left;
}
.inspector-choice-copy strong,
.inspector-choice-copy small {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.inspector-choice-copy small,
.inspector-menu-heading {
  color: var(--muted);
  font-size: var(--text-caption);
}
.inspector-menu-heading {
  display: block;
  padding: 6px 10px;
}
</style>
