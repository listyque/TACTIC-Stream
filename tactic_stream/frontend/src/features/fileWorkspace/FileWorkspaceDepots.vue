<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/workspace/depots.ui.mjs';

const props = defineProps({
  rows: Array,
  selected: Object,
  draft: Object,
  repositories: Array,
  busy: Boolean,
  administrator: Boolean,
  after: String
});
const emit = defineEmits([
  'select',
  'edit',
  'change',
  'save',
  'reset',
  'cancel',
  'refresh',
  'more'
]);
const host = ref(null),
  viewport = ref({ width: 800, height: 600 }),
  desktopExtent = ref(null),
  mobileExtent = ref(null);
const model = computed(() => ({
  ...props,
  extent: viewport.value.width < 600 ? mobileExtent.value : desktopExtent.value
}));
const rows = computed(() =>
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
  } else if (action.type === 'field')
    emit('change', { ...props.draft, [action.key]: action.value });
  else if (action.type === 'new') emit('edit', null);
  else if (action.type === 'edit') emit('edit', props.selected);
  else if (['save', 'reset', 'cancel', 'refresh', 'more'].includes(action.type))
    emit(action.type);
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
  <section ref="host" class="depots-catalog" :aria-label="t('Depots')">
    <FrameView
      :scene="scene"
      :models="{ depots: rows }"
      :describe-row="describeRow"
      @event="event"
    />
  </section>
</template>
<style scoped>
.depots-catalog {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
</style>
