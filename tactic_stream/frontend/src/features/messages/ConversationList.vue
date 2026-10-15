<script setup>
import AppButton from '../../controls/AppButton.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import { contextActions as vContextActions } from '../../controls/contextActions.js'
import { tooltipDirective as vTooltip } from '../../controls/tooltip.js'
import { t } from '../../i18n.js'
import { initials, conversationColor } from './messages.js'
defineProps({ records: Array, selected: String, users: Array, busy: Boolean })
const emit = defineEmits(['selected', 'create', 'context'])
function profile(row, users) { return users.find(user => row.recipients?.length === 1 && user.login === row.recipients[0]) || {} }
</script>
<template>
  <aside class="messages-conversations" :aria-label="t('Conversations')">
    <header><strong>{{ t('CONVERSATIONS') }}</strong><AppButton icon-only icon="MDI_ACCOUNT_MULTIPLE_PLUS" label="New conversation" :disabled="busy" @click="emit('create')" /></header>
    <div class="messages-conversation-list">
      <AppButton v-for="row in records" :key="row.conversationId" v-context-actions="event => emit('context', row.conversationId, event)" class="messages-conversation" :class="{ selected: row.conversationId === selected, unread: row.unread > 0 }" :style="{ '--conversation-accent': conversationColor(row) }"
        :aria-label="row.isPersonalNotes ? t('Favorites') : row.title" :aria-current="row.conversationId === selected ? 'true' : undefined" @click="emit('selected', row.conversationId)">
        <ItemPreview :source="row.previewUrl || profile(row, users).avatarUrl" :fallback-text="row.isPersonalNotes ? '' : initials(row.title)" :fallback-icon="row.isPersonalNotes ? 'MDI_BOOKMARK_OUTLINE' : undefined"
          :accent="conversationColor(row)" :preview-size="34" round outlined />
        <span class="conversation-text"><strong>{{ row.isPersonalNotes ? t('Favorites') : row.title }}</strong><small>{{ row.isPersonalNotes ? t('Your personal notes') : t('{count} members', { count: row.participantCount }) }}</small>
          <small>{{ row.lastMessage ? (row.lastSender ? row.lastSender + ': ' : '') + row.lastMessage.replace(/\s+/g, ' ') : t('No messages yet') }}</small></span>
        <span v-if="row.mentionCount > 0" v-tooltip="t('{count} unread mentions', { count: row.mentionCount })" class="messages-count messages-mention" role="img" :aria-label="t('{count} unread mentions', { count: row.mentionCount })">@</span>
        <span v-if="row.unread" class="messages-count">{{ row.unread > 99 ? '99+' : row.unread }}</span>
      </AppButton>
    </div>
  </aside>
</template>
