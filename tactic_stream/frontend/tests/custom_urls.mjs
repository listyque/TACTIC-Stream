import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';
import {
  addressProject,
  customUrlLocation
} from '../src/features/workspace/links.js';

const base = process.argv[2];
assert.equal(addressProject(new URL(base + '/projects/one/review/A')), 'one');
assert.equal(addressProject(new URL(base + '/tactic/one/review/A')), 'one');
assert.equal(addressProject(new URL(base + '/admin/')), '');
assert.equal(customUrlLocation(new URL(base + '/projects/one/')), null);
assert.equal(
  customUrlLocation(new URL(base + '/projects/one/#/review/A?q=x')).parameters
    .q,
  'x'
);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 950 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('response', async (response) => {
    if (response.status() >= 400)
      console.log(
        response.status(),
        new URL(response.url()).pathname,
        await response.text()
      );
  });
  page.setDefaultTimeout(15000);
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    )
  );
  await page.goto(base + '/projects/one/review/A');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page
    .locator('.configured-view[data-workspace-current="true"]')
    .waitFor();
  await page.waitForFunction(() =>
    document
      .querySelector('.configured-view[data-workspace-current="true"]')
      ?.textContent.includes('A')
  );
  assert.equal(new URL(page.url()).pathname, '/projects/one/review/A');
  await page.reload();
  await page
    .locator('.configured-view[data-workspace-current="true"]')
    .waitFor();
  assert.equal(new URL(page.url()).pathname, '/projects/one/review/A');
  await page.goto(base + '/tactic/one/review/A');
  await page
    .locator('.configured-view[data-workspace-current="true"]')
    .waitFor();
  assert.equal(new URL(page.url()).pathname, '/tactic/one/review/A');
  await page.goto(base + '/projects/one/#/review/A');
  await page
    .locator('.configured-view[data-workspace-current="true"]')
    .waitFor();
  assert.equal(new URL(page.url()).hash, '#/review/A');
  await page.goto(base + '/projects/one/layout');
  try {
    await page.getByText('Custom URL layout result', { exact: true }).waitFor();
  } catch (error) {
    await page.screenshot({
      path: process.env.STREAM_CHECK_OUTPUT + '/layout-error.png'
    });
    console.log((await page.locator('body').innerText()).slice(-3000));
    throw error;
  }
  await page.screenshot({
    path: process.env.STREAM_CHECK_OUTPUT + '/custom-layout.png'
  });
  await page.keyboard.press('Escape');
  await page.goto(base + '/projects/one/dashboard/agent_workspace');
  await page.getByText('Project instructions', { exact: true }).waitFor();
  const body = page.locator('.table-document-body');
  await body.evaluate((element) => {
    element.style.width = '1000px';
    element.style.height = '650px';
    element.style.flex = 'none';
    element.closest('dialog').style.width = '1032px';
    element.closest('dialog').style.height = '730px';
  });
  await body.locator('.document-pane').waitFor();
  await page.evaluate(() => document.fonts.ready);
  const geometry = await body.boundingBox();
  await writeFile(
    process.env.STREAM_CHECK_OUTPUT + '/paired-geometry.json',
    JSON.stringify(geometry)
  );
  await body.screenshot({
    path: process.env.STREAM_CHECK_OUTPUT + '/web-dashboard.png'
  });
  assert.ok((await body.innerText()).includes('Records: 1'));
  await page.keyboard.press('Escape');
  await page.goto(base + '/projects/one/review/A');
  await page.getByLabel('More options', { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'External agent', exact: true })
    .click();
  const chat = page.locator('.agent-request-dialog');
  await chat.screenshot({
    path: process.env.STREAM_CHECK_OUTPUT + '/chat-entry.png'
  });
  await writeFile(
    process.env.STREAM_CHECK_OUTPUT + '/chat-entry.txt',
    await chat.innerText()
  );
  await writeFile(
    process.env.STREAM_CHECK_OUTPUT + '/chat-entry-aria.txt',
    await chat.ariaSnapshot()
  );
  await chat.getByLabel('Agent permissions', { exact: true }).click();
  await chat.getByText('MCP connections', { exact: true }).click();
  const mcp = page.locator('.agent-mcp-dialog');
  await mcp.locator('[data-frame=mcpTitle]').fill('Tracker browser');
  await mcp
    .getByRole('button', { name: 'Select read tools', exact: true })
    .click();
  assert.equal(
    await mcp.locator('[data-frame=mcpTitle]').inputValue(),
    'Tracker browser'
  );
  await mcp
    .getByRole('button', { name: 'Create connection', exact: true })
    .click();
  await mcp.locator('[data-frame=mcpIssued]').waitFor();
  assert.match(
    await mcp.locator('[data-frame=mcpIssued]').inputValue(),
    /Bearer /
  );
  const invitation = await mcp
    .locator('[data-frame=mcpAgentLink]')
    .inputValue();
  assert.match(invitation, /#access_token=[A-Za-z0-9_-]+$/);
  const connectionId = new URL(invitation).pathname.split('/').at(-1);
  await mcp.screenshot({
    path: process.env.STREAM_CHECK_OUTPUT + '/web-mcp.png'
  });
  await mcp.getByRole('button', { name: 'Close', exact: true }).click();
  await chat.getByLabel('Agent permissions', { exact: true }).click();
  await chat.getByText('MCP connections', { exact: true }).click();
  await mcp.locator('[data-frame=mcpTitle]').waitFor();
  assert.equal(await mcp.locator('[data-frame=mcpIssued]').count(), 0);
  await mcp.getByRole('button', { name: 'Close', exact: true }).click();
  await chat.getByRole('button', { name: 'Close', exact: true }).click();
  await page.goto(base + '/projects/one/?agent_mcp=' + connectionId);
  await mcp.locator('[data-frame=mcpTitle]').waitFor();
  await mcp.getByText(/Tracker browser ·/).waitFor();
  assert.equal(await mcp.locator('[data-frame=mcpAgentLink]').count(), 0);
  await mcp.getByRole('button', { name: 'Close', exact: true }).click();
  await page.goto(base + '/projects/one/not-configured');
  await page
    .locator('#workspace-data [role="alert"]')
    .filter({ hasText: 'Custom URL is not configured: /not-configured' })
    .waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'Custom URLs, native dashboard/Markdown, real MCP window creation, token clearing and missing route passed'
  );
} finally {
  await browser.close();
}
