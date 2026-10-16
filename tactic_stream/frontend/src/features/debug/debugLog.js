// Handler DebugLogController / compact session schema v1, EPL-1.0.
import { reactive, shallowReactive, watch } from 'vue'
import { configurationPreview } from '../configuration/preferences.js'
import { randomId as newSessionId } from '../../controls/identity.js'

export const levels = ['LOG', 'INFO', 'WARNING', 'MISSING', 'EXCEPTION', 'ERROR', 'CRITICAL', 'API']
export const sessionFields = { eventId: 'id', timestamp: 't', level: 'l', message: 'm', module: 'o', functionName: 'f', line: 'n', group: 'g', source: 's', command: 'c', stacktrace: 'x', duration: 'd', sizeKb: 'z', thread: 'h', details: 'e' }
const settingsKey = 'tactic_stream.debug_log'
let saved = {}
try { saved = JSON.parse(localStorage.getItem(settingsKey) || '{}') } catch { /* Native defaults. */ }
export const debugSettings = reactive({ recordingLevels: Array.isArray(saved?.recordingLevels) ? levels.filter(level => saved.recordingLevels.includes(level)) : ['ERROR', 'CRITICAL'], groupWidth: Math.max(170, Math.min(520, Number(saved?.groupWidth) || 230)), detailHeight: Math.max(110, Math.min(620, Number(saved?.detailHeight) || 220)) })
export const debugLog = shallowReactive({ entries: [], sessionId: newSessionId(), started: new Date().toISOString(), storageError: '' })
let sequence = 0, database = null
let serverContext = null
const secretKeys = /password|passwd|secret|token|ticket|authorization|cookie|api[_-]?key|private[_-]?key/i
const secrets = new Set()

export function setServerDebugContext(scope) {
  serverContext = scope?.ticket ? { ticket:scope.ticket, project:scope.project || '' } : null
  if (serverContext) remember(serverContext.ticket)
}
function persistError(record, scope) {
  if (!scope?.ticket || !['ERROR','CRITICAL'].includes(record.level)) return
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(),3000)
  const message = JSON.stringify(redact({ session:debugLog.sessionId, timestamp:record.timestamp,
    path:location.pathname || '', viewport:{width:globalThis.innerWidth || 0,height:globalThis.innerHeight || 0},
    group:record.group, message:record.message.slice(0,8192), stacktrace:record.stacktrace.slice(0,8192), details:record.details.slice(0,8192) }))
  // Diagnostics have no retry queue and never pass through the API logger again.
  fetch('/admin/rpc',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
    body:JSON.stringify({method:'log',args:[scope,'error',message],kwargs:{category:record.group || 'browser/error'}})})
    .catch(()=>{}).finally(()=>clearTimeout(timer))
}

watch(debugSettings, () => {
  if (configurationPreview.value) return
  try { localStorage.setItem(settingsKey, JSON.stringify(debugSettings)) }
  catch { debugLog.storageError = 'Debug Log settings could not be saved.' }
})

