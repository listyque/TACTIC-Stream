<script>
import { objectDeletion, objectStatus, rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'

export default {
  components: { AppButton },
  props: { ticket: String, project: String, searchType: String, view: String },
  emits: ['saved'],
  data() { return { record: null, records: [], operation: '', context: null, groups: [], selected: [], loading: false, saving: false, error: '', uncertain: false, request: 0 } },
  computed: {
    title() { return { retire: 'Retire record', reactivate: 'Reactivate record', delete: 'Delete record' }[this.operation] || 'Object actions' },
  },
  watch: {
    ticket() { this.invalidate() },
    project() { this.invalidate() },
    searchType() { this.invalidate() },
    view() { this.invalidate() },
  },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    t,
    invalidate() {
      this.request++
      this.uncertain = true
      this.error = 'Connection context changed. Close this form and reopen it before saving.'
    },
    beforeUnload(event) { if (this.saving || this.uncertain && this.$refs.dialog.open) { event.preventDefault(); event.returnValue = '' } },
    close(event) {
      if (this.saving) { event?.preventDefault(); return }
      this.request++
      this.$refs.dialog.close()
    },
    async open(record, operation) {
      if (this.$refs.dialog.open) return
      const id = ++this.request
      this.records = Array.isArray(record) ? [...record] : [record]
      if (!this.records.length) return
      this.record = this.records[0]; this.operation = operation
      this.groups = []; this.selected = []; this.error = ''; this.uncertain = false
      this.context = { ticket: this.ticket, project: this.project, searchType: this.searchType, view: this.view }
      this.loading = operation === 'delete'
      this.$refs.dialog.showModal()
      if (!this.loading) return
      try {
        const context = this.context
        const definition = await objectDeletion('read', context.ticket, context.project, context.searchType, context.view, this.records.map(record => record.__search_key__))
        if (id !== this.request) return
        this.groups = definition.groups
        this.selected = definition.groups.filter(group => group.selected).map(group => group.search_type)
      } catch (error) { if (id === this.request) { this.error = error.message; this.uncertain = true } }
      finally { if (id === this.request) this.loading = false }
    },
    async apply() {
      if (this.loading || this.saving || this.uncertain) return
      const id = this.request, context = this.context
      this.saving = true; this.error = ''
      try {
        const keys = this.records.map(record => record.__search_key__)
        if (this.operation === 'delete') await objectDeletion('apply', context.ticket, context.project, context.searchType, context.view, keys, this.selected)
        else if (keys.length > 1) await objectStatus(context.ticket, context.project, context.searchType, context.view, keys, this.operation)
        else await rpc(this.operation === 'retire' ? 'retire_sobject' : 'reactivate_sobject', [{ ticket: context.ticket, project: context.project }, this.record.__search_key__])
        if (id !== this.request) return
        this.$refs.dialog.close()
        this.$emit('saved')
      } catch (error) {
        if (id !== this.request) return
        this.error = error.message
        this.uncertain = !error.status || error.status >= 500
      } finally { this.saving = false }
    },
  },
}
</script>

<template>
  <dialog v-window ref="dialog" class="record-dialog object-action" :aria-label="t(title || 'Object actions')" @cancel="close">
    <header><div><h2>{{ t(title) }}</h2><small>{{ record?.name || record?.title || record?.code || record?.id }}</small></div>
      <AppButton label="Close actions" icon="close" icon-only :disabled="saving" @click="close" /></header>
    <p v-if="records.length > 1">{{ t('{count} selected records', { count: records.length }) }}</p>
    <p v-else class="muted">{{ record?.__search_key__ }}</p>
    <p v-if="loading" role="status">{{ t('Loading dependencies…') }}</p>
    <template v-else-if="operation === 'delete'">
      <p>{{ t('The object will be permanently deleted. Select the related groups to delete with it.') }}</p>
      <label v-for="group in groups" :key="group.search_type" class="configuration-toggle">
        <input v-model="selected" type="checkbox" :value="group.search_type" :disabled="saving || uncertain">
        <span>{{ group.title }} <small class="muted">{{ group.search_type }}</small> · {{ group.count }}</span>
      </label>
      <p class="muted">{{ t('Selected groups include their current related records, including retired records. Selected snapshots also remove their owned files. Object-owned repository directories will also be removed.') }}</p>
    </template>
    <p v-else>{{ t(operation === 'retire' ? 'Retiring keeps the data and hides the object from normal searches.' : 'Reactivating returns the object to normal searches.') }}</p>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <p v-if="uncertain" class="notice">{{ t('This operation cannot be retried here. Close this dialog and refresh the data to check the result.') }}</p>
    <footer class="configuration-actions"><button type="button" :disabled="saving" @click="close">{{ t('Cancel') }}</button>
      <button type="button" :class="operation === 'delete' ? 'danger' : 'primary'" :disabled="loading || saving || uncertain" @click="apply">{{ t(saving ? 'Applying…' : title) }}</button></footer>
  </dialog>
</template>
