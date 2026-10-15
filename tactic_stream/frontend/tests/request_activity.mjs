import assert from 'node:assert/strict'
import { rpc, activityFeed, serverUpdates, scriptEditor, uploadFormFile, requestActivity, resetRequestActivity, beginActivity, endActivity } from '../src/api.js'
import { resetNotifications, notificationHistory } from '../src/features/activity/notifications.js'

const original = globalThis.fetch, calls = []
globalThis.fetch = (url, options) => new Promise((resolve, reject) => calls.push({ url, options, resolve, reject }))
const auth = { ticket: 'activity-test-ticket', project: 'admin' }
const answer = (call, result) => call.resolve({ ok: true, json: async () => ({ result }) })
try {
  const first = rpc('query', [auth, 'sthpw/project'])
  const second = rpc('query', [auth, 'sthpw/login'])
  assert.equal(requestActivity.pending.length, 2)
  answer(calls[0], []); await first
  assert.equal(requestActivity.pending.length, 1, 'One completion cannot clear another request')
  calls[1].reject(new TypeError('Network failed'))
  await assert.rejects(second, TypeError)
  assert.equal(requestActivity.pending.length, 0)

  const script = beginActivity(auth.ticket, 'Running…')
  const nested = rpc('query', [auth, 'sthpw/project'])
  answer(calls.at(-1), []); await nested
  assert.deepEqual(requestActivity.pending, [script], 'Script stays busy after its nested request finishes')
  resetRequestActivity()
  const nextScript = beginActivity(auth.ticket, 'Running…')
  endActivity(script)
  assert.deepEqual(requestActivity.pending, [nextScript], 'Late script completion preserves the current operation')
  endActivity(nextScript); endActivity(nextScript)
  assert.equal(requestActivity.pending.length, 0)
  assert.equal(beginActivity(''), undefined)

  const historyCount = notificationHistory.records.length
  const quiet = [serverUpdates(auth.ticket, auth.project), activityFeed(auth.ticket, auth.project, {}, true), rpc('execute_cmd', [auth, 'TaskWorkspaceCmd'], {}, true), scriptEditor('analyse', auth.ticket, auth.project, { source: 'value = 1' })]
  assert.equal(requestActivity.pending.length, 0, 'Background requests never start global progress')
  for (const call of calls.slice(-quiet.length)) { assert(!JSON.stringify(call.options.body).includes('quiet')); answer(call, []) }
  await Promise.all(quiet)
  assert.equal(notificationHistory.records.length, historyCount, 'Quiet success is logged without a completion toast')

  const old = rpc('query', [auth, 'sthpw/project'])
  const oldCall = calls.at(-1)
  resetRequestActivity()
  const current = rpc('query', [{ ...auth, project: 'other' }, 'sthpw/project'])
  const currentCall = calls.at(-1), currentEntry = requestActivity.pending[0]
  answer(oldCall, []); await old
  assert.equal(requestActivity.pending[0], currentEntry, 'Late completion after reset preserves the new request')
  answer(currentCall, []); await current
  assert.equal(requestActivity.pending.length, 0)

  const upload = uploadFormFile(auth.ticket, auth.project, new File(['image'], 'test.png', { type: 'image/png' }))
  assert.equal(requestActivity.pending[0].message, 'Uploading')
  calls.at(-1).resolve({ ok: true, json: async () => ['D:/uploads/test.png'] })
  assert.equal(await upload, 'test.png')
  assert.equal(requestActivity.pending.length, 0)

  const malformed = rpc('query', [auth, 'sthpw/project'])
  calls.at(-1).resolve({ ok: true, json: async () => { throw new SyntaxError('Malformed response') } })
  await assert.rejects(malformed, SyntaxError)
  assert.equal(requestActivity.pending.length, 0)
  const recursive = {}; recursive.self = recursive
  await assert.rejects(rpc('query', [auth, recursive]), TypeError)
  assert.equal(requestActivity.pending.length, 0, 'Serialization failures also release progress')
  const login = rpc('get_ticket', ['admin', 'test-password'])
  assert.equal(requestActivity.pending.length, 0, 'Unauthenticated sign-in is owned by its form')
  answer(calls.at(-1), 'ticket'); await login
  console.log('PASS: foreground/script overlap, nested requests, quiet polling, context reset/late completion, upload, network/JSON/serialization failures and unauthenticated requests')
} finally { globalThis.fetch = original; resetRequestActivity(); resetNotifications() }
