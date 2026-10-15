<script setup>
// ConfigurationView.qml / ConfigurationController (EPL-1.0): Reset/Apply current page; Save all; guarded Close.
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
import AppMenu from '../../controls/AppMenu.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppButton from '../../controls/AppButton.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import SettingRow from '../../controls/SettingRow.vue'
import { appearance, saveAppearance } from '../../appearance.js'
import AppearanceSettings from './AppearanceSettings.vue'
import ServerConfiguration from './ServerConfiguration.vue'
import DebugSettings from '../debug/DebugSettings.vue'
import { debugSettings } from '../debug/debugLog.js'
import NetworkSettings from './NetworkSettings.vue'
import { networkSettings } from '../connection/networkSettings.js'
import { preferences, normalizePreferences, savePreferencePage, configurationPreview } from './preferences.js'
import PreferenceSettings from './PreferenceSettings.vue'
import ProjectSettings from './ProjectSettings.vue'
import RepositorySettings from './RepositorySettings.vue'
import RepositoryEditor from './RepositoryEditor.vue'
const props = defineProps({ ticket:String, project:String, login:String, canAdminister:Boolean, openProject:Function, reloadCache:Function })
const emit = defineEmits(['session-expired','close','help'])
const pages = [
  { id:'server', title:'Server', icon:'cloud', description:'Connection, sign-in status and server presets', help:'server_configuration', groups:['Services and workers','Network','Database','Security','Directories and logs'] },
  { id:'repository', title:'Repositories', icon:'database', description:'Repository locations, availability and default storage', help:'repository_configuration', groups:['File repository'] },
  { id:'project', title:'Projects', icon:'project-diagram', description:'Active project and workspace context', help:'configuration.projects' },
  { id:'checkin', title:'Check-in Options', icon:'tune', description:'Naming and file handling defaults', help:'configuration.checkin' },
  { id:'global', title:'Global', icon:'settings', description:'Application behavior and diagnostics', help:'configuration.global' },
  { id:'appearance', title:'Appearance', icon:'palette', description:'Themes, animations, language and rendering', help:'appearance' },
  { id:'cache', title:'Cache', icon:'cached', description:'Persistent server data and cache policy', help:'configuration.cache' },
  { id:'tasks', title:'Tasks', icon:'briefcase', description:'Task Browser layout and Notes inspector defaults', help:'configuration.tasks', groups:['Task scheduling'] },
]
let savedPage
try { savedPage = localStorage.getItem('tactic_stream.configuration.page') } catch { /* Server is the native initial page. */ }
const page = ref(pages.some(item => item.id === savedPage) ? savedPage : 'server')
const origin = location.origin
const current = computed(() => pages.find(item => item.id === page.value))
const server = ref(null), error = ref(''), notice = ref(''), saving = ref(false), clearing = ref(false), confirmClose = ref(null), confirmClear = ref(null)
const repositoryEditor = ref(null), repositories = ref(null)
const cacheScope = ref('server')
const clone = value => JSON.parse(JSON.stringify(value))
const drafts = reactive(clone(preferences)), networkDraft = reactive(clone(networkSettings)), debugDraft = reactive(clone(debugSettings))
const appearanceBaseline = ref(JSON.stringify(appearance)), networkBaseline = ref(JSON.stringify(networkSettings)), debugBaseline = ref(JSON.stringify(debugSettings)), baselines = ref(clone(preferences))
const busy = computed(() => saving.value || clearing.value || !!server.value?.loading || !!server.value?.saving)
function pageDirty(id) {
  if (id === 'appearance') return JSON.stringify(appearance) !== appearanceBaseline.value
  const settingsDirty = id in drafts && JSON.stringify(drafts[id]) !== JSON.stringify(baselines.value[id])
  const groups = pages.find(item => item.id === id)?.groups || []
  return settingsDirty || id === 'server' && JSON.stringify(networkDraft) !== networkBaseline.value || id === 'global' && JSON.stringify(debugDraft) !== debugBaseline.value || (server.value?.configuration?.groups || []).some(group => groups.includes(group.title) && server.value.groupChanged(group))
}
const dirty = computed(() => pages.some(item => pageDirty(item.id)))
const serverPages = computed(() => pages.filter(item => item.groups).map(item => item.id))
const currentGroups = computed(() => current.value.groups || [])
watch(page, async value => {
  try { localStorage.setItem('tactic_stream.configuration.page',value) } catch { /* Navigation still works. */ }
  await nextTick()
  if (server.value && currentGroups.value.length && !currentGroups.value.includes(server.value.activeGroup)) { server.value.activeGroup = currentGroups.value[0]; server.value.search = '' }
})
function selectPage(value) { error.value = ''; notice.value = ''; page.value = value }
function begin() {
  configurationPreview.value = true
  appearanceBaseline.value = JSON.stringify(appearance); networkBaseline.value = JSON.stringify(networkSettings); debugBaseline.value = JSON.stringify(debugSettings)
  baselines.value = clone(preferences); Object.assign(drafts,clone(preferences)); Object.assign(networkDraft,clone(networkSettings)); Object.assign(debugDraft,clone(debugSettings)); error.value = ''; notice.value = ''
  if (server.value?.configuration && !server.value.hasChanges) server.value.load()
  repositories.value?.load()
  nextTick(() => { if (server.value && currentGroups.value.length) server.value.activeGroup = currentGroups.value[0] })
}
function restore(id) {
  if (id === 'appearance') Object.assign(appearance,JSON.parse(appearanceBaseline.value))
  if (id in drafts) drafts[id] = clone(baselines.value[id])
  if (id === 'server') Object.assign(networkDraft,JSON.parse(networkBaseline.value))
  if (id === 'global') Object.assign(debugDraft,JSON.parse(debugBaseline.value))
  const groups = pages.find(item => item.id === id)?.groups
  if (groups && server.value?.configuration) server.value.resetDraft(groups)
}
function reset() { if (busy.value) return; restore(page.value); error.value = ''; notice.value = ''; if (page.value === 'repository') repositories.value?.load() }
function closeRepository() { repositoryEditor.value.close(); repositories.value?.load() }
function discard() { if (busy.value) return; for (const item of pages) restore(item.id); confirmClose.value?.close(); emit('close') }
function cancel() { if (busy.value) return; if (dirty.value) confirmClose.value.showModal(); else emit('close') }
function persist(entries) {
  const previous = entries.map(([key]) => [key,localStorage.getItem(key)])
  try { for (const [key,value] of entries) localStorage.setItem(key,JSON.stringify(value)) }
  catch (failure) { for (const [key,value] of previous) { try { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key,value) } catch { /* Keep drafts and report unavailable storage. */ } }; throw failure }
}
async function applyPage(id) {
  const definition = pages.find(item => item.id === id)
  if (id === 'checkin' && (!Number.isInteger(drafts.checkin.displayLimit) || drafts.checkin.displayLimit < 1 || drafts.checkin.displayLimit > 500)) { page.value = id; error.value = 'Result limit must be an integer from 1 to 500.'; return false }
  if (id === 'tasks' && drafts.tasks.columns.some(column => !Number.isInteger(column.width) || column.width < 40 || column.width > 480)) { page.value = id; error.value = 'Column width must be an integer from 40 to 480.'; return false }
  if (id === 'repository' && (!drafts.repository.defaultAlias || drafts.repository.enabledAliases && !drafts.repository.enabledAliases.includes(drafts.repository.defaultAlias))) { page.value = id; error.value = 'Enable at least one repository and choose its default.'; return false }
  if (id === 'repository') {
    try {
      const aliases = ['asset_base_dir','base_dir_alias'].flatMap(key => {
        const raw = server.value?.draft['checkin/' + key] || ''
        return raw.startsWith('{') ? Object.keys(JSON.parse(raw)) : ['default']
      })
      if (!aliases.includes(drafts.repository.defaultAlias)) throw new Error()
    } catch { page.value = id; error.value = 'Enable at least one repository and choose its default.'; return false }
  }
  if (definition.groups && server.value?.hasChanges && !await server.value.save(definition.groups)) { page.value = pages.find(item => item.groups?.includes(server.value.activeGroup))?.id || id; if (page.value === 'repository') { await nextTick(); if (!repositoryEditor.value.open) repositoryEditor.value.show() }; return false }
  try {
    if (id === 'appearance') { saveAppearance(); appearanceBaseline.value = JSON.stringify(appearance) }
    if (id === 'server') { persist([['tactic_stream.network',networkDraft]]); Object.assign(networkSettings,clone(networkDraft)); networkBaseline.value = JSON.stringify(networkDraft) }
    if (id === 'global') {
      const next = normalizePreferences({ ...preferences,global:drafts.global })
      persist([['tactic_stream.preferences',next],['tactic_stream.debug_log',debugDraft]])
      Object.assign(preferences.global,next.global); Object.assign(debugSettings,clone(debugDraft)); debugBaseline.value = JSON.stringify(debugDraft); baselines.value.global = clone(drafts.global)
    } else if (id in drafts) { savePreferencePage(id,drafts[id]); drafts[id] = clone(preferences[id]); baselines.value[id] = clone(preferences[id]) }
    if (id === 'repository') await repositories.value?.load()
    return true
  } catch { page.value = id; error.value = 'Browser settings could not be saved. Check browser storage permissions and free space.'; return false }
}
async function apply({ all = false, close = false } = {}) {
  if (busy.value) return
  error.value = ''; notice.value = ''; saving.value = true
  try { for (const id of all ? pages.map(item => item.id) : [page.value]) if (!await applyPage(id)) return; notice.value = server.value?.configuration?.restart_required ? 'Saved to XML. Restart the backend to apply these settings.' : 'Configuration applied'; if (close) { confirmClose.value?.close(); emit('close') } }
  finally { saving.value = false }
}
async function clearCache() {
  confirmClear.value.close(); clearing.value = true; error.value = ''; notice.value = ''
  try { if (await props.reloadCache(cacheScope.value) === false) throw new Error(); notice.value = cacheScope.value === 'tabs' ? 'Tabs cache cleared' : 'Cache reloaded' }
  catch { error.value = 'Cached server data could not be refreshed.' }
  finally { clearing.value = false }
}
function beforeUnload(event) { if (dirty.value || busy.value) { event.preventDefault(); event.returnValue = '' } }
onActivated(() => { begin(); window.addEventListener('beforeunload',beforeUnload) })
onDeactivated(() => { Object.assign(appearance,JSON.parse(appearanceBaseline.value)); configurationPreview.value = false; window.removeEventListener('beforeunload',beforeUnload) })
onBeforeUnmount(() => { Object.assign(appearance,JSON.parse(appearanceBaseline.value)); configurationPreview.value = false; window.removeEventListener('beforeunload',beforeUnload) })
defineExpose({ cancel,dirty })
</script>
<template>
  <div class="configuration-shell configuration configuration-native" :aria-busy="busy">
    <header class="configuration-header">
      <div class="configuration-brand"><h2 id="configuration-title">{{ t('Configuration') }}</h2><small class="muted">TACTIC STREAM · {{ t('Preferences') }}</small></div>
      <div class="configuration-page-heading"><div><h1>{{ t(current.title) }}</h1><p class="muted">{{ t(current.description) }}</p></div><div class="configuration-actions">
        <AppButton v-if="!mobile" label="Reset" icon="undo" :disabled="busy || !pageDirty(page)" :title="t('Reset')" @click="reset" />
        <AppButton v-if="!mobile" label="Apply" icon="check" :disabled="busy || !pageDirty(page)" :title="t('Apply')" @click="apply()" />
        <AppButton label="Save" icon="save" :disabled="busy || !dirty" :aria-label="t('Save configuration')" @click="apply({ all:true })" />
        <AppButton v-if="!mobile" label="Configuration help" icon="help" icon-only @click="emit('help',current.help)" />
        <AppMenu v-if="mobile" label="Configuration actions" overlay><AppButton label="Reset" icon="undo" :disabled="busy || !pageDirty(page)" @click="reset" /><AppButton label="Apply" icon="check" :disabled="busy || !pageDirty(page)" @click="apply()" /><AppButton label="Configuration help" icon="help" @click="emit('help',current.help)" /></AppMenu>
        <AppButton label="Close" icon="close" icon-only :disabled="busy" @click="cancel" />
      </div></div>
    </header>
    <nav class="configuration-navigation" :aria-label="t('Configuration sections')">
      <AppSelect v-if="mobile" :model-value="page" :options="pages.map(item => ({ value:item.id,label:item.title }))" label="Configuration sections" @update:model-value="selectPage" />
      <button v-else v-for="item in pages" :key="item.id" :aria-label="t(item.title)" :aria-pressed="page === item.id" @click="selectPage(item.id)"><AppIcon :name="item.icon" /><span>{{ t(item.title) }}</span><i v-if="pageDirty(item.id)" class="configuration-dirty" :aria-label="t('Unsaved changes')" /></button>
    </nav>
    <div class="configuration-pages">
      <p v-if="error" class="error configuration-feedback" role="alert">{{ t(error) }}</p><p v-if="notice" class="notice configuration-feedback" role="status">{{ t(notice) }}</p>
      <section v-if="page === 'server'" class="configuration-server-overview"><section class="content"><section class="settings-section"><header><h2>{{ t('Connection') }}</h2><p class="muted">{{ t('The browser uses the server that hosts this application.') }}</p></header><div class="configuration-group"><SettingRow title="Server address"><code>{{ origin }}</code></SettingRow><SettingRow title="Current account"><span>{{ login }}</span></SettingRow></div></section></section><NetworkSettings :settings="networkDraft" /></section>
      <section v-if="page === 'appearance'" class="content appearance-page"><AppearanceSettings /></section>
      <ProjectSettings v-if="page === 'project'" :ticket="ticket" :project="project" :can-administer="canAdminister" :open-project="openProject" />
      <RepositorySettings v-if="page === 'repository' && canAdminister" ref="repositories" :ticket="ticket" :busy="busy" @edit="repositoryEditor.show()" @session-expired="emit('session-expired')" />
      <PreferenceSettings v-if="page in drafts && page !== 'repository'" :page="page" :draft="drafts[page]" :busy="busy" />
      <DebugSettings v-if="page === 'global'" :settings="debugDraft" />
      <section v-if="page === 'global'" class="content"><p class="muted">{{ t('System tray, local worker threads, Handler Server and DCC connections belong to the desktop application. Browser requests use the server worker configuration.') }}</p></section>
      <section v-if="page === 'cache'" class="content"><section class="settings-section"><header><h2>{{ t('Cache maintenance') }}</h2><p class="muted">{{ t('Authenticated server records stay in session memory. Project layouts and preferences are stored separately in this browser.') }}</p></header><div class="configuration-group"><SettingRow title="Clear tabs cache" description="Clear saved object, process and version expansion without closing search tabs."><AppButton label="Clear tabs cache" icon="refresh" :disabled="busy" @click="cacheScope = 'tabs'; confirmClear.showModal()" /></SettingRow><SettingRow title="Clear all cached server data" description="Search tabs will keep their layout, but server records will be loaded again when needed."><AppButton label="Clear cache" icon="refresh" :disabled="busy" @click="cacheScope = 'server'; confirmClear.showModal()" /></SettingRow></div></section></section>
      <section v-if="canAdminister && ['server','tasks'].includes(page) && server?.configuration" class="configuration-server-tools"><AppSelect v-model="server.activeGroup" :options="currentGroups.map(title => ({ value:title,label:title }))" label="Server settings section" /><AppSearchField v-model="server.search" label="Find a setting" placeholder="Find a setting…" /></section>
      <Teleport defer to="#configuration-repository-editor-body" :disabled="page !== 'repository'"><ServerConfiguration v-if="canAdminister" ref="server" v-show="serverPages.includes(page)" :group-titles="currentGroups" :ticket="ticket" show-details @session-expired="emit('session-expired')" /></Teleport>
      <p v-if="!canAdminister && page === 'repository'" class="muted configuration-feedback">{{ t('Repository configuration requires administrator access.') }}</p>
    </div>
    <dialog ref="repositoryEditor" v-window="{ type:'window' }" class="record-dialog configuration-repository-editor" :aria-label="t('Repository Editor')"><header><div><h2>{{ t('Repository Editor') }}</h2><small class="muted">{{ t('Repository definitions') }}</small></div><AppButton icon-only icon="close" label="Close" :disabled="busy" @click="closeRepository" /></header><RepositoryEditor :server="server" :draft="drafts.repository" :repositories="repositories?.records || []" :busy="busy || repositories?.checking" @check="repositories.load('check',$event)"><div id="configuration-repository-editor-body" /></RepositoryEditor><footer><AppButton label="Cancel" :disabled="busy || !pageDirty('repository')" @click="reset" /><AppButton label="Close" @click="closeRepository" /><AppButton label="Save" highlighted :disabled="busy || !pageDirty('repository')" @click="apply()" /></footer></dialog>
    <dialog ref="confirmClose" class="record-dialog" :aria-label="t('Unsaved changes')"><header><h2>{{ t('Unsaved changes') }}</h2></header><p>{{ t('Save changes before closing Configuration?') }}</p><footer><AppButton label="Continue editing" @click="confirmClose.close()" /><AppButton label="Discard changes" :disabled="busy" @click="discard" /><AppButton label="Save" icon="save" :disabled="busy" @click="apply({ all:true, close:true })" /></footer></dialog>
    <dialog ref="confirmClear" class="record-dialog" :aria-label="t(cacheScope === 'tabs' ? 'Clear saved branch expansion?' : 'Clear cached server data?')"><header><h2>{{ t(cacheScope === 'tabs' ? 'Clear saved branch expansion?' : 'Clear cached server data?') }}</h2></header><p>{{ t(cacheScope === 'tabs' ? 'Object, process and version branches will collapse. Search tabs, filters and dock layouts remain unchanged.' : 'Projects, Search Types, search results and navigation will be downloaded again. Saved layouts and preferences remain unchanged.') }}</p><footer><AppButton label="Cancel" @click="confirmClear.close()" /><AppButton :label="cacheScope === 'tabs' ? 'Clear tabs cache' : 'Clear cache'" icon="refresh" @click="clearCache" /></footer></dialog>
  </div>
