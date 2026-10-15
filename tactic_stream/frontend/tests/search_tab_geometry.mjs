import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const titles = ['Episode animation and lighting review', 'Short', 'Rendering and compositing for selected episode', 'Final delivery approval']
const native = JSON.parse(readFileSync('../.screenshots/handler-current/search-tabs-geometry.json', 'utf8'))
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  page.setDefaultTimeout(12000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ language: 'en', mode: 'dark' })))
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, project)
  const session = await page.evaluate(() => JSON.parse(localStorage.getItem('tactic_stream.session') || sessionStorage.getItem('tactic_stream.session')))
  const auth = { ticket: session.ticket, project, search_type: 'cg/assets' }
  async function request(action, values = {}) {
    const response = await page.request.post(base + '/admin/search-configuration/' + action, { data: { ...auth, ...values } })
    assert.equal(response.status(), 200, await response.text())
    return (await response.json()).result
  }
  let settings = await request('settings')
  for (const title of titles) {
    settings = await request('save', { title, records: [], keyword: '', order_bys: [], revision: settings.revision })
    const preset = settings.presets.find(row => row.title === title)
    assert(preset)
    const link = 'tactic-search://open?' + new URLSearchParams({ project, search_type: 'cg/assets', view: preset.view })
    await page.goto(base + '/?' + new URLSearchParams({ link }))
    await page.locator('.workspace-tabs[data-kind="search"] [role="tab"][aria-selected="true"]').filter({ hasText: title }).waitFor()
    await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  }
  const root = page.locator('.workspace-tabs[data-kind="search"]')
  const tabs = root.getByRole('tab')
  async function geometry() {
    await page.waitForFunction(() => [...document.querySelectorAll('.workspace-tabs[data-kind="search"] .workspace-tab')].every(node => node.style.width))
    return root.evaluate(node => {
      const list = node.querySelector('.workspace-tab-list'), compact = node.classList.contains('compact')
      const records = [...node.querySelectorAll('.workspace-tab')].map(tab => {
        const label = tab.querySelector('[role="tab"] > span:not(.control-ripple, .control-ripple-clip)'), range = document.createRange()
        range.selectNodeContents(label)
        const current = tab.classList.contains('current'), close = !!tab.querySelector('.icon-button') && (!compact || current)
        const ideal = range.getBoundingClientRect().width + (close ? 64 : 32)
        const bounds = tab.getBoundingClientRect(), text = label.getBoundingClientRect(), font = getComputedStyle(label)
        if (Math.abs(text.left + text.width / 2 - bounds.left - bounds.width / 2) > 1) throw Error('Tab label is not centered')
        return { width: bounds.width, natural: Math.max(compact ? 84 : 96, compact ? Math.min(180, ideal) : ideal), current,
          font: { family: font.fontFamily, pixels: font.fontSize, weight: font.fontWeight } }
      })
      return { records, available: list.clientWidth, compact, minimum: compact ? 84 : 96,
        selected: node.querySelector('.workspace-tab.current').getBoundingClientRect().toJSON(), viewport: list.getBoundingClientRect().toJSON() }
    })
  }
  function assertGeometry(state) {
    const total = state.records.reduce((sum, row) => sum + row.natural, 0), current = state.records.find(row => row.current)
    const inactiveMinimum = (state.records.length - 1) * state.minimum
    const inactiveNatural = Math.max(inactiveMinimum, total - current.natural), remaining = state.available - current.natural
    for (const row of state.records) {
      assert.equal(row.font.pixels, '14px')
      assert.equal(row.font.weight, '400')
      const expected = total <= state.available || total <= state.records.length * state.minimum || row.current ? row.natural
        : remaining <= inactiveMinimum ? state.minimum : state.minimum + (row.natural - state.minimum) * ((remaining - inactiveMinimum) / (inactiveNatural - inactiveMinimum))
      assert(Math.abs(row.width - expected) < 1, `Width ${row.width} differs from native ${expected}`)
    }
    assert(state.selected.left >= state.viewport.left - 1)
    if (state.selected.width <= state.available) assert(state.selected.right <= state.viewport.right + 1)
  }
  assert.equal(await tabs.count(), 5)
  const order = () => tabs.evaluateAll(nodes => nodes.map(node => node.dataset.tabId))
  const originalOrder = await order()
  const dragSelectedId = await root.locator('[aria-selected="true"]').getAttribute('data-tab-id')
  const keyword = page.getByLabel('Search objects', { exact: true })
  // Reordering an inactive tab must preserve the active search's unsubmitted text.
  await keyword.fill('drag draft')
  const rows = root.locator('.workspace-tab')
  async function beginDrag(from, to) {
    await rows.nth(from).getByRole('tab').click({ trial: true })
    const start = await rows.nth(from).boundingBox(), finish = await rows.nth(to).boundingBox()
    const sourceWidth = await rows.nth(from).evaluate(node => parseFloat(getComputedStyle(node).width))
    const x = start.x + start.width / 2, y = start.y + start.height / 2
    await page.mouse.move(x, y); await page.mouse.down()
    await page.mouse.move(x + 3, y)
    assert.equal(await root.locator('.dragging').count(), 0, 'Small motion remains a click')
    await page.mouse.move(finish.x + finish.width / 2, y, { steps: 6 })
    await root.locator('.dragging').waitFor()
    await page.waitForTimeout(80)
    const state = await rows.evaluateAll(nodes => nodes.map(node => ({ offset: parseFloat(node.style.getPropertyValue('--tab-drag-x')),
      scale: getComputedStyle(node).scale, transition: getComputedStyle(node).transitionDuration })))
    assert.equal(state[from].scale, '1.03')
    assert.notEqual(await rows.nth(from).getByRole('tab').evaluate(node => getComputedStyle(node).backgroundColor), 'rgba(0, 0, 0, 0)', 'Native pressed state remains visible during pointer capture')
    const neighbour = from < to ? from + 1 : from - 1
    assert(Math.abs(state[neighbour].offset - (from < to ? -sourceWidth : sourceWidth)) < 1)
    assert(state[neighbour].transition.includes('0.056s'), 'Native medium timing for neighbour displacement')
    assert.equal(await root.locator('[aria-selected="true"]').getAttribute('data-tab-id'), dragSelectedId)
    return { start, finish }
  }
  await beginDrag(1, 3)
  assert.deepEqual(await order(), originalOrder, 'No commit during dragging')
  await page.screenshot({ path: '../.screenshots/handler-current/stream-search-tabs-drag.png' })
  await page.mouse.up()
  const movedOrder = [originalOrder[0], originalOrder[2], originalOrder[3], originalOrder[1], originalOrder[4]]
  assert.deepEqual(await order(), movedOrder)
  assert.equal(await keyword.inputValue(), 'drag draft')
  await page.reload(); await root.waitFor(); await keyword.waitFor()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  assert.deepEqual(await order(), movedOrder, 'Drag order survives browser reload')
  assert.equal(await keyword.inputValue(), 'drag draft')
  await beginDrag(3, 1); await page.mouse.up()
  assert.deepEqual(await order(), originalOrder, 'Reverse direction displaces neighbours by source width')
  await beginDrag(1, 3); await page.keyboard.press('Escape'); await page.mouse.up()
  assert.deepEqual(await order(), originalOrder, 'Escape cancels without committing')
  await beginDrag(1, 3); await page.evaluate(() => window.dispatchEvent(new Event('blur'))); await page.mouse.up()
  assert.deepEqual(await order(), originalOrder, 'Blur cancels without committing')
  await beginDrag(1, 3); await page.setViewportSize({ width: 1430, height: 1000 })
  await root.locator('.dragging').waitFor({ state: 'hidden' }); await page.mouse.up()
  assert.equal(await root.locator('.dragging').count(), 0)
  assert.deepEqual(await order(), originalOrder, 'Resize cancels stale geometry')
  await page.setViewportSize({ width: 1440, height: 1000 }); await page.waitForTimeout(100)
  const touch = await page.context().newCDPSession(page)
  async function touchDrag(cancel = false) {
    const start = await rows.nth(1).boundingBox(), finish = await rows.nth(3).boundingBox()
    const point = { x: start.x + start.width / 2, y: start.y + start.height / 2 }
    await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point] })
    for (const distance of [12, 30, finish.x + finish.width / 2 - point.x]) {
      await touch.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ ...point, x: point.x + distance }] })
    }
    await root.locator('.dragging').waitFor()
    assert.deepEqual(await order(), originalOrder)
    if (cancel === 'second-finger') {
      const first = { ...point, x: finish.x + finish.width / 2, id: 0 }
      await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [first, { ...first, x: first.x + 20, id: 1 }] })
      await root.locator('.dragging').waitFor({ state: 'hidden' })
    }
    await touch.send('Input.dispatchTouchEvent', { type: cancel ? 'touchCancel' : 'touchEnd', touchPoints: [] })
  }
  await touchDrag(true)
  assert.deepEqual(await order(), originalOrder, 'Cancelled touch preserves order')
  await touchDrag('second-finger')
  assert.deepEqual(await order(), originalOrder, 'A second finger cancels the single-pointer drag')
  await touchDrag()
  assert.deepEqual(await order(), movedOrder, 'Real touch pointer reorders tabs')
  assert.equal(await keyword.inputValue(), 'drag draft')
  assert.equal(await root.locator('[aria-selected="true"]').getAttribute('data-tab-id'), dragSelectedId)
  await beginDrag(3, 1); await page.mouse.up()
  await keyword.fill('')
  await touch.detach()
  const snapshots = {}
  for (const width of [1440, 1000, 720, 360, 320]) {
    await page.setViewportSize({ width, height: width < 720 ? 740 : 1000 })
    await page.waitForTimeout(100)
    snapshots[width] = await geometry()
    writeFileSync('../.screenshots/handler-current/stream-search-tabs-geometry.json', JSON.stringify(snapshots, null, 2))
    assertGeometry(snapshots[width])
    for (let index = 0; index < snapshots[width].records.length; index++) {
      // Qt's hinted advances and Chromium's fractional advances differ on long labels.
      assert(Math.abs(snapshots[width].records[index].natural - native[width][index].naturalTabWidth) < 8,
        `Text metrics differ from current Handler QML at ${width}, tab ${index}: ${snapshots[width].records[index].natural} vs ${native[width][index].naturalTabWidth}`)
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    await page.screenshot({ path: `../.screenshots/handler-current/stream-search-tabs-${width}.png`, animations: 'disabled' })
  }
  writeFileSync('../.screenshots/handler-current/stream-search-tabs-geometry.json', JSON.stringify(snapshots, null, 2))
  const overflowMenu = root.locator('.workspace-tab-menu'), historyMenu = root.locator('.workspace-tab-history')
  await root.getByLabel('All search tabs', { exact: true }).tap()
  const openRows = overflowMenu.getByRole('menuitemradio')
  await openRows.first().waitFor()
  assert.equal(await openRows.count(), 5)
  assert.equal(await overflowMenu.locator('[aria-checked="true"]').count(), 1)
  assert.equal(await openRows.first().evaluate(node => node === document.activeElement), true, 'Opening the menu focuses its first native action')
  await page.keyboard.press('ArrowDown')
  assert.equal(await openRows.nth(1).evaluate(node => node === document.activeElement), true, 'Arrow keys move by rows, skipping secondary close buttons')
  await page.keyboard.press('Tab')
  assert.equal(await overflowMenu.getByRole('menuitem', { name: 'Close search tab: ' + titles[0], exact: true }).evaluate(node => node === document.activeElement), true)
  await page.keyboard.press('ArrowDown')
  assert.equal(await openRows.nth(2).evaluate(node => node === document.activeElement), true)
  await page.keyboard.press('Escape')
  assert.equal(await overflowMenu.locator('summary').evaluate(node => node === document.activeElement), true)
  await overflowMenu.locator('summary').press('Enter')
  await openRows.first().waitFor()
  await openRows.filter({ hasText: titles[0] }).tap()
  await page.waitForFunction(title => document.querySelector('.workspace-tabs[data-kind="search"] [aria-selected="true"]')?.getAttribute('aria-label') === title, titles[0])
  await page.waitForTimeout(100)
  assertGeometry(await geometry())
  await root.getByRole('button', { name: 'Close search tab: ' + titles[0], exact: true }).tap()
  await page.waitForTimeout(100)
  assertGeometry(await geometry())
  assert.equal(await historyMenu.locator('.workspace-tab-history-count').innerText(), '1')
  await historyMenu.locator('summary').tap()
  await historyMenu.getByRole('menuitem', { name: titles[0], exact: true }).tap()
  await page.waitForTimeout(100)
  assertGeometry(await geometry())
  assert.equal(await historyMenu.count(), 0)
  await page.reload()
  await tabs.filter({ hasText: titles[0] }).waitFor()
  await page.waitForTimeout(100)
  assertGeometry(await geometry())
  const draft = page.getByLabel('Search objects', { exact: true })
  await draft.fill('Unsubmitted tab menu draft')
  const selectedId = await root.locator('[role="tab"][aria-selected="true"]').getAttribute('data-tab-id')
  for (const title of [titles[3], titles[2]]) {
    await overflowMenu.locator('summary').tap()
    await overflowMenu.getByRole('menuitem', { name: 'Close search tab: ' + title, exact: true }).tap()
    await tabs.filter({ hasText: title }).waitFor({ state: 'hidden' })
    assert.equal(await root.locator('[role="tab"][aria-selected="true"]').getAttribute('data-tab-id'), selectedId)
    assert.equal(await draft.inputValue(), 'Unsubmitted tab menu draft')
  }
  assert.equal(await historyMenu.locator('.workspace-tab-history-count').innerText(), '2')
  await historyMenu.locator('summary').tap()
  await historyMenu.getByRole('menuitem').first().waitFor()
  assert.deepEqual(await historyMenu.getByRole('menuitem').evaluateAll(nodes => nodes.map(node => node.getAttribute('aria-label'))), [titles[3], titles[2]])
  await page.screenshot({ path: '../.screenshots/handler-current/stream-search-tab-history-320.png', animations: 'disabled' })
  await historyMenu.getByRole('button', { name: 'Clear history', exact: true }).tap()
  await historyMenu.waitFor({ state: 'hidden' })
  assert.equal(await draft.inputValue(), 'Unsubmitted tab menu draft')
  await overflowMenu.locator('summary').tap()
  await overflowMenu.getByRole('button', { name: 'Move tab left', exact: true }).tap()
  assert.equal(await tabs.nth(1).getAttribute('data-tab-id'), selectedId)
  await overflowMenu.locator('summary').tap()
  await overflowMenu.getByRole('button', { name: 'Move tab right', exact: true }).tap()
  assert.equal(await tabs.last().getAttribute('data-tab-id'), selectedId)
  for (let index = 0; index < 12; index++) {
    const before = await tabs.count()
    await root.getByLabel('Add new search tab', { exact: true }).tap()
    await page.waitForFunction(count => document.querySelectorAll('.workspace-tabs[data-kind="search"] [role="tab"]').length === count + 1, before)
    await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  }
  for (const width of [1000, 360, 320]) {
    await page.setViewportSize({ width, height: width === 1000 ? 400 : 740 })
    await overflowMenu.locator('summary').click()
    const panel = overflowMenu.locator('.account-panel')
    await overflowMenu.getByRole('menuitemradio').first().waitFor()
    await page.waitForTimeout(160)
    const bounds = await panel.boundingBox()
    assert(bounds.x >= 3 && bounds.x + bounds.width <= width - 3)
    assert(bounds.y >= 3 && bounds.y + bounds.height <= (width === 1000 ? 400 : 740) - 3)
    assert.equal(await overflowMenu.getByRole('menuitemradio').count(), 15)
    assert.equal(await overflowMenu.getByRole('menuitemradio').first().evaluate(node => getComputedStyle(node).fontWeight), '400')
    assert(await overflowMenu.getByRole('menuitemradio').first().locator('[data-icon="tab"]').count())
    await page.screenshot({ path: `../.screenshots/handler-current/stream-search-tabs-menu-${width}.png`, animations: 'disabled' })
    await overflowMenu.getByRole('menuitemradio').first().click()
    assert.equal(await tabs.first().getAttribute('aria-selected'), 'true')
  }
  await page.reload()
  await tabs.first().waitFor()
  assert.equal(await historyMenu.count(), 0, 'Cleared history stays cleared after reload')
  // A fitted final tab cannot be closed; the history menu does not duplicate open tabs.
  await page.setViewportSize({ width: 320, height: 740 })
  while (await tabs.count() > 1) {
    if (await overflowMenu.isVisible()) {
      await overflowMenu.locator('summary').click()
      await overflowMenu.locator('[data-menu-secondary]').last().click()
    } else await root.locator('.workspace-tab > .icon-button').last().click()
    await page.waitForTimeout(30)
  }
  assert.equal(await root.locator('.workspace-tab > .icon-button').count(), 0)
  assert.equal(await overflowMenu.count(), 0)
  await historyMenu.locator('summary').click()
  assert.equal(await historyMenu.getByRole('menuitemradio').count(), 0)
  await page.keyboard.press('Escape')
  await page.reload()
  await tabs.first().waitFor()
  await page.waitForTimeout(100)
  assertGeometry(await geometry())
  assert.deepEqual(errors, [])
  console.log('PASS: native tab geometry/motion, mouse/touch reorder, Escape/blur/resize/pointer cancellation, draft/order reload, row menus, keyboard/secondary close, history and bounded scrolling at 1000/360/320')
} finally { await browser.close() }
