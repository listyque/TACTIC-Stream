<script>
import { nextTick, useId } from 'vue'
import { formDefinition, rpc, uploadFormFile } from '../../api.js'
import { t } from '../../i18n.js'
import { fieldKind, unsupportedField } from './recordFields.js'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppColorInput from '../../controls/AppColorInput.vue'
import AppDateField from '../../controls/AppDateField.vue'
import AppButton from '../../controls/AppButton.vue'
import { mobile } from '../../mobile.js'

export default {
  setup() { return { formId: useId() } },
  components: { AppDateField, AppSwitch, AppColorInput, AppButton },
  props: { ticket: String, project: String, searchType: String, modal:Boolean, editView: { type:String, default:'edit' } },
  emits: ['saved'],
  data() {
    return { definition: null, context: null, draft: {}, baseline: {}, loading: false,
      saving: false, error: '', discard: false, uncertain: false, request: 0, files: {}, selectedFields: [], instanceRelation: null }
  },
  computed: {
    mobile() { return mobile.value },
    contextValid() {
      return this.context?.ticket === this.ticket && this.context?.project === this.project &&
        (!this.definition || this.definition.search_type === this.searchType)
    },
    batch() { return !!this.definition?.search_keys },
    dirty() { return (this.batch && this.selectedFields.length > 0) || JSON.stringify(this.draft) !== JSON.stringify(this.baseline) },
    editableFields() { return (this.definition?.fields || []).filter(field => !this.readOnly(field)) },
    batchFields() {
      return this.editableFields.filter(field => !this.unsupported.includes(field) &&
        !['FileInput', 'MultiUpload', 'HiddenWdg', 'ParentInput'].includes(this.kind(field)) &&
        !['TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'].includes(field.action.handler))
    },
    fieldsToSave() { return this.batch ? this.batchFields.filter(field => this.selectedFields.includes(field.name)) : this.editableFields },
    blocked() { return !this.batch && this.unsupported.length > 0 },
    unsupported() { return (this.definition?.fields || []).filter(unsupportedField) },
  },
  watch: {
    ticket() { this.invalidate() },
    project() { this.invalidate() },
    searchType() { this.invalidate() },
  },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    kind: fieldKind,
    readOnly(field) { return field.input?.read_only || [true, 'true'].includes(field.options.read_only) },
    disabled(field) { return this.readOnly(field) || (this.batch && !this.selectedFields.includes(field.name)) },
    required(field) { return [true, 'true'].includes(field.options.required) },
    checked(value) { return [true, 1, '1', 'true', 'on'].includes(value) },
    inputName(field) { return this.definition.input_prefix ? `${this.definition.input_prefix}|${field.name}` : field.name },
    selectFile(field, event) {
      const file = event.target.files[0]
      if (file) this.files[field.name] = file
      else delete this.files[field.name]
      this.draft[field.name] = file?.name || ''
    },
    selectUploads(field, slot, event) {
      const files = Array.from(event.target.files)
      this.files[slot] = files
      this.draft[field.name].files[slot] = files.map(file => file.name)
    },
    beforeUnload(event) {
      if (this.dirty || this.saving || this.uncertain) { event.preventDefault(); event.returnValue = '' }
    },
    invalidate() {
      this.request++
      this.loading = false
      this.error = 'Connection context changed. Close this form and reopen it before saving.'
    },
    async open(searchKey = null, sourceKey = null, relation = {}) {
      if (this.$refs.dialog.open) { this.$refs.dialog.show(); return }
      const id = ++this.request
      this.context = { ticket: this.ticket, project: this.project, language: 'python' }
      this.instanceRelation = relation.instance || null
      this.definition = null
      this.draft = this.baseline = {}
      this.files = {}
      this.selectedFields = []
      this.error = ''
      this.discard = this.uncertain = false
      this.loading = true
      this.modal || this.searchType === 'sthpw/task' ? this.$refs.dialog.showModal() : this.$refs.dialog.show()
      try {
        const definition = await formDefinition(this.context.ticket, this.context.project,
          this.searchType, searchKey ? this.editView : 'insert', searchKey, sourceKey, this.instanceRelation ? {} : relation)
        if (id !== this.request) return
        this.definition = definition
        this.draft = Object.fromEntries(definition.fields.map(field => [field.name,
          this.kind(field) === 'MultiSelectWdg' ? field.input.value : this.kind(field) === 'MultiUpload'
            ? { context: field.input.context.value, subcontext: '', description: '', is_revision: false, files: {} }
            : ['TimeInputWdg', 'ColorInputWdg'].includes(this.kind(field)) ? field.input.value
            : field.values[0] ?? null]))
        this.baseline = JSON.parse(JSON.stringify(this.draft))
        await nextTick()
        if (!this.mobile) this.$refs.dialog.querySelector('input:not(:disabled), textarea:not(:disabled), select:not(:disabled)')?.focus()
      } catch (error) {
        if (id === this.request) this.error = error instanceof TypeError ? 'Unable to reach the server.' : error.message
      } finally { if (id === this.request) this.loading = false }
    },
    cancel() {
      if (this.saving) return
      if (this.dirty || this.uncertain) this.discard = true
      else this.close()
    },
    close() {
      if (this.saving) return
      this.request++
      this.definition = null
      this.draft = this.baseline = {}
      this.files = {}
      this.uncertain = false
      this.$refs.dialog.close()
    },
    async save() {
      if (!this.contextValid || this.loading || this.saving || this.uncertain || this.blocked || !this.fieldsToSave.length) return
      const request = this.request
      this.saving = true
      this.error = ''
      const files = Object.values(this.files).flat()
      if (new Set(files.map(file => file.name.toLowerCase())).size !== files.length) {
        this.error = 'Choose different file names for separate upload fields.'
        this.saving = false
        return
      }
      const values = { search_type: this.definition.search_type, search_id: '-1' }
      for (const field of this.batch ? this.fieldsToSave : this.definition.fields) {
        let value = this.draft[field.name]
        if (this.kind(field) === 'FileInput') value = ''
        if (this.kind(field) === 'MultiUpload') value = ''
        if (this.kind(field) === 'MultiSelectWdg') value = value.map(item => String(item))
        if (this.kind(field) === 'TimeInputWdg' && ['TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'].includes(field.action.handler)) {
          const [hour, minute] = String(value).split(':')
          values[`${this.inputName(field)}|hour`] = hour
          values[`${this.inputName(field)}|minute`] = minute
        }
        else if (this.kind(field) === 'TimeInputWdg' && value === this.baseline[field.name]) value = field.input.unchanged_value
        if (this.kind(field) === 'CalendarInputWdg') {
          value = value === this.baseline[field.name] ? field.input.unchanged_value
            : value ? value + field.input.value_suffix : ''
        }
        values[this.inputName(field)] = value
      }
      const args = { view: this.definition.view, search_key: this.definition.search_key,
        input_prefix: this.definition.input_prefix, element_names: this.fieldsToSave
          .filter(field => this.kind(field) !== 'MultiUpload' || Object.values(this.draft[field.name].files).some(files => files.length))
          .map(field => field.name) }
      if (this.definition.parent_key) args.parent_key = this.definition.parent_key
      if (this.definition.connect_key) args.connect_key = this.definition.connect_key
      if (this.batch) {
        delete args.search_key
        args.search_keys = this.definition.search_keys
        args.update_data = JSON.stringify(args.search_keys.map(() => Object.fromEntries(
          this.fieldsToSave.map(field => [field.name, values[this.inputName(field)]]))))
        args.extra_data = JSON.stringify(args.search_keys.map(() => ({})))
        args.extra_action = JSON.stringify(args.search_keys.map(() => ({})))
      }
      try {
        for (const field of this.fieldsToSave.filter(field => this.kind(field) === 'FileInput')) {
          const file = this.files[field.name]
          const prefix = this.inputName(field)
          values[`${prefix}|context`] = field.input.context
          values[`${prefix}|column`] = field.input.column
          if (file) {
            values[`${prefix}|path`] = await uploadFormFile(this.context.ticket, this.context.project, file)
            values[`${prefix}|ticket`] = this.context.ticket
          }
        }
        for (const field of this.fieldsToSave.filter(field => this.kind(field) === 'MultiUpload')) {
          const prefix = this.inputName(field)
          for (const name of ['context', 'subcontext', 'description', 'is_revision']) values[`${prefix}|${name}`] = this.draft[field.name][name]
          if (field.input.column) values[`${prefix}|column`] = field.input.column
          for (const slot of field.input.fields) {
            const files = this.files[`${field.name}|${slot.name}`] || []
            for (const [index, file] of files.entries()) {
              const name = field.input.arbitrary ? `${field.name}${index}` : slot.name
              const input = this.definition.input_prefix ? `${this.definition.input_prefix}|${name}` : name
              values[`${input}|path`] = await uploadFormFile(this.context.ticket, this.context.project, file)
              values[`${input}|ticket`] = this.context.ticket
            }
          }
        }
        if (!this.contextValid) {
          const error = new Error('Connection context changed. Close this form and reopen it before saving.')
          error.status = 400
          throw error
        }
        if (this.instanceRelation) Object.assign(args, { create: true, search_type: this.searchType,
          instance_parent_key: this.instanceRelation.parent_key, path: this.instanceRelation.path })
        await rpc('execute_cmd', [this.context, this.instanceRelation ? 'tactic.command.sobject_link_cmd.SObjectLinkCmd' : this.batch ? 'tactic.ui.panel.EditMultipleCmd' : 'tactic.ui.panel.EditCmd', args, values])
        if (request !== this.request || !this.contextValid) return
        this.definition = null
        this.draft = this.baseline = {}
        this.files = {}
        this.$refs.dialog.close()
        this.$emit('saved')
      } catch (error) {
        // A missing response may follow a successful commit. Never retry a write automatically.
        this.uncertain = !error.status || error.status >= 500
        this.error = this.uncertain ? 'The save result is unknown. Close this form and refresh the records before trying again.' : error.message
      } finally { this.saving = false }
    },
  },
}
</script>

