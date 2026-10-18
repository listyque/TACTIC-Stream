<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/feed.ui.mjs';
defineProps({ model: Object });
const emit = defineEmits(['event']);
const root = ref(null),
  width = ref(800);
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
  <div
    ref="root"
    class="activity-feed-toolbar"
    :style="{
      height: UI.toolbar(model, width, appearance.language).height + 'px'
    }"
  >
    <FrameView
      :scene="UI.toolbar(model, width, appearance.language)"
      @event="(event, source) => emit('event', event, source)"
    /><slot />
  </div>
</template>
<style>
.activity-feed-toolbar.activity-feed-toolbar {
  position: relative;
  display: block;
  padding: 0;
  container-type: normal;
  background: transparent;
}
.activity-feed-toolbar > details {
  position: absolute;
  width: 0;
  height: 0;
  right: 10px;
  bottom: 10px;
}
</style>
