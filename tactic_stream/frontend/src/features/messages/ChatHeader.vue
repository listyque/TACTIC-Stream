<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/conversation.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const root = ref(null),
  width = ref(600);
let observer;
const scene = computed(() =>
  UI.header(
    {
      ...props.model,
      presenceWidth: Math.ceil(
        qtLabelTextWidth(props.model.presence || '', '11px Segoe UI')
      )
    },
    width.value,
    appearance.language
  )
);
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
  <div ref="root" class="messages-chat-header">
    <FrameView
      :scene="scene"
      @event="(event, source) => emit('event', event, source)"
    /><slot />
  </div>
</template>
<style>
.messages-chat-header {
  position: relative;
  display: block !important;
  height: 58px;
  min-height: 58px;
  padding: 0 !important;
}
.messages-chat-header > .frame-view {
  height: 58px;
}
.messages-chat-header > .chat-actions {
  position: absolute;
  width: 0;
  height: 0;
  right: 10px;
  top: 16px;
}
.messages-chat-header > .busy-indicator {
  position: absolute;
  right: 12px;
  top: 19px;
  pointer-events: none;
}
</style>
