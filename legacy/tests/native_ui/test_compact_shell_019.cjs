/* Regression tests for removed duplicate chrome, retained actions and refresh. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'../..'),tests=[];
function text(n){return fs.readFileSync(path.join(root,'frontend/src',n==='App'?'App.vue':'components/'+n+'.vue'),'utf8')}
async function test(name,fn){await fn();tests.push({name,passed:true});console.log('PASS '+name)}
function app(confirm=()=>true){let s=text('App').match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];const names=[...s.matchAll(/^import (\w+) from .*?;\s*$/gm)].map(m=>m[1]);s=s.replace(/^import .*?;\s*$/gm,'').replace('export default','module.exports=');let calls=0;const c={...Object.fromEntries(names.map(n=>[n,{}])),module:{exports:{}},confirm,window:{},api:{request:async()=>{calls++;return {id:'x',kind:'layout-editor'}}}};vm.runInNewContext(s,c);const def=c.module.exports,t={id:'x',kind:'layout-editor',dirty:false,refreshKey:2};const a={...def.data(),project:'p',tabs:[t],active:'x',navigationSeq:0,reloadSidebar:async()=>{},loadPage:async()=>{}};Object.assign(a,def.methods);a.reloadSidebar=async()=>{};a.loadPage=async()=>{};Object.defineProperty(a,'current',{get:()=>a.tabs.find(t=>t.id===a.active)});return {a,t,c,calls:()=>calls}}
(async()=>{
 await test('Page title and path block removed from main shell',()=>assert.ok(!text('App').includes('class="view-heading"')));
 await test('Active title remains in workspace tabs',()=>assert.ok(text('App').includes('{{tab.title}}')));
 await test('Refresh and menu live in existing tab row',()=>{const s=text('App');assert.ok(s.includes('class="workspace-tabbar"'));assert.ok(s.includes('aria-label="Обновить представление"'));assert.ok(s.includes('aria-label="Меню представления"'))});
 for(const name of ['CustomLayoutEditor','ManageViews','ScriptEditor','SearchTypes','SidebarEditor','SecurityMatrix']){
  await test(name+' has no duplicated title/eyebrow block',()=>{const s=text(name).split('<template>')[1];assert.ok(!s.includes('class="design-heading"'));assert.ok(!s.includes('class="admin-workspace-heading"'));assert.ok(!s.includes('class="eyebrow"'))})
 }
 await test('Sidebar original XML action retained after merge',()=>assert.ok(text('SidebarEditor').includes('@click="openRaw">Исходный XML')));
 await test('Create SearchType remains a catalog action',()=>assert.ok(text('SearchTypes').includes('@click="startCreate">Новый SearchType')));
 await test('ManageViews keeps SearchType selector',()=>assert.ok(text('ManageViews').includes('v-model="stype" @change="typeChanged"')));
 await test('New project wizard starts with steps, not hero',()=>{assert.ok(!text('ProjectWizard').includes('wizard-intro'));assert.ok(text('ProjectWizard').includes('class="wizard-steps"'))});
 await test('Popup titles and configured field headings retained',()=>{const s=text('ConfiguredForm');assert.ok(s.includes('<h2 :id="titleId">'));assert.ok(s.includes('<h3 v-if="f.kind===\'heading\'">{{f.label}}</h3>'))});
 await test('Headerless forms still have accessible names',()=>assert.ok(text('ConfiguredForm').includes(':aria-label="form.widget?.show_header===false?')));
 await test('No global h2/header hiding in compact CSS',()=>{const s=fs.readFileSync(path.join(root,'frontend/src/styles.css'),'utf8').split('/* 0.19:')[1];assert.ok(!/(^|})\s*(?:h[1-6]|header)[^{}]*\{[^}]*display:\s*none/.test(s))});
 await test('Refresh cancel keeps dirty draft and sends no request',async()=>{const x=app(()=>false);x.t.dirty=true;await x.a.refresh();assert.equal(x.t.dirty,true);assert.equal(x.t.refreshKey,2);assert.equal(x.calls(),0)});
 await test('Refresh bumps editor instance key after success',async()=>{const x=app();x.t.dirty=true;await x.a.refresh();assert.equal(x.t.dirty,false);assert.equal(x.t.refreshKey,3);assert.equal(x.calls(),1);assert.equal(x.a.refreshing,false)});
 await test('Failed refresh keeps draft and reports error',async()=>{const x=app();x.t.dirty=true;x.c.api.request=async()=>{throw Error('offline')};await x.a.refresh();assert.equal(x.t.dirty,true);assert.equal(x.t.refreshKey,2);assert.equal(x.a.error,'offline');assert.equal(x.a.refreshing,false)});
 await test('Second click cannot start parallel refresh',async()=>{const x=app();let release,calls=0;x.c.api.request=()=>{calls++;return new Promise(r=>release=r)};const pending=x.a.refresh();await x.a.refresh();release({id:'x',kind:'layout-editor'});await pending;assert.equal(calls,1)});
 await test('Late response cannot refresh closed editor',async()=>{const x=app();let release;x.c.api.request=()=>new Promise(r=>release=r);const pending=x.a.refresh();x.a.tabs=[];release({id:'x',kind:'script-editor'});await pending;assert.equal(x.t.kind,'layout-editor');assert.equal(x.t.refreshKey,2)});
 await test('Late response cannot refresh other project',async()=>{const x=app();let release;x.c.api.request=()=>new Promise(r=>release=r);const pending=x.a.refresh();x.a.project='q';x.a.navigationSeq++;release({id:'x',kind:'script-editor'});await pending;assert.equal(x.t.kind,'layout-editor')});
 console.log(JSON.stringify({passed:true,tests},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
