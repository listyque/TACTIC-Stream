import assert from 'node:assert/strict'
import { readFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root=fileURLToPath(new URL('..',import.meta.url)),output=fileURLToPath(new URL('../../.screenshots/notifications-current/',import.meta.url))
const reference=JSON.parse(await readFile(new URL('../../.screenshots/handler-current/system-activity-geometry.json',import.meta.url),'utf8'))
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue'
import AppButton from '/src/controls/AppButton.vue'
import SystemActivity from '/src/features/activity/SystemActivity.vue'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import {notify,resetNotifications} from '/src/features/activity/notifications.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',mode:'dark',fadeAnimations:false,popupAnimations:false});initializeAppearance()
window.appearance=appearance;window.notify=notify;window.resetNotifications=resetNotifications
createApp({data(){return {clicks:0}},mounted(){window.host=this},render(){return h('div',[
 h(AppButton,{label:'Workspace action',onClick:()=>this.clicks++}),h(SystemActivity,{ref:'history'})
])}}).directive('window',windowDirective).mount('#app')
</script></body></html>`
let server,browser
const deadline=setTimeout(()=>browser?.close(),55000)
const near=(actual,expected,label)=>assert(Math.abs(actual-expected)<=2,label+': '+actual+' vs Qt '+expected)
try {
 await mkdir(output,{recursive:true})
 server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/notifications-layout',plugins:[vue(),{
  name:'notifications-layout',configureServer(server){server.middlewares.use(async(req,res,next)=>{
   if(req.url!=='/notifications-test')return next()
   try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
  })},
 }],server:{host:'127.0.0.1',port:0,watch:null}});await server.listen()
 browser=await chromium.launch({headless:true})
 const page=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true}),errors=[]
 page.setDefaultTimeout(7000);page.on('pageerror',error=>errors.push(error.message))
 await page.goto(server.resolvedUrls.local[0]+'notifications-test');await page.waitForFunction(()=>window.host)
 await page.evaluate(()=>{window.host.$refs.history.open();return document.fonts.ready})
 const dialog=page.locator('.system-activity-dialog'),panel=dialog.locator('.activity-feed-panel'),toolbar=dialog.locator('.activity-feed-toolbar'),filters=dialog.getByRole('radiogroup')
 assert.equal(await dialog.evaluate(el=>el.matches(':modal')),false)
 await page.getByRole('button',{name:'Workspace action',exact:true}).click();assert.equal(await page.evaluate(()=>window.host.clicks),1)
 for(const row of reference) {
  const phone=row.width<=700
  await page.setViewportSize({width:phone?row.width:1280,height:phone?row.height+40:900})
  await dialog.evaluate((el,row)=>{el.style.width=row.width+2+'px';el.style.height=row.height+42+'px'},row)
  await page.waitForFunction(width=>document.querySelector('.system-activity-content').clientWidth===width,row.width)
  await page.waitForFunction(compact=>!!document.querySelector('.system-activity-dialog [role="radio"].icon-button')===compact,row.width<760)
  near((await panel.boundingBox()).width,row.notificationsPanel.width,'Panel width')
  near((await toolbar.boundingBox()).width,row.notificationsToolbar.width,'Toolbar width')
  near((await toolbar.boundingBox()).height,row.notificationsToolbar.height,'Toolbar height')
  near((await filters.boundingBox()).width,row.notificationHistoryFilters.width,'Filter width')
  near((await filters.boundingBox()).height,row.notificationHistoryFilters.height,'Filter height')
  const title=await toolbar.locator('.activity-feed-title').boundingBox(),description=await toolbar.locator(':scope > p').boundingBox(),segments=await filters.boundingBox()
  assert(description.y>=title.y+title.height+7 && segments.y>=description.y+description.height+7,'Three separate rows with 8px gaps')
  assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth),'No dialog overflow')
  await page.screenshot({path:output+'ts-notifications-'+row.width+'.png'})
 }
 for(const language of ['en','ru']) {
  await page.setViewportSize({width:1440,height:1000})
  await dialog.evaluate(el=>{el.style.width='1080px';el.style.height='750px'})
  await page.evaluate(language=>window.appearance.language=language,language)
  const checkin=filters.getByRole('radio',{name:'Check-in',exact:true})
  const label=checkin.locator(':scope > span:not(.app-icon):not(.control-ripple-clip)')
  assert.equal(await label.evaluate(el=>getComputedStyle(el).whiteSpace),'nowrap')
  assert((await label.boundingBox()).height<20,'Filter labels stay on one line')
  near((await filters.boundingBox()).width,(await toolbar.boundingBox()).width-20,'Filters fill the toolbar')
  await dialog.screenshot({path:output+'ts-notifications-'+language+'-desktop.png'})
 }
 await page.evaluate(()=>{window.appearance.language='en';window.notify('error','Server fixture','Details','server');window.notify('complete','Check-in fixture','','checkin');window.notify('info','Client fixture','','client')})
 const rows=dialog.locator('.system-activity-event')
 assert.equal(await rows.count(),3)
 await filters.getByRole('radio',{name:'Server',exact:true}).click();assert.equal(await rows.count(),1)
 await filters.getByRole('radio',{name:'Check-in',exact:true}).click();assert.equal(await rows.count(),1)
 await page.keyboard.press('Home');assert.equal(await rows.count(),3)
 await dialog.getByRole('button',{name:'Clear history',exact:true}).click();assert.equal(await rows.count(),0)
 assert(await dialog.getByRole('button',{name:'Clear history',exact:true}).isDisabled())
 await dialog.getByRole('button',{name:'Close Notifications',exact:true}).click()
 await page.evaluate(()=>window.resetNotifications())
 assert.deepEqual(errors,[])
 console.log('PASS Notifications: Qt panel/toolbar/filter geometry, three rows, single-line EN/RU labels, desktop/320/360, nonmodal workspace, filters and clear')
}finally{clearTimeout(deadline);await browser?.close();await server?.close()}
