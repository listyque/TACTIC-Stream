import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
import {chromium} from 'playwright'
const repo=fileURLToPath(new URL('../../',import.meta.url))
const types=JSON.parse(await readFile(repo+'tools/frame_types/output/catalog.json','utf8')),naming=JSON.parse(await readFile(repo+'tools/frame_naming/output/catalog.json','utf8'))
const server=await createServer({root:repo,configFile:false,resolve:{alias:{vue:repo+'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},plugins:[vue()],logLevel:'warn',server:{host:'127.0.0.1',port:0,watch:{ignored:['**/.tmp/**','**/.venv/**','**/.standalone*/**','**/output/**']}}})
await server.listen()
const browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL})
try{
 for(const width of [1100,360]){
  const page=await browser.newPage({viewport:{width,height:800}}),errors=[],writes=[],previews=[]
  let stored=structuredClone(naming),loads=0,unknown=false
  page.on('pageerror',error=>errors.push(error.message));page.on('dialog',dialog=>dialog.dismiss())
  await page.route('**/admin/rpc',async route=>{
   const body=route.request().postDataJSON();if(body.method==='log')return route.fulfill({json:{result:null}});assert.equal(body.method,'execute_cmd');const command=body.args[1],args=body.args[2]
   if(command.endsWith('SearchTypesCmd')){assert(['list','load'].includes(args.action));return route.fulfill({json:{result:{info:structuredClone(types)}}})}
   assert(command.endsWith('NamingCmd'))
   if(args.action==='load'){loads++;return route.fulfill({json:{result:{info:structuredClone(stored)}}})}
   if(args.action==='save'){
    writes.push(args);if(unknown)return route.abort('failed')
    assert.equal(args.expected_revision,stored.revision)
    stored.rules[0].document=structuredClone(args.document);stored.revision='saved-revision'
    return route.fulfill({json:{result:{info:structuredClone(stored)}}})
   }
   assert.equal(args.action,'preview');previews.push(args)
   return route.fulfill({json:{result:{info:{results:[{mode:'version',path:'demo/asset/frame_v012.ma',directory:'demo/asset',file:'frame_v012.ma',sandbox:'sandbox/demo',matches:false,selectedRule:'N2',collisions:[{key:'asset/A1',snapshot:'SNAP1'}]}]}}}})
  })
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/tools/frame_types/index.html')
  const control=id=>page.locator('[data-frame="'+id+'"]')
  const ready=()=>page.waitForFunction(()=>window.frameAdmin.screen.value.document&&!window.frameAdmin.screen.value.busy&&!window.frameAdmin.screen.value.namingView?.busy)
  const section=async(selector,value)=>{const button=control(selector+'_'+value);if(await button.count())await button.click();else await control(selector).selectOption(value)}
  await ready();await control('adminSearchType_demo/asset').click();await section('searchTypePages','naming');await ready()
  await control('naming_file_naming').fill('retained_{sobject.name}.{ext}')
  await section('searchTypePages','details')
  assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.dirty),true,'hidden Naming draft keeps Administration dirty')
  assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.canLeave()),false,'closing still guards the hidden naming draft')
  await section('searchTypePages','naming');await ready()
  assert.equal(loads,1,'returning to Naming preserves its local draft without a second server load')
  assert.equal(await control('naming_file_naming').inputValue(),'retained_{sobject.name}.{ext}')
  assert.equal(writes.length,0)
  await control('adminSaveDocument').click();assert.equal(writes.length,0)
  await control('adminConfirmSave').click();await ready();assert.equal(writes.length,1)
  assert.equal(writes[0].document.file_naming,'retained_{sobject.name}.{ext}');assert.equal(writes[0].identity,'N1')
  await section('namingPages','preview')
  await control('namingSample_version').fill('12');await control('namingEvaluate').click();await ready()
  assert.equal(previews.length,1);assert.equal(previews[0].allow_execution,false);assert.equal(previews[0].sample.version,12)
  assert.match(await control('namingPath_version').inputValue(),/frame_v012\.ma/)
  assert.match(await control('namingResultDetails_version').inputValue(),/N2/)
  assert.match(await control('namingCollisions_version').inputValue(),/SNAP1/)
  await control('namingEvaluateCustom').click();assert.equal(previews.length,1,'custom code cannot run before confirmation')
  await control('adminConfirmSave').click();await ready();assert.equal(previews[1].allow_execution,true)
  await section('namingPages','rule');await control('naming_file_naming').fill('unknown.{ext}')
  unknown=true;await control('adminSaveDocument').click();await control('adminConfirmSave').click();await ready()
  assert(await control('adminSaveDocument').isDisabled());assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.namingView.uncertain),true)
  await control('adminReloadDocument').click();await control('adminConfirmSave').click();await ready()
  assert.equal(await page.evaluate(()=>window.frameAdmin.screen.value.namingView.uncertain),false)
  assert.equal(await control('naming_file_naming').inputValue(),'retained_{sobject.name}.{ext}')
  assert.equal(writes.length,2,'readback never retries the unknown write')
  assert.deepEqual(errors,[]);await page.close()
 }
 console.log('Search Types/Naming input: retained hidden drafts, save confirmation/revision, server preview, execution consent, collisions and unknown-write readback passed at 1100/360px')
}finally{await browser.close();await server.close()}
