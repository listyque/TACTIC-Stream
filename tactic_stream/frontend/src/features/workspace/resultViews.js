// Original Handler view_state / results_organization names are persisted as-is.
export const defaultResultView = 'continious'
export const resultViews = [
  { value: 'continious', label: 'Continuous tree', icon: 'MDI_FORMAT_LIST_BULLETED' },
  { value: 'tiles', label: 'Cards', icon: 'MDI_VIEW_DASHBOARD' },
  { value: 'table', label: 'Table', icon: 'MDI_TABLE' },
  { value: 'compact', label: 'Compact rows', icon: 'MDI_VIEW_LIST' },
  { value: 'splitted_vertical', label: 'Versions on the right', icon: 'MDI_VIEW_COLUMN' },
  { value: 'splitted_horizontal', label: 'Versions at the bottom', icon: 'MDI_VIEW_AGENDA' },
]
export const resultGroups = [
  { value: 'none', label: 'No grouping', icon: 'MDI_FORMAT_LIST_BULLETED' },
  { value: 'status', label: 'SObject status', icon: 'FAS_OBJECT_GROUP' },
  { value: 'pipeline', label: 'Pipeline', icon: 'MDI_COGS' },
]
export function groupRecords(records, mode) {
  if (mode === 'none') return [{ key: '', label: '', records }]
  const groups = new Map()
  for (const record of records) {
    const value = mode === 'pipeline' ? record.pipeline_code || '' : record.status || record.state || ''
    if (!groups.has(value)) groups.set(value, { key: value,
      label: mode === 'pipeline' ? value || 'No pipeline' : value || 'No status', records: [] })
    groups.get(value).records.push(record)
  }
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })
  return [...groups.values()].sort((a, b) => !a.key ? 1 : !b.key ? -1 : collator.compare(a.label, b.label))
}
