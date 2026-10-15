<script setup>
// Current Handler ScriptShelfBar.qml / ScriptShelfEditorView.qml and script_shelf.py (EPL-1.0).
import { inject, ref, computed, watch, onBeforeUnmount } from 'vue'
import { scriptShelf, rpc, beginActivity, endActivity } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import IconPicker from '../../controls/IconPicker.vue'
import ScriptPicker from './ScriptPicker.vue'
import { effectiveShelf, globalShelf, buttonId, runBrowserScript } from './scriptShelf.js'
import './scriptShelf.css'

const openHelp = inject('openHelp')
const props = defineProps({ ticket: String, project: String, login: String, entryKey: String, preset: String, title: String, visible: Boolean, searchType: String, searchKeys: Array, updates: Object })
const emit = defineEmits(['saved', 'executed', 'closed'])
const dialog = ref(null), confirmation = ref(null), outputDialog = ref(null)
const catalog = ref(null), busy = ref(false), error = ref(''), uncertain = ref(false), running = ref(''), output = ref('')
const mode = ref('shared'), modeSelected = ref(false), owner = ref('personal'), scope = ref('global'), selected = ref('')
const title = ref(''), buttons = ref([]), baseline = ref(''), confirmAction = ref(''), pending = ref(null)
const editorScope = ref(null)
const contextChanged = computed(() => !!editorScope.value && (editorScope.value.ticket !== props.ticket || editorScope.value.project !== props.project))
const editorEntryKey = computed(() => editorScope.value?.entryKey || '')
let generation = 0, reloadPending = false
const shelves = computed(() => catalog.value?.shelves || [])
const scripts = computed(() => catalog.value?.scripts || [])
const presets = computed(() => shelves.value.filter(row => !row.personal && row.view !== globalShelf).sort((a, b) => a.title.localeCompare(b.title)))
const effective = computed(() => effectiveShelf(shelves.value, mode.value, props.entryKey, props.preset))
const current = computed(() => shelves.value.find(row => row.code === selected.value))
const canRename = computed(() => owner.value === 'shared' && scope.value === 'tab')
const canRemove = computed(() => !!current.value && (owner.value === 'personal' || current.value.view !== globalShelf))
const draft = computed(() => ({ mode: owner.value, title: title.value, configuration: { scope: owner.value === 'shared' && scope.value === 'tab' ? 'preset' : scope.value,
  entryKey: owner.value === 'personal' && scope.value === 'tab' ? editorEntryKey.value : '', buttons: buttons.value } }))
