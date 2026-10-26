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
import * as History from '../../../../src/tactic_stream/shared_ui/features/scripts/history.ui.mjs';

const props = defineProps({ ticket: String, capture: Function });
const emit = defineEmits(['providers']);
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
const historyModels = computed(() => ({
  agentHistoryRows: History.rows(model.value, appearance.language)
}));
const historyRow = (node, row) =>
  History.row(model.value, row, node.width - 16, appearance.language);
let generation = 0,
  queuedAction = '',
  observer,
  timer,
  contextTicket = '',
  inFlight = false,
  historyTimer,
  libraryOperation = null;

async function call(
  action,
  values = {},
  command = 'tactic.ui.panel.agent_request_cmd.AgentRequestCmd'
) {
  const project =
    action === 'draft' ? values.context.project : model.value.context.project;
  const result = await rpc(
    'execute_cmd',
    [
      { ticket: contextTicket, project },
      command,
      { action, project_code: project, ...values }
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
  let filter = {
    query: model.value.history.query,
    archived: model.value.history.archived
  };
  const before = model.value.requests,
    nextOffset = model.value.next_offset;
  inFlight = true;
  model.value.busy = action !== 'poll';
  if (action !== 'poll') model.value.error = '';
  try {
    if (action === 'send') {
      model.value.pending ||= UI.started(model.value)
        ? {
            message_id: randomUuid(),
            host_id: UI.host(model.value).host_id,
            text: model.value.prompt,
            model: model.value.model ?? model.value.request.model ?? '',
            effort: model.value.effort ?? model.value.request.effort ?? '',
            provider: UI.provider(model.value),
            attachments: model.value.attachments.map(
              (file) => file.attachment_id
            )
          }
        : {
            request_id: model.value.selected || randomUuid(),
            host_id: UI.host(model.value).host_id,
            document: {
              prompt: model.value.prompt,
              context: JSON.parse(
                JSON.stringify(
                  model.value.request.document?.context || model.value.context
                )
              ),
              allow_changes: model.value.allowChanges,
              allow_web: model.value.allowWeb,
              model: model.value.model ?? '',
              effort: model.value.effort ?? '',
              provider: UI.provider(model.value),
              attachments: model.value.attachments.map(
                (file) => file.attachment_id
              )
            }
          };
      const saved = UI.started(model.value)
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
      delete model.value.drafts[saved.request_id];
    } else if (action === 'cancel')
      await call('cancel', { request_id: model.value.selected });
    else if (action === 'undo')
      await call('undo', {
        request_id: model.value.selected,
        operation_id: model.value.request.undo_operation
      });
    else if (action === 'library') {
      const operation = libraryOperation;
      const saved = await call(operation.action, operation.values);
      if (id !== generation) return;
      if (operation.action === 'draft') {
        model.value.drafts[model.value.selected] = History.draft(model.value);
        model.value.selected = saved.request_id;
        model.value.request = saved;
        model.value.context = saved.document.context;
        if (!operation.edit) Object.assign(model.value, History.restored());
        if (!operation.edit && size.value.width < 940)
          model.value.history.mobile = false;
        model.value.history.query = '';
        model.value.history.archived = false;
        filter = { query: '', archived: false };
      } else model.value.history.edit = null;
    }
    const state = await call('state', {
      ...filter,
      ...(action === 'historyMore' ? { offset: nextOffset } : {})
    });
    if (id !== generation) return;
    if (
      filter.query !== model.value.history.query ||
      filter.archived !== model.value.history.archived
    ) {
      queuedAction = 'refresh';
      return;
    }
    if (action === 'historyMore' || action === 'poll') {
      state.requests = History.merge(before, state.requests);
      if (action === 'poll' && before.length) state.next_offset = nextOffset;
    }
    Object.assign(model.value, state);
    if (model.value.selected) {
      const current = await call('read', { request_id: model.value.selected });
      if (id !== generation) return;
      const wasActive =
        UI.active(model.value) &&
        model.value.request.request_id === current.request_id;
      model.value.request = current;
      if (action === 'library' && libraryOperation?.edit)
        model.value.history = History.change(
          model.value,
          {
            type: 'historyEdit',
            value: model.value.selected
          },
          size.value.width < 940
        );
      for (const file of [
        ...model.value.attachments,
        ...(current.messages?.flatMap((message) => message.attachments || []) ||
          [])
      ]) {
        if (
          !file.media_type.startsWith('image/') ||
          file.attachment_id in previews.value
        )
          continue;
        try {
          const preview = await call(
            'preview',
            { attachment_id: file.attachment_id },
            attachmentCommand
          );
          if (id !== generation) return;
          previews.value[file.attachment_id] = preview.url;
        } catch {
          if (id !== generation) return;
          previews.value[file.attachment_id] = '';
        }
      }
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
  if (action.type === 'providers') {
    emit('providers');
    return;
  }
  const previousHistory = model.value.history;
  const changed = History.change(model.value, action, size.value.width < 940);
  if (changed) {
    model.value.history = changed;
    if (
      changed.query !== previousHistory.query ||
      changed.archived !== previousHistory.archived
    ) {
      clearTimeout(historyTimer);
      historyTimer = setTimeout(
        () => request(),
        action.type === 'historyQuery' ? 300 : 0
      );
    }
    return;
  }
  if (model.value.busy) return;
  if (
    action.type === 'historyNew' ||
    (action.type === 'historyEdit' && !action.value)
  ) {
    if (model.value.pending || model.value.uploading) return;
    if (
      !model.value.selected &&
      action.type === 'historyNew' &&
      (model.value.prompt.trim() || model.value.attachments.length)
    ) {
      model.value.error =
        'Send or clear the current draft before opening another object';
      return;
    }
    libraryOperation = {
      action: 'draft',
      edit: action.type === 'historyEdit',
      values: {
        request_id: randomUuid(),
        context:
          action.type === 'historyEdit' ? model.value.context : props.capture()
      }
    };
    request('library');
    return;
  }
  if (
    ['historySave', 'historyArchive', 'historyGroupRemove'].includes(
      action.type
    )
  ) {
    const edit = model.value.history.edit;
    if (!edit) return;
    libraryOperation =
      edit.kind === 'group'
        ? {
            action:
              action.type === 'historyGroupRemove'
                ? 'group_remove'
                : 'group_save',
            values: {
              group: edit.id,
              name: edit.name,
              expected_revision: edit.revision
            }
          }
        : {
            action: 'organize',
            values: {
              request_id: edit.id,
              expected_revision: edit.revision,
              document: {
                title: edit.title,
                group: edit.group,
                pinned: edit.pinned,
                archived:
                  action.type === 'historyArchive'
                    ? !edit.archived
                    : edit.archived
              }
            }
          };
    request('library');
    return;
  }
  if (action.type === 'historyMore') {
    request('historyMore');
    return;
  }
  if (
    action.type === 'prompt' ||
    action.type === 'changes' ||
    action.type === 'web'
  ) {
    if (model.value.pending) return;
    if (action.type === 'prompt') model.value.prompt = action.value;
    else if (action.type === 'changes')
      model.value.allowChanges = !!action.value;
    else model.value.allowWeb = !!action.value;
  } else if (action.type === 'select') {
    if (model.value.uploading || model.value.pending) return;
    if (
      !model.value.selected &&
      (model.value.prompt.trim() || model.value.attachments.length)
    ) {
      model.value.error =
        'Send or clear the current draft before opening another object';
      return;
    }
    model.value.drafts[model.value.selected] = History.draft(model.value);
    generation++;
    inFlight = false;
    queuedAction = '';
    Object.assign(model.value, {
      selected: action.value,
      request: {},
      ...History.restored(model.value.drafts[action.value]),
      pending: null
    });
    model.value.history.edit = null;
    if (size.value.width < 940) model.value.history.mobile = false;
    request();
  } else if (action.type === 'send' && UI.canSend(model.value)) request('send');
  else if (action.type === 'cancel') request('cancel');
  else if (action.type === 'refresh') request();
  else if (action.type === 'provider') {
    model.value.provider = action.value;
    model.value.model = '';
    model.value.effort = '';
  } else if (action.type === 'model') {
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
async function open(context, fresh = false) {
  if (fresh) {
    if (
      model.value.prompt.trim() ||
      model.value.attachments.length ||
      model.value.pending ||
      model.value.uploading
    ) {
      await open();
      throw Error(
        'Send or clear the current draft before opening another object'
      );
    }
    generation++;
    inFlight = false;
    queuedAction = '';
    clearTimeout(timer);
    clearPreviews();
    model.value = Object.assign(UI.initial(context), {
      drafts: model.value.drafts,
      history: model.value.history
    });
  }
  if (
    !model.value.selected &&
    !model.value.prompt &&
    !model.value.attachments.length &&
    !model.value.pending &&
    !model.value.uploading
  )
    model.value = Object.assign(UI.initial(context || props.capture()), {
      history: model.value.history,
      drafts: model.value.drafts
    });
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
  clearTimeout(historyTimer);
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
  clearTimeout(historyTimer);
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
        <FrameView
          :scene="scene"
          :models="historyModels"
          :describe-row="historyRow"
          :views="views"
          @event="event"
        />
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
