import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import '/src/App.vue';
import UserProfile from '/src/features/users/UserProfile.vue';
import {windowDirective} from '/src/controls/window.js';
import {initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
initializeAppearance();
createApp({setup(){return()=>h(UserProfile,{ref:instance=>window.profile=instance,ticket:'fixture',project:'demo',login:'artist'})}})
  .directive('window',windowDirective).mount('#app');
</script></body></html>`;
const title = Array.from(
  { length: 1000 },
  (_, i) => 'render/frame' + String(i).padStart(4, '0') + '.exr'
).join(', ');
const records = Array.from({ length: 25 }, (_, index) => ({
  eventId: 'SNAP' + index,
  searchKey: 'sthpw/snapshot?code=SNAP' + index,
  kind: 'publication',
  itemTitle: [9, 10, 11].includes(index) ? title : 'frame.exr',
  targetTitle: 'Shot',
  targetSearchKey: 'demo/shot?code=SHOT',
  actor: 'artist',
  actorLabel: 'Alice Artist',
  actorInitials: 'AA',
  actorColor: '#ad4242',
  process: 'publish',
  version: '001'
}));
let server, browser;
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'profile-activity-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/profile-test') return next();
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
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1450, height: 1000 }
  });
  const errors = [],
    requests = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    requests.push(path);
    let result;
    if (path === '/admin/user-profile/read')
      result = {
        profile: {
          login: 'artist',
          displayName: 'Alice Artist',
          initials: 'AA',
          avatarColor: '#ad4242',
          groups: [],
          roles: []
        },
        users: [],
        permissions: { manage: false, edit: false }
      };
    else if (path === '/admin/user-profile/summary')
      result = {
        taskSummary: { total: 0, incomplete: 0, overdue: 0, dueThisWeek: 0 },
        statusSummary: [],
        processSummary: [],
        permissions: { viewWorkHours: false }
      };
    else if (path === '/admin/activity-feed') result = { records };
    else throw Error('Unexpected profile request: ' + path);
    await route.fulfill({ json: { result } });
  });
  await page.goto(
    'http://127.0.0.1:' + server.httpServer.address().port + '/profile-test'
  );
  await page.waitForFunction(() => window.profile);
  await page.evaluate(() => window.profile.open());
  const dialog = page.getByRole('dialog', {
    name: 'User profile',
    exact: true
  });
  const cards = dialog.locator('.activity-event-card');
  await page.waitForFunction(
    () => document.querySelectorAll('.profile-activity-cards > *').length === 6
  );
  assert.equal(await cards.count(), 6);
  const first = await cards.first().elementHandle();
  await dialog.getByRole('button', { name: 'Show more', exact: true }).click();
  await page.waitForFunction(
    () => document.querySelectorAll('.profile-activity-cards > *').length === 25
  );
  assert.equal(await cards.count(), 25);
  assert((await cards.nth(9).innerText()).includes(title));
  assert(await first.evaluate((element) => element.isConnected));
  await dialog.getByRole('button', { name: 'Show less', exact: true }).click();
  await page.waitForFunction(
    () => document.querySelectorAll('.profile-activity-cards > *').length === 6
  );
  assert.equal(await cards.count(), 6);
  for (const width of [700, 360, 1450]) {
    await page.setViewportSize({ width, height: 850 });
    await page.evaluate(async () => {
      await document.fonts.ready;
      await new Promise(requestAnimationFrame);
      await new Promise(requestAnimationFrame);
    });
    await page.waitForFunction(() => {
      const content = document.querySelector('.profile-activity-cards');
      const host = document.querySelector(
        '[data-frame="profileActivityCards"]'
      );
      return (
        content?.children.length === 6 &&
        host?.getBoundingClientRect().height > 0 &&
        Math.abs(
          host.getBoundingClientRect().height -
            content.getBoundingClientRect().height
        ) < 1
      );
    });
    const heights = await page.evaluate(async () => {
      const height = () =>
        document
          .querySelector('[data-frame="profileActivityCards"]')
          .getBoundingClientRect().height;
      const first = height();
      await new Promise(requestAnimationFrame);
      await new Promise(requestAnimationFrame);
      return [first, height()];
    });
    assert.equal(heights[0], heights[1]);
  }
  assert.deepEqual(
    requests.sort(),
    [
      '/admin/activity-feed',
      '/admin/user-profile/read',
      '/admin/user-profile/summary'
    ].sort()
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS real browser profile: only six collapsed cards, show more/less, intact long titles, retained first cards, narrow layout and no extra requests'
  );
} finally {
  await browser?.close();
  await server?.close();
}
