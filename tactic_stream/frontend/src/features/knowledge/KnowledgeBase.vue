<script setup>
import { randomId } from '../../controls/identity.js';
// Handler KnowledgeBaseView, KnowledgeNavigation and KnowledgeController (EPL-1.0).
import {
  computed,
  inject,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue';
import {
  knowledgeRequest,
  messageFileRequest,
  linkPreviews
} from '../../api.js';
import { t } from '../../i18n.js';
import { copyText } from '../../controls/clipboard.js';
import InitializationState from '../collaboration/InitializationState.vue';
import FrameView from '../../frame/FrameView.vue';
import * as Workspace from '../../../../src/tactic_stream/shared_ui/features/knowledge/workspace.ui.mjs';
import * as Navigation from '../../../../src/tactic_stream/shared_ui/features/knowledge/navigation.ui.mjs';
import * as Commands from '../../../../src/tactic_stream/shared_ui/features/knowledge/commands.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppMenuItem from '../../controls/AppMenuItem.vue';
import AppTextField from '../../controls/AppTextField.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import SKeyPreviewCard from '../objects/SKeyPreviewCard.vue';
import { messageDate } from '../messages/messages.js';
import { appearance } from '../../appearance.js';
import { extractSkeys } from '../../controls/richText.js';
import KnowledgeOutline from './KnowledgeOutline.vue';
import KnowledgeEditor from './KnowledgeEditor.vue';
import { articleHtml, plainText } from './markdown.js';

const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  active: Boolean,
  selection: Array,
  target: String
});
const emit = defineEmits([
  'session-expired',
  'changed',
  'open-link',
  'location'
]);
const openObjectTab = inject('openObjectTab', null);
const host = ref(null),
  width = ref(0),
  height = ref(0),
  initialized = ref(false),
  canEdit = ref(false),
  canInitialize = ref(false);
const catalog = ref([]),
  query = ref(''),
  identity = ref(''),
  searchKey = ref(''),
  revision = ref(''),
  catalogRevision = ref(''),
  selected = ref('');
const document = ref(null),
  metadata = ref({}),
  files = ref([]),
  editing = ref(false),
  step = ref(0),
  expandedMetadata = ref(false);
const navigationExpanded = ref(true),
  navigationPage = ref(true),
  tocVisible = ref(true),
  resourcesVisible = ref(false),
  attachmentsVisible = ref(false);
const loading = ref(false),
  saving = ref(false),
  error = ref(''),
  storageError = ref(false),
  loaded = ref(false);
const drafts = reactive({}),
  collapsed = reactive(new Set()),
  organization = ref(null),
  dragging = ref(''),
  dropTarget = ref('');
const editor = ref(null),
  viewer = ref(null),
  fileInput = ref(null),
  historyDialog = ref(null),
  deletion = ref(null),
  moveDialog = ref(null);
const pendingFiles = ref([]),
  copying = ref(''),
  deletingFile = ref(null),
  deleteGroups = ref([]),
  deleteTypes = ref([]),
  moveParent = ref(''),
  moveIdentity = ref('');
const histories = ref([]),
  historyPreview = ref(null),
  references = ref({}),
  linkedIndex = ref(0);
const stagedFiles = new Map();
let request = 0,
  historyRequest = 0,
  previewRequest = 0,
  observer,
  searchTimer,
  original = '',
  context = '';
const scope = computed(
  () => `tactic_stream.knowledge.${props.login}.${props.project}`
);
const presentation = computed(() => ({
  initialized: initialized.value,
  canEdit: canEdit.value,
  busy: loading.value || saving.value,
  saving: saving.value,
  error: error.value,
  organizationDirty: !!organization.value,
  navigationExpanded: navigationExpanded.value,
  navigationPage: navigationPage.value
}));
const scene = computed(() =>
  Workspace.describe(
    presentation.value,
    width.value,
    height.value,
    appearance.language
  )
);
const bounds = computed(() => scene.value.bounds);
const narrow = computed(() => width.value < 720),
  single = computed(() => bounds.value.single);
