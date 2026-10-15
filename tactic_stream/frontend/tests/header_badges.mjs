import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({headless:true})
try {
  const page = await browser.newPage({viewport:{width:1440,height:900},hasTouch:true})
  page.setDefaultTimeout(12000)
  const errors = []
  page.on('pageerror',error=>errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'})))
  await page.goto(process.argv[2]+'/projects/'+process.env.STREAM_CHECK_PROJECT+'/?search_type=cg/assets')
  await page.getByLabel('Login',{exact:true}).fill('admin')
  await page.getByLabel('Password',{exact:true}).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button',{name:'Sign in',exact:true}).click()
  await selectProject(page,process.env.STREAM_CHECK_PROJECT)
  await page.locator('.workspace-results[aria-busy="false"]').waitFor()
  for (const width of [1440,390,320]) {
    await page.setViewportSize({width,height:900})
    await page.evaluate(async () => {
      const app = document.querySelector('#app').__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy
      app.messageUnread = 120; app.activityUnread = 12; app.checkins = [{status:'Ready'}]
      await app.$nextTick()
    })
    const account = page.locator('.account-menu > summary')
    assert.equal(await account.locator('.app-button-badge').innerText(),'99+')
    const controls = width>700 ? [account,page.locator('.activity-feed-trigger'),page.locator('.commit-queue-trigger')] : [account]
    for (const control of controls) {
      const geometry = await control.evaluate(node => {
        const b=node.getBoundingClientRect(), badge=node.querySelector('.app-button-badge').getBoundingClientRect()
        return {button:b.toJSON(),badge:badge.toJSON(),overflow:getComputedStyle(node).overflow,
          legacy:node.querySelectorAll('.result-count').length,viewport:innerWidth}
      })
      assert.equal(geometry.overflow,'visible','Badge is not clipped to the button circle')
      assert.equal(geometry.legacy,0,'Counter no longer participates in the icon layout')
      assert.ok(geometry.badge.y<geometry.button.y && geometry.badge.right>geometry.button.right,'Badge sits above the outer right edge')
      assert.ok(geometry.badge.x>=0 && geometry.badge.right<=geometry.viewport,'Badge stays inside the viewport')
    }
    await account.click()
    await page.getByRole('button',{name:'My profile',exact:true}).waitFor()
    await page.keyboard.press('Escape')
    await page.screenshot({path:'../.screenshots/header-badges-'+width+'.png',animations:'disabled'})
  }
  await page.evaluate(async () => {
    const app = document.querySelector('#app').__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy
    app.messageUnread=0;await app.$nextTick()
  })
  assert.equal(await page.locator('.account-menu > summary > .app-button-badge').count(),0)
  assert.deepEqual(errors,[])
  console.log('PASS: account/activity/queue badges sit outside circles, preserve icon layout and menu clicks, fit desktop/390/320 and hide at zero')
} finally {await browser.close()}
