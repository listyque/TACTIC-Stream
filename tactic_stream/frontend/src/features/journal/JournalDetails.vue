<script setup>
// Native transaction_log-conf.xml Details -> log -> XmlWdg, without HTML runtime.
import { ref, watch, onBeforeUnmount } from 'vue'
import { transactionDetails } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import CodeBlock from '../../controls/CodeBlock.vue'
import { copyText } from '../../controls/clipboard.js'

const props = defineProps({ ticket: String, project: String, searchKey: String })
const xml = ref(''), hidden = ref(0), busy = ref(false), error = ref(''), message = ref('')
let request = 0
async function load() {
  const token = ++request
  busy.value = true; error.value = ''; xml.value = ''; message.value = ''; hidden.value = 0
  try {
    const result = await transactionDetails(props.ticket, props.project, props.searchKey)
    if (token !== request) return
    xml.value = result.xml; hidden.value = result.hidden
  } catch (failure) { if (token === request) error.value = failure.message }
  finally { if (token === request) busy.value = false }
}
async function copy() {
  try { await copyText(xml.value); message.value = 'Copied to clipboard' }
  catch { error.value = 'Clipboard access failed. Select and copy the text below.' }
}
watch(() => [props.ticket, props.project, props.searchKey], load, { immediate: true })
onBeforeUnmount(() => { request++ })
</script>

<template>
  <section class="journal-details" :aria-label="t('Transaction details')" :aria-busy="busy">
    <header><strong>{{ t('Transaction XML') }}</strong><AppButton icon="copy" icon-only label="Copy transaction XML" :disabled="busy || !xml" @click="copy" /><AppButton icon="refresh" icon-only label="Refresh transaction details" :disabled="busy" @click="load" /></header>
    <p v-if="busy" class="muted" role="status">{{ t('Loading data…') }}</p>
    <p v-if="error" class="error" role="alert">{{ t(error) }} <AppButton label="Retry" icon="refresh" :disabled="busy" @click="load" /></p>
    <p v-if="message" class="muted" role="status">{{ t(message) }}</p>
    <p v-if="hidden" class="muted">{{ t('{count} journal operations are hidden by access rules.', { count: hidden }) }}</p>
    <CodeBlock v-if="xml" :code="xml" language="xml" />
  </section>
</template>

<style scoped>
.journal-details { min-width: 0; max-width: calc(100vw - var(--section-rail-width) - var(--space-md) * 3); padding: var(--space-md); }
.journal-details header { display: flex; align-items: center; gap: var(--space-sm); }
.journal-details header strong { flex: 1; }
.journal-details .code-block { max-height: min(600px, 60vh); margin-bottom: 0; }
</style>
