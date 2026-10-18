<script setup>
import { computed, ref, markRaw, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppButton from '../../controls/AppButton.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import UserComboBox from '../../controls/UserComboBox.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/process.ui.mjs';
const props = defineProps({ record: Object, mode: String, blocked: Boolean });
const emit = defineEmits([
  'change',
  'save',
  'discard',
  'inspect',
  'add',
  'edit',
  'delete',
  'select'
]);
const host = ref(null),
  width = ref(0),
  menu = ref(null),
  anchor = ref(null);
const scene = computed(() =>
  UI.describe(
    {
      label: props.record.label,
      count: props.record.choices.length,
      color: props.record.color,
      hasTask: !!props.record.plan.task_key,
      dirty: props.record.dirty,
      notes: props.record.notes,
      blocked: props.blocked,
      deleting: props.record.deleting,
      hasTarget: true
    },
    width.value,
    props.mode,
    appearance.language
  )
);
const editable = (name) =>
  !props.blocked &&
  !props.record.deleting &&
  props.record.plan.fields.some(
    (field) => field.name === name && field.editable
  );
const statusPort = markRaw({
  setup(_, { attrs }) {
    return () =>
      h(StatusSelect, {
        ...attrs,
        value: props.record.values.status || '',
        options: props.record.statuses,
        disabled: !editable('status'),
        onChange: (value) => emit('change', 'status', value)
      });
  }
});
const userPort = markRaw({
  setup(_, { attrs }) {
    return () =>
      h(UserComboBox, {
        ...attrs,
        value: props.record.values.assigned || '',
        options: props.record.users,
        disabled: !editable('assigned'),
        onChange: (value) => emit('change', 'assigned', value)
      });
  }
});
const views = {
  status: { component: statusPort },
  assigned: { component: userPort }
};
function event(action, source) {
  if (action.type === 'menu') {
    anchor.value = source;
    if (menu.value.open) menu.value.close();
    else {
      const box = source.getBoundingClientRect();
      menu.value.openAt({
        clientX: box.left,
        clientY: box.bottom + 6,
        target: source
      });
    }
  } else emit(action.type === 'notes' ? 'inspect' : action.type);
}
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
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
    class="task-process-item"
    :class="{ dirty: record.dirty, missing: !record.plan.task_key }"
    :data-process="record.value"
    :data-task-key="record.key"
    :style="{
      height: scene.height + 'px',
      minWidth: mode === 'compact' ? UI.minimumWidth(record) + 'px' : undefined
    }"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
    <AppMenu
      ref="menu"
      :anchor="anchor"
      external-trigger
      label="Task actions"
      overlay
      :disabled="blocked"
    >
      <AppButton
        label="Add task"
        icon="add"
        :disabled="blocked"
        @click="emit('add')"
      />
      <AppButton
        v-if="record.plan.task_key"
        label="Edit task"
        icon="edit"
        :disabled="blocked || record.deleting"
        @click="emit('edit')"
      />
      <AppButton
        v-if="record.plan.task_key"
        label="Delete task"
        icon="delete"
        destructive
        :disabled="blocked || record.dirty"
        @click="emit('delete')"
      />
      <template v-if="record.choices.length > 1"
        ><hr />
        <strong>{{ t('Tasks') }}</strong>
        <AppButton
          v-for="choice in record.choices"
          :key="choice.key"
          :label="choice.label"
          :translate-label="false"
          :aria-pressed="record.key === choice.key"
          :icon="record.key === choice.key ? 'check' : undefined"
          @click="emit('select', choice.key)"
        />
      </template>
    </AppMenu>
  </div>
</template>
<style>
.task-process-item {
  position: relative;
  min-width: 0;
}
.task-process-item > .workspace-menu {
  position: absolute;
  width: 0;
  height: 0;
}
</style>
