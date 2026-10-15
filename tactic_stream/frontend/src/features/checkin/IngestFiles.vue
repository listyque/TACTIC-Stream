<script>
import { nextTick, useId } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppIcon from '../../controls/AppIcon.vue'
import SettingRow from '../../controls/SettingRow.vue'

export default {
  setup() { return { formId: useId() } },
  components: { AppButton, AppSelect, AppSwitch, AppCheckbox, AppIcon, SettingRow },
  inject: { queueCheckin: { default: null }, openScriptEditor: { default: null } },
  props: { ticket: String, project: String },
  data() { return { parent: null, branch: null, scope: null, rules: [], selectedRule: '', options: {}, extraJson: '{}',
    files: [], advanced: false, busy: false, ready: false, error: '', discard: false, conflicts: null, request: 0 } },
  computed: {
    canUpdate() { return this.conflicts?.files.filter(item => item.conflict).every(item => item.matches.length === 1) },
    rule() { return this.rules.find(rule => rule.code === this.selectedRule) },
  },
  watch: { ticket() { this.reset() }, project() { if (!this.$refs.dialog?.open) this.reset() }, options: { deep: true, handler() { this.conflicts = null } }, extraJson() { this.conflicts = null } },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    beforeUnload(event) { if (this.files.length) { event.preventDefault(); event.returnValue = '' } },
    reset() { this.request++; this.files = []; this.conflicts = null; this.$refs.deleteDialog?.close(); this.$refs.dialog?.close() },
    close(force = false) { if (this.busy) return; if (!force && this.files.length) { this.discard = true; return }; this.reset() },
    async open(parent, branch) {
      if (this.$refs.dialog.open) { this.$refs.dialog.show(); return }
      this.parent = parent; this.branch = branch; this.scope = { ticket: this.ticket, project: this.project }
      this.files = []; this.rules = []; this.ready = false; this.error = ''; this.discard = false; this.conflicts = null; this.advanced = false
      await nextTick(); this.$refs.dialog.show()
      await this.loadRules()
    },
    async call(action, values = {}) {
      return (await rpc('execute_cmd', [{ ...this.scope, language: 'python' }, 'tactic.command.related_ingest_cmd.RelatedIngestCmd', {
        action, parent_key: this.parent.__search_key__, search_type: this.branch.search_type, path: this.branch.path || '', ...values }])).info
    },
    async loadRules() {
      const request = ++this.request
      this.busy = true
      try {
        const result = await this.call('rules')
        if (request !== this.request) return
        this.rules = result.rules; this.selectRule(this.rules[0]); this.ready = true
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    selectRule(rule) { if (!rule.applicable) return; this.selectedRule = rule.code; this.options = { ...rule.options }; this.extraJson = JSON.stringify(rule.options.extraData, null, 2); this.conflicts = null },
    values() {
      const extraData = JSON.parse(this.extraJson)
      if (!extraData || Array.isArray(extraData) || typeof extraData !== 'object') throw new Error('Extra values must be a JSON object')
      return { ...this.options, extraData }
    },
    addFiles(files) { if (this.busy) return; this.files.push(...[...files].map(file => ({ file, status: 'Ready', reason: '' }))); this.conflicts = null; this.error = '' },
    async start() {
      if (!this.ready || this.busy || !this.files.length) return
      const request = ++this.request
      this.error = ''; this.busy = true; this.conflicts = null
      try {
        const options = this.values()
        const result = await this.call('scan', { options, filenames: this.files.map(row => row.file.name) })
        if (request !== this.request) return
        this.files.forEach((row, index) => { row.status = result.files[index].accepted ? result.files[index].conflict ? 'Conflict' : 'Ready' : 'Skipped'; row.reason = result.files[index].reason || '' })
        this.conflicts = { ...result, options }
        const conflicts = result.files.filter(item => item.conflict)
        if (!conflicts.length) this.enqueue('new')
        else if (options.updateMode === 'update' && this.canUpdate) this.enqueue('update')
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    enqueue(decision) {
      if (!this.conflicts || !this.queueCheckin) return
      const prepared = this.conflicts
      const remaining = []
      try {
        for (const [index, item] of prepared.files.entries()) {
          const row = this.files[index]
          if (!item.accepted || item.conflict && decision === 'skip') { row.status = 'Skipped'; row.reason ||= 'Matching item already exists'; remaining.push(row); continue }
          this.queueCheckin({ ...this.scope, searchKey: this.parent.__search_key__, title: item.name, name: row.file.name, files: [row.file], file: row.file,
            context: item.context, process: prepared.options.process, description: '', ingest: {
              parent_key: this.parent.__search_key__, search_type: this.branch.search_type, path: this.branch.path || '',
              options: prepared.options, decision: item.conflict ? decision : 'new', search_key: decision === 'update' ? item.matches[0] || '' : '' } })
          row.queued = true
        }
        this.files = remaining; this.conflicts = null
        if (!remaining.length) this.reset()
      } catch (error) { this.files = this.files.filter(row => !row.queued); this.conflicts = null; this.error = error.message }
    },
    async saveRule() {
      if (this.busy) return
      const request = ++this.request
      this.busy = true; this.error = ''
      try {
        const options = this.values(), title = options.title.trim()
        if (!title) throw new Error('Enter a rule title')
        await this.call('scan', { options, filenames: ['rule-validation.txt'] })
        const data = { scan_type: 'list', action_type: 'checkin', action: 'file', search_type: this.branch.search_type,
          rule: options.pattern, filter: options.filter, ignore: options.ignore, column: options.column,
          ignore_ext: options.ignoreExtension, update_mode: options.updateMode === 'update', process: options.process, context: options.context,
          context_mode: options.contextMode, keywords: options.keywords, keyword_mode: options.keywordMode, extra_data: options.extraData,
          validation_script: options.validationScript, process_script: options.processScript, create_icon: options.createIcon }
        const payload = { title, base_dir: '', rule: options.pattern, data: JSON.stringify(data) }
        await rpc(this.rule?.key ? 'update' : 'insert', [{ ...this.scope, language: 'python' }, this.rule?.key || 'config/ingest_rule', payload])
        if (request === this.request) await this.loadRules()
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    async deleteRule() {
      if (this.busy || !this.rule?.key) return
      const request = ++this.request
      this.busy = true
      try { await rpc('delete_sobject', [{ ...this.scope, language: 'python' }, this.rule.key]); if (request === this.request) { this.$refs.deleteDialog.close(); await this.loadRules() } }
      catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
  },
}
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{kind:'ingest_files', type:'window' }" ref="dialog" class="record-dialog ingest-files" :aria-label="t('Add files')" @cancel.prevent="close()" @dragover.prevent @drop.prevent="addFiles($event.dataTransfer.files)">
      <header><div><h2>{{ parent?.name || parent?.title || parent?.code }} → {{ branch?.title }}</h2><small>{{ t('One Search Object per file · snapshot in publish') }} · {{ branch?.search_type }}</small></div><AppButton label="Close" icon="close" :disabled="busy" @click="close()" /></header>
      <p v-if="error" role="alert" class="error">{{ t(error) }}</p>
      <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
      <div v-if="ready" class="ingest-files-grid">
        <section class="ingest-file-list"><header><strong>{{ t('Files') }} · {{ files.length }}</strong><AppButton label="Clear" icon="delete-sweep" icon-only :disabled="busy || !files.length" @click="files = []; conflicts = null" /><AppButton label="Add files" icon="add" icon-only :disabled="busy" @click="$refs.picker.click()" /></header>
          <input ref="picker" type="file" multiple hidden @change="addFiles($event.target.files); $event.target.value = ''">
          <p v-if="!files.length" class="muted">{{ t('Drop files here') }}<br>{{ t('Each file creates a child item named without its extension.') }}</p>
          <ul class="ingest-file-rows"><li v-for="(row, index) in files" :key="index"><AppIcon :name="row.status === 'Conflict' ? 'warning' : row.status === 'Skipped' ? 'cancel' : 'file'" :class="{ 'ingest-conflict': ['Conflict', 'Skipped'].includes(row.status) }" /><div><span>{{ row.file.name }}</span><small>{{ t(row.status) }} · {{ row.file.size }} {{ t('bytes') }}</small><small v-if="row.reason">{{ t(row.reason) }}</small></div><small>{{ row.file.name.split('.').at(-1).toUpperCase() }}</small><AppButton label="Remove file" icon="close" icon-only :disabled="busy" @click="files.splice(index, 1); conflicts = null" /></li></ul>
        </section>
        <section class="ingest-rule-panel"><strong>{{ t('Ingest rule') }}</strong>
          <div class="ingest-rules"><AppButton v-for="rule in rules" :key="rule.code" :label="rule.title" :aria-pressed="selectedRule === rule.code" :disabled="busy || !rule.applicable" :icon="rule.code ? 'script' : 'upload'" @click="selectRule(rule)"><span><strong>{{ rule.code ? rule.title : t(rule.title) }}</strong><small>{{ t(!rule.applicable ? 'For another Search Type' : rule.code ? 'Saved server ingest rule' : 'Create one child item per file and publish immediately') }}</small></span></AppButton></div>
          <div class="ingest-rule-toggle"><AppCheckbox :control-id="formId + '-extension'" v-model="options.ignoreExtension" label="Remove extension from item name" :disabled="busy" /><AppButton :label="advanced ? 'Hide rule details' : 'Edit rule details'" icon="settings" @click="advanced = !advanced" /></div>
          <fieldset v-if="advanced" :disabled="busy" class="ingest-rule-details">
            <label>{{ t('Include: .mov, /regex/') }}<input v-model="options.filter"></label><label>{{ t('Ignore: .tmp, .db') }}<input v-model="options.ignore"></label>
            <SettingRow title="Parse values from a path pattern" :control-id="formId + '-pattern'"><AppSwitch :id="formId + '-pattern'" v-model="options.usePattern" label="Parse values from a path pattern" /></SettingRow>
            <label>{{ t('Path pattern') }}<input v-model="options.pattern" :disabled="!options.usePattern" :placeholder="'{sobject.name}_{snapshot.context}.mov'"></label>
            <label>{{ t('Process') }}<input v-model="options.process"></label><label>{{ t('Context') }}<input v-model="options.context"></label>
            <SettingRow title="Update matching item" :control-id="formId + '-update'"><AppSwitch :id="formId + '-update'" :model-value="options.updateMode === 'update'" label="Update matching item" @update:model-value="options.updateMode = $event ? 'update' : 'insert'" /></SettingRow>
            <SettingRow title="Create preview when supported" :control-id="formId + '-preview'"><AppSwitch :id="formId + '-preview'" v-model="options.createIcon" label="Create preview when supported" /></SettingRow>
            <label>{{ t('Extra Search Object values (JSON)') }}<textarea v-model="extraJson" rows="4"></textarea></label>
            <label>{{ t('Keywords') }}<input v-model="options.keywords"></label>
            <label>{{ t('Keyword mode') }}<AppSelect v-model="options.keywordMode" label="Keyword mode" :options="[{ value:'default', label:'Default' }, { value:'simplified', label:'Simplified' }, { value:'none', label:'None' }]" /></label>
            <label>{{ t('Context case') }}<AppSelect v-model="options.contextMode" label="Context case" :options="[{ value:'case_sensitive', label:'Case sensitive' }, { value:'case_insensitive', label:'Lowercase' }]" /></label>
            <p class="muted">{{ t('Scripts receive path, sobject, parent and snapshot. Return a truthy value to accept the file.') }}</p>
            <label>{{ t('Validation script path') }}<input v-model="options.validationScript"></label><AppButton label="Open validation script" icon="code" :disabled="!openScriptEditor" @click="openScriptEditor(options.validationScript)" />
            <label>{{ t('Process script path') }}<input v-model="options.processScript"></label><AppButton label="Open process script" icon="code" :disabled="!openScriptEditor" @click="openScriptEditor(options.processScript)" />
            <label>{{ t('Rule title') }}<input v-model="options.title"></label><div class="configuration-actions"><AppButton label="Save rule" icon="save" @click="saveRule" /><AppButton label="Delete rule" icon="delete" destructive :disabled="!rule?.key" @click="$refs.deleteDialog.showModal()" /></div>
          </fieldset>
        </section>
      </div>
      <section v-if="conflicts?.files.some(item => item.conflict)" class="notice" role="alert"><strong>{{ t('Resolve matching names') }}</strong><p>{{ conflicts.files.filter(item => item.conflict).map(item => item.name).join(', ') }}</p><p v-if="!canUpdate">{{ t('Update is unavailable because at least one name does not identify exactly one existing item.') }}</p>
        <div class="configuration-actions"><AppButton label="Cancel" @click="conflicts = null" /><AppButton label="Create duplicates" icon="copy" @click="enqueue('duplicates')" /><AppButton label="Skip existing" @click="enqueue('skip')" /><AppButton label="Update existing" icon="refresh" :disabled="!canUpdate" @click="enqueue('update')" /></div>
      </section>
      <footer><AppButton label="Close" :disabled="busy" @click="close()" /><AppButton label="Ingest files" icon="upload" highlighted :disabled="!ready || busy || !files.length || !queueCheckin || !!conflicts" @click="start">{{ t('Ingest {count}', { count: files.length }) }}</AppButton></footer>
      <div v-if="discard" class="notice" role="alert"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Continue editing" @click="discard = false" /><AppButton label="Discard" destructive @click="close(true)" /></div>
    </dialog>
    <dialog ref="deleteDialog" class="record-dialog" :aria-label="t('Delete ingest rule?')" @cancel.prevent="!busy && $refs.deleteDialog.close()"><header><h2>{{ t('Delete ingest rule?') }}</h2></header><p>{{ t('The rule will be removed from this TACTIC project.') }}</p><p v-if="error" class="error" role="alert">{{ t(error) }}</p><footer><AppButton label="Cancel" :disabled="busy" @click="$refs.deleteDialog.close()" /><AppButton label="Delete rule" destructive :disabled="busy" @click="deleteRule" /></footer></dialog>
  </Teleport>
</template>

<style>
.ingest-files.record-dialog { width:min(960px, calc(100dvw - 24px)); }
.ingest-files-grid { display:grid; grid-template-columns:minmax(280px, 1fr) minmax(340px, 1fr); gap:10px; }
.ingest-file-list, .ingest-rule-panel { min-width:0; min-height:min(430px, 55dvh); padding:10px; background:var(--surface-deep); border:1px solid var(--outline-variant); border-radius:var(--surface-radius); }
.ingest-file-list > header { display:flex; align-items:center; gap:6px; }
.ingest-file-list > header > strong { flex:1; }
.ingest-file-rows { display:grid; gap:4px; max-height:55dvh; overflow:auto; padding:6px 0; list-style:none; }
.ingest-file-rows > li { display:flex; align-items:center; gap:8px; min-height:46px; padding:4px 6px 4px 10px; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--row); }
.ingest-file-rows > li > div { min-width:0; flex:1; overflow-wrap:anywhere; }
.ingest-file-rows .app-icon { font-size:17px; color:var(--muted); }
.ingest-file-rows .ingest-conflict { color:var(--yellow); }
.ingest-files small { color:var(--muted); font-weight:400; margin-top:2px; }
.ingest-rule-toggle { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:6px; }
.ingest-rule-details, .ingest-rule-details > label { display:grid; gap:10px; }
.ingest-rule-details { border:0; padding:0; margin-top:12px; }
.ingest-rules { display:flex; flex-direction:column; gap:4px; max-height:174px; overflow:auto; margin-block:10px; }
.ingest-rules > button { justify-content:flex-start; min-height:50px; flex-shrink:0; text-align:left; border:1px solid transparent; border-radius:var(--item-radius); background:var(--row); }
.ingest-rules > button[aria-pressed=true] { background:var(--selected); border-color:var(--primary); }
.ingest-files > footer { display:flex; justify-content:flex-end; gap:8px; margin-top:10px; }
@media(max-width:720px) { .ingest-files-grid { grid-template-columns:1fr; }.ingest-file-rows { max-height:30dvh; } }
</style>
