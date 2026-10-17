<script setup>
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ContentLoadingOverlay from '../../controls/display/ContentLoadingOverlay.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { usePagination } from '../../controls/pagination.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import { node } from '../../../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/links.ui.mjs';
const props = defineProps({
  records: Array,
  scope: String,
  total: Number,
  busy: Boolean,
  hasMore: Boolean,
  selected: Array,
  disabled: Boolean
});
const emit = defineEmits(['select', 'drop', 'more']);
const host = ref(null),
  size = ref({ width: 0, height: 0 }),
  scroll = ref(null),
  content = ref(null);
let observer,
  modifiers = {};
const rows = computed(() =>
  props.records.map((record) => ({
    ...record,
    selected: props.selected.includes(record.key),
    dragValue: {
      kind: 'object-links',
      scope: props.scope,
      keys: props.selected.includes(record.key) ? props.selected : [record.key]
    }
  }))
);
const scene = computed(() => {
  const width = size.value.width,
    height = size.value.height;
  const result = UI.list(
    {
      scope: props.scope,
      count: rows.value.length,
      total: props.total,
      loading: props.busy
    },
    width,
    height,
    appearance.language
  );
  result.nodes.push(
    node('List', 'linkList_' + props.scope, result.viewport, {
      source: 'rows',
      keyField: 'key',
      rowHeight: 68,
      rowGap: 4,
      label: t(
        props.scope === 'available' ? 'Available objects' : 'Linked objects'
      )
    })
  );
  return result;
});
usePagination(
  scroll,
  content,
  () => props.hasMore && !props.busy,
  () => emit('more')
);
function event(action) {
  if (action.type === 'select' && !props.disabled)
    emit('select', action.key, modifiers);
}
function drop(event) {
  if (props.disabled) return;
  const raw = event.dataTransfer.getData('application/x-tactic-frame');
  if (!raw) return;
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return;
  }
  if (
    data.kind === 'object-links' &&
    data.scope !== props.scope &&
    Array.isArray(data.keys) &&
    data.keys.every((key) => typeof key === 'string')
  ) {
    event.preventDefault();
    emit('drop', data.keys);
  }
}
onMounted(async () => {
  const measure = () => {
    size.value = {
      width: host.value.clientWidth,
      height: host.value.clientHeight
    };
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
  await nextTick();
  scroll.value = host.value.querySelector('.frame-list');
  content.value = scroll.value.firstElementChild;
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="object-link-list"
    :style="{
      '--link-row-width': scene.rowWidth + 'px',
      '--link-row-left': scene.rowInsets.left + 'px',
      '--link-row-top': scene.rowInsets.top + 'px',
      '--link-row-bottom': scene.rowInsets.bottom + 'px'
    }"
    @pointerdown.capture="
      modifiers = {
        control: $event.ctrlKey || $event.metaKey,
        shift: $event.shiftKey
      }
    "
    @keydown.capture="
      modifiers = {
        control: $event.ctrlKey || $event.metaKey,
        shift: $event.shiftKey
      }
    "
    @dragover.prevent
    @drop="drop"
  >
    <FrameView
      :scene="scene"
      :interactive="!disabled"
      :models="{ rows }"
      :describe-row="(list, record) => UI.row(record, scene.rowWidth)"
      @event="event"
    />
    <ContentLoadingOverlay
      v-if="scene.loading"
      message="Loading objects..."
      :style="{
        left: scene.body.x + 'px',
        top: scene.body.y + 'px',
        width: scene.body.width + 'px',
        height: scene.body.height + 'px'
      }"
    />
  </div>
</template>
<style>
.object-link-list {
  position: relative;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
  border-radius: var(--surface-radius);
  background: var(--surface);
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}
.object-link-list .frame-row {
  left: var(--link-row-left);
  transform: translateY(var(--link-row-top));
  width: var(--link-row-width) !important;
}
.object-link-list .frame-list {
  padding-bottom: var(--link-row-bottom);
}
</style>
