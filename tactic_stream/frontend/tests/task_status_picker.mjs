import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.env.STREAM_STATUS_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const html = `<!doctype html><div id="app"></div><script type="module">
import {createApp,h,ref,reactive,nextTick} from 'vue';
import Row from '/src/features/tasks/TaskRowValue.vue';
import Editor from '/src/features/interface/TaskTableEditor.vue';
import Status from '/src/controls/StatusSelect.vue';
import {initializeAppearance,appearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
const task=reactive({key:'one',title:'One task',status:'',__status__:{}}),events=[],inline=ref(null),width=ref(244),blocked=ref(false);
const choices=[{value:'ready',label:'Готов к работе',color:'#23ab65'},{value:'done',label:'Done',color:'#dfb42e'},{value:'retired',label:'Removed',color:'#e14c42',enabled:false}];
const editor=reactive({plans:[{}],fields:[{name:'status',editable:true}],values:{status:''},statuses:['ready','done','retired'],statusChoices:choices});
window.statusHarness={task,events,inline,width,blocked,editor,appearance};
createApp({render:()=>h('main',{style:{padding:'40px'}},[
 h('div',{id:'status-row',style:{width:width.value+'px',height:'29px',marginBottom:'80px'}},h(Row,{task,column:{key:'status',sourceKey:'status',label:'Status'},blocked:blocked.value,onEdit:async event=>{const anchor=event.currentTarget,bounds=Object.assign(anchor.getBoundingClientRect(),{anchor});editor.values.status=task.status;await nextTick();await inline.value.open(bounds);}})),
 h(Editor,{ref:inline,editor,busy:blocked.value,onChange:(name,value)=>{events.push([name,value]);task.status=value;task.__status__=choices.find(choice=>choice.value===value);inline.value.close();}}),
 h(Status,{id:'field-status',value:'ready',options:choices,actionField:false,disabled:blocked.value,onChange:value=>events.push(['field',value])}),
 h(Status,{id:'mixed-status',value:'',options:choices,placeholder:'Mixed status',onChange:value=>events.push(['mixed',value])})
])}).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'status-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/status') return next();
          try {
            res.setHeader('Content-Type', 'text/html');
            res.end(await server.transformIndexHtml(req.url, html));
          } catch (error) {
            next(error);
          }
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
await server.listen();
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
      viewport: { width: 1000, height: 700 },
      hasTouch: true
    }),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'status');
  const idle = page.locator('#status-row button'),
    editor = page.locator('.task-table-editor'),
    menu = editor.locator('.status-select');
  await idle.waitFor();
  await page.evaluate(() => document.fonts.ready);
  const geometry = (locator) =>
    locator.evaluate((element) => {
      const box = element.getBoundingClientRect(),
        style = getComputedStyle(element);
      return {
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        size: style.fontSize,
        weight: style.fontWeight,
        text: element.textContent.trim()
      };
    });
  for (const mode of ['dark', 'light'])
    for (const language of ['en', 'ru'])
      for (const width of [140, 244]) {
        await page.evaluate(
          ({ mode, language, width }) => {
            Object.assign(window.statusHarness.appearance, { mode, language });
            window.statusHarness.width.value = width;
          },
          { mode, language, width }
        );
        const before = await geometry(
          idle.locator('[data-frame="taskTableCellDisplayLabel"]')
        );
        await idle.click();
        await page.locator('.task-table-editor:popover-open').waitFor();
        assert.equal(
          await menu.count(),
          1,
          'Inline editor retains colored status choices'
        );
        await menu.locator('summary').waitFor();
        const after = await geometry(
          menu.locator('.status-select-label').first()
        );
        assert.equal(
          after.text,
          before.text,
          'Editing retains empty/current caption'
        );
        assert.equal(after.size, before.size, 'Editing retains the text size');
        assert.equal(
          after.weight,
          before.weight,
          'Editing retains the text weight'
        );
        assert(Math.abs(after.x - before.x) < 1, 'Editing retains label inset');
        const row = await idle.boundingBox(),
          trigger = await menu.locator('summary').boundingBox();
        for (const key of ['x', 'y', 'width', 'height'])
          assert(Math.abs(row[key] - trigger[key]) < 1, key);
        for (const [label, color] of [
          ['Готов к работе', 'rgb(35, 171, 101)'],
          ['Done', 'rgb(223, 180, 46)'],
          ['Removed', 'rgb(225, 76, 66)']
        ]) {
          const option = menu.getByRole('menuitemradio', {
            name: label,
            exact: true
          });
          assert.equal(
            await option
              .locator('.status-select-dot')
              .evaluate((element) => getComputedStyle(element).backgroundColor),
            color
          );
        }
        assert(
          await menu
            .getByRole('menuitemradio', { name: 'Removed' })
            .isDisabled()
        );
        if (output && width === 244 && language === 'en')
          await page.screenshot({ path: output + '/browser-' + mode + '.png' });
        await menu.locator('summary').press('Escape');
        await editor.press('Escape');
      }
  await idle.click();
  await menu.getByRole('menuitemradio', { name: 'Готов к работе' }).click();
  assert.deepEqual(await page.evaluate(() => window.statusHarness.events), [
    ['status', 'ready']
  ]);
  assert.equal(
    await idle
      .locator('[data-frame="taskTableCellAccent"]')
      .evaluate((element) => getComputedStyle(element).backgroundColor),
    'rgb(35, 171, 101)'
  );
  await idle.press('Enter');
  await menu
    .getByRole('menuitemradio', { name: 'Done', exact: true })
    .waitFor();
  assert.equal(
    (await menu.locator('summary').innerText()).trim(),
    'Готов к работе'
  );
  assert.equal(
    await menu
      .locator('summary .status-select-dot')
      .evaluate((element) => getComputedStyle(element).backgroundColor),
    'rgb(35, 171, 101)'
  );
  await menu.locator('summary').press('End');
  assert.equal(
    await page.evaluate(() => document.activeElement.textContent.trim()),
    'Done'
  );
  await page.keyboard.press('Enter');
  assert.deepEqual(await page.evaluate(() => window.statusHarness.events), [
    ['status', 'ready'],
    ['status', 'done']
  ]);
  const point = await idle.boundingBox();
  await page.touchscreen.tap(
    point.x + point.width / 2,
    point.y + point.height / 2
  );
  await menu.getByRole('menuitemradio', { name: 'Готов к работе' }).tap();
  assert.equal(
    await page.evaluate(() => window.statusHarness.task.status),
    'ready'
  );
  assert.equal(
    await page
      .locator('#mixed-status > summary .status-select-label')
      .innerText(),
    'Mixed status'
  );
  await page.evaluate(() => {
    window.statusHarness.blocked.value = true;
  });
  assert(await idle.isDisabled());
  await page.locator('#field-status > summary').click();
  assert.equal(
    await page.locator('#field-status').getAttribute('open'),
    null,
    'Disabled field does not open'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: real row/editor caption, color, geometry and font parity; pipeline option colors; disabled states; one scoped change per mouse/key/touch activation; mixed placeholder and safe unmount'
  );
} finally {
  await browser?.close();
  await server.close();
}
