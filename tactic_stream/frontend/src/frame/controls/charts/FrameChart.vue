<script setup>
import {
  computed,
  onMounted,
  onBeforeUnmount,
  ref,
  watch,
  nextTick
} from 'vue';
import { colors } from '../../../../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Chart from '../../../../../src/tactic_stream/shared_ui/controls/charts/chart.ui.mjs';
import { tooltipDirective as vTooltip } from '../../../controls/tooltip.js';

const props = defineProps({ node: { type: Object, required: true } });
const canvas = ref(null),
  hovered = ref(-1);
const tip = computed(() =>
  hovered.value < 0
    ? ''
    : props.node.labels[hovered.value] +
      ': ' +
      Chart.number(props.node.chart.values[hovered.value], props.node.language)
);
let pending = 0,
  observer;
function paint() {
  pending = 0;
  if (!canvas.value) return;
  const g = props.node.chart,
    ratio = devicePixelRatio || 1;
  const element = canvas.value;
  element.width = Math.round(g.width * ratio);
  element.height = Math.round(g.height * ratio);
  const context = element.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  const style = getComputedStyle(element);
  Chart.paint(
    context,
    g,
    (role) => style.getPropertyValue(colors[role]).trim(),
    hovered.value
  );
}
function requestPaint() {
  if (!pending) pending = requestAnimationFrame(paint);
}
function move(event) {
  const box = canvas.value.getBoundingClientRect();
  hovered.value = Chart.hit(
    props.node.chart,
    event.clientX - box.left,
    event.clientY - box.top
  );
}
watch(
  () => props.node.chart,
  () => {
    hovered.value = -1;
    nextTick(requestPaint);
  }
);
watch(hovered, requestPaint);
onMounted(() => {
  observer = new MutationObserver(requestPaint);
  for (let element = canvas.value; element; element = element.parentElement)
    observer.observe(element, {
      attributes: true,
      attributeFilter: ['style', 'class', 'data-theme']
    });
  requestPaint();
});
onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(pending);
});
</script>
<template>
  <canvas
    ref="canvas"
    v-tooltip="tip"
    :data-frame="node.id"
    role="img"
    tabindex="0"
    :aria-label="node.text"
    @pointermove="move"
    @pointerleave="hovered = -1"
  />
</template>
