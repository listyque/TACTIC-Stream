<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { tableDependencies, tableDependencyFile } from '../../api.js';
import { appearance } from '../../appearance.js';
import * as State from '../../../../src/tactic_stream/shared_ui/features/table/dependencies.state.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/dependencies.ui.mjs';

const props = defineProps({ model: Object, width: Number, height: Number });
const emit = defineEmits(['close', 'file']);
const state = ref(State.create('', ''));
const records = computed(() => State.rows(state.value));
let generation = 0;
const requests = new Set();
function cancel() {
  generation++;
  for (const request of requests) request.abort();
  requests.clear();
}
async function read(change) {
  state.value = change.state;
  if (!change.request) return;
  const { path, projectCode, ...arguments_ } = change.request;
  const current = generation,
    abort = new AbortController();
  requests.add(abort);
  try {
    const response = await tableDependencies(
      { ...props.model.context, project: projectCode },
      arguments_,
      abort.signal
    );
    if (current === generation)
      state.value = State.accept(state.value, path, response.info);
  } catch (error) {
    if (current === generation)
      state.value = State.accept(state.value, path, null, error.message);
  } finally {
    requests.delete(abort);
  }
}
function reset() {
  cancel();
  read(
    State.begin(
      State.create(props.model.searchKey, props.model.projectCode),
      'root'
    )
  );
}
async function activate(action) {
  if (action.type === 'close') emit('close');
  else if (action.type === 'refresh') reset();
  else if (action.type === 'read')
    read(State.begin(state.value, action.path, action.more));
  else if (action.type === 'toggle') {
    const record = records.value.find((row) => row.path === action.path);
    if (record) read(State.toggle(state.value, record));
  } else if (action.type === 'file') {
    const current = generation,
      abort = new AbortController();
    requests.add(abort);
    state.value = { ...state.value, notice: '' };
    try {
      const response = await tableDependencyFile(
        { ...props.model.context, project: action.projectCode },
        {
          search_key: action.snapshotKey,
          file_code: action.fileCode,
          expected_revision: action.revision
        },
        abort.signal
      );
      if (current === generation)
        emit('file', { ...response.info, fileCode: action.fileCode });
    } catch (error) {
      if (current === generation)
        state.value = { ...state.value, notice: error.message };
    } finally {
      requests.delete(abort);
    }
  }
}
watch(() => props.model, reset, { immediate: true });
onBeforeUnmount(cancel);
</script>
<template>
  <FrameView
    :scene="UI.describe(state, width, height, appearance.language)"
    :models="{ dependencyRows: records }"
    :describe-row="
      (list, row) =>
        UI.row(row, Math.max(0, list.width - 16), appearance.language)
    "
    @event="activate"
  />
</template>
