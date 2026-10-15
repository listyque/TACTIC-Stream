import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'
import { mkdir, writeFile } from 'node:fs/promises'

const root = fileURLToPath(new URL('..', import.meta.url))
const identity = JSON.stringify(['sthpw', 'raw_background'])
const records = [
  { key: [1], revision: 'first', values: { id: 1, value: 'old', number: 7 } },
  { key: [2], revision: 'second', values: { id: 2, value: 'background', number: 8 } },
]
const writes = [], errors = []
let backgroundChanged = false
const result = () => ({ identity, revision: 'table', canWrite: true,
  metadata: { columns: ['id', 'value', 'number', 'password'].map(name => ({ name, type: ['value', 'password'].includes(name) ? 'TEXT' : 'INTEGER', readonly: name === 'password' })),
    total: records.length, offset: 0, pageSize: 50, label: 'sthpw / raw_background' },
  document: { offset: 0, rows: structuredClone(records) } })
const html = `<!doctype html><html><body><div id="toolbar"></div><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import RawDatabase from '/src/features/administration/RawDatabase.vue';
import {initializeAppearance,appearance} from '/src/appearance.js';import {tooltipDirective} from '/src/controls/tooltip.js';import {windowDirective} from '/src/controls/window.js';
import '/src/theme.css';import '/src/style.css';appearance.language='en';initializeAppearance();window.appearance=appearance;
createApp({mounted(){window.host=this},render(){return h(RawDatabase,{ref:'editor',ticket:'fixture',project:'admin',toolbarTarget:'#toolbar',presentationVisible:true})}})
.provide('openHelp',()=>{}).directive('tooltip',tooltipDirective).directive('window',windowDirective).mount('#app')
</script><style>html,body{height:100%;margin:0}#app{height:calc(100% - 80px);padding:12px;display:flex;flex-direction:column;min-height:0}</style></body></html>`
let server, browser
try {
  server = await createServer({ root, configFile: false, plugins: [vue(), {
    name: 'raw-save-fixture', configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        try {
          if (request.url === '/raw-fixture') {
            response.setHeader('Content-Type', 'text/html')
            response.end(await server.transformIndexHtml(request.url, html)); return
          }
          if (!request.url?.startsWith('/admin/raw-database/')) return next()
          let body = ''; for await (const chunk of request) body += chunk
          const parameters = JSON.parse(body)
          const action = request.url.split('/').at(-1)
          let value
          if (action === 'list') value = { catalog: [{ identity, label: 'sthpw / raw_background' }] }
          else if (action === 'load') {
            value = result()
            if (!backgroundChanged) {
              records[1].values.number++; records[1].revision = 'background-new'; backgroundChanged = true
            }
          } else if (action === 'save') {
            writes.push(parameters.document)
            const stale = parameters.document.rows.some(row => row.key !== null &&
              records.find(record => JSON.stringify(record.key) === JSON.stringify(row.key))?.revision !== row.revision)
            if (stale) {
              response.statusCode = 409; value = { error: 'A row changed or was deleted. Reload before saving.' }
            } else {
              for (const row of parameters.document.rows) {
                if (row.key === null) records.push({ key: [3], revision: 'new', values: row.values })
                else if (row.deleted) records.splice(records.findIndex(record => record.key[0] === row.key[0]), 1)
                else Object.assign(records.find(record => record.key[0] === row.key[0]).values, row.values)
              }
              value = result()
            }
          } else throw new Error('Unexpected raw operation: ' + action)
          response.setHeader('Content-Type', 'application/json')
          response.end(JSON.stringify(response.statusCode === 409 ? value : { result: value }))
        } catch (error) { errors.push(error.message); response.statusCode = 500; response.end(error.message) }
      })
    },
  }], server: { host: '127.0.0.1', port: 0 } })
  await server.listen()
  browser = await chromium.launch({ headless: true, channel: process.env.STREAM_BROWSER_CHANNEL })
  const page = await browser.newPage({ viewport: { width: 1400, height: 940 } })
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(server.resolvedUrls.local[0] + 'raw-fixture')
  const editor = page.getByRole('dialog', { name: 'Cell editor', exact: true })
  async function editCell(name, value, mode = 'value') {
    await page.getByLabel(name, { exact: true }).click()
    await editor.getByLabel('Value mode', { exact: true }).selectOption(mode)
    if (mode === 'value') await editor.getByLabel('Cell value', { exact: true }).fill(value)
    await editor.getByRole('button', { name: 'Apply', exact: true }).click()
    await editor.waitFor({ state: 'hidden' })
  }
  assert.equal(await page.getByLabel('value · 1', { exact: true }).inputValue(), 'old')
  assert(await page.getByLabel('value · 1', { exact: true }).getAttribute('readonly') !== null)
  await page.getByLabel('value · 1', { exact: true }).click()
  await editor.getByLabel('Cell value', { exact: true }).fill('cancelled')
  await editor.getByRole('button', { name: 'Cancel', exact: true }).click()
  assert.equal(await page.getByLabel('value · 1', { exact: true }).inputValue(), 'old')
  await editCell('value · 1', 'edited')
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.deepEqual(writes[0], { offset: 0, rows: [{ key: [1], revision: 'first', deleted: false, values: { value: 'edited' } }] })
  assert.equal(records[0].values.value, 'edited')
  assert.equal(records[1].values.number, 9)
  assert.equal(await page.getByRole('alert').count(), 0)
  await editCell('value · 1', 'stale edit')
  records[0].revision = 'target-changed'
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.equal(records[0].values.value, 'edited')
  assert(await page.getByRole('alert').inputValue().then(text => text.includes('row changed')))
  await page.evaluate(async () => { const editor = window.host.$refs.editor; editor.discard(); await editor.load('load') })
  await page.getByRole('button', { name: 'Delete row', exact: true }).nth(1).click()
  await page.getByRole('button', { name: 'New row', exact: true }).click()
  await editCell('value · 3', 'new')
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.equal(writes[2].rows.length, 2)
  assert.deepEqual(writes[2].rows[0].key, [2])
  assert.equal(writes[2].rows[0].deleted, true)
  assert.equal(writes[2].rows[1].key, null)
  assert.deepEqual(writes[2].rows[1].values, { value: 'new' })
  assert.equal(await page.getByRole('alert').count(), 0)
  await editCell('value · 1', '', 'null')
  assert.equal(await page.getByLabel('value · 1', { exact: true }).inputValue(), 'NULL')
  await editCell('value · 1', '')
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.equal(writes[3].rows[0].values.value, '')
  await editCell('value · 1', 'NULL')
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.equal(writes[4].rows[0].values.value, 'NULL')
  await page.getByLabel('number · 1', { exact: true }).click()
  await editor.getByLabel('Cell value', { exact: true }).fill('NaN')
  await editor.getByRole('button', { name: 'Apply', exact: true }).click()
  assert.equal(await editor.getByRole('alert').count(), 1)
  await editor.getByLabel('Cell value', { exact: true }).fill('9223372036854775807')
  await editor.getByRole('button', { name: 'Apply', exact: true }).click()
  await page.getByRole('button', { name: 'Save to server', exact: true }).click()
  await page.locator('[data-frame=adminConfirmSave]').click()
  await page.waitForFunction(() => !window.host.$refs.editor.busy)
  assert.equal(writes[5].rows[0].values.number, '9223372036854775807')
  records[0].values.value = 'old'
  await page.evaluate(() => window.host.$refs.editor.load('load'))
  const report = root + '/../reports/raw-cell-2026-10-14'
  await mkdir(report, { recursive: true })
  const measurements = []
  for (const language of ['en', 'ru']) for (const width of [1400, 900]) for (const mode of ['dark', 'light']) {
    await page.setViewportSize({ width, height: width === 1400 ? 940 : 620 })
    await page.evaluate(({ language, mode }) => { window.appearance.language = language; window.appearance.mode = mode }, { language, mode })
    await page.getByLabel('value · 1', { exact: true }).focus()
    await page.getByLabel('value · 1', { exact: true }).press('F2')
    const dialog = page.getByRole('dialog', { name: language === 'en' ? 'Cell editor' : 'Редактор ячейки', exact: true })
    await dialog.waitFor()
    await dialog.evaluate((element, width) => { element.style.width = (width === 1400 ? 642 : 482) + 'px'; element.style.height = '442px' }, width)
    await page.waitForFunction(() => {const d=document.querySelector('.raw-cell-editor'), a=d?.querySelector('textarea');if(!a)return false;const b=a.getBoundingClientRect(),w=d.getBoundingClientRect();return b.height>=100&&b.x>w.x&&b.right<w.right})
    const field = dialog.locator('textarea'), bounds = await field.boundingBox(), windowBounds = await dialog.boundingBox()
    assert(bounds.height >= 100 && bounds.x > windowBounds.x && bounds.x + bounds.width < windowBounds.x + windowBounds.width, JSON.stringify({bounds,windowBounds}))
    assert(windowBounds.x >= 0 && windowBounds.x + windowBounds.width <= width)
    measurements.push({ language, viewportWidth: width, mode, dialog: windowBounds, field: bounds,
      combo: await dialog.locator('select').boundingBox(), apply: await dialog.locator('[data-frame=rawCellApply]').boundingBox(),
      styles: await dialog.evaluate(element => { const s = getComputedStyle(element); return {
        controlHeight: s.getPropertyValue('--control-height'), background: s.backgroundColor,
        headerMargin: getComputedStyle(element.querySelector('header')).marginBottom,
        descriptionWeight: getComputedStyle(element.querySelector('[data-frame=rawCellDescription]')).fontWeight,
        descriptionHeight: getComputedStyle(element.querySelector('[data-frame=rawCellDescription]')).lineHeight,
        descriptionFont: getComputedStyle(element.querySelector('[data-frame=rawCellDescription]')).font,
        hintFont: getComputedStyle(element.querySelector('[data-frame=rawCellApplyHelp]')).font,
        hintText: element.querySelector('[data-frame=rawCellApplyHelp]').textContent,
      } }) })
    await dialog.screenshot({ path: report + `/stream-${language}-${width}-${mode}.png` })
    await field.press('Escape')
    await dialog.waitFor({ state: 'hidden' })
  }
  await writeFile(report + '/stream-measurements.json', JSON.stringify(measurements, null, 2))
  records.splice(0, records.length, ...Array.from({ length: 50 }, (_, index) => ({
    key: [index + 1], revision: String(index),
    values: { id: index + 1, value: String(index), number: 7, password: '[redacted]' },
  })))
  await page.evaluate(() => window.host.$refs.editor.load('load'))
  const scroll = page.locator('.frame-grid-body')
  for (const width of [1400, 900]) for (const mode of ['dark', 'light']) {
    await page.setViewportSize({ width, height: width === 1400 ? 940 : 620 })
    await page.evaluate(({ mode, width }) => {
      window.appearance.language = 'en'; window.appearance.mode = mode
      document.querySelector('.raw-database').style.width = (width - 290) + 'px'
    }, { mode, width })
    for (const horizontal of [0, 120]) {
      // Let ResizeObserver publish the new shared scene before measuring the fixed header.
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
      await scroll.evaluate((element, x) => { element.scrollTop = 1; element.scrollLeft = x }, horizontal)
      const bounds = await page.locator('[data-frame=rawTableViewport]').boundingBox()
      assert(bounds.y>=0&&bounds.y+36<page.viewportSize().height,JSON.stringify({bounds, viewport:page.viewportSize(), body:await page.locator('.frame-host-body').boundingBox()}))
      const clip = { x: bounds.x + 2, y: bounds.y + 2, width: bounds.width - 22, height: 36 }
      const baseline = await page.screenshot({ clip })
      for (const vertical of [100, 493]) {
        await scroll.evaluate((element, y) => { element.scrollTop = y }, vertical)
        const heading = await page.locator('[data-frame=rawTableViewport_column_0]').boundingBox()
        assert(Math.abs(heading.y - bounds.y) <= 1,JSON.stringify({heading,bounds}))
        assert((await page.screenshot({ clip })).equals(baseline), `Opaque header: ${width}/${mode}/${horizontal}/${vertical}`)
      }
    }
  }
  assert.deepEqual(errors, [])
  console.log('Raw Vue cell editor and opaque sticky header: save flows and 16 rendered scroll comparisons passed.')
} finally { await browser?.close(); await server?.close() }
