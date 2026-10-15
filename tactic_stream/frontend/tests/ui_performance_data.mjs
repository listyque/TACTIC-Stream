import assert from 'node:assert/strict'
import { UiPerformanceMonitor } from '../src/features/debug/uiPerformance.js'

let now = 0, serial = 0
const frames = new Map(), timers = new Map(), listeners = new Map()
globalThis.performance = { now: () => now }
globalThis.document = { title: 'Test workspace', hidden: false, activeElement: null,
  addEventListener: (name, handler) => listeners.set(name, handler), removeEventListener: name => listeners.delete(name) }
globalThis.requestAnimationFrame = callback => { const id = ++serial; frames.set(id, callback); return id }
globalThis.cancelAnimationFrame = id => frames.delete(id)
globalThis.setTimeout = (callback, delay) => { const id = ++serial; timers.set(id, { callback, at: now + delay }); return id }
globalThis.clearTimeout = id => timers.delete(id)
globalThis.setInterval = (callback, delay) => { const id = ++serial; timers.set(id, { callback, at: now + delay, delay }); return id }
globalThis.clearInterval = id => timers.delete(id)
function advance(ms) {
  now += ms
  for (const [id, timer] of [...timers]) if (timer.at <= now) {
    if (timer.delay) timer.at = now + timer.delay
    else timers.delete(id)
    timer.callback()
  }
}
function frame() {
  advance(16)
  const batch = [...frames.values()]; frames.clear()
  for (const callback of batch) callback(now)
}
const monitor = new UiPerformanceMonitor()
try {
  assert.equal(monitor.begin('Paused'), 0)
  assert.equal(listeners.size, 0)
  monitor.setVisible(true); monitor.setRecording(true)
  assert.equal(listeners.size, 5)
  const id = monitor.begin('Async operation')
  frame(); frame()
  assert.equal(monitor.samples.length, 0, 'First paint opportunity does not finish an asynchronous operation')
  advance(100)
  monitor.details(id, { requestAndSchemaMs: 100, publicationMs: 2 })
  monitor.end(id); frame(); frame(); advance(100)
  const sample = monitor.state.samples[0]
  assert.equal(sample.frameMs, 32)
  assert(sample.readyMs >= 164 && sample.handlerMs >= 132)
  assert.equal(sample.status, 'Browser frame')
  assert.equal(sample.slow, true)
  assert.equal(monitor.state.summary.overBudget, 0, 'Slow operation duration is distinct from a slow first frame')
  assert.equal(monitor.state.summary.p95, 32)
  assert.equal('host' in sample || 'started' in sample, false)

  monitor.input({ type: 'keydown', repeat: true, key: 'secret', target: null })
  assert.equal(monitor.pending.size, 0)
  monitor.input({ type: 'keydown', key: 'secret', target: { value: 'password-text' } })
  advance(1); frame(); frame(); advance(100)
  assert.equal(monitor.samples[0].action, 'Keyboard')
  assert.equal(monitor.samples[0].readyMs, -1)
  assert(!monitor.copyResults().includes('secret') && !monitor.copyResults().includes('password-text'))
  monitor.input({ type: 'wheel', target: null }); monitor.input({ type: 'wheel', target: null })
  assert.equal(monitor.pending.size, 1, 'Wheel events are coalesced per host')
  monitor.clear(); assert.equal(frames.size, 0)

  const hidden = monitor.state.samples
  monitor.setVisible(false)
  const background = monitor.begin('Hidden diagnostics')
  monitor.end(background); frame(); frame(); advance(200)
  assert.equal(monitor.state.samples, hidden, 'Hidden diagnostics do not republish their list')
  monitor.setVisible(true); assert.equal(monitor.state.samples.length, 1)

  for (const status of ['Failed', 'Superseded']) {
    const failed = monitor.begin(status); monitor.end(failed, status)
    assert.equal(monitor.samples[0].status, status)
    assert.equal(monitor.samples[0].readyMs, -1)
  }
  const closed = { closest: () => ({ getAttribute: () => 'Closed dialog', isConnected: false }) }
  monitor.begin('Closing owner', closed); frame(); frame()
  assert.equal(monitor.samples[0].status, 'Window closed')
  monitor.begin('Never completed'); advance(6000)
  assert.equal(monitor.samples[0].status, 'No frame')
  assert.equal(monitor.samples[0].readyMs, -1)
  for (let index = 0; index < 300; index++) {
    const current = monitor.begin('bounded ' + index); monitor.end(current, 'Failed')
  }
  assert.equal(monitor.samples.length, 250)
  assert.equal(monitor.samples[0].action, 'bounded 299')
  for (let index = 0; index < 70; index++) monitor.begin('Pending')
  assert.equal(monitor.pending.size, 64)
  document.hidden = true; listeners.get('visibilitychange')()
  assert.equal(monitor.pending.size, 0)
  document.hidden = false
  monitor.setRecording(false); assert.equal(listeners.size, 0)
  assert.equal(monitor.begin('Paused again'), 0)
} finally { monitor.reset() }
assert.equal(timers.size, 0)
assert.equal(frames.size, 0)
console.log('PASS: opt-in recording, frame/readiness separation, bounded history/pending work, input privacy, hidden publication, cancellation and cleanup')
