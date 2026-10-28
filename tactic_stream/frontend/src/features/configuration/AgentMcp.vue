<script setup>
import { computed, ref, watch, onBeforeUnmount, nextTick } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { copyText } from '../../controls/clipboard.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/mcp.ui.mjs';
const props = defineProps({ ticket: String, project: String });
const dialog = ref(null),
  host = ref(null),
  model = ref(UI.initial()),
  size = ref({ width: 800, height: 650 });
const scene = computed(() =>
  UI.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
let context,
  focusConnection = '',
  generation = 0,
  observer;
watch(host, (element) => {
  observer?.disconnect();
  if (element) {
    observer = observeFrameSizes((entries) => {
      const box = entries.at(-1).contentRect;
      size.value = { width: box.width, height: box.height };
    });
    observer.observe(element);
  }
});
function clear() {
  ++generation;
  context = null;
  model.value = UI.initial();
}
function reset() {
  clear();
  dialog.value?.close();
}
watch(() => [props.ticket, props.project], reset);
onBeforeUnmount(() => {
  ++generation;
  observer?.disconnect();
});
async function call(action, values = {}, copyLink = false) {
  if (!context || model.value.busy) return;
  const id = ++generation,
    owner = context;
  model.value.busy = true;
  model.value.error = '';
  try {
    const reply = await rpc(
      'execute_cmd',
      [
        { ticket: owner.ticket, project: owner.project },
        'tactic.ui.panel.agent_mcp_cmd.AgentMcpCmd',
        { action, project_code: owner.project, ...values }
      ],
      {},
      true,
      true
    );
    if (reply.status !== 'OK')
      throw Error(reply.description || 'MCP connections could not be loaded');
    const result =
      typeof reply.info === 'string' ? JSON.parse(reply.info) : reply.info;
    if (id !== generation || owner !== context) return;
    if (action === 'create' || action === 'reveal') {
      model.value.issued = JSON.stringify(
        {
          url: new URL(result.path, location.origin).href,
          headers: { Authorization: 'Bearer ' + result.token }
        },
        null,
        2
      );
      model.value.busy = false;
      await call('state');
      if (copyLink && context === owner)
        copyText(UI.agentLink(model.value.issued)).catch((error) => {
          if (context === owner) model.value.error = error.message;
        });
    } else
      Object.assign(model.value, result, {
        busy: false,
        project: owner.project,
        connections: result.connections
          .map((item) => ({
            ...item,
            expired: item.expires !== null && item.expires <= Date.now() / 1000,
            expiresLabel:
              item.expires === null
                ? ''
                : new Date(item.expires * 1000).toLocaleString()
          }))
          .sort(
            (a, b) =>
              Number(b.id === focusConnection) -
              Number(a.id === focusConnection)
          )
      });
  } catch (error) {
    if (id === generation)
      Object.assign(model.value, { busy: false, error: error.message });
  }
}
function event(action) {
  if (model.value.busy) return;
  model.value = UI.edit(model.value, action);
  if (action.type === 'refresh') call('state');
  else if (action.type === 'revoke' || action.type === 'reveal')
    call(action.type, { id: action.id });
  else if (action.type === 'reveal_link')
    call('reveal', { id: action.id }, true);
  else if (action.type === 'copy' || action.type === 'copy_link')
    copyText(
      action.type === 'copy_link'
        ? UI.agentLink(model.value.issued)
        : model.value.issued
    ).catch((error) => {
      model.value.error = error.message;
    });
  else if (action.type === 'create')
    call('create', {
      title: model.value.title,
      instructions: model.value.instructions,
      minutes: Number(model.value.minutes),
      tools: [...model.value.selected],
      context: ownerContext()
    });
}
function ownerContext() {
  const { ticket, ...value } = context;
  return value;
}
async function open(value, connectionId = '') {
  clear();
  if (!props.ticket || !value?.project) return;
  context = { ...structuredClone(value), ticket: props.ticket };
  focusConnection = connectionId;
  dialog.value.show();
  await call('state');
  await nextTick();
  if (focusConnection && model.value.connections[0]?.id === focusConnection)
    host.value
      ?.querySelector('[data-frame=mcpCollect_0]')
      ?.scrollIntoView({ block: 'center' });
}
defineExpose({ open });
</script>
<template>
  <AppDialog
    ref="dialog"
    title="MCP connections"
    window-kind="agent_mcp"
    class="agent-mcp-dialog"
    :close-on-outside="false"
    @closed="clear"
  >
    <div ref="host" class="agent-mcp-body">
      <FrameView :scene="scene" @event="event" />
    </div>
  </AppDialog>
</template>
<style>
.agent-mcp-dialog {
  width: min(880px, var(--dialog-owner-width, 96vw));
  height: min(780px, var(--dialog-owner-height, 94dvh));
}
.agent-mcp-body {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.agent-mcp-body > .frame-view {
  position: absolute;
  inset: 0;
}
</style>
