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
const desktop = '11111111-1111-4111-8111-111111111111';
let executor = { state: 'stopped', managed: false, error: '', target: '' };
function snapshot() {
  return {
    ...executor,
    targets: [
      { id: desktop, kind: 'desktop', label: 'My computer' },
      { id: 'server', kind: 'server', label: 'TACTIC server' }
    ].map((row) => ({
      ...row,
      state: row.id === executor.target ? executor.state : 'stopped',
      error: ''
    }))
  };
}
const drafts = new Map();
let projectRules = { project, text: '', revision: 'empty' };
const controls = [],
  errors = [];
let server, browser;
const html = `<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import Chat from '/src/features/scripts/AgentRequest.vue';import Providers from '/src/features/configuration/AgentProviders.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';import {windowDirective} from '/src/controls/window.js';import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',popupAnimations:false});initializeAppearance();
createApp({provide:{currentLogin:()=>sessionStorage.getItem('fixtureLogin')||'fixture-user'},mounted(){window.harness=this},render(){return h('main',[h(Chat,{ref:'chat',ticket:${JSON.stringify(ticket)},capture:()=>({client:'TS',project:${JSON.stringify(project)},page:'',title:'',search_type:'',view:'',search_keys:[]})}),h(Providers,{ref:'providers',ticket:${JSON.stringify(ticket)},project:${JSON.stringify(project)}})])}}).directive('window',windowDirective).mount('#app');
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
                error: '',
                target: values.target
              };
              info = snapshot();
            } else if (command.endsWith('AgentProviderCmd')) {
              info = {
                executor: snapshot(),
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
                executor: snapshot(),
                requests: [
                  {
                    request_id: 'row-fixture',
                    project,
                    project_title: 'CG Test',
                    title: 'Сдублируй текущую сцену с длинным названием',
                    status: 'running',
                    activity: Date.now() / 1000
                  }
                ],
                hosts:
                  values.action === 'library' || executor.state !== 'connected'
                    ? []
                    : [
                        {
                          host_id: 'fixture',
                          capabilities: {
                            changes: true,
                            web_search: true,
                            providers: [
                              { id: 'codex', name: 'Codex', kind: 'codex' }
                            ],
                            models: [
                              {
                                id: 'fixture',
                                label: 'Fixture',
                                provider: 'codex',
                                is_default: true,
                                efforts: ['low', 'high']
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
            if (
              command.endsWith('AgentRequestCmd') &&
              ['draft', 'read'].includes(values.action)
            ) {
              if (values.action === 'draft')
                drafts.set(values.request_id, {
                  request_id: values.request_id,
                  status: 'draft',
                  document: {
                    context: values.context,
                    allow_changes: false,
                    allow_web: false
                  },
                  messages: [],
                  events: []
                });
              info = drafts.get(values.request_id) || {
                request_id: values.request_id,
                status: 'completed',
                provider: 'codex',
                model: 'fixture',
                effort: 'low',
                messages: [],
                events: [],
                document: {
                  context: {
                    client: 'TS',
                    project,
                    page: '',
                    title: '',
                    search_type: '',
                    view: '',
                    search_keys: []
                  },
                  prompt: 'Old task',
                  allow_changes: false,
                  allow_web: false
                }
              };
            }
            if (
              command.endsWith('AgentRequestCmd') &&
              ['rules_read', 'rules_save'].includes(values.action)
            ) {
              if (values.action === 'rules_save') {
                assert.equal(values.expected_revision, projectRules.revision);
                projectRules = {
                  project,
                  text: values.text,
                  revision: 'saved'
                };
              }
              info = projectRules;
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
    if (kind === 'chat' && !process.env.AGENT_EXECUTOR_SERVER) {
      const title = dialog.locator(
        '[data-frame="agentHistoryOpen_' + project + ':row-fixtureLabel"]'
      );
      const subtitle = dialog.locator(
        '[data-frame="agentHistoryProject_' + project + ':row-fixture"]'
      );
      await title.waitFor();
      const first = await title.boundingBox(),
        second = await subtitle.boundingBox();
      assert(
        Math.abs(first.x - second.x) < 0.6,
        'Conversation title and project must share the same inset'
      );
      assert(
        Math.abs(first.width - second.width) < 0.6,
        'Conversation lines must reserve the same action space'
      );
    }
    if (kind === 'chat' && !process.env.AGENT_EXECUTOR_SERVER)
      assert(
        await dialog
          .getByRole('button', { name: 'Connect agent', exact: true })
          .isDisabled(),
        'No silent server launch'
      );
    await dialog
      .getByRole('combobox', { name: 'Run agent on', exact: true })
      .selectOption(
        process.env.AGENT_EXECUTOR_SERVER
          ? process.env.AGENT_EXECUTOR_TARGET || 'server'
          : kind === 'providers'
            ? 'server'
            : desktop
      );
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
  if (!process.env.AGENT_EXECUTOR_SERVER) {
    executor = {
      state: 'connected',
      managed: true,
      error: '',
      target: desktop
    };
    await page.reload();
    await page.waitForFunction(() => !!window.harness);
    await page.evaluate(() => window.harness.$refs.chat.open());
    let chat = page.locator('.agent-request-dialog');
    await chat
      .getByRole('combobox', { name: 'Model', exact: true })
      .selectOption('fixture');
    await chat
      .getByRole('combobox', { name: 'Reasoning effort', exact: true })
      .selectOption('high');
    for (const name of ['Allow requested changes', 'Allow internet access']) {
      await chat.getByLabel('Agent permissions', { exact: true }).click();
      await page.getByRole('menuitemcheckbox', { name, exact: true }).click();
    }
    const read = () =>
      page.evaluate(() =>
        JSON.parse(localStorage.getItem('tactic_stream.agentChat.fixture-user'))
      );
    assert.deepEqual(await read(), {
      provider: 'codex',
      model: 'fixture',
      effort: 'high',
      allowChanges: true,
      allowWeb: true
    });
    await page.reload();
    await page.waitForFunction(() => !!window.harness);
    await page.evaluate(() => window.harness.$refs.chat.open());
    chat = page.locator('.agent-request-dialog');
    assert.equal(
      await chat
        .getByRole('combobox', { name: 'Model', exact: true })
        .inputValue(),
      'fixture'
    );
    assert.equal(
      await chat
        .getByRole('combobox', { name: 'Reasoning effort', exact: true })
        .inputValue(),
      'high'
    );
    await chat.getByLabel('Agent permissions', { exact: true }).click();
    for (const name of ['Allow requested changes', 'Allow internet access'])
      assert.equal(
        await page
          .getByRole('menuitemcheckbox', { name, exact: true })
          .getAttribute('aria-checked'),
        'true'
      );
    await page.keyboard.press('Escape');
    const expected = await read();
    await page.evaluate(
      (project) =>
        window.harness.$refs.chat.restoreWindowContext({
          selected: 'old-chat',
          context: {
            client: 'TS',
            project,
            page: '',
            title: '',
            search_type: '',
            view: '',
            search_keys: []
          },
          draft: {}
        }),
      project
    );
    assert.equal(
      await chat
        .getByRole('combobox', { name: 'Reasoning effort', exact: true })
        .inputValue(),
      'low'
    );
    await chat.getByLabel('Agent permissions', { exact: true }).click();
    assert.equal(
      await page
        .getByRole('menuitemcheckbox', {
          name: 'Allow requested changes',
          exact: true
        })
        .getAttribute('aria-checked'),
      'false'
    );
    await page.keyboard.press('Escape');
    assert.deepEqual(
      await read(),
      expected,
      'Opening history must not replace remembered choices'
    );
    await chat.locator('[data-frame="agentRequestNew"]').click();
    await chat
      .getByRole('combobox', { name: 'Reasoning effort', exact: true })
      .waitFor();
    await page.waitForFunction(
      () =>
        document.querySelector('[aria-label="Reasoning effort"]').value ===
        'high'
    );
    await chat.getByLabel('Agent permissions', { exact: true }).click();
    assert.equal(
      await page
        .getByRole('menuitemcheckbox', {
          name: 'Allow requested changes',
          exact: true
        })
        .getAttribute('aria-checked'),
      'true'
    );
    await page.keyboard.press('Escape');
    await page.evaluate(() =>
      sessionStorage.setItem('fixtureLogin', 'another-user')
    );
    await page.reload();
    await page.waitForFunction(() => !!window.harness);
    await page.evaluate(() => window.harness.$refs.chat.open());
    chat = page.locator('.agent-request-dialog');
    assert.equal(
      await chat
        .getByRole('combobox', { name: 'Model', exact: true })
        .inputValue(),
      ''
    );
    assert.equal(
      await chat
        .getByRole('combobox', { name: 'Reasoning effort', exact: true })
        .inputValue(),
      ''
    );
    await chat.getByLabel('Agent permissions', { exact: true }).click();
    for (const name of ['Allow requested changes', 'Allow internet access'])
      assert.equal(
        await page
          .getByRole('menuitemcheckbox', { name, exact: true })
          .getAttribute('aria-checked'),
        'false'
      );
    assert.equal((await read()).effort, 'high');
    await page
      .getByRole('menuitem', { name: 'Project chat rules', exact: true })
      .click();
    const rules = 'Use shot naming; previews in icon; keep comments concise.';
    await chat
      .getByPlaceholder(
        'Describe naming, preview destinations and comment preferences.',
        { exact: true }
      )
      .fill(rules);
    for (const width of [1000, 520, 360]) {
      await page.setViewportSize({ width, height: 760 });
      for (const id of [
        'agentRulesText',
        'agentRulesSave',
        'agentRulesCancel'
      ]) {
        await page.waitForFunction(
          ([id, width]) => {
            const box = document
              .querySelector('[data-frame="' + id + '"]')
              ?.getBoundingClientRect();
            return box && box.x >= 0 && box.right <= width;
          },
          [id, width]
        );
      }
    }
    await page.screenshot({ path: output + '/project-rules.png' });
    await chat
      .getByRole('button', { name: 'Save project rules', exact: true })
      .click();
    await chat.getByLabel('Agent permissions', { exact: true }).waitFor();
    assert.equal(projectRules.text, rules);
    await chat.getByLabel('Agent permissions', { exact: true }).click();
    await page
      .getByRole('menuitem', { name: 'Project chat rules', exact: true })
      .click();
    await page.waitForFunction((text) => {
      const input =
        document.querySelector('[data-frame="agentRulesText"] textarea') ||
        document.querySelector('textarea[data-frame="agentRulesText"]');
      return input && !input.disabled && input.value === text;
    }, rules);
    await chat.getByRole('button', { name: 'Cancel', exact: true }).click();
    console.log(
      'PASS: project rules menu, text editing, save, reopen and narrow layout'
    );

    console.log(
      'PASS: browser composer choices and permissions survive reload and stay account-scoped'
    );
  }
  assert.deepEqual(errors, []);
  if (!process.env.AGENT_EXECUTOR_SERVER)
    assert.deepEqual(
      controls.map((value) => value.action),
      ['start', 'stop', 'start', 'stop']
    );
  if (!process.env.AGENT_EXECUTOR_SERVER)
    assert.deepEqual(
      controls.map((value) => value.target),
      [desktop, desktop, 'server', 'server']
    );
  console.log(
    'PASS: connect/disconnect from browser chat and AI providers through captured project API'
  );
} finally {
  await browser?.close();
  await server?.close();
}
