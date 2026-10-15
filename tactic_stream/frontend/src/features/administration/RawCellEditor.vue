<script setup>
import { computed, ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/database/raw.state.mjs';
import { cellValue } from './rawCellValues.js';

const props = defineProps({ busy: Boolean }),
  emit = defineEmits(['applied']);
const dialog = ref(null),
  frame = ref(null),
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
    width: dialog.value.clientWidth,
    height: dialog.value.clientHeight
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
  observer = new ResizeObserver((entries) => {
    for (const entry of entries)
      if (entry.contentRect.width && entry.contentRect.height)
        viewport.value = {
          width: entry.contentRect.width,
          height: entry.contentRect.height
        };
  });
  observer.observe(dialog.value);
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
    v-window="{ kind: 'raw_cell', backProvided: true }"
    class="record-dialog raw-cell-editor frame-dialog"
    :aria-label="t('Cell editor')"
    @cancel.prevent="dispatch({ type: 'cancel' })"
    @keydown.ctrl.enter.prevent="dispatch({ type: 'apply' })"
  >
    <FrameView ref="frame" :scene="scene" @event="dispatch" />
  </dialog>
</template>
