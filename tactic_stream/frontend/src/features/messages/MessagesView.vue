<script setup>
// MessagesView.qml / MessagesController: one screen owns requests, drafts and history surfaces.
import {
  inject,
  ref,
  shallowReactive,
  computed,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount
} from 'vue';
import InitializationState from '../collaboration/InitializationState.vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppTextField from '../../controls/AppTextField.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import AppSplitter from '../../controls/AppSplitter.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import UserPicker from '../../controls/UserPicker.vue';
import ItemSurface from '../../controls/ItemSurface.vue';
import { serverClock } from '../../serverClock.js';
import { timestampLabel } from '../activity/activity.js';
import {
  copyText,
  copyImage,
  readClipboardImages
} from '../../controls/clipboard.js';
import { downloadBlob } from '../../controls/files.js';
import ConversationList from './ConversationList.vue';
import MessageBubble from './MessageBubble.vue';
import MessageComposer from './MessageComposer.vue';
import MessageReference from './MessageReference.vue';
import FilePreview from '../objects/FilePreview.vue';
import AttachmentItem from './AttachmentItem.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import {
  messagesRequest,
  messageFileRequest,
  linkPreviews
} from '../../api.js';
import { updatesAvailable } from '../connection/updateRequests.js';
import { extractSkeys } from '../../controls/richText.js';
import { projectPath } from '../workspace/links.js';
import { skeyPlaceholder } from '../objects/skeyPreviews.js';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import {
  messageId,
  initials,
  groupedMessages,
  mergeMessages,
  retainOlderMessages,
  canChangeMessage,
  conversationColor,
  attachmentName,
  formatFileSize,
  conversationAttachments,
  messageAttachments
} from './messages.js';
import ChatHeader from './ChatHeader.vue';
import MessageForm from './MessageForm.vue';
import FrameView from '../../frame/FrameView.vue';
import PinnedMessage from './PinnedMessage.vue';
import MessageMembers from './MessageMembers.vue';
import MessageRevision from './MessageRevision.vue';
import MessagePanelHeader from './MessagePanelHeader.vue';
import MessageForward from './MessageForward.vue';
import AttachmentComposerControls from './AttachmentComposerControls.vue';
import * as Messaging from '../../../../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs';
import './messages.css';

const chatAnchor = ref(null);
function headerEvent(event, source) {
  if (event.type === 'back') listVisible.value = true;
  else if (event.type === 'refresh') refresh();
  else if (event.type === 'menu') {
    chatAnchor.value = source;
    if (chatMenu.value.open) chatMenu.value.close(true);
    else chatMenu.value.openAt({ target: source });
  } else
    showEditor(event.type === 'members' ? 'view-members' : event.type, null, {
      currentTarget: source
    });
}
const openHelp = inject('openHelp');
const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  updates: Object,
  updatesError: String
});
const emit = defineEmits([
  'unread',
  'notification',
  'open-link',
  'session-expired',
  'quick-reply-sent',
  'quick-reply-failed',
  'attachment-location',
  'open-profile'
]);
const fileActions = ref({});
const previews = ref({});
const clockTick = ref(0);
const now = computed(() => {
  clockTick.value;
  return serverClock.now();
});
let previewRequest = 0;
const quickReplies = new Set();
const dialog = ref(null),
  editor = ref(null),
  viewport = ref(null),
  composer = ref(null),
  chatMenu = ref(null);
const followBottom = ref(true);
const visible = ref(false),
  busy = ref(false),
  loading = ref(false),
  sending = ref(false),
  opening = ref(false),
  error = ref('');
const initialized = ref(false),
  canInitialize = ref(false),
  canCreateGroup = ref(false),
  permissions = ref({}),
  privileged = ref(false);
const conversations = ref([]),
  users = ref([]),
  current = ref(''),
  records = ref([]),
  pinned = ref({}),
  pinHistory = ref([]);
const search = ref(''),
  searchOpen = ref(false),
  more = ref(false),
  offset = ref(0),
  paneWidth = ref(252),
  listVisible = ref(true);
const draft = ref(''),
  reply = ref(null),
  selected = ref([]),
  mode = ref(''),
  target = ref(null),
  title = ref(''),
  editText = ref(''),
  recipients = ref([]),
  targets = ref([]);
const formModes = [
  'create',
  'members',
  'rename',
  'edit',
  'search',
  'clear',
  'delete',
  'delete-message'
];
const formText = computed({
  get: () =>
    mode.value === 'edit'
      ? editText.value
      : mode.value === 'search'
        ? searchDraft.value
        : title.value,
  set: (value) => {
    if (mode.value === 'edit') editText.value = value;
    else if (mode.value === 'search') searchDraft.value = value;
    else title.value = value;
  }
});
const editorChat = ref('');
const editorAnchor = ref(null),
  searchDraft = ref('');
const editorPopup = computed(() =>
  [
    'create',
    'members',
    'view-members',
    'files',
    'rename',
    'history',
    'pin-history',
    'search'
  ].includes(mode.value)
);
const editorCentered = computed(() => !Messaging.popup(mode.value).anchored);
const editorWidth = computed(() => Messaging.popup(mode.value).width);
const pickerKey = ref(0);
const attachments = ref([]),
  fileInput = ref(null),
  previewInput = ref(null),
  filePreview = ref(null);
const previewUrls = new Map();
const newFileToken = () =>
  [...crypto.getRandomValues(new Uint8Array(16))]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');
const notifications = ref(true),
  cache = shallowReactive(new Map()),
  viewports = new Map(),
  drafts = {},
  seen = new Set();
let openRequest = 0;
let epoch = 0,
  listRequest = 0,
  historyRequest = 0,
  mutationRequest = 0,
  listLoading = false,
  pendingList = false,
  stopped = false,
  baseline = true,
  lastRead = '',
  draftKey = '';
const storageKey = computed(() => 'tactic_stream.messages.' + props.login);
const conversation = computed(() =>
  conversations.value.find((row) => row.conversationId === current.value)
);
const peer = computed(() =>
  conversation.value?.recipients?.length === 1
    ? users.value.find((row) => row.login === conversation.value.recipients[0])
    : null
);
const presence = computed(() =>
  props.updates?.presence?.find(
    (row) => row.login === conversation.value?.recipients?.[0]
  )
);
const presenceText = computed(() => {
  if (!presence.value) return t('Status unavailable');
  if (presence.value.online) return t('Online');
  const seen = timestampLabel(presence.value.lastSeen, new Date(now.value));
  return seen ? t('Last seen {time}', { time: seen }) : t('Offline');
});
const members = computed(() =>
  [...new Set([props.login, ...(conversation.value?.recipients || [])])]
    .map((login) => users.value.find((row) => row.login === login))
    .filter(Boolean)
);
const invalidRecipients = computed(
  () =>
    !recipients.value.length ||
    (mode.value === 'create' &&
      recipients.value.length > 1 &&
      (!canCreateGroup.value || !title.value.trim()))
);
const invalidEditor = computed(() =>
  ['create', 'members'].includes(mode.value)
    ? invalidRecipients.value
    : mode.value === 'rename'
      ? !title.value.trim()
      : mode.value === 'edit'
        ? !editText.value.trim()
        : mode.value === 'forward'
          ? !targets.value.length || !selected.value.length
          : false
);
const historyEntries = computed(() =>
  mode.value === 'pin-history'
    ? pinHistory.value.map((entry) => ({
        ...entry,
        summary: entry.summary || pinSummary(entry)
      }))
    : target.value?.__edit_history__ || []
);
const timelineId = computed(() =>
  search.value ? 'search' : current.value ? 'chat:' + current.value : 'empty'
);
const timelines = computed(() => {
  const values = [...cache.values()];
  if (search.value)
    values.push({
      id: 'search',
      chat: current.value,
      records: records.value,
      pinned: pinned.value,
      previews: previews.value,
      more: more.value,
      loaded: !loading.value,
      loadFile: fileBlob
    });
  if (!current.value)
    values.push({ id: 'empty', records: [], previews: {}, loaded: true });
  return values;
});
const presented = computed(() =>
  search.value ? !loading.value : !!cache.get(current.value)?.loaded
);
const gallery = computed(() =>
  conversationAttachments(records.value, users.value)
);
const titleFor = (row) =>
  row?.isPersonalNotes
    ? t('Favorites')
    : row?.title || t('Select a conversation');
