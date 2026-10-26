<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppMenuItem from '../../controls/AppMenuItem.vue';
import MarkdownText from '../../controls/MarkdownText.vue';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';
import { colors } from '../../../../src/tactic_stream/shared_ui/core/frame.mjs';

const props = defineProps({ frameNode: Object, previews: Object });
const emit = defineEmits(['event']);
const log = ref(null);
const chips = computed(() =>
  UI.contextItems(props.frameNode.context || {}, appearance.language)
);
const rows = computed(() => props.frameNode.messages || []);
watch([rows, () => props.frameNode.status?.text], async () => {
  const element = log.value;
  const follow =
    element &&
    element.scrollHeight - element.scrollTop - element.clientHeight < 60;
  await nextTick();
  if (follow && log.value) log.value.scrollTop = log.value.scrollHeight;
});
const messageStyle = (row) => {
  const geometry = UI.messageGeometry(props.frameNode.width, row.role, 20, 0);
  return {
    width: geometry.width + 'px',
    marginLeft: geometry.x + 'px',
    padding: geometry.padding + 'px',
    marginBottom: UI.metrics.messageGap + 'px'
  };
};
</script>

<template>
  <AppMenu
    v-if="frameNode.view === 'permissions'"
    label="Agent permissions"
    icon="tune"
    compact-trigger
    overlay
    :width="320"
    :disabled="!frameNode.enabled"
  >
    <template v-for="(action, index) in frameNode.actions" :key="index">
      <hr v-if="action.separator" />
      <AppMenuItem
        v-else
        :label="action.title"
        :icon="action.icon"
        :checked="action.checked"
        :role="action.role"
        :disabled="action.enabled === false"
        @click="emit('event', { type: action.command, value: !action.checked })"
      />
    </template>
  </AppMenu>
  <div v-else-if="frameNode.view === 'context'" class="agent-context">
    <div class="agent-context-row">
      <div class="agent-context-chips">
        <span
          v-for="(chip, index) in chips"
          :key="index"
          class="agent-context-chip"
          :title="chip.value"
          :style="{ width: chip.width + 'px' }"
        >
          <AppIcon :name="chip.icon" /><span>{{ chip.value }}</span>
        </span>
      </div>
      <AppButton
        icon-only
        :icon="frameNode.expanded ? 'expand-less' : 'expand-more'"
        label="Context details"
        :aria-expanded="frameNode.expanded"
        @click="emit('event', { type: 'context' })"
      />
    </div>
    <div v-if="frameNode.expanded" class="agent-context-details" tabindex="0">
      {{
        [
          frameNode.context.page,
          frameNode.context.view,
          ...(frameNode.context.search_keys || [])
        ]
          .filter(Boolean)
          .join('\n')
      }}
    </div>
  </div>
  <div
    v-else-if="frameNode.view === 'attachments'"
    class="agent-attachment-strip"
  >
    <div
      v-for="file in frameNode.files"
      :key="file.attachment_id"
      class="agent-attachment-chip"
    >
      <img
        v-if="previews?.[file.attachment_id]"
        :src="previews[file.attachment_id]"
        alt=""
      />
      <AppIcon v-else name="attach-file" />
      <span :title="file.name">{{ file.name }}</span>
      <AppButton
        icon-only
        icon="close"
        label="Remove attachment"
        @click="emit('event', { type: 'remove', value: file.attachment_id })"
      />
    </div>
  </div>
  <div
    v-else
    ref="log"
    class="agent-transcript"
    role="log"
    :aria-label="t('Conversation')"
    aria-live="polite"
  >
    <div v-if="!rows.length" class="agent-chat-empty">
      <AppIcon name="chat" />
      <strong>{{ t('What would you like to change?') }}</strong>
      <span>{{ t('Describe the task. Attach files or paste an image.') }}</span>
    </div>
    <article
      v-for="row in rows"
      :key="row.id"
      class="agent-message"
      :class="row.role"
      :style="messageStyle(row)"
    >
      <MarkdownText :text="UI.safeMarkdown(row.text)" />
      <div
        v-for="file in row.attachments || []"
        :key="file.attachment_id"
        class="agent-message-file"
      >
        <img
          v-if="previews?.[file.attachment_id]"
          class="agent-message-image"
          :src="previews[file.attachment_id]"
          :alt="file.name"
        />
        <AppButton
          :label="file.name"
          icon="attach-file"
          @click="
            emit('event', { type: 'download', value: file.attachment_id })
          "
        />
      </div>
      <small
        v-if="
          frameNode.active && row.role === 'user' && row.delivered === false
        "
        >{{ t('Correction queued') }}</small
      >
    </article>
    <details
      v-if="frameNode.events?.length"
      class="agent-tool-progress"
      :style="messageStyle({ role: 'assistant' })"
      :open="frameNode.active"
    >
      <summary>
        {{
          t(
            frameNode.active
              ? 'Working with TACTIC tools…'
              : 'Operation details'
          )
        }}
      </summary>
      <div v-for="(step, index) in frameNode.events" :key="index">
        {{ step }}
      </div>
    </details>
    <div
      v-if="frameNode.status"
      class="agent-chat-status"
      data-frame="agentRequestStatusRow"
      role="status"
      :style="{
        ...messageStyle({ role: 'assistant' }),
        color: 'var(' + colors[frameNode.status.color] + ')'
      }"
    >
      <AppIcon :name="frameNode.status.icon" />
      <span data-frame="agentRequestStatus">{{ frameNode.status.text }}</span>
    </div>
  </div>
