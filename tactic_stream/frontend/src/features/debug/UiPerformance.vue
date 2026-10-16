<script setup>
// Current Handler UiPerformanceView.qml, EPL-1.0.
import { ref, computed, onBeforeUnmount, onMounted, nextTick } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import { copyText } from '../../controls/clipboard.js';
import { t } from '../../i18n.js';
import { uiPerformance } from './uiPerformance.js';
import './uiPerformance.css';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/diagnostics/performance.ui.mjs';

const dialog = ref(null),
  selectedId = ref(0),
  message = ref(''),
  failed = ref(false);
const emit = defineEmits(['closed']);
const selected = computed(() =>
  uiPerformance.state.samples.find(
    (sample) => sample.sampleId === selectedId.value
  )
);
const summary = computed(() => uiPerformance.state.summary);
onBeforeUnmount(() => uiPerformance.setVisible(false));
const body = ref(null),
  frame = ref(null),
  viewport = ref({ width: 880, height: 600 });
const model = computed(() => ({
  recording: uiPerformance.state.recording,
  summary: summary.value,
  selectedId: selectedId.value,
  selected: selected.value,
  browserFrames: true,
  message: message.value,
  failed: failed.value
}));
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const row = (list, record) =>
  UI.row(model.value, record, list.width - 16, appearance.language);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'record')
    uiPerformance.setRecording(!uiPerformance.state.recording);
  else if (action.type === 'copy') copy();
  else if (action.type === 'clear') clear();
  else if (action.type === 'sample') selectedId.value = action.record.sampleId;
  else if (action.type === 'sampleKey') {
    const target = UI.selection(
      uiPerformance.state.samples,
      action.id,
      action.key
    );
    if (target) {
      selectedId.value = target.sampleId;
      nextTick(() =>
        frame.value?.focusListRow(
          'uiPerformanceSamples',
          uiPerformance.state.samples.findIndex(
            (record) => record.sampleId === target.sampleId
          ),
          'sample_' + target.sampleId
        )
      );
    }
  }
}
function open() {
  message.value = '';
  dialog.value.show();
  uiPerformance.setVisible(true);
}
function close() {
  dialog.value.close();
  uiPerformance.setVisible(false);
}
function clear() {
  uiPerformance.clear();
  selectedId.value = 0;
  message.value = '';
}
async function copy() {
  try {
    await copyText(uiPerformance.copyResults());
    failed.value = false;
    message.value = 'Copied to clipboard';
  } catch {
    failed.value = true;
    message.value = 'Clipboard access failed';
  }
}
defineExpose({ open });
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'ui_performance', type: 'window' }"
      ref="dialog"
      class="ui-performance-dialog"
      :aria-label="t('UI responsiveness')"
      @cancel.prevent="close"
      @close="
        uiPerformance.setVisible(false);
        emit('closed');
      "
    >
      <header class="ui-performance-heading">
        <AppIcon name="MDI_SPEEDOMETER" /><strong>{{
          t('UI responsiveness')
        }}</strong
        ><AppButton
          icon-only
          icon="close"
          label="Close UI responsiveness"
          @click="close"
        />
      </header>
      <div ref="body" class="ui-performance-screen">
        <FrameView
          ref="frame"
          :scene="scene"
          :models="{ samples: uiPerformance.state.samples }"
          :describe-row="row"
          @event="dispatch"
        />
      </div>
    </dialog>
  </Teleport>
</template>
