<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
defineProps({ mode: String, count: Number });
const root = ref(null),
  width = ref(300);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <header ref="root" class="message-panel-header">
    <FrameView :scene="UI.heading(mode, width, count, appearance.language)" />
  </header>
</template>
<style>
.message-panel-header.message-panel-header {
  display: block;
  position: relative;
  padding: 0;
  height: 18px;
  flex: none;
}
.message-panel-header > .frame-view {
  height: 18px;
}
</style>
