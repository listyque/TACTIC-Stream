<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import AppDialog from '../../controls/AppDialog.vue';
import { randomUuid } from '../../controls/identity.js';
import AgentChatPort from './AgentChatPort.vue';
import { t } from '../../i18n.js';
import { notify } from '../activity/notifications.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';

const props = defineProps({ ticket: String, capture: Function });
const dialog = ref(null),
  body = ref(null),
  size = ref({ width: 900, height: 650 });
const model = ref(UI.initial());
const fileInput = ref(null),
  previews = ref({});
const attachmentCommand =
  'tactic.ui.panel.agent_attachment_cmd.AgentAttachmentCmd';
const views = computed(() =>
  Object.fromEntries(
    ['context', 'transcript', 'attachments'].map((name) => [
      name,
      {
        component: markRaw(AgentChatPort),
        nodeProps: true,
        props: { previews: previews.value, onEvent: event }
      }
    ])
  )
);
const scene = computed(() =>
  UI.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
let generation = 0,
  queuedAction = '',
  observer,
  timer,
  contextTicket = '',
  inFlight = false;

async function call(
  action,
  values = {},
  command = 'tactic.ui.panel.agent_request_cmd.AgentRequestCmd'
) {
  const result = await rpc(
    'execute_cmd',
    [
      { ticket: contextTicket, project: model.value.context.project },
      command,
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
  if (inFlight) {
    if (action !== 'poll' && !model.value.busy) {
      queuedAction = action;
      model.value.busy = true;
    }
    return;
  }
  if (!model.value.context.project) return;
  const id = ++generation;
  inFlight = true;
  model.value.busy = action !== 'poll';
  if (action !== 'poll') model.value.error = '';
  try {
    if (action === 'send') {
      model.value.pending ||= model.value.selected
        ? {
            message_id: randomUuid(),
            host_id: UI.host(model.value).host_id,
            text: model.value.prompt,
            model: model.value.model ?? model.value.request.model ?? '',
            effort: model.value.effort ?? model.value.request.effort ?? '',
            attachments: model.value.attachments.map(
              (file) => file.attachment_id
            )
          }
        : {
            request_id: randomUuid(),
            host_id: UI.host(model.value).host_id,
            document: {
              prompt: model.value.prompt,
              context: JSON.parse(JSON.stringify(model.value.context)),
              allow_changes: model.value.allowChanges,
              model: model.value.model ?? '',
              effort: model.value.effort ?? '',
              attachments: model.value.attachments.map(
                (file) => file.attachment_id
              )
            }
          };
      const saved = model.value.selected
        ? await call('message', {
            request_id: model.value.selected,
            ...model.value.pending
          })
        : await call('submit', model.value.pending);
      if (id !== generation) return;
      model.value.selected = saved.request_id;
      model.value.pending = null;
      model.value.prompt = '';
      model.value.attachments = [];
    } else if (action === 'cancel')
      await call('cancel', { request_id: model.value.selected });
    else if (action === 'undo')
      await call('undo', {
        request_id: model.value.selected,
        operation_id: model.value.request.undo_operation
      });
    const state = await call('state');
    if (id !== generation) return;
    Object.assign(model.value, state);
    if (model.value.selected) {
      const current = await call('read', { request_id: model.value.selected });
      if (id !== generation) return;
      const wasActive = UI.active(model.value);
      model.value.request = current;
      if (wasActive && !UI.active(model.value))
        notify(
          current.status === 'completed' && current.outcome === 'completed'
            ? 'complete'
            : 'warning',
          UI.status(model.value, appearance.language).text,
          model.value.context.title || model.value.context.project,
          'agent-request',
          current.request_id + ':' + current.turn
        );
    }
  } catch (error) {
    if (id === generation) model.value.error = error.message;
  } finally {
    if (id === generation) {
      model.value.busy = false;
      inFlight = false;
    }
    if (id === generation && queuedAction) {
      const next = queuedAction;
      queuedAction = '';
      request(next);
    } else schedule();
  }
}

function schedule() {
  clearTimeout(timer);
  if (dialog.value?.open || UI.active(model.value))
    timer = setTimeout(() => request('poll'), 2500);
}
function event(action) {
  if (model.value.busy) return;
  if (action.type === 'prompt' || action.type === 'changes') {
    if (model.value.pending) return;
    if (action.type === 'prompt') model.value.prompt = action.value;
    else model.value.allowChanges = !!action.value;
  } else if (action.type === 'select') {
    if (model.value.uploading) return;
    if (action.value !== model.value.selected) clearPreviews();
    generation++;
    inFlight = false;
    queuedAction = '';
    if (!action.value) model.value = UI.initial(props.capture());
    else
      Object.assign(model.value, {
        selected: action.value,
        request: {},
        prompt: '',
        attachments: [],
        model: null,
        effort: null,
        pending: null
      });
    request();
  } else if (action.type === 'send' && UI.canSend(model.value)) request('send');
  else if (action.type === 'cancel') request('cancel');
  else if (action.type === 'refresh') request();
  else if (action.type === 'model') {
    model.value.model = action.value;
    model.value.effort = '';
  } else if (action.type === 'effort') model.value.effort = action.value;
  else if (action.type === 'context')
    model.value.contextExpanded = !model.value.contextExpanded;
  else if (action.type === 'remove' && !model.value.pending)
    model.value.attachments = model.value.attachments.filter(
      (file) => file.attachment_id !== action.value
    );
  else if (action.type === 'attach') fileInput.value.click();
  else if (action.type === 'paste') pasteClipboard();
  else if (action.type === 'download') download(action.value);
  else if (action.type === 'undo') request('undo');
}
function clearPreviews() {
  Object.values(previews.value).forEach((url) => URL.revokeObjectURL(url));
  previews.value = {};
}
async function addFiles(files) {
  const state = model.value;
  if (state.uploading || state.pending || state.busy) return;
  state.uploading = true;
  state.error = '';
  try {
    if (state.attachments.length + files.length > 20)
      throw new Error('Attach at most 20 files');
    for (const file of files) {
      if (file.size > 64 * 1024 * 1024)
        throw new Error('Each attachment must be at most 64 MB');
      const attachment_id = randomUuid();
      await call(
        'start',
        {
          attachment_id,
          name: file.name,
          size: file.size,
          media_type: file.type
        },
        attachmentCommand
      );
      for (let offset = 0; offset < file.size; offset += 384 * 1024) {
        if (model.value !== state) return;
        const bytes = new Uint8Array(
          await file.slice(offset, offset + 384 * 1024).arrayBuffer()
        );
        let binary = '';
        for (let index = 0; index < bytes.length; index += 8192)
          binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
        await call(
          'append',
          { attachment_id, offset, data: btoa(binary) },
          attachmentCommand
        );
      }
      const metadata = await call(
        'finish',
        { attachment_id },
        attachmentCommand
      );
      if (model.value !== state) return;
      if (file.type.startsWith('image/'))
        previews.value[attachment_id] = URL.createObjectURL(file);
      state.attachments.push(metadata);
    }
  } catch (error) {
    state.error = error.message;
  } finally {
    state.uploading = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}
function paste(event) {
  const files = event.clipboardData?.files;
  if (files?.length) {
    event.preventDefault();
    addFiles([...files]);
  }
}
async function pasteClipboard() {
  try {
    if (!navigator.clipboard?.read)
      throw new Error(
        'Press Ctrl+V in the message to attach clipboard files or images'
      );
    const files = [];
    for (const item of await navigator.clipboard.read()) {
      const type = item.types.find((type) => type.startsWith('image/'));
      if (type)
        files.push(
          new File(
            [await item.getType(type)],
            'clipboard-' + Date.now() + '.png',
            { type }
          )
        );
    }
    if (!files.length)
      throw new Error(
        'Press Ctrl+V in the message to attach clipboard files or images'
      );
    await addFiles(files);
  } catch (error) {
    model.value.error = error.message;
  }
}
async function download(attachment_id) {
  try {
    const chunks = [];
    let offset = 0,
      result;
    do {
      result = await call('read', { attachment_id, offset }, attachmentCommand);
      chunks.push(
        Uint8Array.from(atob(result.data), (char) => char.charCodeAt(0))
      );
      offset = result.next_offset;
    } while (offset !== null);
    const url = URL.createObjectURL(
      new Blob(chunks, { type: result.media_type })
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = result.name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    model.value.error = error.message;
  }
}
async function open(context) {
  if (!model.value.selected && !model.value.prompt)
    model.value = UI.initial(context || props.capture());
  contextTicket = props.ticket;
  await nextTick();
  if (!dialog.value.open) dialog.value.show();
  observer ||= observeFrameSizes(() => {
    if (body.value.clientWidth > 0 && body.value.clientHeight > 0)
      size.value = {
        width: body.value.clientWidth,
        height: body.value.clientHeight
      };
  });
  observer.observe(body.value);
  if (body.value.clientWidth > 0 && body.value.clientHeight > 0)
    size.value = {
      width: body.value.clientWidth,
      height: body.value.clientHeight
    };
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
    queuedAction = '';
    close();
    contextTicket = '';
    clearPreviews();
    model.value = UI.initial();
  }
);
onBeforeUnmount(() => {
  generation++;
  clearTimeout(timer);
  observer?.disconnect();
  clearPreviews();
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
      @closed="schedule"
    >
      <div
        ref="body"
        class="agent-request-body"
        @paste="paste"
        @dragover.prevent
        @drop.prevent="addFiles([...$event.dataTransfer.files])"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          hidden
          :aria-label="t('Attach files')"
          @change="addFiles([...$event.target.files])"
        />
        <FrameView :scene="scene" :views="views" @event="event" />
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
