<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { timestampLabel, timestampFullLabel } from '../activity/activity.js';
import { messageDate } from './messages.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/message.ui.mjs';
const props = defineProps({
  row: Object,
  user: Object,
  login: String,
  busy: Boolean,
  pinned: Boolean,
  selected: Boolean,
  selectionMode: Boolean,
  permissions: Object,
  hovered: Boolean,
  focused: Boolean,
  touch: Boolean,
  now: Number,
  padding: Number,
  maximumWidth: Number
});
const emit = defineEmits(['event']);
const root = ref(null),
  width = ref(240);
let observer;
const model = computed(() => ({
  sender: props.row.login,
  senderDisplay: props.user?.displayName || props.row.login,
  senderColor: props.user?.avatarColor || 'action',
  first: props.row.groupFirst,
  time: timestampLabel(
    messageDate(props.row.timestamp).toISOString(),
    props.now ? new Date(props.now) : undefined
  ),
  fullTime: timestampFullLabel(props.row.timestamp),
  edited: !!props.row.__edit_history__?.length,
  editedBy: props.row.__edit_history__?.at(-1)?.editedBy,
  editedAt: props.row.__edit_history__?.at(-1)?.editedAt,
  own: props.row.login === props.login,
  recipientCount: props.row.__delivery__?.recipientCount || 0,
  readCount: props.row.__delivery__?.readCount || 0,
  deliveredCount: props.row.__delivery__?.deliveredCount || 0,
  deliveryStatus: props.row.__delivery__?.status || 'sent',
  busy: props.busy,
  pinned: props.pinned,
  selected: props.selected,
  selectionMode: props.selectionMode,
  canReact: props.permissions?.reaction,
  canPin: props.permissions?.pin,
  hovered: props.hovered,
  focused: props.focused,
  touch: props.touch,
  padding: props.padding
}));
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="root"
    class="message-frame-header"
    :style="{
      minWidth:
        Math.min(
          UI.header(model, width, appearance.language).naturalWidth,
          maximumWidth || 9999
        ) + 'px'
    }"
  >
    <FrameView
      :scene="UI.header(model, width, appearance.language)"
      @event="(action, source) => emit('event', action, source)"
    />
  </div>
</template>
<style>
.message-frame-header {
  position: relative;
  flex: none;
  height: 18px;
  min-width: 0;
}
.message-frame-header > .frame-view {
  height: 18px;
}
</style>
