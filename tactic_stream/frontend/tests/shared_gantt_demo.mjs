import assert from 'node:assert/strict'
import {readFile, writeFile} from 'node:fs/promises'
import {fileURLToPath, pathToFileURL} from 'node:url'
import {createHash} from 'node:crypto'
import {build} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
import {stable} from '../../tools/shared_ui_demo/gantt.state.mjs'
import {report} from '../../tools/shared_ui_demo/report.mjs'

const demo=fileURLToPath(new URL('../../tools/shared_ui_demo/',import.meta.url)),out=demo+'output/'
const native=JSON.parse(await readFile(out+'gantt-qml-measurements.json','utf8')),cases=JSON.parse(await readFile(demo+'gantt_cases.json','utf8'))
for(const [name,hash] of Object.entries(native.sha256))assert.equal(createHash('sha256').update(await readFile(demo+name)).digest('hex'),hash,'stale native capture: '+name)
await build({root:demo,configFile:false,base:'./',define:{'process.env.NODE_ENV':'"production"'},resolve:{alias:{vue:fileURLToPath(new URL('../node_modules/vue/dist/vue.runtime.esm-bundler.js',import.meta.url))}},plugins:[vue()],logLevel:'warn',build:{outDir:out+'web',emptyOutDir:false,minify:false,sourcemap:true,lib:{entry:demo+'gantt_entry.js',name:'SharedGanttDemo',formats:['iife'],fileName:()=> 'gantt.js',cssFileName:'gantt'}}})
await writeFile(out+'web/gantt.html','<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Shared Gantt · Vue</title><link rel="stylesheet" href="gantt.css"><body><div id="app"></div><script src="gantt.js"></script></body></html>')
const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL}),captures=[]
let rectangles=0
try {
 for(const mode of ['dark','light'])for(const language of ['en','ru'])for(const [width,height] of [[1100,660],[840,560]]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  try {
   await page.goto(pathToFileURL(out+'web/gantt.html').href+'?mode='+mode+'&language='+language)
   await page.waitForFunction(()=>window.ganttDemo,undefined,{timeout:10000});await page.evaluate(()=>document.fonts.ready)
   const control=id=>page.locator('[data-node="'+id+'"]')
   for(const c of cases){
    for(const event of c.actions){
     if(event.type==='key'){await control(event.target).focus();await page.keyboard.press(event.code);await page.waitForTimeout(35);continue}
     if(event.type==='wheel'){
      await page.mouse.move(width/2,height/2)
      if(event.shift)await page.keyboard.down('Shift');if(event.ctrl)await page.keyboard.down('Control')
      await page.mouse.wheel(0,event.dy);await page.waitForTimeout(75)
      if(event.shift)await page.keyboard.up('Shift');if(event.ctrl)await page.keyboard.up('Control')
      continue
     }
     const rect=await control(event.target).boundingBox();assert(rect,event.target)
     const x=rect.x+(event.target==='working-days'?9:rect.width/2),y=rect.y+rect.height/2
     if(event.type==='click'){await page.mouse.click(x,y)}else if(event.type==='drag'){
      const day=await page.evaluate(()=>window.ganttDemo.scene.value.geometry.day),dx=event.dx??(event.days||0)*day,dy=event.dy||0
      await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+dx,y+dy,{steps:4})
      if(event.cancel)await page.keyboard.press('Escape');await page.mouse.up()
     }else throw Error('Unknown action')
     await page.waitForTimeout(35)
    }
    await page.mouse.move(width-3,height-2);await page.waitForTimeout(30)
    const sample=await page.evaluate(()=>({scene:JSON.parse(JSON.stringify(window.ganttDemo.scene.value)),state:JSON.parse(JSON.stringify(window.ganttDemo.state.value)),boxes:Object.fromEntries([...document.querySelectorAll('[data-node]')].map(el=>{const r=el.getBoundingClientRect();return[el.dataset.node,{x:r.x,y:r.y,width:r.width,height:r.height}]})),styles:Object.fromEntries([...document.querySelectorAll('[data-node]')].map(el=>{const css=getComputedStyle(el),rgba=text=>{const c=text.match(/[\d.]+/g).map(Number);return[c[0],c[1],c[2],Math.round((c[3]??1)*255)]};return[el.dataset.node,el.classList.contains('gantt-rectangle')?{background:rgba(css.backgroundColor)}:{fontSize:parseFloat(css.fontSize),fontWeight:Number(css.fontWeight),color:rgba(css.color)}]}))}))
    const reference=native.captures.find(item=>item.mode===mode&&item.language===language&&item.width===width&&item.phase===c.phase)
    assert.deepEqual(sample.state,reference.state,mode+' '+language+' '+width+' '+c.phase+' state')
    assert.equal(createHash('sha256').update(stable(sample.scene)).digest('hex'),reference.sceneHash,c.phase+' scene graph')
    assert.deepEqual(Object.keys(sample.boxes).sort(),Object.keys(reference.boxes).sort())
    for(const [id,box] of Object.entries(sample.boxes)){
     for(const key of ['x','y','width','height'])assert(Math.abs(box[key]-reference.boxes[id][key])<=.06,JSON.stringify({mode,language,width,phase:c.phase,id,key,vue:box[key],qml:reference.boxes[id][key]}))
     rectangles++
     assert.deepEqual(sample.styles[id],reference.styles[id],c.phase+' '+id+' painted style')
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width)
    const image='gantt-vue-'+mode+'-'+language+'-'+width+'-'+c.phase+'.png';await page.screenshot({path:out+image})
    captures.push({mode,language,width,height,phase:c.phase,image,state:sample.state})
   }
   assert.deepEqual(errors,[])
  }finally{await page.close()}
 }
 await writeFile(out+'gantt-vue-measurements.json',JSON.stringify({captures,rectangles,checks:['real input in both engines','same source hashes','identical state traces','identical scene graph','actual native/DOM rectangles','EN/RU','dark/light','1100x660 / 840x560','no overflow / runtime errors']},null,2))
 await report()
 console.log('PASS: '+captures.length+' paired Gantt states; '+rectangles+' actual native/DOM rectangles')
}finally{await browser.close()}
