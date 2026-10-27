import assert from 'node:assert/strict'
import {chromium} from 'playwright'
import {openViewActions} from './project_selection.mjs'

const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL})
const page=await browser.newPage({viewport:{width:1440,height:950},hasTouch:true,colorScheme:'dark'})
page.setDefaultTimeout(15000)
const errors=[],writes=[]
page.on('pageerror',error=>errors.push(error.message))
page.on('request',request=>{if(request.url().endsWith('/admin/widget-configuration/save'))writes.push(request.postDataJSON())})
const editor=page.locator('.layout-editor'),admin=page.getByRole('dialog',{name:'Administration',exact:true})
const control=id=>admin.locator('[data-frame="'+id+'"]:visible')
const ready=()=>page.waitForFunction(()=>document.querySelector('.layout-editor')?.getAttribute('aria-busy')==='false')
async function section(id,value){const button=control(id+'_'+value);if(await button.count())await button.click();else await control(id).selectOption(value)}
async function field(id,value){await control(id).fill(value);await control(id).blur()}
async function selectView(view){
 await control('layoutView').selectOption(view);await ready();await section('layoutPages','design')
 await editor.locator('.layout-live-preview .result-presentation').waitFor()
}
async function openEditor(){await openViewActions(page);await page.getByRole('button',{name:'Edit layouts',exact:true}).click();await ready()}
async function openView(){
 const popupPromise=page.waitForEvent('popup');await control('layoutOpenView').click();const popup=await popupPromise
 await popup.waitForLoadState('domcontentloaded');assert(await admin.isVisible(),'Opening the saved result keeps the editor')
 await control('layoutView').selectOption(await control('layoutView').inputValue());assert(await admin.isVisible(),'Editor remains interactive')
 await control('administrationCloseButton').click();await admin.waitFor({state:'hidden'})
 await page.goto(popup.url());await popup.close()
}
async function discard(){await control('adminDiscardDocument').click();await control('adminConfirmSave').click();await ready()}
async function createView(name,template){
 await control('layoutNewView').click();await field('layoutNewName',name);await control('layoutTemplate').selectOption(template)
 await control('layoutCreateView').click();await ready();await section('layoutPages','design')
}
async function checkAndSave(){
 const before=writes.length
 await control('layoutCheck').click();await ready();assert.equal(await editor.locator('[role="alert"]').count(),0)
 await control('adminSaveDocument').click();assert.equal(writes.length,before,'confirmation precedes write')
 await control('adminConfirmSave').click();await ready();assert.equal(writes.length,before+1,'one confirmed write')
 assert.equal(await control('adminDocumentError').inputValue(),'Layout saved')
}
async function shot(name){if(process.argv[3])await page.screenshot({path:process.argv[3]+'/'+name+'.png',animations:'disabled'})}
async function details(container){await container.getByRole('button',{name:'Object details',exact:true}).first().click();await page.locator('dialog.object-details:visible').waitFor();await page.locator('dialog.object-details:visible').getByRole('button',{name:'Close details',exact:true}).click()}
try{
 await page.goto(process.argv[2]+'/projects/admin/?search_type=sthpw/project&view=table')
 await page.getByLabel('Login',{exact:true}).fill('admin');await page.getByLabel('Password',{exact:true}).fill('private-test-password')
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.workspace-results')?.getAttribute('aria-busy')==='false')
 await page.getByLabel('Change search results view',{exact:true}).click();await page.getByRole('menuitemradio',{name:'Continuous tree',exact:true}).click()
 await page.locator('.workspace-results .result-item-tree').first().waitFor();assert.equal(await page.locator('.workspace-results .result-item-configured').count(),0)
 await openEditor();await section('layoutPages','configuration')
 assert.equal(await control('layoutSearchType').inputValue(),'sthpw/project');assert.equal(await control('layoutView').inputValue(),'continuous_example')
 assert.deepEqual(await control('layoutView').locator('option').evaluateAll(nodes=>nodes.map(node=>node.value)),['continuous_example','table_example','cards_example'])
 await control('administrationHelpButton').click();await page.locator('dialog.help-view[open] [data-frame="helpTopicList"]').waitFor();await page.locator('dialog.help-view[open]').getByRole('textbox',{name:'Search help',exact:true}).fill('Build your own view');await page.locator('dialog.help-view[open] [data-frame="helpTopic_item_layouts"]').click();await page.locator('dialog.help-view[open] .document-pane').getByRole('heading',{name:'3. Build a card',exact:true}).waitFor()
 await page.locator('dialog.help-view[open]').getByRole('button',{name:'Close help',exact:true}).click()
 await control('layoutPages_design').click();await control('layoutSavedView_cards_example').click();await ready();await openView()
 const cards=page.locator('.workspace-results .result-presentation[data-result-view="tiles"]:visible')
 await cards.locator('[data-layout-element="image"]').first().waitFor();await details(cards);await shot('cards-example')
 await openEditor();await selectView('table_example');await openView()
 const table=page.locator('.workspace-results .item-layout-table:visible');await table.locator('tbody tr').first().waitFor()
 assert.deepEqual(await table.locator('thead th').allTextContents(),['Preview','Title','Description','Tasks','Notes','Object details','Actions']);await details(table);await shot('table-example')
 await openEditor();await selectView('continuous_example');await control('layoutElement_title').click();await field('layoutProperty_title','Object heading')
 await control('administrationCloseButton').click();assert.equal(await admin.isVisible(),true,'dirty editor blocks window close');await discard()
 await createView('my_cards','cards');await control('layoutView').selectOption('continuous_example');await control('adminCancelSave').click()
 assert.equal(await control('layoutView').inputValue(),'my_cards','Keep editing retains the new draft')
 await control('layoutElement_description').click()
 await field('layoutProperty_row','4');assert.equal(await control('layoutProperty_row').inputValue(),'4');await field('layoutProperty_row','3');await control('layoutProperty_option_bind').selectOption('record.description')
 await control('layoutElement_title').click();await field('layoutProperty_row','1');await field('layoutProperty_layer','2')
 await control('layoutElement_image').click();await field('layoutProperty_layer','3')
 await checkAndSave();await shot('layout-editor');await openView();await cards.locator('[data-layout-element="title"]').first().waitFor()
 assert.equal(await cards.locator('[data-layout-element="title"]').first().evaluate(node=>getComputedStyle(node).zIndex),'2')
 await details(cards);await shot('custom-cards');await page.reload();await cards.locator('[data-layout-element="title"]').first().waitFor()
 await openEditor();await section('layoutPages','configuration');assert.equal(await control('layoutView').inputValue(),'my_cards')
 await page.route('**/admin/widget-configuration/read',route=>route.fulfill({status:400,json:{error:'Invalid view name',error_code:'invalid_widget_config'}}),{times:1})
 await control('adminReloadDocument').click();await ready();await editor.locator('[role="alert"]').waitFor()
 await selectView('continuous_example');assert.equal(await editor.locator('[role="alert"]').count(),0)
 await selectView('my_cards');await control('layoutAddWidget').selectOption('link');await field('layoutProperty_option_href','javascript:alert(1)');await field('layoutProperty_option_text','Dangerous link')
 assert.equal(await editor.locator('a[href^="javascript:"]').count(),0);await discard();await selectView('continuous_example')
 await createView('my_tree','continuous');await checkAndSave();await openView()
 const tree=page.locator('.workspace-results .result-presentation:visible');await tree.locator('.result-item-configured.result-item-tree').first().waitFor()
 await tree.locator('.result-item-configured').first().getByRole('button',{name:'Expand item',exact:true}).click();await tree.locator('.result-item-configured.result-item-branch').first().waitFor()
 await tree.locator('.result-item-configured').first().getByRole('button',{name:'Collapse item',exact:true}).click();await shot('custom-continuous-tree')
 await openEditor();await createView('my_table','table');await control('layoutElement_title').click();await control('layoutEarlier').click()
 await checkAndSave();await openView();await table.locator('tbody tr').first().waitFor();assert.deepEqual((await table.locator('thead th').allTextContents()).slice(0,2),['Title','Preview']);await shot('custom-table')
 await openEditor();await createView('my_widget','blank');await control('layoutAddWidget').selectOption('view');await field('layoutProperty_option_view','my_cards')
 await checkAndSave();await openView();await cards.locator('[data-layout-element="item_1"] [data-layout-element="title"]').first().waitFor()
 await page.setViewportSize({width:360,height:740});await page.locator('.mobile-result-list:visible [data-layout-element="title"]').first().waitFor()
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[])
 console.log('Frame Layout: templates, edit/check/confirm/save/open/reload, guards, cards/actions, tree, reordered table, reusable widgets, URL safety and mobile runtime passed')
}catch(error){await shot('failure');throw error}finally{await browser.close()}

