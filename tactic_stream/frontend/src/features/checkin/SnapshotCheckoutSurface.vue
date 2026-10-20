<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import FrameProgress from '../../frame/controls/display/FrameProgress.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/snapshot_checkout.ui.mjs';

const props = defineProps({ model: Object, files: Array });
const emit = defineEmits(['event']);
const host = ref(null),
  size = ref({ width: 0, height: 0 });
const views = {
  progress: { component: markRaw(FrameProgress), nodeProps: true }
};
const scene = computed(() =>
  size.value.width > 0 && size.value.height > 0
    ? UI.describe(
        props.model,
        size.value.width,
        size.value.height,
        appearance.language
      )
    : { nodes: [] }
);
const describeRow = (list, row) =>
  UI.fileRow(row, list.width - 16, appearance.language);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width > 0 && box.height > 0)
      size.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="snapshot-checkout-workspace"
    :aria-busy="model.loading || model.busy"
  >
    <FrameView
      :scene="scene"
      :models="{ files }"
      :views="views"
      :describe-row="describeRow"
      @event="emit('event', $event)"
    />
  </div>
</template>
<style>
.snapshot-checkout-workspace {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
</style>
