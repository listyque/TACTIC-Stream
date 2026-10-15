import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const require = createRequire(new URL('../frontend/package.json', import.meta.url))
const { chromium } = require('playwright')
let input = ''
for await (const chunk of process.stdin) input += chunk
const { url, ticket } = JSON.parse(input)
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL })
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 940 }, hasTouch: true })
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  if (process.env.RAW_DATABASE_STALE_FIELD) {
    await page.route('**/ui/assets/AppTextField.js', async route => {
      const response = await route.fetch()
      const body = (await response.text()).replace(/,\s*tableCell: Boolean/, '')
        .replace(/class: normalizeClass\(\["app-text-field", \{ "table-cell": __props.tableCell \}\]\)/, 'class: "app-text-field"')
      await route.fulfill({ response, body })
    })
  }
  await page.addInitScript(ticket => localStorage.setItem('tactic_stream.session', JSON.stringify({ login: 'admin', ticket, project: 'admin', type: 'sthpw/project' })), ticket)
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ language:'en', theme:'md3', mode:'dark' })))
  await page.goto(url + '/')
  await page.getByLabel('More options', { exact: true }).click()
  await page.getByRole('button', { name: 'Administration', exact: true }).click()
  const admin = page.getByRole('dialog', { name: 'Administration', exact: true })
  await admin.getByRole('button', { name: 'Raw database', exact: true }).click()
  const raw = admin.getByRole('region', { name: 'Raw database', exact: true })
  const assertHeaderAboveRows = async () => {
    const header = await raw.locator('thead').boundingBox()
    const row = await raw.locator('tbody tr').first().boundingBox()
    assert.ok(row.y >= header.y + header.height - 1, 'Raw heading overlaps the first row')
  }
  await raw.getByLabel('Database table').selectOption({ label: 'sthpw / raw_browser' })
  const cell = raw.getByLabel('value · 1', { exact: true })
  await assertHeaderAboveRows()
  await raw.getByLabel('Filter tables').fill('not-a-table')
  assert.equal(await raw.getByLabel('Database table').locator('option').count(), 1)
  assert.equal(await raw.getByLabel('Database table').locator('option').innerText(), 'sthpw / raw_browser')
  await raw.getByLabel('Filter tables').press('Escape')
  assert.equal(await raw.getByLabel('Filter tables').inputValue(), '')
  const readonly = raw.getByLabel('password · 1', { exact: true })
  assert.equal(await readonly.isDisabled(), false)
  assert.equal(await readonly.isEditable(), false)
  assert.equal(await readonly.inputValue(), '"[redacted]"')
  assert.equal(await raw.locator('.raw-page-range').innerText(), '1–1 / 1')
  assert.equal(Math.round((await cell.boundingBox()).width), 229)
  const assertSquareCells = async () => assert.deepEqual(await raw.locator('table, th, td, .app-text-field').evaluateAll(elements =>
    elements.filter(element => {
      const style = getComputedStyle(element)
      return ['borderTopLeftRadius', 'borderTopRightRadius', 'borderBottomLeftRadius', 'borderBottomRightRadius']
        .some(corner => style[corner] !== '0px')
    }).map(element => element.tagName)), [])
  await assertSquareCells()
  for (const theme of ['md3', 'material5', 'fluent']) {
    for (const mode of ['light', 'dark']) {
      await page.evaluate(({ theme, mode }) => {
        document.documentElement.dataset.theme = theme
        document.documentElement.dataset.mode = mode
      }, { theme, mode })
      await assertSquareCells()
    }
  }
  assert.deepEqual(await cell.evaluate(element => {
    const style = getComputedStyle(element)
    return [style.borderRadius, style.borderWidth, style.backgroundColor]
  }), ['0px', '0px', 'rgba(0, 0, 0, 0)'])
  await cell.tap()
  await assertSquareCells()
  assert.match(await cell.evaluate(element => getComputedStyle(element).boxShadow), /inset/)
  await cell.fill('"new"')
  if (process.env.RAW_DATABASE_SCREENSHOT) await raw.screenshot({ path: process.env.RAW_DATABASE_SCREENSHOT })
  assert.equal(await raw.getByLabel('Database table').isDisabled(), true)
  await admin.getByRole('button', { name: 'Save to server', exact: true }).click()
  await raw.getByLabel('Database table').waitFor({ state: 'visible' })
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await cell.inputValue(), '"new"')
  for (const value of ['NaN', 'Infinity', '1e400', '{"value":1e400}']) {
    await cell.fill(value)
    await admin.getByRole('button', { name:'Save to server', exact:true }).click()
    assert.equal(await raw.getByRole('alert').innerText(), 'Enter valid JSON in each cell. Leave new cells empty for DEFAULT.')
    assert.equal(await cell.isEditable(), true)
  }
  await admin.getByRole('button', { name:'Discard', exact:true }).click()
  await raw.getByRole('button', { name:'Discard changes', exact:true }).click()
  assert.equal(await raw.getByRole('alert').count(), 0)
  await cell.fill('"discard this"')
  await admin.getByRole('button', { name:'Discard', exact:true }).click()
  assert.equal(await cell.inputValue(), '"discard this"')
  await raw.getByRole('button', { name:'Discard changes', exact:true }).click()
  assert.equal(await cell.inputValue(), '"new"')
  await raw.getByRole('button', { name: 'New row', exact: true }).tap()
  await raw.getByLabel('value · 2', { exact: true }).fill('"created"')
  await assertSquareCells()
  await admin.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await raw.getByLabel('number · 2', { exact: true }).inputValue(), '7')
  const downloadPromise = page.waitForEvent('download')
  await raw.getByRole('button', { name: 'Export CSV', exact: true }).click()
  const download = await downloadPromise
  assert.equal(download.suggestedFilename(), 'sthpw_raw_browser.csv')
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  await raw.getByRole('button', { name: 'Delete row', exact: true }).first().click()
  await assertSquareCells()
  await admin.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await raw.locator('tbody tr').count(), 1)
  for (const width of [900, 1400]) {
    await page.setViewportSize({ width, height: 940 })
    assert.equal(await raw.evaluate(element => element.scrollWidth <= element.clientWidth + 1), true)
    const filterBox = await raw.getByLabel('Filter tables').boundingBox()
    const actionBox = await raw.getByRole('button', { name:'New row', exact:true }).boundingBox()
    assert.equal(Math.abs(actionBox.y - filterBox.y) <= 1, width === 1400)
  }
  await page.evaluate(() => { document.documentElement.dataset.theme = 'md3'; document.documentElement.dataset.mode = 'dark' })
  if (process.env.RAW_DATABASE_PARITY_SCREENSHOT) {
    for (const close of await page.getByRole('button', { name:'Dismiss notification', exact:true }).all()) await close.click()
    await page.screenshot({ path: process.env.RAW_DATABASE_PARITY_SCREENSHOT })
  }
  if (process.env.RAW_DATABASE_PARITY_METRICS) {
    const row = await raw.locator('tbody tr').boundingBox()
    const header = await raw.locator('thead').boundingBox()
    const input = await cell.boundingBox()
    console.log('Raw geometry:', JSON.stringify({ rowHeight: row.height, headerHeight: header.height, columnWidth: (await raw.locator('tbody td').nth(1).boundingBox()).width, inputWidth: input.width, inputHeight: input.height }))
    console.log('Raw typography:', JSON.stringify(await raw.evaluate(element => ['.notice', '.muted', '.app-select', '.app-text-field'].map(selector => {
      const item = element.querySelector(selector), style = getComputedStyle(item)
      return { selector, font:style.fontSize, weight:style.fontWeight, lineHeight:style.lineHeight, height:item.getBoundingClientRect().height }
    }))))
    console.log('Raw actions:', JSON.stringify(await raw.locator('.raw-row-actions button').evaluateAll(buttons => buttons.map(button => ({label:button.innerText,width:button.getBoundingClientRect().width,height:button.getBoundingClientRect().height})))) )
  }
  await raw.getByRole('button', { name: 'DROP TABLE', exact: true }).click()
  assert.equal(await raw.getByRole('button', { name: 'DROP TABLE', exact: true }).last().isDisabled(), true)
  await raw.getByLabel('Confirm table name').fill('sthpw / raw_browser')
  await raw.getByRole('button', { name: 'DROP TABLE', exact: true }).last().click()
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await raw.getByLabel('Database table').locator('option').filter({ hasText: 'sthpw / raw_browser' }).count(), 0)
  await raw.getByLabel('Database table').selectOption({ label:'sthpw / raw_page_profile' })
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await raw.locator('tbody tr').count(), 50)
  await assertHeaderAboveRows()
  const pageStart = performance.now()
  await raw.getByRole('button', { name:'Next', exact:true }).click()
  await page.waitForFunction(() => document.querySelector('.raw-page-range').innerText === '51–75 / 75')
  console.log('Browser next page ms:', Math.round(performance.now() - pageStart))
  assert.equal(await raw.locator('tbody tr').count(), 25)
  const pageCell = raw.getByLabel('value · 1', { exact:true })
  assert.equal(await pageCell.inputValue(), '"50"')
  await pageCell.fill('"page edit"')
  await admin.getByRole('button', { name:'Save to server', exact:true }).click()
  await page.waitForFunction(() => !document.querySelector('.raw-database [aria-label="Database table"]').disabled)
  assert.equal(await raw.locator('.raw-page-range').innerText(), '51–75 / 75')
  assert.equal(await pageCell.inputValue(), '"page edit"')
  await raw.getByRole('button', { name:'Previous', exact:true }).click()
  await page.waitForFunction(() => document.querySelector('.raw-page-range').innerText === '1–50 / 75')
  assert.equal(await pageCell.inputValue(), '"0"')
  assert.deepEqual(errors, [])
  const invalid = await page.request.post(url + '/admin/raw-database/list', { data: { ticket: 'invalid', project: 'admin' } })
  assert.equal(invalid.status(), 403)
  console.log('Raw database browser: cell edit, insert/defaults, touch, delete, CSV, page layouts and guarded DROP passed')
} finally { await browser.close() }
