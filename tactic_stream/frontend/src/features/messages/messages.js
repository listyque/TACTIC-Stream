// MessagesController's identity, UTC timestamps, five-minute author groups and stable paging.
export const messageId = row => row?.__search_key__ || row?.code || ''
export const messageDate = value => new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value || '') ? value : String(value || '').replace(' ', 'T') + 'Z')
export function initials(value) { return String(value || '').trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?' }
export function groupedMessages(rows) {
  const same = (a, b) => a && b && a.login === b.login && Math.abs(messageDate(a.timestamp) - messageDate(b.timestamp)) <= 300000
  return rows.map((row, index) => ({ ...row, groupFirst: !same(rows[index - 1], row), groupLast: !same(row, rows[index + 1]) }))
}
export function mergeMessages(rows) {
  return [...new Map(rows.map(row => [messageId(row), row])).values()].sort((a, b) =>
    String(a.timestamp).localeCompare(String(b.timestamp)) || Number(a.id || 0) - Number(b.id || 0))
}
// Match the server's timestamp/id ordering when a recent page refreshes loaded history.
export function retainOlderMessages(rows, page) {
  const oldest = page.at(-1), present = new Set(page.map(messageId))
  return rows.filter(row => !oldest || row.timestamp < oldest.timestamp || row.timestamp === oldest.timestamp && Number(row.id) < Number(oldest.id) || present.has(messageId(row)))
}
export function canChangeMessage(row, login, privileged, now = Date.now()) {
  if (row.login !== login) return privileged
  const stamp = messageDate(row.timestamp).getTime()
  return Number.isFinite(stamp) && stamp <= now && now - stamp <= 3600000
}
// MessagesConversationList.qml: color depends on the number of recipients.
export function conversationColor(row) { return ['var(--primary)', 'var(--success)', 'var(--cyan)', '#a06bb4', 'var(--yellow)'][Math.min(4, row?.recipients?.length || 0)] }
export function attachmentName(snapshot) {
  let metadata = snapshot.metadata || {}
  if (typeof metadata === 'string') { try { metadata = JSON.parse(metadata) } catch { metadata = {} } }
  return metadata.chatAttachment?.name || snapshot.__files__?.find(file => !['web', 'icon'].includes(file.type))?.file_name || snapshot.code
}
export function messageAttachments(row) {
  return [...new Map([...(row.__attachments__ || []), ...(row.__forwarded_from__?.available ? row.__forwarded_from__.attachments || [] : [])].map(snapshot => [snapshot.code, snapshot])).values()]
}
// MessagesController.conversationAttachments: each occurrence belongs to its message.
export function conversationAttachments(rows, users) {
  return rows.flatMap(row => messageAttachments(row).map(snapshot => ({
    snapshot, messageId: messageId(row), sender: users.find(user => user.login === row.login)?.displayName || row.login,
    timestamp: row.timestamp,
  })))
}
// MessagesView.qml uses binary units with one decimal above bytes.
export function formatFileSize(bytes) {
  const value = Math.max(0, Number(bytes) || 0)
  if (!value) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB'], unit = Math.min(4, Math.floor(Math.log(value) / Math.log(1024))), scaled = value / 1024 ** unit
  return (unit ? scaled.toFixed(1) : Math.round(scaled)) + ' ' + units[unit]
}

// MessageTimelineFrame.qml: one closed contour includes the curved group tail.
export function bubbleContour(width, height, corner, last) {
  const l = 8, t = 2, r = l + width, b = t + height, radius = Math.min(corner, height / 2, width / 2)
  const arc = ` A ${radius} ${radius} 0 0 1 `
  let path = `M ${l + radius} ${t} H ${r - radius}${arc}${r} ${t + radius} V ${b - radius}${arc}${r - radius} ${b} H ${l + radius}`
  path += last ? ` C ${l} ${b} 2 ${b} 2 ${b - 2} C 2 ${b - 4} ${l} ${b - 4} ${l} ${b - radius}` : arc + `${l} ${b - radius}`
  return path + ` V ${t + radius}${arc}${l + radius} ${t} Z`
}

// MessageBodyText.qml's sticker rule; keep its ranges and cluster/count semantics.
export function emojiCount(value) {
  const points = Array.from(String(value || '').trim(), char => char.codePointAt(0))
  let count = 0, clusterOpen = false, afterJoiner = false, pendingRegional = false
  const base = point => point >= 0x1f000 && point <= 0x1faff || point >= 0x2600 && point <= 0x27bf || point >= 0x2190 && point <= 0x21ff || point >= 0x2300 && point <= 0x23ff || point >= 0x25a0 && point <= 0x25ff || [0xa9, 0xae, 0x203c, 0x2049, 0x2122, 0x2139, 0x2b50, 0x2b55, 0x3030, 0x303d, 0x3297, 0x3299].includes(point)
  for (let index = 0; index < points.length; index++) {
    const point = points[index]
    if ([0x20, 0x09, 0x0a, 0x0d].includes(point)) { if (afterJoiner) return 0; clusterOpen = false; pendingRegional = false; continue }
    if (point >= 0x30 && point <= 0x39 || point === 0x23 || point === 0x2a) {
      let next = index + 1
      if (points[next] === 0xfe0f) next++
      if (points[next] !== 0x20e3) return 0
      count++; index = next; clusterOpen = true; continue
    }
    if (point === 0x200d) { if (!clusterOpen) return 0; afterJoiner = true; continue }
    if (point === 0xfe0e || point === 0xfe0f || point === 0x20e3 || point >= 0x1f3fb && point <= 0x1f3ff) { if (!clusterOpen) return 0; continue }
    if (point >= 0x1f1e6 && point <= 0x1f1ff) { if (!pendingRegional) count++; pendingRegional = !pendingRegional; clusterOpen = true; afterJoiner = false; continue }
    pendingRegional = false
    if (!base(point)) return 0
    if (!afterJoiner) count++
    clusterOpen = true; afterJoiner = false
    if (count > 3) return 0
  }
  return !afterJoiner && count <= 3 ? count : 0
}