<template>
  <dialog v-window="{ type:modal || searchType === 'sthpw/task' ? 'dialog' : 'window' }" ref="dialog" class="record-dialog record-form-dialog" :aria-label="t('Record form')" @cancel.prevent="cancel">
    <slot v-if="$slots.surface" name="surface" :form="{ ...$data }" :save="save" :cancel="cancel" :close="close" :keep="() => { discard = false }" :reportError="value => { error = value }" :contextValid="contextValid" />
    <template v-else>
    <header>
      <div><h2>{{ t(batch ? 'Edit selected' : definition?.source_key ? 'Duplicate record' : definition?.mode === 'edit' ? 'Edit record' : 'Create record') }}</h2><small class="muted">{{ batch ? t('{count} selected records', { count: definition.search_keys.length }) : definition?.source_key || definition?.search_key || searchType }}</small></div>
      <AppButton label="Close" icon="close" :icon-only="mobile" :disabled="saving" @click="cancel" />
    </header>
    <p v-if="loading" role="status">{{ t('Loading data…') }}</p>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <template v-if="definition">
      <p v-if="definition.parent_key" class="notice">{{ t('The new record will belong to this parent: {key}', { key: definition.parent_key }) }}</p>
      <p v-if="definition.source_key" class="notice">{{ t('Copies the editable fields in the creation form. Related objects and repository files are not copied. The new object receives its own code and timestamps.') }}</p>
      <p v-if="batch" class="notice">{{ t('Select the fields to apply to every selected record. Values start from the first record; unselected fields keep their own values.') }}</p>
      <p v-if="blocked" class="notice">{{ t('This form contains unsupported inputs or options. Saving is unavailable.') }} {{ unsupported.map(field => field.title).join(', ') }}</p>
      <p v-else-if="!definition.fields.length" class="notice">{{ t('This view has no elements.') }}</p>
      <form v-if="definition.fields.length" class="record-form" @submit.prevent="save">
        <fieldset :disabled="!contextValid || saving || uncertain || blocked">
          <div v-for="(field, index) in definition.fields" :key="index" class="record-field" :class="{ 'configuration-toggle': !batch && kind(field) === 'CheckboxWdg' }" v-show="kind(field) !== 'HiddenWdg'">
            <label v-if="batch" class="configuration-toggle batch-field-toggle">
              {{ t('Apply {field}', { field: field.title }) }}
              <input type="checkbox" v-model="selectedFields" :value="field.name" :disabled="!batchFields.includes(field)">
            </label>
            <small v-if="batch && field.mixed" class="muted">{{ t('The selected records have different values.') }}</small>
            <small v-if="batch && !readOnly(field) && !batchFields.includes(field)" class="muted">{{ t('Edit this field on one record at a time.') }}</small>
            <label v-if="!['MultiUpload', 'MultiSelectWdg'].includes(kind(field))" :for="`record-field-${formId}-${index}`">{{ field.title }}</label>
            <span v-if="kind(field) === 'ParentInput'" :id="`record-field-${formId}-${index}`">{{ field.input.no_parent_type ? t('No parent type') : field.input.project ? t('Project: {project}', { project: field.input.project }) : field.input.label }}</span>
            <input v-else-if="kind(field) === 'HiddenWdg'" type="hidden" :name="inputName(field)" :value="draft[field.name]">
            <AppColorInput v-else-if="kind(field) === 'ColorInputWdg'" :id="`record-field-${formId}-${index}`" v-model="draft[field.name]" :name="inputName(field)"
              :label="field.title" :readonly="readOnly(field)" :disabled="batch && disabled(field)" :required="required(field)" />
            <input v-else-if="kind(field) === 'FileInput'" :id="`record-field-${formId}-${index}`" type="file" :name="inputName(field)" :disabled="disabled(field)" :required="required(field)"
              @change="selectFile(field, $event)">
            <fieldset v-else-if="kind(field) === 'MultiUpload'" :id="`record-field-${formId}-${index}`" :disabled="disabled(field)" class="compound-upload">
              <legend>{{ field.title }}</legend>
              <label v-for="slot in field.input.fields" :key="slot.name">{{ slot.name }}
                <input type="file" :multiple="field.input.arbitrary" :required="slot.required && (definition.mode === 'insert' || Object.values(draft[field.name].files).some(files => files.length))"
                  @change="selectUploads(field, `${field.name}|${slot.name}`, $event)">
              </label>
              <label>{{ t('Context') }}
                <select v-if="field.input.context.type === 'select'" v-model="draft[field.name].context" :aria-label="t('Context')">
                  <option v-for="(value, option) in field.input.context.choices" :key="option" :value="value">{{ field.input.context.labels[option] }}</option>
                </select>
                <input v-else v-model="draft[field.name].context">
              </label>
              <label v-if="field.input.subcontext">{{ t('Subcontext') }}<input v-model="draft[field.name].subcontext"></label>
              <label>{{ t('Comment') }}<textarea v-model="draft[field.name].description" rows="3" /></label>
              <div class="configuration-toggle"><span>{{ t('Is revision') }}</span><AppSwitch v-model="draft[field.name].is_revision" label="Is revision" /></div>
            </fieldset>
            <AppSwitch v-else-if="kind(field) === 'CheckboxWdg'" :id="`record-field-${formId}-${index}`" :name="inputName(field)" :model-value="checked(draft[field.name])"
              :disabled="disabled(field)" :required="required(field)" @update:model-value="draft[field.name] = $event" />
            <input v-else-if="kind(field) === 'TimeInputWdg'" :id="`record-field-${formId}-${index}`" type="time" step="60" v-model="draft[field.name]" :name="inputName(field)"
              :readonly="readOnly(field)" :disabled="batch && disabled(field)" :required="required(field)">
            <AppDateField v-else-if="kind(field) === 'CalendarInputWdg'" :id="`record-field-${formId}-${index}`" :include-time="field.input.type !== 'date'" :label="field.title"
              :model-value="draft[field.name] === baseline[field.name] ? field.input.value : draft[field.name]" :name="inputName(field)"
              :readonly="readOnly(field)" :disabled="batch && disabled(field)" :required="required(field)" @update:model-value="draft[field.name] = $event === field.input.value ? baseline[field.name] : $event" />
            <select v-else-if="kind(field) === 'SelectWdg'" :id="`record-field-${formId}-${index}`" v-model="draft[field.name]" :name="inputName(field)" :disabled="disabled(field)" :required="required(field)">
              <option v-if="!field.choices.some(value => String(value) === String(draft[field.name]))" :value="draft[field.name]">{{ draft[field.name] ?? t('Not set') }}</option>
              <option v-for="(value, option) in field.choices" :key="option" :value="value">{{ value === '' && field.labels[option] === field.input?.empty_label ? t(field.labels[option]) : field.labels[option] }}</option>
            </select>
            <fieldset v-else-if="kind(field) === 'MultiSelectWdg'" :id="`record-field-${formId}-${index}`" :disabled="disabled(field)">
              <legend>{{ field.title }}</legend>
              <label v-for="(value, option) in field.choices" :key="option" class="configuration-toggle">{{ field.labels[option] }}
                <input type="checkbox" v-model="draft[field.name]" :value="value" :name="inputName(field)" :required="required(field) && !draft[field.name].length && option === 0">
              </label>
            </fieldset>
            <textarea v-else-if="kind(field) === 'TextAreaWdg'" :id="`record-field-${formId}-${index}`" :value="draft[field.name]" :name="inputName(field)" :readonly="readOnly(field)" :disabled="batch && disabled(field)"
              :required="required(field)" :rows="field.options.rows || 3" :cols="field.options.cols || 50" @input="draft[field.name] = $event.target.value" />
            <input v-else-if="kind(field) === 'TextWdg'" :id="`record-field-${formId}-${index}`" :value="draft[field.name]" :name="inputName(field)" :readonly="readOnly(field)" :disabled="batch && disabled(field)"
              :required="required(field)" :size="field.options.size || null" @input="draft[field.name] = $event.target.value">
            <span v-else class="muted">{{ t('Widget unavailable') }}</span>
            <small v-if="field.options.hint || field.options.hint_text" class="muted">{{ field.options.hint || field.options.hint_text }}</small>
            <small v-if="(field.attributes.description || field.attributes.title) && (field.attributes.description || field.attributes.title) !== field.title" class="muted">{{ field.attributes.description || field.attributes.title }}</small>
            <small v-if="field.input?.timezone" class="muted">{{ t('Time zone: {timezone}', { timezone: field.input.timezone === 'local' ? t('Server local time') : field.input.timezone }) }}</small>
          </div>
        </fieldset>
        <div v-if="discard" class="notice" role="alert">
          <p>{{ t('Discard unsaved changes?') }}</p>
          <div class="configuration-actions"><AppButton label="Keep editing" @click="discard = false" /><AppButton label="Discard changes" @click="close" /></div>
        </div>
        <footer class="configuration-actions"><AppButton highlighted type="submit" :label="saving ? 'Saving…' : 'Save record'" icon="save" :disabled="!contextValid || saving || uncertain || blocked || !fieldsToSave.length || (definition.mode === 'edit' && !dirty)" /></footer>
      </form>
    </template>
    </template>
  </dialog>
