import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';

const base = process.argv[2], output = process.argv[3];
const project = process.env.STREAM_CHECK_PROJECT || 'one';
const live = process.env.STREAM_AGENT_LIVE === '1';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
let page;
try {
  page = await browser.newPage({ viewport: { width: 1440, height: 950 }, hasTouch: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })));
  await page.goto(base + '/projects/' + project + '/?search_type=' + encodeURIComponent(process.env.STREAM_AGENT_TYPE || 'cg/shot') + '&view=table');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('banner').getByRole('button', { name: 'Open navigation', exact: true }).tap();
  await writeFile(output + '/navigation.txt', await page.locator('body').innerText());
  await page.getByRole('navigation', { name: 'Object types' }).getByRole('button', { name: process.env.STREAM_AGENT_PAGE || 'Shots', exact: true }).first().tap();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).waitFor();
  await page.screenshot({ path: output + '/before-selection.png' });
  await writeFile(output + '/before-selection.txt', await page.locator('body').innerText());
  await page.getByRole('checkbox', { name: /Select record/ }).first().check();
  await page.getByLabel('More options', { exact: true }).click();
  await page.locator('.settings-menu').getByRole('button', { name: 'External agent', exact: true }).click();
  const dialog = page.locator('.agent-request-dialog');
  await dialog.waitFor();
  const originalBox = await dialog.boundingBox();
  await dialog.locator('header').focus();
  await page.keyboard.press('Alt+ArrowRight');
  assert.ok((await dialog.boundingBox()).x > originalBox.x);
  await dialog.getByRole('button', { name: 'Maximize window', exact: true }).click();
  assert.equal(Math.round((await dialog.boundingBox()).width), 1440);
  await dialog.getByRole('button', { name: 'Restore window', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('connected'));
  const context = await dialog.getByLabel('Context sent to the agent').inputValue();
  assert.ok(context.includes(project), context);
  assert.ok(context.includes('SH'), context);
  await dialog.getByLabel('What should the agent do?').fill(process.env.STREAM_AGENT_PROMPT || 'Explain the selected shots');
  await dialog.getByRole('checkbox', { name: 'Allow the requested configuration changes' }).check();
  await dialog.getByRole('button', { name: 'Send to agent', exact: true }).tap();
  await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('queued') || document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('working') || document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('completed'));
  if (live) {
    await page.waitForFunction(() => /Request (completed|failed|interrupted)/.test(document.querySelector('[data-frame="agentRequestStatus"]')?.textContent || ''), undefined, { timeout: 1200000 });
    const status = await dialog.locator('[data-frame="agentRequestStatus"]').textContent();
    const answer = await dialog.getByLabel('Agent progress and answer').inputValue();
    await writeFile(output + '/live-answer.txt', answer);
    assert.match(status, /completed/, answer);
  } else {
    await dialog.getByRole('button', { name: 'Cancel request', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('cancelled'));
  }
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).click();
  await page.locator('.settings-menu').getByRole('button', { name: 'External agent', exact: true }).click();
  assert.equal(await dialog.getByLabel('Context sent to the agent').inputValue(), context);
  for (const width of [520, 1000]) {
    await dialog.evaluate((element, width) => Object.assign(element.style, { width: width + 'px', height: '700px', maxWidth: 'none', maxHeight: 'none' }), width);
    assert.ok((await dialog.getByLabel('Agent progress and answer').boundingBox()).height > 0);
  }
  await page.setViewportSize({ width: 360, height: 760 });
  await page.waitForFunction(() => {
    const dialog = document.querySelector('.agent-request-dialog');
    return dialog.scrollWidth <= dialog.clientWidth;
  });
  assert.ok(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth));
  await dialog.screenshot({ path: output + '/phone.png' });
  await page.setViewportSize({ width: 1440, height: 950 });
  if (!live) {
    await dialog.locator('.agent-request-body').evaluate(element => Object.assign(element.style, { flex: 'none', width: '1000px', height: '650px' }));
  }
  await dialog.locator('.agent-request-body').screenshot({ path: output + '/browser.png' });
  assert.deepEqual(errors, []);
  console.log('Native TS entry, context, touch submit, status, history/reopen and narrow geometry passed' + (live ? '; real external model completed' : ''));
} catch(error) {
  if(page) {
    await page.screenshot({ path: output + '/failure.png' });
    await writeFile(output + '/failure.txt', await page.locator('body').innerText());
  }
  throw error;
} finally {
  await browser.close();
}
