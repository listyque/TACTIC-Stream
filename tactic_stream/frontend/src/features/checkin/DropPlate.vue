<script setup>
// DropPlateView.qml / DropPlateController: matching remains native server logic.
import {
  computed,
  inject,
  nextTick,
  onMounted,
  onBeforeUnmount,
  ref,
  shallowRef,
  watch
} from 'vue';
import { resultItems, navigationLink } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppTextField from '../../controls/AppTextField.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/drop_plate.ui.mjs';
import { asyncComponent } from '../../controls/asyncComponent.js';
import { matchingDefaults } from './matchingDefaults.js';
import { copyText } from '../../controls/clipboard.js';
import {
  preferences,
  savePreferencePage
} from '../configuration/preferences.js';
import { prettySize, sourcePath, droppedFiles, prepareFiles } from './files.js';
const props = defineProps({ ticket: String, project: String, target: Object });
const emit = defineEmits(['help', 'queue']);
const queueCheckin = inject('queueCheckin'),
  checkinDescription = inject('checkinDescription', () => '');
const files = ref([]),
  groups = ref([]),
  busy = ref(false),
  error = ref(''),
  filter = ref(''),
  filterMode = ref('name');
const input = ref(null),
  directory = ref(null),
  templatesDialog = ref(null),
  templatesEditor = ref(null),
  templatesError = ref('');
const process = ref('publish'),
  context = ref('publish'),
  processes = ref([]),
  padding = ref(3);
let request = 0,
  targetRequest = 0,
  intakeEpoch = 0;
const owner = ref(null);
const selected = computed(() =>
  groups.value.filter((group) => group.checked && group.status !== 'Queued')
);
const visible = computed(() =>
  groups.value.filter((group) =>
    UI.matches(group, filter.value, filterMode.value)
  )
);
const workspace = ref(null),
  viewport = ref({ width: 1000, height: 700 }),
  fileMenu = ref(null),
  menuAnchor = ref(null),
  menuKey = ref('');
