import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

// Mount the shipped components, not a second implementation of their timers.
const server = await createServer({ configFile: false, root: fileURLToPath(new URL('..', import.meta.url)),
  plugins: [vue(), { name: 'update-outage-fixture',
    resolveId: id => id === 'virtual:outage' ? '\0virtual:outage' : undefined,
    load: id => id === '\0virtual:outage' ? `
      import { createApp, reactive, ref, h } from 'vue'
      import ServerUpdates from '/src/features/connection/ServerUpdates.vue'
      import MessagesView from '/src/features/messages/MessagesView.vue'
      import NotesPanel from '/src/features/objects/NotesPanel.vue'
      import { rpc, messagesRequest } from '/src/api.js'
      const state = reactive({ ticket:'test', project:'one', updates:null })
      window.state = state; window.batches = []; window.connections = []; window.errors = []; window.widgets = {}
      const count = Number(new URLSearchParams(location.search).get('clients') || 1)
      const app = createApp({ provide:{openHelp:()=>{}}, setup() { return () => h('main', [
        ...Array.from({length:count}, (_, id) => h(ServerUpdates, { ...state, key:id,
          ref: value => { window.widgets[id] = value },
          onBatch: batch => { window.batches.push(batch); if (id === 0) state.updates = batch },
          onConnection: value => window.connections.push(value), onError: value => window.errors.push(value) })),
        ...(count === 1 ? [h(MessagesView, { ...state, login:'test', ref: value => window.messages = value }),
          h(NotesPanel, { ...state, searchType:'contract/entity', ref: value => window.notes = value })] : [])
      ]) } })
      app.directive('window', {})
      app.mount('#app'); window.stop = () => app.unmount()
      window.read = () => messagesRequest('list','test',state.project)
      window.write = () => rpc('update', [{ticket:'test',project:state.project},'key',{description:'saved'}])
    ` : undefined,
    configureServer(server) { server.middlewares.use((request, response, next) => {
      if (!request.url.startsWith('/outage')) return next()
      response.setHeader('Content-Type', 'text/html')
      response.end('<div id="app"></div><script type="module" src="/@id/__x00__virtual:outage"></script>')
    }) }
  }], server: { host:'127.0.0.1', port:0 }, logLevel:'error' })
