<script>
import { randomId } from './controls/identity.js'
import { markRaw, nextTick } from 'vue'
import { describe as describeMainToolbar, positions as mainToolbarPositions } from '../../src/tactic_stream/shared_ui/shell/main_toolbar.ui.mjs'
import { describe as describeWorkspace } from '../../src/tactic_stream/shared_ui/shell/workspace.ui.mjs'
import { asyncComponent } from './controls/asyncComponent.js'
import { rpc, sessionAction, interfaceDefinition, projectNavigation, projectCatalog, searchConfiguration, navigationLink, requestActivity, resetRequestActivity } from './api.js'
import { t } from './i18n.js'
import AppearanceControls from './features/configuration/AppearanceControls.vue'
import { preferences } from './features/configuration/preferences.js'
import RecordForm from './features/objects/RecordForm.vue'
import ObjectReport from './features/objects/ObjectReport.vue'
import WidgetConfiguration from './features/interface/WidgetConfiguration.vue'
import ConfiguredView from './features/interface/ConfiguredView.vue'
import ObjectOperations from './features/objects/ObjectOperations.vue'
import ObjectAction from './features/objects/ObjectAction.vue'
import RelatedObjects from './features/objects/RelatedObjects.vue'
import AppIcon from './controls/AppIcon.vue'
import AppSwitch from './controls/AppSwitch.vue'
import AdministrationShell from './features/administration/AdministrationShell.vue'
import { administrationSections } from './administration.js'
import AppSelect from './controls/AppSelect.vue'
import AppButton from './controls/AppButton.vue'
import AppMenu from './controls/AppMenu.vue'
import ActionRows from './controls/ActionRows.vue'
import mainMenus from '../../src/tactic_stream/shared_ui/shell/main.menus.json'
import { compose as composeMainMenu } from '../../src/tactic_stream/shared_ui/shell/main.menus.mjs'
import DockWorkspaceFooter from './controls/DockWorkspaceFooter.vue'
import { saveAppearance } from './appearance.js'
import CommitQueue from './features/checkin/CommitQueue.vue'
const FileWorkspace = asyncComponent(() => import('./features/fileWorkspace/FileWorkspaceInspection.vue'))
import DropPlate from './features/checkin/DropPlate.vue'
import Timesheet from './features/objects/Timesheet.vue'
import TaskManager from './features/tasks/TaskManager.vue'
import SectionTabRail from './controls/SectionTabRail.vue'
import { mobile, mobileLayout } from './mobile.js'
import WorkspaceTabs from './controls/WorkspaceTabs.vue'
import NavigationTree from './features/workspace/NavigationTree.vue'
import NavigationDrawer from './features/workspace/NavigationDrawer.vue'
import ProjectCreation from './features/projects/ProjectCreation.vue'
import ProjectChooser from './features/projects/ProjectChooser.vue'
import ItemPreview from './controls/ItemPreview.vue'
import SearchLibrary from './features/workspace/SearchLibrary.vue'
import SearchResultMenu from './features/workspace/SearchResultMenu.vue'
import * as SearchMenus from '../../src/tactic_stream/shared_ui/features/search/menus.ui.mjs'
import UserProfile from './features/users/UserProfile.vue'
import QuickFilterEditor from './features/workspace/QuickFilterEditor.vue'
import SearchQuickFilters from './features/workspace/SearchQuickFilters.vue'
import FieldFilter from './features/workspace/FieldFilter.vue'
import DockWorkspace from './features/workspace/DockWorkspace.vue'
const DescriptionEditor = asyncComponent(() => import('./features/objects/DescriptionEditor.vue'))
const SnapshotBrowser = asyncComponent(() => import('./features/objects/SnapshotBrowser.vue'))
const KnowledgeBase = asyncComponent(() => import('./features/knowledge/KnowledgeBase.vue'))
import TagCloud from './features/workspace/TagCloud.vue'
import WorkspaceSearch from './features/workspace/WorkspaceSearch.vue'
import SearchFooter from './features/workspace/SearchFooter.vue'
import SearchHeader from './features/workspace/SearchHeader.vue'
import { searchFields, searchTab, readWorkspace, saveWorkspace, navigationEntries } from './features/workspace/workspace.js'
import { defaultResultView, resultViews, resultGroups } from './features/workspace/resultViews.js'
import DebugLog from './features/debug/DebugLog.vue'
import { forgetSessions, setServerDebugContext } from './features/debug/debugLog.js'
import UiPerformance from './features/debug/UiPerformance.vue'
import ScriptShelf from './features/scripts/ScriptShelf.vue'
import ActivityFeed from './features/activity/ActivityFeed.vue'
import MessagesView from './features/messages/MessagesView.vue'
import SystemActivity from './features/activity/SystemActivity.vue'
import { notify, resetNotifications, setNotificationProgress } from './features/activity/notifications.js'
import NotesPanel from './features/objects/NotesPanel.vue'
import FilePreview from './features/objects/FilePreview.vue'
import { addressProject, linkProject, searchLink, workspaceAddress, savedSearchLink } from './features/workspace/links.js'
import { uiPerformance } from './features/debug/uiPerformance.js'
import ConnectionMenu from './features/connection/ConnectionMenu.vue'
import SignIn from './features/connection/SignIn.vue'
import SystemActivityButton from './features/activity/SystemActivityButton.vue'
import NotificationStack from './features/activity/NotificationStack.vue'
import ServerUpdates from './features/connection/ServerUpdates.vue'
import HelpView from './features/help/HelpView.vue'

const Configuration = asyncComponent(() => import('./features/configuration/Configuration.vue'))
const SearchTypes = asyncComponent(() => import('./features/administration/SearchTypes.vue'))
const SchemaEditor = asyncComponent(() => import('./features/administration/SchemaEditor.vue'))
const WorkflowEditor = asyncComponent(() => import('./features/administration/WorkflowEditor.vue'))
const SidebarEditor = asyncComponent(() => import('./features/administration/SidebarEditor.vue'))
const LayoutEditor = asyncComponent(() => import('./features/administration/LayoutEditor.vue'))
const ColumnsEditor = asyncComponent(() => import('./features/administration/ColumnsEditor.vue'))
const RawDatabase = asyncComponent(() => import('./features/administration/RawDatabase.vue'))
const SecurityUsers = asyncComponent(() => import('./features/administration/SecurityUsers.vue'))
const SecurityGroups = asyncComponent(() => import('./features/administration/SecurityGroups.vue'))
const SecurityRules = asyncComponent(() => import('./features/administration/SecurityRules.vue'))

const compactLayout = window.matchMedia('(max-width: 900px)')
const shortcutLayout = mobileLayout

