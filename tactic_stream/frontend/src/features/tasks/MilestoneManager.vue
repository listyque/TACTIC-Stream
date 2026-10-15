<script>
// Handler MilestoneController, thlib/ui/milestones.py (EPL-1.0).
// One owner of milestone requests, originals and per-row drafts.
import { nextTick } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import MilestonePanel from './MilestonePanel.vue'

function today() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` }

export default {
  components: { MilestonePanel },
  props: { ticket: String, project: String },
  emits: ['markers', 'saved'],
  data() { return { context: null, result: null, drafts: {}, query: '', busy: false, saving: '', uncertain: '', error: '',
    request: 0, alive: true, confirmation: '', deleting: '', focused: '' } },
  computed: {
    validContext() { return this.alive && this.context?.ticket === this.ticket && this.context?.project === this.project },
    dirty() { return Object.keys(this.drafts).length > 0 },
    rows() {
      const rows = [...(this.result?.records || [])]
      for (const [code, draft] of Object.entries(this.drafts)) if (!rows.some(row => row.code === code)) rows.unshift({ code, ...draft.original })
      return rows.map(row => ({ ...row, ...this.drafts[row.code]?.data, dirty: !!this.drafts[row.code], isNew: !!this.drafts[row.code]?.isNew,
        saving: this.saving === row.code, error: this.drafts[row.code]?.error || '', uncertain: this.uncertain === row.code }))
    },
    visibleRows() { const query = this.query.toLocaleLowerCase(); return this.rows.filter(row => `${row.description} ${row.dueDate}`.toLocaleLowerCase().includes(query)) },
    markers() { return this.rows.filter(row => !row.isNew && row.dueDate).map(row => ({ value: row.code, label: row.description || row.code,
      dueDate: row.dueDate, completion: row.completion, taskCount: row.taskCount })) },
  },
  watch: {
    ticket() { this.reset() }, project() { this.reset() },
    markers: { deep: true, handler(value) { this.$emit('markers', value) } },
  },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.alive = false; this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    beforeUnload(event) { if (this.dirty || this.busy || this.uncertain) { event.preventDefault(); event.returnValue = '' } },
    reset() { this.request++; this.$refs.panel?.close(); this.context = null; this.result = null; this.drafts = {}; this.busy = false; this.uncertain = ''; this.confirmation = ''; this.$emit('markers', []) },
    canLeave() {
      if (this.busy || (this.dirty || this.uncertain) && !window.confirm(t('Discard unsaved milestone changes?'))) return false
      if (this.dirty || this.uncertain) this.reset()
      return true
    },
    close(force = false) {
      if (this.busy) return
      if (!force && (this.dirty || this.uncertain)) { this.confirmation = 'close'; return }
      if (force) { this.drafts = {}; this.uncertain = '' }
      this.confirmation = ''; this.$refs.panel.close()
    },
    async ensureLoaded() {
      if (!this.validContext) { this.reset(); this.context = { ticket: this.ticket, project: this.project } }
      if (!this.busy && !this.dirty && !this.uncertain) await this.command()
    },
    async open(code = '') {
      if (!this.validContext) { this.reset(); this.context = { ticket: this.ticket, project: this.project } }
      this.query = ''; this.focused = code; this.$refs.panel.open()
      if (!this.dirty && !this.uncertain) await this.command()
      await nextTick(); this.$refs.panel.focusRow(code)
    },
    async create() {
      if (this.busy || this.uncertain || !this.result?.canCreate) return
      const code = 'new:' + Array.from(crypto.getRandomValues(new Uint32Array(4)), value => value.toString(16)).join('-')
      const original = { description: '', dueDate: today(), completion: 0, taskCount: 0, completedCount: 0, overdueCount: 0, planStartDate: '', processSummary: '', plannedHours: 0 }
      this.drafts[code] = { isNew: true, original, data: { description: '', dueDate: original.dueDate }, revision: this.result.revision, error: '' }
      this.query = ''; await nextTick(); this.$refs.panel.focusRow(code, true)
    },
    stage(code, name, value) {
      if (this.busy || this.uncertain || !['description', 'dueDate'].includes(name)) return
      const row = this.result.records.find(row => row.code === code)
      let draft = this.drafts[code]
      if (!draft) draft = this.drafts[code] = { original: { ...row }, revision: row.revision, data: { description: row.description, dueDate: row.dueDate }, error: '' }
      draft.data[name] = value; draft.error = ''
      if (!draft.isNew && draft.data.description === draft.original.description && draft.data.dueDate === draft.original.dueDate) delete this.drafts[code]
    },
    discard(code) {
      if (this.busy) return
      if (this.uncertain === code && !window.confirm(t('Inspect the current server data before discarding this uncertain change. Discard the draft?'))) return
      delete this.drafts[code]; if (this.uncertain === code) this.uncertain = ''
    },
    refresh() { if (this.busy) return; if (this.dirty || this.uncertain) this.confirmation = 'refresh'; else this.command() },
    confirm() {
      const action = this.confirmation; this.confirmation = ''; this.drafts = {}; this.uncertain = ''
      if (action === 'close') this.close(true); else this.command()
    },
    remove(code) { if (this.busy || this.uncertain || !this.result?.canDelete) return; if (this.drafts[code]?.isNew) this.discard(code); else this.deleting = code },
    async review(code) {
      if (this.busy || this.uncertain) return
      if (!await this.command()) return
      const draft = this.drafts[code]
      if (!draft || !this.validContext) return
      const current = this.result.records.find(row => row.code === code)
      if (!draft.isNew && !current) { draft.error = 'Milestone no longer exists. Discard this draft.'; return }
      const comparison = draft.isNew ? t('The project milestone list changed.') : `${t('Original')}: ${draft.original.description} · ${draft.original.dueDate}\n${t('Current server data')}: ${current.description} · ${current.dueDate}`
      if (!window.confirm(comparison + '\n' + t('Keep your edits on this revision?'))) return
      draft.revision = current?.revision || ''; draft.error = ''; if (current) draft.original = { ...current }
    },
    async save(code) {
      const draft = this.drafts[code]
      if (!draft || this.busy || this.uncertain) return
      if (!draft.data.description.trim()) { draft.error = 'A milestone name is required'; return }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.data.dueDate)) { draft.error = 'Choose a valid milestone due date'; return }
      await this.command(draft.isNew ? 'create' : 'update', code)
    },
    async command(action = 'read', code = '') {
      if (!this.validContext || this.busy || this.uncertain && action !== 'read') return false
      const context = this.context, id = ++this.request, draft = this.drafts[code]
      this.busy = true; this.saving = action === 'read' ? '' : code; this.error = ''
      try {
        const response = await rpc('execute_cmd', [context, 'tactic.ui.table.milestones.MilestoneCmd', {
          action, code: draft?.isNew ? '' : code, expected_revision: draft?.revision || this.result?.records.find(row => row.code === code)?.revision,
          ...(draft ? { data: { description: draft.data.description, due_date: draft.data.dueDate } } : {}),
        }])
        if (id !== this.request || !this.validContext || context !== this.context) return false
        const result = response.info
        if (action !== 'read') {
          delete this.drafts[code]
          this.deleting = ''; this.focused = result.selected; this.$emit('saved')
        }
        this.result = result
        return true
      } catch (error) {
        if (id === this.request && this.validContext) {
          if (draft) draft.error = error.message; else this.error = error.message
          if (action !== 'read' && (!error.status || error.status >= 500)) this.uncertain = code
        }
        return false
      } finally {
        if (id === this.request) {
          this.busy = false; this.saving = ''
          // Native change timestamps are finalized by the outer Command commit.
          // Refresh after proven success; pending rows retain their own revisions.
          if (action !== 'read' && !this.uncertain && !this.drafts[code] && !this.error) await this.command()
        }
      }
    },
  },
}
</script>

<template>
  <MilestonePanel ref="panel" :project="project" :result="result" :rows="visibleRows" :query="query" :busy="busy" :error="error"
    :uncertain="uncertain" :confirmation="confirmation" :deleting="deleting" :focused="focused"
    @query="query = $event" @create="create" @change="stage" @save="save" @discard="discard" @delete="remove" @review="review"
    @refresh="refresh" @inspect-server="command()" @close="close()" @keep-editing="confirmation = ''" @confirm="confirm"
    @cancel-delete="deleting = ''" @confirm-delete="command('delete', deleting)" />
</template>
