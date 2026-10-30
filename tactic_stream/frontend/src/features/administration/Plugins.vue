<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { rpc, uploadFormFile } from '../../api.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/plugins/plugins.ui.mjs';

const props = defineProps({
    ticket: String,
    project: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  }),
  emit = defineEmits(['saved', 'help']),
  host = ref(null),
  picker = ref(null),
  toolbarHost = ref(null),
  size = ref({ width: 800, height: 600 }),
  toolbarWidth = ref(420),
  rows = ref([]),
  draft = ref({}),
  original = ref({}),
  metadata = ref({}),
  identity = ref(''),
  revision = ref(''),
  busy = ref(false),
  uncertain = ref(false),
  error = ref(''),
  ui = ref(UI.initial()),
  canWrite = ref(false);
const dirty = computed(
    () => JSON.stringify(draft.value) !== JSON.stringify(original.value)
  ),
  model = computed(() => ({
    catalog: rows.value,
    document: draft.value,
    metadata: metadata.value,
    identity: identity.value,
    canWrite: canWrite.value,
    busy: busy.value,
    uncertain: uncertain.value,
    dirty: dirty.value,
    error: error.value
  })),
  scene = computed(() =>
    UI.describe(
      model.value,
      ui.value,
      size.value.width,
      size.value.height,
      appearance.language
    )
  ),
  toolbar = computed(() =>
    UI.toolbar(model.value, toolbarWidth.value, appearance.language)
  ),
  models = computed(() => ({
    plugins: UI.catalog(model.value, ui.value),
    files: metadata.value.files || []
  }));
let generation = 0,
  observer,
  uploadPackage = false,
  uploadReplace = false;
const clone = (value) => JSON.parse(JSON.stringify(value));
function rowScene(list, row) {
  return UI.row(list, row, model.value, appearance.language);
}
function clear() {
  ++generation;
  busy.value = uncertain.value = false;
  rows.value = [];
  draft.value = {};
  original.value = {};
  metadata.value = {};
  identity.value = revision.value = error.value = '';
  ui.value = UI.initial();
}
async function run(action, values = {}, upload = null) {
  if (busy.value || !props.ticket) return;
  const current = ++generation,
    owner = {
      ticket: props.ticket,
      project: props.project,
      language: 'python'
    },
    write = !['list', 'load', 'new', 'browse', 'open_file'].includes(action),
    args = Object.assign(
      {
        action,
        project_code: props.project,
        identity: identity.value,
        expected_revision: revision.value
      },
      values
    );
  if (['save', 'create'].includes(action)) {
    args.document = clone(draft.value);
    args.changed_fields = ['title', 'description'].filter(
      (key) => draft.value[key] !== original.value[key]
    );
  }
  busy.value = true;
  error.value = '';
  try {
    if (upload) {
      args.upload_file_name = await uploadFormFile(
        owner.ticket,
        owner.project,
        upload
      );
      if (current !== generation) return;
      if (!uploadPackage && !uploadReplace)
        args.path = [metadata.value.folder, upload.name]
          .filter(Boolean)
          .join('/');
    }
    const response = await rpc(
        'execute_cmd',
        [owner, 'tactic.ui.app.plugin_wdg.PluginManagerCmd', args],
        {},
        true
      ),
      result = response.info;
    if (current !== generation) return;
    uncertain.value = false;
    if (result.catalog) rows.value = result.catalog;
    if (action === 'list') {
      const selected =
        rows.value.find((row) => row.identity === identity.value) ||
        rows.value[0];
      busy.value = false;
      if (selected) return run('load', { identity: selected.identity });
      draft.value = original.value = {};
      metadata.value = {};
      identity.value = revision.value = '';
    } else {
      identity.value = result.identity;
      revision.value = result.revision;
      draft.value = result.document;
      original.value = clone(result.document);
      metadata.value = result.metadata;
      canWrite.value = result.canWrite;
      if (result.download) {
        const link = document.createElement('a');
        link.href =
          '/assets/_cache/' +
          [owner.ticket, result.download.directory, result.download.filename]
            .map(encodeURIComponent)
            .join('/');
        link.download = result.download.filename;
        link.click();
      }
      if (write) emit('saved');
    }
  } catch (failure) {
    if (current !== generation) return;
    error.value = failure.message;
    if (write) uncertain.value = true;
  } finally {
    if (current === generation) busy.value = false;
  }
}
function discard() {
  if (busy.value) return;
  if (uncertain.value || metadata.value.new) {
    uncertain.value = false;
    draft.value = original.value = {};
    metadata.value = {};
  } else draft.value = clone(original.value);
  error.value = '';
}
function dispatch(event) {
  const result = UI.transition(ui.value, model.value, event);
  ui.value = result.ui;
  for (const command of result.commands) {
    if (command.type === 'help') emit('help', command.topic);
    else if (command.type === 'select')
      run('load', { identity: command.identity });
    else if (command.type === 'request') run(command.action, command.values);
    else if (command.type === 'field') {
      if (command.field === 'file_content' && draft.value.file)
        draft.value.file.content = command.value;
      else if (Object.hasOwn(draft.value, command.field))
        draft.value[command.field] = command.value;
    } else if (command.type === 'save')
      run(metadata.value.new ? 'create' : 'save');
    else if (command.type === 'discard') discard();
    else if (command.type === 'error') error.value = command.value;
    else if (command.type === 'upload') {
      uploadPackage = !!command.package;
      uploadReplace = !!command.replace;
      picker.value.accept = uploadPackage ? '.zip' : '';
      picker.value.click();
    }
  }
}
function upload(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (file)
    run(
      uploadPackage ? 'install' : 'upload',
      {
        folder: metadata.value.folder || '',
        ...(uploadReplace
          ? { path: draft.value.file.path, confirmation: true }
          : {})
      },
      file
    );
}
function canLeave() {
  if (busy.value || dirty.value || uncertain.value) {
    error.value = 'Apply or discard unsaved changes first';
    return false;
  }
  return true;
}
function beforeUnload(event) {
  if (busy.value || dirty.value || uncertain.value) {
    event.preventDefault();
    event.returnValue = '';
  }
}
watch(
  () => [props.ticket, props.project],
  () => {
    clear();
    run('list');
  }
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries) {
      if (entry.target === host.value)
        size.value = {
          width: entry.contentRect.width,
          height: entry.contentRect.height
        };
      else toolbarWidth.value = entry.contentRect.width;
    }
  });
  observer.observe(host.value);
  observer.observe(
    props.toolbarTarget
      ? document.querySelector(props.toolbarTarget)
      : host.value.parentElement
  );
  window.addEventListener('beforeunload', beforeUnload);
  run('list');
});
onBeforeUnmount(() => {
  ++generation;
  observer?.disconnect();
  window.removeEventListener('beforeunload', beforeUnload);
});
defineExpose({
  canLeave,
  dirty,
  busy,
  uncertain,
  error,
  dispatch,
  model,
  ui,
  scene
});
</script>
<template>
  <section
    class="plugins-frame frame-host"
    :aria-busy="busy"
    :style="{ gap: UI.toolbarGap + 'px' }"
  >
    <Teleport defer :to="toolbarTarget || 'body'" :disabled="!toolbarTarget">
      <div
        ref="toolbarHost"
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarWidth + 'px' }"
      >
        <FrameView :scene="toolbar" @event="dispatch" />
      </div>
    </Teleport>
    <div ref="host" class="frame-host-body">
      <FrameView
        :scene="scene"
        :models="models"
        :describe-row="rowScene"
        @event="dispatch"
      />
    </div>
    <input ref="picker" type="file" hidden @change="upload" />
  </section>
</template>
