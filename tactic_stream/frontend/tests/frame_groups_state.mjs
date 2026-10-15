import assert from 'node:assert/strict'
import {initial,permissions,transition} from '../../src/tactic_stream/shared_ui/features/administration/groups/groups.state.mjs'
import {describe} from '../../src/tactic_stream/shared_ui/features/administration/groups/groups.ui.mjs'
import {node,virtualRange} from '../../src/tactic_stream/shared_ui/core/frame.mjs'

const model={ready:true,canWrite:true,canLoad:true,draft:{code:'G1',name:'team'},dirty:true}
const event=(type,values={})=>transition(initial(),model,{type,...values})
assert.deepEqual(event('page',{value:'details'}).commands,[{type:'focus',id:'segmentedButtonSegment_details'}])
assert.deepEqual(event('field',{field:'name',value:'renamed'}).commands,[])
assert.deepEqual(event('field',{field:'access_rules',value:'allow'}).commands,[])
assert.deepEqual(event('select',{code:'G2'}).commands,[])
assert.equal(event('discard').ui.confirmation,'discard')
assert.deepEqual(transition(event('discard').ui,model,{type:'confirm'}).commands,[{type:'discard'}])
assert.equal(event('close').ui.confirmation,'close')
assert.deepEqual(transition(event('close').ui,model,{type:'keep'}).commands,[])
const uncertain={...model,uncertain:true}
assert.equal(permissions(uncertain).save,false)
assert.deepEqual(transition(event('discard').ui,uncertain,{type:'confirm'}).commands,[{type:'reload',force:true}])
for(const restriction of [{busy:true},{canWrite:false},{ready:false}]){
 const blocked={...model,...restriction}
 for(const type of ['create','save','member','field'])assert.deepEqual(transition(initial(),blocked,{type,field:'description',value:'x',login:'admin'}).commands,[])
}
for(const width of [240,320,360,800,1100])for(const language of ['en','ru']){
 const visit=nodes=>{for(const n of nodes){assert(n.width>=0&&n.height>=0);if(n.children)visit(n.children)}}
 visit(describe(model,initial(),width,500,language).nodes)
}
assert.deepEqual(virtualRange(10000,58,400,5800,3),{first:97,last:110,height:580000})
assert.throws(()=>node('Unimplemented','x',{x:0,y:0,width:1,height:1}),/Unsupported/)
assert.throws(()=>node('Box','x',{x:0,y:0,width:NaN,height:1}),/Invalid/)
console.log('PASS: shared Groups permissions, draft guards, unknown-save recovery, narrow layouts and virtualization')
