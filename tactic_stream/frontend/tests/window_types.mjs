import assert from 'node:assert/strict'
import { readFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root=fileURLToPath(new URL('..',import.meta.url))
const handler=await readFile(new URL('../../../../th_codex/thlib/ui/workspace_models/windows.py',import.meta.url),'utf8')
const pairs={
 'help':['help/HelpView','dialog'], 'messages':['messages/MessagesView','dialog'],
 'activity_feed':['activity/ActivityFeed','dialog'], 'notifications':['activity/SystemActivity','dialog'],
 'script_editor':['scripts/ScriptEditor','dialog'], 'script_shelf_editor':['scripts/ScriptShelf','dialog'],
 'debug_log':['debug/DebugLog','dialog'], 'ui_performance':['debug/UiPerformance','dialog'],
 'user_profile':['users/UserProfile','dialog'], 'duplicate_sobject':['objects/DuplicateSObject','dialog'],
 'ingest_files':['checkin/IngestFiles','dialog'], 'milestone_manager':['tasks/MilestonePanel','dialog'],
 'matching_templates':['checkin/DropPlate','templatesDialog'], 'naming_editor':['checkin/CommitQueue','namingDialog'],
 'project_wizard':['projects/ProjectCreation','dialog'], 'project_templates':['projects/ProjectTemplates','dialog'],
 'quick_filter_editor':['workspace/QuickFilterEditor','dialog'], 'process_dependencies':['administration/ProcessRules','dialog'],
 'schema_search_type':['administration/SchemaEditor','creationDialog'],
}
for(const [id,[path,ref]] of Object.entries(pairs)) {
 const spec=handler.match(new RegExp('FloatingWindow\\(\\s*"'+id+'"[\\s\\S]*?\\)'))?.[0]
 assert(spec,id)
 const source=await readFile(root+'/src/features/'+path+'.vue','utf8')
 const tag=source.match(new RegExp('<dialog\\b[^>]*ref="'+ref+'"[^>]*>'))?.[0]
 assert(tag,id)
 assert.equal(/type\s*:\s*['"]window['"]/.test(tag),!spec.includes('blocking=True'),id)
}
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,withDirectives,KeepAlive} from 'vue'
import App from '/src/App.vue'
import AppButton from '/src/controls/AppButton.vue'
import HelpView from '/src/features/help/HelpView.vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import Timesheet from '/src/features/objects/Timesheet.vue'
import ScriptShelf from '/src/features/scripts/ScriptShelf.vue'
import IngestFiles from '/src/features/checkin/IngestFiles.vue'
import SearchLibrary from '/src/features/workspace/SearchLibrary.vue'
import Configuration from '/src/features/configuration/Configuration.vue'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',mode:'dark',fadeAnimations:false,popupAnimations:false,clickAnimations:false});initializeAppearance()
createApp({provide:App.provide,data(){return {session:{ticket:'fixture',login:'alice'},workspaceView:{project:'cg'},workHoursProjects:{week:'',report:'',cost:''},shelfEntry:'tab_a',main:0,parent:0,guard:false,draft:'Original',configMounted:false}},
methods:{openWorkHours:App.methods.openWorkHours,openDock(id){if(['timesheet','work_reports','cost_reports'].includes(id))this.openWorkHours(id==='timesheet'?'week':id==='cost_reports'?'cost':'report')}},mounted(){window.host=this},
render(){const dialog=(ref,type,x,content)=>withDirectives(h('dialog',{ref,id:ref,class:'record-dialog fixture-window',style:'position:fixed;left:'+x+'px;top:60px;margin:0;width:460px;height:300px',onCancel:event=>{if(this.guard)event.preventDefault()}},[
 h('header',[h('h2',ref),h(AppButton,{label:'Close '+ref,icon:'close',onClick:()=>this.$refs[ref].close()})]),...content
]),[[windowDirective,{type}]]);
return h('div',{style:'height:100dvh;display:flex;flex-direction:column'},[
 h('div',{style:'height:45px;display:flex;gap:12px'},[h(AppButton,{label:'Main action',onClick:()=>this.main++}),h('output',{id:'main'},this.main)]),
 dialog('utility','window',40,[h('input',{id:'draft',value:this.draft,onInput:event=>this.draft=event.target.value})]),
 dialog('second','window',300,[h('p','Second tool')]),
 dialog('blocking','dialog',80,[h(AppButton,{label:'Parent action',onClick:()=>this.parent++}),h(AppButton,{label:'Parent help',onClick:()=>this.$refs.help.open('search')}),h('output',{id:'parent'},this.parent)]),
 h('dialog',{ref:'confirmation',id:'confirmation',class:'record-dialog'},[h('h2','Confirm'),h(AppButton,{label:'Cancel confirmation',onClick:()=>this.$refs.confirmation.close()})]),
 h(HelpView,{ref:'help'}),
 h(ScriptShelf,{ref:'shelf',ticket:'fixture',project:this.workspaceView.project,login:'alice',entryKey:this.shelfEntry,title:'Source tab',visible:false}),
 h(IngestFiles,{ref:'ingest',ticket:'fixture',project:this.workspaceView.project}),
 h(SearchLibrary,{ref:'library',ticket:'fixture',project:'cg',searchType:'cg/assets',scope:'cg/assets',records:[],canManage:true}),
 withDirectives(h('dialog',{ref:'configDialog',id:'configuration-window',class:'configuration-dialog'},[
  h(KeepAlive,()=>this.configMounted?h(Configuration,{ticket:'fixture',project:'cg',login:'alice',canAdminister:false,onClose:()=>{this.$refs.configDialog.close();this.configMounted=false}}):null)
 ]),[[windowDirective,{type:'window'}]]),
 withDirectives(h('dialog',{ref:'fullEditor',id:'full-editor',class:'configuration-dialog'},[
  h('header',[h('h2','Full editor'),h(AppButton,{label:'Close full editor',onClick:()=>this.$refs.fullEditor.close()})])
 ]),[[windowDirective]]),
 h('div',{style:'display:flex;flex:1;min-height:0;position:relative'},[h(DockWorkspace,{ref:'docks',ticket:'fixture',project:'cg',login:'window-types',canAdminister:true,onOpen:this.openDock})]),
 h(Timesheet,{ref:'timesheet',dockTarget:'#dock-timesheet',dockMode:'week',ticket:'fixture',project:this.workHoursProjects.week||'cg',currentUser:'alice',onOpened:()=>this.$refs.docks.show('timesheet'),onClosed:()=>this.$refs.docks.hide('timesheet'),onOpenDock:mode=>this.openWorkHours(mode,this.$refs.timesheet.task,this.workHoursProjects.week)}),
 h(Timesheet,{ref:'workReports',dockTarget:'#dock-work_reports',dockMode:'report',ticket:'fixture',project:this.workHoursProjects.report||'cg',currentUser:'alice',onOpened:()=>this.$refs.docks.show('work_reports'),onClosed:()=>this.$refs.docks.hide('work_reports'),onOpenDock:mode=>this.openWorkHours(mode,this.$refs.workReports.task,this.workHoursProjects.report)}),
 h(Timesheet,{ref:'costReports',dockTarget:'#dock-cost_reports',dockMode:'report',dockReport:'labor_cost',ticket:'fixture',project:this.workHoursProjects.cost||'cg',currentUser:'alice',onOpened:()=>this.$refs.docks.show('cost_reports'),onClosed:()=>this.$refs.docks.hide('cost_reports')})
])}}).directive('window',windowDirective).mount('#app')
</script></body></html>`
let server,browser;const deadline=setTimeout(()=>browser?.close(),55000)
const shelf={code:'shelf_a',personal:true,title:'My shelf',valid:true,configuration:{scope:'tab',entryKey:'tab_a',buttons:[{id:'button_a',script:'folder/demo',title:'Original',description:'',icon:'code'}]}}
const shelfCatalog={shelves:[shelf],scripts:[{path:'folder/demo',language:'python',canExecute:true}],canManage:true,canWrite:true,revision:'shelf-revision'}
try {
 server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/window-types',plugins:[vue(),{
  name:'window-types-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
   if(req.url!=='/window-types-test')return next()
   try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
  })},
 }],server:{host:'127.0.0.1',port:0,watch:null}});await server.listen()
 browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL || 'msedge'});const page=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true}),errors=[],commands=[],shelfWrites=[]
 page.setDefaultTimeout(8000);page.on('pageerror',error=>errors.push(error.message))
 await page.route('**/ui/help/**',async route=>{const name=new URL(route.request().url()).pathname.slice('/ui/help/'.length);await route.fulfill({body:await readFile(root+'/public/help/'+name),contentType:name.endsWith('.json')?'application/json':'text/plain; charset=utf-8'})})
 await page.route('**/admin/**',async route=>{
  const path=new URL(route.request().url()).pathname
  if(path==='/admin/search-configuration/settings')return route.fulfill({json:{result:{presets:[],columns:{name:{}},relations:[{value:'=',label:'Equal'}],revision:'fixture'}}})
  if(path==='/admin/script-shelf/read')return route.fulfill({json:{result:shelfCatalog}})
  if(path==='/admin/script-shelf/save'){
   const values=route.request().postDataJSON();shelfWrites.push(values)
   return route.fulfill({json:{result:{...shelfCatalog,savedCode:'shelf_a',shelves:[{...shelf,configuration:values.configuration}],revision:'new-shelf-revision'}}})
  }
  if(path==='/admin/rpc'){
   const payload=route.request().postDataJSON(),values=payload.args[2]
   if(payload.args[1].endsWith('RelatedIngestCmd'))return route.fulfill({json:{result:{info:{rules:[{code:'default',applicable:false}]}}}})
   commands.push(values)
   assert.equal(values.action,'read')
   return route.fulfill({json:{result:{info:{entries:[],rows:[],users:[],reports:[{value:'my_hours',label:'My Hours'},{value:'labor_cost',label:'Labor Cost'}],summary:{logged:0,approved:0,pending:0,overtime:0},week_start:'2026-10-12',week_end:'2026-10-18',total_hours:0,revision:'fixture'}}}})
  }
  await route.fulfill({json:{result:{presets:[],revision:'fixture'}}})
 })
 await page.goto(server.resolvedUrls.local[0]+'window-types-test');await page.waitForFunction(()=>!!window.host)
 await page.evaluate(()=>window.host.$refs.utility.show())
 const utility=page.locator('#utility'),help=page.locator('dialog.help-view')
 assert.equal(await utility.evaluate(el=>el.matches(':modal')),false)
 assert.equal(await utility.evaluate(el=>el.matches(':popover-open')),true)
 await page.getByRole('button',{name:'Main action',exact:true}).click();assert.equal(await page.locator('output#main').textContent(),'1')
 await page.locator('#draft').fill('Retained draft')
 await utility.getByRole('button',{name:'Minimize window',exact:true}).click()
 assert((await utility.boundingBox()).height<50)
 await page.getByRole('button',{name:'Main action',exact:true}).click()
 await page.evaluate(()=>window.host.$refs.utility.show())
 assert((await utility.boundingBox()).height>200);assert.equal(await page.locator('#draft').inputValue(),'Retained draft')
 await utility.getByRole('button',{name:'Maximize window',exact:true}).click();assert.equal(Math.round((await utility.boundingBox()).width),1280)
 await utility.getByRole('button',{name:'Restore window',exact:true}).click();assert((await utility.boundingBox()).width<600)
 const before=await utility.boundingBox(),title=utility.locator('header')
 await title.focus();await page.keyboard.press('Alt+ArrowRight');assert((await utility.boundingBox()).x>before.x)
 await page.evaluate(()=>window.host.$refs.second.show())
 await page.evaluate(()=>window.host.$refs.utility.show())
 assert.equal(await page.evaluate(()=>document.elementFromPoint(350,90).closest('dialog').id),'utility')
 await page.evaluate(()=>{window.host.$refs.second.close();window.host.$refs.utility.close();window.host.$refs.blocking.showModal()})
 const blocking=page.locator('#blocking');assert.equal(await blocking.evaluate(el=>el.matches(':modal')),true)
 await blocking.getByRole('button',{name:'Parent help',exact:true}).click()
 await help.locator('[data-frame="helpTopic_search"][aria-pressed="true"]').waitFor({state:'attached'})
 assert.equal(await help.evaluate(el=>el.matches(':modal')),false)
 assert.equal(await help.evaluate(el=>el.parentElement.id),'blocking')
 await help.getByRole('button',{name:'Close help',exact:true}).click()
 await blocking.getByRole('button',{name:'Parent action',exact:true}).click();assert.equal(await page.locator('output#parent').textContent(),'1')
 await page.evaluate(()=>window.host.guard=true);await blocking.locator('header').focus();await page.keyboard.press('Escape');assert(await blocking.evaluate(el=>el.open))
 await page.evaluate(()=>{window.host.guard=false;window.host.$refs.help.open('overview')})
 await help.waitFor();await page.evaluate(()=>window.host.$refs.blocking.close())
 await page.waitForFunction(()=>!document.querySelector('dialog.help-view').open)
 assert.equal(await help.evaluate(el=>el.parentElement.tagName),'BODY')
 await page.evaluate(()=>window.host.$refs.confirmation.showModal())
 assert.equal(await page.locator('#confirmation .app-window-controls').count(),0)
 await page.getByRole('button',{name:'Cancel confirmation',exact:true}).click()
 await page.evaluate(()=>window.host.$refs.library.open())
 const library=page.locator('.search-library-dialog'),libraryHeader=library.locator('.search-library-shell > header')
 assert((await library.boundingBox()).width<1200 && (await library.boundingBox()).x>0,'Saved searches opens as a bounded dialog')
 assert.equal(await library.evaluate(el=>getComputedStyle(el).borderStyle),'solid')
 assert(await library.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Saved searches has rounded corners')
 await libraryHeader.focus();assert.equal(await libraryHeader.evaluate(el=>getComputedStyle(el).outlineStyle),'none')
 await page.keyboard.press('Alt+ArrowRight')
 await library.getByRole('button',{name:'Maximize window',exact:true}).click()
 assert.equal(Math.round((await library.boundingBox()).width),1280)
 await library.getByRole('button',{name:'Restore window',exact:true}).click()
 assert(await library.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Restore keeps the frame rounded')
 await library.getByRole('button',{name:'Add filter',exact:true}).click()
 await library.getByLabel('Filter value',{exact:true}).fill('Retained filter draft')
 await libraryHeader.getByRole('button',{name:'Close',exact:true}).click()
 assert(await library.evaluate(el=>el.open),'Closing still protects the filter draft')
 await library.getByRole('button',{name:'Keep editing',exact:true}).click()
 assert.equal(await library.getByLabel('Filter value',{exact:true}).inputValue(),'Retained filter draft')
 await mkdir(root+'/../.screenshots/window-types-current',{recursive:true})
 await libraryHeader.focus();await library.screenshot({path:root+'/../.screenshots/window-types-current/saved-searches-rounded.png'})
 await library.getByRole('button',{name:'Cancel',exact:true}).click()
 await library.getByRole('button',{name:'Discard changes',exact:true}).click()
 await page.evaluate(()=>window.host.$refs.fullEditor.showModal())
 const fullEditor=page.locator('#full-editor')
 assert(await fullEditor.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Maximized desktop editors also keep rounded corners')
 await fullEditor.getByRole('button',{name:'Restore window',exact:true}).click()
 assert(await fullEditor.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'All restored configuration editors get a frame')
 await fullEditor.locator('header').focus();assert.equal(await fullEditor.locator('header').evaluate(el=>getComputedStyle(el).outlineStyle),'none')
 await fullEditor.getByRole('button',{name:'Close full editor',exact:true}).click()
 await page.setViewportSize({width:320,height:760});await page.evaluate(()=>window.host.$refs.library.open())
 assert(await library.evaluate(el=>el.scrollWidth<=el.clientWidth),'Saved searches fits a phone')
 await library.getByRole('button',{name:'Cancel',exact:true}).click();await page.setViewportSize({width:1280,height:900})
 await page.evaluate(async()=>{window.host.configMounted=true;await window.host.$nextTick();window.host.$refs.configDialog.show()})
 const config=page.locator('#configuration-window'),configHeader=config.locator('[data-frame=configurationHeader]')
 await config.getByRole('button',{name:'Restore window',exact:true}).waitFor()
 assert(await config.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Configuration opens rounded in its initial maximized state')
 assert.equal(await configHeader.getByRole('button',{name:'Cancel',exact:true}).count(),0)
 await configHeader.getByRole('button',{name:'Close',exact:true}).hover()
 await page.getByRole('tooltip').filter({hasText:/^Close$/}).waitFor()
 await config.getByRole('button',{name:'Check-in Options',exact:true}).click()
 await config.getByLabel('Result limit',{exact:true}).fill('37')
 await configHeader.getByRole('button',{name:'Close',exact:true}).click()
 const unsaved=page.getByRole('dialog',{name:'Unsaved changes',exact:true})
 await unsaved.getByRole('button',{name:'Continue editing',exact:true}).click()
 assert.equal(await config.getByLabel('Result limit',{exact:true}).inputValue(),'37')
 await config.getByRole('button',{name:'Restore window',exact:true}).click()
 assert(await config.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Configuration restores rounded')
 await config.getByRole('button',{name:'Maximize window',exact:true}).click()
 assert(await config.evaluate(el=>parseFloat(getComputedStyle(el).borderRadius)>0),'Configuration maximizes rounded again')
 await config.screenshot({path:root+'/../.screenshots/window-types-current/configuration-rounded.png'})
 await configHeader.getByRole('button',{name:'Close',exact:true}).click()
 await unsaved.getByRole('button',{name:'Discard changes',exact:true}).click()
 assert.equal(await config.evaluate(el=>el.open),false,'Close retains the discard guard')
 await page.evaluate(()=>window.host.openWorkHours('week',null,'other'))
 const timesheet=page.locator('#dock-timesheet .time-entry-panel')
 await timesheet.waitFor();assert.equal(await timesheet.evaluate(el=>el.tagName),'SECTION')
 assert.equal(await page.locator('dialog:modal').count(),0)
 assert.equal(await page.evaluate(()=>window.host.$refs.timesheet.context.project),'other')
 await timesheet.getByRole('button',{name:'Open work reports',exact:true}).click()
 const report=page.locator('#dock-work_reports .time-entry-panel');await report.waitFor()
 assert.equal(await report.evaluate(el=>el.tagName),'SECTION')
 assert.equal(await page.evaluate(()=>window.host.$refs.workReports.mode),'report')
 assert.equal(await page.evaluate(()=>window.host.$refs.timesheet.mode),'week')
 await report.getByRole('combobox',{name:'Report',exact:true}).selectOption('labor_cost')
 const cost=page.locator('#dock-cost_reports .time-entry-panel');await cost.waitFor()
 assert.equal(await cost.evaluate(el=>el.tagName),'SECTION')
 assert.equal(await page.evaluate(()=>window.host.$refs.costReports.report),'labor_cost')
 assert.equal(await page.evaluate(()=>window.host.$refs.workReports.report),'my_hours')
 const layout=await page.evaluate(()=>window.host.$refs.docks.capture())
 const stack=JSON.stringify(layout.layout)
 assert(stack.includes('timesheet')&&stack.includes('work_reports')&&stack.includes('cost_reports'))
 await page.evaluate(()=>{window.host.$refs.timesheet.draft={description:'Draft in dock'};window.host.$refs.docks.hide('timesheet');window.host.$refs.docks.show('timesheet')})
 assert.equal(await page.evaluate(()=>window.host.$refs.timesheet.draft.description),'Draft in dock')
 await page.evaluate(()=>window.host.openWorkHours('week',null,'cg'))
 assert.equal(await page.evaluate(()=>window.host.$refs.timesheet.context.project),'other')
 assert.equal(await page.evaluate(()=>window.host.$refs.timesheet.draft.description),'Draft in dock')
 await page.getByLabel('Panel position: Timesheet',{exact:true}).click()
 await page.getByRole('button',{name:'Float panel',exact:true}).click()
 assert.equal(await timesheet.evaluate(el=>el.tagName),'SECTION')
 await page.evaluate(()=>window.host.$refs.help.open('overview'))
 await help.locator('article .markdown-text').first().waitFor()
 const output=root+'/../.screenshots/window-types-current';await mkdir(output,{recursive:true});await page.screenshot({path:output+'/ts-modeless-help.png'})
 await help.getByRole('button',{name:'Close help',exact:true}).click()
 await page.setViewportSize({width:320,height:700});await page.evaluate(()=>window.host.$refs.help.open('overview'))
 await help.waitFor();assert((await help.boundingBox()).width<=320)
 await help.getByRole('button',{name:'Back',exact:true}).tap();assert.equal(await help.evaluate(el=>el.open),false)
 await page.setViewportSize({width:1280,height:900})
 await page.evaluate(()=>window.host.$refs.shelf.open())
 const shelfDialog=page.locator('dialog.script-shelf-dialog')
 await shelfDialog.getByRole('textbox',{name:'Button label',exact:true}).fill('Edited in source tab')
 await page.evaluate(()=>window.host.shelfEntry='tab_b')
 await shelfDialog.getByRole('button',{name:'Save shelf',exact:true}).click()
 await page.waitForFunction(()=>document.querySelector('dialog.script-shelf-dialog').getAttribute('aria-busy')!=='true')
 assert.equal(shelfWrites.length,1);assert.equal(shelfWrites[0].configuration.entryKey,'tab_a')
 assert.equal(shelfWrites[0].revision,'shelf-revision')
 await shelfDialog.getByRole('textbox',{name:'Button label',exact:true}).fill('Retained after project switch')
 await page.evaluate(()=>window.host.workspaceView.project='other')
 await page.evaluate(()=>window.host.$refs.shelf.open())
 assert.equal(await shelfDialog.getByRole('textbox',{name:'Button label',exact:true}).inputValue(),'Retained after project switch')
 assert.equal(await page.evaluate(()=>window.host.$refs.shelf.canLeave()),false)
 const shelfConfirmation=page.locator('dialog.script-shelf-confirm')
 await shelfConfirmation.getByRole('button',{name:'Cancel',exact:true}).click()
 assert.equal(shelfWrites.length,1)
 await shelfDialog.getByRole('button',{name:'Close script shelf',exact:true}).click()
 await shelfConfirmation.getByRole('button',{name:'Discard',exact:true}).click()
 await page.evaluate(async()=>{
  await window.host.$refs.ingest.open({__search_key__:'other/assets?id=1',name:'Captured parent'},{search_type:'other/files',title:'Files',path:'files'})
  window.host.$refs.ingest.addFiles([new File(['draft'],'retained.txt',{type:'text/plain'})])
  window.host.workspaceView.project='cg'
 })
 assert.equal(await page.evaluate(()=>window.host.$refs.ingest.files[0].file.name),'retained.txt')
 assert.equal(await page.evaluate(()=>window.host.$refs.ingest.scope.project),'other')
 await page.evaluate(()=>window.host.$refs.ingest.open({__search_key__:'cg/assets?id=2',name:'New parent'},{search_type:'cg/files'}))
 assert.equal(await page.evaluate(()=>window.host.$refs.ingest.parent.name),'Captured parent')
 assert.equal(await page.evaluate(()=>window.host.$refs.ingest.files.length),1)
 assert(commands.some(values=>values.mode==='week')&&commands.some(values=>values.mode==='report'))
 assert.deepEqual(errors,[])
 console.log('Window types: '+Object.keys(pairs).length+' Handler mappings; modeless workspace, owned Help, stacking, modal/dirty guards, rounded saved searches/Configuration/maximized editors, guarded Configuration Close, retained window controls, no title focus ring, minimize/restore/maximize/move, separate timesheet/report docks and mobile Back passed.')
}finally{clearTimeout(deadline);await browser?.close();await server?.close()}