const ownIdentity = (login) => users.value.find((row) => row.login === login);
const request = (action, values = {}) => {
  if (stopped || !props.ticket)
    return Promise.reject(
      Object.assign(new Error('Authentication required'), {
        code: 'authentication_failed'
      })
    );
  return messagesRequest(action, props.ticket, props.project, values);
};
const actionTitles = {
  create: 'New conversation',
  rename: 'Rename chat',
  members: 'Add or remove members',
  'view-members': 'Chat members',
  search: 'Search this conversation',
  forward: 'Forward messages',
  edit: 'Edit message',
  history: 'Edit history',
  'pin-history': 'Pin history',
  files: 'Chat files',
  attachment: 'View attachment',
  'delete-message': 'Delete message',
  delete: 'Delete chat',
  clear: 'Clear favorites',
  preview: 'Change preview'
};

function pinSummary(entry) {
  // Handler _pin_preview / _message_content_preview: describe files and links even without a body.
  const row = records.value.find((row) => messageId(row) === entry.messageId),
    body = row?.message || entry.body || '';
  const links = extractSkeys(body),
    text = links
      .reduce((text, link) => text.replaceAll(link, ' '), body)
      .replace(/\s+/g, ' ')
      .replace(/^[ ·,;:|\-]+|[ ·,;:|\-]+$/g, '');
  if (text) return text;
  if (links.length)
    return t(
      links.every((link) => link.includes('/message_log?'))
        ? 'Linked messages'
        : 'Linked TACTIC items'
    );
  if (row && messageAttachments(row).length) return t('Attached files');
  if (row?.__forwarded_from__) return t('Forwarded message');
  if (row?.__reply__) return t('Reply message');
  return t('Pinned message');
}

