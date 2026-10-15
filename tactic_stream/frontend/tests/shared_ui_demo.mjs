import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {build} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'

const demo=fileURLToPath(new URL('../../tools/shared_ui_demo/',import.meta.url)),out=demo+'output/'
const native=JSON.parse(await readFile(out+'qml-measurements.json','utf8'))
await build({root:demo,configFile:false,base:'./',define:{'process.env.NODE_ENV':'"production"'},resolve:{alias:{vue:fileURLToPath(new URL('../node_modules/vue/dist/vue.runtime.esm-bundler.js',import.meta.url))}},plugins:[vue()],logLevel:'warn',build:{outDir:out+'web',emptyOutDir:false,minify:false,sourcemap:true,lib:{entry:demo+'entry.js',name:'SharedUiDemo',formats:['iife'],fileName:()=> 'demo.js',cssFileName:'demo'}}})
await writeFile(out+'web/demo.html','<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Shared UI skeleton · Vue</title><link rel="stylesheet" href="demo.css"><body><div id="app"></div><script src="demo.js"></script></body></html>')
const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL})
const captures=[]
try {
 for(const mode of ['dark','light'])for(const language of ['en','ru'])for(const width of [520,320]){
  const page=await browser.newPage({viewport:{width,height:300}}),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  try {
   await page.goto(pathToFileURL(out+'web/demo.html').href+'?mode='+mode+'&language='+language)
   await page.waitForFunction(()=>window.demo,undefined,{timeout:5000}).catch(error=>{throw Error(error.message+'; '+JSON.stringify(errors))});await page.evaluate(()=>document.fonts.ready)
   const control=id=>page.locator('[data-control="'+id+'"]')
   async function capture(phase){
    await page.locator('main').click({position:{x:width-5,y:295}});await page.mouse.move(width-5,295)
    const sample=await page.evaluate(()=>({geometry:Object.fromEntries([...document.querySelectorAll('[data-control]')].map(el=>{const box=el.getBoundingClientRect();return [el.dataset.control,{x:box.x,y:box.y,width:box.width,height:box.height}]})),styles:Object.fromEntries([...document.querySelectorAll('[data-control]')].map(el=>{const css=getComputedStyle(el);return [el.dataset.control,{fontSize:parseFloat(css.fontSize),fontWeight:Number(css.fontWeight),color:css.color}]})),texts:Object.fromEntries([...document.querySelectorAll('[data-control]')].map(el=>{const clone=el.cloneNode(true);clone.querySelectorAll('.app-icon').forEach(icon=>icon.remove());return [el.dataset.control,el.matches('input')?el.value:clone.textContent]})),state:window.demo.state.value}))
    const reference=native.captures.find(item=>item.mode===mode&&item.language===language&&item.width===width&&item.phase===phase)
    assert.deepEqual(sample.state,reference.state)
    for(const [id,box] of Object.entries(sample.geometry))for(const key of ['x','y','width','height'])assert(Math.abs(box[key]-reference.geometry[id][key])<=.1,JSON.stringify({mode,language,width,phase,id,key,vue:box[key],qml:reference.geometry[id][key]}))
    for(const [id,css] of Object.entries(sample.styles)){
     assert.equal(css.fontSize,reference.styles[id].fontSize,id+' font size');assert.equal(css.fontWeight,reference.styles[id].fontWeight,id+' font weight')
     const rgb=css.color.match(/\d+/g).slice(0,3).map(Number),hex=reference.styles[id].color
     for(let i=0;i<3;i++)assert(Math.abs(rgb[i]-parseInt(hex.slice(1+i*2,3+i*2),16))<=1,JSON.stringify({id,css,qml:reference.styles[id]}))
     assert.equal(sample.texts[id],reference.texts[id],id+' text')
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width)
    const image='vue-'+mode+'-'+language+'-'+width+'-'+phase+'.png'
    await page.screenshot({path:out+image});captures.push({mode,language,width,phase,image,...sample})
   }
   await capture('initial');assert.equal(await control('apply').isDisabled(),true)
   await control('name').fill('');await control('apply').click();await capture('error')
   await control('name').fill('Pipeline B');await control('enabled').locator('input').click();await control('apply').click();await capture('saved')
   await control('name').fill('Draft');await control('reset').click();await capture('reset')
   assert.deepEqual(errors,[])
  }finally{await page.close()}
 }
 await writeFile(out+'vue-measurements.json',JSON.stringify({captures,checks:['same screen.json','same logic.mjs','all 8 native control rectangles','real input/click/change/apply/reset','identical state traces','EN/RU','dark/light','520/320 widths','no browser overflow','no runtime exceptions']},null,2))
 console.log('PASS: 32 paired QML/Vue states; 256 control rectangles; 8 real interaction cases')
}finally{await browser.close()}
