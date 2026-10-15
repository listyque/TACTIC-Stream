<script setup>
// DropPlateView.qml / DropPlateController: matching remains native server logic.
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { resultItems, navigationLink } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppTextField from '../../controls/AppTextField.vue'
import { asyncComponent } from '../../controls/asyncComponent.js'
import { matchingDefaults } from './matchingDefaults.js'
import { copyText } from '../../controls/clipboard.js'
import { preferences, savePreferencePage } from '../configuration/preferences.js'
import { prettySize, sourcePath, droppedFiles, prepareFiles } from './files.js'
const props = defineProps({ ticket:String, project:String, target:Object })
const emit = defineEmits(['help','queue'])
const queueCheckin = inject('queueCheckin'), checkinDescription = inject('checkinDescription',() => '')
const files = ref([]), groups = ref([]), busy = ref(false), error = ref(''), filter = ref(''), filterMode = ref('name')
const input = ref(null), directory = ref(null), templatesDialog = ref(null), templatesEditor = ref(null), templatesError = ref('')
const process = ref('publish'), context = ref('publish'), processes = ref([]), padding = ref(3)
let request = 0, targetRequest = 0
const owner = ref(null)
const selected = computed(() => groups.value.filter(group => group.checked && group.status !== 'Queued'))
const visible = computed(() => groups.value.filter(group => (filterMode.value === 'extension' ? group.extension : group.title + ' ' + group.path).toLowerCase().includes(filter.value.trim().toLowerCase().replace(/^\./,''))))
const scope = computed(() => ({ ticket:props.ticket,project:props.project }))
const MatchingTemplates = asyncComponent(() => import('./MatchingTemplates.vue'))
const templateItems = ref(structuredClone(matchingDefaults)), editingTemplates = ref(false), paddingDraft = ref(3)
try { const saved = JSON.parse(localStorage.getItem('tactic_stream.matching_templates') || 'null'); if (Array.isArray(saved?.items) && saved.items.length) { templateItems.value = saved.items; padding.value = saved.padding } } catch { /* Native defaults. */ }
const activePatterns = computed(() => templateItems.value.filter(row => row.enabled && (!row.process || row.process === process.value) && (!row.context || row.context === context.value)).map(row => row.pattern))
watch([process,context],() => { if (files.value.length) rematch() })
watch([() => props.ticket,() => props.project,() => props.target?.searchKey,() => props.target?.process,() => props.target?.context], async () => {
  const id = ++targetRequest; processes.value = []; process.value = props.target?.process || 'publish'; context.value = props.target?.context || process.value; owner.value = null
  if (props.target?.project !== props.project || !props.target?.searchKey) return
  try {
    let target = props.target
    if (target.searchKey.startsWith('sthpw/snapshot?')) { const link = await navigationLink(props.ticket,props.project,'skey://' + target.searchKey); if (!link.parent) return; target = { ...target,searchKey:link.parent.__search_key__,title:link.parent.name || link.parent.title || link.parent.code } }
    if (id !== targetRequest) return
    owner.value = target
    const result = await resultItems(props.ticket,props.project,target.searchKey.split('?')[0],[target.searchKey]); if (id === targetRequest) processes.value = result.items[0]?.branches.filter(branch => branch.kind === 'process').map(branch => ({ value:branch.process,label:branch.title })) || []
  }
  catch (failure) { if (id === targetRequest) error.value = failure.message }
}, { immediate:true })
function preference(name,value) { try { savePreferencePage('checkin',{ ...preferences.checkin,[name]:value }) } catch (failure) { error.value = failure.message } }
async function rematch() {
  const id = ++request; error.value = ''
  if (!files.value.length) { groups.value = []; busy.value = false; return }
  busy.value = true
  try {
    const matched = await prepareFiles(scope.value,files.value,{ templates:activePatterns.value,padding:padding.value })
    if (id === request) groups.value = matched.map((group,index) => ({ ...group,id:index,checked:true,status:'Matched',files:group.indices.map(index => files.value[index]) }))
  } catch (failure) { if (id === request) error.value = failure.message }
  finally { if (id === request) busy.value = false }
}
async function addFiles(incoming) {
  const known = new Set(files.value.map(sourcePath))
  const additions = [...incoming].filter(file => { const path = sourcePath(file); if (known.has(path) || !preferences.checkin.includeSubfolders && file.webkitRelativePath?.split('/').length > 2) return false; known.add(path); return true })
  files.value.push(...additions); await rematch()
}
async function drop(event) { try { await addFiles(await droppedFiles(event.dataTransfer)) } catch (failure) { error.value = failure.message } }
function remove(group) { const removing = new Set(group.files); files.value = files.value.filter(file => !removing.has(file)); rematch() }
function clear() { request++; files.value = []; groups.value = []; busy.value = false; error.value = '' }
function queue() {
  if (!owner.value?.searchKey || !selected.value.length || !context.value.trim() || busy.value) return
  try {
    const batches = preferences.checkin.groupCheckin ? [selected.value] : selected.value.map(group => [group])
    for (const batch of batches) {
      const inputs = batch.flatMap(group => group.files)
      queueCheckin({ ...scope.value,searchKey:owner.value.searchKey,title:owner.value.title || owner.value.record?.name || owner.value.record?.code,
        process:process.value,context:context.value.trim(),description:checkinDescription(),files:inputs,name:inputs[0].name,
        templates:[...activePatterns.value],padding:padding.value,source:'Drop Plate',keepFileName:preferences.checkin.keepFilename,generatePreviews:preferences.checkin.generatePreviews })
      const moved = new Set(inputs)
      files.value = files.value.filter(file => !moved.has(file))
      groups.value = groups.value.filter(group => !batch.includes(group))
    }
    emit('queue')
  } catch (failure) { error.value = failure.message }
}
function completed(job) {
  const finished = new Set(job.completedFiles || [])
  if (job.source === 'Drop Plate') { files.value = files.value.filter(file => !finished.has(file)); rematch() }
}
async function templates() { paddingDraft.value = padding.value; editingTemplates.value = true; await nextTick(); templatesDialog.value.show() }
async function saveTemplates(items) {
  try {
    localStorage.setItem('tactic_stream.matching_templates',JSON.stringify({ items,padding:Number(paddingDraft.value) })); templateItems.value = items; padding.value = Number(paddingDraft.value); closeTemplates(); rematch()
  } catch (failure) { templatesError.value = failure.message }
}
function closeTemplates() { templatesDialog.value.close(); editingTemplates.value = false }
async function pasteFiles() {
  try {
    if (!navigator.clipboard?.read) throw new Error('Paste files with Ctrl+V or choose files. Browser access to local paths is unavailable.')
    const inputs = []; for (const item of await navigator.clipboard.read()) for (const type of item.types) if (!type.startsWith('text/')) inputs.push(new File([await item.getType(type)],'clipboard.' + type.split('/')[1],{ type }))
    if (!inputs.length) throw new Error('Choose files. Browser access to pasted local paths is unavailable.')
    await addFiles(inputs)
  } catch (failure) { error.value = failure.message }
}
function localFile(group) { const url = URL.createObjectURL(group.files[0]), link = document.createElement('a'); link.href = url; link.download = group.files[0].name; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000) }
function beforeUnload(event) { if (files.value.length) { event.preventDefault(); event.returnValue = '' } }
window.addEventListener('beforeunload',beforeUnload)
onBeforeUnmount(() => { request++; targetRequest++; window.removeEventListener('beforeunload',beforeUnload) })
defineExpose({ completed, clear, pending:() => files.value.length > 0, canLeave:() => !files.value.length || window.confirm(t('Discard files on Drop Plate?')) })
</script>
<template>
  <Teleport defer to="#dock-drop_plate"><section class="drop-plate" :aria-label="t('Drop Plate')" @dragover.prevent @drop.prevent="drop" @paste="if ($event.clipboardData.files.length) { $event.preventDefault(); addFiles($event.clipboardData.files) }">
    <div class="drop-plate-toolbar"><AppButton label="Files" icon="add" :disabled="busy" @click="input.click()" /><AppButton label="Directory" icon="folder" :disabled="busy" @click="directory.click()" />
      <AppCheckbox label="Include subfolders" :model-value="preferences.checkin.includeSubfolders" @update:model-value="preference('includeSubfolders',$event)" /><AppCheckbox label="Group check-in" :model-value="preferences.checkin.groupCheckin" @update:model-value="preference('groupCheckin',$event)" /><AppCheckbox label="Keep filename" :model-value="preferences.checkin.keepFilename" @update:model-value="preference('keepFilename',$event)" />
      <span class="spacer" /><AppButton icon-only label="Paste files" icon="clipboard" :disabled="busy" @click="pasteFiles" /><AppButton icon-only label="Matching Templates" icon="tune" @click="templates" /><AppButton icon-only label="Clear" icon="delete" :disabled="busy || !files.length" @click="clear" />
    </div>
    <div class="drop-plate-filter"><AppSelect v-model="filterMode" label="Filter mode" :options="[{ value:'name',label:'Filename' },{ value:'extension',label:'Extension' }]" /><AppTextField v-model="filter" :placeholder="filterMode === 'extension' ? 'Filter by extension' : 'Filter files'" label="Filter files" /></div>
    <div class="drop-plate-groups"><div v-if="!groups.length" class="drop-plate-empty"><AppIcon name="upload" /><span>{{ t(busy ? 'Matching files…' : 'Drop files or directories here') }}</span></div>
      <article v-for="group in visible" :key="group.id" class="drop-plate-group" @contextmenu.prevent="$refs['menu' + group.id][0].openAt($event)"><AppCheckbox compact hide-label label="Select file group" v-model="group.checked" :disabled="group.status === 'Queued'" /><AppIcon :name="group.matchingType.includes('sequence') ? 'movie' : 'file'" /><div><strong>{{ group.title }}</strong><small>{{ group.sequenceInfo || group.matchingType }} · {{ group.fileCount }} {{ t('Files') }} · {{ prettySize(group.size) }}</small><small>{{ group.path || group.files[0].name }}</small></div><span>{{ t(group.status) }}</span>
        <AppMenu :ref="'menu' + group.id" label="File actions"><AppButton label="Open file" icon="open" @click="localFile(group)" /><AppButton label="Copy file path" icon="copy" @click="copyText(sourcePath(group.files[0]))" /><AppButton label="Copy all file paths" icon="copy" @click="copyText(group.files.map(sourcePath).join('\n'))" /><AppButton label="Remove from Drop Plate" icon="delete" @click="remove(group)" /></AppMenu><AppButton icon-only label="Remove from Drop Plate" icon="close" @click="remove(group)" />
      </article>
    </div>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p><footer class="drop-plate-footer"><div><span class="muted">{{ owner?.title || t('Select an object, process and context first') }}</span><div v-if="owner" class="drop-plate-target"><AppSelect v-model="process" label="Process" :options="processes" :translate-labels="false" @update:model-value="context = process" /><AppTextField v-model="context" label="Context" placeholder="Context" /></div></div><AppButton label="Add to queue" highlighted icon="queue" :disabled="busy || !owner?.searchKey || !selected.length || !context.trim()" @click="queue" /></footer>
    <input ref="input" hidden type="file" multiple @change="addFiles($event.target.files); $event.target.value = ''"><input ref="directory" hidden type="file" multiple webkitdirectory @change="addFiles($event.target.files); $event.target.value = ''">
  </section></Teleport>
  <Teleport to="body"><dialog v-window="{kind:'matching_templates', type:'window' }" ref="templatesDialog" class="record-dialog drop-plate-templates" :aria-label="t('Matching Templates')" @cancel.prevent="templatesEditor?.close()"><header><h2>{{ t('Matching Templates') }}</h2><AppButton label="Close" icon="close" @click="templatesEditor?.close()" /></header><label>{{ t('Frame padding') }}<AppTextField v-model.number="paddingDraft" type="number" min="1" max="9" label="Frame padding" /></label><MatchingTemplates v-if="editingTemplates" ref="templatesEditor" :scope="scope" :processes="processes" :context="context" :items="templateItems" :padding="Number(paddingDraft)" @save="saveTemplates" @close="closeTemplates" /><p v-if="templatesError" class="error" role="alert">{{ t(templatesError) }}</p></dialog></Teleport>
