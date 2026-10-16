<script setup>
import { computed, markRaw, nextTick, ref } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import ControlsExample from './ControlsExample.vue';
import * as BaseCatalog from '../../src/tactic_stream/shared_ui/controls/catalog.ui.mjs';
import * as Variants from '../../src/tactic_stream/shared_ui/controls/catalog/variants.mjs';
import { appearance } from '../../frontend/src/appearance.js';

const model = ref(Variants.initial('button'));
const status = ref('idle');
const generation = ref(0);
const size = ref({ width: 360, height: 520 });
const example = computed(() => Variants.find(model.value.id));
const models = computed(() => ({
  cells: Array.from({ length: 50 }, () => [{}, {}, {}]),
  treeRows: BaseCatalog.treeRows(model.value)
}));
const scene = computed(() =>
  Variants.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language,
    status.value
  )
);
function event(action) {
  model.value = Variants.transition(model.value, action);
  window.dispatchEvent(
    new CustomEvent('control-variant-event', { detail: model.value })
  );
}
const views = computed(() => ({
  example: {
    component: markRaw(ControlsExample),
    props: {
      example: example.value,
      value: model.value.value,
      disabled: ['disabled', 'loading'].includes(status.value),
      readonly: status.value === 'readonly',
      onEvent: event
    }
  }
}));
window.controlVariants = {
  examples: Variants.examples,
  async configure(options) {
    generation.value++;
    model.value = Variants.initial(options.id);
    status.value = options.state || 'idle';
    size.value = { width: options.width || 360, height: options.height || 520 };
    Object.assign(appearance, {
      theme: options.style || 'md3',
      mode: options.mode || 'dark',
      language: options.language || 'en'
    });
    await nextTick();
  },
  setState(state) {
    status.value = state;
  },
  setAppearance(options) {
    Object.assign(appearance, options);
  },
  resize(width, height = 520) {
    size.value = { width, height };
  },
  get model() {
    return model.value;
  },
  get scene() {
    return scene.value;
  }
};
</script>

<template>
  <FrameView
    :key="generation"
    :scene="scene"
    :views="views"
    :models="models"
    :describe-row="
      (list, record) =>
        Variants.row(list, record, model, appearance.language, status)
    "
    :describe-cell="
      (grid, record, row, column) =>
        Variants.cell(grid, record, row, column, model, status)
    "
    @event="event"
  />
</template>
