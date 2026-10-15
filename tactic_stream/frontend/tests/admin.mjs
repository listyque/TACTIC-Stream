import { selectProject } from './project_selection.mjs'
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'ru-RU', colorScheme: 'light' })
const page = await context.newPage()
page.setDefaultTimeout(12000)
const errors = []
page.on('pageerror', error => errors.push(error.message))
await page.addInitScript(() => {
  window.cspViolations = []
  document.addEventListener('securitypolicyviolation', event => window.cspViolations.push(event.violatedDirective))
})
const waitCell = text => page.getByRole('cell', { name: text, exact: true }).first().waitFor()
const checkSwitchGeometry = async control => {
  await control.evaluate(node => Promise.all((node.closest('.account-panel')?.getAnimations() || []).map(animation => animation.finished)))
  await page.waitForFunction(node => {
    const track = getComputedStyle(node), thumb = getComputedStyle(node, '::before')
    const shift = new DOMMatrix(thumb.transform)
    return Math.abs(shift.m41 - (node.checked ? parseFloat(track.getPropertyValue('--switch-travel')) : 0)) < .01
  }, await control.elementHandle())
  assert.deepEqual(await control.evaluate(node => {
    const track = getComputedStyle(node), thumb = getComputedStyle(node, '::before'), shift = new DOMMatrix(thumb.transform)
    const x = parseFloat(track.borderLeftWidth) + parseFloat(thumb.left) + shift.m41
    const y = parseFloat(track.borderTopWidth) + parseFloat(thumb.top) + shift.m42
    const { width, height } = node.getBoundingClientRect(), target = node.parentElement.getBoundingClientRect()
    return [width, height, x >= 3 - .01 && x + parseFloat(thumb.width) <= width - 3 + .01,
      Math.abs(y - (height - parseFloat(thumb.height)) / 2) < .01, target.width >= 36 && target.height >= 36]
  }), [42, 24, true, true, true])
}
const openFilters = async () => {
  if (!await page.locator('.search-filters').evaluate(node => node.open)) await page.getByLabel('Search filters', { exact: true }).click()
}
const openNavigation = async () => {
  if (!await page.locator('#workspace-sidebar').evaluate(node => node.open)) await page.locator('.navigation-toggle').click()
}


