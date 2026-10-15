<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import AttachmentCard from '../../controls/AttachmentCard.vue'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import { contextActions as vContextActions } from '../../controls/contextActions.js'
import { t } from '../../i18n.js'
import { attachmentName, formatFileSize, messageDate } from './messages.js'
import { timestampLabel } from '../activity/activity.js'
const props = defineProps({ snapshot: Object, loadFile: Function, compact: Boolean, actionState: Object, entry: Object })
const emit = defineEmits(['open', 'jump', 'action', 'session-expired'])
const menu = ref(null)
const timestamp = computed(() => { const date = messageDate(props.entry?.timestamp); return Number.isNaN(date.getTime()) ? '' : timestampLabel(date.toISOString()) })
const canCopyImage = !!navigator.clipboard?.write && !!globalThis.ClipboardItem
const isImage = () => /^(png|jpe?g|webp|gif|bmp)$/i.test(filename().split('.').at(-1))
const image = ref(''), error = ref('')
let request = 0
const file = () => props.snapshot.__files__?.find(file => !['web', 'icon'].includes(file.type)) || props.snapshot.__files__?.[0]
const filename = () => attachmentName(props.snapshot)
async function load() {
  const id = ++request
  if (image.value) URL.revokeObjectURL(image.value)
  image.value = error.value = ''
  if (props.entry) return
  const preview = props.snapshot.__files__?.find(file => file.type === 'web') || props.snapshot.__files__?.find(file => file.type === 'icon')
  if (!preview) return
  try { const blob = await props.loadFile(props.snapshot, preview); if (id === request) image.value = URL.createObjectURL(blob) }
  catch (failure) { if (id === request) { error.value = failure.message; if (failure.code === 'authentication_failed') emit('session-expired') } }
}
watch(() => props.snapshot.code, load, { immediate: true })
onBeforeUnmount(() => { request++; if (image.value) URL.revokeObjectURL(image.value) })
</script>
<template>
  <div v-context-actions="event => menu.openAt(event)" class="message-attachment" :data-flow-full="!compact && /^(png|jpe?g|webp|gif|bmp|tiff?|tga|exr|hdr|svg|heic|avif)$/i.test(filename().split('.').at(-1)) ? '' : undefined">
    <AppButton v-if="entry" class="chat-file-entry" :icon="snapshot.__files__?.some(file => ['web', 'icon'].includes(file.type)) ? 'image' : 'description'" :aria-label="filename()" :title="filename()" @click="emit('jump', entry.messageId)"><span><strong>{{ filename() }}</strong><small>{{ entry.sender || t('Unknown') }}{{ timestamp ? ' · ' + timestamp : '' }}</small></span></AppButton>
    <AttachmentCard v-else :title="filename()" :extension="filename().split('.').at(-1)" :size-text="formatFileSize(file()?.st_size)" :preview-url="image" :compact="compact" :disabled="actionState?.pending" @activated="emit('open', snapshot)" />
    <AppMenu ref="menu" class="attachment-actions" label="Attachment actions" overlay>
      <AppButton label="Download" icon="download" :disabled="actionState?.pending" @click="emit('action', 'download', snapshot)" />
      <AppButton label="Show folder" icon="folder-open" disabled :title="t('A browser cannot open a folder on your computer.')" />
      <AppButton label="Download and open" icon="MDI_OPEN_IN_NEW" :disabled="actionState?.pending" @click="emit('open', snapshot)" />
      <hr><AppButton label="Copy file path" icon="MDI_CONTENT_COPY" :disabled="actionState?.pending" @click="emit('action', 'copy-path', snapshot)" />
      <AppButton label="Copy web link" icon="link" :disabled="actionState?.pending" @click="emit('action', 'copy-web', snapshot)" />
      <AppButton label="Copy image" icon="image" :disabled="!isImage() || !canCopyImage || actionState?.pending" :title="!canCopyImage ? t('Copying an image requires HTTPS or localhost and clipboard permission.') : undefined" @click="emit('action', 'copy-image', snapshot)" />
    </AppMenu><p v-if="actionState?.error" class="error" role="alert">{{ t(actionState.error) }}</p><p v-if="error" class="error">{{ t(error) }} <AppButton label="Retry" @click="load" /></p></div>
</template>
<style>.message-attachment { position:relative; }.message-attachment > .attachment-actions { position:absolute; right:4px; top:4px; opacity:0; }.message-attachment:hover .attachment-actions, .message-attachment:focus-within .attachment-actions { opacity:1; }.attachment-actions > summary { width:24px; height:24px; min-width:24px; min-height:24px; background:var(--surface-high); }.message-attachment > .attachment-actions[open] { opacity:1; }@media(pointer:coarse) { .message-attachment > .attachment-actions { opacity:1; } }</style>
