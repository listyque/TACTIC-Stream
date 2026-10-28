import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><body style="margin:0"><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue';
import ItemComposition from '/src/features/interface/ItemComposition.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',mode:'dark'});initializeAppearance();
const count=ref(5);window.setCount=value=>count.value=value;window.actions=[];
const layout={flow:'grid',collection:'tree',columns:12,gap:4,elements:[
 ...[['tasks','task',1,'task_count'],['notes','comment',7,'note_count']].map(([name,icon,column,field])=>({name,kind:'button',row:1,column,span:6,rows:1,height:40,parent:'',variant:'all',options:{action:name,icon,badge:'node.'+field}}))
]};
createApp({render:()=>h(ItemComposition,{layout,node:{kind:'object',record:{},task_count:count.value,note_count:count.value},onAction:action=>window.actions.push(action)})}).mount('#app');
</script></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  cacheDir: root + '/node_modules/.vite/item-action-badges',
  plugins: [
    vue(),
    {
      name: 'item-action-badges',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/') return next();
          res.setHeader('Content-Type', 'text/html');
          res.end(await server.transformIndexHtml(req.url, html));
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 360, height: 120 },
    deviceScaleFactor: 1.5
  });
  page.setDefaultTimeout(6000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0]);
  for (const count of [5, 1, 12, 99, 100, 0, 5]) {
    await page.evaluate((value) => window.setCount(value), count);
    const badges = page.locator('.app-button-badge');
    await page.waitForFunction((count) => {
      const badges = [...document.querySelectorAll('.app-button-badge')];
      return count
        ? badges.length === 2 &&
            badges.every(
              (item) =>
                item.textContent === (count > 99 ? '99+' : String(count))
            )
        : badges.length === 0;
    }, count);
    for (const badge of await badges.all()) {
      assert(await badge.isVisible());
      assert((await badge.boundingBox()).width > 3);
    }
    for (const name of ['tasks', 'notes']) {
      assert.equal(
        await page
          .locator(`[data-frame="itemComposition_${name}Button"]`)
          .getAttribute('aria-label'),
        name[0].toUpperCase() + name.slice(1) + (count ? ` · ${count}` : '')
      );
    }
    if (count === 5 && process.argv[2])
      await page.screenshot({ path: process.argv[2] });
  }
  await page.locator('[data-frame="itemComposition_tasksButton"]').click();
  await page.locator('[data-frame="itemComposition_notesButton"]').click();
  assert.deepEqual(await page.evaluate(() => window.actions), [
    'tasks',
    'notes'
  ]);
  await page.locator('[data-frame="itemComposition_tasksButton"]').focus();
  await page.keyboard.press('Space');
  assert.deepEqual(await page.evaluate(() => window.actions), [
    'tasks',
    'notes',
    'tasks'
  ]);
  assert.deepEqual(errors, []);
  console.log(
    'Custom task/note badges paint counts, update, hide zero and preserve actions'
  );
} finally {
  await browser.close();
  await server.close();
}