let browser
try {
  await server.listen()
  const base = `http://127.0.0.1:${server.httpServer.address().port}`
  browser = await chromium.launch({ headless:true })
  const page = await browser.newPage(), errors = [], updates = [], reads = [], writes = []
  page.on('pageerror', failure => errors.push(failure.message))
  await page.addInitScript(() => { Math.random = () => 0.5; localStorage.setItem('tactic_stream.network','{"pollInterval":5}') })
  await page.clock.install()
  let mode = 'ok', release, active = 0, maximum = 0
  const empty = { activity:[], messages:[], reactions:[], presence:[], cacheChanges:[], cacheRetired:[], messagesInitialized:true }
  await page.route('**/admin/**', async route => {
    const request = route.request(), payload = request.postDataJSON(), url = new URL(request.url()).pathname
    if (url === '/admin/server-updates') {
      updates.push(payload); active++; maximum = Math.max(maximum,active)
      try {
        if (mode === 'network') return await route.abort('connectionrefused')
        if (mode === 'hold') await new Promise(resolve => release = resolve)
        await route.fulfill(mode === 'fail' ? {status:503,json:{error:'temporarily unavailable'}} : {json:{result:empty}})
      } catch { /* Hiding/unmounting aborts the request. */ }
      finally { active-- }
      return
    }
    if (url === '/admin/rpc' && payload.method === 'update') { writes.push(payload); return route.fulfill({json:{result:{saved:true}}}) }
    reads.push({url,payload})
    const result = url.endsWith('/list') ? { initialized:false, permissions:{}, conversations:[{conversationId:'CHAT',title:'Chat',recipients:[]}] }
      : url.endsWith('/history') ? {messages:[],pinnedMessage:{},pinHistory:[]}
      : url.endsWith('/people') ? {users:[]}
      : url === '/admin/rpc' ? {info:{notes:[],identities:[],current_user:'test'}} : {}
    await route.fulfill({json:{result}})
  })
  await page.goto(base + '/outage')
  await page.waitForFunction(() => window.batches?.length === 1)
  await page.evaluate(() => window.messages.open())
  await page.evaluate(() => window.notes.open({__search_key__:'contract/entity?project=one&code=ENTITY'}, {}, 'publish', false))
  await page.waitForFunction(() => !window.notes.loading)
  const idleReads = reads.length
  for (let i = 0; i < 3; i++) {
    const batches = await page.evaluate(() => window.batches.length)
    await page.clock.runFor(5100)
    await page.waitForFunction(count => window.batches.length > count, batches)
  }
  assert.equal(reads.length,idleReads,'Idle updates do not reload messages or notes independently')
  await page.evaluate(() => { window.notes.drafts[window.notes.draftKey].body = 'UNSENT NOTE' })
  mode = 'network'
  for (const delay of [5100,2300,4600,9100,18100,33850]) {
    const count = updates.length, failures = await page.evaluate(() => window.connections.filter(value => value === false).length)
    await page.clock.runFor(delay)
    await page.waitForFunction(count => window.connections.filter(value => value === false).length > count, failures)
    assert.equal(updates.length,count+1)
    mode = 'fail'
  }
  const failed = updates.length
  await page.evaluate(() => {
    for (let i = 0; i < 100; i++) { window.widgets[0].refresh(); window.dispatchEvent(new Event('online')); document.dispatchEvent(new Event('visibilitychange')) }
  })
  await page.clock.runFor(60000)
  assert.equal(updates.length,failed,'Focus and Retry cannot bypass the 67.5-second backoff')
  await page.evaluate(async () => {
    const blocked = await Promise.allSettled(Array.from({length:100}, () => window.read()))
    if (blocked.some(row => row.status !== 'rejected' || row.reason.code !== 'updates_unavailable')) throw new Error('Background reads were not gated')
    if (!(await window.write()).saved) throw new Error('An explicit write was blocked')
  })
  assert.equal(reads.length,idleReads); assert.equal(writes.length,1)
  mode = 'ok'
  const recovered = await page.evaluate(() => window.batches.length)
  await page.clock.runFor(7600)
  await page.waitForFunction(count => window.batches.length > count, recovered)
  await page.waitForFunction(() => !window.notes.loading)
  assert.equal(await page.evaluate(() => window.batches.at(-1).reconnected),true)
  assert.equal(await page.evaluate(() => window.notes.draft.body),'UNSENT NOTE')
  assert.equal(updates.length,failed+1,'Reconnect sends one current update request, not a replay')
  await page.evaluate(() => { Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange')) })
  const hidden = updates.length
  await page.clock.runFor(120000); assert.equal(updates.length,hidden)
  await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event('visibilitychange')) })
  await page.waitForFunction(count => window.batches.length > count, recovered+1)
  mode = 'hold'; await page.clock.runFor(5100)
  await page.waitForFunction(() => true); assert(release)
  const held = updates.length
  await page.clock.runFor(20000); assert.equal(updates.length,held)
  await page.evaluate(() => { window.state.project = 'two'; window.widgets[0].refresh() })
  mode = 'ok'; release()
  await page.waitForFunction(() => window.batches.at(-1).projectCode === 'two')
  assert.equal(updates.at(-1).activity_after,undefined); assert.equal(maximum,1)
  await page.evaluate(() => window.stop())
  const stopped = updates.length
  await page.clock.runFor(120000); assert.equal(updates.length,stopped)
  assert.deepEqual(errors,[])
  console.log('Chromium: real shared poll/messages/notes, idle panels, outage gate, explicit write, backoff/focus, one reconnect, note draft, hidden tab, stale project, no overlap and shutdown PASS')

  const crowd = await browser.newPage()
  await crowd.addInitScript(() => {
    let seed = 42
    Math.random = () => { seed = seed * 16807 % 2147483647; return (seed - 1) / 2147483646 }
  })
  await crowd.clock.install()
  let requests = 0
  await crowd.route('**/admin/server-updates', async route => { requests++; await route.fulfill({status:503,json:{error:'temporarily unavailable'}}) })
  await crowd.goto(base + '/outage?clients=100')
  await crowd.waitForFunction(() => window.connections.filter(value => value === false).length === 100)
  assert.equal(requests,100)
  await crowd.clock.runFor(1900); assert.equal(requests,100)
  const buckets = []
  for (let i = 0; i < 6; i++) {
    const previous = requests
    await crowd.clock.runFor(100)
    await crowd.waitForFunction(count => window.connections.filter(value => value === false).length >= count, requests)
    buckets.push(requests - previous)
  }
  assert.equal(requests,200)
  assert(Math.max(...buckets) < 50, `100 independent pollers should spread retries: ${buckets}`)
  await crowd.evaluate(() => window.stop())
  const ended = requests
  await crowd.clock.runFor(120000); assert.equal(requests,ended)
  console.log(`Chromium: 100 real polling components, staggered reconnect attempts per 100ms: ${buckets.join(', ')}; no requests after shutdown PASS`)
} finally { await browser?.close(); await server.close() }
