import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { openViewActions } from './project_selection.mjs'

const browser = await chromium.launch({ headless:true })
async function clickIcon(control, touch = false) {
  await control.scrollIntoViewIfNeeded()
  await control.hover()
  const page = control.page(), glyph = control.locator(':scope > .app-icon > .icon-glyph')
  const box = await glyph.boundingBox(), x = box.x + box.width / 2, y = box.y + box.height / 2
  const hit = await control.evaluate((button, point) => {
    const target = document.elementFromPoint(point.x, point.y)
    return { owned:target === button, label:button.getAttribute('aria-label'), point, target:target?.outerHTML.slice(0, 350) }
  }, { x, y })
  assert.equal(hit.owned, true, 'The glyph is part of the button hit area: ' + JSON.stringify(hit))
  if (touch) await page.touchscreen.tap(x, y)
  else { await page.mouse.move(x, y); await page.mouse.click(x, y) }
}
async function checkIcons(locator) {
  await locator.page().evaluate(() => document.fonts.ready)
  const rows = await locator.evaluateAll(buttons => buttons.filter(button => button.getClientRects().length).map(button => {
    const icon = button.querySelector(':scope > .app-icon'), glyph = icon?.querySelector('.icon-glyph')
    if (!glyph) return null
    const b = button.getBoundingClientRect(), i = icon.getBoundingClientRect(), g = glyph.getBoundingClientRect()
    const style = getComputedStyle(glyph), ctx = document.createElement('canvas').getContext('2d')
    ctx.font = style.fontSize + ' ' + style.fontFamily
    const m = ctx.measureText(glyph.textContent)
    const baseline = g.y + (parseFloat(style.lineHeight) - m.fontBoundingBoxAscent - m.fontBoundingBoxDescent) / 2 + m.fontBoundingBoxAscent
    return { label:button.getAttribute('aria-label'), width:b.width, height:b.height,
      circle:button.classList.contains('icon-button'), round: !!button.closest('.topbar,.app-window-titlebar,.navigation-drawer-action,.round-button'), radius:getComputedStyle(button).borderRadius, iconSize:parseFloat(getComputedStyle(icon).fontSize),
      glyphSize:parseFloat(style.fontSize), pack:icon.className,
      boxX:i.x + i.width / 2 - b.x - b.width / 2, boxY:i.y + i.height / 2 - b.y - b.height / 2,
      glyphX:g.x + g.width / 2 - i.x - i.width / 2, glyphY:g.y + g.height / 2 - i.y - i.height / 2,
      inkX:g.x + (m.actualBoundingBoxRight - m.actualBoundingBoxLeft) / 2 - i.x - i.width / 2,
      inkY:baseline + (m.actualBoundingBoxDescent - m.actualBoundingBoxAscent) / 2 - i.y - i.height / 2 }
  }).filter(Boolean))
  assert(rows.length)
  for (const row of rows) {
    const message = JSON.stringify(row)
    if (row.circle) {
      assert(row.round ? parseFloat(row.radius) >= row.width / 2 || row.radius === '50%' : parseFloat(row.radius) <= 4, message)
      assert(Math.abs(row.width - row.height) < .1, message)
      assert(Math.abs(row.boxX) < .1, message)
      assert(row.iconSize / row.width <= .65, message)
    }
    assert(Math.abs(row.boxY) < .1, message)
    assert(Math.abs(row.glyphX) < .1 && Math.abs(row.glyphY) < .1, message)
    assert(Math.abs(row.inkX) <= 1 && Math.abs(row.inkY) <= 1, message)
  }
}
try {
  const page = await browser.newPage({ viewport:{ width:1280, height:900 }, hasTouch:true })
  page.setDefaultTimeout(10000)
  const errors = []; page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode:'dark', language:'en' })))
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact:true }).fill('private-test-password')
  await page.getByRole('button', { name:'Sign in', exact:true }).click()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await clickIcon(page.getByLabel('More options', { exact:true }))
  await clickIcon(page.locator('.settings-menu').getByRole('button', { name:'Configuration', exact:true }))
  const dialog = page.locator('dialog[aria-labelledby="configuration-title"]')
  await dialog.locator('.configuration-header .app-window-controls').waitFor()
  const reset = dialog.locator('.configuration-header').getByRole('button', { name:'Reset', exact:true })
  assert.equal(await reset.isDisabled(), true)
  await reset.evaluate(button => { button.dataset.clicks = '0'; button.addEventListener('click', () => button.dataset.clicks = String(Number(button.dataset.clicks) + 1)) })
  await clickIcon(reset)
  assert.equal(await reset.getAttribute('data-clicks'), '0', 'Clicking the glyph does not bypass native disabled')
  const windowButton = dialog.locator('.configuration-header .app-window-controls').getByRole('button', { name:/^(Maximize|Restore) window$/ })
  await windowButton.locator('.app-icon').hover()
  await page.getByRole('tooltip').waitFor()
  await clickIcon(windowButton)
  await page.getByRole('tooltip').waitFor({ state:'hidden' })
  await clickIcon(windowButton)
  await dialog.getByRole('button', { name:'Appearance', exact:true }).click()
  for (const pack of ['material-design', 'fontawesome-solid', 'fontawesome-outline', 'fluent-regular', 'fluent-filled']) {
    await dialog.getByLabel('Icon set', { exact:true }).selectOption(pack)
    for (const theme of ['md3', 'material5', 'fluent']) {
      await dialog.getByLabel('Interface style', { exact:true }).selectOption(theme)
      await checkIcons(dialog.locator('.configuration-header button:has(> .app-icon)'))
      await dialog.evaluate(dialog => {
        dialog.querySelector('#button-samples')?.remove()
        const samples = document.createElement('div'); samples.id = 'button-samples'; samples.style.cssText = 'display:flex; gap:8px; position:absolute; bottom:12px; right:12px; pointer-events:none'
        for (const selector of ['.app-window-controls button', '.configuration-actions button[aria-label="Close"]']) samples.append(dialog.querySelector(selector).cloneNode(true))
        dialog.append(samples)
      })
      await checkIcons(dialog.locator('#button-samples button'))
    }
    await dialog.locator('#button-samples').evaluate(element => element.remove())
    const before = await dialog.boundingBox()
    await clickIcon(windowButton)
    assert.notEqual((await dialog.boundingBox()).width, before.width, pack + ': clicking the glyph toggles the window')
    await clickIcon(windowButton)
    assert.equal((await dialog.boundingBox()).width, before.width, pack + ': clicking the glyph restores geometry')
    await windowButton.focus()
    await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Tab')
    await dialog.locator('.configuration-actions').screenshot({ path:'../.screenshots/button-geometry-' + pack + '.png', animations:'disabled' })
  }
  await clickIcon(dialog.getByRole('button', { name:'Close', exact:true }))
  await page.getByRole('dialog',{ name:'Unsaved changes',exact:true }).getByRole('button',{ name:'Discard changes',exact:true }).click()
  await page.goto(process.argv[2] + '/projects/one/?search_type=contract/entity&view=table')
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  await openViewActions(page)
  await page.locator('details:has(> summary[aria-label="View actions"]) > .account-panel').getByRole('button', { name:'Create record', exact:true }).click()
  const form = page.getByRole('dialog', { name:'Record form', exact:true })
  await form.getByRole('heading', { name:'Create record', exact:true }).waitFor()
  const controls = form.locator('header button')
  const searchIcon = page.locator('.search-header > .workspace-search > .app-icon')
  assert.equal(await searchIcon.evaluate(icon => getComputedStyle(icon).pointerEvents), 'auto', 'The standalone search icon keeps its own click action')
  await checkIcons(controls)
  await clickIcon(form.getByRole('button', { name:'Maximize window', exact:true }))
  assert.equal((await form.boundingBox()).width, 1280, 'Click directly on the icon maximizes the window')
  await checkIcons(controls)
  await clickIcon(form.getByRole('button', { name:'Restore window', exact:true }), true)
  assert((await form.boundingBox()).width < 1280, 'Tap directly on the icon restores the window')
  await form.getByRole('button', { name:'Maximize window', exact:true }).focus()
  await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Tab')
  const header = await form.locator('header').boundingBox()
  await page.screenshot({ path:'../.screenshots/button-geometry-record-header.png', animations:'disabled', clip:{ x:header.x - 6, y:header.y - 6, width:header.width + 12, height:header.height + 12 } })
  // The same real control in the compact contexts that previously squeezed its circle.
  await form.evaluate(dialog => {
    const fixture = document.createElement('div'); fixture.id = 'button-geometry'; fixture.style.cssText = 'display:flex; align-items:center; gap:4px; width:100%; height:48px'
    const source = dialog.querySelector('.app-window-controls button')
    for (const name of ['task-surface-switcher', 'task-manager-pending', 'task-process-toolbar', 'dock-presets-heading', 'dock-preset-row', 'search-suggestion-row', 'workspace-search']) {
      const host = document.createElement('div'); host.className = name; host.style.flexShrink = 0
      host.append(source.cloneNode(true)); fixture.append(host)
    }
    dialog.append(fixture)
  })
  await checkIcons(form.locator('#button-geometry button'))
  await page.setViewportSize({ width:320, height:760 })
  await checkIcons(form.locator('#button-geometry button'))
  await form.locator('#button-geometry').evaluate(element => element.remove())
  await clickIcon(form.getByRole('button', { name:'Close', exact:true }), true)
  await form.waitFor({ state:'hidden' })
  await page.setViewportSize({ width:1280, height:900 })
  await searchIcon.click()
  assert.equal(await page.locator('.search-header input[role="combobox"]').evaluate(input => document.activeElement === input), true, 'Clicking the standalone search icon still focuses the field')
  assert.deepEqual(errors, [])
  console.log('PASS icon centering/hit area: five packs, three themes, tooltip hover, direct glyph clicks/taps, window/menu/close and compact circles')
} finally { await browser.close() }
