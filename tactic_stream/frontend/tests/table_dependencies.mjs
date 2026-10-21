import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  hasTouch: true
});
page.setDefaultTimeout(10000);
const errors = [],
  reads = [],
  files = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (!request.url().endsWith('/admin/rpc')) return;
  const body = request.postDataJSON();
  if (body.args?.[1] === 'tactic.ui.table.TableDependencyReadCmd')
    reads.push({ ...body.args[2], project: body.args[0].project });
  if (body.args?.[1] === 'tactic.ui.table.TableSnapshotFilesCmd')
    files.push(body.args[2]);
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
try {
  await page.goto(
    process.argv[2] +
      '/projects/one/?search_type=contract/entity&view=dependencies_test'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  const row = page
    .getByRole('row')
    .filter({ hasText: 'A' })
    .filter({
      has: page.getByRole('button', { name: 'Dependencies', exact: true })
    })
    .first();
  await row.getByRole('button', { name: 'Dependencies', exact: true }).tap();
  const viewer = page.locator('.table-document[open]');
  await viewer.locator('[data-frame^="dependencyTitle_"]').first().waitFor();
  assert.equal(reads.length, 1);
  const expand = viewer.locator('[data-frame="dependencyExpand_root_2"]');
  // Snapshot files precede upstream links: the last disclosure is the reference.
  await expand.tap();
  await viewer.getByText(/Cyclic dependency/).waitFor();
  assert.equal(reads.length, 2);
  const reference = viewer.locator('[data-frame="dependencyExpand_root_2"]');
  await reference.click();
  await reference.click();
  await viewer.getByText(/Cyclic dependency/).waitFor();
  assert.equal(reads.length, 2, 'cached branch must not reload');
  const sequence = viewer.locator('[data-frame="dependencyExpand_root_1"]');
  await sequence.click();
  await viewer.getByText('render.1001.exr', { exact: true }).waitFor();
  assert.equal(reads.at(-1).file_index, 1);
  assert(reads.at(-1).expected_revision);
  const scrollbar = viewer.locator('[data-frame="dependencyRows"]');
  await scrollbar.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await viewer.getByRole('button', { name: 'Show more', exact: true }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll('[data-frame^="dependencyTitle_"]')].some(
      (element) => element.textContent === 'render.1051.exr'
    )
  );
  assert.equal(reads.at(-1).offset, 50);
  // File open captures one registered file even when another XML node is a sequence.
  await viewer.locator('[data-frame="dependencyRows"]').evaluate((element) => {
    element.scrollTop = 0;
  });
  await viewer.locator('[data-frame^="dependencyFileOpen_"]').first().click();
  const preview = page.locator('.file-preview[open]');
  try {
    await preview
      .getByText('Concrete dependency contents', { exact: true })
      .waitFor();
  } catch (error) {
    throw new Error(
      error.message +
        '; viewer=' +
        (await viewer.innerText()) +
        '; preview=' +
        (await preview.allTextContents())
    );
  }
  assert(files[0].file_code && files[0].expected_revision);
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .click();
  await viewer.locator('[data-frame="dependencyClose"]').click();
  await viewer.waitFor({ state: 'hidden' });
  await row.getByRole('button', { name: 'Dependencies', exact: true }).click();
  await viewer.locator('[data-frame^="dependencyTitle_"]').first().waitFor();
  assert.equal(reads.length, 5, 'reopening starts a fresh root session');
  await viewer.locator('[data-frame="dependencyClose"]').click();
  let release,
    finished,
    intercepted = false;
  const permit = new Promise((resolve) => {
    release = resolve;
  });
  const done = new Promise((resolve) => {
    finished = resolve;
  });
  const hold = async (route) => {
    if (
      route.request().postDataJSON().args?.[1] !==
      'tactic.ui.table.TableDependencyReadCmd'
    )
      return route.continue();
    intercepted = true;
    await permit;
    try {
      await route.abort();
    } finally {
      finished();
    }
  };
  await page.route('**/admin/rpc', hold);
  try {
    const waiting = page.waitForRequest(
      (request) =>
        request.url().endsWith('/admin/rpc') &&
        request.postDataJSON().args?.[1] ===
          'tactic.ui.table.TableDependencyReadCmd'
    );
    await row
      .getByRole('button', { name: 'Dependencies', exact: true })
      .click();
    await waiting;
    const failed = page.waitForEvent(
      'requestfailed',
      (request) =>
        request.url().endsWith('/admin/rpc') &&
        request.postDataJSON().args?.[1] ===
          'tactic.ui.table.TableDependencyReadCmd'
    );
    await viewer.locator('[data-frame="dependencyClose"]').click();
    await failed;
  } finally {
    release();
    if (intercepted) await done;
    await page.unroute('**/admin/rpc', hold);
  }
  await viewer.waitFor({ state: 'hidden' });
  await row.getByRole('button', { name: 'Dependencies', exact: true }).click();
  await viewer.locator('[data-frame^="dependencyTitle_"]').first().waitFor();
  const header = await viewer.locator(':scope > header').boundingBox();
  await page.mouse.move(header.x + 120, header.y + 20);
  await page.mouse.down();
  await page.mouse.move(header.x + 120, header.y + 450, { steps: 8 });
  await page.mouse.up();
  let documentStarted,
    documentRelease,
    documentFinished,
    documentIntercepted = false;
  const documentWaiting = new Promise((resolve) => {
    documentStarted = resolve;
  });
  const documentPermit = new Promise((resolve) => {
    documentRelease = resolve;
  });
  const documentDone = new Promise((resolve) => {
    documentFinished = resolve;
  });
  const holdDocument = async (route) => {
    if (
      route.request().postDataJSON().args?.[1] !==
      'tactic.ui.table.TableDocumentReadCmd'
    )
      return route.continue();
    const response = await route.fetch();
    documentIntercepted = true;
    documentStarted();
    await documentPermit;
    try {
      await route.fulfill({ response });
    } finally {
      documentFinished();
    }
  };
  await page.route('**/admin/rpc', holdDocument);
  try {
    await row
      .getByRole('button', { name: 'Open summary', exact: true })
      .click();
    await Promise.race([
      documentWaiting,
      new Promise((_, reject) => {
        const timeout = setTimeout(
          () => reject(Error('Summary read did not start')),
          10000
        );
        timeout.unref();
      })
    ]);
    const closed = viewer.evaluate(
      (element) =>
        new Promise((resolve) =>
          element.addEventListener('close', () => resolve(), { once: true })
        )
    );
    await viewer.locator('[data-frame="dependencyClose"]').click();
    await closed;
  } finally {
    documentRelease();
    if (documentIntercepted) await documentDone;
    await page.unroute('**/admin/rpc', holdDocument);
  }
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    await viewer.count(),
    0,
    'a successful old document read must not reopen a closed window'
  );
  await page.goto(
    process.argv[2] +
      '/projects/admin/?search_type=sthpw/snapshot&view=dependencies_snapshot_test'
  );
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  await page
    .getByRole('row')
    .filter({ hasText: process.argv[3] })
    .getByRole('button', { name: 'Dependencies', exact: true })
    .click();
  await viewer.locator('[data-frame^="dependencyTitle_"]').first().waitFor();
  assert.equal(
    reads.at(-1).project,
    'one',
    'global snapshot table must open the captured source project'
  );
  assert(
    (
      await viewer.locator('[data-frame="dependencyIdentity"]').innerText()
    ).includes(process.argv[3])
  );
  await viewer.locator('[data-frame="dependencyClose"]').click();
  assert.deepEqual(errors, []);
  console.log(
    'PASS: actual dependency table port, touch, cache, cycles, bounded sequence and concrete file bytes'
  );
} finally {
  await browser.close();
}
