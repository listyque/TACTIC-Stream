import assert from 'node:assert/strict'
import { readFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'
const root=fileURLToPath(new URL('..',import.meta.url)), output=fileURLToPath(new URL('../../.screenshots/gantt-current/',import.meta.url))
const fixture=JSON.parse(await readFile(new URL('./task_schedule_fixture.json',import.meta.url),'utf8'))
const html=`<!doctype html><html><body><div id="mobile-panel-picker"></div><div id="app"></div><script type="module">
import { createApp,h,ref,provide } from 'vue'
import '/src/App.vue'
import HelpView from '/src/features/help/HelpView.vue'
import TaskManager from '/src/features/tasks/TaskManager.vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import { defaults,stack } from '/src/features/workspace/docks.js'
import { windowDirective } from '/src/controls/window.js'
import { appearance,initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{mode:'dark',popupAnimations:false,clickAnimations:false});initializeAppearance();window.appearance=appearance
const fixture=${JSON.stringify(fixture)}
const parents=fixture.records.map((row,i)=>({__search_key__:row.parentKey,code:'ASSET'+(i?i+1:''),name:row.parentTitle}))
const tasks=fixture.records.map((row,i)=>({__search_key__:row.taskCode,search_type:'cg/assets',search_code:parents[i].code,process:row.process,status:row.status,assigned:row.assigned,bid_start_date:row.start,bid_end_date:row.end,progress:row.progress,__status__:{color:row.statusColor},description:'Keep this description'}))
window.fixture={...fixture,parents,tasks}
const state=defaults();state.panels.tasks.visible=true;state.panels.task_calendar.visible=true
state.layout={type:'split',orientation:'horizontal',ratio:.7,first:stack('tasks'),second:stack('task_calendar')}
localStorage.setItem('tactic_stream.docks.gantt-test',JSON.stringify(state))
createApp({setup(){
 const help=ref(null);provide('openHelp',topic=>help.value.open(topic))
 const calendarActive=ref(true), phone=ref(innerWidth<=700)
 window.addEventListener('resize',()=>phone.value=innerWidth<=700)
 return()=>h('div',{style:'height:850px;width:100%;position:relative;display:flex;flex-direction:column'},[
 h(HelpView,{ref:help}),
 h(DockWorkspace,{ref:v=>window.docks=v,login:'gantt-test',mobile:phone.value,canAdminister:true,onOpen:id=>{if(id==='task_calendar')calendarActive.value=true}}),
 h(TaskManager,{ref:v=>window.manager=v,docked:true,ticket:'fixture',project:'cg',currentUser:'alice',calendarTarget:'#dock-task_calendar',calendarActive:calendarActive.value,onCalendar:()=>window.docks.show('task_calendar')})
 ])
}}).directive('window',windowDirective).mount('#app')
</script></body></html>`
let server,browser
try{
 await mkdir(output,{recursive:true})
 server=await createServer({root,configFile:false,plugins:[vue(),{name:'gantt-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(req.url!=='/gantt-test')return next()
  try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
 })}}],server:{host:'127.0.0.1',port:0}})
 await server.listen()
 browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']})
 const page=await browser.newPage({viewport:{width:1280,height:950},hasTouch:true}),errors=[],commands=[]
 page.setDefaultTimeout(10000);page.on('pageerror',error=>{errors.push(error.message);console.error(error.message)})
 const parents=fixture.records.map((r,i)=>({__search_key__:r.parentKey,code:'ASSET'+(i?i+1:''),name:r.parentTitle}))
 const tasks=fixture.records.map((r,i)=>({__search_key__:r.taskCode,search_type:'cg/assets',search_code:parents[i].code,process:r.process,status:r.status,assigned:r.assigned,bid_start_date:r.start,bid_end_date:r.end,progress:r.progress,__status__:{color:r.statusColor},description:'Keep this description'}))
 const catalog={users:[{value:'alice',label:'Alice Artist'},{value:'bob',label:'Bob Supervisor'}],processes:[{value:'model',label:'Modeling'},{value:'texture',label:'Texturing'},{value:'render',label:'Rendering'}],teams:[],milestoneChoices:[],priorityChoices:[],statuses:[]}
 const projection=records=>({calendar:fixture.calendar,gantt:{...fixture.gantt,records:fixture.gantt.records.map(original=>{
  const row=records.find(r=>r.taskCode===original.taskCode) || original
  const valid=!!row.start && !!row.end
  return {...original,...row,ganttScheduled:valid,ganttStartDay:valid?Math.round((Date.parse(row.start.slice(0,10)+'T12:00:00Z')-Date.parse(fixture.gantt.rangeStart+'T12:00:00Z'))/86400000):0,ganttDurationDays:valid?Math.round((Date.parse(row.end.slice(0,10)+'T12:00:00Z')-Date.parse(row.start.slice(0,10)+'T12:00:00Z'))/86400000)+1:0}
 })}})
 await page.route('**/admin/rpc',async route=>{
  const payload=route.request().postDataJSON();commands.push(payload);const [context,command,values]=payload.args
 let info={}
  if(command.endsWith('TaskScheduleCmd')){
   if(values.action==='projection')info=projection(values.records)
   else {const record=values.records.find(row=>row.taskCode===values.primary),start=new Date(Date.parse(values.range_start.slice(0,10)+'T12:00:00Z')+values.start_day*86400000),end=new Date(start.getTime()+(values.duration-1)*86400000);info={edits:{[record.taskCode]:{start:start.toISOString().slice(0,10)+' '+(record.start.slice(11)||'09:00:00'),end:end.toISOString().slice(0,10)+' '+(record.end.slice(11)||'18:00:00')}}}}
  }else if(command.endsWith('TaskWorkspaceEditCmd')){
   assert.equal(values.action,'prepare','Fixture never writes server data')
   info={plans:values.plans.map(plan=>({...plan,task:tasks.find(row=>row.__search_key__===plan.task_key),data:{},fields:['bid_start_date','bid_end_date','progress','description'].map(name=>({name,editable:true})),revision:'original-revision',statuses:[],users:catalog.users}))}
  }else if(command.endsWith('TaskWorkspaceCmd'))info=values.action==='catalog'?catalog:{tasks,parents,facets:{},loaded:tasks.length,total:tasks.length,hasMore:false}
  await route.fulfill({json:{result:{info}}})
 })
 await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/gantt-test')
 await page.waitForFunction(()=>!!window.manager?.$refs.dialog)
 await page.evaluate(({tasks,parents,catalog,fixture})=>{
  Object.assign(window.manager,{context:{ticket:'fixture',project:'cg'},opened:true,result:{tasks,parents,loaded:tasks.length,total:tasks.length,hasMore:false},catalog,parentRecords:Object.fromEntries(parents.map(p=>[p.__search_key__,p])),surface:'workspace',view:'gantt',group:'process',year:2026,month:10,projection:{calendar:fixture.calendar,gantt:fixture.gantt}})
 },{tasks,parents,catalog,fixture})
 const gantt=page.locator('#dock-tasks .task-gantt-view'),calendar=page.locator('#dock-task_calendar .task-calendar-view')
 await gantt.waitFor();await calendar.waitFor()
 const ready=()=>page.waitForFunction(()=>!window.manager.busy && !window.manager.projecting)
 await ready();assert.equal(await calendar.locator('.task-calendar-day').count(),42)
 await page.evaluate(()=>window.docks.maximize('tasks'))
 await page.waitForFunction(()=>window.manager.toolbarWidth>=800)
 const scopeMenu=page.locator('.task-manager-scope'),scopeTrigger=page.getByRole('button',{name:'Choose task scope',exact:true})
 assert.notEqual(await scopeTrigger.evaluate(node=>getComputedStyle(node).borderRadius),'50%','Text scope trigger must not stretch the circular icon shape into an ellipse')
 await scopeTrigger.click()
 await scopeMenu.getByRole('checkbox').first().waitFor()
 assert.equal(await scopeMenu.getByRole('checkbox').count(),5,'Scope uses direct choices, not a nested scope select')
 assert.equal(await scopeMenu.locator('select[aria-label="Task scope"]').count(),0)
 assert.equal(await scopeMenu.locator('[data-frame="menuIcon"]').count(),5)
 await scopeMenu.getByRole('checkbox',{name:'Project tasks',exact:true}).click();await ready()
 assert.equal(await page.evaluate(()=>window.manager.scope),'project')
 assert.equal(await scopeTrigger.locator('.app-icon').getAttribute('data-icon'),'workspaces')
 assert.equal(await scopeMenu.evaluate(node=>node.open),false,'Direct project choice closes the popup')
 await scopeTrigger.click()
 await scopeMenu.getByRole('checkbox',{name:'Project tasks',exact:true}).waitFor()
 await page.screenshot({path:output+'/stream-scope-menu.png',animations:'disabled'})
 await scopeMenu.getByRole('checkbox',{name:'My tasks',exact:true}).click();await ready()
 await scopeMenu.getByLabel('User',{exact:true}).waitFor()
 assert.equal(await page.evaluate(()=>window.manager.identity),'alice','User scope keeps the existing identity owner')
 await page.keyboard.press('Escape')
 await page.evaluate(()=>window.docks.maximize('tasks'))
 await ready()
 await page.locator('[data-frame="taskWorkspaceOverflowButton"]').click()
 const sort=page.getByLabel('Sort',{exact:true}),group=page.getByLabel('Group',{exact:true})
 for (const control of [sort,group]) {
  assert.equal(await control.locator('option .app-icon').count(),await control.locator('option').count(),'Every sort/group option retains its Handler icon')
  assert.ok(await control.locator('.app-select-selected-content .app-icon').count(),'Chosen value also shows its icon')
 }
 assert.equal(await sort.locator('.app-select-selected-content .app-icon').getAttribute('data-icon'),'schedule')
 await sort.selectOption('recent');await ready()
 assert.equal(await page.evaluate(()=>window.manager.sort),'recent')
 assert.equal(await sort.locator('.app-select-selected-content .app-icon').getAttribute('data-icon'),'history')
 await sort.selectOption('due');await ready()
 await sort.click()
 await page.screenshot({path:output+'/stream-sort-icons.png',animations:'disabled'})
 await page.keyboard.press('Escape')
 await page.keyboard.press('Escape')
 if(!await group.isVisible())await page.locator('[data-frame="taskWorkspaceOverflowButton"]').click()
 await group.click()
 await page.screenshot({path:output+'/stream-group-icons.png',animations:'disabled'})
 await page.keyboard.press('Escape')
 const title=gantt.locator('.task-gantt-title').first()
 assert.equal(await title.evaluate(node=>getComputedStyle(node).borderRadius),'0px','Task title has no rounded clip cutting the first letters')
 assert.ok(await title.locator('small').evaluate(node=>node.getBoundingClientRect().left>=node.parentElement.getBoundingClientRect().left),'Process text starts inside the rectangular title area')
 assert.equal(await gantt.locator('.task-gantt-bar').first().evaluate(node=>getComputedStyle(node).height),'27px')
 assert.equal(await gantt.locator('.task-gantt-row.gantt-task').first().evaluate(node=>getComputedStyle(node).height),'50px')
 const body=gantt.locator('.gantt-body'),bar=gantt.locator('[data-task-key="sthpw/task?id=1"] .task-gantt-move')
 assert(await body.evaluate(node=>node.scrollWidth>node.clientWidth),'TH base scale keeps a useful day width')
 const heading=gantt.locator('.gantt-heading-viewport'),head=await heading.boundingBox()
 await page.mouse.move(head.x+head.width/2,head.y+15)
 const before=await bar.boundingBox();await page.mouse.wheel(0,-100);await page.waitForTimeout(100)
 const after=await bar.boundingBox();assert(after.width>before.width,'Wheel zooms the timeline')
 const anchoredDay=await body.evaluate(node=>node.scrollLeft)+head.width/2
 assert(Math.abs(anchoredDay/((after.width+4)/6)-(head.width/2)/((before.width+4)/6))<.2,'Wheel keeps the day under the cursor')
 await page.keyboard.down('Shift');await page.mouse.wheel(0,200);await page.keyboard.up('Shift');await page.waitForTimeout(80)
 assert(await body.evaluate(node=>node.scrollLeft>0),'Shift-wheel pans')
 await body.evaluate(node=>node.scrollLeft=0)
 const drag=async(locator,dx)=>{await locator.scrollIntoViewIfNeeded();const box=await locator.boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+dx,box.y+box.height/2,{steps:6});await page.mouse.up();await ready()}
 await drag(bar,36)
 assert(await page.evaluate(()=>!!window.manager.drafts['sthpw/task?id=1']?.data.bid_start_date))
 assert.equal(await page.evaluate(()=>window.manager.drafts['sthpw/task?id=1'].task.description),'Keep this description')
 assert.equal(await page.evaluate(()=>window.manager.drafts['sthpw/task?id=1'].revision),'original-revision')
 await gantt.getByRole('button',{name:'Undo schedule change',exact:true}).click();await ready()
 assert.equal(await page.evaluate(()=>Object.keys(window.manager.drafts).length),0)
 await gantt.getByRole('button',{name:'Redo schedule change',exact:true}).click();await ready()
 const previous=await page.evaluate(()=>JSON.stringify(window.manager.drafts))
 const bounds=await bar.boundingBox();await page.mouse.move(bounds.x+bounds.width/2,bounds.y+13);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+55,bounds.y+13);await page.keyboard.press('Escape');await page.mouse.up()
 assert.equal(await page.evaluate(()=>JSON.stringify(window.manager.drafts)),previous,'Escape cancels a schedule gesture')
 await gantt.locator('[data-task-key="sthpw/task?id=1"]').hover()
 const progress=gantt.locator('[data-task-key="sthpw/task?id=1"] .gantt-progress-handle')
 await progress.focus();await progress.press('ArrowRight');await ready()
 assert.equal(await page.evaluate(()=>window.manager.drafts['sthpw/task?id=1'].data.progress),36)
 await gantt.getByRole('button',{name:'Undo schedule change',exact:true}).click();await ready()
 assert.equal(await page.evaluate(()=>window.manager.drafts['sthpw/task?id=1'].data.progress),undefined)
 await gantt.getByRole('button',{name:'Redo schedule change',exact:true}).click();await ready()
 await page.waitForFunction(()=>document.querySelector('[data-task-key="sthpw/task?id=1"] .gantt-progress-handle')?.getAttribute('aria-valuenow')==='36')
 await gantt.locator('[data-task-key="sthpw/task?id=1"]').hover();await drag(progress,18)
 assert((await page.evaluate(()=>window.manager.drafts['sthpw/task?id=1'].data.progress))>36,'Progress handle edits the common draft')
 await drag(gantt.locator('[data-task-key="sthpw/task?id=1"] .task-gantt-resize.end'),35)
 assert(await page.evaluate(()=>!!window.manager.drafts['sthpw/task?id=1'].data.bid_end_date))
 await drag(gantt.locator('[data-task-key="sthpw/task?id=1"] .task-gantt-resize.start'),-12)
 await body.evaluate(node=>node.scrollLeft=0)
 const empty=gantt.locator('[data-task-key="sthpw/task?id=4"] .task-gantt-timeline'),emptyBox=await empty.boundingBox()
 const viewportBox=await body.boundingBox(),visibleLeft=Math.max(emptyBox.x,viewportBox.x),visibleRight=Math.min(emptyBox.x+emptyBox.width,viewportBox.x+viewportBox.width),startX=Math.max(visibleLeft+10,Math.min(emptyBox.x+250,visibleRight-45)),startY=emptyBox.y+emptyBox.height/2
 assert.equal(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.closest('[data-task-key]')?.dataset.taskKey,{x:startX,y:startY}),'sthpw/task?id=4','The empty-timeline gesture must hit the visible row')
 await page.mouse.move(startX,startY);await page.mouse.down();await page.mouse.move(startX+30,startY,{steps:5});await page.mouse.up();await page.waitForFunction(()=>!!window.manager.drafts['sthpw/task?id=4']?.data.bid_start_date);await ready()
 assert(await page.evaluate(()=>!!window.manager.drafts['sthpw/task?id=4']?.data.bid_start_date),'Empty timeline creates a schedule in the same draft')
 // Calendar navigation and filtering belong to the same owner, without replacing Gantt.
 await calendar.locator('[data-date="2026-10-12"]').tap();await ready()
 assert.equal(await page.evaluate(()=>window.manager.filters.day),'2026-10-12');assert.equal(await gantt.isVisible(),true)
 assert(commands.some(command=>command.args[2]?.query?.filters?.day==='2026-10-12'))
 await calendar.getByRole('button',{name:'Clear selected day',exact:true}).tap();await ready()
 assert.equal(await page.evaluate(()=>window.manager.filters.day),'')
 await page.locator('[data-dock="task_calendar"] > header').getByRole('button',{name:'Float panel',exact:true}).count()
 await page.evaluate(()=>window.docks.show('task_calendar'))
 const saved=await page.evaluate(()=>window.docks.capture());assert(saved.panels.some(panel=>panel.panel_id==='task_calendar' && panel.visible))
 assert.equal(await page.locator('#dock-tasks .task-calendar-view').count(),0)
 for(const mode of ['light','dark'])for(const theme of ['md3','material5']){
  await page.evaluate(({mode,theme})=>Object.assign(window.appearance,{mode,theme}),{mode,theme})
  await page.screenshot({path:output+'/stream-'+mode+'-'+theme+'.png'})
 }
 await page.evaluate(()=>{
  const original=window.manager.projection.gantt.records[0]
  window.originalRecords=window.manager.projection.gantt.records
  window.manager.projection.gantt.records=Array.from({length:500},(_,i)=>({...original,taskCode:'virtual-'+i,groupFirst:false,ganttSectionFirst:i===0}))
 })
 assert(await gantt.locator('[data-task-key]').count()<40,'Only visible timeline rows mount')
 await body.evaluate(node=>node.scrollTop=18000);await page.waitForTimeout(70)
 assert(await gantt.locator('[data-task-key]').count()<40)
 assert(await gantt.locator('[data-task-key="virtual-360"]').count()>0)
 await page.evaluate(()=>window.manager.projection.gantt.records=window.originalRecords)
 await page.setViewportSize({width:360,height:800});await page.evaluate(()=>window.docks.show('task_calendar'));await page.waitForTimeout(80)
 assert.equal(await calendar.isVisible(),true)
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Calendar dock fits a phone')
 await calendar.getByRole('button',{name:'Agenda',exact:true}).tap();assert(await calendar.locator('.task-calendar-agenda').isVisible())
 await page.screenshot({path:output+'/stream-mobile.png'})
 assert.deepEqual(errors,[])
 console.log('PASS Gantt/calendar: shared owner and revisions, drag/cancel/resize/progress, undo/redo, zoom/pan, day filters, independent dock, saved layout, 500-row virtualization, themes and touch mobile')
}finally{if(browser){await browser.close();assert(!browser.isConnected())}if(server){await server.close();assert(!server.httpServer.listening)}}

