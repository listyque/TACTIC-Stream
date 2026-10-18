<script setup>
import { computed, ref, markRaw, h, watch, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { timestampFullLabel } from '../activity/activity.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/table.ui.mjs';
const props = defineProps({ row: Object, busy: Boolean, checked: Boolean });
const emit = defineEmits(['enter', 'select', 'notes', 'menu']);
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI.mobileRow(
    {
      title: props.row.title,
      process: props.row.process,
      processLabel: props.row.__process__?.label || props.row.process,
      accent: props.row.__process__?.color,
      statusLabel: props.row.__status__?.label || props.row.status,
      statusColor: props.row.__status__?.color,
      assignedLabel: props.row.assigned === '—' ? '' : props.row.assigned,
      deadline: props.row.bid_end_date
        ? timestampFullLabel(props.row.bid_end_date)
        : '',
      progress: props.row.progress ?? props.row.completion,
      pending: props.row.pending,
      deleting: props.row.deleting,
      hasTask: !!props.row.__search_key__,
      notes: props.row.notes,
      busy: props.busy,
      checked: props.checked
    },
    width.value,
    appearance.language
  )
);
const preview = markRaw({
  setup() {
    return () =>
      h(ItemPreview, {
        source: props.row.parent?.__preview__?.image,
        fallbackText: props.row.title
          .trim()
          .split(/\s+/)
          .slice(0, 2)
          .map((word) => word[0])
          .join('')
          .toUpperCase(),
        accent: props.row.__process__?.color,
        previewSize: 42
      });
  }
});
const views = { preview: { component: preview } };
function event(action, source) {
  emit(
    action.type === 'select'
      ? 'select'
      : action.type === 'menu'
        ? 'menu'
        : action.type === 'notes'
          ? 'notes'
          : 'enter',
    action.type === 'select' ? action.value : source
  );
}
let observer;
watch(
  host,
  (element) => {
    observer?.disconnect();
    if (!element) return;
    const measure = () => {
      width.value = frameContentWidth(element);
    };
    measure();
    observer = observeFrameSizes(measure);
    observer.observe(element);
  },
  { flush: 'post' }
);
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="task-mobile-card"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
  </div>
</template>
<style>
.task-mobile-card {
  position: relative;
  width: 100%;
  min-width: 0;
}
.task-mobile-card .frame-button {
  justify-content: flex-start;
  padding: 0;
  background: transparent;
  border: 0;
}
</style>