export default {
  components: { ObjectReport, SearchResultMenu, SearchHeader, SearchFooter, SignIn, ActionRows, DockWorkspaceFooter, AdministrationShell, FileWorkspace, DropPlate, KnowledgeBase, SnapshotBrowser, DescriptionEditor, HelpView, UserProfile, MessagesView, NotificationStack, SystemActivityButton, SystemActivity, ServerUpdates, ConnectionMenu, FilePreview, ActivityFeed, NotesPanel, ScriptShelf, UiPerformance, DebugLog, WorkspaceSearch, TagCloud, DockWorkspace, AppearanceControls, Configuration, RecordForm, WidgetConfiguration, ConfiguredView, ObjectOperations, ObjectAction, RelatedObjects, AppIcon, AppSwitch, SearchTypes, SchemaEditor, WorkflowEditor, AppSelect, AppButton, AppMenu, CommitQueue, Timesheet, TaskManager, SectionTabRail, WorkspaceTabs, NavigationTree, NavigationDrawer, ProjectCreation, ProjectChooser, ItemPreview, SidebarEditor, SearchLibrary, QuickFilterEditor, SearchQuickFilters, FieldFilter, SecurityGroups, SecurityRules, SecurityUsers, LayoutEditor, ColumnsEditor, RawDatabase },
  provide() { return {
    checkinDescription: () => this.$refs.description?.pinnedValue() || '',
    queueCheckin: values => { this.$refs.commitQueue.enqueue(values); this.openCommitQueue() },
    openObjectTab: (key, project) => this.openRichLink(key, false, project, false),
    openTaskManager: (record, process, filters, taskKey) => this.canAdminister ? this.$refs.taskManager.openForObjects(record, process, filters, taskKey) : this.showWorkspaceNotice('Access denied'),
    openTaskInspector: (record, cell, process, taskKey, source) => this.openTaskInspector(record, cell, process, taskKey, source),
    openTableCheckin: (record,cell,project) => this.openTableCheckin(record,cell,project),
    openTableSecurity: code => this.openTableSecurity(code),
    openTablePort: (command,record) => this.openTablePort(command,record),
    openScriptEditor: path => this.openScriptEditor(path),
    openHelp: topic => this.$refs.help.open(topic),
    openUserProfile: login => this.$refs.userProfile.open(login),
    openSnapshotBrowser: (record, process, project = this.workspaceProject) => {
      this.snapshotTarget = { project, key:record.__search_key__, process }
      this.openDock('snapshot'); this.$refs.docks.show('snapshot')
    },
    openWorkHours: (mode, task, project) => this.openWorkHours(mode, task, project),
    currentLogin: () => this.session?.login || '',
  } },
  data() {
    return {
      toolbarWidth: window.innerWidth,
      sessionRequest: 0,
      workHoursProjects: { week:'', report:'', cost:'' },
      descriptionMounted: false, descriptionTarget: null, tableCheckinTarget:null, snapshotMounted:false, snapshotTarget:null, snapshotActive:false,
      inspectorSource: null, inspectorTarget: null, inspectorRequest: 0, taskInspectorActive: false, searchEditorActive: false, inspectorReturn: 'results',
      knowledgeMounted:false, knowledgeActive:false, knowledgeTarget:'',
      attachmentLocation: null,
      scriptEditorComponent: null, scriptEditorLoading: false,
      pingBusy: false, activityUnread: 0, messageUnread: 0, shelfOpen: false, layoutsFocus: null, columnsFocus: null, refreshAfterAdministration: false, version: '', ready: false, restoringSession: true, login: '', password: '', session: null,
      navigationLink: '', openingLink: false, linkRequest: 0, routeReady: false, searchStateTab: null,
      projects: [], types: [], userIdentity: null, project: '', type: '',
      columns: {}, rows: [], searchText: '', filterField: '', filterValue: '', sortField: '', sortDirection: 'asc',
      page: 0, pageSize: 50, pageNumber: 1, hasNext: false, totalCount: null, nextOffset: 0, loadedQuery: null, busy: false, signingIn: false, error: '',
      loadingMode: 'pages', loadingMore: false, paginationArmed: false,
      requestId: 0, detailRequest: 0, detail: null, section: 'data', navigationOpen: false,
      compact: compactLayout.matches, showRetired: false, selectedKeys: [], focusedKey:'',
      interfaceConfig: null, view: 'table', configuredView: false, viewTitle: '',
      connectionOnline: true, compactShortcuts: shortcutLayout.matches, serverBatch: null, updatesError: '', updatesTasksOpen: false, taskCalendarActive: false, updatesNotesOpen: false, updatesActivityOpen: false,
      canAdminister: false, administrationOpen: false, administrationSection: 'types', administrationVisited: [], administrationInstances: {}, administrationPresentation: {mobile:true,library:null}, pendingWorkflow:null, administrationCollapsed: false, workspaceSelection: null, configurationReturnSection: 'data',
      checkins: [],
      workspaceProjects: {}, workspaceProject: '', dockMenuTarget: null, mobileViewMenuTarget: null, mobileSearchOpen:false,
      navigationByProject: {}, navigationErrors: {}, navigationRequests: {},
      sidebarSearch: null,
      reloadingCache: false,
      searchOrganization: { processes: [], statuses: {} }, searchOrganizationKey: '',
      filterRecords: [], savedSearch: '', quickSelections: {}, quickLayout: null, scopeKey: '', presetOrderBys: [],
      selectedTags: [], tagColumn: '',
      searchRelation: 'contains',
      resultMode: defaultResultView, groupMode: 'none', resultState: {},
    }
  },
  computed: {
    mainMenuContext() {
      return {
        platform: 'stream',
        compact: this.compactShortcuts,
        canAdminister: this.canAdminister,
        busy: this.busy,
        openingLink: this.openingLink,
        reloadingCache: this.reloadingCache,
        hasSearch: !!this.activeSearchTab,
        scriptLoading: this.scriptEditorLoading,
        unread: this.messageUnread,
        fileProject: this.fileProject
      }
    },
    configurationActions() { return composeMainMenu(mainMenus.configuration, this.mainMenuContext) },
    accountActions() { return composeMainMenu(mainMenus.user, this.mainMenuContext) },
    mainToolbar() { return describeMainToolbar({width:this.toolbarWidth,compact:this.compactShortcuts,progressReveal:this.activityProgress ? 1 : 0,dccClient:false}) },
    mainToolbarControls() { return mainToolbarPositions(this.mainToolbar) },
    workspaceStyle() {
      const scene = describeWorkspace(this.toolbarWidth, window.innerHeight, this.compactShortcuts)
      return { gridTemplateAreas: scene.grid.areas, gridTemplateColumns: scene.grid.columns, gridTemplateRows: scene.grid.rows }
    },
    mobileSearchContext() { return [this.workspaceProject,this.activeWorkspaceSection?.id,this.activeSearchTab?.id].join(':') },
    serverDebugContext() { return {ticket:this.session?.ticket,project:this.workspaceProject} },
    updateSubscription() {
      const types = [
        'sthpw/message', 'sthpw/message_log', 'sthpw/subscription',
        'config/widget_config', 'config/custom_script', 'config/trigger', 'config/process',
        'sthpw/project', 'sthpw/schema', 'sthpw/search_object', 'sthpw/pipeline',
        'sthpw/login', 'sthpw/login_group', 'sthpw/login_in_group',
      ]
      if (this.activeSearchTab) types.push(this.workspaceView.type.split('?')[0], 'sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file', 'sthpw/connection', 'sthpw/status_log')
      if (this.updatesTasksOpen || this.updatesNotesOpen || this.taskInspectorActive) types.push('sthpw/task', 'sthpw/note', 'sthpw/work_hour')
      const activity = this.updatesActivityOpen || preferences.global.activityNotifications
      return { channels: ['messages', 'reactions', ...(activity ? ['activity'] : []), ...(types.length ? ['cache'] : [])], search_types: [...new Set(types.filter(Boolean))].sort() }
    },
    defaultLoadingMode() { return preferences.checkin.loadingMode },
    activityProgress() {
      if (this.reloadingCache) return 'Reloading cacheвЂ¦'
      if (this.busy || this.loadingMore || (!this.administrationOpen && this.activeSearchTab && !this.activeSearchTab.loaded && !this.error)) return this.loadingMore ? 'Loading moreвЂ¦' : 'Loading dataвЂ¦'
      return this.pingBusy ? 'Pinging TACTIC server' : requestActivity.pending.findLast(row => row.ticket === this.session?.ticket)?.message || ''
    },
    browserTitle() { return [this.activeSearchTab ? this.searchTabTitle(this.activeSearchTab) : '', this.currentProject?.title || '', t('TACTIC Stream')].filter(Boolean).join(' вЂ” ') },
    resultViews() { return resultViews },
    resultGroups() { return resultGroups },
    searchGroupMenuModel() {
      const key = [this.project, this.displayedSearchTab?.id, this.type].join('|')
      return { mode: this.groupMode, busy: this.busy,
        processes: key === this.searchOrganizationKey ? this.searchOrganization.processes : [] }
    },
    searchFilterMenuModel() { return {presets:this.$refs.searchLibrary?.catalog?.presets || [],selected:this.savedSearch,busy:this.$refs.searchLibrary?.busy,error:this.$refs.searchLibrary?.error} },
    searchSortMenuModel() { return {defaultOrder:true,mode:SearchMenus.sorts.find(item=>item.column===this.sortField&&item.direction===this.sortDirection)?.value || '',column:this.sortField,direction:this.sortDirection,busy:this.busy,columns:this.columnNames.map(value=>({value,label:value}))} },
    workspaceView() { return this.workspaceSelection || this },
    currentProject() { return this.projects.find(item => item.code === this.workspaceView.project) },
    fileProject() { return this.projects.find(item => item.code === this.workspaceProject)?.project_mode === 'file_project' },
    projectInitials() { return (this.currentProject?.title || this.workspaceView.project).replaceAll('_', ' ').split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]).join('').toUpperCase() },
    administrationSections() { return administrationSections },
    activeAdministration() { return administrationSections.find(item => item.id === this.administrationSection) },
    administrationEditors() { return Object.values(this.administrationInstances) },
    administrationLocked() {
      return this.administrationEditors.some(editor => editor.dirty || editor.busy || editor.uncertain || editor.previewValidating || editor.$refs.naming?.dirty || editor.$refs.naming?.busy || editor.$refs.naming?.uncertain || editor.$refs.rules?.active || editor.creating || editor.$refs.deletion?.active)
    },
    administrationProjectOptions() { return this.projects.map(item => ({ value: item.code, label: item.title || item.code })) },
    administrationSectionOptions() { return administrationSections.map(item => ({ value: item.id, label: item.title })) },
    administrationColumns() {
      if (this.section !== 'administration' || this.sidebarSearch) return null
      return {
        users: ['code', 'login', 'display_name', 'first_name', 'last_name', 'email', 'department', 's_status'],
        groups: ['code', 'login_group', 'description', 'access_level', 'project_code', 'sub_groups'],
        rules: ['code', 'login_group', 'access_level', 'project_code', 'access_rules'],
      }[this.administrationSection] || null
    },
    navigationVisible() { return this.navigationOpen },
    fallbackNavigation() {
      return this.publicTypes.map(item => ({ key: item.search_type, kind: 'link',
        title: item.title || item.search_type.split('/').pop(), search_type: item.search_type,
        supported: true, icon: 'link' }))
    },
    activeWorkspace() { return this.workspaceProjects[this.workspaceProject] },
    openSections() { return this.activeWorkspace?.sections || [] },
    activeWorkspaceSection() { return this.openSections.find(item => item.id === this.activeWorkspace.current) },
    activeSearchTab() { return this.activeWorkspaceSection?.tabs.find(item => item.id === this.activeWorkspaceSection.current) },
    displayedSearchTab() { return this.section === 'data' ? this.searchStateTab : null },
    searchTabs() { return (this.activeWorkspaceSection?.tabs || []).map(tab => ({ ...tab, title: this.searchTabTitle(tab) })) },
    closedSearchTabs() { return (this.activeWorkspaceSection?.closedTabs || []).map(tab => ({ ...tab, title: this.searchTabTitle(tab) })) },
    retainedSearchTabs() {
      return Object.entries(this.workspaceProjects).flatMap(([project, workspace]) =>
        workspace.sections.flatMap(section => [...section.tabs, ...section.closedTabs].map(tab => ({ project, section, tab }))))
    },
    selectedRecords() { return this.rows.filter(record => this.selectedKeys.includes(record.__search_key__)) },
    selectedType() { return this.types.find(item => item.search_type === this.type) },
    columnNames() { return Object.keys(this.columns).filter(name => !name.startsWith('_tmp')) },
    viewLinks() {
      return navigationEntries(this.navigationByProject[this.workspaceProject]?.entries || [], this.types).filter(item=>this.types.find(type=>type.search_type===item.search_type)?.__record_read__?.available !== false)
    },
    publicTypes() { return this.types.filter(item=>item.__record_read__?.available !== false && (!item.__record_read__?.project_mode || item.__record_read__.project_mode === this.currentProject?.type)) },
    shelfContext() {
      const flatten = entries => entries.flatMap(entry => [entry, ...flatten(entry.children || [])])
      const entry = flatten(this.viewLinks).find(item => item.key === this.activeWorkspaceSection?.navigationKey)
      return { entryKey: entry?.search_type && entry.name ? entry.search_type.split('?')[0] + '@' + entry.name : '', preset: entry?.display?.options?.script_shelf || '', title: this.activeWorkspaceSection?.title || '' }
    },
    configuredNavigation() { return this.navigationByProject[this.workspaceProject]?.configured === true && !(!this.viewLinks.length && this.publicTypes.some(item=>item.__record_read__?.command)) },
    ticket() { return { ticket: this.session.ticket, project: this.project, language: 'python' } },
    continuous() { return this.section === 'data' && !this.administrationOpen && this.loadingMode === 'infinite' },
    rowRange() {
      const first = this.continuous ? 0 : this.page * this.pageSize
      return this.rows.length ? `${first + 1}вЂ“${first + this.rows.length}` : '0'
    },
    pageCount() { return this.totalCount === null ? null : Math.max(1, Math.ceil(this.totalCount / this.pageSize)) },
    pageNumbers() {
      const count = this.pageCount || this.page + 1
      const start = Math.max(1, Math.min(this.page - 1, count - 4))
      return Array.from({ length: Math.min(5, count) }, (_, index) => start + index)
    },
  },
  watch: {
    mobileSearchContext() { this.mobileSearchOpen = false },
    serverDebugContext: { handler(value) { setServerDebugContext(value) }, immediate:true, flush:'sync' },
    defaultLoadingMode(mode) {
      this.loadingMode = mode; this.page = 0
      if (this.session) { try { localStorage.setItem('tactic_stream.loadingMode.' + this.session.login,mode) } catch { /* The active session still uses the applied mode. */ } }
      if (this.activeSearchTab) this.loadRows()
    },
    page(value) { this.pageNumber = value + 1 },
    browserTitle: { handler(value) { document.title = value }, immediate: true },
    session: { handler() { resetNotifications(); resetRequestActivity(); this.inspectorSource = this.inspectorTarget = null; this.inspectorRequest++ }, flush: 'sync' },
    project: { handler() { resetRequestActivity() }, flush: 'sync' },
    workspaceProject: { handler() { resetRequestActivity(); this.inspectorSource = this.inspectorTarget = null; this.inspectorRequest++ }, flush: 'sync' },
    activityProgress(value) { setNotificationProgress(this.session ? value : '') },
    updatesError(value) { if (value) notify('error', value, '', 'server') },
    error(value) { if (value && this.session) notify('error', value, '', 'server') },
  },
  async created() {
    try {
      const response = await fetch('/health', { cache: 'no-store' })
      const health = await response.json()
      this.version = health.version
      this.ready = health.database_initialized
      this.login = localStorage.getItem('tactic_stream.lastLogin') || ''
      const saved = JSON.parse(localStorage.getItem('tactic_stream.session') || sessionStorage.getItem('tactic_stream.session') || 'null')
      if (saved && typeof saved.ticket === 'string' && typeof saved.login === 'string') {
        this.session = saved
        this.login = saved.login
        this.project = saved.project || ''
        this.type = saved.type || ''
        this.view = saved.view || 'table'
        this.configuredView = saved.configuredView === true
        await this.bootstrap()
      }
    } catch (error) { this.fail(error) }
    finally { this.restoringSession = false }
  },
  mounted() {
    window.addEventListener('resize', this.updateToolbarSize)
    compactLayout.addEventListener('change', this.resizeLayout)
    shortcutLayout.addEventListener('change', this.resizeLayout)
    window.addEventListener('pagehide', this.persistWorkspace)
    window.addEventListener('beforeunload', this.persistWorkspace)
    window.addEventListener('popstate', this.openBrowserLocation)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.updateToolbarSize)
    resetNotifications()
    resetRequestActivity()
    uiPerformance.reset()
    compactLayout.removeEventListener('change', this.resizeLayout)
    shortcutLayout.removeEventListener('change', this.resizeLayout)
    window.removeEventListener('pagehide', this.persistWorkspace)
    window.removeEventListener('beforeunload', this.persistWorkspace)
    window.removeEventListener('popstate', this.openBrowserLocation)
    this.linkRequest++
  },
  methods: {
    async invokeMainMenu(command) {
      for (const name of ['settingsMenu', 'accountMenu']) {
        const menu = this.$refs[name]
        if (menu?.open) menu.close(true)
      }
      await nextTick()
      const actions = {
        open_configuration: () => this.showConfiguration(),
        show_administration: () => this.showAdministration(),
        save_preferences: () => this.savePreferences(),
        reload_cache: () => this.reloadCache(),
        apply_view_to_all_tabs: () => this.applyViewToAllTabs(),
        reset_workspace_layout: () => this.$refs.docks.reset(),
        open_script_editor: () => this.openScriptEditor(),
        show_debug_log: () => this.$refs.debugLog.open(),
        show_ui_performance: () => this.$refs.uiPerformance.open(),
        open_script_shelf: () => this.$refs.scriptShelf.open(),
        show_commit_queue: () => this.openCommitQueue(),
        show_work_hours: () => this.openWorkHours(),
        show_tasks: () => this.$refs.taskManager.open(),
        create_project: () => this.showProjectCreation(),
        show_help: () => this.$refs.help.open(),
        mobile_help: () => this.$refs.help.open('mobile'),
        show_user_profile: () => this.$refs.userProfile.open(),
        show_users: () => this.$refs.userProfile.open(this.session.login, true),
        show_messages: () => this.$refs.messages.open(),
        sign_out: () => this.signOut()
      }
      actions[command]?.()
    },
    renameCurrentSearchTab(value) {
      if (!this.activeSearchTab) return
      this.activeSearchTab.title = String(value || '').trim() || this.activeWorkspaceSection?.title || ''
      this.persistWorkspace()
    },
    searchFilterCommand(command) {
      if (command === 'advanced_search') this.openAdvancedSearch()
      else if (command === 'filter_processes') this.openProcessVisibility()
      else if (command === 'refresh_presets') this.$refs.searchLibrary.ensureCatalog(true)
      else if (command.startsWith('preset:')) {
        const preset = this.$refs.searchLibrary.presetValue(command.slice(7))
        if (preset) this.applySearchLibrary(preset)
      }
    },
    searchSortCommand(command) {
      if (command === 'default' && !this.busy) {
        this.sortField = ''
        this.presetOrderBys = []
        this.page = 0
        this.loadRows()
        return
      }
      const item = SearchMenus.sorts.find(item => item.value === command)
      const match = /^column:([A-Za-z_][A-Za-z0-9_]*):(asc|desc)$/.exec(command)
      const column = item?.column || match?.[1]
      if (this.busy || !this.columnNames.includes(column)) return
      this.sortField = column
      this.sortDirection = item?.direction || match[2]
      this.presetOrderBys = []
      this.page = 0
      this.loadRows()
    },
    openProcessVisibility() {
      this.$refs.taskViews?.find(view=>view.workspaceId===this.displayedSearchTab?.id&&view.project===this.project)?.$refs.presentation?.openProcessVisibility()
    },
    openSearchTags(event) {
      const source = this.compactShortcuts ? event.currentTarget : null
      const returnTarget = this.compactShortcuts ? this.$refs.resultActions.$el.querySelector('summary') : null
      this.$refs.viewMenu.open = false
      this.$refs.tagCloud.open(source, returnTarget)
    },
    searchFooterEvent(action) {
      if (action.type === 'page') this.goToPage(action.value)
      else if (action.type === 'previous') this.changePage(-1)
      else if (action.type === 'next') this.changePage(1)
      else if (action.type === 'size') this.changePageSize(action.value)
      else if (action.type === 'mode') this.setLoadingMode(action.value)
      else if (action.type === 'queue') this.openCommitQueue()
      else if (action.type === 'create') this.createRecord()
    },
    t,
    updateToolbarSize() { this.toolbarWidth = window.innerWidth },
    mainToolbarStyle(id) {
      const control = this.mainToolbarControls[id]
      return {position:'absolute',left:control.x+'px',top:control.y+'px',width:control.width+'px',height:control.height+'px',display:control.visible===false?'none':undefined}
    },
    layoutSaved() {this.refreshAfterAdministration=true},
    changeResultView(mode) {
      if (!resultViews.some(item => item.value === mode) || !this.canCloseTaskViews(this.workspaceProject, [this.activeSearchTab?.id])) return
      this.resultMode = mode
      this.persistWorkspace()
    },
    prepareResultGroups() {
      const presentation = this.$refs.taskViews?.find(view =>
        view.workspaceId === this.displayedSearchTab?.id && view.project === this.project)?.$refs.presentation
      if (!presentation) return
      this.searchOrganization = presentation.organization
      this.searchOrganizationKey = [this.project, this.displayedSearchTab?.id, this.type].join('|')
      presentation.ensureOrganization()
    },
    resultOrganizationChanged(entry, organization) {
      if (entry.tab !== this.displayedSearchTab || entry.project !== this.project) return
      this.searchOrganization = organization
      this.searchOrganizationKey = [this.project, entry.tab.id, this.type].join('|')
    },
    changeResultGroup(mode) {
      if (!resultGroups.some(item => item.value === mode) && !(mode.startsWith('task_status:') && this.searchGroupMenuModel.processes.some(row=>'task_status:'+row.key===mode))) return
      this.groupMode = mode
      if (mode !== 'none' && this.resultMode === 'tiles') this.resultMode = 'continious'
      this.persistWorkspace()
    },
    resultStateChanged(entry, state) {
      entry.tab.state.resultState = state
      if (entry.tab === this.displayedSearchTab) this.resultState = state
      this.persistWorkspace()
    },
    dismissMenus(event) {
      if (event.type === 'keydown' && this.navigationOpen) { this.closeNavigation(); return }
      if (event.type === 'keydown' && this.$refs.topbar?.querySelector('select:open')) return
      for (const menu of this.$refs.workspace?.querySelectorAll('.topbar details[open], .workspace-menu[open], .search-filters[open]') || []) {
        if (menu.dataset.menuOwner === 'control') continue
        if (event.type === 'keydown' || !menu.contains(event.target)) {
          menu.open = false
          if (event.type === 'keydown') { menu.querySelector('summary').focus(); event.stopPropagation() }
        }
      }
    },
    menuToggled(event) {
      if (!event.target.open || !event.target.matches('.topbar details, .workspace-menu, .search-filters')) return
      if (event.target.closest('.topbar')) this.closeNavigation(false)
      for (const menu of this.$refs.workspace?.querySelectorAll('.topbar details[open], .workspace-menu[open], .search-filters[open]') || []) {
        if (menu !== event.target && !menu.contains(event.target)) menu.open = false
      }
    },
    resizeLayout() {
      this.closeNavigation(false)
      this.compact = compactLayout.matches
      this.compactShortcuts = shortcutLayout.matches
    },
    openNavigation() {
      if (this.navigationOpen) return
      this.$refs.navigation.open(this.$refs.topbar.getBoundingClientRect().height)
      this.navigationOpen = true
      this.loadNavigation()
    },
    toggleNavigation() {
      if (this.navigationOpen) this.closeNavigation()
      else this.openNavigation()
    },
    closeNavigation(restoreFocus = true) {
      this.$refs.navigation?.close(restoreFocus)
      this.navigationOpen = false
    },
    async openScriptEditor(path) {
      if (this.scriptEditorLoading) return
      const session = this.session
      const project = this.workspaceProject
      const current = () => this.session === session && this.workspaceProject === project
      this.scriptEditorLoading = true
      try {
        const module = await import('./features/scripts/ScriptEditor.vue')
        if (!current()) return
        this.scriptEditorComponent ||= markRaw(module.default)
        await nextTick()
        if (!current()) return
        await this.$refs.scriptEditor.open(typeof path === 'string' ? path : '')
      } catch (error) { if (current()) notify('error', error.message, '', 'script-editor') }
      finally { this.scriptEditorLoading = false }
    },
    async showConfiguration() {
      if (this.busy || this.openingLink) return
      if (this.$refs.rules && !this.$refs.rules.canLeave()) return
      if (this.$refs.columnsEditor && !this.$refs.columnsEditor.canLeave()) return
      if (this.$refs.users && !this.$refs.users.canLeave()) return
      if (this.$refs.groups && !this.$refs.groups.canLeave()) return
      if (this.$refs.searchTypes && !this.$refs.searchTypes.canLeave()) return
      if (this.$refs.workflow && !this.$refs.workflow.canLeave()) return
      if (this.$refs.sidebar && !this.$refs.sidebar.canLeave()) return
      if (this.$refs.schema && !this.$refs.schema.canLeave()) return
      this.$refs.settingsMenu.open = false
      this.closeNavigation()
      if (this.loadingMore) { this.requestId++; this.loadingMore = false }
      this.captureSearchTab()
      this.configurationReturnSection = this.section
      this.section = 'configuration'
      await nextTick()
      this.$refs.configurationDialog.show()
    },
    async openTableSecurity(code) {
      if (!this.canAdminister || this.administrationLocked) throw new Error('Apply or discard unsaved changes first')
      const session = this.session, project = this.workspaceProject
      const current = () => {
        if (this.session !== session || this.workspaceProject !== project || !this.canAdminister)
          throw new Error('Connection context changed. Close this form and reopen it before saving.')
      }
      await SecurityRules.__asyncLoader()
      current()
      if (this.administrationOpen) this.selectAdministration('rules')
      else await this.showAdministration('rules')
      await nextTick()
      current()
      if (!this.$refs.rules) throw new Error('Global Permissions are unavailable in this host')
      this.$refs.rules.focusGroup(code)
    },
    async openTablePort(command,record) {
      const options = command.options || {}, kind = command.type
      const session=this.session, project=this.workspaceProject
      const current=()=>{if(this.session!==session || this.workspaceProject!==project || !this.canAdminister) throw new Error('Connection context changed. Close this form and reopen it before saving.')}
      if (!this.canAdminister) throw new Error('Access denied')
      if (kind === 'schedule') { await this.$refs.taskManager.openForUser({login:options.login}); return }
      if (kind === 'script') { await this.openScriptEditor(options.script_path); return }
      if (kind === 'work-hours') {
        await this.openWorkHours('week', {scope:{search_key:record.__search_key__, task_key:options.taskKey, process:options.process}}, project, options.actionDay)
        return
      }
      if (['task-details','add-task','work','table-schedule'].includes(kind)) {
        const taskKey = options.actionTaskKey || options.taskSearchKey || ''
        await this.$refs.taskManager.openForObjects(record,options.actionProcess || options.process || '',{},taskKey.startsWith('sthpw/task?') ? taskKey : '')
        if (kind === 'add-task') await this.$refs.taskManager.edit([],true,'','inline')
        if (kind === 'work') await this.openTableCheckin(record,options,this.workspaceProject)
        if (kind === 'table-schedule') this.$refs.taskManager.view = 'gantt'
        return
      }
      if (kind === 'workflow') {
        if(options.search_key !== record.__search_key__) throw new Error('The configured table target is unavailable')
        if(this.busy || this.openingLink || this.administrationLocked || this.pendingWorkflow || this.administrationInstances.workflow?.busy) throw new Error('Apply or discard unsaved changes first')
        await WorkflowEditor.__asyncLoader(); current()
        if(this.administrationLocked)throw new Error('Apply or discard unsaved changes first')
        this.pendingWorkflow={identity:record.code}
        if(this.administrationOpen)this.selectAdministration('workflow')
        else await this.showAdministration('workflow')
        current(); await nextTick()
        if(!this.administrationOpen){this.pendingWorkflow=null;throw new Error('Apply or discard unsaved changes first')}
        const editor=this.administrationInstances.workflow
        if(this.pendingWorkflow && editor)this.runWorkflowRequest(editor)
        return
      }
      if (!['users','groups','schema'].includes(kind)) throw new Error('Unsupported table window: ' + kind)
      if (this.administrationLocked) throw new Error('Apply or discard unsaved changes first')
      const components = {users:SecurityUsers,groups:SecurityGroups,schema:SchemaEditor}
      await components[kind].__asyncLoader(); current()
      if (this.administrationOpen) this.selectAdministration(kind)
      else await this.showAdministration(kind)
      await nextTick()
      current()
      const editor = this.$refs[kind]
      if (!editor) throw new Error('This editor is available on a desktop screen.')
      if (['users','groups','workflow'].includes(kind) && options.search_key !== record.__search_key__) throw new Error('The configured table target is unavailable')
      if (kind === 'users') editor.focus(record.login)
      else if (kind === 'groups') editor.focus(record.code)
    },
    async showAdministration(section = null) {
      if (mobile.value) { this.showWorkspaceNotice('This editor is available on a desktop screen.'); return }
      if (!this.canAdminister || this.busy || this.administrationOpen) return
      if (section !== 'columns') this.columnsFocus = null
      this.$refs.settingsMenu.open = false
      this.closeNavigation()
      this.captureSearchTab()
      this.workspaceSelection = Object.fromEntries(['section', 'project', 'type', 'view', 'viewTitle',
        'configuredView', 'searchText', 'searchRelation', 'filterField', 'filterValue', 'sortField', 'sortDirection', 'page', 'pageSize',
        'columns', 'rows', 'hasNext', 'totalCount', 'nextOffset', 'loadedQuery', 'showRetired', 'selectedKeys', 'interfaceConfig', 'error'].map(key => [key, this[key]]))
      Object.assign(this.workspaceSelection, Object.fromEntries(['filterRecords', 'savedSearch', 'quickSelections', 'quickLayout', 'scopeKey', 'presetOrderBys'].map(key => [key, this[key]])))
      Object.assign(this.workspaceSelection, { selectedTags: this.selectedTags, tagColumn: this.tagColumn })
      this.refreshAfterAdministration = false
      this.administrationOpen = true
      this.selectAdministration(typeof section === 'string' ? section : this.administrationSection)
      await nextTick()
      this.$refs.administrationDialog.showModal()
    },
    administrationCommand(command) {
      if(command.type==='section')this.selectAdministration(command.value)
      else if(command.type==='project'&&!this.administrationLocked){this.project=command.value;this.switchProject()}
      else if(command.type==='help')this.$refs.help.open(command.topic)
      else if(command.type==='close')this.closeAdministrationClean()
    },
    schemaNodeWorkflows(identity) {
      const schema=this.administrationInstances.schema
      if(!schema||schema.document?.newTypes?.[identity]||!schema.metadata.searchTypes.some(row=>row.identity===identity))return
      this.openAdministrationWorkflow({searchType:identity,resolveExisting:true},'schema')
    },
    openAdministrationWorkflow(values,source='types') {
      const owner=this.administrationInstances[source],workflow=this.administrationInstances.workflow
      const creator=source==='schema'?owner?.$refs.typeCreator:null
      if(creator?.dirty||creator?.busy){creator.error='Save the Search Type before creating its workflow';return false}
      if(this.pendingWorkflow||workflow&&(workflow.busy||workflow.uncertain||workflow.$refs.rules?.active||workflow.dirty&&(!values.identity||workflow.identity!==values.identity))){
        if(owner)owner.error='Finish the current workflow edit before opening another pipeline'
        return false
      }
      if(creator&&owner.creating)owner.closeCreator()
      this.pendingWorkflow=values
      this.selectAdministration('workflow')
      if(workflow)this.runWorkflowRequest(workflow)
      return true
    },
    administrationWorkflowMounted(editor) {
      this.administrationInstances.workflow=editor
      if(this.pendingWorkflow)this.runWorkflowRequest(editor)
      else editor.open()
    },
    runWorkflowRequest(editor) {
      const request=this.pendingWorkflow;this.pendingWorkflow=null
      if(request.resolveExisting)editor.openSearchType(request.searchType)
      else if(!request.identity||editor.identity!==request.identity||!editor.document)editor.open(request.identity||'',request.identity?'':request.searchType)
    },
    workflowAdministrationSaved() {
      this.refreshTypes();this.administrationInstances.types?.workflowSaved()
    },
    selectAdministration(id) {
      const item = administrationSections.find(item => item.id === id)
      if (!item || !this.canAdminister) return
      this.closeNavigation()
      this.administrationSection = id
      if (!this.administrationVisited.includes(id)) this.administrationVisited.push(id)
      this.section = 'administration'
      this.type = item.type
      this.searchText = ''
      this.view = 'table'
      this.viewTitle = ''
      this.configuredView = false
      this.filterField = item.field || (id === 'schema' ? 'code' : id === 'workflow' ? 'project_code' : '')
      this.filterValue = item.value || (['schema', 'workflow'].includes(id) ? this.project : '')
      this.sortField = ''
      this.sortDirection = 'asc'
      this.page = 0
      this.columns = {}
      this.rows = []
      this.selectedTags = []; this.tagColumn = ''
      this.searchRelation = 'contains'
      this.filterRecords = []; this.savedSearch = ''; this.quickSelections = {}; this.quickLayout = null; this.scopeKey = ''; this.presetOrderBys = []
      if (['types', 'schema', 'workflow', 'columns', 'layouts', 'raw', 'sidebar', 'users', 'groups', 'rules'].includes(id)) {
        this.requestId++
        this.busy = false
      } else this.loadRows()
    },
    leaveAdministration() {this.$refs.administrationShell?.dispatch({type:'close'})},
    closeAdministrationClean() {
      if (this.$refs.adminTaskView && !this.$refs.adminTaskView.canLeave()) return
      for (const [section, editor] of Object.entries(this.administrationInstances)) {
        if (!editor.canLeave()) { this.selectAdministration(section); return }
      }
      if (this.busy) return
      this.$refs.administrationDialog.close()
    },
    async administrationClosed() {
      const tab = this.activeSearchTab, ticket = this.session?.ticket
      const top = tab?.scrollTop || 0, left = tab?.scrollLeft || 0
      const refresh = this.refreshAfterAdministration && this.session
      this.requestId++
      if (this.workspaceSelection) Object.assign(this, this.workspaceSelection)
      this.workspaceSelection = null
      this.administrationOpen = false
      this.administrationVisited = []
      this.administrationInstances = {}
      this.pendingWorkflow = null
      if (refresh) this.reloadWorkspace()
      this.refreshAfterAdministration = false
      await nextTick()
      if (ticket !== this.session?.ticket || tab !== this.activeSearchTab || this.administrationOpen) return
      if (!refresh && this.$refs.results) { this.$refs.results.scrollTop = top; this.$refs.results.scrollLeft = left }
      if (this.session) this.saveSession()
      this.$refs.settingsMenu?.focusTrigger()
    },
    async signOut() {
      const session = this.session
      if (!session) return
      if (this.$refs.scriptShelf && !this.$refs.scriptShelf.canLeave()) return
      if (!this.canCloseTaskViews()) return
      if (this.$refs.adminTaskView && !this.$refs.adminTaskView.canLeave()) return
      if (!this.$refs.commitQueue.canLeave()) return
      if (!this.$refs.dropPlate.canLeave()) return
      if (this.$refs.description && !this.$refs.description.canLeave()) return
      if (this.$refs.rules && !this.$refs.rules.canLeave()) return
      if (this.$refs.columnsEditor && !this.$refs.columnsEditor.canLeave()) return
      if (this.$refs.users && !this.$refs.users.canLeave()) return
      if (this.$refs.groups && !this.$refs.groups.canLeave()) return
      if (this.$refs.searchTypes && !this.$refs.searchTypes.canLeave()) return
      if (this.$refs.workflow && !this.$refs.workflow.canLeave()) return
      if (this.$refs.sidebar && !this.$refs.sidebar.canLeave()) return
      if (this.$refs.schema && !this.$refs.schema.canLeave()) return
      if (this.busy) return
      this.busy = true
      try {
        await sessionAction('logout', session.ticket)
        if (session !== this.session) return
        this.logout()
        history.replaceState(null, '', '/')
      } catch (error) { if (session === this.session) this.fail(error) }
      finally { if (session === this.session) this.busy = false }
    },
    saveSession() {
      if (!this.session) return
      try {
        const selection = this.section === 'administration' ? this.workspaceSelection : this
        const state = { project: selection?.project ?? this.project, type: selection?.type ?? this.type, view: selection?.view ?? this.view, configuredView: selection?.configuredView ?? this.configuredView }
        localStorage.setItem('tactic_stream.session', JSON.stringify({ ...this.session, ...state }))
        localStorage.setItem('tactic_stream.selection.' + this.session.login, JSON.stringify(state))
        localStorage.setItem('tactic_stream.lastLogin', this.session.login)
        sessionStorage.removeItem('tactic_stream.session')
        this.persistWorkspace()
      }
      catch { /* Browser storage may be unavailable; the current session still works. */ }
    },
    async signIn() {
      if (this.signingIn) return
      const request = ++this.sessionRequest, login = this.login.trim()
      this.signingIn = true
      this.error = ''
      try {
        const ticket = await rpc('get_ticket', [login, this.password])
        if (request !== this.sessionRequest) return
        this.password = ''
        this.restoringSession = true
        this.session = { login, ticket }
        try { this.project = JSON.parse(localStorage.getItem('tactic_stream.selection.' + login))?.project || '' }
        catch { this.project = '' }
        await this.bootstrap()
      } catch (error) { if (request === this.sessionRequest) this.fail(error) }
      finally { if (request === this.sessionRequest) { this.signingIn = false; this.restoringSession = false } }
    },
    async bootstrap() {
      const session = this.session
      if (!session) return
      this.routeReady = false
      try { this.loadingMode = localStorage.getItem('tactic_stream.loadingMode.' + this.session.login) || preferences.checkin.loadingMode }
      catch { this.loadingMode = preferences.checkin.loadingMode }
      // Read the registry and project list in the system context first.
      const ticket = { ticket: this.session.ticket, project: 'admin', language: 'python' }
      await rpc('ping', [ticket])
      if (session !== this.session) return
      const [projects, types, identity] = await Promise.all([
        projectCatalog(this.session.ticket),
        rpc('query', [ticket, 'sthpw/search_object'], { order_bys: ['search_type'] }),
        sessionAction('identity', this.session.ticket),
      ])
      if (session !== this.session) return
      this.projects = projects
      this.types = types
      this.userIdentity = identity
      this.canAdminister = identity.administration === true
      if (!projects.some(item => item.code === this.project)) this.project = ''
      if (!types.some(item => item.search_type === this.type)) this.type = ''
      this.workspaceProjects = readWorkspace(this.session.login, projects, types)
      this.workspaceProject = this.project
      await this.loadNavigation()
      if (session !== this.session) return
      // Mount authenticated surfaces before restoring rows; handle the address only once.
      this.busy = true
      this.restoringSession = false
      await nextTick()
      if (session !== this.session) return
      this.routeReady = true
      const request = this.requestId
      const params = new URLSearchParams(location.search)
      if (params.has('link') || params.has('chat') || addressProject(location)) await this.openBrowserLocation()
      else if (!this.activeWorkspace) {
        if (this.project) this.workspaceProjects[this.project] = { current: '', sections: [] }
        this.clearWorkspace()
      } else if (this.activeWorkspace.current) await this.restoreSearchTab()
      else this.clearWorkspace()
      if (session !== this.session) return
      if (request === this.requestId) this.busy = false
      this.saveSession()
      if (!this.error) this.writeLocation(true)
    },
    logout(message = '') {
      this.sessionRequest++
      this.signingIn = false
      this.restoringSession = false
      this.attachmentLocation = null
      uiPerformance.reset()
      forgetSessions()
      this.persistWorkspace()
      this.checkins = []
      this.$refs.administrationDialog?.close()
      this.administrationOpen = false
      this.closeNavigation()
      this.requestId++
      this.linkRequest++; this.openingLink = false; this.routeReady = false
      this.detailRequest++
      this.$refs.details?.close()
      this.session = null
      this.canAdminister = false
      this.workspaceSelection = null
      this.workspaceProjects = {}
      this.searchStateTab = null
      this.section = 'data'
      this.password = ''
      this.rows = this.projects = this.types = []
      this.columns = {}
      this.interfaceConfig = null
      this.navigationByProject = {}; this.navigationErrors = {}; this.navigationRequests = {}
      this.view = 'table'
      this.configuredView = false
      this.viewTitle = ''
      this.detail = null
      this.type = ''
      this.project = this.workspaceProject = ''
      this.searchText = ''
      this.filterValue = this.filterField = this.sortField = ''
      this.page = 0
      this.busy = false
      this.error = message
      try {
        localStorage.removeItem('tactic_stream.session')
        sessionStorage.removeItem('tactic_stream.session')
      } catch { /* No persistent storage. */ }
    },
    showWorkspaceNotice(message, error = false) {
      notify(error ? 'error' : 'complete', message)
    },
    queuePreview(values) { this.$refs.commitQueue.enqueue(values) },
    messageNotification(row) {
      if (!preferences.global.messageNotifications) return
      notify('info', row.senderTitle || row.sender || 'Messages', row.message, 'messages', row.conversationId + ':' + row.message, { sourceType: 'messages', sourceTitle: row.title, action: 'messages', actionData: row.conversationId, avatarText: row.sender, canReply: row.canReply })
    },
    activityNotification(record) {
      if (!preferences.global.activityNotifications) return
      notify('info', record.actorLabel || record.actor || 'Server trigger', record.detail || '', 'server', 'activity:' + record.eventId, { sourceType: 'activity', sourceTitle: record.title, previewUrl: record.actorAvatar, avatarText: record.actorInitials, avatarColor: record.actorColor, sourceIcon: record.serverGenerated ? 'system-activity' : 'activity-feed', action: 'activity', actionData: record.eventId })
    },
    fail(error) {
      if (error instanceof TypeError) this.connectionOnline = false
      if (error.status === 403 && this.session && (!error.code || error.code === 'authentication_failed')) this.logout('Session ended. Sign in again.')
      else this.error = error instanceof TypeError ? 'Unable to reach the server.' : error.message || 'Request failed.'
    },
    async selectType(type, link = null, filterField = '', filterValue = '', navigationRequest = null) {
      if (this.types.find(item=>item.search_type===type)?.__record_read__?.available === false) return
      if (navigationRequest === null) { this.linkRequest++; this.openingLink = false }
      if (type === 'sthpw/transaction_log' && !link) link = { view: 'table' }
      if (this.$refs.rules && !this.$refs.rules.canLeave()) return
      if (this.$refs.columnsEditor && !this.$refs.columnsEditor.canLeave()) return
      if (this.$refs.users && !this.$refs.users.canLeave()) return
      if (this.$refs.groups && !this.$refs.groups.canLeave()) return
      if (this.$refs.searchTypes && !this.$refs.searchTypes.canLeave()) return
      if (this.$refs.workflow && !this.$refs.workflow.canLeave()) return
      if (this.$refs.sidebar && !this.$refs.sidebar.canLeave()) return
      if (this.$refs.schema && !this.$refs.schema.canLeave()) return
      this.closeNavigation()
      if (this.administrationOpen) return
      const id = JSON.stringify([type, link?.key || link?.name || '', link?.view || 'table', !!link, filterField, filterValue])
      if (!this.workspaceProjects[this.project]) this.workspaceProjects[this.project] = { current: '', sections: [] }
      const workspace = this.workspaceProjects[this.project]
      if (!workspace.sections.some(item => item.id === id)) {
        const connection = { ticket: this.session.ticket, project: this.project }
        const title = link?.title || this.types.find(item => item.search_type === type)?.title || type
        const scope = link?.name ? type.split('?')[0] + '@' + link.name : type.split('?')[0]
        let settings
        this.busy = true
        try { settings = await searchConfiguration('settings', connection.ticket, connection.project, type, { scope }) }
        catch (error) { this.fail(error); return }
        finally { this.busy = false }
        if (connection.ticket !== this.session?.ticket || connection.project !== this.project) return
        const tab = searchTab(title, { type, view: link?.view || 'table', viewTitle: link?.title || '',
          resultMode: link?.display?.options?.view_mode || preferences.checkin.defaultViewMode,
          configuredView: !!link, filterField, filterValue, scopeKey: scope,
          quickSelections: settings.configuration.defaultSelections, quickLayout: null })
        // Handler NavigationMixin adds each search in this sidebar namespace as a tab.
        const tabs = [tab]
        if (link?.display?.options?.search_view) for (const saved of settings.presets.filter(row => row.view.endsWith(':' + scope))) {
          if (saved.error) { this.error = saved.error; continue }
          tabs.push(searchTab(saved.title, { ...tab.state, savedSearch: saved.view, filterRecords: saved.records,
            searchText: saved.keyword || '', presetOrderBys: saved.order_bys || [] }))
        }
        workspace.sections.push({ id, type, title, view: link?.view || 'table', configuredView: !!link,
          navigationKey: link?.key || '', layoutPreset: link?.display?.options?.layout_preset || '',
          icon: link?.icon || 'link', accent: this.types.find(item => item.search_type === type)?.color || '',
          tabs, closedTabs: [], current: tabs.at(-1).id })
      }
      return this.activateSection(id, navigationRequest)
    },
    searchTabTitle(tab) { return tab.title || (tab.number ? t('New Search {number}', { number: tab.number }) : '') },
    captureSearchTab(captureViewport = true) {
      if (this.section !== 'data' || !this.activeSearchTab || this.activeSearchTab !== this.searchStateTab) return
      this.activeSearchTab.state = Object.fromEntries(searchFields.map(name => [name, this[name]]))
      if (this.$refs.docks) this.activeSearchTab.workspaceLayout = this.$refs.docks.capture()
      const viewport = this.$refs.results
      if (captureViewport && !this.busy && this.activeSearchTab.loaded && viewport?.getClientRects().length) {
        this.activeSearchTab.scrollTop = viewport.scrollTop
        this.activeSearchTab.scrollLeft = viewport.scrollLeft
      }
    },
    persistWorkspace(event) {
      if (!this.session) return
      // Chromium can shrink rows after beforeunload, before pagehide deactivates the document.
      this.captureSearchTab(event?.type !== 'pagehide')
      saveWorkspace(this.session.login, this.workspaceProjects)
      this.writeLocation()
    },
    async dockLayoutChanged() {
      await nextTick()
      this.snapshotActive = !!this.$refs.docks?.presented('snapshot')
      this.knowledgeActive = !!this.$refs.docks?.presented('knowledge')
      this.taskCalendarActive = !!this.$refs.docks?.presented('task_calendar')
      this.taskInspectorActive = !!this.$refs.docks?.presented('notes')
      this.searchEditorActive = !!this.$refs.docks?.presented('advanced_search')
      if (this.activeSearchTab !== this.searchStateTab) return
      if (this.activeSearchTab && this.$refs.docks) this.activeSearchTab.workspaceLayout = this.$refs.docks.capture()
      if (this.session && !saveWorkspace(this.session.login, this.workspaceProjects)) this.showWorkspaceNotice('Unable to save preferences. Browser storage is unavailable or full.', true)
      if (this.section === 'data' && this.activeSearchTab && this.$refs.results) {
        this.$refs.results.scrollTop = this.activeSearchTab.scrollTop
        this.$refs.results.scrollLeft = this.activeSearchTab.scrollLeft
      }
    },
    openDock(id, restoring = false) {
      if (id === 'advanced_search') this.$refs.searchLibrary.open(true)
      if (['timesheet','work_reports','cost_reports'].includes(id)) this.openWorkHours(id === 'timesheet' ? 'week' : id === 'cost_reports' ? 'cost' : 'report')
      if (id === 'notes') {
        const target = this.inspectorTarget
        const record = target?.record || this.selectedRecords.at(-1)
        if (record) this.openTaskInspector(record, target?.cell || {}, target?.process || '', target?.taskKey || '', { ...target?.source, reveal: !restoring })
        else this.$refs.taskInspector.show(!restoring)
      }
      if (id === 'description') this.descriptionMounted = true
      if (id === 'knowledge') { this.knowledgeMounted = true; nextTick(() => { this.knowledgeActive = !!this.$refs.docks?.presented('knowledge') }) }
      if (id === 'snapshot') { this.snapshotMounted = true; nextTick(() => { this.snapshotActive = !!this.$refs.docks?.presented('snapshot') }) }
      if (id === 'tasks' && this.canAdminister) this.$refs.taskManager.open(false, '', {}, false, null, !restoring)
      if (id === 'task_calendar' && this.canAdminister) { this.updatesTasksOpen = true; this.$refs.taskManager.open(false, '', {}, true) }
      if (id === 'commit_queue' && !this.fileProject && !restoring) this.openCommitQueue()
    },
    async openWorkHours(mode = 'week', task = null, project = this.workspaceView.project, day = '') {
      const id = mode === 'cost' ? 'cost_reports' : mode === 'report' ? 'work_reports' : 'timesheet'
      const panel = this.$refs[mode === 'cost' ? 'costReports' : mode === 'report' ? 'workReports' : 'timesheet']
      if (panel.context && panel.context.project !== project && (panel.draft || panel.busy || panel.uncertain)) {
        panel.error = 'Save or discard time-entry changes before switching projects.'
        this.$refs.docks.show(id); return
      }
      this.workHoursProjects[mode] = project || this.workspaceView.project
      await nextTick()
      this.$refs.docks.show(id)
      await panel.open(task, false, true, day)
    },
    async openTaskInspector(record, cell = {}, process = '', taskKey = '', source = {}) {
      const inspector = this.$refs.taskInspector
      if (!this.session || source.ticket && source.ticket !== this.session.ticket || !inspector?.canSwitchTarget()) return false
      if (this.administrationOpen) {
        const dialog = this.$refs.administrationDialog
        let closed
        const closing = new Promise(resolve => { closed = resolve; dialog.addEventListener('close', closed, { once: true }) })
        this.leaveAdministration()
        if (dialog.open) { dialog.removeEventListener('close', closed); return false }
        await closing
        if (!this.session || source.ticket && source.ticket !== this.session.ticket) return false
      }
      const request = ++this.inspectorRequest
      const returnPanel = this.$refs.docks.capture().presentation.compactActive
      if (returnPanel !== 'notes' && source.reveal !== false) this.inspectorReturn = returnPanel
      this.inspectorSource = { project: source.project || this.workspaceProject, searchType: source.searchType || this.workspaceView.type, saved: source.saved }
      await nextTick()
      if (request !== this.inspectorRequest) return false
      const opened = await inspector.open(record, cell, process, true, taskKey, source.reveal !== false)
      if (opened && request === this.inspectorRequest) this.inspectorTarget = { record: inspector.target, cell, process: inspector.process, taskKey: inspector.selectedTask, source: this.inspectorSource }
      if (opened && request === this.inspectorRequest && source.noteKey) await inspector.focusNote(source.noteKey)
      return opened
    },
    followInspector(record, process = '', taskKey = '') {
      if (!record?.__search_key__) return
      this.inspectorTarget = { record, process, taskKey }
      if (this.taskInspectorActive && !this.compactShortcuts) this.openTaskInspector(record, {}, process, taskKey, { reveal: false })
    },
    inspectorSaved() {
      if (this.inspectorSource?.saved) this.inspectorSource.saved()
      else this.reloadWorkspace({ restore: true })
      if (this.$refs.taskManager?.opened && !this.$refs.taskManager.busy) this.$refs.taskManager.load(true)
    },
    openFileWorkspace() {
      this.$refs.docks.show('commit_queue')
      this.$refs.docks.move('commit_queue','center','results')
    },
    openCommitQueue() {
      if(this.fileProject)this.openFileWorkspace()
      else this.$refs.commitQueue.open()
    },
    savePreferences() {
      this.captureSearchTab()
      try {
        saveAppearance()
        if (!this.$refs.docks.save()) throw new Error('Unable to save preferences. Browser storage is unavailable or full.')
        if (!saveWorkspace(this.session.login, this.workspaceProjects)) throw new Error('Unable to save preferences. Browser storage is unavailable or full.')
        this.showWorkspaceNotice('Preferences saved')
      } catch { this.showWorkspaceNotice('Unable to save preferences. Browser storage is unavailable or full.', true) }
    },
    async reloadCache(scope = 'server') {
      if (this.reloadingCache || this.busy || this.administrationOpen) return false
      if (scope === 'tabs') {
        this.captureSearchTab()
        const previous = [], active = this.resultState
        for (const workspace of Object.values(this.workspaceProjects)) for (const section of workspace.sections) for (const tab of [...section.tabs,...(section.closedTabs || [])]) { previous.push([tab,tab.state.resultState]); tab.state.resultState = {} }
        this.resultState = {}
        if (!saveWorkspace(this.session.login,this.workspaceProjects)) { for (const [tab,state] of previous) tab.state.resultState = state; this.resultState = active; this.showWorkspaceNotice('Unable to save preferences. Browser storage is unavailable or full.',true); return false }
        this.showWorkspaceNotice('Tabs cache cleared'); return true
      }
      const originSection = this.section
      const ticket = this.session.ticket, project = this.workspaceProject, tab = this.activeSearchTab
      let request = this.requestId
      this.captureSearchTab()
      const selected = [...this.selectedKeys], top = tab?.scrollTop || 0, left = tab?.scrollLeft || 0
      this.reloadingCache = true; this.error = ''
      try {
        // Handler reload_cache bootstraps its catalog; never rebuild retained Vue tabs.
        const [projects, types] = await Promise.all([projectCatalog(ticket),
          rpc('query', [{ ticket, project: 'admin', language: 'python' }, 'sthpw/search_object'], { order_bys: ['search_type'] })])
        if (request !== this.requestId || this.section !== originSection || this.administrationOpen || ticket !== this.session?.ticket || project !== this.workspaceProject || tab !== this.activeSearchTab) return false
        this.projects = projects; this.types = types
        for (const code of Object.keys(this.navigationRequests)) this.navigationRequests[code]++
        this.navigationByProject = {}; this.navigationErrors = {}
        for (const entry of this.retainedSearchTabs) entry.tab.loaded = false
        if (!projects.some(item => item.code === project)) throw new Error('This project is no longer available. Choose another project.')
        await this.loadNavigation()
        if (request !== this.requestId || this.section !== 'data' || this.administrationOpen || ticket !== this.session?.ticket || project !== this.workspaceProject || tab !== this.activeSearchTab) return
        if (this.navigationErrors[project]) throw new Error(this.navigationErrors[project])
        if (tab) {
          request = this.requestId + 1
          const loaded = await this.loadRows({ restore: tab.loadingMode === this.loadingMode })
          if (request !== this.requestId || this.section !== originSection || this.administrationOpen || ticket !== this.session?.ticket || project !== this.workspaceProject || tab !== this.activeSearchTab) return false
          if (loaded) this.selectedKeys = selected.filter(key => this.rows.some(row => row.__search_key__ === key))
          await nextTick()
          if (this.$refs.results) { this.$refs.results.scrollTop = top; this.$refs.results.scrollLeft = left }
          if (loaded) tab.loaded = true
        }
        this.persistWorkspace()
        if (!this.error) this.showWorkspaceNotice('Cache reloaded')
        return !this.error
      } catch (error) { if (request === this.requestId && this.section === originSection && !this.administrationOpen && ticket === this.session?.ticket && project === this.workspaceProject && tab === this.activeSearchTab) {
        this.fail(error); this.showWorkspaceNotice(this.error || error.message, true)
      }; return false }
      finally { this.reloadingCache = false }
    },
    async restoreSearchTab(preserveSection = false) {
      if (this.fileProject && this.activeWorkspace) {
        this.activeWorkspace.sections=this.activeWorkspace.sections.filter(section=>this.types.find(type=>type.search_type===section.type)?.__record_read__?.available !== false)
        if(!this.activeWorkspace.sections.some(section=>section.id===this.activeWorkspace.current))this.activeWorkspace.current=this.activeWorkspace.sections[0]?.id || ''
      }
      this.requestId++
      this.detailRequest++
      this.$refs.details?.close()
      this.$refs.objectOperations?.close()
      if (!preserveSection) this.section = 'data'
      this.workspaceSelection = null
      this.busy = false
      this.loadingMore = false
      this.paginationArmed = false
      const tab = this.activeSearchTab
      this.descriptionTarget = this.snapshotTarget = this.tableCheckinTarget = null
      if (!tab) { this.clearWorkspace(preserveSection); return }
      const scrollTop = tab.scrollTop, scrollLeft = tab.scrollLeft
      const workspaceLayout = tab.workspaceLayout
      Object.assign(this, tab.state)
      this.searchStateTab = tab
      if (tab.loadingMode !== this.loadingMode) { tab.loaded = false; this.page = 0 }
      const loaded = tab.loaded
      tab.loaded = false
      this.busy = !loaded
      await nextTick()
      if (this.activeSearchTab !== tab) return
      if (this.$refs.docks) {
        if (workspaceLayout) { if (!this.$refs.docks.apply(workspaceLayout)) tab.workspaceLayout = null }
        if (!tab.workspaceLayout && this.activeWorkspaceSection?.layoutPreset) await this.$refs.docks.applyAssigned(this.activeWorkspaceSection.layoutPreset, () => this.activeSearchTab === tab)
        if (this.activeSearchTab !== tab) return
        tab.workspaceLayout = this.$refs.docks.capture()
      }
      if (!loaded) {
        const selected = this.selectedKeys, request = this.requestId + 1
        const restored = await this.loadRows({ restore: tab.loadingMode === this.loadingMode })
        if (this.activeSearchTab !== tab || this.requestId !== request) return
        if (!restored) return
        this.selectedKeys = selected.filter(key => this.rows.some(row => row.__search_key__ === key))
      }
      await nextTick()
      if (this.activeSearchTab !== tab) return
      if (this.$refs.results) {
        this.$refs.results.scrollTop = scrollTop
        this.$refs.results.scrollLeft = scrollLeft
      }
      const focused = this.rows.find(row => row.__search_key__ === this.focusedKey)
      const restoredFocus = this.$refs.taskViews?.find(view => view.workspaceId === tab.id && view.project === this.workspaceProject)?.restoreFocus(this.focusedKey)
      if (!restoredFocus && focused) this.focusDescription({ record:focused, kind:'object' })
      tab.loaded = true
      this.saveSession()
    },
    async activateSection(id, navigationRequest = null) {
      if (navigationRequest === null) { this.linkRequest++; this.openingLink = false }
      if (this.administrationOpen || !this.activeWorkspace?.sections.some(item => item.id === id)) return
      this.captureSearchTab()
      this.closeNavigation()
      this.activeWorkspace.current = id
      await this.restoreSearchTab()
    },
    async activateSearchTab(id) {
      this.linkRequest++; this.openingLink = false
      const section = this.activeWorkspaceSection
      if (!section?.tabs.some(tab => tab.id === id) || section.current === id) return
      const tab = section.tabs.find(tab => tab.id === id), cached = tab.loaded
      const measurement = uiPerformance.begin('Search tab: ' + this.searchTabTitle(tab))
      const started = measurement ? performance.now() : 0
      try {
        this.captureSearchTab()
        section.current = id
        await this.restoreSearchTab()
      } finally {
        if (measurement) uiPerformance.details(measurement, { cached, restorationMs: performance.now() - started })
        uiPerformance.end(measurement, this.activeSearchTab?.id !== id ? 'Superseded' : this.error ? 'Failed' : undefined)
      }
    },
    async addSearchTab() {
      const section = this.activeWorkspaceSection
      if (!section) return
      this.captureSearchTab()
      const connection = { ticket: this.session.ticket, project: this.project, scope: this.scopeKey || section.type.split('?')[0] }
      let settings
      this.busy = true
      try { settings = await searchConfiguration('settings', connection.ticket, connection.project, section.type, { scope: connection.scope }) }
      catch (error) { this.fail(error); return }
      finally { this.busy = false }
      if (connection.ticket !== this.session?.ticket || connection.project !== this.project || section !== this.activeWorkspaceSection) return
      const tab = searchTab('', { type: section.type, view: section.view, viewTitle: section.configuredView ? section.title : '',
        configuredView: section.configuredView, pageSize: this.pageSize, scopeKey: connection.scope,
        quickSelections: settings.configuration.defaultSelections }, section.tabs.length + 1)
      section.tabs.push(tab)
      section.current = tab.id
      await this.restoreSearchTab()
      this.$refs.workspaceSearch?.focus()
    },
    async closeSearchTab(id) {
      const section = this.activeWorkspaceSection
      const index = section?.tabs.findIndex(tab => tab.id === id) ?? -1
      if (index < 0 || section.tabs.length === 1) return
      this.captureSearchTab()
      const wasCurrent = section.current === id
      section.closedTabs.push(section.tabs.splice(index, 1)[0])
      if (wasCurrent) {
        section.current = section.tabs[Math.min(index, section.tabs.length - 1)].id
        await this.restoreSearchTab()
      } else this.persistWorkspace()
    },
    async restoreClosedSearchTab(id) {
      const section = this.activeWorkspaceSection
      const index = section?.closedTabs.findIndex(tab => tab.id === id) ?? -1
      if (index < 0) return
      this.captureSearchTab()
      const tab = section.closedTabs.splice(index, 1)[0]
      section.tabs.push(tab)
      section.current = tab.id
      await this.restoreSearchTab()
    },
    canCloseTaskViews(project, ids) {
      if (this.$refs.taskInspector && !this.$refs.taskInspector.canSwitchTarget()) return false
      if (this.$refs.taskManager && !this.$refs.taskManager.canLeave()) return false
      return (this.$refs.taskViews || []).filter(view => (!project || view.project === project) && (!ids || ids.includes(view.workspaceId))).every(view => view.canLeave())
    },
    clearSearchHistory() {
      if (!this.canCloseTaskViews(this.workspaceProject, this.activeWorkspaceSection.closedTabs.map(tab => tab.id))) return
      this.activeWorkspaceSection.closedTabs = []; this.persistWorkspace()
    },
    applyViewToAllTabs() {
      this.captureSearchTab()
      for (const section of this.openSections) for (const tab of section.tabs) {
        tab.state.resultMode = this.resultMode
        tab.state.resultState = { ...tab.state.resultState, splitRatio: this.resultState.splitRatio }
      }
      this.persistWorkspace()
    },
    async closeSection(id) {
      const workspace = this.activeWorkspace
      const index = workspace?.sections.findIndex(section => section.id === id) ?? -1
      if (index < 0 || this.administrationOpen) return
      if (!this.canCloseTaskViews(this.workspaceProject, [...workspace.sections[index].tabs, ...workspace.sections[index].closedTabs].map(tab => tab.id))) return
      this.captureSearchTab()
      const wasCurrent = workspace.current === id
      workspace.sections.splice(index, 1)
      if (wasCurrent) {
        workspace.current = workspace.sections[Math.min(index, workspace.sections.length - 1)]?.id || ''
        await this.restoreSearchTab()
      } else this.persistWorkspace()
    },
    reorderTabs(source, target, sections = false) {
      const tabs = sections ? this.openSections : this.activeWorkspaceSection?.tabs
      if (!tabs || source < 0 || target < 0 || source >= tabs.length || target >= tabs.length || source === target) return
      tabs.splice(target, 0, tabs.splice(source, 1)[0])
      this.persistWorkspace()
    },
    clearWorkspace(preserveSection = false) {
      this.searchStateTab = null
      this.type = ''
      this.navigationLink = ''
      this.requestId++
      this.detailRequest++
      this.rows = []; this.columns = {}; this.interfaceConfig = null
      this.selectedKeys = []; this.focusedKey = ''; this.descriptionTarget = this.snapshotTarget = this.tableCheckinTarget = null
      this.busy = false; this.loadingMore = false; this.paginationArmed = false; this.error = ''
      this.filterRecords = []; this.savedSearch = ''; this.quickSelections = {}; this.quickLayout = null; this.scopeKey = ''; this.presetOrderBys = []
      this.selectedTags = []; this.tagColumn = ''
      this.searchRelation = 'contains'
      if (!preserveSection) this.section = 'data'
      this.saveSession()
    },
    switchProject(event) {
      if (this.$refs.fileWorkspace && !this.$refs.fileWorkspace.canLeave()) { this.project = this.workspaceProject; return }
      if(this.$refs.knowledge&&!this.$refs.knowledge.canLeave()){this.project=this.workspaceProject;if(event)event.target.value=this.project;return}
      if (this.$refs.rules && !this.$refs.rules.canLeave()) {
        this.project = this.$refs.rules.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.columnsEditor && !this.$refs.columnsEditor.canLeave()) {
        this.project = this.$refs.columnsEditor.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.users && !this.$refs.users.canLeave()) {
        this.project = this.$refs.users.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.groups && !this.$refs.groups.canLeave()) {
        this.project = this.$refs.groups.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.sidebar && !this.$refs.sidebar.canLeave()) {
        this.project = this.$refs.sidebar.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.schema && !this.$refs.schema.canLeave()) {
        this.project = this.$refs.schema.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.workflow && !this.$refs.workflow.canLeave()) {
        this.project = this.$refs.workflow.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.$refs.searchTypes && !this.$refs.searchTypes.canLeave()) {
        this.project = this.$refs.searchTypes.context.project
        if (event) event.target.value = this.project
        return
      }
      if (this.section === 'administration' && ['types', 'schema', 'workflow', 'columns', 'layouts', 'raw', 'sidebar', 'users', 'groups', 'rules'].includes(this.administrationSection)) return
      if (this.section === 'administration') this.selectAdministration(this.administrationSection)
      else {
        this.captureSearchTab()
        this.workspaceProject = this.project
        this.loadNavigation()
        if (!this.activeWorkspace) {
          this.workspaceProjects[this.project] = { current: '', sections: [] }
        }
        this.restoreSearchTab()
      }
    },
    async loadRows(options = {}) {
      if (this.section === 'data' && !this.activeSearchTab) return
      const append = options.append === true && this.continuous
      const measurement = uiPerformance.begin(append ? 'Load more search results' : 'Load search results')
      const measurementStart = measurement ? performance.now() : 0
      const phases = {}
      let measurementStatus, publicationStart = 0
      const offset = append ? this.nextOffset : this.continuous ? 0 : this.page * this.pageSize
      const workspaceTab = this.section === 'data' ? this.activeSearchTab : null
      const restoring = options.restore === true && !!workspaceTab
      const offsets = restoring && this.continuous && workspaceTab.loadedOffsets.length ? workspaceTab.loadedOffsets : [offset]
      let loaded = false
      if (workspaceTab && !append) workspaceTab.loaded = false
      if (!append && !restoring) {
        this.selectedKeys = []
        this.loadedQuery = null
        if (workspaceTab) workspaceTab.loadedOffsets = []
      }
      const id = ++this.requestId
      this.detailRequest++
      if (!append) { this.$refs.details?.close(); this.$refs.objectOperations?.close() }
      this.busy = !append
      this.loadingMore = append
      this.paginationArmed = false
      this.error = ''
      try {
        const definitionRequest = append ? Promise.resolve(this.interfaceConfig) : interfaceDefinition(this.session.ticket, this.project, this.type, this.view).catch(async error => {
          if (error.code !== 'access_denied' || this.configuredView) throw error
          // The database browser retains its existing access for non-admin users.
          return { columns: await rpc('get_column_info', [this.ticket, this.type]),
            table: { configured: false, elements: [] }, navigation: { elements: [] } }
        })
        // Restored tabs have settings but no schema or records yet.
        if ((this.searchText.trim() || this.filterValue.trim()) && !Object.keys(this.columns).length) {
          const definition = await definitionRequest
          if (id !== this.requestId) return
          this.columns = definition.columns
        }
        const filters = []
        if (this.filterValue.trim() && this.filterField) {
          const dataType = (this.columns[this.filterField]?.data_type || '').toLowerCase()
          const sectionFilter = this.section === 'administration' && !this.sidebarSearch && ['schema', 'workflow', 'sidebar'].includes(this.administrationSection)
          filters.push([this.filterField, !sectionFilter && ['varchar', 'text'].includes(dataType) ? 'contains' : '=', this.filterValue.trim()])
        }
        if (this.searchText.trim()) {
          const title = ['name', 'title', 'code', 'login'].find(name => name in this.columns)
          const fields = (this.searchRelation === '=' ? [title, 'keywords', 'description'] : ['name', 'title', 'code', 'description', 'search_type', 'display_name', 'login', 'email']).filter(name => /^(text|varchar|char|nvarchar|nchar|citext)/i.test(this.columns[name]?.data_type || ''))
          if (fields.length) filters.push('begin', ...fields.map(name => [name, this.searchRelation, this.searchText.trim()]), 'or')
          else if (this.filterField) filters.push([this.filterField, '=', this.searchText.trim()])
        }
        // Appending continues the executed query, not an unsubmitted input draft.
        const query = append || (restoring && this.loadedQuery) ? this.loadedQuery : JSON.parse(JSON.stringify({
            scope: this.scopeKey || this.type.split('?')[0], records: this.filterRecords, selections: this.quickSelections,
            filters, show_retired: this.showRetired, tags: this.selectedTags, tag_column: this.tagColumn,
            include_total: true,
            ...(this.administrationColumns ? { columns: this.administrationColumns } : {}),
            order_bys: this.sortField ? [`${this.sortField} ${this.sortDirection}`] : this.presetOrderBys,
        }))
        const [definition, firstResult] = await Promise.all([
          definitionRequest,
          searchConfiguration('query', this.session.ticket, this.project, this.type, { ...query, limit: this.pageSize + 1, offset: offsets[0] }),
        ])
        if (id !== this.requestId) return false
        // Handler _query_saved_projection rebuilds all saved batches before publishing.
        let result = firstResult, nextOffset = offsets[0], hasNext = false, totalCount = null
        const batches = [], loadedOffsets = [], keys = new Set(append ? this.rows.map(row => row.__search_key__) : [])
        for (const batchOffset of offsets) {
          if (loadedOffsets.length) {
            result = await searchConfiguration('query', this.session.ticket, this.project, this.type, { ...query, limit: this.pageSize + 1, offset: batchOffset })
            if (id !== this.requestId) return false
          }
          const records = Array.isArray(result) ? result : result.records, batch = records.slice(0, this.pageSize)
          totalCount = Array.isArray(result) ? (records.length <= this.pageSize ? batchOffset + records.length : null) : result.total
          nextOffset = batchOffset + batch.length
          hasNext = records.length > this.pageSize && (totalCount === null || nextOffset < totalCount)
          loadedOffsets.push(batchOffset)
          for (const row of batch) if (!keys.has(row.__search_key__)) { keys.add(row.__search_key__); batches.push(row) }
          if (!hasNext) break
        }
        if (measurement) { phases.requestAndSchemaMs = performance.now() - measurementStart; publicationStart = performance.now() }
        if (id !== this.requestId) return
        this.canAdminister = definition.administration === true
        if (this.section === 'administration' && ['types', 'schema'].includes(this.administrationSection)) definition.operations.create = false
        if (this.administrationColumns) {
          definition.columns = Object.fromEntries(this.administrationColumns.filter(name => name in definition.columns).map(name => [name, definition.columns[name]]))
        }
        this.columns = definition.columns
        this.connectionOnline = true
        this.interfaceConfig = definition
        this.loadedQuery = query
        if (this.configuredView) this.viewTitle = this.viewLinks.find(item => item.search_type === this.type && item.view === this.view)?.title || this.viewTitle
        this.totalCount = totalCount
        this.nextOffset = nextOffset
        this.rows = append ? [...this.rows, ...batches] : batches
        this.hasNext = hasNext
        if (workspaceTab) workspaceTab.loadedOffsets = append ? [...new Set([...workspaceTab.loadedOffsets, ...loadedOffsets])] : loadedOffsets
        loaded = true
        if (!this.columns[this.filterField]) this.filterField = 'name' in this.columns ? 'name' : 'code' in this.columns ? 'code' : Object.keys(this.columns)[0]
      } catch (error) {
        measurementStatus = 'Failed'
        if (id !== this.requestId) return
        if (!append) { this.rows = []; this.hasNext = false; this.totalCount = null; this.nextOffset = 0; if (!restoring) this.loadedQuery = null }
        this.fail(error)
      } finally {
        if (id === this.requestId) {
          this.busy = false
          this.loadingMore = false
          if (workspaceTab && this.activeSearchTab === workspaceTab && this.section === 'data') {
            workspaceTab.loaded = !restoring
            workspaceTab.loadingMode = this.loadingMode
            if (!restoring) this.persistWorkspace()
          }
        }
        if (measurement) {
          await nextTick()
          if (publicationStart) phases.publicationMs = performance.now() - publicationStart
          phases.records = this.rows.length
          uiPerformance.details(measurement, phases)
          uiPerformance.end(measurement, id === this.requestId ? measurementStatus : 'Superseded')
        }
      }
      return loaded
    },
    async refreshTypes() {
      try {
        this.types = await rpc('query', [{ ...this.ticket, project: 'admin' }, 'sthpw/search_object'], { order_bys: ['search_type'] })
        for (const entry of this.retainedSearchTabs) entry.tab.loaded = false
        await this.loadNavigation()
      }
      catch (error) { this.fail(error) }
    },
    async loadNavigation() {
      if (!this.session || !this.workspaceProject) return
      const project = this.workspaceProject, ticket = this.session.ticket
      const id = (this.navigationRequests[project] || 0) + 1
      this.navigationRequests[project] = id
      try {
        const result = await projectNavigation(ticket, project)
        if (id !== this.navigationRequests[project] || ticket !== this.session?.ticket) return
        this.navigationByProject[project] = result
        this.navigationErrors[project] = ''
        const links = []
        const collect = entries => { for (const entry of entries) { links.push(entry); collect(entry.children || []) } }
        collect(navigationEntries(result.entries, this.types))
        for (const section of this.workspaceProjects[project]?.sections || []) {
          const link = links.find(link => link.key === section.navigationKey && link.search_type === section.type && link.view === section.view)
          if (!link) continue
          section.title = link.title; section.icon = link.icon
          section.layoutPreset = link.display.options.layout_preset || ''
          for (const tab of [...section.tabs, ...section.closedTabs]) {
            if (!tab.number) tab.title = link.title
            tab.state.viewTitle = link.title
          }
          if (project === this.workspaceProject && this.activeWorkspaceSection === section && this.section === 'data') this.viewTitle = link.title
        }
        saveWorkspace(this.session.login, this.workspaceProjects)
      } catch (error) {
        if (id === this.navigationRequests[project] && ticket === this.session?.ticket) this.navigationErrors[project] = error.message
      }
    },
    async editNavigation() {
      this.closeNavigation()
      await this.showAdministration('sidebar')
    },
    sidebarSaved(result) {
      delete this.navigationByProject[result.project]
      this.loadNavigation()
      if (result.project === this.workspaceProject) this.$refs.docks?.refreshLayouts()
    },
    async configureSidebarSearch(entry) {
      if (this.sidebarSearch || !this.$refs.sidebar.canLeave()) return
      const snapshot = Object.fromEntries([...searchFields, 'showRetired'].map(key => [key, this[key]]))
      this.sidebarSearch = { snapshot, entry }
      Object.assign(this, { type: entry.searchType, view: 'table', viewTitle: entry.title, configuredView: false,
        filterField: '', filterValue: '', searchText: '', searchRelation: 'contains', sortField: '', sortDirection: 'asc', page: 0, columns: {}, rows: [],
        filterRecords: [], selectedTags: [], tagColumn: '', quickSelections: {}, quickLayout: null, presetOrderBys: [], savedSearch: entry.searchView || '', scopeKey: entry.searchType.split('?')[0] + '@' + entry.name })
      await nextTick()
      this.$refs.sidebarSearchDialog.showModal()
      try {
        const settings = await searchConfiguration('settings', this.session.ticket, this.project, this.type, { scope: this.scopeKey })
        const preset = settings.presets.find(row => row.view === entry.searchView)
        if (entry.searchView && (!preset || preset.error)) throw new Error(preset?.error || 'The predefined search is not available. Refresh the sidebar library.')
        this.filterRecords = preset?.records || []; this.quickSelections = settings.configuration.defaultSelections
        this.searchText = preset?.keyword || ''; this.presetOrderBys = preset?.order_bys || []
      } catch (error) { this.error = error.message; return }
      await this.loadRows()
    },
    openAdvancedSearch() {
      if (this.administrationOpen || this.sidebarSearch) this.$refs.searchLibrary.open()
      else {
        this.$refs.docks.show('advanced_search')
        this.openDock('advanced_search')
      }
    },
    applySearchLibrary(value) {
      this.searchRelation = 'contains'
      this.selectedTags = []; this.tagColumn = ''
      this.filterRecords = value.records; this.quickSelections = value.selections || {}; this.savedSearch = value.preset; this.searchText = value.keyword
      this.navigationLink = value.preset ? savedSearchLink(this.project, this.type, value.preset) : ''
      this.presetOrderBys = value.order_bys; this.sortField = ''; this.sortDirection = 'asc'; this.page = 0; this.loadRows()
    },
    clearSearch() { this.searchText = this.filterValue = this.savedSearch = ''; this.filterRecords = []; this.quickSelections = {}; this.applyFilter() },
    applyQuickFilters(value) { this.quickLayout = value; this.quickSelections = value.defaultSelections; this.page = 0; this.loadRows() },
    searchConfigurationChanged() { this.$refs.sidebar?.refreshLibrary(); this.refreshTypes() },
    closeSidebarSearch() {
      this.requestId++
      if (this.sidebarSearch) Object.assign(this, this.sidebarSearch.snapshot)
      this.sidebarSearch = null
      this.busy = false
      this.$refs.sidebarSearchDialog.close()
    },
    async showLayoutEditor() {
      this.layoutsFocus = {searchType:this.type.split('?')[0],view:this.interfaceConfig?.table?.item_layout ? this.view : 'continuous_example'}
      this.$refs.viewMenu.open = false
      await this.showAdministration('layouts')
    },
    async openLayoutView(result) {
      const dialog = this.$refs.administrationDialog, ticket = this.session?.ticket
      let finish
      const closed = new Promise(resolve => { finish = resolve })
      dialog.addEventListener('close', finish, { once:true })
      this.leaveAdministration()
      if (dialog.open) { dialog.removeEventListener('close', finish); return }
      await closed
      await nextTick()
      if (this.administrationOpen || ticket !== this.session?.ticket) return
      if (result.project !== this.project) await this.openCreatedProject(result.project)
      await this.selectType(result.searchType, {view:result.view,title:result.title})
    },
    async showColumnsEditor(input = false, column = '') {
      this.columnsFocus = column && typeof column === 'object' ? column : { project: this.project, searchType: this.type.split('?')[0], view: input ? 'edit_definition' : this.view, column: column || this.sortField || '' }
      this.$refs.viewMenu.open = false
      await this.showAdministration('columns')
    },
    columnsSaved(result) {
      const source = result.records.find(row => row.identity === result.selected)
      if (!source) return
      for (const entry of this.retainedSearchTabs) {
        if (entry.project === this.project && (source.searchType === 'ALL' || entry.tab.state.type.split('?')[0] === source.searchType)) entry.tab.loaded = false
      }
      if (this.workspaceSelection?.project === this.project && (source.searchType === 'ALL' || this.workspaceSelection.type.split('?')[0] === source.searchType)) this.refreshAfterAdministration = true
      if (source.searchType === 'SideBarWdg') this.loadNavigation()
    },
    tableRecordsSaved(result) {
      if (!result?.records?.length) return this.reloadWorkspace({restore:true})
      const records = new Map(result.records.map(record => [record.__search_key__,record]))
      this.rows = this.rows.map(record => records.get(record.__search_key__) || record)
      if (this.detail?.__search_key__ && records.has(this.detail.__search_key__)) this.detail = records.get(this.detail.__search_key__)
      this.persistWorkspace()
    },
    interfaceSaved(result) {
      if (result?.search_type === 'SideBarWdg') this.loadNavigation()
      else this.reloadWorkspace()
    },
    async reloadWorkspace(options = {}) {
      for (const entry of this.retainedSearchTabs) {
        if (entry.tab.state.type === this.type) entry.tab.loaded = false
      }
      const tab = this.activeSearchTab, request = this.requestId + 1
      const loaded = await this.loadRows({ restore: options?.restore === true })
      if (options?.restore === true && loaded && tab && this.activeSearchTab === tab && this.requestId === request) {
        this.selectedKeys = this.selectedKeys.filter(key => this.rows.some(row => row.__search_key__ === key))
        tab.loaded = true; this.saveSession()
      }
    },
    focusDescription(node) {
      this.tableCheckinTarget = null
      const process = node.kind === 'branch' && node.branch?.kind === 'process'
      const record = process ? { description:node.branch.description || '' } : node.record || {}
      const snapshotKey = process ? node.ownerKey : record.__search_key__
      if (snapshotKey) this.focusedKey = snapshotKey
      if (snapshotKey) this.snapshotTarget = { project:this.workspaceProject,key:snapshotKey,process:process ? node.branch.process : '' }
      if (snapshotKey) this.followInspector({ ...record, __search_key__: snapshotKey }, process ? node.branch.process : '')
      if (node.kind === 'branch' && !process) return
      this.descriptionTarget = { project:this.workspaceProject, id:process ? node.id : record.__search_key__, kind:process ? 'process' : record.__search_key__?.startsWith('sthpw/snapshot?') ? 'snapshot' : node.kind || 'object', title:node.title || record.name || record.title || record.code, record, searchKey:!process && Object.hasOwn(record,'description') ? record.__search_key__ : '' }
    },
    selectRecords(records, checked) {
      if (checked && records.length) this.focusDescription({ record:records.at(-1),kind:'object' })
      const keys = new Set(this.selectedKeys)
      for (const record of records) { if (checked) keys.add(record.__search_key__); else keys.delete(record.__search_key__) }
      this.selectedKeys = [...keys]
    },
    applyFilter() { this.navigationLink = ''; this.selectedTags = []; this.tagColumn = ''; this.page = 0; this.loadRows() },
    submitSearch() {
      if (this.compactShortcuts) this.mobileSearchOpen = false
      const link = searchLink(this.searchText)
      if (link) { this.openRichLink(link); return }
      this.searchRelation = 'contains'
      if (this.activeSearchTab) this.activeSearchTab.title = this.searchText.trim() || this.activeWorkspaceSection.title
      this.applyFilter()
    },
    acceptSuggestion(record) {
      if (this.compactShortcuts) this.mobileSearchOpen = false
      this.searchText = record.title; this.searchRelation = '='
      if (this.activeSearchTab) this.activeSearchTab.title = record.title
      this.applyFilter()
    },
    async openSuggestion(record) {
      const section = this.activeWorkspaceSection
      if (!section || (!record.code && record.id == null)) return
      this.captureSearchTab()
      const tab = searchTab(record.title, { type: section.type, view: section.view, viewTitle: this.viewTitle,
        configuredView: section.configuredView, pageSize: this.pageSize, scopeKey: this.scopeKey,
        filterRecords: [{ column: record.code ? 'code' : 'id', relation: '=', value: String(record.code || record.id), rowEnabled: true, operator: 'begin' }] }, section.tabs.length + 1)
      tab.workspaceLayout = this.activeSearchTab.workspaceLayout ? JSON.parse(JSON.stringify(this.activeSearchTab.workspaceLayout)) : null
      section.tabs.push(tab); section.current = tab.id
      await this.restoreSearchTab()
    },
    applyTags({ tags, column }) { this.selectedTags = tags; this.tagColumn = column; this.page = 0; this.loadRows() },
    toggleView() { this.configuredView = !this.configuredView; this.saveSession(); this.loadRows() },
    sortBy(column, direction) {
      this.sortDirection = direction || (this.sortField === column && this.sortDirection === 'asc' ? 'desc' : 'asc')
      this.sortField = column
      this.page = 0
      this.loadRows()
    },
    changePage(direction) { this.goToPage(this.page + direction + 1) },
    goToPage(number) {
      number = Number(number)
      if (this.continuous || this.busy || !Number.isInteger(number) || number < 1 || (this.pageCount !== null && number > this.pageCount) || number === this.page + 1) return
      this.page = number - 1
      this.loadRows()
    },
    changePageSize(size) {
      size = Number(size)
      if (this.busy || ![20, 25, 50, 100, 200, 500].includes(size) || size === this.pageSize) return
      this.pageSize = size
      this.page = 0
      this.selectedKeys = []
      this.loadRows()
    },
    // Handler search_tabs.py / SearchResultSurface.qml: one next batch per scroll gesture.
    setLoadingMode(mode) {
      if (!['pages', 'infinite'].includes(mode) || mode === this.loadingMode || this.busy) return
      this.loadingMode = mode
      try { localStorage.setItem('tactic_stream.loadingMode.' + this.session.login, mode) } catch { /* Current mode still works without storage. */ }
      this.page = 0
      this.loadRows()
    },
    loadMore(retry = false) {
      if (retry && this.activeSearchTab && !this.activeSearchTab.loaded && this.error && !this.busy && !this.loadingMore) { this.restoreSearchTab(); return }
      if (!this.continuous || this.busy || this.loadingMore || !this.hasNext || (this.error && !retry)) return
      this.loadRows({ append: true })
    },
    armResultPagination(event) {
      if (!this.continuous || (event.type === 'wheel' && event.deltaY <= 0) ||
          (event.type === 'keydown' && !['ArrowDown', 'PageDown', 'End', ' '].includes(event.key))) return
      this.paginationArmed = true
      if (event.type === 'wheel') this.scrollResults(event)
    },
    scrollResults(event) {
      const tableViewport = [...(this.$refs.results?.querySelectorAll('.handler-table') || [])]
        .find(element => element.getClientRects().length)
      const viewport = mobile.value ? event?.currentTarget?.classList.contains('mobile-result-screen') ? event.currentTarget
        : [...(this.$refs.results?.querySelectorAll('.mobile-result-screen[data-screen-key="root"]') || [])].find(element => element.getClientRects().length) : tableViewport || this.$refs.results
      if (!mobile.value && viewport === this.$refs.results && !document.hidden && !this.busy && this.activeSearchTab?.loaded && this.activeSearchTab === this.searchStateTab && viewport) {
        this.activeSearchTab.scrollTop = viewport.scrollTop; this.activeSearchTab.scrollLeft = viewport.scrollLeft
      }
      if (this.paginationArmed && viewport && viewport.scrollTop + viewport.clientHeight >= viewport.scrollHeight - 2) this.loadMore()
    },
    createRecord() {
      if (this.$refs.viewMenu) this.$refs.viewMenu.open = false
      if (this.type === 'sthpw/project') { this.showProjectCreation(); return }
      this.$refs.recordForm.open()
    },
    projectChooserOpening(event) {
      this.closeNavigation()
      for (const menu of this.$refs.topbar.querySelectorAll('details[open]')) menu.open = false
      event.currentTarget.focus()
    },
    projectSelected(code) {
      if (code === this.project || !this.projects.some(item => item.code === code)) return
      this.linkRequest++; this.openingLink = false
      this.project = code; this.switchProject()
    },
    showProjectCreation() {
      if (mobile.value) { this.showWorkspaceNotice('This editor is available on a desktop screen.'); return }
      if (!this.canAdminister) return
      if (this.administrationOpen) {
        this.leaveAdministration()
        if (this.$refs.administrationDialog.open) return
      }
      this.$refs.settingsMenu.open = false
      this.closeNavigation()
      this.$refs.projectCreation.open()
    },
    async openCreatedProject(code, preserveSection = false) {
      const ticket = { ticket: this.session.ticket, project: 'admin', language: 'python' }
      const [projects, types] = await Promise.all([
        projectCatalog(this.session.ticket),
        rpc('query', [ticket, 'sthpw/search_object'], { order_bys: ['search_type'] }),
      ])
      if (!projects.some(row => row.code === code)) throw new Error('The created project is not available. Refresh the project catalog.')
      await rpc('ping', [{ ...ticket, project: code }])
      this.captureSearchTab()
      this.projects = projects
      this.types = types
      this.workspaceProject = this.project = code
      this.workspaceProjects[code] ||= { current: '', sections: [] }
      await this.restoreSearchTab(preserveSection)
      await this.loadNavigation()
      this.persistWorkspace()
      this.openNavigation()
    },
    async configureProject(code) {
      if (code) await this.openCreatedProject(code, true)
      else {
        this.captureSearchTab(); this.project = this.workspaceProject = ''
        await this.restoreSearchTab(true); this.persistWorkspace()
      }
      this.closeNavigation()
      return true
    },
    editRecord(record = this.detail) {
      this.$refs.details.close()
      this.$refs.recordForm.open(record.__search_key__)
    },
    async openActivityObject({ record, target }) {
      const note = !target && record.kind === 'note' && record.targetSearchKey
      const key = record.taskCode || note ? record.targetSearchKey : target ? record.targetSearchKey : record.searchKey
      if (!key) return
      const base = key.split('?')[0]
      await this.selectType(base)
      if (this.type !== base || this.section !== 'data') return
      const ticket = this.session.ticket, project = this.project
      try {
        const object = await rpc('get_by_search_key', [{ ticket, project }, key])
        if (ticket !== this.session?.ticket || project !== this.project) return
        if (!object) throw new Error('Object no longer exists')
        if (record.taskCode) this.$refs.activityNotes.openTask(object, {}, { process: record.process || record.context || '', taskSearchKey: record.searchKey })
        else if (note) this.$refs.activityNotes.open(object, {}, record.process || String(record.context || '').split('/')[0])
        else await this.inspect(object)
      } catch (error) { this.fail(error) }
    },
    writeLocation(replace = false) {
      if (!this.routeReady || this.openingLink || !this.session || this.section !== 'data' || this.administrationOpen) return
      let url = workspaceAddress(this.workspaceProject, this.activeSearchTab ? this.type : '', this.view, this.navigationLink)
      if (this.attachmentLocation) {
        const address = new URL(url, location.origin)
        address.searchParams.delete('link')
        for (const [key, value] of Object.entries(this.attachmentLocation)) address.searchParams.set(key, value)
        url = address.pathname + address.search
      }
      const tab = this.activeSearchTab?.id || ''
      if (location.pathname + location.search !== url || history.state?.tab !== tab) {
        history[replace ? 'replaceState' : 'pushState']({ tab }, '', url)
      }
    },
    async openBrowserLocation(event) {
      if (mobile.value && event?.state?.mobileResult?.key === this.workspaceProject + ':' + this.activeSearchTab?.id + ':' + this.type
        && this.$refs.results?.querySelector('.configured-view[data-workspace-current="true"] .mobile-results')?.getClientRects().length) return
      if (!this.session) return
      this.$refs.details?.close()
      this.$refs.linkPreview?.close()
      if (document.querySelector('dialog:modal')) { this.error = 'Close the current window before opening a link'; this.writeLocation(true); return }
      const params = new URLSearchParams(location.search)
      const project = addressProject(location), type = params.get('search_type')
      if (params.has('link')) { await this.openRichLink(params.get('link'), true, project || this.workspaceProject); return }
      if (!project) return
      const request = ++this.linkRequest, ticket = this.session.ticket
      this.openingLink = true
      try {
        if (!this.projects.some(item => item.code === project)) throw new Error('Project is not available')
        this.captureSearchTab(); this.workspaceProject = this.project = project
        await this.loadNavigation()
        if (request !== this.linkRequest || ticket !== this.session?.ticket) return
        if (!params.has('search_type') && !params.has('chat')) {
          this.workspaceProjects[project] ||= { current: '', sections: [] }
          await this.restoreSearchTab()
          return
        }
        if (params.has('chat')) {
          await this.$refs.messages.openAttachmentLink(params.get('chat'), params.get('snapshot'), params.get('file'))
          return
        }
        if (!type) {
          this.workspaceProjects[project] ||= { current: '', sections: [] }
          this.activeWorkspace.current = ''
          this.clearWorkspace()
          return
        }
        const view = params.get('view') || 'table'
        const workspace = this.activeWorkspace, tab = history.state?.tab
        const section = workspace?.sections.find(section => section.type === type && section.view === view && section.tabs.some(item => item.id === tab)) ||
          workspace?.sections.find(section => section.type === type && section.view === view && section.id === workspace.current)
        // A browser address selects the retained tab, not a fresh unconfigured search.
        if (section) {
          if (section.tabs.some(item => item.id === tab)) section.current = tab
          await this.activateSection(section.id, request)
        } else await this.selectType(type, view === 'table' ? null : { view }, '', '', request)
      } catch (error) { if (request === this.linkRequest) this.fail(error) }
      finally { if (request === this.linkRequest) { this.openingLink = false; this.writeLocation(true) } }
    },
    async openRichLink(value, replace = false, projectContext = this.workspaceProject, showDetails = true) {
      const request = ++this.linkRequest, ticket = this.session?.ticket, originProject = this.workspaceProject, originTab = this.activeSearchTab
      this.openingLink = true
      try {
        if (!ticket || this.section !== 'data' || this.administrationOpen || document.querySelector('dialog:modal')) throw new Error('Close the current window before opening a link')
        const project = linkProject(value, projectContext)
        const result = await navigationLink(ticket, project, value)
        if (request !== this.linkRequest || ticket !== this.session?.ticket || originProject !== this.workspaceProject || originTab !== this.activeSearchTab) return
        if (this.section !== 'data' || this.administrationOpen || document.querySelector('dialog:modal')) throw new Error('Close the current window before opening a link')
        if (!this.projects.some(item => item.code === result.project)) throw new Error('Project is not available')
        this.captureSearchTab(); this.workspaceProject = this.project = result.project
        if (result.kind === 'project') { await this.restoreSearchTab(); await this.loadNavigation(); return }
        await this.loadNavigation()
        if (request !== this.linkRequest || ticket !== this.session?.ticket) return
        if (result.kind === 'message' || result.kind === 'chat-attachment') {
          this.navigationLink = value
          if (result.kind === 'message') await this.$refs.messages.openMessage(result.conversationId, result.object.__search_key__)
          else await this.$refs.messages.openAttachmentLink(result.conversationId, result.snapshot.code, result.fileCode)
          this.saveSession()
          return
        }
        if (result.searchType?.endsWith('/th_knowledge_article')) {
          this.navigationLink=value; this.knowledgeTarget=value; this.$refs.docks.show('knowledge'); this.openDock('knowledge'); this.saveSession(); return
        }
        const object = result.parent || result.object, type = result.kind === 'saved-search' ? result.searchType : object.__search_type__.split('?')[0]
        await this.selectType(type, null, '', '', request)
        if (request !== this.linkRequest || this.type !== type || this.project !== result.project || this.section !== 'data') return
        this.captureSearchTab()
        const section = this.activeWorkspaceSection, preset = result.preset
        const id = !showDetails ? 'object-tab:' + randomId() : preset ? 'preset-link:' + preset.view : 'skey-link:' + result.object.__search_key__ + ':' + result.process
        const existing = section.tabs.findIndex(tab => tab.id === id)
        const title = preset?.title || object.name || object.title || object.code || String(object.id)
        const tab = searchTab(title, { type, pageSize: this.pageSize, view: section.view, configuredView: section.configuredView,
          resultMode: existing >= 0 ? section.tabs[existing].state.resultMode : this.resultMode,
          navigationLink: value, scopeKey: type, savedSearch: preset?.view || '', filterRecords: preset?.records || [{ column: object.code ? 'code' : 'id', relation: '=', value: String(object.code || object.id), rowEnabled: true, operator: 'begin' }],
          searchText: preset?.keyword || '', presetOrderBys: preset?.order_bys || [] })
        tab.id = id
        // Restoring a browser address must not replace an already retained draft.
        if (existing < 0) section.tabs.push(tab)
        else if (!replace) section.tabs.splice(existing, 1, tab)
        section.current = id
        await this.restoreSearchTab()
        if (request !== this.linkRequest || ticket !== this.session?.ticket || this.activeSearchTab?.id !== id || this.error) return
        if (result.kind !== 'saved-search') this.selectedKeys = [object.__search_key__]
        await nextTick()
        if (request !== this.linkRequest || ticket !== this.session?.ticket) return
        if (result.kind === 'note' && result.parent) await this.$refs.activityNotes.open(object, {}, result.process.split('/')[0])
        else if (result.kind === 'task' && result.parent) await this.$refs.activityNotes.openTask(object, {}, { process: result.process.split('/')[0], taskSearchKey: result.object.__search_key__ })
        else if (result.preview) this.$refs.linkPreview.open(object, result.preview)
        else if (result.kind !== 'saved-search' && showDetails) { this.detail = result.object; this.$refs.details.show() }
        this.saveSession()
      } catch (error) { if (request === this.linkRequest) { this.fail(error); this.showWorkspaceNotice(this.error, true) } }
      finally { if (request === this.linkRequest) { this.openingLink = false; this.writeLocation(replace) } }
    },
    async openTableCheckin(record,cell,project) {
      if (!this.canAdminister || !this.$refs.dropPlate.canLeave()) return
      if (['copy','move','local','inplace'].includes(cell.transferMode)) throw new Error('This configured check-in mode requires a desktop connection.')
      this.$refs.dropPlate.clear()
      this.tableCheckinTarget = {project,searchKey:record.__search_key__,title:record.name || record.title || record.code,record,
        process:cell.process || 'publish',context:cell.context || cell.process || 'publish'}
      this.$refs.docks.show('drop_plate')
    },
    async inspect(record) {
      this.focusDescription({ record,kind:'object' })
      const id = ++this.detailRequest
      try {
        const detail = (this.section === 'administration' && this.administrationSection === 'users') || this.type === 'sthpw/transaction_log'
          ? record : await rpc('get_by_search_key', [this.ticket, record.__search_key__])
        if (id !== this.detailRequest) return
        this.detail = detail
        if (this.section === 'data' && detail?.__search_key__) {
          const link = new URL('skey://' + detail.__search_key__)
          if (!link.searchParams.has('project')) link.searchParams.set('project', this.workspaceProject)
          this.navigationLink = link.href
          this.persistWorkspace()
        }
        await nextTick()
        this.$refs.details.show()
      } catch (error) { if (id === this.detailRequest) this.fail(error) }
    },
    display(value) {
      if (value === null || value === undefined) return 'вЂ”'
      if (typeof value === 'object') return JSON.stringify(value)
      return String(value)
    },
  },
}
</script>

