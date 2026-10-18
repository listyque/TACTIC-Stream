<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { contextActions as vContextActions } from '../../controls/contextActions.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import { initials } from './messages.js';
import { extractSkeys } from '../../controls/richText.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/conversation.ui.mjs';
const props = defineProps({
  records: Array,
  selected: String,
  users: Array,
  busy: Boolean
});
const emit = defineEmits(['selected', 'create', 'context']);
const root = ref(null),
  width = ref(252),
  height = ref(500);
let observer;
const geometry = computed(() => UI.layout(width.value, height.value));
const style = (rect) => ({
  left: rect.x + 'px',
  top: rect.y + 'px',
  width: rect.width + 'px',
  height: rect.height + 'px'
});
function model(row, index) {
  const profile =
      props.users?.find(
        (user) =>
          row.recipients?.length === 1 && user.login === row.recipients[0]
      ) || {},
    links = extractSkeys(row.lastMessage || '');
  return {
    ...row,
    index,
    selected: row.conversationId === props.selected,
    avatarUrl: row.previewUrl || profile.avatarUrl,
    acronym: profile.initials || initials(row.title),
    colorIndex: Math.min(4, row.recipients?.length || 0),
    summary: links
      .reduce((text, key) => text.replaceAll(key, ' '), row.lastMessage || '')
      .replace(/\s+/g, ' ')
      .trim(),
    lastMessageLinkedCount: links.length
  };
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries[0].borderBoxSize?.[0];
    if (entries[0].contentRect.width > 0) {
      width.value = box?.inlineSize || root.value.offsetWidth;
      height.value = box?.blockSize || root.value.offsetHeight;
    }
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <aside
    ref="root"
    class="messages-conversations conversation-frame"
    :aria-label="t('Conversations')"
  >
    <FrameView
      :style="style(geometry.header)"
      :scene="UI.heading(geometry.inner, busy, appearance.language)"
      @event="emit('create')"
    />
    <div class="messages-conversation-list" :style="style(geometry.list)">
      <div
        v-for="(row, index) in records"
        :key="row.conversationId"
        class="conversation-frame-row messages-conversation"
        :class="{
          selected: row.conversationId === selected,
          unread: row.unread > 0
        }"
        v-context-actions="
          (event) => emit('context', row.conversationId, event)
        "
      >
        <FrameView
          :scene="
            UI.row(model(row, index), geometry.rowWidth, appearance.language)
          "
          @event="emit('selected', row.conversationId)"
        />
      </div>
    </div>
  </aside>
</template>
<style>
.conversation-frame.messages-conversations {
  position: relative;
  padding: 0;
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
  display: block;
}
.conversation-frame > .frame-view,
.conversation-frame > .messages-conversation-list {
  position: absolute;
}
.conversation-frame .messages-conversation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  scrollbar-gutter: stable;
  padding-right: 2px;
}
.conversation-frame-row {
  height: 68px;
  flex: none;
}
.conversation-frame-row > .frame-view {
  height: 68px;
}
</style>
