import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  colorScheme: 'dark'
});
const page = await context.newPage();
let capturePage = page;
page.setDefaultTimeout(10000);
const errors = [],
  suggestions = [],
  queries = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('status of 500'))
    errors.push(message.text());
});
page.on('request', (request) => {
  if (request.url().endsWith('/admin/search-configuration/suggestions'))
    suggestions.push(request.postDataJSON());
  if (request.url().endsWith('/admin/search-configuration/query'))
    queries.push(request.postDataJSON());
});
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false'
  );
const field = page.getByRole('combobox', {
  name: 'Search objects',
  exact: true
});
const popup = page.locator('.search-suggestions:popover-open');
const rows = popup.locator('[role="row"]');
const range = page.locator(
  '.workspace-footer [data-frame="searchResultCount"]'
);
async function navigate(type) {
  await page.locator('.navigation-toggle').click();
  await page
    .locator(`.type-list button[data-search-type="${type}"]`)
    .last()
    .click();
  await ready();
}
async function suggest(text) {
  await page.mouse.move(1400, 900);
  const response = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/suggestions')
  );
  await field.fill(text);
  await response;
  await popup.waitFor();
}
async function choose(action, total) {
  const response = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/query')
  );
  await action();
  await response;
  await ready();
  assert.match(await range.innerText(), new RegExp('of ' + total + '$'));
  assert.equal(await popup.count(), 0);
}
try {
  await page.goto(
    process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ready();
  await selectProject(page, 'search_browser');
  await page
    .getByRole('heading', { name: 'No Search Type open', exact: true })
    .waitFor();
  await navigate('contract/browser_suggestions');
  const initialQueries = queries.length,
    initialReads = suggestions.length;
  await field.fill('b');
  await field.fill('bl');
  await suggest('blue');
  assert.equal(
    suggestions.length - initialReads,
    1,
    '180ms debounce combines consecutive edits'
  );
  assert.equal(
    queries.length,
    initialQueries,
    'Typing does not execute the main search'
  );
  assert.equal(
    await rows.count(),
    2,
    'Duplicate title/description/keyword combinations are collapsed'
  );
  assert.match(
    await rows.first().innerText(),
    /Blue.*First description.*#sky-blue/s
  );
  const bounds = await popup.boundingBox(),
    input = await field.locator('..').boundingBox();
  assert(Math.abs(bounds.width - input.width) <= 1);
  assert(bounds.x >= 0 && bounds.x + bounds.width <= 1440);
  await field.press('ArrowDown');
  assert.match(await field.getAttribute('aria-activedescendant'), /-0$/);
  await field.press('ArrowUp');
  assert.match(await field.getAttribute('aria-activedescendant'), /-1$/);
  if (process.argv[3])
    await page.screenshot({ path: process.argv[3], animations: 'disabled' });
  await choose(() => field.press('Enter'), 1);
  assert.equal(await field.inputValue(), 'Blue Extra');
  const restoredTab = await page
    .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
    .getAttribute('data-tab-id');
  assert.equal(
    new URL(page.url()).searchParams.has('tab'),
    false,
    'Internal tab IDs stay out of the shared address'
  );
  await page.reload();
  await ready();
  assert.equal(new URL(page.url()).searchParams.has('tab'), false);
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
      .getAttribute('data-tab-id'),
    restoredTab
  );
  assert.match(await range.innerText(), /of 1$/);
  const exact = queries.at(-1).filters.filter(Array.isArray);
  assert(
    exact.every((filter) => filter[1] === '='),
    'Exact suggestion search survives reload'
  );
  await page.locator('summary[aria-label="Sort by"]').click();
  await page
    .getByRole('button', { name: 'Sort by column', exact: true })
    .click();
  await page
    .getByRole('combobox', { name: 'Sort by', exact: true })
    .selectOption('code');
  await page.getByRole('button', { name: 'Ascending', exact: true }).click();
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  await ready();
  await page.locator('.search-quick-filters > summary:visible').click();
  await page.getByText('Filter by field', { exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Filter field', exact: true })
    .selectOption('code');
  await page.getByLabel('Filter value', { exact: true }).fill('AB');
  await choose(
    () =>
      page.getByRole('button', { name: 'Apply filters', exact: true }).click(),
    1
  );
  const exactAddress = page.url();
  await page.reload();
  await ready();
  assert.deepEqual(queries.at(-1).order_bys, ['code desc']);
  assert(
    queries
      .at(-1)
      .filters.some(
        (filter) =>
          Array.isArray(filter) && filter[0] === 'code' && filter[2] === 'AB'
      )
  );
  assert.equal(new URL(page.url()).pathname, '/projects/search_browser/');
  assert.equal(new URL(page.url()).searchParams.has('tab'), false);
  await page.goto(exactAddress);
  await ready();
  assert.match(await range.innerText(), /of 1$/);
  assert.equal(new URL(page.url()).searchParams.has('tab'), false);
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
      .getAttribute('data-tab-id'),
    restoredTab
  );
  await page.locator('.search-quick-filters > summary:visible').click();
  await page.getByText('Filter by field', { exact: true }).click();
  await page.getByLabel('Filter value', { exact: true }).fill('');
  await choose(
    () =>
      page.getByRole('button', { name: 'Apply filters', exact: true }).click(),
    1
  );
  await suggest('blue');
  await choose(
    () =>
      rows.first().getByRole('button', { name: 'Blue', exact: true }).click(),
    2
  );
  await suggest('blue');
  const tabsBefore = await page
    .locator('.workspace-tabs[data-kind="search"] [role="tab"]')
    .count();
  await choose(
    () =>
      rows
        .first()
        .getByRole('button', { name: 'Open Blue in new tab', exact: true })
        .click(),
    1
  );
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [role="tab"]')
      .count(),
    tabsBefore + 1
  );
  assert.equal(
    await page
      .locator(
        '.workspace-tabs[data-kind="search"] [role="tab"][aria-selected="true"]'
      )
      .getAttribute('aria-label'),
    'Blue'
  );
  assert.deepEqual(
    queries.at(-1).records.map((row) => [row.column, row.relation, row.value]),
    [['code', '=', 'A']],
    'New tab uses exact stable code, not contains'
  );
  const blueTab = await page
    .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
    .getAttribute('data-tab-id');
  await suggest('blue');
  await choose(
    () =>
      rows
        .nth(1)
        .getByRole('button', { name: 'Blue Extra', exact: true })
        .click({ button: 'middle' }),
    1
  );
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [role="tab"]')
      .count(),
    tabsBefore + 2
  );
  assert.equal(
    await page
      .locator(
        '.workspace-tabs[data-kind="search"] [role="tab"][aria-selected="true"]'
      )
      .getAttribute('aria-label'),
    'Blue Extra'
  );
  const extraTab = await page
    .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
    .getAttribute('data-tab-id');
  assert.notEqual(blueTab, extraTab);
  await page.goBack();
  await page.waitForFunction(
    (id) =>
      document
        .querySelector(
          '.workspace-tabs[data-kind="search"] [aria-selected="true"]'
        )
        ?.getAttribute('data-tab-id') === id,
    blueTab
  );
  await ready();
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
      .getAttribute('data-tab-id'),
    blueTab
  );
  assert.match(await range.innerText(), /of 1$/);
  await page.goForward();
  await page.waitForFunction(
    (id) =>
      document
        .querySelector(
          '.workspace-tabs[data-kind="search"] [aria-selected="true"]'
        )
        ?.getAttribute('data-tab-id') === id,
    extraTab
  );
  await ready();
  assert.equal(
    await page
      .locator('.workspace-tabs[data-kind="search"] [aria-selected="true"]')
      .getAttribute('data-tab-id'),
    extraTab
  );
  await page.setViewportSize({ width: 1440, height: 430 });
  await suggest('item');
  assert.equal(await rows.count(), 20);
  await field.press('ArrowUp');
  assert(
    await popup.evaluate((node) => node.scrollTop > 0),
    'Keyboard scrolls to the last row'
  );
  await field.press('Escape');
  assert.equal(await field.inputValue(), 'item');
  assert.equal(await popup.count(), 0);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await suggest('azure');
  assert.equal(await rows.count(), 1);
  await field.press('Escape');
  const failure = async (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Suggestion test failure' })
    });
  await page.route('**/admin/search-configuration/suggestions', failure);
  await suggest('failed');
  await popup
    .getByRole('status')
    .filter({ hasText: 'Suggestion test failure' })
    .waitFor();
  assert.equal(await field.inputValue(), 'failed');
  await page.unroute('**/admin/search-configuration/suggestions', failure);
  let captured, release;
  const arrived = new Promise((resolve) => (captured = resolve)),
    held = new Promise((resolve) => (release = resolve));
  const delayed = async (route) => {
    const response = await route.fetch();
    captured();
    await held;
    await route.fulfill({ response });
  };
  await page.route('**/admin/search-configuration/suggestions', delayed);
  await field.fill('blue');
  await arrived;
  await navigate('sthpw/project');
  const settled = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/suggestions')
  );
  release();
  await settled;
  await page.unroute('**/admin/search-configuration/suggestions', delayed);
  await field.focus();
  assert.equal(
    await popup.count(),
    0,
    'Late result cannot reopen in another search type'
  );
  await navigate('contract/browser_suggestions');
  const touch = await browser.newContext({
    viewport: { width: 320, height: 740 },
    hasTouch: true,
    isMobile: true,
    colorScheme: 'dark',
    storageState: await context.storageState()
  });
  const mobile = await touch.newPage();
  mobile.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('status of 500'))
      errors.push(message.text());
  });
  capturePage = mobile;
  mobile.on('pageerror', (error) => errors.push(error.message));
  await mobile.goto(process.argv[2] + '/');
  await mobile.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false',
    null,
    { timeout: 10000 }
  );
  await mobile.getByRole('button', { name: 'Open search', exact: true }).tap();
  const mobileField = mobile.getByRole('combobox', {
    name: 'Search objects',
    exact: true
  });
  assert(
    (await mobileField.locator('..').boundingBox()).width >= 100,
    'Compact actions leave room for the primary search'
  );
  assert.equal(
    await mobile.locator('button[aria-label="Script shelf"]:visible').count(),
    0,
    'The phone does not expose desktop script tools'
  );
  await mobileField.tap();
  await mobileField.fill('blue');
  const mobilePopup = mobile.locator('.search-suggestions:popover-open');
  await mobilePopup.waitFor();
  const mobileBounds = await mobilePopup.boundingBox(),
    area = await mobile.locator('.workspace-browser').boundingBox();
  assert(
    mobileBounds.x >= area.x &&
      mobileBounds.x + mobileBounds.width <= 320 &&
      mobileBounds.y + mobileBounds.height <= 740
  );
  if (process.argv[3])
    await mobile.screenshot({
      path: process.argv[3].replace('.png', '-mobile.png'),
      animations: 'disabled'
    });
  const mobileQuery = mobile.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/query')
  );
  await mobilePopup
    .getByRole('button', { name: 'Open Blue in new tab', exact: true })
    .tap();
  assert.equal((await (await mobileQuery).json()).result.total, 1);
  await mobile.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false',
    null,
    { timeout: 10000 }
  );
  assert(
    await mobile.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  );
  await touch.close();
  assert.deepEqual(errors, []);
  console.log(
    'Search suggestions: debounce, projection, exact search, keyboard, new tabs, persistence, stale/error responses and touch passed'
  );
} catch (error) {
  console.error('Browser errors:', errors);
  console.error(
    'Workspace state:',
    await capturePage.evaluate(() => {
      const app =
        document.querySelector('#app').__vue_app__._container._vnode.component
          .subTree.component.subTree.component.proxy;
      return {
        busy: app.busy,
        requestId: app.requestId,
        error: app.error,
        activeTab: app.activeSearchTab?.id,
        displayedTab: app.searchStateTab?.id,
        loaded: app.activeSearchTab?.loaded,
        loadedQuery: app.loadedQuery,
        rows: app.rows.length,
        tabMode: app.activeSearchTab?.loadingMode,
        mode: app.loadingMode
      };
    })
  );
  if (process.argv[3])
    await capturePage.screenshot({
      path: process.argv[3].replace('.png', '-failure.png')
    });
  throw error;
} finally {
  await browser.close();
}
