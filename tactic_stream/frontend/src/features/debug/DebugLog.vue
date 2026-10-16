<script setup>
// Handler DebugLogView.qml, with browser-owned session files in IndexedDB.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
  watch,
  onMounted
} from 'vue';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import FrameView from '../../frame/FrameView.vue';
import ErrorDetails from './ErrorDetails.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/diagnostics/debug.ui.mjs';
import { selection } from '../../../../src/tactic_stream/shared_ui/features/support/diagnostics/performance.ui.mjs';
import { copyText } from '../../controls/clipboard.js';
import {
  clearLive,
  debugLog,
  debugSettings,
  exportSession,
  formatEvent,
  importSession,
  levels,
  savedSessions,
  sessionRecords
} from './debugLog.js';
import './debugLog.css';

const errorDetails = ref(null);
const dialog = ref(null),
  fileInput = ref(null),
  body = ref(null),
  frame = ref(null),
  viewport = ref({ width: 1100, height: 700 });
const emit = defineEmits(['closed', 'help']);
const search = ref(''),
  group = ref(''),
  enabled = ref([...levels]),
  selected = ref(0);
const history = ref([]),
  historyId = ref(''),
  historical = ref([]),
  error = ref(''),
  message = ref('');
const loading = ref(false),
  opened = ref(false);
