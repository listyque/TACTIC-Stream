import assert from 'node:assert/strict'
import { readFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('..', import.meta.url))
const handler = JSON.parse(await readFile(new URL('../../../../th_codex/thlib/ui/translations/ru.json', import.meta.url), 'utf8'))
const stream = JSON.parse(await readFile(root + '/src/locales/ru.json', 'utf8'))
let shared = 0
for (const [source, translated] of Object.entries(stream)) {
  assert(typeof translated === 'string' && translated.trim(), source)
  assert.deepEqual((translated.match(/\{\w+\}|%\d+/g) || []).sort(), (source.match(/\{\w+\}|%\d+/g) || []).sort(), source)
  if (source in handler) { assert.equal(translated, handler[source], source); shared++ }
}
assert(shared > 2000)
const labels = ['Search Type', 'Search Types', 'Task Manager', 'Task Inspector', 'Appearance', 'Workflow', 'Pipelines', 'Snapshot', 'Script shelf', 'New conversation']
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue'
import AppButton from '/src/controls/AppButton.vue'
import AppSelect from '/src/controls/AppSelect.vue'
import AppTextField from '/src/controls/AppTextField.vue'
import TaskInspectorHeader from '/src/features/objects/TaskInspectorHeader.vue'
import {appearance,initializeAppearance} from '/src/appearance.js'
import {t} from '/src/i18n.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',popupAnimations:false,clickAnimations:false});initializeAppearance()
window.appearance=appearance;window.t=t
const editor={object:{record:{name:'Search'},search_type:'cg/assets',type_title:'Workflow',preview:{}},processes:[{value:'proc',label:'Search',type:'task',count:0}],task_choices:[],selected_task:''}
createApp({setup(){const draft=ref('Unsaved draft');window.draft=draft;return ()=>h('main',[
 h('div',{class:'labels'},${JSON.stringify(labels)}.map(label=>h(AppButton,{label,'data-source':label}))),
 h(AppButton,{label:'Search',translateLabel:false,'data-server-label':true}),
 h(AppButton,{label:'Search',translateLabel:false,iconOnly:true,icon:'search','data-server-icon':true}),
 h(AppSelect,{label:'Search Type',translateLabels:false,options:[{value:'raw',label:'Workflow'}],modelValue:'raw'}),
 h(AppTextField,{label:'Description',modelValue:draft.value,'onUpdate:modelValue':value=>draft.value=value}),
 h(TaskInspectorHeader,{editor,process:'proc',expanded:true,busy:false}),
])}}).mount('#app')
</script></body></html>`
let server, browser
const deadline = setTimeout(() => browser?.close(), 45000)
try {
  server = await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/localization',plugins:[vue(),{
    name:'localization-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
      if(req.url!=='/localization-test')return next()
      try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
    })},
  }],server:{host:'127.0.0.1',port:0,watch:null}})
  await server.listen(); browser = await chromium.launch({headless:true})
  const page = await browser.newPage({viewport:{width:1280,height:900}}), errors = []
  page.setDefaultTimeout(8000);page.on('pageerror',error=>errors.push(error.message))
  await page.goto(server.resolvedUrls.local[0]+'localization-test')
  await page.locator('.labels button').first().waitFor()
  await page.getByRole('textbox',{name:'Description',exact:true}).fill('Retained unsaved draft')
  await page.evaluate(()=>window.appearance.language='ru')
  for(const label of labels) {
    const button=page.locator('[data-source="'+label+'"]')
    assert.equal(await button.textContent(),handler[label],label)
    assert.equal(await button.getAttribute('aria-label'),handler[label],label)
  }
  assert.equal(await page.locator('[data-server-label]').textContent(),'Search')
  assert.equal(await page.locator('[data-server-icon]').getAttribute('aria-label'),'Search')
  assert.equal(await page.locator('select option').textContent(),'Workflow')
  assert.equal(await page.locator('.inspector-object-title strong').textContent(),'Search')
  await page.getByLabel(handler.Process,{exact:true}).click()
  const process=page.locator('[data-process-choice="proc"]')
  assert.equal(await process.getAttribute('aria-label'),'Search')
  assert.equal(await process.locator('strong').textContent(),'Search')
  await process.click()
  const output=root+'/../.screenshots/localization-current'
  await mkdir(output,{recursive:true});await page.screenshot({path:output+'/ts-handler-translations.png'})
  const checks=await page.evaluate(()=>({missing:window.t('Unlisted source'),empty:window.t(''),placeholder:window.t('Project: {project}',{project:'Workflow'}),draft:window.draft.value,lang:document.documentElement.lang}))
  assert.equal(checks.missing,'Unlisted source');assert.equal(checks.empty,'')
  assert.equal(checks.placeholder,stream['Project: {project}'].replace('{project}','Workflow'))
  assert.equal(checks.draft,'Retained unsaved draft');assert.equal(checks.lang,'ru')
  // Raw fallback tooltips must keep server labels too.
  await page.locator('[data-server-icon]').hover()
  const tooltip=page.getByRole('tooltip');await tooltip.waitFor();assert.equal(await tooltip.textContent(),'Search')
  await page.evaluate(()=>window.appearance.language='en')
  for(const label of labels) assert.equal(await page.locator('[data-source="'+label+'"]').textContent(),label)
  assert.equal(await page.getByRole('textbox',{name:'Description',exact:true}).inputValue(),'Retained unsaved draft')
  await page.setViewportSize({width:320,height:700});await page.evaluate(()=>window.appearance.language='ru')
  assert.equal(await page.locator('[data-source="Task Inspector"]').textContent(),handler['Task Inspector'])
  assert.deepEqual(errors,[])
  console.log('Localization: '+shared+' exact Handler translations, placeholders, fallback, live EN/RU, draft retention and raw process/button/select/tooltip labels passed.')
}finally{clearTimeout(deadline);await browser?.close();await server?.close()}
