import assert from 'node:assert/strict'
import { readWorkspace, saveWorkspace, searchTab, navigationEntries } from '../src/features/workspace/workspace.js'
import { preferenceDefaults } from '../src/features/configuration/preferences.js'

const storage = new Map()
const legacyLink = { key:'project_view/shot', default_view_mode:'table', display:{ handler:'LinkWdg', options:{ search_type:'vfx/shot', widget_key:'view_panel', view:'shot' } }, action:{handler:''}, children:[] }
const legacyTypes = [{search_type:'vfx/shot'}]
assert.equal(navigationEntries([legacyLink],legacyTypes)[0].resultMode,'table')
assert.equal(navigationEntries([{...legacyLink,display:{...legacyLink.display,options:{...legacyLink.display.options,view_mode:'continious'}}}],legacyTypes)[0].resultMode,'continious')
assert.equal(navigationEntries([{...legacyLink,default_view_mode:''}],legacyTypes)[0].resultMode,'', 'Handler-specific links retain the client preference')
globalThis.localStorage = { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) }
const tab = searchTab('Search', { type: 'demo/assets', page: 2, selectedKeys: ['demo/assets?code=ONE'], focusedKey:'demo/assets?code=ONE', rows: [{ code: 'DO_NOT_CACHE' }] })
assert.equal(tab.state.resultMode, 'continious')
assert.equal(tab.state.mobileResultMode, 'continious')
tab.loadingMode = 'pages'
const projects = [{ code: 'demo' }], types = [{ search_type: 'demo/assets' }]
const workspace = { demo: { current: 'assets', sections: [{ id: 'assets', type: 'demo/assets', tabs: [tab], current: tab.id }] } }
assert(saveWorkspace('alice', workspace))
const restored = () => readWorkspace('alice', projects, types).demo.sections[0].tabs[0]
assert.equal(restored().state.page, 2)
assert.equal(restored().loadingMode, 'pages')
assert.deepEqual(restored().state.selectedKeys, ['demo/assets?code=ONE'])
assert.equal(restored().state.focusedKey, 'demo/assets?code=ONE')
assert.deepEqual(restored().state.rows, [], 'Object data must come from the server again')
assert.equal(restored().loaded, false)
assert.deepEqual(readWorkspace('bob', projects, types), {}, 'Preferences belong to the account')
const saved = JSON.parse(storage.get('tactic_stream.workspace.alice'))
const record = saved.demo.sections[0].tabs[0]
for (const mode of ['table', 'continious', undefined, 'invalid']) {
  record.state.mobileResultMode = mode
  storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
  assert.equal(restored().state.mobileResultMode, mode === 'table' ? 'table' : 'continious')
  assert.equal(restored().state.resultMode, 'continious', 'Mobile view preserves the desktop mode')
}
for (const mode of ['table', 'compact', 'tiles']) {
  record.state.resultMode = mode
  storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
  assert.equal(restored().state.resultMode, mode, 'An explicitly saved view is preserved')
}
for (const mode of [undefined, 'invalid']) {
  record.state.resultMode = mode
  storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
  assert.equal(restored().state.resultMode, 'continious', 'Missing or invalid view uses the default tree')
}
delete record.loadingMode
record.state.selectedKeys = [null, 4, {}, '', 'x'.repeat(16385), 'demo/assets?code=ONE', 'demo/assets?code=ONE']
record.state.focusedKey = { code:'DO_NOT_CACHE' }
storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
assert.equal(restored().loadingMode, 'pages', 'Existing paged caches remain compatible')
assert.deepEqual(restored().state.selectedKeys, ['demo/assets?code=ONE'])
assert.equal(restored().state.focusedKey, '')
record.loadingMode = 'infinite'
record.state.selectedKeys = {}
storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
assert.equal(restored().loadingMode, 'infinite')
assert.deepEqual(restored().state.selectedKeys, [])
record.loadedOffsets = [40, 0, 20, 20, -1, null, '60', 1.5, Number.MAX_SAFE_INTEGER + 1]
record.query = { scope: 'demo/assets', records: [], selections: {}, filters: [], show_retired: false, tags: [], tag_column: '', order_bys: ['code asc'],
  ticket: 'DO_NOT_CACHE', project: 'other', search_type: 'other/objects', offset: 999, limit: 999, columns: ['secret'] }
record.state.searchText = 'Unsubmitted draft'
storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
assert.deepEqual(restored().loadedOffsets, [0, 20, 40])
assert.equal(restored().state.searchText, 'Unsubmitted draft')
assert.deepEqual(restored().state.loadedQuery, { scope: 'demo/assets', records: [], selections: {}, filters: [], show_retired: false, tags: [], tag_column: '', order_bys: ['code asc'], include_total: true })
const restoredWorkspace = readWorkspace('alice', projects, types)
assert(saveWorkspace('alice', restoredWorkspace))
assert(!storage.get('tactic_stream.workspace.alice').includes('DO_NOT_CACHE'))
record.loadedOffsets = Array.from({ length: 300 }, (_, index) => index * 20)
record.query.scope = 'other/objects'
record.state.pageSize = 501
storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
assert.equal(restored().loadedOffsets.length, 256)
assert.equal(restored().state.loadedQuery, null)
assert.equal(restored().state.pageSize, preferenceDefaults.checkin.displayLimit)
record.query.scope = 'demo/assets'
record.query.filters = 'Invalid filters'
storage.set('tactic_stream.workspace.alice', JSON.stringify(saved))
assert.equal(restored().state.loadedQuery, null)
assert.deepEqual(readWorkspace('alice', [], types), {})
assert.deepEqual(readWorkspace('alice', projects, []).demo.sections, [])
const closed = searchTab('Closed search', { type:'demo/assets', searchText:'Preserved history' })
workspace.demo.sections[0].closedTabs = [closed]
assert(saveWorkspace('alice', workspace))
assert.equal(readWorkspace('alice', projects, types).demo.sections[0].closedTabs[0].state.searchText, 'Preserved history')
workspace.demo.sections[0].closedTabs = [tab, ...Array.from({length:25}, (_,index) => searchTab('Closed ' + index, { type:'demo/assets' }))]
assert(saveWorkspace('alice', workspace))
assert.equal(readWorkspace('alice', projects, types).demo.sections[0].closedTabs.length, 20, 'Bounded history survives restart without storing records or credentials')
console.log('PASS workspace state: mode/page/selection, bounded saved offsets/query, rejected routing/credentials, old caches, account/catalog isolation and no object cache')