<template>
  <main v-if="restoringSession" class="login-page" role="status">
    <span class="muted">{{ t('Loading dataвЂ¦') }}</span>
  </main>
  <main v-else-if="!session" class="login-page">
    <SignIn
      v-model:login="login"
      v-model:password="password"
      :busy="signingIn"
      :ready="ready"
      :error="error"
      :version="version"
      @submit="signIn"
      @help="$refs.help.open($event)"
    >
      <AppButton icon="bug" label="Debug Log" icon-only @click="$refs.debugLog.open()" />
      <AppearanceControls />
    </SignIn>
  </main>
  <div v-else ref="workspace" class="workspace" :style="workspaceStyle" @pointerdown="dismissMenus" @keydown.esc="dismissMenus">
    <header ref="topbar" class="topbar frame-main-toolbar" :style="{height:mainToolbar.height+'px','--project-preview-radius':mainToolbar.dimensions.projectPreviewRadius+'px'}" @toggle.capture="menuToggled">
      <AppButton class="navigation-toggle frame-main-control" data-main-control="mainNavigation" :style="mainToolbarStyle('mainNavigation')" icon-only :label="navigationVisible ? 'Close navigation' : 'Open navigation'" :icon="navigationVisible ? 'close' : 'menu'"
        aria-controls="workspace-sidebar" :aria-expanded="navigationVisible" @click="toggleNavigation" />
      <AppButton class="project-picker frame-main-control" data-main-control="mainProject" :style="mainToolbarStyle('mainProject')" label="Project" :title="currentProject?.title || workspaceView.project" :data-project="workspaceView.project" popovertarget="project-chooser" @click="projectChooserOpening">
        <ItemPreview :source="currentProject?.preview" :fallback-text="projectInitials" :preview-size="mainToolbar.dimensions.projectPreviewExtent" accent="var(--surface-container)" outlined /><strong>{{ currentProject?.title || workspaceView.project || t('Project') }}</strong><AppIcon name="MDI_CHEVRON_DOWN" />
      </AppButton>
      <div class="account">
        <div class="workspace-shortcuts">
          <div id="topbar-system-activity" class="frame-main-control" data-main-control="mainActivity" :style="mainToolbarStyle('mainActivity')"></div>
          <div id="topbar-connection-menu" class="frame-main-control" data-main-control="mainConnection" :style="mainToolbarStyle('mainConnection')"></div>
          <AppButton class="commit-queue-trigger frame-main-control" data-main-control="mainQueue" :style="mainToolbarStyle('mainQueue')" icon-only :label="fileProject ? 'Changelists' : 'Commit Queue'" icon="queue" :badge-count="checkins.filter(job => !['Complete', 'Cancelled', 'Skipped'].includes(job.status)).length" @click="openCommitQueue()" />
          <AppButton class="activity-feed-trigger frame-main-control" data-main-control="mainFeed" :style="mainToolbarStyle('mainFeed')" icon-only label="Activity Feed" icon="activity-feed" :badge-count="activityUnread" @click="$refs.activityFeed.open()" />
        </div>
        <AppearanceControls v-if="!compactShortcuts" class="frame-main-control" data-main-control="mainAppearance" :style="mainToolbarStyle('mainAppearance')" compact />
        <AppMenu frame-composition ref="settingsMenu" class="settings-menu frame-main-control" data-main-control="mainSettings" :style="mainToolbarStyle('mainSettings')" label="More options">
            <ActionRows :actions="configurationActions" @triggered="invokeMainMenu" />
            <p v-if="compactShortcuts" class="muted">{{ t('Schema, interface and script editors are available on a desktop screen.') }}</p>
            <div id="compact-connection-menu"></div>
            <div class="compact-shortcuts">
              <div id="compact-system-activity"></div>
              <AppButton label="Activity Feed" icon="activity-feed" @click="$refs.activityFeed.open(); $refs.settingsMenu.open = false" />
            </div>
        </AppMenu>
        <AppMenu frame-composition ref="accountMenu" class="account-menu frame-main-control" data-main-control="mainAccount" :style="mainToolbarStyle('mainAccount')" label="Account" :badge-count="messageUnread">
          <template #trigger><ItemPreview class="account-avatar" :source="userIdentity?.avatarUrl" :fallback-text="userIdentity?.initials || session.login.slice(0, 1).toUpperCase()" :accent="userIdentity?.avatarColor" :preview-size="mainToolbar.dimensions.surfaceExtent-2" round outlined /><span class="account-name">{{ userIdentity?.displayName || session.login }}</span></template>
          <ActionRows :actions="accountActions" @triggered="invokeMainMenu" />
          <p class="muted">{{ t('Signed in as {login}', { login: session.login }) }}</p><p class="version">TACTIC Stream v{{ version }}</p>
        </AppMenu>
      </div>
    </header>
    <Teleport defer :to="compactShortcuts ? '#compact-system-activity' : '#topbar-system-activity'"><SystemActivityButton :busy="!!activityProgress" :message="activityProgress" :compact="compactShortcuts" @open="$refs.systemActivity.open(); $refs.settingsMenu.open = false" /></Teleport>
    <Teleport defer :to="compactShortcuts ? '#compact-connection-menu' : '#topbar-connection-menu'"><ConnectionMenu :ticket="session.ticket" :project="workspaceProject" :online="connectionOnline" :compact="compactShortcuts" :updates-error="updatesError" :messages-initialized="serverBatch?.messagesInitialized" @busy="pingBusy = $event" @connection="connectionOnline = $event" @session-expired="logout('Session ended. Sign in again.')" /></Teleport>
    <ProjectChooser :projects="projects" :selected="workspaceView.project" @selected="projectSelected" />
    <ServerUpdates ref="serverUpdates" :ticket="session.ticket" :project="workspaceProject" :subscription="updateSubscription" @reset="serverBatch = null" @batch="serverBatch = $event; $refs.taskManager?.applyServerBatch($event)" @connection="connectionOnline = $event" @error="updatesError = $event" @session-expired="logout('Session ended. Sign in again.')" />
    <SystemActivity ref="systemActivity" @open-link="openRichLink" />
    <UserProfile ref="userProfile" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :updates="serverBatch" @message="$refs.messages.openDirect($event)" @tasks="$refs.messages.close(); $refs.taskManager.openForUser($event)" @activity="$refs.activityFeed.open($event)" @open-object="$refs.messages.close(); openActivityObject($event)" @open-link="$refs.messages.close(); openRichLink($event)" @logout="signOut" @saved="identity => { if(identity.login === session.login) userIdentity = identity; $refs.messages.refreshPeople() }" @session-expired="logout('Session ended. Sign in again.')" />
    <MessagesView ref="messages" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :updates="serverBatch" :updates-error="updatesError" @notification="messageNotification" @unread="messageUnread = $event" @open-link="openRichLink" @session-expired="logout('Session ended. Sign in again.')" @open-profile="$refs.userProfile.open($event)" @attachment-location="attachmentLocation = $event; writeLocation(true)" @quick-reply-sent="$refs.notifications.replySent($event)" @quick-reply-failed="$refs.notifications.replyFailed($event)" />
    <ActivityFeed @visibility="updatesActivityOpen = $event" ref="activityFeed" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :updates="serverBatch" :updates-error="updatesError" @notification="activityNotification" @unread="activityUnread = $event" @retry="$refs.serverUpdates.refresh()" @session-expired="logout('Session ended. Sign in again.')" @open-object="openActivityObject" @open-link="openRichLink" />
    <FilePreview ref="linkPreview" :ticket="session.ticket" :project="workspaceProject" :search-type="workspaceView.type" />
    <NotesPanel @visibility="updatesNotesOpen = $event" ref="activityNotes" :ticket="session.ticket" :project="project" :search-type="type" :updates="serverBatch" />
    <NotesPanel ref="taskInspector" dock-target="#dock-notes" :active="taskInspectorActive" :ticket="session.ticket"
      :project="inspectorSource?.project || workspaceProject" :search-type="inspectorSource?.searchType || workspaceView.type" :updates="serverBatch"
      @back="$refs.docks.show(inspectorReturn || 'results')" @visibility="$event ? $refs.docks.show('notes') : $refs.docks.hide('notes')" @saved="inspectorSaved" />
    <UiPerformance ref="uiPerformance" @closed="$refs.settingsMenu?.focusTrigger()" />
    <component v-if="scriptEditorComponent" :is="scriptEditorComponent" ref="scriptEditor" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :updates="serverBatch" :search-type="workspaceView.type" :search-keys="workspaceView.selectedKeys" @saved="$refs.scriptShelf.reload()" @executed="loadRows()" @closed="$refs.settingsMenu?.focusTrigger()" />
    <ScriptShelf ref="scriptShelf" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :updates="serverBatch" v-bind="shelfContext" :search-type="workspaceView.type" :search-keys="workspaceView.selectedKeys" :visible="!compactShortcuts && shelfOpen && !!activeSearchTab && !administrationOpen && section === 'data'" @saved="loadNavigation" @executed="loadRows()" @closed="$refs.settingsMenu?.focusTrigger()" />
    <NotificationStack ref="notifications" @activity="$refs.activityFeed.open()" @messages="$refs.messages.open($event)" @reply="$refs.messages.sendQuickReply($event)" />
    <NavigationDrawer ref="navigation" :editable="!compactShortcuts && canAdminister" :edit-enabled="!busy"
      @closed="navigationOpen = false" @edit="editNavigation">
      <template #extras>
        <div v-if="compactShortcuts && openSections.length" class="mobile-open-views"><AppSelect :model-value="activeWorkspace?.current" :options="openSections.map(item => ({ value: item.id, label: item.title }))" label="Open views" @update:model-value="activateSection" /><AppButton icon-only icon="close" label="Close tab" @click="closeSection(activeWorkspace.current)" /></div>
        <div v-if="compactShortcuts" id="mobile-panel-picker" class="mobile-panel-picker"></div>
      </template>
      <div v-if="navigationErrors[workspaceProject]" class="error" role="alert"><p>{{ navigationErrors[workspaceProject] }}</p><AppButton label="Reload navigation" icon="refresh" @click="loadNavigation" /></div>
      <NavigationTree v-else-if="configuredNavigation" :entries="viewLinks" :project="workspaceProject"
        :selected="activeWorkspaceSection?.navigationKey" @select="item => selectType(item.search_type, item)" />
      <NavigationTree v-else :entries="fallbackNavigation" :project="workspaceProject" :selected="workspaceView.type"
        @select="item => selectType(item.search_type)" />
    </NavigationDrawer>
    <SectionTabRail v-if="!compactShortcuts" class="workspace-rail" :tabs="openSections" :selected="activeWorkspace?.current"
      @select="activateSection" @close="closeSection" @reorder="(source, target) => reorderTabs(source, target, true)" />
    <main class="workspace-main">
    <Teleport v-if="fileProject" defer to="#dock-commit_queue"><FileWorkspace ref="fileWorkspace" :key="workspaceProject" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :can-administer="canAdminister" @ready="openFileWorkspace" @help="$refs.help.open($event)" @debug="$refs.debugLog.open()" /></Teleport>
    <DockWorkspace ref="docks" :mobile="compactShortcuts" :login="session.login" :ticket="session.ticket" :project="workspaceProject" :can-administer="canAdminister" :menu-target="dockMenuTarget" :results-active="section === 'data' && !!activeSearchTab" @open="openDock" @help="$refs.help.open($event)" @changing="captureSearchTab" @changed="dockLayoutChanged" @error="showWorkspaceNotice($event, true)">
      <template #view-actions>
        <Teleport v-if="!administrationOpen" :to="mobileViewMenuTarget || 'body'" :disabled="!compactShortcuts || !mobileViewMenuTarget"><AppMenu ref="viewMenu" v-show="!compactShortcuts || !!mobileViewMenuTarget" :class="{ 'dock-group-menu':!compactShortcuts }" :inline="compactShortcuts && !!mobileViewMenuTarget" :submenu="!compactShortcuts" :overlay="!compactShortcuts" label="View actions" @click="compactShortcuts && $refs.resultActions?.close()" @toggle="menuToggled">
            <template v-if="!administrationOpen && !compactShortcuts" #trigger><AppIcon name="edit" /><span>{{ t('View actions') }}</span><AppIcon name="next" /></template>
            <AppButton class="compact-search-action" label="Refresh" icon="refresh" :disabled="busy" @click="loadRows()" />
            <AppButton v-if="!administrationOpen" class="compact-search-action" label="Tags" icon="MDI_TAG_MULTIPLE" :disabled="busy" @click="openSearchTags" />
            <AppButton class="compact-search-action" label="Search help" icon="help" @click="$refs.help.open('search'); $refs.viewMenu.close(true)" />
            <AppButton v-if="(interfaceConfig?.operations?.create && (type !== 'sthpw/project' || !compactShortcuts)) || (type === 'sthpw/project' && canAdminister && !compactShortcuts)" label="Create record" icon="add" :disabled="busy" @click="createRecord" />
            <AppButton v-if="!compactShortcuts" :label="configuredView ? 'Database fields' : 'Configured view'" icon="table" :disabled="busy" :aria-pressed="configuredView" @click="toggleView(); $refs.viewMenu.open = false" />
            <AppButton v-if="interfaceConfig?.schema_version === 1 && !compactShortcuts" label="Edit interface XML" icon="edit" :disabled="busy" @click="$refs.widgetConfiguration.open(); $refs.viewMenu.open = false" />
            <AppButton v-if="canAdminister && !compactShortcuts" label="Edit layouts" icon="table" :disabled="busy" @click="showLayoutEditor()" />
            <AppButton v-for="customView in interfaceConfig?.views || []" :key="customView" :disabled="busy" @click="selectType(type,{view:customView,title:customView}); $refs.viewMenu && ($refs.viewMenu.open=false)">{{ customView }}</AppButton>
            <AppButton v-if="canAdminister && !compactShortcuts" label="Edit columns" icon="table" :disabled="busy" @click="showColumnsEditor()" />
            <AppButton v-if="canAdminister && !compactShortcuts" label="Edit input definitions" icon="edit" :disabled="busy" @click="showColumnsEditor(true)" />
            <AppButton v-if="administrationOpen" label="Saved searches" icon="save" :disabled="busy" @click="$refs.searchLibrary.open(); $refs.viewMenu.open = false" />
            <AppButton v-if="!compactShortcuts" label="Quick filters" icon="filter" :disabled="busy" @click="$refs.quickFilterEditor.open(); $refs.viewMenu.open = false" />
            <AppButton v-if="searchText || filterValue || filterRecords.length || Object.keys(quickSelections).length" label="Clear search" icon="close" :disabled="busy" @click="clearSearch(); $refs.viewMenu.open = false" />
        </AppMenu></Teleport>
      </template>
    </DockWorkspace>
    <dialog v-window="{kind:'configuration', type:'window' }" ref="configurationDialog" class="configuration-dialog" aria-labelledby="configuration-title" @cancel.prevent="$refs.configuration?.cancel()" @close="section = configurationReturnSection">
      <KeepAlive><Configuration v-if="section === 'configuration'" ref="configuration" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :can-administer="canAdminister" :open-project="configureProject" :reload-cache="reloadCache" @help="$refs.help.open($event)" @close="$refs.configurationDialog.close()" @session-expired="logout('Session ended. Sign in again.')" /></KeepAlive>
    </dialog>
    <dialog v-window="{kind:'administration'}" ref="administrationDialog" class="configuration-dialog administration-dialog" :aria-label="t('Administration')" @cancel.prevent="leaveAdministration" @close="administrationClosed">
      <header class="administration-window-titlebar"><strong>{{t('Administration')}}</strong><AppButton icon-only icon="close" label="Close administration" @click="leaveAdministration" /></header>
      <AdministrationShell ref="administrationShell" :model="{section:administrationSection,project,projects:administrationProjectOptions,locked:administrationLocked,busy, drafts:Object.entries(administrationInstances).filter(([,editor])=>editor.dirty||editor.uncertain).map(([id])=>id)}" @command="administrationCommand" @presentation="administrationPresentation=$event" />
    </dialog>
    <Teleport defer :to="administrationOpen ? '#administration-pages' : '#workspace-data'">
    <div v-if="administrationOpen && administrationVisited.includes('types')" v-show="administrationSection === 'types'" class="administration-page"><SearchTypes :presentation-visible="administrationSection === 'types'" @vue:mounted="administrationInstances.types = $event.component.proxy" ref="searchTypes" @open-workflow="openAdministrationWorkflow" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" :queue-preview="queuePreview" :checkins="checkins" @saved="refreshTypes" @open-commit-queue="openCommitQueue()" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('schema')" v-show="administrationSection === 'schema'" class="administration-page"><SchemaEditor :presentation-visible="administrationSection === 'schema'" @vue:mounted="administrationInstances.schema = $event.component.proxy" ref="schema" @node-workflows="schemaNodeWorkflows" @type-workflow="values=>openAdministrationWorkflow(values,'schema')" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" :queue-preview="queuePreview" :checkins="checkins" @saved="refreshTypes" @open-commit-queue="openCommitQueue()" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('workflow')" v-show="administrationSection === 'workflow'" class="administration-page"><WorkflowEditor :catalog-target="administrationPresentation.library" :catalog-placement="administrationPresentation.mobile ? 'inline' : 'sidebar'" :presentation-visible="administrationSection === 'workflow'" @vue:mounted="administrationWorkflowMounted($event.component.proxy)" ref="workflow" :ticket="session.ticket" :project="project" inline defer-initial-load toolbar-target="#administration-actions" @saved="workflowAdministrationSaved" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('rules')" v-show="administrationSection === 'rules'" class="administration-page"><SecurityRules :presentation-visible="administrationSection === 'rules'" @vue:mounted="administrationInstances.rules = $event.component.proxy" ref="rules" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" @saved="loadNavigation" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('raw')" v-show="administrationSection === 'raw'" class="administration-page"><RawDatabase :presentation-visible="administrationSection === 'raw'" @vue:mounted="administrationInstances.raw = $event.component.proxy" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" @saved="refreshAfterAdministration = true" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('layouts')" v-show="administrationSection === 'layouts'" class="administration-page"><LayoutEditor :presentation-visible="administrationSection === 'layouts'" @vue:mounted="administrationInstances.layouts = $event.component.proxy" :ticket="session.ticket" :project="project" :search-types="types" :initial-focus="layoutsFocus" toolbar-target="#administration-actions" @saved="layoutSaved" @open-view="openLayoutView" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('columns')" v-show="administrationSection === 'columns'" class="administration-page"><ColumnsEditor :presentation-visible="administrationSection === 'columns'" @vue:mounted="administrationInstances.columns = $event.component.proxy" ref="columnsEditor" :ticket="session.ticket" :project="project" :initial-focus="columnsFocus" toolbar-target="#administration-actions" @saved="columnsSaved" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('users')" v-show="administrationSection === 'users'" class="administration-page"><SecurityUsers :presentation-visible="administrationSection === 'users'" @vue:mounted="administrationInstances.users = $event.component.proxy" ref="users" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" @saved="loadNavigation" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('groups')" v-show="administrationSection === 'groups'" class="administration-page"><SecurityGroups :presentation-visible="administrationSection === 'groups'" @vue:mounted="administrationInstances.groups = $event.component.proxy" ref="groups" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" @saved="loadNavigation" /></div>
    <div v-if="administrationOpen && administrationVisited.includes('sidebar')" v-show="administrationSection === 'sidebar'" class="administration-page"><SidebarEditor :presentation-visible="administrationSection === 'sidebar'" @vue:mounted="administrationInstances.sidebar = $event.component.proxy" ref="sidebar" :ticket="session.ticket" :project="project" toolbar-target="#administration-actions" @manage-groups="selectAdministration('groups')" @saved="sidebarSaved" @configure-search="configureSidebarSearch" /></div>
    <Teleport defer to="#sidebar-search-pages" :disabled="!sidebarSearch">
    <section v-if="retainedSearchTabs.length || administrationOpen" v-show="section !== 'configuration' && (sidebarSearch || (administrationOpen ? !['types', 'schema', 'workflow', 'columns', 'layouts', 'raw', 'sidebar', 'users', 'groups', 'rules'].includes(administrationSection) : !!activeSearchTab))" class="content workspace-browser">
      <SearchHeader :model="{compact:compactShortcuts&&!administrationOpen,collapseSearch:true,searchOpen:mobileSearchOpen,busy,shelf:!administrationOpen,shelfOpen,tags:!administrationOpen,quick:true,panels:true}"
        @event="action=>{if(action.type==='refresh')loadRows();else if(action.type==='shelf')shelfOpen=!shelfOpen;else if(action.type==='help')$refs.help.open('search')}">
        <template #field>
        <WorkspaceSearch ref="workspaceSearch" :model-value="searchText" :placeholder="t('Search {name}', { name: activeWorkspaceSection?.title || viewTitle || selectedType?.title || type })"
          v-show="!compactShortcuts || administrationOpen || mobileSearchOpen"
          :ticket="session.ticket" :project="project" :search-type="type" :tab-id="activeSearchTab?.id" :disabled="busy"
          @update:model-value="searchText = $event; searchRelation = 'contains'" @search="submitSearch" @accept="acceptSuggestion" @open="openSuggestion" @dismiss="mobileSearchOpen = false" />
        </template>
        <template #tags>
        <Teleport to="body" :disabled="!compactShortcuts">
        <TagCloud v-if="!administrationOpen" ref="tagCloud" :overlay="compactShortcuts" :external-trigger="compactShortcuts" :ticket="session.ticket" :project="project" :search-type="type" :tab-id="activeSearchTab?.id" :selected="selectedTags" :disabled="busy" :boundary="$refs.results?.parentElement" @apply="applyTags" @toggle="menuToggled" />
        </Teleport>
        </template>
        <template #quick>
        <Teleport defer to="#workspace-mobile-search-tools" :disabled="!compactShortcuts || administrationOpen">
        <SearchQuickFilters v-if="!administrationOpen" ref="quickFilters" :overlay="compactShortcuts"
          :ticket="session.ticket" :project="project" :search-type="type" :tab-id="activeSearchTab?.id" :scope="scopeKey || type.split('?')[0]" :login="session.login"
          :selections="quickSelections" :layout="quickLayout" :disabled="busy" :boundary="$refs.results?.parentElement"
          @apply="applyQuickFilters" @reset="quickLayout = null; quickSelections = $event; page = 0; loadRows()" @edit="$refs.quickFilterEditor.open($event)" @toggle="menuToggled">
          <template #default="{ close }"><details class="quick-filter-field"><summary>{{ t('Filter by field') }}</summary>
            <FieldFilter v-model:field="filterField" v-model:value="filterValue" :retired="showRetired" :columns="columnNames" :disabled="busy"
              @update:retired="showRetired = $event; page = 0; loadRows()" @apply="applyFilter(); close(); compactShortcuts && $refs.resultActions.close(true)" />
          </details></template>
        </SearchQuickFilters>
        <details v-else ref="searchFilters" class="search-filters" @toggle="menuToggled">
          <summary class="icon-button" :class="{ 'is-active': filterValue || showRetired }" :aria-label="t('Search filters')" :title="t('Search filters')"><AppIcon name="filter" /></summary>
          <FieldFilter class="account-panel" v-model:field="filterField" v-model:value="filterValue" :retired="showRetired" :columns="columnNames" :disabled="busy"
            @update:retired="showRetired = $event; page = 0; loadRows()" @apply="applyFilter(); $refs.searchFilters.open = false" />
        </details>
        </Teleport>
        </template>
        <template #panels>
        <div v-show="!compactShortcuts" :ref="element => dockMenuTarget = element" id="workspace-dock-actions"></div>
        <AppButton v-if="compactShortcuts && !administrationOpen" v-show="mobileSearchOpen" icon-only label="Close search" icon="close" @click="mobileSearchOpen = false" />
        </template>
      </SearchHeader>
      <div id="workspace-script-shelf"></div>
      <WorkspaceTabs v-if="!administrationOpen" :mobile="compactShortcuts" :tabs="searchTabs" :selected="activeWorkspaceSection?.current" :closed-tabs="closedSearchTabs"
        @select="activateSearchTab" @add="addSearchTab" @close="closeSearchTab" @reorder="reorderTabs"
        @restore="restoreClosedSearchTab" @clear-history="clearSearchHistory">
        <template #before-tabs><SearchResultMenu kind="filters" icon="advanced-search" label="Search filters and presets" icon-only :model="searchFilterMenuModel" @opening="$refs.searchLibrary.ensureCatalog()" @command="searchFilterCommand" /></template>
        <template #mobile-leading><ItemPreview v-if="activeWorkspaceSection" class="mobile-section-badge" :style="{ width:'24px', height:'24px', minWidth:'24px', flex:'0 0 24px', borderRadius:'50%' }" :fallback-icon="activeWorkspaceSection.icon || 'link'" :accent="activeWorkspaceSection.accent" :preview-size="24" round /></template>
        <template #views><template v-if="openSections.length > 1"><strong>{{ t('Open views') }}</strong><AppButton v-for="item in openSections" :key="item.id" class="mobile-section-choice" :label="item.title" role="menuitemradio" :aria-checked="item.id === activeWorkspace?.current" @click="activateSection(item.id)"><ItemPreview class="mobile-section-badge" :style="{ width:'24px', height:'24px', minWidth:'24px', flex:'0 0 24px', borderRadius:'50%' }" :fallback-icon="item.icon || 'link'" :accent="item.accent" :preview-size="24" round /><span class="mobile-section-title">{{ item.title }}</span><AppIcon v-if="item.id === activeWorkspace?.current" name="check-circle" class="menu-check" /></AppButton><hr></template></template>
        <template #actions="{ compact }">
          <AppButton v-if="compactShortcuts" ref="mobileSearchToggle" icon-only label="Open search" icon="search" :aria-expanded="mobileSearchOpen" :highlighted="!!searchText" :disabled="busy" @click="mobileSearchOpen = !mobileSearchOpen; mobileSearchOpen && $nextTick(()=>$refs.workspaceSearch.focus())" />
          <AppMenu ref="resultActions" class="compact-result-actions" label="Result actions" :inline="!compact" :overlay="compactShortcuts" :close-on-select="false" @toggle="menuToggled"><div id="workspace-sort-actions"></div><div v-show="compactShortcuts" id="workspace-mobile-search-tools"></div><AppButton v-if="compactShortcuts" label="Saved searches" icon="filter" :disabled="busy" @click="openAdvancedSearch(); $refs.resultActions.close(true)" /><div v-show="compactShortcuts" :ref="element => mobileViewMenuTarget = element" id="workspace-mobile-view-actions"></div></AppMenu>
        </template>
      </WorkspaceTabs>
      <Teleport v-if="!administrationOpen" defer to="#workspace-sort-actions">
          <SearchResultMenu kind="sort" icon="sort-items" label="Sort by" :model="searchSortMenuModel" :boundary="$refs.results?.parentElement" @command="searchSortCommand" />
          <SearchResultMenu kind="group" icon="group-items" label="Group items" :model="searchGroupMenuModel" @opening="prepareResultGroups" :boundary="$refs.results?.parentElement" @command="changeResultGroup" />
          <SearchResultMenu v-if="!compactShortcuts" kind="view" label="Change search results view" :icon="resultViews.find(item=>item.value===resultMode)?.icon || 'MDI_TABLE'" :model="{mode:resultMode,busy}" :boundary="$refs.results?.parentElement" @command="changeResultView" />
      </Teleport>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <div v-if="selectedRecords.length && (resultMode !== 'continious' || selectedRecords.length > 1 || mobile)" class="selection-actions" role="group" :aria-label="t('Selected record actions')" @toggle.capture="menuToggled">
        <strong>{{ t('{count} selected records', { count: selectedRecords.length }) }}</strong>
        <AppMenu ref="selectionMenu" label="Selected record actions">
            <AppButton v-if="canAdminister" label="Tasks for selected objects" icon="MDI_CLIPBOARD_TEXT_OUTLINE" @click="$refs.taskManager.open(true)" />
            <AppButton v-if="interfaceConfig?.operations?.edit" label="Edit selected" icon="edit" @click="$refs.recordForm.open(selectedKeys)" />
            <AppButton label="Clear selection" icon="close" @click="selectedKeys = []" />
            <AppButton v-if="interfaceConfig?.operations?.retire && selectedRecords.some(record => record[interfaceConfig.operations.retire_column] !== 'retired')" label="Retire selected" icon="archive" @click="$refs.objectAction.open(selectedRecords, 'retire')" />
            <AppButton v-if="interfaceConfig?.operations?.retire && selectedRecords.some(record => record[interfaceConfig.operations.retire_column] === 'retired')" label="Reactivate selected" icon="refresh" @click="$refs.objectAction.open(selectedRecords, 'reactivate')" />
            <AppButton v-if="interfaceConfig?.operations?.delete" label="Delete selected" icon="delete" destructive @click="$refs.objectAction.open(selectedRecords, 'delete')" />
        </AppMenu>
      </div>
      <div ref="results" class="table-container workspace-results" :aria-busy="busy || loadingMore || (!administrationOpen && activeSearchTab && !activeSearchTab.loaded && !error)"
        @wheel.passive="armResultPagination" @touchstart.passive="armResultPagination" @pointerdown="armResultPagination" @keydown="armResultPagination" @scroll.passive="scrollResults"
        :id="!administrationOpen && activeSearchTab ? 'panel-' + activeSearchTab.id : undefined"
        :role="!administrationOpen ? 'tabpanel' : undefined" :aria-labelledby="!administrationOpen && activeSearchTab ? 'tab-' + activeSearchTab.id : undefined">
        <div v-if="busy" class="table-message" role="status">{{ t('Loading dataвЂ¦') }}</div>
        <ConfiguredView v-if="administrationOpen && interfaceConfig" v-show="!busy" ref="adminTaskView" :definition="interfaceConfig" :rows="rows" :configured="configuredView" :read-only="false"
          :ticket="session.ticket" :project="project" :sort-field="sortField" :sort-direction="sortDirection" @sort="sortBy" @inspect="inspect"
          :selected-keys="selectedKeys" @focus="focusDescription" @select="selectRecords" @column="showColumnsEditor(false, $event)"
          @saved="tableRecordsSaved" @operate="(record, event, node) => $refs.objectOperations.open(record, event, node)" />
        <template v-for="entry in retainedSearchTabs" :key="entry.project + entry.tab.id">
          <ConfiguredView v-if="entry.tab === displayedSearchTab ? interfaceConfig : entry.tab.state.interfaceConfig"
            ref="taskViews" @organization="resultOrganizationChanged(entry, $event)" :workspace-id="entry.tab.id" :data-workspace-current="entry.tab === displayedSearchTab && !administrationOpen"
            v-show="!administrationOpen && !busy && entry.tab === displayedSearchTab"
            :definition="entry.tab === displayedSearchTab ? interfaceConfig : entry.tab.state.interfaceConfig"
            :rows="entry.tab === displayedSearchTab ? rows : entry.tab.state.rows"
            :configured="entry.tab === displayedSearchTab ? configuredView : entry.tab.state.configuredView"
            :result-mode="entry.tab === displayedSearchTab ? resultMode : entry.tab.state.resultMode"
            :group-mode="entry.tab === displayedSearchTab ? groupMode : entry.tab.state.groupMode"
            :result-state="entry.tab === displayedSearchTab ? resultState : entry.tab.state.resultState" @result-state="resultStateChanged(entry, $event)"
            :read-only="false" :ticket="session.ticket" :project="entry.project" :accent="entry.section.accent"
            :sort-field="entry.tab === displayedSearchTab ? sortField : entry.tab.state.sortField"
            :sort-direction="entry.tab === displayedSearchTab ? sortDirection : entry.tab.state.sortDirection"
            :selected-keys="entry.tab === displayedSearchTab ? selectedKeys : entry.tab.state.selectedKeys"
            @result-scroll="entry.tab === displayedSearchTab && scrollResults($event)" @sort="sortBy" @inspect="inspect" @focus="entry.tab === displayedSearchTab && focusDescription($event)" @select="selectRecords" @column="showColumnsEditor(false, $event)"
            @saved="tableRecordsSaved" @operate="(record, event, node) => $refs.objectOperations.open(record, event, node)" />
        </template>
        <div v-if="continuous && (hasNext || loadingMore || (!activeSearchTab?.loaded && error))" class="workspace-load-more">
          <span v-if="loadingMore" role="status">{{ t('Loading moreвЂ¦') }}</span>
          <AppButton v-else :label="error ? 'Retry' : 'Load more'" :icon="error ? 'refresh' : 'next'" @click="loadMore(true)" />
        </div>
      </div>
      <DockWorkspaceFooter class="pagination workspace-footer frame-search-footer">
        <SearchFooter :boundary="$refs.results?.parentElement" :model="{mode:continuous?'infinite':'pages',busy,page:page+1,pageCount,pageSize,pageNumbers,hasNext,count:rows.length,total:totalCount,range:rowRange,queue:!compactShortcuts,fileProject,canCreate:(!compactShortcuts || type!=='sthpw/project') && !!(interfaceConfig?.operations?.create || (type==='sthpw/project'&&canAdminister))}"
          @event="searchFooterEvent" />
      </DockWorkspaceFooter>
    </section>
    </Teleport>
    <section v-if="section === 'data' && !activeSearchTab" class="workspace-empty">
      <AppIcon name="search" /><h1>{{ t('No Search Type open') }}</h1>
      <p v-if="workspaceProject" class="muted">{{ t('Open navigation and choose a Search Type to start searching.') }}</p>
      <AppButton v-if="workspaceProject" icon="menu" label="Open navigation" @click="openNavigation" />
      <AppButton v-else icon="MDI_FOLDER" label="Project" popovertarget="project-chooser" @click="projectChooserOpening" />
    </section>
    </Teleport>
    </main>
    <dialog v-window="{kind:'sidebar_search_preview'}" ref="sidebarSearchDialog" class="configuration-dialog sidebar-search-dialog" :aria-label="t('Configure search')" @cancel.prevent="closeSidebarSearch">
      <div class="sidebar-search-shell"><header><div><h2>{{ t('Configure search') }}</h2><p>{{ sidebarSearch?.entry.title }} В· {{ sidebarSearch?.entry.searchType }}</p></div><div id="sidebar-search-actions" class="configuration-actions"><AppButton icon-only label="Quick filters" icon="filter" :disabled="busy" @click="$refs.quickFilterEditor.open()" /><AppButton label="Saved searches" icon="save" :disabled="busy" @click="$refs.searchLibrary.open()" /></div><AppButton label="Close" icon="close" @click="closeSidebarSearch" /></header><div id="sidebar-search-pages"></div></div>
    </dialog>
    <SearchLibrary ref="searchLibrary" :selections="quickSelections" :active="searchEditorActive" @closed="$event && $refs.docks.hide('advanced_search')" :tab-id="activeSearchTab?.id" :tab-title="activeSearchTab ? searchTabTitle(activeSearchTab) : ''" @rename="renameCurrentSearchTab" :ticket="session.ticket" :project="project" :search-type="type" :scope="scopeKey || type.split('?')[0]" :records="filterRecords" :preset="savedSearch" :keyword="searchText" :order-bys="sortField ? [`${sortField} ${sortDirection}`] : presetOrderBys" :can-manage="canAdminister" @apply="applySearchLibrary" @changed="searchConfigurationChanged" />
    <QuickFilterEditor ref="quickFilterEditor" :tab-id="activeSearchTab?.id" :ticket="session.ticket" :project="project" :search-type="type" :scope="scopeKey || type.split('?')[0]" :selections="quickSelections" :layout="quickLayout" :can-manage="canAdminister" @apply="applyQuickFilters" @changed="searchConfigurationChanged(); $refs.quickFilters?.load(true)" />
    <dialog v-window="{kind:'sobject_info', type:'window' }" ref="details" class="record-dialog object-details" :aria-label="t('Object details')">
      <template v-if="detail">
        <header><div><h2>{{ detail.name || detail.title || detail.code || detail.id }}</h2><small class="muted">{{ detail.__search_key__ }}</small></div><div class="configuration-actions"><AppButton v-if="interfaceConfig?.operations?.edit" label="Edit record" icon="edit" :icon-only="compactShortcuts" @click="editRecord()" /><AppButton label="Close details" icon="close" :icon-only="compactShortcuts" @click="$refs.details.close()" /></div></header>
        <ObjectReport :ticket="session.ticket" :project="workspaceProject" :record="detail" />
      </template>
    </dialog>
    <ObjectOperations ref="objectOperations" :ticket="session.ticket" :project="project" :search-type="type" :operations="interfaceConfig?.operations"
      :selection="rows.filter(record => selectedKeys.includes(record.__search_key__))" @edit-selected="records => $refs.recordForm.open(records.map(record => record.__search_key__))"
      @inspect="inspect" @edit="editRecord" @create="createRecord" @related="record => $refs.relatedObjects.open(record)"
      @duplicate="record => $refs.recordForm.open(null, record.__search_key__)"
      @duplicated="reloadWorkspace({ restore:true })"
      @retire="record => $refs.objectAction.open(record, 'retire')" @reactivate="record => $refs.objectAction.open(record, 'reactivate')"
      @delete="record => $refs.objectAction.open(record, 'delete')" />
    <ObjectAction ref="objectAction" :ticket="session.ticket" :project="project" :search-type="type" :view="view" @saved="reloadWorkspace" />
    <RelatedObjects ref="relatedObjects" :ticket="session.ticket" :project="project" :search-type="type" />
    <RecordForm ref="recordForm" :ticket="session.ticket" :project="project" :search-type="type" @saved="reloadWorkspace" />
    <WidgetConfiguration ref="widgetConfiguration" :ticket="session.ticket" :project="project" :search-type="type" :view="view" :rows="rows" :search-types="types" @saved="interfaceSaved" />
    <DescriptionEditor v-if="descriptionMounted" ref="description" :ticket="session.ticket" :project="workspaceProject" :target="descriptionTarget" @saved="reloadWorkspace({ restore:true })" @session-expired="logout" />
    <SnapshotBrowser v-if="snapshotMounted" :ticket="session.ticket" :project="workspaceProject" :target="snapshotTarget" :active="snapshotActive" @changed="reloadWorkspace({ restore:true })" @session-expired="logout" />
    <Teleport defer to="#dock-knowledge"><KnowledgeBase v-if="knowledgeMounted" ref="knowledge" :ticket="session.ticket" :project="workspaceProject" :login="session.login" :active="knowledgeActive" :target="knowledgeTarget" :selection="(workspaceView.rows||[]).filter(record=>(workspaceView.selectedKeys||[]).includes(record.__search_key__))" @changed="reloadWorkspace({restore:true})" @location="navigationLink=$event; writeLocation(true)" @session-expired="logout" @open-link="openRichLink" /></Teleport>
    <DropPlate ref="dropPlate" :ticket="session.ticket" :project="tableCheckinTarget?.project || workspaceProject" :target="tableCheckinTarget || (snapshotTarget ? { ...descriptionTarget, project:snapshotTarget.project, searchKey:snapshotTarget.key, process:snapshotTarget.process } : descriptionTarget)" @help="$refs.help.open($event)" />
    <CommitQueue :presentation-visible="!fileProject" ref="commitQueue" inline :can-administer="canAdminister" :login="session.login" :ticket="session.ticket" :project="workspaceProject" @changed="checkins = $event" @completed="$refs.dropPlate.completed($event); reloadWorkspace({ restore: true })" @opened="$refs.docks.show('commit_queue')" @closed="compactShortcuts && $refs.docks.hide('commit_queue')" @help="$refs.help.open($event)" @snapshot="snapshotTarget = { project:$event.project, key:$event.snapshot?.__search_key__ || $event.searchKey, process:$event.process }; openDock('snapshot'); $refs.docks.show('snapshot')" />
    <Timesheet ref="timesheet" dock-target="#dock-timesheet" dock-mode="week" :ticket="session.ticket" :project="workHoursProjects.week || workspaceView.project" :current-user="session.login" @opened="$refs.docks.show('timesheet')" @closed="$refs.docks.hide('timesheet')" @open-dock="openWorkHours($event,$refs.timesheet.task,workHoursProjects.week)" @saved="reloadWorkspace" />
    <Timesheet ref="workReports" dock-target="#dock-work_reports" dock-mode="report" :ticket="session.ticket" :project="workHoursProjects.report || workspaceView.project" :current-user="session.login" @opened="$refs.docks.show('work_reports')" @closed="$refs.docks.hide('work_reports')" @open-dock="openWorkHours($event,$refs.workReports.task,workHoursProjects.report)" @saved="reloadWorkspace" />
    <Timesheet ref="costReports" dock-target="#dock-cost_reports" dock-mode="report" dock-report="labor_cost" :ticket="session.ticket" :project="workHoursProjects.cost || workspaceView.project" :current-user="session.login" @opened="$refs.docks.show('cost_reports')" @closed="$refs.docks.hide('cost_reports')" @open-dock="openWorkHours($event,$refs.costReports.task,workHoursProjects.cost)" @saved="reloadWorkspace" />
    <TaskManager ref="taskManager" docked calendar-target="#dock-task_calendar" :calendar-active="taskCalendarActive" @calendar="$refs.docks.show('task_calendar'); openDock('task_calendar')" :ticket="session.ticket" :project="workspaceView.project" :current-user="session.login" :search-type="workspaceView.type" :search-type-title="(workspaceView.types || types).find(item => item.search_type === workspaceView.type)?.title || ''" @opened="updatesTasksOpen = true; $refs.docks.show('tasks')" @closed="updatesTasksOpen = taskCalendarActive; $refs.docks.hide('tasks')"
      @snapshot-context="snapshotTarget = $event" @task-context="followInspector($event.parent, $event.process, $event.__search_key__)" :parents="(workspaceView.rows || []).filter(record => (workspaceView.selectedKeys || []).includes(record.__search_key__))" @saved="reloadWorkspace({ restore: true })" @object="inspect" />
    <ProjectCreation ref="projectCreation" :ticket="session.ticket" :open-project="openCreatedProject" />
  </div>
  <HelpView ref="help" />
  <DebugLog ref="debugLog" @help="$refs.help.open($event)" @closed="$refs.settingsMenu?.focusTrigger()" />
</template>

