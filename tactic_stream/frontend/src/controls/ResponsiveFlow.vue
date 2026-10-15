<script setup>
// ResponsiveFlow.qml keeps equal cells and lets individual items occupy a full row.
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
const props = defineProps({ minimumCellWidth: { type: Number, default: 180 }, maximumColumns: { type: Number, default: 0 }, spacing: { type: Number, default: 8 } })
const root = ref(null), width = ref(0)
const columns = computed(() => Math.min(props.maximumColumns || Infinity, Math.max(1, Math.floor((width.value + props.spacing) / (props.minimumCellWidth + props.spacing)))))
let observer, resizeFrame
// Hidden timelines keep their geometry; resize writes follow the observer's layout pass.
onMounted(() => { observer = new ResizeObserver(entries => {
  const next = entries[0].contentRect.width
  if (next > 0 && next !== width.value) { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(() => { width.value = next }) }
}); observer.observe(root.value) })
onBeforeUnmount(() => { observer?.disconnect(); cancelAnimationFrame(resizeFrame) })
</script>
<template><div ref="root" class="responsive-flow" :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap: spacing + 'px' }"><slot /></div></template>
<style>.responsive-flow { display:grid; min-width:0; width:100%; }.responsive-flow > [data-flow-full] { grid-column:1/-1; }</style>
