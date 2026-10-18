<script setup>
import { computed, ref, onMounted, onBeforeUnmount, markRaw } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import WorkspaceLogEntries from './inspection/WorkspaceLogEntries.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/workspace/log.ui.mjs';

const props = defineProps({ entries: Array });
const emit = defineEmits(['clear', 'copy', 'debug']);
const expanded = ref(true),
  host = ref(null),
  viewport = ref({ width: 800, height: 140 });
const entriesComponent = markRaw(WorkspaceLogEntries);
const views = computed(() => ({
  entries: { component: entriesComponent, props: { entries: props.entries } }
}));
const scene = computed(() =>
  UI.describe(
    { expanded: expanded.value },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
function event(action) {
  if (action.type === 'visibility') expanded.value = !expanded.value;
  else if (['clear', 'copy', 'debug'].includes(action.type)) emit(action.type);
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
  <section
    ref="host"
    class="file-operation-log"
    :style="{ height: expanded ? '140px' : '36px' }"
    :aria-label="t('Operation log')"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
  </section>
</template>
<style scoped>
.file-operation-log {
  position: relative;
  flex: none;
  max-height: calc(20vh + 36px);
  min-width: 0;
}
</style>
