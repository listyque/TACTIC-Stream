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
  let dependencyFixture;
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (
      body.args?.[1] !== 'tactic.ui.table.TableDependencyReadCmd' ||
      !dependencyFixture
    )
      return route.continue();
    if (dependencyFixture.mode === 'error')
      return route.fulfill({ status: 400, json: { error: 'File Offline' } });
    const request = body.args[2];
    const info =
      dependencyFixture.mode === 'empty'
        ? { rows: [], hasNext: false, message: 'No snapshot found' }
        : dependencyFixture.data[
            request.file_index !== undefined
              ? 'range'
              : request.search_key === dependencyFixture.data.seed.searchKey
                ? 'root'
                : 'child'
          ];
    await route.fulfill({ json: { result: { info } } });
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
  const tagFixture = native.captures.find(
    (row) =>
      !row.original &&
      row.fixture.mode === 'tags' &&
      row.fixture.language === 'en'
  ).fixture;
  await page.evaluate(
    ({ fixture, data }) => window.tableFixture.show(fixture, data),
    { fixture: tagFixture, data: native.data }
  );
  await page.evaluate(() => window.tableFixture.events.value.splice(0));
  const tagInput = page.locator('[data-frame="tableInlineValue"] input');
  await tagInput.fill('rig, Production asset');
  await tagInput.press('Enter');
  await page.locator('[data-frame="tableInlineTag_0"]').click();
  await tagInput.fill(' final ');
  await page.mouse.click(780, 600);
  assert.equal(
    await page.evaluate(
      () =>
        window.tableFixture.events.value.filter(
          (event) => event.type === 'save'
        ).length
    ),
    0,
    'Tag draft requires explicit Save'
  );
  await page.locator('[data-frame="tableInlineSave"]').click();
  assert.deepEqual(
    await page.evaluate(() =>
      window.tableFixture.events.value
        .filter((event) => event.type === 'save')
        .map((event) => event.value)
    ),
    ['rig, final']
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
  for (const [name, target, expected] of [
    ['custom_layout', 'customLayout_0', 'script'],
    ['custom_layout', 'customLayout_1', 'layout-link'],
    ['parallel_status', 'parallelTask_0_0', 'task-details'],
    ['parallel_status', 'parallelProcess_0', 'task-details'],
    ['drop_links', 'dropEdit', 'edit-links']
  ]) {
    const fixture = structuredClone(
      embedded.find(
        (row) =>
          row.fixture.value.name === name && row.fixture.language === 'en'
      ).fixture
    );
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
    await page.locator('[data-frame="' + target + '"]').click();
    const calls = await page.evaluate(() => window.tableFixture.events.value);
    assert.equal(calls.length, 1, name + ' must activate on its first click');
    assert.equal(calls[0].name, expected);
    if (target === 'customLayout_0')
      assert.equal(
        calls[0].cell.displayOptions.cbjs_action,
        'alert("fixture")'
      );
    if (target === 'parallelTask_0_0')
      assert.equal(calls[0].cell.actionTaskCode, 'T0');
  }
  {
    const fixture = structuredClone(
      native.captures.find(
        (row) =>
          row.fixture.screen === 'table' &&
          !row.original &&
          row.fixture.language === 'en' &&
          row.fixture.width === 1496
      ).fixture
    );
    const data = structuredClone(native.data),
      column = data.definition.table.elements[0];
    column.display = {
      handler: 'pyasm.widget.table_element_wdg.UpdateWdg',
      options: { insert_view: 'insert_review' }
    };
    column.resolvedClass = column.display.handler;
    column.displayOptions = column.display.options;
    column.cell = { ...column.cell, kind: 'commands', supported: true };
    await page.evaluate(
      ({ fixture, data }) => window.tableFixture.show(fixture, data),
      { fixture, data }
    );
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.evaluate(() => window.tableFixture.events.value.splice(0));
    await page.getByRole('button', { name: 'Create', exact: true }).click();
    assert.deepEqual(
      await page.evaluate(() => window.tableFixture.events.value),
      [
        {
          type: 'header-action',
          value: { type: 'insert', view: 'insert_review' }
        }
      ]
    );
  }
  await page.evaluate(() => {
    window.confirmResult = null;
    window.tableFixture
      .confirm('Update fixture?')
      .then((value) => (window.confirmResult = value));
  });
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.waitForFunction(() => window.confirmResult === true);
  await page.evaluate(() => {
    window.confirmResult = null;
    window.tableFixture
      .confirm('Cancel fixture?')
      .then((value) => (window.confirmResult = value));
  });
  await page.getByRole('button', { name: 'Cancel', exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => window.confirmResult === false);
  await page.evaluate(async () => {
    const pending = window.tableFixture.confirm('Stale fixture?');
    window.tableFixture.cancelConfirmation();
    window.confirmResult = await pending;
  });
  assert.equal(
    await page.locator('.table-service-confirmation[open]').count(),
    0,
    'Cancelled confirmation must not reopen on nextTick'
  );
  await page.setViewportSize({ width: 320, height: 700 });
  await page.evaluate(() => {
    window.confirmResult = null;
    window.tableFixture
      .confirm('Narrow fixture?')
      .then((value) => (window.confirmResult = value));
  });
  const accept = page.getByRole('button', { name: 'Continue', exact: true });
  await accept.waitFor();
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  const bounds = await page
    .locator('.table-service-confirmation[open]')
    .boundingBox();
  const button = await accept.boundingBox(),
    message = await page
      .locator(
        '.table-service-confirmation[open] [data-frame="confirmationMessage"]'
      )
      .boundingBox();
  assert(
    button.x >= bounds.x &&
      button.x + button.width <= bounds.x + bounds.width + 0.1
  );
  assert(
    message.y + message.height <= button.y,
    'Narrow confirmation controls must not overlap'
  );
  await accept.click();
  await page.waitForFunction(() => window.confirmResult === true);
  await page.setViewportSize({ width: 900, height: 700 });
  await page.evaluate(() =>
    window.tableFixture.openDocument({
      title: 'Security summary',
      identity: 'admin',
      sections: [
        { title: 'crew', text: '<rules/>', syntax: 'xml' },
        { title: 'review', text: '<rules><allow/></rules>', syntax: 'xml' }
      ]
    })
  );
  const documentWindow = page.locator('.table-document[open]');
  await documentWindow.waitFor();
  assert.equal(
    await documentWindow.evaluate((element) => element.matches(':modal')),
    false
  );
  assert.equal(await documentWindow.locator('.app-window-controls').count(), 1);
  const source = documentWindow.getByRole('textbox', {
    name: 'Script source',
    exact: true
  });
  await source.waitFor();
  assert.equal(await source.inputValue(), '<rules/>');
  assert((await source.getAttribute('readonly')) !== null);
  const groupChoice = documentWindow.getByRole('combobox', {
    name: 'Groups',
    exact: true
  });
  await groupChoice.click();
  await page.getByRole('option', { name: 'review', exact: true }).click();
  assert.equal(await source.inputValue(), '<rules><allow/></rules>');
  assert.equal(await documentWindow.locator('.code-editor').count(), 1);
  await documentWindow
    .getByRole('button', { name: 'Code editor help', exact: true })
    .click();
  assert(
    await page.evaluate(() =>
      window.tableFixture.events.value.some(
        (event) => event.type === 'help' && event.topic === 'table_widgets_b07'
      )
    )
  );
  await page.evaluate(() => window.tableFixture.closeDocument());
  await page.evaluate(() =>
    window.tableFixture.openDocument({
      title: 'Security summary',
      identity: 'test',
      sections: [{ title: 'crew', text: '<other/>', syntax: 'xml' }]
    })
  );
  await source.waitFor();
  assert.equal(await source.inputValue(), '<other/>');
  await documentWindow
    .locator('header')
    .getByRole('button', { name: 'Close', exact: true })
    .click();
  await documentWindow.waitFor({ state: 'hidden' });
  await page.evaluate(
    ({ fixture, data }) =>
      window.tableFixture.show({ ...fixture, language: 'ru' }, data),
    {
      fixture: {
        screen: 'table',
        width: 800,
        height: 420,
        style: 'md3',
        dark: true
      },
      data: native.data
    }
  );
  await page.evaluate(() =>
    window.tableFixture.openDocument({ title: 'Dependencies', sections: [] })
  );
  await documentWindow
    .getByRole('heading', { name: 'Зависимости', exact: true })
    .waitFor();
  await page.evaluate(() => window.tableFixture.closeDocument());
  await documentWindow.waitFor({ state: 'hidden' });
  await page.locator('#table-fixture').focus();
  for (const record of native.captures.filter((item) => !item.original)) {
    const fixture = record.fixture;
    dependencyFixture = fixture.screen === 'dependencies' ? fixture : null;
    await page.setViewportSize({
      width:
        fixture.screen === 'inline' &&
        ['multiline', 'tags'].includes(fixture.mode)
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
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.mouse.move(1599, 699);
    if (fixture.screen === 'inline') {
      const selector = '.table-inline-editor:popover-open > .frame-view';
      if (
        ['multiline', 'tags', 'date', 'datetime', 'color'].includes(
          fixture.mode
        )
      ) {
        const expected = `rgb(${[1, 3, 5].map((index) => parseInt(record.background.slice(index, index + 2), 16)).join(', ')})`;
        assert.equal(
          await page
            .locator('.table-inline-editor:popover-open')
            .evaluate((element) => getComputedStyle(element).backgroundColor),
          expected,
          'Inline popup uses the native surface background'
        );
      }
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
    } else if (['append', 'checkout'].includes(fixture.screen)) {
      const selector =
        fixture.screen === 'append'
          ? '.object-checkin-workspace > .frame-view'
          : '.snapshot-checkout-workspace > .frame-view';
      if (record.progress) {
        const progress = await page
          .locator('[data-frame=snapshotCheckoutProgress].app-progress')
          .evaluate((element, native) => {
            const rgba = (color) => {
              const canvas = document.createElement('canvas');
              canvas.width = canvas.height = 1;
              const context = canvas.getContext('2d');
              // Check visible RGB and alpha separately; unpremultiplication loses low-alpha precision.
              context.fillStyle = '#000';
              context.fillRect(0, 0, 1, 1);
              context.fillStyle = color;
              context.fillRect(0, 0, 1, 1);
              const painted = [...context.getImageData(0, 0, 1, 1).data].slice(
                0,
                3
              );
              context.clearRect(0, 0, 1, 1);
              context.fillRect(0, 0, 1, 1);
              return painted.concat(context.getImageData(0, 0, 1, 1).data[3]);
            };
            const style = getComputedStyle(element),
              fill = getComputedStyle(element, '::before');
            return {
              value: Number(style.getPropertyValue('--progress-value')),
              fill: rgba(fill.backgroundColor),
              track: rgba(style.backgroundColor),
              native: Object.fromEntries(
                ['fill', 'track'].map((name) => {
                  const [red, green, blue, alpha] = native[name];
                  return [
                    name,
                    rgba(`rgba(${red}, ${green}, ${blue}, ${alpha / 255})`)
                  ];
                })
              )
            };
          }, record.progress);
        assert.equal(progress.value, record.progress.value);
        for (const color of ['fill', 'track'])
          progress[color].forEach((channel, index) =>
            assert(
              Math.abs(channel - progress.native[color][index]) <= 1,
              JSON.stringify({
                image: record.image,
                color,
                actual: progress[color],
                native: progress.native[color]
              })
            )
          );
        const actual = await page
          .locator('[data-frame=snapshotCheckoutProgress].app-progress')
          .boundingBox();
        const root = await page.locator(selector).boundingBox();
        for (const [key, expected] of Object.entries(record.progress.bounds)) {
          const value =
            key === 'x'
              ? actual.x - root.x
              : key === 'y'
                ? actual.y - root.y
                : actual[key];
          assert(
            Math.abs(value - expected) <= 0.1,
            record.image + ' progress ' + key
          );
        }
      }
      for (const [id, enabled] of Object.entries(record.enabled))
        assert.equal(
          await page.locator('[data-frame="' + id + '"]').isEnabled(),
          enabled,
          record.image + ' ' + id + ' enabled state'
        );
      const background = `rgb(${[1, 3, 5].map((index) => parseInt(record.background.slice(index, index + 2), 16)).join(', ')})`;
      assert.equal(
        await page
          .locator(
            '[data-frame=' +
              (fixture.screen === 'append'
                ? 'snapshotAppendSurface'
                : 'snapshotCheckoutSurface') +
              ']'
          )
          .evaluate((element) => getComputedStyle(element).backgroundColor),
        background,
        'File form body paint matches the real native host'
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
    } else if (
      ['dependencies', 'parent', 'parent-group'].includes(fixture.screen)
    ) {
      const selector = '#table-fixture > .frame-view';
      if (fixture.screen === 'parent' && fixture.mode === 'unknown') {
        const backgrounds = await page
          .locator(selector + ' button.frame-action:disabled')
          .evaluateAll((items) =>
            items.map((item) => getComputedStyle(item).backgroundColor)
          );
        assert(backgrounds.length > 0);
        assert(
          backgrounds.every((color) => color === 'rgba(0, 0, 0, 0)'),
          'Disabled Frame actions keep their ItemSurface paint without an AppButton background'
        );
      }
      if (fixture.screen === 'parent')
        await page
          .locator(selector)
          .locator(
            '[data-frame="' +
              (fixture.mode === 'discard'
                ? 'confirmationMessage'
                : 'parentHeading') +
              '"]'
          )
          .waitFor();
      else if (fixture.screen === 'parent-group')
        await page
          .locator(selector)
          .locator('[data-frame="parentGroupTitle"]')
          .waitFor();
      else if (fixture.mode === 'error' || fixture.mode === 'empty')
        await page.locator('[data-frame^="dependencyStatus_"]').waitFor();
      else
        await page
          .locator('[data-frame^="dependencyTitle_"]')
          .first()
          .waitFor();
      if (fixture.screen === 'dependencies' && fixture.mode === 'expanded') {
        await page.locator('[data-frame="dependencyExpand_root_0"]').click();
        await page
          .getByText(
            fixture.language === 'ru'
              ? /Циклическая зависимость/
              : /Cyclic dependency/
          )
          .waitFor();
        await page.mouse.move(1599, 699);
      }
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
    } else if (fixture.screen === 'nested') {
      const selector = '.nested-table > .frame-view';
      for (const [text, label] of Object.entries(record.embeddedText)) {
        const cell = page
          .locator('.nested-table .table-cell-text')
          .filter({ hasText: text })
          .first();
        const actualText = await cell.evaluate((element) => {
          const box = element.getBoundingClientRect(),
            origin = element.closest('.nested-table').getBoundingClientRect(),
            style = getComputedStyle(element);
          return {
            x: box.x - origin.x,
            centerY: box.y - origin.y + box.height / 2,
            fontSize: parseFloat(style.fontSize),
            weight: Number(style.fontWeight)
          };
        });
        for (const key of ['x', 'centerY', 'fontSize', 'weight'])
          assert(
            Math.abs(actualText[key] - label[key]) <=
              (key === 'centerY' ? 1 : 0.1),
            JSON.stringify({
              image: record.image,
              text,
              key,
              vue: actualText[key],
              qml: label[key]
            })
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
      for (const [id, text] of Object.entries(record.summaryText || {}))
        assert.equal(
          await page
            .locator(selector)
            .locator('[data-frame="' + id + '"]')
            .innerText(),
          text,
          'Summary text must match visible QML labels'
        );
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
    'frontend/src/api.js',
    'frontend/src/features/objects/previewFiles.js',
    'frontend/src/features/objects/FilePreview.vue',
    'frontend/src/features/objects/FilePreviewContent.vue',
    'frontend/src/locales/ru.json'
  ])
    browserSources[name] = createHash('sha256')
      .update(await readFile(root + name))
      .digest('hex');
  for (const path of [
    'frontend/src/features/interface',
    'frontend/src/features/checkin',
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
