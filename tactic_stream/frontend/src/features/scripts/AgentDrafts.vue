<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { rpc } from '../../api.js';
import { randomUuid } from '../../controls/identity.js';
import { appearance } from '../../appearance.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/drafts.ui.mjs';

const props = defineProps({ ticket: String, project: String });
const emit = defineEmits(['back', 'activated']);
const host = ref(null),
  size = ref({ width: 1000, height: 680 });
const model = ref({
  drafts: [],
  draft: {},
  selected: '',
  busy: false,
  error: '',
  reviewed: false,
  confirming: false
});
const scene = computed(() =>
  UI.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
let generation = 0,
  observer,
  pending;
async function call(action, values = {}) {
  const result = await rpc('execute_cmd', [
    { ticket: props.ticket, project: props.project },
    'tactic.ui.panel.handler_automation_cmd.HandlerAutomationCmd',
    { action, project_code: props.project, ...values }
  ]);
  if (result.status !== 'OK')
    throw new Error(result.description || 'Automation request failed');
  return typeof result.info === 'string'
    ? JSON.parse(result.info)
    : result.info;
}
async function request(action, values = {}) {
  if (model.value.busy) return;
  const id = ++generation;
  model.value.busy = true;
  model.value.error = '';
  try {
    if (action === 'activate') {
      await call('activate', values);
      if (id !== generation) return;
      pending = null;
      emit('activated');
    }
    if (action !== 'select') {
      const catalog = await call('catalog');
      if (id !== generation) return;
      model.value.drafts = catalog.drafts;
      if (!catalog.drafts.some((row) => row.draft_id === model.value.selected))
        model.value.selected = catalog.drafts[0]?.draft_id || '';
    }
    const draft = model.value.selected
      ? await call('draft', { draft_id: model.value.selected })
      : {};
    if (id !== generation) return;
    model.value.draft = draft;
    model.value.reviewed = false;
    model.value.confirming = false;
  } catch (error) {
    if (id === generation) model.value.error = error.message;
  } finally {
    if (id === generation) model.value.busy = false;
  }
}
function event(action) {
  if (model.value.busy) return;
  if (action.type === 'back') emit('back');
  else if (action.type === 'refresh') request('refresh');
  else if (action.type === 'select') {
    model.value.selected = action.value;
    Object.assign(model.value, {
      draft: {},
      reviewed: false,
      confirming: false
    });
    pending = null;
    request('select');
  } else if (action.type === 'reviewed') {
    model.value.reviewed = !!action.value;
    model.value.confirming = false;
  } else if (
    action.type === 'activate' &&
    !model.value.error &&
    model.value.draft.ready &&
    model.value.reviewed
  ) {
    if (!model.value.confirming) {
      model.value.confirming = true;
      return;
    }
    const draft = model.value.draft;
    if (
      !pending ||
      pending.draft_id !== draft.draft_id ||
      pending.draft_revision !== draft.revision ||
      pending.expected_revision !== draft.dependency_revision ||
      JSON.stringify(pending.trial_ids) !== JSON.stringify(draft.trial_ids)
    )
      pending = {
        draft_id: draft.draft_id,
        draft_revision: draft.revision,
        expected_revision: draft.dependency_revision,
        trial_ids: draft.trial_ids,
        operation_id: randomUuid()
      };
    request('activate', pending);
  }
}
watch(
  () => [props.ticket, props.project],
  () => {
    generation++;
    pending = null;
    model.value = {
      drafts: [],
      draft: {},
      selected: '',
      busy: false,
      error: '',
      reviewed: false,
      confirming: false
    };
    request('refresh');
  },
  { immediate: true }
);
onMounted(() => {
  observer = observeFrameSizes(() => {
    size.value = {
      width: host.value.clientWidth,
      height: host.value.clientHeight
    };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
</script>
<template>
  <div ref="host" class="agent-drafts-review" :aria-busy="model.busy">
    <FrameView :scene="scene" @event="event" />
  </div>
</template>
<style>
.agent-drafts-review {
  flex: 1;
  min-height: 400px;
  position: relative;
}
</style>
