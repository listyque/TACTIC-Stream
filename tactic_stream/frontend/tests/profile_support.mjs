import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const base = process.argv[2];
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    hasTouch: true
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    base + '/projects/one/?search_type=contract/entity&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Account', { exact: true }).click();
  await page.getByRole('button', { name: 'My Profile', exact: true }).click();
  const profile = page.getByRole('dialog', {
    name: 'User profile',
    exact: true
  });
  const editor = page.getByRole('dialog', {
    name: 'Edit user profile',
    exact: true
  });
  const idle = () =>
    page.waitForFunction(
      () =>
        document
          .querySelector('.user-profile-window')
          ?.getAttribute('aria-busy') === 'false'
    );
  await idle();
  const edit = async () => {
    await profile
      .getByRole('button', { name: 'Edit user profile', exact: true })
      .click();
    await editor.waitFor();
  };
  await edit();
  await editor.getByLabel('Address', { exact: true }).fill('Fixture studio');
  assert.equal(
    await editor
      .getByLabel('New password — leave empty to keep current', { exact: true })
      .count(),
    1
  );
  await editor.getByRole('button', { name: 'Cancel', exact: true }).click();
  await editor
    .getByRole('button', { name: 'Keep editing', exact: true })
    .click();
  assert.equal(
    await editor.getByLabel('Address', { exact: true }).inputValue(),
    'Fixture studio'
  );
  await editor.getByRole('button', { name: 'Save', exact: true }).click();
  await editor.waitFor({ state: 'hidden' });
  await idle();
  await edit();
  assert.equal(
    await editor.getByLabel('Address', { exact: true }).inputValue(),
    'Fixture studio'
  );
  await editor.getByLabel('Department', { exact: true }).fill('Discarded');
  await page.keyboard.press('Escape');
  await editor
    .getByRole('button', { name: 'Discard changes', exact: true })
    .click();
  await edit();
  assert.equal(
    await editor.getByLabel('Department', { exact: true }).inputValue(),
    ''
  );
  let writes = 0;
  const lostResponse = async (route) => {
    writes++;
    await route.fetch();
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Fixture lost response' })
    });
  };
  await page.route('**/admin/user-profile/save', lostResponse);
  await editor
    .getByLabel('Address', { exact: true })
    .fill('Committed despite lost response');
  await editor.getByRole('button', { name: 'Save', exact: true }).click();
  await editor
    .getByRole('button', { name: 'Reload from server', exact: true })
    .waitFor();
  assert.equal(
    await editor
      .getByRole('button', { name: 'Save', exact: true })
      .isDisabled(),
    true
  );
  assert.equal(
    await editor
      .getByLabel('New password — leave empty to keep current', { exact: true })
      .inputValue(),
    ''
  );
  assert.equal(writes, 1, 'Unknown mutation result cannot be resubmitted');
  await page.unroute('**/admin/user-profile/save', lostResponse);
  await editor
    .getByRole('button', { name: 'Reload from server', exact: true })
    .click();
  await editor.waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="profileField_address"]')?.value ===
      'Committed despite lost response'
  );
  await editor.getByRole('button', { name: 'Cancel', exact: true }).click();
  await profile
    .getByRole('button', { name: 'Edit group membership', exact: true })
    .click();
  const groups = page.getByRole('dialog', {
    name: 'Edit group membership',
    exact: true
  });
  await groups.waitFor();
  assert((await groups.getByRole('checkbox').count()) > 0);
  await groups.getByRole('radio', { name: 'Profile', exact: true }).click();
  await editor.getByLabel('Address', { exact: true }).fill('Both editor pages');
  await editor.getByRole('radio', { name: 'Groups', exact: true }).click();
  await groups.getByRole('button', { name: 'Save', exact: true }).click();
  await groups.waitFor({ state: 'hidden' });
  await idle();
  await edit();
  assert.equal(
    await editor.getByLabel('Address', { exact: true }).inputValue(),
    'Both editor pages'
  );
  await editor.getByRole('button', { name: 'Cancel', exact: true }).click();
  await profile
    .getByRole('button', { name: 'Close profile', exact: true })
    .click();
  assert.deepEqual(errors, []);
  console.log(
    'PASS profile address/password, immutable field drafts, dirty Escape/discard, persisted save/reopen, unknown-write lock/reload and membership editor'
  );
} finally {
  await browser.close();
}
