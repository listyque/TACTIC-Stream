// Handler rich_text.linkify_plain_text: user text is escaped, never interpreted as HTML.
const HTML_ESCAPES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
};
const HTML_ESCAPE_RE = /[&<>"']/g;
const SKEY_RE = /skey:\/\/[^\s<>"]+/g;
const LINK_RE = /(?:skey|tactic-search|https?|ftp):\/\/[^\s<>"]+/gi;
const TRAILING_PUNCT_RE = /[.,;:!?\)\]}]+$/;
const INTERNAL_LINK_RE = /^(skey|tactic-search):/i;

export function escapeHtml(value) {
  const text = String(value ?? '');
  if (!HTML_ESCAPE_RE.test(text)) return text;
  HTML_ESCAPE_RE.lastIndex = 0;
  return text.replace(HTML_ESCAPE_RE, (char) => HTML_ESCAPES[char]);
}

// Handler extract_skeys / display_html_without_skeys preserve trailing punctuation.
export function extractSkeys(value) {
  const text = String(value ?? '');
  if (!text.includes('skey://')) return [];
  return [
    ...new Set(
      [...text.matchAll(SKEY_RE)].map((match) =>
        match[0].replace(TRAILING_PUNCT_RE, '')
      )
    )
  ];
}
export function withoutSkeys(value) {
  const text = String(value ?? '');
  if (!text.includes('skey://')) return text.trim();
  return text
    .replace(SKEY_RE, (raw) =>
      raw.slice(raw.replace(TRAILING_PUNCT_RE, '').length)
    )
    .trim();
}

export function linkifyPlainText(value, linkHref = (value) => value) {
  const text = String(value ?? '');
  if (!text.includes('://')) return escapeHtml(text).replace(/\r?\n/g, '<br>');
  let result = '',
    offset = 0;
  for (const match of text.matchAll(LINK_RE)) {
    const target = match[0].replace(TRAILING_PUNCT_RE, '');
    const internal = INTERNAL_LINK_RE.test(target);
    result += escapeHtml(text.slice(offset, match.index));
    result +=
      '<a href="' +
      escapeHtml(linkHref(target)) +
      '"' +
      (internal
        ? ' data-rich-link="' + escapeHtml(target) + '"'
        : ' target="_blank" rel="noopener noreferrer"') +
      '>' +
      escapeHtml(target) +
      '</a>';
    result += escapeHtml(match[0].slice(target.length));
    offset = match.index + match[0].length;
  }
  return (result + escapeHtml(text.slice(offset))).replace(/\r?\n/g, '<br>');
}

export function activateRichLink(event, open) {
  const anchor = event.target.closest('a[data-rich-link]');
  if (
    !anchor ||
    event.button ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.altKey
  )
    return false;
  event.preventDefault();
  open(anchor.dataset.richLink);
  return true;
}
