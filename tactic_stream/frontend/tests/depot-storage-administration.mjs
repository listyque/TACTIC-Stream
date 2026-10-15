import assert from 'node:assert/strict'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {chromium} from 'playwright'
const browser=await chromium.launch({headless:true,channel:'msedge'})
const page=await browser.newPage({viewport:{width:1440,height:900}}), errors=[], actions=[]
let ticket
const ui=page.locator('.file-workspace')
page.on('pageerror',error=>errors.push(error.message))
page.on('request',request=>{if(request.url().includes('/file-project/command')){actions.push(request.postDataJSON());ticket=request.headers()['x-tactic-ticket']}})
const command=(action,values={})=>page.evaluate(async({ticket,action,values})=>{const response=await fetch('/file-project/command?project=files',{method:'POST',headers:{'Content-Type':'application/json','X-Tactic-Ticket':ticket},body:JSON.stringify({action,...values})});assertResponse(response);return response.json();function assertResponse(response){if(!response.ok)throw Error(response.status)}},{ticket,action,values})
const idle=async()=>{await page.waitForFunction(()=>document.querySelector('.file-workspace')?.getAttribute('aria-busy')==='false');assert.deepEqual(await ui.getByRole('alert').allTextContents(),[])}
const ru=JSON.parse(await readFile(new URL('../src/locales/ru.json',import.meta.url),'utf8'))
let language='en'
const text=value=>language==='ru'?ru[value]||value:value
const open=async title=>{await ui.getByLabel(text('View'),{exact:true}).click();await ui.getByRole('menuitem',{name:text(title),exact:true}).click();await idle()}
try{
  await mkdir(process.argv[3],{recursive:true})
  await page.goto(process.argv[2]+'/projects/files/')
  await page.getByLabel('Login',{exact:true}).fill('admin');await page.getByLabel('Password',{exact:true}).fill('file-test-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();await ui.waitFor();await idle()
  await open('Depots')
  await ui.getByRole('button',{name:'New depot',exact:true}).click();await idle()
  await ui.getByLabel('Depot code',{exact:true}).fill('photos');await ui.getByLabel('Name',{exact:true}).fill('Photos')
  await ui.getByRole('button',{name:'Create',exact:true}).click();await idle()
  await ui.getByRole('button',{name:'Edit depot',exact:true}).click();await idle()
  assert.equal(await ui.getByLabel('Depot code',{exact:true}).getAttribute('readonly'),'')
  await ui.getByLabel('Name',{exact:true}).fill('Edited photos')
  await open('Storage administration')
  await ui.getByLabel('Parallel transfers',{exact:true}).fill('8')
  await open('Depots');assert.equal(await ui.getByLabel('Name',{exact:true}).inputValue(),'Edited photos')
  await ui.getByRole('button',{name:'Save',exact:true}).click();await idle()
  await open('Storage administration');assert.equal(await ui.getByLabel('Parallel transfers',{exact:true}).inputValue(),'8')
  await ui.getByLabel('Byte quota',{exact:true}).fill('9223372036854775807')
  await ui.getByRole('button',{name:'Save storage policy',exact:true}).click();await idle()
  assert.equal(await ui.getByLabel('Byte quota',{exact:true}).inputValue(),'9223372036854775807')
  const saved=actions.findLast(row=>row.action==='storage_policy');assert.equal(saved.policy.bytes_limit,'9223372036854775807')
  let status=await command('storage_status')
  await command('storage_policy',{revision:status.policy_revision,policy:{max_parallel:'7'}})
  await ui.getByLabel('Parallel transfers',{exact:true}).fill('9');await ui.getByRole('button',{name:'Save storage policy',exact:true}).click()
  await ui.getByRole('alert').filter({hasText:'Storage policy revision conflict'}).waitFor()
  assert.equal(await ui.getByLabel('Parallel transfers',{exact:true}).inputValue(),'9')
  await ui.locator('.storage-administration').getByRole('button',{name:'Refresh',exact:true}).click();await idle()
  assert.equal(await ui.getByLabel('Parallel transfers',{exact:true}).inputValue(),'9')
  await ui.getByRole('button',{name:'Reset',exact:true}).click();assert.equal(await ui.getByLabel('Parallel transfers',{exact:true}).inputValue(),'7')
  await ui.getByLabel('Parallel transfers',{exact:true}).fill('8');await ui.getByRole('button',{name:'Save storage policy',exact:true}).click();await idle()
  await ui.getByLabel('Parallel transfers',{exact:true}).fill('17');await ui.getByRole('button',{name:'Save storage policy',exact:true}).click()
  await ui.getByRole('alert').filter({hasText:'Enter non-negative whole numbers'}).waitFor()
  await ui.getByRole('button',{name:'Reset',exact:true}).click();await idle()
  assert.equal(await ui.getByLabel('Parallel transfers',{exact:true}).inputValue(),'8')
  await ui.getByRole('button',{name:'GC dry run',exact:true}).click();await idle()
  status=await command('storage_status');assert.equal(status.gc.dry_run,true);assert.equal(status.gc.state,'queued')
  await ui.getByRole('button',{name:'Cancel GC',exact:true}).click();await idle()
  const before=actions.filter(row=>row.action==='gc_begin').length
  page.once('dialog',dialog=>dialog.dismiss());await ui.getByRole('button',{name:'Run safe GC',exact:true}).click();await idle()
  assert.equal(actions.filter(row=>row.action==='gc_begin').length,before)
  page.once('dialog',dialog=>dialog.accept());await ui.getByRole('button',{name:'Run safe GC',exact:true}).click();await idle()
  status=await command('storage_status');assert.equal(status.gc.dry_run,false)
  await ui.getByRole('button',{name:'Cancel GC',exact:true}).click();await idle()
  const captures=[]
  for(language of ['en','ru'])for(const mode of ['light','dark']){
    await page.evaluate(({language,mode})=>localStorage.setItem('tactic_stream.appearance',JSON.stringify({language,mode,theme:'md3'})),{language,mode})
    await page.reload();await ui.waitFor();await idle()
    for(const title of ['Depots','Storage administration']){
      await open(title)
      if(title==='Depots'){assert.equal(await ui.locator('.depots-catalog aside .depot-row').count(),2);await ui.locator('.depots-catalog').getByRole('button',{name:'photos',exact:true}).click()}
      for(const width of [1440,700,360]){
        await page.setViewportSize({width,height:800});await page.waitForTimeout(200)
        const pane=ui.locator(title==='Depots'?'.depots-catalog':'.storage-administration')
        const bounds=await pane.evaluate(node=>({width:node.clientWidth,height:node.clientHeight,scroll:node.scrollWidth}))
        assert.ok(bounds.scroll<=bounds.width+1,JSON.stringify({title,viewportWidth:width,...bounds}))
        const stem=(title==='Depots'?'depots':'storage')+'-'+language+'-'+mode+'-'+width
        captures.push({source:title==='Depots'?'depots':'storage',language,mode,...bounds,stem})
        await pane.screenshot({path:process.argv[3]+'/browser-'+stem+'.png'})
      }
    }
  }
  await writeFile(process.argv[3]+'/panes.json',JSON.stringify(captures))
  await page.reload();await ui.waitFor();await idle()
  assert.equal(await ui.getByLabel(text('Byte quota'),{exact:true}).inputValue(),'9223372036854775807')
  assert.deepEqual(errors,[])
  console.log('Depot create/edit, exact quota, draft retention, validation, reset, reload and narrow layouts passed')
}catch(error){await page.screenshot({path:process.argv[3]+'/failure.png'});throw error}finally{await browser.close()}
