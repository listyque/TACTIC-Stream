import assert from 'node:assert/strict'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/administration.state.mjs'
const model={section:'types',project:'demo',projects:[{value:'demo',label:'Demo'}],locked:true,drafts:['schema']}
assert.deepEqual(State.transition(State.initial(),model,{type:'close'}).commands,[{type:'section',value:'schema'}])
assert.deepEqual(State.transition(State.initial(),model,{type:'project',value:'demo'}).commands,[])
assert.equal(State.transition(State.initial(),model,{type:'section',value:'missing'}).commands.length,0)
for(const width of [360,800,1100,1400])for(const collapsed of [false,true]){
 const scene=UI.describe(model,{...State.initial(),collapsed},width,740,'ru')
 const check=nodes=>{for(const node of nodes){for(const key of ['x','y','width','height'])assert(Number.isFinite(node[key]),node.id);assert(node.width>=0&&node.height>=0);check(node.children||[])}}
 check(scene.nodes)
 const g=UI.geometry(width,740,collapsed);assert(g.content.x+g.content.width<=width)
}
console.log('Administration shell: navigation, project/close guards and bounded responsive geometry passed')

const workflow={...model,section:'workflow'}
const flatten=nodes=>nodes.flatMap(node=>[node,...flatten(node.children||[])])
for(const width of [360,800,1100,1400]) {
 const ui=State.initial(),scene=UI.describe(workflow,ui,width,740,'en'),nodes=flatten(scene.nodes)
 assert.equal(nodes.filter(node=>node.id==='administrationWorkflowLibrary').length,width>=1000?1:0)
 if(width>=1000) {
  assert.equal(nodes.filter(node=>node.id.startsWith('adminSection_')).length,UI.sections.length)
  const expanded=State.transition(ui,workflow,{type:'navigationSplit',value:330}).ui
  assert.equal(UI.describe(workflow,expanded,width,740,'en').geometry.nav,330)
  assert.equal(State.transition(expanded,workflow,{type:'navigationSplit',value:NaN}).ui.workflowNavigationWidth,330)
  assert(!flatten(UI.describe(workflow,{...expanded,collapsed:true},width,740,'en').nodes).some(node=>node.id==='administrationWorkflowLibrary'))
 }
}
