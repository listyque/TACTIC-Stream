<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
const props = defineProps({
  records: Array,
  targets: Array,
  count: Number,
  busy: Boolean,
  valid: Boolean
});
const emit = defineEmits(['toggle', 'cancel', 'submit']);
const root = ref(null),
  width = ref(400),
  height = ref(400);
let observer;
const row = (node, record) =>
  UI.forward(
    {
      ...record,
      selected: props.targets.includes(record.conversationId),
      busy: props.busy
    },
    Math.max(0, node.width - 16),
    appearance.language
  );
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const size = entries[0].contentRect;
    if (size.width > 0) {
      width.value = size.width;
      height.value = size.height;
    }
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="root" class="messages-forward-surface">
    <FrameView
      :scene="
        UI.forwarding(
          { count, busy, valid },
          width,
          height,
          appearance.language
        )
      "
      :models="{ conversations: records }"
      :describe-row="row"
      @event="(event) => emit(event.type, event.key)"
    />
  </div>
</template>
<style>
.messages-forward-surface {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 240px;
}
.messages-forward-surface > .frame-view {
  height: 100%;
}
</style>
