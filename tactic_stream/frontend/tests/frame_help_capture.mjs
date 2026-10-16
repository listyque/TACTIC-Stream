import { surface, compareSurface } from './frame_capture.mjs';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const handler = 'D:/code/th_codex/';
const output = root + 'tools/frame_help/output/';
const reference = JSON.parse(await readFile(output + 'native.json', 'utf8'));
const hash = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
for (const [name, value] of Object.entries(reference.sha256))
  assert.equal(
    await hash(root + 'src/tactic_stream/shared_ui/' + name),
    value,
    'Stale shared source: ' + name
  );
for (const [name, value] of Object.entries(reference.nativeSources))
  assert.equal(
    await hash(handler + name),
    value,
    'Stale native source: ' + name
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
    viewport: { width: 1600, height: 1200 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const names = (await readdir(handler + 'thlib/ui/help_articles'))
    .filter((name) => name.endsWith('.en.md'))
    .map((name) => ({ id: name.slice(0, -6), languages: ['en', 'ru'] }));
  await page.route('**/ui/help/**', async (route) => {
    const name = new URL(route.request().url()).pathname.split('/').at(-1);
    await route.fulfill({
      body:
        name === 'index.json'
          ? JSON.stringify(names)
          : await readFile(handler + 'thlib/ui/help_articles/' + name),
      contentType: name.endsWith('.json')
        ? 'application/json'
        : 'text/plain; charset=utf-8'
    });
  });
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_help/index.html'
  );
  await page.waitForFunction(() => !!window.help?.value);
  let comparisons = 0;
  const rows = [];
  for (const native of reference.captures.filter((row) => !row.original)) {
    await page.evaluate(async ({ style, dark, language, width }) => {
      Object.assign(window.appearance, {
        theme: style,
        mode: dark ? 'dark' : 'light',
        language
      });
      await window.help.value.open('windows');
      const dialog = document.querySelector('dialog.help-view');
      Object.assign(dialog.style, {
        width: width + 2 + 'px',
        height: '782px',
        minWidth: '0px'
      });
    }, native);
    await page.waitForFunction(
      (title) =>
        document.querySelector('[data-frame="helpArticleTitle"]')
          ?.textContent === title,
      native.articleTitle
    );
    const plainText = await page
      .locator('.document-pane article > .markdown-text')
      .innerText();
    const normalized = (value) => value.replace(/\s+/gu, ' ').trim();
    assert.equal(
      normalized(plainText),
      normalized(native.plainText),
      'The rendered article text and language must match'
    );
    comparisons += 2;
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(
      (width) =>
        Math.abs(
          document
            .querySelector('[data-frame="helpBackground"]')
            .getBoundingClientRect().width - width
        ) < 1,
      native.width
    );
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    if (native.boxes.helpTopic_windows) {
      await page.waitForFunction((expected) => {
        const root = document
          .querySelector('.help-layout')
          .getBoundingClientRect();
        const target = document.querySelector(
          '[data-frame="helpTopic_windows"]'
        );
        if (!target) return false;
        const box = target.getBoundingClientRect();
        return (
          Math.abs(box.x - root.x - expected.x) < 0.1 &&
          Math.abs(box.y - root.y - expected.y) < 0.1 &&
          Math.abs(box.width - expected.width) < 0.1 &&
          Math.abs(box.height - expected.height) < 0.1
        );
      }, native.boxes.helpTopic_windows);
    }
    const actual = await surface(page, '.help-layout');
    const checked = await compareSurface(
      page,
      '.help-layout',
      actual,
      native,
      `${native.style}/${native.dark}/${native.language}/${native.width}`
    );
    comparisons += checked.rectangles * 4 + checked.styles * 3;
    const filename = `stream-${native.style}-${Number(native.dark)}-${native.language}-${native.width}.png`;
    await page.locator('.help-layout').screenshot({ path: output + filename });
    rows.push({
      ...native,
      image: filename,
      boxes: actual.boxes,
      styles: actual.styles
    });
  }
  assert.deepEqual(errors, []);
  const webSources = {};
  async function sources(directory) {
    for (const entry of await readdir(root + directory, {
      withFileTypes: true
    })) {
      const name = directory + '/' + entry.name;
      if (entry.isDirectory()) await sources(name);
      else if (/\.(vue|js|css)$/.test(name))
        webSources[name] = await hash(root + name);
    }
  }
  await sources('frontend/src');
  await writeFile(
    output + 'stream.json',
    JSON.stringify({ captures: rows, comparisons, webSources }, null, 2)
  );
  console.log(
    `Help: ${rows.length} native/browser pairs, ${comparisons} actual geometry/typography comparisons, zero browser errors.`
  );
} finally {
  await browser.close();
  await server.close();
}
