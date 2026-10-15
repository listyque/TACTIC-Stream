import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
import {surface,compareSurface} from './frame_capture.mjs'
const repo=fileURLToPath(new URL('../../',import.meta.url)),out=repo+'tools/frame_graph_editor/output/'
const native=JSON.parse(await readFile(out+'qml.json','utf8')),cases=JSON.parse(await readFile(repo+'tools/frame_graph_editor/cases.json','utf8'))
for(const [name,hash] of Object.entries(native.sha256))assert.equal(createHash('sha256').update(await readFile(repo+'src/tactic_stream/shared_ui/'+name)).digest('hex'),hash,'stale native capture: '+name)
for(const [name,hash] of Object.entries(native.nativeSources))assert.equal(createHash('sha256').update(await readFile('D:/code/th_codex/'+name)).digest('hex'),hash,'stale native renderer: '+name)
const server=await createServer({root:repo,configFile:false,resolve:{alias:{vue:repo+'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},plugins:[vue()],logLevel:'warn',server:{host:'127.0.0.1',port:0,watch:{ignored:['**/.tmp/**','**/.venv/**','**/.standalone*/**','**/output/**']}}})
await server.listen();const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
let rectangles=0,styles=0,interiors=0;const samples=[]
try{
 for(const {editor,mode,language,width,height} of [...new Map(native.captures.map(s=>[[s.editor,s.mode,s.language,s.width,s.height].join(':'),s])).values()]){
  const fixture=JSON.parse(await readFile(out+editor+'.json','utf8')),names=editor==='schema'?['demo/asset','demo/shot']:['model','publish']
  const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',error=>errors.push(error.message))
  await page.route('**/admin/rpc',route=>{const body=route.request().postDataJSON();assert.equal(body.method,'execute_cmd');const action=body.args[2].action;assert(['load','list','columns'].includes(action),'paired capture cannot write');return route.fulfill({json:{result:{info:structuredClone(action==='columns'?fixture.columns:fixture.fixture)}}})})
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/tools/frame_graph_editor/index.html?editor='+editor+'&mode='+mode+'&language='+language)
  await page.waitForFunction(()=>window.frameAdmin?.screen.value?.document&&!window.frameAdmin.screen.value.busy);await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>window.frameAdmin.screen.value.viewport.width>100)
  const control=id=>page.locator('[data-frame="'+id+'"]:visible'),section=async(selector,value)=>{
   if(editor==='workflow'&&selector==='adminGraphInspectorPages'){await control('adminGraphAddNode').click();assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.ui.inspector),value);return}
   const button=control(selector+'_'+value);if(await button.count())await button.click();else await control(selector).selectOption(value)
  }
  for(const c of cases){
   for(const action of c.actions){
    if(action.type==='state')await page.evaluate(value=>{const s=window.frameAdmin.screen.value;s.canWrite=value!=='readonly';s.uncertain=value==='uncertain';s.busy=value==='busy'},action.value)
    else if(action.type==='select')await page.evaluate(identity=>window.frameAdmin.screen.value.dispatch({type:'selectNodes',identities:[identity],primary:identity}),names[action.identity==='second'?1:0])
    else if(action.type==='edge')await page.evaluate(index=>window.frameAdmin.screen.value.dispatch({type:'selectEdge',index}),action.index)
    else if(action.type==='phone'){if(width<800)await section('adminGraphPanels',action.value)}
    else if(action.type==='page'||action.type==='workflowPage'){if(action.type!=='workflowPage'||editor==='workflow')await section(action.selector,action.value)}
    else if(action.type==='reveal'){if(editor!=='workflow'||action.id!=='adminRemoveGraphSelection')await control(action.viewport).evaluate((view,id)=>{const el=view.querySelector('[data-frame="'+id+'"]');view.scrollTop+=el.getBoundingClientRect().top-view.getBoundingClientRect().top-12},action.id)}
    else if(action.type==='workflowClick'){if(editor==='workflow'){await control(action.id).click();assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.node?.identity||''),'')}}
    else if(action.type==='text')await control(action.id).fill(action.value)
    else await control(action.id).click()
    if(action.type!=='state'||action.value!=='busy')await page.waitForFunction(()=>!window.frameAdmin.screen.value.busy&&!window.frameAdmin.screen.value.columnsBusy)
   }
   await page.evaluate(()=>document.activeElement.blur());await page.mouse.move(width-1,height-1);await page.waitForTimeout(35)
   const actual=await page.evaluate(()=>{const s=window.frameAdmin.screen.value;return JSON.parse(JSON.stringify({scene:{toolbar:s.toolbarScene,body:s.frameScene},state:{ui:s.ui,dirty:!!s.dirty,identity:s.identity,selected:s.selected,primary:s.node?.identity||'',edge:s.selectedEdge,attributes:s.node?.attributes||s.edge?.attributes||{},settings:s.frameMode==='workflow'?s.processSettings:{}}}))})
   const label=[editor,mode,language,width,c.phase].join(' '),reference=native.captures.find(s=>s.editor===editor&&s.mode===mode&&s.language===language&&s.width===width&&s.phase===editor+'-'+c.phase)
   assert.deepEqual(errors,[],label+' runtime errors');assert.deepEqual(actual.state,reference.state,label+' state');assert.deepEqual(actual.scene,reference.scene,label+' scene')
   const root=editor==='schema'?'section.schema-editor':'section.workflow-editor'
   const counts=await compareSurface(page,root,await surface(page,root),reference,label);rectangles+=counts.rectangles;styles+=counts.styles;interiors+=counts.interiors
   if(c.phase===cases[0].phase&&width>=1100){
    const painted=await page.evaluate(names=>{
     const port=name=>document.querySelector('[data-frame="'+name+'"]'),a=port('graphOutput_'+names[0]).getBoundingClientRect(),b=port('graphInput_'+names[1]).getBoundingClientRect()
     const canvas=document.querySelector('.graph-camera canvas'),box=canvas.getBoundingClientRect(),ratio=canvas.width/box.width
     const x=Math.round(((a.x+a.width/2+b.x+b.width/2)/2-box.x)*ratio),y=Math.round(((a.y+a.height/2+b.y+b.height/2)/2-box.y)*ratio)
     const pixels=canvas.getContext('2d').getImageData(x-1,y-1,3,3).data
     return [...pixels].some((value,index)=>index%4===3&&value>127)
    },names)
    assert.ok(painted,label+' ordinary connection must have visible pixels')
   }
   const image=editor+'-vue-'+mode+'-'+language+'-'+width+'-'+c.phase+'.png';await page.screenshot({path:out+image,animations:'disabled'});samples.push({editor,mode,language,width,height,phase:editor+'-'+c.phase,image})
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,'no page overflow')
  }
  await page.close()
 }
 await writeFile(out+'vue.json',JSON.stringify({rectangles,styles,interiors,captures:samples},null,2));console.log(JSON.stringify({pairs:samples.length,rectangles,styles,interiors}))
}finally{await browser.close();await server.close()}
