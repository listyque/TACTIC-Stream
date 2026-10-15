import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url)), backend = process.argv[2]
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import Tasks from '/src/features/tasks/TaskManager.vue';
import {initializeAppearance,appearance} from '/src/appearance.js';
import {preferences as configurationPreferences} from '/src/features/configuration/preferences.js';
import {tooltipDirective} from '/src/controls/tooltip.js';import {windowDirective} from '/src/controls/window.js';
import '/src/theme.css';import '/src/style.css';appearance.language='en';initializeAppearance();
configurationPreferences.tasks.workspaceSurface='browser';configurationPreferences.tasks.viewMode='table';
createApp({mounted(){window.host=this;this.$refs.tasks.open()},render(){return h(Tasks,{ref:'tasks',ticket:${JSON.stringify(process.env.STANDALONE_TEST_TICKET)},project:'files',currentUser:'admin',parents:[]})}})
.provide('openHelp',()=>{}).directive('tooltip',tooltipDirective).directive('window',windowDirective).mount('#app')
</script><style>html,body,#app{height:100%;margin:0}</style></body></html>`
let server, browser
try {
  // The private test proxy presents one origin to the server's normal CSRF check.
  const proxy = { target: backend, changeOrigin: true,
    configure(proxy) { proxy.on('proxyReq', request => request.setHeader('origin', backend)) } }
  server = await createServer({ root, configFile: false, plugins: [vue(), { name: 'project-task-fixture', configureServer(server) {
    server.middlewares.use(async (request, response, next) => {
      if (request.url !== '/fixture') return next()
      response.setHeader('Content-Type', 'text/html'); response.end(await server.transformIndexHtml('/fixture', html))
    })
  } }], server: { host: '127.0.0.1', port: 0, proxy: { '/admin': proxy, '/api': proxy } } })
  await server.listen()
  browser = await chromium.launch({ headless: true, channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge' })
  const page = await browser.newPage({ viewport: { width: 1400, height: 940 } }), errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(server.resolvedUrls.local[0] + 'fixture')
  await page.waitForFunction(() => window.host?.$refs.tasks.opened && !window.host.$refs.tasks.busy)
  const manager = page.getByRole('dialog', { name: 'Task Manager', exact: true })
  const add = manager.getByRole('button', { name: 'Create task', exact: true })
  assert(await add.isEnabled())
  assert.equal(await page.evaluate(() => window.host.$refs.tasks.seed.length), 0)
  await add.click()
  await page.waitForFunction(() => !window.host.$refs.tasks.busy)
  assert.equal(await page.evaluate(() => window.host.$refs.tasks.error), '', JSON.stringify(errors))
  const editor = page.getByRole('dialog', { name: 'Edit task draft', exact: true })
  await editor.waitFor()
  await editor.locator('[data-task-field="description"] textarea').fill('Standalone depot task')
  await editor.getByRole('button', { name: 'Apply to draft', exact: true }).click()
  await editor.waitFor({ state: 'hidden' })
  await manager.getByRole('button', { name: 'Save task changes', exact: true }).click()
  await page.waitForFunction(() => !window.host.$refs.tasks.busy && !window.host.$refs.tasks.dirty)
  const task = await page.evaluate(() => window.host.$refs.tasks.tasks.find(task => task.description === 'Standalone depot task'))
  assert(task?.__search_key__)
  assert.equal(task.search_type.split('?')[0], 'sthpw/project')
  assert.equal(task.search_code, 'files')
  await manager.locator('[data-task-key]').first().click({ button: 'right' })
  await page.getByRole('button', { name: 'Task Inspector', exact: true }).click()
  await page.waitForFunction(() => window.host.$refs.tasks.$refs.notes.editor?.selected_task)
  assert.equal(await page.evaluate(() => window.host.$refs.tasks.$refs.notes.editor.task.description), 'Standalone depot task')
  assert.deepEqual(errors, [])
  console.log('Project task: empty selection -> real plus -> draft -> native save -> Inspector passed.')
} finally { await browser?.close(); await server?.close() }
