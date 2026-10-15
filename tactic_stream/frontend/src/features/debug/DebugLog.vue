<script setup>
// Handler DebugLogView.qml, with browser-owned session files in IndexedDB.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
import AppMenu from '../../controls/AppMenu.vue'
import CodeBlock from '../../controls/CodeBlock.vue'
import { copyText } from '../../controls/clipboard.js'
import { clearLive, debugLog, debugSettings, exportSession, formatEvent, importSession, levels, savedSessions, sessionRecords } from './debugLog.js'
import './debugLog.css'

const dialog = ref(null), fileInput = ref(null), eventList = ref(null)
const emit = defineEmits(['closed'])
const search = ref(''), group = ref(''), enabled = ref([...levels]), selected = ref(0)
const history = ref([]), historyId = ref(''), historical = ref([]), error = ref(''), message = ref('')
const loading = ref(false), opened = ref(false)
const narrow = window.matchMedia('(max-width: 760px)'), compact = ref(narrow.matches)
function resized() { compact.value = narrow.matches }
narrow.addEventListener('change', resized)
let request = 0
const records = computed(() => historyId.value ? historical.value : debugLog.entries)
const options = computed(() => [{ value: '', label: 'Live session' }, ...history.value.filter(session => session.id !== debugLog.sessionId).map(session => ({ value: session.id, label: session.label }))])
const groups = computed(() => {
  const modules = new Map(), paths = new Map()
  for (const record of records.value) {
    if (record.module) modules.set(record.module, (modules.get(record.module) || 0) + 1)
    const parts = record.group.split('/').filter(Boolean)
    for (let depth = 1; depth <= parts.length; depth++) { const path = parts.slice(0, depth).join('/'); paths.set(path, (paths.get(path) || 0) + 1) }
  }
  return [{ key: '', label: 'FULL LOG', count: records.value.length, depth: 0 },
    ...[...modules].sort().map(([key, count]) => ({ key, label: key, count, depth: 0 })),
    ...[...paths].sort().map(([key, count]) => ({ key, label: key.split('/').at(-1), count, depth: key.split('/').length }))]
})
const visible = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return records.value.filter(record => enabled.value.includes(record.level) && (!group.value || record.group === group.value || record.group.startsWith(group.value + '/') || record.module === group.value)
    && (!query || [record.message, record.group, record.module, record.functionName, record.command, record.stacktrace].join('\n').toLocaleLowerCase().includes(query)))
})
const entry = computed(() => records.value.find(record => record.eventId === selected.value))
const groupOptions = computed(() => groups.value.map(row => ({ value: row.key, label: (row.key ? row.key : t('FULL LOG')) + ' · ' + row.count })))
function color(level) { return ['ERROR', 'CRITICAL', 'EXCEPTION'].includes(level) ? 'var(--error)' : ['WARNING', 'MISSING'].includes(level) ? '#d5bd51' : level === 'INFO' ? 'var(--success)' : level === 'API' ? 'var(--primary)' : 'var(--muted)' }
watch(visible, async () => { if (opened.value) { await nextTick(); if (eventList.value) eventList.value.scrollTop = eventList.value.scrollHeight } })
async function refreshHistory() { try { history.value = await savedSessions() } catch { error.value = 'Debug Log history is unavailable. Live events remain in memory.' } }
async function open() { opened.value = true; dialog.value.show(); await refreshHistory(); await nextTick(); eventList.value.scrollTop = eventList.value.scrollHeight }
function close() { request++; loading.value = false; opened.value = false; dialog.value.close() }
onBeforeUnmount(() => { request++; opened.value = false; narrow.removeEventListener('change', resized) })
async function selectSession(id) {
  const token = ++request
  loading.value = true; error.value = ''; message.value = ''
  try { const result = id ? await sessionRecords(id) : []; if (token !== request) return; historyId.value = id; historical.value = result; group.value = ''; selected.value = 0 }
  catch { if (token === request) error.value = 'Debug Log session could not be loaded.' }
  finally { if (token === request) loading.value = false }
}
async function loadFile(event) {
  const file = event.target.files[0]; event.target.value = ''
  if (!file) return
  const token = ++request; loading.value = true; error.value = ''; message.value = ''
  try {
    const result = await importSession(file)
    if (token !== request) return
    await refreshHistory()
    if (token !== request) return
    historyId.value = result.id; historical.value = result.records; group.value = ''; selected.value = 0
  } catch (failure) { if (token === request) error.value = t(failure.message) + (failure.line ? ' · ' + t('Line {line}', { line: failure.line }) : '') }
  finally { if (token === request) loading.value = false }
}
async function clear() { if (historyId.value) await selectSession(''); else { selected.value = 0; await clearLive() }; await refreshHistory() }
function download() {
  const url = URL.createObjectURL(new Blob([exportSession(records.value)], { type: 'application/x-ndjson' }))
  const link = document.createElement('a'); link.href = url; link.download = 'session_' + debugLog.started.replaceAll(/[:.]/g, '_') + '.jsonl'; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
async function copy(text) {
  try { await copyText(text); message.value = 'Copied to clipboard'; error.value = '' }
  catch { error.value = 'Clipboard access failed. Select and copy the text below.' }
}
function toggleLevel(level) { enabled.value = enabled.value.includes(level) ? enabled.value.filter(item => item !== level) : [...enabled.value, level] }
function selectNext(event) {
  if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const index = visible.value.findIndex(record => record.eventId === selected.value)
  const target = event.key === 'Home' ? 0 : event.key === 'End' ? visible.value.length - 1 : Math.max(0, Math.min(visible.value.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)))
  selected.value = visible.value[target]?.eventId || 0
  eventList.value?.querySelector('[data-event-id="' + selected.value + '"]')?.focus()
}
defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{kind:'debug_log', type:'window' }" ref="dialog" class="debug-log-dialog" :aria-label="t('Debug Log')" @cancel.prevent="close" @close="opened = false; emit('closed')">
      <header class="debug-log-header"><AppIcon name="MDI_BUG" /><strong>{{ t('Debug Log') }}</strong><AppButton icon-only icon="close" label="Close Debug Log" @click="close" /></header>
      <div class="debug-log-screen" :aria-busy="loading" :style="{ '--debug-group-width': debugSettings.groupWidth + 'px', '--debug-detail-height': debugSettings.detailHeight + 'px' }">
        <section class="debug-log-toolbar">
          <div class="debug-log-toolbar-row">
            <label class="debug-log-search"><AppIcon name="search" /><input v-model="search" type="search" :placeholder="t('Search log…')" :aria-label="t('Search debug log')"></label>
            <AppSelect :model-value="historyId" :options="options" label="Debug session" :disabled="loading" @update:model-value="selectSession" />
            <input ref="fileInput" class="debug-file-input" type="file" accept=".jsonl" :aria-label="t('Open saved debug session')" @change="loadFile">
            <AppButton icon-only icon="folder" label="Open saved debug session" :disabled="loading" @click="fileInput.click()" />
            <AppButton v-if="historyId" icon-only icon="activity" label="Return to live session" :disabled="loading" @click="selectSession('')" />
            <span class="debug-event-count">{{ t('{count} events', { count: records.length }) }}</span>
            <AppButton icon-only icon="MDI_DOWNLOAD" label="Download debug session" @click="download" />
            <AppButton icon-only icon="delete" label="Clear session" :disabled="loading" @click="clear" />
          </div>
          <AppMenu class="debug-level-menu" :inline="!compact" label="Log levels" icon="filter" :close-on-select="false" :boundary="dialog"><template #trigger><AppIcon name="filter" /><span>{{ t('LEVEL') }}</span></template><div class="debug-log-levels"><span v-if="!compact" class="muted">{{ t('LEVEL') }}</span><AppButton v-for="level in levels" :key="level" :label="level" :icon="enabled.includes(level) ? 'check' : 'close'" :aria-pressed="enabled.includes(level)" :style="{ '--debug-accent': color(level) }" @click="toggleLevel(level)" /></div></AppMenu>
        </section>
        <p v-if="error || debugLog.storageError" class="error" role="alert">{{ t(error || debugLog.storageError) }}</p>
        <p v-if="message" class="muted" role="status">{{ t(message) }}</p>
        <AppSelect class="debug-mobile-sources" v-model="group" :options="groupOptions" label="Sources" />
        <div class="debug-log-body">
          <nav class="debug-log-sources" :aria-label="t('Sources')"><header><AppIcon name="MDI_FILE_TREE" /><strong>{{ t('Sources') }}</strong><small class="muted">{{ groups.length }}</small></header><div class="debug-source-list">
            <AppButton v-for="row in groups" :key="row.depth + ':' + row.key" :label="row.key ? row.label : 'FULL LOG'" :aria-pressed="group === row.key" :style="{ paddingLeft: (10 + row.depth * 13) + 'px' }" @click="group = row.key"><AppIcon :name="row.depth ? 'MDI_SUBDIRECTORY_ARROW_RIGHT' : 'folder'" /><span>{{ row.key ? row.label : t('FULL LOG') }}</span><small>{{ row.count }}</small></AppButton>
          </div></nav>
          <AppSplitter v-model="debugSettings.groupWidth" label="Sources panel width" :min="170" :max="520" />
          <div class="debug-log-event-column">
            <section class="debug-log-events"><header><AppIcon name="MDI_BUG" /><strong>{{ t('Activity') }}</strong><small class="muted">{{ t('Newest events appear at the bottom') }}</small></header>
              <div ref="eventList" class="debug-event-list" role="listbox" :aria-label="t('Debug events')" @keydown="selectNext">
                <button v-for="record in visible" :key="record.eventId" class="debug-event" role="option" :aria-selected="record.eventId === selected" :data-event-id="record.eventId" :style="{ '--debug-accent': color(record.level) }" @click="selected = record.eventId">
                  <span class="debug-level">{{ record.level }}</span><AppIcon :name="record.command ? 'MDI_CONSOLE' : 'info'" /><span class="debug-event-summary"><strong>{{ record.message }}</strong><small class="muted">{{ [record.group, record.module, record.functionName].filter(Boolean).join(' · ') }}</small></span><span class="debug-event-metrics"><time>{{ record.timestamp.slice(11, 23) }}</time><small>{{ record.duration > 0 ? record.duration.toFixed(3) + ' s' : '' }} {{ record.sizeKb > 0 ? record.sizeKb.toFixed(1) + ' KB' : '' }}</small></span>
                </button>
                <p v-if="!visible.length" class="debug-empty muted">{{ t('No matching events') }}</p>
              </div>
            </section>
            <AppSplitter v-model="debugSettings.detailHeight" horizontal reverse label="Event details height" :min="110" :max="620" />
            <section class="debug-log-detail"><header><AppIcon name="info" /><strong>{{ entry ? t('Event #{id}', { id: entry.eventId }) + ' · ' + entry.level + ' · ' + entry.timestamp.slice(11, 23) : t('Event details') }}</strong><AppButton v-if="entry" icon-only icon="copy" label="Copy event" @click="copy(formatEvent(entry))" /><AppButton v-if="entry?.command" icon-only icon="MDI_CONSOLE" label="Copy runtime command" @click="copy(entry.command)" /></header>
              <div class="debug-detail-content" tabindex="0">
                <template v-if="entry"><pre>{{ entry.message }}</pre><template v-if="entry.details"><strong>{{ t('Details') }}</strong><pre>{{ entry.details }}</pre></template><template v-if="entry.command"><strong>{{ t('Runtime command') }}</strong><CodeBlock :code="entry.command" /></template><template v-if="entry.stacktrace"><strong>{{ t('Stacktrace') }}</strong><pre>{{ entry.stacktrace }}</pre></template></template>
                <p v-else class="muted">{{ t('Select an event to inspect its message, runtime command and stacktrace.') }}</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
