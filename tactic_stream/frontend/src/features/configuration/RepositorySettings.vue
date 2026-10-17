<script setup>
// ConfigurationRepositoryPage.qml: repository summary, editor and native path check.
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/repository.ui.mjs';
import { preferences } from './preferences.js';
const props = defineProps({ ticket: String, busy: Boolean });
const emit = defineEmits(['edit', 'session-expired']);
const records = ref([]),
  platform = ref(''),
  checking = ref(false),
  error = ref('');
const current = computed(
  () =>
    records.value.find(
      (item) => item.alias === preferences.repository.defaultAlias
    ) || records.value.find((item) => item.is_default)
);
let generation = 0;
watch(
  () => props.ticket,
  () => {
    generation++;
    records.value = [];
    checking.value = false;
    error.value = '';
  }
);
async function load(action = 'load', paths) {
  if (checking.value) return;
  const request = generation;
  checking.value = true;
  error.value = '';
  try {
    const result = await rpc(
      'execute_cmd',
      [
        { ticket: props.ticket, project: 'admin' },
        'tactic.ui.app.RepositoryPathsCmd',
        { action, ...(paths ? { paths } : {}) }
      ],
      {},
      true
    );
    if (request !== generation) return false;
    records.value = result.info.repositories;
    platform.value = result.info.platform;
    return true;
  } catch (failure) {
    if (request !== generation) return false;
    if (failure.code === 'authentication_failed') emit('session-expired');
    error.value = failure.message;
    return false;
  } finally {
    if (request === generation) checking.value = false;
  }
}
const host = ref(null),
  viewport = ref({ width: 800, height: 600 });
const model = computed(() => ({
  currentTitle: current.value?.title,
  currentPath: current.value?.path,
  records: records.value.map((record) => ({
    ...record,
    code: record.alias,
    active: record.enabled,
    isDefault: record.alias === preferences.repository.defaultAlias,
    statusText:
      record.status === 'available'
        ? 'Available'
        : record.status === 'unchecked'
          ? 'Not checked'
          : 'Folder not found or inaccessible'
  })),
  busy: props.busy || checking.value,
  error: error.value,
  style: appearance.theme
}));
const scene = computed(() =>
  UI.summary(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
let observer;
onMounted(() => {
  load();
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
function dispatch(action) {
  if (action.type === 'edit') emit('edit');
  else if (action.type === 'check') load('check');
}
defineExpose({ load, records, checking });
</script>
<template>
  <section
    ref="host"
    class="repository-settings repository-summary-frame"
    :aria-busy="checking"
  >
    <FrameView :scene="scene" @event="dispatch" />
  </section>
</template>
<style>
.repository-summary-frame {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.repository-summary-frame > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
