<script>
import { rpc } from '../../api.js'
import TimeEntryPanel from './TimeEntryPanel.vue'

function today() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` }

export default {
  components: { TimeEntryPanel },
  props: { ticket: String, project: String, currentUser: String, dockTarget:String, dockMode:String, dockReport:String },
  inject: { openWorkHours:{default:null} },
  emits: ['saved','opened','closed','open-dock'],
  data() { return { context: null, task: null, mode: this.dockMode || 'task', week: today(), login: '', report: this.dockReport || 'my_hours',
    result: null, users: [], draft: null, revision: '', selected: [], deleting: '', confirmation: false, busy: false,
    uncertain: false, error: '', request: 0, alive: true } },
  computed: { validContext() { return this.alive && this.context?.ticket === this.ticket && this.context?.project === this.project } },
  watch: { ticket() { this.close(true) }, project() { this.close(true) } },
  mounted() { window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.alive = false; this.request++; window.removeEventListener('beforeunload', this.beforeUnload) },
  methods: {
    beforeUnload(event) { if (this.draft || this.busy || this.uncertain) { event.preventDefault(); event.returnValue = '' } },
    async open(task = null, log = false, weekly = false, day = '') {
      if (this.busy || this.draft || this.uncertain) {
        this.error = 'Save or discard time-entry changes before switching tasks.'
        return
      }
      if (this.$refs.panel.isOpen() && this.task?.scope.task_key === task?.scope.task_key && (!day || day === this.week)) return
      this.context = { ticket: this.ticket, project: this.project }; this.task = task
      if (day) this.week = String(day).slice(0,10)
      this.users = task?.users || []
      this.mode = this.dockMode || (weekly ? 'week' : 'task'); this.login = this.currentUser || ''; this.result = null
      this.draft = null; this.confirmation = false; this.selected = []; this.deleting = ''; this.uncertain = false
      this.$refs.panel.open(); this.$emit('opened'); await this.command()
      if (log && this.result && this.validContext) this.edit()
    },
    openWeekly() { return this.open(null, false, true) },
    edit(entry = null) {
      if (this.busy || this.uncertain || !this.result) return
      this.draft = entry ? { ...entry } : { day: today(), hours: 1, category: 'regular', login: this.login || this.currentUser, description: '' }
      this.revision = this.result.revision; this.deleting = ''; this.error = ''
    },
    close(force = false) {
      if (force !== true && (this.busy || this.draft || this.uncertain)) { if (!this.busy) this.confirmation = true; return }
      this.request++; this.$refs.panel?.close(); this.draft = null; this.confirmation = false
      this.$emit('closed')
      if (force === true) this.busy = false
    },
    scope(name, value) {
      if (this.busy || this.draft || this.uncertain) return
      if (name === 'report' && value === 'labor_cost' && this.dockReport !== 'labor_cost') {
        if (this.dockTarget) { this.$emit('open-dock','cost'); return }
        if (this.openWorkHours) { this.openWorkHours('cost',this.task,this.project); return }
      }
      if (name === 'mode' && ['week','report'].includes(value) && value !== this.dockMode) {
        if (this.dockTarget) { this.$emit('open-dock', value); return }
        if (this.openWorkHours) { this.openWorkHours(value,this.task,this.project); return }
      }
      this[name] = value; this.selected = []; this.deleting = ''; this.result = null; this.command()
    },
    moveWeek(offset) {
      const date = new Date(this.week+'T12:00:00Z'); date.setUTCDate(date.getUTCDate()+offset*7)
      this.scope('week', date.toISOString().slice(0, 10))
    },
    toggle(key, value) { this.selected = value ? [...new Set([...this.selected, key])] : this.selected.filter(item => item !== key) },
    async command(action = 'read', entry = null, approve = false, keys = null) {
      if (!this.validContext || this.busy || this.uncertain && action !== 'read') return
      const context = this.context, id = ++this.request
      this.busy = true; this.error = ''
      try {
        const data = this.draft ? Object.fromEntries(['day', 'hours', 'category', 'login', 'description'].map(name => [name, name === 'hours' ? String(this.draft[name]).replace(',', '.') : this.draft[name]])) : null
        const response = await rpc('execute_cmd', [context, 'tactic.ui.table.work_hours.WorkHoursCmd',
          { ...this.task?.scope, mode: this.mode, week: this.week, login: this.login, report: this.report,
            action, entry_key: entry?.search_key || '', ...(keys ? { entry_keys: keys } : {}),
            expected_revision: ['create', 'update'].includes(action) ? this.revision : this.result?.revision,
            ...(data ? { data: { ...data, approve } } : {}) }])
        if (id !== this.request || !this.validContext || this.context !== context) return
        this.result = response.info; this.uncertain = false; this.deleting = ''
        if (this.result.users) this.users = this.result.users
        if (this.mode !== 'task') this.week = this.result.week_start || this.week
        this.selected = []  // Handler replaces entry records on reload.
        if (action !== 'read') { this.draft = null; this.$emit('saved') }
      } catch (error) {
        if (id === this.request && this.validContext) { this.error = error.message; this.uncertain = action !== 'read' && (!error.status || error.status >= 500) }
      } finally { if (id === this.request) this.busy = false }
    },
  },
}
</script>

<template>
  <TimeEntryPanel ref="panel" :dock-target="dockTarget" :dock-report="dockReport" :data="result" :draft="draft" :editing="!!draft" :busy="busy" :error="error" :uncertain="uncertain" :deleting="deleting"
    :users="users" :mode="mode" :week="week" :login="login" :selected="selected" :report="report" :can-create="!!task?.scope.task_key" :confirmation="confirmation"
    @create="edit()" @edit="edit" @change="(name, value) => draft[name] = value" @cancel-edit="draft = null" @delete="deleting = $event" @close="close()"
    @refresh="command()" @save="approve => command(draft.search_key ? 'update' : 'create', draft, approve)" @action="(entry, action) => command(action, entry)"
    @scope="scope" @move-week="moveWeek" @select="toggle" @clear-selection="selected = []" @bulk="action => command(action, null, false, selected)"
    @keep-editing="confirmation = false" @discard-close="close(true)" />
</template>
