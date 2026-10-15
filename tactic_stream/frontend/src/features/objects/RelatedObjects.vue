<script>
import { nextTick } from 'vue'
import { objectRelations, interfaceDefinition, resultItems, rpc } from '../../api.js'
import { t } from '../../i18n.js'
import ConfiguredView from '../interface/ConfiguredView.vue'
import RecordForm from './RecordForm.vue'
import ObjectOperations from './ObjectOperations.vue'
import ObjectAction from './ObjectAction.vue'
import AppButton from '../../controls/AppButton.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppMenu from '../../controls/AppMenu.vue'
import { mobile } from '../../mobile.js'

export default {
  // ConfiguredView → ResultPresentation → RelatedObjects: resolve after the module cycle initializes.
  components: { get ConfiguredView() { return ConfiguredView }, RecordForm, ObjectOperations, ObjectAction, AppButton, AppSelect, AppMenu },
  props: { ticket: String, project: String, searchType: String },
  inject: { openWorkspaceObjectTab: { from: 'openObjectTab', default: null } },
  provide() { return { openObjectTab: async (key, project) => {
    if (this.saving || this.dirty) throw new Error('Save or discard changes before opening a new tab.')
    this.close(); await this.openWorkspaceObjectTab(key, project)
  } } },
  emits: ['saved'],
  data() { return { parent: null, relations: [], selectedType: '', definition: null, detail: null, linking: false,
    linkBranch: null, readBranch: null, selectedKeys: [], originalKeys: [], linkedRecords: [], relationRows: null, saving: false, discard: false,
    busy: false, error: '', request: 0 } },
  computed: { mobile() { return mobile.value }, relation() { return this.relations.find(item => item.search_type === this.selectedType) },
    dirty() { return this.linking && JSON.stringify([...this.selectedKeys].sort()) !== JSON.stringify([...this.originalKeys].sort()) } },
  watch: { ticket() { this.invalidate() }, project() { this.invalidate() }, searchType() { this.invalidate() } },
  beforeUnmount() { this.request++ },
  methods: {
    t,
    async open(record, searchType = '', linkBranch = null, readBranch = null) {
      if (this.$refs.dialog.open) return
      const id = ++this.request
      this.parent = record
      this.linking = !!linkBranch; this.linkBranch = linkBranch; this.readBranch = readBranch; this.discard = false
      this.selectedKeys = []; this.originalKeys = []; this.linkedRecords = []
      this.relationRows = null
      this.relations = []; this.selectedType = ''; this.definition = this.detail = null
      this.busy = true; this.error = ''
      this.$refs.dialog.show()
      try {
        const result = await objectRelations(this.ticket, this.project, this.searchType, record.__search_key__)
        if (id !== this.request) return
        this.parent = { ...record, __search_key__: this.linking ? record.__search_key__ : result.search_key }
        this.relations = readBranch ? [{ ...readBranch, available: false }] : result.relations
        this.selectedType = searchType || result.relations.find(item => item.available)?.search_type || result.relations[0]?.search_type || ''
        if (this.linking) {
          let offset = 0, next = true
          while (next) {
            const page = await resultItems(this.ticket, this.project, this.searchType, [this.parent.__search_key__], {
              branch: { kind: 'relation', search_type: searchType, path: linkBranch.path }, offset, limit: 100 })
            if (id !== this.request) return
            this.linkedRecords.push(...page.items.map(item => item.record)); offset += page.items.length; next = page.has_next
          }
          this.originalKeys = this.linkedRecords.map(item => item.__search_key__)
          this.selectedKeys = [...this.originalKeys]
        }
        await this.load()
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    async load() {
      const id = ++this.request
      this.definition = null; this.error = ''; this.busy = true
      this.relationRows = null
      try {
        if (this.readBranch || this.linking || this.relation?.available || this.relation?.relationship === 'instance') {
          const definition = await interfaceDefinition(this.ticket, this.project, this.selectedType)
          if (id !== this.request) return
          if (this.readBranch) {
            this.relationRows = []
            let next = true
            while (next) {
              const page = await resultItems(this.ticket, this.project, this.searchType, [this.parent.__search_key__], {
                branch: { kind: 'parent', search_type: this.readBranch.search_type, path: this.readBranch.path }, offset: this.relationRows.length, limit: 100 })
              if (id !== this.request) return
              this.relationRows.push(...page.items.map(item => item.record)); next = page.has_next
            }
          } else if (!this.linking && this.relation.relationship === 'instance') {
            const owner = await resultItems(this.ticket, this.project, this.searchType, [this.parent.__search_key__])
            if (id !== this.request) return
            const related = owner.items[0].branches.find(branch => branch.search_type === this.selectedType)
            if (!related) throw new Error('Relationship is not in the project schema')
            this.relationRows = []
            let next = true
            while (next) {
              const page = await resultItems(this.ticket, this.project, this.searchType, [this.parent.__search_key__], {
                branch: { kind: 'relation', search_type: this.selectedType, path: related.path }, offset: this.relationRows.length, limit: 100 })
              if (id !== this.request) return
              this.relationRows.push(...page.items.map(item => item.record)); next = page.has_next
            }
          }
          this.definition = definition
        }
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    close(force = false) { if (this.saving) return; if (this.dirty && !force) { this.discard = true; return }; this.request++; this.$refs.operations?.close(); this.$refs.dialog?.close() },
    invalidate() { this.saving = false; this.close(true) },
    select(records, selected) {
      const keys = records.map(item => item.__search_key__).filter(key => key !== this.parent.__search_key__)
      this.selectedKeys = selected ? [...new Set([...this.selectedKeys, ...keys])] : this.selectedKeys.filter(key => !keys.includes(key))
    },
    async saveLinks() {
      if (this.saving || !this.dirty) return
      this.saving = true; this.error = ''
      const id = ++this.request
      try {
        await rpc('execute_cmd', [{ ticket: this.ticket, project: this.project }, 'tactic.command.sobject_link_cmd.SObjectLinkCmd', {
          parent_key: this.parent.__search_key__, search_type: this.selectedType, path: this.linkBranch.path,
          insert_search_keys: this.selectedKeys.filter(key => !this.originalKeys.includes(key)),
          exclude_search_keys: this.originalKeys.filter(key => !this.selectedKeys.includes(key)),
        }])
        if (id !== this.request) return
        this.originalKeys = [...this.selectedKeys]; this.saving = false; this.close(); this.$emit('saved')
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.saving = false }
    },
    create(source = null) {
      this.$refs.form.open(null, source?.__search_key__ || null, { parent_key: this.parent.__search_key__ })
    },
    refresh() { if (this.relationRows) this.load(); else this.$refs.table?.load() },
    async inspect(record) {
      this.detail = record
      await nextTick()
      this.$refs.details.show()
    },
    edit(record) { this.$refs.details?.close(); this.$refs.form.open(record.__search_key__) },
    display(value) { return value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value) },
  },
}
</script>

<template>
  <dialog v-window="{ type:'window' }" ref="dialog" class="record-dialog related-objects" :aria-label="t(linking ? 'Link existing objects' : 'Related objects')" @cancel.prevent="close()">
    <header><div><h2>{{ t(linking ? 'Link existing objects' : 'Related objects') }}</h2><small>{{ parent?.name || parent?.title || parent?.code || parent?.id }}</small></div>
      <AppButton label="Close related objects" icon="close" icon-only :disabled="saving" @click="close()" /></header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <div v-if="!linking" class="toolbar">
      <label><span v-if="!mobile">{{ t('Related type') }}</span><AppSelect v-model="selectedType" label="Related type" :translate-labels="false" :options="relations.map(item => ({ value:item.search_type,label:mobile ? item.title : item.title + ' · ' + item.search_type }))" :disabled="busy || !relations.length || !!readBranch" @update:model-value="load" /></label>
      <AppButton v-if="relation?.can_create && definition?.operations?.create" label="Create related object" icon="add" highlighted :icon-only="mobile" @click="create()" />
    </div>
    <template v-else><p class="muted">{{ t('Select objects to link. Clear a selection to unlink an existing object.') }}</p>
      <component :is="mobile ? 'AppMenu' : 'div'" class="toolbar related-linked" label="Linked objects" icon="link" :overlay="mobile" :close-on-select="false"><AppButton v-for="record in linkedRecords" :key="record.__search_key__" :highlighted="selectedKeys.includes(record.__search_key__)" :aria-pressed="selectedKeys.includes(record.__search_key__)" :icon="selectedKeys.includes(record.__search_key__) ? 'link' : 'close'" :disabled="saving" @click="select([record], !selectedKeys.includes(record.__search_key__))">{{ record.name || record.title || record.code }}</AppButton></component>
    </template>
    <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
    <p v-else-if="!linking && relation && !relation.available && !definition" class="notice">{{ t('This relationship is not available in this browser yet.') }}</p>
    <div v-if="definition" class="table-container">
      <ConfiguredView ref="table" :definition="definition" :ticket="ticket" :project="project" :rows="relationRows" :parent-key="linking || relationRows ? undefined : parent.__search_key__"
        :configured="false" :read-only="false" :selection-enabled="linking && !saving" :selected-keys="selectedKeys" @select="select" @inspect="inspect"
        @operate="(record, event, node) => $refs.operations.open(record, event, node)" />
    </div>
    <footer v-if="linking"><AppButton label="Cancel" :disabled="saving" @click="close()" /><AppButton label="Save links" icon="save" highlighted :disabled="busy || saving || !dirty" @click="saveLinks" /></footer>
    <div v-if="discard" class="notice" role="alert"><p>{{ t('Discard unsaved changes?') }}</p><AppButton label="Continue editing" @click="discard = false" /><AppButton label="Discard" destructive @click="close(true)" /></div>
  </dialog>
  <ObjectOperations ref="operations" :ticket="ticket" :project="project" :search-type="selectedType" :show-related="false"
    :operations="{ ...definition?.operations, create: !!relation?.can_create && !!definition?.operations?.create }"
    @inspect="inspect" @edit="edit" @create="create()" @duplicate="create" @duplicated="refresh"
    @retire="record => $refs.action.open(record, 'retire')" @reactivate="record => $refs.action.open(record, 'reactivate')"
    @delete="record => $refs.action.open(record, 'delete')" />
  <RecordForm ref="form" :ticket="ticket" :project="project" :search-type="selectedType" @saved="refresh" />
  <ObjectAction ref="action" :ticket="ticket" :project="project" :search-type="selectedType" view="table" @saved="refresh" />
  <dialog v-window="{ type:'window' }" ref="details" class="record-dialog object-details" :aria-label="t('Object details')">
    <template v-if="detail">
      <header><div><h2>{{ detail.name || detail.title || detail.code || detail.id }}</h2><small>{{ detail.__search_key__ }}</small></div>
        <div class="configuration-actions"><AppButton v-if="definition?.operations?.edit" label="Edit record" icon="edit" :icon-only="mobile" @click="edit(detail)" />
          <AppButton label="Close details" icon="close" :icon-only="mobile" @click="$refs.details.close()" /></div></header>
      <dl><template v-for="(value, key) in detail" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></template></dl>
    </template>
  </dialog>
</template>
<style>
@media(max-width:700px) {
  .related-objects[open] { display:flex; flex-direction:column; overflow:hidden; gap:6px; }
  .related-objects > header { margin:0; flex-wrap:nowrap; gap:8px; flex-shrink:0; }
  .related-objects > header h2 { font-size:var(--text-body-large); margin:0; }
  .related-objects > .toolbar { flex-shrink:0; margin:0; flex-wrap:nowrap; }
  .related-objects > p { margin:4px 0; flex-shrink:0; }
  .related-objects > .table-container { flex:1; min-height:0; max-height:none; border:0; border-radius:0; background:var(--surface); }
  .related-objects > footer { display:flex; flex-shrink:0; justify-content:flex-end; gap:6px; padding-bottom:env(safe-area-inset-bottom); }
}
</style>
