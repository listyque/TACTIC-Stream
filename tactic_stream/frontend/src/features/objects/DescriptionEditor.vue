<script setup>
// Handler DescriptionEditor.qml / state_detail_editing.py (EPL-1.0).
import { computed, inject, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppIcon from '../../controls/AppIcon.vue'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import { linkifyPlainText } from '../../controls/richText.js'
import { browserLink } from '../workspace/links.js'
const props = defineProps({ ticket:String, project:String, target:Object })
const emit = defineEmits(['saved','session-expired'])
const openObjectTab = inject('openObjectTab',null)
const drafts = reactive(new Map()), current = ref(''), pinned = ref(null), editor = ref(null)
const entry = computed(() => drafts.get(current.value))
const pinActive = computed(() => pinned.value?.project === props.project)
const value = computed({
  get() {
    if (pinActive.value) return pinned.value.value
    if (!entry.value) return ''
    return entry.value.editing || entry.value.saving ? entry.value.value : entry.value.original
  },
  set(text) { if (pinActive.value) pinned.value.value = text; else if (entry.value) entry.value.value = text },
})
const dirty = computed(() => !!entry.value && entry.value.value !== entry.value.original)
const retained = computed(() => [...drafts.entries()].filter(([,item]) => item.project === props.project && item.value !== item.original))
const html = computed(() => linkifyPlainText(value.value,link => browserLink(link,props.project)))
function activateLink(event) {
  const link = event.target.closest('[data-rich-link]')?.dataset.richLink
  if (link && openObjectTab && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !event.button) { event.preventDefault(); openObjectTab(link,props.project) }
}
watch(() => [props.target,props.project], () => {
  const target = props.target
  if (!target || target.project !== props.project) { current.value = ''; return }
  const key = target.project + ':' + target.id
  let item = drafts.get(key)
  const original = String(target.record?.description || target.record?.detail || '')
  if (!item) { item = { ...target,original,value:original,editing:false,saving:false,error:'' }; drafts.set(key,item) }
  else { item.title = target.title; if (!item.saving && item.value === item.original) item.value = item.original = original }
  current.value = key
}, { immediate:true })
function edit() { entry.value.editing = true; nextTick(() => editor.value?.focus()) }
function resumeDraft(key) { current.value = key; if (pinActive.value) pinned.value = null; edit() }
function discard() { entry.value.value = entry.value.original; entry.value.editing = false; entry.value.error = '' }
function pin() { pinned.value = { project:props.project,value:value.value }; discard() }
function unpin() { pinned.value = null; if (entry.value) { entry.value.editing = false; entry.value.error = '' } }
async function save() {
  const item = entry.value
  if (!item?.searchKey || item.saving || item.value === item.original) return
  const text = item.value, ticket = props.ticket
  item.saving = true; item.editing = false; item.error = ''
  try {
    await rpc('update',[{ ticket,project:item.project },item.searchKey,{ description:text }])
    item.original = text; item.editing = false; item.record.description = text
    emit('saved',item.searchKey,text)
  } catch (failure) {
    item.editing = true; item.error = failure instanceof TypeError ? 'Unable to reach the server.' : failure.message
    if (failure.code === 'authentication_failed') emit('session-expired')
  } finally { item.saving = false }
}
function canLeave() { return ![...drafts.values()].some(item => item.saving) && (![...drafts.values()].some(item => item.value !== item.original) || window.confirm(t('Discard unsaved descriptions?'))) }
function beforeUnload(event) { if ([...drafts.values()].some(item => item.saving || item.value !== item.original)) { event.preventDefault(); event.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload',beforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload',beforeUnload))
defineExpose({ canLeave,pinnedValue:() => pinActive.value ? pinned.value.value : '' })
</script>
<template>
  <Teleport defer to="#dock-description">
    <section class="description-editor" :class="{ pinned:pinActive, editing:entry?.editing, saving:entry?.saving }" :aria-label="t('Description editor')" @keydown.esc="entry?.editing && !entry.saving && discard()">
      <header><AppIcon :name="pinActive ? 'pin' : entry?.kind === 'snapshot' ? 'snapshot' : entry?.kind === 'process' ? 'settings-suggest' : 'description'" /><strong>{{ entry?.title || t('Description') }}</strong><small v-if="entry?.saving || pinActive || entry?.editing">{{ t(entry?.saving ? 'Saving…' : pinActive ? 'Used for check-in' : dirty ? 'Unsaved' : 'Editing') }}</small></header>
      <AppSelect v-if="retained.length > 1 || retained.some(([key]) => key !== current || !entry?.editing && !entry?.saving && !pinActive)" :model-value="entry?.editing ? current : ''" label="Retained description drafts" :options="[{ value:'',label:'Retained description drafts',disabled:true },...retained.map(([key,item]) => ({ value:key,label:item.title }))]" @update:model-value="resumeDraft" />
      <div class="description-field" :class="{ editing:entry?.editing || pinActive, 'error-outline':!!entry?.error }">
        <AppTextArea v-if="entry?.editing || pinActive" ref="editor" v-model="value" label="Description" :aria-invalid="!!entry?.error" :disabled="entry?.saving" />
        <div v-else class="description-read" @click="activateLink"><div v-if="value" v-html="html"></div><p v-else class="muted">{{ t(entry ? 'No description' : 'Select an sObject, process or snapshot') }}</p></div>
        <footer>
          <p v-if="entry?.error" class="error" role="alert">{{ t(entry.error) }}</p>
          <div class="description-actions">
            <AppButton v-if="!entry?.editing && !pinActive" icon="edit" icon-only label="Edit description" :disabled="!entry || entry.saving" @click="edit" />
            <template v-if="entry?.editing && !pinActive"><AppButton class="description-discard" icon="close" icon-only label="Discard changes" :disabled="entry.saving" @click="discard" /><AppButton class="description-save" icon="save" icon-only label="Save description" :tooltip="entry.searchKey ? 'Save description' : 'This item has no description field'" :disabled="!entry.searchKey || !dirty || entry.saving" @click="save" /><AppButton class="description-pin" icon="pin" icon-only label="Use this text for check-in" :disabled="entry.saving" @click="pin" /></template>
            <AppButton v-if="pinActive" class="description-pin" icon="MDI_LOCK_OPEN_VARIANT" icon-only label="Stop using this text for check-in" :disabled="entry?.saving" @click="unpin" />
          </div>
        </footer>
      </div>
    </section>
  </Teleport>
</template>
<style scoped>
.description-editor { height:100%; min-height:0; display:flex; flex-direction:column; gap:6px; padding:8px; background:var(--surface); border-radius:calc(var(--surface-radius) - 1px); }
.description-editor > header { display:flex; align-items:center; gap:6px; height:16px; flex:none; line-height:16px; }
.description-editor > header .app-icon { --icon-size:15px; color:var(--muted); }
.description-editor.editing > header .app-icon { color:var(--primary); }
.description-editor > header strong { flex:1; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; font-size:var(--text-label); font-weight:600; }
.description-editor > header small { font-size:var(--text-caption); color:var(--primary); font-weight:600; }
.description-editor.saving > header small { color:var(--muted); }
.description-editor.pinned > header small,.description-editor.pinned > header .app-icon,.description-pin { color:var(--tertiary); }
.description-field { flex:1; min-height:0; position:relative; border:1px solid var(--outline); border-radius:var(--surface-radius); background:var(--surface-high); overflow:hidden; }
.description-field.editing { border:2px solid var(--primary); }
.pinned .description-field.editing { border-color:var(--tertiary); }
.description-editor .description-field.error-outline { border-color:var(--error); }
.description-field textarea { width:100%; height:100%; min-height:0; resize:none; border:0; border-radius:0; padding:9px 10px 36px; font-size:var(--text-caption); background:transparent; }
.description-field textarea:focus { border:0; padding:9px 10px 36px; }
.description-read { height:100%; overflow:auto; padding:9px 11px 37px; font-size:var(--text-body); }
.description-read p { margin:0; }
/* Qt draws its outline without consuming the editor's action-row margins. */
.description-field footer { position:absolute; bottom:4px; right:6px; left:11px; display:flex; align-items:center; gap:6px; }
.description-field.editing footer { bottom:3px; right:5px; left:10px; }
.description-field footer .error { flex:1; min-width:0; max-height:16px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin:0; padding:0; border:0; border-radius:0; background:transparent; font-size:var(--text-caption); }
.description-actions { margin-left:auto; display:flex; gap:2px; }
.description-actions .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; max-width:28px; max-height:28px; flex:none; padding:0; border:0; --icon-size:17px; background:var(--surface-high); }
.description-actions .description-save { color:var(--success); }
.description-actions .description-discard { color:var(--muted); }
</style>
