<script setup>
import { computed, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { appearance } from '../../appearance.js';
import { mobile } from '../../mobile.js';
import { formatFileSize } from './messages.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/attachments.ui.mjs';
const props = defineProps({ records: Array, busy: Boolean, upload: Boolean });
const emit = defineEmits(['choose', 'paste', 'clear', 'remove', 'open']);
const menu = ref(null),
  anchor = ref(null),
  previews = ref(false);
watch(
  () => props.records.length,
  (count) => {
    if (!count) menu.value?.close();
  }
);
const controls = computed(() =>
  UI.controls(
    {
      count: props.records.length,
      busy: props.busy,
      upload: props.upload,
      clipboard: !mobile.value,
      canCancel: false
    },
    appearance.language
  )
);
const rows = computed(() =>
  props.records.map((row) => ({
    ...row,
    title: row.name,
    size: formatFileSize(row.size),
    error:
      !row.file && !row.snapshot
        ? 'Select this local file again before sending, or remove it.'
        : ''
  }))
);
const row = (node, record) =>
  UI.row(
    {
      ...record,
      previews: previews.value,
      busy: props.busy,
      canOpen: !!record.file || !!record.snapshot
    },
    Math.max(0, node.width - 16),
    appearance.language
  );
const surfaceWidth = computed(() =>
  Math.min(316, mobile.value ? innerWidth - 16 : 316)
);
function action(event, source) {
  if (event.type === 'drafts') {
    anchor.value = source;
    if (menu.value.open) menu.value.close(true);
    else menu.value.openAt({ target: source });
  } else if (event.type === 'previews') previews.value = event.value;
  else if (['remove', 'open'].includes(event.type))
    emit(
      event.type,
      props.records.find((row) => row.token === event.key)
    );
  else if (['choose', 'paste', 'clear'].includes(event.type)) emit(event.type);
}
</script>
<template>
  <div
    class="message-attachment-controls"
    :style="{ width: controls.width + 'px' }"
  >
    <FrameView :scene="controls" @event="action" /><AppMenu
      ref="menu"
      class="message-attachment-drafts"
      label="Attachments to send"
      external-trigger
      :anchor="anchor"
      overlay
      :width="surfaceWidth"
      :close-on-select="false"
      ><FrameView
        :scene="
          UI.panel({ previews }, surfaceWidth - 20, 256, appearance.language)
        "
        :models="{ drafts: rows }"
        :describe-row="row"
        @event="action"
    /></AppMenu>
  </div>
</template>
<style>
.message-attachment-controls {
  position: relative;
  height: 26px;
  flex: none;
}
.message-attachment-controls > .frame-view {
  height: 26px;
}
.message-attachment-drafts {
  position: absolute;
  right: 0;
  top: 0;
  width: 0;
  height: 0;
}
.message-attachment-drafts > .account-panel {
  height: 276px;
  padding: 10px;
}
.message-attachment-drafts > .account-panel > .frame-view {
  height: 100%;
}
</style>
