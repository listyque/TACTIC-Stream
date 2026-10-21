import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 1280, height: 960 },
  hasTouch: true
});
page.setDefaultTimeout(10000);
const errors = [],
  writes = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/rpc')) {
    const body = request.postDataJSON();
    if (
      body.method === 'execute_cmd' &&
      body.args[1].endsWith('TableConnectionRemoveCmd')
    )
      writes.push(body.args);
  }
});
const ready = () =>
  page.waitForFunction(() => {
    const views = [
      ...document.querySelectorAll('.workspace-results .configured-view')
    ].filter((node) => node.offsetParent);
    return (
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false' &&
      views.length &&
      views.every((node) => node.getAttribute('aria-busy') === 'false')
    );
  });
async function remote(method, args) {
  return page.evaluate(
    async ({ method, args }) => {
      const session = JSON.parse(localStorage.getItem('tactic_stream.session'));
      const response = await fetch('/admin/rpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method,
          args: [
            { ticket: session.ticket, project: 'one', language: 'python' },
            ...args
          ]
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      return result.result;
    },
    { method, args }
  );
}
try {
  await page.goto(
    process.argv[2] +
      '/projects/one/?search_type=contract/browser_connections&view=connections_test'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  const list = page.locator('[data-frame="tableConnections"]');
  await list.waitFor();
  assert.equal(
    await list.evaluate((node) => node.scrollHeight > node.clientHeight),
    true
  );
  const alpha = list.locator('[data-frame-row]').filter({ hasText: 'ALPHA' });
  const archived = list.locator('[data-frame-row]').filter({ hasText: 'BETA' });
  const missing = list
    .locator('[data-frame-row]')
    .filter({ hasText: 'Object is unavailable' });
  assert.equal(await list.locator('[data-frame-row]').count(), 3);
  await archived.getByText('Retired', { exact: true }).waitFor();
  await missing.getByText('Object is unavailable', { exact: true }).waitFor();
  const confirm = page.locator('.table-service-confirmation');
  await alpha
    .getByRole('button', { name: 'Remove connection', exact: true })
    .click();
  await confirm
    .getByText('Remove this connection? The connected objects will be kept.', {
      exact: true
    })
    .waitFor();
  await confirm.getByRole('button', { name: 'Cancel', exact: true }).click();
  assert.equal(writes.length, 0);
  const connectionKey = await alpha.getAttribute('data-frame-row');
  await alpha
    .getByRole('button', { name: 'Remove connection', exact: true })
    .click();
  await remote('execute_python_script', [
    '',
    {
      code: `
from pyasm.search import Search
connection=Search.get_by_search_key(${JSON.stringify(connectionKey)})
connection.set_value('context','changed while confirming')
connection.commit(triggers=False)
return True
`
    }
  ]);
  await confirm
    .getByRole('button', { name: 'Remove connection', exact: true })
    .click();
  await page
    .locator('.workspace-results .configured-view:visible .error')
    .filter({ hasText: 'Connection changed. Reload before removing it.' })
    .waitFor();
  await ready();
  assert.equal(await list.locator('[data-frame-row]').count(), 3);
  await alpha
    .getByRole('button', { name: 'Remove connection', exact: true })
    .click();
  await confirm
    .getByRole('button', { name: 'Remove connection', exact: true })
    .click();
  await alpha.waitFor({ state: 'hidden' });
  await ready();
  assert.equal(await list.locator('[data-frame-row]').count(), 2);
  assert.equal(writes.at(-1)[0].project, 'one');
  assert.equal(
    writes.at(-1)[2].parent_key,
    'contract/browser_connections?project=one&code=TARGET'
  );
  await page.setViewportSize({ width: 320, height: 740 });
  // The phone workspace uses cards; the configured table is restored on desktop.
  await list.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  await page.setViewportSize({ width: 960, height: 740 });
  await list.waitFor();
  await ready();
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (
      body.method === 'execute_cmd' &&
      body.args[1].endsWith('TableConnectionRemoveCmd')
    ) {
      await route.fetch();
      await route.abort('connectionreset');
    } else await route.continue();
  });
  await missing
    .getByRole('button', { name: 'Remove connection', exact: true })
    .tap();
  await confirm
    .getByRole('button', { name: 'Remove connection', exact: true })
    .tap();
  await missing.waitFor({ state: 'hidden' });
  await ready();
  await page.unroute('**/admin/rpc');
  assert.equal(await list.locator('[data-frame-row]').count(), 1);
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  assert.deepEqual(errors, []);
  console.log(
    'Connections: first click/cancel/stale revision/remove/lost response/retired/missing target/touch960/mobile cards transition OK'
  );
} catch (error) {
  await page.screenshot({
    path: '../.screenshots/table-connections-failure.png'
  });
  throw error;
} finally {
  await browser.close();
}
