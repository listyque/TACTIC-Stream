import assert from 'node:assert/strict'
import { normalizePreferences,preferences } from '../src/features/configuration/preferences.js'
import { searchTab,readWorkspace } from '../src/features/workspace/workspace.js'
const saved = normalizePreferences({ checkin:{ displayLimit:700,defaultViewMode:'unknown',loadingMode:'infinite' },tasks:{ viewMode:'unknown',columns:[{ key:'object',visible:false,width:1 },{ key:'process',width:999 },{ key:'object',width:80 },{ key:'unknown' }] } })
assert.equal(saved.checkin.displayLimit,500)
assert.equal(saved.checkin.defaultViewMode,'continious')
assert.equal(saved.checkin.loadingMode,'infinite')
assert.equal(saved.tasks.viewMode,'table')
assert.equal(saved.tasks.columns[0].visible,true)
assert.equal(saved.tasks.columns[0].width,40)
assert.equal(saved.tasks.columns[1].width,480)
assert.equal(saved.tasks.columns.filter(column => column.key === 'object').length,1)
assert.equal(saved.tasks.columns.some(column => column.key === 'unknown'),false)
const repository = normalizePreferences({ repository:{ enabledAliases:['default','custom_0','custom_0','plugins','../bad'],defaultAlias:'custom_0' } }).repository
assert.deepEqual(repository.enabledAliases,['default','custom_0'])
assert.equal(repository.defaultAlias,'custom_0')
assert.equal(searchTab('Fresh').state.pageSize,20)
assert.equal(searchTab('Restored',{ pageSize:50,resultMode:'table' }).state.pageSize,50)
globalThis.localStorage = { getItem:() => JSON.stringify({ one:{ current:'assets',sections:[{ id:'assets',type:'cg/assets',current:'assets-tab',tabs:[{ id:'assets-tab',state:{ resultState:{ expanded:['asset-A'] } } }] }] } }) }
assert.deepEqual(readWorkspace('tester',[{ code:'one' }],[{ search_type:'cg/assets' }]).one.sections[0].tabs[0].state.resultState,{ expanded:['asset-A'] })
preferences.cache.cacheProcessTabs = false
assert.deepEqual(readWorkspace('tester',[{ code:'one' }],[{ search_type:'cg/assets' }]).one.sections[0].tabs[0].state.resultState,{})
console.log('Browser defaults: invalid storage normalized, required columns retained, fresh defaults and explicit workspace state passed')
