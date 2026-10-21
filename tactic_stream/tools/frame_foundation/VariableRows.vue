<script setup>
import { ref } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import {
  node,
  rect,
  button
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import '../../frontend/src/style.css';

const rows = ref([]),
  view = ref(null),
  events = ref([]);
const definition = node('List', 'variableRows', rect(0, 0, 320, 80), {
  source: 'rows',
  keyField: 'key',
  fields: ['key', 'text', 'extent'],
  rowHeight: 40,
  rowGap: 0,
  rowHeightField: 'extent'
});
function row(list, record) {
  return {
    nodes: [
      button(
        'item-' + record.key,
        rect(0, 0, list.width - 16, 40),
        record.text,
        '',
        { type: 'selected', key: record.key },
        true
      )
    ]
  };
}
window.variableRows = {
  set(values) {
    rows.value = values;
  },
  focus(index, key) {
    return view.value.focusListRow('variableRows', index, 'item-' + key);
  },
  events
};
</script>

<template>
  <FrameView
    style="width: 320px; height: 80px"
    ref="view"
    :scene="{ nodes: [definition] }"
    :models="{ rows }"
    :describe-row="row"
    @event="(action) => events.push(action)"
  />
</template>
