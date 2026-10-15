<script setup>
// Current Handler UiPerformanceView.qml, EPL-1.0.
import { ref, computed, onBeforeUnmount } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { copyText } from '../../controls/clipboard.js'
import { t } from '../../i18n.js'
import { uiPerformance } from './uiPerformance.js'
import './uiPerformance.css'

const dialog = ref(null), selectedId = ref(0), message = ref(''), failed = ref(false)
const emit = defineEmits(['closed'])
const selected = computed(() => uiPerformance.state.samples.find(sample => sample.sampleId === selectedId.value))
const summary = computed(() => uiPerformance.state.summary)
onBeforeUnmount(() => uiPerformance.setVisible(false))
function milliseconds(value) { return value >= 0 ? value.toFixed(1) + ' ' + t('ms') : '—' }
function actionText(value) { return value.startsWith('Search tab: ') ? t('Search tab') + ': ' + value.slice(12) : t(value) }
function open() { message.value = ''; dialog.value.show(); uiPerformance.setVisible(true) }
function close() { dialog.value.close(); uiPerformance.setVisible(false) }
function clear() { uiPerformance.clear(); selectedId.value = 0; message.value = '' }
async function copy() {
  try { await copyText(uiPerformance.copyResults()); failed.value = false; message.value = 'Copied to clipboard' }
  catch { failed.value = true; message.value = 'Clipboard access failed' }
}
function selectNext(event) {
  const samples = uiPerformance.state.samples, index = samples.findIndex(sample => sample.sampleId === selectedId.value)
  const target = { ArrowDown: Math.min(samples.length - 1, index + 1), ArrowUp: Math.max(0, index - 1), Home: 0, End: samples.length - 1 }[event.key]
  if (target === undefined || target < 0) return
  event.preventDefault(); selectedId.value = samples[target].sampleId
  dialog.value.querySelector('[data-sample-id="' + selectedId.value + '"]')?.focus()
}
defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{kind:'ui_performance', type:'window' }" ref="dialog" class="ui-performance-dialog" :aria-label="t('UI responsiveness')" @cancel.prevent="close" @close="uiPerformance.setVisible(false); emit('closed')">
      <header class="ui-performance-heading"><AppIcon name="MDI_SPEEDOMETER" /><strong>{{ t('UI responsiveness') }}</strong><AppButton icon-only icon="close" label="Close UI responsiveness" @click="close" /></header>
      <div class="ui-performance-screen">
        <div class="ui-performance-toolbar"><span>{{ t('UI responsiveness') }}</span><AppButton :label="uiPerformance.state.recording ? 'Pause measurements' : 'Resume measurements'" @click="uiPerformance.setRecording(!uiPerformance.state.recording)" /><AppButton icon-only icon="MDI_CONTENT_COPY" label="Copy measurements" @click="copy" /><AppButton icon-only icon="delete" label="Clear measurements" @click="clear" /></div>
        <p class="muted">{{ t('Target: a visible response within 50 ms. Input measures the next frame of the clicked window; controller rows measure work and its ready frame. A frame is not proof that asynchronous loading has finished.') }}</p>
        <p class="muted">{{ t('Browser frame timings bound a paint opportunity using animation callbacks. They do not confirm GPU presentation. Handler time for asynchronous operations includes waiting; details show the measured phases.') }}</p>
        <p class="ui-performance-summary">{{ t('Samples: {count} · Frames over 50 ms: {overBudget} · p95: {p95} · Maximum: {maximum}', { ...summary, p95: milliseconds(summary.p95), maximum: milliseconds(summary.maximum) }) }}</p>
        <p v-if="message" :class="failed ? 'error' : 'muted'" :role="failed ? 'alert' : 'status'">{{ t(message) }}</p>
        <div class="ui-performance-columns muted"><span>{{ t('Action / window') }}</span><span>{{ t('Handler') }}</span><span>{{ t('First frame') }}</span><span>{{ t('Ready frame') }}</span></div>
        <div class="ui-performance-samples" role="listbox" :aria-label="t('UI measurements')" @keydown="selectNext">
          <AppButton v-for="sample in uiPerformance.state.samples" :key="sample.sampleId" class="ui-performance-sample" :class="{ slow: sample.slow }" role="option" :aria-selected="selectedId === sample.sampleId" :data-sample-id="sample.sampleId" :label="actionText(sample.action)" @click="selectedId = sample.sampleId">
            <span class="ui-performance-action"><span>{{ actionText(sample.action) }}</span><small class="muted">{{ sample.window || t(sample.status) }}</small></span><span>{{ milliseconds(sample.handlerMs) }}</span><span :class="{ 'ui-performance-slow': sample.frameMs > 50 }">{{ milliseconds(sample.frameMs) }}</span><span>{{ milliseconds(sample.readyMs) }}</span>
          </AppButton>
          <p v-if="!uiPerformance.state.samples.length" class="muted ui-performance-empty">{{ t('No measurements yet. Resume measurements and interact with the application.') }}</p>
        </div>
        <textarea class="ui-performance-details" readonly :aria-label="t('Measurement details')" :value="(selected ? actionText(selected.action) + '\n' + t(selected.status) + '\n' + selected.details : t('Select a measurement for details'))" />
      </div>
    </dialog>
  </Teleport>
</template>
