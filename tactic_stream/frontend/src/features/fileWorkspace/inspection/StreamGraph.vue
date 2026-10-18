<script setup>
import { computed, ref, markRaw, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import StreamGraphEdges from './StreamGraphEdges.vue';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/graph.ui.mjs';

const props = defineProps({
  nodes: Array,
  edges: Array,
  busy: Boolean,
  after: String
});
const emit = defineEmits(['refresh', 'more']);
const host = ref(null),
  viewport = ref({ width: 800, height: 500 }),
  zoom = ref(1),
  selected = ref('');
const edgeComponent = markRaw(StreamGraphEdges);
const views = computed(() => ({
  streamGraphEdges: {
    component: edgeComponent,
    nodeProps: true,
    props: { nodes: props.nodes, edges: props.edges, zoom: zoom.value }
  }
}));
const scene = computed(() =>
  UI.describe(
    {
      nodes: props.nodes,
      edges: props.edges,
      zoom: zoom.value,
      selected: selected.value,
      busy: props.busy,
      after: props.after
    },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
function event(action) {
  if (action.type === 'zoom') zoom.value = action.value;
  else if (action.type === 'select') selected.value = action.key;
  else if (action.type === 'refresh' || action.type === 'more')
    emit(action.type);
}
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
  <div ref="host" class="workspace-stream-graph">
    <FrameView :scene="scene" :views="views" @event="event" />
  </div>
</template>
<style scoped>
.workspace-stream-graph {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
</style>