</template>

<style>
.agent-context {
  height: 100%;
  min-width: 0;
}
.agent-context-row {
  display: flex;
  height: 36px;
  gap: 8px;
}
.agent-context-chips {
  display: flex;
  gap: 6px;
  min-width: 0;
  flex: 1;
  overflow-x: auto;
}
.agent-context-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: var(--surface-container);
  font-size: 12px;
}
.agent-context-chip > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-context-row > button {
  width: 28px;
  height: 28px;
  flex: none;
}
.agent-context-details {
  height: 76px;
  white-space: pre-wrap;
  overflow: auto;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--muted);
}
.agent-transcript {
  height: 100%;
  overflow: auto;
  padding: 12px 0;
  scrollbar-gutter: stable;
}
.agent-chat-empty {
  min-height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  color: var(--muted);
  text-align: center;
}
.agent-message {
  box-sizing: border-box;
  border-radius: 12px;
  background: transparent;
  border: 0;
}
.agent-chat-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 20px;
  overflow-wrap: anywhere;
}
.agent-chat-status > .app-icon {
  flex: none;
  width: 18px;
  height: 18px;
  font-size: 18px;
}
.agent-message.user {
  background: var(--surface-high);
}

.agent-message .markdown-text {
  font-size: 13px;
  line-height: 20px;
}
.agent-message-file {
  min-height: 28px;
  font-size: 12px;
  overflow: hidden;
}
.agent-message-image {
  display: block;
  width: min(320px, 100%);
  height: 144px;
  object-fit: contain;
  object-position: left center;
}
.agent-message-file button {
  height: 26px;
  max-width: 100%;
}
.agent-tool-progress {
  box-sizing: border-box;
  margin-top: 4px;
  overflow-wrap: anywhere;
  color: var(--muted);
  font-size: 12px;
}
.agent-tool-progress div {
  margin: 6px 0;
}
.agent-attachment-strip {
  height: 36px;
  display: flex;
  gap: 8px;
  overflow-x: auto;
}
.agent-attachment-chip {
  flex: none;
  display: flex;
  align-items: center;
  gap: 6px;
  width: 210px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 2px 4px;
  font-size: 12px;
}
.agent-attachment-chip img {
  width: 28px;
  height: 28px;
  object-fit: contain;
}
.agent-attachment-chip > span {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.agent-attachment-chip button {
  width: 26px;
  height: 26px;
  flex: none;
}
</style>
