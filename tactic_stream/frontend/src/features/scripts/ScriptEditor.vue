<script setup>
// Current Handler ScriptEditorView.qml / script_editor.py (EPL-1.0), browser/server targets.
import { inject, computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { rpc, scriptEditor, beginActivity, endActivity } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import WorkspaceTabs from '../../controls/WorkspaceTabs.vue'
import CodeEditor from '../../controls/CodeEditor.vue'
import { copyText } from '../../controls/clipboard.js'
import { documentSymbols, completions } from '../../controls/codeEditing.js'
import NavigationTree from '../workspace/NavigationTree.vue'
import { buttonId, runBrowserScript, scriptTree } from './scriptShelf.js'
import './scriptEditor.css'

const openHelp = inject('openHelp')
const props = defineProps({ ticket: String, project: String, login: String, searchType: String, searchKeys: Array, updates: Object })
const emit = defineEmits(['saved', 'executed', 'closed'])
const dialog = ref(null), confirmation = ref(null), historyDialog = ref(null), editor = ref(null), actions = ref(null)
const catalog = ref(null), tabs = ref([]), selected = ref(''), busy = ref(false), error = ref(''), running = ref(''), uncertain = ref(false)
const fontSize = ref(9.25), analysis = ref(null), analysisError = ref(''), symbolLine = ref(0), filter = ref(null)
const scriptQuery = ref(''), outlineQuery = ref(''), side = ref('scripts'), treeHidden = ref(false), treeWidth = ref(200), outputHeight = ref(120), outputHidden = ref(false), outputWrap = ref(false), historyRows = ref([])
const query = computed({ get: () => side.value === 'scripts' ? scriptQuery.value : outlineQuery.value, set: value => { if (side.value === 'scripts') scriptQuery.value = value; else outlineQuery.value = value } })
const confirmAction = ref(''), confirmTitle = ref(''), pending = ref(null)
let generation = 0, analysisGeneration = 0, persistTimer, restoring = true, stateKey = storageKey(), reloadPending = false
const active = computed(() => tabs.value.find(tab => tab.id === selected.value))
const supported = computed(() => ['python', 'javascript', 'server_js'].includes(active.value?.language))
const editable = computed(() => !!catalog.value?.canEdit && supported.value)
const dirty = tab => JSON.stringify(fields(tab)) !== tab.baseline
const tree = computed(() => scriptTree((catalog.value?.scripts || []).filter(row => !row.retired).map(row => ({ path: [row.folder, row.title].filter(Boolean).join('/'), language: row.language, runnable: true }))))
const allSymbols = computed(() => analysis.value?.bufferKey === active.value?.id && analysis.value?.source === active.value?.source ? analysis.value.symbols : [])
const symbols = computed(() => allSymbols.value.filter(row => (row.qualifiedName || row.name).toLowerCase().includes(query.value.toLowerCase())))
async function analyse(request) {
  const id = ++analysisGeneration, context = generation, tab = active.value
  if (!tab || tab.id !== request.bufferKey || !catalog.value?.canEdit) return
  try {
    const result = tab.language === 'python' ? await scriptEditor('analyse', props.ticket, props.project, { source: request.source, cursor: request.cursor, manual: request.manual })
      : { symbols: documentSymbols(request.source, 'javascript'), completions: request.manual || /[\w$]{2}$/.test(request.source.slice(0, request.cursor)) ? completions(request.source, request.cursor, 'javascript').map(row => ({ ...row, label: row.name, kind: 'variable', insertText: row.name })) : [] }
    if (id === analysisGeneration && context === generation && active.value?.id === tab.id && tab.source === request.source) { analysis.value = { ...request, ...result }; analysisError.value = '' }
  } catch (exception) { if (id === analysisGeneration && context === generation) analysisError.value = exception.message }
}
function showOutline() { treeHidden.value = false; side.value = 'outline'; nextTick(() => { const input = filter.value?.$el.querySelector('input'); input?.focus(); input?.select() }) }
function goToSymbol(row) { symbolLine.value = row.line; editor.value?.goToLine(row.line) }
function fields(tab) { return { folder: tab.folder, title: tab.title, language: tab.language, source: tab.source } }
function storageKey() { return 'tactic_stream.script_editor.' + props.login + '.' + props.project }
function persist() {
  if (restoring) return
  try { localStorage.setItem(stateKey, JSON.stringify({ tabs: tabs.value, selected: selected.value, treeWidth: treeWidth.value, outputHeight: outputHeight.value, treeHidden: treeHidden.value, outputHidden: outputHidden.value, outputWrap: outputWrap.value, fontSize: fontSize.value, side: side.value })) }
  catch { error.value = t('The browser could not store the script drafts. Keep this window open until you save them.') }
}
watch([tabs, selected, treeWidth, outputHeight, treeHidden, outputHidden, outputWrap, fontSize, side], () => { if (restoring) return; clearTimeout(persistTimer); persistTimer = setTimeout(persist, 250) }, { deep: true })
function restore() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()) || 'null')
    if (!saved || !Array.isArray(saved.tabs)) return
    tabs.value = saved.tabs.filter(tab => typeof tab.id === 'string' && ['code', 'folder', 'title', 'language', 'source', 'baseline', 'revision', 'output'].every(field => typeof tab[field] === 'string')).slice(0, 120)
    selected.value = tabs.value.some(tab => tab.id === saved.selected) ? saved.selected : tabs.value[0]?.id || ''
    treeWidth.value = Math.min(500, Math.max(140, Number(saved.treeWidth) || 200)); outputHeight.value = Math.min(500, Math.max(80, Number(saved.outputHeight) || 120))
    fontSize.value = Math.min(15, Math.max(8, Number(saved.fontSize) || 9.25))
    treeHidden.value = !!saved.treeHidden; outputHidden.value = !!saved.outputHidden; outputWrap.value = !!saved.outputWrap; side.value = saved.side === 'outline' ? 'outline' : 'scripts'
  } catch { error.value = t('The browser script draft could not be restored.') }
}
function create(row) {
  const tab = { id: buttonId(), code: row?.code || '', folder: row?.folder || '', title: row?.title || 'new_script', language: row?.language || 'python', source: row?.source || '', revision: row?.revision || '', output: '', missing: false }
  tab.baseline = JSON.stringify(fields(tab)); tabs.value.push(tab); selected.value = tab.id
  return tab
}
function openScript(path) {
  const row = catalog.value?.scripts.find(row => [row.folder, row.title].filter(Boolean).join('/') === path)
  if (!row) return
  const tab = tabs.value.find(tab => tab.code === row.code) || create(row)
  selected.value = tab.id; nextTick(() => editor.value?.focus())
}
function reconcile() {
  for (const tab of tabs.value.filter(tab => tab.code)) {
    const row = catalog.value.scripts.find(row => row.code === tab.code)
    tab.missing = !row
    if (row && !dirty(tab)) { Object.assign(tab, fields(row), { revision: row.revision }); tab.baseline = JSON.stringify(fields(tab)) }
  }
}
async function load() {
  reloadPending = false
  const id = ++generation; busy.value = true; error.value = ''
  try {
    const result = await scriptEditor('read', props.ticket, props.project)
    if (id !== generation) return
    catalog.value = result; uncertain.value = false
    reconcile()
  } catch (exception) { if (id === generation) error.value = exception.message }
  finally { if (id === generation) busy.value = false }
}
async function open(path = '') {
  dialog.value.show()
  if (!catalog.value) { await load(); if (catalog.value && !tabs.value.length) { restore(); reconcile() }; restoring = !catalog.value }
  else await load()
  if (catalog.value && !tabs.value.length) create()
  if (path) openScript(path)
  nextTick(() => editor.value?.focus())
}
function ask(action, target) {
  pending.value = target; confirmAction.value = action
  confirmTitle.value = action === 'delete' ? t('Delete “{name}”?', { name: target.folder + '/' + target.title }) : action === 'reload' ? t('Discard changes?') : t('Save changes before closing?')
  confirmation.value.show()
}
function removeTabs(ids) { tabs.value = tabs.value.filter(tab => !ids.includes(tab.id)); if (!tabs.value.some(tab => tab.id === selected.value)) selected.value = tabs.value.at(-1)?.id || '' }
function closeTab(id) { const tab = tabs.value.find(tab => tab.id === id); if (!tab || busy.value || running.value) return; if (dirty(tab)) ask('tabs', [id]); else removeTabs([id]) }
function closeAll() { if (busy.value || running.value) return; const ids = tabs.value.map(tab => tab.id); if (tabs.value.some(dirty)) ask('tabs', ids); else removeTabs(ids) }
function close() { if (busy.value || running.value) return; persist(); dialog.value.close(); emit('closed') }
async function save(tab = active.value) {
  if (!tab || !catalog.value?.canEdit || busy.value || uncertain.value || !['python', 'javascript', 'server_js'].includes(tab.language)) return false
  const snapshot = fields(tab), id = generation; busy.value = true; error.value = ''
  try {
    const result = await scriptEditor('save', props.ticket, props.project, { ...snapshot, code: tab.code, revision: tab.code ? tab.revision : catalog.value.revision })
    if (id !== generation) return false
    catalog.value = result
    const row = result.scripts.find(row => row.code === result.savedCode)
    tab.code = row.code; tab.revision = row.revision; tab.missing = false; tab.baseline = JSON.stringify(fields(row))
    if (JSON.stringify(fields(tab)) === JSON.stringify(snapshot)) Object.assign(tab, fields(row))
    persist(); emit('saved'); return true
  } catch (exception) { if (id === generation) { error.value = exception.message; uncertain.value = !['invalid_request', 'access_denied'].includes(exception.code) }; return false }
  finally { if (id === generation) busy.value = false }
}
async function accept(saveFirst = false) {
  if (confirmAction.value === 'reload') {
    const row = catalog.value.scripts.find(row => row.code === pending.value.code)
    if (row) { Object.assign(pending.value, fields(row), { revision: row.revision }); pending.value.baseline = JSON.stringify(fields(row)); uncertain.value = false }
    confirmation.value.close(); return
  }
  if (confirmAction.value === 'delete') {
    const tab = pending.value, id = generation; busy.value = true
    try {
      const result = await scriptEditor('delete', props.ticket, props.project, { code: tab.code, revision: tab.revision })
      if (id !== generation) return
      catalog.value = result; removeTabs(tabs.value.filter(row => row.code === tab.code).map(row => row.id)); emit('saved'); confirmation.value.close()
    } catch (exception) { if (id === generation) { error.value = exception.message; uncertain.value = !['invalid_request', 'access_denied'].includes(exception.code) } }
    finally { if (id === generation) busy.value = false }
    return
  }
  const ids = pending.value
  if (saveFirst) for (const id of ids) { const tab = tabs.value.find(tab => tab.id === id); if (tab && dirty(tab) && !await save(tab)) return }
  removeTabs(ids); confirmation.value.close(); persist()
}
async function run(source = active.value?.source) {
  const tab = active.value
  if (!editable.value || running.value || busy.value || !source?.trim()) return
  const id = generation, context = { ticket: props.ticket, project: props.project, searchType: props.searchType, searchKeys: [...(props.searchKeys || [])] }
  running.value = tab.id; error.value = ''; const started = performance.now()
  const activity = beginActivity(context.ticket, 'Running…')
  try {
    const format = value => { if (typeof value === 'string') return value; try { return JSON.stringify(value, null, 2) ?? String(value) } catch { return String(value) } }
    const scriptConsole = Object.fromEntries(['log', 'info', 'warn', 'error', 'debug', 'table'].map(method => [method, (...args) => { globalThis.console[method](...args); if (id === generation) appendOutput(tab, args.map(format).join(' ') + '\n') }]))
    const result = tab.language === 'javascript' ? await runBrowserScript(source, { project: context.project, searchType: context.searchType, searchKeys: context.searchKeys, console: { ...globalThis.console, ...scriptConsole },
      rpc: (method, args = [], kwargs = {}) => rpc(method, [{ ticket: context.ticket, project: context.project }, ...args], kwargs), refresh: () => { if (id === generation) emit('executed') } })
      : await rpc(tab.language === 'server_js' ? 'execute_js_script' : 'execute_python_script', [{ ticket: context.ticket, project: context.project }, '', { code: source }])
    if (id === generation) { appendOutput(tab, `${t('Execution time')}: ${((performance.now() - started) / 1000).toFixed(3)}s\n${format(result)}\n`); emit('executed') }
  } catch (exception) { if (id === generation) { appendOutput(tab, (exception.stack || exception.message) + '\n'); error.value = exception.message } }
  finally { endActivity(activity); if (id === generation) running.value = '' }
}
function appendOutput(tab, value) {
  // ponytail: cap each browser draft output at 200 KB; use Debug Log for full request responses.
  tab.output = (tab.output + value).slice(-200000); outputHidden.value = false
  nextTick(() => { const output = dialog.value.querySelector('.script-editor-output pre'); if (output) output.scrollTop = output.scrollHeight })
}
async function history() {
  if (!active.value?.code || busy.value) return
  const tab = active.value, id = generation; busy.value = true; historyRows.value = []; historyDialog.value.show()
  try { const result = await scriptEditor('history', props.ticket, props.project, { code: tab.code }); if (id === generation) historyRows.value = result.history }
  catch (exception) { if (id === generation) error.value = exception.message }
  finally { if (id === generation) busy.value = false }
}
async function restoreRevision(row) {
  if (!editable.value || busy.value) return
  const tab = active.value, id = generation; busy.value = true
  try { const result = await scriptEditor('revision', props.ticket, props.project, { code: tab.code, revision_id: row.revisionId }); if (id === generation) { const source = result.revision; Object.assign(tab, { folder: source.folder, title: source.title, language: source.language, source: source.script }); historyDialog.value.close() } }
  catch (exception) { if (id === generation) error.value = exception.message }
  finally { if (id === generation) busy.value = false }
}
async function runner() {
  if (!active.value?.code) return
  const saved = catalog.value.scripts.find(row => row.code === active.value.code)
  if (!saved) return
  const path = saved.folder + '/' + saved.title
  const source = saved.language === 'javascript' ? `if (project !== ${JSON.stringify(props.project)}) throw new Error('Run this script in its saved project');\nconst scripts = await rpc('query', ['config/custom_script'], {filters: [['folder', ${JSON.stringify(saved.folder)}], ['title', ${JSON.stringify(saved.title)}]], limit: 2});\nif (scripts.length !== 1 || scripts[0].language !== 'javascript') throw new Error('Saved JavaScript script is unavailable');\nconst url = URL.createObjectURL(new Blob(['export default async function(context) {\\nconst {project, searchType, searchKeys, rpc, refresh, console = globalThis.console} = context;\\n' + scripts[0].script + '\\n}'], {type: 'text/javascript'}));\ntry { const module = await import(url); return await module.default(context); }\nfinally { URL.revokeObjectURL(url); }\n` : `server.set_project(${JSON.stringify(props.project)})\nserver.${saved.language === 'server_js' ? 'execute_js_script' : 'execute_python_script'}(${JSON.stringify(path)}, {})`
  try { await copyText(source); appendOutput(active.value, t('Script runner copied to clipboard.') + '\n') } catch (exception) { error.value = exception.message }
}
function key(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); save() }
  else if (event.key === 'F5') { event.preventDefault(); run() }
}
watch(() => [props.ticket, props.project, props.login], () => {
  clearTimeout(persistTimer); persist(); restoring = true; stateKey = storageKey()
  generation++; busy.value = false; running.value = ''; catalog.value = null; tabs.value = []; selected.value = ''; uncertain.value = false; error.value = ''
  analysisGeneration++; analysis.value = null; analysisError.value = ''
  if (dialog.value?.open) { const id = generation + 1; load().then(() => { if (id === generation && catalog.value) { restore(); reconcile(); restoring = false; if (!tabs.value.length) create() } }) }
}, { flush: 'sync' })
onBeforeUnmount(() => { clearTimeout(persistTimer); persist(); generation++; analysisGeneration++ })
function refreshUpdates() { if (reloadPending && dialog.value?.open && !busy.value && !running.value) load() }
watch(() => props.updates, batch => {
  if (dialog.value?.open && [...(batch?.cacheChanges || []), ...(batch?.cacheRetired || [])].some(row => row.projectCode === props.project && row.searchType === 'config/custom_script')) { reloadPending = true; refreshUpdates() }
})
watch([busy, running], refreshUpdates)
defineExpose({ open, reload: load })
</script>
<template>
  <Teleport to="body">
    <dialog v-window="{kind:'script_editor', type:'window' }" ref="dialog" class="script-editor-dialog" :style="{ '--editor-font-size': fontSize + 'pt' }" :aria-label="t('Script Editor')" @cancel.prevent="close" @keydown="key" :aria-busy="busy || !!running">
      <header class="script-editor-header"><AppIcon name="code" /><strong>{{ t('Script Editor') }}</strong><AppButton icon-only icon="help" label="Script editor help" @click="openHelp('script_editor')" /><AppButton icon-only icon="close" label="Close script editor" :disabled="busy || !!running" @click="close" /></header>
      <div class="script-editor-screen">
        <div class="script-editor-main">
          <div class="script-editor-toolbar">
            <AppButton icon-only icon="add" label="New script" :disabled="busy || !catalog?.canEdit" @click="create()" />
            <AppButton icon-only icon="save" label="Save current script to server" :disabled="!editable || busy || uncertain" @click="save()" />
            <input v-if="active" v-model="active.folder" :readonly="!editable || busy" :placeholder="t('Folder')" :aria-label="t('Script folder')"><span>/</span><input v-if="active" v-model="active.title" :readonly="!editable || busy" :placeholder="t('Title')" :aria-label="t('Script title')">
            <AppSelect v-if="active" v-model="active.language" label="Script language" :disabled="!editable || busy" :options="[{ value: 'python', label: 'Server Python' }, { value: 'javascript', label: 'JavaScript' }, { value: 'server_js', label: 'Server JavaScript' }, ...(!supported ? [{ value: active.language, label: active.language }] : [])]" />
            <AppButton icon-only icon="FAS_BOLT" label="Handler and DCC script triggers are unavailable in the web editor." disabled />
            <AppButton icon-only icon="refresh" label="Refresh scripts from server" :disabled="busy || !!running" @click="load" /><AppButton icon-only :icon="treeHidden ? 'previous' : 'next'" :label="treeHidden ? 'Show scripts and outline' : 'Hide scripts and outline'" :highlighted="!treeHidden" @click="treeHidden = !treeHidden" />
          </div>
          <WorkspaceTabs kind="script" :tabs="tabs.map(tab => ({ id: tab.id, title: tab.title, dirty: dirty(tab) }))" :selected="selected" :disabled="busy" @select="selected = $event" @add="create()" @close="closeTab" @reorder="(from, to) => tabs.splice(to, 0, tabs.splice(from, 1)[0])"><template #actions><AppButton icon-only icon="close" label="Close all script tabs" :disabled="busy || !!running" @click="closeAll" /><AppMenu ref="actions" overlay label="Saved script actions" :close-on-select="true"><AppButton icon="refresh" label="Reload saved source" :disabled="!active?.code || busy" @click="ask('reload', active)" /><AppButton icon="copy" label="Copy Script Runner" :disabled="!active?.code" @click="runner" /><AppButton destructive icon="delete" label="Delete from server" :disabled="!editable || !active?.code || busy || uncertain" @click="ask('delete', active)" /></AppMenu></template></WorkspaceTabs>
          <section v-if="active" class="script-editor-output" :class="{ wrapped: outputWrap }" :style="{ height: outputHidden ? '28px' : outputHeight + 'px' }"><header><AppIcon name="MDI_CONSOLE" /><span>{{ t('Output') }}</span><AppButton icon-only icon="MDI_WRAP" label="Wrap output" :aria-pressed="outputWrap" @click="outputWrap = !outputWrap" /><AppButton icon-only icon="delete" label="Clear output" :disabled="!active.output" @click="active.output = ''" /><AppButton icon-only :icon="outputHidden ? 'MDI_CHEVRON_UP' : 'MDI_CHEVRON_DOWN'" :label="outputHidden ? 'Expand output' : 'Collapse output'" @click="outputHidden = !outputHidden" /></header><pre v-if="!outputHidden" tabindex="0">{{ active.output }}</pre></section>
          <AppSplitter v-if="active && !outputHidden" v-model="outputHeight" horizontal label="Output height" :min="80" :max="500" />
          <div v-if="active" class="script-editor-code"><CodeEditor ref="editor" v-model="active.source" v-model:font-size="fontSize" :analysis="analysis" :buffer-key="active.id" :language="active.language === 'server_js' ? 'javascript' : active.language" :read-only="!editable" :disabled="busy || !!running" @run="run" @analyse="analyse" @outline="showOutline" @help="openHelp('script_editor')"><template #actions><AppButton icon-only icon="FAS_CLOUD" label="Saved revisions" :disabled="!active?.code || busy" @click="history" /></template></CodeEditor></div>
          <p v-else class="script-editor-empty muted">{{ t('Open a script or create a new one.') }}</p>
          <footer><AppButton label="Run Script" highlighted icon="play-arrow" :disabled="!editable || busy || !!running || !active?.source.trim()" @click="run()" /><span>{{ running ? t('Running…') : t('Run in') }}</span><AppSelect :model-value="active?.language === 'javascript' ? 'browser' : 'server'" label="Execution target" :options="[{ value: active?.language === 'javascript' ? 'browser' : 'server', label: active?.language === 'javascript' ? 'Browser' : 'Server' }]" disabled /></footer>
          <p v-if="!catalog?.canEdit && catalog" class="muted">{{ t('Read-only: script changes and execution require administrator access.') }}</p><p v-else-if="!supported && active" class="muted">{{ t('This legacy language is read-only in the web editor') }}</p><p v-if="active?.missing" class="error">{{ t('This script was deleted on the server. Its local draft is preserved.') }}</p><p v-if="error || analysisError" class="error" role="alert">{{ t(error || analysisError) }}</p>
        </div>
        <AppSplitter v-if="!treeHidden" v-model="treeWidth" reverse label="Scripts panel width" :min="140" :max="500" />
        <aside v-if="!treeHidden" class="script-editor-tree" :style="{ width: treeWidth + 'px' }"><AppSegmentedButton v-model="side" outlined label="Scripts panel" :options="[{ value: 'scripts', label: 'Scripts' }, { value: 'outline', label: 'Outline' }]" /><AppSearchField ref="filter" v-model="query" label="Search scripts and symbols" @keydown.enter.prevent="side === 'outline' && symbols.length && goToSymbol(symbols[0])" :placeholder="t(side === 'scripts' ? 'Search scripts' : 'Filter classes and methods')" />
          <NavigationTree v-if="side === 'scripts'" :entries="tree" :query="query" :selected="active ? active.folder + '/' + active.title : ''" @select="openScript($event.key)" @contextmenu.prevent="event => { const path = event.target.closest('[data-entry-key]')?.dataset.entryKey; if (path && !path.startsWith('folder:')) { openScript(path); nextTick(() => actions.open = true) } }" />
          <nav v-else class="script-editor-outline" :aria-label="t('Outline')"><AppButton v-for="row in symbols" :key="row.qualifiedName || row.position" :icon="row.kind === 'class' ? 'MDI_FORMAT_SIZE' : 'code'" :label="(row.qualifiedName || row.name) + ' · ' + row.line" :title="row.detail" :aria-current="symbolLine === row.line" :style="{ paddingLeft: (7 + (row.depth || 0) * 14) + 'px' }" @click="goToSymbol(row)"><span>{{ row.name }}</span><small>{{ row.line }}</small></AppButton><p v-if="!allSymbols.length" class="muted">{{ t('No classes or methods') }}</p></nav>
        </aside>
      </div>
    </dialog>
    <dialog v-window="{ type:'popup' }" ref="confirmation" class="record-dialog" :aria-label="confirmTitle" @cancel.prevent="!busy && confirmation.close()"><h2>{{ confirmTitle }}</h2><p>{{ confirmAction === 'delete' ? t('Deleting the saved script does not remove its shelf buttons; they become unavailable.') : t('Save, discard the selected drafts, or return to editing.') }}</p><p v-if="error" class="error">{{ t(error) }}</p><div class="configuration-actions"><AppButton v-if="confirmAction === 'tabs'" label="Save" icon="save" :disabled="busy || uncertain || !catalog?.canEdit" @click="accept(true)" /><AppButton :label="confirmAction === 'delete' ? 'Delete' : 'Discard'" destructive :disabled="busy || !!running" @click="accept()" /><AppButton label="Cancel" :disabled="busy" @click="confirmation.close()" /></div></dialog>
    <dialog v-window="{ type:'popup' }" ref="historyDialog" class="record-dialog script-editor-history" :aria-label="t('Saved revisions')"><header><h2>{{ t('Saved revisions') }}</h2><AppButton label="Close" icon="close" @click="historyDialog.close()" /></header><p>{{ t('Restoring a revision changes the local draft. Save publishes it as a new revision.') }}</p><AppButton v-for="row in historyRows" :key="row.revisionId" :label="[row.timestamp, row.actor, row.changedFields.join(', ') || t('Saved version')].filter(Boolean).join(' · ')" :disabled="!editable || busy" @click="restoreRevision(row)" /></dialog>
  </Teleport>
</template>
