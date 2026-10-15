import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { captureLayout, defaults, place } from '../src/features/workspace/docks.js'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({headless:true})
const errors = []
try {
  const page = await browser.newPage({viewport:{width:1280,height:900},hasTouch:true})
  page.setDefaultTimeout(12000)
  page.on('pageerror', error => errors.push(error.message))
  const layout = defaults()
  layout.compactActive = 'tasks'
  await page.addInitScript(value => {
    if (!localStorage.getItem('resize-fixture')) {
      localStorage.setItem('tactic_stream.docks.admin',JSON.stringify(value))
      localStorage.setItem('resize-fixture','true')
    }
    localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'}))
  },layout)
  await page.goto(process.argv[2]+'/projects/'+process.env.STREAM_CHECK_PROJECT+'/?search_type=cg/assets')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Sign in',exact:true}).click()
  await selectProject(page,process.env.STREAM_CHECK_PROJECT)
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  const search = page.locator('[data-dock="results"]'), tasks = page.locator('[data-dock="tasks"]')
  assert.equal(await search.isVisible(),true)
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(() => document.querySelector('.phone-panel-heading'))
  assert.equal(await search.isVisible(),true,'Hidden stored Task Manager must not replace Search on resize')
  assert.equal(await tasks.isVisible(),false)
  await search.locator('.mobile-result-list article').first().waitFor()
  await page.screenshot({path:'../.screenshots/mobile-panel-resize-search.png',animations:'disabled'})
  await page.setViewportSize({width:1280,height:900})
  await page.waitForFunction(() => !document.querySelector('.phone-panel-heading'))
  assert.equal(await search.isVisible(),true)

  layout.panels.tasks.visible = true
  layout.layout = place(layout.layout,'tasks','center','results')
  layout.layout.active = 'results'
  const configuration = {...captureLayout(layout),presentation:{maximized:'',compactActive:'tasks'}}
  await page.evaluate(value => document.querySelector('#app').__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy.$refs.docks.apply(value),configuration)
  assert.equal(await search.isVisible(),true)
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(() => document.querySelector('.phone-panel-heading'))
  assert.equal(await search.isVisible(),true,'Inactive desktop stack tab must not replace Search either')

  await page.getByRole('button',{name:'Open navigation',exact:true}).click()
  await page.getByLabel('Active panel',{exact:true}).selectOption('tasks')
  await page.getByRole('button',{name:'Close navigation',exact:true}).first().click()
  await tasks.waitFor()
  await page.locator('.mobile-task-card').first().waitFor()
  await page.setViewportSize({width:1280,height:900})
  await page.waitForFunction(() => !document.querySelector('.phone-panel-heading'))
  await page.locator('.settings-menu > summary').click()
  await page.locator('.settings-menu').getByRole('button',{name:'Task Manager',exact:true}).click()
  await tasks.waitFor()
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(() => document.querySelector('.phone-panel-heading'))
  await tasks.waitFor()
  assert.ok(await page.locator('.mobile-task-card').count(),'An explicitly opened Task Manager keeps its loaded tasks across resize')
  await page.getByRole('button',{name:'Back to search',exact:true}).click()
  await search.waitFor()
  await page.setViewportSize({width:1280,height:900})
  await page.waitForFunction(() => !document.querySelector('.phone-panel-heading'))
  await tasks.getByRole('button',{name:'Close panel: Task Manager',exact:true}).click()
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(() => document.querySelector('.phone-panel-heading'))
  await search.waitFor()
  assert.equal(await tasks.isVisible(),false,'Back to Search persists through another resize')
  assert.deepEqual(errors,[])
  console.log('PASS: hidden and inactive Task Manager never replace Search; explicit tasks and Back survive desktop/phone resize')
} finally { await browser.close() }
