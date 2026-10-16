import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as Variants from '../../src/tactic_stream/shared_ui/controls/catalog/variants.mjs';
import { textMetrics } from './frame_control_paint.mjs';
import { exerciseVariants } from './frame_control_variants_input.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = root + 'tools/frame_controls/output/variants/';
const input = process.argv.includes('--input');
const smoke = process.argv.includes('--smoke') || input;
await mkdir(output, { recursive: true });
const native = smoke
  ? null
  : JSON.parse(await readFile(output + 'native.json', 'utf8'));
if (!smoke) {
  await writeFile(
    output + 'browser.json',
    JSON.stringify({ status: 'capturing' })
  );
  assert.equal(native.status, 'captured', 'Native capture did not complete');
}
const server = await createServer({
  root,
  publicDir: root + 'frontend/public',
  configFile: false,
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 360, height: 520 },
    hasTouch: true,
    deviceScaleFactor: Number(process.env.FRAME_CONTROL_SCALE || 1)
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_controls/variants.html'
  );
  await page.waitForFunction(() => window.controlVariants);
  if (input) await exerciseVariants(page);
  const expected =
    native?.captures ||
    Variants.examples.map((example) => ({
      id: example.id,
      style: 'md3',
      mode: 'dark',
      language: 'en',
      width: 360,
      state: 'idle'
    }));
  const captures = [],
    differences = [];
  for (const sample of expected) {
    await page.setViewportSize({ width: sample.width, height: 520 });
    await page.evaluate(async (options) => {
      await window.controlVariants.configure(options);
      await document.fonts.ready;
    }, sample);
    await page.mouse.move(sample.width - 2, 500);
    if (
      [
        'preview-photo',
        'preview-contain',
        'preview-selected',
        'avatar-photo'
      ].includes(sample.id)
    )
      await page
        .locator('[data-frame="sample"] img')
        .evaluate((image) => image.decode());
    await page.evaluate(() => new Promise(requestAnimationFrame));
    assert.deepEqual(errors, [], sample.id + ': ' + errors.join('\n'));
    if (sample.scene)
      assert.deepEqual(
        await page.evaluate(() =>
          JSON.parse(JSON.stringify(window.controlVariants.scene))
        ),
        sample.scene,
        sample.id + ' shared composition'
      );
    const boxes = await page
      .locator('[data-frame="sample"]')
      .evaluate((element) => {
        const rect = (node) => {
          const box = node.getBoundingClientRect();
          return { x: box.x, y: box.y, width: box.width, height: box.height };
        };
        const result = { sample: rect(element) };
        if (element.dataset.example && element.firstElementChild)
          result.exampleControl = rect(element.firstElementChild);
        return result;
      });
    if (sample.boxes)
      for (const [name, bounds] of Object.entries(sample.boxes)) {
        if (!['sample', 'exampleControl'].includes(name)) continue;
        assert(boxes[name], sample.id + ': missing actual control ' + name);
        for (const [dimension, value] of Object.entries(bounds))
          if (Math.abs(value - boxes[name][dimension]) > 0.6)
            differences.push({
              id: sample.id,
              style: sample.style,
              language: sample.language,
              width: sample.width,
              control: name,
              dimension,
              native: value,
              browser: boxes[name][dimension]
            });
      }
    const filename =
      'browser-' +
      sample.id +
      '-' +
      sample.style +
      '-' +
      sample.mode +
      '-' +
      sample.language +
      '-' +
      sample.width +
      '.png';
    const content = await textMetrics(page);
    const background = await page
      .locator('[data-frame="sample"]')
      .evaluate((root) => {
        const control = root.dataset.example ? root.firstElementChild : root;
        const surface = control.matches('.app-spin-box')
          ? control.querySelector('input')
          : control.matches('.status-select')
            ? control.querySelector('select')
            : control.querySelector('summary') || control;
        const context = document.createElement('canvas').getContext('2d');
        context.fillStyle = getComputedStyle(
          surface,
          control.matches('.content-loading-overlay') ? '::before' : null
        ).backgroundColor;
        context.fillRect(0, 0, 1, 1);
        const rgba = [...context.getImageData(0, 0, 1, 1).data];
        return rgba[3] === 255
          ? '#' +
              rgba
                .slice(0, 3)
                .map((value) => value.toString(16).padStart(2, '0'))
                .join('')
          : null;
      });
    if (!smoke)
      await page.screenshot({
        path: output + filename,
        animations: 'disabled'
      });
    captures.push({ ...sample, boxes, content, background, image: filename });
  }
  console.log(
    captures.length +
      ' browser standalone variants rendered without runtime errors'
  );
  if (!smoke) {
    const sources = {};
    async function fingerprint(directory) {
      for (const entry of await readdir(root + directory, {
        withFileTypes: true
      })) {
        const path = directory + '/' + entry.name;
        if (entry.isDirectory()) await fingerprint(path);
        else if (/\.(vue|js|mjs|css|json)$/.test(path))
          sources[path] = createHash('sha256')
            .update(await readFile(root + path))
            .digest('hex');
      }
    }
    await fingerprint('frontend/src');
    for (const path of [
      'tools/frame_controls/ControlsExample.vue',
      'tools/frame_controls/VariantsHarness.vue',
      'tools/frame_controls/variants.entry.js',
      'frontend/tests/frame_control_variants.mjs',
      'frontend/tests/frame_control_paint.mjs',
      'frontend/tests/frame_control_variants_input.mjs'
    ])
      sources[path] = createHash('sha256')
        .update(await readFile(root + path))
        .digest('hex');
    await writeFile(
      output + 'browser.json',
      JSON.stringify(
        { status: 'captured', captures, differences, sources },
        null,
        2
      )
    );
    console.log('Geometry differences:', differences.length);
    console.log(differences.slice(0, 12));
    assert.deepEqual(differences, [], 'Actual control geometry differs');
  }
} finally {
  await browser?.close();
  await server.close();
}
