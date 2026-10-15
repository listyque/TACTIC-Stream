import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_admin/output/';
const names = JSON.parse(await readFile(out + 'icon-names.json', 'utf8'));
const native = JSON.parse(await readFile(out + 'icon-values.json', 'utf8'));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'silent',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: { ignored: ['**/.tmp/**', '**/.venv/**', '**/output/**'] }
  }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage();
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_shell/index.html'
  );
  const missing = await page.evaluate(async (names) => {
    const { resolveIcon, iconMaps } = await import('/frontend/src/icons.js');
    return Object.fromEntries(
      Object.keys(iconMaps).map((pack) => [
        pack,
        names.filter((name) => !resolveIcon(name, pack))
      ])
    );
  }, names);
  await writeFile(out + 'icon-missing.json', JSON.stringify(missing, null, 2));
  console.log(JSON.stringify(missing));
  assert(
    Object.values(missing).every((names) => !names.length),
    'Every Frame icon must resolve in every supplied pack'
  );
  const actual = await page.evaluate(async (native) => {
    const { resolveIcon } = await import('/frontend/src/icons.js');
    return Object.fromEntries(
      Object.entries(native).map(([pack, rows]) => [
        pack,
        Object.fromEntries(
          Object.keys(rows).map((name) => [name, resolveIcon(name, pack)])
        )
      ])
    );
  }, native);
  assert.deepEqual(
    actual,
    native,
    'The native and browser renderers must choose the same font family and Unicode glyph'
  );
  console.log(
    'Matched native/browser glyphs: ' +
      Object.values(native).reduce(
        (sum, rows) => sum + Object.keys(rows).length,
        0
      )
  );
} finally {
  await browser.close();
  await server.close();
}
