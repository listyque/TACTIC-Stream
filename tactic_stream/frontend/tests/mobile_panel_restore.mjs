import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { captureLayout, defaults, place } from '../src/features/workspace/docks.js'
import { selectProject } from './project_selection.mjs'

const layout = defaults()
for (const id of ['tasks','commit_queue']) {
  layout.panels[id].visible = true
  layout.layout = place(layout.layout,id,'right')
}
layout.compactActive = 'results'
const browser = await chromium.launch({ headless:true })
const page = await browser.newPage({ viewport:{width:390,height:844},isMobile:true,hasTouch:true })
page.setDefaultTimeout(12000)
const errors = []
page.on('pageerror',error => errors.push(error.message))
const project = process.env.STREAM_CHECK_PROJECT
try {
  await page.addInitScript(value => {
    if (!localStorage.getItem('panel-restore-fixture')) {
      localStorage.setItem('tactic_stream.docks.admin',JSON.stringify(value))
      localStorage.setItem('panel-restore-fixture','true')
    }
    localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'}))
  },layout)
  await page.goto(process.argv[2]+'/projects/'+project+'/?search_type=cg/assets')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Sign in',exact:true}).tap()
  await selectProject(page,project)
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  await page.screenshot({path:'../.screenshots/mobile-panel-restore.png',animations:'disabled'})
  assert.equal(await page.locator('dialog.commit-queue[open]').count(),0,'Restoring inactive docks must not open a modal')
  await page.locator('[data-dock="results"]').waitFor()
  await page.reload()
  await page.locator('[data-dock="results"]').waitFor()
  assert.equal(await page.locator('dialog.commit-queue[open]').count(),0)
  await page.locator('.settings-menu > summary').tap()
  await page.getByRole('button',{name:'Commit Queue',exact:true}).tap()
  const queue = page.locator('[data-dock="commit_queue"]')
  await queue.waitFor()
  await queue.getByRole('button',{name:'Back to search',exact:true}).tap()
  await page.locator('[data-dock="results"]').waitFor()
  assert.equal(await page.locator('[data-dock="commit_queue"]').isVisible(),false,'Closing the queue must return to search')
  await page.getByRole('button',{name:'Open navigation',exact:true}).tap()
  await page.getByLabel('Active panel',{exact:true}).selectOption('description')
  await page.getByRole('button',{name:'Close navigation',exact:true}).first().tap()
  await page.getByRole('button',{name:'Back to search',exact:true}).tap()
  await page.locator('[data-dock="results"]').waitFor()
  await page.screenshot({path:'../.screenshots/mobile-panel-return.png',animations:'disabled'})
  const restored = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true})
  restored.setDefaultTimeout(12000)
  restored.on('pageerror',error => errors.push(error.message))
  const workspace = await page.evaluate(() => JSON.parse(localStorage.getItem('tactic_stream.workspace.admin')))
  const queueLayout = {...captureLayout(layout),presentation:{maximized:'',compactActive:'commit_queue'}}
  for (const project of Object.values(workspace)) for (const section of project.sections) for (const tab of section.tabs) tab.workspaceLayout = queueLayout
  await restored.addInitScript(value => {
    localStorage.setItem('tactic_stream.docks.admin',JSON.stringify(value.docks))
    localStorage.setItem('tactic_stream.workspace.admin',JSON.stringify(value.workspace))
    localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'}))
  },{docks:{...layout,compactActive:'commit_queue'},workspace})
  await restored.goto(process.argv[2]+'/projects/'+project+'/?search_type=cg/assets')
  await restored.getByLabel('Login',{exact:true}).fill('admin')
  await restored.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await restored.getByRole('button',{name:'Sign in',exact:true}).tap()
  await restored.locator('[data-dock="commit_queue"]').waitFor()
  assert.equal(await restored.locator('dialog.commit-queue[open]').count(),0,'Restored queue stays a pane, not a modal')
  await restored.screenshot({path:'../.screenshots/mobile-panel-restored-queue.png',animations:'disabled'})
  const contentBox = await restored.locator('#dock-commit_queue').boundingBox()
  const queueBox = await restored.locator('.commit-queue-docked').boundingBox()
  assert.ok(queueBox.y >= contentBox.y && queueBox.y + queueBox.height <= contentBox.y + contentBox.height + 1,'Docked queue must stay inside its pane and leave Back reachable')
  await restored.getByRole('button',{name:'Back to search',exact:true}).tap()
  await restored.locator('[data-dock="results"]').waitFor()
  await restored.close()
  assert.deepEqual(errors,[])
  console.log('PASS: inactive task/queue restoration, reload without a modal, queue Back returns to Search, restored active queue has a visible Back')
} catch(error) {
  await page.screenshot({path:'../.screenshots/mobile-panel-failure.png',animations:'disabled'}).catch(()=>{})
  throw error
} finally { await browser.close() }
