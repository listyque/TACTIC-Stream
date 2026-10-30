import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const output =
  process.env.AGENT_EXECUTOR_OUTPUT ||
  root + '/../tools/frame_scripts/output/executor';
const project = process.env.AGENT_EXECUTOR_PROJECT || 'one';
const ticket = process.env.AGENT_EXECUTOR_TICKET || 'fixture';
let executor = { state: 'stopped', managed: false, error: '' };
const controls = [],
  errors = [];
let server, browser;
const html = `<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import Chat from '/src/features/scripts/AgentRequest.vue';import Providers from '/src/features/configuration/AgentProviders.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';import {windowDirective} from '/src/controls/window.js';import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',popupAnimations:false});initializeAppearance();
createApp({mounted(){window.harness=this},render(){return h('main',[h(Chat,{ref:'chat',ticket:${JSON.stringify(ticket)},capture:()=>({client:'TS',project:${JSON.stringify(project)},page:'',title:'',search_type:'',view:'',search_keys:[]})}),h(Providers,{ref:'providers',ticket:${JSON.stringify(ticket)},project:${JSON.stringify(project)}})])}}).directive('window',windowDirective).mount('#app');
</script><style>html,body,#app{height:100%;width:100%;overflow:hidden}body{margin:0}</style></body></html>`;

try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'agent-executor-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url === '/executor-fixture') {
              res.setHeader('Content-Type', 'text/html');
              res.end(
                await server.transformIndexHtml('/executor-fixture', html)
              );
              return;
            }
            if (req.url !== '/admin/rpc') return next();
            let raw = '';
            for await (const part of req) raw += part;
            const payload = JSON.parse(raw);
            const [auth, command, values] = payload.args;
            assert.equal(auth.project, project);
            if (process.env.AGENT_EXECUTOR_SERVER) {
              const reply = await fetch(
                process.env.AGENT_EXECUTOR_SERVER + '/admin/rpc',
                {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: raw
                }
              );
              res.setHeader('Content-Type', 'application/json');
              res.end(await reply.text());
              return;
            }
            let info = {};
            if (command.endsWith('AgentExecutorCmd')) {
              controls.push(values);
              executor = {
                state: values.action === 'start' ? 'connected' : 'stopped',
                managed: true,
                error: ''
              };
              info = executor;
            } else if (command.endsWith('AgentProviderCmd')) {
              info = {
                executor,
                default: 'codex',
                revision: 'r1',
                profiles: [
                  {
                    id: 'codex',
                    name: 'Codex',
                    kind: 'codex',
                    enabled: true,
                    models: [],
                    status: 'unchecked'
                  }
                ],
                kinds: []
              };
            } else {
              info = {
                executor,
                requests: [],
                hosts:
                  values.action === 'library' || executor.state !== 'connected'
                    ? []
                    : [
                        {
                          host_id: 'fixture',
                          capabilities: {
                            changes: true,
                            providers: [
                              { id: 'codex', name: 'Codex', kind: 'codex' }
                            ],
                            models: [
                              {
                                id: 'fixture',
                                label: 'Fixture',
                                provider: 'codex',
                                is_default: true
                              }
                            ]
                          }
                        }
                      ],
                groups: [],
                projects: [],
                groups_revision: 'r1',
                total: 0,
                next_offset: null
              };
              if (values.action === 'library') {
                delete info.hosts;
                delete info.executor;
              }
            }
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ result: { status: 'OK', info } }));
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0, watch: null },
    logLevel: 'error'
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    hasTouch: true
  });
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto(
    'http://127.0.0.1:' + server.httpServer.address().port + '/executor-fixture'
  );
  try {
    await page.waitForFunction(() => !!window.harness, null, {
      timeout: 10000
    });
  } catch (error) {
    throw Error(errors.join('\n') || error.message);
  }
  for (const [kind, selector] of [
    ['chat', '.agent-request-dialog'],
    ['providers', '.agent-providers-dialog']
  ]) {
    await page.evaluate((kind) => window.harness.$refs[kind].open(), kind);
    const dialog = page.locator(selector);
    await dialog
      .getByRole('button', { name: 'Connect agent', exact: true })
      .tap();
    await dialog
      .getByRole('button', { name: 'Disconnect agent', exact: true })
      .waitFor({ timeout: 20000 })
      .catch(async (error) => {
        throw Error(error.message + '\n' + (await dialog.innerText()));
      });
    await page.screenshot({ path: output + '/' + kind + '-connected.png' });
    await dialog
      .getByRole('button', { name: 'Disconnect agent', exact: true })
      .tap();
    await dialog
      .getByRole('button', { name: 'Connect agent', exact: true })
      .waitFor({ timeout: 20000 });
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  }
  assert.deepEqual(errors, []);
  if (!process.env.AGENT_EXECUTOR_SERVER)
    assert.deepEqual(
      controls.map((value) => value.action),
      ['start', 'stop', 'start', 'stop']
    );
  console.log(
    'PASS: connect/disconnect from browser chat and AI providers through captured project API'
  );
} finally {
  await browser?.close();
  await server?.close();
}
