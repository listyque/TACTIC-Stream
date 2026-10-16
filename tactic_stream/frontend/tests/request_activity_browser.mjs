import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = []; page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.topbar').waitFor()
  const initialUpdate = page.waitForResponse(response => response.url().endsWith('/admin/server-updates'))
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ search_type: 'sthpw/search_object', view: 'table' }))
  await (await initialUpdate).json()
  const idle = () => page.waitForFunction(() => !document.querySelector('.system-activity-control .busy-indicator.running'))
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false'); await idle()
  const menu = async name => { await page.getByLabel('More options', { exact: true }).click(); await page.locator('.settings-menu').getByRole('button', { name, exact: true }).click() }
  const held = []
  let started
  const both = new Promise(resolve => { started = resolve })
  await page.route('**/admin/rpc', route => {
    const body = route.request().postDataJSON()
    if (body.method === 'execute_cmd' && body.args[1] === 'tactic.ui.table.task_workspace.TaskWorkspaceCmd') {
      held.push(route); if (held.length === 2) started()
    } else route.continue()
  })
  await menu('Task Manager'); await both
  const control = page.locator('.system-activity-control')
  await control.locator('.busy-indicator.running').waitFor()
  assert.equal(await control.getByLabel('System activity', { exact: true }).getAttribute('title'), 'Working…')
  const catalog = held.find(route => route.request().postDataJSON().args[2].action === 'catalog')
  const query = held.find(route => route !== catalog)
  const catalogDone = page.waitForResponse(response => response.request() === catalog.request())
  await catalog.continue(); await catalogDone
  assert.equal(await control.locator('.busy-indicator.running').count(), 1)
  await page.screenshot({ path: '../.screenshots/handler-current/stream-request-activity-tasks.png' })
  await query.continue()
  await page.locator('.task-manager-results[aria-busy="false"]').waitFor(); await idle()
  await page.unroute('**/admin/rpc')

  const automatic = []
  let automaticStarted
  const refreshed = new Promise(resolve => { automaticStarted = resolve })
  await page.route('**/admin/rpc', route => {
    const body = route.request().postDataJSON()
    if (body.method === 'execute_cmd' && body.args[1] === 'tactic.ui.table.task_workspace.TaskWorkspaceCmd') {
      automatic.push(route); if (automatic.length === 2) automaticStarted()
    } else route.continue()
  })
  let backgroundStarted
  const background = new Promise(resolve => { backgroundStarted = resolve })
  await page.route('**/admin/server-updates', route => backgroundStarted(route))
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  const poll = await background
  assert.equal(await control.locator('.busy-indicator.running').count(), 0, 'An outstanding background poll remains quiet')
  await poll.fulfill({ json: { result: { activity: [{ __kind__: 'task', __event_timestamp__: '2099-01-01 12:00:00' }], messages: [], reactions: [], presence: [], cacheChanges: [], cacheRetired: [] } } })
  await refreshed
  assert.equal(await control.locator('.busy-indicator.running').count(), 0, 'Live task refresh remains quiet while both requests are outstanding')
  for (const route of automatic) await route.continue()
  await page.locator('.task-manager-results[aria-busy="false"]').waitFor()
  await page.unroute('**/admin/server-updates'); await page.unroute('**/admin/rpc')
  await page.locator('[data-dock="tasks"]:visible').getByLabel('Close panel: Task Manager', { exact: true }).click()

  let linkStarted
  const link = new Promise(resolve => { linkStarted = resolve })
  await page.route('**/admin/navigation-link', route => linkStarted(route))
  await page.getByLabel('Search objects', { exact: true }).fill(`skey://sthpw/project?project=${project}&code=${project}`)
  await page.getByLabel('Search objects', { exact: true }).press('Enter')
  const obsolete = await link
  await control.locator('.busy-indicator.running').waitFor()
  await selectProject(page, 'admin')
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false'); await idle()

  let readStarted
  const read = new Promise(resolve => { readStarted = resolve })
  await page.route('**/admin/script-editor/read', route => readStarted(route))
  await menu('Script Editor')
  const script = page.locator('.script-editor-dialog'), pending = await read
  await script.locator('.notification-card[data-kind="progress"]').waitFor()
  await control.locator('.busy-indicator.running').waitFor()
  const obsoleteDone = page.waitForResponse(response => response.url().endsWith('/admin/navigation-link'))
  await obsolete.continue(); await obsoleteDone; await page.unroute('**/admin/navigation-link')
  assert.equal(await control.locator('.busy-indicator.running').count(), 1, 'Old project completion cannot stop the new editor request')
  assert.equal(await page.locator('.project-picker').getAttribute('data-project'), 'admin')
  assert.equal(await page.getByRole('dialog', { name: 'Object details', exact: true }).count(), 0)
  assert.equal(await script.locator('.notification-card[data-kind="progress"]').getByRole('progressbar').count(), 1)
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 })
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: `../.screenshots/handler-current/stream-request-activity-editor-${width}.png` })
  }
  await pending.fulfill({ status: 503, json: { error: 'Script catalog failed' } })
  await script.locator('p[role="alert"]').filter({ hasText: 'Script catalog failed' }).waitFor(); await idle()
  assert.equal(await script.locator('.notification-card[data-kind="progress"]').count(), 0)
  await script.getByLabel('Close script editor', { exact: true }).tap()
  await page.getByLabel('Account', { exact: true }).tap(); await page.getByRole('button', { name: 'Sign Out', exact: true }).tap()
  await page.getByLabel('Password', { exact: true }).waitFor()
  assert.equal(await page.locator('.notification-stack:popover-open').count(), 0)
  assert.deepEqual(errors, [])
  console.log('PASS: real task request overlap, quiet shared poll, modal editor progress/failure, touch320/360 and logout')
} finally { await browser.close() }
