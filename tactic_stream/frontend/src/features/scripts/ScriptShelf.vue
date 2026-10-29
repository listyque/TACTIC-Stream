<script setup>
// Current Handler ScriptShelfBar.qml / ScriptShelfEditorView.qml and script_shelf.py (EPL-1.0).
import { inject, ref, computed, watch, onBeforeUnmount } from 'vue';
import { scriptShelf, rpc, beginActivity, endActivity } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ScriptShelfEditor from './ScriptShelfEditor.vue';
import ScriptShelfBar from './ScriptShelfBar.vue';
import { permissions } from '../../../../src/tactic_stream/shared_ui/features/scripts/shelf.ui.mjs';
import { scriptRuntime } from '../../../../src/tactic_stream/shared_ui/features/scripts/bar.ui.mjs';
import { appearance } from '../../appearance.js';
import {
  effectiveShelf,
  globalShelf,
  buttonId,
  runBrowserScript
} from './scriptShelf.js';
import './scriptShelf.css';

const openHelp = inject('openHelp');
const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  entryKey: String,
  preset: String,
  title: String,
  visible: Boolean,
  searchType: String,
  searchKeys: Array,
  updates: Object
});
const emit = defineEmits(['saved', 'executed', 'closed']);
const dialog = ref(null),
  confirmation = ref(null),
  outputDialog = ref(null);
const catalog = ref(null),
  busy = ref(false),
  error = ref(''),
  uncertain = ref(false),
  running = ref(''),
  output = ref(''),
  outputLanguage = ref('');
const outputRuntime = computed(
  () => scriptRuntime(outputLanguage.value, appearance.language).label
);
const mode = ref('shared'),
  modeSelected = ref(false),
  owner = ref('personal'),
  scope = ref('global'),
  selected = ref('');
const title = ref(''),
  buttons = ref([]),
  baseline = ref(''),
  confirmAction = ref(''),
  pending = ref(null);
const editorScope = ref(null);
const editorEpoch = ref(0);
const contextChanged = computed(
  () =>
    !!editorScope.value &&
    (editorScope.value.ticket !== props.ticket ||
      editorScope.value.project !== props.project)
);
const editorEntryKey = computed(() => editorScope.value?.entryKey || '');
let generation = 0,
  reloadPending = false;
