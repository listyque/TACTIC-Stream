<script setup>
import { ref, computed, onMounted, onBeforeUnmount, inject } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as Layout from '../../../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/document.ui.mjs';
const openHelp = inject('openHelp', null);
const props = defineProps({ model: Object });
const emit = defineEmits(['action']);
const dialog = ref(null),
  host = ref(null),
  selected = ref(0),
  size = ref({ width: 1, height: 1 });
let observer;
const scene = computed(() =>
  props.model?.layoutNodes
    ? Layout.describe(
        props.model,
        size.value.width,
        size.value.height,
        appearance.language,
        true,
        location.origin
      )
    : UI.describe(
        props.model || {},
        size.value.width,
        size.value.height,
        appearance.language,
        selected.value
      )
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    size.value = {
      width: entries[0].contentRect.width,
      height: entries[0].contentRect.height
    };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({
  open: () => {
    selected.value = 0;
    dialog.value.show();
  },
  close: () => dialog.value.close()
});
</script>
<template>
  <AppDialog
    ref="dialog"
    :title="model?.title || ''"
    :modal="false"
    :translate-title="model?.translateTitle !== false"
    window-kind="table_document"
    :close-on-outside="false"
    class="table-document"
  >
    <div ref="host" class="table-document-body">
      <FrameView
        :scene="scene"
        @event="
          (action) => {
            if (action.type === 'help') openHelp?.(action.topic);
            else if (action.type === 'section')
              selected = Number(action.value) || 0;
            else if (action.type === 'close') dialog.close();
            else emit('action', action);
          }
        "
      />
    </div>
  </AppDialog>
</template>
<style scoped>
.table-document {
  width: 720px;
  height: 560px;
  max-width: calc(100vw - 24px);
  max-height: calc(100dvh - 24px);
}
.table-document-body {
  flex: 1;
  min-height: 0;
  position: relative;
}
.table-document :deep(.app-dialog-content) {
  display: flex;
  flex-direction: column;
  padding: 12px;
  min-height: 0;
}
</style>
