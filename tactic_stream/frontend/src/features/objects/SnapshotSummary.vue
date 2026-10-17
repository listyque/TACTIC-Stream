<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';
const props = defineProps({ snapshot: Object, selected: Boolean });
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI.summary(
    { ...props.snapshot, selected: props.selected },
    width.value,
    appearance.language,
    (text, size, weight = 400) =>
      qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`)
  )
);
let observer;
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="snapshot-summary"><FrameView :scene="scene" /></div>
</template>
<style>
.snapshot-summary {
  min-width: 0;
  flex: 1;
  height: 59px;
}
</style>
