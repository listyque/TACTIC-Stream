import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.ui.mjs'
const rule={key:'R1',kind:'trigger',managed:false,title:'Rule',description:'',scope:'local',action:'task_status',event:'change|sthpw/task|status',targets:[],outputs:[],srcStatus:'',mode:'same process,same transaction'}
const model={ready:true,canLoad:true,canWrite:true,busy:false,uncertain:false,dirty:true,document:{rules:[rule,{...rule,kind:'notification'}]},rule,metadata:{processes:[{identity:'model',label:'Model',statuses:['Pending','Complete']}],items:[{key:'cg/assets?code=A1',label:'Asset'}]},selected:0}
let ui=State.initial();const send=(event,context=model)=>{const result=State.transition(ui,context,event);ui=result.ui;return result.commands}
assert.deepEqual(send({type:'field',field:'managed',value:true}),[])
assert.deepEqual(send({type:'field',field:'title',value:'Changed'}),[{type:'field',field:'title',value:'Changed'}])
assert.deepEqual(send({type:'field',field:'title',value:'Changed'},{...model,rule:{...rule,managed:true}}),[])
for(const type of ['add','field','target','output','remove','save'])assert.deepEqual(send({type,field:'title',value:'x'},{...model,uncertain:true}),[])
send({type:'remove'});assert.equal(ui.confirmation,'remove');assert.deepEqual(send({type:'confirm'}),[{type:'remove'}])
send({type:'close'});assert.equal(ui.confirmation,'close');send({type:'keep'});assert.equal(ui.confirmation,'');send({type:'close'});assert.deepEqual(send({type:'confirm'}),[{type:'discard'},{type:'close'}])
assert.deepEqual(send({type:'page',value:'notification'}),[{type:'select',index:1}]);assert.deepEqual(send({type:'add'}),[{type:'add',kind:'notification'}])
assert.deepEqual(send({type:'items',offset:50}),[]);assert.deepEqual(send({type:'object',key:'not-in-catalog'}),[])
assert.deepEqual(send({type:'object',key:'cg/assets?code=A1'}),[{type:'object',key:'cg/assets?code=A1'}])
for(const action of ['task_status','parent_status','task_create','task_date','custom_script','python_class','notification'])for(const width of [360,800,1100]){
 const context={...model,rule:{...rule,action,kind:action==='notification'?'notification':'trigger'}};const state={...State.initial(),editing:true,page:context.rule.kind}
 const scene=UI.describe(context,state,width,740,'ru'),ids=new Set();const walk=nodes=>nodes.forEach(node=>{assert(!ids.has(node.id),'duplicate id '+node.id);ids.add(node.id);assert(Number.isFinite(node.width)&&node.width>=0,node.id);walk(node.children||[])})
 walk(scene.nodes)
}
console.log('Process rules: managed protection, fields, actions, confirmations, unknown writes, paging and adaptive forms passed')
