import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import * as sizing from '../../src/tactic_stream/shared_ui/shell/window.sizing.mjs'

// Captured from Handler's WindowSizing.qml before extraction on 2026-10-15.
const reference=JSON.parse(await readFile(new URL('./fixtures/window_sizing.json',import.meta.url),'utf8'))
let checks=0
for(const [name,cases] of Object.entries(reference)) {
  for(const [kind,expected] of Object.entries(cases)) {
    assert.equal(sizing[name](kind),expected,name+' '+kind)
    checks++
  }
  for(const kind of ['__proto__','constructor','toString']) assert.equal(sizing[name](kind),cases.unknown,'Unknown identifiers always return a numeric fallback')
}
console.log('Shared window/dock minimum sizes:',checks,'original Handler values and unknown identifiers passed')
