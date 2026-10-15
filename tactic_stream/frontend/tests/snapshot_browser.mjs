import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'
const [base,output,keyA,keyB,snapshotKey] = process.argv.slice(2)
const browser = await chromium.launch({ headless:true }), page = await browser.newPage({ viewport:{width:1440,height:940} })
await page.context().grantPermissions(['clipboard-read','clipboard-write'])
const projection = JSON.parse(await readFile(`${output}/projection.json`,'utf8'))
page.setDefaultTimeout(12000)
const errors = []; page.on('pageerror',error => errors.push(error.message))
const panel = page.locator('[data-dock="snapshot"]'), content = page.locator('.snapshot-browser')
const options = () => panel.getByLabel('Snapshot Browser options',{exact:true})
async function option(name) { await options().click(); await page.getByRole('menuitemradio',{name,exact:true}).click() }
async function toggle(name) { await options().click(); await page.getByRole('menuitemcheckbox',{name,exact:true}).click() }
async function capture(name) {
  const saved = await content.getAttribute('style')
  await content.evaluate(element => { element._captureParent = element.parentNode; element._captureNext = element.nextSibling; document.body.append(element) })
  try {
    for (const [width,height] of [[440,500],[880,650]]) {
      await content.evaluate((element,{width,height}) => Object.assign(element.style,{position:'fixed',left:'0px',top:'0px',width:width+'px',height:height+'px',zIndex:'10000'}),{width,height})
      await page.waitForTimeout(150); await page.evaluate(() => document.fonts.ready)
      await content.screenshot({path:`${output}/stream-${name}-${width}.png`,animations:'disabled'})
    }
  } finally { await content.evaluate((element,saved) => { element._captureParent.insertBefore(element,element._captureNext); delete element._captureParent; delete element._captureNext; if (saved === null) element.removeAttribute('style'); else element.setAttribute('style',saved) },saved); await page.waitForTimeout(80) }
}
async function selected(row) { await row.click(); await page.waitForFunction(() => !document.querySelector('[data-dock="snapshot"] .snapshot-browser')?.matches('[aria-busy="true"]')) }
try {
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance',JSON.stringify({mode:'dark',language:'en'})))
  await page.goto(base + '/projects/one/?search_type=one%2Fsnapshot_assets')
  await page.getByLabel('Login',{exact:true}).fill('admin'); await page.getByLabel('Password',{exact:true}).fill('private-test-password')
  await page.getByRole('button',{name:'Sign in',exact:true}).click()
  const row = title => page.locator('.workspace-results .result-item:visible').filter({has:page.locator('.result-item-copy > strong',{hasText:title})}).first()
  await row('Snapshot A').waitFor()
  await page.getByLabel('Workspace panels',{exact:true}).click(); await page.getByLabel('Browsing',{exact:true}).click()
  await page.getByRole('menuitemradio',{name:'Snapshot Browser',exact:true}).click(); await panel.waitFor({state:'visible'})
  await capture('empty')
  await selected(row('Snapshot A')); await panel.locator('.snapshot-image img').waitFor(); assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),3)
  await capture('both')
  await panel.getByRole('button',{name:'Next preview',exact:true}).click(); assert.equal(await panel.locator('.snapshot-counter').innerText(),'2 / 3')
  await panel.getByLabel('Snapshot preview',{exact:true}).press('ArrowRight'); assert.equal(await panel.locator('.snapshot-counter').innerText(),'3 / 3')
  await panel.getByLabel('Preview number',{exact:true}).fill('0'); assert.equal(await panel.locator('.snapshot-counter').innerText(),'1 / 3')
  await panel.getByRole('radio',{name:'Fill',exact:true}).click(); assert.equal(await panel.locator('.snapshot-image img').evaluate(image => getComputedStyle(image).objectFit),'cover')
  await panel.getByRole('radio',{name:'Fit',exact:true}).click()
  await toggle('Show All Files'); assert.equal(await panel.locator('.snapshot-file-row.header').count(),3); await capture('all')
  await toggle('Show More Info'); await capture('more')
  await option('Vertical orientation'); await capture('vertical')
  const separator = panel.getByRole('separator',{name:'Resize snapshot panels',exact:true})
  assert.equal(await separator.evaluate(element => getComputedStyle(element).cursor),'ew-resize')
  await separator.press('ArrowRight'); assert.ok(JSON.parse(await page.evaluate(() => localStorage.getItem('tactic_stream.snapshot-browser'))).splitterRatio > .52)
  await option('Files Only'); await capture('files'); assert.equal(await separator.count(),0)
  assert.equal(await panel.locator('.snapshot-file-row[role="option"] .middle-elide').first().evaluate(element => getComputedStyle(element).fontWeight),'400')
  const file = panel.locator('.snapshot-file-list').getByRole('option').first(); await file.click({button:'right'})
  await page.getByRole('button',{name:'Copy File Path',exact:true}).waitFor(); assert.equal(await page.getByRole('button',{name:'Show Folder',exact:true}).isDisabled(),true)
  await page.getByRole('button',{name:'Copy File Path',exact:true}).click()
  await page.waitForFunction(() => navigator.clipboard.readText().then(value => value.includes('/')))
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()),projection.rows.find(row => row.rowType === 'file').fullPath)
  await file.click({button:'right'}); await page.getByRole('button',{name:'Copy To Clipboard',exact:true}).click()
  await page.waitForFunction(() => navigator.clipboard.read().then(items => items.some(item => item.types.includes('image/png'))))
  await file.click({button:'right'})
  // The popup belongs to its exact file, even if another row was previously selected.
  await page.getByRole('button',{name:'Edit Info',exact:true}).click()
  const edit = page.getByRole('dialog',{name:'Record form',exact:true}); await edit.getByRole('heading',{name:'Edit record',exact:true}).waitFor(); assert.equal(await edit.locator('small').first().innerText().then(value => value.startsWith('sthpw/file?')),true)
  await edit.getByLabel('Source Path',{exact:true}).fill('Snapshot Browser verified source')
  await edit.getByRole('button',{name:'Save record',exact:true}).click(); await edit.waitFor({state:'hidden'})
  await file.dblclick(); const preview = page.getByRole('dialog',{name:'File preview',exact:true}); await preview.locator('img').waitFor(); await preview.getByRole('button',{name:'Close preview',exact:true}).click()
  await option('Preview Only'); await capture('preview'); assert.equal(await panel.getByRole('listbox').count(),0)
  await option('Preview and Files'); await option('Horizontal orientation'); await toggle('Show More Info'); await toggle('Show All Files')
  await selected(row('Snapshot B')); await panel.getByText('No files for this selection',{exact:true}).waitFor(); assert.equal(await panel.locator('.snapshot-image img').count(),0)
  await selected(row('Snapshot A'))
  // Changing selection while the old response is in flight cannot restore its files.
  let resume, blocked = true
  await page.route('**/admin/result-items',async route => {
    const data = route.request().postDataJSON()
    if (blocked && data.branch?.kind === 'snapshot_browser' && data.search_keys?.[0] === keyA) { blocked = false; await new Promise(resolve => {resume = resolve}) }
    await route.continue()
  })
  await panel.getByRole('button',{name:'Refresh snapshots',exact:true}).click(); await page.waitForFunction(() => document.querySelector('[data-dock="snapshot"] .snapshot-browser')?.matches('[aria-busy="true"]'))
  await selected(row('Snapshot B')); resume(); await page.waitForTimeout(200); assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),0)
  await page.unroute('**/admin/result-items'); await selected(row('Snapshot A'))
  const publish = page.locator('.workspace-results .result-item-process:visible').filter({hasText:'Publish'}).first()
  await row('Snapshot A').getByRole('button',{name:'Expand item',exact:true}).click(); await publish.waitFor(); await selected(publish)
  assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),3)
  const model = page.locator('.workspace-results .result-item-process:visible').filter({hasText:'Model'}).first(); await selected(model)
  assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),1); await panel.locator('.snapshot-file-list').getByRole('option').first().dblclick()
  await preview.getByText('Model file',{exact:true}).waitFor(); await preview.getByRole('button',{name:'Close preview',exact:true}).click()
  await selected(row('Snapshot A'))
  // A versionless item exposes the context history; a real version exposes only itself.
  await selected(publish)
  const alias = page.locator('.workspace-results .result-item-snapshot:visible').first(); await selected(alias)
  assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),3)
  await alias.getByRole('button',{name:'Expand item',exact:true}).click()
  await page.locator('.workspace-results .result-item-branch:visible').filter({has:page.getByText('Versions',{exact:true})}).first().click()
  const snapshot = page.locator('.workspace-results [data-result-key="' + snapshotKey + '"]:visible'); await snapshot.waitFor(); await selected(snapshot)
  assert.equal(await panel.locator('.snapshot-file-list').getByRole('option').count(),1)
  await panel.locator('.snapshot-file-list').getByRole('option').first().click({button:'right'}); await page.getByRole('button',{name:'Delete',exact:true}).click()
  const deletion = page.getByRole('dialog',{name:'Delete record',exact:true}); await deletion.waitFor(); await deletion.getByRole('button',{name:'Delete record',exact:true}).click(); await deletion.waitFor({state:'hidden'})
  await panel.getByText('No files for this selection',{exact:true}).waitFor()
  await page.goto(base + '/projects/one/?search_type=one%2Fsnapshot_assets'); await row('Snapshot A').waitFor(); await selected(row('Snapshot A'))
  await options().click(); await page.getByRole('menuitemcheckbox',{name:'Show All Files',exact:true}).waitFor()
  await page.screenshot({path:output + '/stream-options-1440.png',animations:'disabled'}); await page.keyboard.press('Escape')
  await panel.getByRole('button',{name:'Help',exact:true}).click(); await page.getByRole('heading',{name:'Snapshot Browser dock',exact:true}).waitFor()
  assert.deepEqual(errors,[])
  console.log('Snapshot Browser: native history, process/snapshot selection, media, exact file editor, options, splitter, refresh races, layout reload and Help passed')
} catch (error) {
  await page.screenshot({path:output + '/failure.png'}); await writeFile(output + '/failure.html',await page.content()); throw error
} finally { await browser.close() }