const shelves = computed(() => catalog.value?.shelves || []);
const scripts = computed(() => catalog.value?.scripts || []);
const presets = computed(() =>
  shelves.value
    .filter((row) => !row.personal && row.view !== globalShelf)
    .sort((a, b) => a.title.localeCompare(b.title))
);
const effective = computed(() =>
  effectiveShelf(shelves.value, mode.value, props.entryKey, props.preset)
);
const current = computed(() =>
  shelves.value.find((row) => row.code === selected.value)
);
const canRename = computed(
  () => owner.value === 'shared' && scope.value === 'tab'
);
const canRemove = computed(
  () =>
    !!current.value &&
    (owner.value === 'personal' || current.value.view !== globalShelf)
);
const draft = computed(() => ({
  mode: owner.value,
  title: title.value,
  configuration: {
    scope:
      owner.value === 'shared' && scope.value === 'tab'
        ? 'preset'
        : scope.value,
    entryKey:
      owner.value === 'personal' && scope.value === 'tab'
        ? editorEntryKey.value
        : '',
    buttons: buttons.value
  }
}));
const dirty = computed(() => JSON.stringify(draft.value) !== baseline.value);
const assignmentPending = computed(
  () =>
    canRename.value &&
    !!current.value &&
    !!editorEntryKey.value &&
    editorScope.value?.preset !== current.value.view
);
const ready = computed(
  () =>
    !!catalog.value &&
    (owner.value === 'personal' ||
      scope.value === 'global' ||
      !!selected.value ||
      !!title.value)
);
const removeName = computed(() => current.value?.title || title.value);
const deleteTitle = computed(() =>
  t(owner.value === 'personal' ? 'Remove “{name}”?' : 'Delete “{name}”?', {
    name: removeName.value
  })
);
function modeKey() {
  return 'tactic_stream.script_shelf.' + props.login;
}
function setMode(value) {
  mode.value = value;
  modeSelected.value = true;
  try {
    localStorage.setItem(modeKey(), value);
  } catch {}
}
function script(path) {
  return scripts.value.find((row) => row.path === path);
}
function runnable(button) {
  return !!script(button.script)?.executable;
}
async function load() {
  reloadPending = false;
  const id = ++generation;
  busy.value = true;
  error.value = '';
  try {
    const result = await scriptShelf('read', props.ticket, props.project);
    if (id !== generation) return;
    catalog.value = result;
    uncertain.value = false;
    if (!modeSelected.value)
      mode.value = effectiveShelf(result.shelves, 'personal', props.entryKey)
        ?.configuration
        ? 'personal'
        : 'shared';
  } catch (exception) {
    if (id === generation) error.value = exception.message;
  } finally {
    if (id === generation) busy.value = false;
  }
}
watch(
  () => [props.ticket, props.project, props.login],
  () => {
    generation++;
    catalog.value = null;
    error.value = '';
    busy.value = false;
    running.value = '';
    modeSelected.value = false;
    let saved;
    try {
      saved = localStorage.getItem(modeKey());
    } catch {}
    if (['personal', 'shared'].includes(saved)) {
      mode.value = saved;
      modeSelected.value = true;
    }
    if (props.visible && props.ticket) load();
  },
  { immediate: true }
);
watch(
  () => props.visible,
  (value) => {
    if (value && !catalog.value && props.ticket) load();
  }
);
function refreshUpdates() {
  if (
    reloadPending &&
    !busy.value &&
    !running.value &&
    (props.visible || dialog.value?.open) &&
    (!dialog.value?.open || !dirty.value)
  ) {
    if (dialog.value?.open) refresh();
    else load();
  }
}
watch(
  () => props.updates,
  (batch) => {
    if (
      [...(batch?.cacheChanges || []), ...(batch?.cacheRetired || [])].some(
        (row) =>
          row.projectCode === props.project &&
          ['config/widget_config', 'config/custom_script'].includes(
            row.searchType
          )
      )
    ) {
      reloadPending = true;
      refreshUpdates();
    }
  }
);
watch([() => props.visible, busy, running, dirty], refreshUpdates);
onBeforeUnmount(() => {
  generation++;
});
function selectNow(target) {
  editorEpoch.value++;
  if (contextChanged.value) {
    error.value =
      'Connection context changed. Close this form and reopen it before saving.';
    return;
  }
  if (editorScope.value && catalog.value)
    editorScope.value.revision = catalog.value.revision;
  owner.value = target.owner;
  scope.value = target.scope;
  selected.value = target.code || '';
  error.value = '';
  let row = target.code
    ? shelves.value.find((row) => row.code === target.code)
    : owner.value === 'personal'
      ? shelves.value.find(
          (row) =>
            row.personal &&
            row.configuration?.scope === scope.value &&
            (scope.value === 'global' ||
              row.configuration.entryKey === editorEntryKey.value)
        )
      : scope.value === 'global'
        ? shelves.value.find((row) => !row.personal && row.view === globalShelf)
        : null;
  selected.value = row?.code || '';
  title.value =
    row?.title ||
    (owner.value === 'personal'
      ? 'My shelf'
      : scope.value === 'global'
        ? 'Shared shelf'
        : target.new
          ? t('New shelf')
          : '');
  buttons.value = JSON.parse(JSON.stringify(row?.configuration?.buttons || []));
  baseline.value = JSON.stringify(draft.value);
  if (row && !row.valid) error.value = row.error;
}
function select(target) {
  if (busy.value || running.value) return;
  if (dirty.value) {
    pending.value = target;
    confirm('select');
  } else selectNow(target);
}
async function open() {
  if (dialog.value.open) {
    dialog.value.show();
    if (!contextChanged.value && !catalog.value) await load();
    return;
  }
  editorScope.value = {
    ticket: props.ticket,
    project: props.project,
    entryKey: props.entryKey,
    preset: props.preset,
    title: props.title
  };
  dialog.value.show();
  confirmAction.value = '';
  baseline.value = '';
  if (!catalog.value || reloadPending) await load();
  if (!catalog.value) return;
  const row = effective.value;
  selectNow({
    owner:
      mode.value === 'shared' && catalog.value.canManage
        ? 'shared'
        : 'personal',
    scope:
      row?.configuration?.scope === 'global'
        ? 'global'
        : props.entryKey
          ? 'tab'
          : 'global',
    code: mode.value === 'shared' && !catalog.value.canManage ? '' : row?.code
  });
}
function close() {
  if (busy.value || running.value) return;
  if (dirty.value && editorScope.value) confirm('close');
  else {
    dialog.value.close();
    emit('closed');
  }
}
function canLeave() {
  if (!dialog.value?.open) return true;
  if (busy.value || running.value) return false;
  if (dirty.value && editorScope.value) {
    confirm('close');
    return false;
  }
  return true;
}
function confirm(action) {
  confirmAction.value = action;
  confirmation.value.showModal();
}
function accept() {
  const action = confirmAction.value;
  confirmation.value.close();
  confirmAction.value = '';
  if (action === 'delete') return write('delete');
  if (action === 'close') {
    dialog.value.close();
    emit('closed');
  }
  if (action === 'select') selectNow(pending.value);
  if (action === 'reload') refresh();
}
function add() {
  const first = scripts.value.find((row) => row.runnable);
  if (first)
    buttons.value.push({
      id: buttonId(),
      title: first.title,
      description: '',
      icon: 'play-arrow',
      script: first.path
    });
}
function move(index, delta) {
  buttons.value.splice(index + delta, 0, buttons.value.splice(index, 1)[0]);
}
async function refresh() {
  const target = {
    owner: owner.value,
    scope: scope.value,
    code: selected.value
  };
  await load();
  if (catalog.value && !error.value) selectNow(target);
}
async function write(action) {
  if (contextChanged.value) {
    error.value =
      'Connection context changed. Close this form and reopen it before saving.';
    return;
  }
  if (busy.value || running.value || uncertain.value) return;
  busy.value = true;
  error.value = '';
  const id = generation;
  try {
    const values = {
      code: selected.value,
      revision: editorScope.value.revision
    };
    if (action === 'save') Object.assign(values, draft.value);
    if ((action === 'save' && canRename.value) || action === 'assign')
      values.entry_key = editorEntryKey.value;
    const result = await scriptShelf(
      action,
      props.ticket,
      props.project,
      values
    );
    if (id !== generation) return;
    catalog.value = result;
    setMode(owner.value);
    if (action === 'save') selected.value = result.savedCode;
    if (values.entry_key && action !== 'delete')
      editorScope.value.preset =
        result.shelves.find((row) => row.code === selected.value)?.view || '';
    selectNow({
      owner: owner.value,
      scope: scope.value,
      code: action === 'delete' ? '' : selected.value
    });
    emit('saved');
  } catch (exception) {
    if (id === generation) {
      error.value = exception.message;
      uncertain.value = !['invalid_request', 'access_denied'].includes(
        exception.code
      );
    }
  } finally {
    if (id === generation) busy.value = false;
  }
}
async function run(button) {
  if (running.value || busy.value || !runnable(button)) return;
  running.value = button.id;
  outputLanguage.value = script(button.script).language;
  error.value = '';
  const id = generation;
  const context = {
    ticket: props.ticket,
    project: props.project,
    searchType: props.searchType,
    searchKeys: [...(props.searchKeys || [])]
  };
  const activity = beginActivity(context.ticket, 'Running…');
  try {
    let result;
    if (script(button.script).language === 'javascript') {
      const saved = await scriptShelf(
        'script',
        context.ticket,
        context.project,
        { path: button.script }
      );
      if (id !== generation) return;
      result = await runBrowserScript(saved.script, {
        project: context.project,
        searchType: context.searchType,
        searchKeys: context.searchKeys,
        rpc: (method, args = [], kwargs = {}) =>
          rpc(
            method,
            [{ ticket: context.ticket, project: context.project }, ...args],
            kwargs
          ),
        refresh: () => {
          if (id === generation) emit('executed');
        }
      });
    } else
      result = await rpc(
        script(button.script).language === 'server_js'
          ? 'execute_js_script'
          : 'execute_python_script',
        [
          { ticket: context.ticket, project: context.project },
          button.script,
          {}
        ]
      );
    if (id === generation) {
      output.value = JSON.stringify(result, null, 2) ?? 'None';
      outputDialog.value.show();
      emit('executed');
    }
  } catch (exception) {
    if (id === generation) {
      error.value = exception.message;
      output.value = exception.message;
      outputDialog.value.show();
    }
  } finally {
    endActivity(activity);
    if (id === generation) running.value = '';
  }
}
const barButtons = computed(() =>
  (effective.value?.configuration.buttons || []).map((button) => ({
    ...button,
    buttonId: button.id,
    iconName: button.icon,
    language: script(button.script)?.language || '',
    available: runnable(button),
    running: running.value === button.id
  }))
);
function runButton(id) {
  const button = effective.value?.configuration.buttons.find(
    (button) => button.id === id
  );
  if (button) run(button);
}
const frameModel = computed(() => ({
  owner: owner.value,
  scope: scope.value,
  title: title.value,
  canManage: !!catalog.value?.canManage,
  canWrite: !!catalog.value?.canWrite,
  canRename: canRename.value,
  canRemove: canRemove.value,
  removeName: removeName.value,
  canAssign: !!editorEntryKey.value && !!current.value,
  assignmentPending: assignmentPending.value,
  dirty: dirty.value,
  busy: busy.value,
  running: !!running.value,
  contextChanged: contextChanged.value,
  uncertain: uncertain.value,
  ready: ready.value,
  existing: !!current.value,
  hasScripts: scripts.value.some((row) => row.runnable),
  error: error.value,
  notice: contextChanged.value
    ? t(
        'Connection context changed. Close this form and reopen it before saving.'
      )
    : uncertain.value
      ? t('Reload before trying again. Your draft remains open.')
      : catalog.value && !catalog.value.canWrite
        ? t(
            'Saving script shelves currently requires administrator access in the TACTIC core.'
          )
        : '',
  count: buttons.value.length,
  selectedPreset: owner.value === 'personal' ? scope.value : selected.value,
  scopeKey: [
    generation,
    editorEpoch.value,
    editorScope.value?.project,
    owner.value,
    scope.value,
    selected.value
  ].join('/')
}));
const frameButtons = computed(() =>
  buttons.value.map((button) => ({
    ...button,
    buttonId: button.id,
    iconName: button.icon,
    available: runnable(button)
  }))
);
const framePresets = computed(() =>
  owner.value === 'personal'
    ? [
        {
          value: 'tab',
          label: 'Only this tab',
          enabled: !!editorEntryKey.value
        }
      ]
    : presets.value.map((row) => ({
        value: row.code,
        label: row.title,
        translate: false
      }))
);
function frameEvent(action) {
  if (
    action.scopeKey !== undefined &&
    action.scopeKey !== frameModel.value.scopeKey
  )
    return;
  if (
    ['title', 'add', 'button', 'removeButton', 'up', 'down'].includes(
      action.type
    ) &&
    !permissions(frameModel.value).edit
  )
    return;
  if (action.type === 'help') openHelp('script_shelf');
  else if (action.type === 'owner')
    select({ owner: action.value, scope: 'global' });
  else if (action.type === 'global')
    select({ owner: owner.value, scope: 'global' });
  else if (action.type === 'preset')
    select({
      owner: owner.value,
      scope: 'tab',
      code: owner.value === 'shared' ? action.value : ''
    });
  else if (action.type === 'new')
    select({ owner: owner.value, scope: 'tab', new: true });
  else if (action.type === 'title') title.value = action.value;
  else if (action.type === 'assign') write('assign');
  else if (action.type === 'add') add();
  else if (action.type === 'remove') confirm('delete');
  else if (action.type === 'discard')
    selectNow({ owner: owner.value, scope: scope.value, code: selected.value });
  else if (action.type === 'save') write('save');
  else {
    const index = buttons.value.findIndex(
      (button) => button.id === action.buttonId
    );
    if (index < 0) return;
    if (action.type === 'button')
      buttons.value[index][
        action.field === 'iconName' ? 'icon' : action.field
      ] = action.value;
    else if (action.type === 'removeButton') buttons.value.splice(index, 1);
    else if (action.type === 'up' || action.type === 'down')
      move(index, action.type === 'up' ? -1 : 1);
  }
}
defineExpose({
  open,
  reload: load,
  canLeave,
  windowContext: () => {
    if (dirty.value || busy.value)
      throw Error('Apply or discard unsaved changes first');
    return {
      route: {
        shelf: {
          entryKey: props.entryKey,
          preset: props.preset,
          title: props.title
        }
      }
    };
  }
});
</script>

