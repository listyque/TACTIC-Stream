import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const calls = [];
let release;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [
    {
      name: 'table-action-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url === '/table-action-fixture') {
            response.setHeader(
              'Content-Security-Policy',
              "default-src 'self'; script-src 'self' blob:; connect-src 'self'; style-src 'self'"
            );
            response.setHeader('Content-Type', 'text/html');
            response.end('<!doctype html><title>Table action fixture</title>');
            return;
          }
          if (request.url !== '/admin/rpc') {
            next();
            return;
          }
          let body = '';
          for await (const chunk of request) body += chunk;
          const payload = JSON.parse(body);
          calls.push(payload);
          if (payload.args[1] === 'slow')
            await new Promise((resolve) => (release = resolve));
          if (response.destroyed) return;
          response.setHeader('Content-Type', 'application/json');
          response.end(
            JSON.stringify({
              result:
                payload.method === 'query' ? [{ code: 'A' }] : { status: 'OK' }
            })
          );
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null, hmr: false }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'table-action-fixture');
  await page.evaluate(async () => {
    window.runAction = (
      await import('/frontend/src/features/interface/tableScript.js')
    ).runTableScript;
    window.context = {
      project: 'one',
      searchType: 'contract/entity',
      searchKey: 'contract/entity?project=one&code=A',
      searchKeys: ['contract/entity?project=one&code=A'],
      record: {},
      column: 'action',
      view: 'table'
    };
  });
  const result = await page.evaluate(() =>
    window.runAction(
      `var server=TacticServerStub.get();var rows=server.query('contract/entity',{limit:2});return rows;`,
      window.context,
      { ticket: 'fixture-auth', confirm: () => true }
    )
  );
  assert.deepEqual(result.output, [{ code: 'A' }]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].kwargs.limit, 2);
  assert.deepEqual(calls[0].args, [
    { ticket: 'fixture-auth', project: 'one', language: 'python' },
    'contract/entity'
  ]);
  await page.evaluate(() =>
    window.runAction(
      `if(confirm('Proceed?')) TacticServerStub.get().execute_cmd('fixture.Command',{value:1});`,
      window.context,
      { ticket: 'fixture-auth', confirm: () => false }
    )
  );
  assert.equal(
    calls.length,
    1,
    'Cancelling confirmation must not send an API request'
  );
  await page.evaluate(() =>
    window.runAction(
      `if(confirm('Proceed?')) TacticServerStub.get().execute_cmd('fixture.Command',{value:1});`,
      window.context,
      { ticket: 'fixture-auth', confirm: () => true }
    )
  );
  assert.equal(
    calls.length,
    2,
    'Confirmation must execute the command exactly once'
  );
  assert.equal(calls[1].method, 'execute_cmd');
  await page.evaluate(() => {
    window.cancelAction = new AbortController();
    window.pendingAction = window
      .runAction(
        `TacticServerStub.get().query('slow');TacticServerStub.get().insert('contract/entity',{code:'BAD'});`,
        window.context,
        {
          ticket: 'fixture-auth',
          signal: window.cancelAction.signal,
          confirm: () => true
        }
      )
      .then(
        () => '',
        (error) => error.name
      );
  });
  for (let attempt = 0; attempt < 100 && !release; attempt++)
    await new Promise((resolve) => setTimeout(resolve, 10));
  assert(release, 'The worker must enter the fixture RPC');
  await page.evaluate(() => window.cancelAction.abort());
  assert.equal(await page.evaluate(() => window.pendingAction), 'AbortError');
  release();
  release = null;
  assert.equal(
    calls.filter((call) => call.method === 'insert').length,
    0,
    'Cancellation must stop the next mutation'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: actual browser worker RPC under production script CSP, confirmation once, cancellation and no next write'
  );
} finally {
  release?.();
  await browser?.close();
  await server.close();
}
