import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const output = '../.screenshots/continuous-topology'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1454, height: 1000 } })
page.setDefaultTimeout(10000)
const errors = []
page.on('pageerror', error => errors.push(error.message))
const project = process.env.STREAM_CHECK_PROJECT
const surface = page.locator('.workspace-browser .result-presentation:visible')
const branch = title => surface.locator('.result-item-branch').filter({ has: page.locator('strong', { hasText: new RegExp('^' + title + '$') }) })
const capture = async name => {
  await page.mouse.move(0, 0)
  await page.waitForTimeout(560)
  const clip = await surface.evaluate(element => {
    const bounds = element.getBoundingClientRect()
    const rows = [...element.querySelectorAll('article')]
    const arm = rows.find(row => row.dataset.resultKey?.includes('code=DEMO_ARM'))
    const children = rows.filter(row => row.dataset.nodeId.startsWith(arm.dataset.nodeId + '/'))
    return { x: bounds.x, y: arm.getBoundingClientRect().top, width: bounds.width,
      height: children.at(-1).getBoundingClientRect().bottom - arm.getBoundingClientRect().top + 12 }
  })
  await page.screenshot({ path: output + '/web-' + name + '.png', clip })
}
try {
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  const url = process.argv[2] + '/projects/' + project + '/?search_type=cg%2Fassets&view=table'
  await page.goto(url)
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, project)
  await page.goto(url)
  await page.getByLabel('Change search results view', { exact: true }).click()
  await page.getByRole('menuitemradio', { name: 'Continuous tree', exact: true }).click()
  const arm = surface.locator('article[data-result-key*="code=DEMO_ARM"]').first()
  await arm.waitFor()
  assert.equal(await arm.locator('.result-description').innerText(), 'Sample asset: Robot Arm · 3D Asset · Props')
  await arm.getByRole('button', { name: 'Expand item', exact: true }).click()
  const snapshot = surface.locator('.result-item-snapshot').filter({ has: page.locator('strong', { hasText: 'Robot Arm.md' }) })
  await snapshot.waitFor()
  const description = await snapshot.locator('.result-snapshot-description').innerText()
  assert.ok(description.includes('No description'), description)
  assert.ok(description.includes('admin:'), description)
  const ids = await surface.locator('article').evaluateAll(rows => rows.map(row => row.dataset.nodeId))
  assert.equal(ids[ids.indexOf(await arm.getAttribute('data-node-id')) + 1], await snapshot.getAttribute('data-node-id'), 'Publish snapshot immediately follows owner')
  await capture('publish')
  await branch('Texture').getByRole('button', { name: 'Expand item', exact: true }).click()
  const metal = surface.locator('article[data-result-key*="code=DEMO_TEX_METAL"]').first()
  await metal.waitFor()
  assert.equal(await metal.locator('.result-description').innerText(), 'Sample texture')
  assert.ok((await metal.innerText()).includes('DEMO_CAT_MAT'))
  assert.ok((await metal.innerText()).includes('Diffuse'))
  await metal.getByRole('button', { name: 'Expand item', exact: true }).click()
  await branch('Attachment').waitFor()
  const subtree = await surface.locator('article').evaluateAll(rows => {
    const texture = rows.find(row => row.dataset.resultKey?.includes('code=DEMO_TEX_METAL'))
    return rows.filter(row => row.dataset.nodeId.startsWith(texture.dataset.nodeId + '/')).map(row => row.getAttribute('aria-label'))
  })
  assert.deepEqual(subtree, ['Icon', 'Attachment', 'Publish'], 'No reverse Assets relation under a texture reached from Assets')
  await capture('texture')
  await page.reload()
  await branch('Attachment').waitFor()
  assert.equal(await surface.locator('article[data-result-key*="code=DEMO_ARM"]').count(), 1, 'No recursive ancestor returned after layout restoration')
  await capture('restored')
  const offsets = []
  await page.route('**/admin/result-items', async route => {
    const body = route.request().postDataJSON()
    if (body.search_keys?.[0]?.includes('code=DEMO_ARM') && body.branch?.kind === 'children') {
      const response = await route.fetch(), data = await response.json()
      data.result.items[0].branches.find(branch => branch.search_type === 'cg/assets').count = 2
      await route.fulfill({ response, json: data })
    } else if (body.search_keys?.[0]?.includes('code=DEMO_ARM') && body.branch?.kind === 'relation' && body.branch.search_type === 'cg/assets') {
      offsets.push(body.offset)
      if (offsets.length === 1) {
        const response = await route.fetch({ postData: JSON.stringify({ ...body, branch: undefined,
          search_keys: [body.search_keys[0], 'cg/assets?project=' + project + '&code=DEMO_BODY'] }) })
        const data = await response.json()
        await route.fulfill({ response, json: { ...data, result: { items: data.result.items, has_next: true } } })
      } else await route.fulfill({ json: { result: { items: [], has_next: false } } })
    } else await route.continue()
  })
  await page.reload()
  await branch('Assets').getByRole('button', { name: 'Expand item', exact: true }).click()
  await page.getByRole('button', { name: 'Load more', exact: true }).click()
  await page.getByRole('button', { name: 'Load more', exact: true }).waitFor({ state: 'detached' })
  assert.deepEqual(offsets, [0, 2], 'Pagination advances by server rows, including an excluded ancestor')
  const armId = await surface.locator('article[data-result-key*="code=DEMO_ARM"]').first().getAttribute('data-node-id')
  assert.equal(await surface.locator('article[data-result-key*="code=DEMO_ARM"]').count(), 1)
  assert.equal(await surface.locator('article[data-result-key*="code=DEMO_BODY"]').evaluateAll((rows, id) =>
    rows.filter(row => row.dataset.nodeId.startsWith(id + '/')).length, armId), 1)
  assert.deepEqual(errors, [])
  console.log('PASS: native publish placement, metadata, ancestor type recursion and restored tree')
} finally { await browser.close() }
