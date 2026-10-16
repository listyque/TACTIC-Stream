<script setup>
import {
  computed,
  markRaw,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import CodeBlock from '../../controls/CodeBlock.vue';
import AppButton from '../../controls/AppButton.vue';
import { copyText } from '../../controls/clipboard.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/feedback/error.ui.mjs';

const emit = defineEmits(['help', 'debug']);
const dialog = ref(null),
  body = ref(null),
  record = ref(null),
  expanded = ref(false),
  status = ref(''),
  viewport = ref({ width: 800, height: 650 });
const model = computed(() => ({
  title: 'Event details',
  kind: record.value?.level || '',
  message: record.value?.message || '',
  stacktrace: record.value?.stacktrace || '',
  expanded: expanded.value,
  status: status.value,
  requestHeight: record.value?.command ? 286 : 0,
  canRetry: false,
  canConfigure: false
}));
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const codeComponent = markRaw(CodeBlock);
const views = computed(() => ({
  requests: {
    component: codeComponent,
    props: { code: record.value?.command || '', language: 'python' }
  }
}));
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width && box.height)
      viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());
async function dispatch(action) {
  if (action.type === 'expand') expanded.value = !expanded.value;
  else if (action.type === 'copyStacktrace') {
    try {
      await copyText(record.value.stacktrace);
      status.value = 'Copied to clipboard';
    } catch {
      status.value = 'Clipboard access failed';
    }
  } else if (action.type === 'dismiss') close();
  else if (action.type === 'help') {
    close();
    emit('help', 'errors');
  } else if (action.type === 'debug') {
    close();
    emit('debug');
  }
}
function close() {
  dialog.value.close();
  record.value = null;
}
async function open(value) {
  record.value = value;
  expanded.value = false;
  status.value = '';
  await nextTick();
  if (!dialog.value.open) dialog.value.showModal();
}
defineExpose({ open, close });
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'error', type: 'dialog' }"
      ref="dialog"
      class="support-error-dialog"
      :aria-label="t('Event details')"
      @cancel.prevent="close"
      @close="record = null"
    >
      <header>
        <strong>{{ t('Event details') }}</strong
        ><AppButton icon="close" label="Close" icon-only @click="close" />
      </header>
      <div ref="body" class="support-error-body">
        <FrameView :scene="scene" :views="views" @event="dispatch" />
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.support-error-dialog {
  width: min(880px, calc(100dvw - 16px));
  height: min(760px, calc(100dvh - 16px));
  max-width: none;
  max-height: none;
  padding: 0;
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  background: var(--surface);
  color: var(--on-surface);
  overflow: hidden;
}
.support-error-dialog[open] {
  display: flex;
  flex-direction: column;
}
.support-error-dialog > header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 40px;
  padding: 2px 6px 2px 14px;
  border-bottom: 1px solid var(--outline-variant);
}
.support-error-dialog > header > strong {
  flex: 1;
}
.support-error-body {
  flex: 1;
  min-height: 0;
  position: relative;
}
.support-error-dialog::backdrop {
  background: var(--scrim);
}
.support-error-body :deep(.code-block) {
  margin: 0;
  height: 100%;
  width: 100%;
  overflow: auto;
}
</style>
