import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const base = process.argv[2],
  project = process.env.STREAM_CHECK_PROJECT;
import { nativeCases } from './frame_communication_reference.mjs';
const native = nativeCases('notifications').map((row) => ({
  width: row.fixture.width,
  height: row.fixture.height,
  notificationsPanel: row.boxes.notificationsPanel,
  notificationsToolbar: row.boxes.notificationsToolbar
}));
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    colorScheme: 'dark',
    hasTouch: true
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() => {
    if (!localStorage.getItem('tactic_stream.appearance'))
      localStorage.setItem(
        'tactic_stream.appearance',
        JSON.stringify({ mode: 'dark', language: 'en' })
      );
  });
  await page.goto(
    base + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.topbar').waitFor();
  await selectProject(page, project);
  const menu = async (name) => {
    await page.getByLabel('More options', { exact: true }).click();
    await page
      .locator('.settings-menu')
      .getByRole('button', { name, exact: true })
      .click();
  };
  await menu('Save Preferences');
  let message = 'Unable to reach the server.';
  await page.route('**/admin/rpc', (route) =>
    route.request().postDataJSON().method === 'ping'
      ? route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ error: message })
        })
      : route.continue()
  );
  const ping = async () => {
    await page.getByLabel('Connection', { exact: true }).click();
    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().endsWith('/admin/rpc') &&
          response.request().postDataJSON()?.method === 'ping'
      ),
      page.getByRole('button', { name: 'Ping now', exact: true }).click()
    ]);
    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.system-activity-control .busy-indicator.running'
        )
    );
    await page.keyboard.press('Escape');
  };
  await ping();
  await page.getByLabel('System activity', { exact: true }).click();
  const dialog = page.getByRole('dialog', {
    name: 'Notifications',
    exact: true
  });
  const rows = dialog.locator('.system-activity-event'),
    filters = dialog.getByRole('radiogroup');
  await rows.filter({ hasText: 'Preferences saved' }).waitFor();
  await dialog.getByLabel('Maximize window', { exact: true }).click();
  const near = (actual, expected, label, tolerance = 2) =>
    assert(
      Math.abs(actual - expected) <= tolerance,
      `${label}: ${actual} vs Qt ${expected}`
    );
  for (const reference of native) {
    // Match Qt content, accounting for the shared web title bar/border and compact-host margins.
    const phone = reference.width <= 700;
    await page.setViewportSize({
      width: reference.width + (phone ? 0 : 2),
      height: reference.height + (phone ? 40 : 42)
    });
    await page.waitForFunction(
      (width) =>
        document.querySelector('.system-activity-content')?.clientWidth ===
        width,
      reference.width
    );
    const compact = reference.width < 760;
    await page.waitForFunction(
      (compact) =>
        !!document.querySelector(
          '.system-activity-dialog [role="radio"].icon-button'
        ) === compact,
      compact
    );
    const panel = dialog.locator('.activity-feed-panel'),
      toolbar = dialog.locator('.activity-feed-toolbar');
    near(
      (await panel.boundingBox()).width,
      reference.notificationsPanel.width,
      'Panel width'
    );
    near(
      (await toolbar.boundingBox()).width,
      reference.notificationsToolbar.width,
      'Toolbar width'
    );
    near(
      (await toolbar.boundingBox()).height,
      reference.notificationsToolbar.height,
      'Toolbar height'
    );
    const row = rows.filter({ hasText: 'Preferences saved' });
    const bounds = await row.boundingBox(),
      title = await row.locator('strong').boundingBox(),
      stamp = await row.locator('time').boundingBox();
    assert(bounds.width > 200 && bounds.height >= 45);
    assert(
      bounds.width < 620 ? stamp.y > title.y : Math.abs(stamp.y - title.y) < 1
    );
    const rail = await row
      .locator('[data-frame=notificationRowRail]')
      .boundingBox();
    assert.equal(rail.width, 3);
    assert(
      rail.y >= bounds.y && rail.y + rail.height <= bounds.y + bounds.height
    );
    assert(
      (await row.locator('time').getAttribute('title')) !==
        (await row.locator('time').getAttribute('datetime'))
    );
    assert.equal(
      await filters.locator('button > span:not(.app-icon)').count(),
      compact ? 0 : 4
    );
    assert.equal(await filters.locator('.app-icon').count(), 4);
    const serverFilter = filters.getByRole('radio', {
      name: 'Server',
      exact: true
    });
    assert.equal(await serverFilter.getAttribute('aria-label'), 'Server');
    if (compact) {
      await serverFilter.hover();
      await page
        .getByRole('tooltip', { name: 'Server', exact: true })
        .waitFor();
      await page.mouse.move(0, 0);
    }
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      )
    );
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-notification-history-${reference.width}.png`,
      animations: 'disabled'
    });
  }
  await filters
    .getByRole('radio', { name: 'Client', exact: true })
    .press('Home');
  assert.equal(
    await filters
      .getByRole('radio', { name: 'All', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );
  await filters.getByRole('radio', { name: 'Check-in', exact: true }).tap();
  assert.equal(await rows.count(), 0);
  const empty = dialog.locator('.system-activity-empty');
  assert.equal(
    await empty
      .locator('.app-icon')
      .evaluate((node) => getComputedStyle(node).fontSize),
    '30px'
  );
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-notification-history-empty-320.png',
    animations: 'disabled'
  });
  await dialog.getByLabel('Close Notifications', { exact: true }).tap();
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (let index = 0; index < 14; index++) {
    message = 'History event ' + index;
    await ping();
  }
  message =
    'Long server message\n' +
    'Select this diagnostic text. '.repeat(16) +
    '\nhttps://example.com/help <img src=x onerror=alert(1)>';
  await ping();
  await page.getByLabel('System activity', { exact: true }).click();
  await filters.getByRole('radio', { name: 'All', exact: true }).click();
  const scroll = dialog.locator('.system-activity-history');
  await rows.filter({ hasText: 'Long server message' }).waitFor();
  assert(
    await scroll.evaluate((node) => node.scrollHeight > node.clientHeight)
  );
  assert.equal(await rows.locator('img').count(), 0);
  assert.equal(
    await rows
      .getByRole('link', { name: 'https://example.com/help', exact: true })
      .getAttribute('rel'),
    'noopener noreferrer'
  );
  assert.notEqual(
    await rows
      .locator('strong')
      .first()
      .evaluate((node) => getComputedStyle(node).userSelect),
    'none'
  );
  await scroll.hover();
  await page.mouse.wheel(0, 600);
  await page.waitForFunction(
    () => document.querySelector('.system-activity-history').scrollTop > 0
  );
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 });
    await page.waitForFunction(
      (node) => node.scrollWidth <= node.clientWidth,
      await dialog.elementHandle()
    );
    assert(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)
    );
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      )
    );
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-notification-history-touch-${width}.png`,
      animations: 'disabled'
    });
  }
  await dialog.getByLabel('Clear history', { exact: true }).click();
  assert.equal(await rows.count(), 0);
  assert(
    await dialog.getByLabel('Clear history', { exact: true }).isDisabled()
  );
  await dialog.getByLabel('Close Notifications', { exact: true }).click();
  await page.unroute('**/admin/rpc');
  await page.evaluate(() => {
    const settings = JSON.parse(
      localStorage.getItem('tactic_stream.appearance')
    );
    settings.language = 'ru';
    settings.mode = 'light';
    localStorage.setItem('tactic_stream.appearance', JSON.stringify(settings));
  });
  await page.reload();
  await page.locator('.topbar').waitFor();
  await page.waitForFunction(
    () =>
      !document.querySelector(
        '.system-activity-control .busy-indicator.running'
      )
  );
  const ru = JSON.parse(
    readFileSync(new URL('../src/locales/ru.json', import.meta.url))
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByLabel(ru['More options'], { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: ru['Save Preferences'], exact: true })
    .click();
  await page.getByLabel(ru['System activity'], { exact: true }).click();
  const russian = page.getByRole('dialog', {
    name: ru['Notifications'],
    exact: true
  });
  await russian
    .locator('.system-activity-event')
    .getByText(ru['Preferences saved'], { exact: true })
    .waitFor();
  assert(
    (
      await russian
        .locator('.system-activity-event')
        .filter({ hasText: ru['Preferences saved'] })
        .locator('time')
        .getAttribute('title')
    ).includes('октября')
  );
  await page.setViewportSize({ width: 320, height: 740 });
  await page.waitForFunction(
    (node) => node.scrollWidth <= node.clientWidth,
    await russian.elementHandle()
  );
  assert.equal(await russian.getByRole('radio').count(), 4);
  assert(
    await russian.evaluate((node) => node.scrollWidth <= node.clientWidth)
  );
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-notification-history-ru-light-320.png',
    animations: 'disabled'
  });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: fresh Frame window geometry, window/row thresholds, compact tooltips, keyboard filters, full dates, empty state, selectable safe links, scrolling and clear'
  );
} finally {
  await browser.close();
}
