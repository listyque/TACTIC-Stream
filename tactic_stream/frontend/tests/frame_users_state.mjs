import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/users/users.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/users/users.ui.mjs'
const base={ready:true,canWrite:true,canLoad:true,draft:{login:'artist',first_name:'',groups:[]},identity:'artist',profile:{login:'artist'},dirty:true,userCount:80,groupCount:3}
let result=State.transition(State.initial(),base,{type:'save'})
assert.equal(result.ui.confirmation,'save');assert.deepEqual(result.commands,[])
result=State.transition(result.ui,base,{type:'confirm'});assert.deepEqual(result.commands,[{type:'save'}])
for(const model of [{...base,canWrite:false},{...base,busy:true},{...base,uncertain:true}]){
 for(const event of [{type:'field',field:'first_name',value:'denied'},{type:'member',name:'Artists',value:true},{type:'save'},{type:'create'}])assert.deepEqual(State.transition(State.initial(),model,event).commands,[])
}
assert.deepEqual(State.transition(State.initial(),base,{type:'field',field:'login',value:'renamed'}).commands,[])
assert.deepEqual(State.transition(State.initial(),base,{type:'field',field:'password_hash',value:'injected'}).commands,[])
result=State.transition(State.initial(),{...base,uncertain:true},{type:'reload'})
assert.equal(result.ui.confirmation,'reload');assert.deepEqual(result.commands,[])
assert.deepEqual(State.transition(result.ui,{...base,uncertain:true},{type:'confirm'}).commands,[{type:'reload',force:true}])
assert.equal(UI.profile({login:'new_user',first_name:' Alice ',last_name:'Jones'},null).initials,'AJ')
assert.equal(UI.translate('Hourly wage must be a non-negative number','ru'),'Почасовая ставка должна быть неотрицательным числом')
assert.equal(UI.translate('A user with this login already exists','ru'),'Пользователь с таким логином уже существует')
for(const width of [320,360,800,1100])for(const page of ['profile','account','groups']){
 const scene=UI.describe(base,{...State.initial(),page},width,694,'ru')
 const walk=nodes=>{for(const node of nodes){for(const key of ['x','y','width','height'])assert(Number.isFinite(node[key]));assert(node.width>=0&&node.height>=0);walk(node.children)}}
 walk(scene.nodes)
 const panel=scene.nodes.find(node=>node.id==='adminUserDetails');assert(panel.x+panel.width<=width)
}
console.log('PASS shared Users confirmation, permissions, immutable login, unknown-save recovery and narrow forms')
