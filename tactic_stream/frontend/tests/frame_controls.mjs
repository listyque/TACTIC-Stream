import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
import { exerciseControls } from './frame_controls_input.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = root + 'tools/frame_controls/output/';
await mkdir(output, { recursive: true });
const inputOnly = process.argv.includes('--input-only');
const native = inputOnly
  ? null
  : JSON.parse(await readFile(output + 'qml.json', 'utf8'));
if (native)
  for (const [name, hash] of Object.entries(native.sha256))
    assert.equal(
      createHash('sha256')
        .update(await readFile(root + 'src/tactic_stream/shared_ui/' + name))
        .digest('hex'),
      hash,
      'Changed shared control source: ' + name
    );
if (native)
  for (const [name, hash] of Object.entries(native.nativeSources))
    assert.equal(
      createHash('sha256')
        .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
        .digest('hex'),
      hash,
      'Changed native control source: ' + name
    );
const server = await createServer({
  root,
  configFile: false,
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: { ignored: ['**/.tmp/**', '**/output/**', '**/.venv/**'] }
  }
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
    viewport: { width: 900, height: 900 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.setDefaultTimeout(10000);
  await page.goto(
    `http://127.0.0.1:${server.httpServer.address().port}/tools/frame_controls/`,
    { waitUntil: 'domcontentloaded', timeout: 30000 }
  );
  await page.waitForFunction(() => window.frameControls);
  await page.evaluate(() => document.fonts.ready);
  const rows = [];
  let rectangles = 0,
    styles = 0,
    interiors = 0,
    texts = 0,
    glyphs = 0;
  for (const expected of (native?.captures || []).slice(
    0,
    process.env.FRAME_CONTROLS_LIMIT
      ? Number(process.env.FRAME_CONTROLS_LIMIT)
      : undefined
  )) {
    await page.setViewportSize({ width: expected.width, height: 900 });
    await page.evaluate(
      (options) => {
        window.frameControls.reset();
        window.frameControls.configure(options);
        document.activeElement?.blur();
      },
      {
        width: expected.width,
        height: 900,
        theme: expected.style,
        mode: expected.mode,
        language: expected.language,
        state: expected.target ? 'idle' : expected.state
      }
    );
    await page
      .locator('[data-frame="catalogScroll"]')
      .evaluate(
        (element, offset) => (element.scrollTop = offset),
        expected.offset
      );
    await page.mouse.move(expected.width - 2, 898);
    if (expected.target) {
      const control = page.locator(`[data-frame="${expected.target}"]`);
      if (expected.state === 'focus') {
        await page.keyboard.press('Tab');
        await control.focus();
      } else {
        await control.hover();
        if (expected.state === 'pressed') await page.mouse.down();
      }
    }
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    const label = [
      expected.style,
      expected.mode,
      expected.language,
      expected.width,
      expected.state,
      expected.part,
      expected.target || ''
    ].join('/');
    assert.deepEqual(
      await page.evaluate(() =>
        JSON.parse(JSON.stringify(window.frameControls.scene))
      ),
      expected.scene,
      label + ' shared declaration'
    );
    const actual = await surface(page, '#app');
    const counts = await compareSurface(page, '#app', actual, expected, label);
    rectangles += counts.rectangles;
    styles += counts.styles;
    interiors += counts.interiors;
    const content = await page.evaluate((ids) => {
      const result = {},
        canvas = document.createElement('canvas'),
        context = canvas.getContext('2d');
      for (const id of ids) {
        const root = document.querySelector(`[data-frame="${id}"]`);
        const row = { icons: [] };
        let label =
          id.startsWith('caption_') ||
          ['checkLabel', 'field', 'area', 'choice'].includes(id)
            ? root
            : root.querySelector(
                '.app-date-presentation, .user-combo-label, button > span:not(.app-icon):not(.app-button-badge)'
              );
        if (['button', 'primary', 'danger', 'segment'].includes(id))
          label = root.querySelector(
            ':scope > span:not(.app-icon):not(.app-button-badge)'
          );
        if (label) {
          const css = getComputedStyle(label),
            box = label.getBoundingClientRect();
          const value = label.matches('input,textarea,select')
            ? label.tagName === 'SELECT'
              ? label.selectedOptions[0].textContent
              : label.value
            : label.textContent;
          context.font = css.font;
          const metrics = context.measureText(value);
          let x, baseline;
          if (label.matches('input,textarea,select')) {
            const left =
                parseFloat(css.borderLeftWidth) + parseFloat(css.paddingLeft),
              top = parseFloat(css.borderTopWidth) + parseFloat(css.paddingTop),
              bottom =
                parseFloat(css.borderBottomWidth) +
                parseFloat(css.paddingBottom);
            const height =
              metrics.fontBoundingBoxAscent + metrics.fontBoundingBoxDescent;
            x = box.x + left;
            baseline =
              label.tagName === 'TEXTAREA'
                ? box.y + top + metrics.fontBoundingBoxAscent - label.scrollTop
                : box.y +
                  top +
                  (box.height - top - bottom - height) / 2 +
                  metrics.fontBoundingBoxAscent;
          } else {
            const range = document.createRange();
            range.selectNodeContents(label);
            const rect = range.getClientRects()[0] || box;
            x = rect.x;
            baseline =
              rect.y +
              (rect.height -
                metrics.fontBoundingBoxAscent -
                metrics.fontBoundingBoxDescent) /
                2 +
              metrics.fontBoundingBoxAscent;
          }
          row.text = { value, x, baseline, advance: metrics.width };
        }
        for (const icon of root.querySelectorAll('.app-icon')) {
          if (!icon.checkVisibility()) continue;
          const box = icon.getBoundingClientRect();
          if (!box.width || !box.height) continue;
          const glyph = icon.querySelector('.icon-glyph');
          row.icons.push({
            value: glyph.textContent,
            family: [...icon.classList]
              .find((name) => name.startsWith('icon-'))
              .slice(5),
            fontSize: parseFloat(getComputedStyle(glyph).fontSize),
            x: box.x,
            y: box.y,
            width: box.width,
            height: box.height
          });
        }
        result[id] = row;
      }
      return result;
    }, Object.keys(expected.content));
    for (const [id, wanted] of Object.entries(expected.content)) {
      const found = content[id];
      if (wanted.text) {
        assert(found.text, label + ' missing text ' + id);
        assert.equal(
          found.text.value,
          wanted.text.value,
          label + ' text ' + id
        );
        for (const key of ['x', 'baseline', 'advance'])
          assert(
            Math.abs(found.text[key] - wanted.text[key]) <=
              (key === 'advance'
                ? Math.max(0.2, wanted.text.value.length * 0.02)
                : 0.6),
            JSON.stringify({
              label,
              id,
              key,
              vue: found.text,
              qml: wanted.text
            })
          );
        texts++;
      }
      assert.equal(
        found.icons.length,
        wanted.icons.length,
        label + ' icon count ' + id
      );
      for (let index = 0; index < wanted.icons.length; index++) {
        const first = wanted.icons[index],
          second = found.icons[index];
        for (const key of ['value', 'family', 'fontSize'])
          assert.equal(
            second[key],
            first[key],
            label + ' icon ' + id + ' ' + key
          );
        for (const key of ['x', 'y', 'width', 'height'])
          assert(
            Math.abs(second[key] - first[key]) <= 0.6,
            JSON.stringify({ label, id, key, vue: second, qml: first })
          );
        glyphs++;
      }
    }
    const paint = await page.evaluate(() => {
      const result = {},
        canvas = document.createElement('canvas'),
        context = canvas.getContext('2d');
      function rgb(value) {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = value;
        context.fillRect(0, 0, 1, 1);
        const data = [...context.getImageData(0, 0, 1, 1).data];
        return {
          color:
            '#' +
            data
              .slice(0, 3)
              .map((value) => value.toString(16).padStart(2, '0'))
              .join(''),
          alpha: data[3] / 255
        };
      }
      for (const name of [
        'button',
        'primary',
        'danger',
        'segment',
        'field',
        'check',
        'choice'
      ]) {
        const root = document.querySelector(`[data-frame="${name}"]`),
          element = name === 'check' ? root?.querySelector('input') : root;
        if (!element) continue;
        const css = getComputedStyle(element),
          color = rgb(css.backgroundColor);
        result[name] = {
          background: color.color,
          alpha: color.alpha,
          content: rgb(css.color).color
        };
      }
      return result;
    });
    for (const [name, wanted] of Object.entries(expected.paint)) {
      const found = paint[name];
      assert(found, label + ' missing paint ' + name);
      assert(
        Math.abs(found.alpha - wanted.alpha) < 0.01,
        label + ' ' + name + ' alpha'
      );
      if (wanted.alpha > 0)
        for (let channel = 1; channel < 7; channel += 2)
          assert(
            Math.abs(
              parseInt(found.background.slice(channel, channel + 2), 16) -
                parseInt(wanted.background.slice(channel, channel + 2), 16)
            ) <= 1,
            JSON.stringify({ label, name, found, wanted })
          );
    }
    const filename = expected.image.replace('.png', '-vue.png');
    await page.screenshot({ path: output + filename, animations: 'disabled' });
    rows.push({ ...expected, image: filename, ...actual, paint, content });
    if (expected.target && expected.state === 'pressed') await page.mouse.up();
  }
  if (!process.env.FRAME_CONTROLS_LIMIT) {
    await exerciseControls(page);
    for (const scale of [1.5, 2]) {
      const scaled = await browser.newPage({
        viewport: { width: 900, height: 900 },
        hasTouch: true,
        deviceScaleFactor: scale
      });
      scaled.on('pageerror', (error) => errors.push(error.message));
      await scaled.goto(page.url(), {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });
      await scaled.waitForFunction(() => window.frameControls);
      await scaled.evaluate(() => document.fonts.ready);
      await exerciseControls(scaled);
      assert.equal(await scaled.evaluate(() => devicePixelRatio), scale);
      await scaled.screenshot({ path: output + 'input-dpr-' + scale + '.png' });
      await scaled.close();
    }
  }
  assert.deepEqual(errors, []);
  const renderSources = {};
  async function sources(directory) {
    for (const entry of await readdir(root + directory, {
      withFileTypes: true
    })) {
      const name = directory + '/' + entry.name;
      if (entry.isDirectory()) await sources(name);
      else if (/\.(vue|css|js|mjs)$/.test(entry.name))
        renderSources[name] = createHash('sha256')
          .update(await readFile(root + name))
          .digest('hex');
    }
  }
  await sources('frontend/src');
  for (const name of [
    'frontend/tests/frame_controls.mjs',
    'frontend/tests/frame_controls_input.mjs',
    'tools/frame_controls/ControlsHarness.vue',
    'tools/frame_controls/controls.entry.js'
  ])
    renderSources[name] = createHash('sha256')
      .update(await readFile(root + name))
      .digest('hex');
  if (!inputOnly)
    await writeFile(
      output + 'vue.json',
      JSON.stringify(
        {
          captures: rows,
          rectangles,
          styles,
          interiors,
          texts,
          glyphs,
          errors,
          renderSources,
          inputScales: [1, 1.5, 2]
        },
        null,
        2
      )
    );
  console.log({
    pairs: rows.length,
    rectangles,
    styles,
    interiors,
    texts,
    glyphs,
    errors
  });
} finally {
  await browser?.close();
  await server.close();
}
