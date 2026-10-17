import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.setDefaultTimeout(20000);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
try {
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(process.argv[2] + '/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.project-picker').waitFor();
  await selectProject(page, '__create_project__');
  const wizard = page.locator('.project-creation-dialog');
  await wizard.getByLabel('Project title', { exact: true }).fill('Delivery CG');
  await wizard.getByLabel('Project code', { exact: true }).fill('delivery_cg');
  await wizard.getByRole('button', { name: 'Next', exact: true }).click();
  await wizard.getByRole('button', { name: 'Next', exact: true }).click();
  await wizard
    .getByRole('button', { name: 'Manage templates', exact: true })
    .click();
  const manager = page.locator('.project-templates');
  await manager
    .getByLabel('Template ZIP archive', { exact: true })
    .setInputFiles(process.argv[3]);
  await manager.getByText('niki_friends', { exact: true }).waitFor();
  await manager.getByRole('button', { name: 'Close', exact: true }).click();
  const source = wizard.getByRole('combobox', {
    name: 'Template',
    exact: true
  });
  await source
    .locator('option[value^="niki_friends|"]')
    .first()
    .waitFor({ state: 'attached' });
  const value = await source
    .locator('option')
    .evaluateAll(
      (rows) => rows.find((row) => row.value.startsWith('niki_friends|')).value
    );
  await source.selectOption(value);
  await wizard.getByRole('button', { name: 'Next', exact: true }).click();
  await page.screenshot({
    path: '../.screenshots/delivery-cg-create.png',
    animations: 'disabled'
  });
  await wizard
    .getByRole('button', { name: 'Create project', exact: true })
    .click();
  await wizard.waitFor({ state: 'hidden', timeout: 60000 });
  assert.equal(
    await page
      .getByLabel('Project', { exact: true })
      .getAttribute('data-project'),
    'delivery_cg'
  );
  assert.equal(new URL(page.url()).pathname, '/projects/delivery_cg/');
  assert.equal(new URL(page.url()).searchParams.has('tab'), false);
  await page.screenshot({
    path: '../.screenshots/delivery-cg-created.png',
    animations: 'disabled'
  });
  assert.deepEqual(errors, []);
  console.log(
    'CG ZIP uploaded and project created through the normal browser wizard'
  );
} finally {
  await browser.close();
}
