<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { databaseResources } from '../../api.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/database_resources.ui.mjs';

const props = defineProps({
  ticket: String,
  active: Boolean,
  canAdminister: Boolean
});
const emit = defineEmits(['session-expired']);
const host = ref(null),
  viewport = ref({ width: 800, height: 600 }),
  state = ref({
    document: {},
    metadata: {},
    catalog: [],
    identity: '',
    revision: '',
    canWrite: false
  });
const original = ref('{}'),
  busy = ref(false),
  error = ref(''),
  uncertain = ref(false),
  confirm = ref(''),
  database = ref(''),
  project = ref('');
const dirty = computed(
  () => JSON.stringify(state.value.document) !== original.value
);
const scene = computed(() =>
  UI.page(
    {
      ...state.value,
      dirty: dirty.value,
      busy: busy.value,
      error: error.value,
      uncertain: uncertain.value,
      confirm: confirm.value,
      database: database.value,
      project: project.value
    },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
let generation = 0,
  observer,
  confirmSaveResolve;
async function request(
  action,
  identity = state.value.identity,
  confirmed = false
) {
  if (busy.value || !props.canAdminister) return false;
  busy.value = true;
  error.value = '';
  const token = ++generation;
  try {
    const result = await databaseResources(action, props.ticket, {
      identity,
      expected_revision: state.value.revision,
      ...(action === 'save' ? { document: state.value.document } : {}),
      ...(confirmed ? { confirmation: action } : {}),
      ...(action === 'test'
        ? { document: state.value.document, database: database.value }
        : {}),
      ...(action === 'upgrade' ? { database: database.value } : {}),
      ...(['bind', 'unbind'].includes(action)
        ? { project_code: project.value }
        : {})
    });
    if (token !== generation) return false;
    state.value = result;
    original.value = JSON.stringify(result.document);
    uncertain.value = false;
    const bound = result.metadata.projects.filter(
      (row) => row.resource === result.identity
    );
    if (!database.value) database.value = bound[0]?.database || '';
    if (!project.value) project.value = bound[0]?.code || '';
    return true;
  } catch (failure) {
    if (token !== generation) return false;
    error.value = failure.message;
    if (
      ['save', 'delete', 'bind', 'unbind'].includes(action) &&
      failure.status !== 400 &&
      failure.status !== 403 &&
      failure.status !== 409
    )
      uncertain.value = true;
    if (failure.status === 403) emit('session-expired');
    return false;
  } finally {
    if (token === generation) busy.value = false;
  }
}
function discard() {
  state.value.document = JSON.parse(original.value);
  error.value = '';
  confirm.value = '';
}
async function save() {
  if (uncertain.value || busy.value) return false;
  if (!dirty.value) return !uncertain.value;
  if (
    state.value.metadata.projects?.some(
      (row) => row.resource === state.value.identity
    )
  ) {
    confirm.value = 'save';
    return new Promise((resolve) => {
      confirmSaveResolve = resolve;
    });
  }
  return await request('save');
}
async function dispatch(action) {
  if (action.type === 'field' && !busy.value) {
    state.value.document[action.field] = action.value;
    return;
  }
  if (action.type === 'database') {
    database.value = action.value;
    return;
  }
  if (action.type === 'project') {
    project.value = action.value;
    database.value =
      state.value.metadata.projects.find((row) => row.code === action.value)
        ?.database || '';
    return;
  }
  if (action.type === 'reject') {
    confirm.value = '';
    confirmSaveResolve?.(false);
    confirmSaveResolve = null;
    return;
  }
  if (action.type === 'accept') {
    const type = confirm.value;
    confirm.value = '';
    const result = await request(type, state.value.identity, true);
    confirmSaveResolve?.(result);
    confirmSaveResolve = null;
    return;
  }
  if (busy.value) return;
  if (action.type === 'discard') discard();
  else if (action.type === 'save') await save();
  else if (action.type === 'select' && !dirty.value) {
    database.value = project.value = '';
    await request('load', action.value);
  } else if (action.type === 'new' && !dirty.value) {
    database.value = project.value = '';
    await request('load', 'new');
  } else if (action.type === 'refresh' && (!dirty.value || uncertain.value))
    await request('list');
  else if (action.type === 'test' && !dirty.value) await request('test');
  else if (
    ['delete', 'bind', 'unbind', 'upgrade'].includes(action.type) &&
    !dirty.value
  )
    confirm.value = action.type;
}
watch(
  () => [props.ticket, props.canAdminister],
  () => {
    generation++;
    confirmSaveResolve?.(false);
    confirmSaveResolve = null;
    confirm.value = '';
    database.value = project.value = '';
    busy.value = false;
    state.value = {
      document: {},
      metadata: {},
      catalog: [],
      identity: '',
      revision: '',
      canWrite: false
    };
    original.value = '{}';
    error.value = '';
    uncertain.value = false;
    if (props.active && props.canAdminister) request('list');
  }
);
watch(
  () => props.active,
  (value) => {
    if (value && props.canAdminister && !state.value.revision) request('list');
  },
  { immediate: true }
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const size = entries.at(-1).contentRect;
    viewport.value = { width: size.width, height: size.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
  state.value.document.password = '';
  confirmSaveResolve?.(false);
});
defineExpose({ dirty, busy, save, discard, request, uncertain });
</script>
<template>
  <div ref="host" class="database-resources">
    <FrameView :scene="scene" @event="dispatch" />
  </div>
</template>
<style scoped>
.database-resources {
  height: 100%;
  min-height: 300px;
  min-width: 0;
}
</style>
