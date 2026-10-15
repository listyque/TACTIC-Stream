import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'
import { extractSkeys, withoutSkeys, linkifyPlainText } from '../src/controls/richText.js'
const base = process.argv[2], project = process.env.STREAM_CHECK_PROJECT
async function request(path, values) {
  const response = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) })
  const data = await response.json(); assert(response.ok, JSON.stringify(data)); return data.result
}
const ticket = await request('/admin/rpc', { method: 'get_ticket', args: ['admin', process.env.STREAM_CHECK_PASSWORD] })
const auth = { ticket, project }, rpc = (method, args = [], kwargs = {}) => request('/admin/rpc', { method, args: [auth, ...args], kwargs })
const chat = (action, values = {}) => request('/admin/messages/' + action, { ...auth, ...values })
await rpc('execute_python_script', ['', { code: `
from pyasm.search import Search, SearchType
from pyasm.security.authenticator import hash_password
user=SearchType.create('sthpw/login')
user.set_value('code','artist'); user.set_value('login','artist')
user.set_value('password',hash_password('skey-password')); user.commit(); user.add_to_group('admin')
return True
` }])
await chat('initialize')
const direct = (await chat('create', { recipients: ['artist'] })).conversationId
const artist = { ticket: await request('/admin/rpc', { method: 'get_ticket', args: ['artist', 'skey-password'] }), project }
const other = (await chat('create')).conversationId
const linkedMessage = (await chat('send', { message_code: other, message: 'Source conversation message' })).message
const object = (await rpc('query', ['cg/assets'], { limit: 5 }))[0]
const key = 'skey://' + object.__search_key__
const missing = `skey://cg/assets?project=${project}&code=NOT_CREATED_YET`
const note = await rpc('insert', ['sthpw/note', { note: 'Nested object reference\n' + key + '\n' + missing, login: 'admin', access: 'public', process: 'publish', project_code: project, search_type: 'cg/assets?project=' + project, search_code: object.code }])
const task = (await rpc('query', ['sthpw/task'], { filters: [['project_code', project]], limit: 1 }))[0]
assert(task, 'The native CG sample contains tasks')
async function metadataSnapshot(kind, template, metadata, context) {
  return (await rpc('execute_python_script', ['', { code: `
from pathlib import Path
from pyasm.common import Environment
from pyasm.search import Search
path=Path(Environment.get_upload_dir()) / 'robot_arm.0001.ma'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text('// Maya fixture', encoding='utf-8')
snapshot=server.simple_checkin(${JSON.stringify(object.__search_key__)}, ${JSON.stringify(context)}, path.name, description='Lighting pass', mode='uploaded', keep_file_name=True, create_icon=False)
files=Search('sthpw/file'); files.add_filter('snapshot_code',snapshot['code'])
file=files.get_sobject()
file.set_json_value('metadata', ${JSON.stringify({ type: kind, template, new_template: template, new_filename: 'robot_arm', new_file_ext: 'ma', new_padding: 4, ...metadata })}); file.commit()
record=Search.get_by_code('sthpw/snapshot',snapshot['code']); record.set_value('repo','base'); record.set_value('revision',2); record.commit()
result=record.get_data(); result['__search_key__']=record.get_search_key()
return result
` }])).info
}
const snapshot = await metadataSnapshot('layer_sequence', '$FILENAME.$LAYER.$FRAME.$EXT', { layer: 'beauty', frameranges: ['1-3', '5'], app_info: { p: '2026' } }, 'skey_metadata')
const tiled = await metadataSnapshot('udim', '$FILENAME.$UDIM.$EXT', { udims: ['1001', '1002'] }, 'skey_tiles')
const combined = await metadataSnapshot('layer_uv_sequence', '$FILENAME.$LAYER.$UV.$FRAME.$EXT', { layer: 'diffuse', frameranges: [['u2_v2', ['1-3']], ['u2_v10', ['4', '6']]] }, 'skey_uv')
await rpc('create_search_type', ['cg/th_knowledge_article', 'Knowledge Base'])
await rpc('add_column_to_search_type', ['cg/th_knowledge_article', 'kind', 'varchar(256)'])
await rpc('add_column_to_search_type', ['cg/th_knowledge_article', 'content_text', 'text'])
const article = await rpc('insert', ['cg/th_knowledge_article', { name: 'Review guide', kind: 'article', description: 'Review the asset and leave a note', content_text: 'Production guide content' }])
const form = new FormData()
for (const [name, value] of Object.entries({ ...auth, message_code: direct, token: crypto.randomUUID(), purpose: 'attachment' })) form.append(name, value)
form.append('file', new Blob([readFileSync('../.screenshots/handler-current/messages-attachment.png')], { type: 'image/png' }), 'private-preview.png')
const upload = await fetch(base + '/admin/messages/upload', { method: 'POST', body: form })
assert(upload.ok)
const attachment = (await upload.json()).result
await chat('send', { message_code: direct, message: '', attachment_keys: [attachment.__search_key__] })
const privateKey = 'skey://' + attachment.__search_key__
const fileKey = 'skey://sthpw/file?code=' + attachment.__files__[0].code
const keys = [key, 'skey://' + task.__search_key__, 'skey://' + snapshot.__search_key__, 'skey://' + note.__search_key__, 'skey://' + linkedMessage.__search_key__, 'skey://sthpw/login?code=artist', 'skey://sthpw/project?code=' + project, 'skey://' + article.__search_key__, privateKey, fileKey, 'skey://' + tiled.__search_key__, 'skey://' + combined.__search_key__, missing]
const body = 'Review these references.\n' + keys.join('\n') + '\nhttps://example.org/?a=1&b=2\n<img src=x onerror="window.skeyInjected=true">'
assert.deepEqual(extractSkeys('(' + key + '). ' + key + '!'), [key])
assert.equal(withoutSkeys('See (' + key + ').'), 'See ().')
assert(!linkifyPlainText('<img src=x onerror=boom>').includes('<img'))
const message = (await request('/admin/messages/send', { ...artist, message_code: direct, message: body })).message
const descriptors = (await request('/admin/navigation-link', { ...auth, keys })).previews
assert.equal(descriptors.filter(row => row.status === 'ready').length, keys.length - 1, JSON.stringify(descriptors))
writeFileSync('../.screenshots/skey-preview-fixture.json', JSON.stringify({ messages: [message], previews: descriptors }, null, 2))
const browser = await chromium.launch({ headless: true })
let page
let releasePreviews
const previewGate = new Promise(resolve => releasePreviews = resolve)
try {
  page = await browser.newPage({ viewport: { width: 1120, height: 1000 }, hasTouch: true, colorScheme: 'dark' })
  const errors = []; page.on('pageerror', error => errors.push(error.message)); page.setDefaultTimeout(12000)
  await page.addInitScript(() => { if (!localStorage.getItem('tactic_stream.appearance')) localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })) })
  let firstPreviews = true
  await page.route('http://tactic-stream.test/**', async route => {
    const url = new URL(route.request().url())
    const response = await route.fetch({ url: base + url.pathname + url.search, headers: { ...route.request().headers(), origin: base, referer: base + '/' } })
    if (firstPreviews && url.pathname === '/admin/navigation-link' && route.request().postDataJSON()?.keys) { firstPreviews = false; await previewGate }
    await route.fulfill({ response })
  })
  await page.goto('http://tactic-stream.test/')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  await selectProject(page, project)
  await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Messages', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Messages', exact: true })
  await dialog.getByRole('button', { name: 'artist', exact: true }).click()
  const cards = dialog.locator('.messages-viewport[data-current="true"] .message-skey-previews > .skey-preview-card')
  await cards.last().waitFor()
  await cards.first().locator('.busy-indicator.running').waitFor({ state: 'visible' })
  releasePreviews()
  await page.waitForFunction(() => [...document.querySelectorAll('.message-skey-previews > .skey-preview-card')].every(node => node.getAttribute('aria-busy') === 'false'))
  assert.equal(await cards.count(), keys.length)
  assert.equal(await cards.nth(0).evaluate(node => node.getBoundingClientRect().height), 72)
  assert.equal(await cards.nth(2).evaluate(node => node.getBoundingClientRect().height), 88)
  assert.equal(await cards.nth(2).locator('.middle-elide').getAttribute('title'), 'robot_arm.beauty.[####].ma')
  assert((await cards.nth(2).locator('.middle-elide').innerText()).endsWith('.ma'))
  assert.equal(await cards.nth(2).locator('.snapshot-summary-version small').last().innerText(), 'General')
  assert.equal(await cards.nth(2).locator('.snapshot-summary-version small').last().evaluate(node => getComputedStyle(node).color), 'rgb(128, 128, 128)')
  assert.equal(await cards.nth(2).locator('.middle-elide').evaluate(node => parseFloat(getComputedStyle(node).fontSize)), 13)
  assert.equal(await cards.nth(2).locator('.snapshot-summary-version small').last().evaluate(node => parseFloat(getComputedStyle(node).fontSize)), 12)
  assert.equal(await cards.nth(2).locator('.skey-open .app-icon').evaluate(node => parseFloat(getComputedStyle(node).fontSize)), 17)
  for (const [label, value] of [['Range', '[1-3, 5]'], ['Frames', '4'], ['Layer', 'beauty'], ['Maya', '2026']]) await cards.nth(2).getByTitle(label + ': ' + value, { exact: true }).waitFor()
  await cards.nth(10).getByTitle('Tiles: 2', { exact: true }).waitFor()
  await cards.nth(11).getByTitle('Range: [4, 6 (u2_v10)], [1-3 (u2_v2)]', { exact: true }).waitFor()
  assert.equal(await cards.nth(3).locator('.skey-preview-card.compact').count(), 2)
  const nativeGeometry = JSON.parse(readFileSync('../.screenshots/handler-current/skey-geometry.json', 'utf8'))
  // Compare the presenters at the same width; the host windows remain independent.
  await dialog.locator('.messages-viewport[data-current="true"] .message-bubble:has(.message-skey-previews)').evaluate((node, width) => node.style.width = (width + 26) + 'px', nativeGeometry.note.width)
  assert(!(await dialog.locator('.messages-viewport[data-current="true"] .message-bubble:has(.message-skey-previews) .message-body').innerText()).includes('skey://'))
  assert.equal(await page.evaluate(() => Boolean(window.skeyInjected)), false)
  assert.equal(await dialog.locator('.messages-viewport[data-current="true"] .message-bubble:has(.message-skey-previews) .message-body img').count(), 0)
  await cards.nth(0).screenshot({ path: '../.screenshots/skey-object-web.png' })
  await cards.nth(2).screenshot({ path: '../.screenshots/skey-snapshot-web.png' })
  await cards.nth(3).screenshot({ path: '../.screenshots/skey-note-web.png' })
  await cards.nth(4).screenshot({ path: '../.screenshots/skey-message-web.png' })
  await cards.nth(7).screenshot({ path: '../.screenshots/skey-knowledge-web.png' })
  const bubble = dialog.locator('.messages-viewport[data-current="true"] .message-bubble:has(.message-skey-previews)')
  await bubble.evaluate(node => { node.style.width = '666px'; node.style.maxWidth = 'none' })
  for (const [index, name] of [[2, 'snapshot'], [10, 'snapshot-tiles'], [11, 'snapshot-tiles-sequence']]) await cards.nth(index).screenshot({ path: `../.screenshots/skey-${name}-wide-web.png` })
  writeFileSync('../.screenshots/snapshot-web-typography.json', JSON.stringify(await cards.nth(2).locator('.snapshot-summary').evaluate(node => [...node.querySelectorAll('.middle-elide,small,.snapshot-summary-chips > span,.snapshot-summary-description > span')].map(part => { const style = getComputedStyle(part); return { text: part.textContent, family: style.fontFamily, pixelSize: style.fontSize, weight: style.fontWeight, color: style.color } })), null, 2))
  await bubble.evaluate((node, width) => { node.style.width = (width + 26) + 'px'; node.style.maxWidth = '' }, nativeGeometry.note.width)
  for (const [index, kind] of [[3, 'note'], [4, 'message'], [7, 'knowledge']])
    assert(Math.abs(await cards.nth(index).evaluate(node => node.getBoundingClientRect().height) - nativeGeometry[kind].height) <= 1, kind + ' native height')
  writeFileSync('../.screenshots/skey-web-geometry.json', JSON.stringify(await cards.evaluateAll(nodes => nodes.map(node => ({ kind: node.className, height: node.getBoundingClientRect().height, parts: [...node.querySelectorAll('.skey-author-heading,.skey-preview-body,.skey-message-text')].map(part => ({ class: part.className, height: part.getBoundingClientRect().height, lineHeight: getComputedStyle(part).lineHeight })) }))), null, 2))
  await page.waitForFunction(() => document.querySelectorAll('.message-skey-previews > .skey-preview-card.snapshot img').length === 1)
  assert((await cards.nth(8).locator('img').getAttribute('src')).startsWith('blob:'))
  await cards.nth(8).getByRole('button', { name: 'Open snapshot', exact: true }).click()
  const filePreview = page.getByRole('dialog', { name: 'File preview', exact: true })
  await filePreview.waitFor(); await filePreview.locator('img').waitFor()
  assert.equal(new URL(page.url()).searchParams.get('snapshot'), attachment.code)
  assert.equal(new URL(page.url()).searchParams.get('chat'), direct)
  await filePreview.getByRole('button', { name: 'Close preview', exact: true }).click()
  await cards.nth(0).click({ button: 'right' })
  await cards.nth(0).getByRole('button', { name: 'Copy sKey', exact: true }).click()
  await cards.last().getByLabel('Link actions', { exact: true }).click()
  await cards.last().getByRole('button', { name: 'Retry preview', exact: true }).click()
  await page.waitForFunction(() => document.querySelectorAll('.message-skey-previews > .skey-preview-card.failed').length === 1)
  const draft = dialog.getByRole('textbox', { name: 'Write a reply', exact: true })
  await draft.fill('Retained across link navigation')
  await cards.nth(4).getByLabel('Link actions', { exact: true }).click()
  await cards.nth(4).getByRole('button', { name: 'Open linked item', exact: true }).click()
  await dialog.locator('.messages-viewport[data-current="true"] .message-row').filter({ hasText: 'Source conversation message' }).waitFor()
  await dialog.getByRole('button', { name: 'artist', exact: true }).click()
  await cards.first().waitFor()
  assert.equal(await draft.inputValue(), 'Retained across link navigation')
  const nested = cards.nth(3).locator('.skey-preview-card.compact').first()
  await nested.click({ button: 'right' })
  assert.equal(await dialog.locator('.skey-actions[open]').count(), 1, 'Only the nested context menu opens')
  await page.keyboard.press('Escape')
  await nested.locator('strong').click()
  await dialog.waitFor({ state: 'hidden' })
  const details = page.getByRole('dialog', { name: 'Object details', exact: true })
  await details.waitFor()
  assert.equal(new URL(page.url()).searchParams.get('link'), key)
  await details.getByRole('button', { name: 'Close details', exact: true }).click()
  await page.getByLabel('Account', { exact: true }).click(); await page.getByRole('button', { name: 'Messages', exact: true }).click()
  await cards.first().waitFor()
  await rpc('update', [object.__search_key__, { name: 'Updated from another client' }])
  await dialog.getByRole('button', { name: 'Refresh conversations and messages', exact: true }).click()
  await cards.first().filter({ hasText: 'Updated from another client' }).waitFor()
  // The same protected resolver restores message sKeys from a browser address.
  const messageLink = 'skey://' + linkedMessage.__search_key__
  await page.goto('http://tactic-stream.test/projects/' + encodeURIComponent(project) + '/?' + new URLSearchParams({ link: messageLink }))
  await dialog.waitFor(); await dialog.locator('.messages-viewport[data-current="true"] .message-row').filter({ hasText: 'Source conversation message' }).waitFor()
  await dialog.getByRole('button', { name: 'artist', exact: true }).click()
  for (const width of [320, 360]) {
    await page.setViewportSize({ width, height: 800 })
    await page.waitForFunction(() => [...document.querySelectorAll('.message-skey-previews > .skey-preview-card')].every(node => node.getAttribute('aria-busy') === 'false'))
    await cards.first().scrollIntoViewIfNeeded()
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Page overflow at ' + width)
    assert(await cards.first().evaluate(node => node.scrollWidth <= node.clientWidth + 1), 'Card overflow at ' + width)
    await page.screenshot({ path: `../.screenshots/skey-${width}-web.png` })
    const box = await cards.first().boundingBox()
    await page.touchscreen.tap(box.x + box.width - 14, box.y + 14)
    await cards.first().getByRole('button', { name: 'Copy sKey', exact: true }).waitFor()
    await page.keyboard.press('Escape')
  }
  await page.evaluate(() => { const value = JSON.parse(localStorage.getItem('tactic_stream.appearance')); Object.assign(value, { language: 'ru', mode: 'light' }); localStorage.setItem('tactic_stream.appearance', JSON.stringify(value)) })
  await page.reload()
  const russian = page.locator('.messages-dialog')
  await russian.locator('.messages-back').click()
  await russian.getByRole('button', { name: 'artist', exact: true }).click()
  const translatedSnapshot = russian.locator('.message-skey-previews > .skey-preview-card').nth(2)
  await translatedSnapshot.getByTitle('Кадры: 4', { exact: true }).waitFor()
  await translatedSnapshot.getByTitle('Диапазон: [1-3, 5]', { exact: true }).waitFor()
  assert.equal(await page.locator('html').getAttribute('lang'), 'ru')
  assert.equal(await page.locator('html').getAttribute('data-mode'), 'light')
  await translatedSnapshot.getByRole('button', { name: 'Открыть снапшот', exact: true }).waitFor()
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.setViewportSize({ width: 1120, height: 1000 })
  await page.waitForFunction(() => document.querySelector('.messages-dialog')?.getAttribute('aria-busy') === 'false')
  await translatedSnapshot.scrollIntoViewIfNeeded()
  await page.screenshot({ path: '../.screenshots/skey-metadata-ru-light.png' })
  assert.deepEqual(errors, [])
  console.log('PASS sKey cards, nested notes, retry/context menu, safe text, object/message routes, retained drafts and 320/360 touch')
} catch (failure) {
  if (page && !page.isClosed()) await page.screenshot({ path: '../.screenshots/skey-failure.png' })
  throw failure
} finally { releasePreviews(); if (page && !page.isClosed()) await page.unrouteAll({ behavior: 'ignoreErrors' }); await browser.close() }
