<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import { downloadBlob } from '../../controls/files.js';
import { fileBlob } from '../objects/previewFiles.js';
import { controls } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import AppButton from '../../controls/AppButton.vue';
import SnapshotCheckoutSurface from './SnapshotCheckoutSurface.vue';

const props = defineProps({ ticket: String, project: String });
const dialog = ref(null),
  snapshot = ref(null),
  files = ref([]),
  selected = ref('');
const loading = ref(false),
  ready = ref(false),
  busy = ref(false),
  progress = ref(0),
  error = ref(''),
  message = ref('');
let generation = 0,
  download,
  scope;
const rows = computed(() =>
  files.value.map((file, index) => ({
    token: String(file.code || index),
    title: file.filename,
    fileType: file.type || '',
    bytes: file.size || 0,
    selected: String(file.code || index) === selected.value,
    enabled: !busy.value
  }))
);
const model = computed(() => ({
  loading: loading.value,
  ready: ready.value,
  busy: busy.value,
  progress: progress.value,
  error: t(error.value),
  message: t(message.value),
  count: files.value.length,
  context: snapshot.value?.context || ''
}));
const title = computed(
  () =>
    t('Check out') +
    (snapshot.value
      ? ' · ' + snapshot.value.code + ' · v' + snapshot.value.version
      : '')
);
const style = {
  '--checkout-header-height': controls.dialog.headerHeight + 'px'
};

function close() {
  generation++;
  download?.abort();
  download = null;
  dialog.value?.close();
  files.value = [];
  snapshot.value = null;
  progress.value = 0;
  busy.value = loading.value = ready.value = false;
}
async function open(record) {
  close();
  const request = generation;
  scope = { ticket: props.ticket, project: props.project };
  loading.value = true;
  error.value = message.value = '';
  await nextTick();
  if (request !== generation) return;
  dialog.value.showModal();
  try {
    const response = await rpc('execute_cmd', [
      scope,
      'tactic.ui.table.TableSnapshotFilesCmd',
      { search_key: record.__search_key__ }
    ]);
    if (request !== generation) return;
    snapshot.value = response.info.snapshot;
    files.value = response.info.files.toSorted((first, second) => {
      const fields = (file) => [
        file.type !== 'main',
        file.filename,
        file.type || '',
        String(file.code || '')
      ];
      const a = fields(first),
        b = fields(second);
      for (let index = 0; index < a.length; index++) {
        if (a[index] < b[index]) return -1;
        if (a[index] > b[index]) return 1;
      }
      return 0;
    });
    const first = Math.max(
      0,
      files.value.findIndex((file) => file.type === 'main')
    );
    selected.value = files.value.length
      ? String(files.value[first].code || first)
      : '';
    ready.value = true;
  } catch (failure) {
    if (request === generation) error.value = failure.message;
  } finally {
    if (request === generation) loading.value = false;
  }
}
async function activate(action) {
  if (action.type === 'cancelTransfer') {
    download?.abort();
    return;
  }
  if (action.type === 'close') {
    close();
    return;
  }
  if (busy.value || !ready.value) return;
  if (action.type === 'select') {
    selected.value = action.token;
    progress.value = 0;
    message.value = error.value = '';
    return;
  }
  if (action.type !== 'checkout') return;
  const file = files.value.find(
    (file, index) => String(file.code || index) === selected.value
  );
  if (!file) return;
  const members = file.members?.length ? file.members : [file];
  const request = generation;
  busy.value = true;
  progress.value = 0;
  error.value = message.value = '';
  download = new AbortController();
  try {
    for (const [index, member] of members.entries()) {
      const blob = await fileBlob(member, { signal: download.signal });
      if (request !== generation) return;
      downloadBlob(blob, member.filename);
      progress.value = (index + 1) / members.length;
    }
    if (request === generation) message.value = 'Download completed';
  } catch (failure) {
    if (request === generation) {
      if (failure.name === 'AbortError') message.value = 'Download cancelled';
      else error.value = failure.message;
    }
  } finally {
    if (request === generation) {
      busy.value = false;
      download = null;
    }
  }
}
watch(
  () => [props.ticket, props.project],
  () => close()
);
onBeforeUnmount(() => close());
defineExpose({ open, close });
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      v-window="{ type: 'dialog', kind: 'snapshot_checkout' }"
      class="record-dialog snapshot-checkout"
      :style="style"
      :aria-label="t('Check out')"
      @cancel.prevent="close()"
    >
      <header>
        <h2>{{ title }}</h2>
        <AppButton label="Close" icon="close" icon-only @click="close()" />
      </header>
      <SnapshotCheckoutSurface :model="model" :files="rows" @event="activate" />
    </dialog>
  </Teleport>
</template>
<style>
.snapshot-checkout.record-dialog {
  width: min(762px, calc(100vw - 24px));
  height: min(
    calc(560px + var(--checkout-header-height) + 2px),
    calc(100dvh - 24px)
  );
  max-height: calc(100dvh - 24px);
  overflow: hidden;
  padding: 0;
  gap: 0;
}
.snapshot-checkout[open] {
  display: flex;
  flex-direction: column;
}
.snapshot-checkout.record-dialog > header.app-window-titlebar {
  height: var(--checkout-header-height);
  min-height: var(--checkout-header-height);
  margin: 0;
  padding: 8px 12px;
  gap: 8px;
}
.snapshot-checkout > header h2 {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0;
}
@media (max-width: 700px) {
  .snapshot-checkout.record-dialog[open] {
    width: 100dvw;
    height: 100dvh;
    max-width: none;
    max-height: 100dvh;
    margin: 0;
    border: 0;
    border-radius: 0;
  }
}
</style>
