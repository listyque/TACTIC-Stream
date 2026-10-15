// Handler ActivityFeedController / ActivityEventCard.qml; no transport or state ownership.
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import { escapeHtml, linkifyPlainText } from '../../controls/richText.js'
import { browserLink } from '../workspace/links.js'

export const feedFilters = [
  { value: 'all', label: 'All', icon: 'select-all' },
  { value: 'my_tasks', label: 'My tasks', icon: 'task' },
  { value: 'my_objects', label: 'My objects', icon: 'inventory-2' },
  { value: 'notes', label: 'Notes', icon: 'notes' },
  { value: 'publications', label: 'Publications', icon: 'snapshot' },
]
export function dateKey(date) { return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-') }
export function dateLabel(value, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!value) return t('All history')
  const date = new Date(value.slice(0, 10) + 'T12:00:00')
  return Number.isNaN(date.getTime()) ? t('No date') : date.toLocaleDateString(appearance.language, options)
}
export function dayLabel(value) {
  if (!value) return t('No date')
  const today = new Date(), yesterday = new Date(); yesterday.setDate(today.getDate() - 1)
  const prefix = value === dateKey(today) ? t('Today') : value === dateKey(yesterday) ? t('Yesterday') : ''
  const suffix = dateLabel(value, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  return prefix ? prefix + ' · ' + suffix : suffix
}
export function timestampLabel(timestamp, now = new Date()) {
  const value = new Date(String(timestamp || '').replace(' ', 'T'))
  if (Number.isNaN(value.getTime())) return ''
  const seconds = (now - value) / 1000
  if (seconds >= 0 && seconds < 60) return t('Just now')
  if (seconds >= 0 && seconds < 3600) return t('{count} min ago', { count: Math.floor(seconds / 60) })
  if (seconds >= 0 && seconds < 86400) return t('{count} h ago', { count: Math.floor(seconds / 3600) })
  if (seconds >= 0 && seconds < 172800) return t('Yesterday')
  if (seconds >= 0 && seconds < 604800) return t('{count} days ago', { count: Math.floor(seconds / 86400) })
  if (seconds >= 0 && seconds < 2629800) return t('{count} wk ago', { count: Math.floor(seconds / 604800) })
  return timestampFullLabel(timestamp)
}
export function timestampFullLabel(timestamp) {
  const value = new Date(String(timestamp || '').replace(' ', 'T'))
  return Number.isNaN(value.getTime()) ? '' : value.toLocaleString(appearance.language, { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}
export function matchesSearch(record, text) {
  const haystack = ['actorLabel', 'actor', 'title', 'detail', 'targetTitle', 'targetTypeTitle', 'itemTitle', 'itemTypeTitle', 'process', 'context', 'statusBefore', 'statusAfter', 'version', 'workDay', 'workHourCategory', 'workHourStatus', 'workHourOwner'].map(key => record[key] || '').join('\n').toLocaleLowerCase()
  return text.toLocaleLowerCase().trim().split(/\s+/).every(word => haystack.includes(word))
}
export function uniqueRecords(records) { return [...new Map(records.slice().reverse().map(row => [row.eventId, row])).values()].reverse() }
export { escapeHtml }
export function safeColor(value) { return /^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(value || '') ? value : '' }
export function compactText(value) { const text = String(value || '').replace(/\s+/g, ' ').trim(); return text.length > 80 ? text.slice(0, 80).trimEnd() + '…' : text }
export function needsExpansion(value) { return /[\r\n]/.test(value || '') || String(value || '').replace(/\s+/g, ' ').trim().length > 80 }
export function changeValue(record, change) {
  if (change.valuesKnown === false) return t('Changed')
  const before = String(change.before || ''), after = String(change.after || '')
  if (record.kind === 'create' && after) return after
  if (record.kind === 'delete' && before) return t('Previous value: {value}', { value: before })
  return before || after ? (before || t('empty')) + ' → ' + (after || t('empty')) : t('Changed')
}
export function eventIcon(record) { return record.relationAction ? 'link' : { publication: 'snapshot', note: 'notes', task: 'task', work_hour: 'schedule', status: 'system-activity', create: 'add', delete: 'delete', change: 'edit' }[record.kind] || 'activity-feed' }
export function eventSentence(row, expanded) {
  const html = value => escapeHtml(value).replace(/\r?\n/g, '<br>')
  const link = (value, action, enabled) => enabled ? '<a href="#' + action + '" data-action="' + action + '">' + html(value) + '</a>' : html(value)
  const colored = (value, color) => safeColor(color) ? '<span data-color="' + safeColor(color) + '">' + html(value) + '</span>' : html(value)
  const semantic = (value, color) => colored((safeColor(color) ? '● ' : '') + value, color)
  const shortType = value => String(value || '').split('/').at(-1).replaceAll('_', ' ')
  const reference = (item = false) => {
    const title = (item ? row.itemTitle : row.targetTitle) || t('the related object')
    const type = item ? row.itemTypeTitle || ({ 'sthpw/task': t('Task'), 'sthpw/note': t('Note'), 'sthpw/snapshot': t('Snapshot') }[row.itemType]) || shortType(row.itemType) : row.targetTypeTitle || (row.relationAction ? '' : shortType(row.targetType))
    return (type ? semantic(type, item ? row.itemTypeColor : row.typeColor) + ' / ' : '') + link(title, item ? 'activity' : 'target', item ? !!row.searchKey : !!row.targetSearchKey)
  }
  const target = reference(), processName = row.process || String(row.context || '').split('/')[0]
  const process = processName ? t(' in process {process}', { process: '<b>' + semantic(processName, row.processColor) + '</b>' }) : ''
  const context = row.context && row.context !== processName ? t(', context {context}', { context: '<b>' + html(row.context) + '</b>' }) : ''
  const detail = linkifyPlainText(expanded ? row.detail : compactText(row.detail), browserLink)
  const action = link(t(row.kind === 'note' ? 'Open note' : row.kind === 'task' ? 'Open task' : 'Open details'), 'activity', !!row.searchKey)
  if (row.relationAction) return t(row.relationAction === 'link' ? 'Linked {item} to {target}.' : 'Removed the link between {item} and {target}.', { item: reference(true), target })
  if (row.kind === 'publication') {
    const raw = String(row.version ?? ''), version = /^\d+$/.test(raw) ? 'v' + raw.padStart(3, '0') : raw
    return t('Committed snapshot {item} to {target}{process}{context}{version}.{comment}', { item: link(row.itemTitle || row.itemCode || t('snapshot'), 'activity', !!row.searchKey), target, process, context,
      version: version ? t(', version {version}', { version: '<b>' + html(version) + '</b>' }) : '', comment: detail ? t(' Comment: “{detail}”', { detail }) : '' })
  }
  if (row.kind === 'note') return t('Added a note to {target}{process}{context}: {detail} {action}', { target, process, context, detail: detail || t('No text'), action })
  if (row.kind === 'task') return t(row.serverGenerated ? 'Created task for {target}{process}{context}: {status}' : 'Updated task for {target}{process}{context}: {status}', { target, process, context, status: row.statusAfter ? '<b>' + colored(row.statusAfter, row.statusAfterColor) + '</b>' : detail || action })
  if (row.kind === 'status') return row.statusBefore || row.statusAfter ? t('Changed status for {target}{process}{context}: {before} → {after}.', { target, process, context, before: '<b>' + colored(row.statusBefore || '—', row.statusBeforeColor) + '</b>', after: '<b>' + colored(row.statusAfter || '—', row.statusAfterColor) + '</b>' }) : t('Updated the status of {target}{process}{context}: {detail}', { target, process, context, detail: detail || action })
  if (row.kind === 'create' || row.kind === 'delete') return row.itemType ? t(row.kind === 'create' ? 'Created {item} for {target}.' : 'Deleted {item} from {target}.', { item: reference(true), target }) : t(row.kind === 'create' ? 'Created object: {target}.' : 'Deleted object: {target}.', { target })
  if (row.kind === 'change') return t('Updated {target}.{detail}', { target, detail: (row.changes || []).length || !detail ? '' : ' ' + detail })
  if (row.kind === 'work_hour') {
    const hours = t('{hours} h', { hours: Number(row.hours || 0).toLocaleString(appearance.language, { maximumFractionDigits: 2 }) })
    const owner = row.workHourOwner && row.workHourOwner !== row.actor ? t(' for user {user}', { user: '<b>' + html(row.workHourOwner) + '</b>' }) : ''
    const sentence = row.workHourAction === 'delete' ? 'Deleted a {hours} work-hours entry{owner} for {target}{process} on {date} ({category}).' : row.workHourAction === 'change' ? 'Updated work hours to {hours}{owner} for {target}{process} on {date} ({category}, {status}).' : 'Logged {hours}{owner} for {target}{process} on {date} ({category}, {status}).'
    return t(sentence, { hours, owner, target, process, date: html(dateLabel(row.workDay)), category: t(row.workHourCategory === 'overtime' ? 'Overtime' : 'Regular'), status: t(String(row.workHourStatus || '').toLowerCase() === 'approved' ? 'Approved' : 'Pending') }) + (detail ? t(' Comment: “{detail}”', { detail }) : '')
  }
  return detail || html(expanded ? row.title : compactText(row.title))
}
