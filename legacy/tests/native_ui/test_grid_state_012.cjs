// Execute the actual SFC methods (no template replacement) with isolated state.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
let src=fs.readFileSync(path.join(root,'frontend/src/components/ConfiguredTable.vue'),'utf8').match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
src=src.replace(/^import .*?;\s*$/gm,'').replace('export default','module.exports=');
let calls=[],request=async(...args)=>{calls.push(args);return {updated:2,cells:3}};
const context={module:{exports:{}},api:{request:(...args)=>request(...args)},ContextMenu:{},TableToolbar:{},TableColumns:{},WidgetDefinition:{},WidgetCell:{},FieldInput:{},WorkHoursPanel:{},confirm:()=>true};
vm.runInNewContext(src,context);const component=context.module.exports;let tests=[];
function test(name,callback){callback();tests.push({name,passed:true})}
function state(){const s={spec:{fields:[],capabilities:{update:true}},rows:[],project:'project',target:'target',$emit(){},$nextTick(){},...component.data()};Object.assign(s,component.methods);for(const [n,fn]of Object.entries(component.computed))Object.defineProperty(s,n,{get:()=>fn.call(s)});return s}
const field={name:'x',kind:'integer'};
test('Large integer differences are not rounded away',()=>assert.strictEqual(state().equalValue('9007199254740992','9007199254740993',field),false));
test('Decimal precision is not rounded away',()=>assert.strictEqual(state().equalValue('0.123456789012345671','0.123456789012345672',{kind:'number'}),false));
test('Equivalent decimal spellings compare equal',()=>assert.strictEqual(state().equalValue('001.2300','1.23e0',{kind:'number'}),true));
test('Negative zero numeric spellings compare equal',()=>assert.strictEqual(state().equalValue('-0.000','0',{kind:'number'}),true));
test('NULL is not empty string',()=>assert.strictEqual(state().equalValue(null,'',field),false));
function edit(s,k,n,original,value,kind='text'){s.editor={key:k,field:{name:n,kind},revision:'row-rev',config_revision:'config-rev',table_revision:'table-rev',original,value};return s.stageCell()}
test('Staging does not mutate original row',()=>{const s=state();s.rows=[{key:'A',values:{x:'old'}}];edit(s,'A','x','old','new');assert.strictEqual(s.rows[0].values.x,'old');assert.strictEqual(s.drafts.A.values.x,'new')});
test('Several cells share a record draft and revision',()=>{const s=state();edit(s,'A','x','old','new');edit(s,'A','y',1,2);assert.strictEqual(s.changedCells,2);assert.strictEqual(s.changedRows.length,1);assert.strictEqual(s.drafts.A.revision,'row-rev')});
test('Several rows remain in one grid buffer',()=>{const s=state();edit(s,'A','x','old','new');edit(s,'B','x','old','new');assert.strictEqual(s.changedRows.length,2)});
test('Changing value back removes only its pending cell',()=>{const s=state();edit(s,'A','x','old','new');edit(s,'A','y',1,2);edit(s,'A','x','new','old');assert.strictEqual(s.changedCells,1);assert.strictEqual(s.drafts.A.values.y,2)});
test('No-op editing leaves no dirty data',()=>{const s=state();edit(s,'A','x','old','old');assert.strictEqual(s.changedCells,0);assert.strictEqual(s.draftTableRevision,null)});
test('Explicit NULL remains a pending update',()=>{const s=state();edit(s,'A','x','old',null);assert.strictEqual(s.drafts.A.values.x,null)});
test('Malformed JSON keeps editor without staging',()=>{const s=state();assert.strictEqual(edit(s,'A','x','{}','{broken','json'),false);assert.ok(s.editor);assert.strictEqual(s.changedCells,0)});
test('Pending outside page tracked without discarding',()=>{const s=state();s.rows=[{key:'A'}];edit(s,'B','x','old','new');assert.strictEqual(s.pendingOutsidePage,1)});
test('Stock tab action opens a main tab, not a modal',()=>{const s=state(),events=[];s.$emit=(...args)=>events.push(args);s.cellOpen({key:'A'},{target:'T/~cell/K',text:'Pipeline',open_mode:'tab',inline:false});assert.strictEqual(events[0][0],'open');assert.strictEqual(events[0][1].id,'T/~cell/K');assert.strictEqual(s.cellWindow,null)});
test('Ordinary cell popups remain popups',()=>{const s=state();s.cellOpen({key:'A'},{target:'membership',text:'Users',inline:false});assert.strictEqual(s.cellWindow.target,'membership')});
test('HiddenRow cell remains inside its parent row',()=>{const s=state();s.cellOpen({key:'A'},{target:'hidden',inline:true});assert.strictEqual(s.expanded.A,'hidden');assert.strictEqual(s.cellWindow,null);s.cellOpen({key:'A'},{target:'hidden',inline:true});assert.strictEqual(s.expanded.A,null)});
(async()=>{
 let s=state();edit(s,'A','x','old','new');edit(s,'B','y',1,2);calls=[];await s.saveAll();assert.strictEqual(calls.length,1);assert.strictEqual(calls[0][0],'/table-changes');assert.strictEqual(calls[0][1].records.length,2);assert.strictEqual(s.changedCells,0);tests.push({name:'One Save Changes sends one batch and clears only on success',passed:true});
 s=state();edit(s,'A','x','old','new');request=async()=>{throw Object.assign(Error('conflict'),{details:{key:'A'}})};await s.saveAll();assert.strictEqual(s.changedCells,1);assert.strictEqual(s.drafts.A.values.x,'new');assert.strictEqual(s.drafts.A.error,'conflict');tests.push({name:'Server conflict preserves values, revision and per-row error',passed:true});
 const output={tests,passed:tests.every(t=>t.passed)};console.log(JSON.stringify(output,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