</template>
<style>
.configuration-native { --configuration-navigation-width:216px; --configuration-header-height:76px; }
.configuration-native > .configuration-header { min-height:77px; }
.configuration-native .configuration-brand h2 { font-size:17px; font-weight:600; }
.configuration-native .configuration-navigation { padding-top:16px; }.configuration-native .configuration-navigation > button { min-height:48px; font-size:13px; padding:0 16px; }
.configuration-native .configuration-navigation .app-icon { width:16px; height:16px; font-size:16px; }
.configuration-native .configuration-navigation > button[aria-pressed=true]::before { top:12px; bottom:12px; }
.configuration-native .configuration-pages { overflow:auto; display:block; }
.configuration-native .content { padding:20px 22px; gap:14px; overflow:visible; height:auto; flex:none; }
.configuration-native .configuration-pages > .content + .content { padding-top:0; }
.configuration-native .configuration-pages .settings-section > header { margin-bottom:0; }
.configuration-native .settings-section > header h2 { font-size:14px; }
.configuration-native .configuration-group { padding:16px; }
.configuration-native .settings-row { grid-template-columns:minmax(0,1fr) 240px; gap:20px; padding:10px 4px; }
.configuration-native .settings-row.appearance-palette-row { grid-template-columns:minmax(0,1fr) min(380px,48%); }
.configuration-native .setting-description { gap:3px; }.configuration-native .settings-row { line-height:normal; }.configuration-native .setting-description p { line-height:normal; }
.configuration-native .setting-description p { font-size:var(--text-caption); }
.configuration-native .setting-description strong, .configuration-native h1, .configuration-native h2 { font-weight:600; }
.configuration-native .setting-control { justify-items:end; }
.configuration-server-tools { display:flex; gap:8px; padding:0 22px; }
.configuration-server-tools > .app-select { width:250px; }
.configuration-server-tools > .app-search-field { flex:1; }
.configuration-feedback { margin:14px 22px; }
.configuration-repository-editor { width:1100px; max-width:calc(100vw - 32px); }.configuration-repository-editor .content { padding:16px 0; }.configuration-repository-editor > header > div { flex:1; }
@media(max-width:960px) { .configuration-native .configuration-actions > .app-button:not(.icon-button) { width:var(--control-height); height:var(--control-height); padding:0; border-radius:50%; flex-shrink:0; }.configuration-native .configuration-actions > .app-button:not(.icon-button) > span:not(.app-icon) { display:none; } }
@container(max-width:560px) { .configuration-native .settings-row { grid-template-columns:minmax(0,1fr); }.configuration-native .setting-control { justify-items:stretch; }.configuration-native .configuration-server-tools { flex-wrap:wrap; } }
</style>
