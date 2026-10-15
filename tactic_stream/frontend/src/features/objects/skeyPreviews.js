// Handler SkeyPreviewController._placeholder, before the protected server read.
export function skeyPlaceholder(searchKey, status = 'loading') {
  let type = '', title = 'TACTIC item'
  try { const url = new URL(searchKey); type = url.hostname + url.pathname; title = url.searchParams.get('code') || url.searchParams.get('id') || title } catch { /* Malformed links get a per-card server error. */ }
  const kind = { 'sthpw/task': 'task', 'sthpw/snapshot': 'snapshot', 'sthpw/file': 'file', 'sthpw/note': 'note', 'sthpw/message_log': 'message', 'sthpw/login': 'user', 'sthpw/project': 'project' }[type] || (type.endsWith('/th_knowledge_article') ? 'knowledge' : 'sobject')
  return { searchKey, status, kind, title, error: status === 'error' ? 'Link preview is unavailable' : '' }
}
