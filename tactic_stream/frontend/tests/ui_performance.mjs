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
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
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
  const dialog = page.getByRole('dialog', {
    name: 'UI responsiveness',
    exact: true
  });
  const open = async () => {
    await page.locator('.settings-menu > summary').click();
    await page
      .locator('.settings-menu')
      .getByRole('button', { name: 'UI responsiveness', exact: true })
      .click();
    await dialog.waitFor();
  };
  const count = async () =>
    Number(
      (
        await dialog.locator('[data-frame="performanceSummary"]').textContent()
      ).match(/Samples: (\d+)/)[1]
    );
  await open();
  assert.equal(await count(), 0, 'Measurements are paused by default');
  assert(
    await dialog
      .getByRole('button', { name: 'Resume measurements', exact: true })
      .locator('span')
      .evaluate((node) => node.scrollWidth <= node.clientWidth),
    'Primary recording caption stays readable'
  );
  await dialog
    .getByRole('button', { name: 'Resume measurements', exact: true })
    .click();
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(
    () =>
      document.querySelector('.settings-menu > summary') ===
      document.activeElement
  );

  const delay = async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 180));
    await route.fallback();
  };
  await page.route('**/admin/search-configuration/query', delay);
  await page
    .locator('.search-header button[aria-label="Refresh"]:visible')
    .click();
  await ready();
  await page.unroute('**/admin/search-configuration/query', delay);
  await page.getByLabel('Add new search tab', { exact: true }).click();
  await ready();
  await page
    .locator('.workspace-tabs[data-kind="search"] [role="tab"]')
    .first()
    .click();
  await ready();
  await open();
  await dialog
    .getByRole('button', { name: 'Pause measurements', exact: true })
    .click();
  await page.waitForTimeout(180);
  await page.evaluate(() => {
    document.execCommand = (command) => {
      if (command !== 'copy') return false;
      window.copiedUiMeasurements = document.activeElement.value;
      return true;
    };
  });
  await dialog.getByLabel('Copy measurements', { exact: true }).click();
  let records = JSON.parse(
    await page.evaluate(() => window.copiedUiMeasurements)
  );
  const query = records
    .filter((sample) => sample.action === 'Load search results')
    .find((sample) => sample.handlerMs > 150);
  assert(query, 'The named operation includes the real delayed request');
  assert(
    query.readyMs >= query.handlerMs && query.readyMs > query.frameMs + 100
  );
  assert.equal(query.status, 'Browser frame');
  assert(JSON.parse(query.details).requestAndSchemaMs > 150);
  assert(
    records.some(
      (sample) =>
        sample.action.startsWith('Search tab: ') &&
        sample.readyMs >= 0 &&
        JSON.parse(sample.details).cached === true
    )
  );
  assert(
    records.some(
      (sample) => sample.action === 'Pointer press' && sample.readyMs === -1
    )
  );
  const ticket = await page.evaluate(
    () =>
      JSON.parse(
        sessionStorage.getItem('tactic_stream.session') ||
          localStorage.getItem('tactic_stream.session')
      ).ticket
  );
  assert(
    !JSON.stringify(records).includes(ticket) &&
      !JSON.stringify(records).includes(process.env.STREAM_CHECK_PASSWORD)
  );
  await dialog
    .locator('[data-frame="uiPerformanceSamples"]')
    .evaluate((node, index) => {
      node.scrollTop = index * 58;
      node.dispatchEvent(new Event('scroll'));
    }, records.indexOf(query));
  await dialog
    .getByRole('option', { name: 'Load search results', exact: true })
    .first()
    .click();
  const details = dialog.getByLabel('Measurement details', { exact: true });
  assert((await details.inputValue()).includes('requestAndSchemaMs'));
  const row = dialog
    .getByRole('option', { name: 'Load search results', exact: true })
    .first();
  assert.equal((await row.boundingBox()).height, 54);
  assert.equal(
    await row.evaluate((node) => getComputedStyle(node).fontWeight),
    '400'
  );
  assert.equal((await details.boundingBox()).height, 95);
  const columns = await row
    .locator(
      '[data-frame="handlerMs"], [data-frame="frameMs"], [data-frame="readyMs"]'
    )
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const box = node.getBoundingClientRect();
        return { x: box.x, width: box.width };
      })
    );
  assert.equal(columns.length, 3);
  assert(columns.every((column) => column.width === 88));
  assert.equal(columns[1].x - columns[0].x, 96);
  assert.equal(Math.round((await dialog.boundingBox()).width), 1008);
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-ui-performance.png',
    animations: 'disabled'
  });
  const paused = await count();
  await row.press('Home');
  await dialog.getByRole('option').first().press('ArrowDown');
  assert.equal(
    await dialog.getByRole('option').nth(1).getAttribute('aria-selected'),
    'true'
  );
  await page.keyboard.press('Escape');
  await page.locator('.navigation-toggle').click();
  await page.keyboard.press('Escape');
  await open();
  assert.equal(
    await count(),
    paused,
    'Pause stops collecting inputs and operations'
  );
  await dialog.getByLabel('Clear measurements', { exact: true }).click();
  assert.equal(await count(), 0);
  await dialog.getByLabel('Copy measurements', { exact: true }).click();
  assert.equal(await page.evaluate(() => window.copiedUiMeasurements), '[]');

  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      ),
      true
    );
    const bounds = await dialog.boundingBox();
    assert(bounds.x >= 0 && bounds.x + bounds.width <= width);
    assert(
      (
        await dialog
          .locator('[data-frame="uiPerformanceSamples"]')
          .boundingBox()
      ).height >=
        2 * 58,
      'Phone retains at least two measurement rows beside its diagnostics and details'
    );
    for (const label of [
      'Resume measurements',
      'Copy measurements',
      'Clear measurements'
    ])
      assert(await dialog.getByLabel(label, { exact: true }).isVisible());
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-ui-performance-${width}.png`,
      animations: 'disabled'
    });
  }
  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('.appearance-controls > summary').click();
  await page
    .getByLabel('Interface language', { exact: true })
    .selectOption('ru');
  await page.keyboard.press('Escape');
  await page.locator('.settings-menu > summary').click();
  await page
    .getByRole('button', { name: 'Отзывчивость интерфейса', exact: true })
    .click();
  const russian = page.getByRole('dialog', {
    name: 'Отзывчивость интерфейса',
    exact: true
  });
  await russian
    .getByRole('button', { name: 'Продолжить замеры', exact: true })
    .waitFor();
  assert.match(
    await russian.getByLabel('Детали измерения', { exact: true }).inputValue(),
    /Выберите замер/
  );
  await russian
    .getByRole('button', { name: 'Продолжить замеры', exact: true })
    .click();
  await page.keyboard.press('Escape');
  await page.locator('.appearance-controls > summary').click();
  await page.getByLabel('Язык интерфейса', { exact: true }).selectOption('en');
  await page.keyboard.press('Escape');
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
    await count(),
    0,
    'Signing out resets measurements and their recording state'
  );
  await dialog
    .getByRole('button', { name: 'Resume measurements', exact: true })
    .waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'PASS: LAN HTTP, opt-in measurements, async ready frame, cached tab, privacy, native geometry, pause/copy/clear, keyboard, mobile, EN/RU and signout cleanup'
  );
} finally {
  await browser.close();
}