const menuGroup = shallowRef(null);
const frameModel = computed(() => ({
  native: false,
  busy: busy.value,
  count: groups.value.length,
  recursive: preferences.checkin.includeSubfolders,
  groupCheckin: preferences.checkin.groupCheckin,
  keepFileName: preferences.checkin.keepFilename,
  filter: filter.value,
  filterMode: filterMode.value,
  hasTarget: !!owner.value?.searchKey,
  targetTitle: owner.value?.title,
  hasChecked: selected.value.length > 0,
  canQueue: !!queueCheckin,
  processes: processes.value,
  process: process.value,
  context: context.value,
  error: t(error.value)
}));
const scene = computed(() =>
  UI.describe(
    frameModel.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const presentedRows = computed(() =>
  visible.value.map((group) => ({
    ...group,
    groupId: String(group.id),
    size: prettySize(group.size),
    path: group.path || group.files[0]?.name || '',
    error: group.error || ''
  }))
);
const describeRow = (list, record) =>
  UI.row(frameModel.value, record, list.width - 16, appearance.language);
let observer;
onMounted(async () => {
  await nextTick();
  if (!workspace.value) return;
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width > 0)
      viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(workspace.value);
});
function dispatch(action, source) {
  if (action.type === 'files') input.value.click();
  else if (action.type === 'directory') directory.value.click();
  else if (action.type === 'paste') pasteFiles();
  else if (action.type === 'templates') templates();
  else if (action.type === 'clear') clear();
  else if (action.type === 'preference')
    preference(
      {
        recursive: 'includeSubfolders',
        groupCheckin: 'groupCheckin',
        keepFileName: 'keepFilename'
      }[action.field],
      action.value
    );
  else if (action.type === 'filter') filter.value = action.value;
  else if (action.type === 'filterMode') filterMode.value = action.value;
  else if (action.type === 'process')
    context.value = process.value = action.value;
  else if (action.type === 'context') context.value = action.value;
  else if (action.type === 'queue') queue();
  else if (action.type === 'check') {
    const group = groups.value.find((group) => String(group.id) === action.key);
    if (group && !busy.value) group.checked = action.value;
  } else if (action.type === 'remove') {
    const group = groups.value.find((group) => String(group.id) === action.key);
    if (group && !busy.value) remove(group);
  } else if (action.type === 'menu') {
    if (!action.value && fileMenu.value.open && menuKey.value === action.key) {
      fileMenu.value.close(true);
      return;
    }
    menuKey.value = action.key;
    menuGroup.value = groups.value.find(
      (group) => String(group.id) === action.key
    );
    menuAnchor.value = source;
    if (action.value) {
      const bounds = source.getBoundingClientRect();
      fileMenu.value.openAt({
        target: source,
        clientX: bounds.x + action.value.x,
        clientY: bounds.y + action.value.y
      });
    } else fileMenu.value.openAt({ target: source });
  }
}
function menuAction(command) {
  const group = menuGroup.value;
  if (!group || !groups.value.includes(group)) return;
  if (command === 'open') localFile(group);
  else if (command === 'copy') copyText(sourcePath(group.files[0]));
  else if (command === 'copy_all')
    copyText(group.files.map(sourcePath).join('\n'));
  else if (command === 'remove' && !busy.value) remove(group);
}
const scope = computed(() => ({
  ticket: props.ticket,
  project: props.project
}));
const MatchingTemplates = asyncComponent(
  () => import('./MatchingTemplates.vue')
);
const templateItems = ref(structuredClone(matchingDefaults)),
  editingTemplates = ref(false),
  paddingDraft = ref(3);
try {
  const saved = JSON.parse(
    localStorage.getItem('tactic_stream.matching_templates') || 'null'
  );
  if (Array.isArray(saved?.items) && saved.items.length) {
    templateItems.value = saved.items;
    padding.value = saved.padding;
  }
} catch {
  /* Native defaults. */
}
const activePatterns = computed(() =>
  templateItems.value
    .filter(
      (row) =>
        row.enabled &&
        (!row.process || row.process === process.value) &&
        (!row.context || row.context === context.value)
    )
    .map((row) => row.pattern)
);
watch([process, context, () => props.ticket, () => props.project], () => {
  intakeEpoch++;
  if (!props.ticket) {
    request++;
    groups.value = [];
    busy.value = false;
  } else if (files.value.length) rematch(true);
});
watch(
  [
    () => props.ticket,
    () => props.project,
    () => props.target?.searchKey,
    () => props.target?.process,
    () => props.target?.context
  ],
  async () => {
    const id = ++targetRequest;
    intakeEpoch++;
    fileMenu.value?.close();
    menuGroup.value = null;
    processes.value = [];
    process.value = props.target?.process || 'publish';
    context.value = props.target?.context || process.value;
    owner.value = null;
    if (props.target?.project !== props.project || !props.target?.searchKey)
      return;
    try {
      let target = props.target;
      if (target.searchKey.startsWith('sthpw/snapshot?')) {
        const link = await navigationLink(
          props.ticket,
          props.project,
          'skey://' + target.searchKey
        );
        if (!link.parent) return;
        target = {
          ...target,
          searchKey: link.parent.__search_key__,
          title: link.parent.name || link.parent.title || link.parent.code
        };
      }
      if (id !== targetRequest) return;
      owner.value = target;
      const result = await resultItems(
        props.ticket,
        props.project,
        target.searchKey.split('?')[0],
        [target.searchKey]
      );
      if (id === targetRequest)
        processes.value =
          result.items[0]?.branches
            .filter((branch) => branch.kind === 'process')
            .map((branch) => ({
              value: branch.process,
              label: branch.title
            })) || [];
    } catch (failure) {
      if (id === targetRequest) error.value = failure.message;
    }
  },
  { immediate: true }
);
function preference(name, value) {
  try {
    savePreferencePage('checkin', { ...preferences.checkin, [name]: value });
  } catch (failure) {
    error.value = failure.message;
  }
}
async function rematch(keepSelection = false) {
  fileMenu.value?.close();
  menuGroup.value = null;
  const id = ++request;
  error.value = '';
  if (!files.value.length) {
    groups.value = [];
    busy.value = false;
    return;
  }
  busy.value = true;
  const excluded = new Set(
    keepSelection
      ? groups.value
          .filter((group) => !group.checked)
          .flatMap((group) => group.files)
      : []
  );
  try {
    const matched = await prepareFiles(scope.value, files.value, {
      templates: activePatterns.value,
      padding: padding.value
    });
    if (id === request)
      groups.value = matched.map((group, index) => ({
        ...group,
        id: index,
        checked: !group.indices.every((index) =>
          excluded.has(files.value[index])
        ),
        status: 'Matched',
        files: group.indices.map((index) => files.value[index])
      }));
  } catch (failure) {
    if (id === request) error.value = failure.message;
  } finally {
    if (id === request) busy.value = false;
  }
}
async function addFiles(incoming) {
  const known = new Set(files.value.map(sourcePath));
  const additions = [...incoming].filter((file) => {
    const path = sourcePath(file);
    if (
      known.has(path) ||
      (!preferences.checkin.includeSubfolders &&
        file.webkitRelativePath?.split('/').length > 2)
    )
      return false;
    known.add(path);
    return true;
  });
  files.value.push(...additions);
  await rematch();
}
async function drop(event) {
  const epoch = intakeEpoch;
  try {
    const incoming = await droppedFiles(event.dataTransfer);
    if (epoch === intakeEpoch) await addFiles(incoming);
  } catch (failure) {
    if (epoch === intakeEpoch) error.value = failure.message;
  }
}
function remove(group) {
  const removing = new Set(group.files);
  files.value = files.value.filter((file) => !removing.has(file));
  rematch();
}
function clear() {
  intakeEpoch++;
  fileMenu.value?.close();
  menuGroup.value = null;
  request++;
  files.value = [];
  groups.value = [];
  busy.value = false;
  error.value = '';
}
function queue() {
  if (
    !owner.value?.searchKey ||
    !selected.value.length ||
    !context.value.trim() ||
    busy.value
  )
    return;
  try {
    const batches = preferences.checkin.groupCheckin
      ? [selected.value]
      : selected.value.map((group) => [group]);
    for (const batch of batches) {
      const inputs = batch.flatMap((group) => group.files);
      queueCheckin({
        ...scope.value,
        searchKey: owner.value.searchKey,
        title:
          owner.value.title ||
          owner.value.record?.name ||
          owner.value.record?.code,
        process: process.value,
        context: context.value.trim(),
        description: checkinDescription(),
        files: inputs,
        name: inputs[0].name,
        templates: [...activePatterns.value],
        padding: padding.value,
        source: 'Drop Plate',
        keepFileName: preferences.checkin.keepFilename,
        generatePreviews: preferences.checkin.generatePreviews
      });
      const moved = new Set(inputs);
      files.value = files.value.filter((file) => !moved.has(file));
      groups.value = groups.value.filter((group) => !batch.includes(group));
    }
    emit('queue');
  } catch (failure) {
    error.value = failure.message;
  }
}
function completed(job) {
  const finished = new Set(job.completedFiles || []);
  if (job.source === 'Drop Plate') {
    files.value = files.value.filter((file) => !finished.has(file));
    rematch();
  }
}
async function templates() {
  paddingDraft.value = padding.value;
  editingTemplates.value = true;
  await nextTick();
  templatesDialog.value?.show();
}
async function saveTemplates(items) {
  try {
    localStorage.setItem(
      'tactic_stream.matching_templates',
      JSON.stringify({ items, padding: Number(paddingDraft.value) })
    );
    templateItems.value = items;
    padding.value = Number(paddingDraft.value);
    closeTemplates();
    rematch();
  } catch (failure) {
    templatesError.value = failure.message;
  }
}
function closeTemplates() {
  templatesDialog.value.close();
  editingTemplates.value = false;
}
async function pasteFiles() {
  const epoch = intakeEpoch;
  try {
    if (!navigator.clipboard?.read)
      throw new Error(
        'Paste files with Ctrl+V or choose files. Browser access to local paths is unavailable.'
      );
    const inputs = [];
    for (const item of await navigator.clipboard.read())
      for (const type of item.types)
        if (!type.startsWith('text/'))
          inputs.push(
            new File(
              [await item.getType(type)],
              'clipboard.' + type.split('/')[1],
              { type }
            )
          );
    if (!inputs.length)
      throw new Error(
        'Choose files. Browser access to pasted local paths is unavailable.'
      );
    if (epoch === intakeEpoch) await addFiles(inputs);
  } catch (failure) {
    if (epoch === intakeEpoch) error.value = failure.message;
  }
}
function localFile(group) {
  const url = URL.createObjectURL(group.files[0]),
    link = document.createElement('a');
  link.href = url;
  link.download = group.files[0].name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function beforeUnload(event) {
  if (files.value.length) {
    event.preventDefault();
    event.returnValue = '';
  }
}
window.addEventListener('beforeunload', beforeUnload);
onBeforeUnmount(() => {
  intakeEpoch++;
  request++;
  targetRequest++;
  observer?.disconnect();
  window.removeEventListener('beforeunload', beforeUnload);
});
defineExpose({
  completed,
  clear,
  pending: () => files.value.length > 0,
  canLeave: () =>
    !files.value.length || window.confirm(t('Discard files on Drop Plate?'))
});
</script>
<template>
  <Teleport defer to="#dock-drop_plate"
    ><section
      ref="workspace"
      class="drop-plate"
      :aria-label="t('Drop Plate')"
      :aria-busy="busy"
      @dragover.prevent
      @drop.prevent="drop"
      @paste="
        if ($event.clipboardData.files.length) {
          $event.preventDefault();
          addFiles($event.clipboardData.files);
        }
      "
    >
      <FrameView
        :scene="scene"
        :models="{ groups: presentedRows }"
        :describe-row="describeRow"
        @event="dispatch"
      />
      <AppMenu
        ref="fileMenu"
        class="drop-plate-file-menu"
        external-trigger
        overlay
        :anchor="menuAnchor"
        label="File actions"
      >
        <template
          v-for="(action, index) in UI.actions(frameModel)"
          :key="index"
        >
          <hr v-if="action.separator" />
          <AppButton
            v-else
            :label="action.title"
            :icon="action.icon"
            :disabled="action.enabled === false"
            @click="menuAction(action.command)"
          />
        </template>
      </AppMenu>
      <input
        ref="input"
        hidden
        type="file"
        multiple
        @change="
          addFiles($event.target.files);
          $event.target.value = '';
        "
      /><input
        ref="directory"
        hidden
        type="file"
        multiple
        webkitdirectory
        @change="
          addFiles($event.target.files);
          $event.target.value = '';
        "
      /></section
  ></Teleport>
  <Teleport to="body"
    ><dialog
      v-window="{ kind: 'matching_templates', type: 'window' }"
      ref="templatesDialog"
      class="record-dialog drop-plate-templates"
      :aria-label="t('Matching Templates')"
      @cancel.prevent="templatesEditor?.close()"
    >
      <header>
        <h2>{{ t('Matching Templates') }}</h2>
        <AppButton
          label="Close"
          icon="close"
          @click="templatesEditor?.close()"
        />
      </header>
      <label
        >{{ t('Frame padding')
        }}<AppTextField
          v-model.number="paddingDraft"
          type="number"
          min="1"
          max="9"
          label="Frame padding" /></label
      ><MatchingTemplates
        v-if="editingTemplates"
        ref="templatesEditor"
        :scope="scope"
        :processes="processes"
        :context="context"
        :items="templateItems"
        :padding="Number(paddingDraft)"
        @save="saveTemplates"
        @close="closeTemplates"
      />
      <p v-if="templatesError" class="error" role="alert">
        {{ t(templatesError) }}
      </p>
    </dialog></Teleport
  >
</template>
<style>
.drop-plate {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.drop-plate-templates {
  width: min(1000px, calc(100dvw - 24px));
  height: min(700px, 85dvh);
}
.drop-plate-templates[open] {
  display: flex;
  flex-direction: column;
}
.drop-plate-templates > header,
.drop-plate-templates > label {
  flex: none;
}
.drop-plate-templates > label {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}
</style>
