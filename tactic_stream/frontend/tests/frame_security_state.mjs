import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/security/security.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/security/security.ui.mjs'
import {policy} from '../../src/tactic_stream/shared_ui/features/administration/admin.document.mjs'

const model={ready:true,canWrite:true,canLoad:true,busy:false,uncertain:false,dirty:false,pendingText:false,
 group:'G0',groups:[{identity:'G0',label:'Artists'}],groupDocument:{xml:'<rules/>',accessLevel:'none',project:'',subGroups:''},
 attributes:{group:'project',code:'demo',access:'allow'},selected:0,records:[{group:'project',code:'demo',access:'allow',ruleIndex:0}],
 metadata:{accessLevels:['none','low'],targets:{project:[{label:'Demo',attributes:{code:'demo'}}]},globalDefaultRulesByLevel:{none:'<rules/>'}},
 matrixRows:[{label:'Demo',attributes:{code:'demo'}}],matrixGroups:[{label:'Artists',identity:'G0'}],xmlSource:'<rules/>',jsonSource:'{}',inheritedSource:'<rules/>'}
const initial=State.synchronize(State.initial(),model,true)
let result=State.transition(initial,{...model,dirty:true},{type:'save'})
assert.equal(result.ui.confirmation,'save');assert.deepEqual(result.commands,[])
result=State.transition(result.ui,{...model,dirty:true},{type:'confirm'})
assert.deepEqual(result.commands,[{type:'save'}])
assert.equal(policy({...model,uncertain:true,dirty:true}).save,false)
assert.deepEqual(State.transition(initial,{...model,uncertain:true,dirty:true},{type:'save'}).commands,[])
result=State.transition({...initial,page:'xml'},model,{type:'text',value:'<rules><!--draft--></rules>'})
const draft=result.ui,pendingModel={...model,dirty:true,pendingText:State.pending(draft)}
assert.equal(State.pending(draft),true)
assert.deepEqual(State.transition(draft,pendingModel,{type:'scope',value:'technical'}).ui,draft)
assert.deepEqual(State.transition(draft,pendingModel,{type:'save'}).commands,[])
assert.equal(State.transition(draft,pendingModel,{type:'save'}).ui.confirmation,'')
assert.equal(State.synchronize(draft,{...model,xmlSource:'other'},false).text,draft.text,'model notifications preserve unapplied text')
assert.equal(State.transition(draft,pendingModel,{type:'discardText'}).ui.text,model.xmlSource)
assert.equal(State.transition({...initial,page:'inherited'},model,{type:'text',value:'change'}).ui.text,initial.text)
assert.equal(State.transition(initial,{...model,busy:true},{type:'scope',value:'technical'}).ui.scope,'project')
assert.deepEqual(State.transition(initial,model,{type:'navigateCell',row:0,column:0,dx:1,dy:0}).commands,[])
assert.deepEqual(State.transition(initial,model,{type:'navigateCell',row:0,column:0,dx:0,dy:0}).commands,[{type:'focusGrid',grid:'adminSecurityMatrix',row:0,column:0,id:'adminSecurityCell_0_0'}])
function inspect(nodes,ids=new Set()){
 for(const n of nodes){assert(!ids.has(n.id),n.id+' unique');ids.add(n.id);assert(n.width>=0&&n.height>=0,n.id);assert(Number.isFinite(n.x+n.y+n.width+n.height),n.id);inspect(n.children||[],ids)}
 return ids
}
for(const language of ['en','ru'])for(const width of [360,800,1100])for(const [scope] of UI.scopes)for(const page of ['group','xml','rule','inherited']){
 const ui=State.synchronize({...initial,scope,page,editing:true},model,true)
 inspect(UI.describe(model,ui,width,694,language).nodes)
 inspect(UI.toolbar(model,ui,width,language).nodes)
 const grid={cellWidth:136,rowHeight:46}
 assert.equal(UI.cell(grid,{checked:true,locked:true},0,0,model,ui,language).nodes[0].enabled,false)
 const scene=UI.describe(pendingModel,{...draft,scope:'technical'},width,694,language)
 assert.equal(scene.nodes.find(n=>n.id==='adminSecuritySource').readOnly,false,'editing a text draft remains possible')
}
console.log('Access rules shared state, guards and all scope/page layouts passed')
