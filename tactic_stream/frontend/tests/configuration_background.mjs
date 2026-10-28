import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.setDefaultTimeout(15000);
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({language:'en',mode:'dark'})));
  await page.goto(process.argv[2] + '/projects/one/?search_type=contract/entity&view=table');
  await page.getByLabel('Login', {exact:true}).fill('admin');
  await page.getByLabel('Password', {exact:true}).fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', {name:'Sign in',exact:true}).click();
  const search = page.locator('.workspace-browser:visible');
  await search.waitFor();
  await page.waitForFunction(() => document.querySelector('.workspace-results')?.getAttribute('aria-busy') === 'false');
  const rows = search.locator('.handler-table-row:visible, .result-item:visible');
  await rows.first().waitFor();
  const content = () => rows.evaluateAll(items => items.map(el => {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('.app-icon').forEach(icon => icon.remove());
    return clone.textContent.replace(/\s+/g, ' ').trim();
  }));
  const before = await content();
  await page.getByLabel('More options', {exact:true}).click();
  await page.locator('.settings-menu').getByRole('button', {name:'Configuration',exact:true}).click();
  const configuration = page.locator('dialog[aria-labelledby="configuration-title"]');
  await configuration.waitFor();
  await configuration.getByRole('button', {name:'Minimize window',exact:true}).click();
  assert.equal(await search.isVisible(), true, 'Minimizing Configuration keeps the search visible');
  assert.deepEqual(await content(), before, 'Search contents survive opening Configuration');
  await configuration.getByRole('button', {name:'Restore window',exact:true}).click();
  await configuration.getByRole('button', {name:'Close',exact:true}).click();
  await configuration.waitFor({state:'hidden'});
  assert.deepEqual(await content(), before);
  assert.deepEqual(errors, []);
  console.log('PASS Configuration minimize/restore/close preserves the underlying search');
} finally { await browser.close(); }