</template>
<style>
.drop-plate { display:flex; flex-direction:column; box-sizing:border-box; width:100%; height:100%; padding:10px; gap:8px; background:var(--surface-deep); min-height:0; }.drop-plate-toolbar { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }.drop-plate-toolbar .spacer { flex:1; }.drop-plate-toolbar .app-checkbox { font-size:var(--text-body); }.drop-plate-toolbar .app-button { min-height:36px; height:36px; }.drop-plate-filter { display:flex; gap:8px; }.drop-plate-filter .app-select { flex:0 0 130px; width:130px; }.drop-plate-filter .app-text-field { flex:1; }.drop-plate-groups { flex:1; min-height:0; overflow:auto; padding:7px; border:1px solid var(--outline-variant); border-radius:16px; background:var(--surface); }.drop-plate-group { display:flex; align-items:center; gap:8px; padding:8px; box-sizing:border-box; height:62px; margin-bottom:5px; border-radius:12px; background:var(--surface-high); }.drop-plate-group > .app-icon { font-size:18px; color:var(--primary); }.drop-plate-group > div { flex:1; min-width:0; }.drop-plate-group strong, .drop-plate-group small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.drop-plate-group strong { font-size:var(--text-body); }.drop-plate-group small { color:var(--muted); font-size:var(--text-caption); }.drop-plate-group > span:not(.app-icon) { color:var(--muted); font-size:var(--text-label); }.drop-plate-group .app-button.icon-button { width:30px; height:30px; min-width:30px; min-height:30px; }.drop-plate-group .app-icon { font-size:16px; }.drop-plate-empty { height:100%; min-height:120px; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:12px; color:var(--muted); }.drop-plate-empty .app-icon { font-size:32px; }.drop-plate-footer { display:flex; gap:12px; align-items:center; margin:0; }.drop-plate-footer > div { flex:1; min-width:0; }.drop-plate-target { display:flex; gap:8px; margin-top:6px; }.drop-plate-target > * { min-width:0; flex:1; }.drop-plate-templates { width:min(620px, calc(100vw - 24px)); }.drop-plate-templates > label { display:flex; align-items:center; gap:12px; margin:12px 0; }.drop-plate-templates textarea { width:100%; box-sizing:border-box; font-family:var(--font-mono); }
</style>
