<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/knowledge/navigation.ui.mjs';
const props = defineProps({ entries: Array, compact: Boolean });
const emit = defineEmits(['heading']);
const host = ref(null),
  width = ref(220),
  height = ref(260);
const scene = computed(() =>
  UI.outline(props.entries, width.value, height.value, '', appearance.language)
);
let observer;
onMounted(() => {
  observer = observeFrameSizes(() => {
    width.value = host.value.clientWidth;
    height.value = host.value.clientHeight;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="knowledge-outline"
    :class="{ compact }"
    :style="
      compact ? { height: Math.min(210, 42 + entries.length * 30) + 'px' } : {}
    "
  >
    <FrameView
      :scene="scene"
      :models="{ headings: UI.outlineEntries(entries) }"
      :describe-row="
        (list, record, index) =>
          UI.heading(record, index, Math.max(0, list.width - 16))
      "
      @event="(action) => emit('heading', entries[action.index])"
    />
  </div>
</template>
<style>
.knowledge-outline {
  position: relative;
  width: 220px;
  flex: none;
  min-height: 0;
  height: 100%;
}
.knowledge-outline.compact {
  width: 100%;
}
</style>
