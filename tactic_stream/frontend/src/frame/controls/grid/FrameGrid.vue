<script setup>
import { computed, nextTick, ref } from 'vue';
import FrameView from '../../FrameView.vue';
import { virtualRange } from '../../../../../src/tactic_stream/shared_ui/core/frame.mjs';

const props = defineProps({
  node: Object,
  source: Array,
  describeCell: Function
});
const emit = defineEmits(['event']);
const body = ref(null),
  position = ref({ x: 0, y: 0 });
const width = computed(() =>
  Math.max(1, props.node.width - props.node.labelWidth - 16)
);
const height = computed(() =>
  Math.max(1, props.node.height - props.node.headerHeight - 16)
);
const range = (count, size, extent, offset) => {
  const r = virtualRange(count, size, extent, offset, 1);
  return Array.from(
    { length: r.last - r.first },
    (_, index) => r.first + index
  );
};
const rows = computed(() =>
  range(
    props.node.rowHeaders.length,
    props.node.rowHeight,
    height.value,
    position.value.y
  )
);
const columns = computed(() =>
  range(
    props.node.columnHeaders.length,
    props.node.cellWidth,
    width.value,
    position.value.x
  )
);
const totalWidth = computed(
  () => props.node.columnHeaders.length * props.node.cellWidth
);
const totalHeight = computed(
  () => props.node.rowHeaders.length * props.node.rowHeight
);
async function focusCell(row, column, name) {
  const el = body.value,
    n = props.node;
  if (column * n.cellWidth < el.scrollLeft)
    el.scrollLeft = column * n.cellWidth;
  else if ((column + 1) * n.cellWidth > el.scrollLeft + width.value)
    el.scrollLeft = (column + 1) * n.cellWidth - width.value;
  if (row * n.rowHeight < el.scrollTop) el.scrollTop = row * n.rowHeight;
  else if ((row + 1) * n.rowHeight > el.scrollTop + height.value)
    el.scrollTop = (row + 1) * n.rowHeight - height.value;
  position.value = { x: el.scrollLeft, y: el.scrollTop };
  await nextTick();
  el.querySelector('[data-frame="' + CSS.escape(name) + '"]')?.focus();
}
defineExpose({ focusCell });
</script>
<template>
  <div
    class="frame-grid"
    :data-frame="node.id"
    role="grid"
    :aria-label="node.text"
  >
    <div
      class="frame-grid-corner"
      :style="{
        width: node.labelWidth + 'px',
        height: node.headerHeight + 'px'
      }"
    >
      {{ node.caption }}
    </div>
    <div
      class="frame-grid-column-headings"
      :style="{
        left: node.labelWidth + 'px',
        width: width + 'px',
        height: node.headerHeight + 'px'
      }"
    >
      <span
        v-for="column in columns"
        :key="column"
        role="columnheader"
        :data-frame="node.id + '_column_' + column"
        :class="{
          'frame-grid-detailed-heading':
            typeof node.columnHeaders[column] === 'object'
        }"
        :style="{
          left: column * node.cellWidth - position.x + 'px',
          width: node.cellWidth + 'px',
          height: node.headerHeight + 'px'
        }"
        ><template v-if="typeof node.columnHeaders[column] === 'object'"
          ><b :data-frame="node.id + '_column_' + column + '_title'">{{
            node.columnHeaders[column].label
          }}</b
          ><small :data-frame="node.id + '_column_' + column + '_detail'">{{
            node.columnHeaders[column].detail
          }}</small></template
        ><template v-else>{{ node.columnHeaders[column] }}</template></span
      >
    </div>
    <div
      class="frame-grid-row-headings"
      :style="{
        top: node.headerHeight + 'px',
        width: node.labelWidth + 'px',
        height: height + 'px'
      }"
    >
      <div
        v-for="row in rows"
        :key="row"
        role="rowheader"
        :data-frame="node.id + '_row_' + row"
        :class="{
          'frame-grid-custom-heading': !!node.rowHeaders[row].children
        }"
        :style="{
          top: row * node.rowHeight - position.y + 'px',
          width: node.labelWidth + 'px',
          height: node.rowHeight + 'px'
        }"
      >
        <FrameView
          v-if="node.rowHeaders[row].children"
          :scene="{ nodes: node.rowHeaders[row].children }"
          @event="emit('event', $event)"
        /><template v-else
          ><span
            :style="{ fontWeight: node.rowHeaders[row].all ? 600 : 400 }"
            >{{ node.rowHeaders[row].label }}</span
          ><small>{{ node.rowHeaders[row].detail }}</small></template
        >
      </div>
    </div>
    <div
      ref="body"
      class="frame-grid-body"
      :style="{
        left: node.labelWidth + 'px',
        top: node.headerHeight + 'px',
        width: width + 16 + 'px',
        height: height + 16 + 'px'
      }"
      @scroll="
        position = { x: $event.target.scrollLeft, y: $event.target.scrollTop }
      "
    >
      <div
        :style="{
          position: 'relative',
          width: totalWidth + 'px',
          height: totalHeight + 'px'
        }"
      >
        <template v-for="row in rows" :key="row"
          ><FrameView
            v-for="column in columns"
            :key="column"
            class="frame-grid-cell"
            :style="{
              left: column * node.cellWidth + 'px',
              top: row * node.rowHeight + 'px',
              width: node.cellWidth + 'px',
              height: node.rowHeight + 'px'
            }"
            :scene="
              describeCell(node, source?.[row]?.[column] || {}, row, column)
            "
            @event="emit('event', $event)"
        /></template>
      </div>
    </div>
  </div>
