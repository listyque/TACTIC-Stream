<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import AppDialog from '../../controls/AppDialog.vue';
import { randomUuid } from '../../controls/identity.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';

const props = defineProps({ ticket: String, capture: Function });
const dialog = ref(null),
  body = ref(null),
  size = ref({ width: 900, height: 650 });
const model = ref(UI.initial());
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
  timer,
  contextTicket = '',
  inFlight = false;

async function call(action, values = {}) {
  const result = await rpc(
    'execute_cmd',
    [
      { ticket: contextTicket, project: model.value.context.project },
      'tactic.ui.panel.agent_request_cmd.AgentRequestCmd',
      { action, project_code: model.value.context.project, ...values }
    ],
    {},
    true,
    true
  );
  if (result.status !== 'OK')
    throw new Error(result.description || 'Agent request failed');
  return typeof result.info === 'string'
    ? JSON.parse(result.info)
    : result.info;
}

async function request(action = 'refresh') {
  if (inFlight || !model.value.context.project) return;
  const id = ++generation;
  inFlight = true;
  model.value.busy = action !== 'poll';
  if (action !== 'poll') model.value.error = '';
  try {
    if (action === 'send') {
      model.value.pending ||= {
        request_id: randomUuid(),
        host_id: model.value.hosts.find(
          (host) => !model.value.allowChanges || host.capabilities.changes
        ).host_id,
        document: {
          prompt: model.value.prompt,
          context: JSON.parse(JSON.stringify(model.value.context)),
          allow_changes: model.value.allowChanges
        }
      };
      const saved = await call('submit', model.value.pending);
      if (id !== generation) return;
      model.value.selected = saved.request_id;
      model.value.pending = null;
    } else if (action === 'cancel')
      await call('cancel', { request_id: model.value.selected });
    const state = await call('state');
    if (id !== generation) return;
    Object.assign(model.value, state);
    if (model.value.selected) {
      const current = await call('read', { request_id: model.value.selected });
      if (id !== generation) return;
      model.value.request = current;
    }
  } catch (error) {
    if (id === generation) model.value.error = error.message;
  } finally {
    if (id === generation) {
      model.value.busy = false;
      inFlight = false;
    }
    schedule();
  }
}

function schedule() {
  clearTimeout(timer);
  if (dialog.value?.open) timer = setTimeout(() => request('poll'), 2500);
}
function event(action) {
  if (model.value.busy) return;
  if (action.type === 'prompt' || action.type === 'changes') {
    if (model.value.pending) return;
    if (action.type === 'prompt') model.value.prompt = action.value;
    else model.value.allowChanges = !!action.value;
  } else if (action.type === 'select') {
    generation++;
    inFlight = false;
    if (!action.value) model.value = UI.initial(props.capture());
    else Object.assign(model.value, { selected: action.value, request: {} });
    request();
  } else if (action.type === 'send' && UI.canSend(model.value)) request('send');
  else if (action.type === 'cancel') request('cancel');
  else if (action.type === 'refresh') request();
}
async function open(context) {
  if (!model.value.selected && !model.value.prompt)
    model.value = UI.initial(context || props.capture());
  contextTicket = props.ticket;
  await nextTick();
  if (!dialog.value.open) dialog.value.show();
  observer ||= observeFrameSizes(() => {
    size.value = {
      width: body.value.clientWidth,
      height: body.value.clientHeight
    };
  });
  observer.observe(body.value);
  if (!model.value.context.project)
    model.value.error = 'Select a project before contacting the agent';
  request();
}
function close() {
  dialog.value?.close();
  clearTimeout(timer);
}
watch(
  () => props.ticket,
  () => {
    generation++;
    inFlight = false;
    close();
    contextTicket = '';
    model.value = UI.initial();
  }
);
onBeforeUnmount(() => {
  generation++;
  clearTimeout(timer);
  observer?.disconnect();
});
defineExpose({ open });
</script>

<template>
  <Teleport to="body">
    <AppDialog
      ref="dialog"
      title="External agent"
      window-kind="agent_request"
      class="agent-request-dialog"
      :close-on-outside="false"
      @closed="clearTimeout(timer)"
    >
      <div ref="body" class="agent-request-body">
        <FrameView :scene="scene" @event="event" />
      </div>
    </AppDialog>
  </Teleport>
</template>

<style>
.agent-request-dialog {
  width: min(1000px, 92dvw);
  height: min(760px, 90dvh);
}
.agent-request-dialog > .app-dialog-content {
  padding: 0;
}
.agent-request-body {
  position: relative;
  flex: 1;
  min-height: 0;
  background: var(--page);
}
.agent-request-body > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
