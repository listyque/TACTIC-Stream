<script setup>
// Current Main.qml connectionMenu and ConnectionMixin.ping_server.
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
import menus from '../../../../src/tactic_stream/shared_ui/shell/main.menus.json';
import { compose } from '../../../../src/tactic_stream/shared_ui/shell/main.menus.mjs';
import AppIcon from '../../controls/AppIcon.vue';
import { networkSettings } from './networkSettings.js';

const props = defineProps({
  ticket: String,
  project: String,
  online: Boolean,
  compact: Boolean,
  updatesError: String,
  messagesInitialized: Boolean
});
const emit = defineEmits(['connection', 'session-expired', 'busy']);
const busy = ref(false),
  error = ref(''),
  message = ref('');
let request = 0;
const menu = ref(null);
const actions = computed(() =>
  compose(menus.connection, {
    platform: 'stream',
    updateMode: networkSettings.updateMode,
    pollInterval: networkSettings.pollInterval,
    pingBusy: busy.value,
    messagesInitialized: props.messagesInitialized
  })
);
function invoke(command) {
  menu.value.close(true);
  if (command === 'ping_now') ping();
  else if (command.startsWith('update_mode_'))
    networkSettings.updateMode = command.slice(12);
  else if (command.startsWith('updates_'))
    networkSettings.pollInterval = Number(command.slice(8));
}
async function ping() {
  if (busy.value) return;
  const token = ++request;
  busy.value = true;
  emit('busy', true);
  error.value = '';
  message.value = '';
  try {
    await rpc('ping', [{ ticket: props.ticket, project: props.project }]);
    if (token !== request) return;
    emit('connection', true);
    message.value = 'TACTIC server responded';
  } catch (failure) {
    if (token !== request) return;
    if (failure.code === 'authentication_failed') {
      emit('session-expired');
      return;
    }
    emit('connection', !!failure.status && failure.status < 500);
    error.value = failure.message;
  } finally {
    if (token === request) {
      busy.value = false;
      emit('busy', false);
    }
  }
}
watch(
  () => [props.ticket, props.project],
  () => {
    request++;
    busy.value = false;
    emit('busy', false);
    error.value = '';
    message.value = '';
  }
);
onBeforeUnmount(() => {
  request++;
  emit('busy', false);
});
</script>

<template>
  <AppMenu
    frame-composition
    :width="330"
    ref="menu"
    class="connection-menu"
    :class="{ 'connection-menu-compact': compact }"
    label="Connection"
    icon="connection"
  >
    <template #trigger
      ><span class="connection-dot" :class="{ online, connecting: busy }"></span
      ><AppIcon
        class="connection-icon"
        name="connection"
        :style="{
          color: busy
            ? 'var(--yellow)'
            : online
              ? 'var(--success)'
              : 'var(--error)'
        }"
      /><span class="connection-caption">{{
        t(busy ? 'Connecting' : online ? 'Connected' : 'Offline')
      }}</span></template
    >
    <ActionRows :actions="actions" @triggered="invoke" />
    <p v-if="error || updatesError" class="error" role="alert">
      {{ t(error || updatesError) }}
    </p>
    <p v-else-if="message" role="status">{{ t(message) }}</p>
  </AppMenu>
</template>

<style scoped>
.connection-menu :deep(.account-panel) {
  width: min(330px, calc(100vw - 16px));
}
.connection-menu-compact :deep(summary) {
  width: 100%;
  justify-content: start;
}
.connection-menu-compact .connection-dot {
  flex-shrink: 0;
}
</style>
