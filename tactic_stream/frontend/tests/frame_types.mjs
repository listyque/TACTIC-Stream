import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
import {surface,compareSurface} from './frame_capture.mjs'
const repo=fileURLToPath(new URL('../../',import.meta.url)),out=repo+'tools/frame_types/output/'
const native=JSON.parse(await readFile(out+'qml.json','utf8')),catalog=JSON.parse(await readFile(out+'catalog.json','utf8')),cases=JSON.parse(await readFile(repo+'tools/frame_types/cases.json','utf8'))
for(const [name,hash] of Object.entries(native.sha256))assert.equal(createHash('sha256').update(await readFile(repo+'src/tactic_stream/shared_ui/'+name)).digest('hex'),hash,'stale native capture: '+name)
for(const [name,hash] of Object.entries(native.nativeSources))assert.equal(createHash('sha256').update(await readFile('D:/code/th_codex/'+name)).digest('hex'),hash,'stale native renderer: '+name)
const server=await createServer({root:repo,configFile:false,resolve:{alias:{vue:repo+'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},plugins:[vue()],logLevel:'warn',server:{host:'127.0.0.1',port:0,watch:{ignored:['**/.tmp/**','**/.venv/**','**/.standalone*/**','**/output/**']}}})
await server.listen()
const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
let rectangles=0,styles=0,interiors=0
const samples=[]
try{
 for(const {mode,language,width,height} of [...new Map(native.captures.map(s=>[[s.mode,s.language,s.width,s.height].join(':'),s])).values()]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.route('**/admin/rpc',route=>{const body=route.request().postDataJSON();assert.equal(body.method,'execute_cmd');const action=body.args[2].action;assert(['list','load'].includes(action),'paired capture never writes');return route.fulfill({json:{result:{info:action==='list'?{catalog:catalog.catalog,canWrite:true}:structuredClone(catalog)}}})})
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/tools/frame_types/index.html?mode='+mode+'&language='+language)
  await page.waitForFunction(()=>window.frameAdmin?.screen.value?.document&&!window.frameAdmin.screen.value.busy);await page.evaluate(()=>document.fonts.ready)
  await page.waitForFunction(()=>window.frameAdmin.screen.value.viewport.width>100)
  for(const c of cases){
   for(const action of c.actions){
    if(action.type==='state')await page.evaluate(value=>{const s=window.frameAdmin.screen.value;s.canWrite=value!=='readonly';s.uncertain=value==='uncertain';s.busy=value==='busy'},action.value)
    else{
     const el=page.locator('section.search-types-editor [data-frame="'+action.id+'"]')
     if(action.type==='page'){const button=page.locator('[data-frame="'+action.selector+'_'+action.value+'"]');if(await button.count())await button.click();else await page.locator('[data-frame="'+action.selector+'"]').selectOption(action.value)}
     else if(action.type==='reveal')await page.locator('[data-frame="'+action.viewport+'"]').evaluate((view,id)=>{const el=view.querySelector('[data-frame="'+id+'"]');view.scrollTop+=el.getBoundingClientRect().top-view.getBoundingClientRect().top-12},action.id)
     else if(action.type==='text')await el.fill(action.value)
     else if(action.type==='choose')await el.selectOption(action.value)
     else{const b=await el.boundingBox();assert(b,action.id);await page.mouse.click(b.x+b.width/2,b.y+b.height/2)}
    }
    if(action.type!=='state'||action.value!=='busy')await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy)
   }
   await page.evaluate(()=>document.activeElement.blur());await page.mouse.move(width-1,height-1);await page.waitForTimeout(35)
   const actual=await page.evaluate(()=>{const s=window.frameAdmin.screen.value,document={};for(const key of ['title','description','color','columns','hasPipeline'])if(s.document?.[key]!==undefined)document[key]=s.document[key];document.removedColumns=s.document?.removedColumns||[];return JSON.parse(JSON.stringify({scene:{toolbar:s.toolbarScene,body:s.frameScene},state:{ui:s.ui,dirty:!!s.dirty,identity:s.identity,document}}))})
   const label=[mode,language,width,c.phase].join(' '),reference=native.captures.find(s=>s.mode===mode&&s.language===language&&s.width===width&&s.phase===c.phase)
   assert.deepEqual(errors,[],label+' runtime errors');assert.deepEqual(actual.state,reference.state,label+' state');assert.deepEqual(actual.scene,reference.scene,label+' graph')
   const counts=await compareSurface(page,'section.search-types-editor',await surface(page,'section.search-types-editor'),reference,label)
   rectangles+=counts.rectangles;styles+=counts.styles;interiors+=counts.interiors
   const image='types-vue-'+mode+'-'+language+'-'+width+'-'+c.phase+'.png';await page.screenshot({path:out+image,animations:'disabled'});samples.push({mode,language,width,height,phase:c.phase,image})
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,'no page overflow')
  }
  await page.close()
 }
 await writeFile(out+'vue.json',JSON.stringify({rectangles,styles,interiors,captures:samples},null,2));console.log(JSON.stringify({pairs:samples.length,rectangles,styles,interiors}))
}finally{await browser.close();await server.close()}
