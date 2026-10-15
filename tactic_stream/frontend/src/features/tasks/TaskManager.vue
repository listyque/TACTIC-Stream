<script>
// Handler TasksWorkspaceView/TasksController: the screen owns requests and drafts.
// Sources: thlib/ui/qml/TasksWorkspaceView.qml and thlib/ui/tasks.py, EPL-1.0.
import { nextTick } from 'vue'
import { asyncComponent } from '../../controls/asyncComponent.js'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
import AppButton from '../../controls/AppButton.vue'
import AppDateField from '../../controls/AppDateField.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import NotesPanel from '../objects/NotesPanel.vue'
import Timesheet from '../objects/Timesheet.vue'
import TaskWorkspaceTable from './TaskWorkspaceTable.vue'
import MobileTasks from './MobileTasks.vue'
import TaskWorkspaceEditor from './TaskWorkspaceEditor.vue'
import TaskWorkspaceFilters from './TaskWorkspaceFilters.vue'
import TaskWorkspaceScope from './TaskWorkspaceScope.vue'
import MilestoneManager from './MilestoneManager.vue'
import TaskWorkspaceSurfaceSwitcher from './TaskWorkspaceSurfaceSwitcher.vue'
import BusyIndicator from '../../controls/BusyIndicator.vue'
import { preferences as configurationPreferences } from '../configuration/preferences.js'
import { taskColumns as columns, normalizeColumns } from './taskColumns.js'
const TaskGanttView = asyncComponent(() => import('./TaskGanttView.vue'))
const TaskCalendarView = asyncComponent(() => import('./TaskCalendarView.vue'))
const TaskProcessPanel = asyncComponent(() => import('./TaskProcessPanel.vue'))

const readCommand = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd'
const editCommand = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
const scheduleCommand = 'tactic.ui.table.task_schedule.TaskScheduleCmd'
const scheduleFields = ['bid_start_date', 'bid_end_date', 'progress', 'completion']
const presets = { mine: 'My tasks', unassigned: 'Unassigned', overdue: 'Overdue', today: 'Today', recent: 'Recently created', review: 'Review' }
const sorts = ['due', 'recent', 'user', 'process', 'status', 'object', 'search_type', 'project', 'priority', 'milestone', 'supervisor']
const sortLabels = ['Deadline', 'Recently created', 'Assigned to', 'Process', 'Status', 'Object', 'Search Type', 'Project', 'Priority', 'Milestone', 'Supervisor']
const sortIcons = ['schedule', 'history', 'person', 'process', 'status', 'sobject', 'schema', 'workspaces', 'priority-high', 'milestone', 'admin-panel-settings']

