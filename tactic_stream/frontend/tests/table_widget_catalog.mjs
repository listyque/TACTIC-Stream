import assert from 'node:assert/strict'
import { readFile, mkdir, copyFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'
import { readArticle } from '../src/features/help/help.js'
import { renderMarkdown } from '../src/controls/markdown.js'

const root = fileURLToPath(new URL('..', import.meta.url))
const fixtures = JSON.parse(await readFile(root+'/tests/fixtures/table-widget-catalog.json','utf8'))
const native = JSON.parse(await readFile(root+'/../reports/table-view-2026-10-13/completion-th-measurements.json','utf8'))
const helpRoot = root+'/public/help', output = helpRoot+'/media'
for (const id of ['widget_database','table_widget_examples']) for (const language of ['en','ru']) {
  const article = readArticle(id, await readFile(helpRoot+'/'+id+'.'+language+'.md','utf8'), '')
  const markup = renderMarkdown(article.body)
  assert(markup.includes('<table>') || id==='table_widget_examples')
  if (id==='widget_database') assert(article.body.includes('SnapshotServerElementWdg') && article.body.includes('SpreadsheetElementWdg'))
}
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue'
import TableCell from '/src/features/interface/TableCell.vue'
import HelpView from '/src/features/help/HelpView.vue'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css';import '/src/style.css'
Object.assign(appearance,{language:'en',mode:'dark',fadeAnimations:false,popupAnimations:false});initializeAppearance();window.appearance=appearance
const samples=${JSON.stringify(fixtures)}
const completion=samples.find(row=>row.key==='completion')
createApp({data(){return {events:[],percent:-10,text:'-10%',failure:false,valueKey:'array',override:null}},computed:{valueSample(){return samples.find(row=>row.key===this.valueKey)}},mounted(){window.host=this},render(){return h('main',[
 h('div',{id:'samples'},samples.map(sample=>h('section',{class:'sample','data-widget':sample.key},[
  h('strong',sample.element.title),h('div',{class:'sample-cell'},[h(TableCell,{element:sample.element,record:sample.record,cell:sample.value,editable:true,onPreview:v=>this.events.push('preview'),onNotes:()=>this.events.push('notes')})])
 ]))),
 h('section',{id:'completion-reference',style:{background:'${native[0].backgroundColor}'}},[0,25,75,100].map(value=>h('div',{class:'reference-cell'},[h(TableCell,{element:completion.element,record:{},cell:{text:value.toFixed(1)+'%',completion:value}})]))),
 h('section',{id:'edge'},[h(TableCell,{element:completion.element,record:{},cell:this.failure?{error:'Example failure'}:{completion:this.percent,text:this.text}})]),
 h('section',{id:'value-reference',class:this.valueSample.element.cell.kind},[h(TableCell,{element:this.valueSample.element,record:{},cell:this.override||this.valueSample.value})]),
 h(HelpView,{ref:'help',topic:'widget_database'})
])}}).directive('window',windowDirective).mount('#app')
</script><style>
body{margin:0;padding:24px;background:var(--surface)}main{max-width:1040px;margin:auto}#samples{display:grid;grid-template-columns:1fr 1fr;gap:12px}.sample{background:var(--surface-container);border-radius:12px;padding:16px;min-height:106px;min-width:0}.sample>strong{display:block;margin-bottom:10px}.sample-cell{min-height:52px;display:flex;align-items:center}.sample-cell>.table-completion{width:100%}#completion-reference{width:240px;background:var(--surface);margin-top:24px}.reference-cell{height:52px;display:flex;align-items:center}.reference-cell>.table-completion{width:100%}#edge{width:240px;margin:24px 0}#samples .task-card{width:190px}.table-thumbnail img{width:48px;height:48px}#value-reference{box-sizing:border-box;width:320px;height:128px;padding:10px;background:var(--surface);overflow:hidden;margin-bottom:20px}#value-reference.text{display:flex;align-items:center}#value-reference.structured>.table-structured{max-width:300px}
</style></body></html>`
let server,browser
const errors=[],requests=[],deadline=setTimeout(()=>browser?.close(),55000)
try {
  server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/table-widget-catalog',plugins:[vue(),{
    name:'table-widget-catalog-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
      if(req.url?.startsWith('/ui/help/')){req.url=req.url.replace('/ui/help/','/help/');return next()}
      if(req.url!=='/widget-test')return next()
      try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
    })}
  }],server:{host:'127.0.0.1',port:0,watch:null}})
  await server.listen()
  browser=await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL})
  const page=await browser.newPage({viewport:{width:1100,height:900}});page.setDefaultTimeout(8000)
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>requests.push(request.url()))
  await page.goto(server.resolvedUrls.local[0]+'widget-test')
  await page.waitForFunction(()=>!!window.host)
  await page.evaluate(()=>document.fonts.ready)
  await mkdir(output,{recursive:true})
  async function capture(locator,name){
    await locator.screenshot({path:output+'/'+name+'.png',animations:'disabled'})
    await copyFile(output+'/'+name+'.png',root+'/../src/tactic_stream/web/help/media/'+name+'.png')
  }
  assert.equal(await page.locator('[data-widget]').count(),fixtures.length)
  await page.waitForFunction(()=>document.querySelector('[data-widget="thumb"] img')?.naturalWidth>0)
  for(const sample of fixtures)await capture(page.locator('[data-widget="'+sample.key+'"]'),'table-widget-'+sample.key)
  const valueView=page.locator('#value-reference')
  for(const sample of fixtures.filter(row=>['array','xml','json','snapshot_version'].includes(row.key))){
    await page.evaluate(key=>{window.host.valueKey=key;window.host.override=null},sample.key)
    await page.waitForFunction(key=>window.host.valueSample.key===key,sample.key)
    assert.equal(await valueView.innerText(),sample.value.text)
    if(sample.element.cell.kind==='structured'){
      const style=await valueView.locator('pre').evaluate(el=>({font:getComputedStyle(el).fontFamily,size:getComputedStyle(el).fontSize}))
      assert(style.font.includes('Consolas'));assert(Math.abs(parseFloat(style.size)-9.25*4/3)<0.01)
      if(sample.key==='json'){
        assert.equal((await valueView.locator('.table-structured').boundingBox()).height,72)
        await valueView.locator('.table-structured').evaluate(el=>el.scrollTop=30)
        assert((await valueView.locator('.table-structured').evaluate(el=>el.scrollTop))>0)
        await valueView.locator('.table-structured').evaluate(el=>el.scrollTop=0)
      }
    }
    await capture(valueView,'table-widget-'+sample.key+'-stream')
  }
  await page.evaluate(()=>{window.host.valueKey='xml';window.host.override={text:'<script>window.injected=true</script>',language:'xml',diagnostic:'Fixture invalid XML'}})
  assert.match(await valueView.innerText(),/Fixture invalid XML/)
  assert.equal(await valueView.locator('pre').innerText(),'<script>window.injected=true</script>')
  assert.equal(await page.evaluate(()=>window.injected),undefined)
  await page.evaluate(()=>{window.host.valueKey='array';window.host.override={text:''}})
  assert.equal(await valueView.innerText(),'')
  await page.evaluate(()=>{window.host.valueKey='snapshot_version';window.host.override={text:'Current',label:'Current'};window.appearance.language='ru'})
  assert.equal(await valueView.innerText(),'Текущий')
  await page.evaluate(()=>{window.host.override={text:'No version',label:'No version'}})
  assert.equal(await valueView.innerText(),'Нет версии')
  await page.evaluate(()=>window.appearance.language='en')
  const bars=page.locator('#completion-reference [role="progressbar"]')
  for(let index=0;index<native.length;index++){
    const expected=native[index], bar=bars.nth(index), fill=bar.locator('.table-completion-fill')
    const bounds=await bar.boundingBox(), parent=await bar.locator('..').boundingBox()
    assert.equal(bounds.width,expected.trackWidth);assert.equal(bounds.height,expected.trackHeight)
    assert.equal(bounds.x-parent.x,expected.margin)
    assert.equal((await fill.boundingBox()).width,expected.fillWidth)
    assert.equal(await bar.getAttribute('aria-valuenow'),String(expected.percent))
    assert.equal(await bar.innerText(),expected.percent.toFixed(1)+'%')
    const colors=await bar.evaluate(el=>{
      const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d')
      const hex=color=>{ctx.fillStyle=color;ctx.fillRect(0,0,1,1);return '#'+[...ctx.getImageData(0,0,1,1).data].slice(0,3).map(n=>n.toString(16).padStart(2,'0')).join('')}
      return {track:hex(getComputedStyle(el).backgroundColor),fill:hex(getComputedStyle(el.querySelector('.table-completion-fill')).backgroundColor),text:hex(getComputedStyle(el.querySelector('.table-completion-label')).color),font:getComputedStyle(el.querySelector('.table-completion-label')).fontSize,weight:getComputedStyle(el.querySelector('.table-completion-label')).fontWeight}
    })
    assert.equal(colors.track,expected.trackColor);assert.equal(colors.fill,expected.fillColor);assert.equal(colors.text,expected.labelColor)
    assert.equal(parseFloat(colors.font),expected.captionPoints*4/3)
    assert.equal(Number(colors.weight),expected.captionWeight)
  }
  await capture(page.locator('#completion-reference'),'table-widget-completion-stream')
  const edge=page.locator('#edge')
  assert.equal(await edge.getByRole('progressbar').getAttribute('aria-valuenow'),'0')
  await page.evaluate(()=>{window.host.percent=150;window.host.text='150%'})
  assert.equal(await edge.getByRole('progressbar').getAttribute('aria-valuenow'),'100')
  await page.evaluate(()=>{window.host.percent=null;window.host.text=''})
  assert.equal(await edge.innerText(),'0.0%')
  await page.evaluate(()=>window.host.failure=true)
  assert.equal(await edge.getByRole('progressbar').count(),0)
  assert.match(await edge.innerText(),/Example failure/)
  await page.locator('[data-widget="thumb"] button').click()
  await page.locator('[data-widget="discussion"] button').click()
  assert.deepEqual(await page.evaluate(()=>window.host.events),['preview','notes'])
  assert.equal(await page.locator('[data-widget="link"] a').getAttribute('href'),'https://example.com/review')
  await page.evaluate(()=>window.host.$refs.help.open('widget_database'))
  const help=page.locator('.help-view[open]')
  await help.locator('h1').filter({hasText:'Table View widget database'}).waitFor()
  await help.locator('table').nth(8).waitFor({state:'attached'})
  assert(await help.locator('table').count()>=9)
  await page.evaluate(()=>window.appearance.language='ru')
  await help.locator('h1').filter({hasText:'Каталог виджетов Table View'}).waitFor()
  await capture(help,'table-widget-database-help')
  await page.setViewportSize({width:320,height:740})
  await page.evaluate(()=>window.host.$refs.help.open('table_widget_examples'))
  await help.locator('h1').filter({hasText:'Table View: примеры виджетов'}).waitFor()
  await help.locator('pre').nth(fixtures.length-1).waitFor({state:'attached'})
  assert((await help.boundingBox()).width<=320)
  assert.equal(await help.locator('pre').count(),fixtures.length)
  await page.evaluate(()=>window.host.$refs.help.open('table_widget_checklist'))
  await help.locator('h1').filter({hasText:'Table View: рабочий чеклист'}).waitFor()
  await help.getByText('108 классов/отдельных ошибочных ссылок.',{exact:false}).first().waitFor()
  assert.deepEqual(errors,[])
  assert(!requests.some(url=>url.includes('/admin/')),'The catalog checks must never access the running database')
  console.log('PASS: '+fixtures.length+' native XML descriptors/renderers, paired value captures, safe XML/JSON, height/scroll/empty, TH completion geometry/colors/type, clamping/errors, actions, bilingual Help and 320px. No live DB requests.')
} finally {
  clearTimeout(deadline)
  await browser?.close()
  await server?.close()
}
