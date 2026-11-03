import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { exerciseSecurity } from './frame_security_input.mjs';

const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_security/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8')),
  catalog = JSON.parse(await readFile(out + 'catalog.json', 'utf8')),
  cases = JSON.parse(
    await readFile(repo + 'tools/frame_security/cases.json', 'utf8')
  );
if (process.env.FRAME_CAPTURE_PHASES) {
  const selected = process.env.FRAME_CAPTURE_PHASES.split(',');
  cases.splice(
    0,
    cases.length,
    ...cases.filter((entry) => selected.includes(entry.phase))
  );
}
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
      .update(
        await readFile(
          (process.env.TACTIC_HANDLER_ROOT || 'D:/grav/Tactic Stream/TH') +
            '/' +
            name
        )
      )
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
const url =
  'http://127.0.0.1:' +
  server.httpServer.address().port +
  '/tools/frame_security/index.html';
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
    await page.route('**/admin/security-rules/read', (route) =>
      route.fulfill({ json: { result: catalog } })
    );
    await page.goto(url + '?mode=' + mode + '&language=' + language);
    await page.waitForFunction(
      () =>
        window.frameAdmin?.screen.value?.document &&
        !window.frameAdmin.screen.value.busy
    );
    await page.evaluate(() => document.fonts.ready);
    const control = (id) => page.locator('[data-frame="' + id + '"]');
    for (const c of cases) {
      for (const event of c.actions) {
        if (event.type === 'focus') {
          await control(event.id).evaluate((element) =>
            element.focus({ preventScroll: true })
          );
        } else if (event.type === 'feature') {
          await control('adminBuiltinFeature').selectOption(event.value);
        } else if (event.type === 'report') {
          await control('adminEffectiveView').selectOption(event.value);
        } else if (event.type === 'scope' || event.type === 'page') {
          const prefix =
              event.type === 'scope'
                ? 'adminSecurityTab_'
                : 'adminSecurityTechnicalPages_',
            button = control(prefix + event.value);
          if (await button.count()) {
            await button.evaluate((element) =>
              element.focus({ preventScroll: true })
            );
            await button.click();
          } else
            await control(
              event.type === 'scope'
                ? 'adminSecurityScope'
                : 'adminSecurityTechnicalPages'
            ).selectOption(event.value);
        } else if (event.type === 'click') {
          const point = await control(event.id).evaluate((element) => {
            const bounds = element.getBoundingClientRect();
            let left = Math.max(0, bounds.left),
              right = Math.min(innerWidth, bounds.right),
              top = Math.max(0, bounds.top),
              bottom = Math.min(innerHeight, bounds.bottom);
            for (
              let parent = element.parentElement;
              parent;
              parent = parent.parentElement
            ) {
              const style = getComputedStyle(parent),
                box = parent.getBoundingClientRect();
              if (
                ['auto', 'scroll', 'hidden', 'clip'].includes(style.overflowX)
              ) {
                left = Math.max(left, box.left + parent.clientLeft);
                right = Math.min(
                  right,
                  box.left + parent.clientLeft + parent.clientWidth
                );
              }
              if (
                ['auto', 'scroll', 'hidden', 'clip'].includes(style.overflowY)
              ) {
                top = Math.max(top, box.top + parent.clientTop);
                bottom = Math.min(
                  bottom,
                  box.top + parent.clientTop + parent.clientHeight
                );
              }
            }
            return right > left && bottom > top
              ? { x: (left + right) / 2, y: (top + bottom) / 2 }
              : null;
          });
          assert(point, 'visible ' + event.id);
          await page.mouse.click(point.x, point.y);
        } else if (event.type === 'text')
          await control(event.id).fill(event.value);
        else
          await page.evaluate((value) => {
            const s = window.frameAdmin.screen.value;
            if (value === 'clean') s.baseline = JSON.stringify(s.document);
            if (value === 'saved') {
              s.message = 'Access rules saved on server';
              return;
            }
            s.canWrite = value !== 'readonly';
            s.uncertain = value === 'uncertain';
            s.error = s.uncertain
              ? 'The save result is unknown. Reload access rules before trying again.'
              : '';
            s.busy = value === 'busy';
          }, event.value);
        await page.waitForTimeout(20);
      }
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(25);
      const sample = await page.evaluate(() => {
        const s = window.frameAdmin.screen.value,
          boxes = {},
          styles = {},
          canvas = document.createElement('canvas'),
          ctx = canvas.getContext('2d');
        const color = (value) => {
          ctx.clearRect(0, 0, 1, 1);
          ctx.fillStyle = value;
          ctx.fillRect(0, 0, 1, 1);
          return (
            '#' +
            [...ctx.getImageData(0, 0, 1, 1).data]
              .slice(0, 3)
              .map((v) => v.toString(16).padStart(2, '0'))
              .join('')
          );
        };
        for (const el of document.querySelectorAll('[data-frame]')) {
          const r = el.getBoundingClientRect();
          let visible = true;
          for (let p = el.parentElement; p; p = p.parentElement) {
            const css = getComputedStyle(p);
            if (
              /hidden|auto|scroll/.test(
                css.overflow + css.overflowX + css.overflowY
              )
            ) {
              const clip = p.getBoundingClientRect(),
                left = clip.left + p.clientLeft,
                top = clip.top + p.clientTop;
              if (
                r.bottom <= top ||
                r.top >= top + p.clientHeight ||
                r.right <= left ||
                r.left >= left + p.clientWidth
              ) {
                visible = false;
                break;
              }
            }
          }
          if (!visible) continue;
          boxes[el.dataset.frame] = {
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height
          };
          const css = getComputedStyle(el);
          styles[el.dataset.frame] = {
            fontSize: parseFloat(css.fontSize),
            weight: Number(css.fontWeight),
            color: color(css.color)
          };
        }
        const ui = JSON.parse(JSON.stringify(s.ui));
        delete ui.text;
        delete ui.baseline;
        return {
          scene: { toolbar: s.toolbarScene, body: s.frameScene },
          state: {
            ui,
            pending: s.pendingText(),
            dirty: s.dirty,
            uncertain: s.uncertain,
            group: s.group,
            selected: s.selected,
            attributes: s.attributes
          },
          boxes,
          styles
        };
      });
      const reference = native.captures.find(
          (r) =>
            r.mode === mode &&
            r.language === language &&
            r.width === width &&
            r.phase === c.phase
        ),
        label = [mode, language, width, c.phase].join(' ');
      assert.deepEqual(errors, [], label + ' runtime errors');
      assert.deepEqual(sample.state, reference.state, label + ' state');
      assert.deepEqual(sample.scene, reference.scene, label + ' graph');
      for (const [id, box] of Object.entries(sample.boxes)) {
        const expected = reference.boxes[id];
        assert(expected, label + ' missing QML control ' + id);
        for (const key of ['x', 'y', 'width', 'height'])
          assert(
            Math.abs(box[key] - expected[key]) <= 0.1,
            JSON.stringify({
              label,
              id,
              key,
              vue: box[key],
              qml: expected[key]
            })
          );
        rectangles++;
        if (reference.styles[id]?.color) {
          assert.deepEqual(
            sample.styles[id],
            reference.styles[id],
            label + ' ' + id + ' typography/color'
          );
          styles++;
        }
        if (reference.interiors[id]) {
          const indicator = await control(id)
            .locator(':scope > .app-checkbox-indicator')
            .boundingBox();
          for (const key of ['x', 'y', 'width', 'height'])
            assert(
              Math.abs(indicator[key] - reference.interiors[id][key]) <= 0.6,
              label + ' ' + id + ' indicator ' + key
            );
          interiors++;
        }
      }
      const clipped = await page
        .locator('.frame-button:not(.icon-button)')
        .evaluateAll((buttons) =>
          buttons.flatMap((button) => {
            const label = button.querySelector(
              ':scope > span:not(.app-icon,.app-button-badge)'
            );
            if (!label) return [];
            const b = button.getBoundingClientRect(),
              r = label.getBoundingClientRect();
            return r.x < b.x - 0.1 ||
              r.right > b.right + 0.1 ||
              r.y < b.y - 0.1 ||
              r.bottom > b.bottom + 0.1
              ? [button.dataset.frame]
              : [];
          })
        );
      assert.deepEqual(clipped, [], label + ' button labels fit');
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width,
        label + ' horizontal overflow'
      );
      const image =
        'security-vue-' +
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
    }
    await page.close();
  }
  await exerciseSecurity(browser, url, catalog);
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
}
