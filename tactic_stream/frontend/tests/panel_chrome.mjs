import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url))
const output = fileURLToPath(new URL('../../.screenshots/panel-chrome-current/', import.meta.url))
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import { createApp, h, ref } from 'vue'
import '/src/App.vue'
import AppSplitter from '/src/controls/AppSplitter.vue'
import ResultPresentation from '/src/features/workspace/ResultPresentation.vue'
import SnapshotBrowser from '/src/features/objects/SnapshotBrowser.vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import { defaults, stack } from '/src/features/workspace/docks.js'
import { windowDirective } from '/src/controls/window.js'
import '/src/theme.css'
import '/src/style.css'
const docks = defaults()
docks.panels.description.visible = true
docks.layout = { type:'split', orientation:'horizontal', ratio:.5, first:stack('results'), second:stack('description') }
localStorage.setItem('tactic_stream.docks.chrome-test', JSON.stringify(docks))
const app = createApp({ setup() {
  const width = ref(200), height = ref(160)
  return () => h('main', { style:'padding:12px;display:grid;grid-template-columns:minmax(0,1fr);gap:12px' }, [
    h('section', { id:'ordinary', style:'display:flex;height:100px' }, [h('div',{style:'width:'+width.value+'px;max-width:calc(100% - 10px)'},'Panel'),h(AppSplitter,{modelValue:width.value,'onUpdate:modelValue':v=>width.value=v,label:'Resize test panels',min:100,max:500})]),
    h('section', { id:'reverse', style:'display:flex;flex-direction:column;height:80px' }, [h(AppSplitter,{modelValue:height.value,'onUpdate:modelValue':v=>height.value=v,label:'Resize test output',horizontal:true,reverse:true,min:100,max:300})]),
    ...['splitted_vertical','splitted_horizontal'].map(mode=>h('section',{id:mode,style:'height:180px;min-width:0'},[h(ResultPresentation,{rows:[],selectedKeys:[],state:{},active:false,mode,groupMode:'none'})])),
    h('section',{id:'dock-snapshot',style:'position:relative;height:400px;min-width:0'}), h(SnapshotBrowser,{active:false}),
    h('section',{id:'dock-test',style:'position:relative;height:460px;display:flex'},[h(DockWorkspace,{login:'chrome-test',resultsActive:true})]),
    h('div',{id:'scroll-test',tabindex:0,style:'width:260px;height:140px;overflow:auto'},[h('div',{style:'width:600px;height:900px'},Array.from({length:30},(_,i)=>h('p','Scrollable row '+i)))]),
    h('textarea',{id:'scroll-text',style:'width:260px;height:80px',value:Array(40).fill('Editor line').join('\\n')})
  ])
}})
app.directive('window',windowDirective).mount('#app')
</script></body></html>`
let server, browser
try {
  await mkdir(output, { recursive:true })
  server = await createServer({ root, configFile:false, plugins:[vue(),{
    name:'panel-chrome-fixture',
    configureServer(server) {
      server.middlewares.use(async (req,res,next) => {
        if (req.url !== '/panel-chrome-test') return next()
        try { res.setHeader('Content-Type','text/html'); res.end(await server.transformIndexHtml(req.url,html)) }
        catch (error) { next(error) }
      })
    },
  }], server:{host:'127.0.0.1',port:0} })
  await server.listen()
  browser = await chromium.launch({headless:true,channel:process.env.STREAM_CHECK_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
  const page = await browser.newPage({viewport:{width:1100,height:900},hasTouch:true})
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('pageerror',error=>errors.push(error.message))
  page.on('console',message=>{if(message.type()==='error') console.error(message.text())})
  page.on('pageerror',error=>console.error(error.message))
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/panel-chrome-test`)
  const normal = page.getByRole('separator',{name:'Resize test panels',exact:true})
  await normal.waitFor()
  const visual = locator => locator.evaluate(node => { const style=getComputedStyle(node,'::after'); return {width:style.width,height:style.height,opacity:style.opacity} })
  await page.mouse.move(0,0)
  assert.deepEqual(await visual(normal),{width:'3px',height:'40px',opacity:'0.28'})
  assert.equal((await normal.boundingBox()).width,10)
  await normal.hover(); await page.waitForTimeout(100)
  assert.equal((await visual(normal)).opacity,'0.85')
  await page.mouse.down(); await page.waitForTimeout(100)
  assert.equal((await visual(normal)).opacity,'1')
  await page.mouse.up()
  await normal.focus(); await normal.press('ArrowRight'); assert.equal(await normal.getAttribute('aria-valuenow'),'210')
  await normal.press('Home'); assert.equal(await normal.getAttribute('aria-valuenow'),'100')
  await normal.press('End'); assert.equal(await normal.getAttribute('aria-valuenow'),'500')
  await normal.press('ArrowLeft'); assert.equal(await normal.getAttribute('aria-valuenow'),'490')
  const drag = async (locator,dx,dy) => {
    const box=await locator.boundingBox(), x=box.x+box.width/2,y=box.y+box.height/2
    await page.mouse.move(x,y); await page.mouse.down(); await page.mouse.move(x+dx,y+dy,{steps:5}); await page.mouse.up()
  }
  await drag(normal,-30,0); assert.equal(await normal.getAttribute('aria-valuenow'),'460')
  const touch = await page.context().newCDPSession(page), touchBox = await normal.boundingBox()
  const touchPoint = {x:touchBox.x+5,y:touchBox.y+30,id:1}
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touchPoint]})
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{...touchPoint,x:touchPoint.x+20}]})
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
  assert.equal(await normal.getAttribute('aria-valuenow'),'480','Touch drag uses the same splitter')
  const reverse = page.getByRole('separator',{name:'Resize test output',exact:true})
  await drag(reverse,0,20); assert.equal(await reverse.getAttribute('aria-valuenow'),'140')
  assert.equal((await visual(reverse)).width,'40px'); assert.equal((await visual(reverse)).height,'3px')
  const result = page.locator('#splitted_vertical .result-split-divider')
  await result.press('ArrowRight'); assert.equal(await result.getAttribute('aria-valuenow'),'56')
  const parentWidth = await result.evaluate(node=>node.parentElement.getBoundingClientRect().width)
  await drag(result,parentWidth/10,0); assert.equal(await result.getAttribute('aria-valuenow'),'66')
  const bottom = page.locator('#splitted_horizontal .result-split-divider')
  await drag(bottom,0,18); assert.equal(await bottom.getAttribute('aria-valuenow'),'65')
  const snapshot = page.getByRole('separator',{name:'Resize snapshot panels',exact:true})
  assert.deepEqual({...(await visual(snapshot)),opacity:'0.28'},{width:'40px',height:'3px',opacity:'0.28'})
  await snapshot.press('ArrowDown'); assert(Number(await snapshot.getAttribute('aria-valuenow'))>52)
  const dock = page.getByRole('separator',{name:'Resize workspace panels',exact:true})
  await dock.waitFor(); assert.equal((await dock.boundingBox()).width,10)
  assert.equal((await visual(dock)).height,'40px')
  await dock.press('ArrowRight'); assert.equal(await dock.getAttribute('aria-valuenow'),'52')
  await drag(dock,30,0); assert(Number(await dock.getAttribute('aria-valuenow'))>52)
  const scroller = page.locator('#scroll-test')
  const gutter = () => scroller.evaluate(node=>[node.offsetWidth-node.clientWidth,node.offsetHeight-node.clientHeight])
  assert.deepEqual(await gutter(),[12,12])
  await scroller.scrollIntoViewIfNeeded()
  const bounds=await scroller.boundingBox()
  await page.mouse.move(bounds.x+bounds.width-5,bounds.y+15)
  assert.deepEqual(await gutter(),[12,12],'Hover keeps content geometry fixed')
  await page.mouse.down(); await page.mouse.move(bounds.x+bounds.width-5,bounds.y+90,{steps:8}); await page.mouse.up()
  assert(await scroller.evaluate(node=>node.scrollTop>0),'The native thumb remains draggable')
  await scroller.focus(); await scroller.press('Home'); await scroller.press('PageDown')
  await page.waitForTimeout(180); assert(await scroller.evaluate(node=>node.scrollTop>0))
  await scroller.tap(); await page.mouse.wheel(0,120); await page.waitForTimeout(100)
  assert.equal(await page.locator('#scroll-text').evaluate(node=>node.offsetWidth-node.clientWidth-2),12)
  await scroller.screenshot({path:output+'/stream-scrollbar.png'})
  for (const mode of ['light','dark']) for (const theme of ['md3','material5']) {
    await page.evaluate(({mode,theme})=>{document.documentElement.dataset.mode=mode;document.documentElement.dataset.theme=theme},{mode,theme})
    await page.screenshot({path:output+`/stream-${mode}-${theme}.png`,fullPage:true})
  }
  await page.setViewportSize({width:360,height:800})
  await page.waitForTimeout(80)
  assert.equal(await normal.isVisible(),false)
  assert.equal(await result.isVisible(),false)
  assert.equal(await snapshot.isVisible(),false)
  assert.equal(await dock.count(),0)
  assert(await page.locator('#splitted_vertical .result-versions').isVisible())
  assert(await page.locator('#splitted_horizontal .result-main').isVisible())
  for (const id of ['splitted_vertical','splitted_horizontal']) assert(await page.locator('#'+id+' .result-versions').evaluate(node=>node.clientHeight>=node.querySelector('header').offsetHeight+16),'Mobile versions toolbar remains readable')
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Phone layout stays within the viewport')
  await page.screenshot({path:output+'/stream-mobile.png',fullPage:true})
  await page.setViewportSize({width:1100,height:900})
  assert.equal(await result.getAttribute('aria-valuenow'),'66','Mobile layout keeps desktop proportions')
  const scaled = await browser.newPage({viewport:{width:1100,height:900},deviceScaleFactor:2})
  await scaled.goto(page.url()); await scaled.getByRole('separator',{name:'Resize test panels',exact:true}).waitFor()
  assert.equal((await visual(scaled.getByRole('separator',{name:'Resize test panels',exact:true}))).width,'3px')
  assert.equal(await scaled.locator('#scroll-test').evaluate(node=>node.offsetWidth-node.clientWidth),12)
  await scaled.locator('#ordinary').screenshot({path:output+'/stream-scale-2.png'})
  await scaled.close()
  assert.deepEqual(errors,[])
  console.log('PASS panel chrome: shared grip states, normal/reverse/percentage drag, keyboard/touch, snapshot/dock input, native scrollbar drag/gutter, light/dark themes, 200% scale, mobile restoration')
} finally {
  await browser?.close()
  assert(!browser?.isConnected())
  const httpServer = server?.httpServer
  await server?.close()
  assert(!httpServer?.listening)
}
