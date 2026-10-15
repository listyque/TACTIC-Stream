import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 740 }, hasTouch: true, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = [], calls = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (request.url().endsWith('/admin/search-configuration/query')) {
      const { offset, project } = request.postDataJSON()
      calls.push({ offset, project })
    }
  })
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  const viewport = page.locator('.workspace-results'), rows = viewport.locator('.configured-view:visible tbody tr')
  const tabs = page.locator('.workspace-tabs[data-kind="search"] [role="tab"]')
  const savedScroll = () => page.evaluate(project => {
    const workspace = JSON.parse(localStorage.getItem('tactic_stream.workspace.admin'))[project]
    const section = workspace.sections.find(section => section.id === workspace.current)
    return section.tabs[0].scrollTop
  }, project)
  const save = async () => {
    await page.getByLabel('More options', { exact: true }).click()
    await page.locator('.settings-menu').getByRole('button', { name: 'Save Preferences', exact: true }).click()
  }
  const selectTab = async index => {
    const overflow = page.getByLabel('All search tabs', { exact: true })
    if (await overflow.isVisible()) {
      await overflow.tap()
      await page.locator('.workspace-tab-menu-items').getByRole('menuitemradio').nth(index).tap()
    } else await tabs.nth(index).click()
    await ready()
  }
  await page.goto(base + '/')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, project)
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ search_type: 'sthpw/search_object', view: 'table' }))
  await ready()
  const footer = page.locator('.workspace-footer')
  await footer.getByLabel('Items per page', { exact: true }).click()
  await footer.getByRole('button', { name: '20 items', exact: true }).click()
  await ready()
  await footer.getByLabel('Result loading', { exact: true }).click()
  await footer.getByRole('button', { name: 'Continuous', exact: true }).click()
  await ready()
  for (let index = 0; index < 2; index++) {
    await page.getByRole('button', { name: 'Load more', exact: true }).click()
    await ready()
  }
  await rows.nth(30).getByRole('checkbox').check()
  const texts = await rows.allInnerTexts()
  await page.getByRole('button', { name: 'Add new search tab', exact: true }).click()
  await ready()
  await selectTab(0)
  assert.deepEqual(await rows.allInnerTexts(), texts, 'The retained tab has all batches before startup')
  const queryUrl = '**/admin/search-configuration/query'
  for (const width of [1280, 320]) {
    let receiveBatch
    const intercepted = new Promise(resolve => { receiveBatch = resolve })
    const holdBatch = route => route.request().postDataJSON().offset === 20 ? receiveBatch(route) : route.continue()
    await page.route(queryUrl, holdBatch)
    await page.setViewportSize({ width, height: 740 })
    await page.evaluate(() => document.fonts.ready)
    await viewport.evaluate(node => node.scrollTop = 700)
    const scroll = await viewport.evaluate(node => node.scrollTop)
    await save()
    assert.equal(await savedScroll(), scroll, 'Scroll is saved before reload')
    await page.reload()
    const delayed = await intercepted
    assert.equal(await savedScroll(), scroll, 'Pending startup preserves scroll')
    assert(await page.locator('.workspace').isVisible(), 'The shell mounts before the second restoration batch finishes')
    assert.equal(await viewport.getAttribute('aria-busy'), 'true')
    assert(await viewport.getByRole('status').filter({ hasText: 'Loading data' }).isVisible())
    assert.equal(await page.locator('.project-picker').getAttribute('data-project'), project)
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: `../.screenshots/handler-current/stream-workspace-startup-${width}.png`, animations: 'disabled' })
    await selectTab(1)
    assert.equal(await savedScroll(), scroll, 'Cancellation preserves source scroll')
    assert.equal(await rows.count(), 20)
    const second = await tabs.nth(1).getAttribute('data-tab-id')
    const lateResponse = page.waitForResponse(response => response.url().endsWith('/admin/search-configuration/query') && response.request().postDataJSON().offset === 20)
    await delayed.continue()
    await (await lateResponse).finished()
    await page.unroute(queryUrl, holdBatch)
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
    assert.equal(await page.locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]').getAttribute('data-tab-id'), second)
    assert.equal(await rows.count(), 20, 'The late startup response leaves the selected tab intact')
    assert.equal(new URL(page.url()).pathname, '/projects/' + encodeURIComponent(project) + '/')
    assert.equal(await savedScroll(), scroll, 'Late startup preserves source scroll')
    await selectTab(0)
    assert.deepEqual(await rows.allInnerTexts(), texts)
    assert(await rows.nth(30).getByRole('checkbox').isChecked())
    assert.equal(await viewport.evaluate(node => node.scrollTop), scroll, 'Returning to the cancelled tab restores scroll at ' + width + 'px')
  }
  await page.setViewportSize({ width: 1280, height: 740 })
  await save()
  let receiveIdentity
  const identityStarted = new Promise(resolve => { receiveIdentity = resolve })
  const holdIdentity = route => receiveIdentity(route)
  await page.route('**/admin/session/identity', holdIdentity)
  const before = calls.length
  await page.reload()
  const identity = await identityStarted
  assert.equal(await page.locator('.workspace').count(), 0, 'The shell stays hidden until authentication/catalog checks finish')
  assert.equal(calls.length, before, 'No result request precedes identity validation')
  await identity.continue()
  await page.unroute('**/admin/session/identity', holdIdentity)
  await ready()
  assert.deepEqual(await rows.allInnerTexts(), texts)

  const invalid = await browser.newPage()
  try {
    invalid.on('pageerror', error => errors.push(error.message))
    await invalid.addInitScript(() => localStorage.setItem('tactic_stream.session', JSON.stringify({ login: 'admin', ticket: 'expired-ticket', project: 'admin' })))
    await invalid.goto(base + '/')
    await invalid.getByRole('button', { name: 'Sign in', exact: true }).waitFor()
    assert.equal(await invalid.locator('.workspace').count(), 0)
    assert.equal(await invalid.evaluate(() => localStorage.getItem('tactic_stream.session')), null)
  } finally { await invalid.close() }
  assert.deepEqual(errors, [])
  console.log('PASS startup: authenticated shell before CG batch completion, desktop/touch320 cancellation, late-response guard, selection/scroll recovery, identity gate and expired session')
} finally { await browser.close() }
