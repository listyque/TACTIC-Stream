<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/inspector.ui.mjs';

const props = defineProps({
  info: Object,
  preview: Object,
  tab: String,
  busy: Boolean,
  error: String,
  history: Boolean
});
const emit = defineEmits(['tab']);
const host = ref(null),
  viewport = ref({ width: 600, height: 220 });
const scene = computed(() =>
  UI.describe(
    props,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
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
  <div ref="host" class="workspace-inspector-view">
    <FrameView
      :scene="scene"
      @event="(action) => action.type === 'tab' && emit('tab', action.value)"
    />
  </div>
</template>
<style scoped>
.workspace-inspector-view {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
</style>
