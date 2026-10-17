import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root=fileURLToPath(new URL('..',import.meta.url))
const output=fileURLToPath(new URL('../../.screenshots/pickers-current/',import.meta.url))
const html=`<!doctype html><html><body><div id="app"></div><script type="module">
import { createApp, h, reactive, ref } from 'vue'
import '/src/App.vue'
import AppDateField from '/src/controls/AppDateField.vue'
import UserComboBox from '/src/controls/UserComboBox.vue'
import UserPicker from '/src/controls/UserPicker.vue'
import TaskHiddenDetails from '/src/features/tasks/TaskHiddenDetails.vue'
import TaskField from '/src/features/objects/TaskField.vue'
import RecordForm from '/src/features/objects/RecordForm.vue'
import { windowDirective } from '/src/controls/window.js'
import { appearance, initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
window.appearance=appearance
Object.assign(appearance,{clickAnimations:false,popupAnimations:false})
initializeAppearance()
const users=[{value:'alice',login:'alice',label:'Alice Artist',displayName:'Alice Artist',email:'alice@example.org',primaryGroup:'Artists',groups:['Artists'],initials:'AA'},
{value:'bob',login:'bob',label:'Bob Supervisor',displayName:'Bob Supervisor',primaryGroup:'Supervisors',groups:['Supervisors'],initials:'BS'}]
const values=reactive({assigned:'alice',supervisor:'bob',bid_start_date:'2024-02-29T13:14',bid_end_date:'2024-03-15T18:30'})
window.values=values
createApp({setup(){
const date=ref('2024-02-29T13:14'), day=ref('2024-02-29'), selected=ref(['bob']), changes=ref(0)
return()=>h('main',{style:'padding:16px;display:grid;gap:16px;max-width:700px'},[
h(TaskHiddenDetails,{editor:{values,plans:[{operation:'update'}],fields:Object.keys(values).map(name=>({name,editable:true})),users,catalog:{}},columns:[{key:'assigned',visible:true},{key:'dates',visible:true}],onChange:(name,v)=>values[name]=v}),
h('section',{id:'form-assignee'},[h(TaskField,{field:{name:'assigned',editable:true},value:values.assigned,users,onChange:v=>values.assigned=v})]),
h('form',{id:'date-form'},[h(AppDateField,{modelValue:date.value,'onUpdate:modelValue':v=>date.value=v,label:'Date test',required:true}),h('output',{id:'date-value'},date.value)]),
h('section',{id:'day-test'},[h(AppDateField,{modelValue:day.value,'onUpdate:modelValue':v=>day.value=v,onChange:()=>changes.value++,label:'Day test',includeTime:false,allowClear:false}),h('output',{id:'day-value'},day.value),h('output',{id:'day-changes'},String(changes.value))]),
h('section',{id:'disabled'},[h(AppDateField,{modelValue:date.value,label:'Disabled date',disabled:true}),h(UserComboBox,{value:'alice',options:users,label:'Disabled user',disabled:true})]),
h('section',{id:'readonly'},[h(AppDateField,{modelValue:date.value,label:'Readonly date',readonly:true})]),
h('section',{id:'multi',style:'height:240px'},[h(UserPicker,{users,currentLogin:'alice',modelValue:selected.value,'onUpdate:modelValue':v=>selected.value=v})]),
h(RecordForm,{ref:instance=>window.record=instance,ticket:'fixture',project:'cg',searchType:'cg/assets'})
])}}).directive('window',windowDirective).mount('#app')
</script></body></html>`
let server,browser
try {
  await mkdir(output,{recursive:true})
  server=await createServer({root,configFile:false,plugins:[vue(),{name:'pickers-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
    if(req.url!=='/pickers-test') return next()
    try {res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))} catch(error){next(error)}
  })}}],server:{host:'127.0.0.1',port:0}})
  await server.listen()
  browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL,ignoreDefaultArgs:['--hide-scrollbars']})
  const page=await browser.newPage({viewport:{width:1000,height:1000},hasTouch:true})
  page.setDefaultTimeout(10000)
  const errors=[]
  page.on('pageerror',error=>{errors.push(error.message);console.error(error.message)})
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/pickers-test`)
  const task=page.locator('.task-workspace-details'), user=task.getByLabel('Assignee',{exact:true})
  await user.waitFor();await user.click()
  const search=task.getByRole('combobox',{name:'Search users',exact:true})
  await search.waitFor();await search.fill('example.org')
  assert.equal(await task.getByRole('radio').count(),1)
  await search.press('ArrowDown');await page.keyboard.press('Enter')
  assert.equal(await page.evaluate(()=>window.values.assigned),'alice')
  await user.click();await page.waitForFunction(()=>document.activeElement.getAttribute('aria-label')==='Search users');await search.fill('supervisors');await search.press('ArrowDown');await page.keyboard.press('Space')
  assert.equal(await page.evaluate(()=>window.values.assigned),'bob')
  await page.waitForFunction(()=>document.querySelector('[data-task-field="assigned"] summary').getAttribute('aria-expanded')==='false')
  assert.equal(await user.getAttribute('aria-expanded'),'false')
  await user.click();await page.waitForFunction(()=>document.activeElement.getAttribute('aria-label')==='Search users');await search.press('ArrowDown')
  assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-checked')),'true')
  assert.equal(await task.locator('.user-combo-box[open] .user-combo-check').count(),1)
  assert.equal(await task.locator('.user-combo-option').first().evaluate(node=>getComputedStyle(node).height),'48px')
  assert.equal(await search.evaluate(node=>node.parentElement.getBoundingClientRect().height),36)
  await page.keyboard.press('Escape')
  assert(await user.evaluate(node=>node===document.activeElement))
  assert.equal(await page.locator('#form-assignee .user-combo-indicator').count(),1)
  const formUser=page.locator('#form-assignee')
  await formUser.getByLabel('Assigned to',{exact:true}).click();await formUser.locator('.account-panel:popover-open').waitFor()
  assert.equal(await formUser.locator('.user-combo-indicator').getAttribute('data-icon'),'MDI_CHEVRON_UP')
  await page.keyboard.press('Escape')
  const date=page.locator('#date-form'), input=date.getByRole('textbox',{name:'Date test',exact:true})
  const openDate=async()=>{await date.getByLabel('Choose date and time',{exact:true}).click();await date.locator('.account-panel:popover-open').waitFor()}
  await openDate()
  assert.equal(await date.getByLabel('Minute',{exact:true}).inputValue(),'14')
  assert.equal(await date.evaluate(node=>node.checkValidity()),true,'Arbitrary minutes remain valid in a parent form')
  await date.getByLabel('Hour',{exact:true}).fill('23');await date.getByLabel('Minute',{exact:true}).fill('59')
  await date.locator('[data-day="29"]').click()
  assert.equal(await page.locator('#date-value').textContent(),'2024-02-29T23:59')
  await openDate();await date.getByRole('button',{name:'Next month',exact:true}).click();await date.locator('[data-day="1"]').click()
  assert.equal(await page.locator('#date-value').textContent(),'2024-03-01T23:59')
  await openDate();await date.locator('[data-day="1"]').press('ArrowLeft');await page.keyboard.press('Enter')
  assert.equal(await page.locator('#date-value').textContent(),'2024-02-29T23:59','Keyboard crosses leap-month boundaries locally')
  await openDate();await date.getByLabel('Minute',{exact:true}).fill('17');await date.getByLabel('Minute',{exact:true}).press('ArrowUp')
  assert.equal(await date.getByLabel('Minute',{exact:true}).inputValue(),'22')
  await date.getByLabel('Hour',{exact:true}).fill('99');await date.getByRole('button',{name:'Clear',exact:true}).click()
  assert.equal(await page.locator('#date-value').textContent(),'')
  assert.equal(await date.evaluate(node=>node.checkValidity()),false,'Required date validation survives the custom calendar')
  await input.fill('2023-02-29T12:00');assert.equal(await input.evaluate(node=>node.validity.valid),false)
  await input.fill('2024-02-29T12:00');assert.equal(await date.evaluate(node=>node.checkValidity()),true)
  await openDate();await date.getByRole('button',{name:'Next month',exact:true}).click();await page.keyboard.press('Escape')
  assert.equal(await page.locator('#date-value').textContent(),'2024-02-29T12:00')
  assert.equal(await date.locator('.account-panel:popover-open').count(),0)
  const day=page.locator('#day-test')
  await day.getByLabel('Choose date',{exact:true}).click();await day.locator('[data-day="28"]').tap()
  assert.equal(await page.locator('#day-value').textContent(),'2024-02-28');assert.equal(await page.locator('#day-changes').textContent(),'1')
  await day.getByRole('textbox').fill('2024-03-10');await day.getByRole('textbox').press('Tab')
  assert.equal(await page.locator('#day-changes').textContent(),'2','Scope changes commit once after manual editing')
  await day.getByRole('textbox').fill('2024-03-10T12:00');assert.equal(await day.getByRole('textbox').evaluate(node=>node.checkValidity()),false)
  await day.getByRole('textbox').fill('2024-03-10');await day.getByRole('textbox').press('Tab')
  await page.locator('#disabled summary').first().click({force:true});await page.locator('#readonly summary').click({force:true})
  assert.equal(await page.locator('#disabled details[open],#readonly details[open]').count(),0)
  assert.equal(await page.locator('#multi').getByRole('checkbox',{name:'Alice Artist'}).isDisabled(),true)
  const selectedCaption=page.locator('#multi .selected small')
  assert.equal(await selectedCaption.evaluate(node=>getComputedStyle(node).color),await selectedCaption.evaluate(node=>getComputedStyle(node.parentElement.firstElementChild).color))
  const start=task.locator('[data-task-field="bid_start_date"]')
  await start.getByLabel('Choose date and time',{exact:true}).click()
  await start.locator('.account-panel:popover-open').waitFor()
  assert.equal(await start.locator('.app-date-presentation').evaluate(node=>getComputedStyle(node).textTransform),'none')
  assert.equal(await start.getByLabel('Hour',{exact:true}).evaluate(node=>getComputedStyle(node.parentElement).width),'92px')
  assert.equal(await start.locator('.calendar-day').first().evaluate(node=>getComputedStyle(node).height),'30px')
  await page.keyboard.press('Escape')
  let saved
  await page.route('**/admin/rpc',async route=>{saved=route.request().postDataJSON();await route.fulfill({json:{result:{}}})})
  await page.evaluate(()=>{
    const deadline='2024-02-29T10:14:15.123456+00:00', day='2024-03-01T00:00:00+00:00'
    const field=(name,title,value,input)=>({name,title,values:[value],options:{},attributes:{},action:{handler:'DatabaseAction',options:{}},class_name:'tactic.ui.widget.calendar_wdg.CalendarInputWdg',input:{...input,unchanged_value:value,display_mode:'browser'}})
    window.record.context={ticket:'fixture',project:'cg'}
    window.record.definition={search_type:'cg/assets',search_key:'cg/assets?id=1',mode:'edit',view:'edit',input_prefix:'picker',fields:[
      field('deadline','Deadline precision',deadline,{type:'datetime-local',value:'2024-02-29T13:14:15.123',value_suffix:''}),
      field('due_day','Due day contract',day,{type:'date',value:'2024-03-01',value_suffix:'T12:00:00+00:00'})]}
    window.record.draft={deadline,due_day:day};window.record.baseline={deadline,due_day:day}
    window.record.$refs.dialog.showModal()
  })
  const record=page.getByRole('dialog',{name:'Record form',exact:true})
  assert.equal(await record.getByRole('textbox',{name:'Deadline precision'}).inputValue(),'2024-02-29T13:14:15.123')
  assert.equal(await record.locator('form').evaluate(node=>node.checkValidity()),true,'Unchanged seconds/milliseconds remain valid')
  await record.getByLabel('Choose date',{exact:true}).click();await record.locator('.account-panel:popover-open').waitFor();await record.locator('.account-panel:popover-open [data-day="10"]').click()
  await record.getByRole('button',{name:/^(?:Create|Save changes)$/,exact:true}).click();await record.waitFor({state:'hidden'})
  assert.equal(saved.args[3]['picker|deadline'],'2024-02-29T10:14:15.123456+00:00','Unchanged UTC precision survives form serialization')
  assert.equal(saved.args[3]['picker|due_day'],'2024-03-10T12:00:00+00:00','Day field retains the server noon suffix')
  for(const mode of ['light','dark']) for(const theme of ['md3','material5']) {
    await page.evaluate(({mode,theme})=>Object.assign(window.appearance,{mode,theme}),{mode,theme})
    await openDate();await page.screenshot({path:output+`/stream-date-${mode}-${theme}.png`});await page.keyboard.press('Escape')
    await user.click();await task.locator('.user-combo-box[open] .account-panel:popover-open').waitFor();await page.screenshot({path:output+`/stream-user-${mode}-${theme}.png`});await page.keyboard.press('Escape')
  }
  await page.evaluate(()=>window.appearance.language='ru')
  await page.setViewportSize({width:360,height:800})
  await date.getByLabel('Выбрать дату и время',{exact:true}).tap()
  const popup=await date.locator('.account-panel:popover-open').boundingBox()
  assert(popup.x>=0 && popup.x+popup.width<=360 && popup.y>=0 && popup.y+popup.height<=800,JSON.stringify(popup))
  await page.screenshot({path:output+'/stream-mobile-ru.png'});await page.keyboard.press('Escape')
  await task.getByLabel('Исполнитель',{exact:true}).tap();await task.locator('.user-combo-box[open] .account-panel:popover-open').waitFor();const usersPopup=await task.locator('.user-combo-box[open] .account-panel').boundingBox()
  assert(usersPopup.x>=0 && usersPopup.x+usersPopup.width<=360)
  await page.keyboard.press('Escape')
  const scaled=await browser.newPage({viewport:{width:800,height:650},deviceScaleFactor:2})
  await scaled.goto(`http://127.0.0.1:${server.httpServer.address().port}/pickers-test`)
  await scaled.locator('#date-form').getByLabel('Choose date and time',{exact:true}).click()
  await scaled.locator('#date-form .account-panel:popover-open').waitFor()
  assert.equal(await scaled.evaluate(()=>devicePixelRatio),2)
  await scaled.screenshot({path:output+'/stream-200-percent.png'});await scaled.close()
  assert.deepEqual(errors,[])
  console.log('Picker checks passed: task layout, user search/selection/keyboard, calendar dates/time/validation, read-only, touch, themes and mobile RU')
} finally {
  if(browser){await browser.close();assert.equal(browser.isConnected(),false)}
  if(server){await server.close();assert.equal(server.httpServer.listening,false)}
}

