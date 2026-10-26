<script setup>
// ConfigurationView.qml / ConfigurationController (EPL-1.0): Reset/Apply current page; Save all; guarded Close.
import {
  computed,
  nextTick,
  onActivated,
  onMounted,
  onBeforeUnmount,
  onDeactivated,
  reactive,
  ref,
  watch
} from 'vue';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/configuration.ui.mjs';
import AppSelect from '../../controls/AppSelect.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppButton from '../../controls/AppButton.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import SettingRow from '../../controls/SettingRow.vue';
import {
  appearance,
  saveAppearance,
  effectiveColorMode,
  themes,
  languages,
  iconSets,
  colorModes
} from '../../appearance.js';
import ServerConfiguration from './ServerConfiguration.vue';
import { debugSettings } from '../debug/debugLog.js';
import {
  networkSettings,
  updateIntervals,
  updateModes,
  updateBatchDelays
} from '../connection/networkSettings.js';
import {
  preferences,
  normalizePreferences,
  savePreferencePage,
  configurationPreview
} from './preferences.js';
import ProjectSettings from './ProjectSettings.vue';
import RepositorySettings from './RepositorySettings.vue';
import RepositoryEditor from './RepositoryEditor.vue';
import FrameSettings from './FrameSettings.vue';
import { resultViews } from '../workspace/resultViews.js';
const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  canAdminister: Boolean,
  openProject: Function,
  reloadCache: Function
});
const emit = defineEmits(['session-expired', 'close', 'help', 'providers']);
const groups = {
  server: [
    'Services and workers',
    'Network',
    'Database',
    'Security',
    'Directories and logs'
  ],
  repository: ['File repository'],
  tasks: ['Task scheduling']
};
const pages = UI.pages.map((page) => ({ ...page, groups: groups[page.id] }));
const host = ref(null),
  viewport = ref({ width: 1100, height: 700 });
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
const scene = computed(() =>
  UI.describe(
    {
      product: 'TACTIC STREAM',
      page: page.value,
      pages,
      dirty: dirty.value,
      currentDirty: pageDirty(page.value),
      dirtyPages: pages
        .filter((item) => pageDirty(item.id))
        .map((item) => item.id),
      canReset: true,
      busy: busy.value
    },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const pageStyle = computed(() =>
  Object.fromEntries(
    Object.entries(scene.value.pageBounds).map(([key, value]) => [
      key === 'x' ? 'left' : key === 'y' ? 'top' : key,
      value + 'px'
    ])
  )
);
function dispatch(action) {
  if (action.type === 'page') selectPage(action.value);
  else if (action.type === 'reset') reset();
  else if (action.type === 'apply') apply();
  else if (action.type === 'save') apply({ all: true });
  else if (action.type === 'close') cancel();
  else if (action.type === 'help') emit('help', current.value.help);
}

let savedPage;
try {
  savedPage = localStorage.getItem('tactic_stream.configuration.page');
} catch {
  /* Server is the native initial page. */
}
const page = ref(
  pages.some((item) => item.id === savedPage) ? savedPage : 'server'
);
const origin = location.origin;
const current = computed(() => pages.find((item) => item.id === page.value));
const server = ref(null),
  error = ref(''),
  notice = ref(''),
  saving = ref(false),
  clearing = ref(false),
  confirmClose = ref(null),
  confirmClear = ref(null);
const repositoryEditor = ref(null),
  repositories = ref(null);
const cacheScope = ref('server');
const clone = (value) => JSON.parse(JSON.stringify(value));
const drafts = reactive(clone(preferences)),
  networkDraft = reactive(clone(networkSettings)),
  debugDraft = reactive(clone(debugSettings));
const appearanceBaseline = ref(JSON.stringify(appearance)),
  networkBaseline = ref(JSON.stringify(networkSettings)),
  debugBaseline = ref(JSON.stringify(debugSettings)),
  baselines = ref(clone(preferences));
const busy = computed(
  () =>
    saving.value ||
    clearing.value ||
    !!server.value?.loading ||
    !!server.value?.saving
);
function pageDirty(id) {
  if (id === 'appearance')
    return JSON.stringify(appearance) !== appearanceBaseline.value;
  const settingsDirty =
    id in drafts &&
    JSON.stringify(drafts[id]) !== JSON.stringify(baselines.value[id]);
  const groups = pages.find((item) => item.id === id)?.groups || [];
  return (
    settingsDirty ||
    (id === 'server' &&
      JSON.stringify(networkDraft) !== networkBaseline.value) ||
    (id === 'global' && JSON.stringify(debugDraft) !== debugBaseline.value) ||
    (server.value?.configuration?.groups || []).some(
      (group) =>
        groups.includes(group.title) && server.value.groupChanged(group)
    )
  );
}
const dirty = computed(() => pages.some((item) => pageDirty(item.id)));
const serverPages = computed(() =>
  pages.filter((item) => item.groups).map((item) => item.id)
);
const currentGroups = computed(() => current.value.groups || []);
watch(page, async (value) => {
  try {
    localStorage.setItem('tactic_stream.configuration.page', value);
  } catch {
    /* Navigation still works. */
  }
  await nextTick();
  if (
    server.value &&
    currentGroups.value.length &&
    !currentGroups.value.includes(server.value.activeGroup)
  ) {
    server.value.activeGroup = currentGroups.value[0];
    server.value.search = '';
  }
});
const pageValues = computed(() => {
  if (page.value === 'server')
    return {
      serverUrl: origin,
      login: props.login,
      serverUpdateMode: networkDraft.updateMode,
      serverUpdateInterval: networkDraft.pollInterval,
      serverUpdateBatchDelay: networkDraft.batchDelay
    };
  if (page.value === 'appearance')
    return {
      ...appearance,
      darkTheme: effectiveColorMode.value === 'dark',
      themeStyle: appearance.theme,
      lightAccent: appearance.themeAccents[appearance.theme].light,
      darkAccent: appearance.themeAccents[appearance.theme].dark
    };
  const values = { ...drafts[page.value] };
  if (page.value === 'global')
    for (const level of [
      'LOG',
      'INFO',
      'WARNING',
      'MISSING',
      'EXCEPTION',
      'ERROR',
      'CRITICAL',
      'API'
    ])
      values['debug_' + level] = debugDraft.recordingLevels.includes(level);
  return values;
});
const pageOptions = computed(() => ({
  themeStyle: themes,
  language: languages,
  iconSet: iconSets,
  mode: colorModes,
  defaultViewMode: resultViews,
  viewMode: [
    { value: 'table', label: 'Table' },
    { value: 'gantt', label: 'Gantt' }
  ],
  sortMode: [
    'due',
    'recent',
    'process',
    'user',
    'status',
    'object',
    'search_type',
    'project',
    'priority',
    'milestone',
    'supervisor'
  ].map((value) => ({
    value,
    label:
      {
        due: 'Deadline',
        recent: 'Recently changed',
        user: 'Assignee',
        search_type: 'Search Type'
      }[value] || value[0].toUpperCase() + value.slice(1)
  })),
  groupMode: ['none', 'process', 'user', 'status', 'object'].map((value) => ({
    value,
    label:
      { none: 'No grouping', user: 'Assignee' }[value] ||
      value[0].toUpperCase() + value.slice(1)
  })),
  serverUpdateMode: updateModes,
  serverUpdateInterval: updateIntervals,
  serverUpdateBatchDelay: updateBatchDelays
}));
function editField({ field, value }) {
  if (page.value === 'server')
    networkDraft[
      {
        serverUpdateMode: 'updateMode',
        serverUpdateInterval: 'pollInterval',
        serverUpdateBatchDelay: 'batchDelay'
      }[field]
    ] = value;
  else if (page.value === 'appearance') {
    if (field === 'darkTheme') appearance.mode = value ? 'dark' : 'light';
    else if (field === 'themeStyle') appearance.theme = value;
    else if (['lightAccent', 'darkAccent'].includes(field))
      appearance.themeAccents[appearance.theme][
        field === 'lightAccent' ? 'light' : 'dark'
      ] = value;
    else appearance[field] = value;
  } else if (field.startsWith('debug_')) {
    const level = field.slice(6);
    debugDraft.recordingLevels = value
      ? [...new Set([...debugDraft.recordingLevels, level])]
      : debugDraft.recordingLevels.filter((item) => item !== level);
  } else drafts[page.value][field] = value;
}
function settingsAction(action) {
  if (action.type === 'providers') emit('providers');
  if (action.type === 'clearTabs' || action.type === 'clearData') {
    cacheScope.value = action.type === 'clearTabs' ? 'tabs' : 'server';
    confirmClear.value.showModal();
  }
}
function selectPage(value) {
  error.value = '';
  notice.value = '';
  page.value = value;
}
function begin() {
  configurationPreview.value = true;
  appearanceBaseline.value = JSON.stringify(appearance);
  networkBaseline.value = JSON.stringify(networkSettings);
  debugBaseline.value = JSON.stringify(debugSettings);
  baselines.value = clone(preferences);
  Object.assign(drafts, clone(preferences));
  Object.assign(networkDraft, clone(networkSettings));
  Object.assign(debugDraft, clone(debugSettings));
  error.value = '';
  notice.value = '';
  if (server.value && !server.value.hasChanges) server.value.load();
  repositories.value?.load();
  nextTick(() => {
    if (server.value && currentGroups.value.length)
      server.value.activeGroup = currentGroups.value[0];
  });
}
function restore(id) {
  if (id === 'appearance')
    Object.assign(appearance, JSON.parse(appearanceBaseline.value));
  if (id in drafts) drafts[id] = clone(baselines.value[id]);
  if (id === 'server')
    Object.assign(networkDraft, JSON.parse(networkBaseline.value));
  if (id === 'global')
    Object.assign(debugDraft, JSON.parse(debugBaseline.value));
  const groups = pages.find((item) => item.id === id)?.groups;
  if (groups && server.value?.configuration) server.value.resetDraft(groups);
}
function reset() {
  if (busy.value) return;
  restore(page.value);
  error.value = '';
  notice.value = '';
  if (page.value === 'repository') repositories.value?.load();
}
function closeRepository() {
  repositoryEditor.value.close();
  repositories.value?.load();
}
function discard() {
  if (busy.value) return;
  for (const item of pages) restore(item.id);
  confirmClose.value?.close();
  emit('close');
}
function cancel() {
  if (busy.value) return;
  if (dirty.value) confirmClose.value.showModal();
  else emit('close');
}
function persist(entries) {
  const previous = entries.map(([key]) => [key, localStorage.getItem(key)]);
  try {
    for (const [key, value] of entries)
      localStorage.setItem(key, JSON.stringify(value));
  } catch (failure) {
    for (const [key, value] of previous) {
      try {
        if (value === null) localStorage.removeItem(key);
        else localStorage.setItem(key, value);
      } catch {
        /* Keep drafts and report unavailable storage. */
      }
    }
    throw failure;
  }
}
async function applyPage(id) {
  const definition = pages.find((item) => item.id === id);
  if (
    id === 'checkin' &&
    (!Number.isInteger(drafts.checkin.displayLimit) ||
      drafts.checkin.displayLimit < 1 ||
      drafts.checkin.displayLimit > 500)
  ) {
    page.value = id;
    error.value = 'Result limit must be an integer from 1 to 500.';
    return false;
  }
  if (
    id === 'tasks' &&
    drafts.tasks.columns.some(
      (column) =>
        !Number.isInteger(column.width) ||
        column.width < 40 ||
        column.width > 480
    )
  ) {
    page.value = id;
    error.value = 'Column width must be an integer from 40 to 480.';
    return false;
  }
  if (
    id === 'repository' &&
    (!drafts.repository.defaultAlias ||
      (drafts.repository.enabledAliases &&
        !drafts.repository.enabledAliases.includes(
          drafts.repository.defaultAlias
        )))
  ) {
    page.value = id;
    error.value = 'Enable at least one repository and choose its default.';
    return false;
  }
  if (id === 'repository') {
    try {
      const aliases = ['asset_base_dir', 'base_dir_alias'].flatMap((key) => {
        const raw = server.value?.draft['checkin/' + key] || '';
        return raw.startsWith('{') ? Object.keys(JSON.parse(raw)) : ['default'];
      });
      if (!aliases.includes(drafts.repository.defaultAlias)) throw new Error();
    } catch {
      page.value = id;
      error.value = 'Enable at least one repository and choose its default.';
      return false;
    }
  }
  if (
    definition.groups &&
    server.value?.hasChanges &&
    !(await server.value.save(definition.groups))
  ) {
    page.value =
      pages.find((item) => item.groups?.includes(server.value.activeGroup))
        ?.id || id;
    if (page.value === 'repository') {
      await nextTick();
      if (!repositoryEditor.value.open) repositoryEditor.value.show();
    }
    return false;
  }
  try {
    if (id === 'appearance') {
      saveAppearance();
      appearanceBaseline.value = JSON.stringify(appearance);
    }
    if (id === 'server') {
      persist([['tactic_stream.network', networkDraft]]);
      Object.assign(networkSettings, clone(networkDraft));
      networkBaseline.value = JSON.stringify(networkDraft);
    }
    if (id === 'global') {
      const next = normalizePreferences({
        ...preferences,
        global: drafts.global
      });
      persist([
        ['tactic_stream.preferences', next],
        ['tactic_stream.debug_log', debugDraft]
      ]);
      Object.assign(preferences.global, next.global);
      Object.assign(debugSettings, clone(debugDraft));
      debugBaseline.value = JSON.stringify(debugDraft);
      baselines.value.global = clone(drafts.global);
    } else if (id in drafts) {
      savePreferencePage(id, drafts[id]);
      drafts[id] = clone(preferences[id]);
      baselines.value[id] = clone(preferences[id]);
    }
    if (id === 'repository') await repositories.value?.load();
    return true;
  } catch {
    page.value = id;
    error.value =
      'Browser settings could not be saved. Check browser storage permissions and free space.';
    return false;
  }
}
async function apply({ all = false, close = false } = {}) {
  if (busy.value) return;
  error.value = '';
  notice.value = '';
  saving.value = true;
  try {
    for (const id of all ? pages.map((item) => item.id) : [page.value])
      if (!(await applyPage(id))) return;
    notice.value = server.value?.configuration?.restart_required
      ? 'Saved to XML. Restart the backend to apply these settings.'
      : 'Configuration applied';
    if (close) {
      confirmClose.value?.close();
      emit('close');
    }
  } finally {
    saving.value = false;
  }
}
async function applyRepository() {
  if (busy.value) return;
  saving.value = true;
  try {
    if (await applyPage('repository')) notice.value = 'Configuration applied';
  } finally {
    saving.value = false;
  }
}
async function clearCache() {
  confirmClear.value.close();
  clearing.value = true;
  error.value = '';
  notice.value = '';
  try {
    if ((await props.reloadCache(cacheScope.value)) === false)
      throw new Error();
    notice.value =
      cacheScope.value === 'tabs' ? 'Tabs cache cleared' : 'Cache reloaded';
  } catch {
    error.value = 'Cached server data could not be refreshed.';
  } finally {
    clearing.value = false;
  }
}
const confirmationWidth = computed(() =>
  Math.max(1, Math.min(430, viewport.value.width - 32))
);
const closeScene = computed(() =>
  UI.confirmation(
    { kind: 'close', busy: busy.value },
    confirmationWidth.value,
    248,
    appearance.language
  )
);
const clearScene = computed(() =>
  UI.confirmation(
    { kind: 'clear', scope: cacheScope.value, busy: busy.value },
    confirmationWidth.value,
    220,
    appearance.language
  )
);
function confirmationAction(action) {
  confirmClose.value.close();
  if (action.type === 'discard') discard();
  else if (action.type === 'save') apply({ all: true, close: true });
}
function beforeUnload(event) {
  if (dirty.value || busy.value) {
    event.preventDefault();
    event.returnValue = '';
  }
}
onActivated(() => {
  begin();
  window.addEventListener('beforeunload', beforeUnload);
});
onDeactivated(() => {
  Object.assign(appearance, JSON.parse(appearanceBaseline.value));
  configurationPreview.value = false;
  window.removeEventListener('beforeunload', beforeUnload);
});
onBeforeUnmount(() => {
  Object.assign(appearance, JSON.parse(appearanceBaseline.value));
  configurationPreview.value = false;
  window.removeEventListener('beforeunload', beforeUnload);
});
defineExpose({ cancel, dirty });
</script>
<template>
  <div
    ref="host"
    class="configuration configuration-native configuration-frame"
    :aria-busy="busy"
  >
    <span id="configuration-title" hidden>{{ t('Configuration') }}</span>
    <FrameView :scene="scene" @event="dispatch" />
    <div class="configuration-pages" :style="pageStyle">
      <p v-if="error" class="error configuration-feedback" role="alert">
        {{ t(error) }}
      </p>
      <p v-if="notice" class="notice configuration-feedback" role="status">
        {{ t(notice) }}
      </p>
      <FrameSettings
        v-if="
          [
            'ai',
            'server',
            'appearance',
            'checkin',
            'global',
            'cache',
            'tasks'
          ].includes(page)
        "
        :page="page"
        :values="pageValues"
        :options="pageOptions"
        :busy="busy"
        :natural="['server', 'tasks'].includes(page) && canAdminister"
        @field="editField"
        @columns="drafts.tasks.columns = $event"
        @action="settingsAction"
      />
      <ProjectSettings
        v-if="page === 'project'"
        :ticket="ticket"
        :project="project"
        :can-administer="canAdminister"
        :open-project="openProject"
        @help="emit('help', $event)"
      />
      <RepositorySettings
        v-if="page === 'repository' && canAdminister"
        ref="repositories"
        :ticket="ticket"
        :busy="busy"
        @edit="repositoryEditor.show()"
        @session-expired="emit('session-expired')"
      />
      <section
        v-if="
          canAdminister &&
          ['server', 'tasks'].includes(page) &&
          server?.configuration
        "
        class="configuration-server-tools"
      >
        <AppSelect
          v-model="server.activeGroup"
          :options="
            currentGroups.map((title) => ({ value: title, label: title }))
          "
          label="Server settings section"
        /><AppSearchField
          v-model="server.search"
          label="Find a setting"
          placeholder="Find a setting…"
        />
      </section>
      <Teleport
        defer
        to="#configuration-repository-editor-body"
        :disabled="page !== 'repository'"
        ><ServerConfiguration
          v-if="canAdminister"
          ref="server"
          v-show="serverPages.includes(page)"
          :group-titles="currentGroups"
          :ticket="ticket"
          show-details
          @session-expired="emit('session-expired')"
      /></Teleport>
      <p
        v-if="!canAdminister && page === 'repository'"
        class="muted configuration-feedback"
      >
        {{ t('Repository configuration requires administrator access.') }}
      </p>
    </div>
    <dialog
      ref="repositoryEditor"
      v-window="{ type: 'window' }"
      class="record-dialog configuration-repository-editor"
      :aria-label="t('Repository Editor')"
    >
      <RepositoryEditor
        :server="server"
        :draft="drafts.repository"
        :repositories="repositories?.records || []"
        :busy="busy || repositories?.checking"
        :dirty="pageDirty('repository')"
        @check="repositories.load('check', $event)"
        @close="closeRepository"
        @reset="restore('repository')"
        @save="applyRepository"
        ><div id="configuration-repository-editor-body"
      /></RepositoryEditor>
    </dialog>
    <dialog
      ref="confirmClose"
      class="record-dialog configuration-confirmation"
      :style="{ width: confirmationWidth + 'px' }"
      :aria-label="t('Unsaved changes')"
    >
      <header>
        <h2>{{ t('Unsaved changes') }}</h2>
      </header>
      <FrameView
        :scene="closeScene"
        style="height: 248px"
        @event="confirmationAction"
      />
    </dialog>
    <dialog
      ref="confirmClear"
      class="record-dialog configuration-confirmation"
      :style="{ width: confirmationWidth + 'px' }"
      :aria-label="
        t(
          cacheScope === 'tabs'
            ? 'Clear saved branch expansion?'
            : 'Clear cached server data?'
        )
      "
    >
      <header>
        <h2>
          {{
            t(
              cacheScope === 'tabs'
                ? 'Clear saved branch expansion?'
                : 'Clear cached server data?'
            )
          }}
        </h2>
      </header>
      <FrameView
        :scene="clearScene"
        style="height: 220px"
        @event="$event.type === 'accept' ? clearCache() : confirmClear.close()"
      />
    </dialog>
  </div>
</template>
<style>
.configuration-confirmation {
  padding: 0;
  border: 0;
  overflow: hidden;
}
.configuration-confirmation > header {
  padding: 20px 20px 0;
  margin: 0;
}
.configuration-confirmation > .frame-view {
  flex: none;
}
.configuration-frame {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.configuration-frame > .frame-view {
  position: absolute;
  inset: 0;
}
.configuration-frame > .configuration-pages {
  position: absolute;
  box-sizing: border-box;
  min-height: 0;
  min-width: 0;
}
.configuration-native {
  --configuration-navigation-width: 216px;
  --configuration-header-height: 76px;
}
.configuration-native > .configuration-header {
  min-height: 77px;
}
.configuration-native .configuration-brand h2 {
  font-size: 17px;
  font-weight: 600;
}
.configuration-native .configuration-navigation {
  padding-top: 16px;
}
.configuration-native .configuration-navigation > button {
  min-height: 48px;
  font-size: 13px;
  padding: 0 16px;
}
.configuration-native .configuration-navigation .app-icon {
  width: 16px;
  height: 16px;
  font-size: 16px;
}
.configuration-native
  .configuration-navigation
  > button[aria-pressed='true']::before {
  top: 12px;
  bottom: 12px;
}
.configuration-native .configuration-pages {
  overflow: auto;
  scrollbar-gutter: stable;
  display: flex;
  flex-direction: column;
}
.configuration-pages > .frame-settings {
  flex: 1;
}
.configuration-pages > .frame-settings-natural {
  flex: none;
}
.configuration-native .content {
  padding: 20px 22px;
  gap: 14px;
  overflow: visible;
  height: auto;
  flex: none;
}
.configuration-native .configuration-pages > .content + .content {
  padding-top: 0;
}
.configuration-native .configuration-pages .settings-section > header {
  margin-bottom: 0;
}
.configuration-native .settings-section > header h2 {
  font-size: 14px;
}
.configuration-native .configuration-group {
  padding: 16px;
}
.configuration-native .settings-row {
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 20px;
  padding: 10px 4px;
}
.configuration-native .settings-row.appearance-palette-row {
  grid-template-columns: minmax(0, 1fr) min(380px, 48%);
}
.configuration-native .setting-description {
  gap: 3px;
}
.configuration-native .settings-row {
  line-height: normal;
}
.configuration-native .setting-description p {
  line-height: normal;
}
.configuration-native .setting-description p {
  font-size: var(--text-caption);
}
.configuration-native .setting-description strong,
.configuration-native h1,
.configuration-native h2 {
  font-weight: 600;
}
.configuration-native .setting-control {
  justify-items: end;
}
.configuration-server-tools {
  display: flex;
  gap: 8px;
  padding: 0 22px;
}
.configuration-server-tools > .app-select {
  width: 250px;
}
.configuration-server-tools > .app-search-field {
  flex: 1;
}
.configuration-feedback {
  margin: 14px 22px;
}
.configuration-repository-editor {
  padding: 0;
  overflow: hidden;
  height: min(800px, calc(100dvh - 32px));
  width: 1100px;
  max-width: calc(100vw - 32px);
}
.configuration-repository-editor .content {
  padding: 16px 0;
}
.configuration-repository-editor > header > div {
  flex: 1;
}
@media (max-width: 960px) {
  .configuration-native .configuration-actions > .app-button:not(.icon-button) {
    width: var(--control-height);
    height: var(--control-height);
    padding: 0;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .configuration-native
    .configuration-actions
    > .app-button:not(.icon-button)
    > span:not(.app-icon) {
    display: none;
  }
}
@container (max-width:560px) {
  .configuration-native .settings-row {
    grid-template-columns: minmax(0, 1fr);
  }
  .configuration-native .setting-control {
    justify-items: stretch;
  }
  .configuration-native .configuration-server-tools {
    flex-wrap: wrap;
  }
}
</style>
