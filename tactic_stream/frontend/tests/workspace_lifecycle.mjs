import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
let release;
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 }
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  const ready = () =>
    page.waitForFunction(
      () =>
        document.querySelector('.workspace') &&
        !document.querySelector('.workspace-results[aria-busy="true"]')
    );
  async function signIn(login) {
    await page.getByLabel('Login', { exact: true }).fill(login);
    await page
      .getByLabel('Password', { exact: true })
      .fill('private-test-password');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await ready();
  }
  async function signOut() {
    await page.getByLabel('Account', { exact: true }).click();
    await page
      .locator('.account-menu')
      .getByRole('button', { name: 'Sign Out', exact: true })
      .click();
    await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor();
  }
  await page.goto(process.argv[2] + '/');
  await signIn('admin');
  await page.evaluate(() => {
    let owner =
      document.querySelector('#app').__vue_app__._container._vnode.component;
    while (owner && typeof owner.proxy?.bootstrap !== 'function')
      owner = owner.subTree?.component;
    if (!owner) throw new Error('The actual workspace owner was not mounted');
    window.workspaceOwner = owner.proxy;
  });

  let intercepted;
  const held = new Promise((resolve) => {
    intercepted = resolve;
  });
  let hold = true;
  await page.route('**/admin/project-catalog', async (route) => {
    const response = await route.fetch();
    if (hold) {
      hold = false;
      await new Promise((resolve) => {
        release = resolve;
        intercepted();
      });
    }
    await route.fulfill({ response });
  });
  await page.evaluate(() => {
    window.bootstrapFinished = false;
    window.workspaceOwner.bootstrap().finally(() => {
      window.bootstrapFinished = true;
    });
  });
  await held;
  await signOut();
  await signIn('workspace_user');
  assert.equal(
    await page.evaluate(() => window.workspaceOwner.canAdminister),
    false
  );
  const identity = await page.evaluate(() =>
    JSON.stringify(window.workspaceOwner.userIdentity)
  );
  release();
  await page.waitForFunction(() => window.bootstrapFinished);
  assert.equal(
    await page.evaluate(() => window.workspaceOwner.canAdminister),
    false,
    'A late administrator bootstrap must not replace the new account'
  );
  assert.equal(
    await page.evaluate(() =>
      JSON.stringify(window.workspaceOwner.userIdentity)
    ),
    identity
  );
  await page.unroute('**/admin/project-catalog');

  await signOut();
  let ticketReady;
  const heldTicket = new Promise((resolve) => {
    ticketReady = resolve;
  });
  await page.route('**/admin/rpc', async (route) => {
    if (route.request().postDataJSON().method !== 'get_ticket')
      return route.continue();
    const response = await route.fetch();
    await new Promise((resolve) => {
      release = resolve;
      ticketReady();
    });
    await route.fulfill({ response });
  });
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await heldTicket;
  await page.evaluate(() =>
    window.workspaceOwner.logout('Session ended. Sign in again.')
  );
  const cancelledResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON()?.method === 'get_ticket'
  );
  release();
  await cancelledResponse;
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await page.waitForFunction(() => !window.workspaceOwner.signingIn);
  assert.equal(
    await page.evaluate(() => window.workspaceOwner.session),
    null,
    'A cancelled sign-in cannot restore a signed-out session'
  );
  assert.equal(await page.locator('.workspace').count(), 0);
  assert.equal(
    await page.evaluate(() => localStorage.getItem('tactic_stream.session')),
    null
  );
  await page.unroute('**/admin/rpc');

  await signIn('admin');
  let logoutReady;
  const heldLogout = new Promise((resolve) => {
    logoutReady = resolve;
  });
  await page.route('**/admin/session/logout', async (route) => {
    const response = await route.fetch();
    await new Promise((resolve) => {
      release = resolve;
      logoutReady();
    });
    await route.fulfill({ response });
  });
  await page.getByLabel('Account', { exact: true }).click();
  await page
    .locator('.account-menu')
    .getByRole('button', { name: 'Sign Out', exact: true })
    .click();
  await heldLogout;
  await page.evaluate(() =>
    window.workspaceOwner.logout('Session ended. Sign in again.')
  );
  await signIn('workspace_user');
  const freshTicket = await page.evaluate(
    () => window.workspaceOwner.session.ticket
  );
  release();
  await page.waitForResponse('**/admin/session/logout');
  await page.evaluate(() => new Promise(requestAnimationFrame));
  assert.equal(
    await page.evaluate(() => window.workspaceOwner.session?.ticket),
    freshTicket,
    'A late logout cannot terminate the new account'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Workspace lifecycle: late bootstrap, cancelled sign-in and late logout preserve the current identity.'
  );
} finally {
  release?.();
  await browser.close();
}
