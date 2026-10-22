import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_objects/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
const digest = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
async function fresh() {
  for (const [prefix, files] of [
    [root + 'src/tactic_stream/shared_ui/', native.shared],
    ['D:/grav/Tactic Stream/TH/', native.nativeSources],
    [root, native.driverSources || {}]
  ])
    for (const [name, hash] of Object.entries(files))
      assert.equal(
        await digest(prefix + name),
        hash,
        'Stale B08 source: ' + name
      );
  assert.equal(
    await digest(root + 'tools/frame_objects/capture.py'),
    native.driver
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
    viewport: { width: 1000, height: 700 }
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_objects/');
  await page.waitForFunction(() => !!window.objectsFixture);
  for (const record of native.captures.filter((row) => !row.original)) {
    await page.evaluate(
      (fixture) => window.objectsFixture.show(fixture),
      record.fixture
    );
    await page.mouse.move(990, 690);
    if (
      record.fixture.screen === 'report' &&
      record.fixture.state === 'header'
    ) {
      const chip = page.locator('[data-frame="objectReportType"]');
      assert.equal(
        await chip.evaluate((element) => getComputedStyle(element).fontSize),
        '11px'
      );
      assert(
        await chip
          .locator(':scope > span:not(.app-icon)')
          .evaluate(
            (element) => element.scrollWidth <= element.clientWidth + 1
          ),
        'Object type fits its intrinsic chip'
      );
    }
    const actual = await surface(page, '#objects-fixture');
    const comparison = await compareSurface(
      page,
      '#objects-fixture',
      actual,
      record,
      record.image
    );
    const image = record.image.replace('-native-', '-stream-');
    await page.locator('#objects-fixture').screenshot({ path: out + image });
    cases.push({ image, fixture: record.fixture, ...comparison });
  }
  const edit = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'description' &&
      row.fixture.state === 'edit'
  ).fixture;
  await page.evaluate((fixture) => window.objectsFixture.show(fixture), edit);
  const input = page.getByRole('textbox', { name: 'Description', exact: true });
  assert.equal(
    await input.evaluate((element) => getComputedStyle(element).fontSize),
    '11px'
  );
  await input.fill('Retained draft\nSecond line');
  assert.equal(await input.inputValue(), 'Retained draft\nSecond line');
  await page
    .getByRole('button', { name: 'Save description', exact: true })
    .click();
  assert.deepEqual(
    await page.evaluate(() => window.objectsFixture.events.value),
    [{ type: 'save' }]
  );
  // A new server value must update this retained presenter instead of retaining its previous editor text.
  await page.evaluate(
    (fixture) =>
      window.objectsFixture.show({
        ...fixture,
        model: { ...fixture.model, value: 'Another object' }
      }),
    edit
  );
  assert.equal(await input.inputValue(), 'Another object');
  const toolbar = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'toolbar' &&
      row.fixture.state === 'both'
  ).fixture;
  await page.evaluate(
    (fixture) => window.objectsFixture.show(fixture),
    toolbar
  );
  await page.getByRole('radio', { name: 'Fill', exact: true }).click();
  assert.deepEqual(
    await page.evaluate(() => window.objectsFixture.events.value),
    [{ type: 'image', value: 'fill' }]
  );
  await page.getByLabel('Snapshot Browser options', { exact: true }).click();
  await page
    .getByRole('menuitemcheckbox', { name: 'Show All Files', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => window.objectsFixture.events.value.at(-1).value),
    'show_all'
  );
  await page.evaluate(() =>
    window.objectsFixture.show({
      screen: 'regression',
      width: 440,
      height: 200,
      style: 'md3',
      dark: true,
      language: 'en',
      model: { value: '', status: '' }
    })
  );
  await page.locator('textarea').fill('Unlabelled textarea still renders');
  const status = page.getByRole('combobox', { name: 'Status', exact: true });
  assert.equal(
    await status.locator('option').first().innerText(),
    'Select status'
  );
  assert(await status.locator('option').first().isDisabled());
  await status.selectOption('Ready');
  assert.equal(
    await page.evaluate(() => window.objectsFixture.model.value.status),
    'Ready'
  );
  const dependencies = structuredClone(
    native.captures.find(
      (row) =>
        !row.original &&
        row.fixture.screen === 'delete' &&
        row.fixture.state === 'groups' &&
        row.fixture.width === 880
    ).fixture
  );
  dependencies.model.groups = [
    {
      ...dependencies.model.groups[0],
      checked: true,
      expanded: true,
      count: 100,
      items: Array.from({ length: 100 }, (_, index) => ({
        searchKey: 'sthpw/note?code=VIRTUAL' + index,
        title: 'Dependency ' + index,
        details: index % 2 ? 'admin · model' : ''
      }))
    }
  ];
  await page.evaluate(
    (fixture) => window.objectsFixture.show(fixture),
    dependencies
  );
  const dependencyViewport = page.locator(
    '[data-frame="deleteDependencyItems_0"]'
  );
  await dependencyViewport.locator('.virtual-collection').waitFor();
  await dependencyViewport.evaluate((element) => {
    element.scrollTop = 400;
    element.dispatchEvent(new Event('scroll'));
  });
  await page.waitForTimeout(50);
  assert(
    (await dependencyViewport.locator('.virtual-collection-entry').count()) < 30
  );
  assert(
    await dependencyViewport.evaluate((element) => element.scrollHeight > 4000)
  );
  dependencies.model.groups[0].checked = false;
  await page.evaluate(
    (fixture) => window.objectsFixture.show(fixture),
    dependencies
  );
  await page.waitForTimeout(50);
  assert.equal(
    await dependencyViewport.evaluate((element) => element.scrollTop),
    400
  );
  assert.deepEqual(errors, []);
  await fresh();
  const browserSources = {};
  for (const name of [
    'frontend/tests/frame_objects.mjs',
    'frontend/tests/frame_capture.mjs',
    'tools/frame_objects/ObjectsFixture.vue',
    'tools/frame_objects/objects.entry.mjs',
    'frontend/src/style.css',
    'frontend/src/App.vue',
    'frontend/src/features/tasks/TaskManager.vue',
    'frontend/src/features/workspace/links.js',
    'frontend/src/features/administration/ProcessRules.vue',
    'frontend/src/appearance.js',
    'frontend/src/i18n.js',
    'frontend/src/locales/ru.json'
  ])
    browserSources[name] = await digest(root + name);
  for (const folder of [
    'frontend/src/features/objects',
    'frontend/src/controls',
    'frontend/src/frame'
  ])
    for (const name of await readdir(root + folder, { recursive: true }))
      if (/\.(vue|js|css)$/.test(name)) {
        const path = folder + '/' + name.replaceAll('\\', '/');
        browserSources[path] = await digest(root + path);
      }
  await writeFile(
    out + 'browser.json',
    JSON.stringify(
      { status: 'passed', smoke: native.smoke, cases, browserSources },
      null,
      2
    )
  );
  console.log(
    'PASS:',
    cases.length,
    'paired production object states; smoke:',
    native.smoke
  );
} finally {
  await browser?.close();
  await server.close();
}
