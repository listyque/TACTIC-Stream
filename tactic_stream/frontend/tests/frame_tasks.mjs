import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out =
    root + (process.env.TASK_FRAME_OUTPUT || 'tools/frame_tasks/output') + '/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
const digest = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
async function fresh() {
  for (const [prefix, files] of [
    [root + 'src/tactic_stream/shared_ui/', native.shared],
    ['D:/code/th_codex/', native.nativeSources],
    [root, native.driverSources]
  ])
    for (const [name, hash] of Object.entries(files))
      assert.equal(
        await digest(prefix + name),
        hash,
        'Stale tasks source: ' + name
      );
}
async function browserFingerprints() {
  const sources = {};
  for (const name of await readdir(root + 'frontend/src', { recursive: true }))
    if (/\.(vue|css|js|mjs|json)$/.test(name))
      sources['frontend/src/' + name.replaceAll('\\', '/')] = await digest(
        root + 'frontend/src/' + name
      );
  for (const name of [
    'frontend/tests/frame_tasks.mjs',
    'frontend/tests/frame_capture.mjs',
    'tools/frame_tasks/TasksFixture.vue',
    'tools/frame_tasks/tasks.entry.mjs',
    'tools/frame_tasks/index.html',
    'tools/frame_tasks/report.html',
    'frontend/src/theme.css',
    'frontend/src/style.css'
  ])
    sources[name] = await digest(root + name);
  return sources;
}
const browserSources = await browserFingerprints();
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
const errors = [],
  cases = [];
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: native.scale || 1
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_tasks/');
  await page.waitForFunction(() => !!window.tasksFixture);
  const languageFixture = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'table' &&
      row.fixture.width === 1280
  ).fixture;
  await page.evaluate(
    (f) => window.tasksFixture.show({ ...f, language: 'en' }),
    languageFixture
  );
  const retainedSelect = await page
    .locator('[data-frame="taskSortModeCombo"]')
    .elementHandle();
  await retainedSelect.focus();
  const selectedValue = await retainedSelect.inputValue();
  await page.evaluate(
    (f) => window.tasksFixture.show({ ...f, language: 'ru' }),
    languageFixture
  );
  assert(
    await retainedSelect.evaluate(
      (element) => element === document.activeElement
    ),
    'Language refresh must retain select focus'
  );
  assert.equal(await retainedSelect.inputValue(), selectedValue);
  await retainedSelect.evaluate((element) => element.blur());
  for (const record of native.captures.filter((row) => !row.original)) {
    await page.evaluate(
      (fixture) => window.tasksFixture.show(fixture),
      record.fixture
    );
    await page.mouse.move(1590, 990);
    const rootSelector = '#tasks-fixture',
      actual = await surface(page, rootSelector);
    // HTML fragments retain real th/td cells; compare their union to Qt's single scene.
    const unions = await page.locator(rootSelector).evaluate((root) => {
      const result = {},
        origin = root.getBoundingClientRect();
      for (const element of root.querySelectorAll('[data-frame]')) {
        const id = element.dataset.frame;
        if (
          !id.startsWith('taskRowSurface_') &&
          !['taskHeaderSurface', 'taskRowSeparator'].includes(id)
        )
          continue;
        const box = element.getBoundingClientRect(),
          row = element.closest('[data-task-key]')?.dataset.taskKey || '',
          previous = result[id];
        if (!previous || previous.row !== row)
          result[id] = {
            row,
            x: box.x - origin.x,
            y: box.y - origin.y,
            width: box.width,
            height: box.height
          };
        else {
          const right = Math.max(
              previous.x + previous.width,
              box.right - origin.x
            ),
            bottom = Math.max(
              previous.y + previous.height,
              box.bottom - origin.y
            );
          previous.x = Math.min(previous.x, box.x - origin.x);
          previous.y = Math.min(previous.y, box.y - origin.y);
          previous.width = right - previous.x;
          previous.height = bottom - previous.y;
        }
      }
      for (const box of Object.values(result)) delete box.row;
      return result;
    });
    Object.assign(actual.boxes, unions);
    if (actual.fills.taskHeaderSurface) {
      const corners = await page.locator(rootSelector).evaluate((root) => {
        const first = root.querySelector(
            '.task-workspace-table thead th:first-child > div'
          ),
          last = root.querySelector(
            '.task-workspace-table thead th:last-child > div'
          );
        return {
          radius: parseFloat(getComputedStyle(first).borderTopLeftRadius),
          bottomRightRadius: parseFloat(
            getComputedStyle(last).borderBottomRightRadius
          )
        };
      });
      Object.assign(actual.fills.taskHeaderSurface, corners);
    }
    const label = [
      record.fixture.screen,
      record.fixture.style,
      record.fixture.dark ? 'dark' : 'light',
      record.fixture.language,
      record.fixture.width
    ].join('-');
    const image = label + '.png';
    await page
      .locator(rootSelector)
      .screenshot({ path: out + image, animations: 'disabled' });
    const checks = await compareSurface(
      page,
      rootSelector,
      actual,
      record,
      label
    );
    const painted = await page.locator(rootSelector).evaluate((root) => {
      const origin = root.getBoundingClientRect(),
        button = root.querySelector('[data-frame="taskWorkspaceCreateButton"]');
      const color = (value) => {
        const canvas = document.createElement('canvas'),
          ctx = canvas.getContext('2d');
        ctx.fillStyle = value;
        ctx.fillRect(0, 0, 1, 1);
        return (
          '#' +
          [...ctx.getImageData(0, 0, 1, 1).data]
            .slice(0, 3)
            .map((value) => value.toString(16).padStart(2, '0'))
            .join('')
        );
      };
      const result = {};
      if (button) {
        const box = button.getBoundingClientRect(),
          css = getComputedStyle(button, '::before');
        result.create = {
          x: box.x - origin.x + parseFloat(css.left),
          y: box.y - origin.y + parseFloat(css.top),
          width: parseFloat(css.width),
          height: parseFloat(css.height),
          radius: parseFloat(css.borderRadius),
          color: color(css.backgroundColor)
        };
      }
      const arrow = root.querySelector(
        '[data-frame="taskWorkspaceEmptyArrow"] path'
      );
      if (arrow) result.arrow = color(getComputedStyle(arrow).stroke);
      return result;
    });
    if (record.filledActions?.taskWorkspaceCreateButton) {
      const expected = record.filledActions.taskWorkspaceCreateButton;
      assert(painted.create, label + ' missing filled Create paint');
      for (const key of ['x', 'y', 'width', 'height', 'radius'])
        assert(
          Math.abs(painted.create[key] - expected[key]) <= 0.1,
          label +
            ' filled Create ' +
            key +
            ': ' +
            painted.create[key] +
            ' / ' +
            expected[key]
        );
      assert.equal(
        painted.create.color,
        expected.color,
        label + ' filled Create color'
      );
    }
    if (record.arrowColor)
      assert.equal(
        painted.arrow,
        record.arrowColor,
        label + ' empty guidance arrow color'
      );
    if (record.filledActions?.taskWorkspaceCreateButton) {
      const button = page.locator(
        rootSelector + ' [data-frame="taskWorkspaceCreateButton"]'
      );
      const transparent = () =>
        button.evaluate(
          (element) =>
            getComputedStyle(element).backgroundColor === 'rgba(0, 0, 0, 0)' &&
            getComputedStyle(element).filter === 'none'
        );
      await button.hover();
      assert(
        await transparent(),
        label + ' filled hover must retain the transparent inset'
      );
      await button.focus();
      assert(
        await transparent(),
        label + ' filled focus must retain the transparent inset'
      );
      await page.mouse.down();
      assert(
        await transparent(),
        label + ' filled press must retain the transparent inset'
      );
      await page.mouse.move(1590, 990);
      await page.mouse.up();
      await button.evaluate((element) => element.blur());
    }
    const text = await page.locator(rootSelector).evaluate((root) => ({
      labels: Object.fromEntries(
        [...root.querySelectorAll('.frame-label[data-frame]')]
          .filter((element) => element.checkVisibility())
          .map((element) => [element.dataset.frame, element.textContent])
      ),
      choices: Object.fromEntries(
        [...root.querySelectorAll('select[data-frame]')].map((select) => [
          select.dataset.frame,
          {
            source:
              select.selectedOptions[0]?.querySelector(
                '.app-select-option-label'
              )?.textContent || select.selectedOptions[0]?.textContent,
            painted: select.querySelector(
              '.app-select-selected-content .app-select-option-label'
            )?.textContent
          }
        ])
      )
    }));
    const plain = (value) =>
      String(value || '')
        .replace(/\s+/g, ' ')
        .trim();
    const search = page.locator(
      rootSelector + ' .task-workspace-toolbar input'
    );
    if (await search.count())
      assert.equal(
        await search.getAttribute('placeholder'),
        record.fixture.language === 'ru' ? 'Найти задачи' : 'Search tasks',
        label + ' search placeholder'
      );
    for (const task of record.fixture.model.tasks || []) {
      const row = page.locator(
        rootSelector + ' tr[data-task-key="' + task.key + '"]'
      );
      if (!(await row.count())) continue;
      const action = row.locator('button[data-frame="taskRowAction"]');
      assert.equal(await action.count(), 1, label + ' row action control');
      const expected =
        task.pending || record.fixture.model.active === task.key ? '1' : '0.35';
      assert.equal(
        await action.evaluate((element) => getComputedStyle(element).opacity),
        expected,
        label + ' idle row action opacity'
      );
      if (record.fixture.screen === 'table') {
        await action.hover();
        assert.equal(
          await action.evaluate((element) => getComputedStyle(element).opacity),
          '1',
          label + ' hovered row action opacity'
        );
        await page.mouse.move(1590, 990);
      }
    }
    const count = page.locator(
      rootSelector + ' [data-frame="taskFooterCount"]'
    );
    if (await count.count())
      assert.equal(
        await count.evaluate((element) => getComputedStyle(element).whiteSpace),
        'pre',
        label + ' footer spacing'
      );
    for (const [id, value] of Object.entries(text.labels))
      assert.equal(
        plain(value),
        plain(record.texts[id]),
        label + ' ' + id + ' painted text'
      );
    for (const [id, value] of Object.entries(text.choices)) {
      assert.equal(
        plain(value.source),
        plain(record.choices[id]),
        label + ' ' + id + ' choice'
      );
      if (value.painted !== undefined)
        assert.equal(
          plain(value.painted),
          plain(value.source),
          label + ' ' + id + ' stale selected label'
        );
    }
    cases.push({ fixture: record.fixture, image, ...checks, actual });
  }
  assert.deepEqual(errors, []);
  await fresh();
  assert.deepEqual(
    await browserFingerprints(),
    browserSources,
    'Browser sources changed during task captures'
  );
  await writeFile(
    out + 'browser.json',
    JSON.stringify(
      { status: 'passed', smoke: native.smoke, cases, browserSources },
      null,
      2
    )
  );
  console.log('Task paired cases:', cases.length);
} finally {
  await browser?.close();
  await server.close();
}
