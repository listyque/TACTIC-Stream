<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { message } from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';

const props = defineProps({ cell: Object, height: Number });
const host = ref(null),
  width = ref(240);
const scene = computed(() =>
  message(props.cell || {}, width.value, props.height, appearance.language)
);
let observer;
onMounted(() => {
  observer = new ResizeObserver(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <div ref="host" class="table-message-cell">
    <FrameView :scene="scene" :style="{ height: height + 'px' }" />
  </div>
</template>

<style scoped>
.table-message-cell {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 100%;
}
</style>
