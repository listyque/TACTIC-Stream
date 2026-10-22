import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  output = root + 'tools/frame_foundation/output/navigation/';
const reference = JSON.parse(await readFile(output + 'native.json', 'utf8'));
for (const [name, value] of Object.entries(reference.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(root + 'src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    value,
    name
  );
for (const [name, value] of Object.entries(reference.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    value,
    name
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
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } }),
    errors = [],
    cases = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/navigation-rows.html'
  );
  await page.waitForFunction(() => !!window.navigationCase);
  let comparisons = 0;
  for (const sample of reference.captures.filter((row) => !row.original)) {
    await page.evaluate(
      (sample) =>
        Object.assign(window.navigationCase, {
          width: sample.width,
          depth: sample.depth,
          selected: sample.selected
        }),
      sample
    );
    await page.waitForFunction(
      (width) =>
        [
          ...document.querySelectorAll(
            '.navigation-row [data-frame="sidebarRowSurface"]'
          )
        ].every(
          (node) =>
            Math.abs(node.getBoundingClientRect().width - width + 24) < 0.6
        ),
      sample.width
    );
    await page.evaluate(() => document.fonts.ready);
    const rows = await page.locator('.navigation-row').evaluateAll((rows) =>
      rows.map((row, index) => {
        const origin = row.getBoundingClientRect(),
          boxes = {};
        for (const node of row.querySelectorAll('[data-frame]')) {
          const b = node.getBoundingClientRect();
          boxes[node.dataset.frame] = {
            x: b.x - origin.x,
            y: b.y - origin.y,
            width: b.width,
            height: b.height
          };
        }
        return { id: 'row' + index, height: origin.height, boxes };
      })
    );
    for (const expected of sample.rows) {
      const actual = rows.find((row) => row.id === expected.id);
      assert.equal(actual.height, expected.height);
      for (const [id, box] of Object.entries(expected.boxes))
        for (const key of ['x', 'y', 'width', 'height']) {
          assert(
            Math.abs(actual.boxes[id][key] - box[key]) < 0.6,
            `${sample.width}/${sample.depth}/${sample.selected} ${expected.id} ${id}.${key}: ${actual.boxes[id][key]} / ${box[key]}`
          );
          comparisons++;
        }
    }
    const image = `stream-${sample.width}-${sample.depth}-${Number(sample.selected)}.png`;
    await page
      .locator('#navigation-capture')
      .screenshot({ path: output + image });
    cases.push({ ...sample, image, rows });
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
        webSources[name] = createHash('sha256')
          .update(await readFile(root + name))
          .digest('hex');
    }
  }
  await sources('frontend/src');
  await writeFile(
    output + 'stream.json',
    JSON.stringify({ comparisons, captures: cases, webSources }, null, 2)
  );
  const cards = cases
    .map((row) => {
      const suffix = `${row.width}-${row.depth}-${Number(row.selected)}.png`;
      return `<section><h2>${row.width}px · depth ${row.depth} · selected ${row.selected}</h2><div>${['original', 'native', 'stream'].map((name) => `<figure><figcaption>${name}</figcaption><img src="${name}-${suffix}"></figure>`).join('')}</div></section>`;
    })
    .join('');
  await writeFile(
    output + 'index.html',
    `<!doctype html><meta charset="utf-8"><title>Frame · Navigation rows</title><style>body{font:14px Segoe UI;background:#202426;color:#eee;margin:24px}section>div{display:flex;gap:16px;flex-wrap:wrap}figure{margin:0}figcaption{margin:8px 0}img{border:1px solid #555}h2{font-size:16px}</style><h1>Navigation · original Handler / Frame Handler / Frame Stream</h1><p>8 native/browser cases, ${comparisons} actual geometry comparisons. The original and current use identical records. Badge typography now uses the named pixel role; rasterization is engine-specific.</p>${cards}`
  );
  console.log(
    `Navigation: ${cases.length} original/native/browser cases; ${comparisons} actual row geometry comparisons passed.`
  );
} finally {
  await browser.close();
  await server.close();
}