const dirty = computed(() => JSON.stringify(draft.value) !== baseline.value)
const assignmentPending = computed(() => canRename.value && !!current.value && !!editorEntryKey.value && editorScope.value?.preset !== current.value.view)
const ready = computed(() => !!catalog.value && (owner.value === 'personal' || scope.value === 'global' || !!selected.value || !!title.value))
const removeName = computed(() => current.value?.title || title.value)
const deleteTitle = computed(() => t(owner.value === 'personal' ? 'Remove “{name}”?' : 'Delete “{name}”?', { name: removeName.value }))
function modeKey() { return 'tactic_stream.script_shelf.' + props.login }
function setMode(value) { mode.value = value; modeSelected.value = true; try { localStorage.setItem(modeKey(), value) } catch {} }
function script(path) { return scripts.value.find(row => row.path === path) }
function runnable(button) { return !!script(button.script)?.executable }
function tooltip(button) { return runnable(button) ? button.description || button.title : t('This script is unavailable. Browser JavaScript, server Python and server JavaScript with execution permission are supported.') + '\n' + button.script }
async function load() {
  reloadPending = false
  const id = ++generation; busy.value = true; error.value = ''
  try {
    const result = await scriptShelf('read', props.ticket, props.project)
    if (id !== generation) return
    catalog.value = result; uncertain.value = false
    if (!modeSelected.value) mode.value = effectiveShelf(result.shelves, 'personal', props.entryKey)?.configuration ? 'personal' : 'shared'
  } catch (exception) { if (id === generation) error.value = exception.message }
  finally { if (id === generation) busy.value = false }
}
watch(() => [props.ticket, props.project, props.login], () => {
  generation++; catalog.value = null; error.value = ''; busy.value = false; running.value = ''; modeSelected.value = false
  let saved; try { saved = localStorage.getItem(modeKey()) } catch {}
  if (['personal', 'shared'].includes(saved)) { mode.value = saved; modeSelected.value = true }
  if (props.visible && props.ticket) load()
}, { immediate: true })
watch(() => props.visible, value => { if (value && !catalog.value && props.ticket) load() })
function refreshUpdates() {
  if (reloadPending && !busy.value && !running.value && (props.visible || dialog.value?.open) && (!dialog.value?.open || !dirty.value)) {
    if (dialog.value?.open) refresh()
    else load()
  }
}
watch(() => props.updates, batch => {
  if ([...(batch?.cacheChanges || []), ...(batch?.cacheRetired || [])].some(row => row.projectCode === props.project && ['config/widget_config', 'config/custom_script'].includes(row.searchType))) { reloadPending = true; refreshUpdates() }
})
watch([() => props.visible, busy, running, dirty], refreshUpdates)
onBeforeUnmount(() => { generation++ })
function selectNow(target) {
  if (contextChanged.value) { error.value = 'Connection context changed. Close this form and reopen it before saving.'; return }
  if (editorScope.value && catalog.value) editorScope.value.revision = catalog.value.revision
  owner.value = target.owner; scope.value = target.scope; selected.value = target.code || ''; error.value = ''
  let row = target.code ? shelves.value.find(row => row.code === target.code) : owner.value === 'personal'
    ? shelves.value.find(row => row.personal && row.configuration?.scope === scope.value && (scope.value === 'global' || row.configuration.entryKey === editorEntryKey.value))
    : scope.value === 'global' ? shelves.value.find(row => !row.personal && row.view === globalShelf) : null
  selected.value = row?.code || ''
  title.value = row?.title || (owner.value === 'personal' ? 'My shelf' : scope.value === 'global' ? 'Shared shelf' : target.new ? t('New shelf') : '')
  buttons.value = JSON.parse(JSON.stringify(row?.configuration?.buttons || []))
  baseline.value = JSON.stringify(draft.value)
  if (row && !row.valid) error.value = row.error
}
function select(target) { if (busy.value || running.value) return; if (dirty.value) { pending.value = target; confirm('select') } else selectNow(target) }
async function open() {
  if (dialog.value.open) { dialog.value.show(); if (!contextChanged.value && !catalog.value) await load(); return }
  editorScope.value = { ticket:props.ticket, project:props.project, entryKey:props.entryKey, preset:props.preset, title:props.title }
  dialog.value.show(); confirmAction.value = ''; baseline.value = ''
  if (!catalog.value || reloadPending) await load()
  if (!catalog.value) return
  const row = effective.value
  selectNow({ owner: mode.value === 'shared' && catalog.value.canManage ? 'shared' : 'personal', scope: row?.configuration?.scope === 'global' ? 'global' : props.entryKey ? 'tab' : 'global', code: mode.value === 'shared' && !catalog.value.canManage ? '' : row?.code })
}
function close() { if (busy.value || running.value) return; if (dirty.value && editorScope.value) confirm('close'); else { dialog.value.close(); emit('closed') } }
function canLeave() { if (!dialog.value?.open) return true; if (busy.value || running.value) return false; if (dirty.value && editorScope.value) { confirm('close'); return false }; return true }
function confirm(action) { confirmAction.value = action; confirmation.value.showModal() }
function accept() {
  const action = confirmAction.value; confirmation.value.close(); confirmAction.value = ''
  if (action === 'delete') return write('delete')
  if (action === 'close') { dialog.value.close(); emit('closed') }
  if (action === 'select') selectNow(pending.value)
  if (action === 'reload') refresh()
}
function add() {
  const first = scripts.value.find(row => row.runnable)
  if (first) buttons.value.push({ id: buttonId(), title: first.title, description: '', icon: 'play-arrow', script: first.path })
}
function move(index, delta) { buttons.value.splice(index + delta, 0, buttons.value.splice(index, 1)[0]) }
async function refresh() {
  const target = { owner: owner.value, scope: scope.value, code: selected.value }
  await load(); if (catalog.value && !error.value) selectNow(target)
}
async function write(action) {
  if (contextChanged.value) { error.value = 'Connection context changed. Close this form and reopen it before saving.'; return }
  if (busy.value || running.value || uncertain.value) return
  busy.value = true; error.value = ''; const id = generation
  try {
    const values = { code: selected.value, revision: editorScope.value.revision }
    if (action === 'save') Object.assign(values, draft.value)
    if ((action === 'save' && canRename.value) || action === 'assign') values.entry_key = editorEntryKey.value
    const result = await scriptShelf(action, props.ticket, props.project, values)
    if (id !== generation) return
    catalog.value = result; setMode(owner.value)
    if (action === 'save') selected.value = result.savedCode
    selectNow({ owner: owner.value, scope: scope.value, code: action === 'delete' ? '' : selected.value })
    emit('saved')
  } catch (exception) {
    if (id === generation) { error.value = exception.message; uncertain.value = !['invalid_request', 'access_denied'].includes(exception.code) }
  } finally { if (id === generation) busy.value = false }
}
async function run(button) {
  if (running.value || busy.value || !runnable(button)) return
  running.value = button.id; error.value = ''; const id = generation
  const context = { ticket: props.ticket, project: props.project, searchType: props.searchType, searchKeys: [...(props.searchKeys || [])] }
  const activity = beginActivity(context.ticket, 'Running…')
  try {
    let result
    if (script(button.script).language === 'javascript') {
      const saved = await scriptShelf('script', context.ticket, context.project, { path: button.script })
      if (id !== generation) return
      result = await runBrowserScript(saved.script, { project: context.project, searchType: context.searchType, searchKeys: context.searchKeys,
        rpc: (method, args = [], kwargs = {}) => rpc(method, [{ ticket: context.ticket, project: context.project }, ...args], kwargs),
        refresh: () => { if (id === generation) emit('executed') } })
    } else result = await rpc(script(button.script).language === 'server_js' ? 'execute_js_script' : 'execute_python_script', [{ ticket: context.ticket, project: context.project }, button.script, {}])
    if (id === generation) { output.value = JSON.stringify(result, null, 2) ?? 'None'; outputDialog.value.show(); emit('executed') }
  } catch (exception) { if (id === generation) { error.value = exception.message; output.value = exception.message; outputDialog.value.show() } }
  finally { endActivity(activity); if (id === generation) running.value = '' }
}
defineExpose({ open, reload: load, canLeave })
</script>

