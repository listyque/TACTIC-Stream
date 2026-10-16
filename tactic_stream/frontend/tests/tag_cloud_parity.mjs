import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'
import { packTagRows, tagRowAt } from '../../src/tactic_stream/shared_ui/controls/lists/chips.mjs'

const root = fileURLToPath(new URL('..', import.meta.url))
const output = fileURLToPath(new URL('../../.screenshots/tag-cloud-current/', import.meta.url))
const records = Object.entries({ cg: 6, demo: 5, arm: 3, body: 3, robot: 2, tool: 1, workshop: 1 })
  .map(([tag, count]) => ({ tag, count, weight: Math.log1p(count) / Math.log1p(6), column: 'keywords' }))
const many = Array.from({ length: 1500 }, (_, n) => ({ tag: 'token' + n.toString().padStart(4, '0'), weight: n / 1500 }))
many[30].tag = 'very-long-production-tag-name-'.repeat(5)
const packed = packTagRows(many, 280, text => text.length * 10, 'ALL')
assert.equal(packed.flatMap(row => row.cells).length, 1501)
assert(packed.every((row, i) => row.width <= 280 && tagRowAt(packed, row.top) === i))
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import { createApp, h } from 'vue'
import TagCloud from '/src/features/workspace/TagCloud.vue'
import { appearance, initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance, { mode: 'dark', popupAnimations: true }); initializeAppearance(); window.appearance = appearance
createApp({
 data: () => ({ selected: [], project: 'demo', type: 'demo/asset', tab: 'one' }),
 mounted() { window.host = this },
 render() { return h('main', { class: 'workspace-browser', style: 'height:100dvh;padding:24px;position:relative' }, [
  h('header', { class: 'search-header', style: 'display:flex;justify-content:flex-end' }, [
   h(TagCloud, { ref: 'cloud', ticket: 'fixture', project: this.project, searchType: this.type, tabId: this.tab, selected: this.selected,
    onApply: value => { this.selected = value.tags; window.lastApply = value } })
  ])
 ]) }
}).mount('#app')
</script></body></html>`
let server, browser, catalog = records, failure = false, hold = false, held, resolveHeld
const calls = [], errors = []
try {
 await mkdir(output, { recursive: true })
 server = await createServer({ root, configFile: false, cacheDir: root + '/node_modules/.vite/tag-cloud-parity',
  plugins: [vue(), { name: 'tag-cloud-fixture', configureServer(server) {
   server.middlewares.use(async (req, res, next) => {
    if (req.url !== '/tag-test') return next()
    try { res.setHeader('Content-Type', 'text/html'); res.end(await server.transformIndexHtml(req.url, html)) }
    catch (error) { next(error) }
   })
  } }], server: { host: '127.0.0.1', port: 0, watch: null } })
 await server.listen()
 browser = await chromium.launch({ headless: true })
 const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, hasTouch: true })
 page.setDefaultTimeout(10000); page.on('pageerror', error => errors.push(error.message))
 await page.route('**/admin/search-configuration/tags', async route => {
  const payload = route.request().postDataJSON(); calls.push(payload)
  if (hold) { held = route; resolveHeld(); return }
  if (failure) return route.fulfill({ status: 500, json: { error: 'Catalog unavailable' } })
  return route.fulfill({ json: { result: { column: payload.search_type === 'no/tags' ? '' : 'keywords', records: payload.search_type === 'no/tags' ? [] : catalog } } })
 })
 await page.goto(server.resolvedUrls.local[0] + 'tag-test'); await page.waitForFunction(() => window.host)
 const cloud = page.locator('.tag-cloud'), panel = cloud.locator('.account-panel'), viewport = cloud.locator('.tag-cloud-viewport')
 const search = cloud.getByRole('searchbox', { name: 'Search tags' }), chip = tag => cloud.getByRole('button', { name: tag, exact: true })
 const ready = () => page.waitForFunction(() => window.host.$refs.cloud.loaded && !window.host.$refs.cloud.busy && document.querySelector('.tag-cloud > summary')?.getAttribute('aria-expanded') === 'true')
 const open = async () => { await page.evaluate(() => window.host.$refs.cloud.open()); await ready(); await cloud.getByRole('searchbox').waitFor() }
 const close = () => search.press('Escape')
 await open()
 await search.focus()
 assert.equal(await search.evaluate(el => getComputedStyle(el).outlineStyle), 'none', 'Shared TextField has one focus border')
 const height = (await panel.boundingBox()).height
 assert.equal(height, 288, 'Handler surface is eight control heights')
 const geometry = await cloud.locator('[data-tag-index]').evaluateAll(nodes => nodes.map(el => {
  const style = getComputedStyle(el)
  return { text: el.textContent.trim(), font: parseFloat(style.fontSize), weight: style.fontWeight,
   border: style.borderTopWidth, radius: parseFloat(style.borderRadius), height: el.getBoundingClientRect().height, top: el.getBoundingClientRect().top }
 }))
 assert(geometry.every(chip => chip.border === '1px' && chip.weight === '600' && chip.radius >= chip.height / 2), 'Menu rows cannot override chip borders, font or shape')
 assert(await cloud.locator('.tag-label').evaluateAll(nodes => nodes.every(el => el.scrollWidth <= el.clientWidth)), 'Measured short names fit including both CSS borders')
 assert(geometry.find(chip => chip.text === 'cg').font > geometry.find(chip => chip.text === 'ALL').font)
 assert.equal(geometry.find(chip => chip.text === 'demo').height, 43, 'Weighted heights use Handler rounding')
 assert.equal(geometry.find(chip => chip.text === 'ALL').top, geometry.find(chip => chip.text === 'cg').top, 'Mixed chip sizes align at the top as in Handler')
 assert(await chip('ALL').evaluate(el => {
  const sample = document.createElement('span'); sample.style.color = 'var(--on-selected)'; el.append(sample)
  const expected = getComputedStyle(sample).color; sample.remove()
  return getComputedStyle(el).color === expected
 }), 'Selected text uses Handler selectedText rather than text on the bare accent')
 await panel.screenshot({ path: output + '/ts-tags.png', animations: 'disabled' })
 await chip('cg').click(); await chip('body').click()
 assert.deepEqual(await page.evaluate(() => window.lastApply), { tags: ['cg', 'body'], column: 'keywords' })
 assert.equal(await chip('cg').getAttribute('aria-pressed'), 'true')
 await search.fill('WORK'); assert.equal(await cloud.locator('[data-tag-index]').count(), 2)
 assert.equal(calls.length, 1, 'Local search and selection do not read catalog')
 await search.fill('missing'); await cloud.getByText('No matching tags', { exact: true }).waitFor()
 assert.equal((await panel.boundingBox()).height, height)
 await cloud.getByRole('button', { name: 'Clear search', exact: true }).click()
 await close(); await open()
 assert.equal(await search.inputValue(), ''); assert.equal(calls.length, 1, 'Cached catalog opens without another request')
 assert(await search.evaluate(el => document.activeElement === el))
 await cloud.getByRole('button', { name: 'Clear tags', exact: true }).click()
 assert.equal(await chip('ALL').getAttribute('aria-pressed'), 'true')
 failure = true; await cloud.getByRole('button', { name: 'Reload tags', exact: true }).click()
 await cloud.getByText('Catalog unavailable', { exact: true }).waitFor()
 assert(await chip('cg').isVisible(), 'Reload failure retains usable catalog')
 failure = false; catalog = many
 await cloud.getByRole('button', { name: 'Reload tags', exact: true }).click(); await ready()
 assert(await cloud.locator('[data-tag-index]').count() < 100)
 await search.fill('very-long-production')
 assert.equal((await chip(many[30].tag).boundingBox()).width, 260)
 assert.equal(await chip(many[30].tag).locator('.tag-label').evaluate(el => getComputedStyle(el).textOverflow), 'ellipsis')
 await search.fill('')
 await viewport.evaluate(el => el.scrollTop = el.scrollHeight)
 await chip('token1499').waitFor()
 assert(await viewport.evaluate(el => el.scrollWidth <= el.clientWidth), 'Chips fit the reserved scrollbar gutter')
 await viewport.evaluate(el => el.scrollTop = 0); await search.press('ArrowDown')
 for (let i = 0; i < 75; i++) await page.keyboard.press('Tab')
 assert(await viewport.evaluate(el => el.scrollTop > 0), 'Keyboard reaches offscreen chips')
 const active = Number(await page.evaluate(() => document.activeElement.dataset.tagIndex))
 await page.keyboard.press('Shift+Tab')
 assert.equal(Number(await page.evaluate(() => document.activeElement.dataset.tagIndex)), active - 1, 'Shift+Tab follows the filtered tag order backwards')
 const started = new Promise(resolve => { resolveHeld = resolve })
 hold = true; await cloud.getByRole('button', { name: 'Reload tags', exact: true }).click()
 await page.waitForFunction(() => window.host.$refs.cloud.busy)
 let timeout
 await Promise.race([started, new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error('Reload did not request the catalog')), 10000) })]).finally(() => clearTimeout(timeout))
 await page.evaluate(() => window.host.type = 'no/tags')
 await held.fulfill({ json: { result: { column: 'keywords', records } } }); hold = false
 await open(); await cloud.getByText('This search type has no tag column.', { exact: true }).waitFor()
 assert.equal(await cloud.locator('[data-tag-index]').count(), 0, 'Late response cannot populate a different type')
 await close(); catalog = records
 await page.evaluate(() => { window.host.type = 'demo/asset'; window.appearance.language = 'ru' })
 await open(); await cloud.getByRole('searchbox', { name: 'Поиск тегов' }).waitFor()
 await panel.screenshot({ path: output + '/ts-tags-ru.png', animations: 'disabled' })
 await page.evaluate(() => window.appearance.language = 'en')
 for (const theme of ['material5', 'fluent', 'md3']) {
  await page.evaluate(theme => window.appearance.theme = theme, theme)
  const expected = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--control-height')) * 8)
  assert.equal((await panel.boundingBox()).height, expected, 'Surface follows theme control height')
 }
 await close(); await page.setViewportSize({ width: 320, height: 480 }); catalog = many
 await page.evaluate(() => window.host.tab = 'phone')
 await open(); await ready()
 const box = await panel.boundingBox()
 assert(box.x >= 0 && box.x + box.width <= 320 && box.y + box.height <= 480, 'Mobile tag bounds: ' + JSON.stringify(box))
 await viewport.evaluate(el => el.scrollTop = el.scrollHeight); await chip('token1499').waitFor(); await chip('token1499').tap()
 assert.equal(await chip('token1499').getAttribute('aria-pressed'), 'true')
 await panel.screenshot({ path: output + '/ts-tags-mobile.png', animations: 'disabled' })
 assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
 assert.deepEqual(errors, [])
 console.log('Tag cloud: Handler chips/geometry, local search, cache/reload, stale requests, virtual scrolling, keyboard, themes, Russian and touch PASS')
} finally { await browser?.close(); await server?.close() }
