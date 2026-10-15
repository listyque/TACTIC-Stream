import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url)), output = fileURLToPath(new URL('../../.screenshots/quick-filters-current/', import.meta.url))
const option = (key, title = key, accent) => ({ key, title, ...(accent ? { accent, showAccentMarker: true } : {}) })
const groups = [
 { key: 'column:category', title: 'Category', source: 'column', accent: '#607d8b', options: ['Characters','Props','Environment'].map(value => option(value)) },
 { key: 'process', title: 'PROCESSES', source: 'task', accent: '#607d8b', options: [option('publish','Publish','#28a96b'), option('storyboard','Storyboard','#b54f3e')] },
 { key: 'status', title: 'STATUSES', source: 'task', accent: '#607d8b', options: [option('Assigned','Assigned','#8a6d3b'), option('In Progress','In Progress','#3f7fc4')] },
 { key: 'assigned', title: 'ASSIGNED TO', source: 'task', accent: '#607d8b', options: [option('__current_login__','MY TASKS'),option('artist')] },
 { key: 'column:hidden', title: 'Server hidden group', source: 'column', options: [option('secret')] },
]
const standard = { groups: [{key:'column:hidden',enabled:false}], defaultSelections:{'column:category':['Props']} }
const catalog = { groups, configuration: standard, revision:'fixture', columns:{}, presets:[] }
const users = [{ login:'alice',displayName:'Alice',initials:'AL' },{login:'artist',displayName:'Artist',initials:'AR',primaryGroup:'Artists'}, {login:'lead',displayName:'Lead',initials:'LE',primaryGroup:'Artists'}]
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,toRaw} from 'vue'
import App from '/src/App.vue'
import SearchQuickFilters from '/src/features/workspace/SearchQuickFilters.vue'
import QuickFilterEditor from '/src/features/workspace/QuickFilterEditor.vue'
import FieldFilter from '/src/features/workspace/FieldFilter.vue'
import {searchConfiguration} from '/src/api.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import {windowDirective} from '/src/controls/window.js'
import '/src/theme.css';import '/src/style.css'
Object.assign(appearance,{mode:'dark',popupAnimations:true});initializeAppearance();window.appearance=appearance
createApp({
 data:()=>({quickSelections:{},quickLayout:null,page:4,queries:[],type:'demo/asset',tab:'one',overlay:false,canManage:false,filterField:'name',filterValue:'',showRetired:false,
 searchText:'hero',selectedTags:['cg'],filterRecords:[{column:'code',value:'A'}]}),
 mounted(){window.host=this},
 methods:{applyQuickFilters:App.methods.applyQuickFilters,loadRows(){this.queries.push({selections:structuredClone(toRaw(this.quickSelections)),page:this.page});return searchConfiguration('query','fixture','demo',this.type,{selections:this.quickSelections})}},
 render(){return h('main',{class:'workspace-browser',style:'height:100dvh;padding:24px;position:relative'},[
 h('header',{class:'search-header',style:'display:flex;justify-content:flex-end'},[
 h(SearchQuickFilters,{ref:'filters',ticket:'fixture',project:'demo',searchType:this.type,tabId:this.tab,scope:this.type,login:'alice',overlay:this.overlay,selections:this.quickSelections,layout:this.quickLayout,
 onApply:this.applyQuickFilters,onReset:values=>{this.quickLayout=null;this.quickSelections=values;this.page=0;this.loadRows()},onEdit:catalog=>this.$refs.editor.open(catalog)},
 {default:({close})=>h('details',{class:'quick-filter-field'},[h('summary','Filter by field'),h(FieldFilter,{columns:['name','code'],field:this.filterField,value:this.filterValue,retired:this.showRetired,
 'onUpdate:field':value=>this.filterField=value,'onUpdate:value':value=>this.filterValue=value,'onUpdate:retired':value=>this.showRetired=value,onApply:close})])})]),
 h(QuickFilterEditor,{ref:'editor',ticket:'fixture',project:'demo',searchType:this.type,tabId:this.tab,scope:this.type,selections:this.quickSelections,layout:this.quickLayout,canManage:this.canManage,onApply:this.applyQuickFilters})])}
}).directive('window',windowDirective).mount('#app')
</script></body></html>`
let server,browser,current=catalog,fail=false,held,resolveHeld,hold=false,stage='initial'
const deadline=setTimeout(()=>{console.error('Fixture deadline at: '+stage);browser?.close()},45000)
const calls=[],errors=[]
try{
 await mkdir(output,{recursive:true})
 server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/quick-filter-popup',plugins:[vue(),{name:'quick-filter-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(req.url!=='/quick-test')return next()
  try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
 })}}],server:{host:'127.0.0.1',port:0,watch:null}});await server.listen()
 browser=await chromium.launch({headless:true})
 const page=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true});page.setDefaultTimeout(10000)
 page.on('pageerror',error=>errors.push(error.message))
 await page.route('**/admin/search-configuration/**',route=>{
  const action=route.request().url().split('/').at(-1),payload=route.request().postDataJSON();calls.push({action,payload})
  if(action==='read'&&hold){held=route;resolveHeld();return}
  if(action==='read'&&fail)return route.fulfill({status:500,json:{error:'Facets unavailable'}})
  return route.fulfill({json:{result:action==='query'?{records:[]}:current}})
 })
 await page.route('**/admin/user-profile/read',route=>route.fulfill({json:{result:{users}}}))
 await page.goto(server.resolvedUrls.local[0]+'quick-test');await page.waitForFunction(()=>window.host)
 const cloud=page.locator('.search-quick-filters'),panel=cloud.locator('.account-panel'),viewport=cloud.locator('.quick-filter-viewport')
 const open=async()=>{await page.evaluate(()=>window.host.$refs.filters.open());await page.waitForFunction(()=>!!window.host.$refs.filters.catalog&&!window.host.$refs.filters.busy);await cloud.getByRole('button',{name:'Props',exact:true}).waitFor()}
 const group=name=>cloud.getByRole('region',{name,exact:true})
 const chip=(name,text)=>group(name).getByRole('button',{name:text,exact:true})
 await open()
 stage='selection'
 assert.equal(await cloud.getByText('Server hidden group').count(),0)
 assert(await chip('Category','ALL').getAttribute('aria-pressed')==='true')
 assert(await chip('PROCESSES','Publish').locator('.quick-filter-accent').count()===1)
 assert.equal(await chip('Category','Props').evaluate(el=>getComputedStyle(el).borderTopWidth),'1px')
 await panel.screenshot({path:output+'/ts-quick-filters.png',animations:'disabled'})
 assert(await cloud.locator('.tag-label').evaluateAll(nodes=>nodes.every(node=>node.scrollWidth<=node.clientWidth)),'Short chip names fit with markers and icons')
 await chip('Category','Props').click();await chip('Category','Characters').click();await chip('PROCESSES','Publish').click()
 await page.waitForFunction(()=>window.host.queries.length===3)
 assert.equal(await cloud.locator('.action-count').innerText(),'3')
 assert.equal(await cloud.locator('summary').first().getAttribute('aria-expanded'),'true')
 assert.deepEqual(await page.evaluate(()=>({search:window.host.searchText,tags:window.host.selectedTags,records:window.host.filterRecords})),{search:'hero',tags:['cg'],records:[{column:'code',value:'A'}]})
 assert(calls.filter(call=>call.action==='query').every(call=>call.payload.selections))
 await chip('Category','ALL').click();assert.equal(await cloud.locator('.action-count').innerText(),'1')
 await cloud.getByRole('button',{name:'Apply the shared default to this tab',exact:true}).click()
 assert.deepEqual(await page.evaluate(()=>window.host.quickSelections),{'column:category':['Props']})
 assert.equal(await cloud.getByRole('button',{name:'Apply the shared default to this tab',exact:true}).count(),0)
 await cloud.getByRole('button',{name:'Clear quick filters',exact:true}).click()
 await viewport.evaluate(el=>el.scrollTop=el.scrollHeight)
 await chip('ASSIGNED TO','MY TASKS').click();await chip('ASSIGNED TO','SELECT USERS').click()
 stage='assignees'
 const assignees=page.locator('.quick-filter-assignees .account-panel')
 await assignees.getByRole('checkbox',{name:'Artist',exact:true}).waitFor()
 assert(await assignees.getByRole('checkbox',{name:'Alice',exact:true}).isDisabled())
 await assignees.getByRole('checkbox',{name:'Artist',exact:true}).click()
 assert.deepEqual(await page.evaluate(()=>window.host.quickSelections.assigned),['artist','__current_login__'])
 await assignees.getByRole('checkbox',{name:'Lead',exact:true}).tap()
 await assignees.screenshot({path:output+'/ts-assignees.png',animations:'disabled'})
 stage='return from assignees'
 await page.keyboard.press('Escape');await open();await viewport.evaluate(el=>el.scrollTop=el.scrollHeight)
 assert.equal(await chip('ASSIGNED TO','USERS / 2').getAttribute('aria-pressed'),'true')
 const reads=calls.filter(call=>call.action==='read').length
 await cloud.getByRole('button',{name:'Edit',exact:true}).click()
 stage='editor'
 const editor=page.locator('.quick-filter-editor-dialog[open]');await editor.waitFor()
 assert.equal(calls.filter(call=>call.action==='read').length,reads,'Edit reuses the current catalog')
 assert.equal(await editor.getByText('Server hidden group').count(),0,'Ordinary editor cannot reveal server-hidden groups')
 await editor.getByRole('button',{name:'Close',exact:true}).click()
 stage='many'
 await open();assert.equal(calls.filter(call=>call.action==='read').length,reads,'Reopening does not reread facets')
 await cloud.getByText('Filter by field',{exact:true}).click()
 await cloud.getByRole('combobox',{name:'Filter field',exact:true}).selectOption('code')
 await cloud.getByLabel('Filter value',{exact:true}).fill('AB')
 await cloud.getByRole('button',{name:'Apply filters',exact:true}).click()
 await page.waitForFunction(()=>!window.host.$refs.filters.$refs.menu.open)
 assert.equal(await page.evaluate(()=>window.host.filterValue),'AB','The additional field filter remains available')
 await open()
 await page.evaluate(()=>{window.host.quickSelections={'column:removed':['stale']};window.host.quickLayout=null})
 await viewport.evaluate(el=>el.scrollTop=el.scrollHeight)
 await cloud.getByRole('button',{name:'stale',exact:true}).click()
 assert.deepEqual(await page.evaluate(()=>window.host.quickSelections),{},'A selection absent from the current catalog can still be removed')
 await page.evaluate(()=>window.host.$refs.filters.close())
 await page.evaluate(()=>{window.host.tab='many';window.host.quickSelections={};window.host.quickLayout=null})
 current={...catalog,groups:Array.from({length:20},(_,g)=>({key:'column:facet'+g,title:'Facet '+g,source:'column',options:Array.from({length:64},(_,n)=>option('value-'+g+'-'+n))})),configuration:{groups:[],defaultSelections:{}}}
 const longTitle='Long categorical option '.repeat(12);current.groups[0].options[1].title=longTitle
 await page.evaluate(()=>window.host.$refs.filters.open());await page.waitForFunction(()=>window.host.$refs.filters.groups.length===20&&!window.host.$refs.filters.busy)
 await cloud.getByRole('button',{name:'value-0-0',exact:true}).waitFor()
 assert((await cloud.getByRole('button',{name:longTitle,exact:true}).boundingBox()).width>260,'Quick options use the full row width from Handler, while tags keep their 260px cap')
 assert(await cloud.locator('[data-option-index]').count()<100,'Only visible chip rows are instantiated')
 await cloud.getByRole('button',{name:'Edit',exact:true}).press('Tab')
 for(let i=0;i<80;i++)await page.keyboard.press('Tab')
 assert(await viewport.evaluate(el=>el.scrollTop>0),'Keyboard scrolls into unmounted rows')
 const active=await page.evaluate(()=>document.activeElement.getAttribute('data-option-index'))
 await page.keyboard.press('Shift+Tab');assert.notEqual(await page.evaluate(()=>document.activeElement.getAttribute('data-option-index')),active)
 await viewport.evaluate(el=>el.scrollTop=el.scrollHeight)
 await cloud.getByRole('button',{name:'value-19-63',exact:true}).waitFor()
 assert(await viewport.evaluate(el=>el.scrollWidth<=el.clientWidth))
 await cloud.getByRole('button',{name:'value-19-63',exact:true}).click()
 assert.deepEqual(await page.evaluate(()=>window.host.quickSelections),{'column:facet19':['value-19-63']})
 const started=new Promise(resolve=>resolveHeld=resolve);hold=true
 await page.evaluate(()=>{window.host.$refs.filters.load(true)});let timeout
 await Promise.race([started,new Promise((_,reject)=>timeout=setTimeout(()=>reject(new Error('Catalog request missing')),10000))]).finally(()=>clearTimeout(timeout))
 await page.evaluate(()=>window.host.tab='other');await held.fulfill({json:{result:current}});hold=false
 await page.waitForFunction(()=>document.querySelector('.search-quick-filters summary')?.getAttribute('aria-expanded')==='false')
 assert.equal(await cloud.locator('summary').first().getAttribute('aria-expanded'),'false')
 current=catalog;fail=true;await page.evaluate(()=>window.host.$refs.filters.open());await cloud.getByText('Facets unavailable',{exact:true}).waitFor()
 fail=false;await cloud.getByRole('button',{name:'Retry',exact:true}).click();await page.waitForFunction(()=>!!window.host.$refs.filters.catalog&&!window.host.$refs.filters.busy)
 await page.evaluate(()=>window.appearance.language='ru');await cloud.getByText('БЫСТРЫЕ ФИЛЬТРЫ',{exact:true}).waitFor()
 await panel.screenshot({path:output+'/ts-quick-filters-ru.png',animations:'disabled'})
 await page.evaluate(()=>window.appearance.language='en')
 const editorStarted=new Promise(resolve=>resolveHeld=resolve);hold=true
 await page.evaluate(()=>{window.host.$refs.filters.close();window.host.$refs.editor.open()})
 let editorTimeout
 await Promise.race([editorStarted,new Promise((_,reject)=>editorTimeout=setTimeout(()=>reject(new Error('Editor request missing')),10000))]).finally(()=>clearTimeout(editorTimeout))
 await page.evaluate(()=>window.host.tab='editor-changed')
 await held.fulfill({json:{result:catalog}});hold=false
 await page.waitForFunction(()=>!window.host.$refs.editor.busy)
 const queriesBefore=await page.evaluate(()=>window.host.queries.length)
 await page.evaluate(()=>window.host.$refs.editor.apply())
 assert.equal(await page.evaluate(()=>window.host.queries.length),queriesBefore,'A late editor response cannot apply to a different tab')
 assert.equal(await page.evaluate(()=>window.host.$refs.editor.catalog),null)
 await page.evaluate(()=>window.host.$refs.editor.$refs.dialog.close())
 await page.evaluate(()=>window.host.$refs.filters.close());await page.setViewportSize({width:320,height:480})
 await page.evaluate(()=>window.host.overlay=true);await open()
 const box=await panel.boundingBox();assert(box.x>=0&&box.x+box.width<=320&&box.y+box.height<=480)
 await chip('Category','Props').tap();await viewport.evaluate(el=>el.scrollTop=el.scrollHeight)
 await panel.screenshot({path:output+'/ts-quick-filters-mobile.png',animations:'disabled'})
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
 for(const theme of ['material5','fluent','md3']){
  await page.evaluate(theme=>window.appearance.theme=theme,theme)
  assert((await panel.boundingBox()).height<=400)
  assert(await viewport.evaluate(el=>el.scrollWidth<=el.clientWidth))
 }
 assert.deepEqual(errors,[])
 console.log('Quick filters: groups, immediate tab query, reset/defaults, shared user picker/editor, cache/stale guards, virtual rows, keyboard, RU and mobile touch PASS')
}finally{clearTimeout(deadline);await browser?.close();await server?.close()}
