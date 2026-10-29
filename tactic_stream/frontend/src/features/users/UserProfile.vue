<script setup>
// UserProfileView.qml / UserController: one owner for requests, selection and editor.
import {
  ref,
  computed,
  nextTick,
  watch,
  onBeforeUnmount,
  toRaw,
  onMounted,
  markRaw
} from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import FrameView from '../../frame/FrameView.vue';
import ProfileActivity from './ProfileActivity.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/identity/profile.ui.mjs';
import * as EditorUI from '../../../../src/tactic_stream/shared_ui/features/support/identity/profile.editor.ui.mjs';
import * as EditorState from '../../../../src/tactic_stream/shared_ui/features/support/identity/profile.editor.state.mjs';
import { userProfile, userAvatar, activityFeed } from '../../api.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import { mobile } from '../../mobile.js';
import './userProfile.css';
const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  updates: Object
});
const emit = defineEmits([
  'message',
  'tasks',
  'activity',
  'open-object',
  'open-link',
  'logout',
  'saved',
  'session-expired'
]);
const serverHost = location.host;
const dialog = ref(null),
  editor = ref(null),
  avatarInput = ref(null);
const directoryExpanded = ref(true);
const visible = ref(false),
  directory = ref(false),
  width = ref(252),
  query = ref(''),
  selected = ref('');
const result = ref(null),
  summary = ref(null),
  events = ref([]),
  expanded = ref(false),
  error = ref(''),
  relatedError = ref(''),
  busy = ref(false),
  relatedBusy = ref(false);
const draft = ref(null),
  original = ref(null),
  mode = ref('profile'),
  creating = ref(false),
  saving = ref(false),
  uncertain = ref(false),
  editingError = ref(''),
  confirmClose = ref(false),
  avatar = ref(null);
let requestId = 0,
  mutationId = 0;
const profile = computed(() => result.value?.profile || {});
const permissions = computed(() => result.value?.permissions || {});
const presence = (login) =>
  props.updates?.presence?.find((row) => row.login === login) ||
  (login === props.login ? { online: true } : undefined);
const filteredUsers = computed(() =>
  (result.value?.users || []).filter(
    (row) => !row.retired && UI.matchesUser(row, query.value)
  )
);
const dirty = computed(() =>
  EditorState.dirty(draft.value, original.value, !!avatar.value)
);
const profileFields = EditorUI.profileFields,
  accountFields = EditorUI.accountFields;
const body = ref(null),
  editorBody = ref(null),
  viewport = ref({ width: 1000, height: 720 }),
  editorViewport = ref({ width: 638, height: 540 }),
  activityHeight = ref(0);
const frame = ref(null),
  editorFrame = ref(null);
