// Shared code-view tokens. Python roles follow TH PythonSyntaxHighlighter.
const keywords = new Set('False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield'.split(' '))

export function xmlTokens(source) {
  const tokens = []; let end = 0
  for (const match of source.matchAll(/<!--[\s\S]*?(?:-->|$)|<!\[CDATA\[[\s\S]*?(?:\]\]>|$)|<\/?[\w:.-]+|\/?>|"[^"\n]*"|'[^'\n]*'|[\w:.-]+(?=\s*=)|&(?:#\w+|\w+);/g)) {
    if (match.index > end) tokens.push({ text: source.slice(end, match.index), role: '' })
    const text = match[0], role = text.startsWith('<!--') ? 'comment' : /^["']/.test(text) || text.startsWith('<![CDATA[') ? 'string' : text.startsWith('<') || text.endsWith('>') ? 'keyword' : text.startsWith('&') ? 'number' : 'type'
    tokens.push({ text, role }); end = match.index + text.length
  }
  if (end < source.length) tokens.push({ text: source.slice(end), role: '' })
  return tokens
}
const builtins = new Set('abs all any bool bytes callable chr dict enumerate filter float format getattr hasattr int isinstance issubclass iter len list map max min next object open ord print property range repr reversed round set setattr slice sorted staticmethod str sum super tuple type zip Exception ValueError TypeError RuntimeError KeyError'.split(' '))
const pattern = /#[^\n]*|(?<!\w)(?:[furb]{1,2})?(?:"""(?:\\[\s\S]|(?!""")[^\\])*?(?:"""|$)|'''(?:\\[\s\S]|(?!''')[^\\])*?(?:'''|$)|"(?:\\[^\n]|[^"\\\n])*(?:"|$)|'(?:\\[^\n]|[^'\\\n])*(?:'|$))|\b(?:0x[\da-f_]+|0b[01_]+|0o[0-7_]+|\d[\d_]*(?:\.[\d_]*)?(?:e[+-]?[\d_]+)?j?)\b|\.[\d_]+(?:e[+-]?[\d_]+)?j?\b|@[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*|\b[A-Za-z_]\w*\b/gi

export function pythonTokens(source, moduleNames = []) {
  const tokens = []
  let end = 0
  let previous = ''
  for (const match of source.matchAll(pattern)) {
    if (match.index > end) tokens.push({ text: source.slice(end, match.index), role: '' })
    const text = match[0]
    const role = text.startsWith('#') ? 'comment' : /^(?:[furb]{0,2})["']/i.test(text) ? 'string'
      : /^[\d.]/.test(text) ? 'number' : text.startsWith('@') ? 'decorator'
      : keywords.has(text) ? 'keyword' : ['def', 'class'].includes(previous) ? 'definition' : moduleNames?.includes(text) ? 'module'
      : ['self', 'cls'].includes(text) ? 'self' : builtins.has(text) ? 'type'
      : /^\s*\(/.test(source.slice(match.index + text.length)) ? 'function' : ''
    tokens.push({ text, role })
    previous = text
    end = match.index + text.length
  }
  if (end < source.length) tokens.push({ text: source.slice(end), role: '' })
  return tokens
}

const jsKeywords = new Set('async await break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield true false null undefined'.split(' '))
export function javascriptTokens(source) {
  const tokens = []; let end = 0, previous = ''
  const expression = /\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\])*(?:"|$)|'(?:\\[\s\S]|[^'\\])*(?:'|$)|`(?:\\[\s\S]|[^`\\])*(?:`|$)|\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|\b[$A-Za-z_][$\w]*\b/gi
  for (const match of source.matchAll(expression)) {
    if (match.index > end) tokens.push({ text: source.slice(end, match.index), role: '' })
    const text = match[0], role = text.startsWith('//') || text.startsWith('/*') ? 'comment' : /^["'`]/.test(text) ? 'string' : /^\d/.test(text) ? 'number' : jsKeywords.has(text) ? 'keyword' : ['function', 'class'].includes(previous) ? 'definition' : /^\s*\(/.test(source.slice(match.index + text.length)) ? 'function' : ''
    tokens.push({ text, role }); previous = text; end = match.index + text.length
  }
  if (end < source.length) tokens.push({ text: source.slice(end), role: '' })
  return tokens
}
