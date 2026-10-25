import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';

const scenario = process.argv[4] ? JSON.parse(readFileSync(process.argv[4], 'utf8')) : {};
const external = scenario.project === 'agentfilm';
const project = scenario.project || 'one';
const title = scenario.title || 'Review shots';
const inspector = external ? 'description' : 'notes';
const expectedCount = Number(process.env.STREAM_CHECK_ROW_COUNT || (external ? 2 : 1));

const browser = await chromium.launch({ headless: true, channel: process.env.STREAM_BROWSER_CHANNEL });
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
page.setDefaultTimeout(15000);
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto(process.argv[2] + '/projects/' + project + '/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD || 'private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('banner').getByRole('button', { name: 'Open navigation', exact: true }).click();
  await page.getByRole('navigation', { name: 'Object types' }).getByRole('button', { name: title, exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false');
  const table = page.locator('.workspace-results .handler-table');
  await table.waitFor();
  await page.waitForFunction(count => document.querySelectorAll('.workspace-results .handler-table-row').length === count, expectedCount);
  assert.match(await table.innerText(), external ? /SH010/ : /Первый/);
  if (external) assert.match(await table.innerText(), /SH030/);
  assert.doesNotMatch(await table.innerText(), external ? /SH020/ : /O'Reilly|Archived|By id/);
  // Inspect the actual dock frame geometry rather than just the saved JSON.
  const resultsBox = await page.locator('[data-dock="results"]').boundingBox();
  const notesBox = await page.locator('[data-dock="' + inspector + '"]').boundingBox();
  assert.ok(resultsBox && notesBox && notesBox.x > resultsBox.x + resultsBox.width - 5);
  assert.ok(resultsBox.width > notesBox.width && Math.abs(resultsBox.y - notesBox.y) < 5);
  await page.screenshot({ path: process.argv[3] + '/page.png', animations: 'disabled' });
  await page.reload();
  await table.waitFor();
  await page.waitForFunction(count => document.querySelectorAll('.workspace-results .handler-table-row').length === count, expectedCount);
  assert.doesNotMatch(await table.innerText(), external ? /SH020/ : /O'Reilly|Archived|By id/);
  assert.deepEqual(errors, []);
  console.log('TS page opened from navigation with filtered rows, native table and dock panels; reload passed');
} catch (error) {
  await page.screenshot({ path: process.argv[3] + '/failure.png', animations: 'disabled' });
  throw error;
} finally {
  await browser.close();
}