<template>
  <Teleport v-if="visible" defer to="#workspace-script-shelf"
    ><ScriptShelfBar
      :mode="mode"
      :buttons="barButtons"
      :busy="busy"
      :running="running"
      :error="error"
      @mode="setMode"
      @edit="open"
      @run="runButton"
  /></Teleport>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'script_shelf_editor', type: 'window' }"
      ref="dialog"
      class="script-shelf-dialog"
      :aria-label="t('Script Shelf')"
      @cancel.prevent="close"
      @close="refreshUpdates"
    >
      <header class="script-shelf-heading">
        <AppIcon name="code" /><strong>{{ t('Script Shelf') }}</strong
        ><AppButton
          icon-only
          icon="refresh"
          label="Reload shelves"
          :disabled="busy"
          @click="dirty ? confirm('reload') : refresh()"
        /><AppButton
          icon-only
          icon="close"
          label="Close script shelf"
          :disabled="busy || !!running"
          @click="close"
        />
      </header>
      <ScriptShelfEditor
        :model="frameModel"
        :buttons="frameButtons"
        :presets="framePresets"
        :scripts="scripts"
        @event="frameEvent"
      />
    </dialog>
    <dialog
      ref="confirmation"
      class="record-dialog script-shelf-confirm"
      :aria-label="
        confirmAction === 'delete' ? deleteTitle : t('Discard changes?')
      "
    >
      <h2>
        {{ confirmAction === 'delete' ? deleteTitle : t('Discard changes?') }}
      </h2>
      <p>
        {{
          t(
            confirmAction === 'delete'
              ? owner === 'personal'
                ? 'The personal shelf will be removed. Shared shelves will not change.'
                : 'The shared shelf and its sidebar assignments will be deleted. Affected tabs will use the project shelf.'
              : 'Discard unsaved changes to this shelf?'
          )
        }}
      </p>
      <footer>
        <AppButton
          :label="
            confirmAction === 'delete'
              ? owner === 'personal'
                ? 'Remove'
                : 'Delete'
              : 'Discard'
          "
          destructive
          @click="accept"
        /><AppButton label="Cancel" @click="confirmation.close()" />
      </footer>
    </dialog>
    <dialog
      v-window="{ type: 'window' }"
      ref="outputDialog"
      class="record-dialog script-shelf-output"
      :aria-label="t('Script result')"
    >
      <header>
        <h2>
          {{ t('Script result')
          }}<small v-if="outputRuntime"> · {{ outputRuntime }}</small>
        </h2>
        <AppButton label="Close" icon="close" @click="outputDialog.close()" />
      </header>
      <pre tabindex="0">{{ output }}</pre>
    </dialog>
  </Teleport>
</template>
