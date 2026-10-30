<script setup>
import {
  computed,
  ref,
  watch,
  onMounted,
  onActivated,
  onDeactivated,
  onBeforeUnmount
} from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/providers.ui.mjs';

const props = defineProps({
  ticket: String,
  project: String,
  embedded: Boolean,
  active: { type: Boolean, default: true }
});
const dialog = ref(null),
  host = ref(null),
  model = ref(UI.initial()),
  viewport = ref({ width: 940, height: 650 });
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
let context = null,
  generation = 0,
  observer,
  timer,
  opened = false;
watch(host, (element) => {
  observer?.disconnect();
  if (element) {
    observer = observeFrameSizes((entries) => {
      const box = entries.at(-1).contentRect;
      viewport.value = { width: box.width, height: box.height };
    });
    observer.observe(element);
  }
});
watch(
  () => [props.ticket, props.project],
  () => {
    generation++;
    context = null;
    model.value = UI.initial();
    if (!props.embedded) dialog.value?.close();
    clearTimeout(timer);
    if (props.embedded && props.active) open();
  }
);
onMounted(() => {
  if (props.embedded && props.active) open();
});
onActivated(() => {
  if (props.embedded && props.active) open();
});
onDeactivated(() => {
  if (props.embedded) closed();
});
watch(
  () => props.active,
  (active) => {
    if (props.embedded) {
      if (active) open();
      else closed();
    }
  }
);
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
  clearTimeout(timer);
});

async function call(action, values = {}) {
  if (!context) return;
  const id = ++generation,
    owner = context;
  model.value.busy = true;
  model.value.error = '';
  try {
    if (action === 'start' || action === 'stop') {
      const reply = await rpc(
        'execute_cmd',
        [
          { ticket: owner.ticket, project: owner.project },
          'tactic.ui.panel.agent_executor_cmd.AgentExecutorCmd',
          { action, project_code: owner.project, target: values.target }
        ],
        {},
        true,
        true
      );
      if (reply.status !== 'OK')
        throw Error(reply.description || 'Agent connection failed');
      if (id !== generation || context !== owner) return;
      action = 'state';
      values = {};
    }
    const reply = await rpc(
      'execute_cmd',
      [
        { ticket: owner.ticket, project: owner.project },
        'tactic.ui.panel.agent_provider_cmd.AgentProviderCmd',
        { action, project_code: owner.project, ...values }
      ],
      {},
      true,
      true
    );
    if (reply.status !== 'OK')
      throw Error(reply.description || 'Provider settings could not be loaded');
    const result =
      typeof reply.info === 'string' ? JSON.parse(reply.info) : reply.info;
    if (id !== generation || context !== owner) return;
    const selected =
      action === 'save' && !model.value.selected
        ? result.profiles.find(
            (row) => !model.value.profiles.some((old) => old.id === row.id)
          )?.id
        : model.value.selected;
    const next = Object.assign({}, model.value, result, { busy: false });
    model.value = UI.select(
      next,
      result.profiles.some((row) => row.id === selected)
        ? selected
        : result.default
    );
    if (action === 'check')
      model.value.notice = 'Waiting for the external host';
    schedule();
  } catch (error) {
    if (id === generation) {
      model.value.error = error.message;
      model.value.busy = false;
    }
  }
}
function schedule() {
  clearTimeout(timer);
  if (opened && model.value.selected)
    timer = setTimeout(() => {
      if (model.value.selected && !UI.dirty(model.value) && !model.value.busy)
        call('state');
      else schedule();
    }, 2000);
}
function event(action) {
  if (model.value.busy) return;
  if (action.type === 'executorTarget')
    model.value.executorTarget = action.value;
  else if (action.type === 'field')
    model.value = UI.edit(model.value, action.field, action.value);
  else if (action.type === 'select' && !UI.dirty(model.value)) {
    model.value = UI.select(model.value, action.value);
    schedule();
  } else if (action.type === 'new' && !UI.dirty(model.value)) {
    model.value = UI.select(model.value, '');
    schedule();
  } else if (action.type === 'reset')
    model.value = UI.select(model.value, model.value.selected);
  else if (action.type === 'refresh' && !UI.dirty(model.value)) call('state');
  else if (
    action.type === 'executor' &&
    ['start', 'stop'].includes(action.value?.action) &&
    !UI.dirty(model.value) &&
    model.value.selected
  )
    call(action.value.action, { target: action.value.target });
  else if (['save', 'check', 'remove'].includes(action.type))
    call(action.type, {
      provider: model.value.selected,
      expected_revision: model.value.revision,
      ...(action.type === 'save' ? { document: { ...model.value.draft } } : {})
    });
}
async function open() {
  if (!props.ticket || !props.project) return;
  context ||= { ticket: props.ticket, project: props.project };
  opened = true;
  if (!props.embedded) dialog.value.show();
  if (
    !model.value.busy &&
    (!UI.dirty(model.value) || !model.value.revision) &&
    (model.value.selected || !model.value.revision)
  )
    await call('state');
}
function closed() {
  opened = false;
  clearTimeout(timer);
}
defineExpose({
  open,
  dirty: computed(() => UI.dirty(model.value)),
  windowContext: () => ({
    route: { provider: model.value.selected },
    state: {
      selected: model.value.selected,
      draft: model.value.draft,
      baseline: model.value.baseline,
      revision: model.value.revision
    }
  }),
  restoreWindowContext: (state) => {
    model.value = UI.select(model.value, state.selected);
    Object.assign(model.value, {
      draft: { ...state.draft },
      baseline: { ...state.baseline },
      revision: state.revision
    });
  }
});
</script>
<template>
  <component
    :is="embedded ? 'section' : AppDialog"
    ref="dialog"
    :title="embedded ? undefined : 'AI providers'"
    window-kind="agent_providers"
    :class="embedded ? 'agent-providers-embedded' : 'agent-providers-dialog'"
    :close-on-outside="false"
    @closed="closed"
  >
    <div ref="host" class="agent-providers-body">
      <FrameView :scene="scene" @event="event" />
    </div>
  </component>
</template>
<style>
.agent-providers-embedded {
  display: flex;
  position: relative;
  height: 100%;
  min-height: 0;
}
.agent-providers-dialog {
  width: min(980px, var(--dialog-owner-width, 96vw));
  height: min(760px, var(--dialog-owner-height, 94dvh));
}
.agent-providers-body {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.agent-providers-body > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
