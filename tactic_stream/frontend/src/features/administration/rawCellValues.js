export function cellText(value) {
  return value == null ? '' : typeof value === 'string' ? value : JSON.stringify(value)
}

export function cellKind(type) {
  type = (type || '').trim().toLowerCase()
  if (/\b(tinyint|smallint|bigint|int(?:eger|[248])?|serial|bigserial|smallserial)\b/.test(type)) return 'integer'
  if (/^bool/.test(type)) return 'boolean'
  if (/^(numeric|decimal)/.test(type)) return 'decimal'
  if (/^(real|float|double)/.test(type)) return 'float'
  if (/^jsonb?\b/.test(type)) return 'json'
  return 'text'
}

export function cellValue(text, type, mode = 'value') {
  if (mode === 'null') return null
  if (mode !== 'value') throw new Error('Invalid cell mode')
  const kind = cellKind(type), trimmed = text.trim()
  if (kind === 'text') return text
  if (kind === 'integer') {
    if (!/^[+-]?\d+$/.test(trimmed)) throw new Error('Invalid integer')
    const value = BigInt(trimmed), number = Number(value)
    return Number.isSafeInteger(number) ? number : value.toString()
  }
  if (kind === 'boolean') {
    if (['true', '1'].includes(trimmed.toLowerCase())) return true
    if (['false', '0'].includes(trimmed.toLowerCase())) return false
    throw new Error('Invalid boolean')
  }
  if (kind === 'json') {
    JSON.parse(text, (_key, value) => {
      if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Invalid JSON number')
      return value
    })
    return text
  }
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) throw new Error('Invalid number')
  if (kind === 'decimal') return trimmed
  const value = Number(trimmed)
  if (!Number.isFinite(value)) throw new Error('Invalid number')
  return value
}
