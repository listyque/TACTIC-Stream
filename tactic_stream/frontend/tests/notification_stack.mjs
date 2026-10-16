import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chromium } from 'playwright'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const native = JSON.parse(readFileSync('../.screenshots/handler-current/notification-stack-geometry.json', 'utf8'))
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  let events = []
  await page.route('**/admin/activity-feed', route => route.fulfill({ json: { result: { records: events, users: [], counts: {}, hasMore: false, nextOffset: events.length } } }))
  await page.route('**/admin/server-updates', route => route.fulfill({ json: { result: { activity: events.map(row => ({ __event_timestamp__: row.timestamp })), messages: [], reactions: [], presence: [], cacheChanges: [], cacheRetired: [] } } }))
  await page.clock.install()
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.topbar').waitFor()
  const baseline = page.waitForResponse(response => response.url().endsWith('/admin/activity-feed'))
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ search_type: 'sthpw/search_object', view: 'table' }))
  await baseline
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await ready()
  const stack = page.locator('.notification-stack'), cards = stack.locator('.notification-card')
  const save = async () => { await page.getByLabel('More options', { exact: true }).click(); await page.locator('.settings-menu').getByRole('button', { name: 'Save Preferences', exact: true }).click() }
  const ping = async () => { await page.getByLabel('Connection', { exact: true }).click(); await page.locator('.connection-menu').getByRole('button', { name: 'Ping now', exact: true }).click() }
  await save()
  let failure = 'Unable to reach the server.'
  await page.route('**/admin/rpc', route => route.request().postDataJSON().method === 'ping' ? route.fulfill({ status: 503, json: { error: failure } }) : route.continue())
  await ping()
  await cards.filter({ hasText: failure }).waitFor()
  await page.waitForFunction(() => !document.querySelector('.notification-card[data-kind="progress"]'))
  events = [{ actor: 'artist', actorLabel: 'Artist', actorInitials: 'AR', eventId: 'toast-live', timestamp: '2099-01-01 12:00:00', title: 'New activity', detail: 'Episode review updated', kind: 'change' }]
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  await cards.filter({ hasText: 'Artist' }).waitFor()
  assert.equal(await cards.count(), 3)
  assert.equal(await stack.evaluate(node => node.matches(':popover-open')), true)
  const box = await stack.boundingBox()
  assert.equal(box.width, native.width)
  assert.equal(Math.round(1440 - box.x - box.width), 18)
  assert.equal(Math.round(1000 - box.y - box.height), 18)
  for (const expected of native.cards) {
    const card = stack.locator(`.notification-card[data-kind="${expected.kind}"]`)
    assert.equal((await card.boundingBox()).height, expected.height)
    const avatar = await card.locator('.image-picker-preview').boundingBox()
    assert.equal(avatar.width, 46); assert.equal(avatar.height, 46)
    assert.equal(await card.locator('.notification-dismiss').evaluate(node => node.offsetWidth), 28)
    const message = await card.locator('.notification-message').boundingBox(), origin = await card.boundingBox()
    assert.equal(message.x - origin.x, expected.fields.notificationMessage.x)
    assert(Math.abs(message.y - origin.y - expected.fields.notificationMessage.y) <= .5)
  }
  await page.screenshot({ path: '../.screenshots/handler-current/stream-notification-stack.png' })
  await page.keyboard.press('Escape')
  await stack.getByRole('button', { name: 'Open Activity Feed', exact: true }).click()
  const feed = page.getByRole('dialog', { name: 'Activity Feed', exact: true })
  await feed.waitFor()
  assert.equal(await stack.locator('.notification-card[data-source="activity"]').count(), 0)
  await page.waitForFunction(() => document.querySelector('.activity-feed-dialog')?.contains(document.querySelector('.notification-stack')))
  const focused = await feed.getByLabel('Search activity', { exact: true }).evaluate(node => { node.focus(); return node === document.activeElement })
  assert(focused)
  await feed.locator('.notification-card[data-kind="error"]').getByLabel('Dismiss notification', { exact: true }).click()
  await feed.getByLabel('Close Activity Feed', { exact: true }).click()
  await page.clock.runFor(8000)
  assert.equal(await cards.count(), 0)
  await save(); await cards.filter({ hasText: 'Preferences saved' }).waitFor()
  await page.clock.runFor(6000)
  assert.equal(await cards.count(), 0)
  await save(); await cards.filter({ hasText: 'Preferences saved' }).waitFor()
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 })
    const bounds = await stack.boundingBox()
    assert.equal(bounds.width, width - 36)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    await page.screenshot({ path: `../.screenshots/handler-current/stream-notification-stack-${width}.png` })
  }
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.route('**/admin/configuration', route => route.fulfill({ status: 503, json: { error: 'Configuration read failed' } }))
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Configuration', exact: true }).click()
  const configuration = page.locator('dialog[open][aria-labelledby="configuration-title"]')
  await configuration.locator('.notification-card').filter({ hasText: 'Configuration read failed' }).waitFor()
  await configuration.locator('.notification-card').filter({ hasText: 'Configuration read failed' }).getByLabel('Dismiss notification', { exact: true }).tap()
  await configuration.getByRole('button', { name: 'Close', exact: true }).click()
  let held
  const pending = new Promise(resolve => { held = resolve })
  await page.route('**/admin/search-configuration/query', route => held(route))
  await page.locator('.search-header').getByLabel('Refresh', { exact: true }).first().click()
  const query = await pending
  const progress = stack.locator('.notification-card[data-kind="progress"]')
  await progress.waitFor()
  assert.equal(await progress.locator('.notification-dismiss').count(), 0)
  assert.equal(await progress.getByRole('progressbar').evaluate(node => node.offsetHeight), 4)
  assert.equal((await progress.boundingBox()).height, native.progress.height)
  assert.equal((await progress.locator('.notification-message').boundingBox()).width, native.progress.messageWidth)
  const bar = progress.getByRole('progressbar')
  for (const time of [300, 1000, 1600]) {
    const measured = await bar.evaluate(async (node, time) => {
      for (const animation of node.getAnimations({ subtree: true })) { animation.pause(); animation.currentTime = time }
      await new Promise(resolve => requestAnimationFrame(resolve))
      return ['::before', '::after'].map(pseudo => {
        const style = getComputedStyle(node, pseudo)
        return { left: parseFloat(style.left) / node.clientWidth, width: parseFloat(style.width) / node.clientWidth }
      })
    }, time)
    for (const [index, segment] of measured.entries()) {
      const phase = Math.max(0, Math.min(1, (time - index * 520) / 1240))
      const value = 1 - (1 - phase) ** 3
      assert(Math.abs(segment.left - value) < .002, `Qt slide position at ${time}ms`)
      assert(Math.abs(segment.width - value * (1 - value)) < .002, `Qt slide width at ${time}ms`)
    }
  }
  await bar.evaluate(node => { for (const animation of node.getAnimations({ subtree: true })) animation.currentTime = 300 })
  await page.screenshot({ path: '../.screenshots/handler-current/stream-notification-progress.png' })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  assert.equal(await bar.evaluate(node => node.getAnimations({ subtree: true }).length), 0)
  assert.equal(await bar.evaluate(node => parseFloat(getComputedStyle(node, '::before').getPropertyValue('--progress-slide'))), .5)
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await query.continue(); await ready(); await progress.waitFor({ state: 'hidden' })
  await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Sign Out', exact: true }).click()
  await page.getByLabel('Password', { exact: true }).waitFor()
  assert.equal(await page.locator('.notification-stack:popover-open').count(), 0)
  assert.deepEqual(errors, [])
  console.log('PASS: live-QML toast geometry, three sources, activity action, native timers, repeated save, modal top layer, touch320/360, transient progress and logout cleanup')
} finally { await browser.close() }
