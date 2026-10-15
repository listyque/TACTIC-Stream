import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const route = '/snapshot-availability-test'
const fixture = {
  name: 'snapshot-availability-fixture',
  configureServer(server) {
    server.middlewares.use(async (request, response, next) => {
      if (request.url !== route) return next()
      const html = `<!doctype html><html><body><div id="app"></div>
    <script type="module">
      import { createApp, reactive } from 'vue'
      import SnapshotSummary from '/src/features/objects/SnapshotSummary.vue'
      const snapshot = reactive({ searchKey: '', fileExists: false,
        title: 'Commit without versionless in animation',
        description: 'Versionless for this commit is not present' })
      window.snapshotFixture = snapshot
      createApp(SnapshotSummary, { snapshot }).mount('#app')
    </script></body></html>`
      response.setHeader('Content-Type', 'text/html')
      response.end(await server.transformIndexHtml(route, html))
    })
  },
}
const server = await createServer({
  configFile: false, root: fileURLToPath(new URL('..', import.meta.url)),
  plugins: [vue(), fixture], server: { host: '127.0.0.1', port: 0 },
})
let browser
try {
  await server.listen()
  const address = server.httpServer.address()
  browser = await chromium.launch({ headless: true, channel: process.env.STREAM_CHECK_BROWSER_CHANNEL })
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(`http://127.0.0.1:${address.port}${route}`)
  await page.locator('.snapshot-summary').waitFor()
  for (const width of [320, 960]) {
    await page.setViewportSize({ width, height: 300 })
    const offline = page.locator('.snapshot-summary .offline')
    assert.equal(await offline.count(), 0, 'An absent snapshot has no file availability status')
    assert.match(await page.locator('.snapshot-summary-description').innerText(), /Versionless.*not present/)
    await page.evaluate(() => { window.snapshotFixture.searchKey = 'sthpw/snapshot?code=SNAPSHOT001' })
    await offline.waitFor()
    assert.match(await offline.innerText(), /File Offline/)
    await page.evaluate(() => { window.snapshotFixture.fileExists = true })
    await offline.waitFor({ state: 'detached' })
    await page.evaluate(() => {
      window.snapshotFixture.searchKey = ''
      window.snapshotFixture.fileExists = false
    })
    await offline.waitFor({ state: 'detached' })
  }
  assert.deepEqual(errors, [])
  console.log('Snapshot availability: absent, offline and available snapshots passed at 320/960px')
} finally {
  await browser?.close()
  await server.close()
}
