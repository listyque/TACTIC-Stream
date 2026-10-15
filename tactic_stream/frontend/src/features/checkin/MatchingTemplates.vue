<script setup>
// Handler MatchingTemplatesView.qml / MatchingTemplatesController (EPL-1.0).
import { computed, onMounted, ref } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckBox.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
const props = defineProps({ scope:Object, items:Array, padding:Number, processes:Array, context:String })
const emit = defineEmits(['save','close'])
const rows = ref(props.items.map(row => ({ ...row }))), selectedIndex = ref(0), width = ref(440), example = ref(''), result = ref(''), matchedType = ref(''), error = ref(''), busy = ref(false)
const selected = computed(() => rows.value[selectedIndex.value])
const workspace = ref(null)
onMounted(() => { width.value = Math.max(300,workspace.value.clientWidth * .48) })
const initialPadding = props.padding
const dirty = computed(() => props.padding !== initialPadding || JSON.stringify(rows.value.map(({ preview,matchingType,validationError,...row }) => row)) !== JSON.stringify(props.items.map(({ preview,matchingType,validationError,...row }) => row)))
let request = 0
async function inspect(test = false) {
  const id = ++request; error.value = ''; result.value = ''; busy.value = true
  try {
    const patterns = test ? [selected.value.pattern] : rows.value.map(row => row.pattern)
    const response = (await rpc('execute_cmd',[props.scope,'tactic.command.browser_checkin_cmd.BrowserCheckinCmd', { action:'templates',templates:patterns,padding:props.padding,example:test ? example.value.trim() : '' }],{},true)).info.templates
    if (id !== request) return false
    for (const row of rows.value) { const value = response.find(item => item.pattern === row.pattern); if (value) { row.preview = value.preview; row.matchingType = value.matchingType; row.validationError = value.validationError } }
    error.value = test ? response[0].validationError : rows.value.find(row => row.enabled && row.validationError)?.validationError || ''
    if (test) { matchedType.value = response[0].matched; result.value = !example.value.trim() ? 'Enter a filename to test' : matchedType.value ? 'Matched as {type}' : 'No match' }
    return !error.value
  } catch (failure) { if (id === request) error.value = failure.message; return false }
  finally { if (id === request) busy.value = false }
}
function select(index) { selectedIndex.value = index; result.value = ''; error.value = '' }
function create(duplicate = false) {
  const item = duplicate ? { ...selected.value,locked:false } : { enabled:true,pattern:'$FILENAME.$EXT',process:'',context:'',locked:false }
  const index = duplicate ? selectedIndex.value + 1 : rows.value.length
  rows.value.splice(index,0,item); select(index); inspect()
}
function move(offset) { const index = selectedIndex.value, target = index + offset; if (target < 0 || target >= rows.value.length) return; rows.value.splice(target,0,...rows.value.splice(index,1)); select(target) }
function remove() { if (selected.value.locked) return; rows.value.splice(selectedIndex.value,1); select(Math.min(selectedIndex.value,rows.value.length - 1)) }
async function save() { if (await inspect()) emit('save',rows.value.map(({ preview,matchingType,matched,validationError,...row }) => row)) }
function close() { if (!dirty.value || window.confirm(t('Discard unsaved changes?'))) emit('close') }
defineExpose({ close })
inspect()
</script>
<template>
  <div ref="workspace" class="matching-templates-workspace">
    <section class="matching-template-list" :style="{ '--template-width':width + 'px' }">
      <header><strong>{{ t('Matching templates') }}</strong><AppButton icon-only label="Add" icon="add" :disabled="rows.length >= 32" @click="create()" /><div class="matching-template-actions"><AppButton icon-only label="Duplicate" icon="copy" :disabled="rows.length >= 32" @click="create(true)" /><AppButton icon-only label="Move up" icon="MDI_ARROW_UP" :disabled="selectedIndex === 0" @click="move(-1)" /><AppButton icon-only label="Move down" icon="MDI_ARROW_DOWN" :disabled="selectedIndex === rows.length - 1" @click="move(1)" /><AppButton icon-only label="Delete" icon="delete" :disabled="selected?.locked" @click="remove" /></div><AppMenu class="matching-template-overflow" label="Template actions"><AppButton label="Duplicate" icon="copy" @click="create(true)" :disabled="rows.length >= 32" /><AppButton label="Move up" icon="MDI_ARROW_UP" :disabled="selectedIndex === 0" @click="move(-1)" /><AppButton label="Move down" icon="MDI_ARROW_DOWN" :disabled="selectedIndex === rows.length - 1" @click="move(1)" /><AppButton label="Delete" icon="delete" :disabled="selected?.locked" @click="remove" /></AppMenu></header>
      <div class="matching-template-rows"><article v-for="(row,index) in rows" :key="index" :class="{ selected:index === selectedIndex }"><AppCheckbox compact hide-label label="Enable template" v-model="row.enabled" :disabled="row.locked" @update:model-value="inspect" /><small>{{ index + 1 }}</small><AppButton :label="row.pattern" @click="select(index)"><strong>{{ row.pattern }}</strong><small>{{ row.validationError || row.preview || row.pattern }}</small><small>{{ row.matchingType }}<template v-if="row.process"> · {{ row.process }}</template><template v-if="row.context"> · {{ row.context }}</template></small></AppButton></article></div>
    </section>
    <AppSplitter v-model="width" :min="260" :max="650" label="Templates pane width" />
    <section class="matching-template-editor"><strong>{{ t('Template properties') }}</strong><label>{{ t('Pattern') }}<AppTextField v-model="selected.pattern" label="Pattern" :disabled="selected.locked" @change="inspect" /></label><small class="muted">{{ t("Preview: {preview} · Type: {type}",{ preview:selected.preview || selected.pattern,type:selected.matchingType || "—" }) }}</small>
      <div class="matching-template-mapping"><label>{{ t('Process mapping') }}<AppTextField v-model="selected.process" label="Process mapping" list="matching-process-options" placeholder="All processes" :disabled="selected.locked" /></label><label>{{ t('Context mapping') }}<AppTextField v-model="selected.context" label="Context mapping" list="matching-context-options" placeholder="All contexts" :disabled="selected.locked" /></label></div>
      <label>{{ t('Test on filename') }}<div class="matching-template-test"><AppTextField v-model="example" label="Test on filename" placeholder="shot.001.exr" @keydown.enter.prevent="inspect(true)" /><AppButton label="Test" icon="search" :disabled="busy" @click="inspect(true)" /></div></label><p v-if="result" :class="{ error:result === 'No match' }" role="status">{{ t(result,{type:matchedType}) }}</p><p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <footer><span class="muted">{{ dirty ? t('Unsaved changes') : '' }}</span><AppButton label="Cancel" @click="close" /><AppButton label="Save" icon="save" highlighted :disabled="!dirty || busy" @click="save" /></footer>
    </section>
    <datalist id="matching-process-options"><option v-for="process in processes || []" :key="process.value" :value="process.value" /></datalist><datalist id="matching-context-options"><option :value="context" /></datalist>
  </div>
