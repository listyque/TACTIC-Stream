<script setup>
import { computed, ref, markRaw, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import FileWorkspaceTree from '../FileWorkspaceTree.vue';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/tree.ui.mjs';

const props = defineProps({ nodes: Array, busy: Boolean });
const emit = defineEmits(['expand', 'select']);
const host = ref(null),
  viewport = ref({ width: 280, height: 600 });
const scene = computed(() =>
  UI.describe(
    {},
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const views = computed(() => ({
  depot: {
    component: markRaw(FileWorkspaceTree),
    props: {
      nodes: props.nodes,
      busy: props.busy,
      canDrag: false,
      label: 'Depot tree',
      onExpand: (value) => emit('expand', value),
      onSelect: (value) => emit('select', value)
    }
  }
}));
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const bounds = entries.at(-1).contentRect;
    if (bounds.width > 0 && bounds.height > 0)
      viewport.value = { width: bounds.width, height: bounds.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="inspection-tree-pane">
    <FrameView :scene="scene" :views="views" />
  </div>
</template>
<style scoped>
.inspection-tree-pane {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
</style>
