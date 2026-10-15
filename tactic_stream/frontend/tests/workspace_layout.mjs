import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({ headless: true })
let cleanup = null
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  page.setDefaultTimeout(10000)
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode:'dark', language:'en' })))
  const errors = [], calls = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (request.url().endsWith('/admin/rpc')) calls.push(request.postDataJSON()) })
  const ready = () => page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false' || document.querySelector('.workspace-empty')?.getClientRects().length)
  const task = page.locator('[data-dock="tasks"]'), root = page.locator('.dock-menu'), presets = page.locator('.dock-presets-menu')
  async function cursorAt(control, expected) {
    await control.hover()
    const box = await control.boundingBox()
    assert.equal(await page.evaluate(({ x, y }) => getComputedStyle(document.elementFromPoint(x, y)).cursor,
      { x:box.x + box.width / 2, y:box.y + box.height / 2 }), expected)
  }
  async function openPresets() { await root.getByLabel('Workspace panels', { exact: true }).click(); await presets.getByLabel('Layout presets', { exact: true }).click() }
  async function reset() { await page.getByLabel('More options', { exact: true }).click(); await page.locator('.settings-menu').getByRole('button', { name: 'Reset workspace layout', exact: true }).click() }
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact: true }).fill('private-test-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await ready()
  for (const [view, cursor] of [['Versions on the right', 'ew-resize'], ['Versions at the bottom', 'ns-resize']]) {
    await page.getByLabel('Change search results view', { exact:true }).click()
    await page.getByRole('menuitemradio', { name:view, exact:true }).click()
    await cursorAt(page.locator('.result-presentation:visible').getByRole('separator',{name:'Resize versions panel',exact:true}), cursor)
  }
  await page.getByLabel('More options', { exact:true }).click()
  await page.locator('.settings-menu').getByRole('button', { name:'Script Editor', exact:true }).click()
  const script = page.locator('.script-editor-dialog')
  await cursorAt(script.getByRole('separator', { name:'Scripts panel width', exact:true }), 'ew-resize')
  await cursorAt(script.getByRole('separator', { name:'Output height', exact:true }), 'ns-resize')
  await script.getByLabel('Close script editor', { exact:true }).click()
  assert.equal(await page.locator('.search-header .dock-grip').count(), 0, 'Browser results have no drag grip')
  const triggerBox = await root.locator(':scope > summary').boundingBox(), searchBox = await page.locator('.search-header:visible').boundingBox()
  assert(triggerBox.x > searchBox.x + searchBox.width - 60, JSON.stringify(await root.evaluate(el => ({ parent:el.parentElement.id, rect:el.getBoundingClientRect().toJSON(), class:el.className, style:getComputedStyle(el).position }))))
  await root.getByLabel('Workspace panels', { exact:true }).click()
  await page.waitForFunction(el => Math.round(el.getBoundingClientRect().width) === 280, await root.locator(':scope > .account-panel').elementHandle())
  assert.equal(Math.round((await root.locator(':scope > .account-panel').boundingBox()).width), 280)
  const tools = root.locator('.dock-group-menu').filter({ has:page.locator('summary[aria-label="Tools"]') })
  await tools.locator(':scope > summary').hover()
  await tools.getByRole('menuitemradio', { name:'Commit Queue', exact:true }).waitFor()
  const parentBox = await root.locator(':scope > .account-panel').boundingBox(), childBox = await tools.locator(':scope > .account-panel').boundingBox()
  assert(childBox.x >= parentBox.x + parentBox.width - 2 || childBox.x + childBox.width <= parentBox.x + 2, 'Submenu opens alongside its row, flipping at the viewport edge')
  assert.equal(await tools.getByRole('menuitemradio', { name:'Commit Queue', exact:true }).getAttribute('aria-checked'), 'false')
  if (process.argv[3]) await page.screenshot({ path:process.argv[3].replace('-mobile.png', '-desktop-menu.png'), animations:'disabled' })
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
  await root.getByLabel('Workspace panels', { exact:true }).click()
  const tasksMenu = root.locator('.dock-group-menu').filter({ has:page.locator('summary[aria-label="Tasks and reports"]') })
  await tasksMenu.locator(':scope > summary').waitFor({ state:'visible' })
  await tasksMenu.locator(':scope > summary').focus(); await page.keyboard.press('ArrowRight')
  await tasksMenu.getByRole('menuitemradio', { name:'Task Manager', exact:true }).waitFor()
  await page.keyboard.press('Enter'); await task.waitFor({ state:'visible' })
  await root.locator(':scope > .account-panel').waitFor({ state:'hidden' })
  await task.getByLabel('Close panel: Task Manager', { exact:true }).click()
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Task Manager', exact: true }).click()
  await task.locator('.task-manager-results[aria-busy="false"]').waitFor()
  await task.getByLabel('Panel position: Task Manager', { exact: true }).click()
  await task.getByRole('button', { name: 'Dock right', exact: true }).click()
  const splitter = page.getByRole('separator', { name:'Resize workspace panels', exact:true })
  await cursorAt(splitter, 'ew-resize')
  await task.getByLabel('Panel position: Task Manager', { exact: true }).click()
  await task.getByRole('button', { name: 'Dock bottom', exact: true }).click()
  await cursorAt(splitter, 'ns-resize')
  await openPresets()
  await presets.getByRole('button', { name: 'Save current layout…', exact: true }).click()
  const save = page.getByRole('dialog', { name: 'Save workspace layout', exact: true })
  await save.getByLabel('Layout preset name', { exact: true }).fill('Browser split')
  await save.getByRole('button', { name: 'Save', exact: true }).click(); await save.waitFor({ state: 'hidden' })
  await reset(); assert.equal(await task.isVisible(), false)
  await openPresets(); await presets.getByRole('button', { name: 'Browser split', exact: true }).click()
  assert.equal(await task.isVisible(), true)
  assert.equal(await page.getByRole('separator', { name: 'Resize workspace panels', exact: true }).getAttribute('aria-orientation'), 'horizontal')
  await task.getByRole('button', { name: 'Close panel: Task Manager', exact: true }).click()
  await openPresets(); await presets.getByRole('button', { name: 'Replace with current layout', exact: true }).click()
  await page.waitForResponse(response => response.url().endsWith('/workspace-layout/save'))
  const ticket = calls.find(call => call.args?.[0]?.ticket).args[0].ticket
  const auth = { ticket, project: 'admin', language: 'python' }
  async function rpc(method, args) {
    const response = await page.request.post(process.argv[2] + '/admin/rpc', { data: { method, args: [auth, ...args] } })
    assert.equal(response.status(), 200); return (await response.json()).result
  }
  const original = await rpc('query', ['config/widget_config', [['search_type', 'SideBarWdg']]])
  cleanup = async () => {
    const current = await rpc('query', ['config/widget_config', [['search_type', 'SideBarWdg']]])
    for (const row of current) {
      const before = original.find(item => item.code === row.code)
      if (!before) await rpc('delete_sobject', [row.__search_key__])
      else if (before.category !== 'workspace_layout') await rpc('update', [row.__search_key__, { config: before.config }])
    }
    const savedPreset = original.find(row => row.title === 'Browser split' && row.category === 'workspace_layout')
    if (savedPreset) await rpc('delete_sobject', [savedPreset.__search_key__])
  }
  async function read(project='admin') {
    const response = await page.request.post(process.argv[2] + '/admin/workspace-layout/read', { data: { ticket, project } })
    assert.equal(response.status(), 200); return (await response.json()).result
  }
  const saved = await read(), preset = saved.presets.find(row => row.title === 'Browser split')
  assert.equal(preset.configuration.panels.find(panel => panel.panel_id === 'tasks').visible, false)
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Administration', exact: true }).click()
  const admin = page.locator('.administration-dialog'), editor = admin.locator('.sidebar-editor')
  await admin.getByRole('button', { name: 'Sidebar Editor', exact: true }).click()
  const editorReady = () => page.waitForFunction(() => document.querySelector('.sidebar-editor')?.getAttribute('aria-busy') === 'false')
  await editorReady(); await editor.getByRole('button', { name: 'Add link', exact: true }).click(); await editorReady()
  await editor.getByLabel('Title', { exact: true }).fill('Layout people')
  await editor.getByLabel('Search Type', { exact: true }).selectOption('sthpw/project'); await editorReady()
  await editor.getByLabel('Default item view', { exact: true }).selectOption('table'); await editorReady()
  await editor.getByLabel('Workspace layout', { exact: true }).selectOption(preset.view); await editorReady()
  await admin.getByRole('button', { name: 'Save to server', exact: true }).click(); await editorReady()
  await admin.getByRole('button', { name: 'Close administration', exact: true }).click()
  assert.equal((await read()).presets.find(row => row.view === preset.view).assignedCount, 1)
  await openPresets(); await presets.getByRole('button', { name: 'Refresh layout presets', exact: true }).click()
  await presets.getByRole('button', { name: 'Delete layout preset', exact: true }).waitFor()
  assert.equal(await presets.getByRole('button', { name: 'Delete layout preset', exact: true }).isDisabled(), true)
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
  // Change the live arrangement; a fresh sidebar section must restore the assigned document.
  await page.getByLabel('More options', { exact: true }).click()
  await page.locator('.settings-menu').getByRole('button', { name: 'Task Manager', exact: true }).click()
  await page.locator('.navigation-toggle').click()
  await page.locator('.type-list').getByRole('button', { name: 'Layout people', exact: true }).click(); await ready()
  assert.equal(await task.isVisible(), false, 'Sidebar assignment applies when a new section opens')
  await selectProject(page, 'one'); await ready()
  assert.equal((await read('one')).presets.some(row => row.title === 'Browser split'), false, 'Presets belong to their project')
  await selectProject(page, 'admin'); await ready()
  await page.setViewportSize({ width: 320, height: 740 })
  await root.waitFor({ state:'detached' })
  assert.equal(await root.count(), 0, 'Phone has no docking or layout preset menu')
  assert.equal(await page.locator('.workspace-rail').count(), 0, 'Phone has no fast sidebar')
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  if (process.argv[3]) await page.screenshot({ path: process.argv[3], animations: 'disabled' })
  await page.setViewportSize({ width:1280, height:900 })
  await root.waitFor()
  const restoredTrigger = await root.locator(':scope > summary').boundingBox(), restoredSearch = await page.locator('.search-header:visible').boundingBox()
  assert(restoredTrigger.x > restoredSearch.x + restoredSearch.width - 60, 'Desktop restores the menu at the right end of search')
  assert.deepEqual(errors, [])
  console.log('Workspace presets: native save/apply/replace, sidebar editor assignment/delete protection, project isolation and mobile menu OK')
} finally { try { if (cleanup) await cleanup() } finally { await browser.close() } }
