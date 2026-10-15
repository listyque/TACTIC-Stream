import assert from 'node:assert/strict'
import { serverEventStream } from '../src/features/connection/serverEventStream.js'

const originalFetch = globalThis.fetch
try {
  const controller = new AbortController(), received = []
  let source, cancelled = false, call
  globalThis.fetch = async (url, options) => {
    call = {url, options}
    return new Response(new ReadableStream({ start(value) { source = value }, cancel() { cancelled = true } }), {headers:{'Content-Type':'text/event-stream'}})
  }
  const run = serverEventStream('/admin/server-events', {ticket:'secret',project:'one'}, value => received.push(value), controller.signal)
  const frame = new TextEncoder().encode(': keepalive\r\n\r\nevent: updates\r\ndata: {"text":"Привет"}\r\n\r\n')
  // Every byte is a separate network chunk, including Unicode and CRLF boundaries.
  for (const byte of frame) source.enqueue(new Uint8Array([byte]))
  source.enqueue(new TextEncoder().encode('event: changes\ndata: {"channels":["cache"],"search_types":["cg/assets"]}\n\n'))
  source.enqueue(new TextEncoder().encode('event: error\ndata: {"error":"Session ended","error_code":"authentication_failed","status":403}\n\n'))
  await assert.rejects(run, failure => failure.code === 'authentication_failed' && failure.status === 403)
  assert.deepEqual(received, [{text:'Привет'}, {channels:['cache'],search_types:['cg/assets']}])
  assert.equal(call.url, '/admin/server-events'); assert(!call.url.includes('secret'))
  assert.equal(call.options.method,'POST'); assert.equal(JSON.parse(call.options.body).ticket,'secret')
  assert.equal(call.options.headers['X-Tactic-Client'], 'TACTIC Stream')
  assert(cancelled)

  globalThis.fetch = async () => new Response(JSON.stringify({error:'Forbidden', error_code:'permission_denied'}), {status:403})
  await assert.rejects(serverEventStream('/stream', {}, () => {}, new AbortController().signal), failure => failure.code === 'permission_denied')
  globalThis.fetch = async () => new Response('Proxy unavailable', {status:503,headers:{'Content-Type':'text/html'}})
  await assert.rejects(serverEventStream('/stream', {}, () => {}, new AbortController().signal), failure => failure.status === 503)
  globalThis.fetch = async () => new Response('html', {headers:{'Content-Type':'text/html'}})
  await assert.rejects(serverEventStream('/stream', {}, () => {}, new AbortController().signal), TypeError)
  globalThis.fetch = async () => new Response(new ReadableStream({start(value) {value.close()}}), {headers:{'Content-Type':'text/event-stream'}})
  await assert.rejects(serverEventStream('/stream', {}, () => {}, new AbortController().signal), /closed/)
  const originalSetTimeout = globalThis.setTimeout, originalClearTimeout = globalThis.clearTimeout
  try {
    const timers = []
    globalThis.setTimeout = (callback, delay) => { timers.push({callback,delay}); return timers.length }
    globalThis.clearTimeout = () => {}
    globalThis.fetch = async (_, options) => new Promise((resolve,reject) => options.signal.addEventListener('abort', () => reject(options.signal.reason), {once:true}))
    let timed = serverEventStream('/stream', {}, () => {}, new AbortController().signal)
    assert.equal(timers.at(-1).delay,30000)
    timers.at(-1).callback()
    await assert.rejects(timed, failure => failure.name === 'TimeoutError')

    globalThis.fetch = async (_, options) => new Response(new ReadableStream({
      start(value) {
        value.enqueue(new TextEncoder().encode(': keepalive\n\n'))
        options.signal.addEventListener('abort', () => value.error(options.signal.reason), {once:true})
      }
    }), {headers:{'Content-Type':'text/event-stream'}})
    timed = serverEventStream('/stream', {}, () => {}, new AbortController().signal)
    await new Promise(resolve => originalSetTimeout(resolve,0))
    assert.equal(timers.at(-1).delay,45000)
    timers.at(-1).callback()
    await assert.rejects(timed, failure => failure.name === 'TimeoutError')
  } finally { globalThis.setTimeout = originalSetTimeout; globalThis.clearTimeout = originalClearTimeout }
  console.log('PASS: fragmented UTF-8 SSE, keepalives, private POST authentication, errors and stream cleanup')
} finally { globalThis.fetch = originalFetch }
