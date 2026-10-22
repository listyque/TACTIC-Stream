import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
const [base, output, key] = process.argv.slice(2);
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
let page;
const requests = new Set(),
  publications = [];
try {
  page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('request', (request) => {
    requests.add(request);
    if (request.url().includes('/admin/') && request.method() === 'POST') {
      const data = request.postDataJSON();
      if (data?.args?.[2]?.action === 'checkin') publications.push(data);
    }
  });
  page.on('requestfinished', (request) => requests.delete(request));
  page.on('requestfailed', (request) => requests.delete(request));
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'warning') console.log('WARNING', message.text());
  });
  await page.addInitScript(() => {
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    );
    localStorage.setItem(
      'tactic_stream.preferences',
      JSON.stringify({ checkin: { commitQueueAutoClean: false } })
    );
  });
  await page.goto(
    base + '/projects/one/?' + new URLSearchParams({ link: 'skey://' + key })
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page
    .getByRole('dialog', { name: 'Object details', exact: true })
    .waitFor();
  await page
    .getByRole('button', { name: 'Close details', exact: true })
    .click();
  const row = page
    .locator('.workspace-results .result-item:visible')
    .filter({
      has: page.locator('.result-title-line > strong', {
        hasText: 'Queue asset'
      })
    })
    .first();
  await row.click();
  const dockMenu = page.getByRole('group', { name: 'Docks', exact: true });
  // The common dock menu remains the single entry point.
  await page.getByLabel('Workspace panels', { exact: true }).click();
  await page.getByLabel('Tools', { exact: true }).click();
  await page
    .getByRole('menuitemradio', { name: 'Drop Plate', exact: true })
    .click();
  const plate = page.locator('#dock-drop_plate');
  await plate.waitFor({ state: 'visible' });
  await page
    .locator('[data-dock=drop_plate]')
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .click();
  const source = [
    {
      name: 'beauty.0001.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('frame one')
    },
    {
      name: 'beauty.0003.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('frame three')
    },
    {
      name: 'diffuse_1001.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('tile one')
    },
    {
      name: 'diffuse_1002.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('tile two')
    }
  ];
  await plate
    .locator('input[type=file]:not([webkitdirectory])')
    .setInputFiles(source);
  await plate.locator('[data-frame^=dropPlateGroup_]').nth(1).waitFor();
  assert.equal(await plate.locator('[data-frame^=dropPlateGroup_]').count(), 2);
  await plate
    .getByRole('textbox', { name: 'Context', exact: true })
    .fill('publish/browser');
  await plate
    .getByRole('button', { name: 'Matching Templates', exact: true })
    .click();
  const templates = page.getByRole('dialog', {
    name: 'Matching Templates',
    exact: true
  });
  const templateList = templates.locator('[data-frame=matchingTemplatesList]');
  async function selectTemplate(pattern) {
    let offset = 0;
    while (true) {
      const box = await templateList.evaluate((list, offset) => {
        list.scrollTop = offset;
        list.dispatchEvent(new Event('scroll'));
        return { height: list.clientHeight, total: list.scrollHeight };
      }, offset);
      await page.waitForTimeout(30);
      const button = templateList.getByRole('button', {
        name: pattern,
        exact: true
      });
      if (await button.count()) {
        await button.click();
        return button;
      }
      assert.ok(
        offset + box.height < box.total,
        'Template not found: ' + pattern
      );
      offset += Math.max(1, box.height / 2);
    }
  }
  async function templateCount() {
    const ids = new Set();
    let offset = 0;
    while (true) {
      const box = await templateList.evaluate((list, offset) => {
        list.scrollTop = offset;
        list.dispatchEvent(new Event('scroll'));
        return { height: list.clientHeight, total: list.scrollHeight };
      }, offset);
      await page.waitForTimeout(30);
      for (const id of await templateList
        .locator('[data-frame-row]')
        .evaluateAll((rows) => rows.map((row) => row.dataset.frameRow)))
        ids.add(id);
      if (offset + box.height >= box.total) break;
      offset += Math.max(1, box.height / 2);
    }
    return ids.size;
  }
  await templateList.waitFor();
  await templateList.evaluate((list) => (list.scrollTop = list.scrollHeight));
  assert.equal(await templateCount(), 19);
  const chosenTemplate = await selectTemplate('$FILENAME_$LAYER.$EXT');
  const templateKey = (await chosenTemplate.getAttribute('data-frame')).replace(
    'matchingTemplateSelect_',
    ''
  );
  await templates
    .locator('[data-frame="matchingEnabled_' + templateKey + '"]')
    .getByRole('checkbox')
    .check();
  await templates
    .getByRole('combobox', { name: 'Process mapping', exact: true })
    .fill('publish');
  await templates
    .getByRole('combobox', { name: 'Context mapping', exact: true })
    .fill('publish/browser');
  await templates
    .getByLabel('Test on filename', { exact: true })
    .fill('diffuse_color.txt');
  await templates.getByRole('button', { name: 'Test', exact: true }).click();
  await templates
    .locator('[data-frame=matchingTestResult]')
    .filter({ hasText: 'Matched as layer_file' })
    .waitFor();
  await templates
    .getByRole('button', { name: 'Duplicate', exact: true })
    .filter({ visible: true })
    .click();
  assert.equal(await templateCount(), 20);
  await templates
    .getByRole('button', { name: 'Move up', exact: true })
    .filter({ visible: true })
    .click();
  await templates
    .getByRole('button', { name: 'Move down', exact: true })
    .filter({ visible: true })
    .click();
  await templates
    .getByRole('button', { name: 'Delete', exact: true })
    .filter({ visible: true })
    .click();
  assert.equal(await templateCount(), 19);
  await selectTemplate('$FILENAME_$LAYER.$EXT');
  await templates.getByRole('button', { name: 'Test', exact: true }).click();
  await templates
    .locator('[data-frame=matchingTestResult]')
    .filter({ hasText: 'Matched as layer_file' })
    .waitFor();
  await templateList.evaluate((node) => (node.scrollTop = 0));
  await page.mouse.move(1, 1);
  await templates.locator('.matching-templates-workspace').screenshot({
    path: output + '/browser-matching-templates.png',
    animations: 'disabled'
  });
  const templatesBox = await templates
    .locator('.matching-templates-workspace')
    .boundingBox();
  await templates.getByRole('button', { name: 'Save', exact: true }).click();
  await templates.waitFor({ state: 'hidden' });
  const plateBox = await plate.boundingBox();
  await plate.screenshot({
    path: output + '/browser-drop-plate.png',
    animations: 'disabled'
  });
  await plate
    .getByRole('button', { name: 'Add to queue', exact: true })
    .click();
  const queue = page.locator('.commit-queue:visible');
  async function queuePane(details) {
    const navigation = queue.locator('[data-frame=commitQueueNavigation]');
    if (await navigation.count())
      await navigation
        .getByRole('radio', {
          name: details ? 'Operation details' : 'QUEUE',
          exact: true
        })
        .click();
  }
  await page
    .locator('[data-dock=commit_queue]')
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .click();
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .waitFor();
  await queue
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Ready to send' })
    .first()
    .waitFor();
  assert.equal(
    publications.length,
    0,
    'Adding only prepares; it never submits'
  );
  await queue
    .getByRole('textbox', { name: 'Description', exact: true })
    .fill('Prepared in Commit Queue');
  await page.keyboard.press('Tab');
  await page.mouse.move(1, 1);
  await queue.screenshot({
    path: output + '/browser-queue-basic.png',
    animations: 'disabled'
  });
  await queue
    .getByRole('button', { name: 'Naming preview', exact: true })
    .click();
  await queue
    .locator(
      '[data-frame=commitQueueNamingDetails] [data-frame^=commitQueueNaming_]'
    )
    .first()
    .waitFor();
  await queue
    .getByRole('button', { name: 'Advanced options', exact: true })
    .click();
  assert.ok(await queue.getByLabel('Version', { exact: true }).isVisible());
  await queue
    .getByRole('button', { name: 'Naming preview', exact: true })
    .click();
  await page.mouse.move(1, 1);
  await queue.screenshot({
    path: output + '/browser-queue-prepared.png',
    animations: 'disabled'
  });
  const dimensions = {
    plate: plateBox,
    queue: await queue.boundingBox(),
    templates: templatesBox
  };
  assert.ok(
    dimensions.queue.x + dimensions.queue.width <= 1440,
    'The queue stays inside its dock'
  );
  assert.ok(
    await queue
      .getByRole('button', { name: 'Commit all', exact: true })
      .isVisible()
  );
  await writeFile(
    output + '/projection.json',
    JSON.stringify(
      {
        dimensions,
        owner: key,
        source: source.map((file) => ({
          name: file.name,
          size: file.buffer.length
        }))
      },
      null,
      2
    )
  );
  await queue
    .getByRole('button', { name: 'Choose preview images', exact: true })
    .click();
  await queue.locator('input[accept="image/*"]').setInputFiles([
    {
      name: 'chosen-preview.png',
      mimeType: 'image/png',
      buffer: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9QAAAABJRU5ErkJggg==',
        'base64'
      )
    }
  ]);
  await queue
    .getByRole('button', { name: 'Manage selected previews', exact: true })
    .click();
  const previews = page.getByRole('dialog', {
    name: 'Operation previews',
    exact: true
  });
  await previews.getByText('chosen-preview.png', { exact: true }).waitFor();
  await previews
    .getByRole('button', { name: 'Remove preview', exact: true })
    .click();
  assert.equal(
    await previews.locator('[data-frame^=commitQueuePreviewRow_]').count(),
    0
  );
  await previews.locator('[data-frame=commitQueuePreviewsClose]').click();
  await queue.getByRole('button', { name: 'Commit all', exact: true }).click();
  await queue
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Completed' })
    .first()
    .waitFor();
  assert.equal(
    await queue.locator('.error').count(),
    0,
    await queue.textContent()
  );
  await queue
    .getByRole('button', { name: 'Snapshot Browser', exact: true })
    .click();
  const snapshot = page.locator('#dock-snapshot');
  await snapshot.waitFor({ state: 'visible' });
  await snapshot.locator('.snapshot-file-row').first().waitFor();
  await snapshot.screenshot({
    path: output + '/browser-snapshot.png',
    animations: 'disabled'
  });
  // Recovery keeps an unsubmitted operation, never browser File permissions.
  if (!(await plate.isVisible()))
    await page.getByRole('tab', { name: 'Drop Plate', exact: true }).click();
  await plate.locator('input[type=file]:not([webkitdirectory])').setInputFiles([
    {
      name: 'retry.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('retry payload')
    }
  ]);
  await plate
    .getByRole('textbox', { name: 'Context', exact: true })
    .fill('publish/recovery');
  await plate
    .getByRole('button', { name: 'Add to queue', exact: true })
    .click();
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .nth(1)
    .waitFor();
  page.once('dialog', (dialog) => dialog.accept());
  await page.reload();
  await page
    .getByRole('dialog', { name: 'Object details', exact: true })
    .waitFor();
  await page
    .getByRole('button', { name: 'Close details', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Commit Queue', exact: true })
    .first()
    .click();
  await queue
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Missing files' })
    .first()
    .waitFor();
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'retry.txt' })
    .click();
  if (!(await queue.locator('[data-frame=commitQueueReselect]').count()))
    await queue
      .locator('[data-frame=commitQueueNavigation]')
      .getByRole('radio', { name: 'QUEUE', exact: true })
      .click();
  await queue.locator('[data-frame=commitQueueReselect]').click();
  await queue
    .locator('input[type=file]:not([webkitdirectory]):not([accept])')
    .setInputFiles([
      {
        name: 'retry.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('retry payload')
      }
    ]);
  if (await queue.locator('[data-frame=commitQueueNavigation]').count())
    await queue
      .locator('[data-frame=commitQueueNavigation]')
      .getByRole('radio', { name: 'Operation details', exact: true })
      .click();
  await queue.getByRole('button', { name: 'Commit all', exact: true }).click();
  await queuePane(false);
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'retry.txt' })
    .getByText(/Completed/)
    .waitFor();
  // Native ordering and duplicates reserve versions only for pending operations.
  if (!(await row.isVisible()))
    await page
      .getByRole('tab', { name: 'Search', exact: true })
      .first()
      .click();
  await row.click();
  if (!(await plate.isVisible()))
    await page.getByRole('tab', { name: 'Drop Plate', exact: true }).click();
  await plate
    .getByRole('checkbox', { name: 'Group check-in', exact: true })
    .uncheck();
  await plate
    .getByRole('textbox', { name: 'Context', exact: true })
    .fill('publish/order');
  const ordered = ['alpha.txt', 'beta.txt', 'gamma.txt'].map((name) => ({
    name,
    mimeType: 'text/plain',
    buffer: Buffer.from(name)
  }));
  await plate
    .locator('input[type=file]:not([webkitdirectory])')
    .setInputFiles(ordered);
  await plate.locator('[data-frame^=dropPlateGroup_]').nth(2).waitFor();
  await plate
    .getByRole('button', { name: 'Add to queue', exact: true })
    .click();
  assert.equal(
    await plate.locator('[data-frame^=dropPlateGroup_]').count(),
    0,
    'Preparation moves from Drop Plate to the native queue'
  );
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'alpha.txt' })
    .click();
  await queue
    .getByRole('button', { name: 'Naming preview', exact: true })
    .click();
  await queue
    .locator('[data-frame=commitQueueNamingDetails]')
    .getByText(/Versioned.*\/v003\//)
    .waitFor();
  await queuePane(false);
  await queue
    .getByRole('button', { name: 'Move operation up', exact: true })
    .click();
  await queue
    .getByRole('button', { name: 'Move operation up', exact: true })
    .click();
  await queuePane(true);
  await queue
    .locator('[data-frame=commitQueueNamingDetails]')
    .getByText(/Versioned.*\/v001\//)
    .waitFor();
  await queuePane(false);
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'alpha.txt' })
    .getByRole('button', { name: 'Remove operation', exact: true })
    .click();
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'beta.txt' })
    .click();
  await queue
    .locator('[data-frame=commitQueueNamingDetails]')
    .getByText(/Versioned.*\/v002\//)
    .waitFor();
  // A new selection of the same paths uses Handler's duplicate identity, not a timestamp.
  if (!(await plate.isVisible()))
    await page.getByRole('tab', { name: 'Drop Plate', exact: true }).click();
  await plate
    .locator('input[type=file]:not([webkitdirectory])')
    .setInputFiles(ordered.slice(1));
  await plate.locator('[data-frame^=dropPlateGroup_]').nth(1).waitFor();
  await plate
    .getByRole('button', { name: 'Add to queue', exact: true })
    .click();
  await queue
    .getByRole('button', { name: 'Ignore duplicate', exact: true })
    .click();
  await queue.getByRole('button', { name: 'Replace', exact: true }).click();
  await queuePane(false);
  assert.equal(
    await queue
      .locator('[data-frame=commitQueueRows] > div > .frame-row')
      .count(),
    4
  );
  await queuePane(true);
  await queue
    .locator('[data-frame=commitQueueNamingDetails]')
    .getByText(/Versioned.*\/v002\//)
    .waitFor();
  await queue
    .getByRole('textbox', { name: 'Description', exact: true })
    .fill('Batch description');
  await page.keyboard.press('Tab');
  await queue
    .getByRole('checkbox', {
      name: 'Apply every edit to checked items',
      exact: true
    })
    .check();
  await queue
    .getByRole('textbox', { name: 'Description', exact: true })
    .fill('Both pending rows');
  await page.keyboard.press('Tab');
  await queuePane(false);
  await queue
    .locator('[data-frame=commitQueueRows] > div > .frame-row')
    .filter({ hasText: 'gamma.txt' })
    .click();
  assert.equal(
    await queue
      .getByRole('textbox', { name: 'Description', exact: true })
      .inputValue(),
    'Both pending rows'
  );
  await queue
    .getByRole('button', { name: 'Context: order', exact: true })
    .click();
  await queue
    .getByRole('textbox', { name: 'Context branch', exact: true })
    .fill('/publish/order branch/');
  await queue
    .getByRole('textbox', { name: 'Context branch', exact: true })
    .press('Enter');
  await queue
    .getByRole('button', { name: 'Context: order_branch', exact: true })
    .waitFor();
  await page.mouse.move(1, 1);
  await queue.screenshot({
    path: output + '/browser-queue-batch.png',
    animations: 'disabled'
  });
  await queuePane(false);
  await queue.getByRole('button', { name: 'Clear queue', exact: true }).click();
  await page
    .locator('.commit-queue-clear-dialog[open] [data-frame=confirmationAccept]')
    .click();
  assert.equal(
    await queue
      .locator('[data-frame=commitQueueRows] > div > .frame-row')
      .count(),
    0
  );
  let lostWrites = 0;
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    if (
      payload.method === 'execute_cmd' &&
      payload.args[2]?.action === 'checkin' &&
      payload.args[2]?.context === 'publish/unknown'
    ) {
      const response = await route.fetch();
      assert.ok(
        response.ok(),
        'The server committed before the response was lost'
      );
      const result = await response.json();
      assert.ok(result.result?.info?.snapshot, result);
      lostWrites++;
      await route.abort('failed');
    } else await route.continue();
  });
  if (!(await plate.isVisible()))
    await page.getByRole('tab', { name: 'Drop Plate', exact: true }).click();
  await plate
    .getByRole('textbox', { name: 'Context', exact: true })
    .fill('publish/unknown');
  await plate.locator('input[type=file]:not([webkitdirectory])').setInputFiles([
    {
      name: 'unknown.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('committed once despite the lost reply')
    }
  ]);
  await plate.locator('[data-frame^=dropPlateGroup_]').waitFor();
  await plate
    .getByRole('button', { name: 'Add to queue', exact: true })
    .click();
  await queuePane(true);
  await queue.getByRole('button', { name: 'Commit all', exact: true }).click();
  await queuePane(false);
  await queue
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Result unknown' })
    .waitFor();
  assert.equal(
    lostWrites,
    1,
    'An uncertain write is never retried automatically'
  );
  await queue.locator('[data-frame^=commitQueueSelect_]').click();
  assert.equal(
    await queue
      .getByRole('button', { name: 'Commit all', exact: true })
      .isDisabled(),
    true
  );
  assert.equal(
    await queue.getByRole('button', { name: 'Retry', exact: true }).count(),
    0
  );
  await queue
    .getByRole('button', { name: 'Snapshot Browser', exact: true })
    .click();
  await snapshot.waitFor({ state: 'visible' });
  await snapshot.getByText('unknown.txt', { exact: true }).first().waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'PASS Drop Plate native sequence/UDIM, preparation without send, naming, explicit commit, description, Snapshot Browser and reload recovery'
  );
} catch (error) {
  await page?.screenshot({ path: output + '/checkin-failure.png' });
  console.log(
    'QUEUE',
    await page?.locator('.commit-queue:visible').allTextContents()
  );
  console.log(
    'NAMING',
    await page
      ?.locator('[data-frame=commitQueueNamingDetails]')
      .allTextContents()
  );
  console.log(
    'ROWS',
    await page
      ?.locator('[data-frame=commitQueueRows] > div > .frame-row')
      .allTextContents()
  );
  console.log(
    'PENDING',
    [...requests].map((row) => [row.url(), row.timing(), row.failure()])
  );
  console.log(
    'DIAGNOSTIC',
    await page
      ?.evaluate(() => {
        function find(node) {
          if (!node) return;
          if (node.component?.proxy?.activityProgress !== undefined)
            return node.component.proxy;
          return (
            find(node.component?.subTree) ||
            find(node.suspense?.activeBranch) ||
            (Array.isArray(node.children)
              ? node.children.map(find).find(Boolean)
              : undefined)
          );
        }
        const app = find(document.querySelector('#app')._vnode);
        return {
          progress: app?.activityProgress,
          busy: app?.busy,
          ping: app?.pingBusy,
          notifications: [
            ...document.querySelectorAll('.notification-card')
          ].map((row) => row.textContent)
        };
      })
      .catch((error) => error.message)
  );
  throw error;
} finally {
  await browser.close();
}
