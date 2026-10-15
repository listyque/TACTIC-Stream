import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { mkdir } from 'node:fs/promises'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url))
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import { createApp, h } from 'vue'
import AppCheckbox from '/src/controls/AppCheckbox.vue'
import { appearance, initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
import '/src/features/messages/messages.css'
Object.assign(appearance,{mode:'dark',language:'ru'});initializeAppearance()
window.appearance=appearance
createApp({data(){return {checked:true}},render(){return h('div',{style:'padding:24px;width:400px'},[
 h('header',{class:'messages-heading'},h(AppCheckbox,{compact:true,label:'Message notifications',modelValue:this.checked,'onUpdate:modelValue':value=>this.checked=value})),
 h(AppCheckbox,{label:'Default checkbox',modelValue:true}),
 h(AppCheckbox,{compact:true,label:'Disabled checkbox',modelValue:true,disabled:true}),
 h(AppCheckbox,{compact:true,label:'Mixed checkbox',indeterminate:true})
])}}).mount('#app')
</script></body></html>`
let server, browser
const deadline = setTimeout(()=>browser?.close(),55000)
try {
 server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/checkbox-geometry',plugins:[vue(),{
  name:'checkbox-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
   if(req.url!=='/checkbox-test')return next()
   try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
  })}
 }],server:{host:'127.0.0.1',port:0,watch:null}});await server.listen()
 browser=await chromium.launch({headless:true})
 const page=await browser.newPage({viewport:{width:1280,height:300},hasTouch:true}),errors=[]
 page.on('pageerror',error=>errors.push(error.message))
 await page.goto(server.resolvedUrls.local[0]+'checkbox-test')
 page.setDefaultTimeout(6000)
 const notification=page.getByRole('checkbox',{name:'Уведомления о сообщениях',exact:true})
 await notification.waitFor()
 await mkdir(root+'/../.screenshots/checkbox-current',{recursive:true})
 for(const mode of ['light','dark']) for(const theme of ['md3','material5','fluent']) for(const pack of ['material-design','fontawesome-solid','fontawesome-outline','fluent-regular','fluent-filled']) {
  await page.evaluate(settings=>Object.assign(window.appearance,settings),{mode,theme,iconSet:pack})
  await page.evaluate(async()=>{await new Promise(requestAnimationFrame);await document.fonts.ready})
  const geometry=await page.locator('.app-checkbox-indicator').evaluateAll(indicators=>indicators.map(indicator=>{
   const icon=indicator.querySelector('.app-icon'),glyph=icon.querySelector('.icon-glyph'),box=indicator.getBoundingClientRect(),rect=glyph.getBoundingClientRect(),style=getComputedStyle(glyph),iconBox=icon.getBoundingClientRect()
   const ctx=document.createElement('canvas').getContext('2d');ctx.font=style.fontSize+' '+style.fontFamily
   const m=ctx.measureText(glyph.textContent),baseline=rect.y+(parseFloat(style.lineHeight)-m.fontBoundingBoxAscent-m.fontBoundingBoxDescent)/2+m.fontBoundingBoxAscent
   const selected=document.createElement('span');selected.style.color='var(--on-selected)';indicator.append(selected)
   const expectedColor=getComputedStyle(selected).color;selected.remove()
   return {width:box.width,fontSize:style.fontSize,color:style.color,expectedColor,
    boxX:iconBox.x+iconBox.width/2-box.x-box.width/2,boxY:iconBox.y+iconBox.height/2-box.y-box.height/2,
    inkX:rect.x+(m.actualBoundingBoxRight-m.actualBoundingBoxLeft)/2-box.x-box.width/2,
    inkY:baseline+(m.actualBoundingBoxDescent-m.actualBoundingBoxAscent)/2-box.y-box.height/2}
  }))
  for(const row of geometry){
   const message=[mode,theme,pack].join('/')+': '+JSON.stringify(row)
   assert(Math.abs(row.boxX)<.1&&Math.abs(row.boxY)<.1,message)
   assert(Math.abs(row.inkX)<=1&&Math.abs(row.inkY)<=1,message)
   assert.equal(row.color,row.expectedColor,message)
  }
  if(mode==='dark'&&theme==='md3')await page.screenshot({path:root+'/../.screenshots/checkbox-current/'+pack+'.png'})
 }
 await page.locator('.messages-heading label').click();assert.equal(await notification.isChecked(),false,'Label toggles the native input')
 await notification.focus();await page.keyboard.press('Space');assert.equal(await notification.isChecked(),true)
 const box=await page.locator('.messages-heading .app-icon').boundingBox()
 await page.touchscreen.tap(box.x+box.width/2,box.y+box.height/2);assert.equal(await notification.isChecked(),false,'Decorative glyph does not block taps')
 const disabled=page.getByRole('checkbox',{name:'Disabled checkbox',exact:true});assert(await disabled.isDisabled())
 const disabledBox=await disabled.boundingBox()
 await page.mouse.click(disabledBox.x+disabledBox.width/2,disabledBox.y+disabledBox.height/2);assert(await disabled.isChecked())
 assert(await page.getByRole('checkbox',{name:'Mixed checkbox',exact:true}).evaluate(input=>input.indeterminate))
 assert.deepEqual(errors,[])
 console.log('PASS checkbox geometry: five icon packs, three themes, light/dark, regular/compact/mixed, selected text color, label/keyboard/touch/disabled')
} finally {clearTimeout(deadline);await browser?.close();await server?.close()}
