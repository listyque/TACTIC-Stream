import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  if (process.argv[3]) await page.route('http://tactic-stream.test/**', async route => {
    const path = new URL(route.request().url()).pathname
    await route.fulfill({ response: await route.fetch({ url: process.argv[3] + path }) })
  })
  await page.goto(process.argv[2] || 'http://192.168.2.55:8081/', { timeout: 15000 })
  assert.equal(await page.evaluate(() => isSecureContext), false, 'Exercise the actual LAN HTTP browser context')
  assert.equal(await page.evaluate(() => typeof crypto.randomUUID), 'undefined')
  await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor()
  await page.getByLabel('Password', { exact: true }).waitFor()
  assert.deepEqual(errors, [])
  await page.screenshot({ path: '../.screenshots/handler-current/stream-lan-startup.png' })
  console.log('PASS: LAN HTTP starts without randomUUID or page errors')
} finally { await browser.close() }
