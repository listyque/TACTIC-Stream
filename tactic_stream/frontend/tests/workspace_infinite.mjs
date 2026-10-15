import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 740 }, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = [], calls = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (request.url().endsWith('/admin/search-configuration/query')) {
      const { offset, filters, project, search_type } = request.postDataJSON()
      calls.push({ offset, filters, project, search_type })
    }
  })
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, project)
  await page.goto(base + '/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ search_type: 'sthpw/search_object', view: 'table' }))
  await ready()
  const footer = page.locator('.workspace-footer'), viewport = page.locator('.workspace-results')
  const rows = viewport.locator('.configured-view:visible tbody tr')
  const search = page.getByLabel('Search objects', { exact: true })
  const save = async () => {
    await page.getByLabel('More options', { exact: true }).click()
    await page.locator('.settings-menu').getByRole('button', { name: 'Save Preferences', exact: true }).click()
  }
  const snapshot = () => page.evaluate(project => {
    const workspace = JSON.parse(localStorage.getItem('tactic_stream.workspace.admin'))[project]
    const section = workspace.sections.find(section => section.id === workspace.current)
    return section.tabs.find(tab => tab.id === section.current)
  }, project)
  await footer.getByLabel('Items per page', { exact: true }).click()
  await footer.getByRole('button', { name: '20 items', exact: true }).click()
  await ready()
  await footer.getByLabel('Result loading', { exact: true }).click()
  const initialBatch = page.waitForResponse(response => response.url().endsWith('/admin/search-configuration/query') && response.request().postDataJSON().offset === 0)
  await footer.getByRole('button', { name: 'Continuous', exact: true }).click()
  await ready()
  const firstRecord = (await (await initialBatch).json()).result.records[0]
  const queryUrl = '**/admin/search-configuration/query'
  const failAppend = route => route.request().postDataJSON().offset === 20
    ? route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'Append test failure' }) }) : route.continue()
  await rows.first().getByRole('checkbox').check()
  await page.route(queryUrl, failAppend)
  await page.getByRole('button', { name: 'Load more', exact: true }).click()
  await ready()
  assert.equal(await rows.count(), 20)
  assert(await rows.first().getByRole('checkbox').isChecked(), 'Append failure retains selection')
  await page.unroute(queryUrl, failAppend)
  const overlapping = async route => {
    if (route.request().postDataJSON().offset !== 20) { await route.continue(); return }
    const response = await route.fetch(), body = await response.json()
    body.result.records[0] = firstRecord
    await route.fulfill({ response, json: body })
  }
  await page.route(queryUrl, overlapping)
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await ready()
  assert.equal(await rows.count(), 39, 'Overlapping pages cannot duplicate objects')
  assert(await rows.first().getByRole('checkbox').isChecked())
  const nextBatch = page.waitForResponse(response => response.url().endsWith('/admin/search-configuration/query') && response.request().postDataJSON().offset === 40)
  await page.getByRole('button', { name: 'Load more', exact: true }).click()
  await nextBatch
  await ready()
  await page.unroute(queryUrl, overlapping)
  await page.getByLabel('Refresh', { exact: true }).first().click()
  await ready()
  for (let batch = 0; batch < 2; batch++) {
    await page.getByRole('button', { name: 'Load more', exact: true }).click()
    await ready()
  }
  assert(await rows.count() > 40, 'The fixture contains three loaded batches')
  await rows.nth(30).getByRole('checkbox').check()
  await search.fill('Unsubmitted search draft')
  await viewport.evaluate(node => node.scrollTop = 700)
  const texts = await rows.allInnerTexts(), scroll = await viewport.evaluate(node => node.scrollTop)
  await save()
  const saved = await snapshot()
  assert.deepEqual(saved.loadedOffsets, [0, 20, 40])
  assert.deepEqual(saved.query.filters, [])
  let before = calls.length
  await page.reload()
  await ready()
  assert.deepEqual(calls.slice(before).map(call => call.offset), [0, 20, 40], 'Reload rebuilds all batches exactly once')
  assert(calls.slice(before).every(call => call.filters.length === 0), 'Unsubmitted text does not change the executed query')
  assert.deepEqual(await rows.allInnerTexts(), texts)
  assert(await rows.nth(30).getByRole('checkbox').isChecked())
  assert.equal(await search.inputValue(), 'Unsubmitted search draft')
  assert.equal(await viewport.evaluate(node => node.scrollTop), scroll)

  // A failed projection must retain its original offsets, selection and scroll for retry.
  const failBatch = route => route.request().postDataJSON().offset === 20
    ? route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'Restore batch test failure' }) }) : route.continue()
  await page.route(queryUrl, failBatch)
  await page.reload()
  await ready()
  await page.locator('#workspace-data').getByRole('alert').filter({ hasText: 'Restore batch test failure' }).waitFor()
  assert.equal(await rows.count(), 0, 'A failed projection never publishes partial results')
  await save()
  assert.deepEqual((await snapshot()).loadedOffsets, [0, 20, 40])
  assert.deepEqual((await snapshot()).state.selectedKeys, saved.state.selectedKeys)
  assert.equal((await snapshot()).scrollTop, scroll)
  await page.unroute(queryUrl, failBatch)
  before = calls.length
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await ready()
  assert.deepEqual(calls.slice(before).map(call => call.offset), [0, 20, 40])
  assert.deepEqual(await rows.allInnerTexts(), texts)
  assert(await rows.nth(30).getByRole('checkbox').isChecked())
  assert.equal(await viewport.evaluate(node => node.scrollTop), scroll)

  // Keep a second tab ready so a suspended restore can be cancelled by tab navigation.
  const tabs = page.locator('.workspace-tabs[data-kind="search"] [role="tab"]')
  const firstTab = await tabs.first().getAttribute('data-tab-id')
  await page.getByRole('button', { name: 'Add new search tab', exact: true }).click()
  await ready()
  await tabs.first().click()
  await ready()
  await save()
  let receiveBatch
  const intercepted = new Promise(resolve => { receiveBatch = resolve })
  const holdBatch = route => route.request().postDataJSON().offset === 20 ? receiveBatch(route) : route.continue()
  await page.route(queryUrl, holdBatch)
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Reload Cache', exact: true }).click()
  const delayed = await intercepted
  assert.equal(await viewport.getAttribute('aria-busy'), 'true', 'Restoration stays busy between batches')
  await tabs.nth(1).click()
  await ready()
  const secondTexts = await rows.allInnerTexts()
  assert.equal(await rows.count(), 20)
  const lateResponse = page.waitForResponse(response => response.url().endsWith('/admin/search-configuration/query') && response.request().postDataJSON().offset === 20)
  await delayed.continue()
  await page.unroute(queryUrl, holdBatch)
  await lateResponse
  assert.deepEqual(await rows.allInnerTexts(), secondTexts, 'A cancelled restore cannot replace the new tab')
  await page.locator(`[role="tab"][data-tab-id="${firstTab}"]`).click()
  await ready()
  assert.deepEqual(await rows.allInnerTexts(), texts, 'Returning to the cancelled tab rebuilds its complete projection')
  assert(await rows.nth(30).getByRole('checkbox').isChecked())
  assert.equal(await viewport.evaluate(node => node.scrollTop), scroll)

  await page.setViewportSize({ width: 320, height: 740 })
  await save()
  await page.reload()
  await ready()
  assert.deepEqual(await rows.allInnerTexts(), texts)
  assert(await rows.nth(30).getByRole('checkbox').isChecked())
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.screenshot({ path: '../.screenshots/handler-current/stream-workspace-infinite-320.png', animations: 'disabled' })
  await page.route(queryUrl, overlapping)
  await page.reload()
  await ready()
  assert.equal(await rows.count(), texts.length - 1, 'Saved projections also deduplicate overlapping server batches')
  assert.equal(await rows.getByRole('checkbox', { checked: true }).count(), 1)
  await page.unroute(queryUrl, overlapping)
  const exhausted = async route => {
    if (route.request().postDataJSON().offset !== 20) { await route.continue(); return }
    const response = await route.fetch(), body = await response.json()
    body.result.records = body.result.records.slice(0, 1)
    body.result.total = 21
    await route.fulfill({ response, json: body })
  }
  await page.route(queryUrl, exhausted)
  before = calls.length
  await page.reload()
  await ready()
  assert.deepEqual(calls.slice(before).map(call => call.offset), [0, 20], 'A shortened server result stops restoration early')
  assert.equal(await rows.count(), 21)
  assert.equal(await page.getByRole('button', { name: 'Load more', exact: true }).count(), 0)
  assert.deepEqual((await snapshot()).state.selectedKeys, [], 'Selection cannot restore an object absent from current results')
  assert.deepEqual((await snapshot()).loadedOffsets, [0, 20])
  await page.unroute(queryUrl, exhausted)
  let receiveSearch, held = false
  const submitted = new Promise(resolve => { receiveSearch = resolve })
  const holdSearch = route => {
    if (!held && route.request().postDataJSON().filters.length) { held = true; receiveSearch(route) }
    else route.continue()
  }
  await page.route(queryUrl, holdSearch)
  await search.fill('pipeline')
  await search.press('Enter')
  const pendingSearch = await submitted
  await tabs.nth(1).click()
  await ready()
  const submittedResponse = page.waitForResponse(response => response.url().endsWith('/admin/search-configuration/query') && response.request().postDataJSON().filters.length > 0)
  await pendingSearch.continue()
  await submittedResponse
  await page.unroute(queryUrl, holdSearch)
  await tabs.first().click()
  await ready()
  assert.equal(await search.inputValue(), 'pipeline')
  assert(await rows.count() > 0)
  assert((await rows.allInnerTexts()).every(text => text.toLowerCase().includes('pipeline')), 'A cancelled submitted search cannot replay the previous executed query')
  assert.deepEqual(errors, [])
  console.log('PASS infinite restore: CG batches, query/draft, selection/scroll, atomic error/retry, tab/submitted-search cancellation, append retry/duplicates/raw offset, current exhaustion and 320px reload')
} finally { await browser.close() }
