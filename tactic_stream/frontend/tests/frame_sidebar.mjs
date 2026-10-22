import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_sidebar/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8')),
  catalog = JSON.parse(await readFile(out + 'catalog.json', 'utf8')),
  cases = JSON.parse(
    await readFile(repo + 'tools/frame_sidebar/cases.json', 'utf8')
  );
for (const [name, hash] of Object.entries(native.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(repo + 'src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    hash,
    'stale native capture: ' + name
  );
for (const [name, hash] of Object.entries(native.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    hash,
    'stale native renderer: ' + name
  );
const server = await createServer({
  root: repo,
  configFile: false,
  resolve: {
    alias: {
      vue: repo + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: {
      ignored: [
        '**/.tmp/**',
        '**/.venv/**',
        '**/.standalone*/**',
        '**/output/**'
      ]
    }
  }
});
await server.listen();
const worker = spawn(
  repo + '.venv/Scripts/python.exe',
  ['-B', '-X', 'utf8', repo + 'tools/frame_sidebar/edit_fixture.py'],
  { cwd: repo, windowsHide: true, stdio: ['pipe', 'pipe', 'inherit'] }
);
const pending = [];
createInterface({ input: worker.stdout }).on('line', (line) =>
  pending.shift()?.(JSON.parse(line))
);
const edit = (values) =>
  new Promise((resolve) => {
    pending.push(resolve);
    worker.stdin.write(JSON.stringify(values) + '\n');
  });
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
let rectangles = 0,
  styles = 0,
  interiors = 0;
const samples = [];
try {
  const dimensions = [
    ...new Map(
      native.captures.map((s) => [
        [s.mode, s.language, s.width, s.height].join(':'),
        s
      ])
    ).values()
  ];
  for (const { mode, language, width, height } of dimensions) {
    const page = await browser.newPage({ viewport: { width, height } }),
      errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/admin/sidebar/*', async (route) => {
      const action = route.request().url().split('/').pop();
      assert(['read', 'edit'].includes(action), 'paired capture never writes');
      const result =
        action === 'read'
          ? { result: catalog }
          : await edit(route.request().postDataJSON());
      await route.fulfill({ status: result.error ? 400 : 200, json: result });
    });
    await page.goto(
      'http://127.0.0.1:' +
        server.httpServer.address().port +
        '/tools/frame_sidebar/index.html?mode=' +
        mode +
        '&language=' +
        language
    );
    await page.waitForFunction(
      () =>
        window.frameAdmin?.screen.value?.draft &&
        !window.frameAdmin.screen.value.busy &&
        !window.frameAdmin.screen.value.dispatching
    );
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(
      () => window.frameAdmin.screen.value.viewport.width > 100
    );
    for (const c of cases) {
      for (const action of c.actions) {
        if (action.type === 'state')
          await page.evaluate((value) => {
            const s = window.frameAdmin.screen.value;
            s.context.ticket =
              value === 'readonly' ? 'readonly-fixture' : s.ticket;
            s.uncertain = value === 'uncertain';
            s.busy = value === 'busy';
          }, action.value);
        else {
          const el = page.locator(
            'section.sidebar-editor [data-frame="' + action.id + '"]'
          );
          if (action.type === 'key') await el.press(action.key);
          else if (action.type === 'text') await el.fill(action.value);
          else {
            const b = await el.boundingBox();
            assert(b, action.id);
            await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
          }
        }
        if (action.type !== 'state' || action.value !== 'busy')
          await page.waitForFunction(
            () =>
              !window.frameAdmin.screen.value.busy &&
              !window.frameAdmin.screen.value.dispatching
          );
        if (action.type === 'key')
          await page.waitForFunction(
            (id) => document.activeElement?.dataset.frame === id,
            action.key === 'ArrowDown'
              ? 'sidebarEditorEntry_1'
              : 'sidebarEditorEntry_0'
          );
      }
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(35);
      const actual = await page.evaluate(() => {
        const s = window.frameAdmin.screen.value;
        return {
          scene: { toolbar: s.toolbarScene, body: s.frameScene },
          state: {
            ui: JSON.parse(JSON.stringify(s.ui)),
            dirty: !!s.dirty,
            selected: s.draft.selected,
            entry: s.entry.name || ''
          }
        };
      });
      const label = [mode, language, width, c.phase].join(' '),
        reference = native.captures.find(
          (s) =>
            s.mode === mode &&
            s.language === language &&
            s.width === width &&
            s.phase === c.phase
        );
      assert.deepEqual(errors, [], label + ' runtime errors');
      assert.deepEqual(actual.state, reference.state, label + ' state');
      assert.deepEqual(
        JSON.parse(JSON.stringify(actual.scene)),
        reference.scene,
        label + ' graph'
      );
      const counts = await compareSurface(
        page,
        'section.sidebar-editor',
        await surface(page, 'section.sidebar-editor'),
        reference,
        label
      );
      rectangles += counts.rectangles;
      styles += counts.styles;
      interiors += counts.interiors;
      const image =
        'sidebar-vue-' +
        mode +
        '-' +
        language +
        '-' +
        width +
        '-' +
        c.phase +
        '.png';
      await page.screenshot({ path: out + image, animations: 'disabled' });
      samples.push({ mode, language, width, height, phase: c.phase, image });
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width,
        'no page overflow'
      );
    }
    await page.close();
  }
  await writeFile(
    out + 'vue.json',
    JSON.stringify(
      { rectangles, styles, interiors, captures: samples },
      null,
      2
    )
  );
  console.log(
    JSON.stringify({ pairs: samples.length, rectangles, styles, interiors })
  );
} finally {
  await browser.close();
  await server.close();
  worker.stdin.end();
  worker.kill();
}
