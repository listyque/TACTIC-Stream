import assert from 'node:assert/strict'
import { readFile, readdir, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'
import { readArticle } from '../src/features/help/help.js'
import { dockPanels } from '../src/features/workspace/docks.js'

const root = fileURLToPath(new URL('..', import.meta.url))
const catalog = JSON.parse(await readFile(root + '/public/help/index.json', 'utf8'))
const ids = new Set(catalog.map(row => row.id))
for (const panel of dockPanels) assert(ids.has('dock.' + panel.id), panel.id)
for (const row of catalog) for (const language of row.languages) {
  const article = readArticle(row.id, await readFile(root + '/public/help/' + row.id + '.' + language + '.md', 'utf8'), '')
  assert(article.title && article.body)
}
// Check every contextual Help route, including existing root/event routes.
async function sources(directory) {
  const result = []
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = directory + '/' + entry.name
    if (entry.isDirectory()) result.push(...await sources(path))
    else if (entry.name.endsWith('.vue')) result.push([path, await readFile(path, 'utf8')])
  }
  return result
}
for (const [path, source] of await sources(root + '/src')) {
  if (!path.endsWith('/App.vue')) assert(!source.includes('<HelpView'), path)
  assert(!/help(?:Dialog)?\.showModal\(\)|help = !help|v-if="help"/.test(source), path)
  for (const match of source.matchAll(/(?:openHelp\(|\$refs\.help\.open\(|emit\('help',\s*)'([a-z_.]+)'(?!\s*\+)/g)) {
    assert(ids.has(match[1]), path + ': ' + match[1])
  }
}
const screens = {
  activity: ['ActivityFeed', 'activity/ActivityFeed', 'Activity Feed help', 'activity_feed'],
  project: ['ProjectCreation', 'projects/ProjectCreation', 'Project creation help', 'project_creation'],
  sidebar: ['SidebarEditor', 'administration/SidebarEditor', 'Sidebar Editor help', 'sidebar_editor'],
  duplicate: ['DuplicateSObject', 'objects/DuplicateSObject', 'Help', 'duplicating_objects'],
  shelf: ['ScriptShelf', 'scripts/ScriptShelf', 'Script shelf help', 'script_shelf'],
  script: ['ScriptEditor', 'scripts/ScriptEditor', 'Script editor help', 'script_editor'],
  messages: ['MessagesView', 'messages/MessagesView', 'Messages help', 'communication'],
  notes: ['NotesPanel', 'objects/NotesPanel', 'Help', 'dock.notes'],
}
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue'
import App from '/src/App.vue'
import HelpView from '/src/features/help/HelpView.vue'
${Object.values(screens).map(([name, path]) => `import ${name} from '/src/features/${path}.vue'`).join('\n')}
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',fadeAnimations:false,popupAnimations:false,clickAnimations:false});initializeAppearance()
const screens={${Object.entries(screens).map(([key, [name]]) => key + ':' + name).join(',')}}
const key=new URLSearchParams(location.search).get('screen')
createApp({provide:App.provide,data(){return {session:{login:'alice'}}},mounted(){window.host=this;window.appearance=appearance},
render(){const component=screens[key],props={ticket:'fixture',project:'cg',login:'alice',searchType:'cg/assets',searchKeys:[],visible:false};return h('div',[h(HelpView,{ref:'help'}),h(component,{ref:'screen',...Object.fromEntries(Object.entries(props).filter(([key])=>key in component.props))})])}
}).directive('window',windowDirective).mount('#app')
</script></body></html>`
const results = {
  '/admin/project-creation': { templates: [], themes: [], installedTemplates: [], defaultProject: {} },
  '/admin/script-shelf/read': { shelves: [], scripts: [], canManage: true, revision: 'fixture' },
  '/admin/script-editor/read': { scripts: [], canEdit: true, revision: 'fixture' },
  '/admin/messages/list': { initialized: true, permissions: {}, conversations: [], users: [] },
  '/admin/messages/users': { users: [] },
  '/admin/activity-feed': { records: [], users: [], dayCounts: [], hasMore: false, nextOffset: 0 },
  '/admin/sidebar/read': { source: 'handler', selected: '', documents: {}, updates: {}, entries: [], groups: [], library: [], searchTypes: [], xml: '', revision: 'fixture' },
}
let server, browser
const deadline = setTimeout(() => browser?.close(), 55000)
try {
  server = await createServer({ root, cacheDir: root + '/node_modules/.vite/shared-help', configFile: false, plugins: [vue(), {
    name: 'shared-help-fixture', configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url.startsWith('/shared-help-test')) return next()
        try { res.setHeader('Content-Type', 'text/html'); res.end(await server.transformIndexHtml(req.url, html)) } catch (error) { next(error) }
      })
    },
  }], server: { host: '127.0.0.1', port: 0, watch: null } })
  await server.listen()
  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } }), errors = [], requests = []
  page.setDefaultTimeout(8000)
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/ui/help/**', async route => {
    const path = new URL(route.request().url()).pathname.slice('/ui/help/'.length)
    await route.fulfill({ body: await readFile(root + '/public/help/' + path), contentType: path.endsWith('.json') ? 'application/json' : 'text/plain; charset=utf-8' })
  })
  await page.route('**/admin/**', async route => {
    const path = new URL(route.request().url()).pathname
    requests.push(path)
    // Duplication deliberately fails its read: Help must remain available on errors.
    if (path === '/admin/rpc') return route.fulfill({ status: 400, json: { error: 'Fixture read failed' } })
    await route.fulfill({ json: { result: results[path] || { users: [] } } })
  })
  const base = server.resolvedUrls.local[0]
  for (const [key, [, , label, topic]] of Object.entries(screens)) {
    await page.goto(base + 'shared-help-test?screen=' + key)
    await page.waitForFunction(() => !!window.host?.$refs.screen)
    await page.evaluate(async key => {
      const screen = window.host.$refs.screen
      if (key === 'sidebar') return
      if (key === 'notes') { screen.target = {__search_key__:'cg/assets?id=1',name:'Fixture'}; screen.$refs.dialog.showModal(); return }
      if (key === 'duplicate') await screen.open({ __search_key__: 'cg/assets?id=1' })
      else await screen.open()
    }, key)
    const button = page.getByRole('button', { name: label, exact: true }).first()
    await button.click()
    const help = page.locator('dialog.help-view')
    await help.locator('[data-topic="' + topic + '"][aria-current="page"]').waitFor({ state: 'attached' })
    assert.equal(await help.count(), 1, key)
    assert.equal(await help.locator('[data-topic]').count(), catalog.length, key)
    await help.locator('article .markdown-text').first().waitFor()
    await page.evaluate(() => document.querySelector('dialog.help-view').dataset.fixture = 'same-window')
    await help.getByRole('button', { name: 'Close help', exact: true }).click()
    // A separate modal remains open beneath Help; no close/discard was triggered.
    if (key !== 'sidebar') assert.equal(await page.locator('dialog[open]').count(), 1, key)
    await button.click()
    assert.equal(await help.getAttribute('data-fixture'), 'same-window', key)
    await help.getByRole('button', { name: 'Close help', exact: true }).click()
    if (key === 'script') {
      await page.getByRole('button', { name: 'Code editor help', exact: true }).click()
      await help.locator('[data-topic="script_editor"][aria-current="page"]').waitFor({ state: 'attached' })
      await help.getByRole('button', { name: 'Close help', exact: true }).click()
    }
  }
  // Same shared owner with a dirty project draft, language changes and compact topics.
  await page.goto(base + 'shared-help-test?screen=project')
  await page.waitForFunction(() => !!window.host?.$refs.screen)
  await page.evaluate(async () => { await window.host.$refs.screen.open(); window.host.$refs.screen.draft.title = 'Unsaved project' })
  await page.getByRole('button', { name: 'Project creation help', exact: true }).click()
  const help = page.locator('dialog.help-view')
  await help.locator('[data-topic="project_creation"][aria-current="page"]').waitFor({ state: 'attached' })
  await page.setViewportSize({ width: 320, height: 700 })
  await help.getByRole('button', { name: 'Help topics', exact: true }).click()
  await help.getByRole('textbox', { name: 'Search help', exact: true }).fill('Mobile guide')
  await help.locator('[data-topic="mobile"]').click()
  await help.getByRole('link', { name: 'Search help', exact: true }).click()
  await help.locator('[data-topic="search"][aria-current="page"]').waitFor({ state: 'attached' })
  await page.evaluate(() => window.host.$refs.help.open('mobile'))
  await page.evaluate(() => window.appearance.language = 'ru')
  await page.waitForFunction(() => document.querySelector('.help-content h1')?.textContent === 'Мобильная справка')
  const bounds = await help.boundingBox(); assert(bounds.x >= 0 && bounds.x + bounds.width <= 321)
  const output = root + '/../.screenshots/shared-help-current'
  await mkdir(output, { recursive: true }); await page.screenshot({ path: output + '/ts-shared-help-mobile.png' })
  await help.locator('article').focus()
  await page.keyboard.press('Escape')
  assert.equal(await page.evaluate(() => window.host.$refs.screen.draft.title), 'Unsaved project')
  assert.equal(await page.locator('dialog[open]').count(), 1)
  assert.deepEqual(errors, [])
  assert(!requests.some(path => /save|create$|send$/.test(path)), requests.join(', '))
  console.log('Shared Help: eight screen launchers, code toolbar, single catalog/window, error state, retained draft, RU, 320px and Escape passed.')
} finally {
  clearTimeout(deadline)
  await browser?.close()
  await server?.close()
}
