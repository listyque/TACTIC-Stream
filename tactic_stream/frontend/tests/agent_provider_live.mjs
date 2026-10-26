import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const [base, output] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  const errors = [];
  let requestId;
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (!request.url().endsWith('/admin/rpc') || request.method() !== 'POST') return;
    const args = request.postDataJSON()?.args;
    if (args?.[1]?.endsWith('AgentRequestCmd') && args[2]?.action === 'submit') requestId = args[2].request_id;
  });
  await page.addInitScript(() => localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' })));
  await page.goto(base + '/projects/cg_test/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).click();
  await page.locator('.settings-menu').getByRole('button', { name: 'External agent', exact: true }).click();
  const dialog = page.locator('.agent-request-dialog');
  await dialog.getByRole('combobox', { name: 'AI connection', exact: true }).selectOption('codex');
  await dialog.getByRole('combobox', { name: 'Model', exact: true }).selectOption('gpt-6.1-sol');
  const effort = dialog.getByRole('combobox', { name: 'Reasoning effort', exact: true });
  if (await effort.count()) await effort.selectOption('low');
  await dialog.getByRole('button', { name: 'AI providers', exact: true }).click();
  const editor = page.locator('.agent-providers-dialog');
  await editor.getByText('Codex uses the account signed in on the external host. Provider API keys are not required.', { exact: true }).waitFor();
  await editor.getByRole('button', { name: 'Close', exact: true }).click();
  await dialog.getByLabel('What should the agent do?', { exact: true }).fill('Проверка подключения. Вызови agent_context один раз и сообщи название текущего проекта и страницы. Ничего не изменяй.');
  assert.equal(await dialog.getByRole('checkbox', { name: 'Allow requested changes', exact: true }).isChecked(), false);
  await dialog.getByRole('button', { name: 'Send to agent', exact: true }).click();
  await page.waitForFunction(() => /Task completed|Task blocked|Request (failed|interrupted)/.test(document.querySelector('[data-frame=agentRequestStatus]')?.textContent || ''), undefined, { timeout: 180000 });
  const status = await dialog.locator('[data-frame=agentRequestStatus]').innerText();
  const answer = await dialog.getByRole('log', { name: 'Conversation' }).innerText();
  await writeFile(output + '/live-chat.json', JSON.stringify({ requestId, status, answer, errors }, null, 2));
  assert.ok(status.includes('Task completed'), status + '\n' + answer);
  assert.deepEqual(errors, []);
  await dialog.screenshot({ path: output + '/live-chat.png' });
  console.log('Real Codex request completed from normal web chat, with explicit connection/model selection and read-only authorization');
} finally {
  await browser.close();
}
