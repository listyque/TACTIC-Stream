import assert from 'node:assert/strict';
import { writeFile, mkdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = new URL('../../', import.meta.url).pathname.replace(
  /^\/(\w:)/,
  '$1'
);
const out = root + 'tools/frame_remaining/output/';
const sources = {};
for (const name of [
  'frontend/tests/frame_remaining_workflows.mjs',
  'tools/frame_remaining/RemainingFixture.vue',
  'frontend/src/features/knowledge/KnowledgeBase.vue',
  'frontend/src/features/collaboration/InitializationState.vue',
  'frontend/src/features/documentation/ApiDocumentation.vue',
  'frontend/src/features/journal/JournalDetails.vue',
  'frontend/src/features/objects/TimeEntryPanel.vue',
  'frontend/src/features/objects/WorkHourForm.vue',
  'frontend/src/features/objects/WorkReportSurface.vue'
])
  sources[name] = createHash('sha256')
    .update(await readFile(root + name))
    .digest('hex');
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
  scenarios = [];
try {
  await mkdir(out, { recursive: true });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const context = await browser.newContext({
    viewport: { width: 900, height: 700 },
    permissions: ['clipboard-read', 'clipboard-write']
  });
  const page = await context.newPage();
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_remaining/index.html'
  );
  await page.waitForFunction(() => window.fixture);
  const configure = async (screen, model = {}, width = 900) => {
    await page.setViewportSize({ width, height: 700 });
    await page.evaluate((value) => window.fixture.load(value), {
      screen,
      model,
      width,
      height: 700,
      style: 'md3',
      dark: true,
      language: 'en'
    });
    await page.evaluate(() => document.fonts.ready);
  };
  await configure('format', { mode: 'visual' });
  await page.locator('[data-frame="knowledgeTextStyle"]').click();
  let actions = await page.evaluate(() => window.frameEvents.splice(0));
  assert.deepEqual(
    actions.map((row) => !!row.pressed),
    [true, false]
  );
  await page.locator('[data-frame="knowledgeTextStyle"]').focus();
  await page.keyboard.press('Space');
  actions = await page.evaluate(() => window.frameEvents.splice(0));
  assert.deepEqual(
    actions.map((row) => !!row.pressed),
    [true, false]
  );
  scenarios.push('Pointer and keyboard preserve Action press/activate order');

  const users = [{ value: 'robin', label: 'Robin' }];
  const entry = {
    search_key: 'sthpw/work_hour?code=H1',
    task_title: 'Robot Arm',
    day: '2026-10-14',
    hours: 2.5,
    category: 'regular',
    login: 'robin',
    process: 'Model',
    status: 'approved',
    description: 'Model review',
    can_edit: true
  };
  const result = {
    entries: [entry],
    summary: { logged: 2.5, approved: 2.5, pending: 0, overtime: 0 },
    week_start: '2026-10-12',
    week_end: '2026-10-18'
  };
  await configure('time', { result, users });
  await page.evaluate(() => window.fixture.openTime());
  await page.getByLabel('Team member', { exact: true }).click();
  await page.getByRole('radio', { name: 'All users', exact: true }).click();
  assert.equal(await page.evaluate(() => window.fixture.data.model.login), '');
  await page.locator('[data-frame="timesheetEntrySelect"]').click();
  assert.equal(
    await page.locator('[data-frame="timesheetEntrySelect"] input').isChecked(),
    true
  );
  await page.locator('[data-frame="timesheetCreate"]').click();
  const hours = page.getByLabel('Duration, hours', { exact: true });
  await hours.fill('25');
  assert.equal(
    await page.locator('[data-frame="workHourApprove"]').isDisabled(),
    true
  );
  await hours.fill('2.75');
  await page
    .getByLabel('Description', { exact: true })
    .fill('Review completed');
  await page.locator('[data-frame="workHourApprove"]').click();
  const saved = await page.evaluate(() =>
    window.frameEvents.find((row) => row.type === 'saveHour')
  );
  assert.equal(saved.approve, true);
  assert.equal(saved.draft.hours, '2.75');
  assert.equal(saved.draft.description, 'Review completed');
  await page.setViewportSize({ width: 320, height: 700 });
  await page.evaluate(() => {
    window.fixture.data.width = 320;
  });
  await page.locator('[data-frame="workHourApprove"]').scrollIntoViewIfNeeded();
  const approval = await page
    .locator('[data-frame="workHourApprove"]')
    .boundingBox();
  assert.ok(approval.x >= 0 && approval.x + approval.width <= 320);
  await page.locator('[data-frame="workHourCancel"]').click();
  assert.equal(await hours.count(), 0);
  scenarios.push(
    'Time entry selection, real fields, validation, approve/cancel and phone bounds'
  );

  const options = [
    { key: 'my_hours', title: 'My Work Hours', permission: 'user' }
  ];
  const values = Array.from({ length: 1500 }, (_, index) => ({
    label: 'Person ' + String(index).padStart(4, '0'),
    valueLabel: index + ' h',
    share: 0.4
  }));
  await configure('reports', {
    report: 'my_hours',
    options,
    values,
    count: values.length,
    weekStart: '2026-10-12',
    weekEnd: '2026-10-18'
  });
  const list = page.locator('[data-frame="workReportValues"]');
  await list.waitFor();
  assert.ok(
    (await page.locator('[data-frame="workReportValueLabel"]').count()) < 80
  );
  await list.evaluate((node) => (node.scrollTop = node.scrollHeight));
  await page.getByText('Person 1499', { exact: true }).waitFor();
  assert.ok(
    (await page.locator('[data-frame="workReportValueLabel"]').count()) < 80
  );
  scenarios.push('1500 report rows remain virtualized and reach the last row');

  let pendingResolve;
  const pending = new Promise((resolve) => (pendingResolve = resolve));
  await page.route('**/api/documentation', (route) => pendingResolve(route));
  await configure('api');
  const request = await pending;
  const failed = page.waitForEvent('requestfailed', {
    predicate: (request) => request.url().endsWith('/api/documentation')
  });
  await configure('editor', { kind: 'article', dirty: true });
  await failed;
  await request.abort();
  await page.unroute('**/api/documentation');
  scenarios.push('Closing the API console aborts its pending catalogue read');

  await page.route('**/admin/transaction-log/details', (route) => {
    const key = route.request().postDataJSON().search_key;
    return route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        result: { xml: '<transaction code="' + key + '"/>', hidden: 2 }
      })
    });
  });
  await configure('journal', { searchKey: 'old' });
  await page.getByText('<transaction code="old"/>', { exact: true }).count();
  await page.locator('[data-frame="journalCopy"]:not([disabled])').waitFor();
  await page.evaluate(() => {
    navigator.clipboard.writeText = () =>
      new Promise((resolve) => (window.finishClipboard = resolve));
  });
  await page.locator('[data-frame="journalCopy"]').click();
  await page.waitForFunction(() => window.finishClipboard);
  await configure('journal', { searchKey: 'new' });
  await page.locator('[data-frame="journalCopy"]:not([disabled])').waitFor();
  await page.evaluate(() => window.finishClipboard());
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    await page.getByText('Copied to clipboard', { exact: true }).count(),
    0
  );
  assert.match(await page.locator('.code-block').innerText(), /new/);
  scenarios.push(
    'A late clipboard completion cannot publish into another transaction'
  );
  await configure('initialization', { canInitialize: true, project: 'alpha' });
  await page.locator('[data-frame="collaborationInitializeButton"]').click();
  await page
    .locator('[data-frame="collaborationInitializationCancel"]')
    .click();
  assert.equal(
    await page
      .locator('[data-frame="collaborationInitializationCancel"]')
      .isVisible(),
    false
  );
  await page.locator('[data-frame="collaborationInitializeButton"]').click();
  await configure('initialization', { canInitialize: true, project: 'beta' });
  assert.equal(
    await page
      .locator('[data-frame="collaborationInitializationCancel"]')
      .isVisible(),
    false
  );
  await page.locator('[data-frame="collaborationInitializeButton"]').click();
  await page
    .locator('[data-frame="collaborationInitializationConfirm"]')
    .click();
  assert.equal(
    await page.evaluate(
      () => window.frameEvents.filter((row) => row.type === 'initialize').length
    ),
    1
  );
  scenarios.push(
    'Schema initialization requires confirmation and closes on project changes'
  );

  let initializeResolve;
  const initializing = new Promise((resolve) => (initializeResolve = resolve));
  await page.route('**/admin/knowledge/*', (route) => {
    const action = route.request().url().split('/').pop();
    if (action === 'initialize') {
      initializeResolve(route);
      return;
    }
    return route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          initialized: false,
          canEdit: false,
          canInitialize: route.request().postDataJSON().project === 'alpha',
          catalog: []
        }
      })
    });
  });
  await configure('knowledge', { project: 'alpha' });
  await page.locator('[data-frame="collaborationInitializeButton"]').click();
  await page
    .locator('[data-frame="collaborationInitializationConfirm"]')
    .click();
  const initializationRequest = await initializing;
  await configure('knowledge', { project: 'beta' });
  await page
    .getByText('A TACTIC administrator must initialize these features once.', {
      exact: true
    })
    .waitFor();
  await initializationRequest.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      result: {
        initialized: true,
        canEdit: true,
        canInitialize: true,
        catalog: []
      }
    })
  });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    await page
      .locator('[data-frame="collaborationInitializeButton"]')
      .isVisible(),
    false
  );
  assert.equal(
    await page
      .getByText(
        'A TACTIC administrator must initialize these features once.',
        { exact: true }
      )
      .count(),
    1
  );
  scenarios.push(
    'A late schema mutation cannot overwrite the next project or its permissions'
  );
  assert.deepEqual(errors, []);
  await writeFile(
    out + 'workflows.json',
    JSON.stringify({ status: 'passed', scenarios, sources }, null, 2)
  );
  console.log('PASS', scenarios.length, 'browser input/lifecycle workflows');
} finally {
  await browser?.close();
  await server.close();
}
