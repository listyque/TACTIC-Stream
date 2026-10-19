import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const out = root + 'tools/frame_table/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
async function fresh() {
  for (const [prefix, sources] of [
    [root + 'src/tactic_stream/shared_ui/', native.sha256],
    ['D:/code/th_codex/', native.nativeSources],
    [root, native.driverSources]
  ])
    for (const [name, digest] of Object.entries(sources))
      assert.equal(
        createHash('sha256')
          .update(await readFile(prefix + name))
          .digest('hex'),
        digest,
        'Stale table source: ' + name
      );
}
await fresh();
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
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
const cases = [],
  errors = [];
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 800 }
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_table/');
  await page.waitForFunction(() => !!window.tableFixture);
  const dateFixture = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'inline' &&
      row.fixture.mode === 'date' &&
      row.fixture.language === 'en'
  ).fixture;
  await page.setViewportSize({ width: 800, height: 700 });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  await page.evaluate(
    ({ fixture, data }) => window.tableFixture.show(fixture, data),
    { fixture: dateFixture, data: native.data }
  );
  await page
    .locator('[data-frame="tableInlineValue"] input')
    .fill('2031-04-02');
  await page.evaluate(() => window.tableFixture.events.value.splice(0));
  await page.mouse.click(780, 600);
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.tableFixture.events.value.filter(
          (event) => event.type === 'save'
        ).length
    ),
    0,
    'Outside click must not save an explicit-save date editor'
  );
  assert(
    await page.locator('.table-inline-editor:popover-open').count(),
    'Date draft must stay open until Save or Cancel'
  );
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  assert.deepEqual(
    await page.evaluate(() =>
      window.tableFixture.events.value
        .filter((event) => event.type === 'save')
        .map((event) => event.value)
    ),
    ['2031-04-02']
  );
  const embedded = native.captures.filter(
    (row) => row.fixture.screen === 'cell'
  );
  for (const name of ['legacy_tasks', 'legacy_notes', 'message_progress']) {
    const fixture = structuredClone(
      embedded.find((row) => row.fixture.value.name === name).fixture
    );
    fixture.height = 90;
    if (name === 'message_progress')
      fixture.value.cell.text = '<img src=x onerror="window.unexpected=true">';
    await page.evaluate(
      ({ fixture, data }) => window.tableFixture.show(fixture, data),
      { fixture, data: native.data }
    );
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.evaluate(() => window.tableFixture.events.value.splice(0));
    if (name === 'legacy_tasks') {
      assert(
        await page
          .getByRole('button', { name: 'Edit task assignee', exact: true })
          .isDisabled()
      );
      assert(
        await page
          .getByRole('button', { name: 'Edit task dates', exact: true })
          .isDisabled()
      );
      await page
        .getByRole('button', { name: 'Task Inspector', exact: true })
        .click();
      const events = await page.evaluate(
        () => window.tableFixture.events.value
      );
      assert.equal(events.length, 1);
      assert.equal(events[0].type, 'tasks');
      assert.equal(events[0].task.taskCode, 'L02_TASK');
    } else if (name === 'legacy_notes') {
      await page
        .getByRole('button', { name: 'Review phase (0)', exact: true })
        .click();
      const events = await page.evaluate(
        () => window.tableFixture.events.value
      );
      assert.equal(events.length, 1);
      assert.equal(events[0].process, 'review');
      assert.equal(events[0].cell.search_key, 'cg/assets?project=cg&code=ARM');
    } else {
      assert.equal(await page.locator('.table-message-cell img').count(), 0);
      assert.equal(await page.evaluate(() => window.unexpected), undefined);
      assert.equal(
        await page.locator('[data-frame="tableMessageBody"]').innerText(),
        fixture.value.cell.text
      );
      const track = await page
        .locator('[data-frame="tableMessageTrack"]')
        .boundingBox();
      const fill = await page
        .locator('[data-frame="tableMessageProgress"]')
        .boundingBox();
      assert(Math.abs(fill.width / track.width - 0.37) < 0.001);
    }
  }
  for (const record of native.captures.filter((item) => !item.original)) {
    const fixture = record.fixture;
    await page.setViewportSize({
      width:
        fixture.screen === 'inline' && fixture.mode === 'multiline'
          ? 396
          : Math.max(800, fixture.width),
      height: 700
    });
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.evaluate(
      ({ fixture, data }) => window.tableFixture.show(fixture, data),
      { fixture, data: native.data }
    );
    await page.evaluate(() => document.fonts.ready);
    await page.mouse.move(1599, 699);
    if (fixture.screen === 'inline') {
      const selector = '.table-inline-editor:popover-open > .frame-view';
      assert(
        await page.locator(selector).count(),
        JSON.stringify({
          fixture,
          state: await page.evaluate(() => ({
            events: window.tableFixture.events.value,
            html: document.querySelector('.table-inline-editor')?.outerHTML
          }))
        })
      );
      const actual = await surface(page, selector);
      const compared = await compareSurface(
        page,
        selector,
        actual,
        record,
        record.image
      );
      const image = record.image.replace('-native-', '-stream-');
      await page.locator(selector).screenshot({ path: out + image });
      cases.push({ image, fixture, ...compared });
    } else if (fixture.screen === 'cell') {
      const selector = '.cell-example';
      if (fixture.value.name === 'legacy_tasks') {
        assert(
          await page
            .locator('.task-card-dates > span')
            .evaluateAll((labels) =>
              labels.every((label) => label.scrollWidth <= label.clientWidth)
            ),
          'Short task dates must fit their card without truncation'
        );
      }
      const actual = await surface(page, selector);
      const compared = await compareSurface(
        page,
        selector,
        actual,
        record,
        record.image
      );
      if (record.completionTracks?.length) {
        const expectedTracks = [...record.completionTracks].sort(
          (a, b) => a.y - b.y || a.x - b.x
        );
        const origin = await page.locator(selector).boundingBox();
        const tracks = (
          await page.locator(selector + ' .table-completion').all()
        ).map(async (element) => await element.boundingBox());
        const actual = (await Promise.all(tracks)).filter(
          (box) => box.y - origin.y < fixture.height
        );
        actual.sort((a, b) => a.y - b.y || a.x - b.x);
        assert.equal(actual.length, expectedTracks.length);
        for (let index = 0; index < actual.length; index++) {
          for (const name of ['x', 'y', 'width', 'height']) {
            const value =
              actual[index][name] -
              (name === 'x' ? origin.x : name === 'y' ? origin.y : 0);
            assert(
              Math.abs(value - expectedTracks[index][name]) <= 0.6,
              JSON.stringify({
                fixture,
                index,
                name,
                value,
                expected: expectedTracks[index][name]
              })
            );
          }
        }
      }
      const image = record.image.replace('-native-', '-stream-');
      await page.locator(selector).screenshot({ path: out + image });
      cases.push({ image, fixture, ...compared });
    } else {
      const header = await page.locator('.handler-table-header').boundingBox();
      assert.equal(header.height, 37);
      const reference = record.table.tableHeaderSurface;
      assert(
        Math.abs(header.width - reference.width) < 1,
        JSON.stringify({ fixture, header, reference })
      );
      const rows = await page.locator('.handler-table-row').count();
      assert.equal(rows, 5);
      if (fixture.width === 1496) {
        const avatar = await page
          .locator('.task-card-assignee .item-preview:has(> .app-icon)')
          .first()
          .evaluate((element) => {
            const box = element.getBoundingClientRect();
            const glyph = element
              .querySelector('.icon-glyph')
              .getBoundingClientRect();
            return {
              offset: glyph.x + glyph.width / 2 - box.x - box.width / 2,
              height: box.height,
              glyphHeight: glyph.height,
              overflow: getComputedStyle(element).overflow
            };
          });
        assert(Math.abs(avatar.offset) <= 0.6, JSON.stringify(avatar));
        if (avatar.glyphHeight > avatar.height)
          assert.equal(
            avatar.overflow,
            'visible',
            'Small fallback avatars must not crop the user glyph'
          );
        assert.equal(
          await page
            .locator('.handler-table-cell')
            .filter({ hasText: 'Hero Robot' })
            .first()
            .evaluate((element) =>
              parseFloat(getComputedStyle(element).fontSize)
            ),
          13,
          'Table body uses the same resolved pixel size as native cells'
        );
      }
      const rgb = (hex) =>
        `rgb(${parseInt(hex.slice(1, 3), 16)}, ${parseInt(hex.slice(3, 5), 16)}, ${parseInt(hex.slice(5, 7), 16)})`;
      const paint = await page
        .locator('.handler-table-header')
        .evaluate((element) => ({
          background: getComputedStyle(element).backgroundColor,
          color: getComputedStyle(element).color
        }));
      assert.equal(paint.background, rgb(record.paint.surfaceContainer));
      assert.equal(paint.color, rgb(record.paint.secondaryText));
      const image = record.image.replace('-native-', '-stream-');
      await page.locator('#table-fixture').screenshot({ path: out + image });
      cases.push({ image, fixture, header, rows });
    }
  }
  assert.deepEqual(errors, []);
  await fresh();
  const browserSources = {};
  for (const name of [
    'tools/frame_table/TableFixture.vue',
    'tools/frame_table/table.entry.mjs',
    'frontend/tests/frame_table.mjs',
    'frontend/src/style.css',
    'frontend/src/appearance.js',
    'frontend/src/i18n.js',
    'frontend/src/locales/ru.json'
  ])
    browserSources[name] = createHash('sha256')
      .update(await readFile(root + name))
      .digest('hex');
  for (const path of [
    'frontend/src/features/interface',
    'frontend/src/frame',
    'frontend/src/controls'
  ]) {
    const { readdir } = await import('node:fs/promises');
    for (const name of await readdir(root + path, { recursive: true })) {
      if (!/\.(vue|js|css)$/.test(name)) continue;
      browserSources[path + '/' + name.replaceAll('\\', '/')] = createHash(
        'sha256'
      )
        .update(await readFile(root + path + '/' + name))
        .digest('hex');
    }
  }
  await writeFile(
    out + 'browser.json',
    JSON.stringify({ status: 'passed', cases, browserSources }, null, 2)
  );
  console.log(
    'PASS:',
    cases.length,
    'fresh paired production table/inline states'
  );
} finally {
  await browser?.close();
  await server.close();
}
