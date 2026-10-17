import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const base = process.argv[2];
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || undefined
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } }),
  errors = [];
page.setDefaultTimeout(8000);
page.on('pageerror', (error) => errors.push(error.message));
const rpc = async (method, args, kwargs = {}) => {
  const response = await page.request.post(base + '/admin/rpc', {
    data: { method, args, kwargs }
  });
  const value = await response.json();
  assert(response.ok(), JSON.stringify(value));
  return value.result;
};
try {
  const ticket = await rpc('get_ticket', ['admin', 'private-test-password']);
  const auth = { ticket, project: 'one' };
  const parent = (
    await rpc('query', [auth, 'contract/entity'], { filters: [['code', 'A']] })
  )[0];
  const candidate = await rpc('insert', [
    auth,
    'contract/collection',
    { code: 'B08_LINK', name: 'Link candidate' }
  ]);
  const result = await (
    await page.request.post(base + '/admin/result-items', {
      data: {
        ticket,
        project: 'one',
        search_type: 'contract/entity',
        search_keys: [parent.__search_key__]
      }
    })
  ).json();
  const branch = result.result.items[0].branches.find(
    (row) => row.search_type === 'contract/collection'
  );
  assert(branch);
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    )
  );
  await page.goto(base + '/projects/one/?search_type=contract%2Fentity');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.workspace-results .result-item').first().waitFor();
  const open = () =>
    page.evaluate(
      ({ parent, branch }) => {
        const app =
          document.querySelector('#app').__vue_app__._container._vnode.component
            .subTree.component.subTree.component.proxy;
        return app.$refs.relatedObjects.open(
          parent,
          'contract/collection',
          branch
        );
      },
      { parent, branch }
    );
  await open();
  const dialog = page.getByRole('dialog', {
    name: 'Link existing objects',
    exact: true
  });
  const available = dialog.locator('[data-frame="availableLinkList"]'),
    linked = dialog.locator('[data-frame="linkedLinkList"]');
  await available
    .getByRole('button', { name: 'Link candidate', exact: true })
    .click();
  await dialog
    .getByRole('button', { name: 'Link selected objects', exact: true })
    .click();
  await linked
    .getByRole('button', { name: 'Link candidate', exact: true })
    .waitFor();
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await dialog
    .getByRole('button', { name: 'Continue editing', exact: true })
    .click();
  assert(
    await linked
      .getByRole('button', { name: 'Link candidate', exact: true })
      .isVisible()
  );
  for (const width of [360, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    assert(
      await dialog.evaluate(
        (element) => element.scrollWidth <= element.clientWidth
      )
    );
    assert(
      await dialog
        .getByRole('button', { name: 'Save', exact: true })
        .isVisible()
    );
  }
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  const mappings = () =>
    rpc('query', [auth, 'contract/entity_in_collection'], {
      filters: [
        ['entity_code', 'A'],
        ['collection_code', candidate.code]
      ]
    });
  assert.equal((await mappings()).length, 1);
  await open();
  const search = dialog.getByRole('combobox', {
    name: 'Search available objects',
    exact: true
  });
  await search.fill('does-not-exist');
  await search.press('Enter');
  await available.getByText('No available objects', { exact: true }).waitFor();
  await linked
    .getByRole('button', { name: 'Link candidate', exact: true })
    .click();
  await dialog
    .getByRole('button', { name: 'Remove selected links', exact: true })
    .click();
  let writes = 0;
  await page.route('**/admin/rpc', async (route) => {
    if (
      route.request().postDataJSON()?.args?.[1] ===
      'tactic.command.sobject_link_cmd.SObjectLinkCmd'
    ) {
      writes++;
      await route.fetch();
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Response lost' })
      });
    } else await route.continue();
  });
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  await dialog
    .locator('[data-frame="linkErrorText"]')
    .filter({ hasText: 'The save result is unknown.' })
    .waitFor();
  assert(
    await dialog.getByRole('button', { name: 'Save', exact: true }).isDisabled()
  );
  assert.equal(writes, 1);
  assert.equal((await mappings()).length, 0);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: object links stage/retain/resize/search/save and lost-response guard with real instance mappings'
  );
} catch (error) {
  console.error(error);
  await page
    .screenshot({
      path: '../.screenshots/object-links-failure.png',
      timeout: 3000
    })
    .catch(() => {});
  throw error;
} finally {
  await browser.close();
}