try {
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByRole('heading', { name: 'Sign in to administration' }).waitFor()
  assert.equal(await page.title(), 'TACTIC Stream')
  assert.equal(await page.locator('html').getAttribute('lang'), 'en')
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'md3')
  assert.equal(await page.locator('html').getAttribute('data-mode'), 'light')
  const typography = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement)
    return { family: style.fontFamily, size: parseFloat(style.fontSize) }
  })
  assert.match(typography.family, /^"Segoe UI"/)
  assert.ok(Math.abs(typography.size - 9.25 * 96 / 72) < .01)
  assert.match(await page.locator('.brand').textContent(), /TACTIC Stream/)
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill('wrong-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('alert').waitFor()
  assert.match(await page.getByRole('alert').textContent(), /Invalid credentials/)
  // A failed login also re-translates live; appearance never stores credentials.
  await page.locator('.appearance-controls summary').click()
  const colorMode = page.getByLabel('Color mode', { exact: true })
  assert.equal(await colorMode.evaluate(element => getComputedStyle(element).appearance), 'base-select')
  await colorMode.click()
  await page.getByRole('option', { name: 'Dark', exact: true }).click()
  assert.equal(await colorMode.inputValue(), 'dark')
  await colorMode.press('Space')
  await page.getByRole('option', { name: 'System', exact: true }).waitFor({ state: 'visible' })
  if (process.argv[3]) await page.screenshot({ path: process.argv[3].replace('.png', '-select.png'), fullPage: true })
  await page.keyboard.press('Home')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  assert.equal(await colorMode.inputValue(), 'light')
  assert(await colorMode.evaluate(element => document.activeElement === element))
  await colorMode.press('Space')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Escape')
  assert.equal(await colorMode.inputValue(), 'light')
  assert.equal(await colorMode.evaluate(element => element.matches(':open')), false)
  await colorMode.press('Space')
  await page.mouse.click(100, 100)
  assert.equal(await colorMode.evaluate(element => element.matches(':open')), false)
  await page.getByLabel('Interface language', { exact: true }).selectOption('ru')
  await page.getByRole('heading', { name: 'Вход в админку' }).waitFor()
  assert.match(await page.getByRole('alert').textContent(), /Неверный/)
  assert.equal(await page.locator('html').getAttribute('lang'), 'ru')
  assert.equal(await page.title(), 'TACTIC Stream')
  await page.getByLabel('Цветовой режим', { exact: true }).selectOption('dark')
  await page.getByLabel('Стиль интерфейса', { exact: true }).selectOption('material5')
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'material5')
  assert.equal(await page.locator('html').getAttribute('data-mode'), 'dark')
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--field-radius').trim()), '15px')
  await page.reload()
  await page.getByRole('heading', { name: 'Вход в админку' }).waitFor()
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'material5')
  assert.equal(await page.locator('html').getAttribute('data-mode'), 'dark')
  assert.equal(await page.getByLabel('Пароль', { exact: true }).inputValue(), '')
  assert.deepEqual(await page.evaluate(() => Object.fromEntries(Object.entries(JSON.parse(localStorage.getItem('tactic_stream.appearance'))).filter(([key]) => ['language', 'theme', 'mode'].includes(key)))), { language: 'ru', theme: 'material5', mode: 'dark' })
  await page.locator('.appearance-controls summary').click()
  await page.getByLabel('Язык интерфейса', { exact: true }).selectOption('en')
  await page.getByRole('heading', { name: 'Sign in to administration' }).waitFor()
  await page.locator('.appearance-controls summary').click()
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill('private-test-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByLabel('Project', { exact: true }).waitFor()
  await page.getByLabel('Change search results view', { exact:true }).click()
  await page.getByRole('menuitemradio', { name:'Table', exact:true }).click()
  await page.getByRole('cell', { name: 'Administration', exact: true }).waitFor()
  assert.equal(await page.locator('input[type=password]').count(), 0)
  assert(!await page.evaluate(() => localStorage.getItem('tactic_stream.session')).then(value => value.includes('private-test-password')))
  assert.ok(await page.locator('.topbar .app-icon').count() >= 8)
  assert.equal(await page.locator('.project-picker .image-picker-preview span').textContent(), 'A')
  await openFilters()
  const retiredSwitch = page.getByRole('switch', { name: 'Show retired', exact: true })
  await openFilters()
  await checkSwitchGeometry(retiredSwitch)
  await retiredSwitch.check()
  await page.waitForFunction(() => document.querySelector('.table-container').getAttribute('aria-busy') === 'false')
  await checkSwitchGeometry(retiredSwitch)
  await retiredSwitch.uncheck()
  await page.waitForFunction(() => document.querySelector('.table-container').getAttribute('aria-busy') === 'false')
  // Screen-specific behavior is covered by administration, table_cells and mobile_complete.
  await selectProject(page, 'one')
  await openNavigation()
  await page.locator('.type-list button[data-search-type="contract/entity"]').click()
  await page.getByLabel('Change search results view', { exact:true }).click()
  await page.getByRole('menuitemradio', { name:'Table', exact:true }).click()
  await waitCell('Первый')
  const savedSession = await page.evaluate(() => JSON.parse(localStorage.getItem('tactic_stream.session')))
  assert.equal(savedSession.project, 'one')
  assert.equal(savedSession.login, 'admin')
  assert(!JSON.stringify(savedSession).includes('private-test-password'))
  await page.reload()
  await waitCell('Первый')
  assert.equal(await page.locator('.login-card').count(), 0)
  assert.equal(new URL(page.url()).pathname, '/projects/one/')
  assert.equal(new URL(page.url()).searchParams.has('tab'), false)
  const freshTab = await context.newPage()
  try {
    await freshTab.goto(page.url())
    await freshTab.getByLabel('Project', { exact:true }).waitFor()
    assert.equal(await freshTab.locator('.login-card').count(), 0)
  } finally { await freshTab.close() }
  if (process.argv[3]) await page.screenshot({ path: process.argv[3], fullPage:true, animations:'disabled' })
  const revokedTicket = savedSession.ticket
  await page.locator('.account-menu summary').click()
  await page.getByRole('button', { name:'Sign out', exact:true }).click()
  await page.getByRole('heading', { name:'Sign in to administration' }).waitFor()
  assert.equal(await page.evaluate(() => localStorage.getItem('tactic_stream.session')), null)
  const revoked = await page.evaluate(async ticket => {
    const response = await fetch('/admin/rpc', { method:'POST', headers:{ 'Content-Type':'application/json' },
      body:JSON.stringify({ method:'ping', args:[{ ticket, project:'admin' }] }) })
    return response.status
  }, revokedTicket)
  assert.equal(revoked, 403)
  await page.evaluate(() => localStorage.setItem('tactic_stream.session', JSON.stringify({ login:'admin', ticket:'expired-ticket', project:'one' })))
  await page.reload()
  await page.getByRole('heading', { name:'Sign in to administration' }).waitFor()
  await page.getByRole('alert').waitFor()
  assert.match(await page.getByRole('alert').textContent(), /Session ended/)
  // Corrupt/unknown stored options fall back to English, MD3 and system mode.
  await page.evaluate(() => localStorage.setItem('tactic_stream.appearance', '{broken'))
  await page.reload()
  await page.getByRole('heading', { name: 'Sign in to administration' }).waitFor()
  assert.equal(await page.locator('html').getAttribute('lang'), 'en')
  await page.evaluate(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ language: 'unknown', theme: 'unknown', mode: 'unknown' })))
  await page.reload()
  await page.getByRole('heading', { name: 'Sign in to administration' }).waitFor()
  assert.deepEqual(await page.evaluate(() => Object.fromEntries(Object.entries(JSON.parse(localStorage.getItem('tactic_stream.appearance'))).filter(([key]) => ['language', 'theme', 'mode'].includes(key)))), { language: 'en', theme: 'md3', mode: 'system' })
  assert.deepEqual(errors, [])
  assert.deepEqual(await page.evaluate(() => window.cspViolations), [])
  console.log('Chromium: login/locales/themes/shared switches/session restore/project URL/new tab/logout/expiry/persistence/system-mode/fallback/CSP OK')
} catch (error) {
  if (process.argv[3]) await page.screenshot({ path: process.argv[3].replace('.png', '-failure.png'), fullPage: true })
  console.error((await page.locator('body').innerText().catch(() => 'Admin content unavailable')).slice(0, 2000))
  throw error
} finally { await browser.close() }
