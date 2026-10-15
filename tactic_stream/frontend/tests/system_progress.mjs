import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chromium } from 'playwright'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const native = JSON.parse(readFileSync('../.screenshots/handler-current/system-progress-geometry.json', 'utf8'))
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.topbar').waitFor()
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ search_type: 'sthpw/search_object', view: 'table' }))
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await ready()
  const control = page.locator('.system-activity-control'), button = control.getByRole('button', { name: 'System activity', exact: true })
  const geometry = () => control.evaluate(node => {
    const button = node.querySelector('button'), style = getComputedStyle(node)
    return { width: node.offsetWidth, height: node.offsetHeight, surfaceWidth: button.offsetWidth, surfaceHeight: button.offsetHeight,
      duration: parseFloat(style.transitionDuration) * 1000, easing: style.transitionTimingFunction }
  })
  const check = async (width, loading) => {
    await page.setViewportSize({ width, height: 1000 })
    const expected = native[`system-progress-${width}-${loading ? 'busy' : 'idle'}`]
    await page.waitForFunction(({ width, height }) => {
      const node = document.querySelector('.system-activity-control')
      return node.offsetWidth === width && node.offsetHeight === height
    }, expected)
    const actual = await geometry()
    for (const key of ['width', 'height', 'surfaceWidth', 'surfaceHeight', 'duration']) assert.equal(actual[key], expected[key], `${width} ${key}`)
    assert.equal(actual.easing, 'cubic-bezier(0.215, 0.61, 0.355, 1)')
    await button.evaluate(node => node.blur())
    await page.mouse.move(width / 2, 500)
    await page.screenshot({ path: `../.screenshots/handler-current/stream-system-progress-${width}-${loading ? 'busy' : 'idle'}.png` })
  }
  await check(1440, false)
  assert.equal(await control.locator('.activity-icon').evaluate(node => getComputedStyle(node).fontSize), '20px')
  let held, release
  const pending = new Promise(resolve => { held = resolve }), finish = new Promise(resolve => { release = resolve })
  await page.route('**/admin/search-configuration/query', async route => { held(); await finish; await route.continue() })
  await page.locator('.search-header').getByLabel('Refresh', { exact: true }).first().click()
  await pending
  await control.locator('.busy-indicator.running').waitFor()
  assert.equal(await button.getAttribute('title'), 'Loading data…')
  assert.deepEqual(await control.locator('.busy-indicator').evaluate(node => [node.offsetWidth, node.offsetHeight]), [22, 22])
  assert.equal(await control.locator('.busy-indicator').evaluate(node => getComputedStyle(node).animationDuration), '4.2s, 1.4s, 1.4s, 50.4s')
  for (const [milliseconds, sweep, tail, start] of [[0, 10, 0, 0], [350, 227.5, 0, 0], [700, 300, 0, 0], [1050, 227.5, 72.5, 0], [1400, 10, 0, 290]]) {
    const frame = await control.locator('.busy-indicator').evaluate((node, time) => {
      node.getAnimations().forEach(animation => { animation.pause(); animation.currentTime = time })
      const style = getComputedStyle(node)
      return ['--busy-sweep', '--busy-tail', '--busy-base'].map(name => parseFloat(style.getPropertyValue(name)))
    }, milliseconds)
    for (const [index, expected] of [sweep, tail, start].entries()) assert(Math.abs(frame[index] - expected) < .02, `${milliseconds}: Qt arc phase ${index}`)
  }
  await control.locator('.busy-indicator').evaluate(node => node.getAnimations().forEach(animation => animation.play()))
  await check(1440, true)
  await button.click()
  const history = page.getByRole('dialog', { name: 'Notifications', exact: true })
  await history.waitFor()
  await page.keyboard.press('Escape')
  await control.click({ position: { x: 0, y: 0 } })
  await history.waitFor()
  await page.keyboard.press('Escape')
  await check(760, true)
  await check(759, true)
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 })
    await page.getByLabel('More options', { exact: true }).tap()
    assert.equal(await control.count(), 1, 'Single activity control moves into the menu')
    assert.equal(await control.getAttribute('class'), 'system-activity-control busy in-menu')
    assert.equal(await control.locator('small').innerText(), 'Loading data…')
    await button.scrollIntoViewIfNeeded()
    await page.waitForFunction(() => {
      const panel = document.querySelector('.settings-menu[open] > .account-panel')
      return panel && getComputedStyle(panel).opacity === '1' && Number(getComputedStyle(panel).scale || 1) === 1
    })
    await page.screenshot({ path: `../.screenshots/handler-current/stream-system-progress-menu-${width}.png` })
    await button.tap(); await history.waitFor(); await page.keyboard.press('Escape')
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  }
  release(); await ready(); await page.unroute('**/admin/search-configuration/query')
  await check(1440, false)
  const pingPending = new Promise(resolve => { held = resolve }), pingFinish = new Promise(resolve => { release = resolve })
  await page.route('**/admin/rpc', async route => {
    if (route.request().postDataJSON().method !== 'ping') return route.continue()
    held(); await pingFinish; await route.fulfill({ status: 503, json: { error: 'Server unavailable' } })
  })
  await page.getByLabel('Connection', { exact: true }).click()
  await page.getByRole('button', { name: 'Ping now', exact: true }).click(); await pingPending
  await page.waitForFunction(() => document.querySelector('.system-activity-control').offsetWidth === 220)
  assert.equal(await button.getAttribute('title'), 'Pinging TACTIC server')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  assert.equal(await control.evaluate(node => getComputedStyle(node).transitionDuration), '0s')
  assert.equal(await control.locator('.busy-indicator').evaluate(node => getComputedStyle(node).animationName), 'none')
  release()
  await page.waitForFunction(() => !document.querySelector('.system-activity-control').classList.contains('busy'))
  assert.equal((await geometry()).width, 36, 'Failed ping clears progress')
  assert.deepEqual(errors, [])
  console.log('System activity progress: native geometry, threshold, loading, history, single mobile control, ping error and reduced motion passed')
} finally { await browser.close() }
