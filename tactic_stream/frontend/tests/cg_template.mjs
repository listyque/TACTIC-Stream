// Open the imported real project through the normal chooser and navigation.
import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.setDefaultTimeout(10000)
const errors = []
page.on('pageerror', error => errors.push(error.message))
try {
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.project-picker').waitFor()
  await selectProject(page, 'cg_test')
  await page.locator('.navigation-toggle').click()
  const sidebar = page.locator('.sidebar')
  await sidebar.getByText('My Assets', { exact: true }).waitFor()
  await page.screenshot({ path: '../.screenshots/cg-test-navigation.png', animations: 'disabled' })
  await sidebar.getByRole('button', { name: 'Assets Category', exact: true }).click()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  assert.equal(await page.getByLabel('Search objects', { exact: true }).getAttribute('placeholder'), 'Search Assets Category')
  assert.equal(await page.locator('.workspace-browser .error:visible').count(), 0)
  for (const category of ['Characters', 'Props', 'Environments', 'Materials']) {
    await page.locator('.workspace-results').getByText(category, { exact: true }).waitFor()
  }
  await page.screenshot({ path: '../.screenshots/cg-test-workspace.png', animations: 'disabled' })
  // Assets has an imported Script Shelf assignment. Its optional toolbar
  // must not disable the underlying Search Type or discard the assignment.
  await page.locator('.navigation-toggle').click()
  const assetLink = sidebar.locator('button[data-search-type="cg/assets"][aria-label="Assets"]')
  assert.equal(await assetLink.isEnabled(), true)
  await assetLink.click()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  assert.equal(await page.getByLabel('Search objects', { exact: true }).getAttribute('placeholder'), 'Search Assets')
  assert.equal(await page.locator('.workspace-browser .error:visible').count(), 0)
  assert.ok(await page.locator('.workspace-results tbody tr').count() > 0)
  await page.reload()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  assert.equal(await page.getByLabel('Search objects', { exact: true }).getAttribute('placeholder'), 'Search Assets')
  await page.screenshot({ path: '../.screenshots/cg-test-assets.png', animations: 'disabled' })
  console.log('CG Test: project chooser, Assets Category, Assets with Script Shelf assignment and reload opened')
  assert.deepEqual(errors, [])
} finally {
  await browser.close()
}
