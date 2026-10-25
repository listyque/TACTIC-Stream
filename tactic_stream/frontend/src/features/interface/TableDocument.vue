<script setup>
import { ref, computed, onMounted, onBeforeUnmount, inject, watch } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import TableDependencies from './TableDependencies.vue';
import CustomLayoutView from './CustomLayoutView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/document.ui.mjs';
const openHelp = inject('openHelp', null);
const props = defineProps({ model: Object, ticket: String, project: String });
const emit = defineEmits([
  'action',
  'file',
  'closed',
  'edit',
  'inspect',
  'cell-event',
  'column',
  'table-action',
  'saved',
  'notice',
  'print'
]);
const dialog = ref(null),
  pages = ref([]),
  activeKey = ref(''),
  host = ref(null),
  selected = ref(0),
  shown = ref(false),
  size = ref({ width: 1, height: 1 });
let observer;
const activeModel = computed(
  () =>
    pages.value.find((page) => page.key === activeKey.value)?.model ||
    props.model
);
const tabs = computed(() =>
  pages.value
    .filter((page) => page.model.tabKey)
    .map((page) => ({ key: page.key, title: page.model.title }))
);
const scene = computed(() =>
  UI.describe(
    props.model || {},
    size.value.width,
    size.value.height,
    appearance.language,
    selected.value
  )
);
function closePage(key) {
  pages.value = pages.value.filter((page) => page.key !== key);
  if (!pages.value.length) dialog.value.close();
  else activeKey.value = pages.value.at(-1).key;
}
watch(
  () => [props.ticket, props.project],
  () => {
    pages.value = [];
    if (shown.value) dialog.value.close();
  },
  { flush: 'sync' }
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
    if (props.model?.layoutNodes) {
      if (!props.model.tabKey) pages.value = [];
      const key = props.model.tabKey || 'popup';
      if (!pages.value.some((page) => page.key === key))
        pages.value.push({ key, model: props.model });
      activeKey.value = key;
    } else pages.value = [];
    selected.value = 0;
    shown.value = true;
    dialog.value.show();
  },
  close: () => dialog.value.close()
});
</script>
<template>
  <AppDialog
    ref="dialog"
    :title="activeModel?.title || ''"
    :modal="false"
    :translate-title="model?.translateTitle !== false"
    window-kind="table_document"
    :close-on-outside="false"
    class="table-document"
    @closed="
      shown = false;
      pages = [];
      emit('closed');
    "
  >
    <div ref="host" class="table-document-body">
      <TableDependencies
        v-if="shown && model?.kind === 'dependencies'"
        :model="model"
        :width="size.width"
        :height="size.height"
        @close="dialog.close()"
        @file="emit('file', $event)"
      />
      <template v-else-if="shown && pages.length"
        ><CustomLayoutView
          v-for="page in pages"
          :key="page.key"
          v-show="activeKey === page.key"
          :model="page.model"
          :tabs="tabs"
          :current-key="activeKey"
          :ticket="ticket"
          :project="project"
          :width="size.width"
          :height="size.height"
          @action="(...args) => emit('table-action', ...args)"
          @edit="(...args) => emit('edit', ...args)"
          @inspect="emit('inspect', $event)"
          @cell-event="(...args) => emit('cell-event', ...args)"
          @column="emit('column', $event)"
          @saved="emit('saved')"
          @notice="emit('notice', $event)"
          @close="closePage(page.key)"
          @tab="activeKey = $event"
          @close-tab="closePage"
          @print="(...args) => emit('print', ...args)"
      /></template>
      <FrameView
        v-else
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
