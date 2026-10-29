<script setup>
import { computed, ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppButton from '../../controls/AppButton.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.state.mjs';
import { cellValue } from './rawCellValues.js';

const props = defineProps({ busy: Boolean }),
  emit = defineEmits(['applied']);
const dialog = ref(null),
  frame = ref(null),
  body = ref(null),
  cell = ref(null),
  ui = ref(State.cellInitial({})),
  error = ref(''),
  viewport = ref({ width: 640, height: 440 });
let sequence = 0,
  observer = null;
const model = computed(() => ({
  ...cell.value,
  busy: props.busy,
  error: error.value
}));
const scene = computed(() =>
  UI.cellDescribe(
    model.value,
    ui.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
function close() {
  if (dialog.value?.open) dialog.value.close();
  cell.value = null;
  ui.value = State.cellInitial({});
}
async function open(scope) {
  cell.value = { ...scope, session: ++sequence };
  ui.value = State.cellInitial(cell.value);
  error.value = '';
  await nextTick();
  dialog.value.showModal();
  viewport.value = {
    width: body.value.clientWidth,
    height: body.value.clientHeight
  };
  await nextTick();
  frame.value.focusControl('rawCellValue');
}
function dispatch(event) {
  const result = State.cellTransition(ui.value, model.value, event);
  ui.value = result.ui;
  for (const command of result.commands) {
    if (command.type === 'cancel') {
      close();
      continue;
    }
    if (command.type !== 'apply')
      throw Error('Unsupported Cell editor command: ' + command.type);
    try {
      if (command.mode !== 'default')
        cellValue(command.text, cell.value.type, command.mode);
      else if (!cell.value.newRow) throw Error('Default requires a new row');
      emit('applied', {
        ...cell.value,
        mode: command.mode,
        text: command.mode === 'value' ? command.text : ''
      });
      close();
    } catch {
      error.value = 'Enter a valid value for the column type.';
    }
  }
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries)
      if (entry.contentRect.width && entry.contentRect.height)
        viewport.value = {
          width: entry.contentRect.width,
          height: entry.contentRect.height
        };
  });
  observer.observe(body.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  close();
});
defineExpose({ open, close, ui, scene, model });
</script>
<template>
  <dialog
    ref="dialog"
    v-window="{ kind: 'raw_cell' }"
    class="record-dialog raw-cell-editor frame-dialog"
    :aria-label="t('Cell editor')"
    @cancel.prevent="dispatch({ type: 'cancel' })"
    @keydown.ctrl.enter.prevent="dispatch({ type: 'apply' })"
  >
    <header class="app-dialog-titlebar">
      <h2>{{ t('Cell editor') }}</h2>
      <AppButton
        label="Close"
        icon="close"
        icon-only
        @click="dispatch({ type: 'cancel' })"
      />
    </header>
    <div ref="body" class="frame-host-body">
      <FrameView ref="frame" :scene="scene" @event="dispatch" />
    </div>
  </dialog>
</template>

<style>
.raw-cell-editor.frame-dialog.app-window[open] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.raw-cell-editor.frame-dialog.app-window > header.app-dialog-titlebar {
  margin-bottom: 0 !important;
}
.raw-cell-editor > .frame-host-body {
  overflow: hidden;
}
</style>
