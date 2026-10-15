import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { mkdir } from 'node:fs/promises'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url))
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h,withDirectives} from 'vue'
import App from '/src/App.vue'
import AppButton from '/src/controls/AppButton.vue'
import AppMenu from '/src/controls/AppMenu.vue'
import WorkspaceTabs from '/src/controls/WorkspaceTabs.vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',mode:'dark',clickAnimations:true,popupAnimations:true,fadeAnimations:true});initializeAppearance()
createApp({data(){return {clicks:0,help:0,selected:'a',tabs:[{id:'a',title:'First search'},{id:'b',title:'Second search'},{id:'c',title:'Third search'}]}},methods:{dismissMenus:App.methods.dismissMenus},mounted(){window.host=this},render(){
 const utility=(id,x)=>withDirectives(h('dialog',{ref:id,id,class:'record-dialog',style:'position:fixed;margin:0;left:'+x+'px;top:100px;width:450px;height:250px'},[
  h('header',[h('h2',id),h(AppButton,{label:'Close '+id,icon:'close',iconOnly:true,onClick:()=>this.$refs[id].close()})]),
  h(AppButton,{label:'Action '+id,icon:'refresh',iconOnly:true,onClick:()=>this.clicks++}),
  h('input',{'aria-label':'Window input '+id}),
  h(AppMenu,{label:'Menu '+id,overlay:true},()=>h(AppButton,{label:'Menu action '+id,onClick:()=>this.clicks++}))
 ]),[[windowDirective,{type:'window'}]])
 return h('div',{class:'workspace',style:'height:100dvh;display:flex;flex-direction:column',onPointerdown:this.dismissMenus},[
  h('div',{style:'display:flex;height:50px'},[h(AppButton,{label:'Round action',icon:'refresh',iconOnly:true,onClick:()=>this.clicks++}),h(AppButton,{label:'Disabled action',icon:'refresh',iconOnly:true,disabled:true,onClick:()=>this.clicks++})]),
  utility('first',60),utility('second',640),
  h(WorkspaceTabs,{kind:'search',tabs:this.tabs,selected:this.selected,onSelect:id=>this.selected=id,onReorder:(source,target)=>this.tabs.splice(target,0,...this.tabs.splice(source,1))}),
  h(DockWorkspace,{ref:'docks',login:'activation-fixture',canAdminister:true,onHelp:()=>this.help++})
 ])}}).directive('window',windowDirective).mount('#app')
