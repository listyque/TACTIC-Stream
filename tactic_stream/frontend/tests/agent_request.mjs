import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';

const base = process.argv[2], output = process.argv[3];
const project = process.env.STREAM_CHECK_PROJECT || 'one';
const live = process.env.STREAM_AGENT_LIVE === '1';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
let page;
let fixtureAuth;
try {
  page = await browser.newPage({ viewport: { width: 1440, height: 950 }, hasTouch: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().endsWith('/admin/rpc') && request.method() === 'POST') {
      const payload = request.postDataJSON();
      if (payload?.method === 'execute_cmd') fixtureAuth = payload.args[0];
    }
  });
  async function fixtureCommand(action, values = {}) {
    const response = await page.request.post(base + '/admin/rpc', { data: { method: 'execute_cmd', args: [fixtureAuth,
      'tactic.ui.panel.agent_request_cmd.AgentRequestCmd', { action, project_code: project, ...values }], kwargs: {} } });
    const result = (await response.json()).result;
    assert.equal(result.status, 'OK');
    return typeof result.info === 'string' ? JSON.parse(result.info) : result.info;
  }
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
  if (!live) {
    await dialog.getByRole('combobox', { name: 'Model', exact: true }).selectOption('fixture');
    await dialog.getByRole('combobox', { name: 'Reasoning effort', exact: true }).selectOption('high');
    const chooser = page.waitForEvent('filechooser');
    await dialog.getByRole('button', { name: 'Attach files', exact: true }).click();
    await (await chooser).setFiles({ name: 'reference.txt', mimeType: 'text/plain', buffer: Buffer.from('Reference file') });
    await dialog.locator('.agent-attachment-strip').getByText('reference.txt', { exact: true }).waitFor();
    await dialog.locator('.agent-request-body').evaluate(element => {
      const transfer = new DataTransfer();
      transfer.items.add(new File(['Dropped file'], 'dropped.bin', { type: 'application/octet-stream' }));
      element.dispatchEvent(new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true }));
    });
    await dialog.locator('.agent-attachment-strip').getByText('dropped.bin', { exact: true }).waitFor();
    await dialog.getByLabel('What should the agent do?', { exact: true }).evaluate(element => {
      const transfer = new DataTransfer();
      const bytes = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII='), char => char.charCodeAt(0));
      transfer.items.add(new File([bytes], 'clipboard.png', { type: 'image/png' }));
      element.dispatchEvent(new ClipboardEvent('paste', { clipboardData: transfer, bubbles: true, cancelable: true }));
    });
    await dialog.locator('.agent-attachment-strip img').waitFor();
    assert.equal(await dialog.locator('.agent-attachment-chip').count(), 3);
  }
  const originalBox = await dialog.boundingBox();
  await dialog.locator('header').focus();
  await page.keyboard.press('Alt+ArrowRight');
  assert.ok((await dialog.boundingBox()).x > originalBox.x);
  await dialog.getByRole('button', { name: 'Maximize window', exact: true }).click();
  assert.equal(Math.round((await dialog.boundingBox()).width), 1440);
  await dialog.getByRole('button', { name: 'Restore window', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('connected'));
  await dialog.getByRole('button', { name: 'Context details', exact: true }).click();
  const context = await dialog.locator('.agent-context-details').textContent();
  assert.ok(context.includes(project), context);
  assert.ok(context.includes('SH'), context);
  await dialog.getByLabel('What should the agent do?').fill(process.env.STREAM_AGENT_PROMPT || 'Explain the selected shots');
  if (!live) await dialog.getByLabel('What should the agent do?').fill('');
  assert.equal(await dialog.getByRole('checkbox', { name: 'Allow requested changes' }).count(),0);
  await dialog.getByLabel('Agent permissions',{exact:true}).click();
  await page.getByRole('menuitemcheckbox',{name:'Allow requested changes',exact:true}).click();
  if (!live) {
    await dialog.getByLabel('Agent permissions',{exact:true}).click();
    await page.getByRole('menuitemcheckbox',{name:'Allow internet access',exact:true}).click();
  }
  await dialog.getByRole('button', { name: 'Send to agent', exact: true }).tap();
  await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('queued') || document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('working') || document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('completed'));
  if (live) {
    await page.waitForFunction(() => /Task completed|Task blocked|Request (failed|interrupted)/.test(document.querySelector('[data-frame="agentRequestStatus"]')?.textContent || ''), undefined, { timeout: 1200000 });
    const status = await dialog.locator('[data-frame="agentRequestStatus"]').textContent();
    const answer = await dialog.getByRole('log', { name: 'Conversation' }).innerText();
    await writeFile(output + '/live-answer.txt', answer);
    assert.match(status, /completed/, answer);
  } else {
    const host_id = process.env.STREAM_FIXTURE_HOST_ID;
    assert.ok(host_id);
    const claimed = (await fixtureCommand('claim', { host_id })).request;
    await fixtureCommand('update', { host_id, request_id: claimed.request_id, event: 'ts_attachment_checkin: inProgress' });
    await dialog.getByText('Checking in attached files · Working', { exact: true }).waitFor();
    const activityBox = await dialog.locator('.agent-tool-progress').boundingBox();
    const transcriptBox = await dialog.getByRole('log').boundingBox();
    assert.ok(Math.abs((activityBox.x + activityBox.width / 2) - (transcriptBox.x + transcriptBox.width / 2)) < 20);
    assert.equal(claimed.model, 'fixture');
    assert.equal(claimed.effort, 'high');
    assert.equal(claimed.document.prompt, '');
    assert.equal(claimed.document.allow_web, true);
    await dialog.getByLabel('Agent permissions',{exact:true}).click();
    assert.ok(await page.getByRole('menuitemcheckbox',{name:'Allow requested changes',exact:true}).isDisabled());
    assert.ok(await page.getByRole('menuitemcheckbox',{name:'Allow internet access',exact:true}).isDisabled());
    await page.keyboard.press('Escape');
    assert.equal(await dialog.locator('.agent-message-image').count(), 1);
    assert.ok(await dialog.getByRole('combobox', { name: 'Reasoning effort', exact: true }).isDisabled());
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('working'));
    const workingStatus = dialog.getByRole('log').locator('[data-frame=agentRequestStatusRow]');
    const statusBox = await workingStatus.boundingBox();
    assert.ok(statusBox.y >= transcriptBox.y && statusBox.y + statusBox.height <= transcriptBox.y + transcriptBox.height);
    assert.ok(Math.abs(statusBox.x - activityBox.x) < 1);
    await dialog.getByRole('log').screenshot({ path: output + '/working-browser.png' });
    await dialog.getByLabel('Add a correction while the agent works', { exact: true }).fill('Use the reference process');
    await dialog.getByRole('button', { name: 'Send correction', exact: true }).click();
    const corrected = await fixtureCommand('read', { request_id: claimed.request_id });
    const correction = corrected.messages.find(message => message.text === 'Use the reference process');
    assert.ok(correction);
    await fixtureCommand('ack', { host_id, request_id: claimed.request_id, message_ids: [correction.id] });
    let offline=true, replayed=0;
    const disconnect=async route=>{
      const payload=route.request().postDataJSON();
      if (payload?.method==='execute_cmd' && payload.args[1].endsWith('.AgentRequestCmd')) {
        const action=payload.args[2].action;
        if (['submit','message'].includes(action)) replayed++;
        if (offline && ['state','library','read'].includes(action)) return route.abort('connectionfailed');
      }
      return route.continue();
    };
    await page.route('**/admin/rpc',disconnect);
    await page.waitForFunction(()=>document.querySelector('[data-frame=agentRequestStatus]')?.textContent.includes('Failed to fetch'));
    await fixtureCommand('update', { host_id, request_id: claimed.request_id, status: 'completed', outcome: 'completed',
      answer: '**Completed**\n\n- Workflow saved\n- References checked in\n\n`reference → model → texture → rig`' });
    offline=false;
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('Task completed'));
    assert.equal(replayed,0,'Reconnection only reads; it never replays a mutation');
    await page.unroute('**/admin/rpc',disconnect);
    assert.equal(await dialog.getByRole('log').locator('strong').textContent(), 'Completed');
    await dialog.getByRole('combobox', { name: 'Model', exact: true }).selectOption('');
    assert.equal(await dialog.getByRole('combobox', { name: 'Reasoning effort', exact: true }).inputValue(), '');
    await dialog.getByRole('combobox', { name: 'Reasoning effort', exact: true }).selectOption('low');
    await dialog.getByLabel('What should the agent do?', { exact: true }).fill('Thank you, summarize the result');
    await dialog.getByRole('button', { name: 'Send to agent', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('queued'));
    const followup = await fixtureCommand('read', { request_id: claimed.request_id });
    assert.equal(followup.model, '');
    assert.equal(followup.effort, 'low');
    await dialog.getByRole('button', { name: 'Cancel request', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('cancelled'));
    const desktop = await page.context().newCDPSession(page);
    await desktop.send('Emulation.setTouchEmulationEnabled', { enabled: false });
    const prompt = dialog.getByLabel('What should the agent do?', { exact: true });
    await prompt.fill('Keep a line');
    await prompt.press('Shift+Enter');
    assert.match(await prompt.inputValue(), /\n/);
    await prompt.fill('Send with Enter');
    await prompt.press('Enter');
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('queued'));
    await dialog.getByRole('button', { name: 'Cancel request', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-frame="agentRequestStatus"]')?.textContent.includes('cancelled'));
  }
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await page.getByLabel('More options', { exact: true }).click();
  await page.locator('.settings-menu').getByRole('button', { name: 'External agent', exact: true }).click();
  assert.equal(await dialog.locator('.agent-context-details').textContent(), context);
  for (const width of [520, 1000]) {
    await dialog.evaluate((element, width) => Object.assign(element.style, { width: width + 'px', height: '700px', maxWidth: 'none', maxHeight: 'none' }), width);
    assert.ok((await dialog.getByRole('log', { name: 'Conversation' }).boundingBox()).height > 0);
    const answer = await dialog.locator('.agent-message.assistant').first().boundingBox();
    const details = await dialog.locator('.agent-tool-progress').boundingBox();
    assert.ok(Math.abs(answer.x - details.x) <= 1, 'Operation details follow the assistant column');
    assert.ok(Math.abs(answer.width - details.width) <= 1);
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
  if(page && await page.locator('.agent-request-dialog').count()) {
    await writeFile(output + '/geometry.json', JSON.stringify(await page.locator('.agent-request-dialog').evaluate(element => [...element.querySelectorAll('.agent-request-body,.frame-view,[data-frame]')].slice(0,24).map(item => ({name:item.dataset.frame || item.className,box:item.getBoundingClientRect().toJSON(),style:item.getAttribute('style')}))),null,2));
    await page.screenshot({ path: output + '/failure.png' });
    await writeFile(output + '/failure.txt', await page.locator('body').innerText());
  }
  throw error;
} finally {
  await browser.close();
}