function remember(value, active = new Set()) {
  if (typeof value === 'string' && value && value !== '<REDACTED>') secrets.add(value)
  if (value && typeof value === 'object' && !active.has(value)) { active.add(value); for (const item of Object.values(value)) remember(item, active); active.delete(value) }
}
export function redact(value, active = new Set()) {
  if (value && typeof value === 'object') {
    if (active.has(value)) return '<recursive reference>'
    active.add(value)
    try {
      if (Array.isArray(value)) return value.map(item => redact(item, active))
      return Object.fromEntries(Object.entries(value).map(([key, item]) => {
        if (secretKeys.test(key)) { remember(item); return [key, '<REDACTED>'] }
        return [key, redact(item, active)]
      }))
    } finally { active.delete(value) }
  }
  if (typeof value === 'string') { for (const secret of secrets) value = value.replaceAll(secret, '<REDACTED>') }
  return value
}
export function requestPayload(payload) {
  // The legacy get_ticket contract carries credentials positionally.
  if (payload?.method === 'get_ticket') {
    remember(payload.args?.[1])
    return redact({ ...payload, args: [payload.args?.[0], '<REDACTED>', ...payload.args.slice(2)] })
  }
  const result = redact(payload)
  return redact(result)
}
function label() { return debugLog.started.replace('T', ' ').slice(0, 19) }
async function db() {
  if (!database) database = new Promise((resolve, reject) => {
    const request = indexedDB.open('tactic_stream.debug_log', 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore('sessions', { keyPath: 'id' })
      request.result.createObjectStore('events', { keyPath: ['session', 'eventId'] }).createIndex('session', 'session')
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
    request.onblocked = () => reject(new Error('Debug Log history is unavailable.'))
  })
  return database
}
async function write(callback) {
  const connection = await db()
  return new Promise((resolve, reject) => {
    const transaction = connection.transaction(['sessions', 'events'], 'readwrite')
    transaction.oncomplete = resolve
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
    callback(transaction.objectStore('sessions'), transaction.objectStore('events'))
  })
}
async function read(store, query) {
  const connection = await db()
  return new Promise((resolve, reject) => {
    const request = query(connection.transaction(store).objectStore(store))
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}
function storageFailed() { debugLog.storageError = 'Debug Log history is unavailable. Live events remain in memory.' }
export async function savedSessions() { return (await read('sessions', store => store.getAll())).sort((a, b) => b.updated.localeCompare(a.updated)) }
export async function sessionRecords(id) { return (await read('events', store => store.index('session').getAll(id))).map(({ session, ...record }) => record) }

export function logEvent(values, scope = serverContext, persist = true) {
  const record = redact({ eventId: ++sequence, timestamp: new Date().toISOString(), level: 'LOG', message: '', module: '', functionName: '', line: 0, group: '', source: 'Browser', command: '', stacktrace: '', duration: 0, sizeKb: 0, thread: 'Main', details: '', ...values })
  if (persist) persistError(record,scope)
  if (!debugSettings.recordingLevels.includes(values.level)) return
  const old = debugLog.entries.length === 10000 ? debugLog.entries[0] : null
  debugLog.entries = [...debugLog.entries.slice(-9999), record]
  const id = debugLog.sessionId
  write((sessions, events) => {
    sessions.put({ id, label: label(), updated: record.timestamp })
    events.put({ session: id, ...record })
    if (old) events.delete([id, old.eventId])
  }).catch(storageFailed)
}
export function logRequest(url, payload, response, error, duration) {
  if (payload?.method === 'log') return
  const safe = requestPayload(payload)
  if (payload?.method === 'get_ticket' && response?.result) remember(response.result)
  if (!error && !debugSettings.recordingLevels.includes('API')) return
  const details = JSON.stringify(redact({ request: safe, response }), null, 2)
  const body = JSON.stringify(safe)
  let command = 'import json\nfrom urllib.request import Request, urlopen\n\npayload = json.loads(' + JSON.stringify(body) + ')\n# Replace <REDACTED> with your own ticket or credentials.\nrequest = Request(' + JSON.stringify(location.origin + url) + ', data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})\nwith urlopen(request) as response:\n    print(response.read().decode("utf-8"))'
  if (safe.file && url.endsWith('/UploadServer/')) command = `from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen

# Replace <FILE_PATH> and <REDACTED> with your file and ticket.
file = Path("<FILE_PATH>")
boundary = uuid4().hex
filename = file.name.replace('"', '%22').replace('\\r', '%0D').replace('\\n', '%0A')
body = (f'--{boundary}\\r\\nContent-Disposition: form-data; name="login_ticket"\\r\\n\\r\\n<REDACTED>\\r\\n'
        f'--{boundary}\\r\\nContent-Disposition: form-data; name="file"; filename="{filename}"\\r\\n'
        'Content-Type: application/octet-stream\\r\\n\\r\\n').encode("utf-8")
body += file.read_bytes() + f'\\r\\n--{boundary}--\\r\\n'.encode("ascii")
request = Request(${JSON.stringify(location.origin + url)}, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
with urlopen(request) as response:
    print(response.read().decode("utf-8"))`
  const scope = payload.ticket ? {ticket:payload.ticket,project:payload.project || ''} : payload.args?.[0]?.ticket ? {ticket:payload.args[0].ticket,project:payload.args[0].project || ''} : null
  logEvent({ level: error ? 'ERROR' : 'API', message: error ? error.message : (payload.method || url), module: 'api.js', functionName: payload.method || url, group: url.slice(1).replaceAll('-', '_'), source: 'TACTIC API', duration, sizeKb: new TextEncoder().encode(details).length / 1024, details, command, stacktrace: error?.stack || '' },scope,url !== '/admin/server-updates')
}
export async function clearLive() {
  debugLog.entries = []
  const id = debugLog.sessionId
  try { await write((sessions, events) => { events.delete(IDBKeyRange.bound([id, 0], [id, Number.MAX_SAFE_INTEGER])); sessions.delete(id) }) }
  catch { storageFailed() }
}
export async function forgetSessions() {
  debugLog.entries = []; sequence = 0; secrets.clear()
  debugLog.sessionId = newSessionId(); debugLog.started = new Date().toISOString()
  try { await write((sessions, events) => { sessions.clear(); events.clear() }) }
  catch { storageFailed() }
}
export function parseSession(text) {
  const lines = text.replace(/^\uFEFF/, '').split(/\r?\n/)
  let header
  try { header = JSON.parse(lines.shift()) } catch { throw new Error('Invalid Debug Log session header') }
  if (JSON.stringify(header) !== '{"v":1}') throw new Error('Unsupported Debug Log session schema')
  const records = [], ids = new Set()
  for (const [index, line] of lines.entries()) {
    if (!line.trim()) continue
    let values
    try { values = JSON.parse(line) } catch { const error = new Error('Invalid JSONL record'); error.line = index + 2; throw error }
    if (!values || Array.isArray(values) || typeof values !== 'object') continue
    const record = Object.fromEntries(Object.entries(sessionFields).map(([field, key]) => [field, values[key] ?? '']))
    for (const field of ['eventId', 'line', 'duration', 'sizeKb']) {
      record[field] = Number(record[field] || (field === 'eventId' ? records.length + 1 : 0))
      if (!Number.isFinite(record[field]) || record[field] < 0) throw new Error('Invalid Debug Log event')
    }
    if (!Number.isSafeInteger(record.eventId) || ids.has(record.eventId)) throw new Error('Invalid Debug Log event')
    ids.add(record.eventId)
    for (const field of Object.keys(sessionFields).filter(key => !['eventId', 'line', 'duration', 'sizeKb'].includes(key))) if (typeof record[field] !== 'string') throw new Error('Invalid Debug Log event')
    record.level = levels.includes(record.level.toUpperCase()) ? record.level.toUpperCase() : 'LOG'
    records.push(redact(record))
  }
  return records.slice(-10000)
}
export async function importSession(file) {
  const session = debugLog.sessionId
  if (!file.name.toLowerCase().endsWith('.jsonl')) throw new Error('A compact Debug Log session (.jsonl) is required.')
  if (file.size > 32 * 1024 * 1024) throw new Error('Debug Log session exceeds 32 MB.')
  const records = parseSession(await file.text()), id = newSessionId()
  if (session !== debugLog.sessionId) throw new DOMException('Session ended', 'AbortError')
  await write((sessions, events) => {
    if (session !== debugLog.sessionId) return
    sessions.put({ id, label: file.name, updated: new Date().toISOString() })
    for (const record of records) events.put({ session: id, ...record })
  })
  if (session !== debugLog.sessionId) throw new DOMException('Session ended', 'AbortError')
  return { id, records }
}
export function exportSession(records) {
  return JSON.stringify({ v: 1 }) + '\n' + records.map(record => JSON.stringify(Object.fromEntries(Object.entries(sessionFields).filter(([field]) => ![undefined, null, '', false, 0].includes(record[field])).map(([field, key]) => [key, record[field]])))).join('\n') + '\n'
}
export function formatEvent(record) {
  return `[${record.timestamp}] [${record.level}] [${record.group}]\n${record.message}\n${record.module} / ${record.functionName}():${String(record.line || 0).padStart(4, '0')}` + (record.details ? '\n\nDetails:\n' + record.details : '') + (record.command ? '\n\nRuntime command:\n' + record.command : '') + (record.stacktrace ? '\n\nStacktrace:\n' + record.stacktrace : '')
}

export function installDebugLogging() {
  for (const [method, level] of Object.entries({ log: 'LOG', info: 'INFO', warn: 'WARNING', error: 'ERROR', debug: 'LOG' })) {
    const original = console[method].bind(console)
    console[method] = (...args) => {
      original(...args)
      if (level !== 'ERROR' && !debugSettings.recordingLevels.includes(level)) return
      try { logEvent({ level, source: 'Browser console', module: 'console', functionName: method, group: 'browser/console', message: args.map(value => value instanceof Error ? value.message : typeof value === 'string' ? value : JSON.stringify(redact(value))).join(' '), stacktrace: args.find(value => value instanceof Error)?.stack || '' }) }
      catch { debugLog.storageError = 'A message could not be recorded in Debug Log.' }
    }
  }
  window.addEventListener('error', event => { if (event.error) logEvent({ level: 'ERROR', source: 'Browser', module: event.filename, line: event.lineno, group: 'browser/error', message: event.message, stacktrace: event.error.stack || '' }) })
  window.addEventListener('unhandledrejection', event => logEvent({ level: 'ERROR', source: 'Browser', group: 'browser/error', message: String(event.reason?.message || event.reason), stacktrace: event.reason?.stack || '' }))
}
