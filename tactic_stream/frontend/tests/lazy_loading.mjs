import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chromium } from 'playwright'
import sourceMap from 'source-map-js'

const manifest = JSON.parse(readFileSync(new URL('../../src/tactic_stream/web/.vite/manifest.json', import.meta.url), 'utf8'))
const chunk = source => '/ui/' + manifest['src/' + source].file
const browser = await chromium.launch({ headless:true })
try {
  const page = await browser.newPage({ viewport:{ width:1280, height:900 } })
  page.setDefaultTimeout(12000)
  const requests = [], errors = []
  page.on('request', request => { if (new URL(request.url()).pathname.endsWith('.js')) requests.push(new URL(request.url()).pathname) })
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode:'dark', language:'en' })))
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill('admin')
  await page.getByLabel('Password', { exact:true }).fill('private-test-password')
  await page.getByRole('button', { name:'Sign in', exact:true }).click()
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false')
  const deferred = ['features/configuration/Configuration.vue', 'features/administration/SearchTypes.vue',
    'features/administration/ColumnsEditor.vue', 'features/scripts/ScriptEditor.vue', 'controls/MarkdownText.vue',
    'features/documentation/ApiDocumentation.vue']
  for (const source of deferred) assert(!requests.includes(chunk(source)), source + ' must not load with the workspace')
  const startupRequests = [...new Set(requests)]
  const menuFile = Object.values(manifest).find(entry => entry.name === 'AppMenu').file
  const scriptResponse = await page.request.get(process.argv[2] + '/ui/' + menuFile)
  assert.equal(scriptResponse.status(), 200)
  const scriptContent = await scriptResponse.text()
  assert(scriptContent.includes('function selected(event)'), 'Built JavaScript retains readable function names')
  const mapName = /\/\/# sourceMappingURL=(\S+)/.exec(scriptContent)?.[1]
  assert(mapName, 'Built JavaScript advertises its source map to DevTools')
  const mapResponse = await page.request.get(new URL(mapName, scriptResponse.url()).href)
  assert.equal(mapResponse.status(), 200)
  assert.match(mapResponse.headers()['content-type'], /^application\/json/)
  const map = await mapResponse.json()
  const offset = scriptContent.indexOf('menu.value.contains(document.activeElement)')
  assert(offset >= 0)
  const before = scriptContent.slice(0, offset), line = before.split('\n').length, column = offset - before.lastIndexOf('\n') - 1
  const original = new sourceMap.SourceMapConsumer(map).originalPositionFor({ line, column })
  assert(original.source.endsWith('/controls/AppMenu.vue'), JSON.stringify(original))
  const source = map.sourcesContent[map.sources.indexOf(original.source)]
  assert(source.split('\n')[original.line - 1].includes('menu.value.contains(document.activeElement)'), 'A stack location maps to the actual Vue source line')
  const openMenu = async label => {
    await page.getByLabel('More options', { exact:true }).click()
    await page.locator('.settings-menu').getByRole('button', { name:label, exact:true }).click()
  }
  const configurationChunk = chunk(deferred[0])
  let release
  const download = new Promise(resolve => { release = resolve })
  await page.route('**' + configurationChunk, async route => { await download; await route.continue() })
  await openMenu('Configuration')
  const configuration = page.locator('dialog[aria-labelledby="configuration-title"]')
  try { await configuration.getByRole('status').filter({ hasText:'Loading interface…' }).waitFor() }
  finally { release() }
  await configuration.locator('.configuration-actions').waitFor()
  await configuration.getByRole('button', { name:'Close', exact:true }).click()
  assert.equal(requests.filter(path => path === configurationChunk).length, 1)
  await openMenu('Configuration')
  await configuration.locator('.configuration-actions').waitFor()
  await configuration.getByRole('button', { name:'Close', exact:true }).click()
  assert.equal(requests.filter(path => path === configurationChunk).length, 1, 'An opened editor reuses its loaded module')
  await openMenu('Script Editor')
  const script = page.getByRole('dialog', { name:'Script Editor', exact:true })
  await script.getByLabel('Script source', { exact:true }).waitFor()
  await page.waitForFunction(() => document.querySelector('.script-editor-dialog')?.getAttribute('aria-busy') === 'false')
  await script.getByLabel('Script source', { exact:true }).fill('return "lazy draft"')
  await script.getByRole('button', { name:'Close script editor', exact:true }).click()
  await openMenu('Script Editor')
  await script.getByLabel('Script source', { exact:true }).waitFor()
  assert.equal(await script.getByLabel('Script source', { exact:true }).inputValue(), 'return "lazy draft"', 'Closing retains the editor draft')
  assert.equal(requests.filter(path => path === chunk('features/scripts/ScriptEditor.vue')).length, 1)
  await page.waitForFunction(() => document.querySelector('.script-editor-dialog')?.getAttribute('aria-busy') === 'false')
  await script.getByRole('button', { name:'Close script editor', exact:true }).click()
  await openMenu('Help')
  const help = page.getByRole('dialog', { name:'Help', exact:true })
  await help.locator('.help-article-scroll article > .markdown-text').waitFor()
  assert(requests.includes(chunk('controls/MarkdownText.vue')), 'Markdown loads when an article is opened')
  await help.getByRole('button', { name:'Close help', exact:true }).click()
  await openMenu('Administration')
  await page.locator('.search-types-editor').waitFor()
  assert(requests.includes(chunk('features/administration/SearchTypes.vue')))
  assert(!requests.includes(chunk('features/administration/ColumnsEditor.vue')), 'Other administration sections stay deferred')
  assert.deepEqual(errors, [])

  const docs = await browser.newPage()
  const docsRequests = []
  docs.on('request', request => docsRequests.push(new URL(request.url()).pathname))
  docs.on('pageerror', error => errors.push(error.message))
  await docs.goto(process.argv[2] + '/docs/')
  await docs.locator('.api-docs-content').waitFor()
  assert(docsRequests.includes(chunk('features/documentation/ApiDocumentation.vue')))
  assert(!docsRequests.includes(chunk('App.vue')), 'The API reference must not download the workspace')
  assert.deepEqual(errors, [])

  const failed = await browser.newPage()
  await failed.route('**' + chunk('App.vue'), route => route.abort())
  await failed.goto(process.argv[2] + '/')
  await failed.getByRole('alert').filter({ hasText:'Unable to load the interface' }).waitFor()
  const bytes = startupRequests.reduce((total, path) => total + readFileSync(new URL('../../src/tactic_stream/web/' + path.slice('/ui/'.length), import.meta.url)).length, 0)
  console.log(JSON.stringify({ startupJsFiles:startupRequests.length, startupJsBytes:bytes, deferred:deferred.length, docsIsolated:true, failedDownloadVisible:true }))
} finally { await browser.close() }