const frameModel = computed(() => {
  const state = presence(selected.value);
  return {
    profile: {
      ...profile.value,
      current: selected.value === props.login,
      presenceKnown: !!state,
      online: !!state?.online
    },
    directory: directory.value,
    directoryExpanded: directoryExpanded.value,
    directoryWidth: width.value,
    query: query.value,
    canManage: permissions.value.manage,
    canEdit: permissions.value.edit,
    saving: saving.value,
    busy: busy.value,
    tasksBusy: relatedBusy.value,
    taskSummary: summary.value?.taskSummary,
    statusSummary: summary.value?.statusSummary,
    processSummary: summary.value?.processSummary,
    viewWorkHours: summary.value?.permissions?.viewWorkHours,
    workHourSummary: summary.value?.workHourSummary,
    activityCount: events.value.length,
    relatedBusy: relatedBusy.value,
    activityHeight: activityHeight.value,
    expanded: expanded.value,
    error: error.value,
    activityError: relatedError.value,
    server: serverHost,
    restricted: mobile.value
  };
});
const scene = computed(() =>
  UI.describe(
    frameModel.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const editorModel = computed(() => ({
  draft: draft.value || {},
  creating: creating.value,
  mode: mode.value,
  canManage: permissions.value.manage,
  restricted: mobile.value,
  saving: saving.value,
  uncertain: uncertain.value,
  confirmClose: confirmClose.value,
  error: editingError.value,
  displayName: profile.value.displayName,
  avatarName: avatar.value?.file.name
}));
const editorScene = computed(() =>
  EditorUI.describe(
    editorModel.value,
    editorViewport.value.width,
    editorViewport.value.height,
    appearance.language
  )
);
const row = (list, record) =>
  UI.userRow(frameModel.value, record, list.width - 16, appearance.language);
const editorRow = (list, record) =>
  EditorUI.groupRow(
    editorModel.value,
    record,
    list.width - 16,
    appearance.language
  );
const activityComponent = markRaw(ProfileActivity),
  avatarComponent = markRaw(ItemPreview);
const views = computed(() => ({
  activity: {
    component: activityComponent,
    props: {
      records: events.value,
      expanded: expanded.value,
      onHeight: (value) => (activityHeight.value = value),
      onActivity: (record) =>
        activate('open-object', { record, target: false }),
      onTarget: (record) => activate('open-object', { record, target: true }),
      onOpenLink: (value) => activate('open-link', value)
    }
  }
}));
const editorViews = computed(() => ({
  avatar: {
    component: avatarComponent,
    props: {
      file: avatar.value?.file,
      source: creating.value ? '' : profile.value.avatarUrl,
      fallbackText: creating.value ? '?' : profile.value.initials,
      accent: profile.value.avatarColor,
      previewSize: 54,
      round: true,
      outlined: true
    }
  }
}));
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries) {
      const box = entry.contentRect;
      if (box.width > 0 && box.height > 0)
        (entry.target === body.value ? viewport : editorViewport).value = {
          width: box.width,
          height: box.height
        };
    }
  });
  observer.observe(body.value);
});
watch(
  editorBody,
  (value, previous) => {
    if (previous) observer?.unobserve(previous);
    if (value) observer?.observe(value);
  },
  { flush: 'post' }
);
function dispatch(action) {
  if (action.type === 'user') {
    load(action.login);
    directoryExpanded.value = false;
  } else if (action.type === 'query') query.value = action.value;
  else if (action.type === 'directoryWidth') width.value = action.value;
  else if (action.type === 'showDirectory') directoryExpanded.value = true;
  else if (action.type === 'create') edit(true);
  else if (action.type === 'edit') edit();
  else if (action.type === 'editGroups') edit(false, 'groups');
  else if (action.type === 'refresh') load();
  else if (action.type === 'message') activate('message', selected.value);
  else if (action.type === 'logout') activate('logout');
  else if (action.type === 'tasks')
    activate('tasks', {
      login: selected.value,
      key: action.key,
      value: action.value
    });
  else if (action.type === 'activity') activate('activity', selected.value);
  else if (action.type === 'expand') expanded.value = !expanded.value;
}
function editorDispatch(action) {
  if (['field', 'group', 'access'].includes(action.type))
    draft.value = EditorState.edit(toRaw(draft.value), action);
  else if (action.type === 'mode')
    mode.value = EditorState.page(editorModel.value, action.value);
  else if (action.type === 'avatar') avatarInput.value.click();
  else if (action.type === 'save') save();
  else if (action.type === 'close') closeEditor();
  else if (action.type === 'discard') closeEditor(true);
  else if (action.type === 'keep') confirmClose.value = false;
  else if (action.type === 'reload') reloadEditor();
}
function fail(failure, editing = false) {
  (editing ? editingError : error).value = failure.message;
  if (failure.code === 'authentication_failed') emit('session-expired');
}
async function load(login = selected.value) {
  if (!props.ticket || !login) return;
  const id = ++requestId,
    ticket = props.ticket,
    project = props.project;
  selected.value = login;
  busy.value = true;
  error.value = '';
  relatedError.value = '';
  result.value = summary.value = null;
  events.value = [];
  expanded.value = false;
  try {
    const value = await userProfile('read', ticket, project, { login });
    if (id !== requestId) return;
    result.value = value;
    busy.value = false;
    relatedBusy.value = true;
    const related = await Promise.allSettled([
      userProfile('summary', ticket, project, { login }),
      activityFeed(ticket, project, { users: [login], filter: 'all' }, true)
    ]);
    if (id !== requestId) return;
    for (const [index, row] of related.entries()) {
      if (row.status === 'fulfilled') {
        if (index) events.value = row.value.records;
        else summary.value = row.value;
      } else {
        relatedError.value +=
          (relatedError.value ? '\n' : '') + row.reason.message;
        if (row.reason.code === 'authentication_failed')
          emit('session-expired');
      }
    }
  } catch (failure) {
    if (id === requestId) fail(failure);
  } finally {
    if (id === requestId) busy.value = relatedBusy.value = false;
  }
}
async function open(login = props.login, showDirectory = false) {
  directory.value = showDirectory;
  directoryExpanded.value = showDirectory;
  visible.value = true;
  await nextTick();
  if (!dialog.value.open) dialog.value.show();
  await load(login);
}
function close(force = false) {
  if (saving.value) return;
  closeEditor(force === true);
  if (editor.value?.open) return;
  requestId++;
  dialog.value?.close();
  visible.value = false;
}
async function edit(create = false, page = 'profile') {
  if (mobile.value && (create || page === 'groups')) return;
  if (
    saving.value ||
    (!create && !permissions.value.edit) ||
    (create && !permissions.value.manage)
  )
    return;
  creating.value = create;
  mode.value = page;
  editingError.value = '';
  uncertain.value = false;
  confirmClose.value = false;
  avatar.value = null;
  draft.value = create
    ? Object.fromEntries(
        [...profileFields, ...accountFields].map(([key]) => [key, ''])
      )
    : structuredClone(toRaw(result.value.document));
  if (create)
    Object.assign(draft.value, { login: '', password: '', groups: [] });
  draft.value.accessLevels = Object.fromEntries(
    (result.value.groups || []).map((row) => [row.code, row.accessLevel])
  );
  draft.value = EditorState.begin(draft.value);
  original.value = structuredClone(toRaw(draft.value));
  await nextTick();
  editor.value.showModal();
}
function closeEditor(force = false) {
  const decision = EditorState.closeDecision(
    { saving: saving.value, dirty: dirty.value, uncertain: uncertain.value },
    force
  );
  if (decision === 'busy') return;
  if (decision === 'confirm') {
    confirmClose.value = true;
    return;
  }
  mutationId++;
  editor.value?.close();
  if (draft.value) draft.value.password = '';
  draft.value = original.value = avatar.value = null;
  confirmClose.value = false;
}
async function save() {
  if (saving.value || uncertain.value) return;
  const id = ++mutationId,
    ticket = props.ticket,
    project = props.project,
    login = creating.value ? draft.value.login : selected.value;
  const document = structuredClone(toRaw(draft.value));
  if (!permissions.value.manage || creating.value) delete document.accessLevels;
  saving.value = true;
  draft.value = EditorState.submitted(toRaw(draft.value));
  editingError.value = '';
  try {
    const value = await userProfile(
      creating.value ? 'create' : 'save',
      ticket,
      project,
      { login, document, revision: result.value.revision }
    );
    if (id !== mutationId) return;
    result.value = value;
    selected.value = login;
    creating.value = false;
    draft.value = {
      ...value.document,
      accessLevels: document.accessLevels || {}
    };
    original.value = structuredClone(toRaw(draft.value));
    if (avatar.value) {
      const uploaded = await userAvatar(
        ticket,
        project,
        login,
        value.revision,
        avatar.value.token,
        avatar.value.file
      );
      if (id !== mutationId) return;
      result.value = uploaded;
      avatar.value = null;
    }
    const saved = result.value.profile;
    saving.value = false;
    closeEditor(true);
    emit('saved', saved);
    await load(login);
  } catch (failure) {
    if (id === mutationId) {
      uncertain.value = !failure.status || failure.status >= 500;
      fail(failure, true);
    }
  } finally {
    if (id === mutationId || !draft.value) saving.value = false;
  }
}
async function reloadEditor() {
  if (saving.value) return;
  closeEditor(true);
  await load();
  if (result.value) await edit();
}
function changeAvatar(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (file)
    avatar.value = {
      file,
      token: [...crypto.getRandomValues(new Uint8Array(16))]
        .map((value) => value.toString(16).padStart(2, '0'))
        .join('')
    };
}
function activate(name, value) {
  if (saving.value) return;
  close();
  emit(name, value);
}
function beforeUnload(event) {
  if (dirty.value || saving.value || uncertain.value) {
    event.preventDefault();
    event.returnValue = '';
  }
}
watch(
  () => [props.ticket, props.project],
  () => {
    mutationId++;
    saving.value = false;
    close(true);
    result.value = null;
  }
);
window.addEventListener('beforeunload', beforeUnload);
onBeforeUnmount(() => {
  observer?.disconnect();
  requestId++;
  mutationId++;
  window.removeEventListener('beforeunload', beforeUnload);
  if (draft.value) draft.value.password = '';
});
defineExpose({
  open,
  windowContext: () => ({
    route: { args: [selected.value || props.login, directory.value] }
  })
});
</script>
<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'user_profile', type: 'window' }"
      ref="dialog"
      class="user-profile-window"
      :class="{ directory }"
      :aria-label="t(directory ? 'Users' : 'User profile')"
      :aria-busy="busy || relatedBusy"
      @cancel.prevent="close"
    >
      <header>
        <AppIcon name="MDI_ACCOUNT" /><strong>{{
          t(directory ? 'Users' : 'User profile')
        }}</strong
        ><AppButton
          label="Close profile"
          icon="close"
          icon-only
          :disabled="saving"
          @click="close"
        />
      </header>
      <div ref="body" class="user-profile-layout">
        <FrameView
          ref="frame"
          :scene="scene"
          :models="{ users: filteredUsers }"
          :views="views"
          :describe-row="row"
          @event="dispatch"
        />
      </div>
    </dialog>
    <dialog
      v-window="{ kind: 'user_profile_editor', type: 'dialog' }"
      ref="editor"
      class="user-profile-editor"
      :aria-label="
        t(
          creating
            ? 'Add user'
            : mode === 'groups'
              ? 'Edit group membership'
              : 'Edit user profile'
        )
      "
      :aria-busy="saving"
      @cancel.prevent="closeEditor()"
    >
      <header>
        <strong>{{
          t(
            creating
              ? 'Add user'
              : mode === 'groups'
                ? 'Edit group membership'
                : 'Edit user profile'
          )
        }}</strong
        ><AppButton
          icon="close"
          label="Close profile editor"
          icon-only
          :disabled="saving"
          @click="closeEditor()"
        />
      </header>
      <input
        ref="avatarInput"
        hidden
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        :aria-label="t('Choose avatar')"
        @change="changeAvatar"
      />
      <form
        v-if="draft"
        ref="editorBody"
        class="profile-editor-frame"
        @submit.prevent="save"
      >
        <FrameView
          ref="editorFrame"
          :scene="editorScene"
          :models="{ groups: result?.groups || [] }"
          :views="editorViews"
          :describe-row="editorRow"
          @event="editorDispatch"
        />
      </form>
    </dialog>
  </Teleport>
</template>
