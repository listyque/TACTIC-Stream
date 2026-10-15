import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1400, height: 1000 },
    hasTouch: true
  });
  page.setDefaultTimeout(8000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const url =
    'http://127.0.0.1:' +
    server.httpServer.address().port +
    '/tools/frame_foundation/docks.html';
  await page.goto(url);
  await page.waitForFunction(() => !!window.dockHarness?.docks.value);
  const setup = async (stacked) =>
    page.evaluate((stacked) => {
      const { docks, defaults, captureLayout, place } = window.dockHarness;
      const state = defaults();
      state.panels.notes.visible = state.panels.description.visible = true;
      state.layout = place(state.layout, 'notes', 'right');
      state.layout = place(
        state.layout,
        'description',
        stacked ? 'center' : 'left',
        stacked ? 'notes' : 'results'
      );
      assertApplied(docks.value.apply(captureLayout(state)));
      function assertApplied(value) {
        if (!value) throw Error('Layout rejected');
      }
    }, stacked);
  const capture = () =>
    page.evaluate(() => window.dockHarness.docks.value.capture());
  await setup(true);
  const description = page.locator('[data-dock="description"]');
  await description
    .getByRole('tab', { name: 'Task Inspector', exact: true })
    .tap();
  const notes = page.locator('[data-dock="notes"]');
  await notes.locator('[data-dock-control="dockMaximize"]').click();
  assert.equal((await capture()).presentation.maximized, 'notes');
  await notes.locator('[data-dock-control="dockMaximize"]').tap();
  assert.equal((await capture()).presentation.maximized, '');
  await notes.locator('[data-dock-control="dockClose"]').tap();
  assert.equal(
    (await capture()).panels.find((row) => row.panel_id === 'notes').visible,
    false
  );
  await setup(false);
  const slot = await capture();
  await notes.locator('[data-dock-control="dockPosition"] > summary').click();
  await notes.getByRole('button', { name: 'Float panel', exact: true }).click();
  assert.deepEqual(
    (await capture()).layout,
    slot.layout,
    'Floating preserves its structural dock slot'
  );
  await notes.locator('[data-dock-control="dockPosition"] > summary').click();
  await notes.getByRole('button', { name: 'Dock panel', exact: true }).click();
  assert.deepEqual(
    (await capture()).layout,
    slot.layout,
    'Docking returns to the saved slot'
  );
  const initial = await capture();
  const grip = notes.locator('[data-dock-control="dockGrip"]');
  const box = await grip.boundingBox();
  const workspace = await page.locator('.dock-workspace').boundingBox();
  async function dragTo(x, y) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(x, y, { steps: 5 });
  }
  await dragTo(workspace.x + 3, workspace.y + workspace.height / 2);
  assert.match(await page.locator('.dock-drop-guide').innerText(), /left/);
  assert(
    Math.abs(
      (await page.locator('.dock-snap-preview').boundingBox()).width -
        workspace.width * 0.28
    ) < 1
  );
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.deepEqual(
    await capture(),
    initial,
    'Escape rolls back the whole drag'
  );
  await dragTo(
    workspace.x + workspace.width / 2,
    workspace.y + workspace.height / 2
  );
  const target = await page.locator('[data-dock="results"]').boundingBox();
  await page.mouse.move(
    target.x + target.width / 2,
    target.y + target.height / 2,
    { steps: 5 }
  );
  assert.match(await page.locator('.dock-drop-guide').innerText(), /center/);
  await page.mouse.up();
  assert.equal(
    await notes.getByRole('tab', { name: 'Search', exact: true }).count(),
    1
  );
  await notes.getByRole('tab', { name: 'Search', exact: true }).click();
  const saved = await capture();
  await page.reload();
  await page.waitForFunction(() => !!window.dockHarness?.docks.value);
  assert.deepEqual(
    await capture(),
    saved,
    'Saved stack and active tab survive host recreation'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Docks: first click/tap, maximize/restore/close, shared root/center preview, Escape rollback and saved active tab passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
