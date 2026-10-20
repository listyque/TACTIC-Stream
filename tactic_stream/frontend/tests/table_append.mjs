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
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const table = page.locator(
  '.workspace-results .configured-view:visible .handler-table'
);
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false' &&
      [...document.querySelectorAll('.workspace-results .configured-view')]
        .filter((node) => node.offsetParent)
        .every((node) => node.getAttribute('aria-busy') === 'false')
  );
try {
  await page.goto(
    process.argv[2] +
      '/projects/admin/?search_type=sthpw/snapshot&view=append_test'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await ready();
  const remote = (method, args, project = 'admin') =>
    page.evaluate(
      async ({ method, args, project }) => {
        const session = JSON.parse(
          localStorage.getItem('tactic_stream.session')
        );
        const response = await fetch('/admin/rpc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            method,
            args: [
              { ticket: session.ticket, project, language: 'python' },
              ...args
            ]
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        return result.result;
      },
      { method, args, project }
    );
  const snapshot = await remote(
    'create_snapshot',
    ['contract/entity?project=one&code=A', 'table_append'],
    'one'
  );
  assert.equal(snapshot.project_code, 'one');
  await page
    .locator('.search-header')
    .getByRole('button', { name: 'Refresh', exact: true })
    .click();
  await ready();
  const appendRequests = [];
  const observeAppend = (request) => {
    if (request.url().includes('/UploadServer/'))
      appendRequests.push({ url: request.url() });
    if (request.url().endsWith('/admin/rpc')) {
      const payload = request.postDataJSON();
      if (
        payload.method === 'execute_cmd' &&
        payload.args[1] === 'tactic.ui.table.TableSnapshotAppendCmd'
      )
        appendRequests.push(payload);
    }
  };
  page.on('request', observeAppend);
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  const snapshotRow = table.getByRole('row').filter({ hasText: snapshot.code });
  await snapshotRow
    .getByRole('button', { name: 'Attach files', exact: true })
    .click();
  const append = page.locator('.object-checkin[open]');
  await append.locator('.object-checkin-workspace[aria-busy=false]').waitFor();
  await append.locator('input[type=file]').setInputFiles({
    name: 'http-append.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('real HTTP attachment bytes')
  });
  await append
    .locator('[data-frame=objectCheckinField_fileType]')
    .fill('reference');
  await append
    .locator('[data-frame=objectCheckinKeepName]')
    .getByRole('switch')
    .check();
  await append.locator('[data-frame=objectCheckinSubmit]').click();
  await append.waitFor({ state: 'hidden' });
  page.off('request', observeAppend);
  const save = appendRequests.find(
    (request) => request.args?.[2]?.action === 'save'
  );
  assert.equal(
    save.args[0].project,
    'one',
    'A global snapshot uses its owning project, not the workspace project'
  );
  assert.equal(save.args[2].search_key, snapshot.__search_key__);
  assert.equal(save.args[2].file_type, 'reference');
  assert.equal(save.args[2].keep_file_name, true);
  assert.match(save.args[2].upload_directory, /^append_[a-f0-9]{32}$/);
  const upload = appendRequests.find((request) => request.url);
  assert.match(upload.url, /\/tactic\/one\/UploadServer\/$/);
  const result = await page.evaluate(async (key) => {
    const session = JSON.parse(localStorage.getItem('tactic_stream.session'));
    const response = await fetch('/admin/navigation-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticket: session.ticket,
        project: 'one',
        link: 'skey://' + key
      })
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error);
    const file = body.result.preview.files.find(
      (file) => file.filename === 'http-append.txt'
    );
    if (!file) throw new Error(JSON.stringify(body.result.preview));
    return {
      version: body.result.object.version,
      text: await (await fetch(file.href)).text()
    };
  }, snapshot.__search_key__);
  assert.equal(
    result.version,
    snapshot.version,
    'Append preserves the concrete snapshot version'
  );
  assert.equal(result.text, 'real HTTP attachment bytes');
  assert.match(page.url(), /\/projects\/admin\//);
  assert.deepEqual(errors, []);
  console.log(
    'Snapshot table append: real HTTP bytes, scoped project, captured version/type/name passed.'
  );
} finally {
  await browser.close();
}
