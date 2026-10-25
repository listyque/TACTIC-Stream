import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const base = process.argv[2], out = process.argv[3];
const project = process.env.STREAM_CHECK_PROJECT || 'one';
const title = process.env.STREAM_CHECK_DRAFT || 'Browser review';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: process.env.STREAM_BROWSER_CHANNEL });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, hasTouch: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })));
  await page.goto(base + '/projects/' + project + '/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).click();
  await page.locator('.settings-menu').getByRole('button', { name: 'Script Editor', exact: true }).click();
  const dialog = page.locator('.script-editor-dialog');
  await dialog.getByRole('button', { name: 'Agent drafts', exact: true }).click();
  const review = dialog.locator('.agent-drafts-review');
  await review.getByLabel('Agent draft', { exact: true }).selectOption({ label: title });
  await page.waitForFunction(() => document.querySelector('.agent-drafts-review')?.getAttribute('aria-busy') === 'false');
  assert.match(await review.getByLabel('Draft source', { exact: true }).inputValue(), /RESULT/);
  assert.match(await review.getByLabel('Isolated trial reports', { exact: true }).inputValue(), /allow: passed/);
  const activate = () => review.locator('[data-frame="agentDraftActivate"]');
  if (process.env.STREAM_CHECK_ACTIVATE === '1') {
    assert.ok(await activate().isDisabled());
    await review.getByRole('checkbox').check();
    await activate().tap();
    await review.getByRole('button', { name: 'Confirm activation on the desktop', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-frame="agentDraftStatus"]')?.textContent === 'Activated');
    assert.ok(await activate().isDisabled());
  }
  await page.screenshot({ path: out + '/agent-review.png' });
  if (process.env.STREAM_CHECK_ACTIVATE === '1') {
    await review.getByLabel('Agent draft', { exact: true }).selectOption({ label: 'Native review' });
    await page.waitForFunction(() => document.querySelector('.agent-drafts-review')?.getAttribute('aria-busy') === 'false');
    await review.evaluate(element => Object.assign(element.style, {flex:'none', width:'1000px', height:'700px'}));
    await page.waitForFunction(() => document.querySelector('[data-frame="agentDraftSource"]')?.getBoundingClientRect().width < 500);
    await review.screenshot({ path: out + '/paired-browser.png' });
    await review.evaluate(element => Object.assign(element.style, {flex:'', width:'', height:''}));
  }
  await page.setViewportSize({ width: 900, height: 700 });
  const source = await review.locator('[data-frame="agentDraftSource"]').boundingBox();
  const report = await review.locator('[data-frame="agentDraftReports"]').boundingBox();
  assert.ok(source && report && source.width > 0 && report.width > 0);
  await review.getByRole('button', { name: 'Back to editor', exact: true }).click();
  await dialog.getByLabel('Script source', { exact: true }).waitFor();
  await dialog.getByRole('button', { name: 'Agent drafts', exact: true }).click();
  await review.waitFor();
  assert.deepEqual(errors, []);
  console.log('Normal TS Script Editor: source/reports, back/reopen and narrow geometry passed; activation ' + (process.env.STREAM_CHECK_ACTIVATE === '1' ? 'tested' : 'left unchanged'));
} finally { await browser.close(); }
