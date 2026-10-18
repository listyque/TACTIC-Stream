<script setup>
import {
  computed,
  ref,
  onMounted,
  onBeforeUnmount,
  markRaw,
  nextTick
} from 'vue';
import AppDialog from '../../../controls/AppDialog.vue';
import FrameView from '../../../frame/FrameView.vue';
import QueuePreview from './QueuePreview.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import { t } from '../../../i18n.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/queue/previews.ui.mjs';
import * as Confirmation from '../../../../../src/tactic_stream/shared_ui/controls/feedback/confirmation.ui.mjs';

const props = defineProps({
  model: Object,
  rows: Array,
  files: Object,
  owner: Object
});
const emit = defineEmits(['event', 'clear']);
const clearDialog = ref(null),
  previewsDialog = ref(null),
  clearContent = ref(null),
  previewsContent = ref(null),
  clearWidth = ref(380),
  viewport = ref({ width: 480, height: 346 }),
  previewsOpen = ref(false);
const confirmation = computed(() =>
  Confirmation.describe(
    {
      message: t(
        'All prepared, failed and completed operations will be removed from the queue.'
      ),
      accept: 'Clear queue',
      destructive: true,
      busy: props.model.busy
    },
    clearWidth.value,
    170,
    appearance.language
  )
);
const scene = computed(() =>
  UI.describe(
    {
      count: props.rows.length,
      canEdit: !props.model.busy && props.model.record?.canPreview
    },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const previewComponent = markRaw(QueuePreview);
const views = computed(() => ({
  preview: {
    component: previewComponent,
    nodeProps: true,
    props: { files: props.files }
  }
}));
const describeRow = (list, record) =>
  UI.row(record, list.width - 16, appearance.language);
function dispatch(action) {
  if (action.type === 'preview' && action.command === 'close')
    previewsDialog.value.close();
  else emit('event', action);
}
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries) {
      if (entry.contentRect.width <= 0) continue;
      if (entry.target === clearContent.value)
        clearWidth.value = entry.contentRect.width;
      else
        viewport.value = {
          width: entry.contentRect.width,
          height: entry.contentRect.height
        };
    }
  });
  observer.observe(clearContent.value);
  observer.observe(previewsContent.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({
  close() {
    clearDialog.value.close();
    previewsDialog.value.close();
  },
  clear() {
    clearDialog.value.show(props.owner);
  },
  async previews() {
    previewsOpen.value = true;
    await nextTick();
    previewsDialog.value.show(props.owner);
  }
});
</script>
<template>
  <Teleport to="body">
    <AppDialog
      ref="clearDialog"
      class="commit-queue-clear-dialog"
      title="Clear commit queue?"
      :owner-margin="UI.metrics.ownerMargin"
      :close-on-escape="!model.busy"
      :close-on-outside="!model.busy"
      :style="{ width: UI.metrics.clearWidth + 'px' }"
    >
      <div ref="clearContent" class="commit-queue-clear-content">
        <FrameView
          :scene="confirmation"
          @event="
            $event.type === 'accept'
              ? (emit('clear'), clearDialog.close())
              : clearDialog.close()
          "
        />
      </div>
    </AppDialog>
    <AppDialog
      ref="previewsDialog"
      class="commit-queue-previews-dialog"
      title="Operation previews"
      :modal="false"
      :owner-margin="UI.metrics.ownerMargin"
      :style="{
        width: UI.metrics.width + 'px',
        height: UI.metrics.height + 'px'
      }"
      @closed="previewsOpen = false"
    >
      <div ref="previewsContent" class="commit-queue-previews-content">
        <FrameView
          v-if="previewsOpen"
          :scene="scene"
          :models="{ previews: rows }"
          :views="views"
          :describe-row="describeRow"
          @event="dispatch"
        />
      </div>
    </AppDialog>
  </Teleport>
</template>
<style>
.commit-queue-clear-content {
  position: relative;
  height: 170px;
}
.commit-queue-previews-content {
  position: relative;
  min-height: 0;
  flex: 1;
}
</style>
