<script setup>
// Current Main.qml connectionMenu and ConnectionMixin.ping_server.
import { ref, watch, onBeforeUnmount } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppMenu from '../../controls/AppMenu.vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { networkSettings, updateIntervals, updateModes } from './networkSettings.js'

const props = defineProps({ ticket: String, project: String, online: Boolean, compact: Boolean, updatesError: String, messagesInitialized: Boolean })
const emit = defineEmits(['connection', 'session-expired', 'busy'])
const busy = ref(false), error = ref(''), message = ref('')
let request = 0
async function ping() {
  if (busy.value) return
  const token = ++request
  busy.value = true; emit('busy', true); error.value = ''; message.value = ''
  try {
    await rpc('ping', [{ ticket: props.ticket, project: props.project }])
    if (token !== request) return
    emit('connection', true); message.value = 'TACTIC server responded'
  } catch (failure) {
    if (token !== request) return
    if (failure.code === 'authentication_failed') { emit('session-expired'); return }
    emit('connection', !!failure.status && failure.status < 500); error.value = failure.message
  } finally { if (token === request) { busy.value = false; emit('busy', false) } }
}
watch(() => [props.ticket, props.project], () => { request++; busy.value = false; emit('busy', false); error.value = ''; message.value = '' })
onBeforeUnmount(() => { request++; emit('busy', false) })
</script>

<template>
  <AppMenu class="connection-menu" :class="{ 'connection-menu-compact': compact }" label="Connection" icon="connection">
    <template #trigger><span class="connection-dot" :class="{ online, connecting: busy }"></span><AppIcon class="connection-icon" name="connection" :style="{ color: busy ? 'var(--yellow)' : online ? 'var(--success)' : 'var(--error)' }" /><span class="connection-caption">{{ t(busy ? 'Connecting' : online ? 'Connected' : 'Offline') }}</span></template>
    <strong>{{ t('Connection') }}</strong>
    <AppButton label="Ping now" icon="sync" :disabled="busy" @click="ping" />
    <p v-if="error || updatesError" class="error" role="alert">{{ t(error || updatesError) }}</p><p v-else-if="message" role="status">{{ t(message) }}</p>
    <hr><strong>{{ t('Server updates') }}</strong>
    <AppButton class="menu-status" icon="dynamic-feed" label="Messages, reactions, activity, tasks and presence" disabled><span><span class="menu-status-title">{{ t('Messages, reactions, activity, tasks and presence') }}</span><small>{{ t(networkSettings.updateMode === 'sse' ? 'Server push (SSE)' : 'One batched server request') }}</small></span></AppButton>
    <small v-if="!messagesInitialized" class="muted">{{ t('Chat updates require an initialized messages schema.') }}</small>
    <AppButton v-for="option in updateModes" :key="option.value" :label="option.label" icon="dynamic-feed"
      role="menuitemradio" :aria-checked="networkSettings.updateMode === option.value" @click="networkSettings.updateMode = option.value"><span>{{ t(option.label) }}</span><AppIcon v-if="networkSettings.updateMode === option.value" class="menu-check" name="check-circle" /></AppButton>
    <AppButton v-for="option in networkSettings.updateMode === 'poll' ? updateIntervals : []" :key="option.value" :label="option.label" icon="schedule"
      role="menuitemradio" :aria-checked="networkSettings.pollInterval === option.value" @click="networkSettings.pollInterval = option.value"><span>{{ t(option.label) }}</span><AppIcon v-if="networkSettings.pollInterval === option.value" class="menu-check" name="check-circle" /></AppButton>
  </AppMenu>
</template>

<style scoped>
.connection-menu :deep(.account-panel) { width: min(330px, calc(100vw - 16px)); }
.connection-menu-compact :deep(summary) { width: 100%; justify-content: start; }
.connection-menu-compact .connection-dot { flex-shrink: 0; }
</style>
