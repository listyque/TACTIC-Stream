import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({headless:true})
const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true})
page.setDefaultTimeout(12000)
const errors = []
let armPreview
page.on('pageerror',error => errors.push(error.message))
page.on('response',async response => {
  if (!response.url().endsWith('/admin/result-items') || !response.ok()) return
  const data = await response.json()
  const item = data.result?.items?.find(item => item.record.code === 'DEMO_ARM')
  if (item) armPreview = item.preview
})
const arm = () => page.locator('.mobile-result-screen article[data-result-key*="code=DEMO_ARM"]').first()
const header = () => page.locator('.mobile-result-header')
async function loaded(item) {
  await item.locator('.result-preview img').waitFor()
  await page.waitForFunction(() => [...document.querySelectorAll('.mobile-results .result-preview img')].some(image => image.complete && image.naturalWidth > 0))
}
async function geometry(item,flat=false) {
  const web = armPreview.files.find(file => file.type === 'web')
  assert.ok(web?.href,'Native preview supplies a web image')
  assert.equal(await item.locator('.result-preview img').getAttribute('src'),web.href,'Mobile card and header use web, not icon')
  const values = await item.evaluate(element => {
    const box = element.getBoundingClientRect(), preview = element.querySelector('.result-preview'), image = preview.querySelector('.image-picker-preview')
    return {width:box.width,height:box.height,preview:preview.getBoundingClientRect().toJSON(),style:getComputedStyle(image).maskImage,
      radius:getComputedStyle(image).borderRadius,pointer:getComputedStyle(preview).pointerEvents,
      blur:getComputedStyle(image,'::after').backdropFilter,blurMask:getComputedStyle(image,'::after').maskImage,
      rail:getComputedStyle(element.querySelector('.result-surface'),'::before').borderLeftWidth,
      railTop:getComputedStyle(element.querySelector('.result-surface'),'::before').borderTopWidth,
      railBottom:getComputedStyle(element.querySelector('.result-surface'),'::before').borderBottomWidth,
      railRadius:getComputedStyle(element.querySelector('.result-surface'),'::before').borderRadius,
      surfaceRadius:getComputedStyle(element.querySelector('.result-surface')).borderRadius,
      images:preview.querySelectorAll('img').length,
      imageCenter:(preview.querySelector('img').getBoundingClientRect().left+preview.querySelector('img').getBoundingClientRect().right)/2-box.left,
      imageY:(preview.querySelector('img').getBoundingClientRect().top+preview.querySelector('img').getBoundingClientRect().bottom)/2-box.top,
      flat:getComputedStyle(preview).borderRadius,overflow:element.scrollWidth>element.clientWidth}
  })
  assert.ok(values.preview.width >= values.width*.4,'Image occupies the left part of the item')
  assert.ok(Math.abs(values.preview.height-values.height)<1,'Image fills the entire item height without grey top/bottom strips')
  assert.equal(values.radius,'0px','Loaded image is not clipped to a circle')
  assert.match(values.style,/linear-gradient/)
  assert.equal(values.blur,'blur(8px)')
  assert.match(values.blurMask,/linear-gradient/,'Blur builds gradually towards the right')
  assert.equal(values.images,1,'Blur reuses the original image without a second image element')
  assert.ok(Math.abs(values.imageCenter-(flat ? 57 : 33))<1,'Image is centred where the original circular preview stood')
  assert.ok(Math.abs(values.imageY-values.height/2)<1,'Image remains vertically centred')
  if (!flat) {
    assert.equal(values.rail,'2px','The left edge stays thin at its widest point')
    assert.equal(values.railTop,'0px','The edge tapers to zero at the upper corner')
    assert.equal(values.railBottom,'0px','The edge tapers to zero at the lower corner')
    assert.equal(values.railRadius,values.surfaceRadius,'The accent follows the same curve as the surface without a gap')
  }
  assert.equal(values.pointer,'none','Preview does not intercept touch actions')
  assert.equal(values.overflow,false)
  if (flat) assert.equal(values.flat,'0px','Detail header stays rectangular')
}
try {
  await page.addInitScript(() => {
    if (!localStorage.getItem('tactic_stream.appearance')) localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'ru'}))
  })
  await page.goto(process.argv[2]+'/projects/'+process.env.STREAM_CHECK_PROJECT+'/?search_type=cg/assets')
  await page.getByLabel('Логин',{exact:true}).fill('admin')
  await page.getByLabel('Пароль',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Войти',exact:true}).tap()
  await selectProject(page,process.env.STREAM_CHECK_PROJECT)
  for (const mode of ['dark','light']) {
    await page.evaluate(mode => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode,language:'ru'})),mode)
    await page.reload()
    for (const width of [320,390]) {
      await page.setViewportSize({width,height:844})
      await loaded(arm())
      await geometry(arm())
      await page.mouse.move(1,1)
      await page.evaluate(() => document.activeElement.blur())
      await page.locator('.configured-view[data-workspace-current="true"] .mobile-result-screen[data-screen-key="root"]').evaluate(element=>{ element.scrollTop=0 })
      await page.locator('.workspace-browser > .workspace-tabs').waitFor()
      await page.screenshot({path:'../.screenshots/mobile-preview-'+mode+'-'+width+'-list.png',animations:'disabled'})
      await arm().locator('.workspace-menu > summary').tap()
      await page.locator('.account-panel:visible').waitFor()
      await page.keyboard.press('Escape')
      await page.mouse.move(1,1)
      await page.evaluate(() => document.activeElement.blur())
      const box = await arm().boundingBox()
      await page.touchscreen.tap(box.x+20,box.y+box.height/2)
      await header().locator('h2',{hasText:'Robot Arm'}).waitFor()
      await loaded(header().locator('article'))
      await geometry(header().locator('article'),true)
      await page.locator('.mobile-result-screen .mobile-result-list article').first().waitFor()
      await page.waitForFunction(() => !document.querySelector('.mobile-result-forward-enter-active,.mobile-result-forward-leave-active,.mobile-result-back-enter-active,.mobile-result-back-leave-active'))
      await page.screenshot({path:'../.screenshots/mobile-preview-'+mode+'-'+width+'-object.png',animations:'disabled'})
      await header().getByRole('button',{name:'Назад',exact:true}).tap()
    }
  }
  await page.route('**/admin/result-items',async route => {
    const response = await route.fetch(), body = await response.json()
    for (const item of body.result?.items || []) if (item.record.code === 'DEMO_ARM') item.preview.files = item.preview.files.filter(file => file.type !== 'web')
    await route.fulfill({response,json:body})
  })
  await page.reload()
  await loaded(arm())
  assert.equal(await arm().locator('.result-preview img').getAttribute('src'),armPreview.image,'Objects without web retain their existing preview')
  await page.unroute('**/admin/result-items')
  await page.route('**/assets/**',route => route.request().resourceType() === 'image' ? route.abort() : route.continue())
  await page.reload()
  await arm().locator('.result-preview span:not(.app-icon)').waitFor()
  assert.equal(await arm().locator('.result-preview').evaluate(element=>getComputedStyle(element).position),'absolute','Failed image keeps the same preview area without a layout jump')
  const fallback = arm().locator('.image-picker-preview')
  assert.match(await fallback.evaluate(element=>getComputedStyle(element).backgroundImage),/linear-gradient/,'Initials use a fading accent background')
  assert.equal(await fallback.evaluate(element=>getComputedStyle(element).borderRadius),'0px','Initials are not placed in a circle')
  assert.equal(await fallback.locator('span:not(.app-icon)').innerText(),'RA')
  assert.ok(await arm().evaluate(element=>{ const box=element.getBoundingClientRect(),text=element.querySelector('.result-preview span:not(.app-icon)').getBoundingClientRect(); return Math.abs((text.left+text.right)/2-box.left-33)<1 }),'Fallback initials share the original preview centre')
  await page.locator('.configured-view[data-workspace-current="true"] .mobile-result-screen[data-screen-key="root"]').evaluate(element=>{ element.scrollTop=0 })
  await page.locator('.workspace-browser > .workspace-tabs').waitFor()
  await page.screenshot({path:'../.screenshots/mobile-preview-fallback.png',animations:'disabled'})
  await page.unroute('**/assets/**')
  await page.setViewportSize({width:1440,height:950})
  await page.reload()
  const desktop = page.locator('.workspace-results .result-item-object[data-result-key*="code=DEMO_ARM"]').first()
  await desktop.locator('.result-preview img').waitFor()
  assert.equal(await desktop.locator('.result-preview img').getAttribute('src'),armPreview.image,'Desktop keeps its native icon preview')
  assert.equal(await desktop.locator('.image-picker-preview').evaluate(element=>getComputedStyle(element).borderRadius),'50%','Desktop preview retains its presentation')
  assert.deepEqual(errors,[])
  console.log('PASS mobile preview: web image in card/header, missing-web fallback, full-height left gradient, dark/light 320/390, menu and image taps, rectangular detail header, failed-image fallback, desktop icon unchanged')
} catch(error) {
  await page.screenshot({path:'../.screenshots/mobile-preview-failure.png',animations:'disabled'}).catch(()=>{})
  throw error
} finally { await browser.close() }
