import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { palette } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import {
  body,
  tileShade
} from '../../src/tactic_stream/shared_ui/features/search/card.ui.mjs';

const luminance = (color) =>
  color
    .map((value) => value / 255)
    .map((value) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    )
    .reduce(
      (sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index],
      0
    );
const contrast = (first, second) =>
  (Math.max(luminance(first), luminance(second)) + 0.05) /
  (Math.min(luminance(first), luminance(second)) + 0.05);
for (const style of ['md3', 'fluent', 'material5'])
  for (const dark of [true, false])
    for (const selected of [false, true]) {
      const colors = palette(
        style,
        dark,
        dark ? [41, 45, 48] : [212, 220, 225],
        dark ? [120, 166, 196] : [61, 117, 153]
      );
      const role = body(
        { kind: 'object', tile: true, selected, subtitle: 'Description' },
        244,
        173
      ).nodes.find((node) => node.id === 'resultTileDescription').color;
      for (const image of [0, 255])
        for (const stop of tileShade) {
          const background = colors[
            selected ? 'contentSelection' : 'panelRaised'
          ].map(
            (channel) => channel * stop.opacity + image * (1 - stop.opacity)
          );
          assert.ok(
            contrast(colors[role], background) >= 4.5,
            `${style}/${dark}/${selected}/${image}: text contrast`
          );
        }
    }
assert.equal(
  body(
    { kind: 'snapshot', tile: true, subtitle: 'Description' },
    244,
    173
  ).nodes.find((node) => node.id === 'resultTileDescription').color,
  'secondaryText'
);
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  publicDir: root + 'frontend/public',
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
const page = await browser.newPage({
  viewport: { width: 260, height: 244 },
  deviceScaleFactor: Number(process.env.FRAME_CAPTURE_DPR || 1.5)
});
const errors = [],
  captures = [];
page.on('pageerror', (error) => errors.push(error.message));
const output = process.env.CARD_CONTRAST_OUTPUT;
if (output) mkdirSync(output, { recursive: true });
try {
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_search/index.html'
  );
  for (const image of ['white', 'black'])
    for (const dark of [true, false])
      for (const selected of [false, true]) {
        await page.evaluate(
          async ({ image, dark, selected }) =>
            window.searchFixture.show({
              screen: 'card-object',
              width: 260,
              height: 244,
              dark,
              selected,
              style: 'md3',
              language: 'en',
              node: {
                id: 'asset',
                kind: 'object',
                title: 'Workshop',
                record: {
                  __search_key__: 'demo/asset?code=A',
                  description: 'Bright preview and readable description'
                },
                preview: {
                  image:
                    'data:image/svg+xml;base64,' +
                    btoa(
                      `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="${image}"/></svg>`
                    )
                },
                hasChildren: false,
                children: []
              }
            }),
          { image, dark, selected }
        );
        await page.waitForFunction(
          () =>
            document.querySelector('.result-preview img')?.complete &&
            document.querySelector('.result-preview img').naturalWidth > 0
        );
        await page.evaluate(() => document.fonts.ready);
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))
            )
        );
        const actual = await page.evaluate(() => ({
          gradient: getComputedStyle(
            document.querySelector('.result-tile-shade')
          ).backgroundImage,
          text: getComputedStyle(
            document.querySelector('[data-frame="resultTileDescription"]')
          ).color,
          title: document.querySelector('.result-title-line strong').textContent
        }));
        assert.ok(actual.gradient.includes('0.82'));
        assert.equal(actual.title, 'Workshop');
        const name = `${image}-${dark ? 'True' : 'False'}-${selected ? 'True' : 'False'}`;
        if (output)
          await page.screenshot({ path: output + '/browser-' + name + '.png' });
        captures.push({ name, ...actual });
      }
  assert.deepEqual(errors, []);
  if (output)
    writeFileSync(
      output + '/browser.json',
      JSON.stringify({ captures, errors }, null, 2)
    );
  console.log(
    'PASS: object-card contrast >=4.5 on extreme images, three themes and selection; 8 real browser captures'
  );
} finally {
  await browser.close();
  await server.close();
}
