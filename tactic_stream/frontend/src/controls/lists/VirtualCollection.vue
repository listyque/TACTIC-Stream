<script setup>
import {
  computed,
  ref,
  onMounted,
  onBeforeUnmount,
  nextTick,
  watch
} from 'vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as Collection from '../../../../src/tactic_stream/shared_ui/controls/lists/collection.mjs';

const props = defineProps({
  items: Array,
  cellWidth: Number,
  columnGap: { type: Number, default: 0 },
  rowGap: { type: Number, default: 0 }
});
const host = ref(null),
  width = ref(1),
  top = ref(0),
  height = ref(600),
  focused = ref(''),
  measurements = ref(new Map());
const geometry = computed(() =>
  Collection.layout(
    props.items.map((item) => ({
      ...item,
      height: measurements.value.get(item.key) || item.height
    })),
    width.value,
    props
  )
);
const visible = computed(() => {
  const [first, last] = Collection.range(
    geometry.value.rows,
    top.value,
    height.value
  );
  const rows = geometry.value.rows.slice(first, last),
    focusRow = geometry.value.rowByKey[focused.value];
  if (focusRow != null && (focusRow < first || focusRow >= last))
    rows.push(geometry.value.rows[focusRow]);
  return rows.flatMap((row) =>
    row.entries.map((entry) => ({ ...entry, top: row.top }))
  );
});
let observer,
  frame = 0;
const scrollParents = [];
function update() {
  frame = 0;
  if (!host.value) return;
  const bounds = host.value.getBoundingClientRect();
  let low = 0,
    high = innerHeight;
  for (const parent of scrollParents) {
    const rect = parent.getBoundingClientRect();
    low = Math.max(low, rect.top + parent.clientTop);
    high = Math.min(high, rect.top + parent.clientTop + parent.clientHeight);
  }
  top.value = low - bounds.top;
  height.value = Math.max(0, high - low);
  width.value = host.value.clientWidth;
}
function schedule() {
  if (!frame) frame = requestAnimationFrame(update);
}
const elements = new Map();
function measure(element, key) {
  const previous = elements.get(key);
  if (previous === element) return;
  if (previous) observer?.unobserve(previous);
  if (element) {
    elements.set(key, element);
    observer?.observe(element);
  } else elements.delete(key);
}
function focus(event) {
  focused.value = host.value?.contains(event.target)
    ? event.target.closest('[data-collection-key]')?.dataset.collectionKey || ''
    : '';
}
async function navigate(event) {
  if (
    !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key) ||
    !event.target.matches('article[tabindex]')
  )
    return;
  const current = props.items.findIndex(
      (item) =>
        item.key ===
        event.target.closest('[data-collection-key]')?.dataset.collectionKey
    ),
    columns = geometry.value.rows[0]?.entries.length || 1,
    target =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? props.items.length - 1
          : Math.max(
              0,
              Math.min(
                props.items.length - 1,
                current + (event.key === 'ArrowUp' ? -columns : columns)
              )
            );
  if (current < 0) return;
  event.preventDefault();
  focused.value = props.items[target].key;
  await nextTick();
  const element = elements.get(focused.value);
  element?.scrollIntoView({ block: 'nearest' });
  element?.querySelector('article[tabindex]')?.focus({ preventScroll: true });
}
watch(
  () => [props.cellWidth, props.items],
  ([cellWidth, items], previous) => {
    if (cellWidth !== previous?.[0]) measurements.value = new Map();
    else {
      const keys = new Set(items.map((item) => item.key));
      if ([...measurements.value.keys()].some((key) => !keys.has(key)))
        measurements.value = new Map(
          [...measurements.value].filter(([key]) => keys.has(key))
        );
    }
    nextTick(schedule);
  }
);
// Keep measured heights during pane resize; observed rows report any actual size change.
onMounted(() => {
  for (
    let parent = host.value.parentElement;
    parent;
    parent = parent.parentElement
  ) {
    if (/(auto|scroll)/.test(getComputedStyle(parent).overflowY)) {
      scrollParents.push(parent);
      parent.addEventListener('scroll', schedule, { passive: true });
    }
  }
  observer = observeFrameSizes((entries) => {
    const sizes = new Map(measurements.value);
    let changed = false;
    for (const entry of entries) {
      if (entry.target === host.value || scrollParents.includes(entry.target)) {
        schedule();
        continue;
      }
      const key = entry.target.dataset.collectionKey,
        measured = Math.ceil(
          entry.borderBoxSize?.[0]?.blockSize ||
            entry.target.getBoundingClientRect().height
        );
      if (key && measured > 0 && sizes.get(key) !== measured) {
        sizes.set(key, measured);
        changed = true;
      }
    }
    if (changed) measurements.value = sizes;
  });
  observer.observe(host.value);
  for (const parent of scrollParents) observer.observe(parent);
  for (const element of elements.values()) observer.observe(element);
  window.addEventListener('resize', schedule);
  window.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('focusin', focus);
  update();
});
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  observer?.disconnect();
  for (const parent of scrollParents)
    parent.removeEventListener('scroll', schedule);
  window.removeEventListener('resize', schedule);
  window.removeEventListener('scroll', schedule);
  document.removeEventListener('focusin', focus);
});
</script>
<template>
  <div
    ref="host"
    class="virtual-collection"
    role="list"
    :style="{ height: geometry.height + 'px' }"
    :data-collection-total="items.length"
    @keydown="navigate"
  >
    <div
      v-for="entry in visible"
      :key="entry.key"
      :ref="(element) => measure(element, entry.key)"
      class="virtual-collection-entry"
      role="listitem"
      :aria-setsize="items.length"
      :aria-posinset="entry.index + 1"
      :data-collection-key="entry.key"
      :style="{
        left: entry.left + 'px',
        top: entry.top + 'px',
        width: entry.width + 'px'
      }"
    >
      <slot :item="entry.data" :index="entry.index" />
    </div>
  </div>
</template>
<style>
.virtual-collection,
.result-item-list.virtual-collection {
  display: block;
  position: relative;
  min-width: 0;
  overflow-anchor: none;
}
.virtual-collection-entry {
  position: absolute;
  display: flow-root;
}
</style>
