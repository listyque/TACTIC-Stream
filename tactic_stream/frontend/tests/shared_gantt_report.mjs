import assert from 'node:assert/strict'
import {fileURLToPath, pathToFileURL} from 'node:url'
import {chromium} from 'playwright'

const out=fileURLToPath(new URL('../../tools/shared_ui_demo/output/',import.meta.url))
const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL})
try {
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[]
 page.on('pageerror',error=>errors.push(error.message))
 await page.goto(pathToFileURL(out+'gantt-report.html').href)
 async function images(){await page.waitForFunction(()=>[...document.querySelectorAll('#comparison img')].every(img=>img.complete&&img.naturalWidth>0))}
 await images();assert.equal(await page.locator('#comparison figure').count(),2)
 const frame=page.frames().find(frame=>frame.url().includes('/web/gantt.html'))
 assert(frame,'live Vue iframe');await frame.waitForFunction(()=>window.ganttDemo)
 assert.equal(await frame.evaluate(()=>window.ganttDemo.state.value.tasks.length),12)
 await page.locator('#skeleton').check();assert.equal(await page.locator('#comparison svg').count(),2)
 await page.locator('#overlay').check();assert.equal(await page.locator('#comparison figure').count(),1)
 await page.locator('#mode').selectOption('light');await page.locator('#language').selectOption('en');await page.locator('#size').selectOption('840');await page.locator('#phase').selectOption('wheel-zoom');await images()
 assert.match(await page.locator('#trace').textContent(),/09:13:00/)
 await page.locator('#mode').selectOption('dark');await page.locator('#language').selectOption('ru');await page.locator('#size').selectOption('1100');await page.locator('#phase').selectOption('initial');await page.locator('#overlay').uncheck();await page.locator('#skeleton').uncheck();await images()
 await page.screenshot({path:out+'gantt-report.png'})
 assert.deepEqual(errors,[]);console.log('PASS: report images, paired/overlay/skeleton modes, theme/language/size/scenario, live Vue iframe')
}finally{await browser.close()}
