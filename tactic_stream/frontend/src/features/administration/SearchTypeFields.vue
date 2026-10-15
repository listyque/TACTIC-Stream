<script>
import { useId } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import SettingRow from '../../controls/SettingRow.vue'
import { automaticFields, fieldTypes, removalReasons } from './searchTypeFields.js'

export default {
  setup() { return { uid: useId() } },
  components: { AppButton, AppSelect, SettingRow },
  props: { document: Object, metadata: Object, creating: Boolean, disabled: Boolean },
  emits: ['add', 'remove-draft', 'toggle-deletion'],
  data() { return { name: '', type: 'varchar(256)', search: '' } },
  computed: {
    automaticFields() { return automaticFields },
    fieldTypes() { return fieldTypes.map(row => ({ value: row.value, label: t(row.label) })) },
    selectedType() { return fieldTypes.find(row => row.value === this.type) },
    existing() { return Object.entries(this.metadata.columns || {}).filter(([name]) => name.toLowerCase().includes(this.search.toLowerCase())) },
  },
  methods: {
    t,
    removalReason(name) { return t(removalReasons[this.metadata.columnRemovalBlocks?.[name]] || '') },
    marked(name) { return this.document.removedColumns.includes(name) },
    fieldDescription(info) {
      const name = String(info.data_type || '').toLowerCase().split('(')[0].trim()
      const types = { varchar: 0, 'character varying': 0, character: 0, char: 0, text: 1,
        integer: 2, bigint: 2, smallint: 2, int: 2, int4: 2, int8: 2,
        numeric: 3, decimal: 3, real: 3, 'double precision': 3, boolean: 4, bool: 4 }
      const type = fieldTypes[name.startsWith('timestamp') ? 5 : types[name]]
      const parts = [type ? `${t(type.label)} · ${info.data_type}` : info.data_type || '']
      if (info.character_maximum_length) parts.push(t('Up to {count} characters', { count: info.character_maximum_length }))
      if (info.is_nullable === 'NO' || info.is_nullable === false) parts.push(t('Cannot be empty in the database'))
      if (type) parts.push(t('Example value: {value}', { value: t(type.example) }))
      return parts.join('\n')
    },
    add() { this.$emit('add', this.name, this.type) },
    clearName() { this.name = '' },
  },
}
</script>

<template>
  <section class="search-type-fields">
    <div v-if="creating" class="configuration-group">
      <h2>{{ t('Default fields') }}</h2>
      <p class="muted">{{ t('TACTIC creates these fields automatically. Add only extra fields below.') }}</p>
      <p>{{ automaticFields.join(', ') }}</p>
      <p class="muted">{{ document.hasPipeline ? t('pipeline_code will also be created: pipeline support is enabled.') : t('pipeline_code will not be created: pipeline support is disabled.') }}</p>
    </div>
    <div class="configuration-group">
      <h2>{{ t('Add a field') }}</h2>
      <p class="muted">{{ t('A field stores one attribute of each Search Object. Define its name and type here; fill in actual values when editing the objects.') }}</p>
      <SettingRow :control-id="uid + '-new-field-name'" title="Field name" description="A technical name: lowercase Latin letters, numbers and underscores. No spaces; start with a letter.">
        <input :id="uid + '-new-field-name'" v-model="name" :disabled="disabled" :placeholder="selectedType.name" :aria-describedby="uid + '-new-field-name-help'" @keydown.enter.prevent="add">
      </SettingRow>
      <SettingRow :control-id="uid + '-new-field-type'" title="Field type" :description="selectedType.help">
        <AppSelect :id="uid + '-new-field-type'" v-model="type" :options="fieldTypes" label="Field type" :disabled="disabled" />
      </SettingRow>
      <p class="muted">{{ t('Example: {name} = {value}', { name: name.trim() || selectedType.name, value: t(selectedType.example) }) }} · {{ t('Database type: {type}', { type }) }}</p>
      <AppButton label="Add field" icon="add" :disabled="disabled || !name.trim()" @click="add" />
    </div>
    <div v-if="document.columns.length" class="configuration-group">
      <h2>{{ t('Fields to create ({count})', { count: document.columns.length }) }}</h2>
      <p class="muted">{{ t('These fields exist only in your draft. Save creates them; removing a draft field does not change the database.') }}</p>
      <SettingRow v-for="(field, index) in document.columns" :key="field.name" :title="field.name" :description="fieldDescription({ data_type: field.type })">
        <AppButton :label="t('Remove draft field {name}', { name: field.name })" icon="delete" icon-only :disabled="disabled" @click="$emit('remove-draft', index)" />
      </SettingRow>
    </div>
    <div v-if="!creating" class="configuration-group">
      <h2>{{ t('Existing fields ({count})', { count: Object.keys(metadata.columns || {}).length }) }}</h2>
      <p class="muted">{{ t('Delete marks a field for removal. Undo cancels the mark. Confirming Save deletes the column and its values; field types are not changed here.') }}</p>
      <label>{{ t('Find a field') }}<input v-model="search" type="search" :disabled="disabled" /></label>
      <SettingRow v-for="[name, info] in existing" :key="name" :title="name" :description="marked(name) ? t('Marked for deletion. The column and its data will be deleted when you save.') : fieldDescription(info) + (removalReason(name) ? '\n' + removalReason(name) : '')">
        <AppButton :label="t(marked(name) ? 'Undo deletion of {name}' : 'Delete field {name}', { name })" :icon="marked(name) ? 'reset' : 'delete'" :destructive="!marked(name) && !removalReason(name)" :disabled="disabled || (!marked(name) && !!removalReason(name))" :title="removalReason(name) || undefined" @click="$emit('toggle-deletion', name)" />
      </SettingRow>
      <p v-if="!existing.length" class="muted">{{ t('No fields found') }}</p>
    </div>
  </section>
</template>
