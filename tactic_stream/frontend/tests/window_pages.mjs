import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const [base, output] = process.argv.slice(2);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  channel: 'msedge',
  ignoreDefaultArgs: ['--hide-scrollbars']
});
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 940 }
  });
  await context.addInitScript((ticket) => {
    if (!location.origin || location.origin === 'null') return;
    if (!localStorage.getItem('tactic_stream.session'))
      localStorage.setItem(
        'tactic_stream.session',
        JSON.stringify({ ticket, login: 'admin', project: 'one' })
      );
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    );
  }, process.env.STREAM_CHECK_TICKET);
  const page = await context.newPage(),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(base + '/projects/one/');
  await page.getByLabel('Account', { exact: true }).first().click();
  await page
    .locator('.account-menu')
    .getByRole('button', { name: 'Messages', exact: true })
    .click();
  const messages = page.locator('.messages-dialog[open]');
  await page.waitForFunction(
    () =>
      document.querySelector('.messages-dialog')?.getAttribute('aria-busy') ===
      'false'
  );
  if (
    await messages
      .getByRole('button', { name: 'Initialize', exact: true })
      .count()
  ) {
    await messages
      .getByRole('button', { name: 'Initialize', exact: true })
      .click();
    await page
      .getByRole('dialog', { name: 'Initialize server features?', exact: true })
      .getByRole('button', { name: 'Initialize', exact: true })
      .click();
    await messages.locator('.messages-layout').waitFor();
  }
  await messages
    .getByRole('button', { name: /Favorites/ })
    .first()
    .click({ timeout: 10000 });
  await messages
    .getByLabel('Write a reply', { exact: true })
    .fill('Unsent window-page draft');
  const saved = await page.evaluate(() =>
    localStorage.getItem('tactic_stream.workspace.admin')
  );
  const next = context.waitForEvent('page');
  await messages
    .locator('> header')
    .getByRole('button', { name: 'Open in separate page', exact: true })
    .click();
  const child = await next;
  child.on('pageerror', (error) => errors.push(error.message));
  const queries = [];
  child.on('request', (request) => {
    if (request.url().includes('/search-configuration/query'))
      queries.push(request.url());
  });
  await child.locator('.window-page-root.messages-dialog[open]').waitFor();
  assert.equal(await child.evaluate(() => window.opener), null);
  assert(!child.url().includes(process.env.STREAM_CHECK_TICKET));
  assert.equal(new URL(child.url()).pathname, '/projects/one/');
  await child.waitForURL((url) => !url.searchParams.has('launch'));
  assert.equal(await child.locator('.topbar:visible').count(), 0);
  assert.equal(await child.locator('.dock-workspace').count(), 0);
  assert.equal(
    await child.getByLabel('Write a reply', { exact: true }).inputValue(),
    'Unsent window-page draft'
  );
  const box = await child.locator('.window-page-root').boundingBox();
  assert(
    Math.abs(box.x) < 1 &&
      Math.abs(box.y) < 1 &&
      Math.abs(box.width - 1440) < 1 &&
      Math.abs(box.height - 940) < 1,
    JSON.stringify(box)
  );
  await child.screenshot({ path: output + '/messages-page.png' });
  await page.close();
  await child.reload();
  await child.locator('.window-page-root.messages-dialog[open]').waitFor();
  assert.equal(
    await child.getByLabel('Write a reply', { exact: true }).inputValue(),
    'Unsent window-page draft'
  );
  assert.equal(
    await child.evaluate(() =>
      localStorage.getItem('tactic_stream.workspace.admin')
    ),
    saved
  );
  assert.deepEqual(queries, []);
  assert.deepEqual(errors, []);
  await child.getByRole('button', { name: 'Send', exact: true }).last().click();
  await child
    .getByText('Unsent window-page draft', { exact: true })
    .first()
    .waitFor();
  await child.setViewportSize({ width: 360, height: 780 });
  assert.equal(await child.locator('.topbar:visible').count(), 0);
  assert(
    await child.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  );
  await child.screenshot({ path: output + '/messages-narrow.png' });
  await child.setViewportSize({ width: 1440, height: 940 });
  // The same owner and chrome are used by ordinary utility pages and editors.
  for (const [kind, route, selector] of [
    [
      'configuration',
      { page: 'projects' },
      '.configuration-dialog.window-page-root[open]'
    ],
    [
      'administration',
      { section: 'rules' },
      '.administration-dialog.window-page-root[open]'
    ],
    ['script_editor', {}, '.script-editor-dialog.window-page-root[open]'],
    ['project_templates', {}, '.window-page-root[open]'],
    ['milestone_manager', {}, '.window-page-root[open]'],
    ['agent_mcp', {}, '.window-page-root[open]'],
    ['agent_request', {}, '.window-page-root[open]'],
    ['agent_providers', {}, '.agent-providers-dialog.window-page-root[open]'],
    ['help', { args: ['communication'] }, '.window-page-root[open]'],
    ['user_profile', { args: ['admin', false] }, '.window-page-root[open]'],
    ['project_wizard', {}, '.window-page-root[open]'],
    [
      'sobject_info',
      { key: 'contract/entity?project=one&code=A' },
      '.object-details.window-page-root[open]'
    ],
    [
      'add_sobject',
      {
        searchType: 'contract/entity',
        args: ['contract/entity?project=one&code=A']
      },
      '.record-form-dialog.window-page-root[open]'
    ],
    ['task_manager', {}, '.task-manager.window-page-root[open]'],
    ['work_hours', { args: [null, false, true] }, '.window-page-root[open]'],
    [
      'snapshot_browser',
      { target: { key: 'contract/entity?project=one&code=A' } },
      '.window-page-root[open]'
    ]
  ]) {
    const tool = await context.newPage();
    tool.on('pageerror', (error) => errors.push(kind + ': ' + error.message));
    await tool.goto(
      base +
        '/projects/one/?window=' +
        kind +
        '&context=' +
        encodeURIComponent(JSON.stringify(route))
    );
    try {
      await tool.locator(selector).waitFor({ timeout: 12000 });
      assert.equal(await tool.locator('.dock-workspace').count(), 0, kind);
      assert.equal(await tool.locator('.workspace-main').count(), 0, kind);
      assert.equal(
        await tool
          .locator('.window-page-root > header .app-window-separate')
          .count(),
        0,
        kind
      );
      assert.equal(
        await tool.locator('.window-page-root > .app-window-resize').count(),
        0,
        kind
      );
      const rect = await tool.locator('.window-page-root').boundingBox();
      assert.equal(Math.round(rect.width), 1440, kind);
      await tool.screenshot({ path: output + '/' + kind + '-page.png' });
      console.log(kind + ': separate page passed');
    } catch (error) {
      await tool.screenshot({ path: output + '/' + kind + '-failure.png' });
      console.log((await tool.locator('body').innerText()).slice(0, 1200));
      throw error;
    }
    tool.on('dialog', (dialog) => dialog.accept());
    await tool.close({ runBeforeUnload: false });
  }
  assert.deepEqual(errors, []);
  // Unknown window kinds and inaccessible projects never restore the workspace.
  for (const address of [
    '?window=not-a-window',
    '?window=messages&context=%7Bbroken',
    '/projects/missing/?window=messages'
  ]) {
    const bad = await context.newPage();
    await bad.goto(
      base + (address.startsWith('/') ? address : '/projects/one/' + address)
    );
    await bad.locator('.window-page-status').waitFor();
    assert.equal(await bad.locator('.workspace-main').count(), 0);
    await bad.close();
  }
  const sessionPage = await context.newPage();
  await sessionPage.goto(base + '/projects/one/?window=messages');
  await sessionPage.locator('.window-page-root[open]').waitFor();
  await child.evaluate(() => localStorage.removeItem('tactic_stream.session'));
  await sessionPage.locator('input[type=password]').waitFor();
  assert.equal(await sessionPage.locator('.messages-dialog').count(), 0);
  await sessionPage.close();
  await child.close();
  await context.close();

  console.log(
    'Standalone Messages: real separate page, captured chat/draft, no opener/ticket URL/background queries, reload after owner close and preserved workspace passed'
  );
} finally {
  await browser.close();
}
