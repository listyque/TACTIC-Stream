// Execute real SFC methods and computed properties, no replacement UI.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
function component(name,globals={}){let src=fs.readFileSync(path.join(root,'frontend/src/components',name+'.vue'),'utf8').match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];src=src.replace(/^import .*?;\s*$/gm,'').replace('export default','module.exports=');const ctx={module:{exports:{}},api:{request:async()=>({})},ContextMenu:{},TableToolbar:{},TableColumns:{},WidgetDefinition:{},WidgetCell:{},FieldInput:{},WorkHoursPanel:{},confirm:()=>true,...globals};vm.runInNewContext(src,ctx);return ctx.module.exports}
const c=component('ConfiguredTable');let tests=[];
function test(name,fn){fn();tests.push({name,passed:true})}
function state(){const s={spec:{fields:[],capabilities:{update:true},revision:'table'},rows:[{key:'a',revision:'ra',values:{name:'A'}},{key:'b',revision:'rb',values:{name:'B'}}],project:'test',target:'configured',selected:['a','b'],$emit(){},$nextTick(){},...c.data()};Object.assign(s,c.methods);for(const [k,v]of Object.entries(c.computed))Object.defineProperty(s,k,{get:()=>v.call(s)});return s}
function preview(s,items){s.fill={busy:false,preview:{items},signature:s.fillSignature()}}
function item(key,original,value,kind='text'){return {key,original,value,field:{name:'name',kind},revision:'r'+key,config_revision:'editor',table_revision:'table'}}
test('Accept fill stages both rows, never mutates source rows',()=>{const s=state();preview(s,[item('a','A','X'),item('b','B','X')]);s.acceptFill();assert.equal(s.changedCells,2);assert.equal(s.rows[0].values.name,'A');assert.equal(s.drafts.b.values.name,'X');assert.equal(s.fill,null)});
test('Existing independent draft survives fill',()=>{const s=state();s.editor={...item('a','1','2'),field:{name:'other',kind:'text'}};s.stageCell();preview(s,[item('a','A','X'),item('b','B','X')]);s.acceptFill();assert.equal(s.drafts.a.values.other,'2');assert.equal(s.changedCells,3)});
test('Fill back to original removes old pending field',()=>{const s=state();s.editor=item('a','A','X');s.stageCell();preview(s,[item('a','A','A')]);s.acceptFill();assert.equal(s.changedCells,0);assert.equal(s.draftTableRevision,null)});
test('Rejected final JSON cannot partially stage prefix',()=>{const s=state();preview(s,[item('a','A','X'),item('b','B','{bad','json')]);s.acceptFill();assert.equal(s.changedCells,0);assert.ok(s.fill.error)});
test('Changing drafts after preview invalidates acceptance',()=>{const s=state();preview(s,[item('a','A','X')]);s.editor=item('b','B','Y');s.stageCell();s.acceptFill();assert.equal(s.changedCells,1);assert.equal(s.drafts.a,undefined);assert.ok(s.fill.error)});
test('Changing table definition invalidates acceptance',()=>{const s=state();preview(s,[item('a','A','X')]);s.spec.revision='new-table';s.acceptFill();assert.equal(s.changedCells,0);assert.ok(s.fill.error)});
test('Changing fill input clears previous preview',()=>{const s=state();preview(s,[item('a','A','X')]);s.changeFill('Y');assert.equal(s.fill.preview,null)});
test('Pending JSON NULL remains NULL',()=>{const s=state();preview(s,[item('a','A',null)]);s.acceptFill();assert.strictEqual(s.drafts.a.values.name,null)});
test('Large integer input remains exact through staging',()=>{const s=state();preview(s,[item('a','1','9007199254740993','integer')]);s.acceptFill();assert.strictEqual(s.drafts.a.values.name,'9007199254740993')});
test('No write while a fill dialog is open',()=>{const s=state();preview(s,[item('a','A','X')]);s.saveAll();assert.equal(s.changedCells,0)});
const f=component('ConfiguredForm');
test('Same-tick duplicate submit emits exactly once',()=>{let emits=0,ticks=[];const s={busy:false,readOnly:false,submitting:false,form:{record:null,defaults:{name:'default'}},dirty:{name:'X'},$emit(){emits++},$nextTick(fn){ticks.push(fn)}};f.methods.save.call(s);f.methods.save.call(s);assert.equal(emits,1);assert.equal(ticks.length,1)});
test('Save sends snapshot rather than live mutable dirty object',()=>{let payload;const s={busy:false,readOnly:false,submitting:false,form:{record:{key:'a'}},dirty:{name:'X'},$emit(_,p){payload=p},$nextTick(){}};f.methods.save.call(s);s.dirty.name='Y';assert.equal(payload.name,'X')});
test('Failed/finished request releases form latch',()=>{const s={submitting:true};f.watch.busy.call(s,false);assert.equal(s.submitting,false)});
test('Read-only form never submits',()=>{let emitted=false;const s={busy:false,readOnly:true,submitting:false,$emit(){emitted=true}};f.methods.save.call(s);assert.equal(emitted,false)});
console.log(JSON.stringify({passed:true,tests},null,2));
