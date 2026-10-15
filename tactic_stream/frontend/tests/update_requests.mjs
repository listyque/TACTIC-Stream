import assert from 'node:assert/strict'
import { backgroundRequest, setUpdatesAvailable, updateDelay } from '../src/features/connection/updateRequests.js'

let calls = 0, finish
const read = signal => new Promise((resolve, reject) => {
  calls++; finish = resolve
  signal.throwIfAborted()
  signal.addEventListener('abort', () => reject(signal.reason), { once: true })
})
const waiting = Array.from({ length: 100 }, () => backgroundRequest('same context and resource', read))
assert(waiting.every(promise => promise === waiting[0]))
await Promise.resolve(); assert.equal(calls, 1)
setUpdatesAvailable(false)
assert((await Promise.allSettled(waiting)).every(row => row.status === 'rejected' && row.reason.code === 'updates_unavailable'))
for (let i = 0; i < 100; i++) await assert.rejects(backgroundRequest('another resource', read), { code: 'updates_unavailable' })
assert.equal(calls, 1, 'Disconnected readers never enter a retry queue')
setUpdatesAvailable(true)
await Promise.resolve(); assert.equal(calls, 1, 'Reconnection does not replay reads')
const latest = backgroundRequest('same context and resource', read)
await Promise.resolve(); finish('fresh'); assert.equal(await latest, 'fresh'); assert.equal(calls, 2)

const realTimeout = AbortSignal.timeout
let deadline
AbortSignal.timeout = delay => { assert.equal(delay, 30000); deadline = new AbortController(); return deadline.signal }
try {
  const slow = backgroundRequest('stalled read', read)
  await Promise.resolve()
  deadline.abort(new DOMException('Timed out', 'TimeoutError'))
  await assert.rejects(slow, { name: 'TimeoutError' })
} finally { AbortSignal.timeout = realTimeout }

// 100 independently scheduled clients: steady-state polls and long outages spread out.
for (const failure of [0, 1, 2, 5, 6, 100]) {
  const delays = Array.from({ length: 100 }, (_, i) => updateDelay(30, failure, () => i / 100))
  assert.equal(new Set(delays).size, 100)
  assert(delays.every(delay => failure ? delay >= 2000 && delay <= 75000 : delay >= 25500 && delay <= 34500))
  if (failure >= 6) assert(delays.every(delay => delay >= 60000))
}
console.log('Background reads: 100 callers coalesced, outage cancellation/gate, no replay, deadline cleanup, and 100 independent jittered retry schedules PASS')
