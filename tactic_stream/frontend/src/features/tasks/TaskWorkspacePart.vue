<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/workspace.ui.mjs';

const props = defineProps({ part: String, model: Object, views: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI[props.part](props.model, width.value, appearance.language)
);
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="task-workspace-part"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="views"
      @event="(action, source) => emit('event', action, source)"
    />
  </div>
</template>
<style>
.task-workspace-part {
  position: relative;
  width: 100%;
  min-width: 0;
  flex: none;
}
</style>
