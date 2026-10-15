import { selectProject } from './project_selection.mjs'
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.setDefaultTimeout(12000)
const errors = [], previews = []
const images = []
page.on('pageerror', error => errors.push(error.message))
page.on('response', async response => {
  if (response.url().includes('/assets/sthpw/')) images.push([response.url(), response.status()])
  if (response.url().endsWith('/admin/rpc') && response.request().postDataJSON()?.method === 'get_snapshot') previews.push(await response.json())
})
try {
  await page.addInitScript(() => localStorage.setItem('tactic_stream.preferences',JSON.stringify({checkin:{commitQueueAutoClean:false}})))
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill('private-test-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, 'one')
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Administration', exact: true }).click()
  const editor = page.locator('.search-types-editor')
  const administration = page.getByRole('dialog', { name: 'Administration', exact: true })
  const ready = () => page.waitForFunction(() => document.querySelector('.search-types-editor')?.getAttribute('aria-busy') === 'false')
  await ready()
  await administration.getByRole('button', { name: 'New Search Type', exact: true }).click()
  await editor.getByLabel('Title', { exact: true }).fill('Browser preview')
  const picker = editor.locator('.image-picker')
  await picker.locator('input[type="file"]').setInputFiles({ name: 'bad.png', mimeType: 'image/png', buffer: Buffer.from('not an image') })
  await picker.getByRole('alert').getByText('The selected preview is not a readable image', { exact: true }).waitFor()
  assert.equal(await picker.getByRole('button', { name: 'Undo image selection', exact: true }).count(), 0)
  const image = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 8; canvas.height = 8
    const context = canvas.getContext('2d'); context.fillStyle = 'red'; context.fillRect(0, 0, 8, 8)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  const file = { name: 'Preview.png', mimeType: 'image/png', buffer: Buffer.from(image, 'base64') }
  await picker.locator('input[type="file"]').setInputFiles(file)
  await picker.getByText('A new preview is ready to be queued', { exact: true }).waitFor()
  await picker.getByRole('button', { name: 'Undo image selection', exact: true }).click()
  await picker.getByText('Preview is optional', { exact: true }).waitFor()
  await picker.locator('input[type="file"]').setInputFiles(file)
  await picker.getByText('A new preview is ready to be queued', { exact: true }).waitFor()
  await editor.getByLabel('Choose color for Color', { exact: true }).click()
  await page.getByRole('dialog', { name: 'Choose a color', exact: true }).getByLabel('Color in HEX format').fill('#3377aa')
  await page.getByRole('dialog', { name: 'Choose a color', exact: true }).getByRole('button', { name: 'OK', exact: true }).click()
  await editor.getByRole('button', { name: 'Reset color', exact: true }).click()
  assert.equal(await editor.getByLabel('Choose color for Color', { exact: true }).getAttribute('title'), '')
  let uploads = 0
  await page.route('**/tactic/sthpw/UploadServer/', async route => {
    uploads++
    if (uploads === 1) await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'File upload failed.' }) })
    else await route.continue()
  })
  await editor.getByRole('button', { name: 'Next', exact: true }).click()
  await editor.getByRole('button', { name: 'Next', exact: true }).click()
  await editor.locator('.search-type-review img').waitFor()
  await administration.getByRole('button', { name: 'Save', exact: true }).click()
  await editor.getByRole('heading', { name: 'one/browser_preview', exact: true }).waitFor()
  await ready()
  assert.equal(await administration.getByRole('button', { name: 'Save', exact: true }).isDisabled(), true)
  await editor.getByRole('button', { name: 'Open Commit Queue', exact: true }).click()
  const queue = page.getByRole('dialog', { name: 'Commit Queue', exact: true })
  await queue.getByRole('button', { name:'Commit all', exact:true }).click()
  await queue.getByRole('status').getByText('Failed', { exact: true }).waitFor()
  await queue.getByRole('button', { name: 'Close', exact: true }).click()
  await administration.getByRole('button', { name: 'Close administration', exact: true }).click()
  await page.setViewportSize({ width: 320, height: 740 })
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Commit Queue', exact: true }).click()
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  await queue.getByLabel('Check-in actions', { exact: true }).click()
  await queue.locator('.queue-row').getByRole('button', { name: 'Retry', exact: true }).click()
  await queue.getByRole('status').getByText('Complete', { exact: true }).waitFor()
  assert.equal(uploads, 2)
  if (process.argv[3]) await page.screenshot({ path: process.argv[3], animations: 'disabled' })
  await queue.getByRole('button', { name: 'Close', exact: true }).click()
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByLabel('More options', { exact: true }).click()
  await page.waitForFunction(() => [...document.querySelectorAll('.settings-menu button')].some(button => button.textContent.includes('Administration') && !button.disabled))
  await page.locator('.settings-menu').getByRole('button', { name: 'Administration', exact: true }).click()
  await administration.waitFor()
  await ready()
  await editor.getByRole('button', { name: 'Browser preview', exact: true }).click()
  await ready()
  await editor.getByRole('tab', { name: 'Details', exact: true }).click()
  try { await page.waitForFunction(() => {
    const image = document.querySelector('.image-picker-preview img')
    return image?.getAttribute('src')?.startsWith('/') && image.complete && image.naturalWidth > 0
  }, null, { timeout: 12000 }) }
  catch (error) { console.log('Preview responses:', JSON.stringify(previews), 'Images:', JSON.stringify(images), await picker.innerHTML()); throw error }
  assert.equal(await editor.getByRole('alert').count(), 0)
  await page.setViewportSize({ width: 320, height: 740 })
  assert.equal(await administration.evaluate(node => node.scrollWidth <= node.clientWidth), true)
  assert.ok(await editor.getByLabel('Choose color for Color', { exact: true }).evaluate(node => node.getBoundingClientRect().width >= 100))
  await picker.scrollIntoViewIfNeeded()
  if (process.argv[3]) await page.screenshot({ path: process.argv[3].replace('-mobile.png', '-details-mobile.png'), animations: 'disabled' })
  assert.deepEqual(errors, [])
  console.log('Search Type preview: validate, undo, save, queue survives editor close, retry, repository image and 320px passed')
} finally { await browser.close() }