<template>
  <Teleport v-if="visible" defer to="#workspace-script-shelf"><div class="script-shelf-bar" :aria-label="t('Script shelf')" :aria-busy="busy || !!running">
    <div class="script-shelf-modes"><AppButton icon-only icon="MDI_ACCOUNT" label="My shelf" :aria-pressed="mode === 'personal'" :highlighted="mode === 'personal'" @click="setMode('personal')" /><AppButton icon-only icon="MDI_ACCOUNT_GROUP" label="Shared shelf" :aria-pressed="mode === 'shared'" :highlighted="mode === 'shared'" @click="setMode('shared')" /></div>
    <div class="script-shelf-buttons" @wheel="event => { if (event.deltaY && event.currentTarget.scrollWidth > event.currentTarget.clientWidth) { event.preventDefault(); event.currentTarget.scrollLeft += event.deltaY } }">
      <AppButton v-for="button in effective?.configuration.buttons || []" :key="button.id" class="script-shelf-button" :label="button.title" :title="tooltip(button)" :disabled="busy || !!running || !runnable(button)" @click="run(button)"><AppIcon :name="button.icon" /><small>{{ button.title }}</small></AppButton>
      <span v-if="busy || running" class="muted">{{ t('Running…') }}</span><span v-else-if="!effective?.configuration.buttons.length" class="muted">{{ t('No buttons') }}</span>
    </div>
    <AppButton icon-only icon="edit" label="Edit script shelf" :disabled="busy || !!running" @click="open" />
    <AppButton v-if="error" icon-only icon="warning" :label="error" @click="open" />
  </div></Teleport>
  <Teleport to="body">
    <dialog v-window="{kind:'script_shelf_editor', type:'window' }" ref="dialog" class="script-shelf-dialog" :aria-label="t('Script Shelf')" @cancel.prevent="close" @close="refreshUpdates">
      <header class="script-shelf-heading"><AppIcon name="code" /><strong>{{ t('Script Shelf') }}</strong><AppButton icon-only icon="refresh" label="Reload shelves" :disabled="busy" @click="dirty ? confirm('reload') : refresh()" /><AppButton icon-only icon="close" label="Close script shelf" :disabled="busy || !!running" @click="close" /></header>
      <div class="script-shelf-editor" :aria-busy="busy">
        <aside class="script-shelf-presets">
          <div class="script-shelf-owners"><AppSegmentedButton :model-value="owner" :options="[{ value: 'personal', label: 'Mine', icon: 'MDI_ACCOUNT' }, ...(catalog?.canManage ? [{ value: 'shared', label: 'Shared', icon: 'MDI_ACCOUNT_GROUP' }] : [])]" label="Shelf owner" :disabled="busy || dirty" @update:model-value="select({ owner: $event, scope: 'global' })" /><AppButton icon-only icon="help" label="Script shelf help" @click="openHelp('script_shelf')" /></div>
          <AppButton :label="owner === 'shared' ? 'Shared shelf' : 'All tabs'" :icon="scope === 'global' ? 'MDI_CHECK' : 'MDI_EARTH'" :highlighted="scope === 'global'" :disabled="busy || dirty" @click="select({ owner, scope: 'global' })" />
          <template v-if="owner === 'personal'"><AppButton label="Only this tab" :highlighted="scope === 'tab'" :disabled="busy || dirty || !editorEntryKey" @click="select({ owner, scope: 'tab' })" /><small class="muted">{{ title ? editorScope?.title : '' }}</small></template>
          <template v-else><div class="script-shelf-presets-title"><strong>{{ t('Tab shelves') }}</strong><AppButton icon-only icon="add" label="New shelf" :disabled="busy || dirty" @click="select({ owner, scope: 'tab', new: true })" /></div><div class="script-shelf-preset-list"><AppButton v-for="row in presets" :key="row.code" :label="row.title" :icon="selected === row.code ? 'MDI_CHECK' : 'MDI_VIEW_AGENDA'" :highlighted="selected === row.code" :disabled="busy || dirty" @click="select({ owner, scope: 'tab', code: row.code })" /></div></template>
        </aside>
        <section class="script-shelf-edit-content">
          <div class="script-shelf-title"><input v-if="canRename" v-model="title" :placeholder="t('Shelf name')" :aria-label="t('Shelf name')" :disabled="busy || !catalog?.canWrite" maxlength="256"><strong v-else>{{ t(owner === 'personal' ? 'My shelf' : 'Shared shelf') }}</strong><AppButton v-if="canRename && editorEntryKey && current" :label="assignmentPending ? 'Apply to this tab' : 'Used on this tab'" :disabled="busy || dirty || !assignmentPending || uncertain || !catalog?.canWrite" @click="write('assign')" /></div>
          <div class="script-shelf-list-heading"><strong>{{ t('Shelf buttons') }}</strong><AppButton label="Add button" icon="add" :disabled="!ready || busy || !catalog?.canWrite || !scripts.some(row => row.runnable)" @click="add" /></div>
          <p v-if="contextChanged" class="notice">{{ t('Connection context changed. Close this form and reopen it before saving.') }}</p>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
          <p v-if="catalog && !catalog.canWrite" class="muted">{{ t('Saving script shelves currently requires administrator access in the TACTIC core.') }}</p>
          <p v-if="uncertain" class="muted">{{ t('Reload before trying again. Your draft remains open.') }}</p>
          <div class="script-shelf-editor-list">
            <fieldset v-for="(button, index) in buttons" :key="button.id" class="script-shelf-editor-row" :class="{ unavailable: !script(button.script)?.runnable }" :disabled="busy || uncertain || !catalog?.canWrite" :inert="busy || uncertain || !catalog?.canWrite">
              <IconPicker v-model="button.icon" icon-only /><div class="script-shelf-button-fields"><div class="script-shelf-button-main"><input v-model="button.title" :placeholder="t('Button label')" :aria-label="t('Button label')" maxlength="256"><ScriptPicker v-model="button.script" :scripts="scripts" /><AppButton icon-only icon="MDI_ARROW_UP" label="Move up" :disabled="index === 0" @click="move(index, -1)" /><AppButton icon-only icon="MDI_ARROW_DOWN" label="Move down" :disabled="index === buttons.length - 1" @click="move(index, 1)" /><AppButton icon-only destructive icon="delete" label="Remove button" @click="buttons.splice(index, 1)" /></div><input v-model="button.description" :placeholder="t('Description shown on hover')" :aria-label="t('Description shown on hover')" maxlength="4096"></div>
            </fieldset>
            <div v-if="!buttons.length" class="script-shelf-empty"><AppIcon name="MDI_VIEW_AGENDA" /><strong>{{ t(ready ? 'Add the first script button' : 'No shelf selected') }}</strong><p class="muted">{{ t(ready ? 'Only saved executable scripts are listed.' : 'Choose a shelf above or create a new one.') }}</p></div>
          </div>
          <footer v-if="ready"><AppButton v-if="canRemove" destructive icon="delete" :label="t(owner === 'personal' ? 'Remove “{name}”' : 'Delete “{name}”', { name: removeName })" :disabled="contextChanged || busy || uncertain || !catalog?.canWrite" @click="confirm('delete')" /><span></span><AppButton v-if="dirty" label="Discard" icon="MDI_UNDO" :disabled="busy" @click="selectNow({ owner, scope, code: selected })" /><AppButton highlighted label="Save shelf" icon="save" :disabled="contextChanged || busy || uncertain || !catalog?.canWrite || (!dirty && !assignmentPending && !!current)" @click="write('save')" /></footer>
        </section>
      </div>
    </dialog>
    <dialog ref="confirmation" class="record-dialog script-shelf-confirm" :aria-label="confirmAction === 'delete' ? deleteTitle : t('Discard changes?')">
      <h2>{{ confirmAction === 'delete' ? deleteTitle : t('Discard changes?') }}</h2><p>{{ t(confirmAction === 'delete' ? owner === 'personal' ? 'The personal shelf will be removed. Shared shelves will not change.' : 'The shared shelf and its sidebar assignments will be deleted. Affected tabs will use the project shelf.' : 'Discard unsaved changes to this shelf?') }}</p><footer><AppButton :label="confirmAction === 'delete' ? owner === 'personal' ? 'Remove' : 'Delete' : 'Discard'" destructive @click="accept" /><AppButton label="Cancel" @click="confirmation.close()" /></footer></dialog>
    <dialog v-window="{ type:'window' }" ref="outputDialog" class="record-dialog script-shelf-output" :aria-label="t('Script result')"><header><h2>{{ t('Script result') }}</h2><AppButton label="Close" icon="close" @click="outputDialog.close()" /></header><pre tabindex="0">{{ output }}</pre></dialog>
  </Teleport>
</template>

