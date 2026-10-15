import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({headless:true})
try {
  const page = await browser.newPage({viewport:{width:1440,height:940}})
  page.setDefaultTimeout(12000)
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'})))
  await page.goto(process.argv[2]+'/projects/'+process.env.STREAM_CHECK_PROJECT+'/?search_type=cg/assets')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Sign in',exact:true}).click()
  await selectProject(page,process.env.STREAM_CHECK_PROJECT)
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  let release
  const gate = new Promise(resolve => {release=resolve})
  await page.route('**/ui/assets/KnowledgeBase.css',async route => {await gate;await route.abort()})
  await page.getByLabel('Workspace panels',{exact:true}).click()
  await page.getByLabel('Browsing',{exact:true}).click()
  await page.getByRole('menuitemradio',{name:'Knowledge Base',exact:true}).click()
  const dock = page.locator('[data-dock="knowledge"]')
  await dock.getByRole('status').filter({hasText:'Loading interface'}).waitFor()
  release()
  const alert = dock.getByRole('alert').filter({hasText:'Unable to load the interface'})
  await alert.waitFor()
  for (const width of [1440,390]) {
    await page.setViewportSize({width,height:900})
    await alert.waitFor()
    await page.waitForFunction(() => {
      const dock = document.querySelector('[data-dock="knowledge"]'), alert = dock.querySelector('[role="alert"]')
      const pane = dock.getBoundingClientRect(), box = alert.getBoundingClientRect()
      return box.width>200 && box.x>=pane.x && box.right<=pane.right+1
    })
    const box = await alert.boundingBox(), pane = await dock.boundingBox()
    assert.ok(box.width>200,'Load error must not collapse into a narrow strip')
    assert.ok(box.x>=pane.x && box.x+box.width<=pane.x+pane.width+1,'Load error stays inside the Knowledge Base dock')
    assert.equal(await page.locator('#app').evaluate(root => [...root.querySelectorAll('[role="alert"]')].filter(node => node.textContent.includes('Unable to load the interface') && !node.closest('[data-dock="knowledge"]')).length),0)
  }
  await page.screenshot({path:'../.screenshots/knowledge-dock-load-error.png',animations:'disabled'})
  await page.unroute('**/ui/assets/KnowledgeBase.css')
  await page.reload()
  await dock.locator('.knowledge-base').waitFor()
  assert.equal(await dock.getByRole('alert').filter({hasText:'Unable to load the interface'}).count(),0)
  const response = await page.request.get(process.argv[2]+'/ui/assets/KnowledgeBase.css')
  assert.equal(response.status(),200)
  assert.equal(response.headers()['cache-control'],'public, no-cache')
  const cached = await page.request.get(process.argv[2]+'/ui/assets/KnowledgeBase.css',{headers:{'If-None-Match':response.headers().etag}})
  assert.equal(cached.status(),304,'Stable CSS validates against the current build')
  await page.screenshot({path:'../.screenshots/knowledge-dock-load-restored.png',animations:'disabled'})
  console.log('PASS: Knowledge Base loading/error stay inside desktop/phone dock, reload restores content, stable CSS uses ETag revalidation')
} finally {await browser.close()}
