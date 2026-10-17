<script setup>
import { ref, onMounted, onUpdated, onBeforeUnmount } from 'vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { arrange } from '../../../../src/tactic_stream/shared_ui/features/objects/fields.ui.mjs';
const host = ref(null),
  height = ref(0);
let observer,
  frame = 0;
const observed = new Set();
function schedule() {
  if (!frame) frame = requestAnimationFrame(layout);
}
function layout() {
  frame = 0;
  const children = [...host.value.children].filter(
    (child) => child.style.display !== 'none'
  );
  const scene = arrange(
    host.value.clientWidth,
    children.map((child) => child.offsetHeight)
  );
  children.forEach((child, index) => {
    const box = scene.cells[index];
    Object.assign(child.style, {
      position: 'absolute',
      left: box.x + 'px',
      top: box.y + 'px',
      width: box.width + 'px'
    });
  });
  height.value = scene.height;
  for (const child of observed)
    if (!children.includes(child)) {
      observer.unobserve(child);
      observed.delete(child);
    }
  for (const child of children)
    if (!observed.has(child)) {
      observer.observe(child);
      observed.add(child);
    }
}
onMounted(() => {
  observer = observeFrameSizes(schedule);
  observer.observe(host.value);
  schedule();
});
onUpdated(schedule);
onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(frame);
});
</script>
<template>
  <div ref="host" class="object-field-grid" :style="{ height: height + 'px' }">
    <slot />
  </div>
</template>
<style>
.object-field-grid {
  position: relative;
  min-width: 0;
  width: 100%;
  flex: none;
}
</style>
