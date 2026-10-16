import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    colorScheme: 'dark'
  });
  page.setDefaultTimeout(12000);
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.route('http://tactic-stream.test/**', async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      response: await route.fetch({
        url: process.argv[2] + url.pathname + url.search,
        headers: {
          ...route.request().headers(),
          origin: process.argv[2],
          referer: process.argv[2] + '/'
        }
      })
    });
  });
  await page.goto(
    'http://tactic-stream.test/projects/one/?search_type=contract/entity&view=table'
  );
  assert.equal(await page.evaluate(() => isSecureContext), false);
  await page.getByRole('button', { name: 'Help', exact: true }).click();
  await page.locator('dialog.help-view').waitFor();
  await page.getByRole('button', { name: 'Close help', exact: true }).click();
  await page.getByRole('button', { name: 'Debug Log', exact: true }).click();
  await page.getByRole('dialog', { name: 'Debug Log', exact: true }).waitFor();
  await page
    .getByRole('button', { name: 'Close Debug Log', exact: true })
    .click();
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const ready = () =>
    page.waitForFunction(
      () =>
        document
          .querySelector('.workspace-results')
          ?.getAttribute('aria-busy') === 'false'
    );
  await ready();
  const log = page.getByRole('dialog', { name: 'Debug Log', exact: true });
  const open = async () => {
    await page.locator('.settings-menu > summary').click();
    await page.getByRole('button', { name: 'Debug Log', exact: true }).click();
    await log.waitFor();
  };
  const configure = async () => {
    await page.locator('.settings-menu > summary').click();
    await page
      .getByRole('button', { name: 'Configuration', exact: true })
      .click();
    await page
      .getByRole('navigation', { name: 'Configuration sections' })
      .getByRole('button', { name: 'Global', exact: true })
      .click();
  };
  await open();
  assert.equal(
    await log
      .locator('[data-frame="eventLevelText"]')
      .filter({ hasText: /^API$/ })
      .count(),
    0,
    'Successful API calls are not recorded by default'
  );
  await log.getByLabel('Clear session', { exact: true }).click();
  await page.waitForFunction(
    () => !document.querySelector('[data-frame^="debugEvent_"]')
  );
  await page.keyboard.press('Escape');
  const ticket = await page.evaluate(
    () =>
      JSON.parse(
        sessionStorage.getItem('tactic_stream.session') ||
          localStorage.getItem('tactic_stream.session')
      ).ticket
  );
  let failedRequests = 0;
  const failure = (route) => {
    failedRequests++;
    return route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({
        error:
          'Request failed: ' +
          ticket +
          ' / ' +
          process.env.STREAM_CHECK_PASSWORD
      })
    });
  };
  await page.route('**/admin/search-configuration/query', failure);
  await page
    .locator('.search-header button[aria-label="Refresh"]:visible')
    .click();
  await ready();
  await page.unroute('**/admin/search-configuration/query', failure);
  await open();
  assert.equal(failedRequests, 1, 'The real search failure is recorded once');
  await log
    .getByRole('listbox', { name: 'Debug events' })
    .getByRole('option')
    .first()
    .click();
  const detail = await log
    .locator('[data-frame="debugDetailContent"]')
    .evaluate((node) =>
      [...node.querySelectorAll('textarea')]
        .map((field) => field.value)
        .join('\n')
    );
  assert(detail.includes('Request failed:'));
  assert(
    !detail.includes(ticket) &&
      !detail.includes(process.env.STREAM_CHECK_PASSWORD),
    'Request, response, traceback and command redact credentials'
  );
  await page.evaluate(() => {
    document.execCommand = (command) => {
      if (command !== 'copy') return false;
      window.copiedDebugText = document.activeElement.value;
      return true;
    };
  });
  await log.getByLabel('Copy runtime command', { exact: true }).click();
  assert(
    (await page.evaluate(() => window.copiedDebugText)).includes(
      'from urllib.request import'
    )
  );
  assert(
    (await page.evaluate(() => window.copiedDebugText)).includes('<REDACTED>')
  );
  await page.keyboard.press('Escape');
  await configure();
  await page.getByRole('checkbox', { name: 'Record API', exact: true }).check();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await page
    .getByRole('dialog', { name: 'Unsaved changes', exact: true })
    .getByRole('button', { name: 'Discard changes', exact: true })
    .click();
  await configure();
  assert.equal(
    await page
      .getByRole('checkbox', { name: 'Record API', exact: true })
      .isChecked(),
    false,
    'Cancel reverts unapplied recording settings'
  );
  await page.getByRole('checkbox', { name: 'Record API', exact: true }).check();
  await page.getByLabel('Save configuration', { exact: true }).click();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await page
    .locator('.search-header button[aria-label="Refresh"]:visible')
    .click();
  await ready();
  await open();
  assert(
    (await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count()) > 1
  );
  await log.getByRole('checkbox', { name: 'API', exact: true }).click();
  assert.equal(
    await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count(),
    1,
    'Level filters only change presentation'
  );
  await log.getByRole('checkbox', { name: 'API', exact: true }).click();
  await log
    .getByLabel('Search debug log', { exact: true })
    .fill('no-such-event');
  assert.equal(
    await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count(),
    0
  );
  await log.getByLabel('Search debug log', { exact: true }).fill('');
  await log
    .getByRole('navigation', { name: 'Sources' })
    .getByRole('button', { name: 'api.js', exact: true })
    .click();
  assert(
    (await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count()) > 0
  );
  const splitter = log.getByRole('separator', { name: 'Sources panel width' });
  const width = Number(await splitter.getAttribute('aria-valuenow'));
  await splitter.focus();
  await splitter.press('ArrowRight');
  assert.equal(
    Number(await splitter.getAttribute('aria-valuenow')),
    width + 10
  );
  await splitter.press('ArrowLeft');

  const huge = 'Large result: ' + 'Текст\n'.repeat(3000);
  const fixture = [
    {
      id: 1,
      t: '2026-10-08T15:24:09.619',
      l: 'API',
      m: 'query',
      o: 'api.js',
      f: 'query',
      g: 'admin/rpc',
      s: 'TACTIC API',
      d: 0.125,
      z: 4.5,
      e: huge,
      c: 'from urllib.request import urlopen\nprint("Example")'
    },
    {
      id: 2,
      t: '2026-10-08T15:24:09.619',
      l: 'ERROR',
      m: 'Example request failed',
      o: 'api.js',
      f: 'query',
      g: 'admin/rpc',
      s: 'TACTIC API',
      x: 'ValueError: Example request failed'
    }
  ];
  const jsonl =
    JSON.stringify({ v: 1 }) +
    '\n' +
    fixture.map((record) => JSON.stringify(record)).join('\n') +
    '\n';
  await log.locator('input[type="file"]').setInputFiles({
    name: 'handler-session.jsonl',
    mimeType: 'application/x-ndjson',
    buffer: Buffer.from(jsonl)
  });
  await log
    .getByRole('listbox', { name: 'Debug events' })
    .getByRole('option')
    .first()
    .click();
  assert.equal(
    await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count(),
    2
  );
  assert(
    (await log.locator('[data-frame="debugDetails"]').inputValue()).includes(
      huge
    ),
    'Large native results remain complete'
  );
  const scroll = await log
    .locator('[data-frame="debugDetailContent"]')
    .evaluate((node) => [node.scrollHeight, node.clientHeight]);
  assert(scroll[0] > scroll[1]);
  const downloadPromise = page.waitForEvent('download');
  await log.getByLabel('Download debug session', { exact: true }).click();
  const download = await downloadPromise,
    stream = await download.createReadStream(),
    chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  const exported = Buffer.concat(chunks).toString();
  assert(exported.includes(huge.replaceAll('\n', '\\n')));
  assert(
    !exported.includes(ticket) &&
      !exported.includes(process.env.STREAM_CHECK_PASSWORD)
  );
  await log.getByLabel('Search debug log', { exact: true }).fill('');
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-debug-log.png'
  });
  await log.locator('input[type="file"]').setInputFiles({
    name: 'invalid.jsonl',
    mimeType: 'application/x-ndjson',
    buffer: Buffer.from('{"v":9}\n')
  });
  await log
    .getByRole('alert')
    .filter({ hasText: 'Unsupported Debug Log session schema' })
    .waitFor();
  assert.equal(
    await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count(),
    2,
    'Invalid import preserves the loaded session'
  );
  await log.getByLabel('Clear session', { exact: true }).click();
  assert(
    (await log.getByLabel('Debug session', { exact: true }).inputValue()) ===
      '',
    'Clear while viewing history returns to the live session'
  );
  await log
    .getByLabel('Debug session', { exact: true })
    .selectOption({ label: 'handler-session.jsonl' });
  await page.waitForFunction(
    () =>
      document.querySelector('.debug-log-screen')?.getAttribute('aria-busy') ===
      'false'
  );
  await log
    .getByRole('listbox', { name: 'Debug events' })
    .getByRole('option')
    .first()
    .waitFor();
  assert.equal(
    await log
      .getByRole('listbox', { name: 'Debug events' })
      .getByRole('option')
      .count(),
    2,
    'Saved sessions remain unchanged'
  );
  await page.keyboard.press('Escape');
  await page.reload();
  await ready();
  await open();
  await log
    .getByLabel('Debug session', { exact: true })
    .selectOption({ label: 'handler-session.jsonl' });
  await page.waitForFunction(
    () =>
      document.querySelector('.debug-log-screen')?.getAttribute('aria-busy') ===
      'false'
  );
  await log
    .getByRole('listbox', { name: 'Debug events' })
    .getByRole('option')
    .first()
    .click();
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 });
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-debug-log-${width}.png`
    });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      ),
      true
    );
    const geometry = await log.evaluate((node) =>
      Object.fromEntries(
        [
          '.debug-log-screen',
          '[data-frame="debugToolbar"]',
          '[data-frame="debugBody"]',
          '[data-frame="debugEvents"]',
          '[data-frame="debugDetailPanel"]'
        ].map((selector) => [
          selector,
          node.querySelector(selector).getBoundingClientRect().height
        ])
      )
    );
    assert(
      geometry['[data-frame="debugEvents"]'] > 120,
      JSON.stringify(geometry)
    );
    assert.equal(
      await log
        .getByRole('combobox', { name: 'Sources', exact: true })
        .isVisible(),
      true
    );
    await log.getByRole('checkbox', { name: 'API', exact: true }).click();
    assert.equal(
      await log
        .getByRole('listbox', { name: 'Debug events' })
        .getByRole('option')
        .count(),
      1
    );
    await log.getByRole('checkbox', { name: 'API', exact: true }).click();
    await log.getByLabel('Open event details', { exact: true }).click();
    await page
      .getByRole('dialog', { name: 'Event details', exact: true })
      .waitFor();
    await page.keyboard.press('Escape');
    assert.equal(
      await log.isVisible(),
      true,
      'Escape closes owned event details before closing Debug Log'
    );
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-debug-log-${width}.png`
    });
  }
  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByLabel('Account', { exact: true }).click();
  await page.getByRole('button', { name: 'Sign Out', exact: true }).click();
  await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor();
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ready();
  await open();
  assert.equal(
    await log
      .getByLabel('Debug session', { exact: true })
      .locator('option')
      .filter({ hasText: 'handler-session' })
      .count(),
    0,
    'Signing out removes local history'
  );
  assert.deepEqual(pageErrors, []);
  console.log(
    'PASS: insecure HTTP startup, recording settings, error redaction, filters, splitters, native JSONL import/export, session history, copy and mobile layout'
  );
} finally {
  await browser.close();
}
