import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  await page.addInitScript(() => {
    Math.random = () => 0.5
    localStorage.setItem('tactic_stream.appearance', '{"mode":"dark","language":"en"}')
    localStorage.setItem('tactic_stream.network', '{"pollInterval":5}')
  })
  await page.clock.install()
  const errors = [], calls = [], feeds = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (request.url().endsWith('/admin/activity-feed')) feeds.push(request.postDataJSON()) })
  let mode = 'real', held, active = 0, maxActive = 0
  const empty = { activity: [], messages: [], reactions: [], presence: [], cacheChanges: [], cacheRetired: [], messagesInitialized: false }
  await page.route('**/admin/server-updates', async route => {
    const payload = route.request().postDataJSON()
    calls.push(payload); active++; maxActive = Math.max(maxActive, active)
    try {
      if (mode === 'hold') {
        await new Promise(resolve => { held = resolve })
        return await route.fulfill({ status: 503, json: { error: 'Obsolete batch failure' } })
      }
      if (mode === 'fail') return await route.fulfill({ status: 503, json: { error: 'Batch temporarily unavailable' } })
      if (mode === 'auth') return await route.fulfill({ status: 403, json: { error_code: 'authentication_failed', error: 'Session ended' } })
      if (mode === 'empty') return await route.fulfill({ json: { result: empty } })
      await route.fulfill({ response: await route.fetch() })
    } finally { active-- }
  })
  const cycle = async delay => {
    const response = page.waitForResponse(row => row.url().endsWith('/admin/server-updates'))
    await page.clock.runFor(delay); await response; await page.clock.runFor(20)
  }
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.project-picker').waitFor()
  const first = page.waitForResponse(row => row.url().endsWith('/admin/server-updates') && row.request().postDataJSON().project === project)
  await selectProject(page, project); await first; await page.clock.runFor(100)
  // A project with no saved tabs legitimately opens an empty workspace.
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?search_type=sthpw/task&view=table')
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  const auth = { ticket: calls.at(-1).ticket, project }
  async function rpc(method, ...args) {
    const response = await page.request.post(base + '/admin/rpc', { data: { method, args } })
    const value = await response.json(); assert(response.ok(), JSON.stringify(value)); return value.result
  }

  // Actual native task writes refresh the open manager; staged values and revisions stay intact.
  await page.getByLabel('More options', { exact: true }).click()
  await page.getByRole('button', { name: 'Task Manager', exact: true }).click()
  const manager = page.getByRole('dialog', { name: 'Task Manager', exact: true })
  const ready = () => page.waitForFunction(() => document.querySelector('.task-manager-results')?.getAttribute('aria-busy') === 'false')
  await ready(); await page.locator('[data-dock="tasks"]').getByRole('button', { name:'Maximize panel', exact:true }).click(); await page.clock.runFor(400)
  await manager.locator('.task-manager-scope > summary').click()
  await manager.getByLabel('Task scope', { exact: true }).selectOption('project'); await ready()
  await manager.locator('.task-manager-scope > summary').click()
  const row = manager.locator('tr[data-task-key]').first(), key = await row.getAttribute('data-task-key')
  const task = await rpc('get_by_search_key', auth, key), progressField = 'progress' in task ? 'progress' : 'completion'
  await rpc('update', auth, key, { description: 'LIVE_BATCH_TASK', [progressField]: 31, timestamp: '2099-10-08 12:00:00' })
  await cycle(5100); await ready()
  await manager.locator(`tr[data-task-key="${key}"] [data-task-cell="progress"]`).getByText('31%', { exact: true }).waitFor()
  await row.getByRole('checkbox').check()
  await manager.getByRole('button', { name: 'Edit selected tasks', exact: true }).click()
  const editor = page.getByRole('dialog', { name: 'Edit task draft', exact: true })
  await editor.locator('[data-task-field="description"] textarea').fill('UNSAVED_BATCH_DRAFT')
  await editor.getByRole('button', { name: 'Apply to draft', exact: true }).click()
  await rpc('update', auth, key, { description: 'PARALLEL_BATCH_TASK', [progressField]: 52, timestamp: '2099-10-08 12:00:01' })
  await cycle(5100)
  await manager.getByText('Tasks changed on the server. Refresh to review current values; your draft keeps its original revisions.').waitFor()
  await manager.getByRole('region', { name: 'Pending task changes', exact: true }).waitFor()
  await manager.getByRole('button', { name: 'Edit selected tasks', exact: true }).click()
  assert.equal(await editor.locator('[data-task-field="description"] textarea').inputValue(), 'UNSAVED_BATCH_DRAFT')
  await editor.getByRole('button', { name: 'Cancel', exact: true }).click()
  await manager.getByRole('button', { name: 'Save task changes', exact: true }).click()
  await manager.getByRole('alert').filter({ hasText: /changed|revision|Reload/ }).waitFor()
  await manager.getByRole('button', { name: 'Discard task changes', exact: true }).click(); await ready()
  await page.getByRole('button', { name: 'Close panel: Task Manager', exact: true }).click()

  mode = 'empty'; await cycle(5100)
  const beforeFeed = feeds.length
  await cycle(5100)
  assert.equal(feeds.length, beforeFeed, 'Idle batches must not start a second activity polling loop')
  assert(calls.at(-1).activity_after)
  assert(calls.at(-1).cache_after)

  // Retry backoff includes jitter; the fifth failure is visible.
  const menu = page.locator('.connection-menu')
  await menu.getByLabel('Connection', { exact: true }).click()
  mode = 'fail'
  for (const [index, delay] of [5100, 2300, 4600, 9100, 18100].entries()) {
    await cycle(delay)
    assert.equal(await menu.getByRole('alert').count(), index === 4 ? 1 : 0)
  }
  assert((await menu.getByLabel('Connection', { exact: true }).innerText()).includes('Offline'))
  const failedCursor = calls.at(-1).activity_after
  mode = 'empty'; await cycle(33850)
  assert.equal(calls.at(-1).activity_after, failedCursor)
  assert.equal(await menu.getByRole('alert').count(), 0)

  mode = 'hold'
  await page.clock.runFor(5100)
  await page.waitForFunction(() => true)
  assert(held)
  const beforeHeld = calls.length
  await page.clock.runFor(11000)
  assert.equal(calls.length, beforeHeld)
  await menu.getByLabel('Connection', { exact: true }).click()
  await selectProject(page, 'admin')
  mode = 'empty'; const fresh = page.waitForResponse(row => row.url().endsWith('/admin/server-updates') && row.request().postDataJSON().project === 'admin')
  held(); await fresh; await page.clock.runFor(100)
  assert.equal(calls.at(-1).activity_after, undefined)
  await menu.getByLabel('Connection', { exact: true }).click()
  assert.equal(await menu.getByRole('alert').count(), 0)
  assert.equal(maxActive, 1)

  await page.evaluate(() => Object.defineProperty(document, 'hidden', { value: true, configurable: true }))
  const hiddenCalls = calls.length
  await page.clock.runFor(11000); assert.equal(calls.length, hiddenCalls)
  const resumed = page.waitForResponse(row => row.url().endsWith('/admin/server-updates'))
  await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event('visibilitychange')) })
  await resumed; await page.clock.runFor(100)
  mode = 'auth'; await cycle(5100)
  await page.getByLabel('Password', { exact: true }).waitFor()
  const signedOut = calls.length
  await page.clock.runFor(60000); assert.equal(calls.length, signedOut)
  assert.deepEqual(errors, [])
  console.log('Server updates: native live tasks/draft conflicts, one request/timer, cursors, silent retry/recovery, stale project replies, visibility and session shutdown PASS')
} finally { await browser.close() }
