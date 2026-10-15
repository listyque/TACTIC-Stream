// Handler _normalize_task_columns: known keys, unique order, 40..480 px and required Object.
export const taskColumns = [
  ['object', 'Object', 'object'], ['process', 'Task / Process', 'process'], ['status', 'Status', 'status'],
  ['assigned', 'Assignee', 'user'], ['dates', 'Start / Deadline', 'due'], ['progress', 'Progress', ''],
  ['bid_duration', 'Hours', ''], ['notes', 'Notes', ''], ['priority', 'Priority', 'priority'],
  ['milestone_code', 'Milestone', 'milestone'], ['supervisor', 'Supervisor', 'supervisor'],
].map(([key, label, sort], index) => ({ key, label, sort, width:[210,126,138,154,112,94,86,48,96,132,154][index], visible:index < 8,
  group:{ object:'object', process:'process', status:'status', assigned:'user' }[key] || '' }))
export function normalizeColumns(saved) {
  const ordered = [], seen = new Set()
  for (const item of Array.isArray(saved) ? saved : []) {
    const original = taskColumns.find(column => column.key === item?.key)
    if (!original || seen.has(item.key)) continue
    const width = Number(item.width)
    ordered.push({ ...original, width:Number.isFinite(width) ? Math.max(40, Math.min(480, Math.trunc(width))) : original.width,
      visible:item.key === 'object' || (typeof item.visible === 'boolean' ? item.visible : original.visible) })
    seen.add(item.key)
  }
  return [...ordered, ...taskColumns.filter(column => !seen.has(column.key)).map(column => ({ ...column }))]
}