function fail(failure) {
  error.value =
    failure instanceof TypeError
      ? 'Unable to reach the server.'
      : failure.message;
  if (failure.code === 'authentication_failed') expireSession();
}
function expireSession() {
  if (stopped) return;
  stopped = true;
  pendingList = false;
  emit('session-expired');
}
function saveDraft() {
  if (!draftKey) return;
  if (current.value)
    drafts[current.value] = {
      text: draft.value,
      reply: reply.value,
      attachments: attachments.value
    };
  const stored = Object.fromEntries(
    Object.entries(drafts).map(([key, value]) => [
      key,
      {
        ...value,
        attachments: (value.attachments || []).map(
          ({ token, name, size, snapshot }) => ({ token, name, size, snapshot })
        )
      }
    ])
  );
  try {
    localStorage.setItem(
      draftKey,
      JSON.stringify({
        drafts: stored,
        selected: current.value,
        notifications: notifications.value
      })
    );
  } catch {
    error.value =
      'Drafts could not be saved in this browser. Keep this window open.';
  }
}
watch([draft, reply, notifications], saveDraft);
watch(attachments, saveDraft, { deep: true });
function unread() {
  emit(
    'unread',
    conversations.value.reduce((sum, row) => sum + Number(row.unread || 0), 0)
  );
}
async function loadList() {
  clockTick.value++;
  if (listLoading) {
    pendingList = true;
    return;
  }
  if (stopped || !props.ticket) return;
  listLoading = true;
  const generation = epoch,
    id = ++listRequest;
  try {
    let result = await request('list');
    if (generation !== epoch || stopped) return;
    if (
      result.initialized &&
      result.permissions.create &&
      !result.conversations.some((row) => row.isPersonalNotes)
    ) {
      await request('create', { recipients: [] });
      result = await request('list');
      if (generation !== epoch || stopped) return;
    }
    initialized.value = result.initialized;
    canInitialize.value = result.canInitialize;
    permissions.value = result.permissions || {};
    privileged.value = result.canDeleteMessages;
    canCreateGroup.value = result.canCreateGroup;
    for (const row of result.conversations) {
      const signature =
        row.conversationId + ':' + row.lastTimestamp + ':' + row.lastMessage;
      if (
        !baseline &&
        !seen.has(signature) &&
        row.unread &&
        row.lastSender !== props.login &&
        notifications.value &&
        !(
          visible.value &&
          (!mobile.value || !listVisible.value) &&
          current.value === row.conversationId
        )
      )
        emit('notification', {
          conversationId: row.conversationId,
          title: titleFor(row),
          message: row.lastMessage || t('New message'),
          sender: row.lastSender,
          canReply: !!permissions.value.send
        });
      seen.add(signature);
    }
    while (seen.size > 500) seen.delete(seen.values().next().value);
    baseline = false;
    conversations.value = [...result.conversations].sort(
      (a, b) => Number(b.isPersonalNotes) - Number(a.isPersonalNotes)
    );
    unread();
    loadConversationPreviews();
    for (const id of cache.keys())
      if (!conversations.value.some((row) => row.conversationId === id))
        cache.delete(id);
    if (current.value && !conversation.value) {
      historyRequest++;
      previewRequest++;
      loading.value = false;
      editor.value?.close();
      current.value = '';
      viewport.value = null;
      records.value = [];
      previews.value = {};
      pinned.value = {};
      selected.value = [];
    }
    prunePreviewUrls();
    if (
      visible.value &&
      !mobile.value &&
      !current.value &&
      conversations.value.length
    )
      await select(conversations.value[0].conversationId);
  } catch (failure) {
    if (generation === epoch) fail(failure);
  } finally {
    if (id === listRequest) listLoading = false;
    if (pendingList && !stopped) {
      pendingList = false;
      loadList();
    }
  }
}
async function people() {
  if (stopped || !props.ticket) return;
  const generation = epoch;
  try {
    const result = await request('people');
    if (generation === epoch) users.value = result.users;
  } catch (failure) {
    if (generation === epoch) fail(failure);
  }
}
function remember() {
  saveDraft();
  if (current.value && !search.value) {
    const state = cache.get(current.value);
    if (state)
      Object.assign(state, {
        records: records.value,
        pinned: pinned.value,
        pinHistory: pinHistory.value,
        more: more.value,
        offset: offset.value,
        previews: previews.value,
        scroll: viewport.value?.scrollTop || 0,
        follow: followBottom.value
      });
  }
}
watch([records, pinned, pinHistory, more, offset, previews], () => {
  if (search.value) return;
  const state = cache.get(current.value);
  if (state)
    Object.assign(state, {
      records: records.value,
      pinned: pinned.value,
      pinHistory: pinHistory.value,
      more: more.value,
      offset: offset.value,
      previews: previews.value
    });
});
function prunePreviewUrls() {
  const keep = new Set(
    [
      ...Object.values(previews.value),
      ...[...cache.values()].flatMap((state) => Object.values(state.previews))
    ].map((row) => row.previewUrl)
  );
  for (const [key, value] of previewUrls)
    if (key.startsWith('skey:') && !keep.has(value.url)) {
      URL.revokeObjectURL(value.url);
      previewUrls.delete(key);
    }
}
async function select(id, focusComposer = true) {
  if (editorPopup.value) editor.value?.close();
  if (
    id === current.value &&
    !search.value &&
    cache.has(id) &&
    (cache.get(id).loaded || loading.value)
  ) {
    listVisible.value = false;
    return;
  }
  remember();
  const generation = epoch;
  for (const menu of viewport.value?.querySelectorAll(
    '.workspace-menu[open]'
  ) || [])
    menu.open = false;
  let saved = cache.get(id);
  if (saved) {
    cache.delete(id);
    cache.set(id, saved);
  } else {
    saved = shallowReactive({
      id: 'chat:' + id,
      chat: id,
      records: [],
      pinned: {},
      pinHistory: [],
      more: false,
      offset: 0,
      scroll: 0,
      follow: true,
      previews: {},
      loaded: false,
      dirty: false,
      serverTimestamp: '',
      loadFile: (snapshot, file) => fileBlob(snapshot, file, id)
    });
    cache.set(id, saved);
  }
  while (cache.size > 12) cache.delete(cache.keys().next().value);
  historyRequest++;
  previewRequest++;
  loading.value = false;
  current.value = id;
  lastRead = '';
  selected.value = [];
  search.value = '';
  searchOpen.value = false;
  listVisible.value = false;
  draft.value = drafts[id]?.text || '';
  reply.value = drafts[id]?.reply || null;
  attachments.value = drafts[id]?.attachments || [];
  records.value = saved.records;
  pinned.value = saved.pinned;
  pinHistory.value = saved.pinHistory;
  more.value = saved.more;
  offset.value = saved.offset;
  followBottom.value = saved.follow;
  previews.value = saved.previews;
  for (const [key, preview] of Object.entries(previews.value))
    if (preview.status === 'loading') delete previews.value[key];
  viewport.value = viewports.get(timelineId.value) || null;
  prunePreviewUrls();
  await nextTick();
  if (generation !== epoch || current.value !== id) return;
  viewport.value = viewports.get(timelineId.value) || null;
  if (viewport.value)
    viewport.value.scrollTop = saved.loaded
      ? saved.scroll
      : viewport.value.scrollHeight;
  if (focusComposer && !mobile.value) composer.value?.focus();
  if (
    !saved.loaded ||
    saved.dirty ||
    saved.serverTimestamp !== (conversation.value?.lastTimestamp || '')
  )
    await loadHistory(true, saved.loaded);
  else {
    markRead();
    loadPreviews(records.value.flatMap((row) => extractSkeys(row.message)));
  }
}
async function conversationContext(id, event) {
  const generation = epoch;
  const selection = select(id, false);
  await nextTick();
  if (generation === epoch && current.value === id && visible.value)
    chatMenu.value?.openAt(event);
  await selection;
}
async function loadHistory(reset = true, background = false) {
  if (
    stopped ||
    !props.ticket ||
    !current.value ||
    (loading.value && (!reset || background)) ||
    (!reset && !more.value)
  )
    return;
  const generation = epoch,
    id = ++historyRequest,
    chat = current.value,
    query = search.value,
    start = reset ? 0 : offset.value,
    serverTimestamp = conversation.value?.lastTimestamp || '';
  loading.value = true;
  const previousTop = viewport.value?.scrollTop || 0,
    previousHeight = viewport.value?.scrollHeight || 0;
  const anchor =
    viewport.value &&
    [...viewport.value.querySelectorAll('[data-message-id]')].find(
      (node) =>
        node.getBoundingClientRect().bottom >
        viewport.value.getBoundingClientRect().top
    );
  const anchorId = anchor?.dataset.messageId,
    anchorTop = anchor?.getBoundingClientRect().top,
    atEnd = followBottom.value;
  try {
    const result = await request('history', {
      message_code: chat,
      limit: 31,
      offset: start,
      search_text: query
    });
    const page = result.messages.slice(0, 30),
      retained = new Set(background ? records.value.map(messageId) : []);
    let hasMore = result.messages.length > 30;
    // Native MessagesController catches up to retained history after a burst; HTTP pages stay bounded.
    while (
      retained.size &&
      hasMore &&
      !page.some((row) => retained.has(messageId(row)))
    ) {
      if (
        generation !== epoch ||
        id !== historyRequest ||
        chat !== current.value ||
        query !== search.value ||
        stopped
      )
        return;
      const older = await request('history', {
        message_code: chat,
        limit: 31,
        offset: page.length,
        search_text: query
      });
      page.push(...older.messages.slice(0, 30));
      hasMore = older.messages.length > 30;
    }
    if (
      generation !== epoch ||
      id !== historyRequest ||
      chat !== current.value ||
      query !== search.value ||
      stopped
    )
      return;
    const keep =
      background && hasMore
        ? retainOlderMessages(records.value, page)
        : reset
          ? []
          : records.value;
    const incoming = new Set(page.map(messageId)),
      keptOlder = keep.some((row) => !incoming.has(messageId(row)));
    records.value = mergeMessages([...keep, ...page]);
    pinned.value = result.pinnedMessage || {};
    pinHistory.value = result.pinHistory || [];
    if (!background) {
      offset.value = start + page.length;
      more.value = hasMore;
    } else {
      offset.value = records.value.length;
      if (!keptOlder) more.value = hasMore;
    }
    const state = cache.get(chat);
    if (state && !query) {
      state.loaded = true;
      state.dirty = false;
      state.serverTimestamp = serverTimestamp;
    }
    await nextTick();
    viewport.value = viewports.get(timelineId.value) || null;
    if (viewport.value) {
      const restored =
        anchorId &&
        [...viewport.value.querySelectorAll('[data-message-id]')].find(
          (node) => node.dataset.messageId === anchorId
        );
      viewport.value.scrollTop = reset
        ? background && !atEnd
          ? restored
            ? viewport.value.scrollTop +
              restored.getBoundingClientRect().top -
              anchorTop
            : previousTop
          : viewport.value.scrollHeight
        : previousTop + viewport.value.scrollHeight - previousHeight;
    }
    markRead();
    return true;
  } catch (failure) {
    if (generation === epoch && id === historyRequest) fail(failure);
  } finally {
    if (generation === epoch && id === historyRequest) loading.value = false;
  }
}
async function markRead() {
  if (
    stopped ||
    !props.ticket ||
    !updatesAvailable() ||
    !visible.value ||
    (mobile.value && listVisible.value) ||
    document.hidden ||
    !document.hasFocus() ||
    !permissions.value.read ||
    search.value ||
    !records.value.length
  )
    return;
  const stamp = records.value.at(-1).timestamp?.slice(0, 19),
    chat = current.value,
    generation = epoch;
  if (!stamp || stamp <= lastRead) return;
  lastRead = stamp;
  try {
    await request('read', { message_code: chat, timestamp: stamp });
    if (generation === epoch && chat === current.value && conversation.value) {
      conversation.value.unread = 0;
      conversation.value.mentionCount = 0;
      unread();
    }
  } catch (failure) {
    if (generation === epoch && chat === current.value) {
      lastRead = '';
      fail(failure);
    }
  }
}
function scroll() {
  if (!viewport.value) return;
  followBottom.value =
    viewport.value.scrollHeight -
      viewport.value.scrollTop -
      viewport.value.clientHeight <
    36;
  if (viewport.value.scrollTop < 64 && more.value && !loading.value)
    loadHistory(false);
}
function latest() {
  if (viewport.value)
    viewport.value.scrollTo({
      top: viewport.value.scrollHeight,
      behavior: parseFloat(
        getComputedStyle(viewport.value).getPropertyValue('--motion-medium')
      )
        ? 'smooth'
        : 'instant'
    });
}
async function jump(id) {
  if (!id) return;
  const generation = epoch,
    chat = current.value;
  let node = [
    ...(viewport.value?.querySelectorAll('[data-message-id]') || [])
  ].find((node) => node.dataset.messageId === id);
  while (!node && more.value && !loading.value) {
    if (!(await loadHistory(false))) return;
    if (generation !== epoch || chat !== current.value || !visible.value)
      return;
    node = [
      ...(viewport.value?.querySelectorAll('[data-message-id]') || [])
    ].find((node) => node.dataset.messageId === id);
  }
  if (node) {
    node.scrollIntoView({ block: 'center', behavior: 'smooth' });
    node.animate(
      [
        { outline: '2px solid var(--primary)' },
        { outline: '2px solid transparent' }
      ],
      { duration: 1800 }
    );
    return true;
  }
}
async function refresh() {
  error.value = '';
  await loadList();
  if (current.value) await loadHistory(true, presented.value);
  if (visible.value)
    loadPreviews(
      records.value.flatMap((row) => extractSkeys(row.message)),
      true
    );
}
async function mutate(action, values, onSuccess = () => {}) {
  if (busy.value || sending.value) return;
  const generation = epoch,
    chat = current.value,
    id = ++mutationRequest;
  busy.value = true;
  error.value = '';
  try {
    const result = await request(action, values);
    if (generation !== epoch) return;
    await onSuccess(result);
    if (generation !== epoch) return;
    if (current.value === chat && current.value) await loadHistory(true, true);
    await loadList();
  } catch (failure) {
    if (generation === epoch) fail(failure);
  } finally {
    if (generation === epoch && id === mutationRequest) busy.value = false;
  }
}
async function send() {
  if (
    stopped ||
    !props.ticket ||
    (!draft.value.trim() && !attachments.value.length) ||
    sending.value ||
    busy.value ||
    !permissions.value.send ||
    !current.value
  )
    return;
  const generation = epoch,
    chat = current.value,
    text = draft.value,
    replyId = reply.value ? messageId(reply.value) : null;
  const files = [...attachments.value],
    keys = [];
  sending.value = true;
  error.value = '';
  try {
    for (const row of files) {
      if (stopped) return;
      if (!row.snapshot) {
        if (!row.file)
          throw new Error(
            'Select this local file again before sending, or remove it.'
          );
        row.status = 'uploading';
        try {
          const snapshot = await messageFileRequest(
            props.ticket,
            props.project,
            { message_code: chat, token: row.token, purpose: 'attachment' },
            row.file
          );
          if (generation !== epoch) return;
          row.snapshot = snapshot;
          row.status = 'uploaded';
          saveDraft();
        } catch (failure) {
          row.status = 'failed';
          throw failure;
        }
      }
      if (generation !== epoch) return;
      keys.push(row.snapshot.__search_key__);
    }
    const result = await request('send', {
      message_code: chat,
      message: text,
      reply_to: replyId,
      attachment_keys: keys
    });
    if (generation !== epoch) return;
    for (const row of files) {
      if (row.previewUrl) URL.revokeObjectURL(row.previewUrl);
      row.previewUrl = '';
    }
    // A send finishing after a conversation switch clears only its original draft.
    if (current.value === chat) {
      if (draft.value === text) {
        draft.value = '';
        reply.value = null;
      }
      attachments.value = attachments.value.filter(
        (row) => !files.some((file) => file.token === row.token)
      );
      saveDraft();
      records.value = mergeMessages([...records.value, result.message]);
      followBottom.value = true;
      await nextTick();
      if (viewport.value)
        viewport.value.scrollTop = viewport.value.scrollHeight;
      await loadHistory(true, true);
      composer.value?.focus();
    } else {
      if (drafts[chat]) {
        if (drafts[chat].text === text) {
          drafts[chat].text = '';
          drafts[chat].reply = null;
        }
        drafts[chat].attachments = (drafts[chat].attachments || []).filter(
          (row) => !files.some((file) => file.token === row.token)
        );
      }
      if (cache.has(chat)) cache.get(chat).dirty = true;
      saveDraft();
    }
    await loadList();
  } catch (failure) {
    if (generation === epoch) fail(failure);
  } finally {
    if (generation === epoch) sending.value = false;
  }
}
async function open(id = '') {
  const generation = epoch,
    requestId = ++openRequest;
  opening.value = true;
  try {
    if (mobile.value && !id) listVisible.value = true;
    visible.value = true;
    dialog.value.show();
    await loadList();
    if (generation !== epoch || requestId !== openRequest || !visible.value)
      return;
    await people();
    if (generation !== epoch || requestId !== openRequest || !visible.value)
      return;
    if (id && conversations.value.some((row) => row.conversationId === id))
      await select(id);
    else if (current.value && !mobile.value) {
      if (cache.has(current.value))
        await loadHistory(true, !!records.value.length);
      else await select(current.value);
    }
    markRead();
  } finally {
    if (requestId === openRequest) opening.value = false;
  }
}
async function sendQuickReply({ notificationId, conversationId, body }) {
  const text = String(body || '').trim(),
    generation = epoch;
  if (
    !notificationId ||
    !conversationId ||
    !text ||
    quickReplies.has(notificationId)
  )
    return;
  if (!permissions.value.send) {
    emit('quick-reply-failed', {
      notificationId,
      error: 'Unable to send message'
    });
    return;
  }
  quickReplies.add(notificationId);
  try {
    await request('send', { message_code: conversationId, message: text });
    if (generation !== epoch) return;
    emit('quick-reply-sent', notificationId);
    if (cache.has(conversationId)) cache.get(conversationId).dirty = true;
    if (visible.value && current.value === conversationId && !loading.value)
      await loadHistory(true, true);
    await loadList();
  } catch (failure) {
    if (generation !== epoch) return;
    emit('quick-reply-failed', {
      notificationId,
      error:
        failure instanceof TypeError
          ? 'Unable to reach the server.'
          : failure.message
    });
    if (failure.code === 'authentication_failed') expireSession();
  } finally {
    if (generation === epoch) quickReplies.delete(notificationId);
  }
}
function close() {
  remember();
  editor.value?.close();
  dialog.value?.close();
  visible.value = false;
}
async function loadPreviews(keys, retry = false) {
  if (stopped || !props.ticket) return;
  const ticket = props.ticket,
    project = props.project,
    generation = epoch,
    id = previewRequest;
  const missing = [...new Set(keys)].filter(
    (key) => retry || !previews.value[key]
  );
  for (const key of missing)
    if (previews.value[key]?.status !== 'ready')
      previews.value[key] = skeyPlaceholder(key);
  for (let start = 0; start < missing.length; start += 50) {
    const batch = missing.slice(start, start + 50);
    try {
      const result = await linkPreviews(ticket, project, batch);
      if (
        id !== previewRequest ||
        generation !== epoch ||
        ticket !== props.ticket ||
        project !== props.project
      )
        return;
      for (const preview of result.previews) {
        previews.value[preview.searchKey] = preview;
        for (const nested of preview.nestedPreviews || [])
          previews.value[nested.searchKey] = nested;
        const attachment = preview.privateAttachment;
        const file = attachment?.snapshot.__files__?.find((row) =>
          ['web', 'icon'].includes(row.type)
        );
        if (file) {
          let blob;
          try {
            blob = await fileBlob(attachment.snapshot, file, attachment.chat);
          } catch (failure) {
            if (
              generation === epoch &&
              failure.code === 'authentication_failed'
            )
              emit('session-expired');
            continue;
          }
          if (
            id !== previewRequest ||
            generation !== epoch ||
            ticket !== props.ticket ||
            project !== props.project
          )
            return;
          const key = 'skey:' + attachment.snapshot.code,
            cached = previewUrls.get(key);
          if (cached) URL.revokeObjectURL(cached.url);
          const url = URL.createObjectURL(blob);
          previewUrls.set(key, { code: attachment.snapshot.code, url });
          previews.value[preview.searchKey].previewUrl = url;
        }
      }
    } catch (failure) {
      if (
        id !== previewRequest ||
        generation !== epoch ||
        ticket !== props.ticket ||
        project !== props.project
      )
        return;
      for (const key of batch)
        previews.value[key] = skeyPlaceholder(key, 'error');
      if (failure.code === 'authentication_failed') expireSession();
    }
  }
}
async function copyLink(key) {
  try {
    await copyText(key);
  } catch (failure) {
    fail(failure);
  }
}
function openLink(key) {
  close();
  emit('open-link', key);
}
async function openMessage(chat, key) {
  await open(chat);
  if (current.value === chat) await jump(key);
}
function addFiles(files) {
  if (sending.value || busy.value || !permissions.value.upload) return;
  for (const file of files) {
    if (attachments.value.length >= 50 || file.size > 63 * 1024 * 1024) {
      error.value = 'Choose at most 50 files, each smaller than 63 MiB.';
      break;
    }
    const missing = attachments.value.find(
      (row) =>
        !row.file &&
        !row.snapshot &&
        row.name === file.name &&
        row.size === file.size
    );
    if (missing) {
      missing.file = file;
      missing.status = 'ready';
      missing.previewUrl = file.type.startsWith('image/')
        ? URL.createObjectURL(file)
        : '';
      continue;
    }
    attachments.value.push({
      token: newFileToken(),
      name: file.name,
      size: file.size,
      file,
      snapshot: null,
      status: 'ready',
      previewUrl: file.type.startsWith('image/')
        ? URL.createObjectURL(file)
        : ''
    });
  }
}
function removeFile(row) {
  if (row.previewUrl) URL.revokeObjectURL(row.previewUrl);
  attachments.value = attachments.value.filter(
    (file) => file.token !== row.token
  );
}
async function pasteFiles() {
  const generation = epoch,
    chat = current.value;
  try {
    const files = await readClipboardImages();
    if (generation === epoch && chat === current.value && visible.value)
      addFiles(files);
  } catch {
    error.value =
      'Clipboard access is unavailable. Paste an image into the reply field or choose a file.';
  }
}
const fileBlob = (snapshot, file, chat = current.value) =>
  messageFileRequest(props.ticket, props.project, {
    message_code: chat,
    snapshot_code: snapshot.code,
    file_code: file.code
  });
