import assert from 'node:assert/strict'
import {readFile, writeFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import {chromium} from 'playwright'

const root = fileURLToPath(new URL('../../', import.meta.url))
const output = root + 'tools/frame_foundation/output/'
const reference = JSON.parse(await readFile(output + 'foundation.json', 'utf8'))
const server = await createServer({
  root, configFile:false, logLevel:'error',
  resolve:{alias:{vue:root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'}},
  server:{host:'127.0.0.1',port:0,watch:{ignored:['**/output/**','**/.tmp/**','**/.venv/**']}}
})
await server.listen()
const browser = await chromium.launch({headless:true,channel:process.env.STREAM_BROWSER_CHANNEL || 'msedge'})
let checks = 0
try {
  const page = await browser.newPage({reducedMotion:'no-preference'})
  const errors = []
  page.on('pageerror',error => errors.push(error.message))
  await page.goto('http://127.0.0.1:' + server.httpServer.address().port + '/tools/frame_foundation/index.html')
  await page.waitForFunction(() => window.foundation)
  for (let index=0; index<reference.cases.length; index++) {
    const sample = reference.cases[index], expected = reference.values[index]
    const actual = await page.evaluate(async ({sample,expected}) => {
      const {appearance,hostedPalette} = window.foundation
      const hex = values => '#' + values.map(value => value.toString(16).padStart(2,'0')).join('')
      appearance.theme = sample.style
      appearance.mode = sample.dark ? 'dark' : 'light'
      hostedPalette.value = {light:hex(sample.accent),dark:hex(sample.accent),lightBase:hex(sample.base),darkBase:hex(sample.base)}
      for (const flag of ['click','hover','fade','popup']) appearance[flag+'Animations'] = true
      await Promise.resolve()
      const probe = document.querySelector('#probe'), colors = {}, variables = {}
      for (const [role,variable] of Object.entries(expected.cssRoles)) {
        probe.style.color = 'var(' + variable + ')'
        colors[role] = getComputedStyle(probe).color.match(/[\d.]+/g).map(Number)
      }
      const style = getComputedStyle(document.documentElement)
      for (const name of Object.keys(expected.css)) variables[name] = style.getPropertyValue(name).trim()
      return {colors,variables}
    },{sample,expected})
    for (const [role,channels] of Object.entries(actual.colors)) {
      const target = expected.colors[role]
      for (let channel=0;channel<3;channel++) assert.ok(Math.abs(channels[channel]-target[channel]) <= 1, sample.style+' '+role)
      checks++
    }
    assert.deepEqual(actual.variables,expected.css,'shared CSS variables '+JSON.stringify(sample))
    checks += Object.keys(expected.css).length
  }
  for (const mask of Array.from({length:16},(_,index)=>index)) {
    const measured = await page.evaluate(async mask => {
      for (const [bit,flag] of ['click','hover','fade','popup'].entries()) window.foundation.appearance[flag+'Animations'] = !!(mask & (1<<bit))
      await Promise.resolve()
      const style = getComputedStyle(document.documentElement)
      return Object.fromEntries(['click','hover','fade','popup'].map(flag=>[flag,parseFloat(style.getPropertyValue('--motion-'+flag))]))
    },mask)
    for (const [bit,flag] of ['click','hover','fade','popup'].entries()) {
      assert.equal(measured[flag] === 0, !(mask & (1<<bit)),flag+' preference is independent')
      checks++
    }
  }
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.waitForFunction(() => getComputedStyle(document.documentElement).getPropertyValue('--motion-click').trim() === '0ms')
  for(const name of ['click','hover','fade','popup']) assert.equal(await page.evaluate(name=>getComputedStyle(document.documentElement).getPropertyValue('--motion-'+name).trim(),name),'0ms')
  assert.deepEqual(errors,[])
  await writeFile(output+'browser-foundation.json',JSON.stringify({cases:reference.cases.length,checks,reducedMotion:true},null,2))
  console.log('Shared foundation in browser:',checks,'checks passed')
} finally {
  await browser.close()
  await server.close()
}
