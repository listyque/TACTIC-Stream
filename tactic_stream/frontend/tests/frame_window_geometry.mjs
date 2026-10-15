import assert from 'node:assert/strict'
import {fit, moved, resized} from '../../src/tactic_stream/shared_ui/shell/window.geometry.mjs'

const desktop = {x:0,y:0,width:1280,height:800}
const minimum = {width:280,height:180}
const original = {x:100,y:80,width:600,height:400}
assert.deepEqual(fit(original,desktop,minimum),original)
assert.deepEqual(fit({x:9000,y:-9000,width:2000,height:2000},desktop,minimum),{x:0,y:0,width:1280,height:800})
assert.deepEqual(fit({x:-9000,y:9000,width:600,height:400},{x:-1920,y:0,width:1920,height:1080},minimum),{x:-1920,y:680,width:600,height:400})
assert.deepEqual(fit({x:NaN,y:Infinity,width:NaN,height:undefined},desktop,minimum),{x:0,y:0,width:280,height:180})
assert.deepEqual(fit({x:0,y:0,width:1280,height:800},desktop,{width:1,height:1},16),{x:0,y:0,width:1264,height:784})
assert.deepEqual(moved(original,{x:-30,y:20}),{x:70,y:100,width:600,height:400})
assert.deepEqual(resized(original,'top-left',{x:1000,y:1000},desktop,minimum),{x:420,y:300,width:280,height:180})
assert.deepEqual(resized(original,'bottom-right',{x:9000,y:9000},desktop,minimum),{x:100,y:80,width:1180,height:720})
assert.deepEqual(original,{x:100,y:80,width:600,height:400},'Drag/resize cannot mutate the saved restore geometry')
assert.throws(()=>fit(original,{...desktop,width:NaN},minimum),/Window bounds/)
assert.throws(()=>resized(original,'unknown',{x:0,y:0},desktop,minimum),/Unknown window resize edge/)
console.log('Shared window geometry: restore, negative monitors, damaged persistence, drag, resize and size limits passed')
