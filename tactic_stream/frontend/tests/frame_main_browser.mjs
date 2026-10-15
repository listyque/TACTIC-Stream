import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright'
import {describe} from '../../src/tactic_stream/shared_ui/shell/main_toolbar.ui.mjs'

const output=fileURLToPath(new URL('../../tools/frame_foundation/output/main/',import.meta.url))
const original=JSON.parse(await readFile(output+'original.json','utf8'))
const native=JSON.parse(await readFile(output+'frame.json','utf8'))
assert.deepEqual(native.map(row=>row.geometry),original.map(row=>row.geometry),'Preserve the original Handler layout')
const browser=await chromium.launch({headless:true})
try {
  const page=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true})
  page.setDefaultTimeout(12000)
  const errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.addInitScript(()=>localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false})))
  await page.goto(process.argv[2]+'/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill('private-test-password')
  await page.getByRole('button',{name:'Sign in',exact:true}).click()
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  const rows=[]
  for(const width of [720,900,1280,1920,390,320]) {
    await page.setViewportSize({width,height:900})
    await page.waitForFunction(width=>Math.abs(document.querySelector('[data-main-control="mainAccount"]').getBoundingClientRect().right-(width-(width<=700?4:12)))<.01,width)
    await page.waitForFunction(()=>!document.querySelector('#topbar-system-activity .busy'))
    await page.evaluate(()=>document.fonts.ready)
    const scene=describe({width,compact:width<=700,dccClient:false,progressReveal:0})
    const geometry={}
    for(const node of scene.nodes) {
      if(node.id==='mainDcc') continue
      const control=page.locator('[data-main-control="'+node.id+'"]')
      if(node.visible===false) {assert.equal(await control.isVisible(),false,node.id);continue}
      const bounds=await control.boundingBox()
      assert(bounds,node.id+' is visible')
      geometry[node.id]={x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}
      for(const key of ['x','y','width','height']) assert(Math.abs(bounds[key]-node[key])<.01,`${width} ${node.id}.${key}: ${bounds[key]} vs ${node[key]}`)
      if(width>700) assert.deepEqual(geometry[node.id],native.find(row=>row.width===width).geometry[node.id],'Actual Qt/Vue '+node.id)
    }
    await page.getByLabel('More options',{exact:true}).click()
    await page.locator('.settings-menu[open]').waitFor()
    await page.keyboard.press('Escape')
    await page.mouse.move(0,200)
    await page.getByLabel('Account',{exact:true}).tap()
    await page.locator('.account-menu[open]').waitFor()
    await page.keyboard.press('Escape')
    await page.getByLabel('Project',{exact:true}).click()
    await page.locator('#project-chooser:popover-open').waitFor()
    await page.keyboard.press('Escape')
    await page.mouse.move(0,200)
    const screenshot='stream-'+width+'.png'
    await page.screenshot({path:output+screenshot,clip:{x:0,y:0,width,height:44}})
    rows.push({width,geometry,screenshot})
  }
  assert.deepEqual(errors,[])
  await writeFile(output+'stream.json',JSON.stringify(rows,null,2))
  console.log('Main toolbar: original Qt = Frame Qt = actual Vue geometry; settings/account/project mouse and touch at six sizes passed')
}finally{await browser.close()}
