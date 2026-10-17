<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance, accentPresets } from '../../appearance.js';
import AccentPresetPicker from '../../controls/AccentPresetPicker.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/settings.ui.mjs';

const props = defineProps({
  page: String,
  values: Object,
  options: Object,
  busy: Boolean,
  fields: Array,
  natural: Boolean
});
const emit = defineEmits(['field', 'action', 'columns']);
const host = ref(null),
  viewport = ref({ width: 800, height: 600 });
const model = computed(() => ({
  values: props.values,
  options: props.options,
  busy: props.busy,
  style: appearance.theme,
  native: false,
  columns: props.page === 'tasks' ? props.values.columns : []
}));
const fields = computed(
  () => props.fields || UI.fieldsFor(props.page, model.value)
);
const scene = computed(() => {
  const result = UI.describe(
    { ...model.value, fields: fields.value },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  );
  if (props.natural) result.nodes[0].height = result.nodes[0].contentHeight;
  return result;
});
const height = computed(() =>
  props.natural ? scene.value.nodes[0].contentHeight + 'px' : '100%'
);
const views = computed(() =>
  Object.fromEntries(
    ['light', 'dark'].map((mode) => [
      mode + 'Accent',
      {
        component: AccentPresetPicker,
        props: {
          options: accentPresets,
          mode,
          label: mode === 'light' ? 'Light mode palette' : 'Dark mode palette',
          disabled: props.busy,
          modelValue: props.values[mode + 'Accent'],
          'onUpdate:modelValue': (value) =>
            emit('field', { field: mode + 'Accent', value })
        }
      }
    ])
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'field' || action.type === 'step') {
    const next = UI.change(props.values, action, fields.value);
    emit('field', { field: action.field, value: next[action.field] });
  } else if (action.type.startsWith('column'))
    emit('columns', UI.editColumn(props.values.columns || [], action));
  else emit('action', action);
}
</script>
<template>
  <div
    ref="host"
    class="frame-settings"
    :class="{ 'frame-settings-natural': natural }"
    :style="{ height }"
  >
    <FrameView :scene="scene" :views="views" @event="dispatch" />
  </div>
</template>
<style>
.frame-settings {
  position: relative;
  min-height: 0;
  width: 100%;
  box-sizing: border-box;
}
.frame-settings > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
