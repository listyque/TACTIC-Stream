<script>
import { widgetConfiguration } from '../../api.js'
import { t } from '../../i18n.js'
import ConfiguredView from './ConfiguredView.vue'
import NavigationTree from '../workspace/NavigationTree.vue'
import { navigationEntries } from '../workspace/workspace.js'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'

export default {
  components: { ConfiguredView, NavigationTree, AppButton, AppSelect },
  props: { ticket: String, project: String, searchType: String, view: String, rows: Array, searchTypes: { type: Array, default: () => [] } },
  emits: ['saved'],
  data() { return { configuration: null, context: null, selectedView: '', source: '', xml: '', baseline: '', checked: '', diff: '', preview: null, error: '', busy: false, uncertain: false, discard: false, request: 0 } },
  computed: {
    dirty() { return this.xml !== this.baseline },
    contextValid() { return this.context?.ticket === this.ticket && this.context?.project === this.project && this.context?.origin_search_type === this.searchType && this.context?.origin_view === this.view },
    previewNavigation() { return navigationEntries(this.preview?.navigation?.entries || [], this.searchTypes) },
  },
  watch: {
    ticket() { this.request++; this.checked = '' },
    project() { this.request++; this.checked = '' },
    searchType() { this.request++; this.checked = '' },
    view() { this.request++; this.checked = '' },
    xml() { this.checked = ''; this.diff = ''; this.preview = null },
  },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    beforeUnload(event) { if (this.dirty || this.busy || this.uncertain) { event.preventDefault(); event.returnValue = '' } },
    async open(options = {}) {
      if (this.$refs.dialog.open) return
      const id = ++this.request
      this.context = { ticket: this.ticket, project: this.project, search_type: options.searchType || this.searchType,
        view: options.view || this.view, origin_view: this.view, origin_search_type: this.searchType }
      this.selectedView = this.context.view
      this.configuration = null
      this.preview = null
      this.xml = this.baseline = this.checked = this.error = this.diff = ''
      this.discard = this.uncertain = false
      this.busy = true
      this.$refs.dialog.showModal()
      try {
        const result = await this.call('read')
        if (id !== this.request) return
        this.configuration = result
        this.source = result.sources[0]?.id ?? ''
        this.selectSource()
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    call(action, values = {}) {
      return widgetConfiguration(action, this.context.ticket, this.context.project, this.context.search_type, this.context.view, values)
    },
    async changeView() {
      const id = ++this.request
      this.context.view = this.selectedView
      this.configuration = null
      this.busy = true
      this.error = ''
      try {
        const result = await this.call('read')
        if (id !== this.request) return
        this.configuration = result
        this.source = result.sources[0]?.id ?? ''
        this.selectSource()
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    selectSource() {
      this.preview = null
      this.xml = this.baseline = this.configuration.sources.find(item => item.id === this.source)?.xml ||
        (this.context.view.includes('@') ? `<config><view name="${this.context.view}"/></config>` : `<config><${this.context.view}/></config>`)
      this.checked = this.error = this.diff = ''
    },
    async run(action) {
      if (this.busy || !this.contextValid || this.uncertain || (action === 'save' && this.checked !== this.xml)) return
      const id = this.request
      this.busy = true
      this.error = ''
      try {
        const result = await this.call(action, { source_id: this.source === '' ? null : this.source, xml: this.xml, revision: this.configuration.revision })
        if (id !== this.request) return
        if (action === 'check' || action === 'preview') { this.checked = this.xml; this.diff = result.diff; this.preview = result.interface || null }
        else { this.xml = this.baseline; this.$refs.dialog.close(); this.$emit('saved', result) }
      } catch (error) {
        this.preview = null
        if (action === 'save' && (!error.status || error.status >= 500)) this.uncertain = true
        this.checked = ''
        this.error = this.uncertain ? 'The save result is unknown. Close this form and refresh the records before trying again.' : error.message
      } finally { this.busy = false }
    },
    close() {
      if (this.busy) return
      if (this.dirty && !this.discard) { this.discard = true; return }
      this.request++
      this.xml = this.baseline = ''
      this.$refs.dialog.close()
    },
  },
}
</script>

<template>
  <dialog v-window ref="dialog" class="record-dialog widget-configuration" :aria-label="t('Interface XML')" @cancel.prevent="close">
    <header><div><h2>{{ t(context?.search_type === 'SideBarWdg' ? 'Navigation XML' : 'Interface XML') }}</h2><small>{{ context?.search_type }} · {{ context?.view }}</small></div><AppButton label="Close" icon="close" :disabled="busy" @click="close" /></header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <p v-if="!contextValid" class="notice">{{ t('Connection context changed. Close this form and reopen it before saving.') }}</p>
    <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
    <template v-if="configuration">
      <label>{{ t('Configuration view') }}<AppSelect v-model="selectedView" label="Configuration view" :options="configuration.views.map(name => ({ value: name, label: name }))" :disabled="busy || dirty || uncertain || !contextValid" @update:model-value="changeView" /></label>
      <label>{{ t('Configuration source') }}
        <AppSelect v-model="source" label="Configuration source" :options="[...configuration.sources.map(item => ({ value: item.id, label: `${item.id} · ${t('Priority')} ${item.priority}` })), { value: '', label: t('New override') }]" :disabled="busy || dirty || uncertain || !contextValid" @update:model-value="selectSource" />
      </label>
      <label>{{ t('Source XML') }}<textarea v-model="xml" rows="16" spellcheck="false" :readonly="busy || uncertain || !contextValid" /></label>
      <p class="muted">{{ t('XML validation does not execute widgets or scripts.') }}</p>
      <p v-if="checked" role="status">{{ t('XML is valid. Review the diff before saving.') }}</p>
      <pre v-if="diff" class="xml-diff">{{ diff }}</pre>
      <section v-if="preview && contextValid" class="interface-preview" :aria-label="t('Interface preview')">
        <h3>{{ t('Interface preview') }}</h3><p class="muted">{{ t('Read-only preview. Changes have not been saved.') }}</p>
        <NavigationTree v-if="context.search_type === 'SideBarWdg'" :entries="previewNavigation" :project="context.project" />
        <ConfiguredView v-else :definition="preview" :ticket="context.ticket" :project="context.project" :rows="rows" />
      </section>
      <details><summary>{{ t('Resolved configuration') }}</summary><pre>{{ JSON.stringify(configuration.resolved, null, 2) }}</pre></details>
      <details v-for="(layer, index) in configuration.layers" :key="index"><summary>{{ t('Inherited layer') }} {{ index + 1 }} · {{ layer.view }}</summary><pre>{{ layer.xml }}</pre></details>
      <footer class="configuration-actions">
        <AppButton label="Check XML" icon="check" :disabled="busy || !contextValid || uncertain" @click="run('check')" />
        <AppButton label="Preview interface" icon="search" :disabled="busy || !contextValid || uncertain" @click="run('preview')" />
        <AppButton label="Save interface" icon="save" highlighted :disabled="busy || !contextValid || uncertain || !dirty || checked !== xml" @click="run('save')" />
      </footer>
    </template>
    <aside v-if="discard" role="alert" class="notice"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Keep editing" @click="discard = false" /><AppButton label="Discard changes" @click="close" /></aside>
  </dialog>
</template>
