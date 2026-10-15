// Handler ConfigurationController: browser defaults apply only where there is no saved workspace state.
import { reactive, ref } from 'vue'
import { normalizeColumns } from '../tasks/taskColumns.js'
export const configurationPreview = ref(false)
export const preferenceDefaults = {
  checkin: { displayLimit: 20, defaultViewMode: 'continious', loadingMode: 'pages', keepFilename: false, groupCheckin: true, includeSubfolders:false, generatePreviews: true, confirmRevision: true, commitQueueAutoClean: true },
  tasks: { workspaceSurface: 'browser', quickViewMode: 'cards', viewMode: 'table', sortMode: 'due', groupMode: 'process', inspectorExpanded: false, columns: [] },
  global: { activityNotifications: true, messageNotifications: true },
  cache: { cacheProcessTabs: true },
  repository: { enabledAliases:null, defaultAlias:'default' },
}
export function normalizePreferences(value = {}) {
  const result = structuredClone(preferenceDefaults)
  for (const [page, fields] of Object.entries(result)) for (const [key, fallback] of Object.entries(fields)) {
    const saved = value?.[page]?.[key]
    if (typeof fallback === 'boolean' && typeof saved === 'boolean') fields[key] = saved
  }
  const choices = { checkin: { defaultViewMode:['continious','tiles','table','compact','splitted_vertical','splitted_horizontal'], loadingMode:['pages','infinite'] },
    tasks: { workspaceSurface:['browser','quick'], quickViewMode:['cards','compact'], viewMode:['table','gantt'], sortMode:['due','recent','user','process','status','object','search_type','project','priority','milestone','supervisor'], groupMode:['none','user','process','status','object'] } }
  for (const [page, fields] of Object.entries(choices)) for (const [key, allowed] of Object.entries(fields)) if (allowed.includes(value?.[page]?.[key])) result[page][key] = value[page][key]
  const limit = Number(value?.checkin?.displayLimit)
  if (Number.isFinite(limit) && limit > 0) result.checkin.displayLimit = Math.max(1, Math.min(500, Math.trunc(limit)))
  result.tasks.columns = normalizeColumns(value?.tasks?.columns)
  const alias = value => typeof value === 'string' && /^[A-Za-z0-9_.-]+$/.test(value) && value !== 'plugins'
  if (Array.isArray(value?.repository?.enabledAliases)) result.repository.enabledAliases = [...new Set(value.repository.enabledAliases.filter(alias))]
  if (alias(value?.repository?.defaultAlias)) result.repository.defaultAlias = value.repository.defaultAlias
  return result
}
let saved
try { saved = JSON.parse(localStorage.getItem('tactic_stream.preferences') || 'null') } catch { /* Native defaults. */ }
export const preferences = reactive(normalizePreferences(saved))
export function savePreferencePage(page, value) {
  const next = normalizePreferences({ ...preferences, [page]:value })
  localStorage.setItem('tactic_stream.preferences', JSON.stringify(next))
  Object.assign(preferences[page], next[page])
}
