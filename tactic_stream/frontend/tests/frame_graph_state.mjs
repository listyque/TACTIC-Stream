import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/controls/graph/graph.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/controls/graph/graph.ui.mjs'

const model={width:1000,height:700,nodes:[{identity:'a',label:'A',nodeX:0,nodeY:0},{identity:'b',label:'B',nodeX:300,nodeY:0},{identity:'ref',nodeX:0,nodeY:150,referenceOnly:true}],edges:[{from:'a',to:'b',label:'A to B'}],selectedNodes:['a','ref'],readOnly:false,selectionEnabled:true}
const viewport=UI.viewport(model)
let ui=State.initial(), commands=[]
function step(event){const result=State.reduce(ui,event,model,viewport);ui=result.ui;commands=result.commands;for(const command of commands)if(command.type==='selectNodes')model.selectedNodes=command.identities;return commands}
function down(x,y,extra={}){return step({type:'down',x,y,...extra})}
function move(x,y){return step({type:'move',x,y})}
function up(x,y){return step({type:'up',x,y})}
const key=(value,extra={})=>step({type:'key',key:value,...extra})
// Dragging publishes exactly once and leaves reference nodes fixed, including negative coordinates.
down(70,40);move(0,0);assert.equal(commands.some(row=>row.type==='moveNodes'),false)
assert.equal(State.position(ui,model.nodes[0]).nodeX,-70)
assert.deepEqual(up(0,0),[{type:'moveNodes',positions:[{identity:'a',nodeX:-70,nodeY:-40}]}])
assert.equal(model.nodes[0].nodeX,0)
down(70,40);move(150,40);step({type:'cancel'});assert.equal(ui.pointer,null);assert.equal(State.position(ui,model.nodes[0]).nodeX,0)
// Ctrl toggles, Shift adds; selecting an already selected group for drag preserves it.
assert.deepEqual(State.selection(model,'b',{control:true},false),['a','ref','b'])
assert.deepEqual(State.selection(model,'a',{control:true},false),['ref'])
assert.deepEqual(State.selection(model,'a',{},true),['a','ref'])
// Ports work in both directions, reject self-links and cancel without writes.
step({type:'activate',target:{kind:'port',identity:'a',input:false}})
assert.deepEqual(step({type:'activate',target:{kind:'port',identity:'b',input:true}}),[{type:'connect',from:'a',to:'b'}]);assert.equal(ui.pending,null)
step({type:'activate',target:{kind:'port',identity:'a',input:true}});assert.equal(step({type:'activate',target:{kind:'port',identity:'a',input:false}}).length,0)
key('Escape');assert.equal(ui.pending,null)
// Zoom keeps the scene point under the pointer; scroll does not extend the world.
ui=State.initial();const before=State.point(ui,240,160);step({type:'zoom',value:1.8,x:240,y:160});assert.deepEqual(State.point(ui,240,160),before)
assert.equal(ui.zoom,1.8);const world={...ui.world};step({type:'scroll',x:1e6,y:1e6});assert.deepEqual(ui.world,world)
// One repeated keypress cannot repeat destructive commands or saves.
assert.deepEqual(key('s',{control:true}),[{type:'save'}]);assert.deepEqual(key('s',{control:true,repeat:true}),[])
assert.deepEqual(key('Delete'),[{type:'remove'}]);assert.deepEqual(key('Delete',{repeat:true}),[])
assert.equal(key('ArrowLeft')[0].positions.length,1)
model.readOnly=true;assert.deepEqual(key('Delete'),[]);assert.deepEqual(key('s',{control:true}),[]);assert.deepEqual(key('ArrowLeft'),[])
// Pinch replaces a drag and releasing one finger must not synthesize a click/write.
ui=State.initial();step({type:'touch',points:[{x:50,y:50}]});step({type:'touch',points:[{x:50,y:50},{x:150,y:50}]});step({type:'touch',points:[{x:0,y:50},{x:200,y:50}]});assert.equal(ui.zoom,2)
assert.deepEqual(step({type:'touch',points:[{x:100,y:50}]}),[]);assert.deepEqual(step({type:'touch',points:[]}),[]);assert.equal(ui.touch,null)
// Reverse edges have distinct curves and missing endpoints are ignored.
const edges=State.curves(State.initial(),{...model,edges:[...model.edges,{from:'b',to:'a'},{from:'absent',to:'a'}]})
assert.equal(edges.length,2);assert.notEqual(State.curvePoint(edges[0],.5).y,State.curvePoint(edges[1],.5).y)
// The production projection explicitly supplies an empty color for ordinary edges.
assert.equal(State.curves(State.initial(),{nodes:[{identity:'a',color:'#ab67c8'},{identity:'b'}],edges:[{from:'a',to:'b',color:''}]})[0].color,'#ab67c8')
assert.equal(State.curves(State.initial(),{nodes:model.nodes,edges:[{from:'a',to:'b',color:''}]})[0].color,'action')
assert.equal(State.curves(State.initial(),{nodes:model.nodes,edges:[{from:'a',to:'b',color:'#123456'}]})[0].color,'#123456')
const graph=UI.describe(model,State.initial(),'en');assert.ok(graph.nodes.some(row=>row.id==='graphNode_a'));assert.ok(!graph.nodes.some(row=>row.id==='graphInput_a'))
console.log('Frame Graph: shared geometry, selection, release-only moves, ports, camera, keys, read-only and pinch passed')
