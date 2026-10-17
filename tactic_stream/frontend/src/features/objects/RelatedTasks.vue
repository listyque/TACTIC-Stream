<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
const props = defineProps({ related: Object, busy: Boolean, accent: String });
const emit = defineEmits(['open']);
const host = ref(null),
  width = ref(0);
let observer;
const rows = computed(() =>
  (props.related.items || []).map((row, index) => ({
    key: row.task_key,
    parentTitle: row.parent_title,
    process: row.process,
    assigned: row.assigned,
    status: row.status,
    accent: props.accent,
    clickable: true,
    busy: props.busy,
    index
  }))
);
const scene = computed(() =>
  UI.related(
    {
      state: props.related.state,
      count: rows.value.length,
      objectCount: props.related.object_count,
      searchType: props.related.search_type,
      summaryAvailable: props.related.summary_available,
      approved: props.related.approved,
      total: props.related.total,
      accent: props.accent
    },
    width.value,
    appearance.language
  )
);
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section
    ref="host"
    role="region"
    :aria-label="t('Related object tasks')"
    class="related-tasks shared-related-tasks"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :models="{ items: rows }"
      :describe-row="
        (list, record) =>
          UI.relatedRow(record, list.width - 16, appearance.language)
      "
      @event="emit('open', related.items[$event.index])"
    />
  </section>
</template>
<style>
.notes-panel > .shared-related-tasks {
  position: relative;
  display: block;
  min-width: 0;
  flex: none;
  padding: 0;
  margin: 5px 8px;
  width: calc(100% - 16px);
  border: 0;
  overflow: hidden;
}
</style>
