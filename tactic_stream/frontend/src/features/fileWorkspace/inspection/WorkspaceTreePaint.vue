<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/rows.ui.mjs';

const props = defineProps({ row: Object, caption: String, subtitle: String });
const host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI.treeRow(
    {
      row: props.row,
      caption: props.caption,
      subtitle: props.subtitle,
      contentOnly: true
    },
    width.value
  )
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
  <span ref="host" class="workspace-tree-paint"
    ><FrameView :scene="scene" :interactive="false"
  /></span>
</template>
<style scoped>
.workspace-tree-paint {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