</template>
<style>
.matching-templates-workspace { display:flex; flex:1; min-height:0; min-width:0; gap:0; background:var(--surface-deep); padding:12px; container:templates / inline-size; }.matching-template-list { flex:0 1 var(--template-width); min-width:250px; display:flex; flex-direction:column; }.matching-template-list, .matching-template-editor { border:1px solid var(--outline-variant); background:var(--surface-low); border-radius:16px; padding:9px; min-height:0; }.matching-template-list > header { display:flex; align-items:center; gap:6px; margin-bottom:7px; }.matching-template-list > header strong { flex:1; font-size:12px; }.matching-template-rows { overflow:auto; flex:1; }.matching-template-rows article { display:flex; align-items:center; gap:8px; padding:8px; height:64px; box-sizing:border-box; margin-bottom:5px; background:var(--surface-high); border-radius:12px; }.matching-template-rows article.selected { background:var(--content-selection); }.matching-template-rows .app-button { flex:1; min-width:0; display:flex; flex-direction:column; align-items:flex-start; gap:1px; background:transparent; border:0; height:auto; padding:0; text-align:left; }.matching-template-rows .app-button > * { display:block; max-width:100%; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.matching-template-rows small { color:var(--muted); font-size:var(--text-caption); font-weight:400; }.matching-template-editor { flex:1; min-width:0; display:flex; flex-direction:column; gap:10px; padding:14px; overflow:auto; }.matching-template-editor > strong { font-size:14px; }.matching-template-editor label { display:flex; flex-direction:column; gap:7px; color:var(--muted); font-size:var(--text-label); }.matching-template-editor .app-text-field { width:100%; box-sizing:border-box; }.matching-template-mapping { display:grid; grid-template-columns:1fr; gap:8px; }.matching-template-mapping > label { flex-direction:row; align-items:center; justify-content:space-between; }.matching-template-mapping .app-text-field { flex:0 1 72%; width:72%; }.matching-template-test { display:flex; gap:8px; }.matching-template-editor footer { margin-top:auto; display:flex; align-items:center; gap:8px; }.matching-template-editor footer > span { flex:1; }.drop-plate-templates.record-dialog { display:none; width:min(1040px,calc(100vw - 24px)); height:min(760px,calc(100dvh - 24px)); padding:10px; overflow:hidden; }.drop-plate-templates.record-dialog[open] { display:flex; flex-direction:column; }.drop-plate-templates > header { flex-shrink:0; }.drop-plate-templates > label { flex-shrink:0; }
.matching-template-list { container:templatelist / inline-size; }.matching-template-actions { display:flex; gap:6px; }.matching-template-overflow { display:none; }.matching-template-list header .app-button.icon-button { width:30px; height:30px; min-width:30px; min-height:30px; }
@container templatelist (max-width:400px) { .matching-template-actions { display:none; }.matching-template-overflow { display:block; } }
@container templates (max-width:650px) { .matching-template-mapping { grid-template-columns:1fr; } }
@media(max-width:700px) { .matching-templates-workspace { flex-direction:column; overflow:auto; }.matching-template-list { flex:0 0 220px; min-width:0; }.matching-templates-workspace > .app-splitter { display:none; }.matching-template-editor { flex:0 0 auto; min-height:330px; } }
</style>
