<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/catalog.ui.mjs';

const props = defineProps({
  rows: Array,
  selected: Object,
  busy: Boolean,
  after: String,
  source: String
});
const emit = defineEmits(['select', 'refresh', 'more']);
const host = ref(null),
  viewport = ref({ width: 800, height: 600 }),
  desktopExtent = ref(null),
  mobileExtent = ref(null);
const model = computed(() => ({
  ...props,
  count: props.rows.length,
  extent: viewport.value.width < 600 ? mobileExtent.value : desktopExtent.value
}));
const records = computed(() =>
  props.rows.map((node) => ({ id: node.id ?? node.code, node }))
);
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const describeRow = (list, record) =>
  UI.row(model.value, record, list.width - 16, appearance.language);
function event(action) {
  if (action.type === 'split') {
    if (viewport.value.width < 600) mobileExtent.value = action.value;
    else desktopExtent.value = action.value;
  } else if (action.type === 'select') {
    const row = props.rows.find((row) => (row.id ?? row.code) === action.key);
    if (row) emit('select', row);
  } else if (['refresh', 'more'].includes(action.type)) emit(action.type);
}
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const bounds = entries.at(-1).contentRect;
    if (bounds.width > 0 && bounds.height > 0)
      viewport.value = { width: bounds.width, height: bounds.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="workspace-catalog">
    <FrameView
      :scene="scene"
      :models="{ catalog: records }"
      :describe-row="describeRow"
      @event="event"
    />
  </div>
</template>
<style scoped>
.workspace-catalog {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 160px;
}
</style>
