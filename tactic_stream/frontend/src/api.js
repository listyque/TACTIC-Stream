import { debugLog, logRequest } from './features/debug/debugLog.js'
import { notify } from './features/activity/notifications.js'
import { shallowReactive } from 'vue'
import { backgroundRequest } from './features/connection/updateRequests.js'

export const requestActivity = shallowReactive({ pending: [] })
export function resetRequestActivity() { requestActivity.pending = [] }
export function beginActivity(ticket, message = 'Working…') {
  if (!ticket) return
  const entry = { ticket, message }
  requestActivity.pending = [...requestActivity.pending, entry]
  return entry
}
export function endActivity(entry) {
  if (entry) requestActivity.pending = requestActivity.pending.filter(item => item !== entry)
}

export async function rpc(method, args = [], kwargs = {}, quiet = false, background = false) {
  const payload = { method, args, kwargs }
  return background ? backgroundPost('/admin/rpc', payload) : post('/admin/rpc', payload, undefined, quiet)
}

export function scriptEditor(action, ticket, project, values = {}) {
  return post(`/admin/script-editor/${action}`, { ticket, project, ...values }, undefined, action === 'analyse')
}

export function activityFeed(ticket, project, values = {}, quiet = false) {
  const payload = { ticket, project, ...values }
  return quiet ? backgroundPost('/admin/activity-feed', payload) : post('/admin/activity-feed', payload)
}

export function serverUpdates(ticket, project, values = {}, signal) {
  return post('/admin/server-updates', { ticket, project, ...values }, AbortSignal.any([AbortSignal.timeout(30000), ...(signal ? [signal] : [])]), true)
}

export function navigationLink(ticket, project, link) {
  return post('/admin/navigation-link', { ticket, project, link })
}

export function linkPreviews(ticket, project, keys) {
  return backgroundPost('/admin/navigation-link', { ticket, project, keys })
}

export async function sessionAction(action, ticket) {
  return post(`/admin/session/${action}`, { ticket })
}

export async function serverConfiguration(ticket) {
  return post('/admin/configuration', { ticket })
}

export function rawDatabase(action, ticket, project, values = {}) {
  return post('/admin/raw-database/' + action, { ticket, project, ...values })
}

export async function interfaceDefinition(ticket, project, search_type, view = 'table') {
  return post('/admin/interface', { ticket, project, search_type, view })
}

export function tableCells(ticket, project, search_type, view, search_keys) {
  return post('/admin/table-cells', { ticket, project, search_type, view, search_keys })
}

export function resultItems(ticket, project, search_type, search_keys, values = {}) {
  return post('/admin/result-items', { ticket, project, search_type, search_keys, ...values })
}

export async function projectNavigation(ticket, project) {
  return post('/admin/navigation', { ticket, project })
}

export async function projectCatalog(ticket) {
  return post('/admin/project-catalog', { ticket, project: 'admin' })
}

export async function projectCreationCatalog(ticket) {
  return post('/admin/project-creation', { ticket, project: 'admin' })
}

export async function formDefinition(ticket, project, search_type, view, search_key, source_key, relation = {}) {
  const selection = Array.isArray(search_key) ? { search_keys: search_key } : { search_key }
  return post('/admin/form', { ticket, project, search_type, view, ...selection, source_key, ...relation })
}

export async function objectRelations(ticket, project, search_type, search_key) {
  return post('/admin/object-relations', { ticket, project, search_type, search_key })
}

export async function objectDeletion(action, ticket, project, search_type, view, search_key, related_types) {
  const selection = Array.isArray(search_key) ? { search_keys: search_key } : { search_key }
  return post(`/admin/object-deletion/${action}`, { ticket, project, search_type, view, ...selection, related_types })
}

export async function objectStatus(ticket, project, search_type, view, search_keys, operation) {
  return post('/admin/object-status', { ticket, project, search_type, view, search_keys, operation })
}

export async function widgetConfiguration(action, ticket, project, search_type, view, values = {}) {
  return post(`/admin/widget-configuration/${action}`, { ticket, project, search_type, view, ...values })
}

export async function uploadFormFile(ticket, project, file, { signal, filename } = {}) {
  const body = new FormData()
  body.append('login_ticket', ticket)
  body.append('file', file, filename || file.name)
  const url = `/tactic/${encodeURIComponent(project)}/UploadServer/`
  const started = performance.now(), session = debugLog.sessionId
  const activity = beginActivity(ticket, 'Uploading')
  let data, failure
  try {
    const response = await fetch(url, { method: 'POST', body, cache: 'no-store', signal })
    data = await response.json().catch(() => null)
    if (!response.ok || !Array.isArray(data) || data.length !== 1 || typeof data[0] !== 'string') {
      const error = new Error(data?.error || 'File upload failed.')
      error.status = response.ok ? 502 : response.status
      throw error
    }
    return data[0].replaceAll('\\', '/').split('/').pop()
  } catch (error) { failure = error; throw error }
  finally { endActivity(activity); recordRequest(url, { ticket, project, file: { name: file.name, type: file.type, size: file.size } }, data, failure, started, session) }
}