</template>
<style>
.frame-grid {
  overflow: hidden;
  font-size: 13px;
}
.frame-grid-corner,
.frame-grid-column-headings {
  background: var(--surface-high);
  color: var(--muted);
  font-size: 12px;
}
.frame-grid-corner {
  position: absolute;
  box-sizing: border-box;
  padding: 6px;
  display: flex;
  align-items: center;
  overflow: hidden;
}
.frame-grid-column-headings,
.frame-grid-row-headings {
  position: absolute;
  overflow: hidden;
}
.frame-grid-column-headings > span {
  position: absolute;
  box-sizing: border-box;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.frame-grid-column-headings > .frame-grid-detailed-heading {
  padding: 1px 6px;
  display: block;
  text-align: left;
}
.frame-grid-detailed-heading > b,
.frame-grid-detailed-heading > small {
  display: block;
  height: 19px;
  line-height: 19px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.frame-grid-detailed-heading > b {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
}
.frame-grid-detailed-heading > small {
  font-size: 12px;
  font-weight: 400;
  color: var(--muted);
}
.frame-grid-row-headings > div {
  position: absolute;
  box-sizing: border-box;
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.frame-grid-row-headings > div > span,
.frame-grid-row-headings > div > small {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 19px;
}
.frame-grid-row-headings > div > small {
  font-size: 12px;
  color: var(--muted);
}
.frame-grid-row-headings > .frame-grid-custom-heading {
  padding: 0;
  display: block;
}
.frame-grid-body {
  position: absolute;
  overflow: scroll;
  overscroll-behavior: contain;
}
.frame-grid-cell {
  position: absolute !important;
}
.frame-grid-body::-webkit-scrollbar {
  width: 16px;
  height: 16px;
}
.frame-grid-body::-webkit-scrollbar-thumb:vertical {
  border-left-width: 7.5px;
}
.frame-grid-body::-webkit-scrollbar-thumb:horizontal {
  border-top-width: 7.5px;
}
.frame-grid-body::-webkit-scrollbar-track:vertical {
  border-left-width: 7px;
}
.frame-grid-body::-webkit-scrollbar-track:horizontal {
  border-top-width: 7px;
}
</style>
