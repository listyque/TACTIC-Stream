<script setup>
import { computed } from 'vue';
import FrameView from '../frame/FrameView.vue';
import { frameColors } from '../appearance.js';
import { row } from '../../../src/tactic_stream/shared_ui/controls/tabs/section.ui.mjs';
const props = defineProps({
  width: { type: Number, default: 48 },
  record: Object,
  revealed: Boolean,
  pressed: Boolean
});
let colorProbe;
const scene = computed(() => {
  let record = props.record;
  if (record.accent && !record.accent.startsWith('#')) {
    colorProbe ||= document.createElement('canvas').getContext('2d');
    colorProbe.fillStyle = '#000000';
    colorProbe.fillStyle = record.accent;
    record = { ...record, accent: colorProbe.fillStyle };
  }
  const scene = row(props.width, record, props, frameColors.value);
  return {
    ...scene,
    nodes: scene.nodes.filter((node) => node.kind !== 'View')
  };
});
</script>
<template>
  <FrameView class="section-tab-visual" :scene="scene" :interactive="false" />
</template>
<style>
.section-tab-visual {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
