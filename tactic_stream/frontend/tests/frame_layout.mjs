import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
import {surface,compareSurface} from './frame_capture.mjs'
const repo=fileURLToPath(new URL('../../',import.meta.url)),out=repo+'tools/frame_layout/output/'
const native=JSON.parse(await readFile(out+'qml.json','utf8'))
for(const [name,hash] of Object.entries(native.sha256))assert.equal(createHash('sha256').update(await readFile(repo+'src/tactic_stream/shared_ui/'+name)).digest('hex'),hash,'stale native capture: '+name)
for(const [name,hash] of Object.entries(native.nativeSources))assert.equal(createHash('sha256').update(await readFile('D:/code/th_codex/'+name)).digest('hex'),hash,'stale native renderer: '+name)
const server=await createServer({root:repo,configFile:false,resolve:{alias:{vue:repo+'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},plugins:[vue()],logLevel:'warn',server:{host:'127.0.0.1',port:0,watch:{ignored:['**/.tmp/**','**/.venv/**','**/.standalone*/**','**/output/**']}}})
await server.listen();const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
let rectangles=0,styles=0,interiors=0;const samples=[]
const fixture=JSON.parse(await readFile(out+'fixture.json','utf8'))
try{
 for(const {mode,language,width,height} of [...new Map(native.captures.map(s=>[[s.mode,s.language,s.width,s.height].join(':'),s])).values()]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',error=>errors.push(error.message))
  let savedXml=fixture.configuration.sources[0].xml,revision='R1',unknown=false,writes=0
  await page.route('**/admin/widget-configuration/*',route=>{
   const action=route.request().url().split('/').pop(),body=route.request().postDataJSON()
   if(action==='preview')return route.fulfill({json:{result:{interface:{table:{item_layout:{elements:[],columns:12,collection:'grid',flow:'grid'}}},diff:'fixture diff'}}})
   if(action==='save'){writes++;savedXml=body.xml;revision='R2';if(unknown)return route.abort('failed')}
   return route.fulfill({json:{result:{...structuredClone(fixture.configuration),revision,sources:[{id:1,xml:savedXml,priority:0}]}}})
  })
  await page.route('**/admin/rpc',route=>route.fulfill({json:{result:[{__search_key__:'demo/asset?code=A1'}]}}))
  await page.route('**/admin/result-items',route=>route.fulfill({json:{result:{items:fixture.items}}}))
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/tools/frame_layout/index.html?mode='+mode+'&language='+language)
  await page.waitForFunction(()=>window.frameAdmin?.screen.value?.configuration&&!window.frameAdmin.screen.value.busy,{},{timeout:12000});await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>window.frameAdmin.screen.value.viewport.width>100)
  const control=id=>page.locator('[data-frame="'+id+'"]:visible')
  for(const phase of ['design','configuration','xml','changes','resolved']){
   await page.evaluate(page=>window.frameAdmin.screen.value.dispatch({type:'page',value:page}),phase)
   if(phase==='design')await page.evaluate(()=>window.frameAdmin.screen.value.dispatch({type:'select',name:'title'}))
   await page.waitForTimeout(50)
   const actual=await page.evaluate(()=>{const s=window.frameAdmin.screen.value;return JSON.parse(JSON.stringify({scene:{toolbar:s.toolbarScene,body:s.frameScene},state:{ui:s.ui,xml:s.xml,dirty:!!s.dirty,uncertain:s.uncertain}}))})
   const label=[mode,language,width,phase].join(' '),reference=native.captures.find(s=>s.mode===mode&&s.language===language&&s.width===width&&s.phase===phase)
   // Explicit platform capability: native opens configured views in the system browser.
   reference.scene.toolbar.nodes.find(n=>n.id==='layoutOpenView').text=actual.scene.toolbar.nodes.find(n=>n.id==='layoutOpenView').text
   assert.deepEqual(errors,[],label+' runtime errors');assert.deepEqual(actual.state,reference.state,label+' state');assert.deepEqual(actual.scene,reference.scene,label+' scene')
   const counts=await compareSurface(page,'section.layout-editor',await surface(page,'section.layout-editor'),reference,label);rectangles+=counts.rectangles;styles+=counts.styles;interiors+=counts.interiors
   const image='vue-'+mode+'-'+language+'-'+width+'-'+phase+'.png';await page.screenshot({path:out+image,animations:'disabled'});samples.push({mode,language,width,height,phase,image})
  }
  // Actual source input and server boundary, including a write applied without acknowledgement.
  await page.evaluate(()=>window.frameAdmin.screen.value.dispatch({type:'page',value:'xml'}))
  const source=control('layoutXmlSource').locator('textarea')
  await source.fill(savedXml.replace('title="Title"','title="Edited"'));await source.press('Tab')
  await page.waitForFunction(()=>window.frameAdmin.screen.value.xml.includes('Edited'))
  assert.equal(await control('adminSaveDocument').isDisabled(),true,'preview required before save')
  await control('layoutCheck').click();await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy)
  await control('adminSaveDocument').click();assert.equal(writes,0);await control('adminConfirmSave').click();await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy)
  assert.equal(writes,1);assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.dirty),false)
  await page.evaluate(()=>window.frameAdmin.screen.value.dispatch({type:'page',value:'xml'}))
  await source.fill(savedXml.replace('Edited','Uncertain'));await source.press('Tab');await control('layoutCheck').click();await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy)
  unknown=true;await control('adminSaveDocument').click();await control('adminConfirmSave').click();await page.waitForFunction(()=>window.frameAdmin.screen.value.uncertain)
  await page.evaluate(()=>window.frameAdmin.screen.value.dispatch({type:'save'}));assert.equal(writes,2,'unknown writes cannot repeat')
  await control('adminReloadDocument').click();await control('adminConfirmSave').click();await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy&&!window.frameAdmin.screen.value.uncertain)
  assert.equal(writes,2);assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.xml.includes('Uncertain')),true)
  assert.deepEqual(errors,[]);await page.close()
 }
 await writeFile(out+'vue.json',JSON.stringify({rectangles,styles,interiors,captures:samples},null,2));console.log(JSON.stringify({pairs:samples.length,rectangles,styles,interiors}))
}finally{await browser.close();await server.close()}
