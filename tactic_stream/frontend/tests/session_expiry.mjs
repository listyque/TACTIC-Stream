import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import { createApp, h } from 'vue'
import ServerUpdates from '/src/features/connection/ServerUpdates.vue'
import { networkSettings } from '/src/features/connection/networkSettings.js'
import { backgroundRequest, updatesAvailable, setUpdatesAvailable } from '/src/features/connection/updateRequests.js'
networkSettings.updateMode = 'poll'
window.backgroundRequest = backgroundRequest
window.updatesAvailable = updatesAvailable
window.setUpdatesAvailable = setUpdatesAvailable
createApp({
  data: () => ({ show: false, ticket: 'rejected-ticket', expirations: [], batches: 0 }),
  mounted() { window.host = this },
  render() { return this.show ? h(ServerUpdates, { ref: 'updates', ticket: this.ticket, project: 'demo',
    onSessionExpired: () => this.expirations.push(updatesAvailable()), onBatch: () => this.batches++ }) : null }
}).mount('#app')
</script></body></html>`;
let server, browser;
try {
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/session-expiry',
    plugins: [
      vue(),
      {
        name: 'session-expiry-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/session-test') return next();
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await server.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage(),
    errors = [],
    calls = [];
  page.setDefaultTimeout(10000);
  page.on('pageerror', (error) => errors.push(error.message));
  await page.clock.install();
  await page.route('**/admin/server-updates', (route) => {
    const payload = route.request().postDataJSON();
    calls.push(payload);
    return payload.ticket === 'rejected-ticket'
      ? route.fulfill({
          status: 403,
          json: { error_code: 'authentication_failed', error: 'Session ended' }
        })
      : route.fulfill({
          json: { result: { messages: [], activity: [], reactions: [] } }
        });
  });
  await page.goto(server.resolvedUrls.local[0] + 'session-test');
  await page.waitForFunction(() => window.host);
  await page.evaluate(() => {
    window.cancelled = false;
    window
      .backgroundRequest(
        'in-flight',
        (signal) =>
          new Promise((resolve, reject) => {
            signal.addEventListener('abort', () => reject(signal.reason), {
              once: true
            });
          })
      )
      .catch(() => {
        window.cancelled = true;
      });
    window.host.show = true;
  });
  await page.waitForFunction(
    () => window.host.expirations.length === 1 && window.cancelled
  );
  assert.deepEqual(
    await page.evaluate(() => window.host.expirations),
    [false],
    'Suspend background reads before notifying the host'
  );
  assert.equal(
    await page.evaluate(async () => {
      let called = false;
      try {
        await window.backgroundRequest('queued', () => {
          called = true;
        });
      } catch {}
      return called;
    }),
    false,
    'No queued read may start with a rejected ticket'
  );
  await page.evaluate(() => {
    window.host.$refs.updates.refresh();
    window.dispatchEvent(new Event('online'));
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.clock.runFor(120000);
  assert.equal(
    calls.length,
    1,
    'Focus and timers must not retry an expired session'
  );
  await page.evaluate(() => {
    window.host.show = false;
  });
  await page.waitForFunction(() => !window.host.$refs.updates);
  await page.evaluate(() => {
    window.host.ticket = 'fresh-ticket';
    window.host.show = true;
  });
  await page.waitForFunction(() => window.host.batches === 1);
  assert.equal(calls.length, 2, 'Signing in restarts updates once');
  assert.equal(await page.evaluate(() => window.updatesAvailable()), true);
  assert.equal(
    await page.evaluate(async () => {
      let started = false;
      const pending = window.backgroundRequest('queued-before-sign-out', () => {
        started = true;
      });
      window.setUpdatesAvailable(false);
      await pending.catch(() => {});
      return started;
    }),
    false,
    'Suspending the session cancels reads before their queued callback starts'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Session expiry: polling and queued reads stop; sign-in resumes updates.'
  );
} finally {
  await browser?.close();
  await server?.close();
}
