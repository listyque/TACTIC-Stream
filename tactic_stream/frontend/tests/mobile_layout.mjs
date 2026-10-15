import { closeInspector } from './inspector_helpers.mjs'
import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({headless:true})
const page = await browser.newPage({viewport:{width:320,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2})
page.setDefaultTimeout(12000)
const errors = []
page.on('pageerror',error => errors.push(error.message))
const mobile = () => page.locator('.workspace-browser .mobile-results:visible')
const screen = () => mobile().locator('.mobile-result-screen').last()
const header = () => mobile().locator('.mobile-result-header')
const back = () => header().getByRole('button',{name:/^(Back|Назад)$/}).tap()
async function openNotes() {
  await header().getByRole('button',{name:'Notes',exact:true}).tap()
  const chooser = page.getByRole('dialog',{name:'Choose process',exact:true})
  await chooser.or(page.getByRole('region',{name:'Task Inspector',exact:true})).waitFor()
  if (await chooser.isVisible()) await chooser.getByRole('menuitem',{name:/publish/i}).tap()
}
async function geometry() {
  await page.waitForFunction(() => !document.querySelector('.mobile-result-forward-enter-active,.mobile-result-back-enter-active'))
  const failures = await mobile().locator('article').evaluateAll(items => items.flatMap(item => {
    const copy = item.querySelector('.result-item-copy'), text = [...copy.children].map(node => node.getBoundingClientRect())
    const controls = [...item.querySelectorAll('.result-mobile-actions button')].map(node => node.getBoundingClientRect())
    const overlap = text.some(a => controls.some(b => Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1))
    const title = item.querySelector('.result-title-line')
    return overlap || title.scrollWidth > title.clientWidth + 1 ? [item.getAttribute('aria-label')] : []
  }))
  assert.deepEqual(failures,[],'Titles/subtitles must stay clear of controls even on narrow phones')
  const asymmetry = await mobile().locator('.result-item-object:not(.result-mobile-header)').evaluateAll(items => items.flatMap(item => {
    const box = item.getBoundingClientRect(), preview = item.querySelector('.result-preview').getBoundingClientRect()
    const copy = item.querySelector('.result-item-copy').getBoundingClientRect(), actions = item.querySelector('.result-mobile-actions').getBoundingClientRect()
    const next = item.querySelector('.result-mobile-next').getBoundingClientRect(), style = getComputedStyle(item)
    const centered = Math.abs((preview.top+preview.bottom-box.top-box.bottom)/2)<1 && Math.abs((next.top+next.bottom-box.top-box.bottom)/2)<1
    return centered && style.paddingLeft === style.paddingRight && style.paddingTop === style.paddingBottom && Math.abs(copy.left-actions.left)<1 ? [] : [item.getAttribute('aria-label')]
  }))
  assert.deepEqual(asymmetry,[],'Subject cards have equal insets, centered preview/navigation and actions aligned to the text')
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false)
}
try {
  await page.addInitScript(() => {
    if (!localStorage.getItem('tactic_stream.appearance')) localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'}))
  })
  const project = process.env.STREAM_CHECK_PROJECT
  await page.goto(process.argv[2]+'/projects/'+project+'/?search_type=cg/assets')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Sign in',exact:true}).tap()
  await selectProject(page,project)
  for (const language of ['en','ru']) {
    await page.evaluate(language => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language})),language)
    await page.reload()
    for (const width of [320,360,390]) {
      await page.setViewportSize({width,height:844})
      const arm = screen().locator('article[data-result-key*="code=DEMO_ARM"]').first()
      await arm.waitFor()
      await geometry()
      await page.screenshot({path:'../.screenshots/mobile-layout-'+language+'-'+width+'-list.png',animations:'disabled'})
      await arm.locator('strong').tap()
      await header().locator('h2',{hasText:'Robot Arm'}).waitFor()
      await geometry()
      const hostBox = await page.locator('.workspace-browser').boundingBox(), titleBox = await header().boundingBox()
      assert.ok(Math.abs(hostBox.x-titleBox.x)<1 && Math.abs(hostBox.width-titleBox.width)<1,'Detail header must reach the workspace edges')
      await page.screenshot({path:'../.screenshots/mobile-layout-'+language+'-'+width+'-object.png',animations:'disabled'})
      await back()
    }
  }
  await page.evaluate(() => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'})))
  await page.reload()
  await screen().locator('article[data-result-key*="code=DEMO_ARM"]').first().locator('strong').tap()
  await openNotes()
  const inspector = page.getByRole('region',{name:'Task Inspector',exact:true})
  await inspector.getByLabel('Note text',{exact:true}).fill('Mobile Back draft')
  assert.equal(await page.locator('.notification-card[data-kind="complete"]').count(),0,'Routine success does not cover the mobile workspace')
  await page.setViewportSize({width:1440,height:1000})
  const desktopToast = page.locator('.notification-card[data-kind="complete"]').filter({hasText:'Server operation completed'}).first()
  await desktopToast.getByText('Server operation completed',{exact:true}).waitFor()
  assert.equal((await desktopToast.locator('.image-picker-preview').boundingBox()).width,46,'Desktop keeps its existing toast proportions')
  await desktopToast.locator('.notification-detail').waitFor()
  await page.setViewportSize({width:390,height:844})
  await page.locator('[data-dock="notes"]').getByRole('button',{name:'Help',exact:true}).tap()
  const help = page.locator('dialog.help-view[open]')
  await help.getByRole('button',{name:'Back',exact:true}).tap()
  await help.waitFor({state:'hidden'})
  await closeInspector(page)
  await inspector.waitFor({state:'hidden'})
  await openNotes()
  await inspector.getByLabel('Note text',{exact:true}).waitFor()
  assert.equal(await inspector.getByLabel('Note text',{exact:true}).inputValue(),'Mobile Back draft','Back must retain the note draft')
  await page.screenshot({path:'../.screenshots/mobile-layout-inspector.png',animations:'disabled'})
  await closeInspector(page)
  await header().getByRole('button',{name:'Add files',exact:true}).tap()
  const upload = page.getByRole('dialog',{name:'Save snapshot',exact:true})
  await upload.locator('input[type=file]').setInputFiles({name:'draft.txt',mimeType:'text/plain',buffer:Buffer.from('Do not upload')})
  await upload.getByRole('button',{name:'Back',exact:true}).tap()
  await upload.getByRole('button',{name:'Discard',exact:true}).waitFor()
  assert.equal(await upload.isVisible(),true,'Back must preserve the upload discard guard')
  await upload.getByRole('button',{name:'Discard',exact:true}).tap()
  await upload.waitFor({state:'hidden'})
  await openNotes()
  await inspector.getByLabel('Note text',{exact:true}).waitFor()
  const explanation = 'Mobile error: ' + 'Detailed explanation. '.repeat(45) + 'END OF ERROR'
  await page.route('**/admin/rpc',route => route.request().postDataJSON()?.method === 'execute_cmd'
    ? route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:explanation})}) : route.continue())
  await inspector.locator('.inspector-process > summary').tap()
  await inspector.getByRole('menuitemradio',{name:'model',exact:true}).tap()
  const errorToast = page.locator('.notification-card[data-kind="error"]').filter({hasText:'Mobile error:'})
  const errorText = errorToast.locator('.notification-message')
  await errorText.waitFor()
  assert.ok((await errorToast.boundingBox()).height <= 88,'Long errors must stay compact')
  assert.match(await errorText.innerText(),/END OF ERROR$/,'Error information must remain available')
  await errorText.evaluate(element => { element.scrollTop = element.scrollHeight })
  assert.ok(await errorText.evaluate(element => element.scrollTop > 0),'Long error text stays scrollable')
  await errorToast.getByRole('button',{name:'Dismiss notification',exact:true}).tap()
  await page.unroute('**/admin/rpc')
  await closeInspector(page)
  assert.deepEqual(errors,[])
  console.log('PASS: 320/360/390 EN/RU titles clear of controls, edge-to-edge header, inspector/nested Help Back, retained note draft, upload discard guard, compact mobile completion/scrollable error toast, desktop toast retained')
} catch(error) {
  await page.screenshot({path:'../.screenshots/mobile-layout-failure.png',animations:'disabled'}).catch(()=>{})
  throw error
} finally { await browser.close() }
