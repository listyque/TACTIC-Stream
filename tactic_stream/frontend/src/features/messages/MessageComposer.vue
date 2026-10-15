<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import EmojiPicker from '../../controls/EmojiPicker.vue'
import AppButton from '../../controls/AppButton.vue'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
const props = defineProps({ modelValue: String, sending: Boolean, disabled: Boolean, members: Array, hasAttachments: Boolean, label:{type:String,default:'Write a reply'},sendLabel:{type:String,default:'Send'} })
const emit = defineEmits(['update:modelValue', 'submit', 'files'])
const field = ref(null), mention = ref(null), activeMention = ref(0)
const matches = computed(() => props.members.filter(row => (row.login + ' ' + (row.displayName || '')).toLowerCase().includes((mention.value || '').toLowerCase())))
const optionId = login => 'message-mention-' + encodeURIComponent(login)
function findMention() { if (props.sending || props.disabled) { mention.value = null; return }; const match = field.value.value.slice(0, field.value.selectionStart).match(/(?:^|\s)@([A-Za-z0-9_.-]*)$/); mention.value = match ? match[1] : null; activeMention.value = 0 }
function input() { emit('update:modelValue', field.value.value); findMention() }
async function insert(value, replace = 0) {
  if (props.disabled || props.sending) return
  const start = field.value.selectionStart, end = field.value.selectionEnd
  emit('update:modelValue', props.modelValue.slice(0, start - replace) + value + props.modelValue.slice(end)); mention.value = null
  await nextTick(); field.value.focus(); field.value.setSelectionRange(start - replace + value.length, start - replace + value.length)
}
function key(event) {
  if (event.key === 'Escape' && mention.value !== null) { event.preventDefault(); event.stopPropagation(); mention.value = null; return }
  if (mention.value !== null && matches.value.length && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key) && !event.isComposing && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    if (event.key === 'Enter') { if (!event.repeat) insert('@' + matches.value[activeMention.value].login + ' ', mention.value.length + 1) }
    else { activeMention.value = (activeMention.value + (event.key === 'ArrowDown' ? 1 : matches.value.length - 1)) % matches.value.length; nextTick(() => document.getElementById(optionId(matches.value[activeMention.value]?.login))?.scrollIntoView({ block: 'nearest' })) }
    return
  }
  if (event.key !== 'Enter' || event.isComposing || mobile.value) return
  event.preventDefault()
  if (props.disabled || props.sending || event.repeat) return
  if (event.ctrlKey || event.metaKey) { event.preventDefault(); insert('\n') }
  else emit('submit')
}
watch(() => props.modelValue, value => { if (value !== field.value?.value) mention.value = null })
watch(() => props.sending || props.disabled, value => { if (value) mention.value = null })
defineExpose({ focus() { field.value?.focus() } })
</script>
<template>
  <div class="message-composer">
    <div class="message-composer-field"><textarea ref="field" :value="modelValue" :disabled="disabled" :readonly="sending" :aria-label="t(label)" :placeholder="t(label === 'Note text' ? mobile ? 'Write a note' : 'Write a note · Enter to send · Ctrl+Enter for a new line' : mobile ? 'Write a reply' : 'Write a reply · Enter to send · Ctrl+Enter for a new line')" :aria-controls="mention !== null && matches.length ? 'message-mentions' : undefined" :aria-activedescendant="mention !== null && matches.length ? optionId(matches[activeMention]?.login) : undefined" aria-autocomplete="list" rows="1" @input="input" @click="findMention" @keydown="key" @paste="event => { if (event.clipboardData.files.length && !sending && !disabled) { event.preventDefault(); emit('files', event.clipboardData.files) } }"></textarea><EmojiPicker label="Insert emoji" :disabled="disabled || sending" @selected="insert" /></div>
    <div v-if="mention !== null && matches.length" id="message-mentions" class="message-mentions" role="listbox" :aria-label="t('Mention a member')"><AppButton v-for="(member, index) in matches" :id="optionId(member.login)" :key="member.login" role="option" :aria-selected="index === activeMention" :tonal="index === activeMention" @click="insert('@' + member.login + ' ', mention.length + 1)">{{ member.displayName || member.login }} · @{{ member.login }}</AppButton></div>
    <AppButton class="message-send" :icon-only="mobile || label === 'Note text'" :label="sending ? 'Sending' : sendLabel" icon="MDI_SEND" highlighted :disabled="disabled || sending || !modelValue.trim() && !hasAttachments" @click="emit('submit')" />
  </div>
</template>
