<script setup>
import { ref, watch, onMounted } from 'vue';
import { frameColors } from '../../../appearance.js';
import { colors } from '../../../../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/graph.ui.mjs';

const props = defineProps({
  frameNode: Object,
  nodes: Array,
  edges: Array,
  zoom: Number
});
const canvas = ref(null);
function paint() {
  if (!canvas.value) return;
  const element = canvas.value,
    ratio = devicePixelRatio || 1;
  element.width = Math.ceil(props.frameNode.width * ratio);
  element.height = Math.ceil(props.frameNode.height * ratio);
  const context = element.getContext('2d');
  context.scale(ratio, ratio);
  UI.paint(context, props.nodes, props.edges, props.zoom, (role) =>
    getComputedStyle(element).getPropertyValue(colors[role]).trim()
  );
}
onMounted(paint);
watch(
  () => [
    props.frameNode,
    props.nodes,
    props.edges,
    props.zoom,
    frameColors.value
  ],
  paint,
  { flush: 'post', deep: true }
);
</script>
<template>
  <canvas ref="canvas" aria-hidden="true" style="pointer-events: none" />
</template>
