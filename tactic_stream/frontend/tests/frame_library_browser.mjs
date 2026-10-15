import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
import {surface,compareSurface} from './frame_capture.mjs'

const root=fileURLToPath(new URL('../../',import.meta.url)),output=root+'tools/frame_foundation/output/administration/'
const native=JSON.parse(await readFile(output+'native.json','utf8')),fixture=JSON.parse(await readFile(output+'fixture.json','utf8'))
const server=await createServer({root,configFile:false,resolve:{alias:{vue:root+'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},plugins:[vue()],logLevel:'error',server:{host:'127.0.0.1',port:0,watch:{ignored:['**/.tmp/**','**/.venv/**','**/output/**']}}})
await server.listen()
let browser
try{
 browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
 const captures=[]
 for(const width of [1100,1600]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto(server.resolvedUrls.local[0]+'tools/frame_foundation/library.html')
  await page.locator('[data-frame="adminSection_workflow"]:visible').click()
  await page.waitForFunction(()=>window.libraryHarness?.workflow.value)
  await page.evaluate(fixture=>window.libraryHarness.workflow.value.accept(fixture),fixture)
  await page.waitForFunction(()=>window.libraryHarness.workflow.value.viewport.height>300)
  await page.locator('#administration-workflow-library [data-frame="adminWorkflowSearch"]').waitFor()
  await page.evaluate(()=>document.fonts.ready)
  await page.mouse.move(width-1,899)
  const reference=native.find(row=>!row.original&&row.width===width)
  const counts=await compareSurface(page,'.administration-frame-shell',await surface(page,'.administration-frame-shell'),reference,'Whole Workflow '+width)
  const image='stream-'+width+'.png'
  await page.screenshot({path:output+image,animations:'disabled'})
  assert.deepEqual(errors,[])
  captures.push({width,image,...counts})
  await page.close()
 }
 await writeFile(output+'stream.json',JSON.stringify(captures,null,2))
 console.log('Whole Workflow: actual Shell + catalog + editor, Qt/Vue geometry/styles on the same original fixture at two widths passed')
}finally{await browser?.close();await server.close()}
