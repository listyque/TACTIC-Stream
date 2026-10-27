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

const workflow={...model,section:'workflow',locked:false},flatten=nodes=>nodes.flatMap(node=>[node,...flatten(node.children||[])])
for(const width of [360,800,1100,1400]) {
 const scene=UI.describe(workflow,State.initial(),width,740,'en'),nodes=flatten(scene.nodes)
 assert(!nodes.some(node=>node.id==='administrationWorkflowLibrary'))
 if(width>=1000) {
  const navigation=nodes.find(node=>node.id==='administrationNavigation')
  assert(navigation,'Workflow retains normal labelled Administration navigation')
  for(const record of UI.sections) assert(flatten(UI.row(navigation,record,workflow,State.initial(),'en').nodes).some(node=>node.id==='adminSectionTitle_'+record.id && node.text))
  assert.equal(scene.geometry.nav,250)
 }
}
