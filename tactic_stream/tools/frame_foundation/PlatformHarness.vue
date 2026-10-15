<script setup>
import { computed, ref, shallowRef } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import { node, rect } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const rows = shallowRef([]);
const view = ref(null);
const commits = ref(0);
const viewport = ref({ width: 640, height: 360 });
const models = computed(() => ({ rows: rows.value }));
const scene = computed(() => ({
  nodes: [
    node(
      'List',
      'arrayRows',
      rect(0, 0, viewport.value.width, viewport.value.height),
      {
        source: 'rows',
        keyField: 'id',
        rowHeight: 40
      }
    )
  ]
}));
function rowScene(list, record) {
  return {
    nodes: [
      node('Field', 'edit_' + record.id, rect(0, 0, 300, 36), {
        text: record.text,
        action: { type: 'edit', id: record.id },
        keys: { Enter: { type: 'commit', id: record.id } }
      })
    ]
  };
}
function edit(action) {
  if (action.type === 'commit') {
    commits.value++;
    return;
  }
  rows.value = rows.value.map((row) =>
    row.id === action.id ? { id: row.id, text: action.value } : row
  );
}
window.framePlatform = {
  populate(count) {
    rows.value = Array.from({ length: count }, (_, index) => ({
      id: String(index),
      text: 'Draft ' + index
    }));
  },
  reverse() {
    rows.value = [...rows.value].reverse();
  },
  resize(width, height) {
    viewport.value = { width, height };
  },
  focus(name) {
    return view.value.focusControl(name);
  },
  rows,
  commits
};
</script>
<template>
  <FrameView
    ref="view"
    :scene="scene"
    :models="models"
    :describe-row="rowScene"
    @event="edit"
  />
</template>