export async function messageFileRequest(ticket, project, values, file, channel = 'messages') {
  const upload = !!file, url = '/admin/' + channel + '/' + (upload ? 'upload' : 'file')
  const payload = { ticket, project, ...values }, started = performance.now(), session = debugLog.sessionId
  const activity = beginActivity(ticket, upload ? 'Uploading' : 'Downloading')
  let data, failure
  try {
    const body = upload ? new FormData() : JSON.stringify(payload)
    if (upload) { for (const [key, value] of Object.entries(payload)) body.append(key, value); body.append('file', file) }
    const response = await fetch(url, { method: 'POST', body, headers: upload ? undefined : { 'Content-Type': 'application/json' }, cache: 'no-store' })
    if (!response.ok) {
      data = await response.json(); const error = new Error(data.error || 'File request failed.'); error.code = data.error_code; error.status = response.status; throw error
    }
    if (upload) { data = await response.json(); return data.result }
    const blob = await response.blob(); data = { size: blob.size, type: blob.type }; return blob
  } catch (error) { failure = error; throw error }
  finally { endActivity(activity); recordRequest(url, { ...payload, ...(upload ? { file: { name: file.name, size: file.size } } : {}) }, data, failure, started, session, true) }
}

export async function saveServerConfiguration(ticket, changes, revision) {
  return post('/admin/configuration/save', { ticket, changes, revision })
}

function backgroundPost(url, payload) {
  return backgroundRequest(JSON.stringify([url, payload]), signal => post(url, payload, signal, true))
}

async function post(url, payload, signal, quiet = false) {
  const started = performance.now(), session = debugLog.sessionId
  const activity = quiet ? undefined : beginActivity(payload.ticket || payload.args?.[0]?.ticket)
  let data, failure
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      cache: 'no-store',
      signal,
    })
    data = await response.json()
    if (!response.ok) {
      const error = new Error(data.error || 'Request failed.')
      error.status = response.status
      error.code = data.error_code
      error.field = data.error_field
      throw error
    }
    return data.result
  } catch (error) { failure = error; throw error }
  finally { endActivity(activity); recordRequest(url, payload, data, failure, started, session, quiet) }
}

function recordRequest(url, payload, data, failure, started, session, quiet = false) {
  if (session === debugLog.sessionId) {
    try { logRequest(url, payload, data, failure, (performance.now() - started) / 1000) }
    catch { debugLog.storageError = 'A request could not be recorded in Debug Log.' }
    // Shared polling reports errors only after its native silent retries are exhausted.
    if (url === '/admin/server-updates' || url.includes('/UploadServer/') || payload.method === 'simple_checkin') return
    if (quiet && failure && (failure instanceof TypeError || ['TimeoutError', 'AbortError'].includes(failure.name) || failure.code === 'updates_unavailable')) return
    if (failure) notify('error', failure instanceof TypeError ? 'Unable to reach the server.' : failure.message, '', 'server')
    else if (!quiet && (['execute_cmd', 'execute_python_script', 'insert', 'update', 'delete_sobject', 'retire_sobject', 'reactivate_sobject'].includes(payload.method)
      || /\/(save|apply|create|delete|commit|activate|run|execute)$/.test(url))) {
      notify('complete', 'Server operation completed', payload.method || url, 'server')
    }
  }
}

export function sidebarRequest(action, ticket, project, values = {}) {
  return post('/admin/sidebar/' + action, { ticket, project, ...values })
}

export function workspaceLayouts(action, ticket, project, values = {}) {
  return post('/admin/workspace-layout/' + action, { ticket, project, ...values })
}

export function scriptShelf(action, ticket, project, values = {}) {
  return post('/admin/script-shelf/' + action, { ticket, project, ...values })
}

export function searchConfiguration(action, ticket, project, search_type, values = {}, quiet = false) {
  return post('/admin/search-configuration/' + action, { ticket, project, search_type, ...values }, undefined, quiet)
}

export function securityGroups(action, ticket, values = {}) {
  return post('/admin/security-groups/' + action, { ticket, project: 'sthpw', ...values })
}

export function securityRules(action, ticket, project, values = {}) {
  return post('/admin/security-rules/' + action, { ticket, project, ...values })
}

export function securityUsers(action, ticket, values = {}) {
  return post('/admin/security-users/' + action, { ticket, project: 'sthpw', ...values })
}

export function columnsEditor(action, ticket, project, values = {}) {
  return post('/admin/columns-editor/' + action, { ticket, project, ...values })
}

export function transactionDetails(ticket, project, searchKey) {
  return post('/admin/transaction-log/details', { ticket, project, search_key: searchKey })
}

export function messagesRequest(action, ticket, project, values = {}) {
  const url = '/admin/messages/' + action, payload = { ticket, project, ...values }
  return ['list', 'history'].includes(action) ? backgroundPost(url, payload) : post(url, payload, undefined, true)
}
export function knowledgeRequest(action, ticket, project, values = {}) {
  return post('/admin/knowledge/' + action, { ticket, project, ...values }, undefined, true)
}

export function userProfile(action, ticket, project, values = {}) {
  return post('/admin/user-profile/' + action, { ticket, project, ...values })
}
export async function userAvatar(ticket, project, login, revision, token, file) {
  const url = '/admin/user-profile/avatar', payload = { ticket, project, login, revision, token }
  const activity = beginActivity(ticket, 'Uploading'), started = performance.now(), session = debugLog.sessionId
  let data, failure
  try {
    const body = new FormData()
    for (const [key, value] of Object.entries(payload)) body.append(key, value)
    body.append('file', file)
    const response = await fetch(url, { method: 'POST', body, cache:'no-store' })
    data = await response.json()
    if (!response.ok) { const error = new Error(data.error?.message || data.error || 'Unable to upload avatar'); error.status = response.status; error.code = data.error_code; throw error }
    return data.result
  } catch (error) { failure = error; throw error }
  finally { endActivity(activity); recordRequest(url, { ...payload, file:{name:file.name,size:file.size} }, data, failure, started, session) }
}
