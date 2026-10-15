import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'
import { chromium } from 'playwright'

const output=path.resolve(process.argv[2]), layout=JSON.parse(await readFile(path.join(output,'layout.json'),'utf8'))
const vite=await createServer({base:'/',server:{host:'127.0.0.1',port:0},appType:'custom'})
const html=`<html><body><div id="app"></div><script type="module">
import {createApp,h,reactive} from 'vue'
import Original from '/src/features/workspace/ResultItem.vue'
import Custom from '/src/features/interface/ConfiguredResultItem.vue'
import {initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'; import '/src/style.css'; import '/src/features/workspace/MobileResults.vue'
initializeAppearance()
const state=reactive({custom:false,node:{},selected:false}), events=[]
window.showItem=(node,custom,selected=false)=>{state.node=node;state.custom=custom;state.selected=selected;events.length=0}
window.itemEvents=events
createApp({setup(){return ()=>h('div',{id:'surface',class:innerWidth<=700?'mobile-results mobile-result-screen':'result-presentation',style:{width:'100%'}},[h(state.custom?Custom:Original,{key:state.custom+'-'+state.node.id,node:state.node,layout:state.custom?${JSON.stringify(layout)}:undefined,tree:innerWidth>700,selected:state.selected,selectable:true,checked:false,onActivate:(node,event)=>events.push(['activate',node.id,event?.type]),onTasks:(node,event)=>events.push(['tasks',node.id,event?.type]),onNotes:(node,event)=>events.push(['notes',node.id,event?.type]),onRelations:(node,event)=>events.push(['relations',node.id,event?.type]),onQuickaction:(node,command)=>events.push(['quickaction',node.id,command]),onOperate:(node,event)=>events.push(['operate',node.id,event?.type])})])}}).mount('#app')
</script></body></html>`
vite.middlewares.use(async(req,res,next)=>{
  if(req.url==='/__preview.svg'){res.setHeader('Content-Type','image/svg+xml');res.end('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90"><rect width="160" height="90" fill="#65a9c8"/><circle cx="80" cy="45" r="30" fill="#f4ce70"/></svg>');return}
  if(req.url!=='/__parity')return next()
  try{res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml(req.url,html))}catch(error){next(error)}
})
let browser
const cases=[
  {id:'main',kind:'object',depth:0,title:'DEMO_ROBOT',subtitle:'A reusable object',record:{id:1,name:'DEMO_ROBOT',description:'A reusable object',color:'#65a9c8'},preview:{},hasChildren:true,has_snapshot:true,task_count:3,note_count:12,progress_items:[{name:'Approved',approved:2,total:4,accent:'#65a9c8'}],info_items:[{column:'category',text:'Character',tooltip:'Category: Character'}],knowledge:[{identity:'article',searchKey:'note?code=ARTICLE',title:'Article'}]},
  {id:'child',kind:'object',depth:2,title:'Episode 01 — Arrival',subtitle:'Child description',record:{id:2,name:'Episode 01 — Arrival'},preview:{},hasChildren:false,task_count:0,note_count:1,progress_items:[],info_items:[]},
  {id:'process',kind:'branch',depth:1,title:'Model',record:{},branch:{kind:'process',process_type:'hierarchy'},preview:{},hasChildren:true,task_count:2,note_count:3},
  {id:'empty-process',kind:'branch',depth:1,title:'Publish',record:{},branch:{kind:'process'},preview:{},hasChildren:true,task_count:0,note_count:0},
  {id:'relation',kind:'branch',depth:1,title:'Assets',record:{},branch:{kind:'relation',relationship:'instance',count:4},hasChildren:true},
  {id:'versions',kind:'branch',depth:2,title:'Versions',record:{},branch:{kind:'versions',count:2},hasChildren:true},
  {id:'snapshot',kind:'snapshot',depth:2,title:'Publish',subtitle:'Snapshot description',record:{timestamp:'2026-09-10T12:00:00Z',repo:'default'},preview:{},hasChildren:true,snapshot_display:{title:'robot_publish.ma',exists:true,version:'v003',revision:'r002',repository:'Main',repositoryColor:'#65a9c8',latest:true,author:'Artist',size:12345,infoChips:[{label:'Type',value:'Maya'},{label:'Files',value:'1'}]}},
  {id:'offline',kind:'snapshot',depth:2,title:'Publish',record:{timestamp:'2026-09-10T12:00:00Z'},preview:{},hasChildren:false,snapshot_display:{title:'robot_missing.ma',exists:false,version:'v001',author:'Artist',size:12345}},
  {id:'image',kind:'object',title:'Object with image',subtitle:'Image preview',record:{},preview:{image:'/__preview.svg',files:[{type:'web',href:'/__preview.svg'}]},task_count:1,note_count:2},
  {id:'long-snapshot',kind:'snapshot',depth:1,title:'Publish',record:{context:'publish',version:3,timestamp:'2026-09-10T12:00:00Z'},preview:{},snapshot_display:{title:'a_very_long_filename_for_a_published_scene_that_should_be_elided_in_the_middle.ma',exists:true,version:'v003'}},
]
try{
  await mkdir(output,{recursive:true});await vite.listen()
  browser=await chromium.launch({headless:true})
  const page=await browser.newPage({viewport:{width:1100,height:500}}), errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.addInitScript(()=>localStorage.setItem('tactic_stream.appearance',JSON.stringify({language:'en',mode:'dark',theme:'md3',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false})))
  await page.goto('http://127.0.0.1:'+vite.httpServer.address().port+'/__parity')
  await page.waitForFunction(()=>!!window.showItem).catch(error=>{throw new Error(errors.join('\n') || error.message)})
  const measurements=[]
  for(const width of [1100,360]){
    await page.setViewportSize({width,height:500})
    for(const node of cases){
      for(const state of ['normal','hover','selected']){
        const metrics=[]
        for(const custom of [false,true]){
          await page.mouse.move(width-1,490)
          await page.evaluate(({node,custom,state})=>window.showItem(node,custom,state==='selected'),{node,custom,state})
          await page.evaluate(async()=>{await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));await document.fonts.ready;await Promise.all([...document.images].map(image=>image.decode().catch(()=>{})))})
          const item=page.locator('article')
          if(state==='hover')await item.hover({position:{x:10,y:10}})
          const measurement=await item.evaluate(root=>{
            const rect=root.getBoundingClientRect(),roles=['.result-preview','.result-branch-icon','.result-item-copy','.result-title-line','.result-description','.result-metadata','.result-item-actions','.result-communication','.result-mobile-actions']
            return {width:rect.width,height:rect.height,parts:Object.fromEntries(roles.map(selector=>{
              const node=root.querySelector(selector),bounds=node?.getBoundingClientRect()
              return [selector,bounds?{x:bounds.x-rect.x,y:bounds.y-rect.y,width:bounds.width,height:bounds.height}:null]
            }))}
          })
          metrics.push(measurement)
          await item.screenshot({path:path.join(output,`${width}-${node.id}-${state}-${custom?'custom':'original'}.png`),animations:'disabled'})
          if(width===1100&&node.id==='main'&&state==='normal'){
            await item.locator('button.result-task-button').click()
            assert.deepEqual(await page.evaluate(()=>window.itemEvents),[['tasks','main','click']])
          }
        }
        measurements.push({width,node:node.id,state,original:metrics[0],custom:metrics[1]})
      }
    }
  }
  await writeFile(path.join(output,'measurements.json'),JSON.stringify(measurements,null,2))
  assert.deepEqual(errors,[])
}finally{await browser?.close();await vite.close()}
