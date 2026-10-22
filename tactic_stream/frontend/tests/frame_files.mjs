import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const out =
  root + (process.env.FILES_FRAME_OUTPUT || 'tools/frame_files/output') + '/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
const digest = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
async function fresh() {
  for (const [prefix, files] of [
    [root + 'src/tactic_stream/shared_ui/', native.shared],
    ['D:/grav/Tactic Stream/TH/', native.nativeSources],
    [root, native.driverSources]
  ])
    for (const [name, hash] of Object.entries(files))
      assert.equal(
        await digest(prefix + name),
        hash,
        'Stale file UI source: ' + name
      );
}
async function fingerprints() {
  const result = {};
  for (const name of await readdir(root + 'frontend/src', { recursive: true }))
    if (/\.(vue|css|js|mjs|json)$/.test(name))
      result['frontend/src/' + name.replaceAll('\\', '/')] = await digest(
        root + 'frontend/src/' + name
      );
  for (const name of [
    'frontend/tests/frame_files.mjs',
    'frontend/tests/frame_capture.mjs',
    ...(await readdir(root + 'tools/frame_files'))
      .filter((name) => /\.(vue|html|mjs|py|json)$/.test(name))
      .map((name) => 'tools/frame_files/' + name)
  ])
    result[name] = await digest(root + name);
  return result;
}
// Native server-queue and local/DCC controls occupy capability-specific regions.
function queueFragments(surface) {
  const names = new Set([
    'commitQueueBackground',
    'commitQueueListSlot',
    'commitQueueFilesDock',
    'commitQueueMainSplitter',
    'commitQueueDetailsSlot',
    'commitQueueDetailsPanel',
    'commitQueueEditorScroll',
    'commitQueueBatchEdit',
    'commitQueueApplyToChecked',
    'commitQueueSummarySlot',
    'commitQueueOperationSummary',
    'commitQueueSummaryPreview',
    'commitQueueObjectTitle',
    'commitQueueFutureName',
    'commitQueueSummaryProcess',
    'commitQueueContextChip',
    'commitQueueFileSummary',
    'commitQueueBasicHeading',
    'commitQueueDescription',
    'descriptionSurface',
    'descriptionValue',
    'commitQueueAdvancedToggle',
    'commitQueueActionFooter',
    'commitQueueFooterStatus',
    'commitQueueHeadingIcon',
    'commitQueueHeading',
    'commitQueueCountPill',
    'commitQueueCount',
    'commitQueueAutoCleanSwitchRow',
    'commitQueueAutoCleanSwitch',
    'commitQueueAutoCleanSwitchText',
    'commitQueueFilesSplitter',
    'commitQueueFileHeader',
    'commitQueueFilesHeading',
    'commitQueueFilesCount',
    'commitQueueSourceFiles',
    'commitQueueNavigation',
    'commitQueueWelcomeIcon',
    'commitQueueWelcomeTitle',
    'commitQueueWelcomeMessage'
  ]);
  const include = (name) =>
    names.has(name) ||
    ['commitQueueSource', 'commitQueueField_', 'commitQueueLabel_'].some(
      (prefix) => name.startsWith(prefix)
    );
  return {
    ...surface,
    ...Object.fromEntries(
      ['boxes', 'styles', 'fills', 'interiors'].map((key) => [
        key,
        Object.fromEntries(
          Object.entries(surface[key] || {}).filter(([name]) => include(name))
        )
      ])
    ),
    frameIds: (surface.frameIds || []).filter(include)
  };
}
await fresh();
const browserSources = await fingerprints(),
  captures = [],
  errors = [],
  scans = [];
let scanConflicts = false,
  matches = 0;
