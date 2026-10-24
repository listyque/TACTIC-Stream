import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';
const browser = await chromium.launch({ headless: true }),
  page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    colorScheme: 'dark'
  });
page.setDefaultTimeout(12000);
const errors = [],
  suggestions = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/search-configuration/suggestions'))
    suggestions.push(request.postDataJSON());
});
const library = page.getByRole('region', {
    name: 'Advanced Search',
    exact: true
  }),
  nameDialog = page.locator('.search-preset-name-dialog');
async function open() {
  await page.getByLabel('Search filters and presets', { exact: true }).click();
  await page
    .getByRole('button', { name: 'Advanced Search', exact: true })
    .click();
  await library
    .getByRole('combobox', { name: 'Select a saved search' })
    .waitFor();
}
async function more(command) {
  await library
    .getByRole('button', { name: 'Saved search actions', exact: true })
    .click();
  await page.getByRole('button', { name: command, exact: true }).click();
}
async function title(value) {
  await nameDialog.getByLabel('Preset name', { exact: true }).fill(value);
  const response = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/save')
  );
  await nameDialog.getByRole('button', { name: 'Save', exact: true }).click();
  await response;
  await nameDialog.waitFor({ state: 'hidden' });
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
  await selectProject(page, 'library_browser');
  await page.locator('.navigation-toggle').click();
  await page
    .locator('.type-list [data-search-type="library_browser/items"]')
    .last()
    .click();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page
    .getByRole('menuitemradio', { name: 'Continuous tree', exact: true })
    .click();
  await open();
  assert.equal(
    await library
      .getByRole('button', { name: 'Add filter', exact: true })
      .count(),
    2
  );
  await library
    .getByRole('combobox', { name: 'Filter column', exact: true })
    .selectOption('code');
  const value = library.getByRole('combobox', {
    name: 'Filter value',
    exact: true
  });
  await value.fill('O');
  await value.fill('ON');
  await value.fill('ONE');
  await page.getByRole('option', { name: 'ONE', exact: true }).waitFor();
  await value.press('ArrowDown');
  await page.waitForFunction(() =>
    document
      .querySelector('.condition-value input')
      ?.getAttribute('aria-activedescendant')
  );
  await value.press('Enter');
  assert.equal(await value.inputValue(), 'ONE');
  assert.equal(suggestions.at(-1).column, 'code');
  await library
    .getByRole('button', { name: 'Save as new preset', exact: true })
    .click();
  await title('Only one');
  const choices = library.getByRole('combobox', {
    name: 'Select a saved search',
    exact: true
  });
  assert(
    await choices.locator('option').filter({ hasText: 'Only one' }).count()
  );
  await more('Rename preset');
  assert.equal(
    await nameDialog
      .getByLabel('Preset name', { exact: true })
      .evaluate((node) => node.selectionEnd - node.selectionStart),
    'Only one'.length
  );
  await title('Renamed');
  await more('Duplicate preset');
  await title('Copy one');
  await more('Delete preset');
  await library
    .getByRole('button', { name: 'Delete preset', exact: true })
    .click();
  await choices.selectOption({ label: 'Renamed' });
  const applied = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/query')
  );
  await library
    .getByRole('button', { name: 'Apply filters', exact: true })
    .first()
    .click();
  assert(await library.isVisible(), 'Apply retains the Advanced Search dock');
  assert.equal((await (await applied).json()).result.total, 1);
  await page
    .locator('.workspace-results .result-item-list[data-collection-total="1"]')
    .waitFor();
  await page
    .locator('.workspace-results .result-item-object:visible')
    .filter({ hasText: 'Two object' })
    .waitFor({ state: 'hidden' });
  await page
    .locator('.workspace-results .result-item-object:visible')
    .filter({ hasText: 'One object' })
    .waitFor();
  assert.equal(
    await page
      .locator('.workspace-results .result-item-object:visible')
      .count(),
    1
  );
  await page.reload();
  await page
    .getByLabel('Change search results view', { exact: true })
    .waitFor();
  await page
    .locator('.workspace-results .result-item-object:visible')
    .filter({ hasText: 'One object' })
    .waitFor();
  await open();
  await value.fill('TWO');
  await page
    .locator('[data-dock=advanced_search]')
    .getByRole('button', { name: 'Close panel: Advanced Search', exact: true })
    .click();
  await library.waitFor({ state: 'hidden' });
  await open();
  assert.equal(
    await value.inputValue(),
    'TWO',
    'Closing and reopening a dock retains its draft'
  );
  const advancedPanel = page.locator('[data-dock="advanced_search"]');
  await advancedPanel
    .getByLabel('Panel position: Advanced Search', { exact: true })
    .click();
  await advancedPanel
    .getByRole('button', { name: 'Stack panels', exact: true })
    .click();
  await advancedPanel.getByRole('tab', { name: 'Search', exact: true }).click();
  await page
    .locator('[data-dock="results"]')
    .getByRole('tab', { name: 'Advanced Search', exact: true })
    .click();
  await value.waitFor({ state: 'visible' });
  assert.equal(
    await value.inputValue(),
    'TWO',
    'Reactivating a retained dock keeps its draft'
  );
  await advancedPanel
    .getByLabel('Panel position: Advanced Search', { exact: true })
    .click();
  await advancedPanel
    .getByRole('button', { name: 'Dock right', exact: true })
    .click();
  const originalTab = await page
    .locator(
      '.workspace-tabs[data-kind="search"] [role="tab"][aria-selected="true"]'
    )
    .getAttribute('data-tab-id');
  await page
    .getByRole('button', { name: 'Add new search tab', exact: true })
    .click();
  await open();
  assert.equal(
    await value.inputValue(),
    '',
    'Another tab of the same Search Type has its own draft'
  );
  await value.fill('Independent draft');
  await page
    .locator(
      '.workspace-tabs[data-kind="search"] [data-tab-id="' + originalTab + '"]'
    )
    .click();
  await library
    .getByRole('combobox', { name: 'Filter value', exact: true })
    .waitFor();
  await page.waitForFunction(
    () => document.querySelector('.condition-value input')?.value === 'TWO'
  );
  const lostReply = async (route) => {
    await route.fetch();
    await route.abort('failed');
  };
  await page.route('**/admin/search-configuration/save', lostReply);
  await library
    .getByRole('button', { name: 'Save as new preset', exact: true })
    .click();
  await nameDialog
    .getByLabel('Preset name', { exact: true })
    .fill('Saved despite lost reply');
  await nameDialog.getByRole('button', { name: 'Save', exact: true }).click();
  await library
    .getByText('The save result is unknown. Reload before trying again.', {
      exact: true
    })
    .waitFor();
  assert(
    await nameDialog
      .getByRole('button', { name: 'Save', exact: true })
      .isDisabled(),
    'Unknown writes cannot be repeated'
  );
  await page.unroute('**/admin/search-configuration/save', lostReply);
  await nameDialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await more('Refresh saved searches');
  await library
    .getByRole('button', { name: 'Discard changes', exact: true })
    .click();
  await choices
    .locator('option')
    .filter({ hasText: 'Saved despite lost reply' })
    .waitFor({ state: 'attached' });
  assert.equal(
    await choices
      .locator('option')
      .filter({ hasText: 'Saved despite lost reply' })
      .count(),
    1,
    'A fresh catalog reconciles the committed write'
  );
  await page
    .getByRole('button', { name: 'Add new search tab', exact: true })
    .click();
  await page.locator('.search-quick-filters > summary').click();
  await page
    .locator('.quick-filter-group[aria-label="PROCESSES"]')
    .getByRole('button', { name: 'model', exact: true })
    .click();
  await page.keyboard.press('Escape');
  await open();
  await library
    .getByText('Managed by Quick Filters', { exact: true })
    .waitFor();
  const managed = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/query')
  );
  await library
    .getByRole('button', { name: 'Apply filters', exact: true })
    .first()
    .click();
  const managedResponse = await managed;
  assert.equal((await managedResponse.json()).result.total, 1);
  assert.deepEqual(managedResponse.request().postDataJSON().selections, {
    process: ['model']
  });
  await library
    .getByRole('button', { name: 'Edit as custom filter', exact: true })
    .click();
  const detached = page.waitForResponse((response) =>
    response.url().endsWith('/admin/search-configuration/query')
  );
  await library
    .getByRole('button', { name: 'Apply filters', exact: true })
    .first()
    .click();
  const detachedResponse = await detached;
  assert.equal(
    (await detachedResponse.json()).result.total,
    1,
    'Detaching keeps the executable related-task filter'
  );
  assert.deepEqual(
    detachedResponse.request().postDataJSON().selections,
    {},
    'A detached filter releases quick-chip ownership'
  );
  assert(
    detachedResponse
      .request()
      .postDataJSON()
      .records.some(
        (row) =>
          row.column === '_expression' &&
          row.value.includes("['process', 'model']")
      )
  );
  assert.deepEqual(errors, []);
  console.log(
    'Saved searches: field suggestions, actual create/rename/duplicate/delete, exact apply, reload and dirty/discard passed'
  );
} catch (error) {
  console.error(errors);
  console.error(
    await page
      .locator('.workspace-results .result-item-object:visible')
      .evaluateAll((rows) =>
        rows.map((row) => ({
          text: row.innerText,
          key: row.parentElement?.parentElement?.dataset.collectionKey,
          html: row.outerHTML.slice(0, 600)
        }))
      )
  );
  console.error(
    await page.locator('.condition-value').evaluateAll((rows) =>
      rows.map((row) => ({
        input: row.querySelector('input')?.outerHTML,
        menu: row.querySelector('details')?.open,
        selected: row.querySelector('.selected')?.outerHTML,
        focus: document.activeElement?.outerHTML
      }))
    )
  );
  await page.screenshot({ path: '../.screenshots/search-library-failure.png' });
  throw error;
} finally {
  await browser.close();
}
