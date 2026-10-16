import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { compose } from '../../src/tactic_stream/shared_ui/shell/main.menus.mjs';
import { row } from '../../src/tactic_stream/shared_ui/controls/menus/action.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url));
const catalog = JSON.parse(
  await readFile(
    root + 'src/tactic_stream/shared_ui/shell/main.menus.json',
    'utf8'
  )
);
const before = JSON.stringify(catalog);
for (const platform of ['native', 'stream'])
  for (const compact of [true, false])
    for (const canAdminister of [true, false]) {
      for (const rows of Object.values(catalog)) {
        const result = compose(rows, {
          platform,
          compact,
          canAdminister,
          updateMode: 'poll'
        });
        assert(!result[0]?.separator && !result.at(-1)?.separator);
        for (const record of result) {
          assert(record.platform === undefined || record.platform === platform);
          assert(!record.admin || canAdminister);
          for (const width of [200, 316])
            validateScene(
              row(record, width, { extent: 32, radius: 8, hovered: true })
            );
        }
      }
    }
assert.equal(JSON.stringify(catalog), before);
const custom = {
  title: 'Script action',
  command: 'extension',
  translate: false,
  children: [{ title: 'Child' }]
};
assert.deepEqual(compose([custom], { platform: 'native' }), [
  { ...custom, enabled: true }
]);
assert.equal(
  compose(catalog.connection, {
    platform: 'stream',
    messagesInitialized: false,
    updateMode: 'sse'
  }).some((a) => a.command === 'updates_30'),
  false
);
assert.equal(
  row({ title: 'Disabled', enabled: false }, 232, {
    extent: 32,
    hovered: true,
    pressed: true
  }).nodes[0].opacity,
  0
);
assert.equal(
  row({ title: 'Checked', checked: true, accent: '#f00' }, 232, {
    extent: 32,
    hovered: true
  }).nodes[0].opacity,
  0.14
);
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
    viewport: { width: 900, height: 850 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_menus/index.html'
  );
  await page.waitForFunction(() => !!window.menuHarness);
  await page.evaluate(() => document.fonts.ready);
  assert.equal(await page.locator('.action-row-hit').first().textContent(), '');
  const trigger = () => page.locator('summary').first();
  for (const input of ['mouse', 'touch', 'keyboard']) {
    if (input === 'keyboard') {
      await trigger().focus();
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('End');
      await page.keyboard.press('Home');
      await page.keyboard.press('Enter');
    } else {
      await trigger().click();
      const action = page.locator('[data-menu-command="show_messages"] button');
      if (input === 'touch') await action.tap();
      else await action.click();
    }
    assert.equal(
      await page.evaluate(() => window.menuHarness.command.value),
      input === 'keyboard' ? 'show_user_profile' : 'show_messages'
    );
    assert.equal(await page.locator('details').getAttribute('open'), null);
  }
  await page.evaluate(() => {
    window.menuHarness.kind.value = 'connection';
    window.menuHarness.context.messagesInitialized = false;
  });
  await trigger().click();
  await page.locator('[data-menu-command="update_mode_sse"] button').click();
  await trigger().click();
  assert.equal(
    await page.locator('[data-menu-command="updates_30"]').count(),
    0
  );
  assert.equal(
    await page
      .locator('[data-menu-command="update_mode_sse"] button')
      .getAttribute('aria-checked'),
    'true'
  );
  await page.keyboard.press('Escape');
  assert.equal(
    await trigger().evaluate((e) => e === document.activeElement),
    true
  );
  await page.evaluate(() => {
    window.menuHarness.context.busy = true;
    window.menuHarness.kind.value = 'user';
  });
  await trigger().click();
  assert.equal(
    await page.locator('[data-menu-command="sign_out"] button').isDisabled(),
    true
  );
  await page.keyboard.press('Escape');
  assert.equal(
    await page
      .locator('.tested-footer')
      .evaluate((e) => e.getBoundingClientRect().height),
    58
  );
  if (process.argv.includes('--capture')) {
    const output = root + 'tools/frame_menus/output/';
    await mkdir(output, { recursive: true });
    const native = JSON.parse(await readFile(output + 'native.json', 'utf8')),
      captures = [];
    let comparisons = 0;
    for (const sample of native.captures.filter((row) => !row.original)) {
      await page.evaluate((sample) => {
        const h = window.menuHarness;
        h.menu.value.close();
        h.kind.value = sample.kind;
        Object.assign(h.appearance, {
          theme: sample.theme,
          language: sample.language,
          mode: sample.language === 'en' ? 'dark' : 'light'
        });
        Object.assign(h.context, {
          busy: false,
          updateMode: 'poll',
          pollInterval: 30,
          messagesInitialized: true
        });
      }, sample);
      await trigger().click();
      await page.evaluate(() => document.fonts.ready);
      const expectedWidth = sample.rows[0].width;
      await page.waitForFunction(
        (w) =>
          Math.abs(
            document
              .querySelector('[data-frame="menuRowSurface"]')
              .getBoundingClientRect().width - w
          ) < 0.1,
        expectedWidth
      );
      await page.mouse.move(850, 800);
      const rows = await page.locator('.action-row').evaluateAll((items) =>
        items.map((item) => {
          const b = item.getBoundingClientRect(),
            boxes = {};
          for (const node of item.querySelectorAll('[data-frame]')) {
            const r = node.getBoundingClientRect();
            boxes[node.dataset.frame] = {
              x: r.x - b.x,
              y: r.y - b.y,
              width: r.width,
              height: r.height,
              fontSize: parseFloat(getComputedStyle(node).fontSize)
            };
          }
          return {
            command: item.dataset.menuCommand,
            height: b.height,
            width: b.width,
            boxes
          };
        })
      );
      for (const expected of sample.rows.filter((row) => row.command)) {
        const actual = rows.find((row) => row.command === expected.command);
        if (!actual) continue; // Product-only actions have no counterpart.
        assert.equal(
          actual.height,
          expected.height,
          sample.id + ' ' + expected.command
        );
        for (const [id, box] of Object.entries(expected.boxes))
          for (const key of Object.keys(box)) {
            assert(actual.boxes[id], id);
            assert(
              Math.abs(actual.boxes[id][key] - box[key]) < 0.6,
              `${sample.id} ${expected.command} ${id}.${key}: ${actual.boxes[id][key]} / ${box[key]}`
            );
            comparisons++;
          }
      }
      const image = 'browser-' + sample.id + '.png';
      await page.locator('.account-panel').screenshot({ path: output + image });
      const footer = await page.locator('.tested-footer').evaluate((e) => {
        const s = getComputedStyle(e);
        return Object.fromEntries(
          [
            'height',
            'borderTopLeftRadius',
            'borderTopRightRadius',
            'borderBottomLeftRadius',
            'borderBottomRightRadius'
          ].map((k) => [k, parseFloat(s[k])])
        );
      });
      assert.equal(footer.height, sample.footer.height);
      for (const corner of ['TopLeft', 'TopRight', 'BottomLeft', 'BottomRight'])
        assert.equal(
          footer['border' + corner + 'Radius'],
          sample.footer[corner[0].toLowerCase() + corner.slice(1) + 'Radius']
        );
      const footerImage = 'browser-' + sample.id + '-footer.png';
      await page
        .locator('.tested-footer')
        .screenshot({ path: output + footerImage });
      captures.push({ id: sample.id, image, rows, footer, footerImage });
      await page.keyboard.press('Escape');
    }
    const sources = {};
    for (const path of [
      'frontend/src/controls/AppButton.vue',
      'frontend/src/controls/NavigationRow.vue',
      'frontend/src/controls/DockWorkspaceFooter.vue',
      'frontend/src/controls/ActionRow.vue',
      'frontend/src/controls/ActionRows.vue',
      'frontend/src/controls/AppMenu.vue',
      'frontend/src/features/connection/ConnectionMenu.vue',
      'frontend/src/App.vue',
      'tools/frame_menus/MenuHarness.vue',
      'frontend/tests/frame_menus.mjs'
    ])
      sources[path] = createHash('sha256')
        .update(await readFile(root + path))
        .digest('hex');
    await writeFile(
      output + 'browser.json',
      JSON.stringify({ captures, comparisons, sources }, null, 2)
    );
    console.log(
      'Menu pairs: ' +
        captures.length +
        ' cases, ' +
        comparisons +
        ' row geometry comparisons.'
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'Main menus: catalog predicates, script records, first mouse/touch/key, close/focus, disabled, update modes and footer passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
