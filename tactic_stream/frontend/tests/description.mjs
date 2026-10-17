import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || undefined
});
const page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
page.setDefaultTimeout(12000);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const [base, output, keyA, keyB, snapshotKey] = process.argv.slice(2);
const panel = page.locator('[data-dock="description"]'),
  editor = panel.getByRole('textbox', { name: 'Description', exact: true });
const states = {};
let hold = false,
  reject = false,
  resume;
async function settled() {
  await page.waitForFunction(
    () =>
      document.querySelector(
        '[data-dock="description"] button[aria-label="Edit description"]'
      )?.disabled === false
  );
}
async function image(state) {
  await page.evaluate(() => document.fonts.ready);
  if (!output) return;
  states[state] = {
    title: (await panel.getByRole('region').count())
      ? await panel.getByRole('region').first().getAttribute('aria-label')
      : 'Description'
  };
  await writeFile(
    output + '/browser-state.json',
    JSON.stringify(states, null, 2)
  );
  // Isolate the rendered component at the native fixture size without resizing live docks.
  const frame = page.locator('#description-reference-fixture');
  try {
    for (const [width, height] of [
      [440, 340],
      [720, 420]
    ]) {
      await panel.locator('.description-editor').evaluate(
        (element, { width, height }) => {
          document.getElementById('description-reference-fixture')?.remove();
          const copy = element.cloneNode(true);
          copy.id = 'description-reference-fixture';
          Object.assign(copy.style, {
            position: 'fixed',
            left: '0px',
            top: '0px',
            width: width + 'px',
            height: height + 'px',
            zIndex: '10000'
          });
          if (element.querySelector('textarea'))
            copy.querySelector('textarea').value =
              element.querySelector('textarea').value;
          document.body.append(copy);
        },
        { width, height }
      );
      await frame.screenshot({
        path: `${output}/stream-${state}-${width}.png`,
        animations: 'disabled'
      });
    }
  } finally {
    await frame.evaluate((element) => element.remove());
  }
}
async function read(key) {
  return page.evaluate(
    async ({ key, base }) => {
      const session = JSON.parse(localStorage.getItem('tactic_stream.session'));
      const code = new URLSearchParams(key.split('?')[1]).get('code');
      const response = await fetch(base + '/admin/rpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: 'query',
          args: [
            { ticket: session.ticket, project: 'one' },
            key.split('?')[0],
            [['code', code]]
          ]
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      return result.result[0].description;
    },
    { key, base }
  );
}
try {
  if (output) await mkdir(output, { recursive: true });
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(base + '/projects/one/?search_type=one%2Fdescription_assets');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const row = (title) =>
    page
      .locator('.workspace-results .result-item:visible')
      .filter({ hasText: title })
      .first();
  await row('Description A').waitFor();
  await page.getByLabel('Workspace panels', { exact: true }).click();
  await page.getByLabel('Browsing', { exact: true }).click();
  await page
    .getByRole('menuitemradio', { name: 'Description', exact: true })
    .click();
  await panel.waitFor({ state: 'visible' });
  await image('empty');
  await row('Description A').click();
  await panel.getByText('Original description', { exact: true }).waitFor();
  await image('read');
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  await editor.fill('Prepared description');
  await image('edit');
  await row('Description B').click();
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  await editor.fill('Draft B');
  await panel
    .getByRole('combobox', { name: 'Retained description drafts', exact: true })
    .click();
  await page
    .getByRole('option', { name: 'Description A', exact: true })
    .click();
  assert.equal(
    await editor.inputValue(),
    'Prepared description',
    'Selection retains independent drafts'
  );
  await panel
    .getByRole('button', { name: 'Use this text for check-in', exact: true })
    .click();
  await panel.getByText('Used for check-in', { exact: true }).waitFor();
  await image('pinned');
  await row('Description B').click();
  assert.equal(
    await editor.inputValue(),
    'Prepared description',
    'Pin follows selection'
  );
  await row('Description B').click({ button: 'right' });
  await page
    .getByRole('dialog', { name: 'Object actions', exact: true })
    .getByRole('button', { name: 'Save snapshot', exact: true })
    .click();
  const checkin = page.getByRole('dialog', {
    name: 'Save snapshot',
    exact: true
  });
  assert.equal(
    await checkin.getByLabel('Description', { exact: true }).inputValue(),
    'Prepared description',
    'Pinned text reaches native check-in form'
  );
  await checkin.getByRole('button', { name: 'Close', exact: true }).click();
  await panel
    .getByRole('button', {
      name: 'Stop using this text for check-in',
      exact: true
    })
    .click();
  await panel.getByText('Original B', { exact: true }).waitFor();
  await panel
    .getByRole('combobox', { name: 'Retained description drafts', exact: true })
    .click();
  await page
    .getByRole('option', { name: 'Description B', exact: true })
    .click();
  assert.equal(
    await editor.inputValue(),
    'Draft B',
    'Unpin keeps the separate retained draft'
  );
  await panel
    .getByRole('button', { name: 'Discard changes', exact: true })
    .click();
  await row('Description A').click();
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  await editor.fill('Saved description');
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (body.method === 'update' && body.args[1] === keyA && hold) {
      hold = false;
      await new Promise((resolve) => {
        resume = resolve;
      });
    }
    if (reject && body.method === 'update' && body.args[1] === keyA) {
      reject = false;
      await route.fulfill({
        status: 400,
        json: { error: 'Unable to save description', error_code: 'test_error' }
      });
    } else await route.continue();
  });
  hold = true;
  await panel
    .getByRole('button', { name: 'Save description', exact: true })
    .click();
  await panel.getByText('Saving…', { exact: true }).waitFor();
  await image('saving');
  resume();
  await settled();
  await panel.getByText('Saved description', { exact: true }).waitFor();
  assert.equal(await read(keyA), 'Saved description');
  reject = true;
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  await editor.fill('Retry description');
  await panel
    .getByRole('button', { name: 'Save description', exact: true })
    .click();
  await panel
    .getByRole('alert')
    .filter({ hasText: 'Unable to save description' })
    .waitFor();
  assert.equal(await editor.inputValue(), 'Retry description');
  assert.equal(
    await read(keyA),
    'Saved description',
    'Failed save does not alter the record'
  );
  await image('error');
  await panel
    .getByRole('button', { name: 'Save description', exact: true })
    .click();
  await settled();
  await panel.getByText('Retry description', { exact: true }).waitFor();
  assert.equal(await read(keyA), 'Retry description');
  assert.equal(
    await read(keyB),
    'Original B',
    'Pin never saves into the selected object'
  );
  await row('Description A')
    .getByRole('button', { name: 'Expand item', exact: true })
    .click();
  const process = page
    .locator('.workspace-results .result-item-process:visible')
    .filter({ has: page.getByText('Publish', { exact: true }) })
    .first();
  await process.click();
  await panel.getByText('Process description', { exact: true }).waitFor();
  await image('process');
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  assert.equal(
    await panel
      .getByRole('button', { name: 'Save description', exact: true })
      .isDisabled(),
    true,
    'Process text has no writable sobject key'
  );
  await panel
    .getByRole('button', { name: 'Discard changes', exact: true })
    .click();
  const snapshot = page
    .locator('.workspace-results .result-item-snapshot:visible')
    .first();
  await snapshot.click();
  await panel.getByText('Snapshot description', { exact: true }).waitFor();
  await image('snapshot');
  await panel
    .getByRole('button', { name: 'Edit description', exact: true })
    .click();
  await editor.fill('Updated snapshot description');
  await panel
    .getByRole('button', { name: 'Save description', exact: true })
    .click();
  await settled();
  await panel
    .getByText('Updated snapshot description', { exact: true })
    .waitFor();
  assert.equal(await read(snapshotKey), 'Updated snapshot description');
  await panel
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .click();
  assert.ok((await panel.boundingBox()).width > 1300);
  await panel
    .getByRole('button', { name: 'Restore panel', exact: true })
    .click();
  await panel.getByRole('button', { name: 'Help', exact: true }).click();
  await page
    .getByRole('dialog', { name: 'Help', exact: true })
    .getByRole('heading', { name: 'Description dock', exact: true })
    .waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'Description: native update, independent drafts, pin/unpin and check-in, failed save/retry, dock maximize passed'
  );
} catch (failure) {
  if (output) {
    await page.screenshot({ path: output + '/failure.png' });
    await writeFile(output + '/failure.html', await page.content());
  }
  throw failure;
} finally {
  await browser.close();
}
