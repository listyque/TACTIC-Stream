import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const [base] = process.argv.slice(2);
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || undefined
});
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } }),
  errors = [];
page.on('pageerror', (error) => errors.push(error.message));
page.setDefaultTimeout(10000);
try {
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    )
  );
  await page.goto(base + '/projects/one/?search_type=one%2Freport_assets');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page
    .getByRole('menuitemradio', { name: 'Continuous tree', exact: true })
    .click();
  const robot = page
    .locator('.workspace-results .result-item')
    .and(page.getByLabel('Report Robot', { exact: true }));
  await robot.click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Advanced menu', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Object details', exact: true })
    .click();
  const dialog = page.getByRole('dialog', {
      name: 'Object details',
      exact: true
    }),
    report = dialog.locator('.object-report');
  await report
    .locator('[data-frame="objectReportTitle"]')
    .filter({ hasText: 'Report Robot' })
    .waitFor();
  const titlebar = dialog.locator(':scope > .app-dialog-titlebar');
  const chrome = await titlebar.evaluate((header) => ({
    height: header.getBoundingClientRect().height,
    expectedHeight: parseFloat(
      getComputedStyle(header).getPropertyValue('--dialog-header-height')
    ),
    title: header.querySelector('h2').textContent,
    buttons: [...header.querySelectorAll('button')].map((button) => ({
      label: button.getAttribute('aria-label'),
      width: button.getBoundingClientRect().width,
      height: button.getBoundingClientRect().height,
      round: getComputedStyle(button).borderRadius,
      iconOnly: button.classList.contains('icon-button')
    }))
  }));
  assert.equal(chrome.title, 'Report Robot');
  assert.equal(chrome.height, chrome.expectedHeight);
  assert.deepEqual(
    chrome.buttons.map((button) => button.label),
    ['Edit record', 'Maximize window', 'Close details']
  );
  for (const button of chrome.buttons) {
    assert.equal(button.width, 34);
    assert.equal(button.height, 34);
    assert.equal(button.round, '50%');
    assert.equal(button.iconOnly, true);
  }
  const normalBounds = await dialog.boundingBox();
  await dialog
    .getByRole('button', { name: 'Maximize window', exact: true })
    .click();
  assert.equal((await dialog.boundingBox()).width, 1360);
  assert.equal(
    await dialog.evaluate((element) => getComputedStyle(element).borderRadius),
    '0px'
  );
  await dialog
    .getByRole('button', { name: 'Restore window', exact: true })
    .click();
  assert(Math.abs((await dialog.boundingBox()).width - normalBounds.width) < 1);
  const headerTop = (await titlebar.boundingBox()).y;
  await report.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  assert.equal(
    (await titlebar.boundingBox()).y,
    headerTop,
    'Report scroll keeps the common window titlebar in place'
  );
  await report.evaluate((element) => {
    element.scrollTop = 0;
  });
  if (process.env.STREAM_REPORT_CAPTURE)
    await page.screenshot({
      path: process.env.STREAM_REPORT_CAPTURE + '-desktop.png'
    });
  await dialog
    .getByRole('button', { name: 'Edit record', exact: true })
    .click();
  const detailEditor = page.getByRole('dialog', {
    name: 'Record form',
    exact: true
  });
  await detailEditor
    .getByRole('button', { name: 'Close', exact: true })
    .click();
  for (const source of ['related', 'presentation']) {
    await page.evaluate(async (source) => {
      const app =
        document.querySelector('#app').__vue_app__._container._vnode.component
          .subTree.component.subTree.component.proxy;
      if (source === 'related')
        await app.$refs.relatedObjects.inspect(app.detail);
      else {
        function findPresentation(node) {
          if (node?.component?.type?.components?.ResultItem)
            return node.component.proxy;
          if (node?.component) return findPresentation(node.component.subTree);
          for (const child of Array.isArray(node?.children)
            ? node.children
            : []) {
            const result = findPresentation(child);
            if (result) return result;
          }
        }
        findPresentation(app.$.subTree).inspect({
          searchType: 'nested-report',
          record: app.detail
        });
      }
    }, source);
    await titlebar
      .getByRole('heading', { name: 'Report Robot', exact: true })
      .waitFor();
    assert.equal(await titlebar.locator('.app-window-controls').count(), 1);
    assert.equal(
      await titlebar.evaluate(
        (element) => element.getBoundingClientRect().height
      ),
      chrome.expectedHeight
    );
    await dialog
      .getByRole('button', { name: 'Close details', exact: true })
      .click();
  }
  await page.evaluate(() =>
    document
      .querySelector('#app')
      .__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy.$refs.details.showModal()
  );
  const searchLink =
    'tactic-search://open?project=one&search_type=one/report_assets';
  await page.evaluate(() => {
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    window.reportOpenLink = app.openRichLink;
    window.reportOpenedLinks = [];
    app.openRichLink = (...args) => window.reportOpenedLinks.push(args);
  });
  await report.getByRole('link', { name: searchLink, exact: true }).click();
  assert.equal(
    await page.evaluate(() => window.reportOpenedLinks[0][0]),
    searchLink
  );
  await page.evaluate(() => {
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    app.openRichLink = window.reportOpenLink;
    delete window.reportOpenLink;
    delete window.reportOpenedLinks;
  });
  await page.evaluate(() =>
    document
      .querySelector('#app')
      .__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy.$refs.details.showModal()
  );
  await report.locator('[data-frame="objectReportRow_task_0"]').waitFor();
  assert.equal(
    await dialog.evaluate((element) => element.matches(':modal')),
    true
  );
  await report.locator('[data-frame="objectReportRow_task_0"]').click();
  const inspector = page.locator('[data-dock="notes"] .notes-panel');
  await inspector.getByText('Task note', { exact: true }).waitFor();
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => {
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    return (
      !!app.$refs.taskManager.active &&
      !app.$refs.taskManager.loading &&
      !app.$refs.taskInspector.loading
    );
  });
  const expand = inspector.getByRole('button', {
    name: 'Expand Task Inspector',
    exact: true
  });
  if (await expand.isVisible()) await expand.click();
  await inspector
    .getByRole('button', { name: 'Edit task in full editor', exact: true })
    .click();
  const taskForm = page.getByRole('dialog', {
    name: 'Record form',
    exact: true
  });
  await taskForm.getByLabel('Description', { exact: true }).waitFor();
  assert.equal(
    await taskForm.evaluate((node) => node.matches(':modal')),
    true,
    'Full task editor is modal, matching the native editor'
  );
  await taskForm.getByRole('button', { name: 'Close', exact: true }).click();
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Report task retained draft');
  await page.evaluate(() =>
    document
      .querySelector('#app')
      .__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy.$refs.details.showModal()
  );
  await report.getByRole('radio', { name: 'Notes', exact: true }).click();
  await report.getByText('Object note', { exact: true }).first().waitFor();
  await report.getByText('Task note', { exact: true }).first().waitFor();
  await report.getByText('Task note', { exact: true }).first().click();
  await page.waitForFunction(() =>
    document.activeElement?.matches('[data-note-kind="note"][data-note-id]')
  );
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Report task retained draft'
  );

  await page.evaluate(() =>
    document
      .querySelector('#app')
      .__vue_app__._container._vnode.component.subTree.component.subTree.component.proxy.$refs.details.showModal()
  );
  await report.getByRole('radio', { name: 'Children', exact: true }).click();
  await report.getByText('No related children', { exact: true }).waitFor();
  await report.getByRole('radio', { name: 'Snapshots', exact: true }).click();
  await report.locator('[data-frame="objectSnapshotProcess_0"]').click();
  await report.getByText('Report package', { exact: true }).first().waitFor();
  await report
    .locator('[data-frame="objectReportFile_0_0"]')
    .getByRole('button')
    .click();
  const preview = page.getByRole('dialog', {
    name: 'File preview',
    exact: true
  });
  await preview.getByText('Report file contents', { exact: true }).waitFor();
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .click();
  await report.getByRole('radio', { name: 'Activity', exact: true }).click();
  await page.waitForFunction(
    () =>
      document.querySelector('.object-report')?.getAttribute('aria-busy') ===
      'false'
  );
  assert.equal(await report.getByRole('alert').count(), 0);
  await report.getByRole('radio', { name: 'Notes', exact: true }).click();
  await report.getByText('Task note', { exact: true }).first().waitFor();
  await dialog
    .getByRole('button', { name: 'Close details', exact: true })
    .click();
  await robot.click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Advanced menu', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Object details', exact: true })
    .click();
  assert.equal(
    await report
      .getByRole('radio', { name: 'Notes', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );
  await page.setViewportSize({ width: 390, height: 800 });
  await report.getByRole('radio', { name: 'Tasks', exact: true }).click();
  await report.locator('[data-frame="objectReportRow_task_0"]').waitFor();
  if (process.env.STREAM_REPORT_CAPTURE)
    await page.screenshot({
      path: process.env.STREAM_REPORT_CAPTURE + '-narrow.png'
    });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  await dialog
    .getByRole('button', { name: 'Close details', exact: true })
    .click();
  await page.setViewportSize({ width: 1360, height: 900 });
  await page.route(
    '**/admin/object-deletion/read',
    (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Read failed' })
      }),
    { times: 1 }
  );
  await robot.click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Delete record', exact: true })
    .click();
  const deletion = page.getByRole('dialog', {
    name: 'Delete record',
    exact: true
  });
  await deletion
    .locator('[data-frame="deleteSObjectError"]')
    .filter({ hasText: 'Read failed' })
    .waitFor();
  assert.equal(
    await deletion
      .getByRole('button', { name: 'Delete', exact: true })
      .isDisabled(),
    true
  );
  await deletion.getByRole('button', { name: 'Retry', exact: true }).click();
  await page.waitForFunction(
    () => !document.querySelector('[data-frame="deleteSubmit"]').disabled
  );
  const notesGroup = deletion
    .locator('[data-frame^="deleteDependencyGroup_"]')
    .filter({
      has: page.getByRole('checkbox', { name: 'Notes', exact: true })
    });
  await notesGroup
    .getByRole('button', { name: 'Show dependencies', exact: true })
    .click();
  await deletion.getByText('Object note', { exact: true }).waitFor();
  let writes = 0;
  await page.route('**/admin/object-deletion/apply', async (route) => {
    writes++;
    const response = await route.fetch();
    assert.equal(response.status(), 200);
    await route.fulfill({
      status: 502,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'The deletion response was lost' })
    });
  });
  await deletion.getByRole('button', { name: 'Delete', exact: true }).click();
  await deletion
    .getByText(
      'This operation cannot be retried here. Close this dialog and refresh the data to check the result.',
      { exact: true }
    )
    .waitFor();
  assert.equal(
    await deletion
      .getByRole('button', { name: 'Delete', exact: true })
      .isDisabled(),
    true
  );
  assert.equal(
    writes,
    1,
    'An unknown deletion result must never trigger an automatic retry'
  );
  await deletion
    .getByRole('button', { name: 'Close actions', exact: true })
    .click();
  assert.deepEqual(errors, []);
  console.log(
    'PASS: object report pages, native data, nonmodal host, retained page and narrow reflow'
  );
} catch (error) {
  console.error('Browser errors:', errors);
  console.log((await page.locator('body').innerText()).slice(-8000));
  throw error;
} finally {
  await browser.close();
}
