// Adapted from Handler controllers/navigation.py and search_tabs.py.
// Persist search settings and selection keys. Records, tickets and server definitions stay in memory.
import { defaultResultView } from './resultViews.js'
import { preferences } from '../configuration/preferences.js'
export const searchFields = ['type', 'view', 'viewTitle', 'configuredView', 'navigationLink', 'resultMode', 'groupMode', 'resultState', 'searchText', 'filterField', 'filterValue',
  'searchRelation', 'sortField', 'sortDirection', 'page', 'pageSize', 'showRetired', 'selectedKeys', 'focusedKey', 'columns', 'rows',
  'hasNext', 'totalCount', 'nextOffset', 'loadedQuery', 'interfaceConfig', 'error', 'filterRecords', 'savedSearch', 'quickSelections', 'quickLayout', 'scopeKey', 'presetOrderBys', 'selectedTags', 'tagColumn']
const savedFields = searchFields.filter(name => !['columns', 'rows', 'hasNext', 'totalCount', 'nextOffset', 'loadedQuery', 'interfaceConfig', 'error'].includes(name))
let serial = 0

export function navigationEntries(items, types) {
  return items.map(item => {
    const options = item.display.options
    const target = types.find(type => type.search_type === (item.layoutSearchType || options.search_type))
    const layout = options.layout === 'default' ? target?.default_layout || 'table' : options.layout || 'table'
    return { ...item, search_type: item.layoutSearchType || options.search_type, view: item.layoutView ? 'table' : options.view || 'table', resultMode: options.view_mode || item.default_view_mode || '', accent: item.color || target?.color || '',
      children: navigationEntries(item.children || [], types),
      supported: !!target && !item.action.handler && ['LinkWdg', 'pyasm.widget.LinkWdg'].includes(item.display.handler) &&
        (!options.class_name || options.class_name === 'tactic.ui.panel.ViewPanelWdg') &&
        (!options.view_mode || ['continious', 'tiles', 'table', 'compact', 'splitted_vertical', 'splitted_horizontal'].includes(options.view_mode)) &&
        (!options.widget_key || options.widget_key === 'view_panel' || (options.widget_key === 'custom_layout' && item.layoutView)) && ['table', 'TableWdg', 'TableLayoutWdg'].includes(layout) }
  })
}

export function searchTab(title, state = {}, number = 0) {
  return { id: 'search-' + Date.now().toString(36) + '-' + ++serial, title, number, loaded: false,
    scrollTop: 0, scrollLeft: 0, workspaceLayout: null, loadedOffsets: [], loadingMode:preferences.checkin.loadingMode,
    state: { type: '', view: 'table', viewTitle: '', configuredView: false, navigationLink: '', resultMode: preferences.checkin.defaultViewMode, groupMode: 'none', resultState: {}, searchText: '', filterField: '', filterValue: '',
      searchRelation: 'contains', sortField: '', sortDirection: 'asc', page: 0, pageSize: preferences.checkin.displayLimit, showRetired: false, selectedKeys: [], focusedKey:'',
      columns: {}, rows: [], hasNext: false, totalCount: null, nextOffset: 0, loadedQuery: null, interfaceConfig: null, error: '', filterRecords: [], savedSearch: '', quickSelections: {}, quickLayout: null, scopeKey: '', presetOrderBys: [], selectedTags: [], tagColumn: '', ...state } }
}

function savedQuery(query) {
  if (!query || typeof query !== 'object' || Array.isArray(query)) return null
  const result = Object.fromEntries(['scope', 'records', 'selections', 'filters', 'show_retired', 'tags', 'tag_column', 'order_bys']
    .filter(name => name in query).map(name => [name, query[name]]))
  if (typeof result.scope !== 'string' || result.scope.length > 256 ||
      !Array.isArray(result.records) || !Array.isArray(result.filters) || !Array.isArray(result.order_bys) ||
      !Array.isArray(result.tags) || !result.selections || typeof result.selections !== 'object' || Array.isArray(result.selections) ||
      typeof result.show_retired !== 'boolean' || typeof result.tag_column !== 'string' || JSON.stringify(result).length > 256 * 1024) return null
  return { ...result, include_total: true }
}

export function saveWorkspace(login, projects) {
  const saveTab = tab => ({ id: tab.id, title: tab.title, number: tab.number,
    loadingMode: tab.loadingMode, loadedOffsets: tab.loadedOffsets, query: savedQuery(tab.state.loadedQuery),
    scrollTop: tab.scrollTop, scrollLeft: tab.scrollLeft, workspaceLayout: tab.workspaceLayout,
    state: Object.fromEntries(savedFields.map(name => [name, name === 'resultState' && !preferences.cache.cacheProcessTabs ? {} : tab.state[name]])) })
  const saved = {}
  for (const [code, project] of Object.entries(projects)) {
    saved[code] = { current: project.current, sections: project.sections.map(section => ({
      id: section.id, title: section.title, type: section.type, view: section.view, configuredView: section.configuredView,
      icon: section.icon, accent: section.accent, current: section.current,
      navigationKey: section.navigationKey || '', layoutPreset: section.layoutPreset || '',
      tabs: section.tabs.map(saveTab), closedTabs: (section.closedTabs || []).slice(-20).map(saveTab),
    })) }
  }
  try { localStorage.setItem('tactic_stream.workspace.' + login, JSON.stringify(saved)); return true }
  catch { return false /* Live tabs still work when browser storage is unavailable or full. */ }
}

