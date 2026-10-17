<script setup>
import { ref, computed, h, useSlots, onMounted, onBeforeUnmount } from 'vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/editors.ui.mjs';
const props = defineProps({ part: String, model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  frame = ref(null),
  width = ref(0);
const slots = useSlots(),
  views = { chips: { component: () => h('div', slots.chips?.()) } };
const scene = computed(() =>
  UI[props.part](props.model, width.value, appearance.language)
);
let observer;
onMounted(() => {
  width.value = host.value.clientWidth;
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({ focusControl: (id) => frame.value?.focusControl(id) });
</script>
<template>
  <div
    ref="host"
    class="search-editor-part"
    :style="{
      position: 'relative',
      height: scene.contentHeight + 'px',
      flex: 'none',
      minWidth: 0
    }"
  >
    <FrameView
      ref="frame"
      :scene="scene"
      :views="views"
      @event="(action) => emit('event', action)"
    />
  </div>
</template>
