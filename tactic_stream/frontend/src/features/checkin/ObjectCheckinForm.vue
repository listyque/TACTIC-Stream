<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { sourcePath } from './files.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/object_checkin.ui.mjs';

const props = defineProps({ model: Object, files: Array });
const emit = defineEmits(['event']);
const host = ref(null),
  viewport = ref({ width: 680, height: 650 });
const rows = computed(() =>
  props.files.map((file, index) => ({
    key: String(index),
    index,
    path: sourcePath(file),
    title: file.name,
    size: file.size,
    canRemove: !props.model.busy
  }))
);
const scene = computed(() =>
  UI.describe(
    props.model,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const describeRow = (list, record) =>
  UI.fileRow(record, list.width - 16, appearance.language);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width > 0 && box.height > 0)
      viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="object-checkin-workspace" :aria-busy="model.busy">
    <FrameView
      :scene="scene"
      :models="{ files: rows }"
      :describe-row="describeRow"
      @event="emit('event', $event)"
    />
  </div>
</template>
<style>
.object-checkin-workspace {
  position: relative;
  min-width: 0;
  min-height: 0;
  flex: 1;
}
</style>
