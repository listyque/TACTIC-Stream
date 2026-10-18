<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import EmojiPicker from '../../controls/EmojiPicker.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import AttachmentItem from './AttachmentItem.vue'
import MessageReference from './MessageReference.vue'
import ResponsiveFlow from '../../controls/ResponsiveFlow.vue'
import SKeyPreviewCard from '../objects/SKeyPreviewCard.vue'
import { skeyPlaceholder } from '../objects/skeyPreviews.js'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
import { tooltipDirective as vTooltip } from '../../controls/tooltip.js'
import { contextActions as vContextActions } from '../../controls/contextActions.js'
import { appearance } from '../../appearance.js'
import { timestampLabel, timestampFullLabel } from '../activity/activity.js'
import { linkifyPlainText, activateRichLink, extractSkeys, withoutSkeys } from '../../controls/richText.js'
import { initials, messageId, messageDate, messageAttachments, attachmentName, bubbleContour, emojiCount } from './messages.js'
const props = defineProps({ row: Object, login: String, user: Object, users: Array, selected: Boolean, selectionMode: Boolean, canEdit: Boolean, permissions: Object, busy: Boolean, pinned: Boolean, loadFile: Function, fileActions: Object, previews: Object, now: Number })
const emit = defineEmits(['action', 'attachment-action', 'reaction', 'link', 'jump', 'session-expired', 'preview-retry', 'copy-link'])
const bubble = ref(null), menu = ref(null), size = ref({ width: 0, height: 0, corner: 14 })
const contour = computed(() => bubbleContour(size.value.width, size.value.height, size.value.corner, props.row.groupLast))
const stickers = computed(() => emojiCount(props.row.message))
const media = computed(() => messageAttachments(props.row).some(snapshot => /^(png|jpe?g|webp|gif|bmp|tiff?|tga|exr|hdr|svg|heic|avif)$/i.test(attachmentName(snapshot).split('.').at(-1))))
let observer
function measure() { if (bubble.value) { const box = bubble.value.getBoundingClientRect(), corner = parseFloat(getComputedStyle(bubble.value).borderTopLeftRadius); if (box.width && box.height && (box.width !== size.value.width || box.height !== size.value.height || corner !== size.value.corner)) size.value = { width: box.width, height: box.height, corner } } }
onMounted(() => { observer = new ResizeObserver(measure); observer.observe(bubble.value); measure() })
onBeforeUnmount(() => observer?.disconnect())
watch(() => appearance.theme, measure, { flush: 'post' })
function timestamp(value, full = false) { const date = messageDate(value); return Number.isNaN(date.getTime()) ? '' : full ? timestampFullLabel(date.toISOString()) : timestampLabel(date.toISOString(), new Date(props.now || Date.now())) }
function delivery(value) { return value?.status === 'read' ? t('Read by {count} of {total}', { count: value.readCount, total: value.recipientCount }) : value?.status === 'delivered' ? t('Delivered to {count} of {total}', { count: value.deliveredCount, total: value.recipientCount }) : t('Sent') }
function edited(row) { const entry = row.__edit_history__?.at(-1); return entry ? t('Last edited by {name} · {time}', { name: entry.editedBy, time: entry.editedAt }) : '' }
const action = (name, row) => emit('action', name, row)
function selectMessage(event) { if (props.selectionMode && !event.target.closest('.message-buttons, .workspace-menu')) { event.preventDefault(); event.stopPropagation(); action('select', props.row) } }
</script>
<template>
  <article v-context-actions="event => menu.openAt(event)" class="message-row" :class="{ outgoing: row.login === login, 'group-first': row.groupFirst, 'group-last': row.groupLast, 'forward-selected': selected, 'media-attachments': media }" :data-message-id="messageId(row)">
    <AppButton v-if="row.groupLast" class="message-author-action" :aria-label="t('Open profile for {name}', { name:row.login })" @click="action('profile',row.login)"><ItemPreview class="message-author" :source="user?.avatarUrl" :fallback-text="user?.initials || initials(row.login)" :accent="user?.avatarColor || 'var(--primary)'" :preview-size="40" round outlined /></AppButton>
    <div ref="bubble" class="message-bubble" :style="{ '--sender-color': user?.avatarColor || 'var(--primary)' }" @click.capture="selectMessage">
      <svg v-if="size.width && size.height" class="message-contour" :viewBox="`0 0 ${size.width + 16} ${size.height + 4}`" aria-hidden="true" focusable="false"><path :d="contour" /></svg>
      <header><AppButton v-if="row.groupFirst" class="message-sender" :aria-label="t('Open profile for {name}', { name:row.login })" @click="action('profile',row.login)"><strong>{{ user?.displayName && user.displayName !== row.login ? user.displayName + ' (' + row.login + ')' : row.login }}</strong></AppButton><span v-else class="message-metadata-spacer"></span><span v-if="row.login === login && row.__delivery__?.recipientCount" v-tooltip="delivery(row.__delivery__)" class="message-delivery" :class="{ read: row.__delivery__.status === 'read', sent: row.__delivery__.status === 'sent' }" tabindex="0" role="img" :aria-label="delivery(row.__delivery__)"><AppIcon :name="row.__delivery__.status === 'sent' ? 'MDI_CHECK' : 'MDI_CHECK_ALL'" /></span><time v-tooltip="timestamp(row.timestamp, true)" tabindex="0" :aria-label="row.timestamp">{{ timestamp(row.timestamp) }}</time>
        <AppButton v-if="row.__edit_history__?.length" :tooltip="edited(row)" class="message-edited" label="Edited" @click="action('history', row)" />
        <div class="message-buttons">
          <AppButton v-if="selectionMode" icon-only :label="selected ? 'Deselect message' : 'Select message'" :icon="selected ? 'MDI_CHECK_CIRCLE' : 'MDI_CIRCLE_OUTLINE'" :aria-pressed="selected" :disabled="busy" @click="action('select', row)" />
          <AppButton v-if="pinned" class="message-pin-action" icon-only icon="pin" label="Unpin message" :disabled="busy || !permissions.pin" @click="action('pin', row)" />
          <EmojiPicker v-if="permissions.reaction && !mobile" class="message-react-picker" label="Add reaction" :disabled="busy" @selected="emit('reaction', row, $event)" />
          <AppMenu ref="menu" class="message-actions" label="Message actions" overlay>
            <EmojiPicker v-if="mobile && permissions.reaction" text-trigger label="Add reaction" :disabled="busy" @selected="menu.close(); emit('reaction', row, $event)" />
            <AppButton label="Reply" icon="MDI_REPLY" :disabled="!permissions.send" @click="action('reply', row)" />
            <AppButton label="Forward" icon="MDI_SHARE" :disabled="!permissions.forward" @click="action('forward', row)" />
            <AppButton :label="selected ? 'Deselect message' : 'Select message'" icon="MDI_CHECKBOX_MARKED_OUTLINE" @click="action('select', row)" />
            <AppButton label="Copy text" icon="MDI_CONTENT_COPY" @click="action('copy', row)" /><AppButton label="Copy sKey" icon="MDI_LINK" @click="action('skey', row)" />
            <AppButton :label="pinned ? 'Unpin message' : 'Pin message'" icon="pin" :disabled="!permissions.pin || busy" @click="action('pin', row)" />
            <AppButton v-if="row.__edit_history__?.length" label="Edit history" icon="MDI_HISTORY" @click="action('history', row)" />
            <AppButton label="Edit message" icon="MDI_PENCIL" :disabled="!canEdit || busy" @click="action('edit', row)" />
            <AppButton label="Delete message" icon="MDI_DELETE" destructive :disabled="!canEdit || busy || !permissions['delete-message']" @click="action('delete-message', row)" />
          </AppMenu>
        </div>
      </header>
      <MessageReference v-if="row.__reply__" :reference="row.__reply__" :users="users" @activate="emit('jump', row.__reply__.messageId)" />
      <MessageReference v-if="row.__forwarded_from__" :reference="row.__forwarded_from__" :users="users" forwarded @activate="action('original', row.__forwarded_from__)" />
      <ResponsiveFlow v-if="messageAttachments(row).length" :minimum-cell-width="210" :maximum-columns="2"><AttachmentItem v-for="snapshot in messageAttachments(row)" :key="snapshot.code" :snapshot="snapshot" :load-file="loadFile" :action-state="fileActions?.[snapshot.code]" @open="action('attachment', $event)" @action="(name, snapshot) => emit('attachment-action', name, snapshot)" @session-expired="emit('session-expired')" /></ResponsiveFlow>
      <div v-if="withoutSkeys(row.message)" class="message-body" :class="{ 'emoji-only': stickers }" :style="stickers ? { fontSize: 'var(--text-emoji-' + stickers + ')' } : undefined" v-html="linkifyPlainText(withoutSkeys(row.message))" @click="activateRichLink($event, value => emit('link', value))"></div>
      <div v-if="extractSkeys(row.message).length" class="message-skey-previews"><SKeyPreviewCard v-for="key in extractSkeys(row.message)" :key="key" :preview="previews?.[key] || skeyPlaceholder(key)" :previews="previews" :now="now" @open="emit('link', $event)" @retry="emit('preview-retry', $event)" @copy="emit('copy-link', $event)" /></div>
      <div v-if="Object.keys(row.__reactions__ || {}).length" class="message-reactions"><AppButton v-for="(actors, emoji) in row.__reactions__" :key="emoji" :tooltip="actors.join(', ')" :aria-label="t('React with {emoji}', { emoji })" :tonal="actors.includes(login)" :disabled="busy || !permissions.reaction" @click="emit('reaction', row, emoji)">{{ emoji }}<small v-if="actors.length > 1">{{ actors.length }}</small></AppButton></div>
    </div>
  </article>
</template>
