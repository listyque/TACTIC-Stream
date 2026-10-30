import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const [base, output] = process.argv.slice(2);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 950 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(base + '/projects/one/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Configuration', exact: true })
    .click();
  const config = page.locator('.configuration-dialog');
  await config
    .locator('[data-frame=configurationNavigation]')
    .getByRole('button', { name: 'AI providers', exact: true })
    .click();
  const editor = config.locator('.agent-providers-embedded');
  assert.equal(await page.locator('.agent-providers-dialog').count(), 0);
  assert.equal(
    await config.locator('[data-frame=configurationApply]').count(),
    0
  );
  await editor
    .getByRole('combobox', { name: 'AI connection', exact: true })
    .waitFor();
  await editor
    .getByRole('button', { name: 'Check connection', exact: true })
    .click();
  await editor
    .getByText('Waiting for the external host', { exact: true })
    .waitFor();
  await editor.getByRole('button', { name: 'New', exact: true }).click();
  await page.waitForTimeout(2500);
  assert.equal(
    await editor
      .getByRole('combobox', { name: 'AI connection', exact: true })
      .inputValue(),
    ''
  );
  await config.locator('[data-frame=configurationPage_server]').click();
  await config.locator('[data-frame=configurationPage_ai]').click();
  assert.equal(
    await editor
      .getByRole('combobox', { name: 'AI connection', exact: true })
      .inputValue(),
    ''
  );
  await editor
    .getByRole('textbox', { name: 'Connection name', exact: true })
    .fill('Local fixture');
  await editor
    .getByRole('combobox', { name: 'Provider', exact: true })
    .selectOption('local');
  assert.equal(
    await editor
      .getByRole('textbox', { name: 'API base URL', exact: true })
      .inputValue(),
    'http://127.0.0.1:11434/v1'
  );
  const key = editor.getByLabel('API key', { exact: true });
  assert.equal(await key.getAttribute('type'), 'password');
  await key.fill('private-fixture');
  await config.locator('[data-frame=configurationPage_server]').click();
  await config.locator('[data-frame=configurationPage_ai]').click();
  assert.equal(await key.inputValue(), 'private-fixture');
  const saving = page.waitForResponse((response) => {
    if (
      !response.url().endsWith('/admin/rpc') ||
      response.request().method() !== 'POST'
    )
      return false;
    const args = response.request().postDataJSON()?.args;
    return (
      args?.[1]?.endsWith('AgentProviderCmd') && args[2]?.action === 'save'
    );
  });
  await editor.getByRole('button', { name: 'Save', exact: true }).click();
  const result = (await (await saving).json()).result;
  assert.equal(result.status, 'OK', result.description);
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame=agentProviderNotice]')
        ?.textContent === 'Connection has not been checked'
  );
  assert.equal(
    await editor.locator('[data-frame=agentProviderNotice]').innerText(),
    'Connection has not been checked'
  );
  assert.equal(await key.inputValue(), '');
  assert.ok((await editor.innerText()).includes('A key is stored'));
  await editor
    .getByRole('button', { name: 'Check connection', exact: true })
    .click();
  await editor
    .getByText('Waiting for the external host', { exact: true })
    .waitFor();
  for (const width of [520, 1000]) {
    await page.setViewportSize({ width: width + 60, height: 850 });
    await page.evaluate(() => document.fonts.ready);
    await editor.screenshot({
      path: output + '/web-providers-' + width + '.png'
    });
    const form = await editor.boundingBox();
    const button = await editor
      .getByRole('button', { name: 'Check connection', exact: true })
      .boundingBox();
    assert.ok(
      button.x >= form.x && button.x + button.width <= form.x + form.width
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'Configuration entry, real provider input, write-only key, preserved draft, check action and responsive editor passed'
  );
} finally {
  await browser.close();
}
