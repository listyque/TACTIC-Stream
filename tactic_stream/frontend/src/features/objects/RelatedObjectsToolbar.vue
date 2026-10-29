<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/related.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(1);
let observer;
const scene = computed(() =>
  UI.toolbar(props.model, width.value, appearance.language)
);
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries.at(-1).contentRect.width)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="related-objects-toolbar"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      @event="(action, value) => emit('event', action, value)"
    />
  </div>
</template>
<style>
.related-objects-toolbar {
  flex: none;
  min-width: 0;
}
</style>
