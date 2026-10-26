import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const [base, output] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })));
  await page.goto(base + '/projects/one/?search_type=cg%2Fshot&view=table');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('banner').getByRole('button', { name: 'Open navigation', exact: true }).click();
  await page.getByRole('navigation', { name: 'Object types' }).getByRole('button', { name: 'Shots', exact: true }).first().click();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  const checks = page.getByRole('checkbox', { name: /Select record/ });
  await checks.nth(1).waitFor();
  const row = index => checks.nth(index).locator('xpath=ancestor::*[@role="row"][1]');
  const menu = page.getByRole('dialog', { name: 'Object actions', exact: true });
  const chat = page.locator('.agent-request-dialog');
  let opens = 0;
  async function open(index) {
    await row(index).click({ button: 'right' });
    await menu.screenshot({ path: output + '/object-menu-' + (++opens) + '.png' });
    await menu.getByRole('button', { name: 'External agent', exact: true }).click();
    await chat.getByRole('button', { name: 'Context details', exact: true }).click();
    return chat.locator('.agent-context-details').innerText();
  }
  await checks.nth(1).check();
  const first = await open(0);
  assert.ok(first.includes('SH001'), first);
  assert.ok(!first.includes('SH002'), first);
  await chat.getByRole('button', { name: 'Close', exact: true }).click();
  await checks.nth(0).check();await checks.nth(1).check();
  const both = await open(0);
  assert.ok(both.includes('SH001') && both.includes('SH002'), both);
  await chat.getByLabel('What should the agent do?', { exact: true }).fill('Keep this draft');
  await chat.getByRole('button', { name: 'Close', exact: true }).click();
  await checks.nth(0).uncheck();
  await row(1).click({ button: 'right' });
  await menu.getByRole('button', { name: 'External agent', exact: true }).click();
  assert.equal(await chat.getByLabel('What should the agent do?', { exact: true }).inputValue(), 'Keep this draft');
  await page.getByRole('region', { name: 'Notifications', exact: true }).getByText('Send or clear the current draft before opening another object', { exact: true }).waitFor();
  await chat.getByLabel('What should the agent do?', { exact: true }).fill('');
  const choosing = page.waitForEvent('filechooser');
  await chat.getByRole('button', { name: 'Attach files', exact: true }).click();
  await (await choosing).setFiles({ name: 'draft.txt', mimeType: 'text/plain', buffer: Buffer.from('Unsent draft') });
  await chat.locator('.agent-attachment-strip').getByText('draft.txt', { exact: true }).waitFor();
  await chat.getByRole('button', { name: 'Close', exact: true }).click();
  await row(1).click({ button: 'right' });
  await menu.getByRole('button', { name: 'External agent', exact: true }).click();
  await chat.locator('.agent-attachment-strip').getByText('draft.txt', { exact: true }).waitFor();
  assert.deepEqual(errors, []);
  await chat.screenshot({ path: output + '/object-menu-chat.png' });
  console.log('Basic context menu opens agent for clicked/selected objects and preserves unsent drafts');
} finally { await browser.close(); }
