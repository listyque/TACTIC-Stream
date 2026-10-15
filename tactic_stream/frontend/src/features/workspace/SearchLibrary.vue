<script>
// Handler FilterEditorController / SearchPresetBar / AdvancedSearchView.
import { searchConfiguration } from '../../api.js'
import { toRaw } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { copyText } from '../../controls/clipboard.js'
import { savedSearchLink, browserLink } from './links.js'

export default {
  components: { AppButton, AppSelect, AppSwitch, AppIcon },
  props: { ticket: String, project: String, searchType: String, scope: String, records: Array, preset: String, canManage: Boolean, keyword: String, orderBys: Array },
  emits: ['apply', 'changed'],
  data() { return { catalog: null, selected: '', rows: [], baseline: '', busy: false, error: '', confirmation: '', title: '', action: '', uncertain: false, link: '', searchKeyword: '', orders: [] } },
  computed: {
    dirty() { return JSON.stringify(this.rows) !== this.baseline },
    current() { return this.catalog?.presets.find(row => row.view === this.selected) },
    columns() { return [...Object.keys(this.catalog?.columns || {}).map(value => ({ value, label: value })), { value: '_expression', label: t('Expression') }] },
    presetOptions() { return [{ value: '', label: t('Select a saved search') }, ...(this.catalog?.presets || []).map(row => ({ value: row.view, label: row.title }))] },
  },
  methods: {
    t,
    async open() {
      this.context = { ticket: this.ticket, project: this.project, type: this.searchType, scope: this.scope }
      this.rows = structuredClone(toRaw(this.records || [])); this.baseline = JSON.stringify(this.rows)
      this.searchKeyword = this.keyword || ''; this.orders = [...(this.orderBys || [])]
      this.selected = this.preset || ''; this.catalog = null; this.error = ''; this.link = ''; this.confirmation = ''; this.action = ''; this.uncertain = false
      this.$refs.dialog.showModal(); await this.load()
    },
    async load() {
      this.busy = true; this.error = ''
      try { this.catalog = await searchConfiguration('settings', this.context.ticket, this.context.project, this.context.type, { scope: this.context.scope }); this.uncertain = false }
      catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    async refresh() { if (this.dirty) { this.confirmation = 'refresh'; return }; await this.load(); if (!this.error) this.selectNow(this.selected) },
    select(value) {
      if (this.dirty) { this.confirmation = 'select'; this.pending = value; return }
      this.selectNow(value)
    },
    selectNow(value) {
      const preset = this.catalog.presets.find(row => row.view === value)
      if (preset?.error) { this.error = preset.error; return }
      this.selected = value; this.rows = structuredClone(toRaw(preset?.records || [])); this.baseline = JSON.stringify(this.rows); this.confirmation = ''
      this.searchKeyword = preset?.keyword || ''; this.orders = [...(preset?.order_bys || [])]
    },
    add() {
      const column = 'name' in this.catalog.columns ? 'name' : Object.keys(this.catalog.columns)[0]
      this.rows.push({ column, relation: '=', value: '', rowEnabled: true, operator: this.rows.length ? 'and' : 'begin' })
    },
    move(index, delta) { this.rows.splice(index + delta, 0, this.rows.splice(index, 1)[0]); this.normalize() },
    normalize() { this.rows.forEach((row, index) => { row.operator = index ? row.operator === 'or' ? 'or' : 'and' : 'begin' }) },
    remove(index) { this.rows.splice(index, 1); this.normalize() },
    relations(row) { return row.column === '_expression' ? [{ value: 'in', label: 'Have' }, { value: 'not in', label: 'Do not have' }, { value: 'match', label: 'Match (slow)' }, { value: 'do not match', label: 'Do not match (slow)' }] : this.catalog.relations },
    prompt(action) { this.action = action; this.title = action === 'rename' ? this.current.title : action === 'duplicate' ? this.current.title + ' copy' : ''; this.$refs.nameDialog.showModal() },
    async save(action = 'update') {
      if (this.busy || this.uncertain) return
      this.busy = true; this.error = ''
      const title = action === 'update' ? this.current.title : this.title
      const code = ['update', 'rename'].includes(action) ? this.current.code : undefined
      try {
        const result = await searchConfiguration('save', this.context.ticket, this.context.project, this.context.type,
          { scope: action === 'new' || action === 'duplicate' ? this.context.scope : this.context.type,
            revision: this.catalog.revision, code, title, records: this.rows, keyword: this.searchKeyword, order_bys: this.orders })
        this.catalog = result; this.baseline = JSON.stringify(this.rows)
        this.selected = code ? result.presets.find(row => row.code === code)?.view || '' : result.presets.find(row => row.title === title)?.view || ''
        this.$refs.nameDialog.close(); this.$emit('changed', result)
      } catch (error) { this.error = error.message; this.uncertain = !error.status || error.status >= 500 }
      finally { this.busy = false }
    },
    async removePreset() {
      this.busy = true; this.error = ''; this.confirmation = ''
      try {
        this.catalog = await searchConfiguration('delete', this.context.ticket, this.context.project, this.context.type, { scope: this.context.scope, code: this.current.code, revision: this.catalog.revision })
        this.selected = ''; this.$emit('changed', this.catalog)
      } catch (error) { this.error = error.message; this.uncertain = !error.status || error.status >= 500 }
      finally { this.busy = false }
    },
    async copyLink() {
      const link = new URL(browserLink(savedSearchLink(this.context.project, this.context.type, this.selected)), location.origin).href
      try { await copyText(link); this.link = '' }
      catch { this.link = link }
    },
    apply() { this.normalize(); this.$emit('apply', { records: structuredClone(toRaw(this.rows)), preset: this.selected, keyword: this.searchKeyword, order_bys: this.orders }); this.$refs.dialog.close() },
    close() { if (this.busy) return; if (this.dirty || this.uncertain) this.confirmation = 'close'; else this.$refs.dialog.close() },
    async confirm() {
      if (this.confirmation === 'delete') this.removePreset()
      else if (this.confirmation === 'select') this.selectNow(this.pending)
      else if (this.confirmation === 'refresh') { this.confirmation = ''; await this.load(); if (!this.error) this.selectNow(this.selected) }
      else { this.$refs.dialog.close(); this.confirmation = '' }
    },
  },
}
</script>

<template>
  <dialog v-window ref="dialog" class="record-dialog search-library-dialog" :aria-label="t('Saved searches')" @cancel.prevent="close">
    <section class="search-library-shell" :aria-busy="busy">
      <header><div><h2>{{ t('Saved searches') }}</h2><p class="muted">{{ project }} · {{ searchType }}</p></div><AppButton icon-only label="Refresh saved searches" icon="refresh" :disabled="busy" @click="refresh" /><AppButton label="Close" icon="close" :disabled="busy" @click="close" /></header>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="uncertain" class="notice">{{ t('The save result is unknown. Reload before trying again.') }}</p>
      <div v-if="confirmation" class="notice" role="alert"><p>{{ t(confirmation === 'delete' ? 'Delete the selected saved search?' : 'Discard unsaved filter changes?') }}</p><AppButton label="Keep editing" @click="confirmation = ''" /><AppButton :label="confirmation === 'delete' ? 'Delete preset' : 'Discard changes'" destructive @click="confirm" /></div>
      <template v-if="catalog">
        <div class="search-preset-bar"><AppSelect :model-value="selected" :options="presetOptions" :translate-labels="false" label="Select a saved search" :disabled="busy" @update:model-value="select" />
          <AppButton icon-only label="Update selected preset" icon="save" :disabled="!canManage || !current || busy || uncertain" @click="save()" /><AppButton icon-only label="Save as new preset" icon="add" :disabled="!canManage || busy || uncertain" @click="prompt('new')" />
          <details class="workspace-menu"><summary class="icon-button" :aria-label="t('Saved search actions')"><AppIcon name="more" /></summary><div class="account-panel">
            <AppButton label="Rename preset" icon="edit" :disabled="!canManage || !current || busy || uncertain" @click="prompt('rename')" /><AppButton label="Duplicate preset" icon="duplicate" :disabled="!canManage || !current || busy || uncertain" @click="prompt('duplicate')" /><AppButton label="Copy saved search link" icon="link" :disabled="!current || busy" @click="copyLink" /><AppButton label="Delete preset" icon="delete" :disabled="!canManage || !current || busy || uncertain" @click="confirmation = 'delete'" />
          </div></details>
        </div>
        <input v-if="link" :value="link" readonly :aria-label="t('Saved search link')">
        <div class="search-library-conditions"><header><h3>{{ t('Filters') }}</h3><AppButton label="Add filter" icon="add" :disabled="busy" @click="add" /><AppButton label="Reset filters" icon="reset" :disabled="busy" @click="rows = []" /></header>
          <article v-for="(row, index) in rows" :key="index" class="configuration-group search-condition">
            <AppSwitch v-model="row.rowEnabled" :label="t('Enable condition {number}', { number: index + 1 })" :disabled="busy" />
            <AppSelect v-if="index" v-model="row.operator" :options="[{ value: 'and', label: 'AND' }, { value: 'or', label: 'OR' }]" label="Condition operator" :disabled="busy" />
            <AppSelect v-model="row.column" :options="columns" :translate-labels="false" label="Filter column" :disabled="busy" @change="row.relation = row.column === '_expression' ? 'in' : '='" />
            <AppSelect v-model="row.relation" :options="relations(row)" label="Filter relation" :disabled="busy" />
            <input v-model="row.value" :aria-label="t('Filter value')" :disabled="busy || ['is empty', 'is not empty'].includes(row.relation)">
            <div class="configuration-actions"><AppButton icon-only label="Move up" icon="previous" :disabled="busy || index === 0" @click="move(index, -1)" /><AppButton icon-only label="Move down" icon="next" :disabled="busy || index === rows.length - 1" @click="move(index, 1)" /><AppButton icon-only label="Remove condition" icon="delete" :disabled="busy" @click="remove(index)" /></div>
          </article>
          <p v-if="!rows.length" class="muted">{{ t('No filters selected') }}</p>
        </div>
        <footer><AppButton label="Apply filters" icon="search" highlighted :disabled="busy || uncertain" @click="apply" /><AppButton label="Cancel" :disabled="busy" @click="close" /></footer>
      </template>
    </section>
  </dialog>
  <dialog ref="nameDialog" class="record-dialog" :aria-label="t(action === 'rename' ? 'Rename preset' : action === 'duplicate' ? 'Duplicate preset' : 'Save filter preset')" @cancel.prevent="!busy && $refs.nameDialog.close()">
    <form @submit.prevent="save(action)"><h2>{{ t(action === 'rename' ? 'Rename preset' : action === 'duplicate' ? 'Duplicate preset' : 'Save filter preset') }}</h2><label>{{ t('Preset name') }}<input v-model="title" required maxlength="256" :disabled="busy"></label><p v-if="error" class="error" role="alert">{{ t(error) }}</p><div class="configuration-actions"><AppButton label="Save" icon="save" highlighted type="submit" :disabled="busy || uncertain" /><AppButton label="Cancel" :disabled="busy" @click="$refs.nameDialog.close()" /></div></form>
  </dialog>
</template>
