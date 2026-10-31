import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.env.WINDOW_HEADER_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const html = `<!doctype html><style>#app{height:700px;display:flex;flex-direction:column}</style><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue';
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue';
import AppDialog from '/src/controls/AppDialog.vue';
import AppButton from '/src/controls/AppButton.vue';
import {defaults,captureLayout} from '/src/features/workspace/docks.js';
import {initializeAppearance,appearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
createApp({setup(){const docks=ref(null),dialog=ref(null),help=ref('');window.headerHarness={docks,dialog,help,defaults,captureLayout,appearance};return()=>[
 h(DockWorkspace,{ref:docks,login:'isolated-round-header',onHelp:topic=>help.value=topic}),
 h(AppDialog,{ref:dialog,title:'Inspector',windowKind:'inspector'},()=>h(AppButton,{iconOnly:true,icon:'refresh',label:'Service refresh'}))
]}}).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'round-header-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url !== '/round-header') return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await server.transformIndexHtml(request.url, html));
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
let browser;
await server.listen();
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1200, height: 700 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'round-header');
  await page.waitForFunction(() => window.headerHarness?.docks.value);
  async function layout(width, stacked = false, floating = false) {
    await page.evaluate(
      ({ width, stacked, floating }) => {
        const { docks, defaults, captureLayout } = window.headerHarness,
          state = defaults();
        const members = stacked
          ? ['notes', 'snapshot', 'description']
          : ['notes'];
        for (const id of members)
          state.panels[id] = {
            visible: true,
            floating,
            rect: [0, 0, width / 1200, 1],
            z: 1
          };
        state.layout = {
          type: 'split',
          orientation: 'horizontal',
          ratio: 1 - width / 1200,
          first: { type: 'stack', panels: ['results'], active: 'results' },
          second: { type: 'stack', panels: members, active: 'notes' }
        };
        if (!docks.value.apply(captureLayout(state)))
          throw Error('Layout rejected');
      },
      { width, stacked, floating }
    );
  }
  const header = page.locator('[data-dock="notes"] > .dock-titlebar');
  async function roundControls(locator) {
    const shapes = await locator.evaluateAll((elements) =>
      elements.map((element) => {
        const target = element.matches('details')
          ? element.querySelector('summary')
          : element;
        const style = getComputedStyle(target),
          surface = getComputedStyle(target, '::before'),
          box = target.getBoundingClientRect();
        return {
          id: element.dataset.dockControl || target.getAttribute('aria-label'),
          width: box.width,
          height: box.height,
          radius: style.borderTopLeftRadius,
          ownerRadius: getComputedStyle(element).borderTopLeftRadius,
          ownerStyle: element.style.cssText,
          surface:
            surface.content === 'none' ? null : surface.borderTopLeftRadius
        };
      })
    );
    assert(shapes.length > 0);
    for (const shape of shapes) {
      assert.equal(shape.width, shape.height, shape.id);
      assert(
        shape.radius === '50%' || parseFloat(shape.radius) >= shape.width / 2,
        JSON.stringify(shape)
      );
      if (shape.surface)
        assert(
          shape.surface === '50%' ||
            parseFloat(shape.surface) >= shape.width / 2 - 1,
          JSON.stringify(shape)
        );
    }
  }
  for (const mode of ['dark', 'light'])
    for (const width of [280, 600])
      for (const stacked of [false, true]) {
        await page.evaluate((mode) => {
          window.headerHarness.appearance.mode = mode;
        }, mode);
        await layout(width, stacked);
        const actions = header.locator(
          '[data-dock-control]:not([data-dock-control="dockGrip"]):not([data-dock-control="dockIcon"]):not([data-dock-control="dockTitle"]):not([data-dock-control="dockTabs"])'
        );
        await roundControls(actions);
        await header.locator('[data-dock-control="dockHelp"]').hover();
        await roundControls(actions);
        if (output && width === 600 && !stacked)
          await header.screenshot({
            path: output + '/browser-' + mode + '.png'
          });
      }
  await layout(600, false, true);
  await roundControls(
    header.locator(
      ':scope > button,:scope > [data-dock-control="dockPosition"]'
    )
  );
  const help = header.locator('[data-dock-control="dockHelp"]');
  const glyph = await help.locator('.app-icon').boundingBox();
  await page.mouse.click(glyph.x + glyph.width / 2, glyph.y + glyph.height / 2);
  assert.equal(
    await page.evaluate(() => window.headerHarness.help.value),
    'dock.notes'
  );
  const position = header.locator('[data-dock-control="dockPosition"]');
  const menuGlyph = await position.locator('summary .app-icon').boundingBox();
  await page.touchscreen.tap(
    menuGlyph.x + menuGlyph.width / 2,
    menuGlyph.y + menuGlyph.height / 2
  );
  await page.waitForFunction(
    () =>
      document.querySelector(
        '[data-dock="notes"] [data-dock-control="dockPosition"]'
      ).open
  );
  await position.locator('summary').press('Escape');
  const maximize = header.locator('[data-dock-control="dockMaximize"]');
  await maximize.press('Enter');
  await roundControls(
    header.locator(
      ':scope > button,:scope > [data-dock-control="dockPosition"]'
    )
  );
  await maximize.click();
  await header.locator('[data-dock-control="dockClose"]').tap();
  await page.waitForFunction(
    () =>
      !document.querySelector('[data-dock="notes"]') ||
      getComputedStyle(document.querySelector('[data-dock="notes"]'))
        .display === 'none'
  );
  await page.evaluate(() => window.headerHarness.dialog.value.show());
  const dialog = page.locator('dialog[open]');
  await roundControls(
    dialog.locator(
      '.app-window-titlebar > .icon-button,.app-window-controls > .icon-button'
    )
  );
  assert(
    parseFloat(
      await dialog
        .getByRole('button', { name: 'Service refresh' })
        .evaluate((element) => getComputedStyle(element).borderRadius)
    ) < 10,
    'Service control stays square'
  );
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  assert.equal(await page.locator('dialog[open]').count(), 0);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: round dock/window chrome, dark/light, narrow/wide/stacks/floating/hover, real glyph mouse/touch/key actions, retained Close and square service controls'
  );
} finally {
  await browser?.close();
  await server.close();
}
