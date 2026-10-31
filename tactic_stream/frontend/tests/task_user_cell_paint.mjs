import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url)),
  output = process.env.STREAM_USER_CELL_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const html = `<!doctype html><div id="app"></div><script type="module">
import {createApp,h,reactive,ref,nextTick} from 'vue';
import Row from '/src/features/tasks/TaskRowValue.vue';
import Editor from '/src/features/interface/TaskTableEditor.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
const users=[{value:'admin',label:'admin',initials:'A',avatarColor:'#447f74'},{value:'artist',label:'Alex Artist',initials:'AA',avatarColor:'#4476b0'}],task=reactive({title:'One task',assigned:'admin',assignedLogin:'admin',assignedUser:users[0]}),width=ref(244),blocked=ref(false),editor=ref(null),changes=[];
const plan=reactive({plans:[{}],fields:[{name:'assigned',editable:true}],values:{assigned:'admin'},users});
window.userCell={appearance,width,blocked,task,changes,editor};
createApp({render:()=>h('main',{style:{padding:'40px'}},[
 h('div',{id:'user-cell',style:{width:width.value+'px',height:'29px'}},h(Row,{task,column:{key:'assigned',sourceKey:'assigned',label:'Assigned to'},blocked:blocked.value,onEdit:async event=>{const anchor=event.currentTarget,bounds=Object.assign(anchor.getBoundingClientRect(),{anchor});plan.values.assigned=task.assignedLogin;await nextTick();editor.value.open(bounds);}})),
 h(Editor,{ref:editor,editor:plan,onChange:(field,value)=>{changes.push([field,value]);const user=users.find(user=>user.value===value);Object.assign(task,{assigned:user?.label||'Not assigned',assignedLogin:value,assignedUser:user});editor.value.close();}})
])}).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'user-cell-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/user-cell') return next();
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
      viewport: { width: 800, height: 700 },
      hasTouch: true
    }),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'user-cell');
  const idle = page.locator('#user-cell button'),
    surface = idle.locator('[data-frame="taskTableCellSurface"]'),
    editor = page.locator('.task-table-editor'),
    picker = editor.locator('.user-combo-box'),
    trigger = picker.locator(':scope > summary');
  await idle.waitFor();
  await page.evaluate(() => document.fonts.ready);
  const paint = (element) => {
    const box = element.getBoundingClientRect(),
      style = getComputedStyle(element);
    return {
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height,
      radius: style.borderRadius,
      background: style.backgroundColor,
      font: style.fontSize,
      weight: style.fontWeight,
      color: style.color
    };
  };
  for (const mode of ['dark', 'light'])
    for (const language of ['en', 'ru'])
      for (const width of [140, 244]) {
        await page.evaluate(
          ({ mode, language, width }) => {
            Object.assign(window.userCell.appearance, { mode, language });
            window.userCell.width.value = width;
          },
          { mode, language, width }
        );
        await idle.hover();
        const before = await surface.evaluate(paint),
          label = await idle
            .locator('[data-frame="taskTableCellDisplayLabel"]')
            .evaluate(paint);
        assert.equal(
          await idle.evaluate(
            (element) => getComputedStyle(element).backgroundColor
          ),
          'rgba(0, 0, 0, 0)',
          'Idle hover must not add a second filled surface'
        );
        const center = await idle.boundingBox();
        await page.mouse.move(
          center.x + center.width / 2,
          center.y + center.height / 2
        );
        await page.mouse.down();
        assert.equal(
          await idle.evaluate(
            (element) => getComputedStyle(element).backgroundColor
          ),
          'rgba(0, 0, 0, 0)',
          'Press must not add a second filled surface'
        );
        await page.mouse.up();
        await trigger.waitFor();
        await picker.locator('.account-panel:popover-open').waitFor();
        const after = await trigger.evaluate(paint),
          editingLabel = await picker
            .locator('.user-combo-label')
            .evaluate(paint);
        for (const key of ['x', 'y', 'width', 'height', 'radius'])
          assert.equal(
            after[key],
            before[key],
            key + ' changes on entering the user editor'
          );
        assert.equal(
          editingLabel.font,
          label.font,
          'User label must retain its font size'
        );
        assert.equal(
          editingLabel.weight,
          label.weight,
          'User label must retain its weight'
        );
        assert.equal(
          editingLabel.color,
          label.color,
          'Opening must not recolor the user label'
        );
        assert.equal(
          editingLabel.x,
          label.x,
          'User label must retain its inset'
        );
        assert.equal(
          await idle.evaluate(
            (element) => getComputedStyle(element).backgroundColor
          ),
          'rgba(0, 0, 0, 0)'
        );
        if (output && width === 244 && language === 'en')
          await page.screenshot({ path: output + '/browser-' + mode + '.png' });
        await trigger.press('Escape');
        await editor.press('Escape');
      }
  await idle.press('Enter');
  await picker.getByRole('radio', { name: /Alex Artist/ }).click();
  assert.deepEqual(await page.evaluate(() => window.userCell.changes), [
    ['assigned', 'artist']
  ]);
  assert.equal(
    await idle.evaluate((element) => getComputedStyle(element).backgroundColor),
    'rgba(0, 0, 0, 0)',
    'Returned focus must not fill the trigger'
  );
  await idle.focus();
  await page.keyboard.press('ArrowRight');
  assert.notEqual(
    await surface.evaluate((element) => getComputedStyle(element).boxShadow),
    'none',
    'Keyboard focus remains visible inside the rounded cell'
  );
  const point = await idle.boundingBox();
  await page.touchscreen.tap(
    point.x + point.width / 2,
    point.y + point.height / 2
  );
  await picker.getByRole('radio', { name: 'admin', exact: true }).tap();
  assert.equal(
    await page.evaluate(() => window.userCell.task.assignedLogin),
    'admin'
  );
  await page.evaluate(() => {
    window.userCell.blocked.value = true;
  });
  assert(await idle.isDisabled());
  assert.equal(
    await idle.evaluate((element) => getComputedStyle(element).backgroundColor),
    'rgba(0, 0, 0, 0)'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: user-cell paint stays transparent on hover/press/focus/disabled; radius, bounds, font and inset survive editor activation; dark/light EN/RU narrow/wide mouse/key/touch'
  );
} finally {
  await browser?.close();
  await server.close();
}
