import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url));
const out =
  process.env.TACTIC_CANVAS_CAPTURE || root + '.screenshots/page-editor';
const native = JSON.parse(await readFile(out + '/page-native.json', 'utf8'));
for (const [path, hash] of Object.entries(native.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(root + 'src/tactic_stream/shared_ui/' + path))
      .digest('hex'),
    hash,
    'Stale shared capture ' + path
  );
for (const [path, hash] of Object.entries(native.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + path))
      .digest('hex'),
    hash,
    'Stale native capture ' + path
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
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: {
      ignored: ['**/.venv/**', '**/.tmp/**', '**/output/**', '**/agent-work/**']
    }
  }
});
await server.listen();
const browser = await chromium.launch({ headless: true });
const counts = [];
try {
  for (const expected of native.captures) {
    const fixture = native.fixtures[expected.fixture];
    const page = await browser.newPage({
      viewport: { width: expected.width, height: expected.height },
      deviceScaleFactor: 1
    });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/admin/rpc', (route) => {
      const command = route.request().postDataJSON().args?.[2];
      assert(
        ['read', 'preview', 'sources'].includes(command?.action),
        'Captures must not write'
      );
      const info =
        command.action === 'sources'
          ? native.source
          : command.action === 'preview'
            ? {
                model: fixture.compiled,
                document: fixture.document,
                revision: 'R1'
              }
            : {
                dashboards: [{ view: 'dashboard.review' }],
                revision: 'R1',
                sourceTypes: [
                  { value: 'demo/asset', label: 'Assets', projectOwned: true }
                ],
                ...(command.name ? { document: fixture.document } : {})
              };
      return route.fulfill({ json: { result: { info } } });
    });
    await page.goto(
      `http://127.0.0.1:${server.httpServer.address().port}/tools/frame_layout/page.html?mode=${expected.mode}&language=${expected.language}`
    );
    await page.waitForFunction(
      () => window.pageEditorFixture?.screen.value?.compiled
    );
    await page.evaluate((panel) => {
      const screen = window.pageEditorFixture.screen.value;
      if (screen.ui.preview !== (panel === 'preview'))
        screen.dispatch({ type: 'preview' });
      if (panel !== 'preview') {
        screen.dispatch({ type: 'panel', value: panel });
        screen.dispatch({ type: 'select', key: '0.0' });
      }
    }, expected.panel);
    await page.waitForTimeout(80);
    const actual = await surface(page, '.page-layout-editor');
    const count = await compareSurface(
      page,
      '.page-layout-editor',
      actual,
      expected,
      expected.image
    );
    counts.push(count);
    assert.deepEqual(errors, []);
    await page.screenshot({
      path: out + '/' + expected.image.replace('.png', '-web.png'),
      animations: 'disabled'
    });
    await page.close();
  }
  await writeFile(
    out + '/page-parity.json',
    JSON.stringify({ pairs: counts.length, counts }, null, 2)
  );
  console.log(
    'Page editor: ' +
      counts.length +
      ' independently rendered paired states match'
  );
} finally {
  await browser.close();
  await server.close();
}
