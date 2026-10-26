<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/providers.ui.mjs';

const props = defineProps({ ticket: String, project: String });
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
    dialog.value?.close();
    clearTimeout(timer);
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
  if (opened && model.value.profiles.some((row) => row.status === 'waiting'))
    timer = setTimeout(() => {
      if (!UI.dirty(model.value) && !model.value.busy) call('state');
      else schedule();
    }, 2000);
}
function event(action) {
  if (model.value.busy) return;
  if (action.type === 'field')
    model.value = UI.edit(model.value, action.field, action.value);
  else if (action.type === 'select' && !UI.dirty(model.value))
    model.value = UI.select(model.value, action.value);
  else if (action.type === 'new' && !UI.dirty(model.value))
    model.value = UI.select(model.value, '');
  else if (action.type === 'reset')
    model.value = UI.select(model.value, model.value.selected);
  else if (action.type === 'refresh' && !UI.dirty(model.value)) call('state');
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
  dialog.value.show();
  if (!UI.dirty(model.value) || !model.value.revision) await call('state');
}
function closed() {
  opened = false;
  clearTimeout(timer);
}
defineExpose({ open });
</script>
<template>
  <AppDialog
    ref="dialog"
    title="AI providers"
    window-kind="agent_providers"
    class="agent-providers-dialog"
    :close-on-outside="false"
    @closed="closed"
  >
    <div ref="host" class="agent-providers-body">
      <FrameView :scene="scene" @event="event" />
    </div>
  </AppDialog>
</template>
<style>
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
