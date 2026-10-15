import { appearance } from './appearance.js'

const catalogs = import.meta.glob('./locales/*.json', { eager: true, import: 'default' })

export function t(source, values = {}) {
  const translated = catalogs[`./locales/${appearance.language}.json`]?.[source]
  const text = typeof translated === 'string' && translated.trim() ? translated : source
  return text.replace(/\{(\w+)\}/g, (placeholder, name) => values[name] ?? placeholder)
}