const style = (b) => ({
  position: 'absolute',
  left: b.x + 'px',
  top: b.y + 'px',
  width: b.width + 'px',
  height: b.height + 'px'
});
function workspaceAction(action) {
  if (action.type === 'navigation') {
    const next = Workspace.toggleNavigation(
      presentation.value,
      !!document.value
    );
    navigationExpanded.value = next.navigationExpanded;
    navigationPage.value = next.navigationPage;
  } else if (action.type === 'dismissError') error.value = '';
  else if (action.type === 'reload') reload();
  else if (action.type === 'createArticle') create('article');
  else if (action.type === 'createSection') create('section');
  else if (action.type === 'saveOrder') saveOrder();
  else if (action.type === 'discardOrder') undoOrder();
}
const editorPresentation = computed(() => ({
  kind: document.value?.kind,
  back: single.value,
  creating: creating.value,
  step: step.value,
  metadataExpanded: expandedMetadata.value,
  selectionCount: props.selection?.length || 0,
  busy: saving.value,
  dirty: dirty.value,
  localDraft: !!drafts[identity.value],
  draft: document.value?.draft
}));
function editorAction(action) {
  if (action.type === 'back') {
    checkpoint();
    navigationPage.value = true;
  } else if (action.type === 'metadata') {
    if (creating.value) {
      step.value = 0;
      expandedMetadata.value = true;
    } else expandedMetadata.value = !expandedMetadata.value;
  } else if (action.type === 'link') linkSelection();
  else if (action.type === 'discard') discard();
  else if (action.type === 'delete') openDeletion();
  else if (action.type === 'saveDraft') save(true);
  else if (action.type === 'save') save();
}
const viewerPresentation = computed(() => ({
  kind: shown.value?.kind,
  title: shown.value?.title,
  description: shown.value?.description,
  minutes: minutes.value,
  back: single.value,
  localDraft: !!drafts[identity.value],
  history: !!historyPreview.value,
  canEdit: canEdit.value,
  busy: saving.value,
  tocCount: toc.value.length,
  tocVisible: tocVisible.value,
  resourceCount: files.value.length + resourceKeys.value.length,
  resourcesVisible: resourcesVisible.value
}));
function viewerAction(action, source) {
  if (action.type === 'back') navigationPage.value = true;
  else if (action.type === 'copy') copy(searchKey.value);
  else if (action.type === 'history') {
    const box = source.getBoundingClientRect();
    historyDialog.value.openAt({
      clientX: box.left,
      clientY: box.bottom,
      target: source
    });
    history();
  } else if (action.type === 'toc') tocVisible.value = !tocVisible.value;
  else if (action.type === 'resources')
    resourcesVisible.value = !resourcesVisible.value;
  else if (action.type === 'delete') openDeletion();
  else if (action.type === 'edit') beginEdit();
}
const pageWidth = computed(() => bounds.value.page.width);
const articleNarrow = computed(() => pageWidth.value < 720);
const creating = computed(() => identity.value.startsWith('local:'));
const dirty = computed(
  () => editing.value && JSON.stringify(document.value) !== original
);
const shown = computed(() => historyPreview.value?.document || document.value);
const html = computed(() =>
  articleHtml(shown.value?.contentMarkdown || '', props.project)
);
const toc = computed(() => {
  const root = documentElement(html.value);
  return [...root.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((node) => ({
    title: node.textContent,
    level: Number(node.tagName[1]),
    id: node.id
  }));
});
const minutes = computed(() =>
  Math.max(
    1,
    Math.ceil(
      (shown.value?.contentText || plainText(shown.value?.contentMarkdown))
        .trim()
        .split(/\s+/)
        .filter(Boolean).length / 200
    )
  )
);
const entries = computed(() => {
  const rows = new Map(catalog.value.map((row) => [row.identity, row]));
  for (const [id, draft] of Object.entries(drafts))
    if (
      !query.value ||
      `${draft.document.title}\n${draft.document.description}\n${draft.document.contentMarkdown}`
        .toLowerCase()
        .includes(query.value.toLowerCase())
    )
      rows.set(id, {
        identity: id,
        title: draft.document.title || t('Untitled article'),
        description: draft.document.description,
        parentCode: draft.document.parentCode,
        kind: draft.document.kind,
        sortOrder: draft.document.sortOrder || 0,
        draft: draft.document.draft,
        localDraft: true
      });
  const values = [...rows.values()],
    result = [],
    seen = new Set();
  function append(parent, depth) {
    for (const row of values
      .filter((row) => row.parentCode === parent)
      .sort(compare)) {
      if (seen.has(row.identity)) continue;
      seen.add(row.identity);
      const children = values.some(
        (child) => child.parentCode === row.identity
      );
      result.push({
        ...row,
        depth,
        hasChildren: children,
        expanded: !collapsed.has(row.identity)
      });
      if (children && !collapsed.has(row.identity))
        append(row.identity, depth + 1);
    }
  }
  append('', 0);
  for (const row of values)
    if (
      !seen.has(row.identity) &&
      !values.some((parent) => parent.identity === row.parentCode)
    ) {
      result.push({ ...row, depth: 0, hasChildren: false });
      seen.add(row.identity);
    }
  return result;
});
const sectionEntries = computed(() => {
  const result = [],
    seen = new Set();
  function append(parent, level) {
    for (const row of catalog.value
      .filter((row) => row.parentCode === parent)
      .sort(compare)) {
      if (seen.has(row.identity)) continue;
      seen.add(row.identity);
      result.push({ ...row, level });
      append(row.identity, level + 1);
    }
  }
  append(identity.value, 1);
  return result;
});
const parentTitle = computed(
  () =>
    catalog.value.find((row) => row.identity === document.value?.parentCode)
      ?.title || t('Knowledge Base root')
);
const sectionOptions = computed(() => [
  { value: '', label: t('Knowledge Base root') },
  ...catalog.value
    .filter((row) => row.kind === 'section')
    .map((row) => ({ value: row.identity, label: row.title }))
]);
const linked = computed(() => document.value?.linkedSearchKeys || []);
const linkedObject = computed(
  () => references.value[linked.value[linkedIndex.value]]
);
const resourceKeys = computed(() => [
  ...new Set([
    ...linked.value,
    ...extractSkeys(shown.value?.contentMarkdown || '')
  ])
]);
const clipboardAvailable = !!navigator.clipboard?.read;
function documentElement(text) {
  const root = window.document.createElement('div');
  root.innerHTML = text;
  return root;
}
function compare(a, b) {
  return (
    a.sortOrder - b.sortOrder ||
    Number(a.kind !== 'section') - Number(b.kind !== 'section') ||
    a.title.localeCompare(b.title)
  );
}
function storeDrafts() {
  try {
    localStorage.setItem(scope.value, JSON.stringify(drafts));
    storageError.value = false;
    return true;
  } catch {
    storageError.value = true;
    error.value = t(
      'Local drafts could not be saved. Keep this page open and save to the server.'
    );
    return false;
  }
}
function checkpoint() {
  if (identity.value && scope.value === context)
    try {
      localStorage.setItem(
        scope.value + '.state',
        JSON.stringify({
          identity: identity.value,
          navigationExpanded: navigationExpanded.value,
          tocVisible: tocVisible.value,
          collapsed: [...collapsed]
        })
      );
    } catch {
      storageError.value = true;
    }
  if (!editing.value || !document.value || !identity.value) return;
  if (dirty.value || creating.value)
    drafts[identity.value] = {
      document: JSON.parse(JSON.stringify(document.value)),
      revision: revision.value,
      searchKey: searchKey.value,
      step: step.value,
      attachments: files.value,
      metadata: metadata.value
    };
  storeDrafts();
}
function clearPage(forget = false) {
  if (forget) {
    try {
      localStorage.removeItem(scope.value + '.state');
    } catch {
      storageError.value = true;
    }
    emit('location', '');
  }
  document.value = null;
  identity.value = '';
  selected.value = '';
  searchKey.value = '';
  revision.value = '';
  editing.value = false;
  files.value = [];
  histories.value = [];
  historyPreview.value = null;
  navigationPage.value = true;
}
function applyCommon(result) {
  initialized.value = result.initialized;
  canEdit.value = result.canEdit;
  canInitialize.value = result.canInitialize;
  if (result.catalog) catalog.value = result.catalog;
  if (result.catalogRevision) catalogRevision.value = result.catalogRevision;
}
function applyPage(result, edit = false) {
  applyCommon(result);
  if (result.entryMissing) {
    clearPage(true);
    error.value = t('This page is no longer available.');
    return;
  }
  document.value = result.document;
  identity.value = selected.value = result.identity;
  searchKey.value = result.searchKey;
  revision.value = result.revision;
  metadata.value = result.articleMetadata || {};
  files.value = result.attachments || [];
  if (searchKey.value) emit('location', searchKey.value);
  original = JSON.stringify(document.value);
  editing.value = edit;
  step.value = 1;
  expandedMetadata.value = false;
  navigationPage.value = false;
  historyPreview.value = null;
  histories.value = [];
  resourcesVisible.value = false;
  linkedIndex.value = 0;
}
async function call(action, values = {}) {
  return knowledgeRequest(action, props.ticket, props.project, values);
}
function fail(reason) {
  error.value = t(reason.message);
  if (reason.code === 'authentication_failed') emit('session-expired');
}
async function reload() {
  if (saving.value || organization.value || !props.ticket || !props.project)
    return;
  checkpoint();
  const id = ++request;
  loading.value = true;
  error.value = '';
  try {
    const result = await call('list', { query: query.value });
    if (id !== request) return;
    applyCommon(result);
    loaded.value = true;
    if (!identity.value) {
      const state = JSON.parse(
        localStorage.getItem(scope.value + '.state') || '{}'
      );
      if (state.identity) await select(state.identity);
    }
  } catch (reason) {
    if (id === request) fail(reason);
  } finally {
    if (id === request) loading.value = false;
  }
}
async function select(id) {
  if (saving.value) return;
  checkpoint();
  stagedFiles.set(identity.value, pendingFiles.value);
  pendingFiles.value = stagedFiles.get(id) || [];
  selected.value = id;
  navigationPage.value = false;
  const turn = ++request;
  loading.value = true;
  error.value = '';
  const draft = drafts[id];
  if (draft) {
    document.value = JSON.parse(JSON.stringify(draft.document));
    identity.value = id;
    searchKey.value = draft.searchKey;
    revision.value = draft.revision;
    files.value = draft.attachments || [];
    metadata.value = draft.metadata || {};
    editing.value = true;
    step.value = draft.step || 0;
    expandedMetadata.value =
      step.value === 0 || document.value.kind === 'section';
    original = '';
    historyPreview.value = null;
    loading.value = false;
    emit('location', searchKey.value || '');
    return;
  }
  try {
    const result = await call('load', { identity: id, query: query.value });
    if (turn !== request) return;
    if (drafts[result.identity]) {
      applyCommon(result);
      await select(result.identity);
    } else applyPage(result);
  } catch (reason) {
    if (turn === request) fail(reason);
  } finally {
    if (turn === request) loading.value = false;
  }
}
function create(kind) {
  if (saving.value || organization.value) return;
  checkpoint();
  stagedFiles.set(identity.value, pendingFiles.value);
  pendingFiles.value = [];
  request++;
  const parent =
    document.value?.kind === 'section'
      ? identity.value
      : document.value?.parentCode || '';
  identity.value = selected.value = 'local:' + randomId();
  searchKey.value = '';
  revision.value = '';
  metadata.value = {};
  files.value = [];
  document.value = {
    title: '',
    description: '',
    kind,
    parentCode: parent.startsWith('local:') ? '' : parent,
    contentMarkdown: '',
    contentText: '',
    linkedSearchKeys: [],
    sortOrder: 0,
    draft: true
  };
  original = '';
  editing.value = true;
  step.value = 0;
  expandedMetadata.value = true;
  navigationPage.value = false;
  attachmentsVisible.value = false;
  historyPreview.value = null;
  error.value = '';
  checkpoint();
  emit('location', '');
}
function beginEdit() {
  if (organization.value) return;
  editing.value = true;
  expandedMetadata.value = document.value.kind === 'section';
  step.value = 1;
  original = JSON.stringify(document.value);
}
async function save(draft = false, reserve = false) {
  if (saving.value || !document.value) return false;
  if (!document.value.title.trim()) {
    error.value = t('Enter a title');
    expandedMetadata.value = true;
    step.value = 0;
    return false;
  }
  const current = identity.value,
    turn = request,
    ticket = props.ticket,
    project = props.project;
  const values = JSON.parse(JSON.stringify(document.value));
  values.contentText = plainText(values.contentMarkdown);
  saving.value = true;
  error.value = '';
  checkpoint();
  try {
    const result = await knowledgeRequest(
      reserve ? 'reserve' : draft ? 'save_draft' : 'save',
      ticket,
      project,
      {
        identity: creating.value ? '' : current,
        expected_revision: revision.value,
        document: values
      }
    );
    if (
      turn !== request ||
      ticket !== props.ticket ||
      project !== props.project
    )
      return false;
    delete drafts[current];
    storeDrafts();
    applyPage(result, draft || reserve);
    emit('changed');
    return true;
  } catch (reason) {
    if (turn === request) fail(reason);
    return false;
  } finally {
    if (turn === request) saving.value = false;
  }
}
async function discard() {
  const id = identity.value;
  delete drafts[id];
  storeDrafts();
  if (creating.value) {
    clearPage(true);
    return;
  }
  editing.value = false;
  await select(id);
}
function search() {
  if (organization.value || saving.value) return;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(reload, 220);
}
function move(source, target, placement = 'inside') {
  if (!canEdit.value || saving.value || editing.value || creating.value) return;
  const rows = JSON.parse(JSON.stringify(catalog.value)),
    item = rows.find((row) => row.identity === source),
    to = rows.find((row) => row.identity === target);
  if (!item || !to || item === to) return;
  const parent = placement === 'inside' ? to.identity : to.parentCode;
  if (placement === 'inside' && to.kind !== 'section') return;
  let ancestor = parent;
  const seen = new Set([source]);
  while (ancestor) {
    if (seen.has(ancestor)) {
      error.value = t('A section cannot be moved inside its child');
      return;
    }
    seen.add(ancestor);
    ancestor = rows.find((row) => row.identity === ancestor)?.parentCode || '';
  }
  organization.value ||= JSON.parse(JSON.stringify(catalog.value));
  item.parentCode = parent;
  const siblings = rows
    .filter((row) => row.parentCode === parent && row.identity !== source)
    .sort(compare);
  const index =
    placement === 'inside'
      ? siblings.length
      : siblings.findIndex((row) => row.identity === target) +
        (placement === 'after' ? 1 : 0);
  siblings.splice(Math.max(0, index), 0, item);
  siblings.forEach((row, index) => {
    row.sortOrder = index;
  });
  catalog.value = rows;
  dropTarget.value = '';
  if (document.value && identity.value === source)
    document.value.parentCode = parent;
}
function drop(event, row) {
  event.preventDefault();
  const box = event.currentTarget.getBoundingClientRect(),
    point = (event.clientY - box.top) / box.height;
  move(
    dragging.value,
    row.identity,
    point < 0.34
      ? 'before'
      : point > 0.66
        ? 'after'
        : row.kind === 'section'
          ? 'inside'
          : 'after'
  );
  dragging.value = '';
  dropTarget.value = '';
}
function reorder(id, direction) {
  const item = catalog.value.find((row) => row.identity === id),
    siblings = catalog.value
      .filter((row) => row.parentCode === item.parentCode)
      .sort(compare),
    target = siblings[siblings.indexOf(item) + direction];
  if (target) move(id, target.identity, direction < 0 ? 'before' : 'after');
}
async function saveOrder() {
  if (!organization.value || saving.value) return;
  const turn = request;
  saving.value = true;
  error.value = '';
  try {
    const result = await call('organize', {
      organization: catalog.value.map(
        ({ identity, parentCode, sortOrder }) => ({
          identity,
          parentCode,
          sortOrder
        })
      ),
      expected_revision: catalogRevision.value
    });
    if (turn !== request) return;
    applyCommon(result);
    organization.value = null;
    emit('changed');
  } catch (reason) {
    if (turn === request) fail(reason);
  } finally {
    if (turn === request) saving.value = false;
  }
}
function undoOrder() {
  catalog.value = organization.value;
  organization.value = null;
  if (document.value)
    document.value.parentCode =
      catalog.value.find((row) => row.identity === identity.value)
        ?.parentCode || '';
}
function openMove(id) {
  moveIdentity.value = id;
  moveParent.value =
    catalog.value.find((row) => row.identity === id)?.parentCode || '';
  moveDialog.value.showModal();
}
function applyMove() {
  if (moveParent.value) move(moveIdentity.value, moveParent.value, 'inside');
  else {
    const root = catalog.value.find(
      (row) => !row.parentCode && row.identity !== moveIdentity.value
    );
    if (root) move(moveIdentity.value, root.identity, 'after');
    else {
      organization.value ||= JSON.parse(JSON.stringify(catalog.value));
      catalog.value = catalog.value.map((row) =>
        row.identity === moveIdentity.value ? { ...row, parentCode: '' } : row
      );
    }
  }
  moveDialog.value.close();
}
async function initialize() {
  const turn = request;
  saving.value = true;
  error.value = '';
  try {
    const result = await call('initialize');
    if (turn !== request) return;
    applyCommon(result);
    loaded.value = true;
  } catch (reason) {
    if (turn === request) fail(reason);
  } finally {
    if (turn === request) saving.value = false;
  }
}
async function history() {
  if (!historyDialog.value?.open) return;
  histories.value = [];
  const id = ++historyRequest;
  try {
    const result = await call('history', { identity: identity.value });
    if (id === historyRequest) histories.value = result.history;
  } catch (reason) {
    if (id === historyRequest) fail(reason);
  }
}
async function previewHistory(id) {
  const current = identity.value,
    turn = ++historyRequest;
  try {
    const result = await call('history_revision', {
      identity: current,
      history_revision: id
    });
    if (current === identity.value && turn === historyRequest) {
      historyPreview.value = result.historyRevision;
      historyDialog.value.close();
    }
  } catch (reason) {
    if (turn === historyRequest) fail(reason);
  }
}
async function refreshFiles() {
  const id = request,
    current = identity.value;
  const result = await call('attachments', { identity: current });
  if (id === request && current === identity.value) {
    files.value = result.attachments || [];
    checkpoint();
  }
}
async function addFiles(selectedFiles) {
  if (!canEdit.value || saving.value || !selectedFiles.length) return;
  pendingFiles.value.push(
    ...selectedFiles.map((file) => ({ file, status: 'ready', error: '' }))
  );
  attachmentsVisible.value = true;
  if (creating.value && !(await save(true, true))) return;
  await uploadPending();
}
async function uploadPending() {
  if (saving.value || creating.value) return;
  const current = identity.value,
    turn = request,
    project = props.project,
    ticket = props.ticket;
  saving.value = true;
  try {
    for (const entry of pendingFiles.value.filter(
      (entry) => entry.status !== 'done'
    )) {
      entry.status = 'uploading';
      entry.error = '';
      try {
        const result = await messageFileRequest(
          ticket,
          project,
          { identity: current },
          entry.file,
          'knowledge'
        );
        if (turn !== request) return;
        entry.status = 'done';
        if (identity.value === current && project === props.project)
          files.value = result.attachments || [];
      } catch (reason) {
        if (turn !== request) return;
        entry.status = 'failed';
        entry.error = reason.message;
      }
    }
    checkpoint();
  } finally {
    if (turn === request) saving.value = false;
  }
}
async function pasteImage() {
  const turn = request;
  try {
    const items = await navigator.clipboard.read();
    const selected = [];
    for (const item of items) {
      const type = item.types.find((type) => type.startsWith('image/'));
      if (type)
        selected.push(
          new File([await item.getType(type)], 'clipboard.png', { type })
        );
    }
    if (turn === request) await addFiles(selected);
  } catch (reason) {
    if (turn === request) fail(reason);
  }
}
function confirmFile(file) {
  deletingFile.value = file;
  deletion.value.showModal();
}
async function removeFile() {
  const turn = request;
  const file = deletingFile.value;
  deletion.value.close();
  saving.value = true;
  try {
    const result = await call('delete_attachment', {
      identity: identity.value,
      attachment_key: file.snapshotKey
    });
    if (turn !== request) return;
    files.value = result.attachments || [];
    checkpoint();
  } catch (reason) {
    if (turn === request) fail(reason);
  } finally {
    if (turn === request) saving.value = false;
  }
}
async function copy(value, token = '') {
  const turn = request;
  try {
    await copyText(value);
    if (turn === request) copying.value = token;
  } catch (reason) {
    if (turn === request) fail(reason);
  }
}
async function openDeletion() {
  const turn = request;
  if (creating.value) {
    await discard();
    return;
  }
  deleteGroups.value = [];
  deleteTypes.value = [];
  deletingFile.value = null;
  deletion.value.showModal();
  loading.value = true;
  try {
    const result = await call('deletion', { identity: identity.value });
    if (turn !== request) return;
    deleteGroups.value = result.groups;
    deleteTypes.value = result.groups
      .filter((row) => row.selected)
      .map((row) => row.search_type);
  } catch (reason) {
    if (turn !== request) return;
    fail(reason);
    deletion.value.close();
  } finally {
    if (turn === request) loading.value = false;
  }
}
async function deletePage() {
  const turn = request;
  saving.value = true;
  error.value = '';
  try {
    const result = await call('delete', {
      identity: identity.value,
      expected_revision: revision.value,
      related_types: deleteTypes.value
    });
    if (turn !== request) return;
    applyCommon(result);
    delete drafts[identity.value];
    storeDrafts();
    deletion.value.close();
    clearPage(true);
    emit('changed');
  } catch (reason) {
    if (turn === request) fail(reason);
  } finally {
    if (turn === request) saving.value = false;
  }
}
function linkSelection() {
  const keys = (props.selection || []).map(
    (row) => 'skey://' + row.__search_key__.replace(/^skey:\/\//, '')
  );
  document.value.linkedSearchKeys = [
    ...new Set([...linked.value, ...keys])
  ].slice(0, 128);
  checkpoint();
}
function unlink() {
  document.value.linkedSearchKeys = linked.value.filter(
    (_, index) => index !== linkedIndex.value
  );
  linkedIndex.value = Math.max(0, linkedIndex.value - 1);
  checkpoint();
}
async function loadReferences() {
  const turn = ++previewRequest,
    keys = resourceKeys.value;
  try {
    const result = await linkPreviews(props.ticket, props.project, keys);
    if (turn === previewRequest)
      references.value = Object.fromEntries(
        result.previews.map((row) => [row.searchKey, row])
      );
  } catch (reason) {
    if (turn === previewRequest) fail(reason);
  }
}
function activate(event) {
  const anchor = event.target.closest('a'),
    image = event.target.closest('img');
  if (anchor) {
    const link = anchor.dataset.link || anchor.getAttribute('href');
    if (link?.startsWith('#')) {
      event.preventDefault();
      viewer.value
        ?.querySelector('#' + CSS.escape(link.slice(1)))
        ?.scrollIntoView({ block: 'start' });
      return;
    }
    if (
      /^(skey|tactic-search):/i.test(link) &&
      !event.ctrlKey &&
      !event.metaKey
    ) {
      event.preventDefault();
      openLink(link);
    }
  } else if (image)
    window.open(image.dataset.original || image.src, '_blank', 'noopener');
}
function openLink(value) {
  if (openObjectTab) openObjectTab(value, props.project);
  else emit('open-link', value);
}
function imageError(event) {
  const image = event.target;
  if (image.tagName !== 'IMG') return;
  const file = files.value.find(
    (file) =>
      file.webUrl === (image.dataset.original || image.getAttribute('src'))
  );
  if (
    file &&
    file.previewUrl !== file.webUrl &&
    image.src !== new URL(file.previewUrl, location.href).href
  ) {
    image.dataset.original = file.webUrl;
    image.src = file.previewUrl;
  }
}
function openFile(file) {
  window.open(file.webUrl, '_blank', 'noopener');
}
function scrollHeading(id) {
  viewer.value
    ?.querySelector('#' + CSS.escape(id))
    ?.scrollIntoView({ block: 'start' });
}
function date(value) {
  const stamp = messageDate(value);
  return Number.isNaN(stamp.getTime())
    ? ''
    : stamp.toLocaleString(appearance.language);
}
function beforeUnload(event) {
  checkpoint();
  if (
    saving.value ||
    (storageError.value && dirty.value) ||
    organization.value
  ) {
    event.preventDefault();
    event.returnValue = '';
  }
}
function canLeave() {
  checkpoint();
  if (
    saving.value ||
    organization.value ||
    (storageError.value && dirty.value)
  ) {
    error.value = t(
      'Finish the current operation or save/discard order changes before leaving.'
    );
    return false;
  }
  return true;
}
watch(document, checkpoint, { deep: true });
watch(resourceKeys, () => {
  references.value = {};
  if (resourceKeys.value.length) loadReferences();
});
watch(
  () => [props.ticket, props.project, props.login],
  () => {
    request++;
    historyRequest++;
    previewRequest++;
    clearTimeout(searchTimer);
    deletion.value?.close();
    moveDialog.value?.close();
    deletingFile.value = null;
    deleteGroups.value = [];
    deleteTypes.value = [];
    saving.value = false;
    loading.value = false;
    error.value = '';
    initialized.value = false;
    canEdit.value = false;
    canInitialize.value = false;
    context = scope.value;
    clearPage();
    catalog.value = [];
    query.value = '';
    organization.value = null;
    pendingFiles.value = [];
    stagedFiles.clear();
    loaded.value = false;
    for (const id of Object.keys(drafts)) delete drafts[id];
    try {
      const state = JSON.parse(
        localStorage.getItem(context + '.state') || '{}'
      );
      navigationExpanded.value = state.navigationExpanded !== false;
      tocVisible.value = state.tocVisible !== false;
      collapsed.clear();
      for (const id of state.collapsed || []) collapsed.add(id);
      const saved = JSON.parse(localStorage.getItem(context) || '{}');
      for (const [id, entry] of Object.entries(saved))
        if (
          entry?.document &&
          typeof entry.document.title === 'string' &&
          typeof entry.document.contentMarkdown === 'string'
        )
          drafts[id] = entry;
    } catch {
      error.value = t('Local drafts could not be restored.');
    }
    if (props.active) reload();
  },
  { immediate: true }
);
watch(
  () => props.active,
  (value) => {
    if (value && !loaded.value) reload();
    else if (!value) checkpoint();
  }
);
watch(
  () => [props.target, props.project],
  ([value, project]) => {
    if (!value) return;
    try {
      const address = new URL(value);
      if ((address.searchParams.get('project') || project) === project)
        select(
          address.searchParams.get('id') || address.searchParams.get('code')
        );
    } catch {
      fail(new Error(t('Invalid TACTIC link')));
    }
  },
  { immediate: true }
);
onMounted(() => {
  observer = new ResizeObserver((entries) => {
    width.value = entries[0].contentRect.width;
    height.value = entries[0].contentRect.height;
  });
  observer.observe(host.value);
  window.addEventListener('beforeunload', beforeUnload);
});
onBeforeUnmount(() => {
  checkpoint();
  request++;
  historyRequest++;
  previewRequest++;
  observer?.disconnect();
  clearTimeout(searchTimer);
  window.removeEventListener('beforeunload', beforeUnload);
});
defineExpose({ open: select, reload, canLeave });
</script>
<template>
  <div ref="host" class="knowledge-base" :class="{ narrow, single }">
    <FrameView
      class="knowledge-workspace-frame"
      :scene="{ nodes: scene.nodes.filter((node) => node.kind !== 'View') }"
      @event="workspaceAction"
    />
    <InitializationState
      v-if="!initialized"
      :style="style(bounds.body)"
      title="Knowledge Base is not initialized"
      message="Initialize the collaboration schema before writing project documentation."
      icon="file"
      :project="project"
      :can-initialize="canInitialize"
      :busy="saving || loading"
      @initialize="initialize"
    />
    <div v-else class="knowledge-layout">
      <nav
        v-show="!single || navigationPage"
        :style="style(bounds.navigation)"
        class="knowledge-navigation"
        :aria-label="t('Articles')"
      >
        <AppSearchField
          v-model="query"
          class="knowledge-search"
          label="Search sections and articles"
          :placeholder="t('Search sections and articles')"
          :disabled="saving || !!organization"
          @update:model-value="search"
          @search="reload"
        />
        <div class="knowledge-tree" role="tree">
          <div
            v-for="row in entries"
            :key="row.identity"
            class="knowledge-tree-row"
            :class="{
              selected: row.identity === selected,
              drop: dropTarget === row.identity,
              section: row.kind === 'section'
            }"
            :style="{ '--depth': row.depth }"
            role="treeitem"
            :aria-selected="row.identity === selected"
            :aria-expanded="row.hasChildren ? row.expanded : undefined"
            :data-knowledge-entry="row.identity"
            :draggable="canEdit && !editing && !row.localDraft"
            @dragstart="dragging = row.identity"
            @dragover.prevent="dropTarget = row.identity"
            @dragleave="dropTarget = ''"
            @drop="drop($event, row)"
            @dragend="
              dragging = '';
              dropTarget = '';
            "
          >
            <FrameView
              class="knowledge-navigation-record"
              :style="{ height: Navigation.rowHeight(row, query) + 'px' }"
              :scene="
                Navigation.row(
                  row,
                  row.identity === selected,
                  query,
                  Math.max(
                    0,
                    bounds.navigation.width -
                      28 -
                      (canEdit && !row.localDraft ? 30 : 0)
                  ),
                  appearance.language
                )
              "
              @event="
                (action) => {
                  if (action.type === 'select') select(action.id);
                  else if (action.type === 'disclose')
                    collapsed.has(action.id)
                      ? collapsed.delete(action.id)
                      : collapsed.add(action.id);
                }
              "
            />
            <AppMenu
              v-if="canEdit && !row.localDraft"
              class="knowledge-row-menu"
              label="Organize page"
              overlay
              :width="220"
              ><AppMenuItem
                label="Move up"
                icon="arrow-up"
                :disabled="editing || saving"
                @click="reorder(row.identity, -1)" /><AppMenuItem
                label="Move down"
                icon="arrow-down"
                :disabled="editing || saving"
                @click="reorder(row.identity, 1)" /><AppMenuItem
                label="Move to section"
                icon="folder"
                :disabled="editing || saving"
                @click="openMove(row.identity)"
            /></AppMenu>
          </div>
          <p v-if="!entries.length && !loading" class="knowledge-no-entries">
            {{ t(query ? 'No matching articles' : 'No articles yet') }}
          </p>
        </div>
      </nav>
      <main
        v-show="!single || !navigationPage"
        :style="style(bounds.page)"
        class="knowledge-page"
        :class="{ 'article-narrow': articleNarrow }"
      >
        <div v-if="loading" class="knowledge-loading" role="status">
          {{ t('Loading…') }}
        </div>
        <div v-else-if="!document" class="knowledge-empty">
          <AppIcon name="file" />
          <h3>{{ t('Choose an article') }}</h3>
          <p>
            {{
              t(
                'Sections, full-text search, files, and object links stay together here.'
              )
            }}
          </p>
        </div>
        <template v-else-if="editing">
          <FrameView
            class="knowledge-editor-commands"
            :style="{ height: Commands.editorHeight(pageWidth) + 'px' }"
            :scene="
              Commands.editor(
                editorPresentation,
                pageWidth,
                appearance.language
              )
            "
            @event="editorAction"
          />
          <div v-if="creating && step === 0" class="knowledge-parent">
            <AppIcon name="folder" /><span
              ><small>{{ t('Parent section') }}</small
              >{{ parentTitle }}</span
            >
          </div>
          <div
            v-if="
              document.kind === 'section' ||
              (creating && step === 0) ||
              (expandedMetadata && !creating)
            "
            class="knowledge-metadata-fields"
          >
            <label
              >{{ t('Title')
              }}<AppTextField
                v-model="document.title"
                label="Title"
                placeholder="A short, recognizable title"
                :disabled="saving" /></label
            ><label
              >{{ t('Summary')
              }}<AppTextArea
                v-model="document.description"
                label="Summary"
                placeholder="What this page is about"
                :disabled="saving" /></label
            ><label v-if="document.kind === 'section'"
              >{{ t('Parent section')
              }}<AppSelect
                v-model="document.parentCode"
                :options="
                  sectionOptions.filter((row) => row.value !== identity)
                "
                label="Parent section" /></label
            ><AppButton
              v-if="creating && document.kind === 'article'"
              label="Continue to content"
              icon="next"
              :disabled="!document.title.trim()"
              @click="
                step = 1;
                expandedMetadata = false;
                checkpoint();
              "
            />
          </div>
          <template
            v-if="document.kind === 'article' && (!creating || step === 1)"
          >
            <AppButton
              v-if="creating"
              class="knowledge-back-metadata"
              label="Back to title and summary"
              icon="previous"
              @click="step = 0"
            />
            <div v-if="linkedObject" class="knowledge-linked-header">
              <AppButton
                v-if="linked.length > 1"
                icon-only
                icon="previous"
                label="Previous linked object"
                @click="
                  linkedIndex =
                    (linkedIndex + linked.length - 1) % linked.length
                "
              /><SKeyPreviewCard
                :preview="linkedObject"
                compact
                @open="openLink"
              /><AppButton
                v-if="linked.length > 1"
                icon-only
                icon="next"
                label="Next linked object"
                @click="linkedIndex = (linkedIndex + 1) % linked.length"
              /><AppButton
                icon-only
                icon="link-off"
                label="Unlink object"
                @click="unlink"
              />
            </div>
            <KnowledgeEditor
              ref="editor"
              v-model="document.contentMarkdown"
              :project="project"
              :attachments="files"
              :disabled="saving"
              @attachments="attachmentsVisible = !attachmentsVisible"
              @upload="addFiles"
            >
              <template #attachments>
                <section
                  v-if="attachmentsVisible"
                  class="knowledge-attachment-library"
                >
                  <header>
                    <AppIcon name="attachments-editor" />
                    <div>
                      <h4>{{ t('Attached files') }}</h4>
                      <p>
                        {{
                          t(
                            'Files are uploaded and attached before you insert their permanent links into the article.'
                          )
                        }}
                      </p>
                    </div>
                    <AppButton
                      icon-only
                      label="Attach files"
                      icon="attachments-editor"
                      :disabled="saving"
                      @click="fileInput.click()"
                    /><AppButton
                      icon-only
                      icon="close"
                      label="Hide attached files"
                      @click="attachmentsVisible = false"
                    />
                  </header>
                  <div
                    class="knowledge-staging"
                    @dragover.prevent
                    @drop.prevent="addFiles([...$event.dataTransfer.files])"
                  >
                    <header>
                      <AppIcon name="attachments-editor" /><small>{{
                        t('Attachments')
                      }}</small
                      ><AppButton
                        icon-only
                        icon="content-paste"
                        label="Paste image"
                        :disabled="saving || !clipboardAvailable"
                        @click="pasteImage"
                      /><AppButton
                        v-if="pendingFiles.length"
                        icon-only
                        icon="close"
                        label="Clear staged files"
                        :disabled="saving"
                        @click="pendingFiles = []"
                      />
                    </header>
                    <AppButton
                      class="knowledge-stage-empty"
                      label="Drop files here or attach them from disk"
                      :disabled="saving"
                      @click="fileInput.click()"
                      ><AppIcon name="attachments-editor" /><span>{{
                        t('Drop files here or attach them from disk')
                      }}</span></AppButton
                    >
                  </div>
                  <div
                    v-for="(entry, index) in pendingFiles"
                    :key="index"
                    v-show="entry.status !== 'done'"
                    class="knowledge-pending"
                  >
                    <span
                      >{{ entry.file.name }} ·
                      {{
                        t(
                          entry.status === 'failed'
                            ? 'Failed'
                            : entry.status === 'uploading'
                              ? 'Uploading'
                              : 'Ready'
                        )
                      }}</span
                    ><small v-if="entry.error" class="error">{{
                      entry.error
                    }}</small
                    ><AppButton
                      v-if="entry.status === 'failed'"
                      icon-only
                      icon="refresh"
                      label="Retry"
                      :disabled="saving"
                      @click="uploadPending"
                    /><AppButton
                      icon-only
                      icon="close"
                      label="Remove staged file"
                      :disabled="saving"
                      @click="pendingFiles.splice(index, 1)"
                    />
                  </div>
                  <div
                    v-for="file in files"
                    :key="file.token"
                    class="knowledge-library-file"
                  >
                    <AttachmentCard
                      compact
                      :activation-icon="file.isImage ? 'image' : 'link'"
                      :activation-label="
                        file.isImage ? 'Insert image' : 'Insert link'
                      "
                      :title="file.title"
                      :extension="file.extension"
                      :preview-url="file.previewUrl"
                      :size-text="String(file.size || 0) + ' B'"
                      @activated="editor.insertAttachment(file)"
                    /><AppButton
                      icon-only
                      :icon="copying === file.token ? 'check' : 'copy'"
                      :label="
                        copying === file.token ? 'Copied' : 'Copy web link'
                      "
                      @click="copy(file.webUrl, file.token)"
                    /><AppButton
                      icon-only
                      icon="delete"
                      label="Delete file"
                      :disabled="saving"
                      @click="confirmFile(file)"
                    />
                  </div>
                  <p v-if="!files.length">
                    {{ t('No files uploaded to this article yet.') }}
                  </p>
                </section>
              </template>
            </KnowledgeEditor>
          </template>
        </template>
        <template v-else>
          <FrameView
            class="knowledge-viewer-commands"
            :style="{ height: Commands.viewerHeight(pageWidth) + 'px' }"
            :scene="
              Commands.viewer(
                viewerPresentation,
                pageWidth,
                appearance.language
              )
            "
            @event="viewerAction"
          />
          <AppMenu
            ref="historyDialog"
            external-trigger
            label="Change history"
            overlay
            :width="390"
            :close-on-select="false"
            class="knowledge-history-menu"
            ><h4><AppIcon name="history" />{{ t('Change history') }}</h4>
            <AppButton
              v-for="row in histories"
              :key="row.revisionId"
              icon="history"
              :label="row.title"
              @click="previewHistory(row.revisionId)"
              ><span
                ><strong>{{ row.title }}</strong
                ><small>{{ row.actor }} · {{ date(row.timestamp) }}</small
                ><small>{{ row.changedFields.join(', ') }}</small></span
              ></AppButton
            >
            <p v-if="!histories.length">{{ t('Loading…') }}</p></AppMenu
          >
          <div v-if="historyPreview" class="knowledge-history-banner">
            <span
              >{{ t('Previewing an earlier revision') }} ·
              {{ historyPreview.actor }} ·
              {{ date(historyPreview.timestamp) }}</span
            ><AppButton
              label="Return to current article"
              icon="close"
              @click="historyPreview = null"
            />
          </div>
          <div
            v-if="shown.kind === 'section'"
            class="knowledge-section-contents"
          >
            <AppButton
              v-for="row in sectionEntries"
              :key="row.identity"
              :style="{ paddingLeft: 7 + (row.level - 1) * 18 + 'px' }"
              :label="row.title"
              @click="select(row.identity)"
              ><AppIcon
                :name="row.kind === 'section' ? 'folder-open' : 'file'"
              /><span
                >{{ row.title
                }}<small v-if="row.kind === 'section'">{{
                  t('Section')
                }}</small></span
              ></AppButton
            >
            <p v-if="!sectionEntries.length">
              {{ t('This section has no pages yet.') }}
            </p>
          </div>
          <div
            v-else
            class="knowledge-reading"
            :class="{
              'side-outline': !articleNarrow && tocVisible && toc.length
            }"
          >
            <div class="knowledge-reading-scroll">
              <div
                v-if="linkedObject && !historyPreview"
                class="knowledge-linked-header"
              >
                <AppButton
                  v-if="linked.length > 1"
                  icon-only
                  icon="previous"
                  label="Previous linked object"
                  @click="
                    linkedIndex =
                      (linkedIndex + linked.length - 1) % linked.length
                  "
                /><SKeyPreviewCard
                  :preview="linkedObject"
                  compact
                  @open="openLink"
                /><AppButton
                  v-if="linked.length > 1"
                  icon-only
                  icon="next"
                  label="Next linked object"
                  @click="linkedIndex = (linkedIndex + 1) % linked.length"
                />
              </div>
              <KnowledgeOutline
                v-if="articleNarrow && tocVisible && toc.length"
                compact
                :entries="toc"
                @heading="(entry) => scrollHeading(entry.id)"
              />
              <article
                ref="viewer"
                class="knowledge-document"
                v-html="html"
                @click="activate"
                @error.capture="imageError"
              />
              <section
                v-if="resourcesVisible && !historyPreview"
                class="knowledge-resources"
              >
                <h4>{{ t('Linked objects and files') }}</h4>
                <SKeyPreviewCard
                  v-for="key in resourceKeys"
                  :key="key"
                  :preview="
                    references[key] || { searchKey: key, status: 'loading' }
                  "
                  @open="openLink"
                  @retry="loadReferences"
                  @copy="copy"
                /><AttachmentCard
                  v-for="file in files"
                  :key="file.token"
                  :title="file.title"
                  :extension="file.extension"
                  :preview-url="file.previewUrl"
                  :size-text="String(file.size || 0) + ' B'"
                  @activated="openFile(file)"
                />
              </section>
              <footer class="knowledge-article-metadata">
                <span
                  >{{ t('Author') }}:
                  {{
                    (historyPreview?.articleMetadata || metadata).author
                  }}</span
                ><span
                  >{{ t('Created') }}:
                  {{
                    date(
                      (historyPreview?.articleMetadata || metadata).createdAt
                    )
                  }}</span
                ><span
                  >{{ t('Updated') }}:
                  {{
                    date(
                      (historyPreview?.articleMetadata || metadata).updatedAt
                    )
                  }}</span
                >
              </footer>
            </div>
            <KnowledgeOutline
              v-if="!articleNarrow && tocVisible && toc.length"
              :entries="toc"
              @heading="(entry) => scrollHeading(entry.id)"
            />
          </div>
        </template>
      </main>
    </div>
    <input
      ref="fileInput"
      type="file"
      multiple
      hidden
      @change="
        addFiles([...$event.target.files]);
        $event.target.value = '';
      "
    />
    <dialog
      ref="deletion"
      class="record-dialog knowledge-deletion"
      :aria-label="t(deletingFile ? 'Delete article file?' : 'Delete record')"
    >
      <header>
        <h2>
          {{ t(deletingFile ? 'Delete article file?' : 'Delete record') }}
        </h2>
        <AppButton
          icon-only
          icon="close"
          label="Close"
          :disabled="saving"
          @click="deletion.close()"
        />
      </header>
      <template v-if="deletingFile"
        ><p>{{ deletingFile.title }}</p>
        <p>
          {{
            t(
              'The attachment snapshot will be retired. Existing article links are retained.'
            )
          }}
        </p></template
      ><template v-else
        ><p>{{ document?.title }}</p>
        <p>
          {{
            t(
              'Review dependencies before deleting this page. Linked project objects are preserved.'
            )
          }}
        </p>
        <AppCheckbox
          v-for="group in deleteGroups"
          :key="group.search_type"
          :model-value="deleteTypes.includes(group.search_type)"
          :label="group.title + ' · ' + group.count"
          @update:model-value="
            (value) => {
              deleteTypes = value
                ? [...deleteTypes, group.search_type]
                : deleteTypes.filter((kind) => kind !== group.search_type);
            }
          "
      /></template>
      <footer>
        <AppButton
          label="Cancel"
          :disabled="saving"
          @click="deletion.close()"
        /><AppButton
          label="Delete"
          destructive
          :disabled="saving || loading"
          @click="deletingFile ? removeFile() : deletePage()"
        />
      </footer>
    </dialog>
    <dialog
      ref="moveDialog"
      class="record-dialog"
      :aria-label="t('Move to section')"
    >
      <header>
        <h2>{{ t('Move to section') }}</h2>
        <AppButton
          icon-only
          icon="close"
          label="Close"
          @click="moveDialog.close()"
        />
      </header>
      <AppSelect
        v-model="moveParent"
        :options="sectionOptions.filter((row) => row.value !== moveIdentity)"
        label="Parent section"
      />
      <footer>
        <AppButton label="Cancel" @click="moveDialog.close()" /><AppButton
          label="Move"
          @click="applyMove"
        />
      </footer>
    </dialog>
  </div>
