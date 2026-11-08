<script setup>
import { computed, ref, markRaw, h } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import TaskWorkspaceEditor from './TaskWorkspaceEditor.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import UserComboBox from '../../controls/UserComboBox.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/bulk.ui.mjs';
import { t } from '../../i18n.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { watch, onBeforeUnmount } from 'vue';
const props = defineProps({
  form: Object,
  count: Number,
  canDelete: { type: Boolean, default: true },
  busy: Boolean,
  blocked: Boolean
});
const emit = defineEmits([
  'change',
  'enable',
  'apply',
  'stage',
  'cancel',
  'delete'
]);
const host = ref(null),
  width = ref(0),
  menu = ref(null),
  anchor = ref(null);
const summary = computed(() => UI.preview(props.form));
const scene = computed(() =>
  UI.bar(
    {
      count: props.count,
      canDelete: props.canDelete,
      busy: props.busy || !props.form,
      blocked: props.blocked,
      enabled: props.form?.enabled || [],
      canApply:
        !props.busy &&
        !props.blocked &&
        !!summary.value.eligible &&
        !summary.value.invalid,
      invalid: summary.value.invalid,
      preview: props.blocked
        ? t('Save or discard row changes first')
        : !summary.value.fields
          ? ''
          : t('{count} ready', { count: summary.value.eligible }) +
            (summary.value.unchanged
              ? ' | ' +
                t('{count} unchanged', { count: summary.value.unchanged })
              : '') +
            (summary.value.invalid
              ? ' | ' + t('{count} invalid', { count: summary.value.invalid })
              : '')
    },
    width.value,
    appearance.language
  )
);
function event(action, source) {
  if (action.type === 'more') {
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
  } else if (action.type === 'enable')
    emit('enable', action.field, action.value);
  else emit(action.type);
}
const status = markRaw({
  setup() {
    return () =>
      h(StatusSelect, {
        value:
          props.form?.mixed.includes('status') &&
          !props.form.set.includes('status')
            ? ''
            : props.form?.values.status,
        options: props.form?.statusChoices || [],
        placeholder:
          props.form?.mixed.includes('status') &&
          !props.form.set.includes('status')
            ? t('Mixed status')
            : '',
        disabled: props.busy || !props.form?.enabled.includes('status'),
        onChange: (value) => emit('change', 'status', value)
      });
  }
});
const assigned = markRaw({
  setup() {
    return () =>
      h(UserComboBox, {
        value:
          props.form?.mixed.includes('assigned') &&
          !props.form.set.includes('assigned')
            ? ''
            : props.form?.values.assigned,
        options: props.form?.users || [],
        placeholder:
          props.form?.mixed.includes('assigned') &&
          !props.form.set.includes('assigned')
            ? t('Mixed assignee')
            : '',
        actionField: false,
        disabled: props.busy || !props.form?.enabled.includes('assigned'),
        onChange: (value) => emit('change', 'assigned', value)
      });
  }
});
const views = {
  status: { component: status },
  assigned: { component: assigned }
};
defineExpose({ closeFields: () => menu.value?.close() });
const moreEditor = computed(() =>
  props.form
    ? {
        ...props.form,
        fields: props.form.fields.filter(
          (field) =>
            width.value < 760 || !['status', 'assigned'].includes(field.name)
        )
      }
    : null
);
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
  <div
    ref="host"
    class="task-bulk-bar"
    role="region"
    :aria-label="t('Bulk task editing')"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
    <AppMenu
      class="task-bulk-more"
      ref="menu"
      :anchor="anchor"
      external-trigger
      overlay
      :width="540"
      :close-on-select="false"
      label="Edit selected tasks"
    >
      <TaskWorkspaceEditor
        role="group"
        :aria-label="t('Bulk fields')"
        v-if="moreEditor"
        :editor="moreEditor"
        :busy="busy"
        :read-only="blocked"
        live
        staging
        @change="(key, value) => emit('change', key, value)"
        @enable="(key, value) => emit('enable', key, value)"
        @cancel="menu.close()"
        @apply="emit('stage')"
      />
    </AppMenu>
  </div>
</template>
<style>
.task-bulk-bar {
  position: relative;
  width: calc(100% - 12px);
  margin-inline: 6px;
  height: 48px;
  flex: none;
}
</style>