async function loadConversationPreviews() {
  const generation = epoch;
  for (const row of conversations.value) {
    const snapshot = row.preview,
      file =
        snapshot?.__files__?.find((file) => file.type === 'web') ||
        snapshot?.__files__?.[0];
    if (!file) continue;
    const cached = previewUrls.get(row.conversationId);
    if (cached?.code === snapshot.code) {
      row.previewUrl = cached.url;
      continue;
    }
    if (cached) URL.revokeObjectURL(cached.url);
    previewUrls.set(row.conversationId, { code: snapshot.code, url: '' });
    try {
      const blob = await fileBlob(snapshot, file, row.conversationId);
      if (generation !== epoch) return;
      const url = URL.createObjectURL(blob);
      previewUrls.set(row.conversationId, { code: snapshot.code, url });
      const active = conversations.value.find(
        (chat) =>
          chat.conversationId === row.conversationId &&
          chat.preview?.code === snapshot.code
      );
      if (active) active.previewUrl = url;
    } catch (failure) {
      if (generation === epoch) {
        previewUrls.delete(row.conversationId);
        fail(failure);
      }
    }
  }
}
function releaseFiles() {
  for (const value of Object.values(drafts))
    for (const row of value.attachments || [])
      if (row.previewUrl) URL.revokeObjectURL(row.previewUrl);
  for (const row of previewUrls.values())
    if (row.url) URL.revokeObjectURL(row.url);
  previewUrls.clear();
}
function openAttachment(snapshot, chat = current.value, fileCode = '') {
  const file =
    snapshot.__files__?.find((file) => file.code === fileCode) ||
    snapshot.__files__?.find((file) => !['web', 'icon'].includes(file.type)) ||
    snapshot.__files__?.[0];
  filePreview.value.open(
    { ...snapshot, title: attachmentName(snapshot) },
    {
      context: snapshot.context,
      version: snapshot.version,
      fileCode,
      files: (snapshot.__files__ || []).map((file) => ({
        ...file,
        filename: ['web', 'icon'].includes(file.type)
          ? file.file_name
          : attachmentName(snapshot),
        size: file.st_size
      })),
      loadFile: (file) => fileBlob(snapshot, file, chat)
    }
  );
  emit('attachment-location', {
    chat,
    snapshot: snapshot.code,
    file: file?.code
  });
}
async function attachmentAction(name, snapshot, chat = current.value) {
  const file =
      snapshot.__files__?.find(
        (file) => !['web', 'icon'].includes(file.type)
      ) || snapshot.__files__?.[0],
    generation = epoch,
    project = props.project;
  if (!file || fileActions.value[snapshot.code]?.pending) return;
  fileActions.value[snapshot.code] = { pending: true, error: '' };
  try {
    if (name === 'download' || name === 'copy-image') {
      const blob = await fileBlob(snapshot, file, chat);
      if (generation !== epoch || project !== props.project) return;
      if (name === 'download') downloadBlob(blob, attachmentName(snapshot));
      else await copyImage(blob);
    } else {
      const info = await request('file-info', {
        message_code: chat,
        snapshot_code: snapshot.code,
        file_code: file.code
      });
      if (generation !== epoch || project !== props.project) return;
      if (name === 'copy-path') await copyText(info.path);
      else if (name === 'copy-web') {
        const url = new URL(projectPath(project), location.origin),
          active = new URLSearchParams(location.search);
        for (const key of ['search_type', 'view'])
          if (active.has(key)) url.searchParams.set(key, active.get(key));
        for (const [key, value] of Object.entries({
          chat,
          snapshot: snapshot.code,
          file: file.code
        }))
          url.searchParams.set(key, value);
        url.hash = '';
        await copyText(url.href);
      }
    }
  } catch (failure) {
    if (generation === epoch) {
      fileActions.value[snapshot.code].error = failure.message;
      if (failure.code === 'authentication_failed') expireSession();
    }
  } finally {
    if (generation === epoch) fileActions.value[snapshot.code].pending = false;
  }
}
async function openAttachmentLink(chat, snapshot, file) {
  const generation = epoch;
  try {
    const info = await request('file-info', {
      message_code: chat,
      snapshot_code: snapshot,
      file_code: file
    });
    if (generation !== epoch) return;
    await open(chat);
    if (generation === epoch) openAttachment(info.snapshot, chat, file);
  } catch (failure) {
    if (generation !== epoch) return;
    visible.value = true;
    await nextTick();
    dialog.value?.show();
    fail(failure);
  }
}
function openDraftFile(row) {
  if (row.snapshot) {
    openAttachment(row.snapshot);
    return;
  }
  if (row.file)
    filePreview.value.open(
      { title: row.name },
      {
        files: [{ filename: row.name, size: row.size, type: 'file' }],
        loadFile: async () => row.file
      }
    );
}
async function changePreview(event) {
  const file = event.target.files[0],
    chat = current.value,
    generation = epoch;
  event.target.value = '';
  if (!file || busy.value || !permissions.value.upload) return;
  busy.value = true;
  try {
    await messageFileRequest(
      props.ticket,
      props.project,
      { message_code: chat, token: newFileToken(), purpose: 'preview' },
      file
    );
    if (generation === epoch) await loadList();
  } catch (failure) {
    if (generation === epoch) fail(failure);
  } finally {
    if (generation === epoch) busy.value = false;
  }
}
async function showEditor(action, row = null, event = null) {
  if (action === 'attachment') {
    openAttachment(row);
    return;
  }
  if (action === 'preview') {
    previewInput.value.click();
    return;
  }
  if (mode.value === action && editorPopup.value && editor.value?.open) {
    editor.value.close();
    return;
  }
  editor.value?.close();
  editorAnchor.value =
    event?.currentTarget
      ?.closest('.workspace-menu')
      ?.querySelector(':scope > summary') ||
    event?.currentTarget ||
    dialog.value.querySelector('.messages-chat-header');
  const generation = epoch;
  editorChat.value = current.value;
  pickerKey.value++;
  mode.value = action;
  target.value = row;
  targets.value = [];
  recipients.value =
    action === 'members' ? [...(conversation.value?.recipients || [])] : [];
  title.value = action === 'rename' ? conversation.value.title : '';
  editText.value = row?.message || '';
  if (action === 'search') searchDraft.value = search.value;
  if (action === 'create' || action === 'members' || action === 'view-members')
    await people();
  await nextTick();
  if (generation === epoch && visible.value && mode.value === action) {
    if (editorPopup.value) {
      editor.value.open = true;
      searchOpen.value = action === 'search';
    } else if (mode.value === 'forward') editor.value.show();
    else editor.value.showModal();
    if (['edit', 'rename', 'search'].includes(action))
      (editor.value.$el || editor.value)
        .querySelector('input, textarea')
        ?.focus();
  }
}
function editorClosed() {
  searchOpen.value = false;
  targets.value = [];
  if (mode.value === 'forward' && !busy.value) selected.value = [];
  if (mode.value === 'edit') {
    target.value = null;
    editText.value = '';
  }
}
function popupToggled(event) {
  if (event.target === editor.value?.$el && !editor.value.open) editorClosed();
}
function applySearch(value = searchDraft.value) {
  remember();
  search.value = value;
  followBottom.value = true;
  loadHistory(true);
  editor.value.close(true);
}
async function showPinnedMessage(entry) {
  if (await jump(entry.messageId)) editor.value.close();
}
function toggle(values, id, enabled) {
  return enabled
    ? [...new Set([...values, id])]
    : values.filter((value) => value !== id);
}
async function action(name, row) {
  if (name === 'profile') emit('open-profile', row);
  else if (name === 'reply') {
    reply.value = row;
    composer.value?.focus();
  } else if (name === 'original') {
    if (!row.available || !row.conversationId || !row.messageId) return;
    const generation = epoch;
    await select(row.conversationId, false);
    if (
      generation === epoch &&
      current.value === row.conversationId &&
      visible.value
    )
      await jump(row.messageId);
  } else if (name === 'select')
    selected.value = toggle(
      selected.value,
      messageId(row),
      !selected.value.includes(messageId(row))
    );
  else if (name === 'copy' || name === 'skey') {
    try {
      await copyText(
        name === 'copy' ? row.message : 'skey://' + messageId(row)
      );
    } catch (failure) {
      fail(failure);
    }
  } else if (name === 'pin')
    mutate('pin', {
      message_log_code: messageId(row),
      unpin: pinned.value.messageId === messageId(row)
    });
  else {
    if (name === 'forward') selected.value = [messageId(row)];
    showEditor(name, row);
  }
}
async function submitEditor() {
  if (busy.value || invalidEditor.value) return;
  const chat = editorChat.value,
    activeEditor = editor.value,
    done = () => {
      if (editor.value === activeEditor) activeEditor.close();
    };
  if (mode.value === 'create')
    await mutate(
      'create',
      { recipients: recipients.value, title: title.value },
      (result) => {
        done();
        return select(result.conversationId);
      }
    );
  else if (mode.value === 'rename')
    await mutate('rename', { message_code: chat, title: title.value }, done);
  else if (mode.value === 'members')
    await mutate(
      'members',
      { message_code: chat, recipients: recipients.value, replace: true },
      done
    );
  else if (mode.value === 'edit')
    await mutate(
      'edit',
      { message_log_code: messageId(target.value), message: editText.value },
      done
    );
  else if (mode.value === 'forward')
    await mutate(
      'forward',
      { message_log_keys: selected.value, target_message_codes: targets.value },
      () => {
        selected.value = [];
        done();
      }
    );
  else if (mode.value === 'delete-message')
    await mutate(
      'delete-message',
      { message_log_code: messageId(target.value) },
      done
    );
  else if (mode.value === 'clear' || mode.value === 'delete')
    await mutate(mode.value, { message_code: chat }, done);
}
watch(
  () => [records.value, visible.value],
  () => {
    if (visible.value && props.ticket)
      loadPreviews(records.value.flatMap((row) => extractSkeys(row.message)));
  }
);
watch(
  () => [props.ticket, props.project],
  () => {
    previewRequest++;
    previews.value = {};
    for (const state of cache.values()) state.previews = {};
    for (const [key, value] of previewUrls)
      if (key.startsWith('skey:')) {
        URL.revokeObjectURL(value.url);
        previewUrls.delete(key);
      }
  },
  { flush: 'sync' }
);
watch(
  () => props.updates,
  (batch) => {
    if (!batch) return;
    const changes = [
      ...(batch.cacheChanges || []),
      ...(batch.cacheRetired || [])
    ];
    if (
      batch.reconnected ||
      batch.messages?.length ||
      batch.reactions?.length ||
      changes.some((row) =>
        ['sthpw/message', 'sthpw/message_log', 'sthpw/subscription'].includes(
          row.searchType
        )
      )
    )
      for (const state of cache.values()) state.dirty = true;
    if (
      baseline ||
      batch.initialMessages ||
      batch.reconnected ||
      batch.messages?.length ||
      batch.reactions?.length ||
      changes.some((row) =>
        ['sthpw/message', 'sthpw/message_log', 'sthpw/subscription'].includes(
          row.searchType
        )
      )
    ) {
      loadList();
      if (visible.value && current.value && !loading.value)
        loadHistory(true, true);
    }
    if (visible.value && (changes.length || batch.messages?.length)) {
      previewRequest++;
      loadPreviews(
        records.value.flatMap((row) => extractSkeys(row.message)),
        true
      );
    }
  }
);
watch(
  () => [props.ticket, props.login],
  () => {
    stopped = !props.ticket;
    epoch++;
    quickReplies.clear();
    listRequest++;
    historyRequest++;
    mutationRequest++;
    listLoading = false;
    pendingList = false;
    remember();
    close();
    filePreview.value?.close();
    conversations.value = [];
    records.value = [];
    users.value = [];
    cache.clear();
    seen.clear();
    baseline = true;
    selected.value = [];
    current.value = '';
    pinned.value = {};
    initialized.value = false;
    error.value = '';
    busy.value = loading.value = sending.value = false;
    mode.value = '';
    target.value = null;
    editorChat.value = '';
    recipients.value = [];
    targets.value = [];
    title.value = editText.value = '';
    canCreateGroup.value = false;
    permissions.value = {};
    releaseFiles();
    for (const key of Object.keys(drafts)) delete drafts[key];
    attachments.value = [];
    fileActions.value = {};
    draftKey = storageKey.value;
    try {
      const state = JSON.parse(localStorage.getItem(storageKey.value) || '{}');
      Object.assign(drafts, state.drafts || {});
      current.value = state.selected || '';
      notifications.value = state.notifications !== false;
    } catch {
      /* Current session remains usable in memory. */
    }
    draft.value = drafts[current.value]?.text || '';
    reply.value = drafts[current.value]?.reply || null;
    emit('unread', 0);
    attachments.value = drafts[current.value]?.attachments || [];
  },
  { immediate: true }
);
watch(
  () => props.project,
  () => {
    loadList();
    if (visible.value && current.value) loadHistory(true, true);
  }
);
function focus() {
  markRead();
}
onMounted(() => {
  window.addEventListener('focus', focus);
  document.addEventListener('visibilitychange', focus);
});
onBeforeUnmount(() => {
  remember();
  releaseFiles();
  stopped = true;
  epoch++;
  window.removeEventListener('focus', focus);
  document.removeEventListener('visibilitychange', focus);
});
async function openDirect(login) {
  const generation = epoch;
  await open();
  if (generation !== epoch) return;
  try {
    const result = await request('create', { recipients: [login], title: '' });
    if (generation !== epoch) return;
    await loadList();
    if (generation === epoch) await select(result.conversationId);
  } catch (failure) {
    if (generation === epoch) fail(failure);
  }
}
defineExpose({
  windowContext: () => {
    saveDraft();
    return { route: { args: [current.value] }, args: [current.value] };
  },
  open,
  close,
  openMessage,
  sendQuickReply,
  openAttachmentLink,
  openDirect,
  refreshPeople: people
});
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'messages', type: 'window' }"
      ref="dialog"
      class="messages-dialog"
      :class="{ 'conversation-open': !listVisible }"
      :aria-label="t('Messages')"
      :aria-busy="busy || loading || sending || opening"
      @cancel.prevent="close"
      @close="visible = false"
    >
      <header class="messages-heading">
        <AppIcon name="MDI_MESSAGE_TEXT" /><strong>{{ t('Messages') }}</strong
        ><AppCheckbox
          v-if="!mobile"
          v-model="notifications"
          compact
          label="Message notifications"
        /><AppMenu v-else label="Messages options" overlay
          ><AppCheckbox
            v-model="notifications"
            compact
            label="Message notifications" /><AppButton
            label="Messages help"
            icon="help"
            @click="openHelp('communication')" /></AppMenu
        ><AppButton
          v-if="!mobile"
          icon-only
          icon="help"
          label="Messages help"
          @click="openHelp('communication')"
        /><AppButton
          icon-only
          icon="close"
          label="Close Messages"
          @click="close"
        />
      </header>
      <p v-if="error || updatesError" class="error messages-error" role="alert">
        {{ t(error || updatesError) }}
        <AppButton
          icon-only
          label="Dismiss error"
          icon="close"
          @click="error = ''"
        />
      </p>
      <InitializationState
        v-if="!initialized"
        title="Messages are not initialized"
        message="Initialize the collaboration schema before starting conversations."
        icon="message"
        :project="project"
        :can-initialize="canInitialize"
        :busy="busy"
        can-refresh
        @initialize="mutate('initialize', {})"
        @refresh="refresh"
      />
      <div
        v-else
        class="messages-layout"
        @dragover.prevent
        @drop.prevent="addFiles($event.dataTransfer.files)"
        :class="{ 'show-conversations': listVisible }"
        :style="{ '--conversations-width': paneWidth + 'px' }"
      >
        <ConversationList
          :records="conversations"
          :selected="current"
          :users="users"
          :busy="busy || !permissions.create"
          @selected="select"
          @create="showEditor('create')"
          @context="conversationContext"
        />
        <AppSplitter
          v-model="paneWidth"
          :min="210"
          :max="420"
          label="Resize conversations"
        />
        <section class="messages-timeline-pane" :aria-label="t('Conversation')">
          <ChatHeader
            :model="{
              ...conversation,
              conversationId: current,
              compact: mobile,
              busy: busy || loading,
              avatarUrl: conversation?.previewUrl || peer?.avatarUrl,
              acronym: initials(conversation?.title || ''),
              colorIndex: Math.min(4, conversation?.recipients?.length || 0),
              search: !!search,
              online: presence?.online,
              presence: peer ? presenceText : '',
              subtitle: conversation
                ? conversation.isPersonalNotes
                  ? t('Your personal notes') +
                    ' · ' +
                    t('{count} notes', { count: conversation.messageCount })
                  : (peer
                      ? ''
                      : t('{count} members', {
                          count: conversation.participantCount
                        }) + ' · ') +
                    t('{count} messages', { count: conversation.messageCount })
                : ''
            }"
            @event="headerEvent"
          >
            <AppMenu
              v-if="conversation"
              ref="chatMenu"
              class="chat-actions"
              label="Chat actions"
              external-trigger
              :anchor="chatAnchor"
              overlay
            >
              <template v-if="mobile">
                <AppButton
                  label="Search messages"
                  icon="search"
                  :aria-expanded="searchOpen"
                  :aria-pressed="!!search"
                  @click="showEditor('search', null, $event)"
                />
                <AppButton
                  label="Chat files"
                  icon="MDI_PAPERCLIP"
                  @click="showEditor('files', null, $event)"
                />
                <AppButton
                  v-if="!conversation.isPersonalNotes"
                  label="Chat members"
                  icon="MDI_ACCOUNT_MULTIPLE"
                  @click="showEditor('view-members', null, $event)"
                />
                <AppButton
                  label="Refresh conversations and messages"
                  icon="refresh"
                  :disabled="busy || loading"
                  @click="refresh"
                />
                <AppCheckbox
                  v-model="notifications"
                  compact
                  label="Message notifications"
                />
                <AppButton
                  label="Messages help"
                  icon="help"
                  @click="openHelp('communication')"
                />
                <hr />
              </template>
              <AppButton
                label="Rename chat"
                icon="MDI_PENCIL"
                :disabled="!conversation.canRename || !permissions.rename"
                @click="showEditor('rename')"
              />
              <AppButton
                label="Change preview"
                icon="image"
                :disabled="!conversation.canManage || !permissions.upload"
                @click="showEditor('preview')"
              />
              <AppButton
                label="Add or remove members"
                icon="MDI_ACCOUNT_COG"
                :disabled="!conversation.canAddMembers || !permissions.members"
                @click="showEditor('members')"
              />
              <AppButton
                label="Pin history"
                icon="pin"
                @click="showEditor('pin-history', null, $event)"
              />
              <hr />
              <AppButton
                :label="
                  conversation.canClearPersonal
                    ? 'Clear favorites'
                    : 'Delete chat'
                "
                icon="MDI_DELETE"
                destructive
                :disabled="
                  conversation.canClearPersonal
                    ? !permissions.clear
                    : !conversation.canDelete || !permissions.delete
                "
                @click="
                  showEditor(conversation.canClearPersonal ? 'clear' : 'delete')
                "
              /> </AppMenu
            ><BusyIndicator v-if="(loading && !presented) || busy" running />
          </ChatHeader>
          <PinnedMessage
            v-if="pinned.messageId"
            :model="pinned"
            @open="jump(pinned.messageId)"
            @history="
              (source) =>
                showEditor('pin-history', null, { currentTarget: source })
            "
          />
          <div class="messages-timeline-frame">
            <div
              v-for="state in timelines"
              :key="state.id"
              :ref="
                (node) => {
                  if (node) viewports.set(state.id, node);
                  else viewports.delete(state.id);
                }
              "
              v-show="state.id === timelineId"
              class="messages-viewport"
              :data-current="state.id === timelineId"
              :data-conversation-id="state.chat"
              :style="{ visibility: state.loaded ? undefined : 'hidden' }"
              :aria-label="t('Messages timeline')"
              tabindex="0"
              @scroll.passive="state.id === timelineId && scroll()"
            >
              <div class="messages-history">
                <AppButton
                  v-if="state.more"
                  label="Load older messages"
                  :disabled="loading"
                  @click="loadHistory(false)"
                /><MessageBubble
                  v-for="row in groupedMessages(state.records)"
                  :key="messageId(row)"
                  :row="row"
                  :user="ownIdentity(row.login)"
                  :users="users"
                  :login="login"
                  :selected="selected.includes(messageId(row))"
                  :selection-mode="!!selected.length"
                  :can-edit="
                    permissions.edit && canChangeMessage(row, login, privileged)
                  "
                  :permissions="permissions"
                  :busy="busy || sending"
                  :pinned="state.pinned?.messageId === messageId(row)"
                  :load-file="state.loadFile"
                  :file-actions="fileActions"
                  :previews="state.previews"
                  :now="now"
                  @preview-retry="loadPreviews([$event], true)"
                  @copy-link="copyLink"
                  @attachment-action="attachmentAction"
                  @session-expired="expireSession"
                  @action="action"
                  @reaction="
                    (row, emoji) =>
                      mutate('reaction', {
                        message_log_code: messageId(row),
                        emoji
                      })
                  "
                  @link="openLink"
                  @jump="jump"
                />
                <p
                  v-if="!state.records.length && (!loading || state.loaded)"
                  class="messages-empty"
                >
                  {{
                    t(
                      search
                        ? 'No matching messages'
                        : current
                          ? 'No messages yet'
                          : 'Select a conversation'
                    )
                  }}
                </p>
              </div>
            </div>
            <div
              v-if="current && !presented && loading"
              class="messages-loading"
              role="status"
            >
              <BusyIndicator running /><span>{{
                t('Loading conversation')
              }}</span>
            </div>
            <AppButton
              class="messages-latest"
              :class="{ hidden: followBottom }"
              :disabled="followBottom"
              :tabindex="followBottom ? -1 : 0"
              :aria-hidden="followBottom"
              icon-only
              icon="MDI_CHEVRON_DOWN"
              label="Jump to latest message"
              @click="latest"
            />
          </div>
          <div v-if="selected.length" class="messages-selection">
            <strong>{{
              t('{count} messages selected', { count: selected.length })
            }}</strong
            ><AppButton
              label="Forward"
              icon="MDI_SHARE"
              :disabled="busy || !permissions.forward"
              @click="showEditor('forward')"
            /><AppButton
              icon-only
              label="Cancel selection"
              icon="close"
              @click="selected = []"
            />
          </div>
          <MessageReference
            v-if="reply"
            class="messages-reply"
            :users="users"
            :reference="{
              sender: reply.login,
              body: reply.message,
              available: true
            }"
            dismissible
            @dismiss="reply = null"
          />
          <div v-if="current" class="messages-compose-row">
            <input
              ref="fileInput"
              type="file"
              multiple
              hidden
              :aria-label="t('Choose files')"
              @change="
                addFiles($event.target.files);
                $event.target.value = '';
              "
            /><input
              ref="previewInput"
              type="file"
              accept="image/*"
              hidden
              :aria-label="t('Choose conversation preview')"
              @change="changePreview"
            /><AttachmentComposerControls
              :records="attachments"
              :busy="sending"
              :upload="permissions.upload"
              @choose="fileInput.click()"
              @paste="pasteFiles"
              @clear="attachments.slice().forEach(removeFile)"
              @remove="removeFile"
              @open="openDraftFile"
            /><MessageComposer
              ref="composer"
              v-model="draft"
              :members="members"
              :sending="sending"
              :disabled="!permissions.send"
              :has-attachments="!!attachments.length"
              @files="addFiles"
              @submit="send"
            />
          </div>
        </section>
      </div>
    </dialog>
    <component
      :is="editorPopup ? AppMenu : 'dialog'"
      :key="mode"
      v-window="
        editorPopup ? false : { type: mode === 'forward' ? 'popup' : 'dialog' }
      "
      ref="editor"
      class="messages-editor"
      :class="{
        'messages-popup': editorPopup,
        'messages-search-popup': mode === 'search',
        'chat-files-window': mode === 'files',
        'messages-people-window': ['create', 'members'].includes(mode),
        'messages-members-window': mode === 'view-members',
        'messages-rename-window': mode === 'rename',
        'messages-edit-window': mode === 'edit',
        'messages-forward-window': mode === 'forward',
        'messages-history-window': ['history', 'pin-history'].includes(mode)
      }"
      :label="actionTitles[mode] || 'Messages'"
      :overlay="editorPopup"
      :close-on-select="false"
      :centered="editorCentered"
      :width="editorWidth"
      :style="{
        '--message-popup-spacing': Messaging.popup(mode).spacing + 'px',
        '--message-popup-height': Messaging.popup(mode).height
          ? Messaging.popup(mode).height + 'px'
          : undefined
      }"
      :anchor="editorAnchor"
      :boundary="dialog"
      :aria-label="t(actionTitles[mode] || 'Messages')"
      :aria-busy="busy || (mode === 'files' && loading)"
      @toggle="popupToggled"
      @cancel.prevent="!busy && editor.close()"
      @close="editorClosed"
    >
      <MessagePanelHeader
        v-if="
          ['view-members', 'files', 'history', 'pin-history'].includes(mode)
        "
        :mode="mode"
        :count="gallery.length"
      />
      <header v-else-if="!editorPopup">
        <strong>{{ t(actionTitles[mode] || 'Messages') }}</strong
        ><AppButton
          icon-only
          icon="close"
          label="Close"
          :disabled="busy"
          @click="editor.close()"
        />
      </header>
      <form
        @submit.prevent="mode === 'search' ? applySearch() : submitEditor()"
      >
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <MessageForm
          v-if="formModes.includes(mode)"
          :mode="mode"
          v-model:text="formText"
          v-model:recipients="recipients"
          :users="users"
          :login="login"
          :busy="busy"
          :valid="!invalidEditor"
          :can-create-group="canCreateGroup"
          :active-search="!!search"
          @submit="mode === 'search' ? applySearch() : submitEditor()"
          @cancel="editor.close()"
          @clear-search="applySearch('')"
        />
        <MessageMembers
          v-if="mode === 'view-members'"
          :members="members"
          :login="login"
          @profile="
            (value) => {
              editor.close();
              emit('open-profile', value);
            }
          "
        />
        <div
          v-if="['history', 'pin-history'].includes(mode)"
          class="messages-edit-history"
        >
          <MessageRevision
            v-for="(entry, index) in historyEntries"
            :key="index"
            :record="entry"
            :mode="mode"
            :busy="loading"
            @open="showPinnedMessage"
          />
        </div>
        <MessageForward
          v-if="mode === 'forward'"
          :records="conversations"
          :targets="targets"
          :count="selected.length"
          :busy="busy"
          :valid="!invalidEditor"
          @toggle="
            (key) => (targets = toggle(targets, key, !targets.includes(key)))
          "
          @cancel="editor.close()"
          @submit="submitEditor"
        />
        <div
          v-if="mode === 'files'"
          class="messages-file-gallery"
          @scroll="
            (event) => {
              const node = event.target;
              if (
                node.scrollHeight > node.clientHeight &&
                node.scrollTop + node.clientHeight >= node.scrollHeight - 16 &&
                more &&
                !loading
              )
                loadHistory(false);
            }
          "
        >
          <p v-if="!gallery.length" class="muted">
            {{ t('No files in loaded messages') }}
          </p>
          <AttachmentItem
            v-for="entry in gallery"
            :key="entry.messageId + entry.snapshot.code"
            :snapshot="entry.snapshot"
            :entry="entry"
            :action-state="fileActions[entry.snapshot.code]"
            @action="
              (name, snapshot) => attachmentAction(name, snapshot, editorChat)
            "
            @jump="
              editor.close();
              jump($event);
            "
            @open="openAttachment($event, editorChat)"
            @session-expired="expireSession"
          />
        </div>
        <AppButton
          v-if="mode === 'files' && more"
          class="chat-files-earlier"
          label="Load earlier messages"
          :disabled="loading"
          @click="loadHistory(false)"
        />
      </form>
    </component>
  </Teleport>
  <FilePreview
    ref="filePreview"
    :ticket="ticket"
    :project="project"
    @closed="emit('attachment-location', null)"
    @session-expired="expireSession"
  />
</template>