</template>
<style>
.knowledge-base {
  position: relative;
  display: block;
  flex-direction: column;
  gap: 7px;
  height: 100%;
  min-width: 0;
  min-height: 0;
  padding: 0;
  color: var(--on-surface);
  background: var(--page);
}
.knowledge-workspace-frame {
  position: absolute;
  inset: 0;
}
.knowledge-layout {
  display: contents;
}
.knowledge-navigation {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
  min-height: 0;
}
.knowledge-editor-commands,
.knowledge-viewer-commands {
  flex: none;
  position: relative;
}
.knowledge-search {
  display: flex;
  align-items: center;
  flex: none;
  background: var(--surface-high);
  border: 1px solid var(--outline-variant);
  border-radius: var(--item-radius);
  padding-left: 10px;
  height: var(--control-height);
}
.knowledge-search > .app-icon {
  width: 18px;
  height: 18px;
  font-size: 18px;
  color: var(--muted);
}
.knowledge-search input {
  width: 100%;
  background: transparent;
  border: 0;
  height: 100%;
}
.knowledge-tree {
  flex: 1;
  overflow: auto;
  padding-right: 12px;
}
.knowledge-tree-row {
  display: flex;
  align-items: flex-start;
  gap: 0;
  position: relative;
  margin-bottom: 1px;
}
.knowledge-tree-row.drop {
  box-shadow: inset 0 -3px var(--primary);
}
.knowledge-navigation-record {
  min-width: 0;
  flex: 1;
  position: relative;
}
.knowledge-row-menu {
  flex: none;
}
.knowledge-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
  gap: 7px;
}
.knowledge-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 8px;
  padding: 24px;
  color: var(--muted);
}
.knowledge-empty > .app-icon {
  font-size: 28px;
}
.knowledge-empty h3,
.knowledge-empty p {
  margin: 0;
}
.knowledge-error {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px;
  border: 1px solid var(--error);
  border-radius: var(--item-radius);
  background: color-mix(in srgb, var(--error) 14%, var(--surface));
  font-size: var(--text-caption);
}
.knowledge-error > span {
  flex: 1;
}
.knowledge-parent {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: var(--item-radius);
  background: var(--surface);
  border: 1px solid var(--outline-variant);
}
.knowledge-parent > span {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.knowledge-parent small {
  font-size: var(--text-caption);
  color: var(--muted);
}
.knowledge-metadata-fields {
  display: flex;
  flex-direction: column;
  gap: 9px;
  overflow: auto;
  min-height: 0;
  padding: 8px;
}
.knowledge-metadata-fields label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: var(--text-label);
}
.knowledge-metadata-fields textarea {
  min-height: 74px;
}
.knowledge-metadata-fields > button {
  align-self: flex-end;
}
.knowledge-back-metadata {
  align-self: flex-start;
}
.knowledge-reading {
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
  gap: 10px;
}
.knowledge-reading-scroll {
  flex: 1;
  min-width: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.knowledge-document {
  font-family: var(--font-family);
  font-size: var(--text-body);
  line-height: 1.45;
  font-weight: 400;
  overflow-wrap: anywhere;
}
.knowledge-document p,
.knowledge-document div {
  margin: 0 0 8px;
}
.knowledge-document h1 {
  font-size: var(--text-heading);
}
.knowledge-document h2 {
  font-size: var(--text-title);
}
.knowledge-document h3 {
  font-size: var(--text-body-large);
}
.knowledge-document h4,
.knowledge-document h5,
.knowledge-document h6 {
  font-size: var(--text-body);
}
.knowledge-document h1,
.knowledge-document h2,
.knowledge-document h3,
.knowledge-document h4,
.knowledge-document h5,
.knowledge-document h6 {
  font-weight: 600;
  margin: 12px 0 8px;
  line-height: 1.25;
}
.knowledge-document > :first-child {
  margin-top: 0;
}
.knowledge-document img {
  max-width: 100%;
  object-fit: contain;
  height: auto;
  cursor: pointer;
}
.knowledge-document img[data-fit='content'] {
  width: 100%;
}
.knowledge-document a {
  color: var(--primary);
}
.knowledge-document ul,
.knowledge-document ol {
  padding-left: 24px;
  margin: 0 0 8px;
}
.knowledge-document li p {
  margin: 0;
}
.knowledge-document blockquote {
  position: relative;
  margin: 8px 0;
  padding: 12px 20px;
  background: var(--surface);
  border-left: 3px solid var(--primary);
  border-radius: var(--item-radius);
}
.knowledge-document blockquote::before {
  content: '“';
  color: var(--primary);
  font-size: 28px;
  position: absolute;
  left: 4px;
  top: 0;
}
.knowledge-document pre {
  position: relative;
  font-family: var(--font-mono);
  font-size: var(--text-body);
  border: 1px solid var(--outline-variant);
  border-radius: var(--item-radius);
  background: var(--surface);
  padding: 28px 12px 12px;
  white-space: pre-wrap;
  overflow: auto;
}
.knowledge-document pre::before {
  content: attr(data-language);
  position: absolute;
  top: 6px;
  left: 12px;
  color: var(--muted);
  font-size: var(--text-caption);
}
.knowledge-document table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
}
.knowledge-document td,
.knowledge-document th {
  padding: 6px;
  border: 1px solid var(--outline-variant);
}
.knowledge-document code {
  font-family: var(--font-mono);
}
.knowledge-document :not(pre) > code {
  background: var(--surface-high);
  padding: 1px 4px;
  border-radius: 4px;
}
.knowledge-linked-header {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
  flex: none;
}
.knowledge-linked-header .skey-preview-card {
  flex: 1;
}
.knowledge-resources {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.knowledge-resources h4 {
  margin: 0;
  font-size: var(--text-label);
  color: var(--muted);
}
.knowledge-article-metadata {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--outline-variant);
  font-size: var(--text-caption);
  color: var(--muted);
}
.knowledge-section-contents {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: auto;
}
.knowledge-section-contents .app-button {
  justify-content: flex-start;
  text-align: left;
  border: 0;
  border-radius: var(--item-radius);
  background: transparent;
  gap: 7px;
  height: 36px;
  min-height: 36px;
  font-weight: 400;
}
.knowledge-section-contents small {
  color: var(--muted);
  font-size: var(--text-caption);
  margin-left: 8px;
}
.knowledge-attachment-library {
  max-height: 70%;
  overflow: auto;
  padding: 10px;
  background: var(--surface);
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  flex-shrink: 0;
}
.knowledge-attachment-library > header {
  display: flex;
  align-items: center;
  gap: 7px;
}
.knowledge-attachment-library h4 {
  margin: 0;
  font-size: var(--text-body-large);
  font-weight: 600;
}
.knowledge-attachment-library p {
  color: var(--muted);
  font-size: var(--text-caption);
  margin: 1px 0 0;
}
.knowledge-library-file {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
}
.knowledge-library-file .attachment-card {
  flex: 1;
}
.knowledge-staging {
  display: flex;
  flex-direction: column;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  background: var(--surface-high);
}
.knowledge-staging > span {
  flex: 1;
  font-size: var(--text-caption);
  color: var(--muted);
}
.knowledge-pending {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  font-size: var(--text-caption);
}
.knowledge-history .app-button {
  display: flex;
  width: 100%;
  border: 0;
  border-radius: var(--item-radius);
  background: transparent;
  padding: 8px;
  text-align: left;
  height: auto;
}
.knowledge-history .app-button > span {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.knowledge-history small {
  color: var(--muted);
  font-size: var(--text-caption);
}
.knowledge-history-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px;
  background: var(--surface);
  border: 1px solid var(--outline-variant);
  border-radius: var(--item-radius);
  flex: none;
}
.knowledge-history-banner > span {
  flex: 1;
  font-size: var(--text-caption);
}
.knowledge-no-entries {
  color: var(--muted);
  font-size: var(--text-body);
}
.knowledge-initialization,
.knowledge-deletion {
  width: min(580px, calc(100vw - 24px));
}
.knowledge-loading {
  color: var(--muted);
}
@media (pointer: coarse) {
  .knowledge-row-menu {
    opacity: 1;
  }
}
.knowledge-history-menu .account-panel {
  max-height: 440px;
  padding: 4px;
}
.knowledge-history-menu h4 {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  height: 36px;
  padding: 0 9px;
  font-size: var(--text-body);
  font-weight: 600;
}
.knowledge-history-menu h4 .app-icon {
  font-size: 18px;
  color: var(--primary);
}
.knowledge-history-menu .app-button {
  width: 100%;
  height: 62px;
  border: 0;
  background: transparent;
  justify-content: flex-start;
  text-align: left;
  padding: 7px 9px;
}
.knowledge-history-menu .app-button > span {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 3px;
}
.knowledge-history-menu .app-button strong {
  font-size: var(--text-body);
  font-weight: 600;
}
.knowledge-history-menu .app-button small {
  color: var(--muted);
  font-size: var(--text-caption);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.knowledge-document {
  font-size: 12.333px;
  font-weight: 400;
  line-height: 1.3;
}
.knowledge-document h1 {
  font-size: 24px;
}
.knowledge-document h2 {
  font-size: 18px;
}
.knowledge-document h3 {
  font-size: 14px;
}
.knowledge-document p {
  margin: 0 0 8px;
}
.knowledge-document h1,
.knowledge-document h2,
.knowledge-document h3 {
  margin: 0 0 7px;
}
.knowledge-tree-row strong {
  font-weight: 400;
}
.knowledge-tree-row.section strong {
  font-weight: 600;
}
.knowledge-tree-row.section .knowledge-entry > .app-icon {
  color: var(--tertiary);
}
.knowledge-article-metadata {
  flex-direction: row;
  flex-wrap: wrap;
  column-gap: 16px;
  color: var(--muted);
}
.knowledge-attachment-library > header > div {
  flex: 1;
  min-width: 0;
}
.knowledge-attachment-library > header > .app-icon {
  color: var(--primary);
  font-size: 18px;
}
.knowledge-attachment-library .icon-button {
  width: 30px;
  height: 30px;
  min-width: 30px;
  min-height: 30px;
}
.knowledge-staging > header {
  display: flex;
  align-items: center;
  gap: 7px;
}
.knowledge-staging > header > small {
  flex: 1;
  color: var(--muted);
}
.knowledge-staging > header > .app-icon {
  color: var(--primary);
  font-size: 18px;
}
.knowledge-stage-empty.app-button {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  border: 0;
  background: transparent;
  height: 96px;
  min-height: 96px;
  font-size: var(--text-body);
  font-weight: 400;
  color: var(--muted);
}
.knowledge-stage-empty > .app-icon {
  font-size: 32px;
}
</style>
