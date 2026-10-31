<script setup>
import { computed, ref, markRaw, h, watch, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import TaskField from '../objects/TaskField.vue';
import AppButton from '../../controls/AppButton.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/editor.ui.mjs';
const props = defineProps({
  editor: Object,
  busy: Boolean,
  inline: Boolean,
  title: String,
  readOnly: Boolean,
  live: Boolean,
  staging: Boolean,
  immediate: Boolean
});
const emit = defineEmits([
  'change',
  'enable',
  'process',
  'apply',
  'cancel',
  'milestones'
]);
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  !props.editor
    ? { nodes: [], height: 0 }
    : UI.describe(
        {
          inline: props.inline,
          title: props.title,
          fields: props.editor.fields,
          bulk:
            props.live || (!props.immediate && props.editor.plans.length > 1),
          enabled: props.editor.enabled,
          busy: props.busy,
          readOnly: props.readOnly,
          live: props.live,
          staging: props.staging,
          immediate: props.immediate
        },
        width.value,
        appearance.language
      )
);
function event(action) {
  if (action.type === 'enable') emit('enable', action.field, action.value);
  else emit(action.type);
}
const port = markRaw({
  props: { frameNode: Object },
  setup(p) {
    return () =>
      h(
        'div',
        {
          'data-task-field': p.frameNode.field.name,
          class: 'task-editor-field-port'
        },
        [
          h(TaskField, {
            field: p.frameNode.field,
            value: props.editor.values[p.frameNode.field.name],
            statuses: props.editor.statuses,
            statusChoices: props.editor.statusChoices,
            users: props.editor.users,
            catalog: props.editor.catalog,
            busy: !p.frameNode.enabled,
            onChange: (value) =>
              emit(
                p.frameNode.field.name === 'process' && props.editor.creating
                  ? 'process'
                  : 'change',
                ...(p.frameNode.field.name === 'process' &&
                props.editor.creating
                  ? [value]
                  : [p.frameNode.field.name, value])
              )
          }),
          ...(p.frameNode.field.name === 'milestone_code'
            ? [
                h(AppButton, {
                  label: 'Project milestones',
                  icon: 'milestone',
                  iconOnly: true,
                  disabled: props.busy,
                  onClick: () => emit('milestones')
                })
              ]
            : [])
        ]
      );
  }
});
const views = { field: { component: port, nodeProps: true } };
let observer;
watch(
  host,
  (element) => {
    observer?.disconnect();
    if (!element) return;
    const measure = () => {
      width.value = frameContentWidth(element);
    };
    measure();
    observer = observeFrameSizes(measure);
    observer.observe(element);
  },
  { flush: 'post' }
);
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <form
    v-if="editor"
    ref="host"
    class="task-workspace-editor"
    :style="{ height: scene.height + 'px' }"
    @submit.prevent="!immediate && emit('apply')"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
  </form>
</template>
<style>
.task-workspace-editor {
  position: relative;
  width: 100%;
  min-width: 0;
}
.task-editor-field-port {
  display: flex;
  gap: 4px;
  min-width: 0;
  height: 100%;
}
.task-editor-field-port > :first-child {
  flex: 1;
  min-width: 0;
  height: 100%;
}
.task-editor-field-port textarea {
  resize: none;
}
.task-editor-field-port .app-select,
.task-editor-field-port input {
  width: 100%;
  height: 100%;
  min-height: 0;
}
</style>
