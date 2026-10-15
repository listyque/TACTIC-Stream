// ScriptCodeEditor.qml / script_editor_features.edit_command (EPL-1.0), UTF-16 browser offsets.
export function editCommand(action, text, start, end, language = 'python') {
  const left = text.lastIndexOf('\n', start - 1) + 1, found = text.indexOf('\n', end), right = found < 0 ? text.length : found
  const block = text.slice(left, right), lines = block.split('\n'), marker = language === 'javascript' ? '//' : '#'
  if (action === 'duplicate') {
    const value = start === end ? '\n' + block : text.slice(start, end), position = start === end ? right : end
    return { text: text.slice(0, position) + value + text.slice(position), start: position + (start === end ? 1 : 0), end: position + value.length }
  }
  if (action === 'delete_line') {
    const a = right === text.length && left > 0 ? left - 1 : left, b = right < text.length ? right + 1 : right
    return { text: text.slice(0, a) + text.slice(b), start: a, end: a }
  }
  let replacement
  if (action === 'indent') replacement = lines.map(line => '    ' + line).join('\n')
  else if (action === 'unindent') replacement = lines.map(line => line.startsWith('    ') ? line.slice(4) : line.startsWith('\t') ? line.slice(1) : line.replace(/^ {1,3}/, '')).join('\n')
  else if (action === 'toggle_comment') {
    const remove = lines.filter(line => line.trim()).every(line => line.trimStart().startsWith(marker))
    replacement = lines.map(line => !line.trim() ? line : remove ? line.replace(new RegExp('^(\\s*)' + marker + ' ?'), '$1') : line.replace(/^(\s*)/, '$1' + marker + ' ')).join('\n')
  } else return { text, start, end }
  return { text: text.slice(0, left) + replacement + text.slice(right), start: left, end: left + replacement.length }
}

export function findMatches(text, query, { regex = false, caseSensitive = false, wholeWord = false } = {}) {
  if (!query) return []
  let pattern = regex ? query : query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  if (wholeWord) pattern = '\\b(?:' + pattern + ')\\b'
  try { return [...text.matchAll(new RegExp(pattern, caseSensitive ? 'g' : 'gi'))].filter(match => match[0].length).map(match => ({ start: match.index, end: match.index + match[0].length })) }
  catch { return [] }
}

// Browser JavaScript fallback; Python uses the native server AST analysis.
export function documentSymbols(text, language) {
  const pattern = language === 'javascript' ? /^[ \t]*(?:(?:export|async)[ \t]+)*(function|class)[ \t]+([\w$]+)/gm : /^[ \t]*(?:async[ \t]+)?(def|class)[ \t]+(\w+)/gm
  return [...text.matchAll(pattern)].map(match => ({ name: match[2], kind: match[1], position: match.index + match[0].indexOf(match[2]), line: text.slice(0, match.index).split('\n').length }))
}

export function completions(text, cursor, language, apiMethods = []) {
  const prefix = /[\w$]*$/.exec(text.slice(0, cursor))[0]
  const names = language === 'javascript' ? 'async await const let function return if else for while class import export new try catch throw Promise console context project searchType searchKeys rpc refresh' : 'def class return if elif else for while import from as try except finally raise with pass True False None print len range str int dict list set tuple enumerate sorted server Search SearchType'
  const server = language === 'python' && /\bserver\.\w*$/.test(text.slice(0, cursor))
  const candidates = server ? apiMethods : [...names.split(' '), ...(text.match(/\b[A-Za-z_][\w$]*\b/g) || [])]
  return [...new Set(candidates)].filter(name => name.startsWith(prefix) && name !== prefix).sort().slice(0, 200).map(name => ({ name, start: cursor - prefix.length, end: cursor }))
}