let server, browser, current;
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [vue()],
    publicDir: root + 'frontend/public',
    resolve: {
      alias: {
        vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
      }
    },
    logLevel: 'error',
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
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
  await page.route('**/admin/**', async (route) => {
    if (route.request().url().endsWith('/admin/result-items')) {
      assert.equal(route.request().postDataJSON().search_type, 'cg/asset');
      await route.fulfill({
        json: {
          result: {
            items: [
              {
                branches: current.model.processes.map((process) => ({
                  kind: 'process',
                  process,
                  title: process
                }))
              }
            ]
          }
        }
      });
      return;
    }
    assert(
      route.request().url().endsWith('/admin/rpc'),
      'Unexpected fixture request'
    );
    const payload = route.request().postDataJSON();
    if (payload.method === 'get_base_dirs') {
      await route.fulfill({ json: { result: {} } });
      return;
    }
    assert.equal(payload.method, 'execute_cmd');
    if (payload.args[2].action === 'plan') {
      const value = payload.args[2];
      await route.fulfill({
        json: {
          result: {
            info: {
              plan: {
                version: value.version || 1,
                files: value.source_files.map((file, index) => ({
                  title: file.path,
                  indices: [index],
                  versioned: ['repo/v001/' + file.path],
                  versionless: ['repo/latest/' + file.path]
                }))
              }
            }
          }
        }
      });
      return;
    }
    if (payload.args[2].action === 'match') {
      matches++;
      assert.equal(
        payload.args[1],
        'tactic.command.browser_checkin_cmd.BrowserCheckinCmd'
      );
      const paths = payload.args[2].source_files.map((file) => file.path);
      const groups = current.model.groups
        .filter((group) => paths.includes(group.path))
        .map((group) => ({
          ...group,
          size: group.sizeBytes,
          indices: [paths.indexOf(group.path)]
        }));
      await route.fulfill({ json: { result: { info: { groups } } } });
      return;
    }
    if (payload.args[2].action === 'rules') {
      assert.equal(
        payload.args[1],
        'tactic.command.related_ingest_cmd.RelatedIngestCmd'
      );
      await route.fulfill({
        json: { result: { info: { rules: current.model.ingest.rules } } }
      });
      return;
    }
    if (payload.args[2].action === 'scan') {
      assert.equal(
        payload.args[1],
        'tactic.command.related_ingest_cmd.RelatedIngestCmd'
      );
      const values = payload.args[2];
      scans.push(values);
      await route.fulfill({
        json: {
          result: {
            info: {
              files: values.filenames.map((name) => ({
                accepted: true,
                conflict: scanConflicts,
                name: name.replace(/\.[^.]+$/, ''),
                context: values.options.context,
                matches: scanConflicts ? ['cg/shot?code=SHOT001'] : []
              }))
            }
          }
        }
      });
      return;
    }
    assert.equal(payload.args[2].action, 'templates');
    const templates = payload.args[2].templates.map((pattern) => {
      const record = current.model.inspection.find(
        (row) => row.pattern === pattern
      );
      assert(record, 'Missing inspected pattern ' + pattern);
      return record;
    });
    await route.fulfill({ json: { result: { info: { templates } } } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_files/');
  await page.waitForFunction(() => !!window.filesFixture);
  async function seedDrop(host, value) {
    await host
      .locator('[data-frame=dropPlateProcess] option[value=publish]')
      .waitFor({ state: 'attached' });
    if (value.model.groups.length) {
      await host
        .locator('input[type=file]:not([webkitdirectory])')
        .evaluate((input, groups) => {
          const transfer = new DataTransfer();
          for (const group of groups) {
            const file = new File(['fixture'], group.path.split('/').at(-1));
            Object.defineProperty(file, 'webkitRelativePath', {
              value: group.path
            });
            transfer.items.add(file);
          }
          input.files = transfer.files;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }, value.model.groups);
      for (const group of value.model.groups) {
        const checkbox = host.locator(
          '[data-frame=dropPlateCheck_' + group.groupId + '] input'
        );
        await checkbox.waitFor();
        if (!group.checked) await checkbox.uncheck();
      }
    }
  }
  for (const record of native.captures.filter(
    (row) => !row.original && !row.fixture.nativeOnly
  )) {
    current = record.fixture;
    await page.evaluate((value) => window.filesFixture.show(value), current);
    const matching = current.screen.startsWith('matching');
    const dropPlate = current.screen.startsWith('drop-plate');
    const workspace = current.screen.startsWith('workspace-');
    const queue = current.screen.startsWith('queue');
    const selector = matching
      ? '#files-fixture'
      : workspace
        ? '#files-fixture'
        : queue
          ? '.commit-queue-workspace'
          : dropPlate
            ? '.drop-plate'
            : '.ingest-workspace';
    const host = page.locator(selector);
    if (matching)
      await host
        .locator('.matching-templates-workspace[aria-busy=false]')
        .waitFor();
    else if (!dropPlate && !workspace && !queue) {
      await page.waitForFunction(({ width, height }) => {
        const element = document.querySelector('.ingest-workspace');
        const box = element?.getBoundingClientRect();
        return (
          box &&
          Math.abs(box.width - width) < 0.1 &&
          Math.abs(box.height - height) < 0.1 &&
          element.getAttribute('aria-busy') === 'false'
        );
      }, current);
    }
    if (dropPlate) await seedDrop(host, current);
    if (matching && current.model.selected) {
      const key = current.model.templates[current.model.selected].templateId;
      await host
        .locator(
          '[data-frame-row="' + key + '"] [data-frame^=matchingTemplateSelect_]'
        )
        .click();
    }
    await page.evaluate(() => document.activeElement?.blur());
    await page.mouse.move(1590, 990);
    for (let i = 0; i < 3; i++)
      await page.evaluate(() => new Promise(requestAnimationFrame));
    const measured = await surface(page, selector);
    const result = await compareSurface(
      page,
      selector,
      queue ? queueFragments(measured) : measured,
      queue ? queueFragments(record) : record,
      record.image
    );
    for (const [id, expected] of Object.entries(record.indicatorPaint || {})) {
      const paint = await host
        .locator('[data-frame="' + id + '"] > .app-checkbox-indicator > input')
        .evaluate((element) => {
          const context = document.createElement('canvas').getContext('2d');
          context.fillStyle = getComputedStyle(element).backgroundColor;
          context.fillRect(0, 0, 1, 1);
          return [...context.getImageData(0, 0, 1, 1).data];
        });
      for (let channel = 0; channel < 3; channel++)
        assert(
          Math.abs(
            paint[channel] -
              parseInt(
                expected.color.slice(1 + channel * 2, 3 + channel * 2),
                16
              )
          ) <= 1,
          JSON.stringify({ id, actual: paint, expected })
        );
      assert(
        Math.abs(paint[3] / 255 - expected.alpha) < 0.01,
        id + ' indicator alpha'
      );
    }
    for (const [id, parts] of Object.entries(record.editableParts || {})) {
      const control = host.locator('[data-frame="' + id + '"]');
      const input = await control.locator('input').boundingBox(),
        indicator = await control
          .locator('.editable-select-indicator .app-icon')
          .boundingBox();
      for (const key of ['x', 'y', 'width', 'height']) {
        assert(
          Math.abs(input[key] - record.boxes[id][key]) <= 0.1,
          id + ' input ' + key
        );
        assert(
          Math.abs(indicator[key] - parts.indicator[key]) <= 0.1,
          id + ' indicator ' + key
        );
      }
    }
    const image = record.image.replace('-native-', '-stream-');
    await host.screenshot({ path: out + image, animations: 'disabled' });
    captures.push({
      fixture: current,
      image,
      comparison: queue ? 'shared-fragments' : 'full-content',
      ...result
    });
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log('PASS', image, result.rectangles, 'controls');
  }
  current = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'matching' &&
      row.fixture.width === 1000 &&
      row.fixture.language === 'en'
  ).fixture;
  await page.evaluate((value) => window.filesFixture.show(value), current);
  const host = page.locator('#files-fixture');
  await host
    .locator('.matching-templates-workspace[aria-busy=false]')
    .waitFor();
  const selected = current.model.templates[2];
  const selectRow = host.locator(
    '[data-frame="matchingTemplateSelect_' + selected.templateId + '"]'
  );
  await selectRow.click();
  const processField = host.getByRole('combobox', {
    name: 'Process mapping',
    exact: true
  });
  await processField.fill('custom');
  await processField.press('Enter');
  assert.equal(
    await processField.inputValue(),
    'custom',
    'Custom values retain the first character'
  );
  await host
    .getByRole('button', { name: 'Process mapping', exact: true })
    .click();
  await page.getByRole('option', { name: 'render', exact: true }).click();
  assert.equal(await processField.inputValue(), 'render');
  await processField.press('ArrowDown');
  await page.keyboard.press('Escape');
  assert.equal(
    await page
      .getByRole('listbox', { name: 'Process mapping', exact: true })
      .isVisible(),
    false
  );
  assert.equal(
    await processField.evaluate(
      (element) => document.activeElement === element
    ),
    true
  );
  await host
    .locator('[data-frame="matchingEnabled_' + selected.templateId + '"] input')
    .uncheck();
  await host
    .locator('.matching-templates-workspace[aria-busy=false]')
    .waitFor();
  assert.equal(
    await host
      .locator(
        '[data-frame="matchingEnabled_' + selected.templateId + '"] input'
      )
      .isChecked(),
    false
  );
  await selectRow.focus();
  await selectRow.press('ArrowDown');
  await page.waitForFunction(
    () =>
      document.activeElement?.dataset.frame === 'matchingTemplateSelect_udim'
  );
  await page.keyboard.press('End');
  await page.waitForFunction(
    () =>
      document.activeElement?.dataset.frame === 'matchingTemplateSelect_layer'
  );
  await selectRow.click();
  await host.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(() =>
    window.filesFixture.events().some((event) => event.type === 'save')
  );
  const saved = await page.evaluate(
    () =>
      window.filesFixture.events().find((event) => event.type === 'save').value
  );
  assert.equal(
    saved.find((row) => row.templateId === selected.templateId).process,
    'render'
  );
  assert.equal(
    saved.find((row) => row.templateId === selected.templateId).enabled,
    false
  );
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log(
    'PASS matching native-equivalent input: custom text, popup, Escape/focus, check, keyboard and save'
  );
  current = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'drop-plate' &&
      row.fixture.width === 1000 &&
      row.fixture.language === 'en'
  ).fixture;
  await page.evaluate((value) => window.filesFixture.show(value), current);
  const plate = page.locator('.drop-plate');
  await seedDrop(plate, current);
  await plate
    .locator('[data-frame=dropPlateGroup_0]')
    .click({ button: 'right' });
  const fileActions = plate.locator(
    '.drop-plate-file-menu[open] > .account-panel'
  );
  await fileActions.waitFor();
  await seedDrop(plate, current);
  await fileActions.waitFor({ state: 'hidden' });
  await plate
    .locator('[data-frame=dropPlateGroup_0]')
    .click({ button: 'right' });
  await fileActions.waitFor();
  assert.equal(
    await plate.locator('[data-frame=dropPlateCheck_0] input').isChecked(),
    true
  );
  await page.keyboard.press('Escape');
  await fileActions.waitFor({ state: 'hidden' });
  await plate.locator('[data-frame=dropPlateFilter]').fill('diffuse');
  await plate
    .locator('[data-frame=dropPlateGroup_0]')
    .waitFor({ state: 'hidden' });
  assert.equal(
    await plate.locator('[data-frame=dropPlateGroup_1]').isVisible(),
    true
  );
  await plate
    .locator('[data-frame=dropPlateFilterMode]')
    .selectOption('extension');
  await plate.locator('[data-frame=dropPlateFilter]').fill('.exr');
  await plate.locator('[data-frame=dropPlateGroup_0]').waitFor();
  await plate.locator('[data-frame=dropPlateContext]').fill('custom');
  await page.locator('.drop-plate[aria-busy=false]').waitFor();
  assert.equal(
    await plate.locator('[data-frame=dropPlateCheck_1] input').isChecked(),
    false,
    'Context changes preserve excluded file groups'
  );
  await plate.locator('[data-frame=dropPlateQueue]').click();
  const plateQueued = await page.evaluate(() =>
    window.filesFixture
      .events()
      .filter((event) => event.type === 'queue')
      .map((event) => ({
        context: event.value.context,
        description: event.value.description,
        names: event.value.files.map((file) => file.name)
      }))
  );
  assert.deepEqual(plateQueued, [
    { context: 'custom', description: '', names: ['beauty.0001.exr'] }
  ]);
  assert.equal(
    await plate.locator('[data-frame=dropPlateGroup_1]').isVisible(),
    true
  );
  console.log(
    'PASS Drop Plate native-equivalent input: right-click menu, Escape, name/extension filters, retained checks and queue handoff'
  );
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        read: () =>
          new Promise((resolve) => {
            window.releaseDropClipboard = resolve;
          })
      }
    });
  });
  await plate.locator('[data-frame=dropPlatePaste]').click();
  await page.waitForFunction(() => window.releaseDropClipboard);
  await plate.locator('[data-frame=dropPlateClear]').click();
  const beforeStaleClipboard = matches;
  await page.evaluate(async () => {
    window.releaseDropClipboard([
      {
        types: ['image/png'],
        getType: async () => new Blob(['stale'], { type: 'image/png' })
      }
    ]);
    for (let i = 0; i < 3; i++) await new Promise(requestAnimationFrame);
  });
  assert.equal(await plate.locator('[data-frame^=dropPlateGroup_]').count(), 0);
  assert.equal(matches, beforeStaleClipboard);
  console.log('PASS Drop Plate clear rejects a late clipboard read');
  current = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.screen === 'ingest-advanced' &&
      row.fixture.width === 1000 &&
      row.fixture.language === 'en'
  ).fixture;
  await page.evaluate((value) => window.filesFixture.show(value), current);
  const ingestDialog = page.locator('.ingest-files[open]');
  const ingestHost = page.locator('.ingest-workspace');
  await ingestHost.locator('[data-frame=ingestOption_filter]').fill('.mov');
  assert.equal(
    await page.evaluate(() => window.filesFixture.ingest().options.filter),
    '.mov'
  );
  await ingestHost
    .locator('[data-frame=ingestOption_usePattern] input')
    .check();
  await ingestHost
    .locator('[data-frame=ingestOption_pattern]')
    .fill('{sobject.name}.mov');
  await ingestHost
    .locator('[data-frame=ingestOption_updateMode] input')
    .check();
  await ingestHost
    .locator('[data-frame=ingestOption_keywordMode]')
    .selectOption('simplified');
  await ingestHost
    .locator('[data-frame=ingestOption_contextMode]')
    .selectOption('case_insensitive');
  await ingestHost
    .locator('[data-frame=ingestOption_extraDataJson]')
    .fill('[]');
  const beforeInvalid = scans.length;
  await ingestHost.locator('[data-frame=ingestStart]').click();
  await ingestHost
    .getByRole('alert')
    .getByText('Extra values must be a JSON object', { exact: true })
    .waitFor();
  assert.equal(
    scans.length,
    beforeInvalid,
    'Invalid JSON is rejected before a server request'
  );
  await ingestHost
    .locator('[data-frame=ingestOption_extraDataJson]')
    .fill('{"description":"fixture"}');
  await ingestHost
    .locator('[data-frame=ingestOption_updateMode] input')
    .uncheck();
  scanConflicts = true;
  await ingestHost.locator('[data-frame=ingestStart]').click();
  const conflicts = page.locator('.ingest-conflict-dialog[open]');
  await conflicts.waitFor();
  await conflicts.locator('[data-frame=ingestConflict_cancel]').click();
  await conflicts.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(() => window.filesFixture.ingest().files.length),
    3
  );
  await ingestHost.locator('[data-frame=ingestStart]').click();
  await conflicts.waitFor();
  await conflicts.locator('[data-frame=ingestConflict_update]').click();
  await ingestDialog.waitFor({ state: 'hidden' });
  const queued = await page.evaluate(() =>
    window.filesFixture
      .events()
      .filter((event) => event.type === 'queue')
      .map((event) => ({
        name: event.value.file.name,
        ingest: event.value.ingest
      }))
  );
  assert.equal(queued.length, 3);
  assert.equal(queued[0].name, 'shot_010.exr');
  assert.equal(queued[0].ingest.decision, 'update');
  assert.equal(queued[0].ingest.options.keywordMode, 'simplified');
  assert.equal(queued[0].ingest.options.contextMode, 'case_insensitive');
  assert.deepEqual(queued[0].ingest.options.extraData, {
    description: 'fixture'
  });
  const empty = structuredClone(current);
  empty.screen = 'ingest-empty';
  empty.model.ingest.files = [];
  await page.evaluate((value) => window.filesFixture.show(value), empty);
  await ingestDialog.locator('input[type=file]').setInputFiles(
    Array.from({ length: 1000 }, (_, index) => ({
      name: 'file_' + index + '.exr',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from(String(index))
    }))
  );
  const collection = ingestHost.locator('.virtual-collection');
  await collection.locator('[data-frame=ingestFile_0]').waitFor();
  assert.equal(await collection.getAttribute('data-collection-total'), '1000');
  assert(
    (await collection.locator('[data-frame^=ingestFileRemove_]').count()) < 50,
    'Large file staging remains virtualized'
  );
  await collection.locator('[data-frame=ingestFileRemove_0]').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.ingest().files[0].file.name),
    'file_1.exr'
  );
  await ingestHost
    .locator('.ingest-file-viewport')
    .evaluate((element) => (element.scrollTop = element.scrollHeight));
  await collection.locator('[data-frame=ingestFile_998]').waitFor();
  await ingestHost.locator('[data-frame=ingestClose]').click();
  const discard = page.locator('.ingest-confirmation-dialog[open]');
  await discard.locator('[data-frame=confirmationReject]').click();
  assert.equal(await ingestDialog.isVisible(), true);
  assert.equal(await collection.getAttribute('data-collection-total'), '999');
  await ingestHost.locator('[data-frame=ingestClose]').click();
  await discard.locator('[data-frame=confirmationAccept]').click();
  await ingestDialog.waitFor({ state: 'hidden' });
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log(
    'PASS ingest native-equivalent input: rule fields, JSON guard, conflict cancel/update, queue payload, 1000 files, remove/scroll and discard guard'
  );
  await fresh();
  assert.deepEqual(
    await fingerprints(),
    browserSources,
    'Sources changed during browser capture'
  );
  await writeFile(
    out + 'browser.json',
    JSON.stringify({ status: 'passed', captures, browserSources }, null, 2)
  );
} finally {
  await browser?.close();
  await server?.close();
}
