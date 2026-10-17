<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/inline.ui.mjs';
import { fieldKind } from '../objects/recordFields.js';
import { t } from '../../i18n.js';

const props = defineProps({
  editor: Object,
  busy: Boolean,
  error: String,
  uncertain: Boolean
});
const emit = defineEmits(['save', 'cancel', 'check']);
const panel = ref(null),
  frame = ref(null),
  value = ref(''),
  panelWidth = ref(300),
  inputHeight = ref(36);
const initialValue = ref('');
const kind = computed(() =>
  props.editor ? fieldKind(props.editor.field) : ''
);
const multiline = computed(
  () =>
    kind.value === 'TextAreaWdg' || props.editor?.field.name === 'description'
);
const mode = computed(() =>
  multiline.value
    ? 'multiline'
    : kind.value === 'SelectWdg' &&
        props.editor?.field.class_name ===
          'tactic.ui.input.process_group_select_wdg.ProcessGroupSelectWdg'
      ? 'user'
      : {
          SelectWdg: 'select',
          CheckboxWdg: 'bool',
          CalendarInputWdg:
            props.editor?.field.input?.type === 'datetime-local'
              ? 'datetime'
              : 'date',
          ColorInputWdg: 'color',
          MultiSelectWdg: 'multi',
          TimeInputWdg: 'time'
        }[kind.value] || 'text'
);
const scene = computed(() =>
  UI.describe(
    {
      mode: mode.value,
      title: props.editor?.field.title,
      value: value.value,
      options: props.editor ? choices.value : [],
      height: inputHeight.value,
      count: props.editor?.plans.length || 1,
      busy: props.busy,
      uncertain: props.uncertain,
      error: props.error ? t(props.error) : ''
    },
    panelWidth.value,
    appearance.language
  )
);
function dispatch(action) {
  if (action.type === 'value' || action.type === 'toggle') {
    value.value = UI.change(value.value, action);
    if (UI.savesOnChange(mode.value)) save();
  } else if (action.type === 'save') {
    if (action.value !== undefined) value.value = action.value;
    save();
  } else if (action.type === 'check') emit('check', value.value);
  else if (action.type === 'cancel')
    props.uncertain ? emit('cancel', true) : cancel();
}
const choices = computed(() => {
  const field = props.editor.field,
    options = (field.choices || []).map((value, index) => ({
      value,
      label: field.labels[index]
    }));
  return field.input?.empty_label != null
    ? [{ value: '', label: field.input.empty_label }, ...options]
    : options;
});
async function open(bounds) {
  const field = props.editor.field;
  value.value = [
    'CalendarInputWdg',
    'TimeInputWdg',
    'ColorInputWdg',
    'MultiSelectWdg'
  ].includes(fieldKind(field))
    ? (field.input?.value ?? field.values[0] ?? '')
    : (field.values[0] ?? '');
  if (fieldKind(field) === 'CheckboxWdg')
    value.value = [true, 1, '1', 'true', 'on'].includes(value.value);
  initialValue.value = JSON.stringify(value.value);
  await nextTick();
  panelWidth.value = Math.max(
    1,
    Math.min(
      innerWidth - 36,
      multiline.value
        ? 600
        : UI.explicitSave(mode.value)
          ? Math.max(280, bounds.width - 8)
          : bounds.width - 8
    )
  );
  inputHeight.value = Math.max(36, bounds.height - 8);
  panel.value.style.width = panelWidth.value + 'px';
  panel.value.style.setProperty('--inline-height', bounds.height - 8 + 'px');
  panel.value.showPopover();
  panel.value.style.left =
    Math.max(
      8,
      Math.min(
        bounds.left + (UI.explicitSave(mode.value) ? 0 : 4),
        innerWidth - panel.value.offsetWidth - 8
      )
    ) + 'px';
  panel.value.style.top =
    Math.max(
      8,
      Math.min(
        UI.explicitSave(mode.value) ? bounds.bottom + 4 : bounds.top + 4,
        innerHeight - panel.value.offsetHeight - 8
      )
    ) + 'px';
  await nextTick();
  frame.value.focusControl('tableInlineValue');
}
function close() {
  panel.value?.hidePopover();
}
function save() {
  if (!props.busy && !props.uncertain) {
    if (JSON.stringify(value.value) === initialValue.value) cancel();
    else emit('save', value.value);
  }
}
function cancel() {
  if (!props.busy && !props.uncertain) {
    close();
    emit('cancel');
  }
}
function toggle(event) {
  if (
    event.newState === 'closed' &&
    props.editor &&
    !props.busy &&
    !props.uncertain
  )
    emit('cancel');
}
function outside(event) {
  if (
    props.editor &&
    !UI.explicitSave(mode.value) &&
    !panel.value?.contains(event.target) &&
    !props.busy &&
    !props.uncertain
  )
    save();
}
function moved(event) {
  if (
    props.editor &&
    (!(event.target instanceof Node) || !panel.value?.contains(event.target)) &&
    !props.busy &&
    !props.uncertain
  )
    cancel();
}
onMounted(() => {
  window.addEventListener('pointerdown', outside, true);
  window.addEventListener('scroll', moved, true);
  window.addEventListener('resize', moved);
});
onBeforeUnmount(() => {
  close();
  window.removeEventListener('pointerdown', outside, true);
  window.removeEventListener('scroll', moved, true);
  window.removeEventListener('resize', moved);
});
defineExpose({ open, close });
</script>

<template>
  <Teleport to="body"
    ><div
      ref="panel"
      popover="manual"
      class="table-inline-editor"
      :class="{ 'in-cell': !UI.explicitSave(mode) }"
      role="dialog"
      :aria-label="editor?.field.title"
      @toggle="toggle"
      @keydown.esc.stop.prevent="cancel"
    >
      <FrameView
        v-if="editor"
        ref="frame"
        :scene="scene"
        :style="{ height: scene.height + 'px' }"
        @event="dispatch"
      /></div
  ></Teleport>
</template>

<style>
.table-inline-editor {
  position: fixed;
  inset: auto;
  margin: 0;
  padding: 10px;
  max-height: min(520px, calc(100dvh - 16px));
  overflow: auto;
  background: var(--surface-high);
  color: var(--on-surface);
  border: 1px solid var(--outline-variant);
  border-radius: var(--item-radius);
  box-shadow: 2px 6px 16px var(--shadow-color);
}
.table-inline-editor.in-cell {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  padding: 0;
  overflow: visible;
}
.table-inline-editor.in-cell:has([role='alert']) {
  background: var(--surface-high);
  padding: 8px;
  border-radius: var(--item-radius);
}
</style>
