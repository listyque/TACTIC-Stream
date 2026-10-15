import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chromium } from 'playwright'

const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
const native = JSON.parse(readFileSync('../.screenshots/handler-current/notification-quick-reply-geometry.json', 'utf8'))
async function request(path, payload) {
  const response = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  const data = await response.json(); assert(response.ok, JSON.stringify(data)); return data.result
}
const ticket = await request('/admin/rpc', { method: 'get_ticket', args: ['admin', process.env.STREAM_CHECK_PASSWORD] })
const auth = { ticket, project }, chat = (action, values = {}) => request('/admin/messages/' + action, { ...auth, ...values })
await request('/admin/rpc', { method: 'execute_python_script', args: [auth, '', { code: `
from pyasm.search import SearchType
from pyasm.security.authenticator import hash_password
user = SearchType.create('sthpw/login')
user.set_value('code', 'artist'); user.set_value('login', 'artist')
user.set_value('password', hash_password('quick-reply-password'))
user.commit(); user.add_to_group('admin')
return True
` }] })
await chat('initialize')
const artist = { ticket: await request('/admin/rpc', { method: 'get_ticket', args: ['artist', 'quick-reply-password'] }), project }
const direct = (await chat('create', { recipients: ['artist'], title: 'Artist review' })).conversationId
const browser = await chromium.launch({ headless: true })
let page
try {
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  const errors = []; page.on('pageerror', error => errors.push(error.message)); page.setDefaultTimeout(15000)
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })))
  await page.clock.install()
  await page.goto(base + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.locator('.topbar').waitFor()
  await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Messages', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Messages', exact: true })
  const idle = () => page.waitForFunction(() => document.querySelector('.messages-dialog')?.getAttribute('aria-busy') === 'false')
  await idle(); await dialog.getByRole('button', { name: 'Favorites', exact: true }).click(); await idle()
  const draft = dialog.getByRole('textbox', { name: 'Write a reply', exact: true })
  await draft.fill('Keep this conversation draft')
  const cards = page.locator('.notification-card[data-source="messages"]')
  async function incoming(text) {
    await request('/admin/messages/send', { ...artist, message_code: direct, message: text })
    await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
    await page.clock.runFor(5100)
    const card = cards.filter({ hasText: text }); await card.waitFor(); return card
  }
  let card = await incoming('Please review the lighting.')
  assert.equal((await card.boundingBox()).height, native.collapsedHeight)
  await card.getByRole('button', { name: 'Reply', exact: true }).click()
  const field = card.getByRole('textbox', { name: 'Write a reply', exact: true })
  await field.fill('Lighting approved')
  assert.equal((await card.boundingBox()).height, native.editingHeight)
  const origin = await card.boundingBox(), box = await field.boundingBox()
  assert.equal(box.x - origin.x, native.fields.notificationReplyField.x)
  assert.equal(box.y - origin.y, native.fields.notificationReplyField.y)
  assert.equal(box.width, native.fields.notificationReplyField.width)
  await page.locator('.notification-stack').screenshot({ path: '../.screenshots/quick-reply-web.png' })
  await page.clock.runFor(16000)
  assert.equal(await card.count(), 1, 'Reply editing pauses toast expiry')
  let sends = 0, fail = true
  await page.route('**/messages/send', async route => { sends++; if (fail) { fail = false; await route.fulfill({ status: 400, json: { error: 'Unable to send message', error_code: 'invalid_request' } }) } else await route.continue() })
  await field.press('Enter')
  await card.getByRole('alert').waitFor()
  assert.equal(await field.inputValue(), 'Lighting approved')
  assert.equal((await card.boundingBox()).height, native.errorHeight)
  await page.locator('.notification-stack').screenshot({ path: '../.screenshots/quick-reply-error.png' })
  await field.press('Enter'); await card.waitFor({ state: 'hidden' })
  assert.equal(sends, 2)
  await page.unroute('**/messages/send')
  assert.equal(await draft.inputValue(), 'Keep this conversation draft')
  assert((await dialog.locator('.messages-chat-title').innerText()).includes('Favorites'))
  assert.equal((await chat('history', { message_code: direct })).messages.filter(row => row.message === 'Lighting approved' && row.login === 'admin').length, 1)
  card = await incoming('Second question')
  await card.getByRole('button', { name: 'Reply', exact: true }).click()
  await card.getByRole('textbox', { name: 'Write a reply', exact: true }).fill('Cancelled draft')
  await card.getByRole('textbox', { name: 'Write a reply', exact: true }).press('Escape')
  assert.equal(await card.getByRole('textbox').count(), 0)
  await card.getByRole('button', { name: 'Reply', exact: true }).click()
  assert.equal(await card.getByRole('textbox').inputValue(), 'Cancelled draft')
  await page.setViewportSize({ width: 320, height: 740 })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  await page.locator('.notification-stack').screenshot({ path: '../.screenshots/quick-reply-mobile.png' })
  await card.getByRole('button', { name: 'Cancel reply', exact: true }).click()
  await page.clock.runFor(15001)
  assert.equal(await cards.count(), 0, 'Cancel restarts the native fifteen-second timer')
  await page.setViewportSize({ width: 1440, height: 1000 })
  card = await incoming('Late session question')
  await card.getByRole('button', { name: 'Reply', exact: true }).click()
  await card.getByRole('textbox').fill('Pending reply')
  let release, started, attempts = 0
  const gate = new Promise(resolve => { release = resolve }), begun = new Promise(resolve => { started = resolve })
  await page.route('**/messages/send', async route => { attempts++; started(); await gate; await route.fulfill({ status: 403, json: { error: 'Old session expired', error_code: 'authentication_failed' } }) })
  try {
    await card.getByRole('button', { name: 'Send', exact: true }).click(); await begun
    await card.locator('form').evaluate(node => node.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })))
    assert.equal(attempts, 1, 'Second submit while pending cannot dispatch another request')
    assert.equal(await card.getByRole('textbox').isDisabled(), true)
    assert.equal(await card.getByRole('button', { name: 'Cancel reply', exact: true }).isDisabled(), true)
    await dialog.getByRole('button', { name: 'Close Messages', exact: true }).click()
    await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Sign out', exact: true }).click()
    await page.getByLabel('Login', { exact: true }).fill('artist')
    await page.getByLabel('Password', { exact: true }).fill('quick-reply-password')
    await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await page.locator('.topbar').waitFor()
    const failed = page.waitForResponse(response => response.url().endsWith('/messages/send'))
    release(); await failed
    await page.clock.runFor(100)
    assert.equal(await cards.count(), 0)
    assert.equal(await page.getByRole('button', { name: 'Sign in', exact: true }).count(), 0, 'Late failure cannot log out a new account')
  } finally { release(); await page.unroute('**/messages/send') }
  await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  assert.equal(await cards.count(), 0)
  assert.deepEqual(errors, [])
  console.log('PASS: native quick-reply geometry, real send, untouched conversation/draft, failed send/retry, stopped/restarted timers, duplicate-submit guard, late failure after account switch, Escape, mobile320 and logout cleanup')
} catch (error) {
  if (page && !page.isClosed()) await page.screenshot({ path: '../.screenshots/quick-reply-failure.png' })
  throw error
} finally { if (page && !page.isClosed()) await page.unrouteAll({ behavior: 'ignoreErrors' }); await browser.close() }