window.events=[]
for(const name of ['pointerdown','pointerup','click','pointercancel'])document.addEventListener(name,event=>window.events.push({type:name,target:event.target.closest('[aria-label]')?.getAttribute('aria-label')||event.target.tagName}),true)
</script></body></html>`
let server, browser
const deadline = setTimeout(() => browser?.close(), 55000)
try {
 server = await createServer({ root, configFile:false, cacheDir:root+'/node_modules/.vite/button-activation', plugins:[vue(),{
  name:'button-activation-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
   if(req.url !== '/activation-test')return next()
   try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
  })},
 }], server:{host:'127.0.0.1',port:0,watch:null} });await server.listen()
 browser = await chromium.launch({headless:true})
 const page = await browser.newPage({viewport:{width:1280,height:900},hasTouch:true}), errors=[]
 page.setDefaultTimeout(6000);page.on('pageerror',error=>errors.push(error.message))
 await page.route('**/admin/**',route=>route.fulfill({json:{result:{presets:[],revision:'fixture'}}}))
 await page.goto(server.resolvedUrls.local[0]+'activation-test');await page.waitForFunction(()=>!!window.host)
 await page.evaluate(()=>document.fonts.ready)
 async function press(locator,{touch=false,hold=0,edge=false,drift=0}={}) {
  if(await locator.getAttribute('role')==='tab') {
   await locator.evaluate(el=>el.scrollIntoView({block:'nearest',inline:'nearest'}))
   await page.evaluate(()=>new Promise(requestAnimationFrame))
  }
  const box=await locator.boundingBox();assert(box)
  const x=box.x+(edge ? 2 : box.width/2),y=box.y+box.height/2
  await page.mouse.move(x,y)
  if(hold)await page.waitForTimeout(hold)
  await page.evaluate(point=>{window.events=[{point,hit:document.elementFromPoint(point.x,point.y)?.outerHTML.slice(0,300)}]}, {x,y})
  const tabs=await locator.evaluate(el=>el.closest('.dock-titlebar') ? [...el.closest('.dock-titlebar').querySelectorAll('[role="tab"]')].map(tab=>({id:tab.dataset.tabId,x:tab.getBoundingClientRect().x,width:tab.getBoundingClientRect().width})) : [])
  if(touch)await page.touchscreen.tap(x,y)
  else{await page.mouse.down();await page.waitForTimeout(40);
   if(await locator.getAttribute('role')==='tab') {
    const after=await locator.boundingBox()
    assert(Math.abs(after.x-box.x)<1 && Math.abs(after.width-box.width)<1,'Tab moves during press: '+JSON.stringify({before:box,after}))
   }
   if(tabs.length)assert.deepEqual(await locator.evaluate(el=>[...el.closest('.dock-titlebar').querySelectorAll('[role="tab"]')].map(tab=>({id:tab.dataset.tabId,x:tab.getBoundingClientRect().x,width:tab.getBoundingClientRect().width}))),tabs,'Dock tabs move before the mouse is released')
   if(drift)await page.mouse.move(x+drift,y)
   await page.mouse.up()}
  await page.evaluate(()=>new Promise(requestAnimationFrame))
  return page.evaluate(()=>window.events)
 }
 const count=()=>page.evaluate(()=>window.host.clicks)
 const round=page.getByRole('button',{name:'Round action',exact:true})
 for(const options of [{},{hold:700},{edge:true},{touch:true},{edge:true,drift:-4}]) {
  const before=await count(),events=await press(round,options)
  assert.equal(await count(),before+1,JSON.stringify(events))
 }
 const beforeDisabled=await count();await press(page.getByRole('button',{name:'Disabled action',exact:true}));assert.equal(await count(),beforeDisabled)
 const beforeCancel=await count();await press(round,{edge:true,drift:-30});assert.equal(await count(),beforeCancel,'Dragging away cancels the click')
 await round.focus();assert.equal(await round.evaluate(el=>getComputedStyle(el).outlineStyle),'none')
 await page.keyboard.press('Space');assert.equal(await count(),beforeCancel+1,'Keyboard activation remains native and fires once')
 const searchTabs=page.locator('.workspace-tabs[data-kind="search"]')
 await press(searchTabs.getByRole('tab',{name:'Second search',exact:true}),{edge:true,drift:-4});assert.equal(await page.evaluate(()=>window.host.selected),'b')
 const dragTab=await searchTabs.getByRole('tab',{name:'First search',exact:true}).boundingBox()
 await page.mouse.move(dragTab.x+dragTab.width/2,dragTab.y+dragTab.height/2);await page.mouse.down()
 await page.mouse.move(dragTab.x+dragTab.width/2+dragTab.width,dragTab.y+dragTab.height/2,{steps:4});await page.mouse.up()
 assert.deepEqual(await page.evaluate(()=>window.host.tabs.map(tab=>tab.id)),['b','a','c'],'Capture transfers to the tab drag without losing reorder')
 assert.equal(await page.evaluate(()=>window.host.selected),'b','Tab dragging does not activate it')
 await page.evaluate(()=>window.host.$refs.docks.show('notes'))
 const dock=page.locator('[data-dock="notes"]'),help=dock.getByRole('button',{name:'Help',exact:true})
 for(const options of [{},{hold:700},{edge:true},{touch:true},{edge:true,drift:-4}]) {
  const before=await page.evaluate(()=>window.host.help),events=await press(help,options)
  assert.equal(await page.evaluate(()=>window.host.help),before+1,JSON.stringify(events))
 }
 const position=dock.getByLabel('Panel position: Task Inspector',{exact:true})
 await press(position,{edge:true,drift:-4});assert(await position.evaluate(el=>el.parentElement.open),'Dock position opens on the first click')
 await press(position);assert.equal(await position.evaluate(el=>el.parentElement.open),false)
 const maximize=dock.getByRole('button',{name:'Maximize panel',exact:true})
 await press(maximize,{edge:true,drift:-4});assert.equal(await dock.getByRole('button',{name:'Restore panel',exact:true}).count(),1)
 await press(dock.getByRole('button',{name:'Restore panel',exact:true}))
 const grip=dock.locator('.dock-move-handle'),box=await grip.boundingBox()
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2)
 assert.equal(await grip.evaluate(el=>{const box=el.getBoundingClientRect();return getComputedStyle(document.elementFromPoint(box.x+box.width/2,box.y+box.height/2)).cursor}),'grab')
 await page.mouse.down();await page.mouse.move(box.x+box.width/2-60,box.y+box.height/2+55,{steps:3})
 assert.equal(await grip.evaluate(el=>getComputedStyle(el).cursor),'grabbing')
 await page.keyboard.press('Escape');await page.mouse.up()
 assert.equal(await grip.evaluate(el=>getComputedStyle(el).cursor),'grab')
 await dock.locator('.dock-titlebar').focus();assert.equal(await dock.locator('.dock-titlebar').evaluate(el=>getComputedStyle(el).outlineStyle),'none')
 const dockedBox=await dock.boundingBox(),dockedTitle=await dock.locator('strong').boundingBox()
 await page.mouse.move(dockedTitle.x+10,dockedTitle.y+5);await page.mouse.down();await page.mouse.move(dockedTitle.x-30,dockedTitle.y+45);await page.mouse.up()
 assert.equal(Math.round((await dock.boundingBox()).x),Math.round(dockedBox.x),'A docked title does not move the panel')
 await press(position);await dock.getByRole('button',{name:'Float panel',exact:true}).click()
 const floatBefore=await dock.boundingBox(),layoutBefore=await page.evaluate(()=>window.host.$refs.docks.capture().layout)
 const floatTitle=await dock.locator('strong').boundingBox()
 await page.mouse.move(floatTitle.x+20,floatTitle.y+5);await page.mouse.down();await page.mouse.move(floatTitle.x+90,floatTitle.y+45,{steps:3})
 assert.equal(await page.locator('.dock-drop-guide').count(),0,'Title drag only moves, without docking')
 await page.mouse.up()
 const moved=await dock.boundingBox();assert(Math.abs(moved.x-floatBefore.x-70)<2&&Math.abs(moved.y-floatBefore.y-40)<2,'Floating title moves the panel: '+JSON.stringify({floatBefore,moved,events:await page.evaluate(()=>window.events)}))
 assert.deepEqual(await page.evaluate(()=>window.host.$refs.docks.capture().layout),layoutBefore,'Title drag preserves the dock tree')
 const cancelTitle=await dock.locator('strong').boundingBox()
 await page.mouse.move(cancelTitle.x+20,cancelTitle.y+5);await page.mouse.down();await page.mouse.move(cancelTitle.x+60,cancelTitle.y+35)
 await page.keyboard.press('Escape');await page.mouse.up()
 assert(Math.abs((await dock.boundingBox()).x-moved.x)<2,'Escape restores floating position')
 await press(position);await dock.getByRole('button',{name:'Dock panel',exact:true}).click()
 await page.evaluate(()=>{window.host.$refs.docks.show('description');window.host.$refs.docks.show('snapshot');window.host.$refs.docks.show('notes')})
 await page.evaluate(()=>new Promise(requestAnimationFrame))
 assert.equal(await dock.locator('.dock-stack-tabs').evaluate(el=>getComputedStyle(el).overflowY),'hidden','The title has no vertical scrollbar')
 assert(await dock.locator('.dock-stack-tabs').evaluate(el=>el.scrollHeight<=el.clientHeight),'Horizontal tab scrolling fits inside the title')
 for(const id of ['description','notes','snapshot','notes']) {
  const tab=page.locator('.dock-panel:visible').getByRole('tab',{name:id==='notes'?'Task Inspector':id==='snapshot'?'Snapshot Browser':'Description',exact:true})
  const events=await press(tab,{edge:true,drift:-4})
  assert.equal(await page.evaluate(id=>window.host.$refs.docks.presented(id),id),true,'Stack tab: '+JSON.stringify(events))
 }
 await press(dock.getByRole('button',{name:'Maximize panel',exact:true}));assert.equal(await dock.getByRole('button',{name:'Restore panel',exact:true}).count(),1)
 await press(dock.getByRole('button',{name:'Restore panel',exact:true}))
 await press(dock.getByRole('button',{name:'Close panel: Task Inspector',exact:true}),{edge:true,drift:-4});assert.equal(await page.evaluate(()=>window.host.$refs.docks.presented('notes')),false)
 const withQueue=await page.evaluate(()=>{window.host.$refs.docks.show('commit_queue');return window.host.$refs.docks.capture()})
 const withoutQueue=await page.evaluate(()=>{window.host.$refs.docks.hide('commit_queue');return window.host.$refs.docks.capture()})
 await page.evaluate(layout=>window.host.$refs.docks.apply(layout),withQueue)
 assert.equal(await page.evaluate(()=>window.host.$refs.docks.capture().panels.find(panel=>panel.panel_id==='commit_queue').visible),true)
 await page.evaluate(layout=>window.host.$refs.docks.apply(layout),withoutQueue)
 assert.equal(await page.evaluate(()=>window.host.$refs.docks.capture().panels.find(panel=>panel.panel_id==='commit_queue').visible),false,'Queue visibility belongs to each saved layout, matching Handler')
 await page.evaluate(()=>{
  const layout=window.host.$refs.docks.capture(),results=layout.panels.find(panel=>panel.panel_id==='results')
  Object.assign(results,{dock_area:'floating',x:.1,y:.1,width:.45,height:.4});window.host.$refs.docks.apply(layout)
 })
 assert(await page.locator('[data-dock="results"] > .dock-titlebar').isVisible(),'Floating Results also has a draggable title')
 await page.evaluate(layout=>window.host.$refs.docks.apply(layout),withoutQueue)
 await page.evaluate(()=>window.host.$refs.docks.show('notes'))
 const screenshots=fileURLToPath(new URL('../../.screenshots/dock-controls-current/',import.meta.url))
 await mkdir(screenshots,{recursive:true});await page.screenshot({path:screenshots+'dock-title.png'})
 await page.evaluate(()=>{window.host.$refs.first.show();window.host.$refs.second.show()})
 const first=page.locator('#first'),second=page.locator('#second')
 await first.getByLabel('Window input first',{exact:true}).focus()
 assert.equal(await first.getByLabel('Window input first',{exact:true}).evaluate(el=>getComputedStyle(el).outlineStyle),'none')
 for(let i=0;i<4;i++) {
  const target=i%2===0?first:second,before=await count(),events=await press(target.getByRole('button',{name:i%2===0?'Action first':'Action second',exact:true}))
  assert.equal(await count(),before+1,'Inactive window: '+JSON.stringify(events))
 }
 for(const target of [first,second,first]) {
  const name=await target.getAttribute('id')
  const trigger=target.getByLabel('Menu '+name,{exact:true})
  const events=await press(trigger,{hold:700})
  assert(await trigger.evaluate(el=>el.parentElement.open),'Inactive window menu: '+JSON.stringify(events))
  const before=await count()
  await press(target.getByRole('button',{name:'Menu action '+name,exact:true}))
  assert.equal(await count(),before+1)
 }
 assert.deepEqual(errors,[])
 console.log('PASS mouse release drift, keyboard/touch/disabled, tab reorder, dock grip/title drag/cancel, no vertical title scrollbar or focus rings, saved queue visibility and inactive utility windows')
} finally {clearTimeout(deadline);await browser?.close();await server?.close()}
