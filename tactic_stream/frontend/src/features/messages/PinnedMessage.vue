<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/message.ui.mjs';
defineProps({ model: Object });
const emit = defineEmits(['open', 'history']);
const root = ref(null),
  width = ref(600);
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
  <div ref="root" class="messages-pin-frame">
    <FrameView
      :scene="UI.pinned(model, width, appearance.language)"
      @event="(event, source) => emit(event.type, source)"
    />
  </div>
</template>
<style>
.messages-pin-frame {
  height: 48px;
  flex: none;
  position: relative;
}
.messages-pin-frame > .frame-view {
  height: 48px;
}
</style>