export default {
  components: { AppDateField, AppButton, AppSelect, AppCheckbox, AppIcon, AppMenu, AppSearchField, AppSegmentedButton, NotesPanel, Timesheet, TaskWorkspaceTable, MobileTasks, TaskWorkspaceEditor, TaskWorkspaceFilters, TaskWorkspaceScope, TaskGanttView, TaskCalendarView, MilestoneManager, TaskWorkspaceSurfaceSwitcher, TaskProcessPanel, BusyIndicator },
  props: { ticket: String, project: String, currentUser: String, searchType: String, parents: Array, docked: Boolean, calendarTarget: String, calendarActive: Boolean },
  emits: ['calendar', 'saved', 'object', 'opened', 'closed', 'snapshot-context', 'task-context'],
  data() { return { opened: false, context: null, alive: true, busy: false, loading: false, backgroundRequest:null, mobileSearchOpen:false, pendingSource: false, savedPreferenceKey: '', toolbarWidth: 0, error: '', uncertain: false, request: 0, liveVersion: 0, loadedLiveVersion: 0,
    scope: 'user', identity: '', seed: [], objectParents:null, catalog: null, result: null, parentRecords: {},
    surface: 'workspace', processResult: null, preferredTasks: {},
    filters: {}, quick: {}, sort: 'due', descending: false, group: 'none', collapsed: [],
    limit: 50, selected: [], drafts: {}, editor: null, deletion: null, rowMenu: null, rebaseReview: null,
    confirmation: false, columns: normalizeColumns(), presets, active: '', anchor: '', expanded: [], rowPlans: {}, inline: null, columnMenu: null,
    mobileTaskKey: '', mobileDirection: 'forward', mobileScroll: {},
    view: 'table', projection: null, projectionRequest: 0, projecting: false, projectionError: '',
    year: new Date().getFullYear(), month: new Date().getMonth() + 1,
    workingDays: false, resourcePrevious: null, scheduleEditor: null, undo: [], redo: [], milestoneRecords: [],
    sortOptions: sorts.map((value, index) => ({ value, label: sortLabels[index], icon: sortIcons[index] })),
    groupOptions: ['none', 'user', 'process', 'status', 'object'].map((value, index) => ({ value, label: ['No grouping', 'Assigned to', 'Process', 'Status', 'Object'][index], icon: ['ungroup-items', 'person', 'process', 'status', 'sobject'][index] })) } },
  computed: {
    mobile() { return mobile.value },
    refreshing() { return this.backgroundRequest !== null && this.backgroundRequest === this.request },
    mobileTask() { return this.tasks.find(task => task.key === this.mobileTaskKey) || null },
    mobileHistoryKey() { return JSON.stringify([this.currentUser, this.project]) },
    displayedView() { return mobile.value ? 'table' : this.view },
    processRecords() {
      return (this.processResult?.processes || []).map(process => {
        const additional = Object.entries(this.drafts).filter(([key, plan]) => plan.operation === 'create' && plan.search_key === this.processResult.parent.__search_key__ && plan.process === process.value && !process.branches.some(branch => (branch.plan.task_key || branch.plan.draft_id) === key))
          .map(([, plan]) => ({ plan, statuses: process.branches[0].statuses, users: process.branches[0].users, notes: 0 }))
        const branches = [...process.branches.filter(branch => branch.plan.task_key || !additional.length), ...additional].map(branch => {
          const key = branch.plan.task_key || branch.plan.draft_id
          const plan = { ...branch.plan, ...this.drafts[key] }
          return { ...branch, key, plan, values: { ...plan.task, ...plan.data } }
        })
        const branch = branches.find(branch => branch.key === this.preferredTasks[process.value]) || branches.find(branch => branch.key === process.selected) || branches[0]
        return { ...process, ...branch, dirty: !!this.drafts[branch.key], deleting: branch.plan.operation === 'delete',
          choices: branches.map(branch => ({ key: branch.key, label: (branch.values.context || t('No context')) + ' / ' + (this.userLabel(branch.values.assigned) === '—' ? t('Not assigned') : this.userLabel(branch.values.assigned)) })) }
      })
    },
    liveChanged() { return this.liveVersion > this.loadedLiveVersion },
    validContext() { return this.alive && this.context?.ticket === this.ticket && this.context?.project === this.project },
    dirty() { return !!Object.keys(this.drafts).length },
    blocked() { return this.busy || this.uncertain },
    visibleTasks() { return this.groups.flatMap(group => this.collapsed.includes(group.key) ? [] : group.tasks) },
    rowEditors() {
      return Object.fromEntries(this.tasks.filter(task => !task.deleting && (this.rowPlans[task.key] || this.drafts[task.key])).map(task => {
        const plan = this.drafts[task.key] || this.rowPlans[task.key]
        return [task.key, { plans: [plan], fields: plan.fields || [], values: { ...plan.task, ...plan.data }, enabled: [],
          statuses: plan.statuses || [], statusChoices: plan.statusChoices || [], users: (plan.users || []).map(user => ({ ...this.catalog?.users.find(item => item.value === user.value), ...user })), catalog: this.catalog ? { ...plan.catalog, milestoneChoices: this.catalog.milestoneChoices } : plan.catalog }]
      }))
    },
    inlineEditor() { const editor = this.rowEditors[this.inline?.key]; return editor ? { ...editor, fields: editor.fields.filter(field => this.inline.fields.includes(field.name)) } : null },
    scopeOptions() { return [{ value: 'user', label: 'User tasks', icon:'person' }, { value: 'team', label: 'Team tasks', icon:'groups' },
      { value: 'project', label: 'Project tasks', icon:'workspaces' }, { value: 'selected', label: 'Selected objects', icon:this.seed.length > 1 ? 'select-all' : 'inventory-2' }, { value: 'search_type', label: 'Search Type tasks', icon:'MDI_TABLE' }] },
    scopeTitle() {
      if (this.scope === 'user') return this.identity === this.currentUser ? 'My tasks' : 'User'
      return { selected:'Selected', team:'Team', project:'Project' }[this.scope] || this.scopeOptions.find(option => option.value === this.scope)?.label
    },
    tasks() {
      const raw = [...(this.result?.tasks || [])]
      for (const [key, plan] of Object.entries(this.drafts)) if (plan.operation === 'create') raw.unshift({ ...plan.task, __draft__: key })
      return raw.map(row => {
        const key = row.__draft__ || row.__search_key__, plan = this.drafts[key]
        const task = { ...row, ...plan?.task, ...plan?.data }, parent = this.parentFor(plan || row)
        return { ...task, key, pending: !!plan, deleting: plan?.operation === 'delete', parent,
          __status__: (this.rowPlans[key]?.statusChoices || plan?.statusChoices || []).find(choice => choice.value === task.status) || task.__status__,
          title: parent?.name || parent?.title || parent?.code || row.search_code || '—',
          assignedLogin: task.assigned || '',
          supervisorLogin: task.supervisor || '',
          assignedUser: this.catalog?.users.find(user => user.value === task.assigned), supervisorUser: this.catalog?.users.find(user => user.value === task.supervisor),
          assigned: this.userLabel(task.assigned), supervisor: this.userLabel(task.supervisor),
          notes: row.__notes_count__ || 0,
          milestone_code: this.catalog?.milestoneChoices.find(item => item.value === task.milestone_code)?.label || task.milestone_code || '—' }
      })
    },
    groups() {
      const groups = new Map(), fields = { user: 'assignedLogin', process: 'process', status: 'status', object: 'title' }
      for (const task of this.tasks) {
        const key = this.group === 'none' ? '' : String(task[fields[this.group]] || t('Not set'))
        if (!groups.has(key)) groups.set(key, { key, label: this.group === 'user' ? this.userLabel(task.assignedLogin) : this.group === 'process' ? this.catalog?.processes.find(item => item.value === task.process)?.label || key : key, tasks: [] })
        groups.get(key).tasks.push(task)
      }
      return [...groups.values()]
    },
    allSelected() { return !!this.visibleTasks.length && this.visibleTasks.every(task => this.selected.includes(task.key)) },
    creationParent() { return this.surface !== 'workspace' ? this.processResult?.parent : this.tasks.find(task => task.key === this.active)?.parent || this.tasks.find(task => this.selected.includes(task.key))?.parent || this.seed[0] },
    preferenceKey() { return 'tactic-stream:task-table:' + JSON.stringify([this.currentUser, this.project]) },
    parentKeys() { return JSON.stringify((this.parents || []).map(parent => parent.__search_key__)) },
    filtersActive() { return Object.values(this.filters).some(Boolean) || Object.values(this.quick).some(values => values.length) },
    sessionState() { return JSON.stringify({ columns: this.columns, scope: this.scope, identity: this.identity, filters: this.filters, quick: this.quick,
      sort: this.sort, group: this.group, descending: this.descending, collapsed: this.collapsed, view: this.view,
      limit: this.limit, year: this.year, month: this.month, workingDays: this.workingDays, surface: this.surface }) },
    scheduleRecords() {
      return this.groups.flatMap(group => group.tasks.filter(task => !task.deleting).map(task => {
        const original = this.drafts[task.key]?.task || task
        const section = this.projection?.gantt.records.find(record => record.taskCode === task.key)?.ganttSection
        const scheduled = section ? section === 'scheduled' : !!(original.bid_start_date && original.bid_end_date &&
          Date.parse(original.bid_start_date.replace(' ', 'T')) <= Date.parse(original.bid_end_date.replace(' ', 'T')))
        return {
          taskCode: task.key, parentKey: task.parent?.__search_key__ || '', parentTitle: task.title,
          process: task.process || '', processLabel: this.catalog?.processes.find(item => item.value === task.process)?.label || task.process || '', status: task.status || '',
          assigned: task.assignedLogin, assignedLabel: task.assigned, start: task.bid_start_date || '', end: task.bid_end_date || '',
          ...(task.pending ? { _ganttSectionScheduled: scheduled } : {}),
          progress: Math.max(0, Math.min(100, Number(task.progress ?? task.completion) || 0)), groupKey: group.key, group: group.label,
        }
      }))
    },
    projectionInput() { return JSON.stringify({ records: this.scheduleRecords, year: this.year, month: this.month,
      milestones: this.milestoneRecords }) },
  },
  watch: { ticket() { this.resetContext() }, project() { this.resetContext() },
    parentKeys() { if (!this.objectParents) this.syncSource(this.surface !== 'workspace' || this.scope === 'selected') },
    searchType() { this.syncSource(this.scope === 'search_type') },
    busy(value) { if (!value) this.flushSource() },
    active(key) { const task = this.tasks.find(task => task.key === key); if (task && !task.pending) this.$emit('task-context', task) },
    editor(value) { if (!value) this.flushSource() },
    scheduleEditor(value) { if (!value) this.flushSource() },
    sessionState() { this.storeColumns() },
    projectionInput: { flush: 'post', handler() { this.projectSchedule() } },
    view() { this.projectSchedule() },
    calendarActive() { this.projectSchedule() },
    mobile() { this.projectSchedule(); this.mobileHistory(true) },
  },
  async mounted() {
    window.addEventListener('beforeunload', this.beforeUnload); window.addEventListener('resize', this.closeInline)
    window.addEventListener('popstate', this.mobilePopstate, true)
    this.toolbarObserver = new ResizeObserver(entries => {
      this.toolbarWidth = entries[0].contentRect.width
      if (!this.toolbarWidth) {
        this.$refs.viewOptions?.close(); this.$refs.filtersMenu?.close(); this.$refs.scopeMenu?.close()
        this.closeInline(); this.$refs.menu?.hidePopover(); this.$refs.columnMenu?.hidePopover()
      }
    })
    await nextTick()
    if (this.alive) this.toolbarObserver.observe(this.$refs.dialog)
  },
  beforeUnmount() { this.storeColumns(); clearTimeout(this.searchTimer); this.toolbarObserver.disconnect(); this.alive = false; this.request++; window.removeEventListener('beforeunload', this.beforeUnload); window.removeEventListener('resize', this.closeInline); window.removeEventListener('popstate', this.mobilePopstate, true) },
  methods: {
    t,
    mobileHistory(replace = false) {
      if (!this.mobile || !this.opened || !this.$refs.dialog?.getClientRects().length) return
      const previous = window.history.state?.mobileTask
      window.history[replace ? 'replaceState' : 'pushState']({ ...window.history.state,
        mobileTask: { key: this.mobileHistoryKey, task: this.mobileTaskKey,
          depth: replace ? previous?.key === this.mobileHistoryKey ? previous.depth || 0 : 0 : 1 } }, '')
    },
    async mobileEnter(task) {
      if (this.blocked || task.deleting || !task.parent) return
      this.closeInline(); this.mobileHistory(true)
      this.mobileDirection = 'forward'; this.mobileTaskKey = task.key; this.active = task.key
      this.mobileHistory(); await this.prepareRow(task)
    },
    mobileBack() {
      if (!this.mobileTaskKey) return
      const entry = window.history.state?.mobileTask
      if (entry?.key === this.mobileHistoryKey && entry.task === this.mobileTaskKey && entry.depth > 0) window.history.back()
      else { this.mobileDirection = 'back'; this.mobileTaskKey = ''; this.mobileHistory(true) }
    },
    async mobilePopstate(event) {
      const entry = event.state?.mobileTask
      if (!this.mobile || !this.opened || !this.$refs.dialog?.getClientRects().length || entry?.key !== this.mobileHistoryKey || entry.task === this.mobileTaskKey) return
      event.preventDefault(); event.stopImmediatePropagation()
      const task = this.tasks.find(task => task.key === entry.task)
      this.mobileDirection = task ? 'forward' : 'back'; this.mobileTaskKey = task?.key || ''
      this.closeInline()
      if (task && !this.blocked) await this.prepareRow(task)
    },
    resetContext() { this.close(true); if (this.calendarActive && this.ticket && this.project) this.open(false, '', {}, true) },
    async changeSurface(surface) {
      if (this.busy && !this.loading || this.editor || this.scheduleEditor) return
      clearTimeout(this.searchTimer)
      if (this.loading) { this.request++; this.loading = this.busy = false }
      this.closeInline(); this.$refs.viewOptions?.close(); this.$refs.filtersMenu?.close(); this.$refs.scopeMenu?.close()
      this.surface = surface; await this.load()
    },
    stageProcess(record, name, value) {
      if (this.blocked) return
      if (String(value ?? '') === String(record.values[name] ?? '')) return
      this.rowPlans[record.key] = record.plan
      this.stageRow(record.key, name, value)
      if (record.plan.operation === 'create' && !Object.keys(this.drafts[record.key]?.data || {}).length) delete this.drafts[record.key]
    },
    processTask(record) {
      return { ...record.values, key: record.key, __search_key__: record.plan.task_key, parent: this.processResult.parent, preparedPlan: record.plan }
    },
    async processAction(action, record) {
      if (this.blocked) return
      if (action === 'discard') { delete this.drafts[record.key]; this.undo = []; this.redo = []; return }
      if (action === 'save') { await this.save([record.key]); return }
      if (action === 'inspect') {
        if (record.dirty) { this.error = t('Save or discard task edits before opening the Inspector.'); return }
        this.$refs.notes.openTask(this.processResult.parent, {}, { process: record.value, taskSearchKey: record.plan.task_key }); return
      }
      const task = this.processTask(record)
      if (action === 'edit') { this.rowPlans[record.key] = record.plan; await this.edit([task]); return }
      if (action === 'delete') { await this.remove([task]); return }
      await this.edit([], true, record.value)
    },
    syncSource(reload) {
      this.seed = [...(this.objectParents || this.parents || [])]; this.rememberParents(this.seed)
      if (!this.opened || !reload) return
      this.pendingSource = true
      // Invalidate reads only. Editors and saves retain their original parent and revisions.
      if (this.loading) { this.request++; this.loading = this.busy = false }
      this.flushSource()
    },
    flushSource() {
      if (this.pendingSource && this.opened && !this.busy && !this.editor && !this.scheduleEditor && !this.uncertain) this.load()
    },
    searchEdited(value) {
      this.filters.text = value; clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => this.queryChanged(), 250)
    },
    restoreSession(preferences) {
      if (!preferences || typeof preferences !== 'object') return
      if (this.scopeOptions.some(option => option.value === preferences.scope)) this.scope = preferences.scope
      if (typeof preferences.identity === 'string') this.identity = preferences.identity.slice(0, 256)
      this.filters = Object.fromEntries(['text', 'process', 'status', 'assigned', 'supervisor', 'priority', 'milestone', 'due', 'day']
        .filter(name => typeof preferences.filters?.[name] === 'string').map(name => [name, preferences.filters[name].slice(0, 2048)]))
      if (preferences.filters?.hasNotes === true) this.filters.hasNotes = true
      this.quick = Object.fromEntries(['preset', 'process', 'status', 'assigned', 'supervisor', 'priority', 'milestone']
        .filter(name => Array.isArray(preferences.quick?.[name])).map(name => [name, preferences.quick[name].filter(value => typeof value === 'string').slice(0, 64).map(value => value.slice(0, 512))]))
      if (sorts.includes(preferences.sort)) this.sort = preferences.sort
      if (this.groupOptions.some(option => option.value === preferences.group)) this.group = preferences.group
      this.descending = preferences.descending === true
      this.collapsed = Array.isArray(preferences.collapsed) ? preferences.collapsed.filter(value => typeof value === 'string').slice(0, 500) : []
      if (['table', 'gantt'].includes(preferences.view)) this.view = preferences.view
      if (['workspace', 'cards', 'compact'].includes(preferences.surface)) this.surface = preferences.surface
      if ([20, 50, 100, 500].includes(preferences.limit)) this.limit = preferences.limit
      if (Number.isInteger(preferences.year) && preferences.year >= 1900 && preferences.year <= 9999) this.year = preferences.year
      if (Number.isInteger(preferences.month) && preferences.month >= 1 && preferences.month <= 12) this.month = preferences.month
      this.workingDays = preferences.workingDays === true
    },
    applyServerBatch(batch) {
      if (!this.opened || batch.initialActivity || batch.projectCode !== this.project || this.context?.project !== this.project) return
      const changed = batch.reconnected || (batch.activity || []).some(row => ['task', 'status', 'note', 'publication', 'work_hour'].includes(row.__kind__)) ||
        [...(batch.cacheChanges || []), ...(batch.cacheRetired || [])].some(row => row.searchType === 'sthpw/task')
      // A live refresh must never rebase or discard an editor's staged revision.
      if (changed) {
        this.liveVersion++
        if (!this.busy && !this.refreshing && !this.dirty && !this.editor && !this.scheduleEditor && !this.uncertain) this.load(true)
      }
    },
    userLabel(login) { return this.catalog?.users.find(item => item.value === login)?.label || login || '—' },
    parentFor(task) {
      if (task.search_key) return Object.values(this.parentRecords).find(parent => parent.__search_key__ === task.search_key)
      return Object.values(this.parentRecords).find(parent => parent.code === task.search_code &&
        parent.__search_key__.split('?')[0] === task.search_type?.split('?')[0])
    },
    rememberParents(parents) { for (const parent of parents || []) this.parentRecords[parent.__search_key__] = parent },
    beforeUnload(event) { if (this.dirty || this.editor || this.scheduleEditor || this.busy || this.uncertain) { event.preventDefault(); event.returnValue = '' } },
    canLeave() {
      if (!this.$refs.milestones.canLeave()) return false
      if (this.busy || (this.dirty || this.uncertain) && !window.confirm(t('Discard unsaved task changes?'))) return false
      if (this.dirty || this.uncertain) this.close(true)
      return true
    },
    close(force = false) {
      if (force !== true && !this.$refs.milestones.canLeave()) return
      if (force !== true && (this.busy || this.dirty || this.uncertain)) { if (!this.busy) this.confirmation = true; return }
      this.storeColumns(); clearTimeout(this.searchTimer)
      this.$refs.milestones.reset()
      this.request++; this.projectionRequest++; this.$refs.scheduleDialog?.close(); this.$refs.editor?.close(); this.$refs.deleteDialog?.close(); this.$refs.rebaseDialog?.close(); this.$refs.menu?.hidePopover(); if (!this.docked) this.$refs.dialog?.close()
      this.opened = false; this.backgroundRequest = null; this.mobileSearchOpen = this.loading = this.pendingSource = false; this.$emit('closed')
      this.editor = this.deletion = null; this.drafts = {}; this.uncertain = this.confirmation = false; this.busy = false
      this.closeInline(); this.rowPlans = {}; this.expanded = []; this.active = this.anchor = ''; this.$refs.columnMenu?.hidePopover()
      this.mobileTaskKey = ''; this.mobileScroll = {}
      if (this.$refs.viewOptions) this.$refs.viewOptions.open = false
      this.scheduleEditor = null; this.undo = []; this.redo = []; this.projection = null; this.projecting = false
    },
    async openForUser({ login, key, value }) {
      if (this.opened && !this.canLeave()) return
      if (this.opened) this.close(true)
      await this.open(false, login, key ? { [key]:value } : {})
    },
    async openForObjects(parent, process = '') {
      if (this.opened && !this.canLeave()) return
      if (this.opened) this.close(true)
      await this.open(true, '', process ? { process } : {}, false, [parent])
    },
    async open(selected = false, user = '', filters = {}, calendarOnly = false, parents = null, reveal = true) {
      if (this.opened) {
        if (selected) { this.objectParents = parents; this.scope = 'selected'; this.identity = ''; this.filters = filters; this.quick = {}; this.syncSource(true) }
        if (calendarOnly && this.surface !== 'workspace') await this.changeSurface('workspace'); if (!calendarOnly && reveal) this.$emit('opened'); return
      }
      this.objectParents = parents
      this.context = { ticket: this.ticket, project: this.project }; this.seed = [...(parents || this.parents || [])]
      this.savedPreferenceKey = this.preferenceKey
      this.parentRecords = {}; this.rememberParents(this.seed); this.drafts = {}; this.selected = []; this.result = null
      this.catalog = null; this.error = ''; this.uncertain = false; this.filters = {}; this.quick = {}; this.collapsed = []
      this.surface = configurationPreferences.tasks.workspaceSurface === 'browser' ? 'workspace' : configurationPreferences.tasks.quickViewMode; this.processResult = null; this.preferredTasks = {}
      this.view = configurationPreferences.tasks.viewMode; this.undo = []; this.redo = []; this.resourcePrevious = null; this.projectionError = ''
      this.scope = 'user'; this.identity = this.currentUser || ''; this.sort = configurationPreferences.tasks.sortMode; this.group = configurationPreferences.tasks.groupMode; this.descending = false
      this.limit = 50; this.year = new Date().getFullYear(); this.month = new Date().getMonth() + 1; this.workingDays = false
      this.columns = normalizeColumns(configurationPreferences.tasks.columns)
      try { const preferences = JSON.parse(localStorage.getItem(this.preferenceKey) || '{}')
        this.columns = normalizeColumns(preferences.columns || (Array.isArray(preferences.visible) ? columns.map(column => ({ ...column, visible: column.key === 'object' || preferences.visible.includes(column.key) })) : configurationPreferences.tasks.columns))
        this.restoreSession(preferences)
      } catch { /* Preferences do not prevent opening the workspace. */ }
      if (selected || user) { this.scope = selected ? 'selected' : 'user'; this.identity = user || ''; this.filters = filters; this.quick = {} }
      if (selected || user) this.surface = 'workspace'
      if (calendarOnly) this.surface = 'workspace'
      this.opened = true; if (!this.docked) this.$refs.dialog.show(); if (!calendarOnly && reveal) this.$emit('opened')
      await this.load(); await this.$refs.milestones.ensureLoaded()
    },
    async refreshMilestoneCatalog() {
      const context = this.context
      try {
        const catalog = await this.command(readCommand, { action: 'catalog' })
        if (context !== this.context || !this.validContext) return
        this.catalog = catalog
        if (this.editor) this.editor.catalog.milestoneChoices = catalog.milestoneChoices
        // Existing task drafts keep their original catalog revisions for review.
      } catch (error) { if (this.validContext && context === this.context) this.error = error.message }
    },
    async command(command, values, quiet = false) {
      if (!this.validContext) throw new Error(t('The context changed. Reopen the editor.'))
      const response = await rpc('execute_cmd', [this.context, command, values], {}, quiet)
      if (!this.validContext) throw new Error(t('The context changed. Reopen the editor.'))
      return response.info
    },
    async load(quiet = false, append = false) {
      quiet = quiet === true
      if (!this.validContext || this.busy || quiet && this.refreshing) return
      const background = quiet && !!(this.result || this.processResult)
      const id = ++this.request, liveVersion = this.liveVersion; this.backgroundRequest = background ? id : null; this.busy = this.loading = !background; this.pendingSource = false; this.error = ''
      const scope = this.scope === 'selected' ? this.seed.length === 1 ? 'object' : 'multiple' : this.scope
      try {
        if (this.surface !== 'workspace') {
          const parent = this.seed[0]
          const result = parent ? await this.command(readCommand, { action: 'processes', search_key: parent.__search_key__ }, quiet) : null
          if (id !== this.request) return
          if (background && (this.dirty || this.editor || this.scheduleEditor || this.uncertain)) return
          if (background && JSON.stringify(result) === JSON.stringify(this.processResult)) { this.loadedLiveVersion = liveVersion; return }
          this.processResult = result; this.rememberParents(result ? [result.parent] : [])
          if (result?.processes.length) this.catalog = result.processes[0].branches[0].plan.catalog
          this.loadedLiveVersion = liveVersion
          return
        }
        const [result, catalog] = await Promise.all([
          this.command(readCommand, { scope, identity: scope === 'object' ? this.seed[0].__search_key__ : this.scope === 'search_type' ? this.searchType : this.identity,
            search_keys: this.seed.map(row => row.__search_key__), offset: append ? this.result?.nextOffset || 0 : 0, limit: this.limit,
            query: { filters: this.filters, quickFilters: this.quick, sort: this.sort, group: this.group, descending: this.descending } }, quiet),
          this.command(readCommand, { action: 'catalog' }, quiet),
        ])
        if (id !== this.request) return
        if (background && (this.dirty || this.editor || this.scheduleEditor || this.uncertain)) return
        result.nextOffset = result.offset + result.loaded
        if (background && JSON.stringify(result) === JSON.stringify(this.result) && JSON.stringify(catalog) === JSON.stringify(this.catalog)) { this.loadedLiveVersion = liveVersion; return }
        if (!background) { this.closeInline(); this.rowPlans = {} }
        if (append) {
          result.tasks = [...new Map([...this.result.tasks, ...result.tasks].map(task => [task.__search_key__, task])).values()]
          result.loaded = result.tasks.length
        } else if (background) { this.selected = this.selected.filter(key => result.tasks.some(task => task.__search_key__ === key)) }
        else { this.selected = []; this.active = this.anchor = '' }
        this.result = result; this.catalog = catalog; this.rememberParents(result.parents)
        this.loadedLiveVersion = liveVersion
        if (this.mobileTaskKey && !this.mobileTask) { this.mobileTaskKey = ''; this.mobileHistory(true) }
        this.expanded = this.expanded.filter(key => this.tasks.some(task => task.key === key && !task.deleting))
        const expanded = this.tasks.filter(task => (this.expanded.includes(task.key) || task.key === this.mobileTaskKey) && !task.deleting && !this.drafts[task.key] && task.parent)
        if (expanded.length) {
          const prepared = await this.command(editCommand, { action: 'prepare', plans: expanded.map(task => this.taskRequest(task)) }, quiet)
          if (id !== this.request) return
          if (background && (this.dirty || this.editor || this.scheduleEditor || this.uncertain)) return
          this.rowPlans = Object.fromEntries(prepared.plans.map(plan => [plan.task_key, plan]))
        }
      } catch (error) { if (id === this.request) this.error = error.message }
      finally {
        if (id === this.request) {
          this.busy = this.loading = false; this.backgroundRequest = null
          if (this.pendingSource) this.flushSource()
          else if (background && !this.error && this.liveChanged && this.loadedLiveVersion >= liveVersion && !this.dirty && !this.editor && !this.scheduleEditor && !this.uncertain) this.load(true)
        }
      }
    },
    changeScope(scope) {
      if (this.blocked) return
      this.scope = scope; this.identity = scope === 'user' ? this.currentUser : scope === 'team' ? this.catalog?.teams[0]?.value || '' : ''
      this.seed = [...(this.parents || [])]; this.rememberParents(this.seed)
      this.filters = {}; this.quick = {}; this.load()
    },
    queryChanged() {
      clearTimeout(this.searchTimer)
      if (this.loading) { this.request++; this.loading = this.busy = false }
      this.pendingSource = true; this.flushSource()
    },
    filterChanged(name, value) { this.filters[name] = value; this.queryChanged() },
    clearFilters() { this.filters = {}; this.quick = {}; this.queryChanged() },
    identityChanged(value) { this.identity = value; this.queryChanged() },
    sortBy(sort) { this.descending = this.sort === sort ? !this.descending : false; this.sort = sort; this.queryChanged() },
    toggleQuick(name, value, checked) {
      this.quick[name] = checked ? [...new Set([...(this.quick[name] || []), value])] : (this.quick[name] || []).filter(item => item !== value)
      this.queryChanged()
    },
    toggleColumn(key, checked) {
      if (key === 'object') return
      const column = this.columns.find(column => column.key === key)
      if (column) { column.visible = checked; this.storeColumns() }
    },
    storeColumns() { if (this.opened) try { localStorage.setItem(this.savedPreferenceKey, this.sessionState) } catch { /* Session choices still work. */ } },
    sizeColumn(key, width) {
      const column = this.columns.find(column => column.key === key)
      if (!column || !Number.isFinite(Number(width))) return
      column.width = Math.max(40, Math.min(480, Math.trunc(Number(width)))); this.storeColumns()
    },
    moveColumn(key, direction) {
      const index = this.columns.findIndex(column => column.key === key), target = index + direction
      if (index < 0 || target < 0 || target >= this.columns.length) return
      this.columns.splice(target, 0, this.columns.splice(index, 1)[0]); this.storeColumns()
    },
    resetColumns() { this.columns = normalizeColumns(configurationPreferences.tasks.columns); this.storeColumns() },
    openColumns() { this.$refs.columnMenu?.hidePopover(); this.$refs.viewOptions.open = true; nextTick(() => this.$refs.viewOptions.$el.querySelector('.task-column-options input')?.focus()) },
    async columnContext(column, bounds) {
      this.columnMenu = column; await nextTick(); const menu = this.$refs.columnMenu; menu.showPopover()
      menu.style.left = Math.max(8, Math.min(bounds.left, innerWidth - menu.offsetWidth - 8)) + 'px'
      menu.style.top = Math.max(8, Math.min(bounds.bottom, innerHeight - menu.offsetHeight - 8)) + 'px'
    },
    columnSort(descending) { if (!this.columnMenu?.sort || this.busy) return; this.sort = this.columnMenu.sort; this.descending = descending; this.$refs.columnMenu.hidePopover(); this.queryChanged() },
    toggle(key, checked, modifiers = {}) {
      if (this.busy) return
      if (modifiers.shiftKey && this.anchor && this.visibleTasks.some(task => task.key === this.anchor)) {
        const keys = this.visibleTasks.map(task => task.key), from = keys.indexOf(this.anchor), to = keys.indexOf(key)
        if (to >= 0) { const range = keys.slice(Math.min(from, to), Math.max(from, to) + 1); this.selected = checked ? [...new Set([...this.selected, ...range])] : this.selected.filter(key => !range.includes(key)) }
      } else { this.selected = checked ? [...new Set([...this.selected, key])] : this.selected.filter(item => item !== key); this.anchor = key }
      this.active = key
    },
    selectVisible(checked) {
      const keys = this.visibleTasks.map(task => task.key)
      this.selected = checked ? [...new Set([...this.selected, ...keys])] : this.selected.filter(key => !keys.includes(key))
    },
    activate(key, modifiers = {}) {
      if (this.busy) return
      if (modifiers.shiftKey) this.toggle(key, true, modifiers)
      else if (modifiers.ctrlKey || modifiers.metaKey) this.toggle(key, !this.selected.includes(key))
      else { this.active = this.anchor = key }
    },
    async tableKey(key, modifiers) {
      if (this.busy || !this.visibleTasks.length) return
      const tasks = this.visibleTasks, index = tasks.findIndex(task => task.key === this.active)
      if (key === 'a' && (modifiers.ctrlKey || modifiers.metaKey)) { this.selected = tasks.map(task => task.key); return }
      if (key === ' ') { const task = tasks[index < 0 ? 0 : index]; this.toggle(task.key, !this.selected.includes(task.key), modifiers); return }
      const next = key === 'Home' ? 0 : key === 'End' ? tasks.length - 1 : key === 'ArrowDown' ? Math.min(tasks.length - 1, index + 1) : Math.max(0, index - 1)
      this.activate(tasks[next].key, modifiers); await nextTick(); this.$refs.table.focusRow(tasks[next].key)
    },
    async prepareRow(task) {
      if (this.blocked || task.deleting || !task.parent) return null
      if (this.drafts[task.key]) return this.drafts[task.key]
      if (this.rowPlans[task.key]) return this.rowPlans[task.key]
      const id = ++this.request; this.busy = true; this.error = ''
      try {
        const result = await this.command(editCommand, { action: 'prepare', plans: [this.taskRequest(task)] })
        if (id !== this.request) return null
        return this.rowPlans[task.key] = result.plans[0]
      } catch (error) { if (id === this.request) this.error = error.message; return null }
      finally { if (id === this.request) this.busy = false }
    },
    async expand(task) {
      if (this.busy) return
      if (this.expanded.includes(task.key)) { this.expanded = this.expanded.filter(key => key !== task.key); return }
      if (await this.prepareRow(task)) { this.activate(task.key, {}); this.expanded.push(task.key) }
    },
    stageRow(key, name, value) {
      if (this.blocked) return
      const plan = this.drafts[key] || this.rowPlans[key]
      if (!plan || plan.operation === 'delete' || !plan.fields.some(field => field.name === name && field.editable)) return
      const data = { ...plan.data }
      if (String(value ?? '') === String(plan.task[name] ?? '')) delete data[name]; else data[name] = value ?? ''
      this.undo = []; this.redo = []
      if (plan.operation === 'create' || Object.keys(data).length) this.drafts[key] = { ...plan, data }; else delete this.drafts[key]
    },
    async editCell(task, column, bounds) {
      const fields = { process: ['process', 'context'], status: ['status'], assigned: ['assigned'], dates: ['bid_start_date', 'bid_end_date'],
        progress: ['progress', 'completion'], bid_duration: ['bid_duration'], priority: ['priority'], milestone_code: ['milestone_code'], supervisor: ['supervisor'] }[column.key]
      if (!fields) return
      const plan = await this.prepareRow(task)
      if (!plan || !plan.fields.some(field => field.editable && fields.includes(field.name))) return
      this.inline = { key: task.key, fields }; await nextTick(); const popup = this.$refs.inline
      popup.showPopover(); popup.style.left = Math.max(8, Math.min(bounds.left, innerWidth - popup.offsetWidth - 8)) + 'px'
      popup.style.top = Math.max(8, Math.min(bounds.bottom, innerHeight - popup.offsetHeight - 8)) + 'px'
      popup.querySelector('select, input, textarea')?.focus()
    },
    closeInline() { this.$refs.inline?.hidePopover(); this.inline = null },
    collapse(key) { this.collapsed = this.collapsed.includes(key) ? this.collapsed.filter(item => item !== key) : [...this.collapsed, key] },
    taskRequest(task, operation = 'update') {
      const plan = this.drafts[task.key]
      return plan ? { ...plan, operation } : { operation, search_key: task.parent.__search_key__, task_key: task.__search_key__, process: task.process }
    },
    async edit(tasks, creating = false, process = '') {
      if (this.blocked || !creating && tasks.some(task => !task.parent || task.deleting)) return
      this.busy = true; this.error = ''
      const id = ++this.request
      try {
        let plans
        if (creating) {
          const parent = this.editor?.creating ? this.parentFor(this.editor.plans[0]) : this.creationParent
          const catalog = await this.command(readCommand, { action: 'catalog', search_key: parent?.__search_key__ || '' })
          if (!parent) this.rememberParents([{ __search_key__: catalog.parent_key, code: catalog.project }])
          const selectedProcess = process || catalog.processes[0]?.value
          if (!selectedProcess) throw new Error(t('No task process is available for this object.'))
          const empty = this.surface !== 'workspace' && !this.editor?.creating ? this.processResult?.processes.find(item => item.value === selectedProcess)?.branches.find(branch => !branch.plan.task_key)?.plan : null
          plans = empty ? [this.drafts[empty.draft_id] || empty] : (await this.command(editCommand, { action: 'prepare', plans: [{ operation: 'create',
            draft_id: this.editor?.creating ? this.editor.plans[0].draft_id : Array.from(crypto.getRandomValues(new Uint32Array(4)), value => value.toString(16)).join('-'), search_key: parent?.__search_key__ || '', process: selectedProcess }] })).plans
        } else {
          // Retain the original revisions for already staged edits; refreshing must not rebase them silently.
          const fresh = tasks.filter(task => !this.drafts[task.key] && !task.preparedPlan)
          const prepared = fresh.length ? (await this.command(editCommand, { action: 'prepare', plans: fresh.map(task => this.taskRequest(task)) })).plans : []
          plans = tasks.map(task => this.drafts[task.key] || task.preparedPlan || prepared.find(plan => plan.task_key === task.__search_key__))
        }
        if (id !== this.request) return
        const first = plans[0]
        const intersect = (name, path) => first[path].filter(choice => plans.every(plan => plan[path].some(other => String(other[name]) === String(choice[name]))))
        const catalog = { ...first.catalog, priorityChoices: first.catalog.priorityChoices.filter(choice => plans.every(plan => plan.catalog.priorityChoices.some(other => String(other.value) === String(choice.value)))),
          milestoneChoices: first.catalog.milestoneChoices.filter(choice => plans.every(plan => plan.catalog.milestoneChoices.some(other => other.value === choice.value))) }
        const fields = first.fields.filter(field => field.editable && plans.every(plan => plan.fields.some(other => other.name === field.name && other.editable)))
        const retained = creating && this.editor?.creating ? Object.fromEntries(['description', 'priority', 'milestone_code'].map(name => [name, this.editor.values[name]]).filter(([, value]) => value !== undefined)) : {}
        const values = { ...first.task, ...first.data, ...retained }
        this.editor = { plans, creating: plans.length === 1 && first.operation === 'create', fields, values, baseline: { ...values }, enabled: [], catalog,
          statuses: first.statuses.filter(value => plans.every(plan => plan.statuses.includes(value))), users: intersect('value', 'users') }
        await nextTick(); if (!this.$refs.editor.open) this.$refs.editor.showModal()
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    cancelEdit(force = false) {
      if (this.busy || force !== true && this.editor && JSON.stringify(this.editor.values) !== JSON.stringify(this.editor.baseline) && !window.confirm(t('Discard unsaved task changes?'))) return
      this.$refs.editor.close(); this.editor = null
    },
    stageEditor() {
      this.undo = []; this.redo = []
      for (const plan of this.editor.plans) {
        const names = this.editor.plans.length > 1 ? this.editor.enabled : this.editor.fields.map(field => field.name)
        const data = { ...plan.data }
        for (const name of names) {
          const value = this.editor.values[name] ?? ''
          if (String(value) !== String(plan.task[name] ?? '')) data[name] = value
          else delete data[name]
        }
        if (plan.operation === 'create' && !Object.keys(data).length) {
          const field = this.editor.fields.find(field => ['process', 'context'].includes(field.name))
          if (!field) { this.error = t('No editable task fields are available.'); return }
          data[field.name] = plan.task[field.name]
        }
        const key = plan.draft_id || plan.task_key
        if (plan.operation === 'create' || Object.keys(data).length) this.drafts[key] = { ...plan, data }
        else delete this.drafts[key]
      }
      if (this.surface !== 'workspace') for (const plan of this.editor.plans) this.preferredTasks[plan.process] = plan.task_key || plan.draft_id
      this.cancelEdit(true)
    },
    async remove(tasks) {
      this.$refs.menu?.hidePopover()
      if (this.blocked) return
      if (tasks.some(task => this.drafts[task.key])) { this.error = t('Save or discard task edits before deleting.'); return }
      this.busy = true; this.error = ''; const id = ++this.request
      try {
        const result = await this.command(editCommand, { action: 'prepare', plans: tasks.map(task => this.taskRequest(task, 'delete')) })
        if (id !== this.request) return
        this.deletion = result.plans.map(plan => ({ ...plan, related_types: [] }))
        await nextTick(); this.$refs.deleteDialog.showModal()
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    stageDeletion() {
      this.undo = []; this.redo = []
      for (const plan of this.deletion) this.drafts[plan.task_key] = plan
      this.$refs.deleteDialog.close(); this.deletion = null
    },
    discard() {
      if (this.busy || !window.confirm(t(this.uncertain ? 'Discard this draft? Some changes may already have been saved.' : 'Discard unsaved task changes?'))) return
      this.drafts = {}; this.undo = []; this.redo = []; this.uncertain = false; this.load()
    },
    async rebase() {
      if (this.blocked || !this.dirty) return
      if (Object.values(this.drafts).some(plan => plan.operation === 'delete')) { this.error = t('Discard staged deletions and review dependencies again before rebasing.'); return }
      this.busy = true; this.error = ''; const id = ++this.request
      try {
        const previous = Object.values(this.drafts)
        const result = await this.command(editCommand, { action: 'prepare', plans: previous })
        if (id !== this.request) return
        this.rebaseReview = result.plans.map((plan, index) => ({ ...plan, data: previous[index].data || {} }))
        await nextTick(); this.$refs.rebaseDialog.showModal()
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    async save(keys = null) {
      if (this.blocked || !this.dirty) return
      const entries = Object.entries(this.drafts).filter(([key]) => !Array.isArray(keys) || keys.includes(key))
      if (!entries.length) return
      this.busy = true; this.error = ''; const id = ++this.request; let saved = false
      try {
        await this.command(editCommand, { action: 'save', plans: entries.map(([, plan]) => plan) })
        if (id !== this.request) return
        for (const [key] of entries) { delete this.drafts[key]; delete this.rowPlans[key] }
        this.undo = []; this.redo = []; saved = true; this.$emit('saved')
      } catch (error) {
        if (id === this.request) { this.error = error.message; this.uncertain = !error.status || error.status >= 500 }
      } finally { if (id === this.request) this.busy = false }
      if (saved) { await this.load(); await this.$refs.milestones.ensureLoaded() }
    },
    async showMenu(task, bounds) {
      this.rowMenu = task; await nextTick(); this.$refs.menu.showPopover()
      this.$refs.menu.style.left = Math.max(8, Math.min(bounds.left, innerWidth - this.$refs.menu.offsetWidth - 8)) + 'px'
      this.$refs.menu.style.top = Math.max(8, Math.min(bounds.bottom, innerHeight - this.$refs.menu.offsetHeight - 8)) + 'px'
    },
    openObject(task) {
      if (this.blocked || this.dirty || !task?.parent || task.deleting) return
      this.$refs.menu.hidePopover(); this.$emit('object', task.parent); this.close()
    },
    inspect(task) {
      if (task?.parent?.__search_key__) this.$emit('snapshot-context',{ project:this.project,key:task.parent.__search_key__,process:task.process || '' })
      this.$refs.menu.hidePopover()
      if (!task?.__search_key__ || this.drafts[task.key]) { this.error = t('Save or discard task edits before opening the Inspector.'); return }
      this.$refs.notes.openTask(task.parent, {}, { process: task.process, taskSearchKey: task.__search_key__ })
    },
    logTime(task) {
      this.$refs.menu.hidePopover()
      this.$refs.timesheet.open({ scope: { search_key: task.parent.__search_key__, process: task.process, task_key: task.__search_key__ }, users: this.catalog.users })
    },
    async projectSchedule() {
      const id = ++this.projectionRequest
      if ((!this.calendarActive && (this.mobile || this.surface !== 'workspace' || this.view === 'table')) || !this.result || !this.opened || !this.validContext) { this.projecting = false; return }
      const input = this.projectionInput
      this.projecting = true; this.projectionError = ''
      try {
        const projection = await this.command(scheduleCommand, { action: 'projection', ...JSON.parse(input) })
        if (id === this.projectionRequest) {
          const tasks = new Map(this.tasks.map(task => [task.key, task]))
          for (const day of projection.calendar) for (const record of day.tasks) record.statusColor = tasks.get(record.taskCode)?.__status__?.color || ''
          this.projection = projection
        }
      } catch (error) { if (id === this.projectionRequest) { this.projection = null; this.projectionError = error.message } }
      finally { if (id === this.projectionRequest) this.projecting = false }
    },
    selectDay(day) { this.filters.day = this.filters.day === day ? '' : day; this.queryChanged() },
    changeMonth(delta) {
      if (this.busy) return
      const value = new Date(this.year, this.month - 1 + delta, 1)
      this.year = value.getFullYear(); this.month = value.getMonth() + 1
      if (this.filters.day) { this.filters.day = ''; this.queryChanged() }
    },
    setMonth(value) {
      if (this.busy || !/^\d{4}-\d{2}$/.test(value)) return
      const [year, month] = value.split('-').map(Number)
      if (year < 2 || year > 9997 || month < 1 || month > 12) return
      this.year = year; this.month = month
      if (this.filters.day) { this.filters.day = ''; this.queryChanged() }
    },
    calendarToday() {
      const value = new Date(); this.year = value.getFullYear(); this.month = value.getMonth() + 1
      this.filters.day = `${this.year}-${String(this.month).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`; this.queryChanged()
    },
    resourceMode(enabled) {
      if (this.blocked) return
      if (enabled) { this.resourcePrevious = { sort: this.sort, group: this.group, descending: this.descending }; this.sort = this.group = 'user'; this.descending = false }
      else { Object.assign(this, this.resourcePrevious); this.resourcePrevious = null }
      this.queryChanged()
    },
    scheduleSnapshot() {
      return Object.fromEntries(Object.entries(this.drafts).filter(([, plan]) => plan.operation !== 'delete').map(([key, plan]) =>
        [key, { plan, data: Object.fromEntries(Object.entries(plan.data || {}).filter(([name]) => scheduleFields.includes(name))) }]))
    },
    restoreSchedule(snapshot) {
      for (const key of new Set([...Object.keys(this.drafts), ...Object.keys(snapshot)])) {
        const current = this.drafts[key] || snapshot[key]?.plan
        if (!current || current.operation === 'delete') continue
        const data = { ...Object.fromEntries(Object.entries(this.drafts[key]?.data || {}).filter(([name]) => !scheduleFields.includes(name))), ...snapshot[key]?.data }
        if (current.operation === 'create' || Object.keys(data).length) this.drafts[key] = { ...current, data }
        else delete this.drafts[key]
      }
    },
    history(back = true) {
      if (this.blocked) return
      const source = back ? this.undo : this.redo, target = back ? this.redo : this.undo
      if (!source.length) return
      target.push(this.scheduleSnapshot()); this.restoreSchedule(source.pop())
    },
    async stageSchedule(edits) {
      const id = this.request
      const keys = Object.keys(edits), tasks = keys.map(key => this.tasks.find(task => task.key === key))
      if (tasks.some(task => !task || task.deleting)) throw new Error(t('Save or discard task edits before deleting.'))
      const fresh = tasks.filter(task => !this.drafts[task.key])
      const prepared = fresh.length ? (await this.command(editCommand, { action: 'prepare', plans: fresh.map(task => this.taskRequest(task)) })).plans : []
      if (id !== this.request || !this.opened || !this.validContext) throw new Error(t('The context changed. Reopen the editor.'))
      const staged = {}
      for (const task of tasks) {
        const plan = this.drafts[task.key] || prepared.find(plan => plan.task_key === task.__search_key__)
        const data = { ...plan.data }
        for (const [name, value] of Object.entries(edits[task.key])) {
          if (!plan.fields.some(field => field.name === name && field.editable)) throw new Error(t('The selected schedule field is not editable.'))
          if (String(value) !== String(plan.task[name] ?? '')) data[name] = value
          else delete data[name]
        }
        staged[task.key] = { ...plan, data }
      }
      if (keys.every(key => JSON.stringify(staged[key].data) === JSON.stringify(this.drafts[key]?.data || {}))) return
      this.undo.push(this.scheduleSnapshot()); this.undo = this.undo.slice(-50); this.redo = []
      for (const [key, plan] of Object.entries(staged)) {
        if (plan.operation === 'create' || Object.keys(plan.data).length) this.drafts[key] = plan
        else delete this.drafts[key]
      }
    },
    async stageProgress(key, value) {
      if (this.blocked || this.projecting) return
      const task = this.tasks.find(task => task.key === key)
      const field = task && (Object.hasOwn(task, 'progress') ? 'progress' : Object.hasOwn(task, 'completion') ? 'completion' : '')
      if (!field) return
      this.busy = true; this.error = ''
      try { await this.stageSchedule({ [key]: { [field]: value } }) }
      catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    async schedule(values, keys = this.selected) {
      if (this.blocked || !keys.length || this.projecting) return
      this.busy = true; this.error = ''; const id = ++this.request
      try {
        const records = this.scheduleRecords.filter(record => keys.includes(record.taskCode))
        const result = await this.command(scheduleCommand, { ...values, records, working_days: this.workingDays })
        if (id !== this.request) return
        await this.stageSchedule(Object.fromEntries(Object.entries(result.edits).map(([key, value]) => [key, { bid_start_date: value.start, bid_end_date: value.end }])))
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    async openSchedule(key) {
      if (this.blocked) return
      const task = this.tasks.find(task => task.key === key)
      if (!task || task.deleting) return
      this.busy = true; this.error = ''; const id = ++this.request
      try {
        const plan = this.drafts[key] || (await this.command(editCommand, { action: 'prepare', plans: [this.taskRequest(task)] })).plans[0]
        if (id !== this.request) return
        const editable = name => plan.fields.some(field => field.name === name && field.editable)
        const record = this.projection?.gantt.records.find(record => record.taskCode === key)
        const start = task.bid_start_date?.slice(0, 10) || new Date().toLocaleDateString('en-CA')
        this.scheduleEditor = { key, plan, dates: editable('bid_start_date') && editable('bid_end_date'),
          progressField: editable('progress') ? 'progress' : editable('completion') ? 'completion' : '',
          start, duration: record?.ganttDurationDays || 1, progress: Number(task.progress ?? task.completion) || 0, move: false }
        this.scheduleEditor.baseline = JSON.stringify([start, this.scheduleEditor.duration, this.scheduleEditor.progress, false])
        await nextTick(); this.$refs.scheduleDialog.showModal()
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    cancelSchedule() {
      const form = this.scheduleEditor
      if (this.busy || form && JSON.stringify([form.start, form.duration, form.progress, form.move]) !== form.baseline && !window.confirm(t('Discard unsaved task changes?'))) return
      this.$refs.scheduleDialog.close(); this.scheduleEditor = null
    },
    async applySchedule() {
      if (this.blocked || !this.scheduleEditor) return
      const form = this.scheduleEditor, id = ++this.request; this.busy = true; this.error = ''
      try {
        const records = this.scheduleRecords.filter(record => record.taskCode === form.key || form.move && this.selected.includes(record.taskCode))
        const result = form.dates ? await this.command(scheduleCommand, { action: 'schedule', records, primary: form.key, range_start: form.start,
          start_day: 0, duration: Number(form.duration), working_days: this.workingDays, move_selected: form.move }) : { edits: {} }
        if (id !== this.request) return
        const edits = Object.fromEntries(Object.entries(result.edits).map(([key, value]) => [key, { bid_start_date: value.start, bid_end_date: value.end }]))
        if (form.progressField) edits[form.key] = { ...edits[form.key], [form.progressField]: Number(form.progress) }
        // Reuse the form's original revision, including changes arriving while it was open.
        const previous = this.drafts[form.key]
        if (!previous) this.drafts[form.key] = { ...form.plan, data: {} }
        try { await this.stageSchedule(edits) } catch (error) { if (!previous && !Object.keys(this.drafts[form.key]?.data || {}).length) delete this.drafts[form.key]; throw error }
        if (!Object.keys(this.drafts[form.key]?.data || {}).length && form.plan.operation !== 'create') delete this.drafts[form.key]
        this.$refs.scheduleDialog.close(); this.scheduleEditor = null
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    scheduleShortcut(event) {
      if (this.view !== 'gantt' || !(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'z' ||
          this.scheduleEditor || this.editor || event.target.closest('input, textarea, select, [contenteditable="true"]')) return
      event.preventDefault(); this.history(!event.shiftKey)
    },
  },
}
</script>

<template>
  <Teleport defer :to="docked ? '#dock-tasks' : 'body'">
    <component v-window="docked ? false : { type:'window' }" :is="docked ? 'section' : 'dialog'" ref="dialog" class="configuration-dialog task-manager" :class="{ 'task-manager-docked': docked, 'task-manager-detail': mobile && !!mobileTask }" :open="opened" :role="docked ? 'region' : 'dialog'" :aria-modal="false" :aria-label="t('Task Manager')" @cancel.prevent="close()" @keydown="scheduleShortcut">
      <header v-if="!docked" class="task-manager-heading"><div><h2>{{ t('Task Manager') }}</h2><small class="muted">{{ project }}</small></div>
        <AppButton label="Close" icon="close" icon-only :disabled="busy" @click="close()" /></header>
      <aside v-if="confirmation" class="notice"><p>{{ t('Discard unsaved task changes?') }}</p><AppButton label="Keep editing" @click="confirmation = false" /><AppButton label="Discard changes" destructive @click="close(true)" /></aside>
      <div v-if="surface !== 'workspace'" class="task-manager-toolbar task-process-toolbar">
        <AppIcon name="MDI_CHECK_CIRCLE" /><strong>{{ processResult?.parent?.name || processResult?.parent?.title || processResult?.parent?.code || t('Select an sObject') }}</strong>
        <AppButton label="Save all process changes" icon="save" icon-only :disabled="blocked || !dirty" @click="save()" />
        <AppButton label="Discard all process changes" icon="undo" icon-only :disabled="busy || !dirty" @click="discard" />
        <TaskWorkspaceSurfaceSwitcher :value="surface" :disabled="blocked && !loading" @change="changeSurface" />
        <AppButton label="Refresh" icon="refresh" icon-only :disabled="busy" @click="load()" />
      </div>
      <form v-else class="task-manager-toolbar" @submit.prevent="queryChanged()">
        <AppButton label="Create task" icon="add" icon-only :disabled="blocked" @click="edit([], true)" />
        <AppButton v-if="toolbarWidth >= 520 && !mobile" label="Project milestones" icon="MDI_FLAG_VARIANT" icon-only :disabled="busy" @click="$refs.milestones.open()" />
        <AppButton v-if="mobile" class="task-search-toggle" icon-only icon="search" label="Open search" :aria-expanded="mobileSearchOpen" :highlighted="!!filters.text" @click="mobileSearchOpen = !mobileSearchOpen; mobileSearchOpen && $nextTick(()=>$refs.taskSearch.focus())" />
        <AppSearchField v-show="!mobile || mobileSearchOpen" ref="taskSearch" :model-value="filters.text || ''" label="Search tasks" :placeholder="t('Search tasks')" :disabled="blocked && !loading" @update:model-value="searchEdited" @search="queryChanged(); mobileSearchOpen = false" @dismiss="mobileSearchOpen = false" />
        <AppMenu v-if="toolbarWidth >= 520 && !mobile" ref="filtersMenu" class="task-manager-filters" overlay :close-on-select="false" label="Task filters" icon="filter" :class="{ 'filters-active': filtersActive }">
          <TaskWorkspaceFilters :filters="filters" :quick="quick" :presets="presets" :facets="result?.facets" :busy="busy" @filter="filterChanged" @quick="toggleQuick" @clear="clearFilters" />
        </AppMenu>
        <AppButton v-if="toolbarWidth >= 520 && !mobile" label="Clear filters" icon="MDI_FILTER_OFF" icon-only :disabled="busy || !filtersActive" @click="clearFilters" />
        <AppMenu v-if="toolbarWidth >= 380 && !mobile" ref="scopeMenu" class="task-manager-scope" overlay :close-on-select="false" label="Choose task scope" icon="MDI_ARCHIVE_OUTLINE">
          <template #trigger><AppIcon :name="scopeOptions.find(option => option.value === scope)?.icon" /><span v-if="toolbarWidth >= 800">{{ t(scopeTitle) }}</span></template>
          <TaskWorkspaceScope :scope="scope" :identity="identity" :options="scopeOptions" :catalog="catalog" :blocked="blocked" @scope="changeScope($event); !['user','team'].includes($event) && $refs.scopeMenu.close()" @identity="identityChanged" />
        </AppMenu>
        <AppSelect v-if="toolbarWidth >= 1180" v-model="sort" class="task-manager-sort" :options="sortOptions" label="Sort" :disabled="busy" @update:model-value="queryChanged" />
        <AppSelect v-if="toolbarWidth >= 720" v-model="group" class="task-manager-group" :options="groupOptions" label="Group" :disabled="busy" @update:model-value="queryChanged" />
        <TaskWorkspaceSurfaceSwitcher v-if="toolbarWidth >= 720" :value="surface" :disabled="blocked && !loading" @change="changeSurface" />
        <AppMenu ref="viewOptions" class="task-manager-options" overlay :close-on-select="false" label="Task view options">
          <AppCheckbox v-if="mobile" label="Select all tasks" :model-value="allSelected" :indeterminate="!!selected.length && !allSelected" :disabled="busy" @update:model-value="selectVisible" />
          <TaskWorkspaceSurfaceSwitcher v-if="toolbarWidth < 720" :value="surface" :disabled="blocked && !loading" @change="changeSurface" />
          <AppButton v-if="mobile || toolbarWidth < 520" label="Project milestones" icon="MDI_FLAG_VARIANT" :disabled="busy" @click="$refs.viewOptions.close(); $refs.milestones.open()" />
          <TaskWorkspaceScope v-if="mobile || toolbarWidth < 380" :scope="scope" :identity="identity" :options="scopeOptions" :catalog="catalog" :blocked="blocked" @scope="changeScope" @identity="identityChanged" />
          <TaskWorkspaceFilters v-if="mobile || toolbarWidth < 520" :filters="filters" :quick="quick" :presets="presets" :facets="result?.facets" :busy="busy" @filter="filterChanged" @quick="toggleQuick" @clear="clearFilters" />
            <label v-if="toolbarWidth < 1180">{{ t('Sort') }}<AppSelect v-model="sort" :options="sortOptions" label="Sort" :disabled="busy" @update:model-value="queryChanged" /></label>
            <AppCheckbox label="Descending" v-model="descending" :disabled="busy" @update:model-value="queryChanged" />
            <label v-if="toolbarWidth < 720">{{ t('Group') }}<AppSelect v-model="group" :options="groupOptions" label="Group" :disabled="busy" @update:model-value="queryChanged" /></label>
            <template v-if="!mobile"><strong>{{ t('Task columns') }}</strong><div class="task-column-options">
              <section v-for="(column, index) in columns" :key="column.key" :data-column-option="column.key">
                <AppCheckbox :label="column.label" :model-value="column.visible" :disabled="column.key === 'object'" @update:model-value="toggleColumn(column.key, $event)" />
                <div><input type="number" min="40" max="480" step="1" :value="column.width" :aria-label="t('Width of {column}', { column: t(column.label) })" @change="sizeColumn(column.key, $event.target.value)" @keydown.enter.prevent="sizeColumn(column.key, $event.target.value)">
                  <AppButton label="Move column left" icon="previous" icon-only :disabled="index === 0" @click="moveColumn(column.key, -1)" /><AppButton label="Move column right" icon="next" icon-only :disabled="index === columns.length - 1" @click="moveColumn(column.key, 1)" />
                </div>
              </section><AppButton label="Reset task columns" icon="undo" @click="resetColumns" />
            </div></template>
            <label>{{ t('Records per page') }}<AppSelect :model-value="limit" label="Records per page" :options="[20, 50, 100, 500].map(value => ({ value, label: String(value) }))" :disabled="busy" @update:model-value="limit = $event; queryChanged()" /></label>
        </AppMenu>
        <AppButton label="Refresh" icon="refresh" icon-only :disabled="busy" @click="load()" />
      </form>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="uncertain" class="notice" role="alert">{{ t('The server may have saved these tasks. Saving is blocked; inspect the refreshed data before discarding the draft.') }}</p>
      <p v-if="liveChanged && !refreshing && !loading" class="notice" role="status">{{ t('Tasks changed on the server. Refresh to review current values; your draft keeps its original revisions.') }}</p>
      <p v-if="surface === 'workspace' && projectionError && displayedView !== 'table'" class="error" role="alert">{{ t(projectionError) }}</p>
      <small v-if="surface === 'workspace' && displayedView !== 'table' && result?.hasMore" class="muted">{{ t('Calendar and Gantt show loaded tasks. Use Load more tasks to include the remaining tasks.') }}</small>
      <div v-if="surface === 'workspace' && selected.length" class="task-manager-selection"><span>{{ t('{count} selected', { count: selected.length }) }}</span><AppButton label="Edit selected tasks" icon="edit" icon-only :disabled="blocked" @click="edit(tasks.filter(task => selected.includes(task.key)))" /><AppButton label="Delete selected tasks" icon="delete" icon-only destructive :disabled="blocked" @click="remove(tasks.filter(task => selected.includes(task.key)))" /><AppButton label="Clear selection" icon="close" icon-only @click="selected = []" /></div>
      <div class="task-manager-results" :aria-busy="busy" @scroll="closeInline">
        <div v-if="dirty && surface === 'workspace'" class="task-manager-pending-slot" :class="{ overlay: displayedView === 'table' }"><div class="task-manager-pending" role="region" :aria-label="t('Pending task changes')"><span>{{ t('{count} unsaved tasks', { count: Object.keys(drafts).length }) }}</span><AppButton v-if="error" label="Reload draft revisions" icon="refresh" icon-only :disabled="blocked" @click="rebase" /><AppButton label="Discard task changes" :disabled="busy" @click="discard"><span>{{ t('Discard') }}</span></AppButton><AppButton label="Save task changes" icon="save" highlighted :disabled="blocked" @click="save"><span>{{ t('Save') }}</span></AppButton></div></div>
        <TaskProcessPanel v-if="surface !== 'workspace'" :records="processRecords" :mode="surface" :target="processResult?.parent" :blocked="blocked"
          @change="stageProcess" @select="(process, key) => preferredTasks[process] = key" @save="processAction('save', $event)" @discard="processAction('discard', $event)"
          @inspect="processAction('inspect', $event)" @add="processAction('add', $event)" @edit="processAction('edit', $event)" @delete="processAction('delete', $event)" />
        <MobileTasks v-else-if="mobile" :groups="groups" :selected="selected" :collapsed="collapsed"
          :task="mobileTask" :editor="rowEditors[mobileTaskKey]" :busy="busy" :blocked="blocked" :dirty="dirty" :active="opened"
          :direction="mobileDirection" :scroll="mobileScroll" :has-more="!!result?.hasMore"
          @enter="mobileEnter" @back="mobileBack" @scrolled="(key, top) => mobileScroll[key] = top" @change="stageRow" @retry="prepareRow"
          @select="toggle" @collapse="collapse" @inspect="inspect" @operate="showMenu" @object="openObject" @milestones="$refs.milestones.open()" @more="load(false, true)" />
        <TaskWorkspaceTable v-else-if="displayedView === 'table' && tasks.length" ref="table" :groups="groups" :columns="columns" :selected="selected" :collapsed="collapsed" :busy="busy" :blocked="blocked" :all-selected="allSelected" :active="active" :expanded="expanded" :editors="rowEditors"
          @activate="activate" @key="tableKey" @expand="expand" @change="stageRow" @edit-cell="editCell" @milestones="$refs.milestones.open()" @size-column="sizeColumn" @columns="openColumns" @column-context="columnContext"
          @select="toggle" @select-all="selectVisible" @collapse="collapse" @sort="sortBy" @inspect="inspect" @object="openObject" @operate="showMenu" />
        <TaskGanttView v-else-if="displayedView !== 'table'" :active="active" :has-more="!!result?.hasMore" :projection="projection" :tasks="tasks"
          :selected="selected" :collapsed="collapsed" :busy="blocked || projecting" :projecting="projecting" :working-days="workingDays" :resource-mode="!!resourcePrevious" :can-undo="!!undo.length" :can-redo="!!redo.length"
          @select="toggle" @collapse="collapse" @edit="openSchedule" @inspect="key => inspect(tasks.find(task => task.key === key))"
          @load-more="load(false,true)" @activate="activate" @select-all="selectVisible" @object="key => openObject(tasks.find(task => task.key === key))" @progress="stageProgress" @delete="remove(tasks.filter(task => selected.includes(task.key)))"
          @milestone="$refs.milestones.open($event)" @working-days="workingDays = $event" @resource-mode="resourceMode" @undo="history(true)" @redo="history(false)"
          @batch="(operation, amount) => schedule({ action: 'batch', operation, amount })"
          @schedule="(key, start, duration, mode) => schedule({ action: 'schedule', primary: key, range_start: projection.gantt.rangeStart, start_day: start, duration, move_selected: mode === 'move' }, mode === 'move' && selected.includes(key) ? selected : [key])">
          <template #footer><AppSegmentedButton :model-value="view" label="Task view" icon-only :options="[{ value: 'table', label: 'Table', icon: 'MDI_TABLE' }, { value: 'gantt', label: 'Gantt', icon: 'MDI_CHART_GANTT' }]" :disabled="busy" @update:model-value="view = $event" /><AppButton v-if="calendarTarget" label="Calendar" icon="MDI_CALENDAR_MONTH" icon-only @click="$emit('calendar')" /></template>
        </TaskGanttView>
        <div v-if="!mobile && surface === 'workspace' && displayedView === 'table' && !tasks.length" class="task-manager-empty" role="status"><strong>{{ t(busy ? 'Loading data…' : filtersActive ? 'No tasks match the current filters' : 'Create a task') }}</strong><p v-if="!busy">{{ t(filtersActive ? 'Clear filters to see all tasks' : creationParent ? 'Use the + button above' : 'Select a parent object before creating a task.') }}</p></div>
      </div>
      <footer v-if="surface !== 'workspace'" class="task-manager-footer task-process-footer"><AppIcon name="MDI_CHECK_CIRCLE" /><span>{{ t('{count} processes', { count: processRecords.length }) }}</span><small v-if="dirty">{{ t('{count} unsaved', { count: Object.keys(drafts).length }) }}</small><BusyIndicator :running="busy" /></footer>
      <footer v-else-if="displayedView === 'table'" class="task-manager-footer"><span>{{ t('{loaded} of {total} tasks', { loaded: result?.loaded || 0, total: result?.total || 0 }) }}</span>
        <AppButton v-if="!mobile && result?.hasMore" label="Load more tasks" icon="add" :disabled="busy" @click="load(false, true)" />
        <AppSegmentedButton v-if="!mobile" :model-value="view" label="Task view" icon-only :options="[{ value: 'table', label: 'Table', icon: 'MDI_TABLE' }, { value: 'gantt', label: 'Gantt', icon: 'MDI_CHART_GANTT' }]" :disabled="busy" @update:model-value="view = $event" />
        <AppButton v-if="!mobile && calendarTarget" label="Calendar" icon="MDI_CALENDAR_MONTH" icon-only :disabled="busy" @click="$emit('calendar')" />
      </footer>
      <div ref="menu" class="task-table-editor task-manager-menu" popover="auto" :aria-label="t('Task actions')">
        <template v-if="rowMenu"><AppButton label="Edit task" icon="edit" :disabled="blocked || rowMenu.deleting" @click="$refs.menu.hidePopover(); edit([rowMenu])" />
          <AppButton label="Task Inspector" icon="MDI_CLIPBOARD_TEXT_OUTLINE" :disabled="!rowMenu.__search_key__ || rowMenu.deleting" @click="inspect(rowMenu)" />
          <AppButton label="Task timesheet" icon="MDI_CLOCK_OUTLINE" :disabled="!rowMenu.__search_key__ || rowMenu.deleting" @click="logTime(rowMenu)" />
          <AppButton label="Open object" icon="next" :disabled="blocked || dirty || !rowMenu.parent" @click="openObject(rowMenu)" />
          <AppButton v-if="drafts[rowMenu.key]" label="Discard task changes" icon="close" :disabled="blocked" @click="delete drafts[rowMenu.key]; undo = []; redo = []; $refs.menu.hidePopover()" />
          <AppButton v-else label="Delete task" icon="delete" destructive :disabled="blocked" @click="remove([rowMenu])" /></template>
      </div>
      <div ref="inline" class="task-table-editor task-manager-inline" popover="auto" role="dialog" :aria-label="t('Edit task cell')" @toggle="$event.newState === 'closed' && (inline = null)">
        <template v-if="inlineEditor"><header><strong>{{ t('Edit task cell') }}</strong><AppButton label="Close" icon="close" icon-only @click="closeInline" /></header>
          <TaskWorkspaceEditor immediate :editor="inlineEditor" :busy="blocked" @change="(name, value) => stageRow(inline.key, name, value)" @milestones="$refs.milestones.open()" />
        </template>
      </div>
      <div ref="columnMenu" class="task-table-editor task-manager-menu" popover="auto" :aria-label="t('Column actions')">
        <template v-if="columnMenu"><strong>{{ t(columnMenu.label) }}</strong>
          <AppButton label="Sort ascending" icon="MDI_SORT_ASCENDING" :disabled="busy || !columnMenu.sort" @click="columnSort(false)" /><AppButton label="Sort descending" icon="MDI_SORT_DESCENDING" :disabled="busy || !columnMenu.sort" @click="columnSort(true)" />
          <AppButton label="Group by column" icon="MDI_FORMAT_LIST_GROUP" :disabled="busy || !columnMenu.group" @click="group = columnMenu.group; $refs.columnMenu.hidePopover(); queryChanged()" />
          <AppButton label="No grouping" :disabled="busy" @click="group = 'none'; $refs.columnMenu.hidePopover(); queryChanged()" />
          <AppButton label="Hide column" icon="MDI_EYE_OFF" :disabled="columnMenu.key === 'object'" @click="toggleColumn(columnMenu.key, false); $refs.columnMenu.hidePopover()" />
          <AppButton label="Task columns" icon="MDI_VIEW_COLUMN" @click="openColumns" />
        </template>
      </div>
    </component>
  </Teleport>
  <Teleport to="body">
    <dialog ref="scheduleDialog" class="record-dialog task-manager-editor" :aria-label="t('Edit schedule')" @cancel.prevent="cancelSchedule">
      <header><h2>{{ t('Edit schedule') }}</h2><AppButton label="Close" icon="close" icon-only :disabled="busy" @click="cancelSchedule" /></header>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <form v-if="scheduleEditor" class="record-form" @submit.prevent="applySchedule">
        <label>{{ t('Start date') }}<AppDateField v-model="scheduleEditor.start" label="Start date" :include-time="false" :allow-clear="false" required :disabled="busy || !scheduleEditor.dates" /></label>
        <label>{{ t(workingDays ? 'Duration in working days' : 'Duration in calendar days') }}<input v-model="scheduleEditor.duration" type="number" min="1" max="3650" step="1" required :disabled="busy || !scheduleEditor.dates"></label>
        <AppCheckbox label="Working days only" v-model="workingDays" :disabled="busy || !scheduleEditor.dates" />
        <label v-if="scheduleEditor.progressField">{{ t('Progress') }}<input v-model="scheduleEditor.progress" type="number" min="0" max="100" step="1" :disabled="busy"></label>
        <AppCheckbox v-if="selected.includes(scheduleEditor.key) && selected.length > 1" label="Move selected tasks together" v-model="scheduleEditor.move" :disabled="busy || !scheduleEditor.dates" />
        <footer class="configuration-actions"><AppButton label="Cancel" :disabled="busy" @click="cancelSchedule" /><AppButton label="Apply to draft" icon="check" type="submit" highlighted :disabled="busy || !scheduleEditor.dates && !scheduleEditor.progressField" /></footer>
      </form>
    </dialog>
    <dialog ref="editor" class="record-dialog task-manager-editor" :aria-label="t('Edit task draft')" @cancel.prevent="cancelEdit">
      <header><h2>{{ t(editor?.creating ? 'Create task' : 'Edit selected tasks') }}</h2><AppButton label="Close" icon="close" icon-only :disabled="busy" @click="cancelEdit" /></header>
      <TaskWorkspaceEditor :editor="editor" :busy="busy" @milestones="$refs.milestones.open()" @change="(name, value) => editor.values[name] = value" @enable="(name, checked) => editor.enabled = checked ? [...editor.enabled, name] : editor.enabled.filter(item => item !== name)" @process="edit([], true, $event)" @cancel="cancelEdit" @apply="stageEditor" />
    </dialog>
    <dialog ref="deleteDialog" class="record-dialog" :aria-label="t('Delete selected tasks')" @cancel.prevent="$refs.deleteDialog.close(); deletion = null">
      <header><h2>{{ t('Delete selected tasks') }}</h2><AppButton label="Close" icon="close" icon-only @click="$refs.deleteDialog.close(); deletion = null" /></header>
      <p>{{ t('Select dependencies to delete. Deletion remains pending until Save.') }}</p>
      <section v-for="plan in deletion" :key="plan.task_key"><strong>{{ plan.process }} · {{ plan.task_key }}</strong>
        <AppCheckbox v-for="item in plan.deletion.groups" :key="item.search_type" :label="`${item.title || item.search_type} · ${item.count}`" :translate-label="false" :model-value="plan.related_types.includes(item.search_type)" @update:model-value="plan.related_types = $event ? [...plan.related_types, item.search_type] : plan.related_types.filter(value => value !== item.search_type)" />
      </section><footer class="configuration-actions"><AppButton label="Cancel" @click="$refs.deleteDialog.close(); deletion = null" /><AppButton label="Apply to draft" icon="delete" destructive @click="stageDeletion" /></footer>
    </dialog>
    <dialog ref="rebaseDialog" class="record-dialog" :aria-label="t('Review task conflicts')" @cancel.prevent="$refs.rebaseDialog.close(); rebaseReview = null">
      <header><h2>{{ t('Review task conflicts') }}</h2><AppButton label="Close" icon="close" icon-only @click="$refs.rebaseDialog.close(); rebaseReview = null" /></header>
      <p>{{ t('Review the current server values and your draft. Applying refreshes revisions; Save is still a separate action.') }}</p>
      <section v-for="plan in rebaseReview" :key="plan.task_key || plan.draft_id"><strong>{{ plan.process }} · {{ plan.task_key || plan.search_key }}</strong>
        <dl class="task-conflict-values"><template v-for="(value, name) in plan.data" :key="name"><dt>{{ name }}</dt><dd><span class="muted">{{ t('Server value') }}: {{ plan.task[name] ?? '—' }}</span><br>{{ t('Draft value') }}: {{ value }}</dd></template></dl>
      </section>
      <footer class="configuration-actions"><AppButton label="Cancel" @click="$refs.rebaseDialog.close(); rebaseReview = null" /><AppButton label="Use latest revisions" icon="check" highlighted @click="drafts = Object.fromEntries(rebaseReview.map(plan => [plan.draft_id || plan.task_key, plan])); undo = []; redo = []; $refs.rebaseDialog.close(); rebaseReview = null" /></footer>
    </dialog>
    <NotesPanel ref="notes" :ticket="ticket" :project="project" @saved="load(); $emit('saved')" />
    <Timesheet ref="timesheet" :ticket="ticket" :project="project" :current-user="currentUser" @saved="load(); $emit('saved')" />
    <MilestoneManager ref="milestones" :ticket="ticket" :project="project" @markers="milestoneRecords = $event" @saved="refreshMilestoneCatalog" />
  </Teleport>
  <Teleport v-if="calendarTarget" defer :to="calendarTarget">
    <TaskCalendarView :projection="projection" :year="year" :month="month" :selected-day="filters.day || ''" :busy="blocked || projecting" :projecting="projecting" :error="projectionError || error" :has-more="result?.hasMore"
      @month="changeMonth" @month-value="setMonth" @today="calendarToday" @day="selectDay" @inspect="key => inspect(tasks.find(task => task.key === key))" @milestone="$refs.milestones.open($event)" @load-more="load(false,true)" @tasks="$emit('opened')" />
  </Teleport>
</template>
<style>
.task-manager-results:has(> .task-gantt-view) { display:flex; flex-direction:column; overflow:hidden; }
.task-manager-results > .task-gantt-view { flex:1; height:auto; }
.task-manager-results:has(> .task-gantt-view) > .task-manager-pending-slot { flex:none; }
@media(max-width:700px) {
  .task-manager-toolbar { height:40px; min-height:40px; padding:4px 8px; gap:4px; }
  .task-manager-toolbar > .icon-button,.task-manager-toolbar > .workspace-menu > summary { width:32px; height:32px; min-width:32px; min-height:32px; }
  .task-manager-toolbar > .app-search-field { height:32px; min-height:32px; }
  .task-manager-toolbar > .app-search-field input { height:30px; min-height:30px; }
  .task-manager-toolbar > .task-search-toggle { margin-left:auto; }
  .task-manager > .task-manager-results:has(> .mobile-tasks) { display:flex; flex-direction:column; overflow:hidden; }
  .task-manager-results:has(> .mobile-tasks) > .task-manager-pending-slot { position:relative; flex:none; }
  .task-manager-detail > :is(.task-manager-toolbar,.task-manager-selection,.task-manager-footer) { display:none; }
  .task-manager:has(.mobile-tasks[data-chrome-hidden="true"]):not(.task-manager-detail) > .task-manager-toolbar { display:none; }
}
</style>

