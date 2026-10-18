<script setup>
import { computed, ref, onMounted, onBeforeUnmount, markRaw } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import ShelfScriptPicker from './ShelfScriptPicker.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/shelf.ui.mjs';

const props = defineProps({
  model: Object,
  buttons: Array,
  presets: Array,
  scripts: Array
});
const emit = defineEmits(['event']);
const host = ref(null),
  size = ref({ width: 0, height: 0 });
const scene = computed(() =>
  UI.describe(
    props.model,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
const models = computed(() => ({
  buttons: props.buttons,
  presets: props.presets
}));
const picker = markRaw(ShelfScriptPicker);
const views = computed(() => ({
  script: {
    component: picker,
    nodeProps: true,
    props: { scripts: props.scripts, onPick: (action) => emit('event', action) }
  }
}));
let observer;
onMounted(() => {
  const measure = () =>
    (size.value = {
      width: frameContentWidth(host.value),
      height: host.value.clientHeight
    });
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="script-shelf-editor"
    :aria-busy="model.busy || !!model.running"
  >
    <FrameView
      :scene="scene"
      :models="models"
      :views="views"
      :describe-row="
        (list, record, index) =>
          UI.row(list, record, index, model, appearance.language)
      "
      @event="emit('event', $event)"
    />
  </div>
</template>
<style>
.script-shelf-editor {
  display: block;
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
  padding: 0;
}
</style>
