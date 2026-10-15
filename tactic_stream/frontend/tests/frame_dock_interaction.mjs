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

  // A nested tree must use each subtree's minimum, preserving preferred ratios.
  await page.evaluate(() => {
    const { docks, defaults, captureLayout } = window.dockHarness;
    const state = defaults();
    state.panels.tasks.visible =
      state.panels.notes.visible =
      state.panels.snapshot.visible =
        true;
    state.layout = {
      type: 'split',
      orientation: 'horizontal',
      ratio: 0.66,
      first: {
        type: 'split',
        orientation: 'horizontal',
        ratio: 0.34,
        first: { type: 'stack', panels: ['results'], active: 'results' },
        second: { type: 'stack', panels: ['tasks'], active: 'tasks' }
      },
      second: {
        type: 'stack',
        panels: ['notes', 'description', 'snapshot'],
        active: 'notes'
      }
    };
    docks.value.apply(captureLayout(state));
  });
  const preferred = (await capture()).layout;
  const resultWidth = () =>
    page
      .locator('[data-dock="results"]')
      .evaluate((item) => item.getBoundingClientRect().width);
  const wideWidth = await resultWidth();
  await page.setViewportSize({ width: 760, height: 640 });
  await page.waitForFunction(
    () =>
      Math.abs(
        document.querySelector('[data-dock="results"]').getBoundingClientRect()
          .width -
          (760 * 360) / 1080
      ) < 1
  );
  assert.deepEqual(
    (await capture()).layout,
    preferred,
    'Narrow projection never overwrites preferred ratios'
  );
  await page.setViewportSize({ width: 1400, height: 1000 });
  await page.waitForFunction(
    (expected) =>
      Math.abs(
        document.querySelector('[data-dock="results"]').getBoundingClientRect()
          .width - expected
      ) < 1,
    wideWidth
  );
  const inner = page.getByRole('separator').nth(1);
  await inner.focus();
  await page.keyboard.press('Home');
  assert.ok(
    Math.abs((await resultWidth()) - 360) < 1,
    'Keyboard resize respects Results minimum'
  );
  const divider = await inner.boundingBox();
  const beforeResize = await capture();
  await page.mouse.move(
    divider.x + divider.width / 2,
    divider.y + divider.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(600, divider.y + divider.height / 2, { steps: 5 });
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.deepEqual(
    await capture(),
    beforeResize,
    'Escape restores preferred ratios after split preview'
  );

  // A hidden tab keeps its structural slot while visible tabs are reordered.
  const tab = notes.getByRole('tab', { name: 'Snapshot Browser', exact: true });
  const firstTab = notes.getByRole('tab', {
    name: 'Task Inspector',
    exact: true
  });
  const sourceBox = await tab.boundingBox(),
    targetBox = await firstTab.boundingBox();
  const tabsBefore = await capture();
  for (const cancel of [true, false]) {
    await page.mouse.move(
      sourceBox.x + sourceBox.width / 2,
      sourceBox.y + sourceBox.height / 2
    );
    await page.mouse.down();
    await page.mouse.move(
      targetBox.x + targetBox.width / 2 - 20,
      targetBox.y + targetBox.height / 2,
      { steps: 6 }
    );
    if (cancel) await page.keyboard.press('Escape');
    await page.mouse.up();
    if (cancel)
      assert.deepEqual(
        await capture(),
        tabsBefore,
        'Escape cancels tab reorder'
      );
  }
  assert.deepEqual((await capture()).layout.second.panels, [
    'snapshot',
    'description',
    'notes'
  ]);
  await page.reload();
  await page.waitForFunction(() => !!window.dockHarness?.docks.value);
  assert.deepEqual((await capture()).layout.second.panels, [
    'snapshot',
    'description',
    'notes'
  ]);
  await page.evaluate(
    (configuration) => window.dockHarness.docks.value.apply(configuration),
    tabsBefore
  );
  const touchSource = await tab.boundingBox(),
    touchTarget = await firstTab.boundingBox();
  const client = await page.context().newCDPSession(page);
  const touchPoint = {
    x: touchSource.x + touchSource.width / 2,
    y: touchSource.y + touchSource.height / 2
  };
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [touchPoint]
  });
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchMove',
    touchPoints: [{ ...touchPoint, x: touchPoint.x - 20 }]
  });
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchMove',
    touchPoints: [
      { x: touchTarget.x + touchTarget.width / 2 - 20, y: touchPoint.y }
    ]
  });
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchEnd',
    touchPoints: []
  });
  assert.deepEqual((await capture()).layout.second.panels, [
    'snapshot',
    'description',
    'notes'
  ]);
  assert.equal(
    (await capture()).layout.second.active,
    'notes',
    'Touch reorder never activates the dragged tab'
  );
  await client.detach();

  // Every floating edge uses the same per-kind minimum as native DockPanel.
  for (const edge of [
    'left',
    'right',
    'top',
    'bottom',
    'top-left',
    'top-right',
    'bottom-left',
    'bottom-right'
  ]) {
    await page.evaluate(() => {
      const { docks, defaults, captureLayout } = window.dockHarness;
      const state = defaults();
      Object.assign(state.panels.notes, {
        visible: true,
        floating: true,
        rect: [0.1, 0.1, 0.6, 0.6]
      });
      docks.value.apply(captureLayout(state));
    });
    const before = await notes.boundingBox();
    const handle = await notes
      .locator('.dock-resize-edge.' + edge)
      .boundingBox();
    const x = handle.x + handle.width / 2,
      y = handle.y + handle.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(
      x + (edge.includes('left') ? 600 : -600),
      y + (edge.includes('top') ? 500 : -500),
      { steps: 5 }
    );
    await page.mouse.up();
    const after = await notes.boundingBox();
    assert.ok(after.width >= 399.5 && after.height >= 299.5, edge);
    if (edge.includes('left'))
      assert.ok(
        Math.abs(after.x + after.width - before.x - before.width) < 1,
        edge
      );
    if (edge.includes('top'))
      assert.ok(
        Math.abs(after.y + after.height - before.y - before.height) < 1,
        edge
      );
  }
  assert.deepEqual(errors, []);
  console.log(
    'Docks: first click/tap, previews, nested minimums, resize/restore, mouse/touch reorder, Escape rollback, hidden slots and eight floating handles passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
