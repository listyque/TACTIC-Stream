<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../frame/FrameView.vue';
import { observeFrameSizes } from '../frame/resize.js';
import { tab } from '../../../src/tactic_stream/shared_ui/controls/tabs/workspace.ui.mjs';
const props = defineProps({
  record: Object,
  hovered: Boolean,
  pressed: Boolean,
  focused: Boolean,
  closeHovered: Boolean,
  closePressed: Boolean
});
const root = ref(null),
  width = ref(120),
  height = ref(50);
const scene = computed(() =>
  tab(width.value, height.value, props.record, props)
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    width.value = box.width;
    height.value = box.height;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="root" class="frame-workspace-tab">
    <FrameView :scene="scene" :interactive="false" />
  </div>
</template>
<style>
.frame-workspace-tab {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
