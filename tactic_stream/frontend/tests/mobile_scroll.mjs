import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import { createApp, h, ref } from 'vue'
import MobilePage from '/src/controls/MobilePage.vue'
import AppButton from '/src/controls/AppButton.vue'
import { initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
initializeAppearance()
createApp({setup() {
  const busy = ref(false), scroll = ref({}), active = ref(true)
  const reload = () => { busy.value = true; setTimeout(() => { busy.value = false }, 100) }
  const resume = () => {
    active.value = false; busy.value = true
    setTimeout(() => { document.querySelector('.mobile-result-screen').scrollTop = 0; active.value = true }, 20)
    setTimeout(() => { busy.value = false }, 160)
  }
  return () => h('main',{style:'height:100dvh;display:flex;flex-direction:column'},[
    h(AppButton,{label:'Reload',onClick:reload}),
    h(AppButton,{label:'Resume',onClick:resume}),
    h('section',{class:'workspace-browser',style:'flex:1;min-height:0;display:flex;flex-direction:column'},[
      h('div',{class:'search-header',style:'height:50px;min-height:50px'},'Search'),
      h('div',{class:'workspace-tabs',style:'height:38px;min-height:38px'},'Tabs'),
      h(MobilePage,{screenKey:'root',title:'Items',back:false,active:active.value,busy:busy.value,scroll:scroll.value,
        style:'height:auto;flex:1',onScrolled:(key,top)=>scroll.value[key]=top},
        {default:()=>Array.from({length:80},(_,i)=>h('p',{style:'height:50px;flex:none'},'Item '+i))})
    ])
  ])
}}).mount('#app')
</script><style>
.workspace-browser:has(.mobile-results[data-chrome-hidden="true"]) > :is(.search-header,.workspace-tabs) { display:none }
</style></body></html>`
let server, browser
try {
  server = await createServer({root:fileURLToPath(new URL('..',import.meta.url)),configFile:false,
    plugins:[vue(),{name:'mobile-scroll-fixture',configureServer(server) {
      server.middlewares.use(async (req,res,next) => {
        if (req.url !== '/mobile-scroll-test') return next()
        try { res.setHeader('Content-Type','text/html'); res.end(await server.transformIndexHtml(req.url,html)) }
        catch(error) { next(error) }
      })
    }}],server:{host:'127.0.0.1',port:0}})
  await server.listen()
  browser = await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']})
  const page = await browser.newPage({viewport:{width:390,height:844},hasTouch:true})
  const errors = []
  page.on('pageerror',error => errors.push(error.message))
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/mobile-scroll-test')
  const screen = page.locator('.mobile-result-screen')
  await screen.waitFor()
  const anchor = screen.locator('p').nth(10), anchorStart = await anchor.boundingBox()
  await page.mouse.move(190,400)
  await page.mouse.wheel(0,40)
  await page.waitForFunction(() => document.querySelector('.mobile-result-screen').scrollTop >= 39)
  assert.equal(await page.locator('.mobile-results').getAttribute('data-chrome-hidden'),'false','Small navigation must not expose a blank toolbar-sized gap')
  await page.mouse.wheel(0,110)
  await page.waitForFunction(() => document.querySelector('.mobile-result-screen').scrollTop >= 145)
  await page.waitForFunction(() => document.querySelector('.mobile-results').dataset.chromeHidden === 'true' && parseFloat(document.querySelector('.mobile-result-screen').style.paddingTop) > 0)
  assert.ok(Math.abs(anchorStart.y-(await anchor.boundingBox()).y-150)<1,'Hiding toolbars must move rows only by the wheel distance')
  const beforeClick = await screen.evaluate(element => element.scrollTop)
  await page.getByRole('button',{name:'Reload',exact:true}).click()
  await page.waitForTimeout(130)
  assert.equal(await screen.evaluate(element => element.scrollTop),beforeClick,'A click starting a read must not restore an older scroll position')
  await page.getByRole('button',{name:'Reload',exact:true}).click()
  await page.mouse.move(190,400)
  await page.mouse.wheel(0,120)
  await page.waitForFunction(top => document.querySelector('.mobile-result-screen').scrollTop >= top+115,beforeClick)
  const duringRead = await screen.evaluate(element => element.scrollTop)
  await page.waitForTimeout(150)
  assert.equal(await screen.evaluate(element => element.scrollTop),duringRead,'Wheel navigation during a read must keep its new position')
  await page.waitForTimeout(200)
  await page.getByRole('button',{name:'Resume',exact:true}).click()
  await page.waitForTimeout(210)
  assert.equal(await screen.evaluate(element => element.scrollTop),duringRead,'Returning to a loading screen still restores its saved position')
  await page.getByRole('button',{name:'Resume',exact:true}).click()
  await page.waitForTimeout(50)
  await page.mouse.move(190,400)
  await page.mouse.wheel(0,90)
  await page.waitForFunction(() => document.querySelector('.mobile-result-screen').scrollTop >= 85)
  const resumedNavigation = await screen.evaluate(element => element.scrollTop)
  await page.waitForTimeout(180)
  assert.equal(await screen.evaluate(element => element.scrollTop),resumedNavigation,'User navigation cancels a pending restore')
  await screen.evaluate(element => { element.scrollTop = element.scrollHeight })
  await page.waitForTimeout(80)
  const trace = await screen.evaluate(async element => {
    const trace = []
    for (let i=0;i<24;i++) { await new Promise(requestAnimationFrame); trace.push([element.scrollTop,element.clientHeight,element.closest('.mobile-results').dataset.chromeHidden]) }
    return trace
  })
  assert.equal(new Set(trace.map(row=>JSON.stringify(row))).size,1,'At the end, toolbar hiding must settle instead of oscillating')
  await page.mouse.move(190,400)
  const lastRow = screen.locator('p').last(), lastRowBefore = await lastRow.boundingBox()
  await page.mouse.wheel(0,-120)
  await page.waitForFunction(() => document.querySelector('.mobile-results').dataset.chromeHidden === 'false')
  assert.ok(Math.abs((await lastRow.boundingBox()).y-lastRowBefore.y-120)<1,'Showing toolbars must move rows only by the wheel distance')
  const afterUp = await screen.evaluate(element => element.scrollTop)
  await page.waitForTimeout(150)
  assert.equal(await screen.evaluate(element => element.scrollTop),afterUp,'Showing toolbars must not undo upward navigation')
  assert.deepEqual(errors,[])
  console.log('PASS mobile scrolling: click/read and wheel keep position, toolbar resize settles at the end and on upward navigation')
} finally {
  await browser?.close()
  const httpServer = server?.httpServer
  await server?.close()
  assert(!browser?.isConnected() && !httpServer?.listening)
}
