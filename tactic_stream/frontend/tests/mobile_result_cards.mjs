import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = fileURLToPath(
  new URL('../../.screenshots/mobile-result-cards/', import.meta.url)
);
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,reactive,h} from 'vue';
import '/src/App.vue';
import MobileResults from '/src/features/workspace/MobileResults.vue';
import {initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
initializeAppearance();
const state=reactive({parent:null,events:[]});window.fixture=state;
const nodes=Array.from({length:5},(_,i)=>({id:'asset'+i,kind:'object',depth:0,
 record:{__search_key__:'demo/asset?code=A'+i,name:'Robot arm '+i},title:'Robot arm '+i,
 subtitle:'Mechanical arm for the main character, with a long description.',
 accent:'#d35f65',preview:{},task_count:1,note_count:2,hasChildren:true,children:[],
 progress_items:[],info_items:[]}));
nodes[0].preview={image:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNqUAAAAASUVORK5CYII='};
nodes[4].title='Very long asset name describing a robot with several mechanical parts and references';
nodes[0].children=[{id:'reference',kind:'branch',title:'Reference',depth:1,
 branch:{kind:'process',process:'reference',count:1},record:{},hasChildren:true,
 children:[{id:'snapshot',kind:'snapshot',title:'robot.png',depth:2,
 record:{context:'reference',version:1},subtitle:'Reference image',children:[]}]}];
window.nodes=nodes;
createApp({setup(){return()=>h('main',{class:'result-presentation',style:'height:100dvh'},[
 h(MobileResults,{groups:[{key:'',nodes}],parent:state.parent,path:[],scroll:{},active:true,
 closedGroups:{},selectedKeys:[],onEnter:node=>{state.events.push('enter');state.parent=node},
 onBack:()=>{state.events.push('back');state.parent=null},
 onTasks:()=>state.events.push('tasks'),onNotes:()=>state.events.push('notes'),
 onUpload:()=>state.events.push('upload')})])}}).mount('#app');
</script></body></html>`;
let server, browser;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'mobile-result-cards-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/mobile-result-cards-test') return next();
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await owner.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0, watch: null },
    logLevel: 'error'
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  for (const language of ['en', 'ru']) {
    await page.addInitScript(
      (language) =>
        localStorage.setItem(
          'tactic_stream.appearance',
          JSON.stringify({ mode: 'dark', language })
        ),
      language
    );
    await page.goto(server.resolvedUrls.local[0] + 'mobile-result-cards-test');
    const row = page.locator('article[data-node-id="asset0"]');
    await row.waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() =>
      [...document.images].every((image) => image.complete)
    );
    for (const width of [320, 360, 390, 600, 700]) {
      await page.setViewportSize({ width, height: 844 });
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      await page.waitForFunction(() => {
        const host = document.querySelector('.mobile-result-list');
        const rows = [...host.querySelectorAll('article')].map((el) =>
          el.getBoundingClientRect()
        );
        return (
          rows.length > 1 &&
          rows.every(
            (r, i) =>
              Math.abs(r.width - host.clientWidth) < 1 &&
              (!i || r.top - rows[i - 1].bottom >= 5)
          )
        );
      });
      await page.waitForFunction(
        () =>
          document.querySelector('.result-item-copy')?.getBoundingClientRect()
            .width > 100
      );
      const geometry = await row.evaluate((el) => {
        const box = el.getBoundingClientRect(),
          title = el.querySelector('strong'),
          text = title.getBoundingClientRect(),
          preview = el
            .querySelector('.image-picker-preview')
            .getBoundingClientRect(),
          actions = el
            .querySelector('.result-mobile-actions')
            .getBoundingClientRect();
        return {
          titlePainted: title.contains(
            document.elementFromPoint(text.x + 4, text.y + text.height / 2)
          ),
          contained: text.right <= box.right - 28 && text.left >= preview.right,
          preview: [preview.width, preview.height],
          actionsBelow: actions.top >= text.bottom,
          overflow: document.documentElement.scrollWidth > innerWidth,
          height: box.height
        };
      });
      assert(geometry.titlePainted, JSON.stringify({ width, geometry }));
      assert(geometry.contained, 'Title stays between the thumbnail and menu');
      assert.deepEqual(geometry.preview, [40, 40]);
      assert(geometry.actionsBelow, 'Actions follow the text');
      assert(!geometry.overflow);
      assert(
        geometry.height < 160,
        'Compact card rather than an oversized empty panel'
      );
      const first = await row.boundingBox(),
        second = await page
          .locator('article[data-node-id="asset1"]')
          .boundingBox();
      assert(
        second.y - first.y - first.height >= 5,
        'Virtual rows keep their gap ' +
          JSON.stringify({ width, language, first, second })
      );
      await page.screenshot({ path: output + language + '-' + width + '.png' });
    }
    const labels =
      language === 'ru'
        ? ['Задачи', 'Заметки', 'Добавить файлы']
        : ['Tasks', 'Notes', 'Add files'];
    for (const label of labels)
      await row.getByRole('button', { name: label, exact: true }).tap();
    assert.deepEqual(await page.evaluate(() => window.fixture.events), [
      'tasks',
      'notes',
      'upload'
    ]);
    await row.locator('strong').tap();
    const header = page.locator('.mobile-result-header');
    await header.waitFor();
    assert(await header.locator('strong,h2').first().isVisible());
    const back = header.getByRole('button', {
      name: language === 'ru' ? 'Назад' : 'Back',
      exact: true
    });
    const backBox = await back.boundingBox(),
      previewBox = await header.locator('.result-preview').boundingBox();
    assert(
      backBox.x + backBox.width <= previewBox.x,
      'Back does not overlap the thumbnail'
    );
    await page.locator('article[data-node-id="reference"] strong').tap();
    const snapshot = page.locator('article[data-node-id="snapshot"]');
    await snapshot.waitFor();
    assert(await snapshot.locator('strong').isVisible());
    await page
      .locator('.mobile-result-header')
      .getByRole('button', {
        name: language === 'ru' ? 'Назад' : 'Back',
        exact: true
      })
      .tap();
    await row.waitFor();
    assert.deepEqual(await page.evaluate(() => window.fixture.events), [
      'tasks',
      'notes',
      'upload',
      'enter',
      'enter',
      'back'
    ]);
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS mobile card text/preview/spacing, 320–700px EN/RU, touch actions, child navigation and back'
  );
} finally {
  await browser?.close();
  await server?.close();
}