export function readWorkspace(login, projects, types) {
  const result = {}
  let saved
  try { saved = JSON.parse(localStorage.getItem('tactic_stream.workspace.' + login)) } catch { return result }
  if (!saved || typeof saved !== 'object') return result
  for (const project of projects) {
    const source = saved[project.code]
    if (!Array.isArray(source?.sections)) continue
    const sections = []
    for (const item of source.sections) {
      if (typeof item?.id !== 'string' || sections.some(section => section.id === item.id) ||
          !types.some(type => type.search_type === item.type) || !Array.isArray(item.tabs)) continue
      const tabs = [], closedTabs = [], seen = new Set()
      const history = Array.isArray(item.closedTabs) ? item.closedTabs.slice(-20) : []
      for (const [closed, records] of [[false, item.tabs], [true, history]]) for (const record of records) {
        if (typeof record?.id !== 'string' || seen.has(record.id)) continue
        seen.add(record.id)
        const tab = searchTab(typeof record.title === 'string' ? record.title : item.title)
        tab.id = record.id
        tab.number = Number.isInteger(record.number) && record.number > 0 ? record.number : 0
        tab.loadingMode = record.loadingMode === 'infinite' ? 'infinite' : 'pages'
        tab.loadedOffsets = Array.isArray(record.loadedOffsets)
          ? [...new Set(record.loadedOffsets.slice(0, 256).filter(offset => Number.isSafeInteger(offset) && offset >= 0))].sort((a, b) => a - b) : []
        tab.state.loadedQuery = savedQuery(record.query)
        if (tab.state.loadedQuery && tab.state.loadedQuery.scope.split('@')[0] !== item.type.split('?')[0]) tab.state.loadedQuery = null
        if (record.workspaceLayout && typeof record.workspaceLayout === 'object') tab.workspaceLayout = record.workspaceLayout
        for (const name of savedFields) {
          if (typeof record.state?.[name] === typeof tab.state[name]) tab.state[name] = record.state[name]
        }
        if (!Array.isArray(tab.state.filterRecords)) tab.state.filterRecords = []
        tab.state.selectedKeys = Array.isArray(tab.state.selectedKeys)
          ? [...new Set(tab.state.selectedKeys.filter(key => typeof key === 'string' && key && key.length <= 16384).slice(0, 5000))] : []
        if (typeof tab.state.focusedKey !== 'string' || tab.state.focusedKey.length > 16384) tab.state.focusedKey = ''
        if (!['continious', 'tiles', 'table', 'compact', 'splitted_vertical', 'splitted_horizontal'].includes(tab.state.resultMode)) tab.state.resultMode = defaultResultView
        if (!['none', 'status', 'pipeline'].includes(tab.state.groupMode) && !/^task_status:.{1,256}$/.test(tab.state.groupMode || '')) tab.state.groupMode = 'none'
        if (!preferences.cache.cacheProcessTabs || !tab.state.resultState || Array.isArray(tab.state.resultState)) tab.state.resultState = {}
        if (!['contains', '='].includes(tab.state.searchRelation)) tab.state.searchRelation = 'contains'
        if (!Array.isArray(tab.state.presetOrderBys)) tab.state.presetOrderBys = []
        tab.state.selectedTags = Array.isArray(tab.state.selectedTags) ? tab.state.selectedTags.filter(value => typeof value === 'string' && value && value.length <= 16384).slice(0, 128) : []
        if (!tab.state.quickSelections || Array.isArray(tab.state.quickSelections)) tab.state.quickSelections = {}
        if (tab.state.quickLayout && (Array.isArray(tab.state.quickLayout) || !Array.isArray(tab.state.quickLayout.groups))) tab.state.quickLayout = null
        tab.state.type = item.type
        if (typeof tab.state.navigationLink !== 'string' || tab.state.navigationLink.length > 16384 || !/^(skey|tactic-search):\/\//i.test(tab.state.navigationLink)) tab.state.navigationLink = ''
        for (const name of ['page', 'pageSize']) {
          if (!Number.isSafeInteger(tab.state[name]) || tab.state[name] < (name === 'page' ? 0 : 1) || (name === 'pageSize' && tab.state[name] > 500)) tab.state[name] = name === 'page' ? 0 : preferences.checkin.displayLimit
        }
        for (const name of ['scrollTop', 'scrollLeft']) {
          if (Number.isFinite(record[name]) && record[name] >= 0) tab[name] = record[name]
        }
        if (closed) closedTabs.push(tab)
        else tabs.push(tab)
      }
      if (!tabs.length) continue
      sections.push({ id: item.id, title: typeof item.title === 'string' ? item.title : item.type,
        type: item.type, view: typeof item.view === 'string' ? item.view : 'table', configuredView: item.configuredView === true,
        icon: typeof item.icon === 'string' ? item.icon : 'link', accent: typeof item.accent === 'string' ? item.accent : '',
        navigationKey: typeof item.navigationKey === 'string' ? item.navigationKey : '',
        layoutPreset: typeof item.layoutPreset === 'string' ? item.layoutPreset : '',
        tabs, closedTabs, current: tabs.some(tab => tab.id === item.current) ? item.current : tabs[0].id })
    }
    result[project.code] = { sections, current: sections.some(section => section.id === source.current) ? source.current : sections[0]?.id || '' }
  }
  return result
}
