<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { keyValues } from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
const props = defineProps({ entries: Array, height: Number });
const host = ref(null),
  width = ref(160);
const scene = computed(() =>
  keyValues(props.entries || [], width.value, props.height, appearance.language)
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
  <div ref="host" class="table-value-fields">
    <FrameView :scene="scene" :style="{ height: height + 'px' }" />
  </div>
</template>
<style scoped>
.table-value-fields {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 100%;
}
</style>
