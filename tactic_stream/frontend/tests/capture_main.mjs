// Read the running application using the viewport of the live Handler capture.
import { chromium } from 'playwright'
import { readFile } from 'node:fs/promises'
import { selectProject } from './project_selection.mjs'

const output = process.env.HANDLER_REFERENCE ? '../.screenshots/handler-current/' : '../.screenshots/main-parity/'
const { width, height, deviceScaleFactor } = process.env.HANDLER_REFERENCE
  ? { width: 1440, height: 1000, deviceScaleFactor: 1 }
  : JSON.parse(await readFile(output + 'viewport.json', 'utf8'))
const browser = await chromium.launch({ headless: true })
try {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor, colorScheme: 'dark' })
  await context.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en', iconSet: 'material-design' })))
  const page = await context.newPage()
  await page.goto((process.argv[2] || 'http://192.168.2.55:8081') + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill('admin')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await ready()
  await selectProject(page, 'ui_test')
  await ready()
  await page.locator('.navigation-toggle').click()
  await page.locator('.type-list').getByRole('button', { name: /Collection/ }).first().click()
  await ready()
  const suffix = process.argv[3] || 'after'
  await page.screenshot({ path: output + `stream-main-${suffix}.png`, animations: 'disabled' })
  await page.locator('.settings-menu > summary').click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Task Manager', exact: true }).click()
  await page.locator('.task-manager-results[aria-busy="false"]').waitFor()
  await page.screenshot({ path: output + `stream-docks-${suffix}.png`, animations: 'disabled' })
  const tasks = page.locator('[data-dock="tasks"]')
  await tasks.getByLabel('Panel position: Task Manager', { exact: true }).click()
  await tasks.getByRole('button', { name: 'Float panel', exact: true }).click()
  await page.screenshot({ path: output + `stream-floating-${suffix}.png`, animations: 'disabled' })
  await page.locator('.settings-menu > summary').click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Reset workspace layout', exact: true }).click()
  await page.locator('.settings-menu > summary').click()
  await page.screenshot({ path: output + `stream-menu-${suffix}.png`, animations: 'disabled' })
  await page.keyboard.press('Escape')
  await page.locator('.navigation-toggle').click()
  await page.screenshot({ path: output + `stream-navigation-${suffix}.png`, animations: 'disabled' })
  await page.keyboard.press('Escape')
  await page.setViewportSize({ width: 360, height: 740 })
  await page.screenshot({ path: output + `stream-mobile-${suffix}.png`, animations: 'disabled' })
  console.log(`Live Stream captured (${width}x${height}, scale ${deviceScaleFactor}).`)
} finally { await browser.close() }
