import assert from 'node:assert/strict'

export async function exerciseUsers(browser,url,catalog){
 const context=await browser.newContext({viewport:{width:360,height:740},hasTouch:true})
 try{
  const page=await context.newPage(),errors=[],writes=[]
  page.on('pageerror',error=>errors.push(error.message))
  let stored=structuredClone(catalog),reads=0,reply='success'
  await page.route('**/admin/security-users/*',async route=>{
   if(route.request().url().endsWith('/read')){reads++;await route.fulfill({json:{result:stored}});return}
   const payload=route.request().postDataJSON();writes.push(payload)
   if(reply==='unknown'){await route.abort('failed');return}
   if(reply==='conflict'){await route.fulfill({status:409,json:{error:'User details changed. Reload before saving.'}});return}
   const document={...payload.document,password:''},login=document.login
   stored.users=stored.users.filter(user=>user.login!==login)
   stored.users.push({login,displayName:document.display_name||login,initials:'FU',avatarColor:'#44786f',retired:document.s_status==='retired',document,revision:'saved-revision'})
   await route.fulfill({json:{result:{...stored,selected:login}}})
  })
  await page.goto(url)
  const control=id=>page.locator('[data-frame="'+id+'"]')
  const ready=()=>page.waitForFunction(()=>window.frameGroups.groups.value.catalog&&!window.frameGroups.groups.value.busy)
  await ready();await control('adminCreateDocument').waitFor()
  const directory=control('adminUsersList')
  await directory.hover();await page.mouse.wheel(0,600);await page.waitForTimeout(150)
  assert(await directory.evaluate(el=>el.scrollTop>0),'User directory scrolls with the wheel')
  await directory.evaluate(el=>el.scrollTop=0)
  await control('adminCreateDocument').tap()
  await control('adminUserLogin').fill('frame_user')
  await control('adminUserField_first_name').fill('Frame')
  assert(await control('adminUserField_first_name').evaluate(el=>el===document.activeElement),'Editing keeps focus')
  await control('segmentedButtonSegment_account').tap()
  await control('adminUserField_project_code').fill('demo')
  await control('adminUserPassword').fill('isolated-password')
  assert.equal(await control('adminUserPassword').getAttribute('type'),'password')
  await control('segmentedButtonSegment_groups').tap()
  await control('userGroupMembership_Artists').locator('input').check()
  assert.equal(writes.length,0,'Draft profile/account/membership edits do not write')
  await control('adminSaveDocument').tap();assert.equal(writes.length,0,'Account save requires confirmation')
  await control('adminConfirmSave').tap();await ready()
  assert.equal(writes.length,1)
  assert.equal(writes[0].identity,'');assert.equal(writes[0].document.login,'frame_user')
  assert.equal(writes[0].document.project_code,'demo');assert.equal(writes[0].document.password,'isolated-password')
  assert.deepEqual(writes[0].document.groups,['Artists'])
  assert.equal(await control('adminUserLogin').getAttribute('readonly'),'')
  await control('segmentedButtonSegment_account').tap()
  assert.equal(await control('adminUserPassword').inputValue(),'','Password is cleared after saving')
  await control('segmentedButtonSegment_profile').tap()
  await control('adminUserField_first_name').fill('Unknown draft')
  reply='unknown';await control('adminSaveDocument').tap();await control('adminConfirmSave').tap();await ready()
  assert.equal(await control('adminSaveDocument').isDisabled(),true)
  await page.evaluate(()=>window.frameGroups.groups.value.save());assert.equal(writes.length,2,'Unknown write is never retried')
  await control('adminReloadDocument').tap();await control('adminCancelSave').tap()
  assert.equal(await control('adminUserField_first_name').inputValue(),'Unknown draft')
  await control('adminReloadDocument').tap();await control('adminConfirmSave').tap();await ready()
  assert.equal(reads,2);assert.equal(await control('adminUserField_first_name').inputValue(),'Frame')
  await control('adminUserField_first_name').fill('Concurrent draft')
  reply='conflict';await control('adminSaveDocument').tap();await control('adminConfirmSave').tap();await ready()
  assert.equal(writes.at(-1).expected_revision,'saved-revision')
  assert.equal(await control('adminUserField_first_name').inputValue(),'Concurrent draft')
  assert.equal(await page.evaluate(()=>window.frameGroups.groups.value.canLeave()),false)
  await control('adminDiscardDocument').tap();await control('adminConfirmSave').tap()
  assert.equal(await control('adminUserField_first_name').inputValue(),'Frame')
  await page.evaluate(()=>window.frameGroups.groups.value.catalog.canWrite=false)
  assert(await control('adminUserField_first_name').isDisabled())
  assert.deepEqual(errors,[])
 }finally{await context.close()}
}
