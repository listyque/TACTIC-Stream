// Handler rich_text.linkify_plain_text: user text is escaped, never interpreted as HTML.
export function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char])) }

// Handler extract_skeys / display_html_without_skeys preserve trailing punctuation.
export function extractSkeys(value) {
  return [...new Set([...String(value ?? '').matchAll(/skey:\/\/[^\s<>"]+/g)].map(match => match[0].replace(/[.,;:!?\)\]}]+$/, '')))]
}
export function withoutSkeys(value) {
  return String(value ?? '').replace(/skey:\/\/[^\s<>"]+/g, raw => raw.slice(raw.replace(/[.,;:!?\)\]}]+$/, '').length)).trim()
}

export function linkifyPlainText(value, linkHref = value => value) {
  const text = String(value ?? '')
  let result = '', offset = 0
  for (const match of text.matchAll(/(?:skey|tactic-search|https?|ftp):\/\/[^\s<>"]+/gi)) {
    const target = match[0].replace(/[.,;:!?\)\]}]+$/, '')
    const internal = /^(skey|tactic-search):/i.test(target)
    result += escapeHtml(text.slice(offset, match.index))
    result += '<a href="' + escapeHtml(linkHref(target)) + '"' + (internal ? ' data-rich-link="' + escapeHtml(target) + '"' : ' target="_blank" rel="noopener noreferrer"') + '>' + escapeHtml(target) + '</a>'
    result += escapeHtml(match[0].slice(target.length))
    offset = match.index + match[0].length
  }
  return (result + escapeHtml(text.slice(offset))).replace(/\r?\n/g, '<br>')
}

export function activateRichLink(event, open) {
  const anchor = event.target.closest('a[data-rich-link]')
  if (!anchor || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false
  event.preventDefault(); open(anchor.dataset.richLink)
  return true
}
