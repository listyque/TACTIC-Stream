<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
defineProps({ model: Object });
const emit = defineEmits(['jump', 'menu']);
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
  <div ref="root" class="chat-file-entry-frame">
    <FrameView
      :scene="
        UI.gallery({ ...model, actions: true }, width, appearance.language)
      "
      @event="
        (event, source) =>
          emit(event.type, event.type === 'menu' ? source : event.value)
      "
    />
  </div>
</template>
<style>
.chat-file-entry-frame {
  position: relative;
  height: 60px;
  min-width: 0;
}
.chat-file-entry-frame > .frame-view {
  height: 60px;
}
</style>
