<script>
// Handler QuickFilterEditorController and QuickFilterEditorView.
import { searchConfiguration } from '../../api.js'
import { toRaw } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSwitch from '../../controls/AppSwitch.vue'

export default {
  components: { AppButton, AppSwitch },
  props: { ticket: String, project: String, searchType: String, tabId: String, scope: String, selections: Object, layout: Object, canManage: Boolean },
  emits: ['apply', 'changed'],
  data() { return { catalog: null, groups: [], selected: {}, original: {}, baseline: '', busy: false, error: '', message: '', showHidden: false, confirmation: false, uncertain: false, request: 0 } },
  computed: { contextKey() { return [this.ticket, this.project, this.searchType, this.tabId, this.scope] }, dirty() { return JSON.stringify(this.configuration()) !== this.baseline }, chips() { return Object.entries(this.selected).flatMap(([key, values]) => values.map(value => ({ key, value, title: (this.groups.find(group => group.key === key)?.title || key) + ': ' + (this.groups.find(group => group.key === key)?.options.find(option => option.key === value)?.title || value) }))) } },
  watch: { contextKey() { this.request++; this.busy = false; this.catalog = null; this.error = 'Search context changed. Reopen the editor.' } },
  beforeUnmount() { this.request++ },
  methods: {
    t, toRaw,
    async open(catalog = null) {
      const request = ++this.request
      this.context = { ticket: this.ticket, project: this.project, type: this.searchType, scope: this.scope }
      this.error = ''; this.message = ''; this.catalog = null; this.confirmation = false; this.uncertain = false; this.$refs.dialog.showModal(); this.busy = true
      try {
        const result = catalog || await searchConfiguration('read', this.context.ticket, this.context.project, this.context.type, { scope: this.context.scope })
        if (request !== this.request) return
        this.catalog = result
        this.original = structuredClone(toRaw(this.layout || this.catalog.configuration))
        this.selected = structuredClone(toRaw(this.selections || this.original.defaultSelections || {}))
        const settings = new Map(this.original.groups.map(row => [row.key, row]))
        const standard = new Map(this.catalog.configuration.groups.map(row => [row.key, row]))
        const order = [...settings.keys(), ...this.catalog.groups.map(row => row.key).filter(key => !settings.has(key))]
        this.groups = order.map(key => {
          const group = this.catalog.groups.find(row => row.key === key)
          if (!group || !this.canManage && standard.get(key)?.enabled === false) return null
          const config = settings.get(key) || {}
          return { ...group, enabled: config.enabled !== false, options: group.options.filter(option => this.canManage || !standard.get(key)?.options || standard.get(key).options.includes(option.key)).map(option => ({ ...option, enabled: !config.options || config.options.includes(option.key) })) }
        }).filter(Boolean)
        this.sanitize(); this.baseline = JSON.stringify(this.configuration())
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    configuration() {
      const known = new Set(this.groups.map(row => row.key))
      const groups = this.groups.map(row => {
        const previous = this.original.groups?.find(group => group.key === row.key) || {}
        return { ...previous, key: row.key, enabled: row.enabled }
      }).concat((this.original.groups || []).filter(row => !known.has(row.key)))
      return { groups, defaultSelections: structuredClone(toRaw(this.selected)) }
    },
    sanitize() {
      for (const [key, values] of Object.entries(this.selected)) {
        const group = this.groups.find(row => row.key === key)
        if (!group) continue // Preserve selections absent from the current catalog.
        const allowed = new Set(group.options.filter(option => option.enabled).map(option => option.key))
        this.selected[key] = group.enabled ? values.filter(value => allowed.has(value)) : []
        if (!this.selected[key].length) delete this.selected[key]
      }
    },
    toggle(group, value) {
      const values = new Set(this.selected[group.key] || [])
      if (values.has(value)) values.delete(value); else values.add(value)
      if (values.size) this.selected[group.key] = [...values].sort(); else delete this.selected[group.key]
    },
    remove(key, value) { this.selected[key] = this.selected[key].filter(item => item !== value); if (!this.selected[key].length) delete this.selected[key] },
    move(index, delta) { this.groups.splice(index + delta, 0, this.groups.splice(index, 1)[0]) },
    apply() { if (!this.catalog || this.busy || this.uncertain) return; this.sanitize(); this.$emit('apply', this.configuration()); this.baseline = JSON.stringify(this.configuration()); this.message = 'Quick filters saved for this tab' },
    async saveDefaults() {
      if (!this.canManage || !this.catalog || this.busy || this.uncertain) return
      const request = this.request
      this.busy = true; this.error = ''; this.message = ''; this.sanitize()
      try {
        const catalog = await searchConfiguration('quick-save', this.context.ticket, this.context.project, this.context.type, { scope: this.context.scope, revision: this.catalog.revision, configuration: this.configuration() })
        if (request !== this.request) return
        this.catalog = catalog
        this.original = structuredClone(toRaw(this.catalog.configuration)); this.baseline = JSON.stringify(this.configuration()); this.$emit('changed', this.catalog)
        this.message = 'Quick-filter defaults saved on server'
      } catch (error) { if (request === this.request) { this.error = error.message; this.uncertain = !error.status || error.status >= 500 } }
      finally { if (request === this.request) this.busy = false }
    },
    close() { if (this.busy) return; if (this.dirty || this.uncertain) this.confirmation = true; else this.$refs.dialog.close() },
  },
}
</script>

<template>
  <dialog v-window ref="dialog" class="configuration-dialog quick-filter-editor-dialog" :aria-label="t('Quick filters')" @cancel.prevent="close">
    <section class="search-library-shell" :aria-busy="busy">
      <header><div><h2>{{ t('Quick filters') }}</h2><p class="muted">{{ project }} · {{ searchType }}</p></div><AppButton label="Close" icon="close" :disabled="busy" @click="close" /></header>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="message" class="notice" role="status">{{ t(message) }}</p>
      <p v-if="uncertain" class="notice">{{ t('The save result is unknown. Reload before trying again.') }}</p>
      <div v-if="confirmation" class="notice" role="alert"><p>{{ t('Discard unsaved filter changes?') }}</p><AppButton label="Keep editing" @click="confirmation = false" /><AppButton label="Discard changes" destructive @click="$refs.dialog.close(); confirmation = false" /></div>
      <div v-if="catalog" class="search-library-conditions">
        <section class="configuration-group"><h3>{{ t('Selected filters') }}</h3><div class="configuration-actions quick-filter-chips"><AppButton class="quick-filter-chip" v-for="chip in chips" :key="chip.key + ':' + chip.value" icon="close" :disabled="busy" @click="remove(chip.key, chip.value)">{{ chip.title }}</AppButton></div><p v-if="!chips.length" class="muted">{{ t('No filters selected') }}</p>
          <div class="configuration-actions"><AppButton label="Copy selection from current tab" icon="duplicate" :disabled="busy" @click="selected = structuredClone(toRaw(selections || {})); sanitize()" /><AppButton label="Clear selected filters" icon="reset" :disabled="busy || !chips.length" @click="selected = {}" /></div>
        </section>
        <header><h3>{{ t('Available filters') }}</h3><AppSwitch v-model="showHidden" label="Show hidden filters" /></header>
        <article v-for="(group, index) in groups" v-show="group.enabled || showHidden" :key="group.key" class="configuration-group">
          <header class="search-preset-bar"><AppSwitch v-model="group.enabled" :aria-label="group.title" :disabled="busy" @update:model-value="sanitize" /><h3>{{ ['process', 'status', 'assigned'].includes(group.key) ? t(group.title) : group.title }}</h3><div class="configuration-actions"><AppButton icon-only label="Move up" icon="previous" :disabled="busy || index === 0" @click="move(index, -1)" /><AppButton icon-only label="Move down" icon="next" :disabled="busy || index === groups.length - 1" @click="move(index, 1)" /></div></header>
          <div v-if="group.enabled" class="quick-filter-chips"><AppButton class="quick-filter-chip" v-for="option in group.options" :key="option.key" :aria-pressed="(selected[group.key] || []).includes(option.key)" :highlighted="(selected[group.key] || []).includes(option.key)" :disabled="busy || !option.enabled" @click="toggle(group, option.key)">{{ option.key === '__current_login__' ? t('MY TASKS') : option.title }}<small v-if="option.count !== undefined">{{ option.count }}</small></AppButton></div>
        </article>
        <p v-if="!groups.length" class="muted">{{ t('No filters available') }}</p>
      </div>
      <footer><AppButton label="Save for this tab" icon="save" highlighted :disabled="busy || !catalog || uncertain" @click="apply" /><AppButton v-if="canManage" label="Save as defaults on server" icon="upload" :disabled="busy || !catalog || uncertain" @click="saveDefaults" /><AppButton label="Cancel" :disabled="busy" @click="close" /></footer>
    </section>
  </dialog>
</template>
