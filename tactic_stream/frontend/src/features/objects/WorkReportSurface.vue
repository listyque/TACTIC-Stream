<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/workhours/reports.ui.mjs';
const props = defineProps({ data: Object, report: String, busy: Boolean });
const emit = defineEmits(['report', 'refresh']);
const host = ref(null),
  width = ref(600),
  height = ref(400);
const options = computed(() =>
  (props.data?.reports || []).map((row) => ({ ...row, key: row.value }))
);
const values = computed(() =>
  (props.data?.rows || []).map((row) => ({
    ...row,
    valueLabel:
      props.data.unit === 'cost'
        ? Number(row.value).toFixed(2)
        : row.value + ' h'
  }))
);
const model = computed(() => ({
  report: props.report,
  busy: props.busy,
  count: values.value.length,
  options: options.value,
  weekStart: props.data?.week_start,
  weekEnd: props.data?.week_end,
  message: props.data?.message
}));
const scene = computed(() =>
  UI.describe(model.value, width.value, height.value, appearance.language)
);
function row(list, record) {
  return list.source === 'reports'
    ? UI.descriptor(
        record,
        model.value,
        Math.max(0, list.width - 16),
        appearance.language
      )
    : UI.valueRow(record, Math.max(0, list.width - 16), appearance.language);
}
let observer;
onMounted(() => {
  observer = observeFrameSizes(() => {
    width.value = host.value.clientWidth;
    height.value = host.value.clientHeight;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="work-report-surface">
    <FrameView
      :scene="scene"
      :models="{ reports: options, values }"
      :describe-row="row"
      @event="
        (action) =>
          action.type === 'report'
            ? emit('report', action.value)
            : emit('refresh')
      "
    />
  </div>
</template>
<style>
.work-report-surface {
  position: relative;
  min-height: 300px;
  flex: 1;
}
</style>
