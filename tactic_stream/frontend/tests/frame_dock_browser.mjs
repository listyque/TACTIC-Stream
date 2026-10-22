import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { describe } from '../../src/tactic_stream/shared_ui/shell/dock_chrome.ui.mjs';

const root = fileURLToPath(new URL('../', import.meta.url)),
  output = root + '../tools/frame_foundation/output/docks/';
const reference = JSON.parse(await readFile(output + 'native.json', 'utf8')),
  native = reference.captures;
for (const [name, hash] of Object.entries(reference.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(root + '../src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    hash,
    'Stale shared source: ' + name
  );
for (const [name, hash] of Object.entries(reference.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    hash,
    'Stale native source: ' + name
  );
const html = `<!doctype html><style>#app{height:700px;display:flex;flex-direction:column}</style><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import {defaults,captureLayout} from '/src/features/workspace/docks.js'
import {initializeAppearance,appearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance()
createApp({setup(){const docks=ref(null);window.dockHarness={docks,defaults,captureLayout};return()=>h(DockWorkspace,{ref:docks,login:'isolated-dock-header'})}}).mount('#app')
</script>`;
let browser;
const server = await createServer({
  root,
  configFile: false,
  cacheDir: root + '/node_modules/.vite/frame-dock-browser',
  plugins: [
    vue(),
    {
      name: 'dock-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/dock-fixture') return next();
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
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL,
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
      viewport: { width: 1800, height: 700 }
    }),
    errors = [],
    rows = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'dock-fixture');
  await page.waitForFunction(() => window.dockHarness?.docks.value);
  for (const width of [280, 600, 1200])
    for (const stacked of [false, true])
      for (const floating of [false, true]) {
        if (stacked && floating) continue; // Browser floating panels are individual; native floating stacks remain a separate capability.
        await page.evaluate(
          ({ width, stacked, floating }) => {
            const { defaults, captureLayout, docks } = window.dockHarness,
              state = defaults(),
              host = document
                .querySelector('.dock-workspace')
                .getBoundingClientRect();
            const members = stacked
              ? ['notes', 'snapshot', 'description']
              : ['notes'];
            for (const id of members)
              state.panels[id] = {
                visible: true,
                floating,
                rect: [0, 0, width / host.width, 1],
                z: 1
              };
            state.layout = {
              type: 'split',
              orientation: 'horizontal',
              ratio: 1 - width / host.width,
              first: { type: 'stack', panels: ['results'], active: 'results' },
              second: { type: 'stack', panels: members, active: 'notes' }
            };
            assertApplied(docks.value.apply(captureLayout(state)));
            function assertApplied(value) {
              if (!value) throw Error('Fixture layout rejected');
            }
          },
          { width, stacked, floating }
        );
        const panel = page.locator('[data-dock="notes"]:visible'),
          header = panel.locator('.dock-titlebar');
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))
            )
        );
        const actualWidth = await panel.evaluate(
          (element) => element.getBoundingClientRect().width
        );
        assert.equal(
          actualWidth,
          width,
          JSON.stringify({
            width,
            stacked,
            floating,
            actualWidth,
            layout: await page.evaluate(() =>
              window.dockHarness.docks.value.capture()
            )
          })
        );
        await page.evaluate(() => document.fonts.ready);
        const bounds = await header.boundingBox(),
          outer = await panel.boundingBox();
        assert.equal(outer.width, width);
        const expected = describe({
          width: width - (floating ? 7 : 6) * 2,
          kind: 'notes',
          stackSize: stacked ? 3 : 1,
          closable: true,
          floating,
          capabilities: {
            maximize: true,
            positionMenu: true,
            floatingResultsTitle: true,
            resultsActions: true
          }
        });
        assert.equal(bounds.height, 38);
        const controls = {};
        for (const node of expected.nodes.filter(
          (node) => node.visible !== false
        )) {
          const actual = await header
            .locator('[data-dock-control="' + node.id + '"]')
            .boundingBox();
          assert(actual, node.id);
          controls[node.id] = {
            x: actual.x - bounds.x,
            y: actual.y - bounds.y,
            width: actual.width,
            height: actual.height
          };
          for (const key of ['x', 'y', 'width', 'height'])
            assert(
              Math.abs(controls[node.id][key] - node[key]) < 0.01,
              `${width}/${stacked}/${floating} ${node.id}.${key}`
            );
        }
        const qt = native.find(
          (row) =>
            !row.original &&
            row.width === width &&
            row.stacked === stacked &&
            row.floating === floating
        );
        for (const id of ['dockHelp', 'dockGrip'])
          for (const key of ['x', 'y', 'width', 'height'])
            assert(
              Math.abs(
                controls[id][key] -
                  (qt.controls[id][key] - (key === 'x' ? 38 : 0))
              ) < 0.01,
              'Explicit extra browser action: ' + id + '.' + key
            );
        assert.deepEqual(controls.dockClose, qt.controls.dockClose);
        const screenshot = `stream-${width}-${Number(stacked)}-${Number(floating)}.png`;
        await page.screenshot({
          path: output + screenshot,
          clip: { x: outer.x, y: outer.y, width, height: 60 },
          animations: 'disabled'
        });
        rows.push({
          width,
          stacked,
          floating,
          controls,
          image: screenshot,
          native: qt.image
        });
      }
  assert.deepEqual(errors, []);
  await writeFile(output + 'stream.json', JSON.stringify(rows, null, 2));
  console.log(
    'Actual browser dock headers: 9 native/browser cases, common geometry and explicit capability differences passed'
  );
} finally {
  await browser?.close();
  await server.close();
}
