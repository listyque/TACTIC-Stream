<script>
// DuplicateSObjectView.qml and SObjectDuplicateController: the same five steps.
import { nextTick } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import { notify } from '../activity/notifications.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppDateField from '../../controls/AppDateField.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppColorInput from '../../controls/AppColorInput.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import SummaryChip from '../../controls/SummaryChip.vue'
import { contentChoices, duplicateProfile, saveDuplicateProfile, applyDuplicateProfile, changeContent } from './duplicateProfiles.js'

const steps = ['Fields', 'Relations', 'Snapshots', 'Tasks and messages', 'Review duplicate']
const icons = ['edit', 'account-tree', 'inventory-2', 'task', 'fact-check']
const choices = [
  { name:'copySnapshots', label:'Snapshots', count:'snapshotCount', page:2 },
  { name:'copyTasks', label:'Tasks', count:'taskCount', page:3 },
  { name:'copyProcessMessages', label:'Process messages', count:'processMessageCount', page:3 },
  { name:'copyProcessAttachments', label:'Process attachments', count:'processAttachmentCount', page:3 },
  { name:'copyTaskMessages', label:'Task messages', count:'taskMessageCount', page:3 },
  { name:'copyTaskAttachments', label:'Task attachments', count:'taskAttachmentCount', page:3 },
]
export default {
  components: { AppDateField, AppButton, AppIcon, AppCheckbox, AppSelect, AppTextField, AppColorInput, AppSegmentedButton, SummaryChip },
  inject: { openHelp: {}, currentLogin: { default: () => () => '' } },
  props: { ticket:String, project:String },
  emits: ['completed'],
  data() { return { analysis:null, draft:{}, baseline:'', scope:null, sourceKey:'', sourceType:'', owner:'', revision:'', step:0, remember:true, busy:false, saving:false, uncertain:false, error:'', discard:false, request:0, quick:false } },
  computed: {
    steps() { return steps.map((label, value) => ({ value, label, icon:icons[value] })) },
    processes() { return this.analysis?.processes.filter(process => choices.some(choice => choice.page === this.step && process[choice.count])) || [] },
    dirty() { return !!this.analysis && JSON.stringify(this.options()) !== this.baseline },
    valid() { return this.scope?.ticket === this.ticket && this.scope?.project === this.project },
    totals() {
      const result = { related:0, snapshots:0, tasks:0, messages:0 }
      for (const relation of this.analysis?.relations || []) if (relation.mode !== 'none') result.related += relation.count
      for (const process of this.analysis?.processes || []) {
        if (process.copySnapshots) result.snapshots += process.snapshotCount
        if (process.copyTasks) result.tasks += process.taskCount
        if (process.copyProcessMessages) result.messages += process.processMessageCount
        if (process.copyTaskMessages) result.messages += process.taskMessageCount
        if (process.copyProcessAttachments) result.messages += process.processAttachmentCount
        if (process.copyTaskAttachments) result.messages += process.taskAttachmentCount
      }
      return result
    },
  },
  watch: { ticket() { this.invalidate() }, project() { this.invalidate() } },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    changeContent,
    beforeUnload(event) { if (this.$refs.dialog?.open && (this.dirty || this.saving || this.uncertain)) { event.preventDefault(); event.returnValue = '' } },
    invalidate() { this.request++; this.busy = this.saving = false; if (this.$refs.dialog?.open) this.error = 'Connection context changed. Close this form and reopen it before saving.' },
    async open(record, quick = false) {
      if (this.$refs.dialog.open) { this.$refs.dialog.show(); return }
      this.scope = { ticket:this.ticket, project:this.project, language:'python' }
      this.sourceKey = record.__search_key__; this.sourceType = record.__search_key__.split('?')[0]
      this.owner = this.currentLogin(); this.analysis = null; this.draft = {}; this.revision = ''
      this.step = 0; this.quick = quick; this.error = ''; this.uncertain = this.discard = false
      await nextTick(); this.$refs.dialog.show()
      await this.analyze()
      if (quick && this.analysis && !this.error && this.valid) await this.duplicate()
    },
    async call(action, values = {}) { return (await rpc('execute_cmd', [this.scope, 'tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd', { action, search_key:this.sourceKey, ...values }])).info },
    async analyze() {
      if (!this.valid || this.saving || this.uncertain) return
      const request = ++this.request, previous = this.analysis ? this.options() : null
      this.busy = true; this.error = ''
      try {
        const result = await this.call('analyze')
        if (request !== this.request) return
        const profile = duplicateProfile(this.owner, this.scope.project, this.sourceType)
        if (this.quick && !profile) throw new Error('Open Duplicate… once to save choices for this Search Type.')
        applyDuplicateProfile(result.analysis, previous || profile)
        this.analysis = result.analysis; this.revision = result.revision
        this.draft = Object.fromEntries(this.analysis.fields.map(field => [field.name,
          previous?.fields?.[field.name] ?? (this.fieldKind(field) === 'checkbox' ? ['True','true','1','on'].includes(field.value) : String(field.widget?.input?.value ?? field.value))]))
        if (!previous) this.baseline = JSON.stringify(this.options())
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    readOnly(field) { return field.widget?.input?.read_only || [true,'true'].includes(field.widget?.options?.read_only) },
    fieldKind(field) {
      const widget = field.widget
      if (widget?.input?.type === 'hidden' || widget?.class_name?.endsWith('.HiddenWdg')) return 'hidden'
      if (widget?.input?.type === 'color') return 'color'
      if (widget?.choices && widget.input?.type !== 'multiselect') return 'select'
      if (widget?.class_name?.endsWith('.CheckboxWdg') || /bool/i.test(field.dataType)) return 'checkbox'
      if (field.multiline || widget?.class_name?.endsWith('.TextAreaWdg')) return 'textarea'
      if (widget?.input?.type === 'time') return 'time'
      if (widget?.class_name?.includes('CalendarInput')) return 'datetime-local'
      return /int|float|double|numeric|decimal/i.test(field.dataType) ? 'number' : 'text'
    },
    fieldChoices(field) { const widget = field.widget; return [ ...(widget.input?.empty_label ? [{value:'', label:widget.input.empty_label}] : []), ...widget.choices.map((value,index) => ({value,label:widget.labels[index]})) ] },
    pageChoices(process) { return choices.filter(choice => choice.page === this.step && process[choice.count]) },
    options() { return { fields:Object.fromEntries((this.analysis?.fields || []).filter(field => !this.readOnly(field)).map(field => [field.name,this.draft[field.name]])),
      relations:Object.fromEntries((this.analysis?.relations || []).map(row => [row.key,row.mode])),
      processes:Object.fromEntries((this.analysis?.processes || []).map(row => [row.name,Object.fromEntries(contentChoices.map(name => [name,row[name] === true]))])) } },
    async duplicate() {
      if (!this.analysis || this.busy || this.saving || this.uncertain || !this.valid) return
      if (!this.$refs.fields?.checkValidity()) { this.step = 0; await nextTick(); this.$refs.fields.reportValidity(); return }
      const request = ++this.request
      this.saving = true; this.error = ''
      try {
        const options = this.options()
        if (this.remember) {
          try { saveDuplicateProfile(this.owner, this.scope.project, this.sourceType, { relations:options.relations, processes:options.processes }) }
          catch { const error = new Error('Unable to save choices in this browser. Turn off Remember choices to continue.'); error.status = 400; throw error }
        }
        const result = await this.call('duplicate', { options, revision:this.revision })
        if (request !== this.request) return
        this.baseline = JSON.stringify(options); this.$refs.dialog.close(); this.analysis = null
        notify('info', 'Object duplicated'); this.$emit('completed', result.result)
      } catch (error) {
        if (request !== this.request) return
        this.uncertain = !error.status || error.status >= 500
        this.error = this.uncertain ? 'The result is unknown. Refresh the objects before trying again.' : error.message
      } finally { if (request === this.request) this.saving = false }
    },
    close(force = false) { if (this.saving) return; if (!force && (this.dirty || this.uncertain)) { this.discard = true; return }; this.request++; this.$refs.dialog.close(); this.analysis = null; this.busy = this.uncertain = this.discard = false },
  },
}
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{kind:'duplicate_sobject', type:'window' }" ref="dialog" class="record-dialog duplicate-sobject" :aria-label="t('Duplicate object')" @cancel.prevent="close()">
      <header class="duplicate-header"><span class="duplicate-symbol"><AppIcon name="control-point-duplicate" /></span><div><h2>{{ t('Duplicate') }} {{ analysis?.title }}</h2><small>{{ analysis?.searchType || sourceType }}</small></div><span class="duplicate-step">{{ t('Step {step} of 5', {step:step + 1}) }}</span><AppButton label="Help" icon="help" icon-only @click="openHelp('duplicating_objects')" /><AppButton label="Close" icon="close" icon-only :disabled="saving" @click="close()" /></header>
      <p v-if="error" role="alert" class="error">{{ t(error) }} <AppButton v-if="!uncertain && valid" label="Analyze again" :disabled="busy || saving" @click="analyze" /></p>
      <p v-if="busy || saving" role="status">{{ t(saving ? 'Creating duplicate on server…' : 'Analyzing object…') }}</p>
      <template v-if="analysis">
        <AppSegmentedButton v-model="step" :options="steps" label="Duplicate steps" :disabled="saving || busy" class="duplicate-steps" />
        <form ref="fields" class="duplicate-pages" @submit.prevent="duplicate">
          <section v-show="step === 0" class="duplicate-page"><p class="muted duplicate-intro"><AppIcon name="edit" />{{ t('Edit values for the new object. Identity, project and relationship fields are managed automatically.') }}</p>
            <div class="duplicate-fields"><div v-for="field in analysis.fields.filter(field => fieldKind(field) !== 'hidden')" :key="field.name" class="duplicate-field"><span class="duplicate-field-heading"><span class="duplicate-symbol small"><AppIcon :name="fieldKind(field) === 'textarea' ? 'description' : 'text-fields'" /></span><span><strong>{{ t(field.widget?.title || field.label) }}</strong><small>{{ field.name }}</small></span></span>
              <AppCheckbox v-if="fieldKind(field) === 'checkbox'" v-model="draft[field.name]" :label="field.widget?.title || field.label" :disabled="saving || readOnly(field)" />
              <AppSelect v-else-if="fieldKind(field) === 'select'" v-model="draft[field.name]" :options="fieldChoices(field)" :label="field.widget?.title || field.label" :translate-labels="false" :disabled="saving || readOnly(field)" />
              <AppColorInput v-else-if="fieldKind(field) === 'color'" v-model="draft[field.name]" :label="field.label" :disabled="saving || readOnly(field)" />
              <textarea v-else-if="fieldKind(field) === 'textarea'" v-model="draft[field.name]" :aria-label="t(field.widget?.title || field.label)" rows="4" :disabled="saving || readOnly(field)"></textarea>
              <AppDateField v-else-if="fieldKind(field) === 'datetime-local'" v-model="draft[field.name]" :label="field.widget?.title || field.label" :required="[true, 'true'].includes(field.widget?.options?.required)" :disabled="saving || readOnly(field)" />
              <AppTextField v-else v-model="draft[field.name]" :label="field.widget?.title || field.label" :type="fieldKind(field)" :required="[true,'true'].includes(field.widget?.options?.required)" :disabled="saving || readOnly(field)" step="any" />
              <small v-if="field.widget?.options?.hint || field.widget?.options?.hint_text" class="muted">{{ t(field.widget.options.hint || field.widget.options.hint_text) }}</small>
            </div></div>
          </section>
          <section v-if="step === 1" class="duplicate-page"><p class="muted">{{ t('Keep parent and instance links, or duplicate direct children. Linked targets are not cloned.') }}</p>
            <p v-if="!analysis.relations.length" class="muted">{{ t('No linked objects') }}</p>
            <article v-for="relation in analysis.relations" :key="relation.key" class="duplicate-card"><div class="duplicate-card-heading"><span class="duplicate-symbol small"><AppIcon :name="relation.kind === 'instance' ? 'link' : 'account-tree'" /></span><div><strong>{{ relation.title }}</strong><small>{{ t(relation.kind === 'parent' ? 'Parent' : relation.kind === 'instance' ? 'Instance links' : 'Children') }} · {{ relation.count }}<template v-if="relation.path"> · {{ relation.path }}</template></small></div></div><AppSegmentedButton v-model="relation.mode" :options="relation.options.map(option => ({value:option.value,label:option.label}))" :label="relation.title" :disabled="saving" /><p class="muted">{{ relation.items.map(item => item.title).join(' · ') }}</p></article>
          </section>
          <section v-if="step === 2 || step === 3" class="duplicate-page"><p class="muted">{{ t(step === 2 ? 'Copy current snapshots and their files by process. Message attachments are selected separately.' : 'Choose tasks, message threads and attachments to duplicate. Attachment choices include their messages and tasks.') }}</p><p v-if="!processes.length" class="muted">{{ t(step === 2 ? 'No current snapshots' : 'No tasks or messages') }}</p>
            <article v-for="process in processes" :key="process.name" class="duplicate-card"><div class="duplicate-card-heading"><span class="duplicate-symbol small"><AppIcon name="account-tree" /></span><div><strong>{{ process.name }}</strong><small v-if="step === 2">{{ t('Snapshots') }} {{ process.snapshotCount }} · {{ t('Files') }} {{ process.fileCount }}</small></div><SummaryChip :label="t('Items')" :count="step === 2 ? process.snapshotCount : process.taskCount + process.processMessageCount + process.taskMessageCount" :show-dot="false" /></div><div class="duplicate-content-choices"><AppCheckbox v-for="choice in pageChoices(process)" :key="choice.name" :model-value="process[choice.name]" :label="choice.label" compact :disabled="saving" @update:model-value="changeContent(process, choice.name, $event)">{{ t(choice.label) }} {{ process[choice.count] }}<template v-if="choice.name === 'copySnapshots'"> · {{ t('Files') }} {{ process.fileCount }}</template></AppCheckbox></div></article>
          </section>
          <section v-if="step === 4" class="duplicate-page"><div class="duplicate-review"><AppIcon name="control-point-duplicate" /><h3>{{ t('Ready to duplicate') }}</h3><p class="muted">{{ t('The new object will have its own identity. Instance links refer to the same objects; selected children and content are copied.') }}</p><div class="duplicate-totals"><SummaryChip :label="t('Related objects')" :count="totals.related" /><SummaryChip :label="t('Snapshots')" :count="totals.snapshots" /><SummaryChip :label="t('Tasks')" :count="totals.tasks" /><SummaryChip :label="t('Messages and files')" :count="totals.messages" /></div></div><p class="duplicate-intro muted"><AppIcon name="MDI_LIGHTNING_BOLT" />{{ t(remember ? 'These choices will be available for Quick Duplicate.' : 'These choices apply only to this duplicate.') }}</p></section>
        </form>
      </template>
      <footer><AppCheckbox v-model="remember" label="Remember choices" compact :disabled="saving || !analysis" /><div class="configuration-actions"><AppButton label="Cancel" :disabled="saving" @click="close()" /><AppButton v-if="step > 0" label="Back" icon="chevron-left" icon-only :disabled="busy || saving" @click="step--" /><AppButton v-if="step < 4" label="Next" icon="chevron-right" icon-only :disabled="!analysis || busy || saving" @click="step++" /><AppButton label="Duplicate" icon="copy" highlighted :disabled="!analysis || busy || saving || uncertain || !valid" @click="duplicate" /></div></footer>
      <div v-if="discard" class="notice" role="alert"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Continue editing" @click="discard = false" /><AppButton label="Discard" destructive @click="close(true)" /></div>
    </dialog>
  </Teleport>
</template>

<style>
.duplicate-sobject { width:min(960px, calc(100vw - 32px)); height:min(620px, calc(100dvh - 32px)); padding:14px; background:var(--surface-deep); }
.duplicate-sobject[open] { display:flex; flex-direction:column; gap:10px; }
.duplicate-sobject .duplicate-header { flex:none; margin:0; min-height:68px; padding:10px 12px; border-radius:var(--item-radius); background:var(--surface-container); gap:10px; }
.app-window.duplicate-sobject > .duplicate-header { margin:0; gap:10px; }.app-window.duplicate-sobject > .duplicate-header h2 { font-size:var(--text-body); margin:0 0 4px; }.duplicate-header > div { flex:1; min-width:0; }.duplicate-header small,.duplicate-card small,.duplicate-field-heading small { font-size:var(--text-caption); color:var(--muted); }
.duplicate-step { font-size:var(--text-caption); white-space:nowrap; padding:6px 10px; border-radius:20px; background:var(--surface-high); }
.duplicate-symbol { display:grid; place-items:center; flex:none; width:42px; height:42px; border-radius:var(--item-radius); background:var(--surface-high); color:var(--primary); }.duplicate-symbol .app-icon { width:21px; height:21px; font-size:21px; }.duplicate-symbol.small { width:34px; height:34px; }.duplicate-symbol.small .app-icon { width:17px; height:17px; font-size:17px; }
.duplicate-steps { flex:none; }.duplicate-pages { flex:1; min-height:0; overflow:auto; padding:6px 10px 10px 6px; }.duplicate-page > .muted:first-child { margin:0 0 12px; }.duplicate-fields { display:grid; align-items:start; grid-template-columns:repeat(auto-fit,minmax(min(430px,100%),1fr)); gap:12px; }.duplicate-field { display:flex; flex-direction:column; gap:12px; padding:12px; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface); }.duplicate-field-heading { display:flex; gap:10px; align-items:center; font-size:var(--text-body); }.duplicate-field-heading > span:last-child { display:flex; flex-direction:column; gap:4px; }.duplicate-field input,.duplicate-field textarea,.duplicate-field select { width:100%; }.duplicate-field textarea { height:112px; }
.duplicate-card { padding:11px; margin-bottom:10px; border-radius:var(--item-radius); background:var(--surface-container); }.duplicate-card-heading { display:flex; align-items:center; gap:10px; }.duplicate-card-heading > div:not(.summary-chip) { flex:1; display:flex; flex-direction:column; gap:4px; }.duplicate-card > .app-segmented-button { margin-top:10px; width:100%; }.duplicate-card > p { margin:10px 0 0; font-size:var(--text-caption); }.duplicate-content-choices { display:flex; flex-wrap:wrap; gap:5px 12px; margin:5px 0 0; }.duplicate-review { text-align:center; padding:14px; border-radius:var(--item-radius); background:var(--surface-container); }.duplicate-review > .app-icon { font-size:34px; width:34px; height:34px; color:var(--primary); }.duplicate-review h3 { font-size:var(--text-body-large); }.duplicate-totals { display:flex; justify-content:center; flex-wrap:wrap; gap:12px; }
.duplicate-sobject > footer { flex:none; min-height:64px; display:flex; align-items:center; justify-content:space-between; gap:10px; margin:0; padding:10px 14px; border-radius:var(--item-radius); background:var(--surface-container); }.duplicate-sobject > .error,.duplicate-sobject > [role="status"] { margin:0; }
@media(max-width:700px) { .duplicate-card-heading { flex-wrap:wrap; }.duplicate-sobject > footer { flex-wrap:wrap; }.duplicate-header .duplicate-step { display:none; }.duplicate-steps .app-button { font-size:var(--text-caption); }.duplicate-steps .app-icon { display:none; } }
.duplicate-intro { display:flex; align-items:center; gap:10px; padding:12px; border-radius:var(--item-radius); background:var(--surface); }.duplicate-intro .app-icon { flex:none; font-size:18px; width:18px; height:18px; color:var(--primary); }.duplicate-card .duplicate-symbol { background:transparent; }.duplicate-content-choices { margin-left:0; }.duplicate-review h3 { margin:10px 0; }.duplicate-page .duplicate-review + .duplicate-intro { margin-top:10px; }</style>