</template>
<style>
@media(max-width:700px) {
  .record-form-dialog[open] { display:flex; flex-direction:column; overflow:hidden; }
  .record-form-dialog > header { flex-wrap:nowrap; flex-shrink:0; gap:8px; margin:0 0 6px; }
  .record-form-dialog > header > div { flex:1; min-width:0; }
  .record-form-dialog > header h2 { font-size:var(--text-body-large); margin:0; }
  .record-form-dialog > header small { margin-top:2px; max-height:36px; overflow:auto; }
  .record-form-dialog > p { flex-shrink:0; margin:4px 0; max-height:20dvh; overflow:auto; }
  .record-form-dialog > .record-form { display:flex; flex-direction:column; flex:1; min-height:0; margin-top:4px; gap:8px; }
  .record-form-dialog .record-form > fieldset { flex:1; min-height:0; overflow:auto; overscroll-behavior:contain; padding:0 2px; align-content:start; }
  .record-form-dialog .record-form input:not([type=checkbox]), .record-form-dialog .record-form select, .record-form-dialog .record-form textarea { font-size:16px; }
  .record-form-dialog .record-form footer { flex-shrink:0; margin:0; padding-bottom:env(safe-area-inset-bottom); justify-content:flex-end; }
  .record-form-dialog .record-form > .notice { flex-shrink:0; margin:0; max-height:30dvh; overflow:auto; }
}
</style>
