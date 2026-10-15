import { closeInspector } from './inspector_helpers.mjs'
import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
async function request(path, values) {
  const response = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) })
  const data = await response.json(); assert(response.ok, JSON.stringify(data)); return data.result
}
const ticket = await request('/admin/rpc', { method: 'get_ticket', args: ['admin', process.env.STREAM_CHECK_PASSWORD] })
const auth = { ticket, project }
const rpc = (method, args = [], kwargs = {}) => request('/admin/rpc', { method, args: [auth, ...args], kwargs })
const objects = await rpc('query', ['cg/assets'], { limit: 50 })
const object = objects.find(row => row.code === 'DEMO_ARM') || objects[0]
assert(object)
const key = `skey://cg/assets?project=${project}&code=${encodeURIComponent(object.code)}`
const catalog = await request('/admin/search-configuration/settings', { ...auth, search_type: 'cg/assets' })
const saved = await request('/admin/search-configuration/save', { ...auth, search_type: 'cg/assets', title: 'Linked asset', records: [{ column: 'code', relation: '=', value: object.code, rowEnabled: true, operator: 'begin' }], keyword: '', order_bys: ['code asc'], revision: catalog.revision })
const preset = saved.presets.find(row => row.title === 'Linked asset')
const savedLink = 'tactic-search://open?' + new URLSearchParams({ project, search_type: 'cg/assets', view: preset.view })
const note = await rpc('insert', ['sthpw/note', { note: `Rich links demonstration\n${key}\n${savedLink}\nhttps://example.org/?a=1&b=2\n<img src=x onerror="window.linkInjected=true">`, login: 'admin', access: 'public', process: 'publish', search_type: 'cg/assets?project=' + project, search_code: object.code, search_id: object.id, project_code: project }])
const snapshot = await rpc('create_snapshot', [object.__search_key__, 'publish/link_demo'])
const resolvedNote = await request('/admin/navigation-link', { ...auth, link: 'skey://' + note.__search_key__ })
assert.equal(resolvedNote.parent?.code, object.code, JSON.stringify({ kind: resolvedNote.kind, project: resolvedNote.project, type: resolvedNote.object.search_type, code: resolvedNote.object.search_code, id: resolvedNote.object.search_id, inputType: object.__search_type__ }))
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  const errors = []; page.on('pageerror', error => errors.push(error.message)); page.setDefaultTimeout(12000)
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  const routePage = async page => page.route('http://tactic-stream.test/**', async route => { const url = new URL(route.request().url()); await route.fulfill({ response: await route.fetch({ url: base + url.pathname + url.search, headers: { ...route.request().headers(), origin: base, referer: base + '/' } }) }) })
  await routePage(page)
  await page.goto('http://tactic-stream.test/')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  const idle = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await idle(); await selectProject(page, project); await idle()
  assert.equal(new URL(page.url()).pathname, '/projects/' + encodeURIComponent(project) + '/')
  assert((await page.title()).includes(project) || (await page.title()).includes('CG'))

  await page.locator('.activity-feed-trigger').click()
  const feed = page.getByRole('dialog', { name: 'Activity Feed', exact: true })
  await feed.getByRole('radio', { name: 'Notes', exact: true }).click()
  const card = feed.locator('.activity-event-card').filter({ hasText: 'Rich links demonstration' })
  await card.waitFor(); await card.getByRole('button', { name: 'Expand', exact: true }).click()
  assert.equal(await card.locator('.activity-event-sentence img').count(), 0)
  assert.equal(await page.evaluate(() => Boolean(window.linkInjected)), false)
  const link = card.locator('a[data-rich-link]').filter({ hasText: key })
  assert.equal(new URL(await link.getAttribute('href'), page.url()).searchParams.get('link'), key)
  const external = card.getByRole('link', { name: 'https://example.org/?a=1&b=2', exact: true })
  assert.equal(await external.getAttribute('target'), '_blank')
  assert((await external.getAttribute('rel')).includes('noopener'))
  const events = (await request('/admin/activity-feed', { ...auth, filter: 'notes' })).records
  writeFileSync('../.screenshots/handler-current/activity-rich-links-fixture.json', JSON.stringify({ records: events, counts: {} }, null, 2))
  await feed.screenshot({ path: '../.screenshots/handler-current/stream-activity-rich-links.png', animations: 'disabled' })
  await link.click()
  const details = page.getByRole('dialog', { name: 'Object details', exact: true })
  await details.waitFor(); assert((await details.innerText()).includes(object.code))
  assert.equal(new URL(page.url()).searchParams.get('link'), key)
  const url = page.url()
  await details.getByRole('button', { name: 'Close details', exact: true }).click()
  const tabCount = await page.locator('.workspace-tab-list [role="tab"]').count()
  const search = page.getByLabel('Search objects', { exact: true })
  await search.fill(key); await search.press('Enter'); await details.waitFor()
  assert.equal(await page.locator('.workspace-tab-list [role="tab"]').count(), tabCount)
  await details.getByRole('button', { name: 'Close details', exact: true }).click()

  // A copied URL works before sign-in, with no access to another client's session.
  const fresh = await browser.newPage({ viewport: { width: 1000, height: 800 } })
  await routePage(fresh); await fresh.goto(url)
  await fresh.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await fresh.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await fresh.getByRole('button', { name: 'Sign in', exact: true }).click()
  await fresh.getByRole('dialog', { name: 'Object details', exact: true }).waitFor()
  assert((await fresh.title()).includes(object.name || object.title || object.code))
  await fresh.close()

  await search.fill(savedLink); await search.press('Enter')
  await page.locator('.workspace-tab-list [role="tab"][aria-selected="true"]').filter({ hasText: 'Linked asset' }).waitFor(); await idle()
  assert.equal(new URL(page.url()).searchParams.get('link'), savedLink)
  const savedCount = await page.locator('.workspace-tab-list [role="tab"]').count()
  await search.fill(savedLink); await search.press('Enter'); await idle()
  assert.equal(await page.locator('.workspace-tab-list [role="tab"]').count(), savedCount)
  await page.reload(); await page.locator('.workspace-tab-list [role="tab"][aria-selected="true"]').filter({ hasText: 'Linked asset' }).waitFor(); await idle()
  assert.equal(new URL(page.url()).searchParams.get('link'), savedLink)

  await search.fill(key); await search.press('Enter'); await details.waitFor()
  await page.goBack()
  await page.locator('.workspace-tab-list [role="tab"][aria-selected="true"]').filter({ hasText: 'Linked asset' }).waitFor(); await idle()
  assert.equal(await details.count(), 0)
  await page.goForward(); await details.waitFor()
  assert.equal(new URL(page.url()).searchParams.get('link'), key)
  await details.getByRole('button', { name: 'Close details', exact: true }).click()

  await search.fill('skey://' + note.__search_key__ + '&project=' + project); await search.press('Enter')
  const notes = page.getByRole('region', { name: 'Task Inspector', exact: true }); await notes.waitFor()
  await page.waitForFunction(() => document.querySelector('#dock-notes .notes-panel[open]')?.getAttribute('aria-busy') === 'false')
  assert((await notes.innerText()).includes('Rich links demonstration'))
  await notes.getByLabel('Note text', { exact: true }).fill('Unsaved link draft')
  await page.goBack()
  await page.locator('.notification-card[role="alert"]').filter({ hasText: 'Close the current window before opening a link' }).waitFor()
  assert.equal(await notes.getByLabel('Note text', { exact: true }).inputValue(), 'Unsaved link draft')
  await notes.getByLabel('Note text', { exact: true }).fill('')
  await closeInspector(page)

  await search.fill('skey://' + snapshot.__search_key__ + '&project=' + project); await search.press('Enter')
  const preview = page.getByRole('dialog', { name: 'File preview', exact: true }); await preview.waitFor()
  assert((await preview.innerText()).includes('publish/link_demo'))
  await preview.getByRole('button', { name: 'Close preview', exact: true }).click()

  // Errors keep the current project and native workspace; no fallback success.
  await search.fill('skey://cg/assets?project=missing&code=X'); await search.press('Enter')
  await page.locator('.notification-card[data-kind="error"]').filter({ hasNotText: 'Close the current window before opening a link' }).waitFor()
  assert.equal(await page.locator('.project-picker').getAttribute('data-project'), project)
  await page.setViewportSize({ width: 320, height: 760 })
  await page.locator('.settings-menu > summary').tap()
  await page.locator('.compact-shortcuts').getByRole('button', { name: 'Activity Feed', exact: true }).tap()
  await feed.getByRole('radio', { name: 'Notes', exact: true }).tap(); await card.waitFor()
  if (await card.getByRole('button', { name: 'Expand', exact: true }).count()) await card.getByRole('button', { name: 'Expand', exact: true }).tap()
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await link.tap(); await details.waitFor()
  await details.getByRole('button', { name: 'Close details', exact: true }).tap()

  await page.setViewportSize({ width: 1440, height: 1000 })
  let release, received
  const gate = new Promise(resolve => { release = resolve }), started = new Promise(resolve => { received = resolve })
  const pending = async route => { received(); await gate; await route.fallback() }
  await page.route('**/admin/navigation-link', pending)
  await search.fill(savedLink); await search.press('Enter'); await started
  await selectProject(page, 'admin'); await idle()
  const completed = page.waitForResponse(response => response.url().endsWith('/admin/navigation-link'))
  release(); await completed
  await page.unroute('**/admin/navigation-link', pending)
  assert.equal(await page.locator('.project-picker').getAttribute('data-project'), 'admin')
  assert.equal(new URL(page.url()).pathname, '/projects/admin/')
  assert.deepEqual(errors, [])
  console.log('Native rich links: CG object/note/snapshot, preset tabs, browser URL/title/history, fresh sign-in, reload, draft/stale guards, errors and touch320 PASS')
} finally { await browser.close() }