let request = 0;
const records = computed(() =>
  historyId.value ? historical.value : debugLog.entries
);
const options = computed(() => [
  { value: '', label: 'Live session' },
  ...history.value
    .filter((session) => session.id !== debugLog.sessionId)
    .map((session) => ({ value: session.id, label: session.label }))
]);
const groups = computed(() => {
  const modules = new Map(),
    paths = new Map();
  for (const record of records.value) {
    if (record.module)
      modules.set(record.module, (modules.get(record.module) || 0) + 1);
    const parts = record.group.split('/').filter(Boolean);
    for (let depth = 1; depth <= parts.length; depth++) {
      const path = parts.slice(0, depth).join('/');
      paths.set(path, (paths.get(path) || 0) + 1);
    }
  }
  return [
    { key: '', label: 'FULL LOG', count: records.value.length, depth: 0 },
    ...[...modules]
      .sort()
      .map(([key, count]) => ({ key, label: key, count, depth: 0 })),
    ...[...paths].sort().map(([key, count]) => ({
      key,
      label: key.split('/').at(-1),
      count,
      depth: key.split('/').length
    }))
  ].map((row) => ({ ...row, identity: row.depth + ':' + row.key }));
});
const visible = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return records.value.filter(
    (record) =>
      enabled.value.includes(record.level) &&
      (!group.value ||
        record.group === group.value ||
        record.group.startsWith(group.value + '/') ||
        record.module === group.value) &&
      (!query ||
        [
          record.message,
          record.group,
          record.module,
          record.functionName,
          record.command,
          record.stacktrace
        ]
          .join('\n')
          .toLocaleLowerCase()
          .includes(query))
  );
});
const entry = computed(() =>
  records.value.find((record) => record.eventId === selected.value)
);
const groupOptions = computed(() =>
  groups.value.map((row) => ({
    value: row.key,
    label: row.key,
    count: row.count
  }))
);
const frameModel = computed(() => ({
  search: search.value,
  group: group.value,
  enabled: enabled.value,
  levels,
  selectedId: selected.value,
  entry: entry.value,
  historyId: historyId.value,
  sessions: options.value,
  groups: groupOptions.value,
  loading: loading.value,
  canDownload: true,
  groupWidth: debugSettings.groupWidth,
  detailHeight: debugSettings.detailHeight,
  count: records.value.length,
  visibleCount: visible.value.length,
  error: error.value || debugLog.storageError,
  message: message.value
}));
const scene = computed(() =>
  UI.describe(
    frameModel.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const row = (list, record) =>
  UI.row(frameModel.value, list, record, list.width - 16, appearance.language);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(body.value);
});
function scrollEnd() {
  const list = dialog.value?.querySelector('[data-frame="debugEvents"]');
  if (list) list.scrollTop = list.scrollHeight;
}
watch(visible, async () => {
  if (opened.value) {
    await nextTick();
    scrollEnd();
  }
});
function dispatch(action) {
  if (action.type === 'search') search.value = action.value;
  else if (action.type === 'group') group.value = action.value;
  else if (action.type === 'level') toggleLevel(action.level);
  else if (action.type === 'sourceWidth')
    debugSettings.groupWidth = action.value;
  else if (action.type === 'detailHeight')
    debugSettings.detailHeight = action.value;
  else if (action.type === 'session') selectSession(action.value);
  else if (action.type === 'event') selected.value = action.id;
  else if (action.type === 'eventKey') {
    const target = selection(visible.value, action.id, action.key, 'eventId');
    if (target) {
      selected.value = target.eventId;
      nextTick(() =>
        frame.value?.focusListRow(
          'debugEvents',
          visible.value.findIndex(
            (record) => record.eventId === target.eventId
          ),
          'debugEvent_' + target.eventId
        )
      );
    }
  } else if (action.type === 'open') fileInput.value.click();
  else if (action.type === 'live') selectSession('');
  else if (action.type === 'download') download();
  else if (action.type === 'clear') clear();
  else if (action.type === 'inspect') errorDetails.value.open(entry.value);
  else if (action.type === 'copy') copy(formatEvent(entry.value));
  else if (action.type === 'copyCommand') copy(entry.value.command);
  else if (action.type === 'help') emit('help', 'debug_log');
}
watch(
  () => debugLog.sessionId,
  () => {
    close();
    history.value = [];
    historyId.value = '';
    historical.value = [];
    selected.value = 0;
    error.value = '';
    message.value = '';
  }
);
async function refreshHistory() {
  const token = request,
    session = debugLog.sessionId;
  try {
    const result = await savedSessions();
    if (token === request && session === debugLog.sessionId)
      history.value = result;
  } catch {
    if (token === request && session === debugLog.sessionId)
      error.value =
        'Debug Log history is unavailable. Live events remain in memory.';
  }
}
async function open() {
  const token = ++request;
  opened.value = true;
  dialog.value.show();
  await refreshHistory();
  if (token !== request || !opened.value) return;
  await nextTick();
  scrollEnd();
}
function close() {
  request++;
  loading.value = false;
  opened.value = false;
  errorDetails.value?.close();
  dialog.value.close();
}
onBeforeUnmount(() => {
  request++;
  opened.value = false;
  observer?.disconnect();
});
async function selectSession(id) {
  const token = ++request;
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const result = id ? await sessionRecords(id) : [];
    if (token !== request) return;
    historyId.value = id;
    historical.value = result;
    group.value = '';
    selected.value = 0;
  } catch {
    if (token === request)
      error.value = 'Debug Log session could not be loaded.';
  } finally {
    if (token === request) loading.value = false;
  }
}
async function loadFile(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file) return;
  const token = ++request;
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const result = await importSession(file);
    if (token !== request) return;
    await refreshHistory();
    if (token !== request) return;
    historyId.value = result.id;
    historical.value = result.records;
    group.value = '';
    selected.value = 0;
  } catch (failure) {
    if (token === request)
      error.value =
        t(failure.message) +
        (failure.line ? ' · ' + t('Line {line}', { line: failure.line }) : '');
  } finally {
    if (token === request) loading.value = false;
  }
}
async function clear() {
  if (historyId.value) await selectSession('');
  else {
    selected.value = 0;
    await clearLive();
  }
  await refreshHistory();
}
function download() {
  const url = URL.createObjectURL(
    new Blob([exportSession(records.value)], { type: 'application/x-ndjson' })
  );
  const link = document.createElement('a');
  link.href = url;
  link.download =
    'session_' + debugLog.started.replaceAll(/[:.]/g, '_') + '.jsonl';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
async function copy(text) {
  try {
    await copyText(text);
    message.value = 'Copied to clipboard';
    error.value = '';
  } catch {
    error.value = 'Clipboard access failed. Select and copy the text below.';
  }
}
function toggleLevel(level) {
  enabled.value = enabled.value.includes(level)
    ? enabled.value.filter((item) => item !== level)
    : [...enabled.value, level];
}
defineExpose({ open });
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'debug_log', type: 'window' }"
      ref="dialog"
      class="debug-log-dialog"
      :aria-label="t('Debug Log')"
      @cancel.prevent="close"
      @close="
        opened = false;
        emit('closed');
      "
    >
      <header class="debug-log-header">
        <AppIcon name="MDI_BUG" /><strong>{{ t('Debug Log') }}</strong
        ><AppButton
          icon-only
          icon="close"
          label="Close Debug Log"
          @click="close"
        />
      </header>
      <input
        ref="fileInput"
        hidden
        type="file"
        accept=".jsonl"
        :aria-label="t('Open saved debug session')"
        @change="loadFile"
      />
      <div ref="body" class="debug-log-screen" :aria-busy="loading">
        <FrameView
          ref="frame"
          :scene="scene"
          :models="{ groups, events: visible }"
          :describe-row="row"
          @event="dispatch"
        />
      </div>
    </dialog>
    <ErrorDetails
      ref="errorDetails"
      @help="emit('help', $event)"
      @debug="open"
    />
  </Teleport>
</template>
